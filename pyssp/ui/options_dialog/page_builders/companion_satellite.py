from __future__ import annotations

from ..shared import *


class CompanionSatellitePageMixin:
    def _build_companion_satellite_page(
        self,
        *,
        host: str,
        port: int,
        start_mode: str,
        columns: int,
        rows: int,
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

        self.companion_satellite_start_mode_combo = QComboBox()
        self.companion_satellite_start_mode_combo.addItem("Manual start", "manual")
        self.companion_satellite_start_mode_combo.addItem("Auto when enabled", "auto")
        self.companion_satellite_start_mode_combo.addItem("Connect on open", "open")
        start_index = self.companion_satellite_start_mode_combo.findData(str(start_mode or "manual").strip().lower())
        self.companion_satellite_start_mode_combo.setCurrentIndex(start_index if start_index >= 0 else 0)
        form.addRow("Startup Behavior:", self.companion_satellite_start_mode_combo)

        self.companion_satellite_columns_spin = QSpinBox()
        self.companion_satellite_columns_spin.setRange(1, 12)
        self.companion_satellite_columns_spin.setValue(max(1, min(12, int(columns))))
        form.addRow("Grid Columns:", self.companion_satellite_columns_spin)

        self.companion_satellite_rows_spin = QSpinBox()
        self.companion_satellite_rows_spin.setRange(1, 8)
        self.companion_satellite_rows_spin.setValue(max(1, min(8, int(rows))))
        form.addRow("Grid Rows:", self.companion_satellite_rows_spin)

        layout.addLayout(form)
        note = QLabel(
            "pySSP will connect to Companion's Satellite API as one virtual surface and render the configured grid."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page
