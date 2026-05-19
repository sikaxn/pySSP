from __future__ import annotations

import ctypes
import os
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage


_NDI_SEND_TIMECODE_SYNTHESIZE = (1 << 63) - 1
_NDI_FRAME_FORMAT_PROGRESSIVE = 1


def _fourcc(ch0: str, ch1: str, ch2: str, ch3: str) -> int:
    return (
        ord(ch0)
        | (ord(ch1) << 8)
        | (ord(ch2) << 16)
        | (ord(ch3) << 24)
    )


_FOURCC_BGRX = _fourcc("B", "G", "R", "X")


class NDIRuntimeError(RuntimeError):
    pass


class _NDIlib_send_create_t(ctypes.Structure):
    _fields_ = [
        ("p_ndi_name", ctypes.c_char_p),
        ("p_groups", ctypes.c_char_p),
        ("clock_video", ctypes.c_bool),
        ("clock_audio", ctypes.c_bool),
    ]


class _NDIlib_video_frame_v2_t(ctypes.Structure):
    _fields_ = [
        ("xres", ctypes.c_int),
        ("yres", ctypes.c_int),
        ("FourCC", ctypes.c_int),
        ("frame_rate_N", ctypes.c_int),
        ("frame_rate_D", ctypes.c_int),
        ("picture_aspect_ratio", ctypes.c_float),
        ("frame_format_type", ctypes.c_int),
        ("timecode", ctypes.c_int64),
        ("p_data", ctypes.POINTER(ctypes.c_uint8)),
        ("line_stride_in_bytes", ctypes.c_int),
        ("p_metadata", ctypes.c_char_p),
        ("timestamp", ctypes.c_int64),
    ]


class _NDIlib_audio_frame_interleaved_32f_t(ctypes.Structure):
    _fields_ = [
        ("sample_rate", ctypes.c_int),
        ("no_channels", ctypes.c_int),
        ("no_samples", ctypes.c_int),
        ("timecode", ctypes.c_int64),
        ("p_data", ctypes.POINTER(ctypes.c_float)),
    ]


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


class _NDIRuntimeLibrary:
    _instances: dict[str, "_NDIRuntimeLibrary"] = {}
    _instances_lock = threading.RLock()

    @classmethod
    def acquire(cls, library_path: str) -> "_NDIRuntimeLibrary":
        candidate = str(library_path or "").strip()
        if not candidate:
            raise NDIRuntimeError("NDI runtime library path is empty.")
        with cls._instances_lock:
            instance = cls._instances.get(candidate)
            if instance is None:
                instance = cls(candidate)
                cls._instances[candidate] = instance
            instance._refcount += 1
            return instance

    def __init__(self, library_path: str) -> None:
        self.library_path = str(library_path)
        self._refcount = 0
        self._lock = threading.RLock()
        self._dll_directory = None
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            dll_dir = str(os.path.dirname(self.library_path) or "").strip()
            if dll_dir:
                try:
                    self._dll_directory = os.add_dll_directory(dll_dir)
                except Exception:
                    self._dll_directory = None
        try:
            self._dll = ctypes.CDLL(self.library_path)
        except Exception as exc:
            raise NDIRuntimeError(f"Unable to load NDI runtime library: {exc}") from exc
        self._bind()
        if not bool(self._dll.NDIlib_initialize()):
            raise NDIRuntimeError("NDIlib_initialize failed.")
        version_ptr = self._dll.NDIlib_version()
        try:
            self.version_text = str(version_ptr.decode("utf-8", errors="ignore") if version_ptr else "").strip()
        except Exception:
            self.version_text = ""

    def _bind(self) -> None:
        self._dll.NDIlib_initialize.argtypes = []
        self._dll.NDIlib_initialize.restype = ctypes.c_bool
        self._dll.NDIlib_destroy.argtypes = []
        self._dll.NDIlib_destroy.restype = None
        self._dll.NDIlib_version.argtypes = []
        self._dll.NDIlib_version.restype = ctypes.c_char_p
        self._dll.NDIlib_send_create.argtypes = [ctypes.POINTER(_NDIlib_send_create_t)]
        self._dll.NDIlib_send_create.restype = ctypes.c_void_p
        self._dll.NDIlib_send_destroy.argtypes = [ctypes.c_void_p]
        self._dll.NDIlib_send_destroy.restype = None
        self._dll.NDIlib_send_send_video_async_v2.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_NDIlib_video_frame_v2_t),
        ]
        self._dll.NDIlib_send_send_video_async_v2.restype = None
        self._dll.NDIlib_send_get_no_connections.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self._dll.NDIlib_send_get_no_connections.restype = ctypes.c_int
        self._dll.NDIlib_util_send_send_audio_interleaved_32f.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_NDIlib_audio_frame_interleaved_32f_t),
        ]
        self._dll.NDIlib_util_send_send_audio_interleaved_32f.restype = None

    def release(self) -> None:
        with self._instances_lock:
            self._refcount = max(0, int(self._refcount) - 1)
            if self._refcount > 0:
                return
            try:
                self._dll.NDIlib_destroy()
            except Exception:
                pass
            if self._dll_directory is not None:
                try:
                    self._dll_directory.close()
                except Exception:
                    pass
                self._dll_directory = None
            self._instances.pop(self.library_path, None)


