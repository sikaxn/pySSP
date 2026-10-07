from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from PyQt5.QtGui import QColor, QImage, QPixmap
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.engine.types import VideoFrameSnapshot, VideoSessionSnapshot
from pyssp.ui.main_window.video_display import VideoDisplayMixin
from pyssp.ui.main_window.widgets import SoundButtonData
from pyssp.ui.video_display import VideoDisplayWidget


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _FakeVideoSessionService:
    def __init__(self) -> None:
        self.configure_calls: list[tuple[str, str, int, int, int, bool]] = []
        self.prime_calls: list[tuple[str, int]] = []
        self.clear_calls: list[str] = []
        self.submitted_frames: list[tuple[str, str, int, str]] = []
        self.snapshot = VideoSessionSnapshot(session_id="player-a")
        self.frame = VideoFrameSnapshot(session_id="player-a")

    def configure_video_session(
        self,
        player_id: str,
        source_path: str,
        *,
        position_ms: int,
        width: int,
        height: int,
        force: bool = False,
    ) -> bool:
        self.configure_calls.append((str(player_id), str(source_path), int(position_ms), int(width), int(height), bool(force)))
        return True

    def prime_video_session(self, player_id: str, position_ms: int) -> None:
        self.prime_calls.append((str(player_id), int(position_ms)))

    def clear_video_session(self, player_id: str) -> None:
        self.clear_calls.append(str(player_id))

    def video_session_snapshot(self, _player_id: str) -> VideoSessionSnapshot:
        return self.snapshot

    def video_session_frame(self, _player_id: str) -> VideoFrameSnapshot:
        return self.frame

    def submit_video_destination_frame(
        self,
        destination_id: str,
        image: QImage,
        *,
        route_mode: str,
        pts_ms: int,
        source_path: str,
    ) -> None:
        self.submitted_frames.append((str(destination_id), str(route_mode), int(pts_ms), str(source_path)))

    def clear_video_destination_frame(self, _destination_id: str) -> None:
        return None


class _BannerStub:
    def __init__(self) -> None:
        self.text = ""
        self.visible = False

    def setText(self, text: str) -> None:
        self.text = str(text or "")

    def setVisible(self, visible: bool) -> None:
        self.visible = bool(visible)


class _VideoSyncHarness(VideoDisplayMixin):
    def __init__(
        self,
        *,
        use_pending_session: bool = False,
        local_video_visible: bool = True,
    ) -> None:
        self._audio_service = _FakeVideoSessionService()
        self._slot = SoundButtonData(file_path=r"C:\Media\clip.mp4")
        self._info = SimpleNamespace(has_video=True, fps=30.0, width=640, height=360)
        self._video_active_session_id = ""
        self._video_active_session_source_path = ""
        self._video_current_frame_key = None
        self._video_current_frame_image = QImage()
        self._video_current_frame_pixmap = QPixmap()
        self._video_last_frame_pts_ms = 0
        self._video_force_blank_until_frame = False
        self._video_force_blank_expected_path = ""
        self._video_prestart_hold_until_frame = bool(use_pending_session)
        self._video_prestart_hold_expected_path = self._normalized_media_probe_key(self._slot.file_path) if use_pending_session else ""
        self._pending_video_synced_start = {"player_id": "player-b"} if use_pending_session else None
        self._completed_pending_paths: list[str] = []
        self._video_display_window = None
        self.video_preview_widget = None
        self.video_backend_warning_banner = _BannerStub()
        self.ndi_output_enabled = False
        self._local_video_visible = bool(local_video_visible)
        self.current_position_ms = 1200
        self.current_playing = None if use_pending_session else ("A", 0, 0)
        self._player = SimpleNamespace(player_id="player-a")
        self.video_low_spec_mode = False

    def _video_display_target_visible(self) -> bool:
        return True

    def _local_video_surface_visible(self) -> bool:
        return bool(self._local_video_visible)

    def _current_video_slot_and_probe(self):
        return self._slot, self._info

    def _active_video_route_mode(self) -> str:
        return "video"

    def _stage_playback_status(self) -> str:
        return "playing"

    def _current_video_display_position_ms(self) -> int:
        return int(self.current_position_ms)

    def _player_for_slot_key(self, _slot_key):
        return self._player

    def _apply_video_frame_to_targets(self) -> None:
        return None

    def _refresh_ndi_output(self, force: bool = False) -> None:
        _ = force

    def _complete_pending_video_synced_start(self, path_key: str) -> None:
        self._completed_pending_paths.append(str(path_key))


