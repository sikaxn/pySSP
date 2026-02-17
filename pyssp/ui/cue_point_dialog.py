from __future__ import annotations

import os
from typing import Callable, Optional

from PyQt5.QtCore import Qt, QTimer
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
        self._preview_active = False
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
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        self.preview_btn = QPushButton("Preview")
        transport.addWidget(self.play_btn)
        transport.addWidget(self.pause_btn)
        transport.addWidget(self.stop_btn)
        transport.addWidget(self.preview_btn)
        transport.addStretch(1)
        self.position_label = QLabel("00:00:00 / 00:00:00")
        transport.addWidget(self.position_label)
        root.addLayout(transport)

        self.jog_slider = QSlider(Qt.Horizontal)
        self.jog_slider.setRange(0, 0)
        self.jog_slider.setValue(0)
        root.addWidget(self.jog_slider)

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
        bottom.addStretch(1)
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn = QPushButton("Save")
        bottom.addWidget(self.cancel_btn)
        bottom.addWidget(self.save_btn)
        root.addLayout(bottom)

        self.play_btn.clicked.connect(self._play)
        self.pause_btn.clicked.connect(self._pause)
        self.stop_btn.clicked.connect(self._stop)
        self.preview_btn.clicked.connect(self._preview)
        self.jog_slider.sliderPressed.connect(self._on_slider_pressed)
        self.jog_slider.sliderReleased.connect(self._on_slider_released)
        self.jog_slider.valueChanged.connect(self._on_slider_value_changed)
        self.start_set_btn.clicked.connect(self._set_start_from_current)
        self.end_set_btn.clicked.connect(self._set_end_from_current)
        self.start_reset_btn.clicked.connect(self._reset_start)
        self.end_reset_btn.clicked.connect(self._reset_end)
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
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
            self.jog_slider.setEnabled(False)
            self.start_set_btn.setEnabled(False)
            self.end_set_btn.setEnabled(False)
            self.save_btn.setEnabled(False)

        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_position_label(0)

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
        if self._stop_host_playback is not None:
            try:
                self._stop_host_playback()
            except Exception:
                pass
        self._preview_active = False
        self._player.play()

    def _pause(self) -> None:
        if self._load_error:
            return
        self._preview_active = False
        self._player.pause()

    def _stop(self) -> None:
        if self._load_error:
            return
        self._preview_active = False
        self._player.stop()
        if self._cue_start_ms is not None:
            self._player.setPosition(self._cue_start_ms)

    def _preview(self) -> None:
        if self._load_error:
            return
        if self._stop_host_playback is not None:
            try:
                self._stop_host_playback()
            except Exception:
                pass
        start = 0 if self._cue_start_ms is None else max(0, self._cue_start_ms)
        self._player.setPosition(start)
        self._preview_active = True
        self._player.play()

    def _stop_preview_player(self) -> None:
        try:
            self._player.stop()
        except Exception:
            pass

    def _on_position_changed(self, pos: int) -> None:
        if not self._is_scrubbing:
            self.jog_slider.setValue(pos)
        self._refresh_position_label(pos)

    def _on_duration_changed(self, duration: int) -> None:
        self._duration_ms = max(0, int(duration))
        self.jog_slider.setRange(0, self._duration_ms)
        self._normalize_cues()
        self._refresh_timecode_edits()
        self._refresh_position_label(self._player.position())

    def _on_state_changed(self, _state: int) -> None:
        if self._player.state() == ExternalMediaPlayer.StoppedState:
            self._preview_active = False

    def _on_slider_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_slider_released(self) -> None:
        self._is_scrubbing = False
        self._player.setPosition(self.jog_slider.value())

    def _on_slider_value_changed(self, value: int) -> None:
        if not self._is_scrubbing:
            return
        self._refresh_position_label(value)

    def _set_start_from_current(self) -> None:
        self._cue_start_ms = max(0, int(self.jog_slider.value()))
        self._normalize_cues()
        self._refresh_timecode_edits()

    def _set_end_from_current(self) -> None:
        self._cue_end_ms = max(0, int(self.jog_slider.value()))
        self._normalize_cues()
        self._refresh_timecode_edits()

    def _reset_start(self) -> None:
        self._cue_start_ms = None
        self._normalize_cues()
        self._refresh_timecode_edits()

    def _reset_end(self) -> None:
        self._cue_end_ms = None
        self._normalize_cues()
        self._refresh_timecode_edits()

    def _commit_start_timecode(self) -> None:
        value = self.start_tc_edit.text().strip()
        if not value:
            self._cue_start_ms = None
            self._normalize_cues()
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

    def _commit_end_timecode(self) -> None:
        value = self.end_tc_edit.text().strip()
        if not value:
            self._cue_end_ms = None
            self._normalize_cues()
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

    def _refresh_position_label(self, position_ms: int) -> None:
        self.position_label.setText(
            f"{format_timecode(position_ms)} / {format_timecode(self._duration_ms)}"
        )

    def _enforce_end_limit(self) -> None:
        if self._cue_end_ms is None:
            return
        if self._player.state() != ExternalMediaPlayer.PlayingState:
            return
        if self._player.position() < self._cue_end_ms:
            return
        self._player.pause()
        self._player.setPosition(self._cue_end_ms)
        self._preview_active = False

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
