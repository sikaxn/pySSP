from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAbstractItemView, QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout

from pyssp.companion_available_commands import (
    is_black_empty_command,
    is_navigation_command,
    list_companion_available_commands,
)
from pyssp.i18n import tr


class CompanionAvailableCommandsDialog(QDialog):
    locationCommandRequested = pyqtSignal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Available Commands"))
        self.resize(760, 520)

        root = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addStretch(1)
        self.hide_black_empty_checkbox = QCheckBox(tr("Hide Black Empty Buttons"))
        header.addWidget(self.hide_black_empty_checkbox, 0)
        self.hide_navigation_checkbox = QCheckBox(tr("Hide Page Buttons"))
        header.addWidget(self.hide_navigation_checkbox, 0)
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

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.press_button = QPushButton(tr("Press"))
        self.down_button = QPushButton(tr("Down"))
        self.up_button = QPushButton(tr("Up"))
        action_row.addWidget(self.press_button)
        action_row.addWidget(self.down_button)
        action_row.addWidget(self.up_button)
        root.addLayout(action_row)

        self.table.itemDoubleClicked.connect(lambda _item: self._emit_selected_location_command("press"))
        self.press_button.clicked.connect(lambda: self._emit_selected_location_command("press"))
        self.down_button.clicked.connect(lambda: self._emit_selected_location_command("down"))
        self.up_button.clicked.connect(lambda: self._emit_selected_location_command("up"))

    def set_payload(
        self,
        payload: dict,
        *,
        hide_black_empty: bool = False,
        hide_navigation: bool = False,
    ) -> None:
        rows = list_companion_available_commands(payload)
        if hide_black_empty:
            rows = [entry for entry in rows if not is_black_empty_command(entry)]
        if hide_navigation:
            rows = [entry for entry in rows if not is_navigation_command(entry)]
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