def test_video_display_widget_crossfades_mode_changes(qapp):
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    red = QPixmap(160, 90)
    red.fill(QColor("#ff0000"))
    blue = QPixmap(160, 90)
    blue.fill(QColor("#0000ff"))

    try:
        widget.set_content_pixmap(red)
        widget.set_mode("image")
        qapp.processEvents()

        widget.set_transition_duration_seconds(0.2)
        widget.set_backdrop_pixmap(blue)
        widget.set_mode("backdrop")
        qapp.processEvents()

        assert widget.is_transition_active() is True
        mid_image = widget.grab().toImage()
        mid_color = mid_image.pixelColor(mid_image.width() // 2, mid_image.height() // 2)
        assert mid_color.red() > mid_color.blue()

        deadline = time.monotonic() + 1.0
        while widget.is_transition_active() and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.02)

        assert widget.is_transition_active() is False
        qapp.processEvents()
        final_image = widget.grab().toImage()
        final_color = final_image.pixelColor(final_image.width() // 2, final_image.height() // 2)
        assert final_color.blue() > final_color.red()
    finally:
        widget.close()


def test_video_display_widget_skips_fade_when_duration_is_zero(qapp):
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    green = QPixmap(160, 90)
    green.fill(QColor("#00ff00"))
    white = QPixmap(160, 90)
    white.fill(QColor("#ffffff"))

    try:
        widget.set_content_pixmap(green)
        widget.set_mode("image")
        qapp.processEvents()

        widget.set_transition_duration_seconds(0.0)
        widget.set_backdrop_pixmap(white)
        widget.set_mode("backdrop")
        qapp.processEvents()

        assert widget.is_transition_active() is False
    finally:
        widget.close()


def test_video_display_widget_transition_expires_without_timer_events(qapp):
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    red = QPixmap(160, 90)
    red.fill(QColor("#ff0000"))
    blue = QPixmap(160, 90)
    blue.fill(QColor("#0000ff"))

    try:
        widget.apply_surface_state(mode="image", content_pixmap=red)
        qapp.processEvents()

        widget.set_transition_duration_seconds(0.05)
        widget.apply_surface_state(mode="backdrop", backdrop_pixmap=blue)
        time.sleep(0.12)

        assert widget.is_transition_active() is False
    finally:
        widget.close()


def test_video_display_widget_paints_video_image(qapp):
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    frame = QImage(160, 90, QImage.Format_RGB32)
    frame.fill(QColor("#3366cc"))

    try:
        widget.apply_surface_state(mode="video", video_image=frame, transition_key="clip-a")
        qapp.processEvents()

        image = widget.grab().toImage()
        color = image.pixelColor(image.width() // 2, image.height() // 2)
        assert color.blue() > color.red()
        assert widget._video_image.isNull() is False
    finally:
        widget.close()


def test_video_display_widget_reports_present_fps_for_non_video_updates(qapp):
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    red = QPixmap(160, 90)
    red.fill(QColor("#ff0000"))
    blue = QPixmap(160, 90)
    blue.fill(QColor("#0000ff"))

    try:
        widget.apply_surface_state(mode="image", content_pixmap=red, show_fps_overlay=True)
        qapp.processEvents()

        widget.set_transition_duration_seconds(0.12)
        widget.apply_surface_state(mode="backdrop", backdrop_pixmap=blue, show_fps_overlay=True)

        deadline = time.monotonic() + 1.0
        while widget.current_present_fps() <= 0.0 and time.monotonic() < deadline:
            widget.paintGL()
            qapp.processEvents()
            time.sleep(0.01)

        assert widget.current_present_fps() > 0.0
    finally:
        widget.close()


def test_video_display_widget_caches_scaled_live_video_pixmap(qapp):
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    frame = QPixmap(320, 180)
    frame.fill(QColor("#3366cc"))

    try:
        widget.apply_surface_state(mode="video", video_pixmap=frame, transition_key="clip-a")
        qapp.processEvents()
        _ = widget.grab()

        assert widget._video_scaled_pixmap_cache.isNull() is False
        assert widget._video_scaled_pixmap_target_size.width() > 0
        assert widget._video_scaled_pixmap_target_size.height() > 0
    finally:
        widget.close()


def test_video_display_widget_crossfades_same_mode_when_transition_key_changes(qapp):
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    red = QPixmap(160, 90)
    red.fill(QColor("#ff0000"))
    blue = QPixmap(160, 90)
    blue.fill(QColor("#0000ff"))

    try:
        widget.set_transition_duration_seconds(0.2)
        widget.apply_surface_state(mode="video", video_pixmap=red, transition_key="clip-a")
        qapp.processEvents()

        widget.apply_surface_state(mode="video", video_pixmap=blue, transition_key="clip-b")
        qapp.processEvents()

        assert widget.is_transition_active() is True
        mid_image = widget.grab().toImage()
        mid_color = mid_image.pixelColor(mid_image.width() // 2, mid_image.height() // 2)
        assert mid_color.red() > mid_color.blue()

        deadline = time.monotonic() + 1.0
        while widget.is_transition_active() and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.02)

        assert widget.is_transition_active() is False
        qapp.processEvents()
        final_image = widget.grab().toImage()
        final_color = final_image.pixelColor(final_image.width() // 2, final_image.height() // 2)
        assert final_color.blue() > final_color.red()
    finally:
        widget.close()


def test_queue_video_frame_refresh_uses_runtime_video_session_backend():
    host = _VideoSyncHarness()
    frame = QImage(320, 180, QImage.Format_RGB32)
    frame.fill(QColor("#224466"))
    host._audio_service.snapshot = VideoSessionSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        configured=True,
        primed=True,
        state=1,
        position_ms=host.current_position_ms,
        duration_ms=5000,
        frame_pts_ms=host.current_position_ms,
        frame_width=320,
        frame_height=180,
        backend_name="pyav",
    )
    host._audio_service.frame = VideoFrameSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        pts_ms=host.current_position_ms,
        ready=True,
        image=frame,
    )

    host._queue_video_frame_refresh(force=True)

    assert host._audio_service.configure_calls == [
        ("player-a", host._slot.file_path, host.current_position_ms, 640, 360, True)
    ]
    assert host._audio_service.prime_calls == [("player-a", host.current_position_ms)]
    assert host._video_current_frame_pixmap.isNull() is False
    assert host._video_last_frame_pts_ms == host.current_position_ms
    assert host._audio_service.submitted_frames == [
        ("local_program", "video", host.current_position_ms, host._slot.file_path)
    ]


def test_queue_video_frame_refresh_uses_pending_session_during_prestart_hold():
    host = _VideoSyncHarness(use_pending_session=True)
    host._audio_service.snapshot = VideoSessionSnapshot(
        session_id="player-b",
        source_path=host._slot.file_path,
        configured=True,
        primed=True,
        backend_name="pyav",
    )

    host._queue_video_frame_refresh(force=True)

    assert host._audio_service.configure_calls == [
        ("player-b", host._slot.file_path, host.current_position_ms, 640, 360, True)
    ]
    assert host._completed_pending_paths == [host._normalized_media_probe_key(host._slot.file_path)]


def test_queue_video_frame_refresh_skips_eager_pixmap_conversion_without_local_surface():
    host = _VideoSyncHarness(local_video_visible=False)
    frame = QImage(320, 180, QImage.Format_RGB32)
    frame.fill(QColor("#224466"))
    host._audio_service.snapshot = VideoSessionSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        configured=True,
        primed=True,
        state=1,
        position_ms=host.current_position_ms,
        duration_ms=5000,
        frame_pts_ms=host.current_position_ms,
        frame_width=320,
        frame_height=180,
        backend_name="pyav",
    )
    host._audio_service.frame = VideoFrameSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        pts_ms=host.current_position_ms,
        ready=True,
        image=frame,
    )

    host._queue_video_frame_refresh(force=True)

    assert host._video_current_frame_image.isNull() is False
    assert host._video_current_frame_pixmap.isNull() is True
    assert host._audio_service.submitted_frames == [
        ("local_program", "video", host.current_position_ms, host._slot.file_path)
    ]


