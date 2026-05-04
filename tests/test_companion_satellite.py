from __future__ import annotations

import base64
import queue
import socket
import threading
from pathlib import Path

from pyssp.companion_satellite import CompanionSatelliteClient
from pyssp.settings_store import (
    AppSettings,
    default_companion_satellite_serial_suffix,
    load_settings,
    save_settings,
)


class _FakeCompanionServer:
    def __init__(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(1)
        self.host, self.port = self._server.getsockname()
        self._stop_event = threading.Event()
        self.add_device_lines: queue.Queue[str] = queue.Queue()
        self.key_press_lines: queue.Queue[str] = queue.Queue()
        self.change_page_lines: queue.Queue[str] = queue.Queue()
        self._thread = threading.Thread(target=self._run, name="fake-companion-satellite", daemon=True)
        self._conn: socket.socket | None = None

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        try:
            self._server.close()
        except Exception:
            pass
        conn = self._conn
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            conn, _addr = self._server.accept()
        except Exception:
            return
        self._conn = conn
        text_payload = base64.b64encode(b"Hello").decode("ascii")
        with conn:
            conn.sendall(b"BEGIN CompanionVersion=4.2.0 ApiVersion=1.10.0\n")
            conn.sendall(b"CAPS SUBSCRIPTIONS=1 NONSQUARE=1\n")
            buffer = b""
            while not self._stop_event.is_set():
                try:
                    chunk = conn.recv(65536)
                except Exception:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    raw_line, buffer = buffer.split(b"\n", 1)
                    line = raw_line.rstrip(b"\r").decode("utf-8", errors="replace")
                    if line.startswith("PING "):
                        payload = line.partition(" ")[2]
                        conn.sendall(f"PONG {payload}\n".encode("utf-8"))
                    elif line.startswith("ADD-DEVICE "):
                        self.add_device_lines.put(line)
                        conn.sendall(
                            (
                                f"KEY-STATE DEVICEID=pyssp:my-surface KEY=0 PRESSED=0 COLOR=#112233 "
                                f'TEXT="{text_payload}" FONT_SIZE=18\n'
                            ).encode("utf-8")
                        )
                    elif line.startswith("KEY-PRESS "):
                        self.key_press_lines.put(line)
                    elif line.startswith("CHANGE-PAGE "):
                        self.change_page_lines.put(line)


def test_companion_satellite_settings_round_trip(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)
    settings = AppSettings()
    settings.companion_satellite_host = "companion.local"
    settings.companion_satellite_port = 17777
    settings.companion_satellite_enabled = True
    settings.companion_satellite_columns = 7
    settings.companion_satellite_rows = 4
    settings.companion_satellite_render_mode = "styled"
    settings.companion_satellite_serial_suffix = "my-surface"
    save_settings(settings)
    loaded = load_settings()
    assert loaded.companion_satellite_host == "companion.local"
    assert loaded.companion_satellite_port == 17777
    assert loaded.companion_satellite_enabled is True
    assert loaded.companion_satellite_columns == 7
    assert loaded.companion_satellite_rows == 4
    assert loaded.companion_satellite_render_mode == "styled"
    assert loaded.companion_satellite_serial_suffix == "my-surface"


def test_companion_satellite_defaults_use_machine_serial_and_8x4_layout():
    settings = AppSettings()
    assert settings.companion_satellite_columns == 8
    assert settings.companion_satellite_rows == 4
    assert settings.companion_satellite_render_mode == "bitmap"
    assert settings.companion_satellite_serial_suffix == default_companion_satellite_serial_suffix()


def test_companion_satellite_client_registers_surface_and_sends_key_presses():
    server = _FakeCompanionServer()
    server.start()
    events: queue.Queue[tuple[str, dict]] = queue.Queue()
    client = CompanionSatelliteClient(
        host=server.host,
        port=server.port,
        columns=5,
        rows=4,
        serial_suffix="my-surface",
        on_event=lambda event_type, payload: events.put((event_type, payload)),
    )
    try:
        client.start()
        add_device_line = server.add_device_lines.get(timeout=5.0)
        assert "KEYS_TOTAL=20" in add_device_line
        assert "KEYS_PER_ROW=5" in add_device_line
        assert 'SERIAL="pyssp:my-surface"' in add_device_line
        assert 'CAN_CHANGE_PAGE="Page buttons"' in add_device_line
        seen_key_state = None
        for _ in range(10):
            event_type, payload = events.get(timeout=5.0)
            if event_type == "key_state":
                seen_key_state = payload
                break
        assert seen_key_state is not None
        assert seen_key_state["key"] == 0
        assert seen_key_state["state"]["text"] == "Hello"
        assert seen_key_state["state"]["color"] == "#112233"
        assert client.send_key_press(0, True) is True
        key_press_line = server.key_press_lines.get(timeout=5.0)
        assert "KEY-PRESS DEVICEID=pyssp:my-surface KEY=0 PRESSED=true" in key_press_line
        assert client.send_change_page(True) is True
        assert "CHANGE-PAGE DEVICEID=pyssp:my-surface DIRECTION=1" in server.change_page_lines.get(timeout=5.0)
        assert client.send_change_page(False) is True
        assert "CHANGE-PAGE DEVICEID=pyssp:my-surface DIRECTION=0" in server.change_page_lines.get(timeout=5.0)
    finally:
        client.stop()
        server.stop()
