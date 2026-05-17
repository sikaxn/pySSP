from __future__ import annotations

from fractions import Fraction
import json
import subprocess
import sys
import time

import numpy as np
from PyQt5.QtGui import QImage

from pyssp.ndi_output import NDIOutputConfig, NDIOutputDispatcher, NDIOutputSender
from pyssp.ndi_support import NDICapabilityStatus, probe_ndi_capability


class _DummyVideoFrame:
    def __init__(self) -> None:
        self.resolution = (0, 0)
        self.frame_rate = None
        self.fourcc = None
        self.progressive = None

    def set_resolution(self, width: int, height: int) -> None:
        self.resolution = (int(width), int(height))

    def set_frame_rate(self, rate) -> None:
        self.frame_rate = rate

    def set_fourcc(self, value) -> None:
        self.fourcc = value

    def set_progressive(self, value: bool) -> None:
        self.progressive = bool(value)


class _DummyAudioFrame:
    def __init__(self) -> None:
        self.sample_rate = 0
        self.num_channels = 0
        self.reference_level = None
        self.max_num_samples = 0

    def set_max_num_samples(self, value: int) -> None:
        self.max_num_samples = int(value)


class _DummySender:
    def __init__(self, name: str, ndi_groups: str = "", clock_video: bool = True, clock_audio: bool = True) -> None:
        self.name = str(name)
        self.clock_video = bool(clock_video)
        self.clock_audio = bool(clock_audio)
        self.video_frame = None
        self.audio_frame = None
        self.opened = False
        self.video_payloads = []
        self.audio_payloads = []

    def set_video_frame(self, frame) -> None:
        self.video_frame = frame

    def set_audio_frame(self, frame) -> None:
        self.audio_frame = frame

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.opened = False

    def write_video_async(self, data) -> bool:
        self.video_payloads.append(np.asarray(data, dtype=np.uint8))
        return True

    def write_audio(self, data) -> bool:
        self.audio_payloads.append(np.asarray(data, dtype=np.float32))
        return True


class _DummyAudioReference:
    dBVU = "dbvu"
    dBFS_smpte = "dbfs"


class _DummyFourCC:
    BGRX = "bgrx"


def _ready_status() -> NDICapabilityStatus:
    return NDICapabilityStatus(
        ndi_backend_name="cyndilib",
        ndi_python_available=True,
        ndi_python_version="0.1.1",
        ndi_module_importable=True,
        ndi_runtime_or_sdk_detected=True,
        availability_reason="ready",
    )


def test_ndi_sender_uses_cyndilib_audio_and_video_shapes():
    sender = NDIOutputSender(_ready_status())
    sender._sender_cls = _DummySender
    sender._video_frame_cls = _DummyVideoFrame
    sender._audio_frame_cls = _DummyAudioFrame
    sender._audio_reference = _DummyAudioReference
    sender._fourcc = _DummyFourCC
    sender._initialize_failed = False

    config = NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )

    assert sender.configure(config) is True
    assert sender._sender is not None
    assert sender._sender.clock_audio is True
    assert sender._sender.video_frame.resolution == (1920, 1080)
    assert sender._sender.video_frame.frame_rate == Fraction(30, 1)
    assert sender._sender.video_frame.fourcc == "bgrx"
    assert sender._sender.audio_frame.reference_level == "dbvu"
    assert sender._sender.audio_frame.max_num_samples >= 8192

    frames = np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    assert sender.send_audio_frames(frames, 48000) is True
    assert len(sender._sender.audio_payloads) == 1
    assert np.allclose(sender._sender.audio_payloads[0], np.asarray([[0.1, 0.3], [0.2, 0.4]], dtype=np.float32))

    image = QImage(4, 2, QImage.Format_RGB32)
    image.fill(0x112233)
    assert sender.send_video_frame(image) is True
    assert len(sender._sender.video_payloads) == 1
    assert sender._sender.video_payloads[0].ndim == 1
    assert sender._sender.video_payloads[0].dtype == np.uint8


