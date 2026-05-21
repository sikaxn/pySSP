from __future__ import annotations

import numpy as np
import pytest
from pyssp.ffmpeg_support import MediaProbeInfo
from pyssp.audio_service import AudioPlayerProxy, AudioStateCache
from pyssp.automation_command import AUTOMATION_SOURCE_TYPE, AutomationCommandSpec
from pyssp.audio_beat_map import AudioBeatMap
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QPaintEvent, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel

from pyssp.ui import main_window as mw
from pyssp.ui.main_window import MainWindow, SLOTS_PER_PAGE, _equal_power_crossfade_volume
from pyssp.ui.main_window import video_display as video_display_module
from pyssp.ui.main_window.playback import PlaybackMixin
from pyssp.ui.main_window.video_display import VideoDisplayMixin
from pyssp.ui.video_display import VideoDisplayWidget
from pyssp.utility_audio import UTILITY_SOURCE_TYPE, UtilitySoundSpec


def test_main_window_import_surface_stays_compatible():
    assert MainWindow is mw.MainWindow
    assert SLOTS_PER_PAGE == mw.SLOTS_PER_PAGE
    assert _equal_power_crossfade_volume is mw._equal_power_crossfade_volume


def test_main_window_module_exposes_monkeypatch_targets():
    assert hasattr(mw, "QFileDialog")
    assert hasattr(mw, "QImage")
    assert hasattr(mw, "LtcAudioOutput")
    assert hasattr(mw, "MtcMidiOutput")
    assert hasattr(mw, "load_settings")
    assert hasattr(mw, "save_settings")
    assert hasattr(mw, "set_output_device")
    assert hasattr(mw, "configure_audio_preload_cache_policy")
    assert hasattr(mw, "configure_waveform_disk_cache")
    assert hasattr(mw, "shutdown_audio_preload")


class _AudioOnlyVideoRouteHost(VideoDisplayMixin):
    def __init__(self) -> None:
        self._media_probe_cache = {}
        self.current_playing = ("A", 0, 0)
        self.video_display_mode_idle = "blank"
        self.video_display_mode_playing = "follow_sound_button"
        self.video_display_show_backdrop_message = True
        self.video_display_use_default_backdrop = True
        self.video_display_backdrop_path = ""
        self._slot = mw.SoundButtonData(file_path="theme_song.mp3")

    def _slot_for_key(self, _key):
        return self._slot

    def _stage_playback_status(self) -> str:
        return "playing"

    def _asset_file_path(self, name: str) -> str:
        return name


class _VideoRefreshHost(VideoDisplayMixin):
    def __init__(self) -> None:
        class _NullPixmap:
            def isNull(self) -> bool:
                return True

        self._media_probe_cache = {}
        self.current_playing = ("A", 0, 0)
        self.video_display_mode_idle = "blank"
        self.video_display_mode_playing = "follow_sound_button"
        self._slot = mw.SoundButtonData(file_path="clip.mp4")
        self._probe = MediaProbeInfo(has_video=True, has_audio=True, fps=25.0, duration_ms=10000, width=640, height=360)
        self._video_frame_cache = {}
        self._video_requested_frame_key = None
        self._video_requested_frame_path = ""
        self._video_decode_inflight_key = None
        self._video_request_tag_serial = 0
        self._video_active_request_tag = 0
        self._video_transport_revision = 0
        self._video_active_stream_revision = -1
        self._video_stream_path_key = ""
        self._video_stream_interval_ms = 0
        self._video_stream_dimensions = (0, 0)
        self._video_last_frame_pts_ms = 0
        self._video_current_frame_key = None
        self._video_current_frame_pixmap = _NullPixmap()
        self._video_current_frame_image = mw.QImage()
        self._video_force_blank_until_frame = False
        self._video_force_blank_expected_path = ""
        self.preload_video_enabled = False
        self._video_display_window = None
        self.video_preview_widget = None
        self._position_ms = 80

        class _Dispatcher:
            def __init__(self):
                self.requests = []

            def request_frame(self, tag, path, bucket_ms, width, height):
                self.requests.append(("frame", tag, path, bucket_ms, width, height))

            def request_stream(self, tag, path, start_ms, width, height, interval_ms):
                self.requests.append(("stream", tag, path, start_ms, width, height, interval_ms))

            def clear(self):
                self.requests.append(("clear",))

        self._video_frame_dispatcher = _Dispatcher()
        self._target_size = (0, 0)

    def _slot_for_key(self, _key):
        return self._slot

    def _stage_playback_status(self) -> str:
        return "playing"

    def _media_probe_for_path(self, path: str) -> MediaProbeInfo:
        if str(path or "").strip().lower().endswith(".mp4"):
            return self._probe
        return MediaProbeInfo()

    def _video_display_target_visible(self) -> bool:
        return True

    def _current_video_display_position_ms(self) -> int:
        return int(self._position_ms)

    def _apply_video_frame_to_targets(self) -> None:
        return None

    def _video_target_surface_pixel_size(self) -> tuple[int, int]:
        return self._target_size

    def _video_snapshot_target_pixel_size(self) -> tuple[int, int]:
        if bool(getattr(self, "ndi_output_enabled", False)):
            ndi_mode = self._active_ndi_route_mode()
            if ndi_mode in {"stage_display", "lyric_display", "backdrop", "blank", "white_screen", "colour_bars"}:
                return self._ndi_output_dimensions()
        return self._target_size

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
            self._video_current_frame_pixmap = type(self._video_current_frame_pixmap)()
        self._video_frame_dispatcher.clear()


class _CheckedButton:
    def __init__(self, checked: bool) -> None:
        self._checked = bool(checked)

    def isChecked(self) -> bool:
        return self._checked


