from __future__ import annotations

import numpy as np

from pyssp.ndi_output import NDIOutputConfig, NDIOutputSender
from pyssp.ndi_support import NDICapabilityStatus


class _DummyAudioFrameInterleaved32f:
    def __init__(self) -> None:
        self.sample_rate = 0
        self.no_channels = 0
        self.no_samples = 0
        self.data = None
        self.timecode = 0


class _DummyAudioFrameV3:
    def __init__(self) -> None:
        self.sample_rate = 0
        self.no_channels = 0
        self.no_samples = 0
        self.data = None
        self.channel_stride_in_bytes = 0
        self.timecode = 0


class _DummyNDI:
    AudioFrameV3 = _DummyAudioFrameV3
    AudioFrameInterleaved32f = _DummyAudioFrameInterleaved32f

    def __init__(self) -> None:
        self.audio_calls = []

    def send_send_audio_v3(self, sender, audio_data) -> None:
        self.audio_calls.append(("v3", sender, audio_data))

    def util_send_send_audio_interleaved_32f(self, sender, audio_data) -> None:
        self.audio_calls.append(("interleaved", sender, audio_data))


def test_ndi_sender_uses_interleaved_float_audio_path():
    sender = NDIOutputSender(
        NDICapabilityStatus(
            ndi_python_available=True,
            ndi_module_importable=True,
            ndi_runtime_or_sdk_detected=True,
            availability_reason="ready",
        )
    )
    sender._ndi = _DummyNDI()
    sender._sender = object()
    sender._config = NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )

    frames = np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)

    assert sender.send_audio_frames(frames, 48000) is True
    assert len(sender._ndi.audio_calls) == 1
    mode, _capsule, frame = sender._ndi.audio_calls[0]
    assert mode == "v3"
    assert frame.sample_rate == 48000
    assert frame.no_channels == 2
    assert frame.no_samples == 2
    assert frame.channel_stride_in_bytes == 8
    assert np.allclose(frame.data, np.asarray([[0.1, 0.3], [0.2, 0.4]], dtype=np.float32))
