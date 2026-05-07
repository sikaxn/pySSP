from __future__ import annotations

import os
import time
from typing import Callable, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import ExternalMediaPlayer, is_audio_preloaded, request_audio_preload
from pyssp.automation_command import AutomationCommandSpec, normalize_automation_spec
from pyssp.automation_script import (
    AutomationScript,
    AutomationScriptAction,
    AutomationScriptCue,
    AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
    automation_script_cue_command_summary,
    load_automation_script,
    save_automation_script,
)
from pyssp.i18n import localize_widget_tree, tr
from pyssp.lyrics import LyricLine, parse_lyric_file
from pyssp.ui.automation_command_sound_button_dialog import AutomationCommandSoundButtonDialog
from pyssp.ui.waveform_view import CueRangeIndicator, WaveformRefreshController


class AutomationScriptEditorDialog(QDialog):
    def __init__(
        self,
        *,
        script_path: str,
        audio_path: str,
        audio_source: object,
        title: str,
        lyric_path: str = "",
        cue_start_ms: Optional[int] = None,
        cue_end_ms: Optional[int] = None,
        companion_payload: Optional[dict] = None,
        hide_black_empty: bool = True,
        language: str = "en",
        stop_host_playback: Optional[Callable[[], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Automation Script Editor"))
        self.resize(980, 700)

        self._script_path = str(script_path or "").strip()
        self._audio_path = str(audio_path or "").strip()
        self._audio_source = audio_source
        self._lyric_path = str(lyric_path or "").strip()
        self._cue_start_ms = None if cue_start_ms is None else max(0, int(cue_start_ms))
        self._cue_end_ms = None if cue_end_ms is None else max(0, int(cue_end_ms))
        self._companion_payload = dict(companion_payload or {"pages": {}, "updated_at": ""})
        self._hide_black_empty = bool(hide_black_empty)
        self._duration_ms = 0
        self._is_scrubbing = False
        self._is_loading_media = False
        self._load_wait_started = 0.0
        self._load_wait_timeout_sec = 120.0
        self._media_load_request_id = 0
        self._waveform_refresh: Optional[WaveformRefreshController] = None
        self._stop_host_playback = stop_host_playback
        self._script = self._load_script()
        self._lyric_lines = self._load_lyric_lines()
        self._display_rows: List[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        name = str(title or "").strip() or os.path.basename(self._audio_path or self._script_path)
        self._title_label = QLabel(name)
        root.addWidget(self._title_label)

        self._path_label = QLabel(self._script_path)
        self._path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        root.addWidget(self._path_label)

        audio_service = getattr(parent, "_audio_service", None)
        if audio_service is not None:
            self._player = audio_service.create_player(self)
        else:
            self._player = ExternalMediaPlayer(self)
        self._player.setNotifyInterval(40)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.stateChanged.connect(self._on_state_changed)
        self._player.mediaLoadFinished.connect(self._on_media_load_finished)

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
        self._waveform_refresh = WaveformRefreshController(
            on_peaks=self._cue_indicator.set_waveform,
            is_valid=lambda: self._duration_ms > 0,
            sample_count=1800,
            parent=self,
        )

        notes_form = QFormLayout()
        self._notes_edit = QPlainTextEdit(str(self._script.notes or ""))
        self._notes_edit.setMaximumHeight(70)
        notes_form.addRow(tr("Notes"), self._notes_edit)
        root.addLayout(notes_form)

        toggle_row = QHBoxLayout()
        self._show_lyric_checkbox = QCheckBox(tr("Show lyric alongside automation cues"))
        self._show_lyric_checkbox.setChecked(bool(self._lyric_lines))
        self._show_lyric_checkbox.setEnabled(bool(self._lyric_lines))
        toggle_row.addWidget(self._show_lyric_checkbox)
        toggle_row.addStretch(1)
        root.addLayout(toggle_row)

        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Comment"), tr("Commands"), tr("Lyric")])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        root.addWidget(self._table, 1)

        actions = QHBoxLayout()
        self._add_current_btn = QPushButton(tr("Add Cue At Current Timestamp"))
        self._add_selected_lyric_btn = QPushButton(tr("Add Cue On Selected Lyric Time"))
        self._edit_btn = QPushButton(tr("Edit Selected Cue"))
        self._delete_btn = QPushButton(tr("Delete Selected Cue"))
        actions.addWidget(self._add_current_btn)
        actions.addWidget(self._add_selected_lyric_btn)
        actions.addWidget(self._edit_btn)
        actions.addWidget(self._delete_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._load_poll_timer = QTimer(self)
        self._load_poll_timer.setInterval(30)
        self._load_poll_timer.timeout.connect(self._poll_media_preload_state)

        self._play_btn.clicked.connect(self._play)
        self._stop_btn.clicked.connect(self._stop)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._slider.valueChanged.connect(self._on_slider_value_changed)
        self._show_lyric_checkbox.toggled.connect(self._rebuild_table)
        self._table.cellClicked.connect(self._on_table_clicked)
        self._table.itemSelectionChanged.connect(self._refresh_action_buttons)
        self._add_current_btn.clicked.connect(self._add_cue_at_current)
        self._add_selected_lyric_btn.clicked.connect(self._add_cue_at_selected_lyric)
        self._edit_btn.clicked.connect(self._edit_selected_cue)
        self._delete_btn.clicked.connect(self._delete_selected_cue)

        self._refresh_cue_indicator()
        self._refresh_transport_times(0)
        self._rebuild_table()
        self._refresh_action_buttons()
        localize_widget_tree(self, language)
        QTimer.singleShot(0, self._load_preview_media)

    def closeEvent(self, event) -> None:
        if self._load_poll_timer.isActive():
            self._load_poll_timer.stop()
        if self._waveform_refresh is not None:
            self._waveform_refresh.stop()
        self._stop_preview_player()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        if self._load_poll_timer.isActive():
            self._load_poll_timer.stop()
        if self._waveform_refresh is not None:
            self._waveform_refresh.stop()
        self._stop_preview_player()
        super().done(result)

    def _load_script(self) -> AutomationScript:
        if not self._script_path or not os.path.exists(self._script_path):
            return AutomationScript(notes="", cues=[])
        try:
            return load_automation_script(self._script_path)
        except Exception as exc:
            try:
                if os.path.getsize(self._script_path) <= 0:
                    return AutomationScript(notes="", cues=[])
            except OSError:
                pass
            QMessageBox.warning(
                self,
                tr("Automation Script Editor"),
                f"{tr('Failed to read automation script:')}\n{exc}",
            )
            return AutomationScript(notes="", cues=[])

    def _load_lyric_lines(self) -> List[LyricLine]:
        if not self._lyric_path or not os.path.exists(self._lyric_path):
            return []
        try:
            return list(parse_lyric_file(self._lyric_path) or [])
        except Exception:
            return []

    def _stop_preview_player(self) -> None:
        try:
            self._player.stop()
        except Exception:
            pass

    def _request_waveform_refresh(self) -> None:
        if self._waveform_refresh is None:
            return
        self._waveform_refresh.request(player=self._player, duration_ms=self._duration_ms)

    def _set_loading_state(self, loading: bool) -> None:
        self._is_loading_media = bool(loading)
        self._cue_indicator.set_loading(self._is_loading_media, "Loading audio waveform...")
        ready = not self._is_loading_media
        self._play_btn.setEnabled(ready)
        self._stop_btn.setEnabled(ready)
        self._slider.setEnabled(ready)

    def _load_preview_media(self) -> None:
        if self._waveform_refresh is not None:
            self._waveform_refresh.stop()
        self._cue_indicator.set_waveform([])
        self._set_loading_state(True)
        self._load_wait_started = time.perf_counter()
        if not self._audio_path or not os.path.exists(self._audio_path):
            self._finalize_media_load()
            return
        try:
            request_audio_preload([self._audio_path], prioritize=True, force=True)
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
        if self._audio_path and is_audio_preloaded(self._audio_path):
            self._load_poll_timer.stop()
            self._finalize_media_load()
            return
        if elapsed >= self._load_wait_timeout_sec:
            self._load_poll_timer.stop()
            self._finalize_media_load()

    def _finalize_media_load(self) -> None:
        try:
            self._media_load_request_id = int(self._player.setMediaAsync(self._audio_source))
        except Exception:
            self._set_loading_state(False)

    def _on_media_load_finished(self, request_id: int, ok: bool, _error: str) -> None:
        if int(request_id) != int(self._media_load_request_id):
            return
        if not ok:
            self._set_loading_state(False)
            return
        self._duration_ms = max(0, int(self._player.duration()))
        self._slider.setRange(0, self._duration_ms)
        self._request_waveform_refresh()
        self._refresh_cue_indicator()
        self._refresh_transport_times(self._player.position())
        self._set_loading_state(False)

    def _on_duration_changed(self, duration: int) -> None:
        self._duration_ms = max(0, int(duration))
        self._slider.setRange(0, self._duration_ms)
        self._refresh_transport_times(self._player.position())
        self._refresh_cue_indicator()

    def _on_state_changed(self, _state: int) -> None:
        self._play_btn.setText("Pause" if self._player.state() == ExternalMediaPlayer.PlayingState else "Play")

    def _on_position_changed(self, position: int) -> None:
        position_ms = max(0, int(position))
        if not self._is_scrubbing:
            self._slider.setValue(position_ms)
        self._refresh_transport_times(position_ms)
        self._highlight_row_for_position(position_ms)

    def _refresh_transport_times(self, position_ms: int) -> None:
        total = max(0, int(self._duration_ms))
        position_value = max(0, min(total, int(position_ms)))
        remaining = max(0, total - position_value)
        self._total_label.setText(f"Total {self._format_clock_time(total)}")
        self._elapsed_label.setText(f"Elapsed {self._format_clock_time(position_value)}")
        self._remaining_label.setText(f"Remaining {self._format_clock_time(remaining)}")

    def _refresh_cue_indicator(self) -> None:
        self._cue_indicator.set_values(self._duration_ms, self._cue_start_ms, self._cue_end_ms)

    def _play(self) -> None:
        if callable(self._stop_host_playback):
            try:
                self._stop_host_playback()
            except Exception:
                pass
        if self._player.state() == ExternalMediaPlayer.PlayingState:
            self._player.pause()
            return
        self._player.play()

    def _stop(self) -> None:
        self._player.stop()
        self._player.setPosition(0)

    def _on_slider_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_slider_released(self) -> None:
        self._is_scrubbing = False
        self._player.setPosition(max(0, int(self._slider.value())))

    def _on_slider_value_changed(self, value: int) -> None:
        if self._is_scrubbing:
            self._refresh_transport_times(max(0, int(value)))
            self._highlight_row_for_position(max(0, int(value)))

    def _rebuild_table(self) -> None:
        self._display_rows = []
        for cue in list(self._script.cues or []):
            self._display_rows.append({"kind": "cue", "time_ms": int(cue.time_ms), "cue": cue, "lyric": ""})
        if self._show_lyric_checkbox.isChecked():
            for line in self._lyric_lines:
                self._display_rows.append(
                    {
                        "kind": "lyric",
                        "time_ms": int(line.start_ms),
                        "cue": None,
                        "lyric": str(line.text or ""),
                    }
                )
        self._display_rows.sort(key=lambda item: (int(item["time_ms"]), 0 if item["kind"] == "cue" else 1))
        self._table.setRowCount(0)
        for row_idx, row in enumerate(self._display_rows):
            self._table.insertRow(row_idx)
            ts_item = QTableWidgetItem(self._format_timestamp(int(row["time_ms"])))
            ts_item.setFlags(ts_item.flags() & ~Qt.ItemIsEditable)
            cue = row.get("cue")
            if cue is not None:
                comment = str(getattr(cue, "comment", "") or "")
                commands = automation_script_cue_command_summary(cue)
                lyric = self._lyric_text_for_time(int(row["time_ms"]))
            else:
                comment = ""
                commands = ""
                lyric = str(row.get("lyric", "") or "")
            comment_item = QTableWidgetItem(comment)
            command_item = QTableWidgetItem(commands)
            lyric_item = QTableWidgetItem(lyric)
            for item in (comment_item, command_item, lyric_item):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row_idx, 0, ts_item)
            self._table.setItem(row_idx, 1, comment_item)
            self._table.setItem(row_idx, 2, command_item)
            self._table.setItem(row_idx, 3, lyric_item)
        self._highlight_row_for_position(max(0, int(self._slider.value())))
        self._refresh_action_buttons()

    def _highlight_row_for_position(self, position_ms: int) -> None:
        if not self._display_rows:
            self._table.clearSelection()
            return
        row = -1
        for idx, item in enumerate(self._display_rows):
            if int(item["time_ms"]) <= position_ms:
                row = idx
            else:
                break
        if row >= 0:
            self._table.selectRow(row)
            current_item = self._table.item(row, 0)
            if current_item is not None:
                self._table.scrollToItem(current_item, QTableWidget.PositionAtCenter)

    def _on_table_clicked(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self._display_rows):
            return
        target_ms = max(0, int(self._display_rows[row]["time_ms"]))
        self._player.setPosition(target_ms)
        self._refresh_action_buttons()

    def _refresh_action_buttons(self) -> None:
        row = int(self._table.currentRow())
        selected = self._display_rows[row] if 0 <= row < len(self._display_rows) else None
        selected_is_cue = bool(selected and selected.get("kind") == "cue")
        selected_is_lyric = bool(selected and selected.get("kind") == "lyric")
        self._edit_btn.setEnabled(selected_is_cue)
        self._delete_btn.setEnabled(selected_is_cue)
        self._add_selected_lyric_btn.setEnabled(selected_is_lyric)

    def _cue_for_time(self, time_ms: int) -> Optional[AutomationScriptCue]:
        target_ms = max(0, int(time_ms))
        for cue in list(self._script.cues or []):
            if int(cue.time_ms) == target_ms:
                return cue
        return None

    def _add_cue_at_current(self) -> None:
        self._edit_or_create_cue(max(0, int(self._slider.value())))

    def _add_cue_at_selected_lyric(self) -> None:
        row = int(self._table.currentRow())
        if row < 0 or row >= len(self._display_rows):
            return
        item = self._display_rows[row]
        if item.get("kind") != "lyric":
            return
        self._edit_or_create_cue(max(0, int(item["time_ms"])))

    def _edit_selected_cue(self) -> None:
        row = int(self._table.currentRow())
        if row < 0 or row >= len(self._display_rows):
            return
        item = self._display_rows[row]
        cue = item.get("cue")
        if item.get("kind") != "cue" or cue is None:
            return
        self._edit_or_create_cue(int(cue.time_ms))

    def _delete_selected_cue(self) -> None:
        row = int(self._table.currentRow())
        if row < 0 or row >= len(self._display_rows):
            return
        item = self._display_rows[row]
        cue = item.get("cue")
        if item.get("kind") != "cue" or cue is None:
            return
        remaining = [existing for existing in list(self._script.cues or []) if int(existing.time_ms) != int(cue.time_ms)]
        self._script.cues = remaining
        self._rebuild_table()

    def _edit_or_create_cue(self, time_ms: int) -> None:
        cue = self._cue_for_time(time_ms)
        if cue is None:
            cue = AutomationScriptCue(time_ms=max(0, int(time_ms)), comment="", actions=[])
            current_cues = list(self._script.cues or [])
            current_cues.append(cue)
            self._script.cues = sorted(current_cues, key=lambda item: int(item.time_ms))
        comment, actions, accepted = self._open_cue_dialog(cue)
        if not accepted:
            if cue not in list(self._script.cues or []) or list(cue.actions or []):
                self._rebuild_table()
            else:
                self._script.cues = [existing for existing in list(self._script.cues or []) if existing is not cue]
                self._rebuild_table()
            return
        cue.comment = comment
        cue.actions = [
            AutomationScriptAction(
                type=AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
                payload=normalize_automation_spec(action),
            )
            for action in list(actions or [])
            if normalize_automation_spec(action).location
        ]
        if not cue.actions:
            self._script.cues = [existing for existing in list(self._script.cues or []) if existing is not cue]
        self._script.cues = sorted(list(self._script.cues or []), key=lambda item: int(item.time_ms))
        self._rebuild_table()

    def _open_cue_dialog(
        self,
        cue: AutomationScriptCue,
    ) -> tuple[str, List[AutomationCommandSpec], bool]:
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Automation Cue"))
        dialog.resize(760, 460)
        root = QVBoxLayout(dialog)
        root.addWidget(QLabel(f"{tr('Timestamp')}: {self._format_timestamp(int(cue.time_ms))}", dialog))
        form = QFormLayout()
        comment_edit = QLineEdit(str(cue.comment or ""), dialog)
        form.addRow(tr("Comment"), comment_edit)
        root.addLayout(form)

        table = QTableWidget(0, 2, dialog)
        table.setHorizontalHeaderLabels([tr("Location"), tr("Button")])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        root.addWidget(table, 1)

        actions: List[AutomationCommandSpec] = [
            normalize_automation_spec(getattr(action, "payload", None) or {})
            for action in list(cue.actions or [])
            if normalize_automation_spec(getattr(action, "payload", None) or {}).location
        ]

        def refresh_table() -> None:
            table.setRowCount(0)
            for row_idx, spec in enumerate(actions):
                table.insertRow(row_idx)
                location_item = QTableWidgetItem(str(spec.location or ""))
                button_item = QTableWidgetItem(str(spec.button_text or ""))
                location_item.setFlags(location_item.flags() & ~Qt.ItemIsEditable)
                button_item.setFlags(button_item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_idx, 0, location_item)
                table.setItem(row_idx, 1, button_item)

        refresh_table()

        action_row = QHBoxLayout()
        add_command_btn = QPushButton(tr("Add Command"), dialog)
        remove_command_btn = QPushButton(tr("Remove Selected Command"), dialog)
        action_row.addWidget(add_command_btn)
        action_row.addWidget(remove_command_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        root.addWidget(buttons)

        def add_command() -> None:
            picker = AutomationCommandSoundButtonDialog(
                caption="",
                notes="",
                automation_spec=None,
                companion_payload=self._companion_payload,
                hide_black_empty=self._hide_black_empty,
                selection_only=True,
                window_title=tr("Select Companion Command"),
                parent=dialog,
            )
            if picker.exec_() != QDialog.Accepted:
                return
            _caption, _notes, spec, _color, _hotkey, _midi = picker.values()
            normalized = normalize_automation_spec(spec)
            if not normalized.location:
                return
            actions.append(normalized)
            refresh_table()

        def remove_command() -> None:
            row = int(table.currentRow())
            if 0 <= row < len(actions):
                actions.pop(row)
                refresh_table()

        add_command_btn.clicked.connect(add_command)
        remove_command_btn.clicked.connect(remove_command)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec_() != QDialog.Accepted:
            return str(cue.comment or ""), list(actions), False
        return comment_edit.text().strip(), list(actions), True

    def _save(self) -> None:
        self._script.notes = self._notes_edit.toPlainText().strip()
        self._script.cues = sorted(
            [
                cue
                for cue in list(self._script.cues or [])
                if list(getattr(cue, "actions", []) or [])
            ],
            key=lambda item: int(item.time_ms),
        )
        try:
            save_automation_script(self._script_path, self._script)
        except Exception as exc:
            QMessageBox.warning(self, tr("Automation Script Editor"), f"{tr('Failed to save automation script:')}\n{exc}")
            return
        self.accept()

    def _lyric_text_for_time(self, time_ms: int) -> str:
        for line in self._lyric_lines:
            if int(line.start_ms) == int(time_ms):
                return str(line.text or "")
        return ""

    @staticmethod
    def _format_clock_time(ms: int) -> str:
        value = max(0, int(ms))
        hours = value // 3600000
        minutes = (value // 60000) % 60
        seconds = (value // 1000) % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _format_timestamp(ms: int) -> str:
        value = max(0, int(ms))
        hours = value // 3600000
        minutes = (value // 60000) % 60
        seconds = (value // 1000) % 60
        millis = value % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