class _PlaybackSmartFadeHost(PlaybackMixin):
    def __init__(self, *, smart_in: bool = False, smart_out: bool = False, smart_cross: bool = False) -> None:
        self.control_buttons = {
            "Smart In": _CheckedButton(smart_in),
            "Smart Out": _CheckedButton(smart_out),
            "Smart X": _CheckedButton(smart_cross),
            "X": _CheckedButton(True),
        }
        self.fade_in_sec = 1.0
        self.fade_out_sec = 1.0
        self.cross_fade_sec = 1.0
        self.vocal_removed_toggle_fade_mode = "follow_cross_fade"
        self.vocal_removed_toggle_custom_sec = 1.0
        self.vocal_removed_toggle_always_sec = 1.0
        self.play_vocal_removed_tracks = False
        self._slot = mw.SoundButtonData(
            file_path="theme.mp3",
            duration_ms=4000,
            audio_beat_map=AudioBeatMap(
                bpm=120.0,
                time_signature_num=4,
                time_signature_den=4,
                first_downbeat_ms=0,
                beat_times_ms=[0, 500, 1000, 1500, 2000, 2500, 3000, 3500],
                beat_numbers=[1, 2, 3, 4, 1, 2, 3, 4],
                source="librosa",
                confidence=0.85,
                analysis_method="librosa",
                analysis_confidence=0.85,
            ),
        )
        self.player = type(
            "_Player",
            (),
            {
                "duration": lambda _self: 4000,
                "position": lambda _self: 1200,
                "enginePositionMs": lambda _self: 1200,
                "state": lambda _self: mw.ExternalMediaPlayer.PlayingState,
            },
        )()
        self._player_slot_key_map = {id(self.player): ("A", 0, 0)}

    def _slot_for_key(self, _key):
        return self._slot

    def _cue_start_for_playback(self, slot, duration_ms: int) -> int:
        _ = duration_ms
        return 0 if slot.cue_start_ms is None else int(slot.cue_start_ms)

    def _cue_end_for_playback(self, slot, duration_ms: int):
        if slot.cue_end_ms is None:
            return int(duration_ms)
        return int(slot.cue_end_ms)


def test_video_display_skips_media_probe_for_audio_only_paths(monkeypatch):
    def _unexpected_probe(_path: str):
        raise AssertionError("audio-only paths should not be probed for video metadata")

    monkeypatch.setattr("pyssp.ui.main_window.video_display.probe_media_info", _unexpected_probe)
    host = _AudioOnlyVideoRouteHost()

    info = host._media_probe_for_path("theme_song.wav")
    assert info.has_video is False
    assert info.has_audio is False
    assert host._slot_has_video_media(host._slot) is False
    assert host._silent_video_source_payload(host._slot) is None
    assert host._active_video_route_mode() == "blank"


def test_disable_video_loading_treats_video_file_as_audio_only(monkeypatch):
    def _unexpected_probe(_path: str):
        raise AssertionError("video metadata probe should be skipped when video loading is disabled")

    monkeypatch.setattr("pyssp.ui.main_window.video_display.probe_media_info", _unexpected_probe)
    host = _AudioOnlyVideoRouteHost()
    host._slot = mw.SoundButtonData(file_path="clip.mp4", disable_video_loading=True)

    assert host._slot_has_video_media(host._slot) is False
    assert host._slot_or_media_has_audio(host._slot) is True
    assert host._silent_video_source_payload(host._slot) is None
    assert host._active_video_route_mode() == "blank"


def test_backdrop_mode_uses_default_asset_and_message_for_idle_state():
    host = _AudioOnlyVideoRouteHost()
    host.video_display_mode_idle = "backdrop"

    assert host._active_video_route_mode() == "backdrop"
    assert host._active_ndi_route_mode() == "backdrop"
    assert host._resolved_video_backdrop_path() == "logo2.png"
    assert host._video_backdrop_message_text() == "No video is playing"


def test_metronome_utility_defaults_to_metronome_display_route():
    host = _AudioOnlyVideoRouteHost()
    host._slot = mw.SoundButtonData(
        source_type=UTILITY_SOURCE_TYPE,
        title="Count In",
        duration_ms=10000,
        utility_spec=UtilitySoundSpec(mode="metronome", tempo_bpm=120.0, time_signature_num=4, time_signature_den=4),
    )
    host.display_focus_default_utility_metronome = "metronome_display"

    assert host._active_video_route_mode() == "metronome_display"


def test_automation_button_uses_idle_video_route():
    host = _AudioOnlyVideoRouteHost()
    host.video_display_mode_idle = "backdrop"
    host.video_display_mode_playing = "stage_display"
    host._slot = mw.SoundButtonData(
        source_type=AUTOMATION_SOURCE_TYPE,
        title="Automation",
        automation_spec=AutomationCommandSpec(location="5/1/2", button_text="Take"),
    )

    assert host._active_video_route_mode() == "backdrop"
    assert host._active_ndi_route_mode() == "backdrop"


def test_video_route_override_can_replace_sound_button_focus():
    host = _AudioOnlyVideoRouteHost()
    host.video_display_mode_playing = "stage_display"
    host._slot = mw.SoundButtonData(file_path="theme_song.mp3")

    assert host._active_video_route_mode() == "stage_display"


def test_smart_fade_helpers_follow_beat_map_when_enabled():
    host = _PlaybackSmartFadeHost(smart_in=True, smart_out=True, smart_cross=True)

    fade_in = host._fade_in_seconds_for_slot(host._slot, duration_ms=4000, start_ms=0)
    fade_out = host._fade_out_seconds_for_slot(host._slot, duration_ms=4000, start_ms=1200, end_limit_ms=4000)
    cross = host._cross_fade_seconds_for_slots(
        host._slot,
        host._slot,
        outgoing_duration_ms=4000,
        incoming_duration_ms=4000,
        outgoing_start_ms=1200,
        incoming_start_ms=0,
        outgoing_end_limit_ms=4000,
    )

    assert fade_in == pytest.approx(0.5)
    assert fade_out == pytest.approx(0.3)
    assert cross == pytest.approx(0.8)


