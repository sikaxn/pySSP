from __future__ import annotations

import os
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.i18n import localize_widget_tree


class VocalRemovedBatchDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        note: str,
        rows: List[Tuple[str, str, str, bool]],
        target_header: str,
        action_header: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(980, 500)
        self._row_count = len(rows)

        root = QVBoxLayout(self)
        note_label = QLabel(note, self)
        note_label.setWordWrap(True)
        root.addWidget(note_label)

        self.table = QTableWidget(self._row_count, 4, self)
        self.table.setHorizontalHeaderLabels(["Audio File", target_header, "Page", action_header])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, self.table.horizontalHeader().Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, self.table.horizontalHeader().ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, self.table.horizontalHeader().ResizeToContents)

        for row_index, (audio_path, target_path, location, enabled) in enumerate(rows):
            audio_item = QTableWidgetItem(os.path.basename(audio_path) or audio_path)
            audio_item.setToolTip(audio_path)
            self.table.setItem(row_index, 0, audio_item)

            target_text = os.path.basename(target_path) if target_path else "(not found)"
            target_item = QTableWidgetItem(target_text)
            target_item.setToolTip(target_path or "")
            self.table.setItem(row_index, 1, target_item)

            location_item = QTableWidgetItem(location)
            location_item.setToolTip(location)
            self.table.setItem(row_index, 2, location_item)

            check_item = QTableWidgetItem("")
            check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            if enabled:
                check_item.setCheckState(Qt.Checked)
            else:
                check_item.setCheckState(Qt.Unchecked)
                check_item.setFlags(Qt.NoItemFlags)
            self.table.setItem(row_index, 3, check_item)

        root.addWidget(self.table, 1)

        action_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All Eligible", self)
        clear_all_btn = QPushButton("Unselect All", self)
        select_all_btn.clicked.connect(self._select_all)
        clear_all_btn.clicked.connect(self._clear_all)
        action_row.addWidget(select_all_btn)
        action_row.addWidget(clear_all_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        localize_widget_tree(self)

    def checked_flags(self) -> List[bool]:
        flags: List[bool] = []
        for row_index in range(self._row_count):
            item = self.table.item(row_index, 3)
            if item is None:
                flags.append(False)
                continue
            if not (item.flags() & Qt.ItemIsEnabled):
                flags.append(False)
                continue
            flags.append(item.checkState() == Qt.Checked)
        return flags

    def _select_all(self) -> None:
        for row_index in range(self._row_count):
            item = self.table.item(row_index, 3)
            if item is None:
                continue
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(Qt.Checked)

    def _clear_all(self) -> None:
        for row_index in range(self._row_count):
            item = self.table.item(row_index, 3)
            if item is None:
                continue
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(Qt.Unchecked)
