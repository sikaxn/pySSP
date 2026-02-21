from pyssp import audio_engine


def test_preload_capacity_not_zero_when_memory_metrics_unavailable(monkeypatch):
    monkeypatch.setattr(audio_engine, "_system_memory_bytes", lambda: (0, 0))
    audio_engine.configure_audio_preload_cache_policy(True, 512, True)
    try:
        remaining, effective_limit, used = audio_engine.get_audio_preload_capacity_bytes()
        assert effective_limit > 0
        assert remaining == effective_limit
        assert used == 0
    finally:
        audio_engine.configure_audio_preload_cache_policy(False, 512, True)