def test_smart_fade_helpers_fall_back_without_beat_analysis():
    host = _PlaybackSmartFadeHost(smart_in=True, smart_out=True, smart_cross=True)
    host._slot.audio_beat_map = None

    assert host._fade_in_seconds_for_slot(host._slot, duration_ms=4000, start_ms=0) == pytest.approx(1.0)
    assert host._fade_out_seconds_for_slot(host._slot, duration_ms=4000, start_ms=1200, end_limit_ms=4000) == pytest.approx(1.0)
    assert host._cross_fade_seconds_for_slots(
        host._slot,
        host._slot,
        outgoing_duration_ms=4000,
        incoming_duration_ms=4000,
        outgoing_start_ms=1200,
        incoming_start_ms=0,
        outgoing_end_limit_ms=4000,
    ) == pytest.approx(1.0)


def test_vocal_removed_toggle_uses_smart_crossfade_timing():
    host = _PlaybackSmartFadeHost(smart_cross=True)

    assert host._vocal_removed_toggle_fade_seconds(host.player) == pytest.approx(0.8)


@pytest.mark.parametrize(
    ("mode", "expected_html", "expect_content"),
    [
        ("video", "<b>Lyric</b>", False),
        ("stage_display", "", True),
        ("lyric_display", "", True),
        ("image", "", True),
        ("metronome_display", "", True),
        ("backdrop", "", False),
        ("blank", "", False),
        ("white_screen", "", False),
        ("colour_bars", "", False),
    ],
)
def test_sync_output_surface_widget_supports_all_display_modes(mode, expected_html, expect_content):
    class _CaptureWidget:
        def __init__(self) -> None:
            self.mode = ""
            self.alert_text = ""
            self.backdrop_message = ""
            self.show_backdrop_message = False
            self.lyric_html = ""
            self.video_pixmap = QPixmap()
            self.content_pixmap = QPixmap()
            self.backdrop_pixmap = QPixmap()
            self.overlay_args = None

        def configure_overlay(self, **kwargs) -> None:
            self.overlay_args = dict(kwargs)

        def set_mode(self, mode_value: str) -> None:
            self.mode = str(mode_value)

        def set_alert_text(self, text: str) -> None:
            self.alert_text = str(text)

        def set_backdrop_pixmap(self, pixmap) -> None:
            self.backdrop_pixmap = QPixmap(pixmap)

        def configure_backdrop(self, *, show_message: bool = False, message_text: str = "") -> None:
            self.show_backdrop_message = bool(show_message)
            self.backdrop_message = str(message_text)

        def set_video_pixmap(self, pixmap) -> None:
            self.video_pixmap = QPixmap(pixmap)

        def set_content_pixmap(self, pixmap) -> None:
            self.content_pixmap = QPixmap(pixmap)

        def set_lyric_html(self, html: str) -> None:
            self.lyric_html = str(html)

        def width(self) -> int:
            return 320

        def height(self) -> int:
            return 180

    class _OutputWidgetHost(_AudioOnlyVideoRouteHost):
        def __init__(self) -> None:
            super().__init__()
            self.video_display_lyric_overlay_rect = {"x": 0, "y": 0, "w": 10000, "h": 10000}
            self.video_display_show_lyric_overlay = True
            self.video_display_show_stage_alert = True
            self._stage_alert_message = "Alert"
            self._video_current_frame_pixmap = QPixmap(8, 8)
            self._video_current_frame_pixmap.fill(Qt.black)
            self.stage_snapshot_calls = 0
            self.lyric_snapshot_calls = 0
            self.metronome_snapshot_calls = 0
            self._slot.display_image_path = "image.png"

        def _stage_alert_active(self) -> bool:
            return False

        def _video_backdrop_pixmap(self) -> QPixmap:
            pixmap = QPixmap(8, 8)
            pixmap.fill(Qt.black)
            return pixmap

        def _video_backdrop_message_text(self) -> str:
            return "No video is playing"

        def _runtime_video_destination_frame(self, _destination_id: str):
            return mw.QImage()

        def _current_video_lyric_html(self) -> str:
            return "<b>Lyric</b>"

        def _render_stage_display_snapshot(self, target_width=None, target_height=None) -> QPixmap:
            _ = (target_width, target_height)
            self.stage_snapshot_calls += 1
            pixmap = QPixmap(12, 12)
            pixmap.fill(Qt.black)
            return pixmap

        def _render_lyric_display_snapshot(self, target_width=None, target_height=None) -> QPixmap:
            _ = (target_width, target_height)
            self.lyric_snapshot_calls += 1
            pixmap = QPixmap(10, 10)
            pixmap.fill(Qt.black)
            return pixmap

        def _slot_display_image_pixmap(self, slot) -> QPixmap:
            _ = slot
            pixmap = QPixmap(14, 14)
            pixmap.fill(Qt.black)
            return pixmap

        def _render_metronome_display_snapshot(self, slot, width: int, height: int) -> QPixmap:
            _ = (slot, width, height)
            self.metronome_snapshot_calls += 1
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.black)
            return pixmap

    app = QApplication.instance() or QApplication([])
    host = _OutputWidgetHost()
    widget = _CaptureWidget()

    host._sync_output_surface_widget(widget, mode, force=True)

    assert widget.mode == mode
    assert widget.lyric_html == expected_html
    assert widget.content_pixmap.isNull() is (not expect_content)
    if mode == "stage_display":
        assert host.stage_snapshot_calls == 1
    if mode == "lyric_display":
        assert host.lyric_snapshot_calls == 1
    if mode == "metronome_display":
        assert host.metronome_snapshot_calls == 1
    if mode == "backdrop":
        assert widget.show_backdrop_message is True
        assert widget.backdrop_message == "No video is playing"
    assert app is not None


