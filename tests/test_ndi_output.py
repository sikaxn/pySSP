from __future__ import annotations

import json
import subprocess
import sys
import threading
import time

import numpy as np
from PyQt5.QtGui import QImage

from pyssp.ndi_output import NDIOutputConfig, NDIOutputDispatcher, NDIOutputSender
from pyssp.ndi_support import NDICapabilityStatus, probe_ndi_capability


class _FakeSession:
    def __init__(self, _library_path: str, config) -> None:
        self.config = config
        self.video_payloads = []
        self.audio_payloads = []
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def get_num_connections(self, _timeout: float = 0.0) -> int:
        return 1

    def send_video_frame(self, image: QImage) -> bool:
        self.video_payloads.append((int(image.width()), int(image.height())))
        return True

    def send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool:
        self.audio_payloads.append((np.asarray(frames, dtype=np.float32).copy(), int(sample_rate)))
        return True


def _ready_status() -> NDICapabilityStatus:
    return NDICapabilityStatus(
        ndi_backend_name="ndi-runtime",
        ndi_python_available=True,
        ndi_python_version="builtin",
        ndi_module_importable=True,
        ndi_runtime_or_sdk_detected=True,
        availability_reason="ready",
        runtime_library_path="/opt/ndi/libndi.so.6",
        ndi_runtime_version="6.3.1",
    )


def test_ndi_sender_uses_runtime_session_for_audio_and_video():
    sender = NDIOutputSender(_ready_status(), session_factory=lambda path, config: _FakeSession(path, config))

    config = NDIOutputConfig(
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
    )

    assert sender.configure(config) is True
    assert sender._session is not None
    assert sender._session.config.source_name == "pyssp-video"
    assert sender._session.config.width == 1920

    frames = np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    assert sender.send_audio_frames(frames, 48000) is True
    stored_audio, sample_rate = sender._session.audio_payloads[0]
    assert sample_rate == 48000
    assert stored_audio.shape == (2, 2)
    assert np.allclose(stored_audio, frames)

    image = QImage(4, 2, QImage.Format_RGB32)
    image.fill(0x112233)
    assert sender.send_video_frame(image) is True
    assert sender._session.video_payloads == [(4, 2)]


