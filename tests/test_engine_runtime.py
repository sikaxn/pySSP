from __future__ import annotations

import numpy as np
import pytest
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QImage

import pyssp.audio_engine as audio_engine_module
from pyssp.audio_service import AudioService
import pyssp.engine.runtime as runtime_module
import pyssp.engine.video_session as video_session_module
from pyssp.engine import FFmpegEngineServices, MediaRuntime
from pyssp.engine.types import MediaProbeResult, VideoFrameSnapshot, VideoSessionSnapshot


class _FakePlayer(QObject):
    StoppedState = 0
    PlayingState = 1
    PausedState = 2

    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)
    mediaLoadFinished = pyqtSignal(int, bool, str)

    def __init__(self) -> None:
        super().__init__()
        self._state = self.StoppedState
        self._position_ms = 0
        self._duration_ms = 0
        self.monitor_id = ""
        self.deleted = False

    def setOutputMonitorId(self, player_id: str) -> None:
        self.monitor_id = str(player_id)

    def stop(self) -> None:
        self._state = self.StoppedState
        self._position_ms = 0
        self.stateChanged.emit(self._state)
        self.positionChanged.emit(self._position_ms)

    def play(self) -> None:
        self._state = self.PlayingState
        self.stateChanged.emit(self._state)

    def pause(self) -> None:
        self._state = self.PausedState
        self.stateChanged.emit(self._state)

    def deleteLater(self) -> None:
        self.deleted = True

    def sampleRate(self) -> int:
        return 48000

    def outputBlockSize(self) -> int:
        return 1024


class _FakeVideoSession:
    def __init__(
        self,
        session_id: str,
        _state_getter,
        _position_getter,
        _duration_getter,
    ) -> None:
        self.session_id = str(session_id)
        self.configure_calls: list[tuple[str, int, int, int, bool]] = []
        self.prime_calls: list[int] = []
        self.clear_count = 0
        self.shutdown_count = 0
        self.snapshot_value = VideoSessionSnapshot(session_id=self.session_id)
        self.frame_value = VideoFrameSnapshot(session_id=self.session_id)

    def configure(
        self,
        source_path: str,
        *,
        position_ms: int = 0,
        width: int = 0,
        height: int = 0,
        force: bool = False,
    ) -> bool:
        self.configure_calls.append((str(source_path), int(position_ms), int(width), int(height), bool(force)))
        return True

    def clear(self) -> bool:
        self.clear_count += 1
        return True

    def prime(self, position_ms: int | None = None) -> bool:
        self.prime_calls.append(0 if position_ms is None else int(position_ms))
        return True

    def snapshot(self) -> VideoSessionSnapshot:
        return self.snapshot_value

    def current_frame(self) -> VideoFrameSnapshot:
        return self.frame_value

    def shutdown(self) -> None:
        self.shutdown_count += 1


def test_media_runtime_tracks_reference_session_and_multi_play_policy():
    runtime = MediaRuntime(player_factory=_FakePlayer)

    a = runtime.create_legacy_session("a")
    b = runtime.create_legacy_session("b")
    a.durationChanged.emit(5000)
    b.durationChanged.emit(6000)
    a.positionChanged.emit(1200)
    b.positionChanged.emit(2400)
    a.play()
    b.play()

    snapshot = runtime.transport_snapshot()
    assert snapshot.reference_session_id == "b"
    assert snapshot.position_ms == 2400
    assert snapshot.duration_ms == 6000
    assert snapshot.playing_session_ids == ("a", "b")

    runtime.set_multi_play_enabled(True)
    snapshot = runtime.transport_snapshot()
    assert snapshot.reference_session_id == "a"
    assert snapshot.position_ms == 1200
    assert snapshot.multi_play_enabled is True

    runtime.delete_session("a")
    snapshot = runtime.transport_snapshot()
    assert snapshot.reference_session_id == "b"
    assert snapshot.active_session_ids == ("b",)