def test_ndi_sender_loopback_audio_round_trip():
    script = r"""
import json
import numpy as np
from PyQt5.QtGui import QImage
from pyssp.ndi_output import NDIOutputConfig, NDIOutputSender
from pyssp.ndi_support import probe_ndi_capability
from cyndilib.finder import Finder
from cyndilib.receiver import ReceiveFrameType, Receiver
from cyndilib.audio_frame import AudioRecvFrame

status = probe_ndi_capability(force_refresh=True)
result = {'ready': bool(status.ready), 'configured': False, 'captured': False}
if status.ready:
    sender = NDIOutputSender(status)
    config = NDIOutputConfig(
        source_name='pyssp-audio-loopback-test',
        width=320,
        height=180,
        fps=30.0,
        audio_enabled=True,
    )
    ok = sender.configure(config)
    result['configured'] = bool(ok)
    source = None
    receiver = None
    try:
        with Finder() as finder:
            for _ in range(30):
                finder.wait_for_sources(0.2)
                sources = list(finder.iter_sources())
                for candidate in sources:
                    if getattr(candidate, 'stream_name', '') == config.source_name or config.source_name in str(getattr(candidate, 'name', '')):
                        source = candidate
                        break
                if source is not None:
                    break
            if source is not None:
                receiver = Receiver()
                receiver.connect_to(source)
                recv_audio = AudioRecvFrame()
                receiver.set_audio_frame(recv_audio)
                image = QImage(config.width, config.height, QImage.Format_RGB32)
                image.fill(0)
                sender.send_video_frame(image)
                sample_rate = 48000
                sample_count = int(sample_rate / config.fps)
                for index in range(8):
                    t = (np.arange(sample_count, dtype=np.float32) + (index * sample_count)) / sample_rate
                    frames = np.stack([
                        0.35 * np.sin(2.0 * np.pi * 440.0 * t),
                        0.25 * np.sin(2.0 * np.pi * 660.0 * t),
                    ], axis=1).astype(np.float32)
                    sender.send_audio_frames(frames, sample_rate)
                    frame_type = receiver.receive(ReceiveFrameType.recv_audio, 500)
                    if int(frame_type) != int(ReceiveFrameType.recv_audio):
                        continue
                    payload = recv_audio.get_read_data()
                    if not payload:
                        continue
                    data = payload[0]
                    result['captured'] = True
                    result['shape'] = list(data.shape)
                    result['max'] = float(np.max(np.abs(data))) if data.size else 0.0
                    break
    finally:
        if receiver is not None:
            try:
                receiver.disconnect()
            except Exception:
                pass
        sender.stop()
print(json.dumps(result))
"""
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads((proc.stdout or "").strip().splitlines()[-1])
    if not result["ready"]:
        return
    assert result["configured"] is True
    assert result["captured"] is True
    assert result["shape"] == [2, 1600]
    assert 0.20 < result["max"] < 0.40


def test_ndi_dispatcher_does_not_block_caller_on_slow_backend():
    class _SlowSender:
        available = True

        def __init__(self, _status) -> None:
            self.video_calls = 0
            self.audio_calls = 0
            self.configure_calls = 0
            self._last_audio_error = ""
            self._last_audio_mode = ""

        def configure(self, _config) -> bool:
            self.configure_calls += 1
            return True

        def stop(self) -> None:
            return None

        def get_num_connections(self, _timeout: float = 0.0) -> int:
            return 1

        def send_video_frame(self, _image: QImage) -> bool:
            time.sleep(0.15)
            self.video_calls += 1
            return True

        def send_audio_frames(self, _frames: np.ndarray, _sample_rate: int) -> bool:
            self.audio_calls += 1
            self._last_audio_mode = "slow_sender"
            return True

    dispatcher = NDIOutputDispatcher(_ready_status(), sender_factory=_SlowSender, connection_poll_interval_sec=0.05)
    try:
        config = NDIOutputConfig(
            source_name="pyssp-video",
            width=640,
            height=360,
            fps=30.0,
            audio_enabled=True,
        )
        assert dispatcher.configure(config) is True

        image = QImage(640, 360, QImage.Format_RGB32)
        image.fill(0x112233)
        audio = np.ones((1600, 2), dtype=np.float32) * 0.25

        start = time.perf_counter()
        assert dispatcher.send_video_frame(image) is True
        assert dispatcher.send_audio_frames(audio, 48000) is True
        elapsed = time.perf_counter() - start

        assert elapsed < 0.05

        deadline = time.time() + 1.0
        while time.time() < deadline:
            if dispatcher.get_num_connections() > 0 and dispatcher._last_audio_mode == "slow_sender":
                break
            time.sleep(0.01)
        assert dispatcher.get_num_connections() == 1
        assert dispatcher._last_audio_mode == "slow_sender"
    finally:
        dispatcher.shutdown()


