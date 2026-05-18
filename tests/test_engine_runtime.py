from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal

from pyssp.audio_service import AudioService
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
