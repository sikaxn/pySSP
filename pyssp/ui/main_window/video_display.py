from __future__ import annotations

import threading
import weakref

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *
from pyssp.automation_command import AUTOMATION_SOURCE_TYPE
from pyssp.audio_beat_map import beat_phase_at_position, normalize_audio_beat_map
from pyssp.ffmpeg_support import FFMPEG_VIDEO_EXTENSIONS
from pyssp.utility_audio import utility_source_payload
from pyssp.utility_audio import UTILITY_SOURCE_TYPE
from pyssp.utility_audio import UTILITY_MODE_METRONOME, UTILITY_MODE_PINK_NOISE, UTILITY_MODE_WAVEFORM
from pyssp.ui.video_display import VideoDisplayWidget

_VIDEO_FILE_EXTENSIONS = {str(token or "").strip().lower() for token in FFMPEG_VIDEO_EXTENSIONS}
_VIDEO_FRAME_FALLBACK_INTERVAL_MS = 33
_VIDEO_BACKDROP_MESSAGE = "No video is playing"
_MERGED_VIDEO_ROUTE_OPTIONS = [
    (DISPLAY_ROUTE_SOURCE_LABELS[DISPLAY_FOCUS_VIDEO], DISPLAY_FOCUS_VIDEO),
    (DISPLAY_ROUTE_SOURCE_LABELS[DISPLAY_FOCUS_IMAGE], DISPLAY_FOCUS_IMAGE),
    ("Lyric Display", DISPLAY_FOCUS_LYRIC),
    ("Stage Display", DISPLAY_FOCUS_STAGE),
    (DISPLAY_ROUTE_SOURCE_LABELS[DISPLAY_FOCUS_METRONOME], DISPLAY_FOCUS_METRONOME),
    ("Backdrop", DISPLAY_FOCUS_BACKDROP),
    (DISPLAY_ROUTE_SOURCE_LABELS[DISPLAY_ROUTE_SOURCE_BLANK], DISPLAY_ROUTE_SOURCE_BLANK),
    ("White Screen", DISPLAY_FOCUS_WHITE),
    ("Colour Bars", DISPLAY_FOCUS_COLOUR_BARS),
]


def _freeze_snapshot_token(value):
    if isinstance(value, dict):
        return tuple((str(key), _freeze_snapshot_token(item)) for key, item in sorted(value.items(), key=lambda pair: str(pair[0])))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_snapshot_token(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze_snapshot_token(item) for item in value))
    return value


@dataclass(frozen=True)
class _VideoDecodeRequest:
    tag: int
    path: str
    start_ms: int
    width: int
    height: int
    interval_ms: int
    stream: bool


class _VideoFrameDecodeDispatcher(QObject):
    frameDecoded = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._condition = threading.Condition()
        self._request: Optional[_VideoDecodeRequest] = None
        self._generation = 0
        self._shutdown = False
        self._process: Optional[subprocess.Popen] = None
        self._latest_frame: Optional[tuple[int, str, int, int, int, bytes]] = None
        self._frame_signal_pending = False
        self._thread = threading.Thread(target=self._run, name="pyssp-video-frame-decode", daemon=True)
        self._thread.start()
        if parent is not None:
            self_ref = weakref.ref(self)
            parent.destroyed.connect(lambda _obj=None, ref=self_ref: (ref() and ref().stop()))

    def request_stream(self, tag: int, path: str, start_ms: int, width: int, height: int, interval_ms: int) -> None:
        candidate = str(path or "").strip()
        if not candidate:
            return
        self._set_request(
            _VideoDecodeRequest(
                tag=max(0, int(tag)),
                path=candidate,
                start_ms=max(0, int(start_ms)),
                width=max(1, int(width)),
                height=max(1, int(height)),
                interval_ms=max(16, int(interval_ms)),
                stream=True,
            )
        )

    def request_frame(self, tag: int, path: str, position_ms: int, width: int, height: int) -> None:
        candidate = str(path or "").strip()
        if not candidate:
            return
        self._set_request(
            _VideoDecodeRequest(
                tag=max(0, int(tag)),
                path=candidate,
                start_ms=max(0, int(position_ms)),
                width=max(1, int(width)),
                height=max(1, int(height)),
                interval_ms=_VIDEO_FRAME_FALLBACK_INTERVAL_MS,
                stream=False,
            )
        )

    def clear(self) -> None:
        self._set_request(None)

    def take_latest_frame(self) -> Optional[tuple[int, str, int, int, int, bytes]]:
        with self._condition:
            frame = self._latest_frame
            self._latest_frame = None
            self._frame_signal_pending = False
            return frame

    def _set_request(self, request: Optional[_VideoDecodeRequest]) -> None:
        with self._condition:
            self._request = request
            self._generation += 1
            self._latest_frame = None
            self._frame_signal_pending = False
            self._terminate_process_locked()
            self._condition.notify_all()

    def stop(self, timeout_sec: float = 1.5) -> None:
        with self._condition:
            self._shutdown = True
            self._request = None
            self._generation += 1
            self._terminate_process_locked()
            self._condition.notify_all()
        try:
            self._thread.join(max(0.1, float(timeout_sec)))
        except Exception:
            pass

    def _run(self) -> None:
        last_generation = -1
        while True:
            with self._condition:
                while (not self._shutdown) and self._generation == last_generation:
                    self._condition.wait()
                if self._shutdown:
                    return
                last_generation = self._generation
                request = self._request
            if request is None:
                continue
            if request.stream:
                self._run_stream(request, last_generation)
            else:
                self._run_single_frame(request, last_generation)

    def _run_single_frame(self, request: _VideoDecodeRequest, generation: int) -> None:
        payload = self._decode_frame_bytes(request)
        if not payload or self._is_stale(generation):
            return
        self._publish_frame(request.tag, request.path, request.start_ms, request.width, request.height, payload)

    def _run_stream(self, request: _VideoDecodeRequest, generation: int) -> None:
        proc = self._start_stream_process(request)
        if proc is None:
            return
        frame_size = max(1, int(request.width) * int(request.height) * 3)
        frame_index = 0
        with self._condition:
            self._process = proc
        try:
            while not self._is_stale(generation):
                payload = self._read_exact(proc.stdout, frame_size)
                if len(payload) != frame_size:
                    break
                pts_ms = request.start_ms + (frame_index * request.interval_ms)
                frame_index += 1
                if self._is_stale(generation):
                    break
                self._publish_frame(request.tag, request.path, pts_ms, request.width, request.height, payload)
        finally:
            with self._condition:
                if self._process is proc:
                    self._terminate_process_locked()

    def _is_stale(self, generation: int) -> bool:
        with self._condition:
            return self._shutdown or generation != self._generation

    def _start_stream_process(self, request: _VideoDecodeRequest) -> Optional[subprocess.Popen]:
        ffmpeg = get_ffmpeg_executable()
        if not ffmpeg:
            return None
        seconds = max(0.0, float(request.start_ms) / 1000.0)
        try:
            return subprocess.Popen(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-hwaccel",
                    "auto",
                    "-re",
                    "-fflags",
                    "nobuffer",
                    "-flags",
                    "low_delay",
                    "-noautorotate",
                    "-ss",
                    f"{seconds:.3f}",
                    "-i",
                    request.path,
                    "-an",
                    "-sn",
                    "-dn",
                    "-vf",
                    f"scale={int(request.width)}:{int(request.height)}:flags=bilinear",
                    "-pix_fmt",
                    "rgb24",
                    "-f",
                    "rawvideo",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                bufsize=max(1, request.width * request.height * 3 * 2),
                **_video_subprocess_platform_kwargs(),
            )
        except Exception:
            return None

    @staticmethod
    def _decode_frame_bytes(request: _VideoDecodeRequest) -> bytes:
        ffmpeg = get_ffmpeg_executable()
        if not ffmpeg:
            return b""
        seconds = max(0.0, float(request.start_ms) / 1000.0)
        try:
            proc = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-hwaccel",
                    "auto",
                    "-noautorotate",
                    "-ss",
                    f"{seconds:.3f}",
                    "-i",
                    request.path,
                    "-an",
                    "-sn",
                    "-dn",
                    "-vf",
                    f"scale={int(request.width)}:{int(request.height)}:flags=bilinear",
                    "-frames:v",
                    "1",
                    "-pix_fmt",
                    "rgb24",
                    "-f",
                    "rawvideo",
                    "-",
                ],
                capture_output=True,
                timeout=8,
                check=False,
                **_video_subprocess_platform_kwargs(),
            )
        except Exception:
            return b""
        return bytes(proc.stdout or b"")

    @staticmethod
    def _read_exact(stream, byte_count: int) -> bytes:
        if stream is None or byte_count <= 0:
            return b""
        chunks: list[bytes] = []
        remaining = int(byte_count)
        while remaining > 0:
            chunk = stream.read(remaining)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _terminate_process_locked(self) -> None:
        proc = self._process
        self._process = None
        if proc is None:
            return
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=0.5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=0.5)
            except Exception:
                pass

    def _publish_frame(self, tag: int, path: str, pts_ms: int, width: int, height: int, payload: bytes) -> None:
        should_emit = False
        with self._condition:
            if self._shutdown:
                return
            self._latest_frame = (int(tag), str(path), int(pts_ms), int(width), int(height), bytes(payload))
            if not self._frame_signal_pending:
                self._frame_signal_pending = True
                should_emit = True
        if not should_emit:
            return
        try:
            self.frameDecoded.emit()
        except Exception:
            with self._condition:
                self._frame_signal_pending = False


def _video_subprocess_platform_kwargs() -> dict:
    if os.name != "nt":
        return {}
    kwargs: dict = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    try:
        startup = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        startup.wShowWindow = 0
        kwargs["startupinfo"] = startup
    except Exception:
        pass
    return kwargs


