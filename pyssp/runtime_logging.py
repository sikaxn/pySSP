from __future__ import annotations

import logging
import os
import platform
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyssp.settings_store as settings_store
from pyssp.version import get_display_build_id, get_display_version

PLAYBACK_LOG_FILENAME = "pySSPLogFile.txt"
RUNTIME_LOG_FILENAME_PREFIX = "pySSP-runtime"
_QUEUE_MAXSIZE = 5000
_ACTIVE_MANAGER: Optional["RuntimeLogManager"] = None
_ACTIVE_MANAGER_LOCK = threading.Lock()


def get_log_root_dir() -> Path:
    return settings_store.get_settings_path().parent


def get_playback_log_path() -> Path:
    root = get_log_root_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / PLAYBACK_LOG_FILENAME


def get_runtime_log_dir() -> Path:
    path = get_log_root_dir() / "runtimelog"
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_playback_log_entry(enabled: bool, message: str) -> None:
    if (not enabled) or (not str(message or "").strip()):
        return
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp}\t{str(message).strip()}\n"
    try:
        path = get_playback_log_path()
        with open(path, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(line)
    except OSError:
        pass


class _RuntimeLogStream:
    def __init__(self, manager: "RuntimeLogManager", original, stream_name: str) -> None:
        self._manager = manager
        self._original = original
        self._stream_name = stream_name

    def write(self, data) -> int:
        text = "" if data is None else str(data)
        if not text:
            return 0
        try:
            self._original.write(text)
        except Exception:
            pass
        self._manager.capture_stream_text(self._stream_name, text)
        return len(text)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass
        self._manager.flush_stream(self._stream_name)

    def isatty(self) -> bool:
        try:
            return bool(self._original.isatty())
        except Exception:
            return False

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8")

    @property
    def errors(self):
        return getattr(self._original, "errors", "replace")

    def fileno(self) -> int:
        return self._original.fileno()

    def writable(self) -> bool:
        return True

    def __getattr__(self, name: str):
        return getattr(self._original, name)


class _QueueLogHandler(logging.Handler):
    def __init__(self, manager: "RuntimeLogManager") -> None:
        super().__init__(level=logging.NOTSET)
        self._manager = manager

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except Exception:
            message = "<unprintable log record>"
        self._manager.capture_logging_record(record, message)


class RuntimeLogManager:
    def __init__(self, *, limit_mb: int) -> None:
        self.limit_mb = settings_store.clamp_runtime_log_limit_mb(limit_mb)
        self.limit_bytes = int(self.limit_mb) * 1024 * 1024
        self.log_dir = get_runtime_log_dir()
        self.log_path = self.log_dir / f"{RUNTIME_LOG_FILENAME_PREFIX}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        self._queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=_QUEUE_MAXSIZE)
        self._stop_requested = threading.Event()
        self._writer_thread: Optional[threading.Thread] = None
        self._file_handle = None
        self._stdout_original = sys.stdout
        self._stderr_original = sys.stderr
        self._stdout_stream = _RuntimeLogStream(self, self._stdout_original, "stdout")
        self._stderr_stream = _RuntimeLogStream(self, self._stderr_original, "stderr")
        self._stream_lock = threading.Lock()
        self._stream_buffers: dict[str, str] = {"stdout": "", "stderr": ""}
        self._drop_lock = threading.Lock()
        self._dropped_entries = 0
        self._logging_handler = _QueueLogHandler(self)
        self._started = False

    def start(self) -> bool:
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._file_handle = open(self.log_path, "a", encoding="utf-8", buffering=1, errors="replace")
        except Exception as exc:
            try:
                print(f"pySSP runtime logging could not start: {exc}", file=self._stderr_original)
            except Exception:
                pass
            return False
        self._writer_thread = threading.Thread(target=self._writer_loop, name="pyssp-runtime-log", daemon=True)
        self._writer_thread.start()
        sys.stdout = self._stdout_stream
        sys.stderr = self._stderr_stream
        self._logging_handler.setLevel(logging.NOTSET)
        logging.getLogger().addHandler(self._logging_handler)
        logging.captureWarnings(True)
        self._started = True
        self.enqueue_system_line("INFO", "Runtime logging started")
        self.enqueue_system_line("INFO", f"Runtime log path: {self.log_path}")
        self.enqueue_system_line("INFO", f"pySSP version: {get_display_version()}")
        self.enqueue_system_line("INFO", f"pySSP build: {get_display_build_id() or '(none)'}")
        self.enqueue_system_line("INFO", f"Platform: {platform.platform()}")
        self.prune_runtime_logs()
        return True

    def stop(self) -> None:
        if not self._started:
            return
        self.enqueue_system_line("INFO", "Runtime logging stopping")
        self.flush_stream("stdout")
        self.flush_stream("stderr")
        self._started = False
        try:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self._logging_handler)
        except Exception:
            pass
        try:
            logging.captureWarnings(False)
        except Exception:
            pass
        sys.stdout = self._stdout_original
        sys.stderr = self._stderr_original
        self._stop_requested.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._writer_thread is not None:
            self._writer_thread.join(timeout=2.0)
        try:
            if self._file_handle is not None:
                self._file_handle.close()
        except Exception:
            pass
        self._file_handle = None

    def update_limit_mb(self, limit_mb: int) -> None:
        self.limit_mb = settings_store.clamp_runtime_log_limit_mb(limit_mb)
        self.limit_bytes = int(self.limit_mb) * 1024 * 1024
        self.enqueue_system_line("INFO", f"Runtime log limit updated to {self.limit_mb} MB")
        self.prune_runtime_logs()

    def capture_stream_text(self, stream_name: str, text: str) -> None:
        if not self._started:
            return
        normalized = str(text or "")
        if not normalized:
            return
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        with self._stream_lock:
            buffer = self._stream_buffers.get(stream_name, "")
            buffer += normalized
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                self._enqueue(self._format_stream_line(stream_name, line))
            self._stream_buffers[stream_name] = buffer

    def flush_stream(self, stream_name: str) -> None:
        if not self._started:
            return
        with self._stream_lock:
            remaining = self._stream_buffers.get(stream_name, "")
            self._stream_buffers[stream_name] = ""
        if remaining:
            self._enqueue(self._format_stream_line(stream_name, remaining))

    def capture_logging_record(self, record: logging.LogRecord, message: str) -> None:
        if not self._started:
            return
        stamp = datetime.fromtimestamp(record.created)
        text = str(message or "")
        lines = text.splitlines() or [""]
        for line in lines:
            self._enqueue(
                f"{stamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [{record.levelname}] [{record.name}] {line}\n"
            )

    def enqueue_system_line(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self._enqueue(f"{stamp} [{str(level or 'INFO').upper()}] [pyssp.runtime] {str(message or '').strip()}\n")

    def prune_runtime_logs(self) -> None:
        try:
            files: list[tuple[Path, int, float]] = []
            total_bytes = 0
            for path in self.log_dir.iterdir():
                if not path.is_file():
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                files.append((path, int(stat.st_size), float(stat.st_mtime)))
                total_bytes += int(stat.st_size)
            for path, size_bytes, _mtime in sorted(files, key=lambda item: (item[2], item[0].name)):
                if total_bytes <= self.limit_bytes:
                    break
                if path == self.log_path:
                    continue
                try:
                    path.unlink()
                except OSError:
                    continue
                total_bytes -= size_bytes
        except Exception:
            pass

    def _writer_loop(self) -> None:
        while True:
            try:
                payload = self._queue.get(timeout=0.5)
            except queue.Empty:
                self._write_dropped_entry_notice()
                if self._stop_requested.is_set():
                    break
                continue
            if payload is None:
                self._write_dropped_entry_notice()
                if self._stop_requested.is_set():
                    break
                continue
            self._write_dropped_entry_notice()
            try:
                if self._file_handle is not None:
                    self._file_handle.write(payload)
            except Exception:
                pass
        self.prune_runtime_logs()

    def _write_dropped_entry_notice(self) -> None:
        with self._drop_lock:
            dropped = self._dropped_entries
            self._dropped_entries = 0
        if dropped <= 0:
            return
        notice = self._format_stream_line("runtime", f"dropped {dropped} runtime log entries because the queue was full")
        try:
            if self._file_handle is not None:
                self._file_handle.write(notice)
        except Exception:
            pass

    def _enqueue(self, payload: str) -> None:
        if not payload:
            return
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            with self._drop_lock:
                self._dropped_entries += 1

    @staticmethod
    def _format_stream_line(stream_name: str, line: str) -> str:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return f"{stamp} [{stream_name}] {line}\n"


def start_runtime_logging(*, enabled: bool, limit_mb: int) -> Optional[RuntimeLogManager]:
    global _ACTIVE_MANAGER
    if not enabled:
        return None
    with _ACTIVE_MANAGER_LOCK:
        if _ACTIVE_MANAGER is not None:
            _ACTIVE_MANAGER.update_limit_mb(limit_mb)
            return _ACTIVE_MANAGER
        manager = RuntimeLogManager(limit_mb=limit_mb)
        if not manager.start():
            return None
        _ACTIVE_MANAGER = manager
        return manager


def update_runtime_logging_settings(*, enabled: bool, limit_mb: int) -> Optional[RuntimeLogManager]:
    global _ACTIVE_MANAGER
    with _ACTIVE_MANAGER_LOCK:
        if not enabled:
            if _ACTIVE_MANAGER is not None:
                manager = _ACTIVE_MANAGER
                _ACTIVE_MANAGER = None
                manager.stop()
            return None
        if _ACTIVE_MANAGER is None:
            manager = RuntimeLogManager(limit_mb=limit_mb)
            if not manager.start():
                return None
            _ACTIVE_MANAGER = manager
            return manager
        _ACTIVE_MANAGER.update_limit_mb(limit_mb)
        return _ACTIVE_MANAGER


def stop_runtime_logging() -> None:
    global _ACTIVE_MANAGER
    with _ACTIVE_MANAGER_LOCK:
        manager = _ACTIVE_MANAGER
        _ACTIVE_MANAGER = None
    if manager is not None:
        manager.stop()


def current_runtime_log_path() -> Optional[Path]:
    manager = _ACTIVE_MANAGER
    if manager is None:
        return None
    return manager.log_path