def test_update_current_video_frame_from_session_scales_local_pixmap_only():
    class _LocalScaleHost(_VideoSyncHarness):
        def _local_video_surface_pixel_size(self) -> tuple[int, int]:
            return 160, 90

    host = _LocalScaleHost()
    frame = QImage(640, 360, QImage.Format_RGB32)
    frame.fill(QColor("#224466"))
    snapshot = VideoFrameSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        pts_ms=host.current_position_ms,
        ready=True,
        image=frame,
    )

    assert host._update_current_video_frame_from_session(snapshot) is True
    assert host._video_current_frame_image.size() == frame.size()
    assert host._video_current_frame_pixmap.width() == 160
    assert host._video_current_frame_pixmap.height() == 90


def test_queue_video_frame_refresh_shows_ffmpeg_backend_warning():
    host = _VideoSyncHarness(local_video_visible=False)
    frame = QImage(320, 180, QImage.Format_RGB32)
    frame.fill(QColor("#224466"))
    host._audio_service.snapshot = VideoSessionSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        configured=True,
        primed=True,
        state=1,
        position_ms=host.current_position_ms,
        duration_ms=5000,
        frame_pts_ms=host.current_position_ms,
        frame_width=320,
        frame_height=180,
        backend_name="ffmpeg",
    )
    host._audio_service.frame = VideoFrameSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        pts_ms=host.current_position_ms,
        ready=True,
        image=frame,
    )

    host._queue_video_frame_refresh(force=True)

    assert host.video_backend_warning_banner.visible is True
    assert "FFmpeg frame extraction" in host.video_backend_warning_banner.text
    assert "Low-spec mode" in host.video_backend_warning_banner.text

    host._audio_service.snapshot = VideoSessionSnapshot(
        session_id="player-a",
        source_path=host._slot.file_path,
        configured=True,
        primed=True,
        backend_name="pyav",
    )
    host._queue_video_frame_refresh()

    assert host.video_backend_warning_banner.visible is False


