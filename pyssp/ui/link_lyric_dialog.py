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
from pyssp.i18n import localize_widget_tree, tr


class LinkLyricDialog(QDialog):
    def __init__(self, rows: List[Tuple[str, str]], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Lyric File Found"))
        self.setModal(True)
        self.resize(920, 460)
        self._row_count = len(rows)

        root = QVBoxLayout(self)
        note = QLabel(tr("Matching lyric files were found. Check whether to link each lyric file."), self)
        note.setWordWrap(True)
        root.addWidget(note)

        self.table = QTableWidget(self._row_count, 3, self)
        self.table.setHorizontalHeaderLabels([tr("Audio File"), tr("Lyric File Found"), tr("Link")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, self.table.horizontalHeader().Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, self.table.horizontalHeader().ResizeToContents)

        for row_index, (audio_path, lyric_path) in enumerate(rows):
            audio_item = QTableWidgetItem(os.path.basename(audio_path) or audio_path)
            audio_item.setToolTip(audio_path)
            self.table.setItem(row_index, 0, audio_item)

            lyric_text = os.path.basename(lyric_path) if lyric_path else tr("(not found)")
            lyric_item = QTableWidgetItem(lyric_text)
            lyric_item.setToolTip(lyric_path or "")
            self.table.setItem(row_index, 1, lyric_item)

            check_item = QTableWidgetItem("")
            check_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            if lyric_path:
                check_item.setCheckState(Qt.Checked)
            else:
                check_item.setCheckState(Qt.Unchecked)
                check_item.setFlags(Qt.NoItemFlags)
            self.table.setItem(row_index, 2, check_item)

        root.addWidget(self.table, 1)

        action_row = QHBoxLayout()
        link_all_btn = QPushButton(tr("Link All Found"), self)
        unlink_all_btn = QPushButton(tr("Unlink All"), self)
        link_all_btn.clicked.connect(self._link_all_found)
        unlink_all_btn.clicked.connect(self._unlink_all)
        action_row.addWidget(link_all_btn)
        action_row.addWidget(unlink_all_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        localize_widget_tree(self)

    def link_flags(self) -> List[bool]:
        flags: List[bool] = []
        for row_index in range(self._row_count):
            item = self.table.item(row_index, 2)
            if item is None:
                flags.append(False)
                continue
            if not (item.flags() & Qt.ItemIsEnabled):
                flags.append(False)
                continue
            flags.append(item.checkState() == Qt.Checked)
        return flags

    def _link_all_found(self) -> None:
        for row_index in range(self._row_count):
            item = self.table.item(row_index, 2)
            if item is None:
                continue
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(Qt.Checked)

    def _unlink_all(self) -> None:
        for row_index in range(self._row_count):
            item = self.table.item(row_index, 2)
            if item is None:
                continue
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(Qt.Unchecked)