def test_audio_service_delegates_session_ownership_to_runtime():
    runtime = MediaRuntime(player_factory=_FakePlayer)
    service = AudioService(runtime=runtime)

    assert service._dispatch("primary", "create", {}) is True
    assert runtime.has_session("primary") is True
    player = runtime.player_for_session("primary")
    assert isinstance(player, _FakePlayer)
    assert player.monitor_id == "primary"

    player.play()
    player.positionChanged.emit(1500)
    transport = service._dispatch("__runtime__", "transportSnapshot", {})
    diagnostics = service._dispatch("__runtime__", "engineDiagnostics", {})

    assert transport.reference_session_id == "primary"
    assert diagnostics.session_count == 1
    assert diagnostics.reference_session_id == "primary"

    assert service._dispatch("primary", "delete", {}) is True
    assert runtime.has_session("primary") is False
    assert player.deleted is True


def test_media_runtime_manages_video_sessions_alongside_players():
    runtime = MediaRuntime(player_factory=_FakePlayer, video_session_factory=_FakeVideoSession)
    try:
        runtime.create_legacy_session("primary")
        session = runtime._video_sessions["primary"]
        assert runtime.configure_session_video(
            "primary",
            "clip.mp4",
            position_ms=1200,
            width=640,
            height=360,
            force=True,
        ) is True
        assert runtime.prime_session_video("primary", position_ms=1200) is True

        assert session.configure_calls == [("clip.mp4", 1200, 640, 360, True)]
        assert session.prime_calls == [1200]

        image = QImage(16, 9, QImage.Format_RGB32)
        session.snapshot_value = VideoSessionSnapshot(
            session_id="primary",
            source_path="clip.mp4",
            configured=True,
            primed=True,
            state=1,
            position_ms=1200,
            duration_ms=5000,
            frame_pts_ms=1188,
            frame_width=16,
            frame_height=9,
            backend_name="pyav",
        )
        session.frame_value = VideoFrameSnapshot(
            session_id="primary",
            source_path="clip.mp4",
            pts_ms=1188,
            ready=True,
            image=image,
        )

        assert runtime.video_session_snapshot("primary") == session.snapshot_value
        assert runtime.video_session_frame("primary") == session.frame_value
        assert runtime.clear_session_video("primary") is True
        assert session.clear_count == 1
    finally:
        runtime.shutdown()


def test_audio_service_dispatches_runtime_video_session_commands():
    runtime = MediaRuntime(player_factory=_FakePlayer, video_session_factory=_FakeVideoSession)
    service = AudioService(runtime=runtime)
    try:
        assert service._dispatch("primary", "create", {}) is True
        assert service._dispatch(
            "primary",
            "configureVideoSession",
            {"source_path": "clip.mp4", "position_ms": 900, "width": 320, "height": 180, "force": True},
        ) is True
        assert service._dispatch("primary", "primeVideoSession", {"position_ms": 900}) is True
        assert service._dispatch("primary", "clearVideoSession", {}) is True
    finally:
        runtime.shutdown()


def test_pyav_frame_source_preserves_lookahead_frame():
    def _solid_image(color) -> QImage:
        image = QImage(8, 8, QImage.Format_RGB32)
        image.fill(color)
        return image

    frames = [
        {"pts_ms": 0, "image": _solid_image(Qt.red)},
        {"pts_ms": 40, "image": _solid_image(Qt.green)},
        {"pts_ms": 80, "image": _solid_image(Qt.blue)},
    ]

    source = video_session_module._PyAVFrameSource.__new__(video_session_module._PyAVFrameSource)
    source._path = "clip.mp4"
    source._width = 8
    source._height = 8
    source._container = object()
    source._stream = object()
    source._decoder = object()
    source._eof = False
    source._rotation_deg = 0
    source._last_selected_image = QImage()
    source._last_selected_pts_ms = 0
    source._pending_image = QImage()
    source._pending_pts_ms = -1
    source._last_decoded_pts_ms = -1
    source._last_seek_target_ms = -1
    source._ensure_open = lambda: None
    source._should_seek = lambda _target_ms: False
    source._seek_to = lambda _target_ms: None
    source._frame_pts_ms = lambda frame: int(frame["pts_ms"])
    source._frame_to_image = lambda frame: QImage(frame["image"])
    source._next_frame = lambda: frames.pop(0) if frames else None

    first_image, first_pts = source.frame_at(10)
    second_image, second_pts = source.frame_at(50)
    third_image, third_pts = source.frame_at(90)

    assert first_pts == 0
    assert second_pts == 40
    assert third_pts == 80
    assert first_image.pixelColor(0, 0).name() == "#ff0000"
    assert second_image.pixelColor(0, 0).name() == "#00ff00"
    assert third_image.pixelColor(0, 0).name() == "#0000ff"


