from __future__ import annotations

import os
from typing import Callable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from pyssp.automation_script import (
    AutomationScriptCue,
    automation_script_cue_command_summary,
    find_automation_script_cue_indices,
    load_automation_script,
)
from pyssp.i18n import localize_widget_tree, tr


class AutomationScriptNavigatorWindow(QWidget):
    def __init__(
        self,
        *,
        on_seek_to_ms: Callable[[int], None],
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Automation Script Navigator"))
        self.resize(860, 560)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._on_seek_to_ms = on_seek_to_ms
        self._cache_path: str = ""
        self._cache_mtime: float = -1.0
        self._cache_rows: List[AutomationScriptCue] = []
        self._cache_error: str = ""
        self._rows: List[AutomationScriptCue] = []
        self._current_script_path: str = ""
        self._active_row = -1
        self._track_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._table = QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Comment"), tr("Commands")])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.cellClicked.connect(self._on_cell_clicked)
        root.addWidget(self._table, 1)

        localize_widget_tree(self, language)

    def retranslate_ui(self, language: str = "en") -> None:
        self.setWindowTitle(tr("Automation Script Navigator"))
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Comment"), tr("Commands")])
        localize_widget_tree(self, language)

    def clear(self) -> None:
        self._track_active = False
        self._rows = []
        self._current_script_path = ""
        self._active_row = -1
        self._status_label.setText("")
        self._table.setRowCount(0)

    def update_playback_state(
        self,
        *,
        has_active_track: bool,
        script_path: str,
        position_ms: int,
        force: bool = False,
    ) -> None:
        self._track_active = bool(has_active_track)
        if not has_active_track:
            self.clear()
            return

        path = str(script_path or "").strip()
        if not path:
            self._status_label.setText("No automation script assigned for this sound.")
            self._rows = []
            self._table.setRowCount(0)
            return
        if not os.path.exists(path):
            self._status_label.setText(f"Automation script not found:\n{path}")
            self._rows = []
            self._table.setRowCount(0)
            return

        rows, error = self._load_rows(path)
        if error:
            self._status_label.setText(error)
            self._rows = []
            self._current_script_path = ""
            self._table.setRowCount(0)
            return
        self._status_label.setText(path)
        if force or self._rows != rows or self._current_script_path != path:
            self._rows = list(rows)
            self._current_script_path = path
            self._table.setRowCount(0)
            for row_idx, cue in enumerate(self._rows):
                self._table.insertRow(row_idx)
                ts_item = QTableWidgetItem(self._format_timestamp(int(cue.time_ms)))
                ts_item.setFlags(ts_item.flags() & ~Qt.ItemIsEditable)
                comment_item = QTableWidgetItem(str(cue.comment or ""))
                comment_item.setFlags(comment_item.flags() & ~Qt.ItemIsEditable)
                command_item = QTableWidgetItem(automation_script_cue_command_summary(cue))
                command_item.setFlags(command_item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(row_idx, 0, ts_item)
                self._table.setItem(row_idx, 1, comment_item)
                self._table.setItem(row_idx, 2, command_item)

        current_index, _next_index = find_automation_script_cue_indices({"cues": self._rows}, position_ms)
        self._highlight_row(current_index)

    def _load_rows(self, script_path: str) -> tuple[List[AutomationScriptCue], str]:
        try:
            mtime = os.path.getmtime(script_path)
        except OSError:
            return [], f"Automation script not found:\n{script_path}"
        if script_path == self._cache_path and abs(mtime - self._cache_mtime) < 0.0001:
            return self._cache_rows, self._cache_error
        try:
            script = load_automation_script(script_path)
            rows = list(script.cues or [])
            error = ""
        except Exception as exc:
            rows = []
            error = f"Failed to read automation script:\n{exc}"
        self._cache_path = script_path
        self._cache_mtime = mtime
        self._cache_rows = rows
        self._cache_error = error
        return rows, error

    def _highlight_row(self, row: int) -> None:
        if row < 0 or row >= len(self._rows):
            self._active_row = -1
            self._table.clearSelection()
            return
        if row == self._active_row:
            return
        self._active_row = row
        self._table.selectRow(row)
        item = self._table.item(row, 0)
        if item is not None:
            self._table.scrollToItem(item, QTableWidget.PositionAtCenter)

    def _on_cell_clicked(self, row: int, _column: int) -> None:
        if not self._track_active:
            return
        if row < 0 or row >= len(self._rows):
            return
        self._on_seek_to_ms(max(0, int(self._rows[row].time_ms)))

    @staticmethod
    def _format_timestamp(ms: int) -> str:
        value = max(0, int(ms))
        hours = value // 3600000
        minutes = (value // 60000) % 60
        seconds = (value // 1000) % 60
        millis = value % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