def test_ndi_dispatcher_sends_audio_immediately_via_backend():
    class _TrackingSender:
        available = True

        def __init__(self, _status) -> None:
            self.audio_calls = 0
            self.configure_calls = 0
            self._last_audio_error = ""
            self._last_audio_mode = ""

        def configure(self, _config) -> bool:
            self.configure_calls += 1
            return True

        def stop(self) -> None:
            return None

        def get_num_connections(self, _timeout: float = 0.0) -> int:
            return 1

        def send_video_frame(self, _image: QImage) -> bool:
            return True

        def send_audio_frames(self, _frames: np.ndarray, _sample_rate: int) -> bool:
            self.audio_calls += 1
            self._last_audio_error = ""
            self._last_audio_mode = "ok"
            return True

    dispatcher = NDIOutputDispatcher(_ready_status(), sender_factory=_TrackingSender, connection_poll_interval_sec=0.05)
    try:
        config = NDIOutputConfig(
            source_name="pyssp-video",
            width=640,
            height=360,
            fps=30.0,
            audio_enabled=True,
        )
        assert dispatcher.configure(config) is True

        audio = np.ones((1024, 2), dtype=np.float32) * 0.25
        assert dispatcher.send_audio_frames(audio, 48000) is True

        assert dispatcher._last_audio_mode == "ok"
    finally:
        dispatcher.shutdown()


def test_ndi_sender_recovers_after_buffer_write_item_error():
    class _RecoveringSender:
        instances = 0

        def __init__(self, name: str, ndi_groups: str = "", clock_video: bool = True, clock_audio: bool = True) -> None:
            _ = (name, ndi_groups, clock_video, clock_audio)
            type(self).instances += 1
            self.instance_index = type(self).instances
            self.video_frame = None
            self.audio_frame = None

        def set_video_frame(self, frame) -> None:
            self.video_frame = frame

        def set_audio_frame(self, frame) -> None:
            self.audio_frame = frame

        def open(self) -> None:
            return None

        def close(self) -> None:
            return None

        def get_num_connections(self, _timeout: float = 0.0) -> int:
            return 1

        def write_video_async(self, _data) -> bool:
            return True

        def write_audio(self, data) -> bool:
            _ = data
            if self.instance_index == 1:
                raise RuntimeError("buffer_write_item is not null")
            return True

    sender = NDIOutputSender(_ready_status())
    sender._sender_cls = _RecoveringSender
    sender._video_frame_cls = _DummyVideoFrame
    sender._audio_frame_cls = _DummyAudioFrame
    sender._audio_reference = _DummyAudioReference
    sender._fourcc = _DummyFourCC
    sender._initialize_failed = False

    config = NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )
    assert sender.configure(config) is True

    frames = np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    assert sender.send_audio_frames(frames, 48000) is True
    assert sender._audio_recovery_count == 1
    assert sender._last_audio_mode == "cyndilib_write_audio_recovered"


def test_ndi_sender_audio_capacity_is_not_limited_by_video_fps():
    sender = NDIOutputSender(_ready_status())
    sender._sender_cls = _DummySender
    sender._video_frame_cls = _DummyVideoFrame
    sender._audio_frame_cls = _DummyAudioFrame
    sender._audio_reference = _DummyAudioReference
    sender._fourcc = _DummyFourCC
    sender._initialize_failed = False

    config = NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=60.0,
        audio_enabled=True,
    )

    assert sender.configure(config) is True
    assert sender._sender.audio_frame.max_num_samples >= 8192

    frames = np.ones((1024, 2), dtype=np.float32) * 0.25
    assert sender.send_audio_frames(frames, 48000) is True
    assert len(sender._sender.audio_payloads) == 1
    assert sender._last_audio_error == ""


def test_ndi_dispatcher_throttles_audio_to_realtime():
    class _TrackingSender:
        available = True

        def __init__(self, _status) -> None:
            self.audio_calls = 0
            self._last_audio_error = ""
            self._last_audio_mode = ""

        def configure(self, _config) -> bool:
            return True

        def stop(self) -> None:
            return None

        def get_num_connections(self, _timeout: float = 0.0) -> int:
            return 1

        def send_video_frame(self, _image: QImage) -> bool:
            return True

        def send_audio_frames(self, _frames: np.ndarray, _sample_rate: int) -> bool:
            self.audio_calls += 1
            self._last_audio_mode = "ok"
            self._last_audio_error = ""
            return True

    dispatcher = NDIOutputDispatcher(_ready_status(), sender_factory=_TrackingSender, connection_poll_interval_sec=0.05)
    try:
        config = NDIOutputConfig(
            source_name="pyssp-video",
            width=640,
            height=360,
            fps=30.0,
            audio_enabled=True,
        )
        assert dispatcher.configure(config) is True

        audio = np.ones((1024, 2), dtype=np.float32) * 0.25
        assert dispatcher.send_audio_frames(audio, 48000) is True
        assert dispatcher.send_audio_frames(audio, 48000) is True

        assert dispatcher._sender.audio_calls == 1
        assert dispatcher._audio_drop_count == 1
        assert dispatcher._last_audio_mode == "dispatcher_audio_drop_realtime"
    finally:
        dispatcher.shutdown()