def test_ffmpeg_engine_services_wrap_existing_support_module(monkeypatch):
    monkeypatch.setattr("pyssp.ffmpeg_support.ffmpeg_available", lambda: True)
    monkeypatch.setattr("pyssp.ffmpeg_support.get_ffmpeg_executable", lambda: "/tmp/ffmpeg")
    monkeypatch.setattr("pyssp.ffmpeg_support.get_ffprobe_executable", lambda: "/tmp/ffprobe")
    monkeypatch.setattr("pyssp.ffmpeg_support.ffmpeg_source", lambda: "bundled")
    monkeypatch.setattr("pyssp.ffmpeg_support.ffmpeg_version_text", lambda: "ffmpeg version test")
    monkeypatch.setattr("pyssp.ffmpeg_support.ffmpeg_supported_audio_extensions", lambda: [".wav", ".mp3"])
    monkeypatch.setattr("pyssp.ffmpeg_support.ffmpeg_supported_video_extensions", lambda: [".mp4"])
    monkeypatch.setattr("pyssp.ffmpeg_support.ffmpeg_supported_media_extensions", lambda: [".wav", ".mp3", ".mp4"])
    monkeypatch.setattr("pyssp.ffmpeg_support.probe_media_duration_ms", lambda path: 4321 if path == "demo.mp4" else 0)
    monkeypatch.setattr("pyssp.ffmpeg_support.media_has_audio_stream", lambda path: True if path == "demo.mp4" else None)
    monkeypatch.setattr("pyssp.ffmpeg_support.media_has_video_stream", lambda path: True if path == "demo.mp4" else None)
    monkeypatch.setattr(
        "pyssp.ffmpeg_support.probe_media_info",
        lambda path: type(
            "_Probe",
            (),
            {
                "duration_ms": 4321,
                "has_audio": True,
                "has_video": True,
                "width": 1920,
                "height": 1080,
                "fps": 29.97,
                "rotation_deg": 0,
            },
        )(),
    )

    services = FFmpegEngineServices()
    try:
        assert services.available() is True
        assert services.ffmpeg_executable() == "/tmp/ffmpeg"
        assert services.ffprobe_executable() == "/tmp/ffprobe"
        assert services.source() == "bundled"
        assert services.version_text() == "ffmpeg version test"
        assert services.supported_media_extensions() == [".wav", ".mp3", ".mp4"]
        assert services.probe_duration_ms("demo.mp4") == 4321
        assert services.has_audio_stream("demo.mp4") is True
        assert services.has_video_stream("demo.mp4") is True

        result = services.probe_media_info("demo.mp4")
        assert result == MediaProbeResult(
            source_path="demo.mp4",
            duration_ms=4321,
            has_audio=True,
            has_video=True,
            width=1920,
            height=1080,
            fps=29.97,
            rotation_deg=0,
        )
    finally:
        services.shutdown()


class _CapturingDispatcher:
    def __init__(self) -> None:
        self.audio_payloads = []

    def send_audio_frames(self, frames, sample_rate: int) -> bool:
        self.audio_payloads.append((frames.copy(), int(sample_rate)))
        return True


