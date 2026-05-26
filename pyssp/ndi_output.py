from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import sys
import threading
import time
from typing import Callable, Optional

import numpy as np
from PyQt5.QtGui import QImage

from pyssp.ndi_debug import apply_ndi_debug_idle_audio_pacing, ndi_debug_print_enabled
from pyssp.ndi_config import NDIAccessManagerSettings, apply_ndi_access_manager_settings
from pyssp.ndi_runtime import NDIRuntimeSenderConfig, NDIRuntimeSenderSession
from pyssp.ndi_support import NDICapabilityStatus


def _print_ndi_error(message: str) -> None:
    if not ndi_debug_print_enabled():
        return
    text = str(message or "").strip()
    if not text:
        return
    try:
        print(f"[pySSP][NDI] {text}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _print_ndi_info(message: str) -> None:
    if not ndi_debug_print_enabled():
        return
    text = str(message or "").strip()
    if not text:
        return
    try:
        print(f"[pySSP][NDI] {text}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _normalize_csv(value: object) -> str:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in str(value or "").replace(";", ",").split(","):
        token = str(raw or "").strip()
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)
    return ",".join(tokens)


def _normalize_adapter_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        text = _normalize_csv(",".join(str(item or "") for item in value))
    else:
        text = _normalize_csv(value)
    return tuple(text.split(",")) if text else ()


@dataclass(frozen=True)
class NDIOutputConfig:
    source_name: str
    width: int
    height: int
    fps: float
    audio_enabled: bool
    groups: str = "Public"
    discovery_servers: str = ""
    allowed_adapters: tuple[str, ...] = ()
    multicast_enabled: bool = False
    multicast_ttl: int = 1
    multicast_netmask: str = "255.255.0.0"
    multicast_netprefix: str = "239.255.0.0"


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
        self._last_network_config_error = ""
        self._last_network_config_path = ""
        self._audio_send_count = 0

    @property
    def available(self) -> bool:
        return bool(self._status.ready and self._status.runtime_library_path)

    def configure(self, config: NDIOutputConfig, *, force_restart: bool = False) -> bool:
        if not self.available:
            self.stop()
            return False
        normalized = NDIOutputConfig(
            source_name=str(config.source_name or "pyssp-video").strip() or "pyssp-video",
            width=max(2, int(config.width)),
            height=max(2, int(config.height)),
            fps=max(1.0, float(config.fps)),
            audio_enabled=bool(config.audio_enabled),
            groups=str(config.groups or "Public").strip() or "Public",
            discovery_servers=_normalize_csv(config.discovery_servers),
            allowed_adapters=_normalize_adapter_tuple(config.allowed_adapters),
            multicast_enabled=bool(config.multicast_enabled),
            multicast_ttl=max(1, min(255, int(config.multicast_ttl))),
            multicast_netmask=str(config.multicast_netmask or "255.255.0.0").strip() or "255.255.0.0",
            multicast_netprefix=str(config.multicast_netprefix or "239.255.0.0").strip() or "239.255.0.0",
        )
        if (not force_restart) and self._config == normalized and self._session is not None:
            return True
        _print_ndi_info(
            "configure sender "
            f"name={normalized.source_name!r} "
            f"size={normalized.width}x{normalized.height} "
            f"fps={normalized.fps:.3f} "
            f"audio_enabled={normalized.audio_enabled} "
            f"groups={normalized.groups!r} "
            f"force_restart={force_restart}"
        )
        self.stop()
        self._last_network_config_error = ""
        self._last_network_config_path = ""
        try:
            config_path = apply_ndi_access_manager_settings(
                NDIAccessManagerSettings.normalized(
                    send_groups=normalized.groups,
                    discovery_servers=normalized.discovery_servers,
                    allowed_adapters=normalized.allowed_adapters,
                    multicast_send_enabled=normalized.multicast_enabled,
                    multicast_send_ttl=normalized.multicast_ttl,
                    multicast_send_netmask=normalized.multicast_netmask,
                    multicast_send_netprefix=normalized.multicast_netprefix,
                )
            )
            self._last_network_config_path = str(config_path)
        except Exception as exc:
            self._last_network_config_error = f"{type(exc).__name__}: {exc}"
            _print_ndi_error(f"Unable to update NDI Access Manager config: {self._last_network_config_error}")
        try:
            self._session = self._session_factory(
                str(self._status.runtime_library_path or "").strip(),
                NDIRuntimeSenderConfig(
                    source_name=normalized.source_name,
                    width=normalized.width,
                    height=normalized.height,
                    fps=normalized.fps,
                    audio_enabled=normalized.audio_enabled,
                    groups=normalized.groups,
                ),
            )
            self._config = normalized
            self._clear_audio_error()
            self._audio_send_count = 0
            runtime_version = str(getattr(self._session, "version_text", "") or "").strip() or "unknown"
            _print_ndi_info(
                "sender configured "
                f"name={normalized.source_name!r} "
                f"runtime={runtime_version} "
                f"config_path={self._last_network_config_path or '(none)'}"
            )
            return True
        except Exception as exc:
            self._set_audio_error(f"{type(exc).__name__}: {exc}")
            self._session = None
            self._config = None
            _print_ndi_error(f"sender configure failed: {type(exc).__name__}: {exc}")
            return False

    def stop(self) -> None:
        session = self._session
        self._session = None
        self._config = None
        if session is None:
            return
        _print_ndi_info("sender stop requested")
        try:
            session.close()
        except Exception:
            pass

    def reconfigure_current(self) -> bool:
        config = self._config
        if config is None:
            return False
        return self.configure(config, force_restart=True)

    def get_num_connections(self, timeout: float = 0.0) -> int:
        session = self._session
        if session is None:
            return 0
        try:
            return max(0, int(session.get_num_connections(timeout)))
        except Exception:
            return 0

    def send_video_frame(
        self,
        image: QImage,
        *,
        route_mode: str = "",
        source_path: str = "",
        frame_submit_count: int = 0,
        pts_ms: int = 0,
        source_kind: str = "",
    ) -> bool:
        session = self._session
        if session is None:
            return False
        try:
            return bool(
                self._call_send_video_frame(
                    session,
                    image,
                    route_mode=route_mode,
                    source_path=source_path,
                    frame_submit_count=frame_submit_count,
                    pts_ms=pts_ms,
                    source_kind=source_kind,
                )
            )
        except Exception:
            return False

    @staticmethod
    def _call_send_video_frame(
        target: object,
        image: QImage,
        *,
        route_mode: str,
        source_path: str,
        frame_submit_count: int,
        pts_ms: int,
        source_kind: str,
    ) -> bool:
        send = getattr(target, "send_video_frame", None)
        if not callable(send):
            return False
        try:
            return bool(
                send(
                    image,
                    route_mode=route_mode,
                    source_path=source_path,
                    frame_submit_count=frame_submit_count,
                    pts_ms=pts_ms,
                    source_kind=source_kind,
                )
            )
        except TypeError:
            return bool(send(image))

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
            self._audio_send_count += 1
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
        _print_ndi_info(f"recovering audio sender attempt={self._audio_recovery_count}")
        self.stop()
        return self.configure(config, force_restart=True)

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
        max_audio_queue_blocks: int = 48,
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
        self._pending_video_frame: Optional[tuple[QImage, dict[str, object]]] = None
        self._pending_audio_blocks: deque[tuple[np.ndarray, int, bool]] = deque()
        self._max_audio_queue_blocks = max(2, int(max_audio_queue_blocks))
        self._connection_poll_interval_sec = max(0.05, float(connection_poll_interval_sec))
        self._sender_configured = False
        self._connection_count = 0
        self._last_connection_count = 0
        self._needs_reconnect_rearm = False
        self._last_audio_error = ""
        self._last_audio_mode = ""
        self._audio_send_count = 0
        self._audio_drop_count = 0
        self._audio_recovery_count = 0
        self._last_reported_audio_error = ""
        self._last_network_config_error = ""
        self._last_network_config_path = ""
        self._last_logged_drop_count = 0
        self._last_logged_queue_depth = 0
        self._audio_worker_send_count = 0
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
            groups=str(config.groups or "Public").strip() or "Public",
            discovery_servers=_normalize_csv(config.discovery_servers),
            allowed_adapters=_normalize_adapter_tuple(config.allowed_adapters),
            multicast_enabled=bool(config.multicast_enabled),
            multicast_ttl=max(1, min(255, int(config.multicast_ttl))),
            multicast_netmask=str(config.multicast_netmask or "255.255.0.0").strip() or "255.255.0.0",
            multicast_netprefix=str(config.multicast_netprefix or "239.255.0.0").strip() or "239.255.0.0",
        )
        with self._condition:
            self._pending_config = normalized
            self._config_dirty = True
            self._disable_sender = False
            self._sender_configured = False
            self._needs_reconnect_rearm = False
            self._condition.notify_all()
        with self._audio_condition:
            self._audio_condition.notify_all()
        return True

    def stop(self) -> None:
        with self._condition:
            self._disable_sender = True
            self._pending_config = None
            self._config_dirty = False
            self._pending_video_frame = None
            self._sender_configured = False
            self._needs_reconnect_rearm = False
            self._condition.notify_all()
        with self._audio_condition:
            self._pending_audio_blocks.clear()
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

    def send_video_frame(
        self,
        image: QImage,
        *,
        route_mode: str = "",
        source_path: str = "",
        frame_submit_count: int = 0,
        pts_ms: int = 0,
        source_kind: str = "",
    ) -> bool:
        if not self.available or image.isNull():
            return False
        metadata = {
            "route_mode": str(route_mode or "").strip(),
            "source_path": str(source_path or "").strip(),
            "frame_submit_count": max(0, int(frame_submit_count)),
            "pts_ms": max(0, int(pts_ms)),
            "source_kind": str(source_kind or "").strip(),
        }
        with self._condition:
            self._pending_video_frame = (image.copy(), metadata)
            self._condition.notify_all()
        return True

    def send_audio_frames(self, frames: np.ndarray, sample_rate: int, *, idle: bool = False) -> bool:
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
                if (
                    self._audio_drop_count <= 5
                    or self._audio_drop_count >= (self._last_logged_drop_count + 25)
                ):
                    self._last_logged_drop_count = self._audio_drop_count
                    _print_ndi_error(
                        "audio queue overflow "
                        f"drops={self._audio_drop_count} "
                        f"queued={len(self._pending_audio_blocks)} "
                        f"sample_rate={max(1, int(sample_rate))} "
                        f"shape={tuple(int(value) for value in payload.shape)}"
                    )
            self._pending_audio_blocks.append((payload, max(1, int(sample_rate)), bool(idle)))
            queued = len(self._pending_audio_blocks)
            if (
                queued >= 8
                and (
                    queued > self._last_logged_queue_depth
                    or queued >= (self._last_logged_queue_depth + 4)
                )
            ):
                self._last_logged_queue_depth = queued
                _print_ndi_error(
                    "audio queue depth "
                    f"queued={queued} "
                    f"sample_rate={max(1, int(sample_rate))} "
                    f"shape={tuple(int(value) for value in payload.shape)}"
                )
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
        self._last_network_config_error = str(getattr(self._sender, "_last_network_config_error", "") or "")
        self._last_network_config_path = str(getattr(self._sender, "_last_network_config_path", "") or "")

    def _set_audio_error(self, message: str) -> None:
        text = str(message or "").strip()
        self._last_audio_error = text
        if text and text != self._last_reported_audio_error:
            _print_ndi_error(text)
            self._last_reported_audio_error = text

    def _clear_audio_error(self) -> None:
        self._last_audio_error = ""

    @staticmethod
    def _dispatch_video_frame(
        target: object,
        image: QImage,
        metadata: dict[str, object],
    ) -> bool:
        send = getattr(target, "send_video_frame", None)
        if not callable(send):
            return False
        try:
            return bool(
                send(
                    image,
                    route_mode=str(metadata.get("route_mode", "") or ""),
                    source_path=str(metadata.get("source_path", "") or ""),
                    frame_submit_count=max(0, int(metadata.get("frame_submit_count", 0) or 0)),
                    pts_ms=max(0, int(metadata.get("pts_ms", 0) or 0)),
                    source_kind=str(metadata.get("source_kind", "") or ""),
                )
            )
        except TypeError:
            return bool(send(image))

    def _worker_loop(self) -> None:
        last_connection_poll = 0.0
        while True:
            with self._condition:
                while not self._stop_thread:
                    if self._disable_sender or self._config_dirty or self._pending_video_frame is not None:
                        break
                    self._condition.wait(timeout=self._connection_poll_interval_sec)
                    break
                if self._stop_thread:
                    break
                disable_sender = self._disable_sender
                self._disable_sender = False
                config = self._pending_config if self._config_dirty else None
                self._config_dirty = False
                video_frame_payload = self._pending_video_frame
                self._pending_video_frame = None
            if disable_sender:
                try:
                    with self._sender_lock:
                        self._sender.stop()
                except Exception:
                    pass
                self._connection_count = 0
                self._last_connection_count = 0
                self._sender_configured = False
                self._needs_reconnect_rearm = False
                with self._audio_condition:
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
                self._needs_reconnect_rearm = False
                with self._audio_condition:
                    self._audio_condition.notify_all()
                self._sync_public_state()
            if video_frame_payload is not None:
                video_frame, video_metadata = video_frame_payload
                try:
                    with self._sender_lock:
                        if self._sender_configured:
                            self._dispatch_video_frame(self._sender, video_frame, video_metadata)
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
                if self._last_connection_count > 0 and self._connection_count <= 0:
                    self._needs_reconnect_rearm = True
                elif self._needs_reconnect_rearm and self._connection_count > 0:
                    try:
                        with self._sender_lock:
                            self._sender_configured = bool(self._sender.reconfigure_current())
                    except Exception:
                        self._sender_configured = False
                    with self._audio_condition:
                        self._pending_audio_blocks.clear()
                        self._audio_condition.notify_all()
                    self._needs_reconnect_rearm = False
                    self._sync_public_state()
                self._last_connection_count = int(self._connection_count)
                self._sync_public_state()

    def _audio_worker_loop(self) -> None:
        while True:
            with self._audio_condition:
                while not self._stop_thread:
                    if self._disable_sender or self._config_dirty or (not self._sender_configured) or (not self._pending_audio_blocks):
                        self._audio_condition.wait(timeout=self._connection_poll_interval_sec)
                        continue
                    frames, sample_rate, idle = self._pending_audio_blocks.popleft()
                    queue_remaining = len(self._pending_audio_blocks)
                    break
                else:
                    return
            self._audio_worker_send_count += 1
            send_index = int(self._audio_worker_send_count)
            if (
                send_index <= 5
                or queue_remaining >= 8
                or (send_index % 100) == 0
            ):
                _print_ndi_info(
                    "audio worker send start "
                    f"count={send_index} "
                    f"queued_remaining={queue_remaining} "
                    f"sample_rate={int(sample_rate)} "
                    f"shape={tuple(int(value) for value in frames.shape)}"
                )
            send_started = time.perf_counter()
            try:
                if idle:
                    apply_ndi_debug_idle_audio_pacing()
                with self._sender_lock:
                    ok = bool(self._sender.send_audio_frames(frames, sample_rate)) if self._sender_configured else False
            except Exception as exc:
                ok = False
                self._set_audio_error(f"{type(exc).__name__}: {exc}")
            elapsed_ms = max(0.0, (time.perf_counter() - send_started) * 1000.0)
            if (
                send_index <= 5
                or queue_remaining >= 8
                or elapsed_ms >= 10.0
                or (send_index % 100) == 0
            ):
                _print_ndi_info(
                    "audio worker send done "
                    f"count={send_index} "
                    f"ok={ok} "
                    f"elapsed_ms={elapsed_ms:.3f} "
                    f"queued_remaining={queue_remaining}"
                )
            if ok:
                self._audio_send_count += 1
            else:
                self._audio_drop_count += 1
            self._sync_public_state()


__all__ = ["NDIOutputConfig", "NDIOutputDispatcher", "NDIOutputSender"]
