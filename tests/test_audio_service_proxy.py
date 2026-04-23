from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from pyssp.audio_service import AudioPlayerProxy, AudioStateCache


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


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


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
