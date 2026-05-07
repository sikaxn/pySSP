from __future__ import annotations

import os
import time
from typing import Callable, List, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIntValidator
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import ExternalMediaPlayer, is_audio_preloaded, request_audio_preload
from pyssp.automation_command import AutomationCommandSpec, normalize_automation_spec
from pyssp.automation_script import (
    AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
    AutomationScript,
    AutomationScriptAction,
    AutomationScriptCue,
    automation_script_cue_command_summary,
    load_automation_script,
    save_automation_script,
)
from pyssp.companion_available_commands import (
    is_black_empty_command,
    is_navigation_command,
    list_companion_available_commands,
)
from pyssp.i18n import localize_widget_tree, tr
from pyssp.lyrics import LyricLine, parse_lyric_file
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
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.resize(1280, 760)

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
        self._active_row = -1
        self._updating_cue_form = False

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

        waveform_row = QHBoxLayout()
        waveform_row.setSpacing(8)
        self._cue_indicator = CueRangeIndicator()
        waveform_row.addWidget(self._cue_indicator, 1)
        self._waveform_refresh = WaveformRefreshController(
            on_peaks=self._cue_indicator.set_waveform,
            is_valid=lambda: self._duration_ms > 0,
            sample_count=1800,
            parent=self,
        )

        notes_panel = QWidget(self)
        notes_panel.setMaximumWidth(280)
        notes_panel.setMinimumWidth(220)
        notes_layout = QVBoxLayout(notes_panel)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        notes_layout.setSpacing(4)
        notes_layout.addWidget(QLabel(tr("Notes"), self))
        self._notes_edit = QPlainTextEdit(str(self._script.notes or ""))
        self._notes_edit.setPlaceholderText(tr("Optional script-wide notes"))
        self._notes_edit.setMaximumHeight(40)
        self._notes_edit.setMaximumWidth(260)
        notes_layout.addWidget(self._notes_edit)
        waveform_row.addWidget(notes_panel, 0, Qt.AlignTop)
        root.addLayout(waveform_row)

        toggle_row = QHBoxLayout()
        self._show_lyric_checkbox = QCheckBox(tr("Show lyric alongside automation cues"))
        self._show_lyric_checkbox.setChecked(bool(self._lyric_lines))
        self._show_lyric_checkbox.setEnabled(bool(self._lyric_lines))
        toggle_row.addWidget(self._show_lyric_checkbox)
        toggle_row.addStretch(1)
        root.addLayout(toggle_row)

        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self._timeline_hint_label = QLabel(
            tr("1. Pick a cue or lyric time here. This top list is your timing map.")
        )
        self._timeline_hint_label.setWordWrap(True)
        self._timeline_hint_label.setStyleSheet(
            "QLabel{background:#EAF3FF;border:1px solid #9DBEE8;border-radius:4px;padding:6px;font-weight:600;}"
        )
        left_layout.addWidget(self._timeline_hint_label)

        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels([tr("Timestamp"), tr("Comment"), tr("Commands"), tr("Lyric")])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        left_layout.addWidget(self._table, 3)

        actions = QHBoxLayout()
        self._add_current_btn = QPushButton(tr("Add Cue At Current Timestamp"))
        self._add_selected_lyric_btn = QPushButton(tr("Add Cue On Selected Lyric Time"))
        self._delete_btn = QPushButton(tr("Delete Selected Cue"))
        actions.addWidget(self._add_current_btn)
        actions.addWidget(self._add_selected_lyric_btn)
        actions.addWidget(self._delete_btn)
        actions.addStretch(1)
        left_layout.addLayout(actions)

        cue_group = QGroupBox(tr("Automation Cue"), self)
        cue_layout = QVBoxLayout(cue_group)
        cue_layout.setContentsMargins(8, 8, 8, 8)
        cue_layout.setSpacing(6)

        self._cue_editor_hint_label = QLabel(
            tr("2. Edit the selected cue here. Add comments only if they help the operator.")
        )
        self._cue_editor_hint_label.setWordWrap(True)
        self._cue_editor_hint_label.setStyleSheet(
            "QLabel{background:#EEF9EC;border:1px solid #9BC78C;border-radius:4px;padding:6px;font-weight:600;}"
        )
        cue_layout.addWidget(self._cue_editor_hint_label)

        cue_form = QFormLayout()
        self._cue_timestamp_label = QLabel("-")
        cue_form.addRow(tr("Timestamp"), self._cue_timestamp_label)
        comment_row = QWidget(self)
        comment_row_layout = QHBoxLayout(comment_row)
        comment_row_layout.setContentsMargins(0, 0, 0, 0)
        self._cue_comment_edit = QLineEdit(self)
        self._cue_comment_edit.setPlaceholderText(tr("Optional operator note for this cue"))
        self._cue_comment_edit.setMaximumWidth(360)
        comment_row_layout.addWidget(self._cue_comment_edit)
        comment_row_layout.addStretch(1)
        cue_form.addRow(tr("Comment"), comment_row)
        cue_layout.addLayout(cue_form)

        self._cue_commands_table = QTableWidget(0, 3, self)
        self._cue_commands_table.setHorizontalHeaderLabels([tr("Location"), tr("Button"), tr("Input")])
        self._cue_commands_table.verticalHeader().setVisible(False)
        self._cue_commands_table.horizontalHeader().setStretchLastSection(True)
        self._cue_commands_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._cue_commands_table.setSelectionMode(QTableWidget.SingleSelection)
        self._cue_commands_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        cue_layout.addWidget(self._cue_commands_table, 1)

        cue_button_row = QHBoxLayout()
        self._add_selected_command_btn = QPushButton(tr("Add Selected Command To Cue"))
        self._remove_command_btn = QPushButton(tr("Remove Selected Command"))
        self._move_command_up_btn = QPushButton(tr("Move Up"))
        self._move_command_down_btn = QPushButton(tr("Move Down"))
        cue_button_row.addWidget(self._add_selected_command_btn)
        cue_button_row.addWidget(self._remove_command_btn)
        cue_button_row.addWidget(self._move_command_up_btn)
        cue_button_row.addWidget(self._move_command_down_btn)
        cue_button_row.addStretch(1)
        cue_layout.addLayout(cue_button_row)

        self._cue_hint_label = QLabel(tr("Select a cue row to edit it. Cues without commands are not saved."))
        self._cue_hint_label.setWordWrap(True)
        cue_layout.addWidget(self._cue_hint_label)
        cue_group.setMaximumHeight(300)
        left_layout.addWidget(cue_group, 1)

        splitter.addWidget(left_panel)

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        command_group = QGroupBox(tr("Companion Command"), self)
        command_layout = QVBoxLayout(command_group)
        command_layout.setContentsMargins(8, 8, 8, 8)
        command_layout.setSpacing(6)

        self._command_panel_hint_label = QLabel(
            tr("3. Pick a Companion command on the right, then add it into the selected cue.")
        )
        self._command_panel_hint_label.setWordWrap(True)
        self._command_panel_hint_label.setStyleSheet(
            "QLabel{background:#FFF4E5;border:1px solid #E0B26C;border-radius:4px;padding:6px;font-weight:600;}"
        )
        command_layout.addWidget(self._command_panel_hint_label)

        command_form = QFormLayout()
        self._selected_command_label = QLabel("-")
        command_form.addRow(tr("Selected Command"), self._selected_command_label)
        command_layout.addLayout(command_form)

        mode_row = QWidget(self)
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        self._pick_from_list_radio = QRadioButton(tr("Pick from Available Commands"))
        self._manual_location_radio = QRadioButton(tr("Enter Location Manually"))
        self._location_mode_group = QButtonGroup(self)
        self._location_mode_group.addButton(self._pick_from_list_radio)
        self._location_mode_group.addButton(self._manual_location_radio)
        mode_layout.addWidget(self._pick_from_list_radio)
        mode_layout.addWidget(self._manual_location_radio)
        command_layout.addWidget(mode_row)

        manual_row = QWidget(self)
        manual_layout = QHBoxLayout(manual_row)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        numeric_validator = QIntValidator(0, 9999, self)
        self._manual_page_edit = QLineEdit(self)
        self._manual_page_edit.setPlaceholderText(tr("Page"))
        self._manual_row_edit = QLineEdit(self)
        self._manual_row_edit.setPlaceholderText(tr("Row"))
        self._manual_column_edit = QLineEdit(self)
        self._manual_column_edit.setPlaceholderText(tr("Column"))
        for edit in (self._manual_page_edit, self._manual_row_edit, self._manual_column_edit):
            edit.setValidator(numeric_validator)
            edit.setMaxLength(4)
            manual_layout.addWidget(edit)
        command_layout.addWidget(manual_row)

        self._hold_to_release_checkbox = QCheckBox(tr("Respect press-down / release-up input"))
        command_layout.addWidget(self._hold_to_release_checkbox)

        filters_row = QGridLayout()
        self._hide_black_empty_checkbox = QCheckBox(tr("Hide Black Empty Buttons"))
        self._hide_black_empty_checkbox.setChecked(bool(self._hide_black_empty))
        self._hide_navigation_checkbox = QCheckBox(tr("Hide Page Buttons"))
        self._search_edit = QLineEdit(self)
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.setPlaceholderText(tr("Search by location or button text"))
        filters_row.addWidget(self._hide_black_empty_checkbox, 0, 0)
        filters_row.addWidget(self._hide_navigation_checkbox, 0, 1)
        filters_row.addWidget(QLabel(tr("Search:")), 1, 0)
        filters_row.addWidget(self._search_edit, 1, 1)
        command_layout.addLayout(filters_row)

        self._command_help_label = QLabel(
            tr("Pick a Companion Available Command below. If your command is missing, open Available Commands or Virtual Satellite first so pySSP can learn it.")
        )
        self._command_help_label.setWordWrap(True)
        command_layout.addWidget(self._command_help_label)

        self._command_table = QTableWidget(self)
        self._command_table.setColumnCount(3)
        self._command_table.setHorizontalHeaderLabels([tr("Location"), tr("Type"), tr("Button")])
        self._command_table.setSortingEnabled(True)
        self._command_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._command_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._command_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._command_table.verticalHeader().setVisible(False)
        self._command_table.horizontalHeader().setStretchLastSection(True)
        command_layout.addWidget(self._command_table, 1)

        self._command_text_label = QLabel("")
        self._command_text_label.setWordWrap(True)
        command_layout.addWidget(self._command_text_label)
        right_layout.addWidget(command_group, 1)
        splitter.addWidget(right_panel)
        splitter.setSizes([900, 360])

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
        self._table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self._add_current_btn.clicked.connect(self._add_cue_at_current)
        self._add_selected_lyric_btn.clicked.connect(self._add_cue_at_selected_lyric)
        self._delete_btn.clicked.connect(self._delete_selected_cue)
        self._cue_comment_edit.textChanged.connect(self._on_cue_comment_changed)
        self._cue_commands_table.itemSelectionChanged.connect(self._refresh_action_buttons)
        self._add_selected_command_btn.clicked.connect(self._add_selected_command_to_current_cue)
        self._remove_command_btn.clicked.connect(self._remove_selected_command)
        self._move_command_up_btn.clicked.connect(lambda _=False: self._move_selected_command(-1))
        self._move_command_down_btn.clicked.connect(lambda _=False: self._move_selected_command(1))
        self._command_table.itemSelectionChanged.connect(self._sync_selected_command)
        self._command_table.itemDoubleClicked.connect(lambda _item: self._add_selected_command_to_current_cue())
        self._hide_black_empty_checkbox.toggled.connect(self._apply_command_filters)
        self._hide_navigation_checkbox.toggled.connect(self._apply_command_filters)
        self._search_edit.textChanged.connect(self._apply_command_filters)
        self._pick_from_list_radio.toggled.connect(self._on_location_mode_changed)
        self._manual_page_edit.textChanged.connect(self._sync_selected_command)
        self._manual_row_edit.textChanged.connect(self._sync_selected_command)
        self._manual_column_edit.textChanged.connect(self._sync_selected_command)
        self._hold_to_release_checkbox.toggled.connect(self._sync_selected_command)

        self._apply_command_filters()
        if self._command_table.rowCount() > 0:
            self._pick_from_list_radio.setChecked(True)
        else:
            self._manual_location_radio.setChecked(True)
        self._on_location_mode_changed()
        self._refresh_cue_indicator()
        self._refresh_transport_times(0)
        self._rebuild_table()
        self._refresh_cue_editor()
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

    def _selected_row_data(self) -> Optional[dict]:
        row = int(self._table.currentRow())
        if row < 0 or row >= len(self._display_rows):
            return None
        return self._display_rows[row]

    def _selected_cue(self) -> Optional[AutomationScriptCue]:
        selected = self._selected_row_data()
        if not selected or selected.get("kind") != "cue":
            return None
        cue = selected.get("cue")
        return cue if isinstance(cue, AutomationScriptCue) else None

    def _cue_for_time(self, time_ms: int) -> Optional[AutomationScriptCue]:
        target_ms = max(0, int(time_ms))
        for cue in list(self._script.cues or []):
            if int(cue.time_ms) == target_ms:
                return cue
        return None

    def _ensure_cue(self, time_ms: int) -> AutomationScriptCue:
        cue = self._cue_for_time(time_ms)
        if cue is not None:
            return cue
        cue = AutomationScriptCue(time_ms=max(0, int(time_ms)), comment="", actions=[])
        current_cues = list(self._script.cues or [])
        current_cues.append(cue)
        self._script.cues = sorted(current_cues, key=lambda item: int(item.time_ms))
        return cue

    def _rebuild_table(self, selected_time_ms: Optional[int] = None) -> None:
        if selected_time_ms is None:
            selected_cue = self._selected_cue()
            if selected_cue is not None:
                selected_time_ms = int(selected_cue.time_ms)
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
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        selected_row = -1
        for row_idx, row in enumerate(self._display_rows):
            self._table.insertRow(row_idx)
            ts_item = QTableWidgetItem(self._format_timestamp(int(row["time_ms"])))
            ts_item.setFlags(ts_item.flags() & ~Qt.ItemIsEditable)
            cue = row.get("cue")
            if cue is not None:
                comment = str(getattr(cue, "comment", "") or "")
                commands = automation_script_cue_command_summary(cue)
                lyric = self._lyric_text_for_time(int(row["time_ms"]))
                if selected_time_ms is not None and int(cue.time_ms) == int(selected_time_ms):
                    selected_row = row_idx
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
        self._table.blockSignals(False)
        if selected_row >= 0:
            self._table.selectRow(selected_row)
        self._highlight_row_for_position(max(0, int(self._slider.value())))
        self._refresh_cue_editor()
        self._refresh_action_buttons()

    def _set_active_row(self, row: int) -> None:
        previous = self._active_row
        self._active_row = row if 0 <= row < self._table.rowCount() else -1
        for row_index in {previous, self._active_row}:
            if row_index < 0:
                continue
            for column in range(self._table.columnCount()):
                item = self._table.item(row_index, column)
                if item is None:
                    continue
                if row_index == self._active_row:
                    item.setBackground(Qt.yellow)
                else:
                    item.setBackground(Qt.white)

    def _highlight_row_for_position(self, position_ms: int) -> None:
        if not self._display_rows:
            self._set_active_row(-1)
            return
        row = -1
        for idx, item in enumerate(self._display_rows):
            if int(item["time_ms"]) <= position_ms:
                row = idx
            else:
                break
        self._set_active_row(row)

    def _on_table_clicked(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self._display_rows):
            return
        target_ms = max(0, int(self._display_rows[row]["time_ms"]))
        self._player.setPosition(target_ms)

    def _on_table_selection_changed(self) -> None:
        self._refresh_cue_editor()
        self._refresh_action_buttons()

    def _refresh_cue_editor(self) -> None:
        cue = self._selected_cue()
        self._updating_cue_form = True
        try:
            enabled = cue is not None
            self._cue_timestamp_label.setText("-" if cue is None else self._format_timestamp(int(cue.time_ms)))
            self._cue_comment_edit.setEnabled(enabled)
            self._cue_comment_edit.setText("" if cue is None else str(cue.comment or ""))
            self._cue_commands_table.setEnabled(enabled)
            self._cue_commands_table.setRowCount(0)
            if cue is not None:
                for row_index, action in enumerate(list(cue.actions or [])):
                    spec = normalize_automation_spec(getattr(action, "payload", None) or {})
                    self._cue_commands_table.insertRow(row_index)
                    location_item = QTableWidgetItem(str(spec.location or ""))
                    button_item = QTableWidgetItem(str(spec.button_text or ""))
                    input_item = QTableWidgetItem(
                        tr("Press / Release") if bool(spec.hold_to_release) else tr("Normal")
                    )
                    for item in (location_item, button_item, input_item):
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self._cue_commands_table.setItem(row_index, 0, location_item)
                    self._cue_commands_table.setItem(row_index, 1, button_item)
                    self._cue_commands_table.setItem(row_index, 2, input_item)
            self._cue_hint_label.setText(
                tr("Select a cue row to edit it. Cues without commands are not saved.")
                if cue is None
                else tr("This cue is edited inline. Use the right panel to add Companion commands.")
            )
        finally:
            self._updating_cue_form = False
        self._refresh_action_buttons()

    def _refresh_action_buttons(self) -> None:
        selected = self._selected_row_data()
        cue = self._selected_cue()
        selected_is_lyric = bool(selected and selected.get("kind") == "lyric")
        selected_command_row = int(self._cue_commands_table.currentRow())
        cue_command_count = 0 if cue is None else len(list(cue.actions or []))
        can_add_command = cue is not None and bool(self._build_selected_command_spec().location)
        self._delete_btn.setEnabled(cue is not None)
        self._add_selected_lyric_btn.setEnabled(selected_is_lyric)
        self._add_selected_command_btn.setEnabled(can_add_command)
        self._remove_command_btn.setEnabled(cue is not None and 0 <= selected_command_row < cue_command_count)
        self._move_command_up_btn.setEnabled(cue is not None and selected_command_row > 0)
        self._move_command_down_btn.setEnabled(
            cue is not None and 0 <= selected_command_row < cue_command_count - 1
        )

    def _add_cue_at_current(self) -> None:
        cue = self._ensure_cue(max(0, int(self._slider.value())))
        self._rebuild_table(selected_time_ms=int(cue.time_ms))

    def _add_cue_at_selected_lyric(self) -> None:
        selected = self._selected_row_data()
        if not selected or selected.get("kind") != "lyric":
            return
        cue = self._ensure_cue(max(0, int(selected["time_ms"])))
        self._rebuild_table(selected_time_ms=int(cue.time_ms))

    def _delete_selected_cue(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        self._script.cues = [existing for existing in list(self._script.cues or []) if int(existing.time_ms) != int(cue.time_ms)]
        self._rebuild_table(selected_time_ms=None)

    def _on_cue_comment_changed(self, text: str) -> None:
        if self._updating_cue_form:
            return
        cue = self._selected_cue()
        if cue is None:
            return
        cue.comment = str(text or "").strip()
        row = int(self._table.currentRow())
        if row >= 0:
            item = self._table.item(row, 1)
            if item is not None:
                item.setText(cue.comment)

    def _apply_command_filters(self) -> None:
        rows = list_companion_available_commands(self._companion_payload)
        if self._hide_black_empty_checkbox.isChecked():
            rows = [entry for entry in rows if not is_black_empty_command(entry)]
        if self._hide_navigation_checkbox.isChecked():
            rows = [entry for entry in rows if not is_navigation_command(entry)]
        query = str(self._search_edit.text() or "").strip().lower()
        if query:
            rows = [
                entry
                for entry in rows
                if query in f"{entry.get('page', '')}/{entry.get('row', '')}/{entry.get('column', '')}".lower()
                or query in str(entry.get("text", "") or "").lower()
            ]
        previous_location = self._build_selected_command_spec().location
        self._command_table.setSortingEnabled(False)
        self._command_table.setRowCount(len(rows))
        selected_row = -1
        for row_index, entry in enumerate(rows):
            location_value = f"{entry.get('page', '')}/{entry.get('row', '')}/{entry.get('column', '')}"
            location_item = QTableWidgetItem(location_value)
            location_item.setTextAlignment(Qt.AlignCenter)
            location_item.setData(Qt.UserRole, location_value)
            type_item = QTableWidgetItem(str(entry.get("type", "") or ""))
            type_item.setTextAlignment(Qt.AlignCenter)
            button_item = QTableWidgetItem(str(entry.get("text", "") or ""))
            button_item.setData(Qt.UserRole, str(entry.get("text", "") or ""))
            color = QColor(str(entry.get("color", "") or ""))
            if color.isValid():
                button_item.setBackground(color)
                button_item.setForeground(QColor(255 - color.red(), 255 - color.green(), 255 - color.blue()))
            self._command_table.setItem(row_index, 0, location_item)
            self._command_table.setItem(row_index, 1, type_item)
            self._command_table.setItem(row_index, 2, button_item)
            if location_value == previous_location:
                selected_row = row_index
        self._command_table.resizeColumnsToContents()
        self._command_table.setSortingEnabled(True)
        if selected_row >= 0:
            self._command_table.selectRow(selected_row)
        elif self._command_table.rowCount() > 0:
            self._command_table.selectRow(0)
        self._sync_selected_command()

    def _find_command_row(self, location: str) -> int:
        target = str(location or "").strip()
        if not target:
            return -1
        for row_index in range(self._command_table.rowCount()):
            item = self._command_table.item(row_index, 0)
            if item is not None and str(item.data(Qt.UserRole) or item.text() or "").strip() == target:
                return row_index
        return -1

    def _selected_command_location_from_table(self) -> str:
        row = int(self._command_table.currentRow())
        if row < 0:
            return ""
        item = self._command_table.item(row, 0)
        if item is None:
            return ""
        return str(item.data(Qt.UserRole) or item.text() or "").strip()

    def _selected_command_text_from_table(self) -> str:
        row = int(self._command_table.currentRow())
        if row < 0:
            return ""
        item = self._command_table.item(row, 2)
        if item is None:
            return ""
        return str(item.data(Qt.UserRole) or item.text() or "").strip()

    def _build_selected_command_spec(self) -> AutomationCommandSpec:
        if self._manual_location_radio.isChecked():
            parts = [
                str(self._manual_page_edit.text() or "").strip(),
                str(self._manual_row_edit.text() or "").strip(),
                str(self._manual_column_edit.text() or "").strip(),
            ]
            location = "/".join(parts) if all(parts) else ""
            button_text = ""
        else:
            location = self._selected_command_location_from_table()
            button_text = self._selected_command_text_from_table()
        return normalize_automation_spec(
            {
                "location": location,
                "button_text": button_text,
                "hold_to_release": bool(self._hold_to_release_checkbox.isChecked()),
            }
        )

    def _sync_selected_command(self) -> None:
        spec = self._build_selected_command_spec()
        self._selected_command_label.setText(spec.location or "-")
        if spec.button_text:
            self._command_text_label.setText(spec.button_text)
        elif self._manual_location_radio.isChecked():
            self._command_text_label.setText(tr("Manual location entry"))
        else:
            self._command_text_label.setText("")
        self._refresh_action_buttons()

    def _on_location_mode_changed(self) -> None:
        use_picker = self._pick_from_list_radio.isChecked()
        self._hide_black_empty_checkbox.setEnabled(use_picker)
        self._hide_navigation_checkbox.setEnabled(use_picker)
        self._search_edit.setEnabled(use_picker)
        self._command_table.setEnabled(use_picker)
        self._manual_page_edit.setEnabled(not use_picker)
        self._manual_row_edit.setEnabled(not use_picker)
        self._manual_column_edit.setEnabled(not use_picker)
        if use_picker and self._command_table.rowCount() > 0 and self._command_table.currentRow() < 0:
            self._command_table.selectRow(0)
        self._sync_selected_command()

    def _add_selected_command_to_current_cue(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        spec = self._build_selected_command_spec()
        if not spec.location:
            return
        action = AutomationScriptAction(
            type=AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
            payload=normalize_automation_spec(spec),
        )
        cue.actions = list(cue.actions or []) + [action]
        self._refresh_cue_editor()
        self._refresh_selected_cue_row()

    def _remove_selected_command(self) -> None:
        cue = self._selected_cue()
        row = int(self._cue_commands_table.currentRow())
        if cue is None or row < 0:
            return
        actions = list(cue.actions or [])
        if row >= len(actions):
            return
        actions.pop(row)
        cue.actions = actions
        self._refresh_cue_editor()
        self._refresh_selected_cue_row()

    def _move_selected_command(self, delta: int) -> None:
        cue = self._selected_cue()
        row = int(self._cue_commands_table.currentRow())
        if cue is None or row < 0:
            return
        actions = list(cue.actions or [])
        new_index = row + int(delta)
        if row >= len(actions) or new_index < 0 or new_index >= len(actions):
            return
        actions[row], actions[new_index] = actions[new_index], actions[row]
        cue.actions = actions
        self._refresh_cue_editor()
        self._cue_commands_table.selectRow(new_index)
        self._refresh_selected_cue_row()

    def _refresh_selected_cue_row(self) -> None:
        cue = self._selected_cue()
        row = int(self._table.currentRow())
        if cue is None or row < 0:
            return
        comment_item = self._table.item(row, 1)
        if comment_item is not None:
            comment_item.setText(str(cue.comment or ""))
        command_item = self._table.item(row, 2)
        if command_item is not None:
            command_item.setText(automation_script_cue_command_summary(cue))
        self._refresh_action_buttons()

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
