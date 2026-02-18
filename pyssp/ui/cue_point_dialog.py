from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import ExternalMediaPlayer


class CueRangeIndicator(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._duration_ms = 0
        self._start_ms: Optional[int] = None
        self._end_ms: Optional[int] = None
        self.setMinimumHeight(12)

    def sizeHint(self) -> QSize:
        return QSize(360, 14)

    def set_values(self, duration_ms: int, start_ms: Optional[int], end_ms: Optional[int]) -> None:
        self._duration_ms = max(0, int(duration_ms))
        self._start_ms = None if start_ms is None else max(0, int(start_ms))
        self._end_ms = None if end_ms is None else max(0, int(end_ms))
        self.update()

    def _x_for_ms(self, value_ms: int, width: int) -> int:
        if self._duration_ms <= 0 or width <= 1:
            return 0
        ratio = max(0.0, min(1.0, value_ms / float(self._duration_ms)))
        return int(round(ratio * (width - 1)))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        w = max(1, self.width())
        h = max(1, self.height())

        painter.fillRect(0, 0, w, h, QColor("#D7DEE2"))
        if self._duration_ms <= 0:
            painter.end()
            return

        start = self._start_ms
        end = self._end_ms
        if start is not None and end is not None and end < start:
            end = start

        if start is not None and end is not None:
            x1 = self._x_for_ms(start, w)
            x2 = self._x_for_ms(end, w)
            if x2 < x1:
                x2 = x1
            painter.fillRect(x1, 0, max(1, x2 - x1 + 1), h, QColor("#BFEFFF"))

        pen = QPen(QColor("#00A4D8"))
        pen.setWidth(2)
        painter.setPen(pen)
        if start is not None:
            x = self._x_for_ms(start, w)
            painter.drawLine(x, 0, x, h - 1)
        if end is not None:
            x = self._x_for_ms(end, w)
            painter.drawLine(x, 0, x, h - 1)
        painter.end()


class CuePointDialog(QDialog):
    def __init__(
        self,
        file_path: str,
        title: str,
        cue_start_ms: Optional[int],
        cue_end_ms: Optional[int],
        stop_host_playback: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Set Cue Points")
        self.resize(760, 260)

        self._player = ExternalMediaPlayer(self)
        self._player.setNotifyInterval(30)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.stateChanged.connect(self._on_state_changed)

        self._duration_ms = 0
        self._cue_start_ms = cue_start_ms
        self._cue_end_ms = cue_end_ms
        self._is_scrubbing = False
        self._mode = "idle"
        self._timeline_mode = "audio_file"
        self._load_error: Optional[str] = None
        self._stop_host_playback = stop_host_playback

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        name = title.strip() or os.path.basename(file_path)
        self.title_label = QLabel(name)
        root.addWidget(self.title_label)

        self.path_label = QLabel(file_path)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self.path_label)

        transport = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.preview_btn = QPushButton("Preview")
        self.stop_btn = QPushButton("Stop")
        transport.addWidget(self.play_btn)
        transport.addWidget(self.preview_btn)
        transport.addWidget(self.stop_btn)
        transport.addStretch(1)
        self.total_label = QLabel("Total 00:00:00")
        self.elapsed_label = QLabel("Elapsed 00:00:00")
        self.remaining_label = QLabel("Remaining 00:00:00")
        transport.addWidget(self.total_label)
        transport.addWidget(self.elapsed_label)
        transport.addWidget(self.remaining_label)
        root.addLayout(transport)

        self.jog_slider = QSlider(Qt.Horizontal)
        self.jog_slider.setRange(0, 0)
        self.jog_slider.setValue(0)
        root.addWidget(self.jog_slider)
        jog_meta = QHBoxLayout()
        jog_meta.setContentsMargins(0, 0, 0, 0)
        self.jog_in_label = QLabel("In 00:00:00")
        self.jog_percent_label = QLabel("0%")
        self.jog_percent_label.setAlignment(Qt.AlignCenter)
        self.jog_out_label = QLabel("Out 00:00:00")
        self.jog_out_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        jog_meta.addWidget(self.jog_in_label)
        jog_meta.addStretch(1)
        jog_meta.addWidget(self.jog_percent_label)
        jog_meta.addStretch(1)
        jog_meta.addWidget(self.jog_out_label)
        root.addLayout(jog_meta)
        self.cue_indicator = CueRangeIndicator()
        root.addWidget(self.cue_indicator)

        form = QFormLayout()
        start_row = QWidget()
        start_layout = QHBoxLayout(start_row)
        start_layout.setContentsMargins(0, 0, 0, 0)
        self.start_set_btn = QPushButton("Set Start Cue")
        self.start_tc_edit = QLineEdit("")
        self.start_tc_edit.setPlaceholderText("mm:ss:ff")
        self.start_reset_btn = QPushButton("Reset")
        start_layout.addWidget(self.start_set_btn)
        start_layout.addWidget(self.start_tc_edit, 1)
        start_layout.addWidget(self.start_reset_btn)
        form.addRow("Start", start_row)

        end_row = QWidget()
        end_layout = QHBoxLayout(end_row)
        end_layout.setContentsMargins(0, 0, 0, 0)
        self.end_set_btn = QPushButton("Set End Cue")
        self.end_tc_edit = QLineEdit("")
        self.end_tc_edit.setPlaceholderText("mm:ss:ff")
        self.end_reset_btn = QPushButton("Reset")
        end_layout.addWidget(self.end_set_btn)
        end_layout.addWidget(self.end_tc_edit, 1)
        end_layout.addWidget(self.end_reset_btn)
        form.addRow("End", end_row)

        root.addLayout(form)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color:#B00020;")
        root.addWidget(self.error_label)

        bottom = QHBoxLayout()
        self.clear_cue_btn = QPushButton("Clear Cue")
        bottom.addWidget(self.clear_cue_btn)
        bottom.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn = QPushButton("Save")
        bottom.addWidget(self.cancel_btn)
        bottom.addWidget(self.save_btn)
        root.addLayout(bottom)

        self.play_btn.clicked.connect(self._play)
        self.stop_btn.clicked.connect(self._stop)
        self.preview_btn.clicked.connect(self._preview)
        self.jog_slider.sliderPressed.connect(self._on_slider_pressed)
        self.jog_slider.sliderReleased.connect(self._on_slider_released)
        self.jog_slider.valueChanged.connect(self._on_slider_value_changed)
        self.start_set_btn.clicked.connect(self._set_start_from_current)
        self.end_set_btn.clicked.connect(self._set_end_from_current)
        self.start_reset_btn.clicked.connect(self._reset_start)
        self.end_reset_btn.clicked.connect(self._reset_end)
        self.clear_cue_btn.clicked.connect(self._clear_cues)
        self.start_tc_edit.editingFinished.connect(self._commit_start_timecode)
        self.end_tc_edit.editingFinished.connect(self._commit_end_timecode)
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._save)

        self._limit_timer = QTimer(self)
        self._limit_timer.setInterval(30)
        self._limit_timer.timeout.connect(self._enforce_end_limit)
        self._limit_timer.start()

        try:
            self._player.setMedia(file_path)
            self._duration_ms = max(0, int(self._player.duration()))
            self.jog_slider.setRange(0, self._duration_ms)
        except Exception as exc:
            self._load_error = str(exc)
            self.error_label.setText(f"Could not load audio preview: {exc}")
            self.play_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
            self.jog_slider.setEnabled(False)
            self.start_set_btn.setEnabled(False)
            self.end_set_btn.setEnabled(False)
            self.clear_cue_btn.setEnabled(False)
            self.save_btn.setEnabled(False)

        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(0)
        self._refresh_transport_buttons()

    def closeEvent(self, event) -> None:
        self._stop_preview_player()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        self._stop_preview_player()
        super().done(result)

    def values(self) -> tuple[Optional[int], Optional[int]]:
        return self._cue_start_ms, self._cue_end_ms

    def _play(self) -> None:
        if self._load_error:
            return
        if self._mode == "play" and self._player.state() == ExternalMediaPlayer.PlayingState:
            self._player.pause()
            self._refresh_transport_buttons()
            return
        if self._stop_host_playback is not None:
            try:
                self._stop_host_playback()
            except Exception:
                pass
        self._set_mode("play")
        self._player.play()
        self._refresh_transport_buttons()

    def _stop(self) -> None:
        if self._load_error:
            return
        self._set_mode("idle")
        self._player.stop()
        self._player.setPosition(0)
        self._refresh_transport_buttons()

    def _preview(self) -> None:
        if self._load_error:
            return
        if self._mode == "preview" and self._player.state() == ExternalMediaPlayer.PlayingState:
            self._player.pause()
            self._refresh_transport_buttons()
            return
        if self._stop_host_playback is not None:
            try:
                self._stop_host_playback()
            except Exception:
                pass
        start = 0 if self._cue_start_ms is None else max(0, self._cue_start_ms)
        self._player.setPosition(start)
        self._set_mode("preview")
        self._player.play()
        self._refresh_transport_buttons()

    def _stop_preview_player(self) -> None:
        try:
            self._player.stop()
        except Exception:
            pass

    def _on_position_changed(self, pos: int) -> None:
        if not self._is_scrubbing:
            self.jog_slider.setValue(self._to_relative_ms(pos))
        self._refresh_transport_times(pos)

    def _on_duration_changed(self, duration: int) -> None:
        self._duration_ms = max(0, int(duration))
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _on_state_changed(self, _state: int) -> None:
        if self._player.state() == ExternalMediaPlayer.StoppedState:
            self._set_mode("idle")
        self._refresh_transport_buttons()

    def _on_slider_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_slider_released(self) -> None:
        self._is_scrubbing = False
        self._player.setPosition(self._to_absolute_ms(self.jog_slider.value()))

    def _on_slider_value_changed(self, value: int) -> None:
        if not self._is_scrubbing:
            return
        self._refresh_transport_times(self._to_absolute_ms(value))

    def _set_start_from_current(self) -> None:
        self._cue_start_ms = max(0, int(self._to_absolute_ms(self.jog_slider.value())))
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _set_end_from_current(self) -> None:
        self._cue_end_ms = max(0, int(self._to_absolute_ms(self.jog_slider.value())))
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _reset_start(self) -> None:
        self._cue_start_ms = None
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _reset_end(self) -> None:
        self._cue_end_ms = None
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _clear_cues(self) -> None:
        self._cue_start_ms = None
        self._cue_end_ms = None
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _commit_start_timecode(self) -> None:
        value = self.start_tc_edit.text().strip()
        if not value:
            self._cue_start_ms = None
            self._normalize_cues()
            self._refresh_timecode_edits()
            self._refresh_cue_indicator()
            self._apply_jog_bounds()
            self._refresh_transport_times(self._player.position())
            return
        parsed = parse_timecode_to_ms(value)
        if parsed is None:
            self.error_label.setText("Invalid start cue timecode. Use mm:ss or mm:ss:ff.")
            self._refresh_timecode_edits()
            return
        self.error_label.setText("")
        self._cue_start_ms = parsed
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _commit_end_timecode(self) -> None:
        value = self.end_tc_edit.text().strip()
        if not value:
            self._cue_end_ms = None
            self._normalize_cues()
            self._refresh_timecode_edits()
            self._refresh_cue_indicator()
            self._apply_jog_bounds()
            self._refresh_transport_times(self._player.position())
            return
        parsed = parse_timecode_to_ms(value)
        if parsed is None:
            self.error_label.setText("Invalid end cue timecode. Use mm:ss or mm:ss:ff.")
            self._refresh_timecode_edits()
            return
        self.error_label.setText("")
        self._cue_end_ms = parsed
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_cue_indicator()
        self._apply_jog_bounds()
        self._refresh_transport_times(self._player.position())

    def _normalize_cues(self) -> None:
        if self._cue_start_ms is not None:
            self._cue_start_ms = max(0, int(self._cue_start_ms))
        if self._cue_end_ms is not None:
            self._cue_end_ms = max(0, int(self._cue_end_ms))

        if self._duration_ms > 0:
            if self._cue_start_ms is not None:
                self._cue_start_ms = min(self._duration_ms, self._cue_start_ms)
            if self._cue_end_ms is not None:
                self._cue_end_ms = min(self._duration_ms, self._cue_end_ms)
        if self._cue_start_ms is not None and self._cue_end_ms is not None and self._cue_end_ms < self._cue_start_ms:
            self._cue_end_ms = self._cue_start_ms

    def _refresh_timecode_edits(self) -> None:
        self.start_tc_edit.blockSignals(True)
        self.end_tc_edit.blockSignals(True)
        self.start_tc_edit.setText("" if self._cue_start_ms is None else format_timecode(self._cue_start_ms))
        self.end_tc_edit.setText("" if self._cue_end_ms is None else format_timecode(self._cue_end_ms))
        self.start_tc_edit.blockSignals(False)
        self.end_tc_edit.blockSignals(False)

    def _effective_bounds(self) -> tuple[int, int]:
        if self._timeline_mode == "audio_file":
            low = 0
            high = self._duration_ms
        else:
            low = 0 if self._cue_start_ms is None else max(0, int(self._cue_start_ms))
            high = self._duration_ms if self._cue_end_ms is None else max(0, int(self._cue_end_ms))
        if self._duration_ms > 0:
            low = min(low, self._duration_ms)
            high = min(high, self._duration_ms)
        if high < low:
            high = low
        return low, high

    def _to_relative_ms(self, absolute_ms: int) -> int:
        low, high = self._effective_bounds()
        region = max(0, high - low)
        value = int(absolute_ms) - low
        return max(0, min(region, value))

    def _to_absolute_ms(self, relative_ms: int) -> int:
        low, high = self._effective_bounds()
        region = max(0, high - low)
        rel = max(0, min(region, int(relative_ms)))
        return low + rel

    def _apply_jog_bounds(self) -> None:
        low, high = self._effective_bounds()
        region = max(0, high - low)
        self.jog_slider.setRange(0, region)
        pos = self._player.position()
        target = max(low, min(high, pos))
        if target != pos:
            self._player.setPosition(target)
        else:
            self.jog_slider.setValue(self._to_relative_ms(target))

    def _refresh_transport_times(self, position_ms: int) -> None:
        low, high = self._effective_bounds()
        clamped = max(low, min(high, int(position_ms)))
        total = max(0, high - low)
        elapsed = max(0, clamped - low)
        remaining = max(0, high - clamped)
        self.total_label.setText(f"Total {format_timecode(total)}")
        self.elapsed_label.setText(f"Elapsed {format_timecode(elapsed)}")
        self.remaining_label.setText(f"Remaining {format_timecode(remaining)}")
        self._refresh_jog_meta(elapsed, total)

    def _refresh_cue_indicator(self) -> None:
        self.cue_indicator.set_values(self._duration_ms, self._cue_start_ms, self._cue_end_ms)

    def _refresh_jog_meta(self, elapsed_ms: int, total_ms: int) -> None:
        in_ms = 0 if self._cue_start_ms is None else max(0, int(self._cue_start_ms))
        out_ms = self._duration_ms if self._cue_end_ms is None else max(0, int(self._cue_end_ms))
        if self._duration_ms > 0:
            in_ms = min(in_ms, self._duration_ms)
            out_ms = min(out_ms, self._duration_ms)
        if out_ms < in_ms:
            out_ms = in_ms
        self.jog_in_label.setText(f"In {format_timecode(in_ms)}")
        self.jog_out_label.setText(f"Out {format_timecode(out_ms)}")
        percent = 0 if total_ms <= 0 else int((max(0, min(total_ms, elapsed_ms)) / float(total_ms)) * 100.0)
        self.jog_percent_label.setText(f"{percent}%")

    def _enforce_end_limit(self) -> None:
        if self._mode != "preview":
            return
        if self._cue_end_ms is None:
            return
        if self._player.state() != ExternalMediaPlayer.PlayingState:
            return
        if self._player.position() < self._cue_end_ms:
            return
        self._player.pause()
        self._player.setPosition(self._cue_end_ms)
        self._refresh_transport_buttons()

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self._refresh_transport_buttons()

    def _refresh_transport_buttons(self) -> None:
        playing = self._player.state() == ExternalMediaPlayer.PlayingState
        self.play_btn.setText("Pause" if (self._mode == "play" and playing) else "Play")
        self.preview_btn.setText("Pause" if (self._mode == "preview" and playing) else "Preview")

    def _save(self) -> None:
        if self._load_error:
            self.reject()
            return
        self._commit_start_timecode()
        self._commit_end_timecode()
        if self.error_label.text().strip():
            return
        self.accept()


def format_timecode(ms: int) -> str:
    fps = 30
    total_ms = max(0, int(ms))
    total_seconds, remainder_ms = divmod(total_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    frames = min(fps - 1, int((remainder_ms / 1000.0) * fps))
    return f"{minutes:02d}:{seconds:02d}:{frames:02d}"


def parse_timecode_to_ms(value: str) -> Optional[int]:
    text = value.strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) == 2:
        mm, ss = parts
        if mm.isdigit() and ss.isdigit():
            return (int(mm) * 60 + int(ss)) * 1000
        return None
    if len(parts) == 3:
        first, second, third = parts
        if not (first.isdigit() and second.isdigit() and third.isdigit()):
            return None
        minutes = int(first)
        seconds = int(second)
        frames = int(third)
        if frames >= 30:
            return None
        return ((minutes * 60) + seconds) * 1000 + int((frames / 30.0) * 1000)
    return None
