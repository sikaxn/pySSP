from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import threading
import time
from collections import deque
from typing import Callable, Deque, Optional

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage

from pyssp.ndi_support import NDICapabilityStatus


@dataclass(frozen=True)
class NDIOutputConfig:
    source_name: str
    width: int
    height: int
    fps: float
    audio_enabled: bool


def _fps_fraction(value: float) -> Fraction:
    fps = max(1.0, float(value))
    common = {
        23.976: Fraction(24000, 1001),
        29.97: Fraction(30000, 1001),
        59.94: Fraction(60000, 1001),
    }
    for target, fraction in common.items():
        if abs(fps - target) < 0.02:
            return fraction
    return Fraction(str(fps)).limit_denominator(1000)


class NDIOutputSender:
    def __init__(self, status: NDICapabilityStatus) -> None:
        self._status = status
        self._cyndilib = None
        self._sender_cls = None
        self._video_frame_cls = None
        self._audio_frame_cls = None
        self._audio_reference = None
        self._fourcc = None
        self._sender = None
        self._video_frame = None
        self._audio_frame = None
        self._config: Optional[NDIOutputConfig] = None
        self._initialize_failed = False
        self._audio_format: tuple[int, int, int] = (0, 0, 0)
        self._last_audio_error = ""
        self._last_audio_mode = ""
        self._load_module()

    def _load_module(self) -> None:
        if not self._status.ready:
            return
        try:
            import cyndilib  # type: ignore
            from cyndilib import AudioReference, AudioSendFrame, VideoSendFrame  # type: ignore
            from cyndilib.sender import Sender  # type: ignore
            from cyndilib.wrapper.ndi_structs import FourCC  # type: ignore

            self._cyndilib = cyndilib
            self._sender_cls = Sender
            self._video_frame_cls = VideoSendFrame
            self._audio_frame_cls = AudioSendFrame
            self._audio_reference = AudioReference
            self._fourcc = FourCC
        except Exception:
            self._initialize_failed = True
            self._cyndilib = None

    @property
    def available(self) -> bool:
        return bool(self._status.ready and self._sender_cls is not None and not self._initialize_failed)

    def configure(self, config: NDIOutputConfig) -> bool:
        if not self.available:
            self.stop()
            return False
        normalized = NDIOutputConfig(
            source_name=str(config.source_name or "pyssp-video").strip() or "pyssp-video",
            width=max(2, int(config.width)),
            height=max(2, int(config.height)),
            fps=max(1.0, float(config.fps)),
            audio_enabled=bool(config.audio_enabled),
        )
        if self._config == normalized and self._sender is not None:
            return True
        self.stop()
        try:
            sender = self._sender_cls(
                normalized.source_name,
                clock_video=True,
                clock_audio=bool(normalized.audio_enabled),
            )
            video_frame = self._video_frame_cls()
            video_frame.set_resolution(normalized.width, normalized.height)
            video_frame.set_frame_rate(_fps_fraction(normalized.fps))
            video_frame.set_fourcc(self._fourcc.BGRX)
            try:
                video_frame.set_progressive(True)
            except Exception:
                pass
            sender.set_video_frame(video_frame)
            audio_frame = None
            if normalized.audio_enabled:
                audio_frame = self._create_audio_frame(
                    sample_rate=48000,
                    channels=2,
                    sample_count=max(1, int(round(48000.0 / normalized.fps))),
                )
                sender.set_audio_frame(audio_frame)
            sender.open()
            self._sender = sender
            self._video_frame = video_frame
            self._audio_frame = audio_frame
            self._config = normalized
            self._last_audio_error = ""
            self._last_audio_mode = ""
            return True
        except Exception as exc:
            self._initialize_failed = True
            self._last_audio_error = f"{type(exc).__name__}: {exc}"
            self._sender = None
            self._video_frame = None
            self._audio_frame = None
            self._config = None
            return False

    def _create_audio_frame(self, *, sample_rate: int, channels: int, sample_count: int):
        frame = self._audio_frame_cls()
        frame.sample_rate = max(1, int(sample_rate))
        frame.num_channels = max(1, int(channels))
        frame.reference_level = self._audio_reference.dBVU
        frame.set_max_num_samples(max(1, int(sample_count)))
        self._audio_format = (frame.sample_rate, frame.num_channels, frame.max_num_samples)
        return frame

    def _ensure_audio_frame(self, *, sample_rate: int, channels: int, sample_count: int) -> bool:
        if self._sender is None or self._config is None or not self._config.audio_enabled:
            return False
        current_rate, current_channels, current_capacity = self._audio_format
        if (
            self._audio_frame is not None
            and current_rate == sample_rate
            and current_channels == channels
            and current_capacity >= sample_count
        ):
            return True
        try:
            frame = self._create_audio_frame(
                sample_rate=sample_rate,
                channels=channels,
                sample_count=sample_count,
            )
            self._sender.set_audio_frame(frame)
            self._audio_frame = frame
            return True
        except Exception as exc:
            self._last_audio_error = f"{type(exc).__name__}: {exc}"
            return False

    def stop(self) -> None:
        sender = self._sender
        self._sender = None
        self._video_frame = None
        self._audio_frame = None
        self._config = None
        self._audio_format = (0, 0, 0)
        if sender is None:
            return
        try:
            sender.close()
        except Exception:
            pass

    def get_num_connections(self, timeout: float = 0.0) -> int:
        sender = self._sender
        if sender is None:
            return 0
        try:
            return max(0, int(sender.get_num_connections(float(timeout))))
        except Exception:
            return 0

    def send_video_frame(self, image: QImage) -> bool:
        if self._sender is None or self._config is None or image.isNull():
            return False
        converted = image.convertToFormat(QImage.Format_RGB32)
        width = max(1, int(converted.width()))
        height = max(1, int(converted.height()))
        if width != self._config.width or height != self._config.height:
            converted = converted.scaled(
                self._config.width,
                self._config.height,
                Qt.IgnoreAspectRatio,
                Qt.FastTransformation,
            )
        ptr = converted.bits()
        ptr.setsize(converted.byteCount())
        data = np.frombuffer(ptr, dtype=np.uint8).copy()
        try:
            return bool(self._sender.write_video_async(data))
        except Exception:
            return False

    def send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool:
        if self._sender is None or self._config is None or (not self._config.audio_enabled):
            self._last_audio_error = "sender unavailable"
            return False
        block = np.asarray(frames, dtype=np.float32)
        if block.ndim != 2 or len(block) <= 0:
            self._last_audio_error = "invalid audio block"
            return False
        channels = int(block.shape[1])
        if channels <= 0:
            self._last_audio_error = "invalid channel count"
            return False
        if not self._ensure_audio_frame(
            sample_rate=max(1, int(sample_rate)),
            channels=channels,
            sample_count=max(1, int(block.shape[0])),
        ):
            return False
        payload = np.ascontiguousarray(block.T, dtype=np.float32)
        try:
            ok = bool(self._sender.write_audio(payload))
            self._last_audio_mode = "cyndilib_write_audio"
            self._last_audio_error = "" if ok else "write_audio returned False"
            return ok
        except Exception as exc:
            self._last_audio_error = f"{type(exc).__name__}: {exc}"
            return False