class _ExplodingAudioService:
    def video_destination_frame(self, _destination_id: str):
        raise AssertionError("visible video sync should not fetch local_program frames")


class _SurfaceSyncHarness(VideoDisplayMixin):
    def __init__(self) -> None:
        self.video_display_transition_fade_sec = 0.5
        self.video_display_lyric_overlay_rect = {"x": 800, "y": 6800, "w": 8400, "h": 2400}
        self.video_display_show_lyric_overlay = False
        self.video_display_show_stage_alert = False
        self._stage_alert_message = ""
        self.current_playing = None
        self._audio_service = _ExplodingAudioService()
        self._video_current_frame_pixmap = QPixmap(160, 90)
        self._video_current_frame_pixmap.fill(QColor("#8844ff"))

    def _stage_alert_active(self) -> bool:
        return False

    def _current_video_lyric_html(self) -> str:
        return ""


def test_sync_output_surface_widget_uses_local_video_frame_cache(qapp):
    host = _SurfaceSyncHarness()
    widget = VideoDisplayWidget()
    widget.resize(160, 90)
    widget.show()

    try:
        host._sync_output_surface_widget(widget, "video", force=True)
        qapp.processEvents()

        assert widget._video_pixmap.isNull() is False
        assert widget._video_image.isNull() is True
    finally:
        widget.close()


def test_apply_video_frame_to_targets_prefers_pixmap_for_local_video_widgets():
    class _VideoWidgetStub:
        def __init__(self) -> None:
            self._mode = "video"
            self.pixmap_calls = 0
            self.image_calls = 0
            self.last_pixmap = QPixmap()
            self.last_image = QImage()

        def isVisible(self) -> bool:
            return True

        def set_video_pixmap(self, pixmap: QPixmap) -> None:
            self.pixmap_calls += 1
            self.last_pixmap = QPixmap(pixmap)

        def set_video_image(self, image: QImage) -> None:
            self.image_calls += 1
            self.last_image = QImage(image)

    class _WindowStub:
        def __init__(self, widget) -> None:
            self.display_widget = widget

        def isVisible(self) -> bool:
            return True

    class _LiveFrameHost(VideoDisplayMixin):
        def __init__(self) -> None:
            self._video_current_frame_image = QImage(32, 18, QImage.Format_RGB32)
            self._video_current_frame_image.fill(QColor("#224466"))
            self._video_current_frame_pixmap = QPixmap(32, 18)
            self._video_current_frame_pixmap.fill(QColor("#224466"))
            self.video_preview_widget = _VideoWidgetStub()
            self._video_display_window = _WindowStub(_VideoWidgetStub())

    host = _LiveFrameHost()

    host._apply_video_frame_to_targets()

    assert host.video_preview_widget.pixmap_calls == 1
    assert host.video_preview_widget.image_calls == 0
    assert host.video_preview_widget.last_pixmap.isNull() is False
    assert host._video_display_window.display_widget.pixmap_calls == 1
    assert host._video_display_window.display_widget.image_calls == 0


def test_video_position_change_refresh_only_for_transport_dependent_routes():
    class _VisibleWindow:
        def __init__(self, visible: bool) -> None:
            self._visible = bool(visible)

        def isVisible(self) -> bool:
            return self._visible

    class _PositionRefreshHost(VideoDisplayMixin):
        def __init__(self, *, video_mode: str, ndi_mode: str = "blank", lyric_overlay: bool = False, metronome_visible: bool = False) -> None:
            self._video_mode = str(video_mode)
            self._ndi_mode = str(ndi_mode)
            self.video_display_show_lyric_overlay = bool(lyric_overlay)
            self.ndi_output_enabled = self._ndi_mode != "blank"
            self._metronome_display_window = _VisibleWindow(metronome_visible)

        def _active_video_route_mode(self) -> str:
            return self._video_mode

        def _active_ndi_route_mode(self) -> str:
            return self._ndi_mode

    assert _PositionRefreshHost(video_mode="video", lyric_overlay=False)._video_position_change_requires_surface_refresh() is False
    assert _PositionRefreshHost(video_mode="video", lyric_overlay=True)._video_position_change_requires_surface_refresh() is True
    assert _PositionRefreshHost(video_mode="stage_display")._video_position_change_requires_surface_refresh() is True
    assert _PositionRefreshHost(video_mode="blank", ndi_mode="lyric_display")._video_position_change_requires_surface_refresh() is True
    assert _PositionRefreshHost(video_mode="blank", metronome_visible=True)._video_position_change_requires_surface_refresh() is True
