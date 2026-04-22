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


def test_macos_stop_emits_declick_tail_before_silence(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.sys, "platform", "darwin")
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        with player._lock:
            player._declick_frames = 4
            player._state = player.PlayingState
            player._last_output_frame = np.array([0.8, -0.4], dtype=np.float32)
        player.stop()

        out = np.zeros((4, 2), dtype=np.float32)
        player._audio_callback(out, 4, None, None)

        assert np.max(np.abs(out)) > 0.0
        assert abs(float(out[0, 0])) > abs(float(out[-1, 0]))
        assert np.all(np.abs(out[-1, :]) < np.abs(out[0, :]))
    finally:
        player.deleteLater()


def test_macos_seek_applies_declick_tail_then_fade_in(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.sys, "platform", "darwin")
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        with player._lock:
            player._declick_frames = 4
            player._source_frames = np.ones((4096, 2), dtype=np.float32)
            player._duration_ms = 90
            player._state = player.PlayingState
            player._last_output_frame = np.array([1.0, 1.0], dtype=np.float32)

        player.setPosition(20)

        tail = np.zeros((4, 2), dtype=np.float32)
        player._audio_callback(tail, 4, None, None)
        assert abs(float(tail[0, 0])) > abs(float(tail[-1, 0]))

        faded = np.zeros((4, 2), dtype=np.float32)
        player._audio_callback(faded, 4, None, None)
        assert 0.0 < float(faded[0, 0]) < float(faded[-1, 0]) <= 1.0
    finally:
        player.deleteLater()


def test_audio_callback_returns_silence_when_player_lock_is_busy(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        out = np.ones((8, 2), dtype=np.float32)
        player._lock.acquire()
        try:
            player._audio_callback(out, 8, None, None)
        finally:
            player._lock.release()
        assert np.allclose(out, 0.0)
    finally:
        player.deleteLater()


def test_create_stream_uses_safer_defaults_on_macos(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.sys, "platform", "darwin")
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))

    captured = {}

    class _CaptureStream:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            return None

        def stop(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(audio_engine.sd, "OutputStream", lambda **kwargs: _CaptureStream(**kwargs))

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        assert captured["blocksize"] == 2048
        assert captured["latency"] == "high"
    finally:
        player.deleteLater()


def test_set_dsp_config_does_not_wait_for_player_lock(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        player._lock.acquire()
        try:
            player.setDSPConfig(audio_engine.DSPConfig(tempo_pct=5, pitch_pct=3))
        finally:
            player._lock.release()
        assert player._pending_dsp_config is not None
        assert player._pending_dsp_config.tempo_pct == 5
        assert player._pending_dsp_config.pitch_pct == 3
    finally:
        player.deleteLater()


def test_macos_stop_uses_recent_audio_tail_not_repeated_sample(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.sys, "platform", "darwin")
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        with player._lock:
            player._declick_frames = 4
            player._state = player.PlayingState
            player._recent_output_frames = np.array(
                [[0.9, 0.9], [0.7, 0.7], [0.4, 0.4], [0.2, 0.2]],
                dtype=np.float32,
            )
            player._last_output_frame = np.array([0.2, 0.2], dtype=np.float32)
        player.stop()

        out = np.zeros((4, 2), dtype=np.float32)
        player._audio_callback(out, 4, None, None)

        assert np.allclose(out[0, :], [0.9, 0.9], atol=1e-6)
        assert np.allclose(out[-1, :], [0.2 * 0.25, 0.2 * 0.25], atol=1e-6)
    finally:
        player.deleteLater()


def test_read_source_block_uses_fast_slice_when_tempo_is_neutral(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        frames = np.arange(20, dtype=np.float32).reshape(10, 2)
        with player._lock:
            player._source_frames = frames
            player._source_pos = 2.0
            player._dsp_config = audio_engine.DSPConfig()
        block = player._read_source_block_locked(3)
        assert block is not None
        assert np.array_equal(block, frames[2:5])
        assert player._source_pos == 5.0
    finally:
        player.deleteLater()


def test_retain_coreaudio_keepalive_opens_singleton_stream_on_macos(monkeypatch):
    monkeypatch.setattr(audio_engine.sys, "platform", "darwin")
    captured = {"starts": 0, "stops": 0, "closes": 0, "kwargs": []}

    class _KeepAliveStream:
        def __init__(self, **kwargs):
            captured["kwargs"].append(kwargs)

        def start(self):
            captured["starts"] += 1

        def stop(self):
            captured["stops"] += 1

        def close(self):
            captured["closes"] += 1

    monkeypatch.setattr(audio_engine.sd, "OutputStream", lambda **kwargs: _KeepAliveStream(**kwargs))
    audio_engine._shutdown_coreaudio_keepalive()
    try:
        audio_engine._retain_coreaudio_keepalive(44100, 2)
        audio_engine._retain_coreaudio_keepalive(44100, 2)
        assert captured["starts"] == 1
        assert len(captured["kwargs"]) == 1
        assert captured["kwargs"][0]["latency"] == "high"
        assert captured["kwargs"][0]["blocksize"] == 2048
        audio_engine._release_coreaudio_keepalive()
        assert captured["stops"] == 0
        audio_engine._release_coreaudio_keepalive()
        assert captured["stops"] == 1
        assert captured["closes"] == 1
    finally:
        audio_engine._shutdown_coreaudio_keepalive()


def test_set_media_clears_previous_stop_tail_before_new_file(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    prepared_frames = np.zeros((128, 2), dtype=np.float32)

    def _prepare(_file_path, _sample_rate, _channels, dsp_config=None):
        _ = dsp_config
        return prepared_frames, 10, False, None

    monkeypatch.setattr(audio_engine, "_prepare_media_source", _prepare)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        with player._lock:
            player._declick_tail = np.ones((8, 2), dtype=np.float32)
            player._recent_output_frames = np.ones((8, 2), dtype=np.float32)
            player._last_output_frame = np.ones((2,), dtype=np.float32)
        player.setMedia("demo.mp3")
        with player._lock:
            assert len(player._declick_tail) == 0
            assert len(player._recent_output_frames) == 0
            assert np.allclose(player._last_output_frame, 0.0)
    finally:
        player.deleteLater()


def test_first_play_after_media_load_uses_longer_startup_fade_on_macos(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.sys, "platform", "darwin")
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        with player._lock:
            player._declick_frames = 4
            player._startup_fade_frames = 12
            player._fresh_media_fade_frames = 12
            player._fresh_media_start_pending = True
            player._source_frames = np.ones((256, 2), dtype=np.float32)
            player._duration_ms = 100
        player.play()
        with player._lock:
            assert player._declick_fade_in_remaining == 12
            assert player._fresh_media_start_pending is False
    finally:
        player.deleteLater()


def test_mp3_media_load_uses_longer_fresh_start_fade_on_macos(monkeypatch):
    monkeypatch.setattr(audio_engine, "_ensure_decoder", lambda: None)
    monkeypatch.setattr(audio_engine.sys, "platform", "darwin")
    monkeypatch.setattr(audio_engine.pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: _DummyStream())

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    _ = app
    player = audio_engine.ExternalMediaPlayer()
    try:
        with player._lock:
            player._startup_fade_frames = 12
            frames = player._fresh_start_fade_frames_for_media_locked("demo.mp3")
        assert frames >= int(44100 * 0.08)
    finally:
        player.deleteLater()
