from __future__ import annotations

import numpy as np
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
        if command == "sampleRate":
            return 48000
        if command == "outputBlockSize":
            return 1024
        if command == "takeOutputFrames":
            return np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        if command == "outputTapFrameCounts":
            return {"pre_fader": 12, "post_fader": 34}
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


def test_proxy_exposes_sample_rate_and_output_tap_frames_via_controller() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    sample_rate = player.sampleRate()
    block_size = player.outputBlockSize()
    frames = player.takeOutputFrames(max_frames=4, mode="pre_fader")

    assert sample_rate == 48000
    assert block_size == 1024
    assert np.allclose(frames, np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32))
    assert controller.calls == [
        ("player-test", "sampleRate", None, 0.5),
        ("player-test", "outputBlockSize", None, 0.5),
        ("player-test", "takeOutputFrames", {"max_frames": 4, "mode": "pre_fader"}, 0.5),
    ]


def test_proxy_exposes_output_tap_frame_counts_via_controller() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    counts = player.outputTapFrameCounts()

    assert counts == {"pre_fader": 12, "post_fader": 34}
    assert controller.calls == [
        ("player-test", "outputTapFrameCounts", None, 0.5),
    ]
