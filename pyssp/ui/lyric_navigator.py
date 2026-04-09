from __future__ import annotations

import os
from typing import Callable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from pyssp.i18n import localize_widget_tree, tr
from pyssp.lyrics import LyricLine, parse_lyric_file


class LyricNavigatorWindow(QWidget):
    def __init__(
        self,
        *,
        on_seek_to_ms: Callable[[int], None],
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Lyric Navigator"))
        self.resize(780, 560)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._on_seek_to_ms = on_seek_to_ms
        self._cache_path: str = ""
        self._cache_mtime: float = -1.0
        self._cache_lines: List[LyricLine] = []
        self._cache_error: str = ""
        self._rows: List[LyricLine] = []
        self._current_lyric_path: str = ""
        self._active_row = -1
        self._track_active = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Lyric")])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.cellClicked.connect(self._on_cell_clicked)
        root.addWidget(self._table, 1)

        localize_widget_tree(self, language)

    def retranslate_ui(self, language: str = "en") -> None:
        self.setWindowTitle(tr("Lyric Navigator"))
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Lyric")])
        localize_widget_tree(self, language)

    def clear(self) -> None:
        self._track_active = False
        self._rows = []
        self._current_lyric_path = ""
        self._active_row = -1
        self._status_label.setText("")
        self._table.setRowCount(0)

    def update_playback_state(
        self,
        *,
        has_active_track: bool,
        lyric_path: str,
        position_ms: int,
        force: bool = False,
    ) -> None:
        self._track_active = bool(has_active_track)
        if not has_active_track:
            self.clear()
            return

        path = str(lyric_path or "").strip()
        if not path:
            self._status_label.setText("No lyric file assigned for this sound.")
            self._rows = []
            self._table.setRowCount(0)
            return
        if not os.path.exists(path):
            self._status_label.setText(f"Lyric file not found:\n{path}")
            self._rows = []
            self._table.setRowCount(0)
            return

        lines, error = self._load_lyric_lines(path)
        if error:
            self._status_label.setText(error)
            self._rows = []
            self._current_lyric_path = ""
            self._table.setRowCount(0)
            return
        self._status_label.setText(path)
        if force or self._rows != lines or self._current_lyric_path != path:
            self._rows = list(lines)
            self._current_lyric_path = path
            self._table.setRowCount(0)
            for row_idx, line in enumerate(self._rows):
                self._table.insertRow(row_idx)
                ts_item = QTableWidgetItem(self._format_timestamp(path, line.start_ms))
                ts_item.setFlags(ts_item.flags() & ~Qt.ItemIsEditable)
                lyric_item = QTableWidgetItem(str(line.text or ""))
                lyric_item.setFlags(lyric_item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(row_idx, 0, ts_item)
                self._table.setItem(row_idx, 1, lyric_item)

        self._highlight_row_for_position(max(0, int(position_ms)))

    def _load_lyric_lines(self, lyric_path: str) -> tuple[List[LyricLine], str]:
        mtime = -1.0
        try:
            mtime = os.path.getmtime(lyric_path)
        except OSError:
            return [], f"Lyric file not found:\n{lyric_path}"
        if lyric_path == self._cache_path and abs(mtime - self._cache_mtime) < 0.0001:
            return self._cache_lines, self._cache_error
        try:
            lines = parse_lyric_file(lyric_path)
            error = ""
        except Exception as exc:
            lines = []
            error = f"Failed to read lyric file:\n{exc}"
        self._cache_path = lyric_path
        self._cache_mtime = mtime
        self._cache_lines = lines
        self._cache_error = error
        return lines, error

    def _highlight_row_for_position(self, position_ms: int) -> None:
        if not self._rows:
            self._active_row = -1
            self._table.clearSelection()
            return
        row = -1
        for idx, line in enumerate(self._rows):
            if line.start_ms <= position_ms <= line.end_ms:
                row = idx
                break
            if line.start_ms <= position_ms:
                row = idx
        if row < 0:
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
        self._on_seek_to_ms(max(0, int(self._rows[row].start_ms)))

    @staticmethod
    def _format_timestamp(path: str, ms: int) -> str:
        value = max(0, int(ms))
        if os.path.splitext(str(path or "").strip())[1].lower() == ".lrc":
            minutes = value // 60000
            seconds = (value // 1000) % 60
            centi = (value % 1000) // 10
            return f"{minutes:02d}:{seconds:02d}.{centi:02d}"
        hours = value // 3600000
        minutes = (value // 60000) % 60
        seconds = (value // 1000) % 60
        millis = value % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
