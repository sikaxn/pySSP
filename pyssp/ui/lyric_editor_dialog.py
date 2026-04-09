from __future__ import annotations

import os
import re
import time
from typing import Callable, List, Optional, Tuple

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import (
    ExternalMediaPlayer,
    get_audio_preload_runtime_status,
    is_audio_preloaded,
    request_audio_preload,
)
from pyssp.i18n import localize_widget_tree
from pyssp.lyrics import parse_lyric_file
from pyssp.ui.cue_point_dialog import CueRangeIndicator


class LyricEditorDialog(QDialog):
    def __init__(
        self,
        *,
        lyric_path: str,
        audio_path: str,
        title: str,
        language: str = "en",
        preferred_mode: str = "srt",
        cue_start_ms: Optional[int] = None,
        cue_end_ms: Optional[int] = None,
        stop_host_playback: Optional[Callable[[], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Lyric Editor")
        self.resize(860, 590)

        self._lyric_path = str(lyric_path or "").strip()
        self._audio_path = str(audio_path or "").strip()
        self._duration_ms = 0
        self._is_scrubbing = False
        self._is_loading_media = False
        self._load_wait_started = 0.0
        self._load_wait_timeout_sec = 20.0
        self._cue_start_ms = None if cue_start_ms is None else max(0, int(cue_start_ms))
        self._cue_end_ms = None if cue_end_ms is None else max(0, int(cue_end_ms))
        self._stop_host_playback = stop_host_playback

        mode = str(preferred_mode or "").strip().lower()
        if mode not in {"srt", "lrc"}:
            mode = "srt"
        ext = os.path.splitext(self._lyric_path)[1].lower()
        if ext == ".lrc":
            mode = "lrc"
        elif ext == ".srt":
            mode = "srt"
        self._mode = mode
        self._active_row = -1
        self._rapid_undo_stack: List[Tuple[List[Tuple[str, str]], str]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        name = str(title or "").strip() or os.path.basename(self._audio_path or self._lyric_path)
        self._title_label = QLabel(name)
        root.addWidget(self._title_label)

        self._path_label = QLabel(self._lyric_path)
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self._path_label)

        self._player = ExternalMediaPlayer(self)
        self._player.setNotifyInterval(40)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.stateChanged.connect(self._on_state_changed)

        transport = QHBoxLayout()
        self._play_btn = QPushButton("Play")
        self._stop_btn = QPushButton("Stop")
        transport.addWidget(self._play_btn)
        transport.addWidget(self._stop_btn)
        transport.addStretch(1)
        self._total_label = QLabel("Total 00:00:00")
        self._elapsed_label = QLabel("Elapsed 00:00:00")
        self._remaining_label = QLabel("Remaining 00:00:00")
        transport.addWidget(self._total_label)
        transport.addWidget(self._elapsed_label)
        transport.addWidget(self._remaining_label)
        root.addLayout(transport)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.setValue(0)
        root.addWidget(self._slider)

        self._cue_indicator = CueRangeIndicator()
        root.addWidget(self._cue_indicator)

        top_form = QFormLayout()
        mode_row = QHBoxLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("SRT", "srt")
        self._mode_combo.addItem("LRC", "lrc")
        self._mode_combo.setCurrentIndex(0 if self._mode == "srt" else 1)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch(1)
        top_form.addRow("Mode", mode_row)
        root.addLayout(top_form)

        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels(["Timestamp", "Lyric"])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.ExtendedSelection)
        root.addWidget(self._table, 1)

        actions = QHBoxLayout()
        self._highlight_follow_checkbox = QCheckBox("Highlight now playing lyric (follow playhead)")
        self._highlight_follow_checkbox.setChecked(True)
        self._add_line_btn = QPushButton("Add Line At Current Timestamp")
        self._delete_line_btn = QPushButton("Delete Selected Line")
        actions.addWidget(self._highlight_follow_checkbox)
        actions.addWidget(self._add_line_btn)
        actions.addWidget(self._delete_line_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        self._rapid_toggle_btn = QPushButton("Expand Rapid Editor")
        root.addWidget(self._rapid_toggle_btn)

        self._rapid_panel = QWidget(self)
        rapid_layout = QVBoxLayout(self._rapid_panel)
        rapid_layout.setContentsMargins(0, 0, 0, 0)
        rapid_layout.setSpacing(6)
        self._rapid_text = QPlainTextEdit(self._rapid_panel)
        self._rapid_text.setPlaceholderText("Paste lyric lines here, one line per row...")
        self._rapid_text.setMinimumHeight(220)
        rapid_layout.addWidget(self._rapid_text, 1)
        rapid_actions = QHBoxLayout()
        self._rapid_insert_line_btn = QPushButton("Insert Line At Current Timestamp")
        self._rapid_insert_blank_btn = QPushButton("Insert Blank At Current Timestamp")
        self._rapid_undo_btn = QPushButton("Undo")
        self._rapid_undo_btn.setEnabled(False)
        rapid_actions.addWidget(self._rapid_insert_line_btn)
        rapid_actions.addWidget(self._rapid_insert_blank_btn)
        rapid_actions.addWidget(self._rapid_undo_btn)
        rapid_actions.addStretch(1)
        rapid_layout.addLayout(rapid_actions)
        self._rapid_panel.setVisible(False)
        root.addWidget(self._rapid_panel)

        self._default_row_color = self._table.palette().color(QPalette.Text)
        self._playing_row_color = QColor("#E53935")

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self._cancel_btn = QPushButton("Cancel")
        self._save_btn = QPushButton("Save")
        bottom.addWidget(self._cancel_btn)
        bottom.addWidget(self._save_btn)
        root.addLayout(bottom)

        self._load_poll_timer = QTimer(self)
        self._load_poll_timer.setInterval(80)
        self._load_poll_timer.timeout.connect(self._poll_media_preload_state)

        self._play_btn.clicked.connect(self._play)
        self._stop_btn.clicked.connect(self._stop)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider.valueChanged.connect(self._on_slider_value_changed)
        self._add_line_btn.clicked.connect(self._add_line_at_current)
        self._delete_line_btn.clicked.connect(self._delete_selected_lines)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._highlight_follow_checkbox.toggled.connect(
            lambda _checked=False: self._sync_now_playing_row(self._slider.value())
        )
        self._rapid_toggle_btn.clicked.connect(self._toggle_rapid_editor)
        self._rapid_insert_line_btn.clicked.connect(lambda _=False: self._rapid_insert(line_mode=True))
        self._rapid_insert_blank_btn.clicked.connect(lambda _=False: self._rapid_insert(line_mode=False))
        self._rapid_undo_btn.clicked.connect(self._rapid_undo)
        self._cancel_btn.clicked.connect(self.reject)
        self._save_btn.clicked.connect(self._save)

        self._load_rows_from_file()
        self._refresh_cue_indicator()
        self._refresh_transport_times(0)
        self._refresh_buttons()
        localize_widget_tree(self, language)
        QTimer.singleShot(0, self._load_preview_media)

    def closeEvent(self, event) -> None:
        if self._load_poll_timer.isActive():
            self._load_poll_timer.stop()
        try:
            self._player.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def _set_loading_state(self, loading: bool) -> None:
        self._is_loading_media = bool(loading)
        self._cue_indicator.set_loading(self._is_loading_media, "Loading audio waveform...")
        ready = not self._is_loading_media
        self._play_btn.setEnabled(ready)
        self._stop_btn.setEnabled(ready)
        self._slider.setEnabled(ready)
        self._add_line_btn.setEnabled(ready)
        self._delete_line_btn.setEnabled(ready)
        self._save_btn.setEnabled(ready)

    def _load_preview_media(self) -> None:
        if not self._audio_path or not os.path.exists(self._audio_path):
            return
        self._cue_indicator.set_waveform([])
        self._set_loading_state(True)
        self._load_wait_started = time.perf_counter()
        preload_enabled, _active = get_audio_preload_runtime_status()
        if not preload_enabled:
            self._finalize_media_load()
            return
        try:
            request_audio_preload([self._audio_path], prioritize=True)
        except Exception:
            pass
        if is_audio_preloaded(self._audio_path):
            self._finalize_media_load()
            return
        self._load_poll_timer.start()

    def _poll_media_preload_state(self) -> None:
        if not self._is_loading_media:
            self._load_poll_timer.stop()
            return
        elapsed = max(0.0, time.perf_counter() - self._load_wait_started)
        dot_count = int(elapsed * 3.0) % 4
        self._cue_indicator.set_loading(True, "Loading audio waveform" + ("." * dot_count))
        if is_audio_preloaded(self._audio_path):
            self._load_poll_timer.stop()
            self._finalize_media_load()
            return
        if elapsed >= self._load_wait_timeout_sec:
            self._load_poll_timer.stop()
            self._cue_indicator.set_loading(True, "Finalizing audio load...")
            self._finalize_media_load()

    def _finalize_media_load(self) -> None:
        try:
            self._player.setMedia(self._audio_path)
            self._duration_ms = max(0, int(self._player.duration()))
            self._slider.setRange(0, self._duration_ms)
            self._cue_indicator.set_waveform(self._player.waveformPeaks(1800))
            self._refresh_cue_indicator()
            self._refresh_transport_times(self._player.position())
        finally:
            self._set_loading_state(False)

    def _load_rows_from_file(self) -> None:
        rows: List[Tuple[int, str]] = []
        if self._lyric_path and os.path.exists(self._lyric_path):
            try:
                parsed = parse_lyric_file(self._lyric_path)
                rows = [
                    (max(0, int(line.start_ms)), str(line.text or ""))
                    for line in parsed
                    if str(line.text or "").strip()
                ]
            except Exception:
                rows = []
        rows.sort(key=lambda item: item[0])
        self._table.setRowCount(0)
        for start_ms, text in rows:
            self._append_table_row(start_ms, text)

    def _append_table_row(self, start_ms: int, text: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(self._format_timestamp(start_ms)))
        self._table.setItem(row, 1, QTableWidgetItem(str(text or "")))

    def _format_timestamp(self, ms: int) -> str:
        value = max(0, int(ms))
        if self._mode == "lrc":
            minutes = value // 60000
            seconds = (value // 1000) % 60
            centi = (value % 1000) // 10
            return f"{minutes:02d}:{seconds:02d}.{centi:02d}"
        hours = value // 3600000
        minutes = (value // 60000) % 60
        seconds = (value // 1000) % 60
        millis = value % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    def _parse_timestamp(self, value: str) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        m = re.match(r"^(\d+):(\d{1,2})[.:](\d{1,3})$", text)
        if m:
            minutes = int(m.group(1))
            seconds = int(m.group(2))
            frac = m.group(3)
            if len(frac) == 1:
                ms = int(frac) * 100
            elif len(frac) == 2:
                ms = int(frac) * 10
            else:
                ms = int(frac[:3])
            return (minutes * 60 + seconds) * 1000 + ms
        m = re.match(r"^(\d+):(\d{2}):(\d{2})[,.](\d{1,3})$", text)
        if m:
            hours = int(m.group(1))
            minutes = int(m.group(2))
            seconds = int(m.group(3))
            millis = int(m.group(4).ljust(3, "0")[:3])
            return ((hours * 3600) + (minutes * 60) + seconds) * 1000 + millis
        return None

    def _read_rows(self) -> Optional[List[Tuple[int, str]]]:
        rows: List[Tuple[int, str]] = []
        for row in range(self._table.rowCount()):
            ts_item = self._table.item(row, 0)
            text_item = self._table.item(row, 1)
            lyric = str(text_item.text() if text_item is not None else "").strip()
            if not lyric:
                continue
            timestamp = self._parse_timestamp(ts_item.text() if ts_item is not None else "")
            if timestamp is None:
                QMessageBox.warning(self, "Lyric Editor", f"Invalid timestamp at row {row + 1}.")
                return None
            rows.append((max(0, int(timestamp)), lyric))
        rows.sort(key=lambda item: item[0])
        return rows

    def _write_lrc(self, rows: List[Tuple[int, str]]) -> None:
        lines: List[str] = []
        for start_ms, text in rows:
            mm = start_ms // 60000
            ss = (start_ms // 1000) % 60
            cc = (start_ms % 1000) // 10
            lines.append(f"[{mm:02d}:{ss:02d}.{cc:02d}]{text}")
        with open(self._lyric_path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("\n".join(lines))

    def _write_srt(self, rows: List[Tuple[int, str]]) -> None:
        out: List[str] = []
        for idx, (start_ms, text) in enumerate(rows):
            if idx + 1 < len(rows):
                end_ms = max(start_ms, rows[idx + 1][0] - 1)
            else:
                end_ms = start_ms + 4000
            out.append(str(idx + 1))
            out.append(f"{self._srt_time(start_ms)} --> {self._srt_time(end_ms)}")
            out.append(text)
            out.append("")
        with open(self._lyric_path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("\n".join(out).rstrip() + ("\n" if out else ""))

    @staticmethod
    def _srt_time(ms: int) -> str:
        value = max(0, int(ms))
        hh = value // 3600000
        mm = (value // 60000) % 60
        ss = (value // 1000) % 60
        mmm = value % 1000
        return f"{hh:02d}:{mm:02d}:{ss:02d},{mmm:03d}"

    def _add_line_at_current(self) -> None:
        pos = max(0, int(self._slider.value()))
        self._append_table_row(pos, "")
        self._sort_table_by_time()
        self._sync_now_playing_row(pos)

    def _toggle_rapid_editor(self) -> None:
        show = not self._rapid_panel.isVisible()
        self._rapid_panel.setVisible(show)
        self._rapid_toggle_btn.setText("Collapse Rapid Editor" if show else "Expand Rapid Editor")

    def _rapid_snapshot(self) -> Tuple[List[Tuple[str, str]], str]:
        rows: List[Tuple[str, str]] = []
        for row in range(self._table.rowCount()):
            ts_item = self._table.item(row, 0)
            lyric_item = self._table.item(row, 1)
            rows.append(
                (
                    str(ts_item.text() if ts_item is not None else ""),
                    str(lyric_item.text() if lyric_item is not None else ""),
                )
            )
        return rows, self._rapid_text.toPlainText()

    def _rapid_restore(self, snapshot: Tuple[List[Tuple[str, str]], str]) -> None:
        rows, rapid_text = snapshot
        self._table.setRowCount(0)
        for ts, lyric in rows:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(ts))
            self._table.setItem(row, 1, QTableWidgetItem(lyric))
        self._rapid_text.setPlainText(rapid_text)
        self._sync_now_playing_row(self._slider.value())

    def _rapid_take_top_line(self) -> Optional[str]:
        raw = self._rapid_text.toPlainText()
        normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized:
            return None
        parts = normalized.split("\n")
        top = parts[0]
        rest = "\n".join(parts[1:])
        self._rapid_text.setPlainText(rest)
        return top

    def _rapid_insert(self, *, line_mode: bool) -> None:
        snapshot = self._rapid_snapshot()
        top = self._rapid_take_top_line()
        if top is None:
            QMessageBox.information(self, "Rapid Editor", "Rapid editor is empty.")
            return
        self._rapid_undo_stack.append(snapshot)
        if len(self._rapid_undo_stack) > 100:
            self._rapid_undo_stack = self._rapid_undo_stack[-100:]
        pos = max(0, int(self._slider.value()))
        self._append_table_row(pos, top if line_mode else "")
        self._sort_table_by_time()
        self._sync_now_playing_row(pos)
        self._rapid_undo_btn.setEnabled(True)

    def _rapid_undo(self) -> None:
        if not self._rapid_undo_stack:
            self._rapid_undo_btn.setEnabled(False)
            return
        snapshot = self._rapid_undo_stack.pop()
        self._rapid_restore(snapshot)
        self._rapid_undo_btn.setEnabled(bool(self._rapid_undo_stack))

    def _delete_selected_lines(self) -> None:
        rows = sorted({index.row() for index in self._table.selectionModel().selectedRows()}, reverse=True)
        for row in rows:
            self._table.removeRow(row)
        self._sync_now_playing_row(self._slider.value())

    def _sort_table_by_time(self) -> None:
        parsed: List[Tuple[int, str]] = []
        for row in range(self._table.rowCount()):
            ts_item = self._table.item(row, 0)
            text_item = self._table.item(row, 1)
            ts = self._parse_timestamp(ts_item.text() if ts_item is not None else "")
            if ts is None:
                ts = 0
            parsed.append((ts, str(text_item.text() if text_item is not None else "")))
        parsed.sort(key=lambda item: item[0])
        self._table.setRowCount(0)
        for ts, text in parsed:
            self._append_table_row(ts, text)

    def _on_mode_changed(self) -> None:
        self._mode = str(self._mode_combo.currentData() or "srt")
        self._sort_table_by_time()
        for row in range(self._table.rowCount()):
            ts_item = self._table.item(row, 0)
            if ts_item is None:
                continue
            ts = self._parse_timestamp(ts_item.text())
            if ts is None:
                continue
            ts_item.setText(self._format_timestamp(ts))
        self._sync_now_playing_row(self._slider.value())

    def _play(self) -> None:
        if self._is_loading_media:
            return
        if not self._audio_path or not os.path.exists(self._audio_path):
            return
        state = self._player.state()
        if state == ExternalMediaPlayer.PausedState:
            self._player.play()
        elif state == ExternalMediaPlayer.PlayingState:
            self._player.pause()
        else:
            if self._stop_host_playback is not None:
                try:
                    self._stop_host_playback()
                except Exception:
                    pass
            self._player.setMedia(self._audio_path)
            self._player.play()
        self._refresh_buttons()

    def _stop(self) -> None:
        if self._is_loading_media:
            return
        self._player.stop()
        self._refresh_buttons()

    def _on_slider_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_slider_released(self) -> None:
        self._is_scrubbing = False
        self._player.setPosition(self._slider.value())

    def _on_slider_value_changed(self, value: int) -> None:
        if self._is_scrubbing:
            self._refresh_transport_times(value)

    def _on_position_changed(self, pos: int) -> None:
        if not self._is_scrubbing:
            self._slider.blockSignals(True)
            self._slider.setValue(max(0, int(pos)))
            self._slider.blockSignals(False)
            self._refresh_transport_times(pos)

    def _on_duration_changed(self, duration: int) -> None:
        self._duration_ms = max(0, int(duration))
        self._slider.setRange(0, self._duration_ms)
        if self._duration_ms > 0:
            self._cue_indicator.set_waveform(self._player.waveformPeaks(1800))
        self._refresh_cue_indicator()
        self._refresh_transport_times(self._slider.value())

    def _on_state_changed(self, _state: int) -> None:
        self._refresh_buttons()
        self._sync_now_playing_row(self._slider.value())

    def _refresh_buttons(self) -> None:
        state = self._player.state()
        self._play_btn.setText("Pause" if state == ExternalMediaPlayer.PlayingState else "Play")

    def _refresh_transport_times(self, position_ms: int) -> None:
        pos = max(0, int(position_ms))
        total = max(0, int(self._duration_ms))
        remaining = max(0, total - pos)
        self._total_label.setText(f"Total {self._hms(total)}")
        self._elapsed_label.setText(f"Elapsed {self._hms(pos)}")
        self._remaining_label.setText(f"Remaining {self._hms(remaining)}")
        self._cue_indicator.set_position(pos)
        self._stop_btn.setEnabled((not self._is_loading_media) and (total > 0))
        self._sync_now_playing_row(pos)

    def _refresh_cue_indicator(self) -> None:
        self._cue_indicator.set_values(self._duration_ms, self._cue_start_ms, self._cue_end_ms)

    def _sync_now_playing_row(self, position_ms: int) -> None:
        playing = self._player.state() == ExternalMediaPlayer.PlayingState
        follow = bool(self._highlight_follow_checkbox.isChecked())
        if not playing:
            self._apply_active_row(-1, follow=False)
            return
        target = self._row_for_position(max(0, int(position_ms)))
        self._apply_active_row(target, follow=follow)

    def _row_for_position(self, position_ms: int) -> int:
        points: List[Tuple[int, int]] = []
        for row in range(self._table.rowCount()):
            ts_item = self._table.item(row, 0)
            ts = self._parse_timestamp(ts_item.text() if ts_item is not None else "")
            if ts is None:
                continue
            points.append((max(0, int(ts)), row))
        if not points:
            return -1
        points.sort(key=lambda item: item[0])
        pos = max(0, int(position_ms))
        active_row = -1
        for idx, (start_ms, row) in enumerate(points):
            next_start = points[idx + 1][0] if idx + 1 < len(points) else None
            if pos < start_ms:
                break
            if next_start is None or pos < next_start:
                active_row = row
                break
            active_row = row
        return active_row

    def _apply_active_row(self, row: int, *, follow: bool) -> None:
        if self._active_row == row:
            return
        self._active_row = row
        for ridx in range(self._table.rowCount()):
            color = self._playing_row_color if ridx == row else self._default_row_color
            for cidx in range(self._table.columnCount()):
                item = self._table.item(ridx, cidx)
                if item is not None:
                    item.setForeground(color)
        if row >= 0 and follow:
            self._table.selectRow(row)
            anchor = self._table.item(row, 0) or self._table.item(row, 1)
            if anchor is not None:
                self._table.scrollToItem(anchor, QTableWidget.PositionAtCenter)

    @staticmethod
    def _hms(ms: int) -> str:
        value = max(0, int(ms))
        h = value // 3600000
        m = (value // 60000) % 60
        s = (value // 1000) % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _save(self) -> None:
        rows = self._read_rows()
        if rows is None:
            return
        os.makedirs(os.path.dirname(self._lyric_path) or ".", exist_ok=True)
        try:
            if self._mode == "lrc":
                self._write_lrc(rows)
            else:
                self._write_srt(rows)
        except OSError as exc:
            QMessageBox.warning(self, "Lyric Editor", f"Failed to save lyric file:\n{exc}")
            return
        self.accept()