def test_video_widget_paints_lyric_overlay_without_type_error():
    app = QApplication.instance() or QApplication([])
    widget = VideoDisplayWidget()
    widget.resize(320, 180)
    widget.set_mode("video")
    widget.set_video_pixmap(mw.QPixmap(320, 180))
    widget.configure_overlay(
        overlay_rect={"x": 800, "y": 6800, "w": 8400, "h": 2400},
        show_lyric_overlay=True,
        show_stage_alert=False,
    )
    widget.set_lyric_html("<div style='color:#fff;'>hello<br/>world</div>")

    widget.paintEvent(QPaintEvent(widget.rect()))

    assert widget._lyric_html


def test_metronome_display_snapshot_supports_audio_beat_map():
    app = QApplication.instance() or QApplication([])

    class _MetronomeHost(_AudioOnlyVideoRouteHost):
        def __init__(self) -> None:
            super().__init__()
            self._slot = mw.SoundButtonData(
                file_path="theme_song.mp3",
                title="Theme",
                audio_beat_map=AudioBeatMap(
                    bpm=128.0,
                    time_signature_num=3,
                    time_signature_den=4,
                    first_downbeat_ms=100,
                    beat_times_ms=[100, 568, 1036],
                    beat_numbers=[1, 2, 3],
                    source="librosa",
                    confidence=0.75,
                ),
            )

        def _player_for_slot_key(self, _key):
            return None

        def font(self):
            return QApplication.font()

        class _SeekSlider:
            @staticmethod
            def value() -> int:
                return 700

        seek_slider = _SeekSlider()

    host = _MetronomeHost()
    pixmap = host._render_metronome_display_snapshot(host._slot, 320, 180)

    assert pixmap.isNull() is False
    assert app is not None


def test_stage_display_snapshot_reuses_hidden_renderer_and_cached_pixmap(monkeypatch):
    app = QApplication.instance() or QApplication([])
    created = []

    class _FakeStageWindow:
        def __init__(self, _parent):
            created.append(self)
            self.values = None
            self.alert = None
            self.status = ""

        def configure_gadgets(self, _gadgets) -> None:
            return None

        def configure_font_settings(self, **_kwargs) -> None:
            return None

        def update_values(self, **kwargs) -> None:
            self.values = dict(kwargs)

        def set_alert(self, text: str, active: bool) -> None:
            self.alert = (text, bool(active))

        def set_playback_status(self, status: str) -> None:
            self.status = str(status)

    monkeypatch.setattr(video_display_module, "GadgetStageDisplayWindow", _FakeStageWindow)

    class _StageSnapshotHost(VideoDisplayMixin):
        def __init__(self) -> None:
            self.current_playing = None
            self.stage_display_gadgets = {}
            self.stage_display_font_family = ""
            self.stage_display_font_size = 24
            self.stage_display_lyric_font_family = ""
            self.stage_display_lyric_font_size = 32
            self.stage_display_lyric_role_colors = {"played": "#AAA", "current": "#FFF000", "next": "#FFF"}
            self.stage_display_lyric_role_sizes = {"played": 16, "current": 24, "next": 20}
            self.stage_display_lyric_auto_adjust_role_sizes = True
            self.stage_display_lyric_role_scale_percents = {"played": 70, "current": 115, "next": 90}
            self.stage_display_lyric_role_bold = {"played": True, "current": True, "next": True}
            self.stage_display_lyric_role_italic = {"played": False, "current": False, "next": False}
            self.seek_slider = type("_Slider", (), {"value": lambda _self: 1000})()
            self.total_time = QLabel("00:01:00")
            self.elapsed_time = QLabel("00:00:01")
            self.remaining_time = QLabel("00:00:59")
            self.progress_label = QLabel("1%")
            self._stage_alert_message = ""
            self.render_calls = 0

        def _transport_total_ms(self) -> int:
            return 60000

        def _current_transport_cue_bounds(self):
            return None, None

        def _stage_display_current_lyric(self) -> str:
            return "Current lyric"

        def _next_stage_song_name(self) -> str:
            return "Next song"

        def _build_progress_bar_stylesheet(self, _progress_ratio: float, _cue_in_ms, _cue_out_ms) -> str:
            return "style"

        def _stage_alert_active(self) -> bool:
            return False

        def _stage_playback_status(self) -> str:
            return "playing"

        def _render_widget_snapshot(self, widget, width: int = 960, height: int = 540) -> QPixmap:
            _ = widget
            self.render_calls += 1
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.black)
            return pixmap

    host = _StageSnapshotHost()

    first = host._render_stage_display_snapshot(640, 360)
    second = host._render_stage_display_snapshot(640, 360)

    assert len(created) == 1
    assert host.render_calls == 1
    assert not first.isNull()
    assert not second.isNull()
    assert app is not None


