from __future__ import annotations

from PyQt5 import sip
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

import pytest

from pyssp.audio_service import AudioPlayerProxy, AudioServiceController, AudioStateCache
import pyssp.audio_service as audio_service


class _FakeAudioController(QObject):
    positionChanged = pyqtSignal(str, int)
    durationChanged = pyqtSignal(str, int)
    stateChanged = pyqtSignal(str, int)
    mediaLoadFinished = pyqtSignal(str, int, bool, str)

    def __init__(self) -> None:
        super().__init__()
        self.state_cache = AudioStateCache()
        self.posts: list[tuple[str, str, dict]] = []
        self.calls: list[tuple[str, str, dict | None, float]] = []

    def post(self, player_id: str, command: str, payload: dict | None = None) -> None:
        self.posts.append((str(player_id), str(command), dict(payload or {})))

    def call(self, player_id: str, command: str, payload: dict | None = None, timeout: float = 2.0):
        self.calls.append((str(player_id), str(command), payload, float(timeout)))
        raise AssertionError(f"Unexpected blocking call: {command}")


class _FakeSampledController(_FakeAudioController):
    positionSampled = pyqtSignal(str, int, float)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_audio_service_shutdown_is_repeatable_and_rejects_new_requests(monkeypatch) -> None:
    app = _app()
    controller = AudioServiceController()
    try:
        controller.shutdown()
        assert not controller._thread.isRunning()
        assert sip.isdeleted(controller._service)

        def unexpected_call(*args, **kwargs):
            raise AssertionError("Shutdown requested work from a stopped service")

        with monkeypatch.context() as patch:
            patch.setattr(controller, "call", unexpected_call)
            controller.shutdown()

        with pytest.raises(RuntimeError, match="shut down"):
            controller.call("player-test", "state")
        with pytest.raises(RuntimeError, match="shut down"):
            controller.request_async("player-test", "state").result()
        controller.post("player-test", "play")
        app.processEvents()
    finally:
        controller.shutdown()


def test_proxy_set_media_async_posts_request_without_blocking_call() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    request_id = player.setMediaAsync("song.wav")

    assert request_id >= 1_000_000
    assert controller.calls == []
    assert controller.posts[-1] == (
        "player-test",
        "setMediaAsyncRequest",
        {"file_path": "song.wav", "dsp_config": None, "request_id": request_id},
    )


def test_proxy_hot_state_reads_use_cache_without_blocking_call() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    player.setPosition(1234)
    assert player.position() == 1234
    assert player.enginePositionMs() == 1234
    assert player.meterLevels() == (0.0, 0.0)
    assert controller.calls == []


def test_proxy_engine_clock_advances_between_worker_updates(monkeypatch) -> None:
    _app()
    now = [10.0]
    monkeypatch.setattr(audio_service.time, "perf_counter", lambda: now[0])
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-clock")
    player._on_position_changed("player-clock", 1000)
    player._on_state_changed("player-clock", player.PlayingState)
    now[0] += 0.05
    assert player.enginePositionMs() == 1050
    player.pause()
    now[0] += 0.5
    assert player.enginePositionMs() == 1050


def test_delayed_worker_samples_keep_display_clock_current(monkeypatch) -> None:
    _app()
    now = [10.0]
    monkeypatch.setattr(audio_service.time, "perf_counter", lambda: now[0])
    controller = _FakeSampledController()
    player = AudioPlayerProxy(controller, "player-clock")
    player._on_state_changed("player-clock", player.PlayingState)

    now[0] = 11.0
    controller.positionSampled.emit("player-clock", 500, 10.5)
    assert player.enginePositionMs() == 1000
    controller.positionSampled.emit("player-clock", 900, 10.9)
    assert 999 <= player.enginePositionMs() <= 1000


def test_proxy_ignores_position_sample_from_before_cue_seek(monkeypatch) -> None:
    _app()
    now = [10.0]
    monkeypatch.setattr(audio_service.time, "perf_counter", lambda: now[0])
    controller = _FakeSampledController()
    player = AudioPlayerProxy(controller, "player-cue")
    player.setPosition(30_000)
    player.play()

    controller.positionSampled.emit("player-cue", 0, 9.9)
    assert player.position() == 30_000

    now[0] = 10.2
    controller.positionSampled.emit("player-cue", 30_100, 10.1)
    assert player.position() == 30_100
    assert player.enginePositionMs() == 30_200


def test_proxy_set_media_async_supports_structured_utility_source() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    source = {
        "source_type": "utility",
        "utility_spec": {"mode": "blank", "duration_ms": 5000},
    }
    request_id = player.setMediaAsync(source)

    assert controller.calls == []
    assert controller.posts[-1] == (
        "player-test",
        "setMediaAsyncRequest",
        {"source": source, "file_path": "", "dsp_config": None, "request_id": request_id},
    )
