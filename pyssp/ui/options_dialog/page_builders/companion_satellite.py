from __future__ import annotations

from ..shared import *


class CompanionSatellitePageMixin:
    def _build_companion_satellite_page(
        self,
        *,
        host: str,
        port: int,
        enabled: bool,
        bypass: bool,
        columns: int,
        rows: int,
        render_mode: str,
        serial_suffix: str,
        command_mode: str,
        command_tcp_port: int,
        command_udp_port: int,
        command_http_port: int,
        warn_dual_automation_sources: bool,
        automation_script_editor_show_lyric: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()

        self.companion_satellite_host_edit = QLineEdit(str(host or "").strip() or "127.0.0.1")
        form.addRow(tr("Companion IP / Hostname:"), self.companion_satellite_host_edit)

        self.companion_satellite_port_spin = QSpinBox()
        self.companion_satellite_port_spin.setRange(1, 65535)
        self.companion_satellite_port_spin.setValue(max(1, min(65535, int(port))))
        form.addRow(tr("Companion Port:"), self.companion_satellite_port_spin)

        self.companion_satellite_enabled_checkbox = QCheckBox(tr("Enable Companion Satellite at pySSP startup"))
        self.companion_satellite_enabled_checkbox.setChecked(bool(enabled))
        form.addRow(tr("Companion Satellite:"), self.companion_satellite_enabled_checkbox)

        self.companion_bypass_checkbox = QCheckBox(tr("Bypass Companion remote commands"))
        self.companion_bypass_checkbox.setChecked(bool(bypass))
        form.addRow(tr("Companion Bypass:"), self.companion_bypass_checkbox)

        self.warn_dual_automation_sources_checkbox = QCheckBox(
            tr("Warn when both Sound Button Automation and Automation Script are linked to the same sound button")
        )
        self.warn_dual_automation_sources_checkbox.setChecked(bool(warn_dual_automation_sources))
        form.addRow(tr("Automation Warning:"), self.warn_dual_automation_sources_checkbox)

        self.automation_script_editor_show_lyric_checkbox = QCheckBox(
            tr("Show lyric by default in Automation Script Editor")
        )
        self.automation_script_editor_show_lyric_checkbox.setChecked(bool(automation_script_editor_show_lyric))
        form.addRow(tr("Automation Script Editor:"), self.automation_script_editor_show_lyric_checkbox)

        self.companion_satellite_columns_spin = QSpinBox()
        self.companion_satellite_columns_spin.setRange(1, 12)
        self.companion_satellite_columns_spin.setValue(max(1, min(12, int(columns))))
        form.addRow(tr("Grid Columns:"), self.companion_satellite_columns_spin)

        self.companion_satellite_rows_spin = QSpinBox()
        self.companion_satellite_rows_spin.setRange(1, 8)
        self.companion_satellite_rows_spin.setValue(max(1, min(8, int(rows))))
        form.addRow(tr("Grid Rows:"), self.companion_satellite_rows_spin)

        self.companion_satellite_render_mode_combo = QComboBox()
        self.companion_satellite_render_mode_combo.addItem(tr("Bitmap"), "bitmap")
        self.companion_satellite_render_mode_combo.addItem(tr("Styled Buttons"), "styled")
        render_index = self.companion_satellite_render_mode_combo.findData(
            str(render_mode or "").strip().lower()
        )
        self.companion_satellite_render_mode_combo.setCurrentIndex(render_index if render_index >= 0 else 0)
        form.addRow(tr("Button Rendering:"), self.companion_satellite_render_mode_combo)

        serial_row = QHBoxLayout()
        self.companion_satellite_serial_prefix_label = QLabel("pyssp:")
        self.companion_satellite_serial_suffix_edit = QLineEdit(
            str(serial_suffix or "").strip() or default_companion_satellite_serial_suffix()
        )
        serial_row.addWidget(self.companion_satellite_serial_prefix_label)
        serial_row.addWidget(self.companion_satellite_serial_suffix_edit, 1)
        form.addRow(tr("Serial Suffix:"), serial_row)

        serial_warning = QLabel(
            tr("If two Companion Satellite clients use the same serial number, Companion may not distinguish them correctly.")
        )
        serial_warning.setWordWrap(True)
        form.addRow("", serial_warning)

        command_mode_row = QHBoxLayout()
        self.companion_command_mode_group = QButtonGroup(page)
        self.companion_command_mode_tcp_radio = QRadioButton("TCP")
        self.companion_command_mode_udp_radio = QRadioButton("UDP")
        self.companion_command_mode_http_radio = QRadioButton("HTTP")
        self.companion_command_mode_group.addButton(self.companion_command_mode_tcp_radio)
        self.companion_command_mode_group.addButton(self.companion_command_mode_udp_radio)
        self.companion_command_mode_group.addButton(self.companion_command_mode_http_radio)
        command_mode_row.addWidget(self.companion_command_mode_tcp_radio)
        command_mode_row.addWidget(self.companion_command_mode_udp_radio)
        command_mode_row.addWidget(self.companion_command_mode_http_radio)
        command_mode_row.addStretch(1)
        token = str(command_mode or "").strip().lower()
        if token == "udp":
            self.companion_command_mode_udp_radio.setChecked(True)
        elif token == "http":
            self.companion_command_mode_http_radio.setChecked(True)
        else:
            self.companion_command_mode_tcp_radio.setChecked(True)
        form.addRow(tr("Command Mode:"), command_mode_row)

        self.companion_command_tcp_port_spin = QSpinBox()
        self.companion_command_tcp_port_spin.setRange(1, 65535)
        self.companion_command_tcp_port_spin.setValue(max(1, min(65535, int(command_tcp_port))))
        form.addRow(tr("Command TCP Port:"), self.companion_command_tcp_port_spin)

        self.companion_command_udp_port_spin = QSpinBox()
        self.companion_command_udp_port_spin.setRange(1, 65535)
        self.companion_command_udp_port_spin.setValue(max(1, min(65535, int(command_udp_port))))
        form.addRow(tr("Command UDP Port:"), self.companion_command_udp_port_spin)

        self.companion_command_http_port_spin = QSpinBox()
        self.companion_command_http_port_spin.setRange(1, 65535)
        self.companion_command_http_port_spin.setValue(max(1, min(65535, int(command_http_port))))
        form.addRow(tr("Command HTTP Port:"), self.companion_command_http_port_spin)

        enabled_note = QLabel(
            tr("When enabled, pySSP starts the Companion Satellite client automatically at startup.")
        )
        enabled_note.setWordWrap(True)
        form.addRow("", enabled_note)

        command_note = QLabel(
            tr("Available Commands sends Companion remote-control commands to the same host using the selected mode and port.")
        )
        command_note.setWordWrap(True)
        form.addRow("", command_note)

        bypass_note = QLabel(
            tr("When bypass is enabled, Companion TCP/UDP/HTTP remote commands do not send. Satellite mode still works normally.")
        )
        bypass_note.setWordWrap(True)
        form.addRow("", bypass_note)

        layout.addLayout(form)
        note = QLabel(
            tr("pySSP will connect to Companion's Satellite API as one virtual surface and render the configured grid.")
            + " "
            + tr("The effective serial is always pyssp:<suffix>.")
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page
