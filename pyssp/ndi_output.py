from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import sys
import threading
import time
from typing import Callable, Optional

import numpy as np
from PyQt5.QtGui import QImage

from pyssp.ndi_runtime import NDIRuntimeError, NDIRuntimeSenderConfig, NDIRuntimeSenderSession
from pyssp.ndi_support import NDICapabilityStatus


def _print_ndi_error(message: str) -> None:
    text = str(message or "").strip()
    if not text:
        return
    try:
        print(f"[pySSP][NDI] {text}", file=sys.stderr, flush=True)
    except Exception:
        pass


@dataclass(frozen=True)
class NDIOutputConfig:
    source_name: str
    width: int
    height: int
    fps: float
    audio_enabled: bool


class NDIOutputSender:
    def __init__(
        self,
        status: NDICapabilityStatus,
        *,
        session_factory: Optional[Callable[[str, NDIRuntimeSenderConfig], NDIRuntimeSenderSession]] = None,
    ) -> None:
        self._status = status
        self._session_factory = session_factory or (lambda path, config: NDIRuntimeSenderSession(path, config))
        self._session: Optional[NDIRuntimeSenderSession] = None
        self._config: Optional[NDIOutputConfig] = None
        self._last_audio_error = ""
        self._last_audio_mode = ""
        self._audio_recovery_count = 0
        self._last_reported_audio_error = ""

    @property
    def available(self) -> bool:
        return bool(self._status.ready and self._status.runtime_library_path)

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
        if self._config == normalized and self._session is not None:
            return True
        self.stop()
        try:
            self._session = self._session_factory(
                str(self._status.runtime_library_path or "").strip(),
                NDIRuntimeSenderConfig(
                    source_name=normalized.source_name,
                    width=normalized.width,
                    height=normalized.height,
                    fps=normalized.fps,
                    audio_enabled=normalized.audio_enabled,
                ),
            )
            self._config = normalized
            self._clear_audio_error()
            return True
        except Exception as exc:
            self._set_audio_error(f"{type(exc).__name__}: {exc}")
            self._session = None
            self._config = None
            return False

    def stop(self) -> None:
        session = self._session
        self._session = None
        self._config = None
        if session is None:
            return
        try:
            session.close()
        except Exception:
            pass

    def get_num_connections(self, timeout: float = 0.0) -> int:
        session = self._session
        if session is None:
            return 0
        try:
            return max(0, int(session.get_num_connections(timeout)))
        except Exception:
            return 0

    def send_video_frame(self, image: QImage) -> bool:
        session = self._session
        if session is None:
            return False
        try:
            return bool(session.send_video_frame(image))
        except Exception:
            return False

    def send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool:
        session = self._session
        if session is None or self._config is None or (not self._config.audio_enabled):
            self._set_audio_error("sender unavailable")
            return False
        block = np.asarray(frames, dtype=np.float32)
        if block.ndim != 2 or len(block) <= 0:
            self._set_audio_error("invalid audio block")
            return False
        ok, error_text = self._try_send_audio(session, block, sample_rate)
        if ok:
            self._last_audio_mode = "runtime_interleaved_32f"
            self._clear_audio_error()
            return True
        if not self._is_recoverable_audio_error(error_text):
            self._set_audio_error(error_text)
            return False
        if not self._recover_audio_sender():
            return False
        session = self._session
        if session is None:
            return False
        ok, error_text = self._try_send_audio(session, block, sample_rate)
        if ok:
            self._last_audio_mode = "runtime_interleaved_32f_recovered"
            self._clear_audio_error()
            return True
        self._set_audio_error(error_text)
        return False

    @staticmethod
    def _try_send_audio(session: NDIRuntimeSenderSession, frames: np.ndarray, sample_rate: int) -> tuple[bool, str]:
        try:
            return bool(session.send_audio_frames(frames, sample_rate)), ""
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    @staticmethod
    def _is_recoverable_audio_error(message: str) -> bool:
        text = str(message or "").strip().lower()
        return (
            "device or resource busy" in text
            or "temporarily unavailable" in text
            or "audio frame format mismatch" in text
            or "sender unavailable" in text
        )

    def _recover_audio_sender(self) -> bool:
        config = self._config
        if config is None:
            return False
        self._audio_recovery_count += 1
        self.stop()
        return self.configure(config)

    def _set_audio_error(self, message: str) -> None:
        text = str(message or "").strip()
        self._last_audio_error = text
        if text and text != self._last_reported_audio_error:
            _print_ndi_error(text)
            self._last_reported_audio_error = text

    def _clear_audio_error(self) -> None:
        self._last_audio_error = ""