def test_lyric_display_snapshot_reuses_hidden_renderer_and_cached_pixmap(monkeypatch):
    app = QApplication.instance() or QApplication([])
    created = []

    class _FakeLyricWindow:
        def __init__(self, _parent):
            created.append(self)

        def set_transparent_mode_enabled(self, _enabled: bool) -> None:
            return None

        def configure_display_settings(self, **_kwargs) -> None:
            return None

        def update_playback_state(self, **_kwargs) -> None:
            return None

    monkeypatch.setattr(video_display_module, "LyricDisplayWindow", _FakeLyricWindow)

    class _LyricSnapshotHost(VideoDisplayMixin):
        def __init__(self) -> None:
            self.current_playing = None
            self.lyric_display_font_family = ""
            self.lyric_display_font_size = 36
            self.lyric_display_show_not_playing_message = True
            self.lyric_display_previous_line_count = 1
            self.lyric_display_next_line_count = 2
            self.lyric_display_role_colors = {"played": "#AAA", "current": "#FFF000", "next": "#FFF"}
            self.lyric_display_role_sizes = {"played": 18, "current": 28, "next": 22}
            self.lyric_display_auto_adjust_role_sizes = True
            self.lyric_display_role_scale_percents = {"played": 70, "current": 115, "next": 90}
            self.lyric_display_role_bold = {"played": True, "current": True, "next": True}
            self.lyric_display_role_italic = {"played": False, "current": False, "next": False}
            self._lyric_force_blank = False
            self.render_calls = 0

        def _render_widget_snapshot(self, widget, width: int = 960, height: int = 540) -> QPixmap:
            _ = widget
            self.render_calls += 1
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.black)
            return pixmap

    host = _LyricSnapshotHost()

    first = host._render_lyric_display_snapshot(640, 360)
    second = host._render_lyric_display_snapshot(640, 360)

    assert len(created) == 1
    assert host.render_calls == 1
    assert not first.isNull()
    assert not second.isNull()
    assert app is not None


def test_video_frame_bucket_uses_media_fps():
    host = _AudioOnlyVideoRouteHost()
    info = MediaProbeInfo(has_video=True, fps=25.0)

    assert host._video_frame_interval_ms(info) == 40
    assert host._video_frame_bucket_ms(83, info) == 80
    assert host._video_frame_interval_ms(MediaProbeInfo()) == 33


def test_video_output_dimensions_follow_rotation_metadata():
    host = _AudioOnlyVideoRouteHost()

    assert host._video_output_dimensions(MediaProbeInfo(width=1920, height=1080, rotation_deg=0)) == (1920, 1080)
    assert host._video_output_dimensions(MediaProbeInfo(width=1920, height=1080, rotation_deg=90)) == (1080, 1920)
    assert host._video_decode_dimensions(MediaProbeInfo(width=3840, height=2160)) == (3840, 2160)


def test_video_target_decode_dimensions_follow_surface_size():
    host = _VideoRefreshHost()
    info = MediaProbeInfo(width=3840, height=2160, rotation_deg=0)

    host._target_size = (1280, 720)
    assert host._video_target_decode_dimensions(info) == (1280, 720)

    host._target_size = (4096, 2160)
    assert host._video_target_decode_dimensions(info) == (3840, 2160)

    rotated = MediaProbeInfo(width=1920, height=1080, rotation_deg=90)
    host._target_size = (540, 960)
    assert host._video_target_decode_dimensions(rotated) == (960, 540)


def test_video_snapshot_dimensions_follow_surface_size():
    host = _VideoRefreshHost()

    host._target_size = (1920, 1080)
    assert host._video_snapshot_dimensions() == (1920, 1080)

    host._target_size = (0, 0)
    assert host._video_snapshot_dimensions() == (960, 540)


def test_video_snapshot_dimensions_include_ndi_target_when_enabled():
    host = _VideoRefreshHost()
    host.ndi_output_enabled = True
    host.ndi_output_resolution_mode = "custom"
    host.ndi_output_width = 1600
    host.ndi_output_height = 900
    host.video_display_mode_playing = "stage_display"
    host.video_display_mode_idle = "blank"

    host._target_size = (0, 0)

    assert host._video_snapshot_dimensions() == (1600, 900)


def test_video_refresh_keeps_single_decode_in_flight():
    host = _VideoRefreshHost()

    host._queue_video_frame_refresh()
    host._position_ms = 120
    host._queue_video_frame_refresh()

    assert host._video_decode_inflight_key == ("stream", 80)
    assert host._video_frame_dispatcher.requests == [("stream", 1, "clip.mp4", 80, 640, 360, 40)]


def test_video_refresh_does_not_restart_stream_during_normal_playback_progress():
    host = _VideoRefreshHost()
    host._video_stream_path_key = host._normalized_media_probe_key("clip.mp4")
    host._video_stream_interval_ms = 40
    host._video_stream_dimensions = (640, 360)
    host._video_active_stream_revision = 0
    host._video_decode_inflight_key = ("stream", 80)
    host._video_current_frame_key = (host._normalized_media_probe_key("clip.mp4"), 80)
    host._video_last_frame_pts_ms = 80
    host._position_ms = 240

    host._queue_video_frame_refresh()

    assert host._video_frame_dispatcher.requests == []


def test_video_refresh_restarts_stream_after_transport_invalidation():
    host = _VideoRefreshHost()
    host._video_stream_path_key = host._normalized_media_probe_key("clip.mp4")
    host._video_stream_interval_ms = 40
    host._video_stream_dimensions = (640, 360)
    host._video_active_stream_revision = 0
    host._video_decode_inflight_key = ("stream", 80)
    host._position_ms = 240
    host._invalidate_video_playback_sync(refresh=False)

    host._queue_video_frame_refresh()

    assert host._video_frame_dispatcher.requests[-1] == ("stream", 1, "clip.mp4", 240, 640, 360, 40)


def test_video_surface_geometry_change_preserves_current_frame():
    app = QApplication.instance() or QApplication([])
    host = _VideoRefreshHost()
    host._video_current_frame_key = ("clip.mp4", 80)
    current_pixmap = host._video_current_frame_pixmap

    host._on_video_surface_geometry_changed()

    assert host._video_current_frame_key == ("clip.mp4", 80)
    assert host._video_current_frame_pixmap is current_pixmap
    assert host._video_frame_dispatcher.requests == [("clear",), ("stream", 1, "clip.mp4", 80, 640, 360, 40)]
    assert app is not None