def test_ndi_sender_loopback_audio_round_trip():
    script = r"""
import json
import importlib.util
import numpy as np
from PyQt5.QtGui import QImage
from pyssp.ndi_output import NDIOutputConfig, NDIOutputSender
from pyssp.ndi_support import probe_ndi_capability

result = {'ready': False, 'receiver_available': False, 'configured': False, 'captured': False}
if importlib.util.find_spec('cyndilib.finder') and importlib.util.find_spec('cyndilib.receiver'):
    from cyndilib.finder import Finder
    from cyndilib.receiver import ReceiveFrameType, Receiver
    from cyndilib.audio_frame import AudioRecvFrame

    status = probe_ndi_capability(force_refresh=True)
    result['ready'] = bool(status.ready)
    result['receiver_available'] = True
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
                    sample_count = 1024
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
    if not result["receiver_available"] or not result["ready"]:
        return
    assert result["configured"] is True
    assert result["captured"] is True
    assert result["shape"] == [2, 1024]
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
            self._audio_recovery_count = 0

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
            time.sleep(0.05)
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


def test_ndi_dispatcher_queues_audio_via_backend_thread():
    class _TrackingSender:
        available = True

        def __init__(self, _status) -> None:
            self.audio_calls = 0
            self._last_audio_error = ""
            self._last_audio_mode = ""
            self._audio_recovery_count = 0

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

        deadline = time.time() + 1.0
        while time.time() < deadline and dispatcher._sender.audio_calls <= 0:
            time.sleep(0.01)
        assert dispatcher._sender.audio_calls == 1
        assert dispatcher._last_audio_mode == "ok"
    finally:
        dispatcher.shutdown()


def test_ndi_dispatcher_does_not_add_extra_sleep_pacing():
    class _TrackingSender:
        available = True

        def __init__(self, _status) -> None:
            self.audio_call_times = []
            self._last_audio_error = ""
            self._last_audio_mode = ""
            self._audio_recovery_count = 0

        def configure(self, _config) -> bool:
            return True

        def stop(self) -> None:
            return None

        def get_num_connections(self, _timeout: float = 0.0) -> int:
            return 1

        def send_video_frame(self, _image: QImage) -> bool:
            return True

        def send_audio_frames(self, _frames: np.ndarray, _sample_rate: int) -> bool:
            self.audio_call_times.append(time.perf_counter())
            self._last_audio_mode = "paced"
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

        audio = np.ones((100, 2), dtype=np.float32) * 0.25
        for _ in range(3):
            assert dispatcher.send_audio_frames(audio, 1000) is True

        started = time.perf_counter()
        deadline = time.time() + 1.0
        while time.time() < deadline and len(dispatcher._sender.audio_call_times) < 3:
            time.sleep(0.01)
        assert len(dispatcher._sender.audio_call_times) == 3
        elapsed = dispatcher._sender.audio_call_times[-1] - started
        assert elapsed < 0.25
        assert dispatcher._last_audio_mode == "paced"
    finally:
        dispatcher.shutdown()


def test_ndi_sender_recovers_after_runtime_error():
    class _RecoveringSession(_FakeSession):
        instances = 0

        def __init__(self, library_path: str, config) -> None:
            super().__init__(library_path, config)
            type(self).instances += 1
            self.instance_index = type(self).instances

        def send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool:
            if self.instance_index == 1:
                raise RuntimeError("temporarily unavailable")
            return super().send_audio_frames(frames, sample_rate)

    sender = NDIOutputSender(_ready_status(), session_factory=lambda path, config: _RecoveringSession(path, config))
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
    assert sender._last_audio_mode == "runtime_interleaved_32f_recovered"


def test_ndi_dispatcher_bounds_audio_queue():
    class _TrackingSender:
        available = True

        def __init__(self, _status) -> None:
            self.audio_calls = 0
            self._last_audio_error = ""
            self._last_audio_mode = ""
            self._audio_recovery_count = 0

        def configure(self, _config) -> bool:
            return True

        def stop(self) -> None:
            return None

        def get_num_connections(self, _timeout: float = 0.0) -> int:
            return 1

        def send_video_frame(self, _image: QImage) -> bool:
            return True

        def send_audio_frames(self, _frames: np.ndarray, _sample_rate: int) -> bool:
            time.sleep(0.02)
            self.audio_calls += 1
            self._last_audio_mode = "ok"
            self._last_audio_error = ""
            return True

    dispatcher = NDIOutputDispatcher(
        _ready_status(),
        sender_factory=_TrackingSender,
        connection_poll_interval_sec=0.05,
        max_audio_queue_blocks=2,
    )
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
        for _ in range(5):
            assert dispatcher.send_audio_frames(audio, 48000) is True

        deadline = time.time() + 1.0
        while time.time() < deadline and dispatcher._sender.audio_calls <= 0:
            time.sleep(0.01)
        assert dispatcher._audio_drop_count > 0
    finally:
        dispatcher.shutdown()


def test_ndi_dispatcher_prioritizes_video_when_audio_backlog_exists():
    class _TrackingSender:
        available = True

        def __init__(self, _status) -> None:
            self.order = []
            self._allow_config = threading.Event()
            self._last_audio_error = ""
            self._last_audio_mode = ""
            self._audio_recovery_count = 0

        def configure(self, _config) -> bool:
            self.order.append("configure")
            self._allow_config.wait(timeout=1.0)
            return True

        def stop(self) -> None:
            return None

        def get_num_connections(self, _timeout: float = 0.0) -> int:
            return 1

        def send_video_frame(self, _image: QImage) -> bool:
            self.order.append("video")
            return True

        def send_audio_frames(self, _frames: np.ndarray, _sample_rate: int) -> bool:
            self.order.append("audio")
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
        image = QImage(640, 360, QImage.Format_RGB32)
        image.fill(0x112233)

        for _ in range(3):
            assert dispatcher.send_audio_frames(audio, 48000) is True
        assert dispatcher.send_video_frame(image) is True

        dispatcher._sender._allow_config.set()

        deadline = time.time() + 1.0
        while time.time() < deadline:
            if dispatcher._sender.order.count("video") >= 1 and dispatcher._sender.order.count("audio") >= 1:
                break
            time.sleep(0.01)

        assert dispatcher._sender.order[:3] == ["configure", "video", "audio"]
    finally:
        dispatcher.shutdown()
