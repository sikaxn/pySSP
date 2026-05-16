from __future__ import annotations

import threading

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *
from pyssp.ffmpeg_support import FFMPEG_VIDEO_EXTENSIONS
from pyssp.utility_audio import utility_source_payload
from pyssp.ui.video_display import VideoDisplayWidget

_VIDEO_FILE_EXTENSIONS = {str(token or "").strip().lower() for token in FFMPEG_VIDEO_EXTENSIONS}
_VIDEO_FRAME_FALLBACK_INTERVAL_MS = 33
_VIDEO_BACKDROP_MESSAGE = "No video is playing"


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

        self.video_mode_playing_combo = QComboBox(panel)
        for label, value in [
            ("Video", "video"),
            ("Lyric Display", "lyric_display"),
            ("Stage Display", "stage_display"),
            ("Backdrop", "backdrop"),
            ("Blank", "blank"),
            ("White Screen", "white_screen"),
            ("Colour Bars", "colour_bars"),
        ]:
            self.video_mode_playing_combo.addItem(label, value)
        index = self.video_mode_playing_combo.findData(self.video_display_mode_playing)
        self.video_mode_playing_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("When video is playing:", self.video_mode_playing_combo)

        self.video_mode_idle_combo = QComboBox(panel)
        for label, value in [
            ("Lyric Display", "lyric_display"),
            ("Stage Display", "stage_display"),
            ("Backdrop", "backdrop"),
            ("Blank", "blank"),
            ("White Screen", "white_screen"),
            ("Colour Bars", "colour_bars"),
        ]:
            self.video_mode_idle_combo.addItem(label, value)
        index = self.video_mode_idle_combo.findData(self.video_display_mode_idle)
        self.video_mode_idle_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("When video is not playing:", self.video_mode_idle_combo)
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
        self.video_mode_playing_combo.currentIndexChanged.connect(self._on_video_display_route_changed)
        self.video_mode_idle_combo.currentIndexChanged.connect(self._on_video_display_route_changed)
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
        self.video_display_mode_playing = str(self.video_mode_playing_combo.currentData() or "video")
        self.video_display_mode_idle = str(self.video_mode_idle_combo.currentData() or "blank")
        self._refresh_video_display(force=True)
        if not self._suspend_settings_save:
            self._save_settings()

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

    def _active_video_route_mode(self) -> str:
        slot, info = self._current_video_slot_and_probe()
        if slot is None or not info.has_video:
            return str(self.video_display_mode_idle or "blank")
        status = self._stage_playback_status()
        if status == "not_playing":
            return str(self.video_display_mode_idle or "blank")
        return str(self.video_display_mode_playing or "video")

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
        mode = self._active_video_route_mode()
        if mode == "video":
            self._clear_video_frame_runtime(preserve_current_frame=True)
            self._refresh_video_display(force=True)
            return
        if mode in {"stage_display", "lyric_display"}:
            self._refresh_video_display(force=True)

    def _invalidate_video_playback_sync(self, *, refresh: bool = False) -> None:
        self._video_transport_revision = max(0, int(getattr(self, "_video_transport_revision", 0))) + 1
        self._clear_video_frame_runtime(preserve_current_frame=True)
        if refresh:
            self._refresh_video_display(force=True)

    def _video_frame_bucket_ms(self, position_ms: int, info: Optional[MediaProbeInfo] = None) -> int:
        interval_ms = self._video_frame_interval_ms(info)
        return max(0, int(round(max(0, int(position_ms)) / float(interval_ms)) * interval_ms))

    def _video_display_target_visible(self) -> bool:
        preview = getattr(self, "video_preview_widget", None)
        if preview is not None and preview.isVisible():
            return True
        return self._video_display_window is not None and self._video_display_window.isVisible()

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
        pixmap = QPixmap(widget.size())
        pixmap.fill(Qt.black)
        widget.render(pixmap)
        return pixmap

    def _video_snapshot_dimensions(self) -> tuple[int, int]:
        width, height = self._video_snapshot_target_pixel_size()
        if width > 0 and height > 0:
            return width, height
        return 960, 540

    def _render_stage_display_snapshot(self) -> QPixmap:
        target_width, target_height = self._video_snapshot_dimensions()
        window = GadgetStageDisplayWindow(self)
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
        window.update_values(
            total_time=self.total_time.text().strip() or "00:00:00",
            elapsed=self.elapsed_time.text().strip() or "00:00:00",
            remaining=self.remaining_time.text().strip() or "00:00:00",
            progress_percent=progress,
            song_name=song_name,
            lyric=self._stage_display_current_lyric(),
            automation_comment_current=current_automation_comment,
            automation_comment_next=next_automation_comment,
            next_song=self._next_stage_song_name(),
            progress_text=self.progress_label.text().strip(),
            progress_style=self._build_progress_bar_stylesheet(progress_ratio, cue_in_ms, cue_out_ms),
        )
        window.set_alert(self._stage_alert_message, self._stage_alert_active())
        window.set_playback_status(self._stage_playback_status())
        return self._render_widget_snapshot(window, target_width, target_height)

    def _render_lyric_display_snapshot(self) -> QPixmap:
        target_width, target_height = self._video_snapshot_dimensions()
        window = LyricDisplayWindow(self)
        window.set_transparent_mode_enabled(False)
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
        has_active_track = False
        lyric_path = ""
        position_ms = 0
        if self.current_playing is not None:
            slot = self._slot_for_key(self.current_playing)
            if slot is not None:
                has_active_track = True
                lyric_path = str(slot.lyric_file or "").strip()
                position_ms = self._lyric_position_ms_for_key(self.current_playing)
        window.update_playback_state(
            has_active_track=has_active_track,
            lyric_path=lyric_path,
            position_ms=position_ms,
            force_blank=bool(self._lyric_force_blank),
            force=True,
        )
        return self._render_widget_snapshot(window, target_width, target_height)

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

    def _sync_video_surface_widget(self, widget: Optional[VideoDisplayWidget], *, force: bool = False) -> None:
        if widget is None:
            return
        mode = self._active_video_route_mode()
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
        if mode == "video":
            widget.set_video_pixmap(getattr(self, "_video_current_frame_pixmap", QPixmap()))
            widget.set_content_pixmap(QPixmap())
            widget.set_lyric_html(self._current_video_lyric_html())
            return
        if mode == "stage_display":
            widget.set_content_pixmap(self._render_stage_display_snapshot())
        elif mode == "lyric_display":
            widget.set_content_pixmap(self._render_lyric_display_snapshot())
        else:
            widget.set_content_pixmap(QPixmap())
        widget.set_video_pixmap(QPixmap())
        widget.set_lyric_html("")

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
        dispatcher = getattr(self, "_video_frame_dispatcher", None)
        if dispatcher is not None:
            try:
                dispatcher.clear()
            except Exception:
                pass
        if (not self.preload_video_enabled) and (not preserve_current_frame):
            self._video_frame_cache.clear()

    def _queue_video_frame_refresh(self, *, force: bool = False) -> None:
        if not self._video_display_target_visible():
            if force or self._video_stream_path_key or self._video_decode_inflight_key is not None:
                self._clear_video_frame_runtime()
            return
        slot, info = self._current_video_slot_and_probe()
        if slot is None or (not info.has_video) or self._active_video_route_mode() != "video":
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
        if self._active_video_route_mode() != "video":
            return
        self._queue_video_frame_refresh()

    def _on_video_frame_ready(self) -> None:
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
        self._video_current_frame_pixmap = QPixmap(pixmap)
        self._video_last_frame_pts_ms = bucket_ms
        self._apply_video_frame_to_targets()
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
        if self._active_video_route_mode() == "video":
            self._queue_video_frame_refresh(force=force)

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
