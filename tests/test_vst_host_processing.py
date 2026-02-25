import numpy as np

from pyssp.vst_host import VSTChainHost


class _FailPlugin:
    def process(self, _audio, _sample_rate, buffer_size=1024, reset=False):
        _ = (buffer_size, reset)
        raise RuntimeError("plugin failed")


class _SamplesFirstPlugin:
    def process(self, audio, _sample_rate, buffer_size=1024, reset=False):
        _ = (_sample_rate, buffer_size, reset)
        return np.asarray(audio, dtype=np.float32).T


class _EmptyOutputPlugin:
    def process(self, audio, _sample_rate, buffer_size=1024, reset=False):
        _ = (_sample_rate, buffer_size, reset)
        arr = np.asarray(audio, dtype=np.float32)
        return np.zeros((arr.shape[0], 0), dtype=np.float32)


class _NaNOutputPlugin:
    def process(self, audio, _sample_rate, buffer_size=1024, reset=False):
        _ = (_sample_rate, buffer_size, reset)
        arr = np.asarray(audio, dtype=np.float32).copy()
        if arr.size > 0:
            arr.flat[0] = np.nan
        return arr


class _EditorPlugin:
    def __init__(self):
        self.opened = False
        self.parameters = {}

    def show_editor(self):
        self.opened = True


def _build_host_with_plugin(plugin):
    host = VSTChainHost(sample_rate=48000, channels=2, block_size=256)
    host._enabled = True
    host._chain = ["plugin"]
    host._chain_enabled = [True]
    host._plugin_cache = {"plugin": plugin}
    return host


def test_process_block_keeps_audio_when_plugin_raises():
    host = _build_host_with_plugin(_FailPlugin())
    block = np.array([[0.1, -0.2], [0.3, -0.4], [0.5, 0.0]], dtype=np.float32)
    out = host.process_block(block)
    np.testing.assert_allclose(out, block)


def test_process_block_handles_samples_first_output():
    host = _build_host_with_plugin(_SamplesFirstPlugin())
    block = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]], dtype=np.float32)
    out = host.process_block(block)
    np.testing.assert_allclose(out, block)


def test_process_block_keeps_audio_when_plugin_returns_empty():
    host = _build_host_with_plugin(_EmptyOutputPlugin())
    block = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]], dtype=np.float32)
    out = host.process_block(block)
    np.testing.assert_allclose(out, block)


def test_process_block_keeps_audio_when_plugin_returns_nan():
    host = _build_host_with_plugin(_NaNOutputPlugin())
    block = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]], dtype=np.float32)
    out = host.process_block(block)
    np.testing.assert_allclose(out, block)


def test_open_plugin_editor_uses_loaded_plugin_instance():
    plugin = _EditorPlugin()
    host = _build_host_with_plugin(plugin)
    state = host.open_plugin_editor("plugin")
    assert plugin.opened is True
    assert state == {}
