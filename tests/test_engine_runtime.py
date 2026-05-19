from __future__ import annotations

import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from pyssp.audio_service import AudioService
import pyssp.engine.runtime as runtime_module
from pyssp.engine import FFmpegEngineServices, MediaRuntime
from pyssp.engine.types import MediaProbeResult


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
        assert runtime._video_destinations["ndi_program"].audio_send_count == 1
    finally:
        runtime.shutdown()


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
        assert call_count["mix"] == 1
        assert call_count["consume"] == 1
        assert runtime._video_destinations["ndi_program"].audio_send_count == 1
    finally:
        runtime.shutdown()
