from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from PyQt5.QtGui import QImage

from pyssp.ndi_support import NDICapabilityStatus


@dataclass(frozen=True)
class NDIOutputConfig:
    source_name: str
    width: int
    height: int
    fps: float
    audio_enabled: bool


class NDIOutputSender:
    def __init__(self, status: NDICapabilityStatus) -> None:
        self._status = status
        self._ndi = None
        self._sender = None
        self._config: Optional[NDIOutputConfig] = None
        self._initialize_failed = False
        self._load_module()

    def _load_module(self) -> None:
        if not self._status.ready:
            return
        try:
            import NDIlib as ndi  # type: ignore

            self._ndi = ndi
        except Exception:
            self._initialize_failed = True
            self._ndi = None

    @property
    def available(self) -> bool:
        return bool(self._status.ready and self._ndi is not None and not self._initialize_failed)

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
        ndi = self._ndi
        if ndi is None:
            return False
        try:
            if not ndi.initialize():
                self._initialize_failed = True
                return False
            create = ndi.SendCreate()
            create.ndi_name = normalized.source_name
            create.clock_video = True
            create.clock_audio = bool(normalized.audio_enabled)
            self._sender = ndi.send_create(create)
            if self._sender is None:
                return False
            self._config = normalized
            return True
        except Exception:
            self._initialize_failed = True
            self._sender = None
            self._config = None
            return False

    def stop(self) -> None:
        ndi = self._ndi
        sender = self._sender
        self._sender = None
        self._config = None
        if ndi is None or sender is None:
            return
        try:
            ndi.send_destroy(sender)
        except Exception:
            pass
        try:
            ndi.destroy()
        except Exception:
            pass

    def send_video_frame(self, image: QImage) -> bool:
        if self._sender is None or self._config is None or self._ndi is None or image.isNull():
            return False
        ndi = self._ndi
        frame = ndi.VideoFrameV2()
        converted = image.convertToFormat(QImage.Format_RGB32)
        width = max(1, int(converted.width()))
        height = max(1, int(converted.height()))
        ptr = converted.bits()
        ptr.setsize(converted.byteCount())
        data = np.frombuffer(ptr, dtype=np.uint8).reshape((height, converted.bytesPerLine() // 4, 4))[:, :width, :]
        frame.data = np.ascontiguousarray(data)
        frame.FourCC = ndi.FOURCC_VIDEO_TYPE_BGRX
        frame.xres = width
        frame.yres = height
        frame.frame_rate_N = max(1, int(round(float(self._config.fps) * 1000.0)))
        frame.frame_rate_D = 1000
        frame.picture_aspect_ratio = float(width) / float(max(1, height))
        frame.frame_format_type = ndi.FRAME_FORMAT_TYPE_PROGRESSIVE
        try:
            ndi.send_send_video_v2(self._sender, frame)
            return True
        except Exception:
            return False

    def send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool:
        if (
            self._sender is None
            or self._config is None
            or self._ndi is None
            or (not self._config.audio_enabled)
        ):
            return False
        block = np.asarray(frames, dtype=np.float32)
        if block.ndim != 2 or len(block) <= 0:
            return False
        channels = int(block.shape[1])
        if channels <= 0:
            return False
        try:
            if hasattr(self._ndi, "AudioFrameV3") and hasattr(self._ndi, "send_send_audio_v3"):
                audio = self._ndi.AudioFrameV3()
                audio.sample_rate = max(1, int(sample_rate))
                audio.no_channels = channels
                audio.no_samples = max(1, int(block.shape[0]))
                planar = np.ascontiguousarray(block.T, dtype=np.float32)
                audio.data = planar
                audio.channel_stride_in_bytes = int(planar.shape[1] * planar.dtype.itemsize)
                self._ndi.send_send_audio_v3(self._sender, audio)
                return True
            if hasattr(self._ndi, "AudioFrameInterleaved32f") and hasattr(
                self._ndi, "util_send_send_audio_interleaved_32f"
            ):
                audio = self._ndi.AudioFrameInterleaved32f()
                audio.sample_rate = max(1, int(sample_rate))
                audio.no_channels = channels
                audio.no_samples = max(1, int(block.shape[0]))
                audio.data = np.ascontiguousarray(block, dtype=np.float32)
                self._ndi.util_send_send_audio_interleaved_32f(self._sender, audio)
                return True
            audio = self._ndi.AudioFrameV2()
            audio.sample_rate = max(1, int(sample_rate))
            audio.no_channels = channels
            audio.no_samples = max(1, int(block.shape[0]))
            planar = np.ascontiguousarray(block.T, dtype=np.float32)
            audio.data = planar
            audio.channel_stride_in_bytes = int(planar.strides[0])
            self._ndi.send_send_audio_v2(self._sender, audio)
            return True
        except Exception:
            return False


__all__ = ["NDIOutputConfig", "NDIOutputSender"]
