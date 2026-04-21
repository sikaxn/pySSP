import os
import threading
import time

import numpy as np
from PyQt5.QtWidgets import QApplication

from pyssp import audio_engine


class _DummyStream:
    def start(self):
        return None

    def stop(self):
        return None

    def close(self):
        return None


class _BlockingDecoder:
    def __init__(self):
        self.entered = threading.Event()
        self.resume = threading.Event()

    def seek(self, _target):
        self.entered.set()
        assert self.resume.wait(1.0)


def _wait_for(predicate, app, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_stream_seek_does_not_report_eof_while_decoder_restarts(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    decoder = _BlockingDecoder()
    try:
        with player._lock:
            player._stream_decoder = decoder
            player._streaming_mode = True
            player._duration_ms = 5000
            player._state = player.PlayingState

        worker = threading.Thread(target=player.setPosition, args=(1200,))
        worker.start()
        assert decoder.entered.wait(1.0)

        with player._lock:
            block, consumed, eof = player._read_stream_block_locked(256)
        assert isinstance(block, np.ndarray)
        assert block.shape == (256, 2)
        assert consumed == 0
        assert eof is False
        assert player.state() == player.PlayingState

        decoder.resume.set()
        worker.join(timeout=1.0)
        assert not worker.is_alive()
        with player._lock:
            assert player._stream_seek_in_progress is False
    finally:
        player.deleteLater()


def test_set_media_async_applies_result_on_qt_thread(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    ready = threading.Event()

    def _prepare(_file_path, _sample_rate, _channels, dsp_config=None):
        assert ready.wait(1.0)
        _ = dsp_config
        frames = np.zeros((4410, 2), dtype=np.float32)
        return frames, 100, False, None

    monkeypatch.setattr(audio_engine, "_prepare_media_source", _prepare)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    completed = []
    try:
        player.mediaLoadFinished.connect(lambda request_id, ok, error: completed.append((request_id, ok, error)))
        request_id = player.setMediaAsync("demo.wav")
        ready.set()
        assert _wait_for(lambda: len(completed) == 1, app)
        assert completed == [(request_id, True, "")]
        assert player.duration() == 100
        assert player.position() == 0
    finally:
        player.deleteLater()


def test_set_media_async_ignores_stale_result_after_stop(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    ready = threading.Event()

    def _prepare(_file_path, _sample_rate, _channels, dsp_config=None):
        assert ready.wait(1.0)
        _ = dsp_config
        frames = np.zeros((4410, 2), dtype=np.float32)
        return frames, 100, False, None

    monkeypatch.setattr(audio_engine, "_prepare_media_source", _prepare)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    completed = []
    try:
        player.mediaLoadFinished.connect(lambda request_id, ok, error: completed.append((request_id, ok, error)))
        _request_id = player.setMediaAsync("demo.wav")
        player.stop()
        ready.set()
        app.processEvents()
        time.sleep(0.05)
        app.processEvents()
        assert completed == []
        assert player.duration() == 0
        assert player.position() == 0
    finally:
        player.deleteLater()
