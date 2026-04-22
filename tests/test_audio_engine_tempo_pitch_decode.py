from pyssp import audio_engine
from pyssp.dsp import DSPConfig


def test_prepare_media_source_forces_frame_decode_when_tempo_or_pitch_active(monkeypatch):
    calls = {"decoder": 0, "load_frames": 0}

    class _DummyDecoder:
        def start(self, _position_ms):
            calls["decoder"] += 1

    monkeypatch.setattr(audio_engine, "_peek_cached_media_frames", lambda _path: None)
    monkeypatch.setattr(audio_engine, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(audio_engine, "FFmpegPCMStream", lambda *args, **kwargs: _DummyDecoder())
    monkeypatch.setattr(audio_engine, "probe_media_duration_ms", lambda _path: 1000)

    def _load_frames(_path, prefer_ffmpeg=False):
        calls["load_frames"] += 1
        assert prefer_ffmpeg is True
        return "frames", 1000

    monkeypatch.setattr(audio_engine, "_load_media_frames", _load_frames)

    frames, duration_ms, use_streaming, decoder = audio_engine._prepare_media_source(
        "demo.wav",
        48000,
        2,
        dsp_config=DSPConfig(tempo_pct=10.0),
    )

    assert frames == "frames"
    assert duration_ms == 1000
    assert use_streaming is False
    assert decoder is None
    assert calls == {"decoder": 0, "load_frames": 1}
