from __future__ import annotations

import base64
import select
import shlex
import socket
import threading
import time
import uuid
from typing import Any, Callable, Optional


SatelliteEventFn = Callable[[str, dict[str, Any]], None]


def _parse_bool(raw: object) -> bool:
    value = str(raw or "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _decode_b64(raw: str) -> bytes:
    text = str(raw or "").strip()
    if not text:
        return b""
    padding = (-len(text)) % 4
    if padding:
        text += "=" * padding
    return base64.b64decode(text.encode("ascii"), validate=False)


def _parse_line(raw_line: str) -> tuple[str, dict[str, str], str]:
    text = str(raw_line or "").strip()
    if not text:
        return "", {}, ""
    try:
        tokens = shlex.split(text, posix=True)
    except Exception:
        return "", {}, text
    if not tokens:
        return "", {}, text
    command = str(tokens[0] or "").strip().upper()
    args: dict[str, str] = {}
    for token in tokens[1:]:
        if "=" not in token:
            args[token.upper()] = ""
            continue
        key, value = token.split("=", 1)
        args[str(key or "").strip().upper()] = str(value or "")
    return command, args, text


class CompanionSatelliteClient:
    DEVICE_ID = "pyssp-main"
    PRODUCT_NAME = "pySSP Virtual Satellite"
    SERIAL_PREFIX = "pyssp:"

    @staticmethod
    def default_serial_suffix() -> str:
        return f"{int(uuid.getnode()):012x}"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        columns: int,
        rows: int,
        serial_suffix: str,
        on_event: SatelliteEventFn,
    ) -> None:
        self.host = str(host or "127.0.0.1").strip() or "127.0.0.1"
        self.port = max(1, int(port))
        self.columns = max(1, int(columns))
        self.rows = max(1, int(rows))
        self.serial_suffix = self._normalize_serial_suffix(serial_suffix)
        self._on_event = on_event
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._reconnect_event = threading.Event()
        self._write_lock = threading.Lock()
        self._socket_lock = threading.Lock()
        self._socket: Optional[socket.socket] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return bool(self._running and thread is not None and thread.is_alive())

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._reconnect_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run, name="pyssp-companion-satellite", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        self._reconnect_event.set()
        self._close_socket()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2.0)
        self._thread = None
        self._emit("status", state="stopped", message="")

    def reconnect(self) -> None:
        if not self.is_running:
            self.start()
            return
        self._reconnect_event.set()
        self._close_socket()

    def send_key_press(self, key: int, pressed: bool) -> bool:
        if key < 0:
            return False
        return self._send_line(
            f"KEY-PRESS DEVICEID={self.DEVICE_ID} KEY={int(key)} PRESSED={'true' if pressed else 'false'}"
        )

    def _emit(self, event_type: str, **payload: Any) -> None:
        try:
            self._on_event(event_type, payload)
        except Exception:
            pass

    def _set_socket(self, sock: Optional[socket.socket]) -> None:
        with self._socket_lock:
            self._socket = sock

    def _close_socket(self) -> None:
        with self._socket_lock:
            sock = self._socket
            self._socket = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass

    def _send_line(self, line: str) -> bool:
        payload = (str(line or "").rstrip("\r\n") + "\n").encode("utf-8")
        with self._socket_lock:
            sock = self._socket
        if sock is None:
            return False
        try:
            with self._write_lock:
                sock.sendall(payload)
            return True
        except Exception:
            return False

    def _run(self) -> None:
        reconnect_delay = 2.0
        while not self._stop_event.is_set():
            self._emit("status", state="connecting", message=f"{self.host}:{self.port}")
            try:
                sock = socket.create_connection((self.host, self.port), timeout=5.0)
                sock.settimeout(0.25)
            except Exception as exc:
                self._emit("status", state="disconnected", message=str(exc))
                if self._stop_event.wait(reconnect_delay):
                    break
                continue

            self._set_socket(sock)
            self._reconnect_event.clear()
            self._emit("status", state="connected", message=f"{self.host}:{self.port}")
            try:
                self._connection_loop(sock)
            except Exception as exc:
                if not self._stop_event.is_set():
                    self._emit("status", state="disconnected", message=str(exc))
            finally:
                self._close_socket()
            if self._stop_event.is_set():
                break
            if self._reconnect_event.is_set():
                self._emit("status", state="reconnecting", message=f"{self.host}:{self.port}")
                time.sleep(0.25)
                continue
            self._emit("status", state="disconnected", message="Connection closed.")
            if self._stop_event.wait(reconnect_delay):
                break

    def _connection_loop(self, sock: socket.socket) -> None:
        read_buffer = b""
        last_ping_at = 0.0
        while not self._stop_event.is_set() and not self._reconnect_event.is_set():
            now = time.monotonic()
            if (now - last_ping_at) >= 2.0:
                self._send_line("PING pyssp")
                last_ping_at = now

            try:
                readable, _, _ = select.select([sock], [], [], 0.25)
            except Exception:
                break
            if not readable:
                continue
            chunk = sock.recv(65536)
            if not chunk:
                break
            read_buffer += chunk
            while b"\n" in read_buffer:
                raw_line, read_buffer = read_buffer.split(b"\n", 1)
                line = raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
                self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        command, args, raw = _parse_line(line)
        if not command:
            return
        if command == "BEGIN":
            version = str(args.get("APIVERSION", "") or args.get("ApiVersion", "")).strip()
            self._emit("hello", api_version=version, raw=raw)
            self._register_device()
            return
        if command == "CAPS":
            self._emit("caps", caps={k.lower(): _parse_bool(v) for k, v in args.items()})
            return
        if command == "PING":
            payload = raw.partition(" ")[2]
            self._send_line(f"PONG {payload}".rstrip())
            return
        if command == "KEY-STATE":
            key_index = self._safe_int(args.get("KEY", "-1"), -1)
            if key_index < 0:
                return
            self._emit(
                "key_state",
                key=key_index,
                state={
                    "pressed": _parse_bool(args.get("PRESSED", "0")),
                    "color": str(args.get("COLOR", "") or "").strip(),
                    "text_color": str(args.get("TEXTCOLOR", "") or "").strip(),
                    "text": _decode_b64(str(args.get("TEXT", "") or "")).decode("utf-8", errors="replace"),
                    "font_size": self._safe_int(args.get("FONT_SIZE", "0"), 0),
                    "bitmap": _decode_b64(str(args.get("BITMAP", "") or "")),
                    "location": str(args.get("LOCATION", "") or "").strip(),
                    "type": str(args.get("TYPE", "") or "").strip(),
                },
            )
            return
        if command == "KEYS-CLEAR":
            self._emit("keys_clear")
            return
        if command.endswith("ERROR") or command == "ERROR":
            message = str(args.get("MESSAGE", "") or raw).strip()
            self._emit("status", state="error", message=message)
            return

    @staticmethod
    def _safe_int(raw: object, default: int = 0) -> int:
        try:
            return int(raw)
        except Exception:
            return int(default)

    def _register_device(self) -> None:
        total_keys = max(1, int(self.columns) * int(self.rows))
        command = (
            f'ADD-DEVICE DEVICEID={self.DEVICE_ID} PRODUCT_NAME="{self.PRODUCT_NAME}" '
            f'SERIAL="{self.SERIAL_PREFIX}{self.serial_suffix}" KEYS_TOTAL={total_keys} KEYS_PER_ROW={int(self.columns)} '
            "BITMAPS=72 COLORS=hex TEXT=true TEXT_STYLE=true BRIGHTNESS=false"
        )
        self._send_line(command)

    @staticmethod
    def _normalize_serial_suffix(raw: object) -> str:
        text = str(raw or "").strip().lower()
        if text.startswith("pyssp:"):
            text = text.partition(":")[2].strip().lower()
        cleaned = "".join(ch for ch in text if ch.isalnum() or ch in {"-", "_"})
        return cleaned or CompanionSatelliteClient.default_serial_suffix()
