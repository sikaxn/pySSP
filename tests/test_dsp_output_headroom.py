import numpy as np

from pyssp import dsp


def test_realtime_dsp_processor_normalizes_instead_of_hard_clipping(monkeypatch):
    class _FakeGain:
        def __init__(self):
            self.gain_db = 0.0

    class _FakeLimiter:
        def __init__(self):
            self.threshold_db = 0.0
            self.release_ms = 0.0

    class _FakePedalboard:
        def __init__(self, plugins):
            self.plugins = list(plugins)

        def process(self, block, sample_rate, buffer_size=0, reset=False):
            _ = (sample_rate, buffer_size, reset)
            return np.asarray(block, dtype=np.float32) * 2.0

        def reset(self):
            return None

    backend = dsp._PedalboardBackend(
        Pedalboard=_FakePedalboard,
        Gain=_FakeGain,
        HighShelfFilter=lambda: object(),
        Limiter=_FakeLimiter,
        LowShelfFilter=lambda: object(),
        PeakFilter=lambda: object(),
        Reverb=lambda: object(),
        load_plugin=lambda path: {"path": path},
    )
    monkeypatch.setattr(dsp, "_load_pedalboard_backend", lambda: backend)

    processor = dsp.RealTimeDSPProcessor(sample_rate=48000, channels=2)
    processor.set_config(dsp.DSPConfig(plugin_paths=["rack/test-plugin.vst3"]))

    block = np.full((32, 2), 0.75, dtype=np.float32)
    out = processor.process_block(block)

    assert out.shape == block.shape
    assert float(np.max(np.abs(out))) <= 1.0
    assert np.allclose(out, 1.0)
