from __future__ import annotations

from .shared import *

from pyssp.companion_satellite import CompanionSatelliteClient
from pyssp.ui.companion_satellite_window import CompanionSatelliteWindow


class _CompanionSatelliteBridge(QObject):
    statusChanged = pyqtSignal(str, str)
    helloReceived = pyqtSignal(str)
    capsReceived = pyqtSignal(dict)
    keyStateReceived = pyqtSignal(int, dict)
    keysCleared = pyqtSignal()


class CompanionSatelliteMixin:
    def _companion_satellite_event(self, event_type: str, payload: dict) -> None:
        if event_type == "status":
            self._companion_satellite_bridge.statusChanged.emit(
                str(payload.get("state", "") or ""),
                str(payload.get("message", "") or ""),
            )
        elif event_type == "hello":
            self._companion_satellite_bridge.helloReceived.emit(str(payload.get("api_version", "") or ""))
        elif event_type == "caps":
            self._companion_satellite_bridge.capsReceived.emit(dict(payload.get("caps", {}) or {}))
        elif event_type == "key_state":
            self._companion_satellite_bridge.keyStateReceived.emit(
                int(payload.get("key", -1)),
                dict(payload.get("state", {}) or {}),
            )
        elif event_type == "keys_clear":
            self._companion_satellite_bridge.keysCleared.emit()

    def _companion_satellite_should_run(self) -> bool:
        return bool(self.companion_satellite_enabled)

    def _companion_satellite_client_matches_settings(self) -> bool:
        client = self._companion_satellite_client
        if client is None:
            return False
        return (
            client.host == self.companion_satellite_host
            and int(client.port) == int(self.companion_satellite_port)
            and int(client.columns) == int(self.companion_satellite_columns)
            and int(client.rows) == int(self.companion_satellite_rows)
            and client.serial_suffix == CompanionSatelliteClient._normalize_serial_suffix(
                self.companion_satellite_serial_suffix
            )
        )

    def _apply_companion_satellite_state(self) -> None:
        self._refresh_companion_satellite_window()
        should_run = self._companion_satellite_should_run()
        if should_run:
            if not self._companion_satellite_client_matches_settings():
                self._stop_companion_satellite_client()
            self._start_companion_satellite_client()
        else:
            self._stop_companion_satellite_client()

    def _start_companion_satellite_client(self) -> None:
        if self._companion_satellite_client is None:
            self._companion_satellite_client = CompanionSatelliteClient(
                host=self.companion_satellite_host,
                port=self.companion_satellite_port,
                columns=self.companion_satellite_columns,
                rows=self.companion_satellite_rows,
                serial_suffix=self.companion_satellite_serial_suffix,
                on_event=self._companion_satellite_event,
            )
        if not self._companion_satellite_client.is_running:
            self._companion_satellite_client.start()

    def _stop_companion_satellite_client(self) -> None:
        client = self._companion_satellite_client
        self._companion_satellite_client = None
        if client is not None:
            client.stop()

    def _reconnect_companion_satellite_client(self) -> None:
        if self._companion_satellite_client is None:
            self._start_companion_satellite_client()
            return
        self._companion_satellite_client.reconnect()

    def _open_companion_satellite_options(self) -> None:
        self._open_options_dialog(initial_page="Companion Satellite")

    def _open_virtual_satellite(self) -> None:
        window = self._ensure_companion_satellite_window()
        window.show()
        window.raise_()
        window.activateWindow()
        self._refresh_companion_satellite_window()

    def _ensure_companion_satellite_window(self) -> CompanionSatelliteWindow:
        window = self._companion_satellite_window
        if window is not None:
            return window
        window = CompanionSatelliteWindow(None)
        window.openOptionsRequested.connect(self._open_companion_satellite_options)
        window.buttonPressed.connect(self._on_companion_satellite_button_pressed)
        window.windowClosed.connect(self._on_companion_satellite_window_closed)
        self._companion_satellite_window = window
        self._refresh_companion_satellite_window()
        return window

    def _on_companion_satellite_window_closed(self) -> None:
        return

    def _refresh_companion_satellite_window(self) -> None:
        window = self._companion_satellite_window
        if window is None:
            return
        window.set_target(self.companion_satellite_host, self.companion_satellite_port)
        window.set_grid_size(self.companion_satellite_columns, self.companion_satellite_rows)
        window.set_render_mode(self.companion_satellite_render_mode)
        state, message = self._companion_satellite_last_status
        window.set_connection_state(state, message)

    def _on_companion_satellite_status_changed(self, state: str, message: str) -> None:
        self._companion_satellite_last_status = (str(state or ""), str(message or ""))
        self._update_companion_satellite_status_indicator()
        window = self._companion_satellite_window
        if window is not None:
            window.set_connection_state(state, message)

    def _update_companion_satellite_status_indicator(self) -> None:
        label = getattr(self, "companion_satellite_status_icon", None)
        if label is None:
            return
        state = str(self._companion_satellite_last_status[0] or "").strip().lower()
        text = "SAT"
        if state == "connected":
            style = "QLabel{font-size:9pt;font-weight:bold;color:#165A20;background:#CFF3D6;border:1px solid #2E9B47;border-radius:8px;padding:0 6px;}"
        elif state in {"connecting", "reconnecting"}:
            style = "QLabel{font-size:9pt;font-weight:bold;color:#5F4200;background:#FFF0A6;border:1px solid #CFAE2A;border-radius:8px;padding:0 6px;}"
        else:
            style = "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#D6D9DE;border:1px solid #8C939D;border-radius:8px;padding:0 6px;}"
        label.setText(text)
        label.setStyleSheet(style)
        message = str(self._companion_satellite_last_status[1] or "").strip()
        tooltip = message or (
            tr("Connected") if state == "connected" else tr("Connecting") if state in {"connecting", "reconnecting"} else tr("Not Connected")
        )
        label.setToolTip(tooltip)

    def _on_companion_satellite_hello_received(self, version: str) -> None:
        self._companion_satellite_api_version = str(version or "").strip()

    def _on_companion_satellite_caps_received(self, caps: dict) -> None:
        self._companion_satellite_caps = dict(caps or {})

    def _on_companion_satellite_key_state_received(self, key: int, state: dict) -> None:
        window = self._ensure_companion_satellite_window()
        window.update_button(int(key), dict(state or {}))

    def _on_companion_satellite_keys_cleared(self) -> None:
        window = self._companion_satellite_window
        if window is not None:
            window.clear_buttons()

    def _on_companion_satellite_button_pressed(self, key: int, pressed: bool) -> None:
        client = self._companion_satellite_client
        if client is None:
            return
        client.send_key_press(int(key), bool(pressed))
