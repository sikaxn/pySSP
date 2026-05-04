from __future__ import annotations

from ..shared import *


class CompanionSatellitePageMixin:
    def _build_companion_satellite_page(
        self,
        *,
        host: str,
        port: int,
        enabled: bool,
        columns: int,
        rows: int,
        render_mode: str,
        serial_suffix: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()

        self.companion_satellite_host_edit = QLineEdit(str(host or "").strip() or "127.0.0.1")
        form.addRow("Companion IP / Hostname:", self.companion_satellite_host_edit)

        self.companion_satellite_port_spin = QSpinBox()
        self.companion_satellite_port_spin.setRange(1, 65535)
        self.companion_satellite_port_spin.setValue(max(1, min(65535, int(port))))
        form.addRow("Companion Port:", self.companion_satellite_port_spin)

        self.companion_satellite_enabled_checkbox = QCheckBox("Enable Companion Satellite at pySSP startup")
        self.companion_satellite_enabled_checkbox.setChecked(bool(enabled))
        form.addRow("Companion Satellite:", self.companion_satellite_enabled_checkbox)

        self.companion_satellite_columns_spin = QSpinBox()
        self.companion_satellite_columns_spin.setRange(1, 12)
        self.companion_satellite_columns_spin.setValue(max(1, min(12, int(columns))))
        form.addRow("Grid Columns:", self.companion_satellite_columns_spin)

        self.companion_satellite_rows_spin = QSpinBox()
        self.companion_satellite_rows_spin.setRange(1, 8)
        self.companion_satellite_rows_spin.setValue(max(1, min(8, int(rows))))
        form.addRow("Grid Rows:", self.companion_satellite_rows_spin)

        self.companion_satellite_render_mode_combo = QComboBox()
        self.companion_satellite_render_mode_combo.addItem("Bitmap", "bitmap")
        self.companion_satellite_render_mode_combo.addItem("Styled Buttons", "styled")
        render_index = self.companion_satellite_render_mode_combo.findData(
            str(render_mode or "").strip().lower()
        )
        self.companion_satellite_render_mode_combo.setCurrentIndex(render_index if render_index >= 0 else 0)
        form.addRow("Button Rendering:", self.companion_satellite_render_mode_combo)

        serial_row = QHBoxLayout()
        self.companion_satellite_serial_prefix_label = QLabel("pyssp:")
        self.companion_satellite_serial_suffix_edit = QLineEdit(
            str(serial_suffix or "").strip() or default_companion_satellite_serial_suffix()
        )
        serial_row.addWidget(self.companion_satellite_serial_prefix_label)
        serial_row.addWidget(self.companion_satellite_serial_suffix_edit, 1)
        form.addRow("Serial Suffix:", serial_row)

        serial_warning = QLabel(
            "If two Companion Satellite clients use the same serial number, Companion may not distinguish them correctly."
        )
        serial_warning.setWordWrap(True)
        form.addRow("", serial_warning)

        enabled_note = QLabel(
            "When enabled, pySSP starts the Companion Satellite client automatically at startup."
        )
        enabled_note.setWordWrap(True)
        form.addRow("", enabled_note)

        layout.addLayout(form)
        note = QLabel(
            "pySSP will connect to Companion's Satellite API as one virtual surface and render the configured grid."
            " The effective serial is always pyssp:<suffix>."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page