def test_media_runtime_ndi_audio_keepalive_uses_nominal_block_size(monkeypatch):
    runtime = MediaRuntime(player_factory=_FakePlayer)
    try:
        runtime._audio_sample_rate = 48000
        runtime._audio_channels = 2
        runtime._audio_stream_blocksize = 1024
        runtime._ndi_dispatcher = _CapturingDispatcher()
        runtime._video_destinations["ndi_program"].enabled = True
        runtime._video_destinations["ndi_program"].audio_enabled = True
        monkeypatch.setattr(runtime_module, "list_output_monitor_players", lambda mode="post_fader": ["a"])
        monkeypatch.setattr(runtime_module, "mix_output_monitor_chunk", lambda *args, **kwargs: None)
        monkeypatch.setattr(runtime_module, "consume_output_monitor_chunk", lambda *args, **kwargs: None)

        runtime._service_ndi_audio_from_render(1024)

        assert len(runtime._ndi_dispatcher.audio_payloads) == 1
        frames, sample_rate = runtime._ndi_dispatcher.audio_payloads[0]
        assert sample_rate == 48000
        assert frames.shape == (1024, 2)
        assert np.max(np.abs(frames)) > 0.0
        assert runtime._video_destinations["ndi_program"].audio_send_count == 1
    finally:
        runtime.shutdown()


def test_media_runtime_destination_video_wait_timeout_tracks_remaining_frame_time():
    image = QImage(8, 8, QImage.Format_RGB32)
    image.fill(Qt.black)
    record = runtime_module._DestinationRecord(
        destination_id="ndi_program",
        enabled=True,
        fps=60.0,
        frame_image=image,
        last_video_sent_at=1.0,
    )

    assert MediaRuntime._destination_video_wait_timeout(record, 1.0) == pytest.approx(0.01)
    assert MediaRuntime._destination_video_wait_timeout(record, 1.010) == pytest.approx((1.0 / 60.0) - 0.010, abs=1e-6)
    assert MediaRuntime._destination_video_wait_timeout(record, 1.017) == 0.0


def test_media_runtime_ndi_audio_keepalive_uses_runtime_stream_format_without_players(monkeypatch):
    runtime = MediaRuntime(player_factory=_FakePlayer)
    try:
        runtime._audio_sample_rate = 44100
        runtime._audio_channels = 4
        runtime._audio_stream_blocksize = 2048
        runtime._ndi_dispatcher = _CapturingDispatcher()
        runtime._video_destinations["ndi_program"].enabled = True
        runtime._video_destinations["ndi_program"].audio_enabled = True
        monkeypatch.setattr(runtime_module, "list_output_monitor_players", lambda mode="post_fader": [])
        monkeypatch.setattr(runtime_module, "mix_output_monitor_chunk", lambda *args, **kwargs: None)
        monkeypatch.setattr(runtime_module, "consume_output_monitor_chunk", lambda *args, **kwargs: None)

        runtime._service_ndi_audio_from_render(2048)

        assert len(runtime._ndi_dispatcher.audio_payloads) == 1
        frames, sample_rate = runtime._ndi_dispatcher.audio_payloads[0]
        assert sample_rate == 44100
        assert frames.shape == (2048, 4)
        assert np.max(np.abs(frames)) > 0.0
        assert runtime._video_destinations["ndi_program"].last_audio_sample_rate == 44100
        assert runtime._video_destinations["ndi_program"].last_audio_channel_count == 4
    finally:
        runtime.shutdown()