@dataclass(frozen=True)
class NDIRuntimeSenderConfig:
    source_name: str
    width: int
    height: int
    fps: float
    audio_enabled: bool


class NDIRuntimeSenderSession:
    def __init__(self, library_path: str, config: NDIRuntimeSenderConfig) -> None:
        self._runtime = _NDIRuntimeLibrary.acquire(library_path)
        self._lock = threading.RLock()
        self._config = NDIRuntimeSenderConfig(
            source_name=str(config.source_name or "pyssp-video").strip() or "pyssp-video",
            width=max(2, int(config.width)),
            height=max(2, int(config.height)),
            fps=max(1.0, float(config.fps)),
            audio_enabled=bool(config.audio_enabled),
        )
        self._name_bytes = self._config.source_name.encode("utf-8", errors="ignore")
        self._sender = self._create_sender()
        self._video_payload: Optional[np.ndarray] = None
        self._video_frame = self._build_video_frame()

    @property
    def version_text(self) -> str:
        return str(getattr(self._runtime, "version_text", "") or "").strip()

    def _create_sender(self):
        create_desc = _NDIlib_send_create_t(
            p_ndi_name=self._name_bytes,
            p_groups=None,
            clock_video=False,
            clock_audio=True,
        )
        sender = self._runtime._dll.NDIlib_send_create(ctypes.byref(create_desc))
        if not sender:
            raise NDIRuntimeError("NDIlib_send_create returned null.")
        return sender

    def _build_video_frame(self) -> _NDIlib_video_frame_v2_t:
        rate = _fps_fraction(self._config.fps)
        return _NDIlib_video_frame_v2_t(
            xres=max(2, int(self._config.width)),
            yres=max(2, int(self._config.height)),
            FourCC=int(_FOURCC_BGRX),
            frame_rate_N=int(rate.numerator),
            frame_rate_D=int(rate.denominator),
            picture_aspect_ratio=float(self._config.width) / float(max(1, self._config.height)),
            frame_format_type=int(_NDI_FRAME_FORMAT_PROGRESSIVE),
            timecode=int(_NDI_SEND_TIMECODE_SYNTHESIZE),
            p_data=None,
            line_stride_in_bytes=max(2, int(self._config.width)) * 4,
            p_metadata=None,
            timestamp=0,
        )

    def close(self) -> None:
        with self._lock:
            sender = self._sender
            self._sender = None
            if sender:
                try:
                    self._runtime._dll.NDIlib_send_send_video_async_v2(sender, None)
                except Exception:
                    pass
                try:
                    self._runtime._dll.NDIlib_send_destroy(sender)
                except Exception:
                    pass
            self._video_payload = None
        self._runtime.release()

    def get_num_connections(self, timeout: float = 0.0) -> int:
        sender = self._sender
        if not sender:
            return 0
        try:
            return max(0, int(self._runtime._dll.NDIlib_send_get_no_connections(sender, int(max(0.0, float(timeout)) * 1000.0))))
        except Exception:
            return 0

    def send_video_frame(self, image: QImage) -> bool:
        if image.isNull() or not self._sender:
            return False
        converted = image.convertToFormat(QImage.Format_RGB32)
        if converted.width() != self._config.width or converted.height() != self._config.height:
            converted = converted.scaled(
                self._config.width,
                self._config.height,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
        ptr = converted.bits()
        ptr.setsize(converted.byteCount())
        payload = np.frombuffer(ptr, dtype=np.uint8).copy()
        with self._lock:
            if not self._sender:
                return False
            self._video_payload = payload
            self._video_frame.xres = int(converted.width())
            self._video_frame.yres = int(converted.height())
            self._video_frame.picture_aspect_ratio = float(converted.width()) / float(max(1, converted.height()))
            self._video_frame.line_stride_in_bytes = int(converted.bytesPerLine())
            self._video_frame.p_data = payload.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
            self._runtime._dll.NDIlib_send_send_video_async_v2(self._sender, ctypes.byref(self._video_frame))
        return True

    def send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool:
        sender = self._sender
        if sender is None or (not self._config.audio_enabled):
            return False
        block = np.asarray(frames, dtype=np.float32)
        if block.ndim != 2 or len(block) <= 0:
            return False
        payload = np.ascontiguousarray(block, dtype=np.float32)
        frame = _NDIlib_audio_frame_interleaved_32f_t(
            sample_rate=max(1, int(sample_rate)),
            no_channels=max(1, int(payload.shape[1])),
            no_samples=max(1, int(payload.shape[0])),
            timecode=int(_NDI_SEND_TIMECODE_SYNTHESIZE),
            p_data=payload.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        )
        with self._lock:
            if self._sender is None:
                return False
            self._runtime._dll.NDIlib_util_send_send_audio_interleaved_32f(self._sender, ctypes.byref(frame))
        return True


def probe_runtime_version(library_path: str) -> str:
    candidate = str(library_path or "").strip()
    if not candidate:
        return ""
    runtime = None
    try:
        runtime = _NDIRuntimeLibrary.acquire(candidate)
        return str(getattr(runtime, "version_text", "") or "").strip()
    except Exception:
        return ""
    finally:
        if runtime is not None:
            runtime.release()
