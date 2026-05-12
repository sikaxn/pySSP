from __future__ import annotations

from ..shared import *
from ..widgets import *


class WebRemotePageMixin:
    def _build_web_remote_page(
        self,
        web_remote_enabled: bool,
        web_remote_port: int,
        web_remote_http_url: str,
        web_remote_https_enabled: bool,
        web_remote_enforce_https: bool,
        web_remote_require_authentication: bool,
        web_remote_username: str,
        web_remote_password: str,
        web_remote_guest_view_enabled: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.web_remote_enabled_checkbox = QCheckBox("Enable Web Remote (Flask API)")
        self.web_remote_enabled_checkbox.setChecked(web_remote_enabled)
        form.addRow("Web Remote:", self.web_remote_enabled_checkbox)
        self.web_remote_port_spin = QSpinBox()
        self.web_remote_port_spin.setRange(1, 65532)
        self.web_remote_port_spin.setValue(max(1, min(65532, int(web_remote_port))))
        form.addRow("Port:", self.web_remote_port_spin)
        self.web_remote_ws_port_value = QLabel("")
        self.web_remote_ws_port_value.setWordWrap(True)
        form.addRow("WS Port (auto):", self.web_remote_ws_port_value)
        self.web_remote_https_port_value = QLabel("")
        self.web_remote_https_port_value.setWordWrap(True)
        form.addRow("HTTPS Port (auto):", self.web_remote_https_port_value)
        self.web_remote_wss_port_value = QLabel("")
        self.web_remote_wss_port_value.setWordWrap(True)
        form.addRow("WSS Port (auto):", self.web_remote_wss_port_value)
        parsed = urlparse(web_remote_http_url.strip() or "http://127.0.0.1:5050/")
        self._web_remote_url_host = parsed.hostname or "127.0.0.1"
        self.web_remote_url_value = QLabel("")
        self.web_remote_url_value.setOpenExternalLinks(True)
        self.web_remote_url_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.web_remote_url_value.setWordWrap(True)
        form.addRow("HTTP URL:", self.web_remote_url_value)
        self.web_remote_https_url_value = QLabel("")
        self.web_remote_https_url_value.setOpenExternalLinks(True)
        self.web_remote_https_url_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.web_remote_https_url_value.setWordWrap(True)
        form.addRow("HTTPS URL:", self.web_remote_https_url_value)
        self.web_remote_https_enabled_checkbox = QCheckBox("Enable HTTPS + WSS (self-signed certificate)")
        self.web_remote_https_enabled_checkbox.setChecked(bool(web_remote_https_enabled))
        form.addRow("HTTPS:", self.web_remote_https_enabled_checkbox)
        self.web_remote_enforce_https_checkbox = QCheckBox("Enforce HTTPS and WSS only")
        self.web_remote_enforce_https_checkbox.setChecked(bool(web_remote_enforce_https))
        form.addRow("", self.web_remote_enforce_https_checkbox)
        self.web_remote_require_authentication_checkbox = QCheckBox("Require authentication (HTTP Basic Auth)")
        self.web_remote_require_authentication_checkbox.setChecked(bool(web_remote_require_authentication))
        form.addRow("Authentication:", self.web_remote_require_authentication_checkbox)
        self.web_remote_username_edit = QLineEdit(str(web_remote_username or "").strip() or "admin")
        form.addRow("Username:", self.web_remote_username_edit)
        self.web_remote_password_edit = QLineEdit(str(web_remote_password or ""))
        self.web_remote_password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Password:", self.web_remote_password_edit)
        self.web_remote_guest_view_checkbox = QCheckBox("Allow built-in guest user view-only access")
        self.web_remote_guest_view_checkbox.setChecked(bool(web_remote_guest_view_enabled))
        form.addRow("Guest:", self.web_remote_guest_view_checkbox)
        self.web_remote_guest_note_label = QLabel(
            tr("Guest login uses username ")
            + "<b>guest</b>"
            + tr(" with an empty password. Guests can view Web Remote state and use lyric/stage display, but cannot control playback.")
        )
        self.web_remote_guest_note_label.setWordWrap(True)
        form.addRow("", self.web_remote_guest_note_label)
        self._set_web_remote_url_label(self._build_web_remote_url_text(self.web_remote_port_spin.value()))
        self._set_web_remote_ws_port_label(self._build_web_remote_ws_port_text(self.web_remote_port_spin.value()))
        self._set_web_remote_https_url_label(self._build_web_remote_https_url_text(self.web_remote_port_spin.value() + 2))
        self._set_web_remote_https_port_label(self._build_web_remote_https_port_text(self.web_remote_port_spin.value()))
        self._set_web_remote_wss_port_label(self._build_web_remote_wss_port_text(self.web_remote_port_spin.value()))
        layout.addLayout(form)

        companion_group = QGroupBox(tr("Bitfocus Companion"))
        companion_layout = QVBoxLayout(companion_group)
        self.web_remote_companion_link_value = QLabel(
            tr("Bitfocus Companion is a button-based control and automation tool for production systems. Learn more at ")
            + " "
            '<a href="https://bitfocus.io/companion">bitfocus.io/companion</a>.'
        )
        self.web_remote_companion_link_value.setOpenExternalLinks(True)
        self.web_remote_companion_link_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.web_remote_companion_link_value.setWordWrap(True)
        companion_layout.addWidget(self.web_remote_companion_link_value)
        self.web_remote_companion_setup_value = QLabel("")
        self.web_remote_companion_setup_value.setWordWrap(True)
        companion_layout.addWidget(self.web_remote_companion_setup_value)
        self.web_remote_companion_ip_value = QLabel("")
        self.web_remote_companion_ip_value.setWordWrap(True)
        companion_layout.addWidget(self.web_remote_companion_ip_value)
        self.web_remote_companion_port_value = QLabel("")
        self.web_remote_companion_port_value.setWordWrap(True)
        companion_layout.addWidget(self.web_remote_companion_port_value)
        self.web_remote_companion_default_value = QLabel("")
        self.web_remote_companion_default_value.setWordWrap(True)
        companion_layout.addWidget(self.web_remote_companion_default_value)
        layout.addWidget(companion_group)
        layout.addStretch(1)
        self._set_web_remote_companion_text(self.web_remote_port_spin.value())
        self.web_remote_port_spin.valueChanged.connect(
            lambda value: self._update_web_remote_page_labels(int(value))
        )
        self.web_remote_require_authentication_checkbox.toggled.connect(self._update_web_remote_auth_controls)
        self.web_remote_guest_view_checkbox.toggled.connect(self._update_web_remote_auth_controls)
        self.web_remote_https_enabled_checkbox.toggled.connect(self._update_web_remote_https_controls)
        self.web_remote_enforce_https_checkbox.toggled.connect(self._update_web_remote_https_controls)
        self._update_web_remote_auth_controls()
        self._update_web_remote_https_controls()
        return page

    def _update_web_remote_auth_controls(self) -> None:
        auth_enabled = bool(self.web_remote_require_authentication_checkbox.isChecked())
        self.web_remote_username_edit.setEnabled(auth_enabled)
        self.web_remote_password_edit.setEnabled(auth_enabled)
        self.web_remote_guest_view_checkbox.setEnabled(auth_enabled)
        self.web_remote_guest_note_label.setVisible(
            auth_enabled and bool(self.web_remote_guest_view_checkbox.isChecked())
        )

    def _update_web_remote_https_controls(self) -> None:
        https_enabled = bool(self.web_remote_https_enabled_checkbox.isChecked())
        if bool(self.web_remote_enforce_https_checkbox.isChecked()) and not https_enabled:
            self.web_remote_https_enabled_checkbox.setChecked(True)
            https_enabled = True
        self.web_remote_enforce_https_checkbox.setEnabled(https_enabled)

