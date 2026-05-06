from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAbstractItemView, QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout

from pyssp.companion_available_commands import (
    is_black_empty_command,
    is_navigation_command,
    list_companion_available_commands,
)
from pyssp.i18n import tr


class CompanionAvailableCommandsDialog(QDialog):
    locationCommandRequested = pyqtSignal(str, str)
    openVirtualSatelliteRequested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Available Commands"))
        self.resize(680, 500)

        root = QVBoxLayout(self)
        header = QHBoxLayout()
        self.hide_black_empty_checkbox = QCheckBox(tr("Hide Black Empty Buttons"))
        header.addWidget(self.hide_black_empty_checkbox, 0)
        self.hide_navigation_checkbox = QCheckBox(tr("Hide Page Buttons"))
        header.addWidget(self.hide_navigation_checkbox, 0)
        header.addStretch(1)
        self.open_virtual_satellite_button = QPushButton(tr("Open Virtual Satellite"))
        header.addWidget(self.open_virtual_satellite_button, 0)
        self.clear_button = QPushButton(tr("Clear List"))
        header.addWidget(self.clear_button, 0)
        root.addLayout(header)

        self.help_label = QLabel(
            tr("To add or update Available Commands, open Virtual Satellite and scroll pages with Page Up and Page Down. The list updates automatically as Companion sends changes.")
        )
        self.help_label.setWordWrap(True)
        root.addWidget(self.help_label, 0)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr("Location"), tr("Type"), tr("Button")])
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel(tr("Search:")), 0)
        self.search_edit = QLineEdit(self)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(tr("Search by location or button text"))
        search_row.addWidget(self.search_edit, 1)
        root.addLayout(search_row)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.press_button = QPushButton(tr("Press"))
        self.down_button = QPushButton(tr("Press Down"))
        self.up_button = QPushButton(tr("Release Up"))
        action_row.addWidget(self.press_button)
        action_row.addWidget(self.down_button)
        action_row.addWidget(self.up_button)
        root.addLayout(action_row)

        self.table.itemDoubleClicked.connect(lambda _item: self._emit_selected_location_command("press"))
        self.press_button.clicked.connect(lambda: self._emit_selected_location_command("press"))
        self.down_button.clicked.connect(lambda: self._emit_selected_location_command("down"))
        self.up_button.clicked.connect(lambda: self._emit_selected_location_command("up"))
        self.search_edit.textChanged.connect(self._apply_filters)
        self.open_virtual_satellite_button.clicked.connect(self.openVirtualSatelliteRequested.emit)

        self._payload: dict = {"pages": {}, "updated_at": ""}

    def set_payload(
        self,
        payload: dict,
        *,
        hide_black_empty: bool = False,
        hide_navigation: bool = False,
    ) -> None:
        self._payload = dict(payload or {"pages": {}, "updated_at": ""})
        self._apply_filters(hide_black_empty=hide_black_empty, hide_navigation=hide_navigation)

    def _apply_filters(
        self,
        _text: str = "",
        *,
        hide_black_empty: bool | None = None,
        hide_navigation: bool | None = None,
    ) -> None:
        rows = list_companion_available_commands(self._payload)
        if hide_black_empty is None:
            hide_black_empty = bool(self.hide_black_empty_checkbox.isChecked())
        if hide_navigation is None:
            hide_navigation = bool(self.hide_navigation_checkbox.isChecked())
        if hide_black_empty:
            rows = [entry for entry in rows if not is_black_empty_command(entry)]
        if hide_navigation:
            rows = [entry for entry in rows if not is_navigation_command(entry)]
        query = str(self.search_edit.text() or "").strip().lower()
        if query:
            rows = [
                entry
                for entry in rows
                if query in f"{entry.get('page', '')}/{entry.get('row', '')}/{entry.get('column', '')}".lower()
                or query in str(entry.get("text", "") or "").lower()
            ]
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            location_value = f"{entry.get('page', '')}/{entry.get('row', '')}/{entry.get('column', '')}"
            location_item = QTableWidgetItem(location_value)
            location_item.setTextAlignment(Qt.AlignCenter)
            location_item.setData(Qt.UserRole, location_value)
            self.table.setItem(row_index, 0, location_item)

            type_item = QTableWidgetItem(str(entry.get("type", "") or ""))
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_index, 1, type_item)

            text_value = str(entry.get("text", "") or "")
            color_value = str(entry.get("color", "") or "")
            button_item = QTableWidgetItem(text_value)
            color = QColor(color_value)
            if color.isValid():
                button_item.setBackground(color)
                button_item.setForeground(QColor(255 - color.red(), 255 - color.green(), 255 - color.blue()))
                button_item.setToolTip(color_value)
            self.table.setItem(row_index, 2, button_item)
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def selected_location(self) -> str:
        row = int(self.table.currentRow())
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.UserRole) or item.text() or "").strip()

    def _emit_selected_location_command(self, action: str) -> None:
        location = self.selected_location()
        if not location:
            return
        self.locationCommandRequested.emit(location, str(action or "").strip().lower())
