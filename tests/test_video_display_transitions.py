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


class _VideoSyncHarness(VideoDisplayMixin):
    def __init__(
        self,
        *,
        use_pending_session: bool = False,
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
        self.ndi_output_enabled = False
        self.current_position_ms = 1200
        self.current_playing = None if use_pending_session else ("A", 0, 0)
        self._player = SimpleNamespace(player_id="player-a")

    def _video_display_target_visible(self) -> bool:
        return True

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
    finally:
        widget.close()
