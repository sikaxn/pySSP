from __future__ import annotations

from ..shared import *
from ..widgets import *


class WebRemotePageMixin:
    def _build_web_remote_page(
        self,
        web_remote_enabled: bool,
        web_remote_port: int,
        web_remote_url: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.web_remote_enabled_checkbox = QCheckBox("Enable Web Remote (Flask API)")
        self.web_remote_enabled_checkbox.setChecked(web_remote_enabled)
        form.addRow("Web Remote:", self.web_remote_enabled_checkbox)
        self.web_remote_port_spin = QSpinBox()
        self.web_remote_port_spin.setRange(1, 65534)
        self.web_remote_port_spin.setValue(max(1, min(65534, int(web_remote_port))))
        form.addRow("Port:", self.web_remote_port_spin)
        self.web_remote_ws_port_value = QLabel("")
        self.web_remote_ws_port_value.setWordWrap(True)
        form.addRow("WS Port (auto):", self.web_remote_ws_port_value)
        parsed = urlparse(web_remote_url.strip() or "http://127.0.0.1:5050/")
        self._web_remote_url_scheme = parsed.scheme or "http"
        self._web_remote_url_host = parsed.hostname or "127.0.0.1"
        self.web_remote_url_value = QLabel("")
        self.web_remote_url_value.setOpenExternalLinks(True)
        self.web_remote_url_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.web_remote_url_value.setWordWrap(True)
        form.addRow("Open URL:", self.web_remote_url_value)
        self._set_web_remote_url_label(self._build_web_remote_url_text(self.web_remote_port_spin.value()))
        self._set_web_remote_ws_port_label(self._build_web_remote_ws_port_text(self.web_remote_port_spin.value()))
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
        return page

