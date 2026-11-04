from types import SimpleNamespace

import pytest

from pyssp import audio_engine


@pytest.mark.parametrize("platform, expected", [
    ("linux", (1024, "low")),
    ("win32", (1024, "low")),
    ("darwin", (2048, "high")),
])
def test_existing_output_timing_defaults(monkeypatch, platform, expected):
    monkeypatch.setattr(audio_engine.sys, "platform", platform)
    monkeypatch.delenv("PYSSP_AUDIO_BLOCKSIZE", raising=False)
    monkeypatch.delenv("PYSSP_AUDIO_LATENCY", raising=False)
    assert audio_engine._output_stream_timing() == expected


@pytest.mark.parametrize("blocksize, latency", [
    ("bad", "bad"), ("0", "0"), ("-1", "-1"),
    ("65536", "3"), ("1.5", "nan"), ("", "inf"),
])
def test_invalid_overrides_keep_defaults(monkeypatch, blocksize, latency):
    monkeypatch.setattr(audio_engine.sys, "platform", "linux")
    monkeypatch.setenv("PYSSP_AUDIO_BLOCKSIZE", blocksize)
    monkeypatch.setenv("PYSSP_AUDIO_LATENCY", latency)
    assert audio_engine._output_stream_timing() == (1024, "low")


def test_pi_overrides_reach_output_stream(monkeypatch):
    monkeypatch.setenv("PYSSP_AUDIO_BLOCKSIZE", "2048")
    monkeypatch.setenv("PYSSP_AUDIO_LATENCY", "0.15")
    monkeypatch.setattr(audio_engine, "_REQUESTED_DEVICE", "")
    monkeypatch.setattr(audio_engine.sd, "OutputStream", lambda **kwargs: kwargs)
    player = SimpleNamespace(_sample_rate=44100, _channels=2, _audio_callback=object())
    stream = audio_engine.ExternalMediaPlayer._create_stream(player)
    assert stream["blocksize"] == 2048
    assert stream["latency"] == 0.15
    assert stream["samplerate"] == 44100
    assert stream["callback"] is player._audio_callback