def test_media_runtime_ndi_audio_sends_one_block_per_render_tick(monkeypatch):
    runtime = MediaRuntime(player_factory=_FakePlayer)
    call_count = {"mix": 0, "consume": 0}

    def _mix(*_args, **_kwargs):
        call_count["mix"] += 1
        return np.ones((1024, 2), dtype=np.float32) * 0.25, {"a": 1024}

    def _consume(consume_map, mode="post_fader"):
        _ = mode
        call_count["consume"] += int(consume_map.get("a", 0) > 0)

    try:
        runtime._audio_sample_rate = 48000
        runtime._audio_channels = 2
        runtime._audio_stream_blocksize = 1024
        runtime._ndi_dispatcher = _CapturingDispatcher()
        runtime._video_destinations["ndi_program"].enabled = True
        runtime._video_destinations["ndi_program"].audio_enabled = True
        monkeypatch.setattr(runtime_module, "list_output_monitor_players", lambda mode="post_fader": ["a"])
        monkeypatch.setattr(runtime_module, "mix_output_monitor_chunk", _mix)
        monkeypatch.setattr(runtime_module, "consume_output_monitor_chunk", _consume)

        runtime._service_ndi_audio_from_render(1024)

        assert len(runtime._ndi_dispatcher.audio_payloads) == 1
        frames, _sample_rate = runtime._ndi_dispatcher.audio_payloads[0]
        assert np.max(np.abs(frames)) > 0.2
        assert call_count["mix"] == 1
        assert call_count["consume"] == 1
        assert runtime._video_destinations["ndi_program"].audio_send_count == 1
    finally:
        runtime.shutdown()


def test_media_runtime_ndi_audio_post_fader_uses_direct_mixed_block(monkeypatch):
    runtime = MediaRuntime(player_factory=_FakePlayer)
    try:
        runtime._audio_sample_rate = 48000
        runtime._audio_channels = 2
        runtime._audio_stream_blocksize = 1024
        runtime._ndi_dispatcher = _CapturingDispatcher()
        runtime._video_destinations["ndi_program"].enabled = True
        runtime._video_destinations["ndi_program"].audio_enabled = True
        runtime._video_destinations["ndi_program"].audio_tap_mode = "post_fader"
        monkeypatch.setattr(
            runtime_module,
            "mix_output_monitor_chunk",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("monitor mix should not be used")),
        )
        monkeypatch.setattr(runtime_module, "consume_output_monitor_chunk", lambda *args, **kwargs: None)

        direct = np.ones((1024, 2), dtype=np.float32) * 0.125
        runtime._service_ndi_audio_from_render(1024, mixed_post_fader=direct)

        assert len(runtime._ndi_dispatcher.audio_payloads) == 1
        frames, sample_rate = runtime._ndi_dispatcher.audio_payloads[0]
        assert sample_rate == 48000
        assert frames.shape == (1024, 2)
        assert np.allclose(frames, direct)
    finally:
        runtime.shutdown()


def test_media_runtime_ndi_audio_flushes_partial_monitor_tail_instead_of_idle_tone():
    runtime = MediaRuntime(player_factory=_FakePlayer)
    try:
        runtime._audio_sample_rate = 48000
        runtime._audio_channels = 2
        runtime._audio_stream_blocksize = 1024
        runtime._ndi_dispatcher = _CapturingDispatcher()
        runtime._video_destinations["ndi_program"].enabled = True
        runtime._video_destinations["ndi_program"].audio_enabled = True
        runtime._video_destinations["ndi_program"].audio_tap_mode = "pre_fader"
        audio_engine_module.clear_output_monitor_frames()
        audio_engine_module.append_output_monitor_frames(
            "player-a",
            np.ones((600, 2), dtype=np.float32) * 0.375,
            mode="pre_fader",
        )

        runtime._service_ndi_audio_from_render(1024)

        assert len(runtime._ndi_dispatcher.audio_payloads) == 1
        frames, sample_rate = runtime._ndi_dispatcher.audio_payloads[0]
        assert sample_rate == 48000
        assert frames.shape == (600, 2)
        assert np.allclose(frames, np.ones((600, 2), dtype=np.float32) * 0.375)
        assert audio_engine_module.output_monitor_frame_counts("player-a") == {"pre_fader": 0, "post_fader": 0}
    finally:
        audio_engine_module.clear_output_monitor_frames()
        runtime.shutdown()
