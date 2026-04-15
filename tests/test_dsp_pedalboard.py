import numpy as np

from pyssp import dsp


def test_realtime_dsp_processor_uses_optional_pedalboard_rack(monkeypatch):
    calls = {"loaded": [], "processed": 0}

    class _FakeRack:
        def __init__(self, plugins):
            self.plugins = list(plugins)

        def __call__(self, block, sample_rate, reset=False):
            _ = (sample_rate, reset)
            calls["processed"] += 1
            return block + 0.25

    def _fake_loader(path):
        calls["loaded"].append(path)
        return {"path": path}

    monkeypatch.setattr(dsp, "_load_pedalboard_backend", lambda: (_FakeRack, _fake_loader))

    processor = dsp.RealTimeDSPProcessor(sample_rate=48000, channels=2)
    processor.set_config(dsp.DSPConfig(plugin_paths=["rack/test-plugin.vst3"]))

    block = np.zeros((16, 2), dtype=np.float32)
    out = processor.process_block(block)

    assert calls["loaded"] == ["rack/test-plugin.vst3"]
    assert calls["processed"] == 1
    assert out.shape == block.shape
    assert np.allclose(out, 0.25)