def test_stage_display_geometry_change_triggers_snapshot_refresh():
    app = QApplication.instance() or QApplication([])

    class _StageRefreshHost(_VideoRefreshHost):
        def __init__(self) -> None:
            super().__init__()
            self.video_display_mode_playing = "stage_display"
            self.refresh_calls: list[bool] = []
            self.clear_calls: list[bool] = []

        def _refresh_video_display(self, force: bool = False) -> None:
            self.refresh_calls.append(bool(force))

        def _clear_video_frame_runtime(self, preserve_current_frame: bool = False) -> None:
            self.clear_calls.append(bool(preserve_current_frame))

    host = _StageRefreshHost()

    host._on_video_surface_geometry_changed()

    assert host.refresh_calls == [True]
    assert host.clear_calls == []
    assert app is not None


def test_video_decoder_ignores_stale_request_tags():
    host = _VideoRefreshHost()
    host._video_active_request_tag = 2

    host._on_video_frame_decoded(1, "clip.mp4", 80, 640, 360, b"x" * (640 * 360 * 3))

    assert host._video_current_frame_key is None


def test_video_route_forces_blank_during_video_switch_until_cleared():
    class _VideoSwitchRouteHost(_AudioOnlyVideoRouteHost):
        def __init__(self) -> None:
            super().__init__()
            self._slot = mw.SoundButtonData(file_path="clip.mp4")
            self._media_probe_cache = {}
            self._video_force_blank_until_frame = False
            self._video_force_blank_expected_path = ""
            self.refresh_calls = []

        def _media_probe_for_path(self, path: str) -> MediaProbeInfo:
            if str(path or "").strip().lower().endswith(".mp4"):
                return MediaProbeInfo(has_video=True, has_audio=True, fps=25.0, duration_ms=10000, width=640, height=360)
            return MediaProbeInfo()

        def _clear_video_frame_runtime(self, preserve_current_frame: bool = False) -> None:
            return None

        def _refresh_video_display(self, force: bool = False) -> None:
            self.refresh_calls.append(bool(force))

    host = _VideoSwitchRouteHost()

    host._start_video_switch_blank("clip.mp4")
    assert host._active_video_route_mode() == "blank"
    assert host.refresh_calls == [True]

    host._clear_video_switch_blank()
    assert host._active_video_route_mode() == "video"


def test_video_route_stays_blank_during_switch_even_without_current_playing_key():
    class _VideoSwitchRouteHost(_AudioOnlyVideoRouteHost):
        def __init__(self) -> None:
            super().__init__()
            self.current_playing = None
            self._media_probe_cache = {}
            self._video_force_blank_until_frame = False
            self._video_force_blank_expected_path = ""

        def _media_probe_for_path(self, path: str) -> MediaProbeInfo:
            if str(path or "").strip().lower().endswith(".mp4"):
                return MediaProbeInfo(has_video=True, has_audio=True, fps=25.0, duration_ms=10000, width=640, height=360)
            return MediaProbeInfo()

        def _clear_video_frame_runtime(self, preserve_current_frame: bool = False) -> None:
            return None

        def _refresh_video_display(self, force: bool = False) -> None:
            return None

    host = _VideoSwitchRouteHost()

    host._start_video_switch_blank("clip.mp4")

    assert host._active_video_route_mode() == "blank"


def test_video_refresh_continues_decoding_during_switch_blank():
    host = _VideoRefreshHost()
    host._start_video_switch_blank("clip.mp4")

    host._queue_video_frame_refresh()

    assert host._video_frame_dispatcher.requests[-1] == ("stream", 1, "clip.mp4", 80, 640, 360, 40)
    assert host._active_video_route_mode() == "blank"


def test_video_prestart_hold_uses_video_route_before_play_state():
    app = QApplication.instance() or QApplication([])

    class _VideoPrestartHost(_VideoRefreshHost):
        def _stage_playback_status(self) -> str:
            return "not_playing"

    host = _VideoPrestartHost()

    host._begin_video_prestart_hold("clip.mp4")
    host._queue_video_frame_refresh()

    assert host._active_video_route_mode() == "video"
    assert host._video_frame_dispatcher.requests[-1] == ("frame", 1, "clip.mp4", 80, 640, 360)
    assert app is not None


def test_video_frame_decode_completes_pending_video_synced_start():
    app = QApplication.instance() or QApplication([])

    class _VideoPrestartHost(_VideoRefreshHost):
        def __init__(self) -> None:
            super().__init__()
            self.completed_paths = []

        def _stage_playback_status(self) -> str:
            return "not_playing"

        def _complete_pending_video_synced_start(self, path_key: str) -> None:
            self.completed_paths.append(path_key)

    host = _VideoPrestartHost()
    host._begin_video_prestart_hold("clip.mp4")
    host._video_active_request_tag = 1

    host._on_video_frame_decoded(1, "clip.mp4", 80, 640, 360, b"x" * (640 * 360 * 3))

    assert host.completed_paths == [host._normalized_media_probe_key("clip.mp4")]
    assert host._video_current_frame_key == (host._normalized_media_probe_key("clip.mp4"), 80)
    assert app is not None


def test_send_ndi_audio_flushes_player_tap_blocks():
    class _DummySender:
        def __init__(self):
            self.chunks = []

        def send_audio_frames(self, frames, sample_rate):
            self.chunks.append((np.asarray(frames, dtype=np.float32), int(sample_rate)))
            return True

    class _DummyPlayer:
        def __init__(self):
            self.calls = []
            self.player_id = "player-a"

        def sampleRate(self):
            return 48000
    video_display_module.clear_output_monitor_frames()
    video_display_module.append_output_monitor_frames(
        "player-a",
        np.ones((3000, 2), dtype=np.float32) * 0.25,
        mode="pre_fader",
    )
    original_take = video_display_module.take_output_monitor_frames
    video_display_module.take_output_monitor_frames = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy path"))

    host = _VideoRefreshHost()
    try:
        host.ndi_output_audio_enabled = True
        host.ndi_output_audio_tap_mode = "pre_fader"
        host._ndi_sender = _DummySender()
        host._ndi_last_config = mw.NDIOutputConfig(
            source_name="pyssp-video",
            width=1920,
            height=1080,
            fps=30.0,
            audio_enabled=True,
        )
        player = _DummyPlayer()
        host._ndi_audio_players = lambda: [player]

        host._send_ndi_audio()
    finally:
        video_display_module.take_output_monitor_frames = original_take

    assert len(host._ndi_sender.chunks) == 2
    chunk, sample_rate = host._ndi_sender.chunks[0]
    assert sample_rate == 48000
    assert chunk.shape == (1024, 2)
    assert video_display_module.output_monitor_frame_counts("player-a") == {"pre_fader": 952, "post_fader": 0}
    video_display_module.clear_output_monitor_frames()


