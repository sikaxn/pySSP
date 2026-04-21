import numpy as np

from pyssp import dsp


class _FakeFilter:
    def __init__(self):
        self.cutoff_frequency_hz = 0.0
        self.gain_db = 0.0
        self.q = 0.0


class _FakeGain:
    def __init__(self):
        self.gain_db = 0.0


class _FakeReverb:
    def __init__(self):
        self.room_size = 0.0
        self.damping = 0.0
        self.wet_level = 0.0
        self.dry_level = 0.0
        self.width = 0.0
        self.freeze_mode = 0.0


class _FakeLimiter:
    def __init__(self):
        self.threshold_db = 0.0
        self.release_ms = 0.0


def test_realtime_dsp_processor_builds_pedalboard_chain(monkeypatch):
    calls = {"loaded": [], "processed": 0, "plugins": []}

    class _FakePedalboard:
        def __init__(self, plugins):
            self.plugins = list(plugins)
            calls["plugins"] = list(plugins)

        def process(self, block, sample_rate, buffer_size=0, reset=False):
            _ = (sample_rate, buffer_size, reset)
            calls["processed"] += 1
            return block + 0.25

        def reset(self):
            return None

    def _fake_loader(path):
        calls["loaded"].append(path)
        return {"path": path}

    backend = dsp._PedalboardBackend(
        Pedalboard=_FakePedalboard,
        Gain=_FakeGain,
        HighShelfFilter=_FakeFilter,
        Limiter=_FakeLimiter,
        LowShelfFilter=_FakeFilter,
        PeakFilter=_FakeFilter,
        Reverb=_FakeReverb,
        load_plugin=_fake_loader,
    )
    monkeypatch.setattr(dsp, "_load_pedalboard_backend", lambda: backend)

    processor = dsp.RealTimeDSPProcessor(sample_rate=48000, channels=2)
    processor.set_config(
        dsp.DSPConfig(
            eq_enabled=True,
            eq_bands=[3, 0, 0, 0, 0, 0, 0, 0, 0, -2],
            reverb_sec=4.0,
            plugin_paths=["rack/test-plugin.vst3"],
        )
    )

    block = np.zeros((16, 2), dtype=np.float32)
    out = processor.process_block(block)

    assert calls["loaded"] == ["rack/test-plugin.vst3"]
    assert calls["processed"] == 1
    assert out.shape == block.shape
    assert np.allclose(out, 0.25)
    assert len(calls["plugins"]) == 6
    assert isinstance(calls["plugins"][0], _FakeGain)