class VideoDisplayMixin:
    @staticmethod
    def _manual_video_route_value_from_modes(mode_playing: str, mode_idle: str, *, default: str = "blank") -> str:
        playing = normalize_display_focus_override(str(mode_playing or ""), default=DISPLAY_FOCUS_FOLLOW)
        idle = normalize_display_route_source(str(mode_idle or default), default=default)
        valid = {value for _label, value in _MERGED_VIDEO_ROUTE_OPTIONS}
        if playing in valid:
            return playing
        if playing == DISPLAY_FOCUS_NONE:
            return DISPLAY_ROUTE_SOURCE_BLANK
        if idle in valid:
            return idle
        return default

    @staticmethod
    def _slot_allows_video_loading(slot: Optional[SoundButtonData]) -> bool:
        return not bool(getattr(slot, "disable_video_loading", False)) if slot is not None else True

    def _path_may_have_video(self, path: str) -> bool:
        candidate = str(path or "").strip()
        if not candidate:
            return False
        ext = os.path.splitext(candidate)[1].strip().lower()
        if not ext:
            return True
        return ext in _VIDEO_FILE_EXTENSIONS

    def _build_video_control_dock(self) -> None:
        dock = QDockWidget("Video Control", self)
        dock.setObjectName("video_control_widget_dock")
        panel = QWidget(dock)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        form = QFormLayout()

        self.video_follow_sound_button_focus_checkbox = QCheckBox("Follow Sound Button Display Focus", panel)
        self.video_follow_sound_button_focus_checkbox.setChecked(
            normalize_display_focus_override(self.video_display_mode_playing, default=DISPLAY_FOCUS_FOLLOW)
            == DISPLAY_FOCUS_FOLLOW
        )
        form.addRow(self.video_follow_sound_button_focus_checkbox)

        self.video_route_combo = QComboBox(panel)
        for label, value in _MERGED_VIDEO_ROUTE_OPTIONS:
            self.video_route_combo.addItem(label, value)
        manual_route = self._manual_video_route_value_from_modes(self.video_display_mode_playing, self.video_display_mode_idle)
        index = self.video_route_combo.findData(manual_route)
        self.video_route_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("Otherwise:", self.video_route_combo)
        layout.addLayout(form)

        self.video_preview_widget = VideoDisplayWidget(panel, allow_fullscreen_toggle=False)
        self.video_preview_widget.setMinimumHeight(180)
        self.video_preview_widget.surfaceChanged.connect(self._on_video_surface_geometry_changed)
        layout.addWidget(self.video_preview_widget, 1)

        dock.setWidget(panel)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetMovable
        )
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        if bool(self.show_video_control_panel):
            dock.show()
        else:
            self._park_hidden_dock(dock)
        dock.visibilityChanged.connect(self._on_video_control_dock_visibility_changed)
        dock.dockLocationChanged.connect(lambda _area: self._schedule_dock_layout_save())
        dock.topLevelChanged.connect(lambda _floating: self._schedule_dock_layout_save())
        self.video_follow_sound_button_focus_checkbox.toggled.connect(self._on_video_display_route_changed)
        self.video_route_combo.currentIndexChanged.connect(self._on_video_display_route_changed)
        self.video_control_dock = dock
        self.video_control_panel = panel
        self._refresh_video_display(force=True)

    def _on_video_control_dock_visibility_changed(self, visible: bool) -> None:
        self.show_video_control_panel = bool(visible)
        action = self._menu_actions.get("video_control_panel")
        if action is not None:
            action.setChecked(bool(visible))
        self._schedule_dock_layout_save()
        if not self._suspend_settings_save:
            self._save_settings()

    def _toggle_video_control_panel(self) -> None:
        if self.video_control_dock is None:
            return
        if self.video_control_dock.isVisible():
            self._park_hidden_dock(self.video_control_dock)
            return
        self.video_control_dock.show()

    def _on_video_display_route_changed(self, _index: int = 0) -> None:
        manual_route = str(self.video_route_combo.currentData() or "blank")
        if bool(self.video_follow_sound_button_focus_checkbox.isChecked()):
            self._apply_video_display_route_action("set_source_only", source=manual_route, refresh=False)
            self._apply_video_display_route_action("follow", mode="enable", refresh=True)
        else:
            self._apply_video_display_route_action("set_source_override", source=manual_route, refresh=True)
        if not self._suspend_settings_save:
            self._save_settings()

    def _video_display_follow_sound_button_focus_enabled(self) -> bool:
        return normalize_display_focus_override(
            getattr(self, "video_display_mode_playing", DISPLAY_FOCUS_FOLLOW),
            default=DISPLAY_FOCUS_FOLLOW,
        ) == DISPLAY_FOCUS_FOLLOW

    def _video_display_route_state_payload(self) -> dict:
        return {
            "video_display_follow_sound_button_focus": self._video_display_follow_sound_button_focus_enabled(),
            "video_display_manual_source": self._manual_video_route_value_from_modes(
                getattr(self, "video_display_mode_playing", DISPLAY_FOCUS_FOLLOW),
                getattr(self, "video_display_mode_idle", DISPLAY_ROUTE_SOURCE_BLANK),
            ),
            "video_display_active_source": str(self._active_video_route_mode() or DISPLAY_ROUTE_SOURCE_BLANK),
        }

    def _sync_video_display_route_controls_from_state(self) -> None:
        checkbox = getattr(self, "video_follow_sound_button_focus_checkbox", None)
        combo = getattr(self, "video_route_combo", None)
        if checkbox is None and combo is None:
            return
        checked = self._video_display_follow_sound_button_focus_enabled()
        manual_route = self._manual_video_route_value_from_modes(
            getattr(self, "video_display_mode_playing", DISPLAY_FOCUS_FOLLOW),
            getattr(self, "video_display_mode_idle", DISPLAY_ROUTE_SOURCE_BLANK),
        )
        if checkbox is not None:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)
        if combo is not None:
            combo.blockSignals(True)
            index = combo.findData(manual_route)
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def _apply_video_display_route_action(
        self,
        action: str,
        *,
        source: str = "",
        mode: str = "",
        refresh: bool = True,
    ) -> dict:
        action_token = str(action or "").strip().lower()
        if action_token not in {"set_source_override", "set_source_only", "follow"}:
            return self._api_error("invalid_action", "Action must be set_source_override, set_source_only, or follow.")

        source_token = ""
        if action_token in {"set_source_override", "set_source_only"}:
            source_token = normalize_display_route_source(source, allow_empty=True)
            if source_token not in DISPLAY_ROUTE_SOURCE_VALUES:
                return self._api_error("invalid_source", "Source is not supported for video display routing.")

        mode_token = ""
        if action_token == "follow":
            parser = getattr(self, "_parse_api_mode", None)
            mode_token = parser(mode) if callable(parser) else str(mode or "").strip().lower()
            if mode_token not in {"enable", "disable", "toggle"}:
                return self._api_error("invalid_mode", "Mode must be enable, disable, or toggle.")

        if action_token == "set_source_override":
            self.video_display_mode_idle = source_token
            self.ndi_output_mode_idle = source_token
            self.video_display_mode_playing = source_token
            self.ndi_output_mode_playing = source_token
        elif action_token == "set_source_only":
            self.video_display_mode_idle = source_token
            self.ndi_output_mode_idle = source_token
        else:
            if mode_token == "toggle":
                mode_token = "disable" if self._video_display_follow_sound_button_focus_enabled() else "enable"
            if mode_token == "enable":
                self.video_display_mode_playing = DISPLAY_FOCUS_FOLLOW
                self.ndi_output_mode_playing = DISPLAY_FOCUS_FOLLOW
            else:
                self.video_display_mode_playing = normalize_display_route_source(
                    getattr(self, "video_display_mode_idle", DISPLAY_ROUTE_SOURCE_BLANK),
                    default=DISPLAY_ROUTE_SOURCE_BLANK,
                )
                self.ndi_output_mode_playing = normalize_display_route_source(
                    getattr(self, "ndi_output_mode_idle", "backdrop"),
                    default="backdrop",
                )

        self._sync_video_display_route_controls_from_state()
        if refresh:
            self._refresh_video_display(force=True)
        return self._api_success(self._video_display_route_state_payload())

    def _open_video_display(self) -> None:
        if self._video_display_window is None:
            self._video_display_window = VideoDisplayWindow(self)
            self._video_display_window.destroyed.connect(self._on_video_display_destroyed)
            self._video_display_window.display_widget.surfaceChanged.connect(self._on_video_surface_geometry_changed)
        self._video_display_window.show()
        self._video_display_window.raise_()
        self._video_display_window.activateWindow()
        self._refresh_video_display(force=True)

    def _on_video_display_destroyed(self, _obj=None) -> None:
        self._video_display_window = None

    def _open_metronome_display(self) -> None:
        if self._metronome_display_window is None:
            self._metronome_display_window = MetronomeDisplayWindow(self)
            self._metronome_display_window.destroyed.connect(self._on_metronome_display_destroyed)
            self._metronome_display_window.display_widget.surfaceChanged.connect(self._on_video_surface_geometry_changed)
        self._metronome_display_window.show()
        self._metronome_display_window.raise_()
        self._metronome_display_window.activateWindow()
        self._refresh_video_display(force=True)

    def _on_metronome_display_destroyed(self, _obj=None) -> None:
        self._metronome_display_window = None

    def _normalized_media_probe_key(self, path: str) -> str:
        return os.path.normcase(os.path.normpath(str(path or "").strip()))

    def _media_probe_for_path(self, path: str) -> MediaProbeInfo:
        candidate = str(path or "").strip()
        if not candidate:
            return MediaProbeInfo()
        if not self._path_may_have_video(candidate):
            return MediaProbeInfo()
        key = self._normalized_media_probe_key(candidate)
        cached = self._media_probe_cache.get(key)
        if cached is not None:
            return cached
        info = probe_media_info(candidate)
        self._media_probe_cache[key] = info
        return info

    def _slot_has_video_media(self, slot: Optional[SoundButtonData]) -> bool:
        if slot is None or slot.marker or (not slot.assigned) or (not self._slot_allows_video_loading(slot)):
            return False
        path = str(slot.file_path or "").strip()
        if not path:
            return False
        if not self._path_may_have_video(path):
            return False
        return bool(self._media_probe_for_path(path).has_video)

    def _current_video_slot_and_probe(self) -> tuple[Optional[SoundButtonData], MediaProbeInfo]:
        if self.current_playing is None:
            return None, MediaProbeInfo()
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return None, MediaProbeInfo()
        if not self._slot_allows_video_loading(slot):
            return slot, MediaProbeInfo()
        path = str(slot.file_path or "").strip()
        if not self._path_may_have_video(path):
            return slot, MediaProbeInfo()
        return slot, self._media_probe_for_path(path)

    def _default_display_focus_for_slot(self, slot: Optional[SoundButtonData]) -> str:
        if slot is None or slot.marker or (not slot.assigned):
            return DISPLAY_FOCUS_NONE
        if slot.source_type == AUTOMATION_SOURCE_TYPE:
            return normalize_display_focus(
                getattr(self, "display_focus_default_automation", DISPLAY_FOCUS_NONE),
                default=DISPLAY_FOCUS_NONE,
            )
        if slot.source_type == UTILITY_SOURCE_TYPE:
            utility_mode = ""
            if slot.utility_spec is not None:
                utility_mode = str(getattr(slot.utility_spec, "mode", "") or "").strip().lower()
            if utility_mode == UTILITY_MODE_PINK_NOISE:
                default_focus = getattr(self, "display_focus_default_utility_noise", DISPLAY_FOCUS_COLOUR_BARS)
            elif utility_mode == UTILITY_MODE_WAVEFORM:
                default_focus = getattr(self, "display_focus_default_utility_tone", DISPLAY_FOCUS_COLOUR_BARS)
            elif utility_mode == UTILITY_MODE_METRONOME:
                default_focus = getattr(self, "display_focus_default_utility_metronome", DISPLAY_FOCUS_METRONOME)
            else:
                default_focus = getattr(self, "display_focus_default_utility_blank", DISPLAY_FOCUS_NONE)
            return normalize_display_focus(default_focus, default=DISPLAY_FOCUS_NONE)
        lyric_path = str(getattr(slot, "lyric_file", "") or "").strip()
        if lyric_path:
            return normalize_display_focus(
                getattr(self, "display_focus_default_audio_with_lyric", DISPLAY_FOCUS_LYRIC),
                default=DISPLAY_FOCUS_LYRIC,
            )
        if self._slot_has_video_media(slot):
            return normalize_display_focus(
                getattr(self, "display_focus_default_video", getattr(self, "video_display_mode_playing", DISPLAY_FOCUS_VIDEO)),
                default=DISPLAY_FOCUS_VIDEO,
            )
        return normalize_display_focus(
            getattr(self, "display_focus_default_audio", DISPLAY_FOCUS_NONE),
            default=DISPLAY_FOCUS_NONE,
        )

    def _resolved_display_focus_for_slot(self, slot: Optional[SoundButtonData], *, persist: bool = False) -> str:
        if slot is None:
            return DISPLAY_FOCUS_NONE
        raw_value = normalize_display_focus(
            getattr(slot, "display_focus", ""),
            allow_empty=True,
            default=DISPLAY_FOCUS_NONE,
        )
        focus = raw_value or self._default_display_focus_for_slot(slot)
        if persist and focus and getattr(slot, "display_focus", "") != focus:
            slot.display_focus = focus
        return normalize_display_focus(focus, default=DISPLAY_FOCUS_NONE)

    @staticmethod
    def _route_mode_for_display_focus(focus: str) -> str:
        token = normalize_display_focus(focus, default=DISPLAY_FOCUS_NONE)
        return token if token in DISPLAY_FOCUS_ROUTE_MODES else "blank"

    def _active_video_route_mode(self) -> str:
        slot, info = self._current_video_slot_and_probe()
        if slot is not None and slot.source_type == AUTOMATION_SOURCE_TYPE:
            return str(self.video_display_mode_idle or "blank")
        override_focus = normalize_display_focus_override(
            getattr(self, "video_display_mode_playing", DISPLAY_FOCUS_FOLLOW),
            default=DISPLAY_FOCUS_FOLLOW,
        )
        slot_focus = self._resolved_display_focus_for_slot(slot, persist=slot is not None)
        focus = slot_focus if override_focus == DISPLAY_FOCUS_FOLLOW else override_focus
        if bool(getattr(self, "_video_prestart_hold_until_frame", False)):
            expected_path = str(getattr(self, "_video_prestart_hold_expected_path", "") or "").strip()
            if focus == DISPLAY_FOCUS_VIDEO and expected_path and self._path_may_have_video(expected_path):
                expected_info = self._media_probe_for_path(expected_path)
                if expected_info.has_video:
                    return "video"
            if focus == DISPLAY_FOCUS_VIDEO and slot is not None and info.has_video:
                return "video"
        if bool(getattr(self, "_video_force_blank_until_frame", False)):
            expected_path = str(getattr(self, "_video_force_blank_expected_path", "") or "").strip()
            if focus == DISPLAY_FOCUS_VIDEO and expected_path and self._path_may_have_video(expected_path):
                expected_info = self._media_probe_for_path(expected_path)
                if expected_info.has_video:
                    return "blank"
            if focus == DISPLAY_FOCUS_VIDEO and slot is not None and info.has_video:
                return "blank"
        if slot is None:
            return str(self.video_display_mode_idle or "blank")
        status = self._stage_playback_status()
        if status == "not_playing":
            return str(self.video_display_mode_idle or "blank")
        if focus == DISPLAY_FOCUS_NONE:
            return str(self.video_display_mode_idle or "blank")
        if focus == DISPLAY_FOCUS_VIDEO and not info.has_video:
            return str(self.video_display_mode_idle or "blank")
        if focus == DISPLAY_FOCUS_IMAGE and self._slot_display_image_pixmap(slot).isNull():
            return str(self.video_display_mode_idle or "blank")
        return self._route_mode_for_display_focus(focus)

    def _active_ndi_route_mode(self) -> str:
        return self._active_video_route_mode()

    def _video_frame_interval_ms(self, info: Optional[MediaProbeInfo] = None) -> int:
        fps = 0.0
        if info is not None:
            try:
                fps = float(getattr(info, "fps", 0.0) or 0.0)
            except Exception:
                fps = 0.0
        if fps <= 0.0:
            return _VIDEO_FRAME_FALLBACK_INTERVAL_MS
        fps = max(15.0, min(60.0, fps))
        return max(16, int(round(1000.0 / fps)))

    def _default_video_backdrop_path(self) -> str:
        helper = getattr(self, "_asset_file_path", None)
        if callable(helper):
            try:
                return str(helper("logo2.png") or "").strip()
            except Exception:
                return ""
        return ""

    def _resolved_video_backdrop_path(self) -> str:
        default_path = self._default_video_backdrop_path()
        if bool(getattr(self, "video_display_use_default_backdrop", True)):
            return default_path
        custom_path = str(getattr(self, "video_display_backdrop_path", "") or "").strip()
        if custom_path:
            candidate = QPixmap(custom_path)
            if not candidate.isNull():
                return custom_path
        return default_path

    def _video_backdrop_pixmap(self) -> QPixmap:
        path = self._resolved_video_backdrop_path()
        cache_key = str(path or "").strip()
        if cache_key == str(getattr(self, "_video_backdrop_cache_path", "") or ""):
            return QPixmap(getattr(self, "_video_backdrop_cache_pixmap", QPixmap()))
        pixmap = QPixmap(cache_key) if cache_key else QPixmap()
        if pixmap.isNull() and cache_key != self._default_video_backdrop_path():
            fallback_path = self._default_video_backdrop_path()
            pixmap = QPixmap(fallback_path) if fallback_path else QPixmap()
            cache_key = fallback_path
        self._video_backdrop_cache_path = cache_key
        self._video_backdrop_cache_pixmap = QPixmap(pixmap)
        return pixmap

    def _video_backdrop_message_text(self) -> str:
        if not bool(getattr(self, "video_display_show_backdrop_message", True)):
            return ""
        slot, info = self._current_video_slot_and_probe()
        if slot is not None and info.has_video and self._stage_playback_status() == "playing":
            return ""
        return _VIDEO_BACKDROP_MESSAGE

    def _video_output_dimensions(self, info: Optional[MediaProbeInfo]) -> tuple[int, int]:
        width = int(getattr(info, "width", 0) or 0) if info is not None else 0
        height = int(getattr(info, "height", 0) or 0) if info is not None else 0
        rotation = int(getattr(info, "rotation_deg", 0) or 0) if info is not None else 0
        if rotation in {90, 270}:
            width, height = height, width
        if width <= 0 or height <= 0:
            return 640, 360
        return width, height

    def _video_decode_dimensions(self, info: Optional[MediaProbeInfo]) -> tuple[int, int]:
        width = int(getattr(info, "width", 0) or 0) if info is not None else 0
        height = int(getattr(info, "height", 0) or 0) if info is not None else 0
        if width <= 0 or height <= 0:
            return 640, 360
        return width, height

    def _next_video_request_tag(self) -> int:
        self._video_request_tag_serial = max(0, int(getattr(self, "_video_request_tag_serial", 0))) + 1
        return self._video_request_tag_serial

    def _video_target_surface_pixel_size(self) -> tuple[int, int]:
        candidates: list[tuple[int, int]] = []
        for widget in (
            getattr(self, "video_preview_widget", None),
            None if self._video_display_window is None else self._video_display_window.display_widget,
        ):
            if widget is None or (not widget.isVisible()) or getattr(widget, "_mode", "") != "video":
                continue
            try:
                dpr = max(1.0, float(widget.devicePixelRatioF()))
            except Exception:
                dpr = 1.0
            width = max(0, int(round(widget.width() * dpr)))
            height = max(0, int(round(widget.height() * dpr)))
            if width > 0 and height > 0:
                candidates.append((width, height))
        if bool(getattr(self, "ndi_output_enabled", False)) and self._active_ndi_route_mode() == "video":
            width, height = self._ndi_output_dimensions()
            if width > 0 and height > 0:
                candidates.append((width, height))
        if not candidates:
            return 0, 0
        return max(candidates, key=lambda item: item[0] * item[1])

    def _video_snapshot_target_pixel_size(self) -> tuple[int, int]:
        candidates: list[tuple[int, int]] = []
        for widget in (
            getattr(self, "video_preview_widget", None),
            None if self._video_display_window is None else self._video_display_window.display_widget,
        ):
            if widget is None or (not widget.isVisible()):
                continue
            try:
                dpr = max(1.0, float(widget.devicePixelRatioF()))
            except Exception:
                dpr = 1.0
            width = max(0, int(round(widget.width() * dpr)))
            height = max(0, int(round(widget.height() * dpr)))
            if width > 0 and height > 0:
                candidates.append((width, height))
        if bool(getattr(self, "ndi_output_enabled", False)):
            ndi_mode = self._active_ndi_route_mode()
            if ndi_mode in {
                DISPLAY_FOCUS_STAGE,
                DISPLAY_FOCUS_LYRIC,
                DISPLAY_FOCUS_BACKDROP,
                DISPLAY_FOCUS_IMAGE,
                DISPLAY_FOCUS_METRONOME,
                "blank",
                DISPLAY_FOCUS_WHITE,
                DISPLAY_FOCUS_COLOUR_BARS,
            }:
                width, height = self._ndi_output_dimensions()
                if width > 0 and height > 0:
                    candidates.append((width, height))
        if not candidates:
            return 0, 0
        return max(candidates, key=lambda item: item[0] * item[1])

    def _video_target_decode_dimensions(self, info: Optional[MediaProbeInfo]) -> tuple[int, int]:
        source_width, source_height = self._video_decode_dimensions(info)
        target_width, target_height = self._video_target_surface_pixel_size()
        if target_width <= 0 or target_height <= 0:
            return source_width, source_height
        output_width, output_height = self._video_output_dimensions(info)
        if output_width <= 0 or output_height <= 0:
            return source_width, source_height
        scale = min(1.0, min(target_width / float(output_width), target_height / float(output_height)))
        if scale >= 0.999:
            return source_width, source_height
        desired_output_width = max(2, int(round(output_width * scale)))
        desired_output_height = max(2, int(round(output_height * scale)))
        rotation = int(getattr(info, "rotation_deg", 0) or 0) if info is not None else 0
        if rotation in {90, 270}:
            return desired_output_height, desired_output_width
        return desired_output_width, desired_output_height

    def _on_video_surface_geometry_changed(self) -> None:
        if bool(getattr(self, "_video_surface_geometry_refresh_inflight", False)):
            return
        self._video_surface_geometry_refresh_inflight = True
        try:
            self._stage_snapshot_cache_key = None
            self._stage_snapshot_cache_pixmap = QPixmap()
            self._lyric_snapshot_cache_key = None
            self._lyric_snapshot_cache_pixmap = QPixmap()
            mode = self._active_video_route_mode()
            if mode == "video":
                self._clear_video_frame_runtime(preserve_current_frame=True)
                self._refresh_video_display(force=True)
                return
            if mode in {DISPLAY_FOCUS_STAGE, DISPLAY_FOCUS_LYRIC, DISPLAY_FOCUS_METRONOME}:
                self._refresh_video_display(force=True)
        finally:
            self._video_surface_geometry_refresh_inflight = False

    def _invalidate_video_playback_sync(self, *, refresh: bool = False) -> None:
        self._video_transport_revision = max(0, int(getattr(self, "_video_transport_revision", 0))) + 1
        self._clear_video_frame_runtime(preserve_current_frame=True)
        if refresh:
            self._refresh_video_display(force=True)

    def _start_video_switch_blank(self, expected_path: str = "") -> None:
        self._video_force_blank_until_frame = True
        self._video_force_blank_expected_path = self._normalized_media_probe_key(expected_path) if expected_path else ""
        self._clear_video_frame_runtime(preserve_current_frame=False)
        self._refresh_video_display(force=True)

    def _clear_video_switch_blank(self) -> None:
        self._video_force_blank_until_frame = False
        self._video_force_blank_expected_path = ""

    def _begin_video_prestart_hold(self, expected_path: str = "") -> None:
        self._video_prestart_hold_until_frame = True
        self._video_prestart_hold_expected_path = self._normalized_media_probe_key(expected_path) if expected_path else ""
        self._clear_video_frame_runtime(preserve_current_frame=False)
        self._refresh_video_display(force=True)

    def _clear_video_prestart_hold(self) -> None:
        self._video_prestart_hold_until_frame = False
        self._video_prestart_hold_expected_path = ""

    def _video_frame_bucket_ms(self, position_ms: int, info: Optional[MediaProbeInfo] = None) -> int:
        interval_ms = self._video_frame_interval_ms(info)
        return max(0, int(round(max(0, int(position_ms)) / float(interval_ms)) * interval_ms))

    def _video_display_target_visible(self) -> bool:
        preview = getattr(self, "video_preview_widget", None)
        if preview is not None and preview.isVisible():
            return True
        if self._video_display_window is not None and self._video_display_window.isVisible():
            return True
        return bool(getattr(self, "ndi_output_enabled", False)) and self._active_ndi_route_mode() == "video"

    def _current_video_display_position_ms(self) -> int:
        if self.current_playing is None:
            try:
                return max(0, int(self.seek_slider.value()))
            except Exception:
                return 0
        player = self._player_for_slot_key(self.current_playing)
        if player is None:
            try:
                return max(0, int(self.seek_slider.value()))
            except Exception:
                return 0
        try:
            absolute_pos = max(0, int(self._player_transport_sync_ms(player)))
        except Exception:
            absolute_pos = 0
        try:
            return max(0, int(self._transport_display_ms_for_absolute(absolute_pos)))
        except Exception:
            return absolute_pos

    def _video_frame_pixmap(self, path: str, position_ms: int) -> QPixmap:
        candidate = str(path or "").strip()
        if not candidate:
            return QPixmap()
        info = self._media_probe_for_path(candidate)
        bucket_ms = self._video_frame_bucket_ms(position_ms, info)
        cache_key = (self._normalized_media_probe_key(candidate), bucket_ms)
        cached = self._video_frame_cache.get(cache_key)
        if cached is not None:
            return QPixmap(cached)
        return QPixmap()

    def _render_widget_snapshot(self, widget: QWidget, width: int = 960, height: int = 540) -> QPixmap:
        widget.resize(width, height)
        widget.ensurePolished()
        layout = widget.layout()
        if layout is not None:
            layout.activate()
        pixmap = QPixmap(widget.size())
        pixmap.fill(Qt.black)
        widget.render(pixmap)
        return pixmap

    def _render_widget_image(self, widget: QWidget, width: int, height: int) -> QImage:
        widget.resize(max(1, int(width)), max(1, int(height)))
        widget.ensurePolished()
        layout = widget.layout()
        if layout is not None:
            layout.activate()
        image = QImage(widget.size(), QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.black)
        painter = QPainter(image)
        widget.render(painter)
        painter.end()
        return image

    def _video_snapshot_dimensions(self) -> tuple[int, int]:
        width, height = self._video_snapshot_target_pixel_size()
        if width > 0 and height > 0:
            return width, height
        return 960, 540

    def _stage_snapshot_renderer(self) -> GadgetStageDisplayWindow:
        window = getattr(self, "_video_stage_snapshot_window", None)
        if window is None:
            window = GadgetStageDisplayWindow(self)
            self._video_stage_snapshot_window = window
        return window

    def _lyric_snapshot_renderer(self) -> LyricDisplayWindow:
        window = getattr(self, "_video_lyric_snapshot_window", None)
        if window is None:
            window = LyricDisplayWindow(self)
            window.set_transparent_mode_enabled(False)
            self._video_lyric_snapshot_window = window
        return window

    def _render_stage_display_snapshot(self, target_width: Optional[int] = None, target_height: Optional[int] = None) -> QPixmap:
        if target_width is None or target_height is None:
            target_width, target_height = self._video_snapshot_dimensions()
        total_ms = max(0, self._transport_total_ms())
        display_pos = max(0, int(self.seek_slider.value()))
        progress = 0 if total_ms <= 0 else int((display_pos / float(total_ms)) * 100)
        progress_ratio = 0.0 if total_ms <= 0 else max(0.0, min(1.0, display_pos / float(total_ms)))
        cue_in_ms, cue_out_ms = self._current_transport_cue_bounds()
        song_name = "-"
        if self.current_playing is not None:
            slot = self._slot_for_key(self.current_playing)
            if slot is not None:
                song_name = self._build_stage_slot_text(slot) or "-"
        current_automation_comment = ""
        next_automation_comment = ""
        if self.current_playing is not None:
            player = self._player_for_slot_key(self.current_playing)
            current_automation_comment, next_automation_comment = self._automation_script_comments_for_slot_key(
                self.current_playing,
                player,
            )
        total_text = self.total_time.text().strip() or "00:00:00"
        elapsed_text = self.elapsed_time.text().strip() or "00:00:00"
        remaining_text = self.remaining_time.text().strip() or "00:00:00"
        lyric_text = self._stage_display_current_lyric()
        next_song = self._next_stage_song_name()
        progress_text = self.progress_label.text().strip()
        progress_style = self._build_progress_bar_stylesheet(progress_ratio, cue_in_ms, cue_out_ms)
        alert_active = self._stage_alert_active()
        alert_text = self._stage_alert_message if alert_active else ""
        playback_status = self._stage_playback_status()
        cache_key = _freeze_snapshot_token(
            (
                int(target_width),
                int(target_height),
                self.stage_display_gadgets,
                self.stage_display_font_family,
                self.stage_display_font_size,
                self.stage_display_lyric_font_family,
                self.stage_display_lyric_font_size,
                self.stage_display_lyric_role_colors,
                self.stage_display_lyric_role_sizes,
                self.stage_display_lyric_auto_adjust_role_sizes,
                self.stage_display_lyric_role_scale_percents,
                self.stage_display_lyric_role_bold,
                self.stage_display_lyric_role_italic,
                total_text,
                elapsed_text,
                remaining_text,
                int(progress),
                song_name,
                lyric_text,
                current_automation_comment,
                next_automation_comment,
                next_song,
                progress_text,
                progress_style,
                alert_text,
                playback_status,
            )
        )
        if cache_key == getattr(self, "_stage_snapshot_cache_key", None):
            cached = getattr(self, "_stage_snapshot_cache_pixmap", QPixmap())
            if not cached.isNull():
                return QPixmap(cached)
        window = self._stage_snapshot_renderer()
        window.configure_gadgets(self.stage_display_gadgets)
        window.configure_font_settings(
            default_font_family=self.stage_display_font_family,
            default_font_size=self.stage_display_font_size,
            lyric_font_family=self.stage_display_lyric_font_family,
            lyric_font_size=self.stage_display_lyric_font_size,
            lyric_role_colors=self.stage_display_lyric_role_colors,
            lyric_role_sizes=self.stage_display_lyric_role_sizes,
            lyric_auto_adjust_role_sizes=self.stage_display_lyric_auto_adjust_role_sizes,
            lyric_role_scale_percents=self.stage_display_lyric_role_scale_percents,
            lyric_role_bold=self.stage_display_lyric_role_bold,
            lyric_role_italic=self.stage_display_lyric_role_italic,
        )
        window.update_values(
            total_time=total_text,
            elapsed=elapsed_text,
            remaining=remaining_text,
            progress_percent=progress,
            song_name=song_name,
            lyric=lyric_text,
            automation_comment_current=current_automation_comment,
            automation_comment_next=next_automation_comment,
            next_song=next_song,
            progress_text=progress_text,
            progress_style=progress_style,
        )
        window.set_alert(self._stage_alert_message, alert_active)
        window.set_playback_status(playback_status)
        pixmap = self._render_widget_snapshot(window, target_width, target_height)
        self._stage_snapshot_cache_key = cache_key
        self._stage_snapshot_cache_pixmap = QPixmap(pixmap)
        return pixmap

    def _render_lyric_display_snapshot(self, target_width: Optional[int] = None, target_height: Optional[int] = None) -> QPixmap:
        if target_width is None or target_height is None:
            target_width, target_height = self._video_snapshot_dimensions()
        has_active_track = False
        lyric_path = ""
        position_ms = 0
        if self.current_playing is not None:
            slot = self._slot_for_key(self.current_playing)
            if slot is not None:
                has_active_track = True
                lyric_path = str(slot.lyric_file or "").strip()
                position_ms = self._lyric_position_ms_for_key(self.current_playing)
        cache_key = _freeze_snapshot_token(
            (
                int(target_width),
                int(target_height),
                self.lyric_display_font_family,
                self.lyric_display_font_size,
                self.lyric_display_show_not_playing_message,
                self.lyric_display_previous_line_count,
                self.lyric_display_next_line_count,
                self.lyric_display_role_colors,
                self.lyric_display_role_sizes,
                self.lyric_display_auto_adjust_role_sizes,
                self.lyric_display_role_scale_percents,
                self.lyric_display_role_bold,
                self.lyric_display_role_italic,
                has_active_track,
                lyric_path,
                int(position_ms),
                bool(self._lyric_force_blank),
            )
        )
        if cache_key == getattr(self, "_lyric_snapshot_cache_key", None):
            cached = getattr(self, "_lyric_snapshot_cache_pixmap", QPixmap())
            if not cached.isNull():
                return QPixmap(cached)
        window = self._lyric_snapshot_renderer()
        window.configure_display_settings(
            font_family=self.lyric_display_font_family,
            font_size=self.lyric_display_font_size,
            show_not_playing_message=self.lyric_display_show_not_playing_message,
            previous_line_count=self.lyric_display_previous_line_count,
            next_line_count=self.lyric_display_next_line_count,
            role_colors=self.lyric_display_role_colors,
            role_sizes=self.lyric_display_role_sizes,
            auto_adjust_role_sizes=self.lyric_display_auto_adjust_role_sizes,
            role_scale_percents=self.lyric_display_role_scale_percents,
            role_bold=self.lyric_display_role_bold,
            role_italic=self.lyric_display_role_italic,
        )
        window.update_playback_state(
            has_active_track=has_active_track,
            lyric_path=lyric_path,
            position_ms=position_ms,
            force_blank=bool(self._lyric_force_blank),
            force=True,
        )
        pixmap = self._render_widget_snapshot(window, target_width, target_height)
        self._lyric_snapshot_cache_key = cache_key
        self._lyric_snapshot_cache_pixmap = QPixmap(pixmap)
        return pixmap

    def _video_display_lyric_role_styles(self) -> dict[str, dict[str, object]]:
        if self.video_display_lyric_auto_adjust_role_sizes:
            sizes = {
                key: max(
                    8,
                    int(round(self.video_display_lyric_font_size * (self.video_display_lyric_role_scale_percents.get(key, 100) / 100.0))),
                )
                for key in ("played", "current", "next")
            }
        else:
            sizes = dict(self.video_display_lyric_role_sizes)
        return {
            "played": {
                "color": self.video_display_lyric_role_colors.get("played", "#A0A0A0"),
                "font_size_px": sizes.get("played", 24),
                "bold": bool(self.video_display_lyric_role_bold.get("played", True)),
                "italic": bool(self.video_display_lyric_role_italic.get("played", False)),
            },
            "current": {
                "color": self.video_display_lyric_role_colors.get("current", "#FFD400"),
                "font_size_px": sizes.get("current", 40),
                "bold": bool(self.video_display_lyric_role_bold.get("current", True)),
                "italic": bool(self.video_display_lyric_role_italic.get("current", False)),
            },
            "next": {
                "color": self.video_display_lyric_role_colors.get("next", "#FFFFFF"),
                "font_size_px": sizes.get("next", 32),
                "bold": bool(self.video_display_lyric_role_bold.get("next", True)),
                "italic": bool(self.video_display_lyric_role_italic.get("next", False)),
            },
        }

    def _current_video_lyric_html(self) -> str:
        if self.current_playing is None:
            return ""
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return ""
        lyric_path = str(slot.lyric_file or "").strip()
        if not lyric_path:
            return ""
        lines, error = self._load_stage_lyric_lines(lyric_path)
        if error or not lines:
            return ""
        position_ms = self._lyric_position_ms_for_key(self.current_playing)
        segments = lyric_segments_around_position(
            lines,
            position_ms,
            self.video_display_lyric_previous_line_count,
            self.video_display_lyric_next_line_count,
        )
        if not segments:
            return ""
        return lyric_segments_to_html(
            segments,
            font_family=self.video_display_lyric_font_family,
            role_styles=self._video_display_lyric_role_styles(),
        )

    def _slot_display_image_path(self, slot: Optional[SoundButtonData]) -> str:
        if slot is None:
            return ""
        return str(getattr(slot, "display_image_path", "") or "").strip()

    def _slot_display_image_pixmap(self, slot: Optional[SoundButtonData]) -> QPixmap:
        path = self._slot_display_image_path(slot)
        if not path:
            return QPixmap()
        cache_key = os.path.normcase(os.path.normpath(path))
        if cache_key == str(getattr(self, "_display_image_cache_path", "") or ""):
            return QPixmap(getattr(self, "_display_image_cache_pixmap", QPixmap()))
        pixmap = QPixmap(path)
        self._display_image_cache_path = cache_key
        self._display_image_cache_pixmap = QPixmap(pixmap)
        return pixmap

    def _render_metronome_display_snapshot(self, slot: Optional[SoundButtonData], width: int, height: int) -> QPixmap:
        pixmap = QPixmap(max(1, int(width)), max(1, int(height)))
        pixmap.fill(QColor("#12151B"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        title = str(getattr(slot, "title", "") or "").strip() or "Metronome"
        tempo_bpm = 120.0
        numerator = 4
        denominator = 4
        beat_index = 0
        beat_progress = 0.0
        has_metronome_data = False
        empty_state_title = ""
        empty_state_detail = ""
        if slot is not None and slot.utility_spec is not None:
            try:
                tempo_bpm = max(1.0, float(getattr(slot.utility_spec, "tempo_bpm", 120.0) or 120.0))
            except Exception:
                tempo_bpm = 120.0
            try:
                numerator = max(1, int(getattr(slot.utility_spec, "time_signature_num", 4) or 4))
            except Exception:
                numerator = 4
            try:
                denominator = int(getattr(slot.utility_spec, "time_signature_den", 4) or 4)
            except Exception:
                denominator = 4
            position_ms = max(0, int(self._current_video_display_position_ms()))
            beat_ms = max(1.0, 60000.0 / tempo_bpm)
            beat_index = int(position_ms / beat_ms) % max(1, numerator)
            beat_progress = max(0.0, min(1.0, (position_ms % beat_ms) / beat_ms))
            has_metronome_data = True
        else:
            beat_map = normalize_audio_beat_map(getattr(slot, "audio_beat_map", None))
            if beat_map is not None:
                tempo_bpm = max(1.0, float(beat_map.bpm or 120.0))
                numerator = max(1, int(beat_map.time_signature_num or 4))
                denominator = max(1, int(beat_map.time_signature_den or 4))
                position_ms = max(0, int(self._current_video_display_position_ms()))
                _beat_cursor, beat_number, denominator, beat_progress = beat_phase_at_position(beat_map, position_ms)
                beat_index = max(0, beat_number - 1)
                has_metronome_data = True
            else:
                empty_state_title = "No metronome data" if slot is not None else "No sound button selected"
                empty_state_detail = (
                    "Analyze BPM or enable metronome timing for this song."
                    if slot is not None
                    else "Start a metronome utility or select a song with timing data."
                )
        accent = QColor("#F2C94C")
        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSize(max(16, min(34, pixmap.height() // 14)))
        painter.setFont(title_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRect(0, 24, pixmap.width(), 56), Qt.AlignHCenter | Qt.AlignTop, title)
        if not has_metronome_data:
            message_font = QFont(self.font())
            message_font.setBold(True)
            message_font.setPointSize(max(18, min(40, pixmap.height() // 10)))
            painter.setFont(message_font)
            painter.setPen(accent)
            painter.drawText(
                QRect(24, max(64, pixmap.height() // 4), max(120, pixmap.width() - 48), max(60, pixmap.height() // 5)),
                Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextWordWrap,
                empty_state_title,
            )
            detail_font = QFont(self.font())
            detail_font.setPointSize(max(11, min(20, pixmap.height() // 18)))
            painter.setFont(detail_font)
            painter.setPen(QColor("#D7DCE5"))
            painter.drawText(
                QRect(36, max(120, pixmap.height() // 2 - 10), max(120, pixmap.width() - 72), max(56, pixmap.height() // 5)),
                Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                empty_state_detail,
            )
            painter.end()
            return pixmap
        bpm_font = QFont(self.font())
        bpm_font.setBold(True)
        bpm_font.setPointSize(max(24, min(72, pixmap.height() // 6)))
        painter.setFont(bpm_font)
        painter.setPen(accent)
        painter.drawText(
            QRect(0, max(48, pixmap.height() // 5), pixmap.width(), max(80, pixmap.height() // 4)),
            Qt.AlignHCenter | Qt.AlignVCenter,
            f"{int(round(tempo_bpm))} BPM",
        )
        sub_font = QFont(self.font())
        sub_font.setPointSize(max(12, min(24, pixmap.height() // 18)))
        painter.setFont(sub_font)
        painter.setPen(QColor("#D7DCE5"))
        painter.drawText(
            QRect(0, max(110, pixmap.height() // 2 - 10), pixmap.width(), 36),
            Qt.AlignHCenter | Qt.AlignVCenter,
            f"{numerator}/{denominator}",
        )
        beat_area = QRect(
            40,
            max(140, int(pixmap.height() * 0.62)),
            max(120, pixmap.width() - 80),
            max(60, int(pixmap.height() * 0.18)),
        )
        spacing = max(12, beat_area.width() // max(2, numerator * 2))
        radius = max(12, min(40, (beat_area.width() - ((numerator - 1) * spacing)) // max(2, numerator * 2)))
        total_width = (radius * 2 * numerator) + (spacing * max(0, numerator - 1))
        start_x = beat_area.x() + max(0, (beat_area.width() - total_width) // 2)
        center_y = beat_area.y() + (beat_area.height() // 2)
        for idx in range(numerator):
            rect = QRect(start_x + idx * ((radius * 2) + spacing), center_y - radius, radius * 2, radius * 2)
            fill = QColor("#2D3748")
            border = QColor("#667085")
            if idx == 0:
                fill = QColor("#4E5D78")
            if idx == beat_index:
                fill = QColor("#F2C94C")
                border = QColor("#FFF4C2")
            painter.setPen(QPen(border, 2))
            painter.setBrush(fill)
            painter.drawEllipse(rect)
            if idx == beat_index:
                inner = rect.adjusted(radius // 2, radius // 2, -(radius // 2), -(radius // 2))
                pulse = max(0, int((1.0 - beat_progress) * (radius // 3)))
                painter.setBrush(QColor(255, 255, 255, 180))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(inner.adjusted(-pulse, -pulse, pulse, pulse))
        painter.end()
        return pixmap

    def _sync_output_surface_widget(self, widget: Optional[VideoDisplayWidget], mode: str, *, force: bool = False) -> None:
        if widget is None:
            return
        widget.configure_overlay(
            overlay_rect=self.video_display_lyric_overlay_rect,
            show_lyric_overlay=self.video_display_show_lyric_overlay and mode == "video",
            show_stage_alert=self.video_display_show_stage_alert and mode == "video",
        )
        widget.set_mode(mode)
        widget.set_alert_text(self._stage_alert_message if self._stage_alert_active() else "")
        widget.set_backdrop_pixmap(self._video_backdrop_pixmap() if mode == "backdrop" else QPixmap())
        backdrop_message = self._video_backdrop_message_text() if mode == "backdrop" else ""
        widget.configure_backdrop(show_message=bool(backdrop_message), message_text=backdrop_message)
        active_slot = self._slot_for_key(self.current_playing) if self.current_playing is not None else None
        if mode == DISPLAY_FOCUS_VIDEO:
            runtime_image = self._runtime_video_destination_frame("local_program")
            if not runtime_image.isNull():
                widget.set_video_pixmap(QPixmap.fromImage(runtime_image))
            else:
                widget.set_video_pixmap(getattr(self, "_video_current_frame_pixmap", QPixmap()))
            widget.set_content_pixmap(QPixmap())
            widget.set_lyric_html(self._current_video_lyric_html())
            return
        if mode == DISPLAY_FOCUS_STAGE:
            widget.set_content_pixmap(self._render_stage_display_snapshot())
        elif mode == DISPLAY_FOCUS_LYRIC:
            widget.set_content_pixmap(self._render_lyric_display_snapshot())
        elif mode == DISPLAY_FOCUS_IMAGE:
            widget.set_content_pixmap(self._slot_display_image_pixmap(active_slot))
        elif mode == DISPLAY_FOCUS_METRONOME:
            widget.set_content_pixmap(
                self._render_metronome_display_snapshot(active_slot, max(1, widget.width()), max(1, widget.height()))
            )
        else:
            widget.set_content_pixmap(QPixmap())
        widget.set_video_pixmap(QPixmap())
        widget.set_lyric_html("")

    def _sync_video_surface_widget(self, widget: Optional[VideoDisplayWidget], *, force: bool = False) -> None:
        self._sync_output_surface_widget(widget, self._active_video_route_mode(), force=force)

    def _sync_metronome_surface_widget(self, widget: Optional[VideoDisplayWidget], *, force: bool = False) -> None:
        self._sync_output_surface_widget(widget, DISPLAY_FOCUS_METRONOME, force=force)

    def _ndi_output_dimensions(self) -> tuple[int, int]:
        mode = str(getattr(self, "ndi_output_resolution_mode", "source") or "source").strip().lower()
        if mode == "720p":
            return 1280, 720
        if mode == "1080p":
            return 1920, 1080
        if mode == "custom":
            return max(2, int(getattr(self, "ndi_output_width", 1920))), max(2, int(getattr(self, "ndi_output_height", 1080)))
        slot, info = self._current_video_slot_and_probe()
        if slot is not None and info.has_video:
            return self._video_output_dimensions(info)
        return max(2, int(getattr(self, "ndi_output_width", 1920))), max(2, int(getattr(self, "ndi_output_height", 1080)))

    def _sync_ndi_timer_intervals(self) -> None:
        try:
            for player in list(self._ndi_audio_players() or []):
                getter = getattr(player, "sampleRate", None)
                if not callable(getter):
                    continue
                rate = max(1, int(getter()))
                if rate > 0:
                    self._ndi_audio_last_sample_rate = rate
                    break
        except Exception:
            self._ndi_audio_last_sample_rate = int(getattr(self, "_ndi_audio_last_sample_rate", 48000) or 48000)

    def _runtime_video_destination_snapshot(self, destination_id: str) -> Optional[object]:
        service = getattr(self, "_audio_service", None)
        getter = getattr(service, "video_destination_snapshots", None)
        if not callable(getter):
            return None
        try:
            for snapshot in getter():
                if str(getattr(snapshot, "destination_id", "") or "") == str(destination_id):
                    return snapshot
        except Exception:
            return None
        return None

    def _runtime_video_destination_frame(self, destination_id: str) -> QImage:
        service = getattr(self, "_audio_service", None)
        getter = getattr(service, "video_destination_frame", None)
        if not callable(getter):
            return QImage()
        try:
            image = getter(str(destination_id))
        except Exception:
            return QImage()
        return image if isinstance(image, QImage) else QImage()

    def _configure_local_video_destination(self) -> None:
        service = getattr(self, "_audio_service", None)
        configure = getattr(service, "configure_video_destination", None)
        if not callable(configure):
            return
        slot, info = self._current_video_slot_and_probe()
        target_width, target_height = self._video_target_surface_pixel_size()
        source_width, source_height = self._video_output_dimensions(info)
        width = max(2, int(target_width or source_width or 640))
        height = max(2, int(target_height or source_height or 360))
        fps = 30.0
        try:
            fps = max(1.0, float(getattr(info, "fps", 0.0) or 0.0))
        except Exception:
            fps = 30.0
        if fps <= 0.0:
            fps = 30.0
        source_name = "local-program"
        if slot is not None:
            source_name = str(slot.file_path or "").strip() or source_name
        try:
            configure(
                "local_program",
                enabled=bool(self._video_display_target_visible()),
                route_mode=self._active_video_route_mode(),
                width=width,
                height=height,
                fps=fps,
                source_name=source_name,
                audio_enabled=False,
                audio_tap_mode="post_fader",
                groups="Public",
                discovery_servers="",
                allowed_adapters=(),
                multicast_enabled=False,
                multicast_ttl=1,
                multicast_netmask="255.255.0.0",
                multicast_netprefix="239.255.0.0",
                ndi_status=None,
            )
        except Exception:
            pass

    def _ensure_ndi_preview_widget(self) -> VideoDisplayWidget:
        widget = getattr(self, "ndi_preview_widget", None)
        if widget is None:
            widget = VideoDisplayWidget(self, allow_fullscreen_toggle=False)
            widget.hide()
            self.ndi_preview_widget = widget
        return widget

    def _current_ndi_video_frame_image(self) -> QImage:
        image = QImage(getattr(self, "_video_current_frame_image", QImage()))
        if not image.isNull():
            return image
        pixmap = QPixmap(getattr(self, "_video_current_frame_pixmap", QPixmap()))
        if pixmap.isNull():
            return QImage()
        return pixmap.toImage()

    def _render_ndi_frame_image(self) -> QImage:
        width, height = self._ndi_output_dimensions()
        mode = self._active_ndi_route_mode()
        if (
            mode == "video"
            and (not bool(getattr(self, "video_display_show_lyric_overlay", False)))
            and (not (bool(getattr(self, "video_display_show_stage_alert", False)) and self._stage_alert_active()))
        ):
            image = self._current_ndi_video_frame_image()
            if not image.isNull():
                return image.scaled(
                    max(1, int(width)),
                    max(1, int(height)),
                    Qt.IgnoreAspectRatio,
                    Qt.FastTransformation,
                )
        widget = self._ensure_ndi_preview_widget()
        self._sync_output_surface_widget(widget, mode, force=True)
        return self._render_widget_image(widget, width, height)

    def _ndi_audio_players(self) -> List[ExternalMediaPlayer]:
        players: List[ExternalMediaPlayer] = []
        seen: set[int] = set()
        current_key = getattr(self, "current_playing", None)
        if current_key is not None:
            primary = self._player_for_slot_key(current_key)
            for player in [primary, self._shadow_player_for(primary)]:
                if player is None or id(player) in seen:
                    continue
                try:
                    if player.state() != ExternalMediaPlayer.PlayingState:
                        continue
                except Exception:
                    continue
                seen.add(id(player))
                players.append(player)
        primaries = [self.player, self.player_b, *self._multi_players]
        for player in primaries:
            if player is None or id(player) in seen:
                continue
            try:
                if player.state() == ExternalMediaPlayer.PlayingState:
                    players.append(player)
                    seen.add(id(player))
            except Exception:
                pass
            shadow = self._shadow_player_for(player)
            if shadow is None or id(shadow) in seen:
                continue
            try:
                if shadow.state() == ExternalMediaPlayer.PlayingState:
                    players.append(shadow)
                    seen.add(id(shadow))
            except Exception:
                pass
        return players

    def _ndi_sender_has_receivers(self) -> bool:
        snapshot = self._runtime_video_destination_snapshot("ndi_program")
        if snapshot is not None:
            return bool(getattr(snapshot, "connection_count", 0) or 0)
        sender = getattr(self, "_ndi_sender", None)
        if sender is None:
            return False
        return bool(getattr(sender, "get_num_connections", lambda _timeout=0.0: 0)(0.0) > 0)

    def _ndi_audio_output_block_frames(self) -> int:
        players = []
        try:
            players = list(self._ndi_audio_players() or [])
        except Exception:
            players = []
        for player in players:
            getter = getattr(player, "outputBlockSize", None)
            if not callable(getter):
                continue
            try:
                value = max(0, int(getter()))
            except Exception:
                continue
            if value > 0:
                return value
        return 1024

    def _ndi_audio_target_frames(self, sample_rate: int) -> int:
        _ = sample_rate
        return max(240, int(self._ndi_audio_output_block_frames()))

    def _ndi_audio_send_silence_keepalive(
        self,
        sender: object,
        *,
        sample_rate: int,
        channel_count: int,
    ) -> bool:
        frames = max(1, int(self._ndi_audio_target_frames(sample_rate)))
        silence = np.zeros((frames, max(1, int(channel_count))), dtype=np.float32)
        send = getattr(sender, "send_audio_frames", None)
        if not callable(send):
            return False
        try:
            return bool(send(silence, int(sample_rate)))
        except Exception:
            return False

    def _configure_ndi_sender(self) -> bool:
        enabled = bool(getattr(self, "ndi_output_enabled", False))
        if (not enabled) or (not getattr(self, "_ndi_status", None) or not self._ndi_status.ready):
            self._ndi_last_config = None
            self._ndi_audio_last_sample_rate = 48000
            self._ndi_audio_last_channel_count = 2
            service = getattr(self, "_audio_service", None)
            clear_method = getattr(service, "clear_video_destination_frame", None)
            configure_method = getattr(service, "configure_video_destination", None)
            if callable(clear_method):
                try:
                    clear_method("ndi_program")
                except Exception:
                    pass
            if callable(configure_method):
                try:
                    configure_method(
                        "ndi_program",
                        enabled=False,
                        route_mode="blank",
                        width=max(2, int(getattr(self, "ndi_output_width", 1920) or 1920)),
                        height=max(2, int(getattr(self, "ndi_output_height", 1080) or 1080)),
                        fps=max(1.0, float(getattr(self, "ndi_output_fps", 30) or 30)),
                        source_name=str(getattr(self, "ndi_output_name", "pyssp-video") or "pyssp-video"),
                        audio_enabled=bool(getattr(self, "ndi_output_audio_enabled", True)),
                        audio_tap_mode=str(getattr(self, "ndi_output_audio_tap_mode", "post_fader") or "post_fader"),
                        groups=str(getattr(self, "ndi_output_group", "Public") or "Public"),
                        discovery_servers=str(getattr(self, "ndi_output_discovery_servers", "") or ""),
                        allowed_adapters=self._ndi_allowed_adapter_tokens(),
                        multicast_enabled=bool(getattr(self, "ndi_output_multicast_enabled", False)),
                        multicast_ttl=max(1, int(getattr(self, "ndi_output_multicast_ttl", 1) or 1)),
                        multicast_netmask=str(getattr(self, "ndi_output_multicast_netmask", "255.255.0.0") or "255.255.0.0"),
                        multicast_netprefix=str(getattr(self, "ndi_output_multicast_netprefix", "239.255.0.0") or "239.255.0.0"),
                        ndi_status=getattr(self, "_ndi_status", None),
                    )
                except Exception:
                    pass
            return False
        width, height = self._ndi_output_dimensions()
        config = NDIOutputConfig(
            source_name=str(getattr(self, "ndi_output_name", "pyssp-video") or "pyssp-video").strip() or "pyssp-video",
            width=width,
            height=height,
            fps=max(1.0, float(getattr(self, "ndi_output_fps", 30) or 30)),
            audio_enabled=bool(getattr(self, "ndi_output_audio_enabled", True)),
            groups=str(getattr(self, "ndi_output_group", "Public") or "Public").strip() or "Public",
            discovery_servers=str(getattr(self, "ndi_output_discovery_servers", "") or "").strip(),
            allowed_adapters=self._ndi_allowed_adapter_tokens(),
            multicast_enabled=bool(getattr(self, "ndi_output_multicast_enabled", False)),
            multicast_ttl=max(1, int(getattr(self, "ndi_output_multicast_ttl", 1) or 1)),
            multicast_netmask=str(getattr(self, "ndi_output_multicast_netmask", "255.255.0.0") or "255.255.0.0").strip() or "255.255.0.0",
            multicast_netprefix=str(getattr(self, "ndi_output_multicast_netprefix", "239.255.0.0") or "239.255.0.0").strip() or "239.255.0.0",
        )
        self._ndi_last_config = config
        service = getattr(self, "_audio_service", None)
        configure_method = getattr(service, "configure_video_destination", None)
        if callable(configure_method):
            try:
                configure_method(
                    "ndi_program",
                    enabled=True,
                    route_mode=self._active_ndi_route_mode(),
                    width=config.width,
                    height=config.height,
                    fps=config.fps,
                    source_name=config.source_name,
                    audio_enabled=config.audio_enabled,
                    audio_tap_mode=str(getattr(self, "ndi_output_audio_tap_mode", "post_fader") or "post_fader"),
                    groups=config.groups,
                    discovery_servers=config.discovery_servers,
                    allowed_adapters=config.allowed_adapters,
                    multicast_enabled=config.multicast_enabled,
                    multicast_ttl=config.multicast_ttl,
                    multicast_netmask=config.multicast_netmask,
                    multicast_netprefix=config.multicast_netprefix,
                    ndi_status=getattr(self, "_ndi_status", None),
                )
                return True
            except Exception:
                self._ndi_last_config = None
                return False
        sender = getattr(self, "_ndi_sender", None)
        if sender is not None and sender.configure(config):
            return True
        self._ndi_last_config = None
        return False

    def _ndi_allowed_adapter_tokens(self) -> tuple[str, ...]:
        text = str(getattr(self, "ndi_output_allowed_adapters", "") or "").replace(";", ",")
        tokens: list[str] = []
        seen: set[str] = set()
        for raw in text.split(","):
            token = str(raw or "").strip()
            if not token:
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            tokens.append(token)
        return tuple(tokens)

    def _send_ndi_audio(self) -> None:
        if not bool(getattr(self, "ndi_output_audio_enabled", True)):
            return
        service = getattr(self, "_audio_service", None)
        if callable(getattr(service, "configure_video_destination", None)):
            self._configure_ndi_sender()
            return
        sender = getattr(self, "_ndi_sender", None)
        config = getattr(self, "_ndi_last_config", None)
        if sender is None or config is None:
            return
        players = self._ndi_audio_players()
        sample_rate = int(getattr(self, "_ndi_audio_last_sample_rate", 48000) or 48000)
        active_player_ids: List[str] = []
        for player in players:
            player_token = str(getattr(player, "player_id", "") or "").strip()
            if not player_token:
                continue
            sample_rate_getter = getattr(player, "sampleRate", None)
            if not callable(sample_rate_getter):
                continue
            try:
                player_rate = max(1, int(sample_rate_getter()))
            except Exception:
                continue
            sample_rate = player_rate
            active_player_ids.append(player_token)
        if sample_rate <= 0:
            sample_rate = 48000
        self._ndi_audio_last_sample_rate = int(sample_rate)
        self._sync_ndi_timer_intervals()
        mode = str(getattr(self, "ndi_output_audio_tap_mode", "post_fader") or "post_fader")
        channel_count = max(1, int(getattr(self, "_ndi_audio_last_channel_count", 2) or 2))
        ordered_player_ids = list(dict.fromkeys([*active_player_ids, *list_output_monitor_players(mode)]))
        if ordered_player_ids:
            max_available = 0
            for player_id in ordered_player_ids:
                counts = output_monitor_frame_counts(player_id)
                max_available = max(max_available, max(0, int(counts.get(mode, 0) or 0)))
            target_frames = min(max_available, int(self._ndi_audio_target_frames(sample_rate)))
            burst_limit = 4
            burst_count = 0
            while burst_count < burst_limit and target_frames > 0:
                mixed = mix_output_monitor_chunk(
                    ordered_player_ids,
                    target_frames=target_frames,
                    mode=mode,
                )
                if mixed is None:
                    break
                chunk, consume_map = mixed
                if chunk.ndim != 2 or len(chunk) <= 0 or chunk.shape[1] <= 0:
                    break
                channel_count = int(chunk.shape[1])
                self._ndi_audio_last_channel_count = int(channel_count)
                if not sender.send_audio_frames(chunk, sample_rate):
                    break
                consume_output_monitor_chunk(consume_map, mode=mode)
                burst_count += 1
        else:
            self._ndi_audio_send_silence_keepalive(
                sender,
                sample_rate=sample_rate,
                channel_count=channel_count,
            )

    def _refresh_ndi_output(self, force: bool = False) -> None:
        if not self._configure_ndi_sender():
            return
        mode = self._active_ndi_route_mode()
        live_video_frame = self._current_ndi_video_frame_image() if mode == "video" else QImage()
        if mode == "video" and live_video_frame.isNull():
            queue_refresh = getattr(self, "_queue_video_frame_refresh", None)
            if callable(queue_refresh):
                try:
                    queue_refresh(force=bool(force))
                except Exception:
                    pass
            cached = QImage(getattr(self, "_ndi_last_video_frame_image", QImage()))
            if not cached.isNull():
                service = getattr(self, "_audio_service", None)
                submit = getattr(service, "submit_video_destination_frame", None)
                if callable(submit):
                    try:
                        submit(
                            "ndi_program",
                            cached,
                            route_mode=mode,
                            pts_ms=max(0, int(getattr(self, "_video_last_frame_pts_ms", 0) or 0)),
                            source_path=str(getattr(self, "_video_requested_frame_path", "") or ""),
                        )
                    except Exception:
                        pass
                else:
                    sender = getattr(self, "_ndi_sender", None)
                    if sender is not None:
                        sender.send_video_frame(cached)
            return
        frame_image = self._render_ndi_frame_image()
        if not frame_image.isNull():
            service = getattr(self, "_audio_service", None)
            submit = getattr(service, "submit_video_destination_frame", None)
            if callable(submit):
                source_path = ""
                slot, _info = self._current_video_slot_and_probe()
                if slot is not None:
                    source_path = str(slot.file_path or "").strip()
                try:
                    submit(
                        "ndi_program",
                        frame_image,
                        route_mode=mode,
                        pts_ms=max(0, int(getattr(self, "_video_last_frame_pts_ms", 0) or 0)),
                        source_path=source_path,
                    )
                except Exception:
                    pass
            else:
                sender = getattr(self, "_ndi_sender", None)
                if sender is not None:
                    sender.send_video_frame(frame_image)
            if mode == "video":
                self._ndi_last_video_frame_image = frame_image.copy()

    def _tick_ndi_refresh(self) -> None:
        self._refresh_ndi_output()

    def _tick_ndi_audio_refresh(self) -> None:
        if not self._configure_ndi_sender():
            return
        self._send_ndi_audio()

    def _apply_video_frame_to_targets(self) -> None:
        pixmap = getattr(self, "_video_current_frame_pixmap", QPixmap())
        preview = getattr(self, "video_preview_widget", None)
        if preview is not None and preview.isVisible() and preview._mode == "video":
            preview.set_video_pixmap(pixmap)
        if self._video_display_window is not None and self._video_display_window.isVisible():
            display_widget = self._video_display_window.display_widget
            if display_widget._mode == "video":
                display_widget.set_video_pixmap(pixmap)

    def _clear_video_frame_runtime(self, preserve_current_frame: bool = False) -> None:
        self._video_requested_frame_key = None
        self._video_requested_frame_path = ""
        self._video_decode_inflight_key = None
        self._video_stream_path_key = ""
        self._video_stream_interval_ms = 0
        self._video_stream_dimensions = (0, 0)
        self._video_active_request_tag = 0
        self._video_active_stream_revision = -1
        self._video_last_frame_pts_ms = 0
        if not preserve_current_frame:
            self._video_current_frame_key = None
            self._video_current_frame_pixmap = QPixmap()
            self._video_current_frame_image = QImage()
            clear_method = getattr(getattr(self, "_audio_service", None), "clear_video_destination_frame", None)
            if callable(clear_method):
                try:
                    clear_method("local_program")
                except Exception:
                    pass
                try:
                    clear_method("ndi_program")
                except Exception:
                    pass
        dispatcher = getattr(self, "_video_frame_dispatcher", None)
        if dispatcher is not None:
            try:
                dispatcher.clear()
            except Exception:
                pass
        if (not self.preload_video_enabled) and (not preserve_current_frame):
            self._video_frame_cache.clear()

    def _video_decode_allowed_during_switch_blank(self) -> bool:
        if not bool(getattr(self, "_video_force_blank_until_frame", False)):
            return False
        slot, info = self._current_video_slot_and_probe()
        return slot is not None and bool(info.has_video)

    def _queue_video_frame_refresh(self, *, force: bool = False) -> None:
        if not self._video_display_target_visible():
            if force or self._video_stream_path_key or self._video_decode_inflight_key is not None:
                self._clear_video_frame_runtime()
            return
        slot, info = self._current_video_slot_and_probe()
        route_mode = self._active_video_route_mode()
        allow_decode_while_blank = self._video_decode_allowed_during_switch_blank()
        if slot is None or (not info.has_video) or (route_mode != "video" and not allow_decode_while_blank):
            if force:
                self._clear_video_frame_runtime()
            return
        path = str(slot.file_path or "").strip()
        if not path:
            if force:
                self._clear_video_frame_runtime()
            return
        position_ms = self._current_video_display_position_ms()
        bucket_ms = self._video_frame_bucket_ms(position_ms, info)
        cache_key = (self._normalized_media_probe_key(path), bucket_ms)
        self._video_requested_frame_key = cache_key
        self._video_requested_frame_path = path
        dispatcher = getattr(self, "_video_frame_dispatcher", None)
        if dispatcher is None:
            return
        status = self._stage_playback_status()
        width, height = self._video_decode_dimensions(info)
        interval_ms = self._video_frame_interval_ms(info)
        normalized_key = cache_key[0]
        if status == "playing":
            if (
                self._video_stream_path_key == normalized_key
                and self._video_stream_interval_ms == interval_ms
                and tuple(getattr(self, "_video_stream_dimensions", (0, 0))) == (width, height)
                and int(getattr(self, "_video_active_stream_revision", -1)) == int(getattr(self, "_video_transport_revision", 0))
                and isinstance(self._video_decode_inflight_key, tuple)
                and self._video_decode_inflight_key
                and self._video_decode_inflight_key[0] == "stream"
            ):
                return
            should_restart_stream = force
            if normalized_key != str(getattr(self, "_video_stream_path_key", "") or ""):
                should_restart_stream = True
            if int(getattr(self, "_video_stream_interval_ms", 0) or 0) != interval_ms:
                should_restart_stream = True
            if tuple(getattr(self, "_video_stream_dimensions", (0, 0))) != (width, height):
                should_restart_stream = True
            if int(getattr(self, "_video_active_stream_revision", -1)) != int(getattr(self, "_video_transport_revision", 0)):
                should_restart_stream = True
            if should_restart_stream:
                tag = self._next_video_request_tag()
                self._video_stream_path_key = normalized_key
                self._video_stream_interval_ms = interval_ms
                self._video_stream_dimensions = (width, height)
                self._video_active_request_tag = tag
                self._video_active_stream_revision = int(getattr(self, "_video_transport_revision", 0))
                self._video_last_frame_pts_ms = bucket_ms
                self._video_decode_inflight_key = ("stream", bucket_ms)
                dispatcher.request_stream(tag, path, bucket_ms, width, height, interval_ms)
            return
            cached = self._video_frame_cache.get(cache_key)
            if cached is not None:
                if force or self._video_current_frame_key != cache_key:
                    self._video_current_frame_key = cache_key
                    self._video_current_frame_pixmap = QPixmap(cached)
                    self._video_current_frame_image = QImage()
                    self._apply_video_frame_to_targets()
                return
        if self._video_decode_inflight_key == cache_key:
            return
        self._video_stream_path_key = ""
        self._video_stream_interval_ms = 0
        self._video_stream_dimensions = (0, 0)
        self._video_last_frame_pts_ms = bucket_ms
        self._video_decode_inflight_key = cache_key
        tag = self._next_video_request_tag()
        self._video_active_request_tag = tag
        dispatcher.request_frame(tag, path, bucket_ms, width, height)

    def _tick_video_refresh(self) -> None:
        if self._active_video_route_mode() != "video" and not self._video_decode_allowed_during_switch_blank():
            return
        self._queue_video_frame_refresh()

    def _on_video_frame_ready(self) -> None:
        if bool(getattr(self, "_shutdown_in_progress", False)):
            return
        dispatcher = getattr(self, "_video_frame_dispatcher", None)
        if dispatcher is None:
            return
        try:
            frame = dispatcher.take_latest_frame()
        except Exception:
            frame = None
        if not frame:
            return
        self._on_video_frame_decoded(*frame)

    def _on_video_frame_decoded(self, tag: int, path: str, bucket_ms: int, width: int, height: int, payload: bytes) -> None:
        candidate = str(path or "").strip()
        if not candidate or not payload:
            return
        if int(tag) != int(getattr(self, "_video_active_request_tag", 0) or 0):
            return
        cache_key = (self._normalized_media_probe_key(candidate), max(0, int(bucket_ms)))
        expected_blank_key = str(getattr(self, "_video_force_blank_expected_path", "") or "")
        if bool(getattr(self, "_video_force_blank_until_frame", False)) and expected_blank_key and cache_key[0] == expected_blank_key:
            self._clear_video_switch_blank()
        image = QImage(payload, max(1, int(width)), max(1, int(height)), max(1, int(width)) * 3, QImage.Format_RGB888)
        if image.isNull():
            return
        frame_image = image.copy()
        rotation = int(getattr(self._media_probe_for_path(candidate), "rotation_deg", 0) or 0)
        if rotation in {90, 180, 270}:
            transform = QTransform()
            transform.rotate(rotation)
            frame_image = frame_image.transformed(transform, Qt.SmoothTransformation)
        pixmap = QPixmap.fromImage(frame_image)
        if pixmap.isNull():
            return
        if self.preload_video_enabled:
            self._video_frame_cache[cache_key] = QPixmap(pixmap)
            if len(self._video_frame_cache) > 120:
                oldest_keys = list(self._video_frame_cache.keys())[:-120]
                for old_key in oldest_keys:
                    self._video_frame_cache.pop(old_key, None)
        else:
            self._video_frame_cache.clear()
        inflight_key = getattr(self, "_video_decode_inflight_key", None)
        if inflight_key == cache_key or (isinstance(inflight_key, tuple) and inflight_key and inflight_key[0] == "stream"):
            self._video_decode_inflight_key = None
        slot, info = self._current_video_slot_and_probe()
        if slot is None or (not info.has_video) or self._active_video_route_mode() != "video":
            return
        active_path = str(slot.file_path or "").strip()
        active_key = self._normalized_media_probe_key(active_path)
        if active_key != cache_key[0]:
            return
        self._video_current_frame_key = cache_key
        self._video_current_frame_image = QImage(frame_image)
        self._video_current_frame_pixmap = QPixmap(pixmap)
        self._video_last_frame_pts_ms = bucket_ms
        submit_method = getattr(getattr(self, "_audio_service", None), "submit_video_destination_frame", None)
        if callable(submit_method):
            try:
                submit_method(
                    "local_program",
                    frame_image,
                    route_mode="video",
                    pts_ms=max(0, int(bucket_ms)),
                    source_path=active_path,
                )
            except Exception:
                pass
        self._apply_video_frame_to_targets()
        self._refresh_ndi_output(force=False)
        complete_pending_start = getattr(self, "_complete_pending_video_synced_start", None)
        if callable(complete_pending_start):
            try:
                complete_pending_start(active_key)
            except Exception:
                pass
        desired_key = getattr(self, "_video_requested_frame_key", None)
        desired_path = str(getattr(self, "_video_requested_frame_path", "") or "").strip()
        if self._stage_playback_status() == "playing":
            return
        if desired_key is None or desired_key == cache_key:
            return
        if desired_key[0] != active_key or desired_path != active_path:
            return
        if self._video_frame_cache.get(desired_key) is not None:
            return
        dispatcher = getattr(self, "_video_frame_dispatcher", None)
        if dispatcher is None or self._video_decode_inflight_key is not None:
            return
        self._video_decode_inflight_key = desired_key
        width, height = self._video_decode_dimensions(info)
        tag = self._next_video_request_tag()
        self._video_active_request_tag = tag
        dispatcher.request_frame(tag, desired_path, desired_key[1], width, height)

    def _refresh_video_display(self, force: bool = False) -> None:
        self._configure_local_video_destination()
        if force and self._active_video_route_mode() != "video":
            self._clear_video_frame_runtime()
        preview = getattr(self, "video_preview_widget", None)
        if preview is not None and (preview.isVisible() or force):
            self._sync_video_surface_widget(preview, force=force)
        if self._video_display_window is not None and (self._video_display_window.isVisible() or force):
            self._video_display_window.configure_overlay(
                overlay_rect=self.video_display_lyric_overlay_rect,
                show_lyric_overlay=self.video_display_show_lyric_overlay and self._active_video_route_mode() == "video",
                show_stage_alert=self.video_display_show_stage_alert and self._active_video_route_mode() == "video",
            )
            self._sync_video_surface_widget(self._video_display_window.display_widget, force=force)
        metronome_window = getattr(self, "_metronome_display_window", None)
        if metronome_window is not None and (metronome_window.isVisible() or force):
            metronome_window.configure_overlay(
                overlay_rect=self.video_display_lyric_overlay_rect,
                show_lyric_overlay=False,
                show_stage_alert=False,
            )
            self._sync_metronome_surface_widget(metronome_window.display_widget, force=force)
        if self._active_video_route_mode() == "video":
            self._queue_video_frame_refresh(force=force)
        self._refresh_ndi_output(force=force)

    def _slot_or_media_has_audio(self, slot: Optional[SoundButtonData]) -> bool:
        if slot is None:
            return False
        if not self._slot_allows_video_loading(slot):
            return True
        path = str(slot.file_path or "").strip()
        if not path:
            return False
        if not self._path_may_have_video(path):
            return True
        return bool(self._media_probe_for_path(path).has_audio)

    def _silent_video_source_payload(self, slot: SoundButtonData) -> Optional[dict]:
        if not self._slot_allows_video_loading(slot):
            return None
        path = str(slot.file_path or "").strip()
        if not path:
            return None
        if not self._path_may_have_video(path):
            return None
        info = self._media_probe_for_path(path)
        if not info.has_video or info.has_audio:
            return None
        duration_ms = max(1, int(info.duration_ms or slot.duration_ms or 1))
        return utility_source_payload(
            mode="blank",
            duration_ms=duration_ms,
        )