def test_send_ndi_audio_mixes_active_players():
    class _DummySender:
        def __init__(self):
            self.chunks = []

        def send_audio_frames(self, frames, sample_rate):
            self.chunks.append((np.asarray(frames, dtype=np.float32), int(sample_rate)))
            return True

    class _DummyPlayer:
        def __init__(self, value):
            self.value = float(value)
            self.player_id = f"player-{value}"

        def sampleRate(self):
            return 48000
    video_display_module.clear_output_monitor_frames()
    video_display_module.append_output_monitor_frames(
        "player-0.25",
        np.ones((1600, 2), dtype=np.float32) * 0.25,
        mode="post_fader",
    )
    video_display_module.append_output_monitor_frames(
        "player-0.5",
        np.ones((1600, 2), dtype=np.float32) * 0.5,
        mode="post_fader",
    )

    host = _VideoRefreshHost()
    host.ndi_output_audio_enabled = True
    host.ndi_output_audio_tap_mode = "post_fader"
    host._ndi_sender = _DummySender()
    host._ndi_last_config = mw.NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )
    host._ndi_audio_players = lambda: [_DummyPlayer(0.25), _DummyPlayer(0.5)]

    try:
        host._send_ndi_audio()
    finally:
        video_display_module.clear_output_monitor_frames()

    assert len(host._ndi_sender.chunks) == 1
    chunk, sample_rate = host._ndi_sender.chunks[0]
    assert sample_rate == 48000
    assert chunk.shape == (1024, 2)
    assert np.allclose(chunk, np.ones((1024, 2), dtype=np.float32) * 0.75)


def test_send_ndi_audio_supports_audio_player_proxy():
    class _DummySender:
        def __init__(self):
            self.chunks = []

        def send_audio_frames(self, frames, sample_rate):
            self.chunks.append((np.asarray(frames, dtype=np.float32), int(sample_rate)))
            return True

    class _FakeAudioController(QObject):
        positionChanged = pyqtSignal(str, int)
        durationChanged = pyqtSignal(str, int)
        stateChanged = pyqtSignal(str, int)
        mediaLoadFinished = pyqtSignal(str, int, bool, str)

        def __init__(self):
            super().__init__()
            self.state_cache = AudioStateCache()
            self.calls = []

        def post(self, player_id: str, command: str, payload=None):
            return None

        def call(self, player_id: str, command: str, payload=None, timeout: float = 2.0):
            self.calls.append((str(player_id), str(command), payload, float(timeout)))
            if command == "sampleRate":
                return 48000
            if command == "outputBlockSize":
                return 1024
            raise AssertionError(command)

    app = QApplication.instance() or QApplication([])
    _ = app
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")
    controller.stateChanged.emit("player-test", AudioPlayerProxy.PlayingState)

    host = _VideoRefreshHost()
    host.ndi_output_audio_enabled = True
    host.ndi_output_audio_tap_mode = "post_fader"
    host._ndi_sender = _DummySender()
    host._ndi_last_config = mw.NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )
    host._ndi_audio_players = lambda: [player]
    video_display_module.clear_output_monitor_frames()
    video_display_module.append_output_monitor_frames(
        "player-test",
        np.ones((3000, 2), dtype=np.float32) * 0.125,
        mode="post_fader",
    )
    try:
        host._send_ndi_audio()
    finally:
        video_display_module.clear_output_monitor_frames()

    assert len(host._ndi_sender.chunks) == 2
    chunk, sample_rate = host._ndi_sender.chunks[0]
    assert sample_rate == 48000
    assert chunk.shape == (1024, 2)
    assert np.allclose(chunk, np.ones((1024, 2), dtype=np.float32) * 0.125)


def test_send_ndi_audio_does_not_stall_when_one_playing_player_has_no_frames():
    class _DummySender:
        def __init__(self):
            self.chunks = []

        def send_audio_frames(self, frames, sample_rate):
            self.chunks.append((np.asarray(frames, dtype=np.float32), int(sample_rate)))
            return True

    class _DummyPlayer:
        def __init__(self, frames):
            self._frames = np.asarray(frames, dtype=np.float32)
            self.player_id = f"player-{len(self._frames)}"

        def sampleRate(self):
            return 48000
    video_display_module.clear_output_monitor_frames()
    video_display_module.append_output_monitor_frames(
        "player-2048",
        np.ones((2048, 2), dtype=np.float32) * 0.5,
        mode="post_fader",
    )

    host = _VideoRefreshHost()
    host.ndi_output_audio_enabled = True
    host.ndi_output_audio_tap_mode = "post_fader"
    host._ndi_sender = _DummySender()
    host._ndi_last_config = mw.NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )
    host._ndi_audio_players = lambda: [
        _DummyPlayer(np.ones((2048, 2), dtype=np.float32) * 0.5),
        _DummyPlayer(np.zeros((0, 2), dtype=np.float32)),
    ]

    try:
        host._send_ndi_audio()
    finally:
        video_display_module.clear_output_monitor_frames()

    assert len(host._ndi_sender.chunks) == 2
    chunk, sample_rate = host._ndi_sender.chunks[0]
    assert sample_rate == 48000
    assert chunk.shape == (1024, 2)
    assert np.allclose(chunk, np.ones((1024, 2), dtype=np.float32) * 0.5)
    assert video_display_module.output_monitor_frame_counts("player-2048") == {"pre_fader": 0, "post_fader": 0}