class NDIOutputDispatcher:
    def __init__(
        self,
        status: NDICapabilityStatus,
        *,
        sender_factory: Optional[Callable[[NDICapabilityStatus], NDIOutputSender]] = None,
        connection_poll_interval_sec: float = 0.25,
        max_audio_queue_blocks: int = 12,
    ) -> None:
        self._status = status
        self._sender = (sender_factory or NDIOutputSender)(status)
        self._condition = threading.Condition()
        self._sender_lock = threading.RLock()
        self._stop_thread = False
        self._disable_sender = False
        self._pending_config: Optional[NDIOutputConfig] = None
        self._config_dirty = False
        self._pending_video_frame: Optional[QImage] = None
        self._pending_audio_blocks: Deque[tuple[np.ndarray, int]] = deque()
        self._max_audio_queue_blocks = max(1, int(max_audio_queue_blocks))
        self._connection_poll_interval_sec = max(0.05, float(connection_poll_interval_sec))
        self._connection_count = 0
        self._last_audio_error = ""
        self._last_audio_mode = ""
        self._thread = threading.Thread(target=self._worker_loop, name="pyssp-ndi-output", daemon=True)
        self._thread.start()

    @property
    def available(self) -> bool:
        return bool(getattr(self._sender, "available", False))

    def configure(self, config: NDIOutputConfig) -> bool:
        if not self.available:
            self.stop()
            return False
        normalized = NDIOutputConfig(
            source_name=str(config.source_name or "pyssp-video").strip() or "pyssp-video",
            width=max(2, int(config.width)),
            height=max(2, int(config.height)),
            fps=max(1.0, float(config.fps)),
            audio_enabled=bool(config.audio_enabled),
        )
        with self._condition:
            self._pending_config = normalized
            self._config_dirty = True
            self._disable_sender = False
            self._condition.notify_all()
        return True

    def stop(self) -> None:
        with self._condition:
            self._disable_sender = True
            self._pending_config = None
            self._config_dirty = False
            self._pending_video_frame = None
            self._pending_audio_blocks.clear()
            self._condition.notify_all()

    def shutdown(self) -> None:
        with self._condition:
            self._stop_thread = True
            self._condition.notify_all()
        self._thread.join(timeout=2.0)
        try:
            with self._sender_lock:
                self._sender.stop()
        except Exception:
            pass
        self._sync_public_state()

    def get_num_connections(self, timeout: float = 0.0) -> int:
        _ = timeout
        return max(0, int(self._connection_count))

    def send_video_frame(self, image: QImage) -> bool:
        if not self.available or image.isNull():
            return False
        with self._condition:
            self._pending_video_frame = image.copy()
            self._condition.notify_all()
        return True

    def send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool:
        if not self.available:
            self._last_audio_error = "sender unavailable"
            return False
        block = np.asarray(frames, dtype=np.float32)
        if block.ndim != 2 or len(block) <= 0:
            self._last_audio_error = "invalid audio block"
            return False
        try:
            with self._sender_lock:
                ok = bool(self._sender.send_audio_frames(np.ascontiguousarray(block, dtype=np.float32), max(1, int(sample_rate))))
        except Exception as exc:
            self._last_audio_error = f"{type(exc).__name__}: {exc}"
            return False
        self._sync_public_state()
        return bool(ok)

    def _sync_public_state(self) -> None:
        self._last_audio_error = str(getattr(self._sender, "_last_audio_error", "") or "")
        self._last_audio_mode = str(getattr(self._sender, "_last_audio_mode", "") or "")

    def _worker_loop(self) -> None:
        last_connection_poll = 0.0
        while True:
            with self._condition:
                while not self._stop_thread:
                    if (
                        self._disable_sender
                        or self._config_dirty
                        or self._pending_video_frame is not None
                    ):
                        break
                    self._condition.wait(timeout=self._connection_poll_interval_sec)
                if self._stop_thread:
                    break
                disable_sender = self._disable_sender
                self._disable_sender = False
                config = self._pending_config if self._config_dirty else None
                self._config_dirty = False
                video_frame = self._pending_video_frame
                self._pending_video_frame = None
            if disable_sender:
                try:
                    with self._sender_lock:
                        self._sender.stop()
                except Exception:
                    pass
                self._connection_count = 0
                self._sync_public_state()
            if config is not None:
                try:
                    with self._sender_lock:
                        self._sender.configure(config)
                except Exception:
                    pass
                self._sync_public_state()
            if video_frame is not None:
                try:
                    with self._sender_lock:
                        self._sender.send_video_frame(video_frame)
                except Exception:
                    pass
                self._sync_public_state()
            now = time.perf_counter()
            if (now - last_connection_poll) >= self._connection_poll_interval_sec:
                last_connection_poll = now
                try:
                    with self._sender_lock:
                        self._connection_count = max(0, int(self._sender.get_num_connections(0.0)))
                except Exception:
                    self._connection_count = 0
                self._sync_public_state()


__all__ = ["NDIOutputConfig", "NDIOutputDispatcher", "NDIOutputSender"]
