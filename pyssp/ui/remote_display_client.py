from __future__ import annotations

import html
import json
import threading
import time
from queue import Empty, Queue
from typing import Any, Optional
from urllib.error import URLError
from urllib.request import urlopen

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from websockets.sync.client import connect

from pyssp.i18n import tr
from pyssp.remote_client_settings import (
    RemoteClientSettings,
    load_remote_client_settings,
    save_remote_client_settings,
)
from pyssp.ui.lyric_display import LyricDisplayWindow
from pyssp.ui.stage_display import StageDisplayWindow


class RemoteWebSocketClient(QThread):
    status_changed = pyqtSignal(bool, str)
    ws_state_received = pyqtSignal(dict)
    lyric_bundle_received = pyqtSignal(dict)
    state_received = pyqtSignal(dict)

    def __init__(self, host: str, http_port: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._host = str(host or "127.0.0.1").strip() or "127.0.0.1"
        self._http_port = max(1, min(65534, int(http_port)))
        self._ws_port = self._http_port + 1
        self._stop_event = threading.Event()
        self._outbound: Queue[tuple[str, Optional[dict[str, Any]]]] = Queue()
        self._pending_paths: dict[str, str] = {}
        self._request_counter = 0
        self._latest_ws_state: dict[str, Any] = {}
        self._lyric_query_supported: Optional[bool] = None

    def stop(self) -> None:
        self._stop_event.set()

    def request_api(self, path: str, body: Optional[dict[str, Any]] = None) -> None:
        self._outbound.put((str(path or "").strip(), dict(body or {}) if body else None))

    def request_lyric_bundle(self) -> None:
        if self._lyric_query_supported is False:
            self._outbound.put(("__legacy_http_lyric_bundle__", None))
            return
        self.request_api("/api/query/lyric-openlp")

    def run(self) -> None:
        ws_url = f"ws://{self._host}:{self._ws_port}/ws"
        while not self._stop_event.is_set():
            try:
                self.status_changed.emit(False, tr("Connecting..."))
                with connect(ws_url, open_timeout=3, close_timeout=1) as websocket:
                    self._lyric_query_supported = None
                    self._latest_ws_state = {}
                    self.status_changed.emit(True, tr("Connected"))
                    self.request_api("/api/query")
                    self.request_lyric_bundle()
                    last_query_at = 0.0
                    while not self._stop_event.is_set():
                        now = time.monotonic()
                        if (now - last_query_at) >= 0.5:
                            self.request_api("/api/query")
                            last_query_at = now
                        self._drain_outbound(websocket)
                        try:
                            raw_message = websocket.recv(timeout=0.25)
                        except TimeoutError:
                            continue
                        if raw_message is None:
                            raise ConnectionError("Connection closed.")
                        self._handle_message(raw_message)
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                self.status_changed.emit(False, f"{tr('Disconnected')}: {exc}")
                self._pending_paths.clear()
                self._stop_event.wait(1.0)
        self.status_changed.emit(False, tr("Disconnected"))

    def _drain_outbound(self, websocket) -> None:
        while not self._stop_event.is_set():
            try:
                path, body = self._outbound.get_nowait()
            except Empty:
                return
            if not path:
                continue
            if path == "__legacy_http_lyric_bundle__":
                bundle = self._fetch_legacy_lyric_bundle_http()
                if bundle is not None:
                    self.lyric_bundle_received.emit(bundle)
                continue
            self._request_counter += 1
            request_id = f"remote-client-{self._request_counter}"
            self._pending_paths[request_id] = path
            websocket.send(
                json.dumps(
                    {
                        "type": "api_request",
                        "id": request_id,
                        "path": path,
                        "method": "POST",
                        "body": dict(body or {}),
                    },
                    ensure_ascii=False,
                )
            )

    def _handle_message(self, raw_message: Any) -> None:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8", errors="ignore")
        payload = json.loads(str(raw_message))
        if not isinstance(payload, dict):
            return
        if isinstance(payload.get("results"), dict):
            self._latest_ws_state = dict(payload["results"])
            self.ws_state_received.emit(dict(payload["results"]))
            return
        if str(payload.get("type", "")).strip().lower() != "api_response":
            return
        request_id = str(payload.get("id", "")).strip()
        path = self._pending_paths.pop(request_id, "")
        response_payload = payload.get("payload")
        if not isinstance(response_payload, dict):
            return
        if path == "/api/query":
            result = response_payload.get("result")
            if isinstance(result, dict):
                self.state_received.emit(dict(result))
            return
        if path == "/api/query/lyric-openlp":
            result = response_payload.get("result")
            if isinstance(result, dict):
                self._lyric_query_supported = True
                self.lyric_bundle_received.emit(dict(result))
                return
            if response_payload.get("ok") is False:
                self._lyric_query_supported = False
                bundle = self._fetch_legacy_lyric_bundle_http()
                if bundle is not None:
                    self.lyric_bundle_received.emit(bundle)
                return

    def _fetch_legacy_lyric_bundle_http(self) -> Optional[dict]:
        base_url = f"http://{self._host}:{self._http_port}"
        try:
            live_items = self._http_get_json(f"{base_url}/lyric/api/v2/controller/live-items")
            service_items = self._http_get_json(f"{base_url}/stage/api/v2/service/items")
        except Exception:
            return None
        if not isinstance(live_items, dict):
            return None
        if not isinstance(service_items, list):
            service_items = []
        return {
            "ws": dict(self._latest_ws_state),
            "live_items": dict(live_items),
            "service_items": list(service_items),
        }

    @staticmethod
    def _http_get_json(url: str) -> Any:
        try:
            with urlopen(url, timeout=3.0) as response:
                status = int(getattr(response, "status", 200))
                if status >= 400:
                    raise URLError(f"HTTP {status}")
                payload = response.read().decode("utf-8")
        except URLError:
            raise
        return json.loads(payload)


class RemoteClientSettingsDialog(QDialog):
    def __init__(self, settings: RemoteClientSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Remote Display Settings"))
        self.resize(720, 640)
        self._settings = settings
        self._lyric_role_buttons: dict[str, dict[str, QPushButton]] = {}
        self._stage_role_buttons: dict[str, dict[str, QPushButton]] = {}

        root = QVBoxLayout(self)
        tabs = QTabWidget(self)
        root.addWidget(tabs, 1)
        tabs.addTab(self._build_connection_tab(), tr("Connection"))
        tabs.addTab(self._build_lyric_tab(), tr("Lyric Display"))
        tabs.addTab(self._build_stage_tab(), tr("Stage Display"))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_connection_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        group = QGroupBox(tr("Remote pySSP Instance"), page)
        form = QFormLayout(group)
        self.server_host_edit = QLineEdit(str(self._settings.server_host or "127.0.0.1").strip() or "127.0.0.1", group)
        self.server_http_port_spin = QSpinBox(group)
        self.server_http_port_spin.setRange(1, 65534)
        self.server_http_port_spin.setValue(int(self._settings.server_http_port))
        self.server_ws_port_value = QLabel(group)
        form.addRow(tr("IP Address:"), self.server_host_edit)
        form.addRow(tr("HTTP Port:"), self.server_http_port_spin)
        form.addRow(tr("WS Port (auto):"), self.server_ws_port_value)
        self.server_http_port_spin.valueChanged.connect(self._refresh_ws_port_label)
        self._refresh_ws_port_label()
        layout.addWidget(group)
        layout.addStretch(1)
        return page

    def _build_lyric_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        group = QGroupBox(tr("Lyric Window Fonts"), page)
        form = QFormLayout(group)
        self.lyric_transparent_checkbox = QCheckBox(tr("Transparent mode"), group)
        self.lyric_transparent_checkbox.setChecked(bool(self._settings.lyric_display_transparent_mode))
        self.lyric_idle_checkbox = QCheckBox(tr("Show idle message when nothing is playing"), group)
        self.lyric_idle_checkbox.setChecked(bool(self._settings.lyric_display_show_not_playing_message))
        self.lyric_font_family_combo = QFontComboBox(group)
        self.lyric_font_family_combo.setCurrentFont(QFont(self._settings.lyric_display_font_family or self.lyric_font_family_combo.currentFont().family()))
        self.lyric_font_size_spin = self._size_spin(group, 10, 240, self._settings.lyric_display_font_size)
        self.lyric_previous_spin = self._size_spin(group, 0, 20, self._settings.lyric_display_previous_line_count)
        self.lyric_next_spin = self._size_spin(group, 0, 20, self._settings.lyric_display_next_line_count)
        form.addRow(self.lyric_transparent_checkbox)
        form.addRow(self.lyric_idle_checkbox)
        form.addRow(tr("Font:"), self.lyric_font_family_combo)
        form.addRow(tr("Base Text Size:"), self.lyric_font_size_spin)
        form.addRow(tr("Played Lines:"), self.lyric_previous_spin)
        form.addRow(tr("Next Lines:"), self.lyric_next_spin)
        self._build_role_controls(
            form=form,
            scope="lyric",
            prefix="lyric_display",
            size_defaults={
                "played": self._settings.lyric_display_played_text_size,
                "current": self._settings.lyric_display_current_text_size,
                "next": self._settings.lyric_display_next_text_size,
            },
            scale_defaults={
                "played": self._settings.lyric_display_played_scale_percent,
                "current": self._settings.lyric_display_current_scale_percent,
                "next": self._settings.lyric_display_next_scale_percent,
            },
            color_defaults={
                "played": self._settings.lyric_display_played_color,
                "current": self._settings.lyric_display_current_color,
                "next": self._settings.lyric_display_next_color,
            },
            bold_defaults={
                "played": self._settings.lyric_display_played_bold,
                "current": self._settings.lyric_display_current_bold,
                "next": self._settings.lyric_display_next_bold,
            },
            italic_defaults={
                "played": self._settings.lyric_display_played_italic,
                "current": self._settings.lyric_display_current_italic,
                "next": self._settings.lyric_display_next_italic,
            },
            auto_adjust=self._settings.lyric_display_auto_adjust_role_sizes,
        )
        layout.addWidget(group)
        layout.addStretch(1)
        return page

    def _build_stage_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        general_group = QGroupBox(tr("Stage Display Window"), page)
        general_form = QFormLayout(general_group)
        self.stage_open_on_startup_checkbox = QCheckBox(tr("Open stage display on startup"), general_group)
        self.stage_open_on_startup_checkbox.setChecked(bool(self._settings.stage_display_open_on_startup))
        self.stage_font_family_combo = QFontComboBox(general_group)
        self.stage_font_family_combo.setCurrentFont(QFont(self._settings.stage_display_font_family or self.stage_font_family_combo.currentFont().family()))
        self.stage_font_size_spin = self._size_spin(general_group, 10, 240, self._settings.stage_display_font_size)
        general_form.addRow(self.stage_open_on_startup_checkbox)
        general_form.addRow(tr("Info Font:"), self.stage_font_family_combo)
        general_form.addRow(tr("Info Text Size:"), self.stage_font_size_spin)
        layout.addWidget(general_group)

        lyric_group = QGroupBox(tr("Stage Lyric Fonts"), page)
        lyric_form = QFormLayout(lyric_group)
        self.stage_lyric_font_family_combo = QFontComboBox(lyric_group)
        self.stage_lyric_font_family_combo.setCurrentFont(
            QFont(self._settings.stage_display_lyric_font_family or self.stage_lyric_font_family_combo.currentFont().family())
        )
        self.stage_lyric_font_size_spin = self._size_spin(lyric_group, 10, 240, self._settings.stage_display_lyric_font_size)
        self.stage_previous_spin = self._size_spin(lyric_group, 0, 20, self._settings.stage_display_lyric_previous_line_count)
        self.stage_next_spin = self._size_spin(lyric_group, 0, 20, self._settings.stage_display_lyric_next_line_count)
        lyric_form.addRow(tr("Lyric Font:"), self.stage_lyric_font_family_combo)
        lyric_form.addRow(tr("Lyric Base Text Size:"), self.stage_lyric_font_size_spin)
        lyric_form.addRow(tr("Played Lines:"), self.stage_previous_spin)
        lyric_form.addRow(tr("Next Lines:"), self.stage_next_spin)
        self._build_role_controls(
            form=lyric_form,
            scope="stage",
            prefix="stage_display_lyric",
            size_defaults={
                "played": self._settings.stage_display_lyric_played_text_size,
                "current": self._settings.stage_display_lyric_current_text_size,
                "next": self._settings.stage_display_lyric_next_text_size,
            },
            scale_defaults={
                "played": self._settings.stage_display_lyric_played_scale_percent,
                "current": self._settings.stage_display_lyric_current_scale_percent,
                "next": self._settings.stage_display_lyric_next_scale_percent,
            },
            color_defaults={
                "played": self._settings.stage_display_lyric_played_color,
                "current": self._settings.stage_display_lyric_current_color,
                "next": self._settings.stage_display_lyric_next_color,
            },
            bold_defaults={
                "played": self._settings.stage_display_lyric_played_bold,
                "current": self._settings.stage_display_lyric_current_bold,
                "next": self._settings.stage_display_lyric_next_bold,
            },
            italic_defaults={
                "played": self._settings.stage_display_lyric_played_italic,
                "current": self._settings.stage_display_lyric_current_italic,
                "next": self._settings.stage_display_lyric_next_italic,
            },
            auto_adjust=self._settings.stage_display_lyric_auto_adjust_role_sizes,
        )
        layout.addWidget(lyric_group)
        layout.addStretch(1)
        return page

    def _build_role_controls(
        self,
        *,
        form: QFormLayout,
        scope: str,
        prefix: str,
        size_defaults: dict[str, int],
        scale_defaults: dict[str, int],
        color_defaults: dict[str, str],
        bold_defaults: dict[str, bool],
        italic_defaults: dict[str, bool],
        auto_adjust: bool,
    ) -> None:
        auto_checkbox = QCheckBox(tr("Auto adjust role sizes from base text size"), self)
        auto_checkbox.setChecked(bool(auto_adjust))
        setattr(self, f"{prefix}_auto_checkbox", auto_checkbox)
        form.addRow(auto_checkbox)
        button_store = self._lyric_role_buttons if scope == "lyric" else self._stage_role_buttons
        button_store.clear()

        for role, label in [("played", tr("Played")), ("current", tr("Current")), ("next", tr("Next"))]:
            scale_spin = self._size_spin(self, 25, 300, int(scale_defaults.get(role, 100)))
            scale_spin.setSuffix("%")
            size_spin = self._size_spin(self, 8, 240, int(size_defaults.get(role, 24)))
            bold_box = QCheckBox(tr("Bold"), self)
            bold_box.setChecked(bool(bold_defaults.get(role, True)))
            italic_box = QCheckBox(tr("Italic"), self)
            italic_box.setChecked(bool(italic_defaults.get(role, False)))
            style_row = QWidget(self)
            style_layout = QHBoxLayout(style_row)
            style_layout.setContentsMargins(0, 0, 0, 0)
            style_layout.setSpacing(8)
            style_layout.addWidget(bold_box)
            style_layout.addWidget(italic_box)
            style_layout.addStretch(1)
            color_button = QPushButton(self)
            self._set_color_button(color_button, color_defaults.get(role, "#FFFFFF"))
            color_button.clicked.connect(lambda _checked=False, btn=color_button: self._pick_color(btn))
            setattr(self, f"{prefix}_{role}_scale_spin", scale_spin)
            setattr(self, f"{prefix}_{role}_size_spin", size_spin)
            setattr(self, f"{prefix}_{role}_bold_box", bold_box)
            setattr(self, f"{prefix}_{role}_italic_box", italic_box)
            form.addRow(f"{label} {tr('Scale')}:", scale_spin)
            form.addRow(f"{label} {tr('Text Size')}:", size_spin)
            form.addRow(f"{label} {tr('Style')}:", style_row)
            form.addRow(f"{label} {tr('Color')}:", color_button)
            button_store[role] = {"button": color_button}

        auto_checkbox.toggled.connect(lambda checked, p=prefix: self._sync_role_size_mode(p, bool(checked)))
        self._sync_role_size_mode(prefix, bool(auto_adjust))

    def _sync_role_size_mode(self, prefix: str, auto_mode: bool) -> None:
        for role in ("played", "current", "next"):
            getattr(self, f"{prefix}_{role}_scale_spin").setEnabled(auto_mode)
            getattr(self, f"{prefix}_{role}_size_spin").setEnabled(not auto_mode)

    def _pick_color(self, button: QPushButton) -> None:
        current = str(button.property("color") or "#FFFFFF")
        chosen = QColorDialog.getColor()
        if chosen.isValid():
            self._set_color_button(button, chosen.name().upper() or current)

    def _set_color_button(self, button: QPushButton, color: str) -> None:
        token = str(color or "#FFFFFF").strip() or "#FFFFFF"
        button.setProperty("color", token)
        button.setText(token)
        button.setStyleSheet(f"QPushButton{{background:{token}; color:#000000; min-height:28px;}}")

    def _size_spin(self, parent: QWidget, low: int, high: int, value: int) -> QSpinBox:
        widget = QSpinBox(parent)
        widget.setRange(low, high)
        widget.setValue(int(value))
        return widget

    def _refresh_ws_port_label(self) -> None:
        self.server_ws_port_value.setText(str(int(self.server_http_port_spin.value()) + 1))

    def selected_settings(self) -> RemoteClientSettings:
        return RemoteClientSettings(
            server_host=str(self.server_host_edit.text() or "127.0.0.1").strip() or "127.0.0.1",
            server_http_port=int(self.server_http_port_spin.value()),
            lyric_display_transparent_mode=bool(self.lyric_transparent_checkbox.isChecked()),
            lyric_display_show_not_playing_message=bool(self.lyric_idle_checkbox.isChecked()),
            lyric_display_font_family=self.lyric_font_family_combo.currentFont().family(),
            lyric_display_font_size=int(self.lyric_font_size_spin.value()),
            lyric_display_previous_line_count=int(self.lyric_previous_spin.value()),
            lyric_display_next_line_count=int(self.lyric_next_spin.value()),
            lyric_display_played_color=str(self._lyric_role_buttons["played"]["button"].property("color") or "#A0A0A0"),
            lyric_display_current_color=str(self._lyric_role_buttons["current"]["button"].property("color") or "#FFD400"),
            lyric_display_next_color=str(self._lyric_role_buttons["next"]["button"].property("color") or "#FFFFFF"),
            lyric_display_auto_adjust_role_sizes=bool(self.lyric_display_auto_checkbox.isChecked()),
            lyric_display_played_scale_percent=int(self.lyric_display_played_scale_spin.value()),
            lyric_display_current_scale_percent=int(self.lyric_display_current_scale_spin.value()),
            lyric_display_next_scale_percent=int(self.lyric_display_next_scale_spin.value()),
            lyric_display_played_text_size=int(self.lyric_display_played_size_spin.value()),
            lyric_display_current_text_size=int(self.lyric_display_current_size_spin.value()),
            lyric_display_next_text_size=int(self.lyric_display_next_size_spin.value()),
            lyric_display_played_bold=bool(self.lyric_display_played_bold_box.isChecked()),
            lyric_display_current_bold=bool(self.lyric_display_current_bold_box.isChecked()),
            lyric_display_next_bold=bool(self.lyric_display_next_bold_box.isChecked()),
            lyric_display_played_italic=bool(self.lyric_display_played_italic_box.isChecked()),
            lyric_display_current_italic=bool(self.lyric_display_current_italic_box.isChecked()),
            lyric_display_next_italic=bool(self.lyric_display_next_italic_box.isChecked()),
            stage_display_open_on_startup=bool(self.stage_open_on_startup_checkbox.isChecked()),
            stage_display_gadgets=self._settings.stage_display_gadgets,
            stage_display_font_family=self.stage_font_family_combo.currentFont().family(),
            stage_display_font_size=int(self.stage_font_size_spin.value()),
            stage_display_lyric_font_family=self.stage_lyric_font_family_combo.currentFont().family(),
            stage_display_lyric_font_size=int(self.stage_lyric_font_size_spin.value()),
            stage_display_lyric_previous_line_count=int(self.stage_previous_spin.value()),
            stage_display_lyric_next_line_count=int(self.stage_next_spin.value()),
            stage_display_lyric_played_color=str(self._stage_role_buttons["played"]["button"].property("color") or "#A0A0A0"),
            stage_display_lyric_current_color=str(self._stage_role_buttons["current"]["button"].property("color") or "#FFD400"),
            stage_display_lyric_next_color=str(self._stage_role_buttons["next"]["button"].property("color") or "#FFFFFF"),
            stage_display_lyric_auto_adjust_role_sizes=bool(self.stage_display_lyric_auto_checkbox.isChecked()),
            stage_display_lyric_played_scale_percent=int(self.stage_display_lyric_played_scale_spin.value()),
            stage_display_lyric_current_scale_percent=int(self.stage_display_lyric_current_scale_spin.value()),
            stage_display_lyric_next_scale_percent=int(self.stage_display_lyric_next_scale_spin.value()),
            stage_display_lyric_played_text_size=int(self.stage_display_lyric_played_size_spin.value()),
            stage_display_lyric_current_text_size=int(self.stage_display_lyric_current_size_spin.value()),
            stage_display_lyric_next_text_size=int(self.stage_display_lyric_next_size_spin.value()),
            stage_display_lyric_played_bold=bool(self.stage_display_lyric_played_bold_box.isChecked()),
            stage_display_lyric_current_bold=bool(self.stage_display_lyric_current_bold_box.isChecked()),
            stage_display_lyric_next_bold=bool(self.stage_display_lyric_next_bold_box.isChecked()),
            stage_display_lyric_played_italic=bool(self.stage_display_lyric_played_italic_box.isChecked()),
            stage_display_lyric_current_italic=bool(self.stage_display_lyric_current_italic_box.isChecked()),
            stage_display_lyric_next_italic=bool(self.stage_display_lyric_next_italic_box.isChecked()),
        )


class RemoteDisplayClientWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self._settings = load_remote_client_settings()
        self._confirm_close = True
        self._lyric_display_window: Optional[LyricDisplayWindow] = None
        self._stage_display_window: Optional[StageDisplayWindow] = None
        self._connection: Optional[RemoteWebSocketClient] = None
        self._connection_status_text = tr("Disconnected")
        self._ws_state: dict[str, Any] = {}
        self._lyric_bundle: dict[str, Any] = {
            "ws": {},
            "live_items": {"item": "", "slides": []},
            "service_items": [],
        }
        self._api_state: dict[str, Any] = {}
        self.setWindowTitle(tr("pySSP Remote Display Client"))
        self.resize(440, 260)
        self._build_main_ui()
        self._apply_settings_to_windows()
        self._update_window_title()
        if self._settings.stage_display_open_on_startup:
            self._show_stage_display()
        self._start_connection()

    def _build_main_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel(tr("Remote Display Client"), self)
        title_font = QFont(title.font())
        title_font.setPointSize(max(14, title_font.pointSize() + 3))
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        self._connection_status_label = QLabel("", self)
        self._connection_status_label.setWordWrap(True)
        root.addWidget(self._connection_status_label)

        self._server_target_label = QLabel("", self)
        self._server_target_label.setWordWrap(True)
        root.addWidget(self._server_target_label)

        self._transparent_checkbox = QCheckBox(tr("Lyric Display Transparent Mode"), self)
        self._transparent_checkbox.setChecked(bool(self._settings.lyric_display_transparent_mode))
        self._transparent_checkbox.toggled.connect(self._set_transparent_mode_from_ui)
        root.addWidget(self._transparent_checkbox)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        self._settings_button = QPushButton(tr("Open Settings"), self)
        self._settings_button.clicked.connect(self._open_settings_dialog)
        buttons_row.addWidget(self._settings_button)
        self._lyric_button = QPushButton(tr("Open Lyric Display"), self)
        self._lyric_button.clicked.connect(self._show_lyric_display)
        buttons_row.addWidget(self._lyric_button)
        self._stage_button = QPushButton(tr("Open Stage Display"), self)
        self._stage_button.clicked.connect(self._show_stage_display)
        buttons_row.addWidget(self._stage_button)
        root.addLayout(buttons_row)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self._reconnect_button = QPushButton(tr("Reconnect"), self)
        self._reconnect_button.clicked.connect(self._start_connection)
        actions_row.addWidget(self._reconnect_button)
        self._close_lyric_button = QPushButton(tr("Close Lyric Display"), self)
        self._close_lyric_button.clicked.connect(self._close_lyric_display)
        actions_row.addWidget(self._close_lyric_button)
        self._close_stage_button = QPushButton(tr("Close Stage Display"), self)
        self._close_stage_button.clicked.connect(self._close_stage_display)
        actions_row.addWidget(self._close_stage_button)
        root.addLayout(actions_row)
        root.addStretch(1)
        self._refresh_window_buttons()

    def closeEvent(self, event) -> None:
        if self._confirm_close:
            answer = QMessageBox.question(
                self,
                tr("Quit Remote Display Client"),
                tr("Closing the main window will quit the remote display client. Continue?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self._stop_connection()
        self._close_lyric_display()
        self._close_stage_display()
        super().closeEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        transparent_action = QAction(tr("Lyric Display Transparent Mode"), self)
        transparent_action.setCheckable(True)
        transparent_action.setChecked(bool(self._settings.lyric_display_transparent_mode))
        lyric_action = QAction(tr("Open Lyric Display"), self)
        stage_action = QAction(tr("Open Stage Display"), self)
        reconnect_action = QAction(tr("Reconnect"), self)
        settings_action = QAction(tr("Remote Display Settings"), self)
        menu.addAction(transparent_action)
        menu.addAction(lyric_action)
        menu.addAction(stage_action)
        menu.addAction(reconnect_action)
        menu.addAction(settings_action)
        chosen = menu.exec_(event.globalPos())
        if chosen == transparent_action:
            self._set_transparent_mode_from_ui(bool(transparent_action.isChecked()))
        elif chosen == lyric_action:
            self._show_lyric_display()
        elif chosen == stage_action:
            self._show_stage_display()
        elif chosen == reconnect_action:
            self._start_connection()
        elif chosen == settings_action:
            self._open_settings_dialog()

    def _create_lyric_display_window(self) -> LyricDisplayWindow:
        window = LyricDisplayWindow(
            None,
            on_toggle_transparent_mode=self._set_transparent_mode_from_ui,
            on_adjust_font_size=self._adjust_font_size_from_ui,
            on_open_settings=self._open_settings_dialog,
        )
        window.destroyed.connect(lambda _obj=None, closed_window=window: self._on_lyric_display_destroyed(closed_window))
        return window

    def _show_lyric_display(self) -> None:
        if self._lyric_display_window is None:
            self._lyric_display_window = self._create_lyric_display_window()
        self._apply_settings_to_windows()
        self._lyric_display_window.show()
        self._lyric_display_window.raise_()
        self._lyric_display_window.activateWindow()
        self._render_lyric_display()
        self._refresh_window_buttons()

    def _close_lyric_display(self) -> None:
        if self._lyric_display_window is None:
            return
        window = self._lyric_display_window
        self._lyric_display_window = None
        window.close()
        self._refresh_window_buttons()

    def _on_lyric_display_destroyed(self, window=None) -> None:
        if window is not None and self._lyric_display_window is not window:
            return
        self._lyric_display_window = None
        self._refresh_window_buttons()

    def _set_transparent_mode_from_ui(self, enabled: bool) -> None:
        self._settings.lyric_display_transparent_mode = bool(enabled)
        if self._transparent_checkbox.isChecked() != bool(enabled):
            self._transparent_checkbox.blockSignals(True)
            self._transparent_checkbox.setChecked(bool(enabled))
            self._transparent_checkbox.blockSignals(False)
        self._apply_settings_to_windows()
        save_remote_client_settings(self._settings)

    def _adjust_font_size_from_ui(self, delta: int) -> None:
        self._settings.lyric_display_font_size = max(10, min(240, int(self._settings.lyric_display_font_size) + int(delta)))
        self._apply_settings_to_windows()
        self._render_lyric_display()
        save_remote_client_settings(self._settings)

    def _open_settings_dialog(self) -> None:
        dialog = RemoteClientSettingsDialog(self._settings, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        previous_host = self._settings.server_host
        previous_http_port = self._settings.server_http_port
        self._settings = dialog.selected_settings()
        save_remote_client_settings(self._settings)
        self._apply_settings_to_windows()
        self._render_lyric_display()
        self._refresh_stage_display()
        self._refresh_window_buttons()
        if self._settings.server_host != previous_host or int(self._settings.server_http_port) != int(previous_http_port):
            self._start_connection()

    def _apply_settings_to_windows(self) -> None:
        if self._transparent_checkbox.isChecked() != bool(self._settings.lyric_display_transparent_mode):
            self._transparent_checkbox.blockSignals(True)
            self._transparent_checkbox.setChecked(bool(self._settings.lyric_display_transparent_mode))
            self._transparent_checkbox.blockSignals(False)
        if self._lyric_display_window is not None:
            self._lyric_display_window.set_transparent_mode_enabled(bool(self._settings.lyric_display_transparent_mode))
            self._lyric_display_window.configure_display_settings(
                font_family=self._settings.lyric_display_font_family,
                font_size=self._settings.lyric_display_font_size,
                show_not_playing_message=self._settings.lyric_display_show_not_playing_message,
                previous_line_count=self._settings.lyric_display_previous_line_count,
                next_line_count=self._settings.lyric_display_next_line_count,
                role_colors={
                    "played": self._settings.lyric_display_played_color,
                    "current": self._settings.lyric_display_current_color,
                    "next": self._settings.lyric_display_next_color,
                },
                role_sizes={
                    "played": self._settings.lyric_display_played_text_size,
                    "current": self._settings.lyric_display_current_text_size,
                    "next": self._settings.lyric_display_next_text_size,
                },
                auto_adjust_role_sizes=self._settings.lyric_display_auto_adjust_role_sizes,
                role_scale_percents={
                    "played": self._settings.lyric_display_played_scale_percent,
                    "current": self._settings.lyric_display_current_scale_percent,
                    "next": self._settings.lyric_display_next_scale_percent,
                },
                role_bold={
                    "played": self._settings.lyric_display_played_bold,
                    "current": self._settings.lyric_display_current_bold,
                    "next": self._settings.lyric_display_next_bold,
                },
                role_italic={
                    "played": self._settings.lyric_display_played_italic,
                    "current": self._settings.lyric_display_current_italic,
                    "next": self._settings.lyric_display_next_italic,
                },
            )
        if self._stage_display_window is not None:
            self._stage_display_window.configure_gadgets(self._settings.stage_display_gadgets)
            self._stage_display_window.configure_font_settings(
                default_font_family=self._settings.stage_display_font_family,
                default_font_size=self._settings.stage_display_font_size,
                lyric_font_family=self._settings.stage_display_lyric_font_family,
                lyric_font_size=self._settings.stage_display_lyric_font_size,
                lyric_role_colors={
                    "played": self._settings.stage_display_lyric_played_color,
                    "current": self._settings.stage_display_lyric_current_color,
                    "next": self._settings.stage_display_lyric_next_color,
                },
                lyric_role_sizes={
                    "played": self._settings.stage_display_lyric_played_text_size,
                    "current": self._settings.stage_display_lyric_current_text_size,
                    "next": self._settings.stage_display_lyric_next_text_size,
                },
                lyric_auto_adjust_role_sizes=self._settings.stage_display_lyric_auto_adjust_role_sizes,
                lyric_role_scale_percents={
                    "played": self._settings.stage_display_lyric_played_scale_percent,
                    "current": self._settings.stage_display_lyric_current_scale_percent,
                    "next": self._settings.stage_display_lyric_next_scale_percent,
                },
                lyric_role_bold={
                    "played": self._settings.stage_display_lyric_played_bold,
                    "current": self._settings.stage_display_lyric_current_bold,
                    "next": self._settings.stage_display_lyric_next_bold,
                },
                lyric_role_italic={
                    "played": self._settings.stage_display_lyric_played_italic,
                    "current": self._settings.stage_display_lyric_current_italic,
                    "next": self._settings.stage_display_lyric_next_italic,
                },
            )

    def _start_connection(self) -> None:
        self._stop_connection()
        self._connection = RemoteWebSocketClient(self._settings.server_host, self._settings.server_http_port, self)
        self._connection.status_changed.connect(self._on_connection_status_changed)
        self._connection.ws_state_received.connect(self._on_ws_state_received)
        self._connection.lyric_bundle_received.connect(self._on_lyric_bundle_received)
        self._connection.state_received.connect(self._on_state_received)
        self._connection.start()

    def _stop_connection(self) -> None:
        if self._connection is None:
            return
        self._connection.stop()
        self._connection.wait(2500)
        self._connection = None

    def _on_connection_status_changed(self, connected: bool, text: str) -> None:
        self._connection_status_text = str(text or "").strip() or (tr("Connected") if connected else tr("Disconnected"))
        self._update_window_title()
        self._refresh_stage_display()

    def _on_ws_state_received(self, state: dict) -> None:
        previous_item = str(self._ws_state.get("item", "") or "")
        previous_service = str(self._ws_state.get("service", "") or "")
        self._ws_state = dict(state or {})
        bundle_ws = self._lyric_bundle.get("ws")
        if isinstance(bundle_ws, dict):
            bundle_ws.update(self._ws_state)
        if previous_item != str(self._ws_state.get("item", "") or "") or previous_service != str(self._ws_state.get("service", "") or ""):
            if self._connection is not None:
                self._connection.request_lyric_bundle()
        self._render_lyric_display()
        self._refresh_stage_display()

    def _on_lyric_bundle_received(self, bundle: dict) -> None:
        self._lyric_bundle = {
            "ws": dict(bundle.get("ws", {})) if isinstance(bundle.get("ws"), dict) else {},
            "live_items": dict(bundle.get("live_items", {})) if isinstance(bundle.get("live_items"), dict) else {"item": "", "slides": []},
            "service_items": list(bundle.get("service_items", [])) if isinstance(bundle.get("service_items"), list) else [],
        }
        if self._ws_state:
            bundle_ws = self._lyric_bundle.get("ws")
            if isinstance(bundle_ws, dict):
                bundle_ws.update(self._ws_state)
        self._render_lyric_display()
        self._refresh_stage_display()

    def _on_state_received(self, state: dict) -> None:
        self._api_state = dict(state or {})
        self._refresh_stage_display()

    def _update_window_title(self) -> None:
        host = str(self._settings.server_host or "127.0.0.1").strip() or "127.0.0.1"
        self.setWindowTitle(f"{tr('pySSP Remote Display Client')} - {host}:{self._settings.server_http_port} - {self._connection_status_text}")
        self._connection_status_label.setText(f"{tr('Status')}: {self._connection_status_text}")
        self._server_target_label.setText(
            f"{tr('Target')}: {host}:{self._settings.server_http_port}  |  WS {self._settings.server_http_port + 1}"
        )

    def _refresh_window_buttons(self) -> None:
        lyric_open = self._lyric_display_window is not None and self._lyric_display_window.isVisible()
        stage_open = self._stage_display_window is not None and self._stage_display_window.isVisible()
        self._lyric_button.setText(tr("Open Lyric Display") if not lyric_open else tr("Show Lyric Display"))
        self._stage_button.setText(tr("Open Stage Display") if not stage_open else tr("Show Stage Display"))
        self._close_lyric_button.setEnabled(lyric_open)
        self._close_stage_button.setEnabled(stage_open)

    def _current_slide(self) -> dict[str, Any]:
        live_items = self._lyric_bundle.get("live_items")
        slides = list(live_items.get("slides", [])) if isinstance(live_items, dict) else []
        if not slides:
            return {}
        raw_index = self._ws_state.get("slide", 0)
        try:
            index = max(0, min(len(slides) - 1, int(raw_index)))
        except Exception:
            index = 0
        slide = slides[index]
        return dict(slide) if isinstance(slide, dict) else {}

    def _resolved_lyric_html(self) -> str:
        if bool(self._ws_state.get("blank")) or str(self._ws_state.get("display", "")).strip().lower() == "blank":
            return ""
        slide = self._current_slide()
        item_id = str(self._ws_state.get("item", "") or "").strip()
        html_value = str(slide.get("html", "") or "").strip()
        if html_value in {"&#8203;", "&#x200b;"}:
            html_value = ""
        if html_value:
            return html_value
        text_value = str(slide.get("text", "") or "").strip()
        if text_value == "\u200b":
            text_value = ""
        if text_value:
            return "<br />".join(html.escape(part) for part in text_value.splitlines())
        if not item_id:
            return ""
        if self._settings.lyric_display_show_not_playing_message:
            return html.escape(tr("No sound is currently playing."))
        return ""

    def _render_lyric_display(self) -> None:
        if self._lyric_display_window is None:
            return
        self._lyric_display_window.set_lyric_text(self._resolved_lyric_html())

    def _show_stage_display(self) -> None:
        if self._stage_display_window is None:
            self._stage_display_window = StageDisplayWindow(self)
            self._stage_display_window.destroyed.connect(self._on_stage_display_destroyed)
        self._stage_display_window.retranslate_ui()
        self._apply_settings_to_windows()
        self._stage_display_window.show()
        self._stage_display_window.raise_()
        self._stage_display_window.activateWindow()
        self._refresh_stage_display()
        self._refresh_window_buttons()

    def _close_stage_display(self) -> None:
        if self._stage_display_window is None:
            return
        window = self._stage_display_window
        self._stage_display_window = None
        window.close()
        self._refresh_window_buttons()

    def _on_stage_display_destroyed(self, _obj=None) -> None:
        self._stage_display_window = None
        self._refresh_window_buttons()

    def _refresh_stage_display(self) -> None:
        if self._stage_display_window is None or not self._stage_display_window.isVisible():
            return
        track = self._primary_track()
        progress_percent = 0
        total_time = "00:00:00"
        elapsed = "00:00:00"
        remaining = "00:00:00"
        song_name = self._current_song_title()
        next_song = self._next_song_title()
        if track:
            total_time = str(track.get("duration", "00:00:00") or "00:00:00")
            elapsed = str(track.get("position", "00:00:00") or "00:00:00")
            remaining = str(track.get("remaining", "00:00:00") or "00:00:00")
            try:
                duration_ms = max(0, int(track.get("duration_ms", 0)))
                position_ms = max(0, int(track.get("position_ms", 0)))
                progress_percent = 0 if duration_ms <= 0 else int(max(0.0, min(100.0, (position_ms / float(duration_ms)) * 100.0)))
            except Exception:
                progress_percent = 0
        self._stage_display_window.update_values(
            total_time=total_time,
            elapsed=elapsed,
            remaining=remaining,
            progress_percent=progress_percent,
            song_name=song_name,
            lyric=self._resolved_lyric_html() if not bool(self._ws_state.get("blank")) else "",
            next_song=next_song,
            progress_text=f"{progress_percent}%",
            progress_style="",
        )
        self._stage_display_window.set_alert(
            str(self._api_state.get("alert_message", "") or ""),
            bool(self._api_state.get("alert_active", False)),
        )
        self._stage_display_window.set_playback_status(self._playback_status())

    def _primary_track(self) -> dict[str, Any]:
        tracks = self._api_state.get("playing_tracks")
        if not isinstance(tracks, list) or not tracks:
            return {}
        track = tracks[0]
        return dict(track) if isinstance(track, dict) else {}

    def _current_song_title(self) -> str:
        slide = self._current_slide()
        title = str(slide.get("title", "") or "").strip()
        if title:
            return title
        service_items = self._lyric_bundle.get("service_items")
        if isinstance(service_items, list):
            for item in service_items:
                if isinstance(item, dict) and bool(item.get("selected")):
                    title = str(item.get("title", "") or "").strip()
                    if title:
                        return title
        track = self._primary_track()
        return str(track.get("title", "") or "-").strip() or "-"

    def _next_song_title(self) -> str:
        service_items = self._lyric_bundle.get("service_items")
        if isinstance(service_items, list):
            for item in service_items:
                if isinstance(item, dict) and not bool(item.get("selected")):
                    title = str(item.get("title", "") or "").strip()
                    if title:
                        return title
        return "-"

    def _playback_status(self) -> str:
        tracks = self._api_state.get("playing_tracks")
        if isinstance(tracks, list):
            for item in tracks:
                if not isinstance(item, dict):
                    continue
                state = str(item.get("state", "") or "").strip().lower()
                if state == "playing":
                    return "playing"
            for item in tracks:
                if not isinstance(item, dict):
                    continue
                state = str(item.get("state", "") or "").strip().lower()
                if state == "paused":
                    return "paused"
        return "not_playing"
