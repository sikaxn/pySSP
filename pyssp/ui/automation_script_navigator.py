from __future__ import annotations

import os
from typing import Callable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from pyssp.automation_script import (
    AutomationScriptCue,
    automation_script_cue_command_summary,
    load_automation_script,
)
from pyssp.i18n import localize_widget_tree, tr
from pyssp.lyrics import parse_lyric_file


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
        self._cache_script_path: str = ""
        self._cache_script_mtime: float = -1.0
        self._cache_lyric_path: str = ""
        self._cache_lyric_mtime: float = -1.0
        self._cache_rows: List[dict] = []
        self._cache_error: str = ""
        self._rows: List[dict] = []
        self._current_script_path: str = ""
        self._active_row = -1
        self._track_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Type"), tr("Comment / Lyric"), tr("Commands")])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.cellClicked.connect(self._on_cell_clicked)
        root.addWidget(self._table, 1)

        localize_widget_tree(self, language)

    def retranslate_ui(self, language: str = "en") -> None:
        self.setWindowTitle(tr("Automation Script Navigator"))
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Type"), tr("Comment / Lyric"), tr("Commands")])
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
        lyric_path: str = "",
        position_ms: int,
        force: bool = False,
    ) -> None:
        self._track_active = bool(has_active_track)
        if not has_active_track:
            self.clear()
            return

        path = str(script_path or "").strip()
        lyric_file_path = str(lyric_path or "").strip()
        if not path and not lyric_file_path:
            self._status_label.setText(tr("No automation script assigned for this sound."))
            self._rows = []
            self._table.setRowCount(0)
            return
        if path and not os.path.exists(path):
            self._status_label.setText(tr("Automation script not found:\n{path}").format(path=path))
            self._rows = []
            self._table.setRowCount(0)
            return
        if lyric_file_path and not os.path.exists(lyric_file_path):
            lyric_file_path = ""

        rows, error = self._load_rows(path, lyric_file_path)
        if error:
            self._status_label.setText(error)
            self._rows = []
            self._current_script_path = ""
            self._table.setRowCount(0)
            return
        status_lines = []
        if path:
            status_lines.append(path)
        if lyric_file_path:
            status_lines.append(lyric_file_path)
        self._status_label.setText("\n".join(status_lines))
        if force or self._rows != rows or self._current_script_path != path:
            self._rows = list(rows)
            self._current_script_path = path
            self._table.setRowCount(0)
            for row_idx, row in enumerate(self._rows):
                self._table.insertRow(row_idx)
                ts_item = QTableWidgetItem(self._format_timestamp(int(row["time_ms"])))
                ts_item.setFlags(ts_item.flags() & ~Qt.ItemIsEditable)
                type_item = QTableWidgetItem(tr("Cue") if row["kind"] == "cue" else tr("Lyric"))
                type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
                comment_item = QTableWidgetItem(str(row.get("comment", "") or ""))
                comment_item.setFlags(comment_item.flags() & ~Qt.ItemIsEditable)
                command_item = QTableWidgetItem(str(row.get("commands", "") or ""))
                command_item.setFlags(command_item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(row_idx, 0, ts_item)
                self._table.setItem(row_idx, 1, type_item)
                self._table.setItem(row_idx, 2, comment_item)
                self._table.setItem(row_idx, 3, command_item)

        self._highlight_row(self._row_index_for_position(position_ms))

    def _load_rows(self, script_path: str, lyric_path: str) -> tuple[List[dict], str]:
        try:
            script_mtime = os.path.getmtime(script_path) if script_path else -1.0
        except OSError:
            return [], tr("Automation script not found:\n{path}").format(path=script_path)
        try:
            lyric_mtime = os.path.getmtime(lyric_path) if lyric_path else -1.0
        except OSError:
            lyric_mtime = -1.0
        if (
            script_path == self._cache_script_path
            and lyric_path == self._cache_lyric_path
            and abs(script_mtime - self._cache_script_mtime) < 0.0001
            and abs(lyric_mtime - self._cache_lyric_mtime) < 0.0001
        ):
            return self._cache_rows, self._cache_error
        try:
            rows: List[dict] = []
            if script_path:
                script = load_automation_script(script_path)
                for cue in list(script.cues or []):
                    rows.append(
                        {
                            "kind": "cue",
                            "time_ms": int(cue.time_ms),
                            "comment": str(cue.comment or ""),
                            "commands": automation_script_cue_command_summary(cue),
                        }
                    )
            if lyric_path:
                for line in list(parse_lyric_file(lyric_path) or []):
                    rows.append(
                        {
                            "kind": "lyric",
                            "time_ms": int(line.start_ms),
                            "comment": str(line.text or ""),
                            "commands": tr("Reference"),
                        }
                    )
            rows.sort(key=lambda entry: (int(entry["time_ms"]), 0 if entry["kind"] == "cue" else 1))
            error = ""
        except Exception as exc:
            rows = []
            error = f"{tr('Failed to read automation script:')}\n{exc}"
        self._cache_script_path = script_path
        self._cache_script_mtime = script_mtime
        self._cache_lyric_path = lyric_path
        self._cache_lyric_mtime = lyric_mtime
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
        self._on_seek_to_ms(max(0, int(self._rows[row]["time_ms"])))

    def _row_index_for_position(self, position_ms: int) -> int:
        row = -1
        for index, item in enumerate(self._rows):
            if int(item["time_ms"]) <= max(0, int(position_ms)):
                row = index
            else:
                break
        return row

    @staticmethod
    def _format_timestamp(ms: int) -> str:
        value = max(0, int(ms))
        hours = value // 3600000
        minutes = (value // 60000) % 60
        seconds = (value // 1000) % 60
        millis = value % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