class NDIOutputDispatcher:
    def __init__(
        self,
        status: NDICapabilityStatus,
        *,
        sender_factory: Optional[Callable[[NDICapabilityStatus], NDIOutputSender]] = None,
        connection_poll_interval_sec: float = 0.25,
        max_audio_queue_blocks: int = 24,
    ) -> None:
        self._status = status
        self._sender = (sender_factory or NDIOutputSender)(status)
        self._condition = threading.Condition()
        self._audio_condition = threading.Condition()
        self._sender_lock = threading.RLock()
        self._stop_thread = False
        self._disable_sender = False
        self._pending_config: Optional[NDIOutputConfig] = None
        self._config_dirty = False
        self._pending_video_frame: Optional[QImage] = None
        self._pending_audio_blocks: deque[tuple[np.ndarray, int]] = deque()
        self._max_audio_queue_blocks = max(2, int(max_audio_queue_blocks))
        self._connection_poll_interval_sec = max(0.05, float(connection_poll_interval_sec))
        self._sender_configured = False
        self._next_audio_send_at = 0.0
        self._connection_count = 0
        self._last_audio_error = ""
        self._last_audio_mode = ""
        self._audio_send_count = 0
        self._audio_drop_count = 0
        self._audio_recovery_count = 0
        self._last_reported_audio_error = ""
        self._thread = threading.Thread(target=self._worker_loop, name="pyssp-ndi-output", daemon=True)
        self._audio_thread = threading.Thread(target=self._audio_worker_loop, name="pyssp-ndi-audio", daemon=True)
        self._thread.start()
        self._audio_thread.start()

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
            self._sender_configured = False
            self._condition.notify_all()
        with self._audio_condition:
            self._next_audio_send_at = 0.0
            self._audio_condition.notify_all()
        return True

    def stop(self) -> None:
        with self._condition:
            self._disable_sender = True
            self._pending_config = None
            self._config_dirty = False
            self._pending_video_frame = None
            self._sender_configured = False
            self._condition.notify_all()
        with self._audio_condition:
            self._pending_audio_blocks.clear()
            self._next_audio_send_at = 0.0
            self._audio_condition.notify_all()

    def shutdown(self) -> None:
        with self._condition:
            self._stop_thread = True
            self._condition.notify_all()
        with self._audio_condition:
            self._audio_condition.notify_all()
        self._thread.join(timeout=2.0)
        self._audio_thread.join(timeout=2.0)
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
            self._set_audio_error("sender unavailable")
            return False
        block = np.asarray(frames, dtype=np.float32)
        if block.ndim != 2 or len(block) <= 0:
            self._set_audio_error("invalid audio block")
            return False
        payload = np.ascontiguousarray(block, dtype=np.float32)
        with self._audio_condition:
            while len(self._pending_audio_blocks) >= self._max_audio_queue_blocks:
                self._pending_audio_blocks.popleft()
                self._audio_drop_count += 1
            self._pending_audio_blocks.append((payload, max(1, int(sample_rate))))
            self._audio_condition.notify_all()
        return True

    def _sync_public_state(self) -> None:
        sender_error = str(getattr(self._sender, "_last_audio_error", "") or "")
        if sender_error:
            self._set_audio_error(sender_error)
        else:
            self._clear_audio_error()
        self._last_audio_mode = str(getattr(self._sender, "_last_audio_mode", "") or "")
        self._audio_recovery_count = max(0, int(getattr(self._sender, "_audio_recovery_count", 0) or 0))

    def _set_audio_error(self, message: str) -> None:
        text = str(message or "").strip()
        self._last_audio_error = text
        if text and text != self._last_reported_audio_error:
            _print_ndi_error(text)
            self._last_reported_audio_error = text

    def _clear_audio_error(self) -> None:
        self._last_audio_error = ""

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
                self._sender_configured = False
                with self._audio_condition:
                    self._next_audio_send_at = 0.0
                    self._audio_condition.notify_all()
                self._sync_public_state()
            if config is not None:
                configured = False
                try:
                    with self._sender_lock:
                        configured = bool(self._sender.configure(config))
                except Exception:
                    configured = False
                self._sender_configured = configured
                with self._audio_condition:
                    self._next_audio_send_at = 0.0
                    self._audio_condition.notify_all()
                self._sync_public_state()
            if video_frame is not None:
                try:
                    with self._sender_lock:
                        if self._sender_configured:
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

    def _audio_worker_loop(self) -> None:
        while True:
            with self._audio_condition:
                while not self._stop_thread:
                    if (
                        self._disable_sender
                        or self._config_dirty
                        or (not self._sender_configured)
                        or (not self._pending_audio_blocks)
                    ):
                        self._audio_condition.wait(timeout=self._connection_poll_interval_sec)
                        continue
                    frames, sample_rate = self._pending_audio_blocks.popleft()
                    break
                else:
                    return
            interval_sec = 0.0
            try:
                interval_sec = float(len(frames)) / float(max(1, int(sample_rate)))
            except Exception:
                interval_sec = 0.0
            now = time.perf_counter()
            target_send_at = self._next_audio_send_at if self._next_audio_send_at > 0.0 else now
            if target_send_at > now:
                time.sleep(target_send_at - now)
                now = time.perf_counter()
            elif interval_sec > 0.0 and (now - target_send_at) > interval_sec:
                target_send_at = now
            try:
                with self._sender_lock:
                    ok = bool(self._sender.send_audio_frames(frames, sample_rate)) if self._sender_configured else False
            except Exception as exc:
                ok = False
                self._set_audio_error(f"{type(exc).__name__}: {exc}")
            if ok:
                self._audio_send_count += 1
            else:
                self._audio_drop_count += 1
            self._sync_public_state()
            next_send_at = max(target_send_at, now)
            if interval_sec > 0.0:
                next_send_at += interval_sec
            else:
                next_send_at = time.perf_counter()
            with self._audio_condition:
                if self._disable_sender or self._config_dirty or (not self._sender_configured):
                    self._next_audio_send_at = 0.0
                else:
                    self._next_audio_send_at = next_send_at


__all__ = ["NDIOutputConfig", "NDIOutputDispatcher", "NDIOutputSender"]