def test_send_ndi_audio_keeps_buffers_when_sender_defers_block():
    class _DummySender:
        def __init__(self):
            self.calls = 0

        def send_audio_frames(self, frames, sample_rate):
            _ = (frames, sample_rate)
            self.calls += 1
            return False

    class _DummyPlayer:
        player_id = "player-a"

        def sampleRate(self):
            return 48000
    video_display_module.clear_output_monitor_frames()
    video_display_module.append_output_monitor_frames(
        "player-a",
        np.ones((1600, 2), dtype=np.float32) * 0.5,
        mode="post_fader",
    )

    host = _VideoRefreshHost()
    host.ndi_output_audio_enabled = True
    host.ndi_output_audio_tap_mode = "post_fader"
    host._ndi_sender = _DummySender()
    host._ndi_last_config = mw.NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )
    player = _DummyPlayer()
    host._ndi_audio_players = lambda: [player]

    try:
        host._send_ndi_audio()
    finally:
        pass

    assert host._ndi_sender.calls == 1
    assert video_display_module.output_monitor_frame_counts("player-a") == {"pre_fader": 0, "post_fader": 1600}
    video_display_module.clear_output_monitor_frames()


def test_send_ndi_audio_flushes_pending_buffer_after_player_stops():
    class _DummySender:
        def __init__(self):
            self.chunks = []

        def send_audio_frames(self, frames, sample_rate):
            self.chunks.append((np.asarray(frames, dtype=np.float32), int(sample_rate)))
            return True

    host = _VideoRefreshHost()
    host.ndi_output_audio_enabled = True
    host.ndi_output_audio_tap_mode = "post_fader"
    host._ndi_sender = _DummySender()
    host._ndi_last_config = mw.NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )
    host._ndi_audio_last_sample_rate = 48000
    host._ndi_audio_last_channel_count = 2
    video_display_module.clear_output_monitor_frames()
    video_display_module.append_output_monitor_frames(
        "player-a",
        np.ones((600, 2), dtype=np.float32) * 0.375,
        mode="post_fader",
    )
    host._ndi_audio_players = lambda: []

    try:
        host._send_ndi_audio()
    finally:
        pass

    assert len(host._ndi_sender.chunks) == 1
    chunk, sample_rate = host._ndi_sender.chunks[0]
    assert sample_rate == 48000
    assert chunk.shape == (600, 2)
    assert np.allclose(chunk, np.ones((600, 2), dtype=np.float32) * 0.375)
    assert video_display_module.output_monitor_frame_counts("player-a") == {"pre_fader": 0, "post_fader": 0}
    video_display_module.clear_output_monitor_frames()


def test_send_ndi_audio_sends_silence_keepalive_when_idle():
    class _DummySender:
        def __init__(self):
            self.chunks = []

        def send_audio_frames(self, frames, sample_rate):
            self.chunks.append((np.asarray(frames, dtype=np.float32), int(sample_rate)))
            return True

    host = _VideoRefreshHost()
    host.ndi_output_audio_enabled = True
    host.ndi_output_audio_tap_mode = "post_fader"
    host._ndi_sender = _DummySender()
    host._ndi_last_config = mw.NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )
    host._ndi_audio_last_sample_rate = 48000
    host._ndi_audio_last_channel_count = 2
    video_display_module.clear_output_monitor_frames()
    host._ndi_audio_players = lambda: []

    try:
        host._send_ndi_audio()
    finally:
        video_display_module.clear_output_monitor_frames()

    assert len(host._ndi_sender.chunks) == 1
    chunk, sample_rate = host._ndi_sender.chunks[0]
    assert sample_rate == 48000
    assert chunk.shape == (1024, 2)
    assert np.allclose(chunk, np.zeros((1024, 2), dtype=np.float32))


def test_ndi_audio_players_prioritizes_current_playing_player_mapping_without_excluding_other_active_players():
    class _DummyPlayer:
        PlayingState = 1

        def __init__(self, name):
            self.name = name

        def state(self):
            return self.PlayingState

    host = _VideoRefreshHost()
    host.current_playing = ("B", 0, 8)
    mapped = _DummyPlayer("mapped")
    fallback = _DummyPlayer("fallback")
    host.player = fallback
    host.player_b = None
    host._multi_players = []
    host._shadow_player_for = lambda player: None
    host._player_for_slot_key = lambda key: mapped if key == ("B", 0, 8) else None

    players = host._ndi_audio_players()

    assert players == [mapped, fallback]


def test_tick_ndi_audio_refresh_runs_even_when_receiver_count_is_zero():
    host = _VideoRefreshHost()
    calls = []
    host._configure_ndi_sender = lambda: True
    host._ndi_sender_has_receivers = lambda: False
    host._send_ndi_audio = lambda: calls.append("audio")

    host._tick_ndi_audio_refresh()

    assert calls == ["audio"]


def test_refresh_ndi_output_sends_video_even_when_receiver_count_is_zero():
    class _DummySender:
        def __init__(self):
            self.calls = 0

        def send_video_frame(self, _image):
            self.calls += 1
            return True

    host = _VideoRefreshHost()
    host._configure_ndi_sender = lambda: True
    host._ndi_sender_has_receivers = lambda: False
    host._ndi_sender = _DummySender()
    image = mw.QImage(8, 8, mw.QImage.Format_RGB32)
    image.fill(0)
    host._video_current_frame_image = image
    host._render_ndi_frame_image = lambda: image

    host._refresh_ndi_output()

    assert host._ndi_sender.calls == 1
