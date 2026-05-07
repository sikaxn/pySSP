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
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QRadioButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import ExternalMediaPlayer, is_audio_preloaded, request_audio_preload
from pyssp.automation_command import (
    AUTOMATION_COMMAND_SOURCE_COMPANION,
    AUTOMATION_COMMAND_SOURCE_INTERNAL,
    AutomationCommandSpec,
    automation_display_name,
    automation_spec_detail_text,
    automation_spec_is_valid,
    normalize_automation_spec,
)
from pyssp.automation_script import (
    AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
    AUTOMATION_SCRIPT_ACTION_TYPE_INTERNAL_COMMAND,
    AutomationScript,
    AutomationScriptAction,
    AutomationScriptCue,
    automation_script_cue_command_summary,
    automation_script_command_display_name,
    load_automation_script,
    save_automation_script,
)
from pyssp.companion_available_commands import (
    is_black_empty_command,
    is_navigation_command,
    list_companion_available_commands,
)
from pyssp.i18n import localize_widget_tree, tr
from pyssp.internal_automation import list_internal_automation_commands, normalize_internal_automation_params
from pyssp.lyrics import LyricLine, parse_lyric_file
from pyssp.ui.waveform_view import CueRangeIndicator, WaveformRefreshController


_TARGET_GROUPS = list("ABCDEFGHIJ") + ["Q"]
_TARGET_PAGE_COUNT = 18
_TARGET_SLOTS_PER_PAGE = 48


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
        show_lyric_default: bool = False,
        on_show_lyric_changed: Optional[Callable[[bool], None]] = None,
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
        self._show_lyric_default = bool(show_lyric_default)
        self._on_show_lyric_changed = on_show_lyric_changed
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
        self._play_btn = QPushButton(tr("Play"))
        self._stop_btn = QPushButton(tr("Stop"))
        transport.addWidget(self._play_btn)
        transport.addWidget(self._stop_btn)
        transport.addStretch(1)
        self._total_label = QLabel(f"{tr('Total')} 00:00:00")
        self._elapsed_label = QLabel(f"{tr('Elapsed')} 00:00:00")
        self._remaining_label = QLabel(f"{tr('Remaining')} 00:00:00")
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
        self._show_lyric_checkbox.setChecked(bool(self._lyric_lines) and self._show_lyric_default)
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

        self._timeline_tree = QTreeWidget(self)
        self._timeline_tree.setColumnCount(4)
        self._timeline_tree.setHeaderLabels([tr("Timestamp"), tr("Type"), tr("Comment / Lyric"), tr("Commands")])
        self._timeline_tree.setRootIsDecorated(True)
        self._timeline_tree.setItemsExpandable(True)
        self._timeline_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._timeline_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._timeline_tree.header().setStretchLastSection(True)
        left_layout.addWidget(self._timeline_tree, 3)

        actions = QHBoxLayout()
        self._add_current_btn = QPushButton(tr("Add Cue At Current Timestamp"))
        self._add_selected_lyric_btn = QPushButton(tr("Add Cue On Selected Lyric Time"))
        self._delete_btn = QPushButton(tr("Delete Selected Cue"))
        actions.addWidget(self._add_current_btn)
        actions.addWidget(self._add_selected_lyric_btn)
        actions.addWidget(self._delete_btn)
        actions.addStretch(1)
        left_layout.addLayout(actions)

        self._cue_editor_panel = QWidget(self)
        self._cue_editor_panel.setObjectName("automationCueEditorPanel")
        self._cue_editor_panel.setStyleSheet(
            "#automationCueEditorPanel{border-top:1px solid #C8D6E6;padding-top:6px;}"
        )
        cue_layout = QVBoxLayout(self._cue_editor_panel)
        cue_layout.setContentsMargins(0, 6, 0, 0)
        cue_layout.setSpacing(6)

        cue_form = QFormLayout()
        timestamp_row = QWidget(self)
        timestamp_row_layout = QHBoxLayout(timestamp_row)
        timestamp_row_layout.setContentsMargins(0, 0, 0, 0)
        timestamp_row_layout.setSpacing(6)
        self._cue_timestamp_edit = QLineEdit(self)
        self._cue_timestamp_edit.setPlaceholderText("00:00:00,000")
        self._cue_timestamp_edit.setMaximumWidth(150)
        self._cue_shift_back_btn = QPushButton(tr("-0.5s"), self)
        self._cue_shift_forward_btn = QPushButton(tr("+0.5s"), self)
        timestamp_row_layout.addWidget(self._cue_timestamp_edit)
        timestamp_row_layout.addWidget(self._cue_shift_back_btn)
        timestamp_row_layout.addWidget(self._cue_shift_forward_btn)
        timestamp_row_layout.addStretch(1)
        cue_form.addRow(tr("Timestamp"), timestamp_row)
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
        self._cue_editor_panel.setMaximumHeight(150)
        left_layout.addWidget(self._cue_editor_panel, 0)

        splitter.addWidget(left_panel)

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        command_group = QGroupBox(tr("Automation Command"), self)
        command_layout = QVBoxLayout(command_group)
        command_layout.setContentsMargins(8, 8, 8, 8)
        command_layout.setSpacing(6)

        command_form = QFormLayout()
        self._selected_command_label = QLabel("-")
        command_form.addRow(tr("Selected Command"), self._selected_command_label)
        command_layout.addLayout(command_form)

        self._command_source_tabs = QTabWidget(self)
        command_layout.addWidget(self._command_source_tabs, 1)

        companion_tab = QWidget(self)
        companion_tab_layout = QVBoxLayout(companion_tab)
        companion_tab_layout.setContentsMargins(0, 0, 0, 0)
        companion_tab_layout.setSpacing(6)

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
        companion_tab_layout.addWidget(mode_row)

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
        companion_tab_layout.addWidget(manual_row)

        self._hold_to_release_checkbox = QCheckBox(tr("Respect press-down / release-up input"))
        companion_tab_layout.addWidget(self._hold_to_release_checkbox)

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
        companion_tab_layout.addLayout(filters_row)

        self._command_help_label = QLabel(
            tr("Pick a Companion Available Command below. If your command is missing, open Available Commands or Virtual Satellite first so pySSP can learn it.")
        )
        self._command_help_label.setWordWrap(True)
        companion_tab_layout.addWidget(self._command_help_label)

        self._command_table = QTableWidget(self)
        self._command_table.setColumnCount(3)
        self._command_table.setHorizontalHeaderLabels([tr("Location"), tr("Type"), tr("Button")])
        self._command_table.setSortingEnabled(True)
        self._command_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._command_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._command_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._command_table.verticalHeader().setVisible(False)
        self._command_table.horizontalHeader().setStretchLastSection(True)
        companion_tab_layout.addWidget(self._command_table, 1)

        self._command_text_label = QLabel("")
        self._command_text_label.setWordWrap(True)
        companion_tab_layout.addWidget(self._command_text_label)
        self._command_source_tabs.addTab(companion_tab, tr("Companion"))

        internal_tab = QWidget(self)
        internal_tab_layout = QHBoxLayout(internal_tab)
        internal_tab_layout.setContentsMargins(0, 0, 0, 0)
        internal_tab_layout.setSpacing(8)
        self._internal_command_list = QListWidget(self)
        internal_tab_layout.addWidget(self._internal_command_list, 1)
        internal_form_panel = QWidget(self)
        internal_form_panel_layout = QVBoxLayout(internal_form_panel)
        internal_form_panel_layout.setContentsMargins(0, 0, 0, 0)
        internal_form_panel_layout.setSpacing(6)
        self._internal_summary_label = QLabel("-")
        self._internal_summary_label.setWordWrap(True)
        internal_form_panel_layout.addWidget(self._internal_summary_label)
        self._internal_form = QFormLayout()
        internal_form_panel_layout.addLayout(self._internal_form)
        self._internal_mode_combo = QComboBox(self)
        self._internal_mode_combo.addItem(tr("Show"), "show")
        self._internal_mode_combo.addItem(tr("Blank"), "blank")
        self._internal_mode_combo.addItem(tr("Toggle"), "toggle")
        self._internal_toggle_mode_combo = QComboBox(self)
        self._internal_toggle_mode_combo.addItem(tr("Enable"), "enable")
        self._internal_toggle_mode_combo.addItem(tr("Disable"), "disable")
        self._internal_toggle_mode_combo.addItem(tr("Toggle"), "toggle")
        self._internal_fade_kind_combo = QComboBox(self)
        self._internal_fade_kind_combo.addItem(tr("Fade In"), "fadein")
        self._internal_fade_kind_combo.addItem(tr("Fade Out"), "fadeout")
        self._internal_fade_kind_combo.addItem(tr("Crossfade"), "crossfade")
        self._internal_reset_scope_combo = QComboBox(self)
        self._internal_reset_scope_combo.addItem(tr("Current"), "current")
        self._internal_reset_scope_combo.addItem(tr("All"), "all")
        self._internal_nav_target_combo = QComboBox(self)
        self._internal_nav_target_combo.addItem(tr("Group"), "group")
        self._internal_nav_target_combo.addItem(tr("Page"), "page")
        self._internal_nav_target_combo.addItem(tr("Sound Button"), "sound_button")
        self._internal_nav_direction_combo = QComboBox(self)
        self._internal_nav_direction_combo.addItem(tr("Next"), "next")
        self._internal_nav_direction_combo.addItem(tr("Previous"), "prev")
        self._internal_target_input_mode_combo = QComboBox(self)
        self._internal_target_input_mode_combo.addItem(tr("List"), "list")
        self._internal_target_input_mode_combo.addItem(tr("Text Box"), "text")
        self._internal_target_kind_combo = QComboBox(self)
        self._internal_target_kind_combo.addItem(tr("Button"), "button")
        self._internal_target_kind_combo.addItem(tr("Page"), "page")
        self._internal_target_edit = QLineEdit(self)
        self._internal_target_edit.setPlaceholderText("A-1-1")
        self._internal_target_group_combo = QComboBox(self)
        for group in _TARGET_GROUPS:
            self._internal_target_group_combo.addItem(group, group)
        self._internal_target_page_combo = QComboBox(self)
        for page_number in range(1, _TARGET_PAGE_COUNT + 1):
            self._internal_target_page_combo.addItem(str(page_number), page_number)
        self._internal_target_slot_combo = QComboBox(self)
        for slot_number in range(1, _TARGET_SLOTS_PER_PAGE + 1):
            self._internal_target_slot_combo.addItem(str(slot_number), slot_number)
        self._internal_volume_spin = QSpinBox(self)
        self._internal_volume_spin.setRange(0, 100)
        self._internal_volume_spin.setSuffix("%")
        self._internal_seek_mode_combo = QComboBox(self)
        self._internal_seek_mode_combo.addItem(tr("Percent"), "percent")
        self._internal_seek_mode_combo.addItem(tr("Time"), "time")
        self._internal_seek_percent_spin = QDoubleSpinBox(self)
        self._internal_seek_percent_spin.setRange(0.0, 100.0)
        self._internal_seek_percent_spin.setDecimals(1)
        self._internal_seek_percent_spin.setSuffix("%")
        self._internal_seek_time_edit = QLineEdit(self)
        self._internal_alert_mode_combo = QComboBox(self)
        self._internal_alert_mode_combo.addItem(tr("Show Alert"), "show")
        self._internal_alert_mode_combo.addItem(tr("Clear Alert"), "clear")
        self._internal_alert_text_edit = QPlainTextEdit(self)
        self._internal_alert_text_edit.setMaximumHeight(84)
        self._internal_alert_keep_checkbox = QCheckBox(tr("Keep on screen until cleared"), self)
        self._internal_alert_keep_checkbox.setChecked(True)
        self._internal_alert_seconds_spin = QSpinBox(self)
        self._internal_alert_seconds_spin.setRange(1, 600)
        self._internal_alert_seconds_spin.setValue(10)
        self._internal_form.addRow(tr("Mode"), self._internal_mode_combo)
        self._internal_form.addRow(tr("Toggle Mode"), self._internal_toggle_mode_combo)
        self._internal_form.addRow(tr("Fade Type"), self._internal_fade_kind_combo)
        self._internal_form.addRow(tr("Scope"), self._internal_reset_scope_combo)
        self._internal_form.addRow(tr("Target"), self._internal_nav_target_combo)
        self._internal_form.addRow(tr("Direction"), self._internal_nav_direction_combo)
        self._internal_form.addRow(tr("Target Input"), self._internal_target_input_mode_combo)
        self._internal_form.addRow(tr("Target Type"), self._internal_target_kind_combo)
        self._internal_form.addRow(tr("Button / Page"), self._internal_target_edit)
        self._internal_form.addRow(tr("Group"), self._internal_target_group_combo)
        self._internal_form.addRow(tr("Page"), self._internal_target_page_combo)
        self._internal_form.addRow(tr("Button"), self._internal_target_slot_combo)
        self._internal_form.addRow(tr("Volume"), self._internal_volume_spin)
        self._internal_form.addRow(tr("Seek Mode"), self._internal_seek_mode_combo)
        self._internal_form.addRow(tr("Seek Percent"), self._internal_seek_percent_spin)
        self._internal_form.addRow(tr("Seek Time"), self._internal_seek_time_edit)
        self._internal_form.addRow(tr("Alert Action"), self._internal_alert_mode_combo)
        self._internal_form.addRow(tr("Alert Text"), self._internal_alert_text_edit)
        self._internal_form.addRow("", self._internal_alert_keep_checkbox)
        self._internal_form.addRow(tr("Seconds"), self._internal_alert_seconds_spin)
        internal_form_panel_layout.addStretch(1)
        internal_tab_layout.addWidget(internal_form_panel, 1)
        self._command_source_tabs.addTab(internal_tab, tr("Internal"))
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
        self._show_lyric_checkbox.toggled.connect(self._on_show_lyric_toggled)
        self._timeline_tree.itemClicked.connect(self._on_tree_clicked)
        self._timeline_tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self._add_current_btn.clicked.connect(self._add_cue_at_current)
        self._add_selected_lyric_btn.clicked.connect(self._add_cue_at_selected_lyric)
        self._delete_btn.clicked.connect(self._delete_selected_cue)
        self._cue_timestamp_edit.editingFinished.connect(self._on_cue_timestamp_edited)
        self._cue_shift_back_btn.clicked.connect(lambda _=False: self._shift_selected_cue_time(-500))
        self._cue_shift_forward_btn.clicked.connect(lambda _=False: self._shift_selected_cue_time(500))
        self._cue_comment_edit.textChanged.connect(self._on_cue_comment_changed)
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
        self._command_source_tabs.currentChanged.connect(self._sync_selected_command)
        self._internal_command_list.currentRowChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_toggle_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_fade_kind_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_reset_scope_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_nav_target_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_nav_direction_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_target_input_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_target_kind_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_target_edit.textChanged.connect(self._sync_selected_command)
        self._internal_target_group_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_target_page_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_target_slot_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_volume_spin.valueChanged.connect(lambda _value: self._sync_selected_command())
        self._internal_seek_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_seek_percent_spin.valueChanged.connect(lambda _value: self._sync_selected_command())
        self._internal_seek_time_edit.textChanged.connect(self._sync_selected_command)
        self._internal_alert_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self._internal_alert_text_edit.textChanged.connect(self._sync_selected_command)
        self._internal_alert_keep_checkbox.toggled.connect(self._sync_selected_command)
        self._internal_alert_seconds_spin.valueChanged.connect(lambda _value: self._sync_selected_command())

        self._apply_command_filters()
        self._populate_internal_command_list()
        if self._command_table.rowCount() > 0:
            self._pick_from_list_radio.setChecked(True)
        else:
            self._manual_location_radio.setChecked(True)
        self._command_source_tabs.setCurrentIndex(0)
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
        self._cue_indicator.set_loading(self._is_loading_media, tr("Loading audio waveform..."))
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
        self._cue_indicator.set_loading(True, tr("Loading audio waveform") + ("." * dot_count))
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
        self._play_btn.setText(tr("Pause") if self._player.state() == ExternalMediaPlayer.PlayingState else tr("Play"))

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
        self._total_label.setText(f"{tr('Total')} {self._format_clock_time(total)}")
        self._elapsed_label.setText(f"{tr('Elapsed')} {self._format_clock_time(position_value)}")
        self._remaining_label.setText(f"{tr('Remaining')} {self._format_clock_time(remaining)}")

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

    def _selected_tree_item(self) -> Optional[QTreeWidgetItem]:
        item = self._timeline_tree.currentItem()
        return item if isinstance(item, QTreeWidgetItem) else None

    def _on_show_lyric_toggled(self, checked: bool) -> None:
        if callable(self._on_show_lyric_changed):
            try:
                self._on_show_lyric_changed(bool(checked))
            except Exception:
                pass
        self._rebuild_table()

    def _selected_row_data(self) -> Optional[dict]:
        item = self._selected_tree_item()
        if item is None:
            return None
        data = item.data(0, Qt.UserRole)
        return data if isinstance(data, dict) else None

    def _selected_cue(self) -> Optional[AutomationScriptCue]:
        selected = self._selected_row_data()
        if not selected:
            return None
        cue = selected.get("cue")
        return cue if isinstance(cue, AutomationScriptCue) else None

    def _selected_command_index_in_cue(self) -> int:
        selected = self._selected_row_data()
        if not selected or selected.get("kind") != "command":
            return -1
        try:
            return max(-1, int(selected.get("action_index", -1)))
        except Exception:
            return -1

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

    def _rebuild_table(self, selected_time_ms: Optional[int] = None, selected_command_index: int = -1) -> None:
        selected = self._selected_row_data()
        if selected_time_ms is None and selected is not None:
            try:
                selected_time_ms = int(selected.get("time_ms", -1))
            except Exception:
                selected_time_ms = None
        if selected_command_index < 0 and selected and selected.get("kind") == "command":
            selected_command_index = self._selected_command_index_in_cue()
        expanded_times: set[int] = set()
        for index in range(self._timeline_tree.topLevelItemCount()):
            item = self._timeline_tree.topLevelItem(index)
            if item is None or not item.isExpanded():
                continue
            data = item.data(0, Qt.UserRole)
            if isinstance(data, dict) and data.get("kind") == "cue":
                try:
                    expanded_times.add(int(data.get("time_ms", -1)))
                except Exception:
                    pass
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
        self._timeline_tree.blockSignals(True)
        self._timeline_tree.clear()
        selected_item: Optional[QTreeWidgetItem] = None
        for row in self._display_rows:
            cue = row.get("cue")
            if cue is not None:
                comment = str(getattr(cue, "comment", "") or "")
                commands = automation_script_cue_command_summary(cue)
                item = QTreeWidgetItem(
                    [
                        self._format_timestamp(int(row["time_ms"])),
                        tr("Cue"),
                        comment,
                        commands,
                    ]
                )
                item.setData(0, Qt.UserRole, dict(row))
                self._tint_tree_item(item, QColor("#F2F8FF"))
                for action_index, action in enumerate(list(cue.actions or [])):
                    spec = normalize_automation_spec(getattr(action, "payload", None) or {})
                    child = QTreeWidgetItem(
                        [
                            "",
                            tr("Command"),
                            automation_script_command_display_name(spec),
                            tr("Press / Release") if bool(spec.hold_to_release) else tr("Normal"),
                        ]
                    )
                    child.setData(
                        0,
                        Qt.UserRole,
                        {
                            "kind": "command",
                            "time_ms": int(cue.time_ms),
                            "cue": cue,
                            "action_index": action_index,
                        },
                    )
                    self._tint_tree_item(child, QColor("#FFF8EB"))
                    item.addChild(child)
                    if (
                        selected_time_ms is not None
                        and int(cue.time_ms) == int(selected_time_ms)
                        and int(selected_command_index) == action_index
                    ):
                        selected_item = child
                if selected_time_ms is not None and int(cue.time_ms) == int(selected_time_ms) and selected_item is None:
                    selected_item = item
                if int(cue.time_ms) in expanded_times or selected_item is not None and selected_item.parent() is item:
                    item.setExpanded(True)
            else:
                item = QTreeWidgetItem(
                    [
                        self._format_timestamp(int(row["time_ms"])),
                        tr("Lyric"),
                        str(row.get("lyric", "") or ""),
                        tr("Reference"),
                    ]
                )
                item.setData(0, Qt.UserRole, dict(row))
                self._tint_tree_item(item, QColor("#F2FBF2"))
                if selected_item is None and selected_time_ms is not None and int(row["time_ms"]) == int(selected_time_ms):
                    selected_item = item
            self._timeline_tree.addTopLevelItem(item)
        self._timeline_tree.blockSignals(False)
        if selected_item is not None:
            self._timeline_tree.setCurrentItem(selected_item)
        self._highlight_row_for_position(max(0, int(self._slider.value())))
        self._refresh_cue_editor()
        self._refresh_action_buttons()

    def _tint_tree_item(self, item: QTreeWidgetItem, color: QColor) -> None:
        for column in range(item.columnCount()):
            item.setBackground(column, color)

    def _set_active_row(self, row: int) -> None:
        previous = self._active_row
        self._active_row = row if 0 <= row < self._timeline_tree.topLevelItemCount() else -1
        for row_index in {previous, self._active_row}:
            if row_index < 0:
                continue
            item = self._timeline_tree.topLevelItem(row_index)
            if item is None:
                continue
            kind = ""
            data = item.data(0, Qt.UserRole)
            if isinstance(data, dict):
                kind = str(data.get("kind", "") or "")
            if row_index == self._active_row:
                self._tint_tree_item(item, QColor(Qt.yellow))
            elif kind == "cue":
                self._tint_tree_item(item, QColor("#F2F8FF"))
            else:
                self._tint_tree_item(item, QColor("#F2FBF2"))

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

    def _on_tree_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, Qt.UserRole)
        if not isinstance(data, dict):
            return
        target_ms = max(0, int(data.get("time_ms", 0)))
        self._player.setPosition(target_ms)

    def _on_tree_selection_changed(self) -> None:
        self._refresh_cue_editor()
        self._refresh_action_buttons()

    def _refresh_cue_editor(self) -> None:
        cue = self._selected_cue()
        self._updating_cue_form = True
        try:
            enabled = cue is not None
            self._cue_timestamp_edit.setEnabled(enabled)
            self._cue_timestamp_edit.setText("" if cue is None else self._format_timestamp(int(cue.time_ms)))
            self._cue_shift_back_btn.setEnabled(enabled)
            self._cue_shift_forward_btn.setEnabled(enabled)
            self._cue_comment_edit.setEnabled(enabled)
            self._cue_comment_edit.setText("" if cue is None else str(cue.comment or ""))
            self._cue_hint_label.setText(
                tr("Select a cue row to edit it. Cues without commands are not saved.")
                if cue is None
                else tr("This cue is edited inline. Expand its row above to inspect the command stack.")
            )
        finally:
            self._updating_cue_form = False
        self._refresh_action_buttons()

    def _refresh_action_buttons(self) -> None:
        selected = self._selected_row_data()
        cue = self._selected_cue()
        selected_is_lyric = bool(selected and selected.get("kind") == "lyric")
        selected_command_row = self._selected_command_index_in_cue()
        cue_command_count = 0 if cue is None else len(list(cue.actions or []))
        can_add_command = cue is not None and automation_spec_is_valid(self._build_selected_command_spec())
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
        self._refresh_selected_cue_row()

    def _on_cue_timestamp_edited(self) -> None:
        if self._updating_cue_form:
            return
        cue = self._selected_cue()
        if cue is None:
            return
        parsed = self._parse_timestamp(self._cue_timestamp_edit.text())
        if parsed is None:
            self._refresh_cue_editor()
            return
        self._move_cue_to_time(cue, parsed)

    def _shift_selected_cue_time(self, delta_ms: int) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        self._move_cue_to_time(cue, max(0, int(cue.time_ms) + int(delta_ms)))

    def _move_cue_to_time(self, cue: AutomationScriptCue, target_ms: int) -> None:
        target_ms = max(0, int(target_ms))
        source_ms = int(cue.time_ms)
        if target_ms == source_ms:
            self._refresh_cue_editor()
            return
        destination = self._cue_for_time(target_ms)
        if destination is not None and destination is not cue:
            destination.actions = list(destination.actions or []) + list(cue.actions or [])
            if not str(destination.comment or "").strip():
                destination.comment = str(cue.comment or "").strip()
            self._script.cues = [
                existing for existing in list(self._script.cues or []) if existing is not cue
            ]
            self._rebuild_table(selected_time_ms=target_ms)
            return
        cue.time_ms = target_ms
        self._script.cues = sorted(list(self._script.cues or []), key=lambda item: int(item.time_ms))
        self._rebuild_table(selected_time_ms=target_ms)

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
        previous_location = self._selected_command_location_from_table()
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

    def _populate_internal_command_list(self) -> None:
        self._internal_command_list.clear()
        for entry in list_internal_automation_commands():
            item = QListWidgetItem(f"{entry.get('category', '')}: {entry.get('label', '')}")
            item.setData(Qt.UserRole, str(entry.get("id", "") or "").strip())
            self._internal_command_list.addItem(item)
        if self._internal_command_list.count() > 0 and self._internal_command_list.currentRow() < 0:
            self._internal_command_list.setCurrentRow(0)

    def _selected_internal_command_id(self) -> str:
        item = self._internal_command_list.currentItem()
        if item is None:
            return ""
        return str(item.data(Qt.UserRole) or "").strip().lower()

    def _selected_internal_params(self, command_id: str) -> dict:
        params: dict[str, object] = {}
        if command_id == "lyric_display":
            params["mode"] = self._internal_mode_combo.currentData()
        elif command_id in {"vocal_removed", "talk", "playlist", "playlist_shuffle", "multiplay"}:
            params["mode"] = self._internal_toggle_mode_combo.currentData()
        elif command_id == "fade":
            params["kind"] = self._internal_fade_kind_combo.currentData()
            params["mode"] = self._internal_toggle_mode_combo.currentData()
        elif command_id == "resetpage":
            params["scope"] = self._internal_reset_scope_combo.currentData()
        elif command_id == "navigate":
            params["target"] = self._internal_nav_target_combo.currentData()
            params["direction"] = self._internal_nav_direction_combo.currentData()
        elif command_id == "play":
            params["button_id"] = self._selected_internal_target_value(command_id)
        elif command_id == "goto":
            params["target"] = self._selected_internal_target_value(command_id)
        elif command_id == "volume_set":
            params["level"] = int(self._internal_volume_spin.value())
        elif command_id == "seek":
            params["seek_mode"] = self._internal_seek_mode_combo.currentData()
            if params["seek_mode"] == "time":
                params["time"] = self._internal_seek_time_edit.text().strip()
            else:
                params["percent"] = float(self._internal_seek_percent_spin.value())
        elif command_id == "alert":
            params["alert_mode"] = self._internal_alert_mode_combo.currentData()
            params["text"] = self._internal_alert_text_edit.toPlainText().strip()
            params["keep"] = bool(self._internal_alert_keep_checkbox.isChecked())
            params["seconds"] = int(self._internal_alert_seconds_spin.value())
        return normalize_internal_automation_params(command_id, params)

    def _refresh_internal_form_visibility(self) -> None:
        command_id = self._selected_internal_command_id()
        is_internal = self._command_source_tabs.currentIndex() == 1
        widgets = [
            self._internal_mode_combo,
            self._internal_toggle_mode_combo,
            self._internal_fade_kind_combo,
            self._internal_reset_scope_combo,
            self._internal_nav_target_combo,
            self._internal_nav_direction_combo,
            self._internal_target_input_mode_combo,
            self._internal_target_kind_combo,
            self._internal_target_edit,
            self._internal_target_group_combo,
            self._internal_target_page_combo,
            self._internal_target_slot_combo,
            self._internal_volume_spin,
            self._internal_seek_mode_combo,
            self._internal_seek_percent_spin,
            self._internal_seek_time_edit,
            self._internal_alert_mode_combo,
            self._internal_alert_text_edit,
            self._internal_alert_keep_checkbox,
            self._internal_alert_seconds_spin,
        ]
        for widget in widgets:
            label = self._internal_form.labelForField(widget)
            if label is not None:
                label.setVisible(False)
            widget.setVisible(False)
        if not is_internal:
            return
        def _show(widget):
            label = self._internal_form.labelForField(widget)
            if label is not None:
                label.setVisible(True)
            widget.setVisible(True)
        if command_id == "lyric_display":
            _show(self._internal_mode_combo)
        elif command_id in {"vocal_removed", "talk", "playlist", "playlist_shuffle", "multiplay"}:
            _show(self._internal_toggle_mode_combo)
        elif command_id == "fade":
            _show(self._internal_fade_kind_combo)
            _show(self._internal_toggle_mode_combo)
        elif command_id == "resetpage":
            _show(self._internal_reset_scope_combo)
        elif command_id == "navigate":
            _show(self._internal_nav_target_combo)
            _show(self._internal_nav_direction_combo)
        elif command_id in {"play", "goto"}:
            _show(self._internal_target_input_mode_combo)
            if self._internal_target_input_mode_combo.currentData() == "text":
                _show(self._internal_target_edit)
            else:
                if command_id == "goto":
                    _show(self._internal_target_kind_combo)
                _show(self._internal_target_group_combo)
                _show(self._internal_target_page_combo)
                if command_id == "play" or self._internal_target_kind_combo.currentData() == "button":
                    _show(self._internal_target_slot_combo)
        elif command_id == "volume_set":
            _show(self._internal_volume_spin)
        elif command_id == "seek":
            _show(self._internal_seek_mode_combo)
            if self._internal_seek_mode_combo.currentData() == "time":
                _show(self._internal_seek_time_edit)
            else:
                _show(self._internal_seek_percent_spin)
        elif command_id == "alert":
            _show(self._internal_alert_mode_combo)
            if self._internal_alert_mode_combo.currentData() == "show":
                _show(self._internal_alert_text_edit)
                _show(self._internal_alert_keep_checkbox)
                if not self._internal_alert_keep_checkbox.isChecked():
                    _show(self._internal_alert_seconds_spin)

    def _build_selected_command_spec(self) -> AutomationCommandSpec:
        if self._command_source_tabs.currentIndex() == 1:
            command_id = self._selected_internal_command_id()
            return normalize_automation_spec(
                {
                    "source": AUTOMATION_COMMAND_SOURCE_INTERNAL,
                    "internal_command": command_id,
                    "internal_params": self._selected_internal_params(command_id),
                }
            )
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
                "source": AUTOMATION_COMMAND_SOURCE_COMPANION,
                "location": location,
                "button_text": button_text,
                "hold_to_release": bool(self._hold_to_release_checkbox.isChecked()),
            }
        )

    def _sync_selected_command(self) -> None:
        spec = self._build_selected_command_spec()
        self._refresh_internal_form_visibility()
        self._selected_command_label.setText(automation_display_name(spec) or "-")
        if spec.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
            self._internal_summary_label.setText(automation_display_name(spec) or "-")
            self._command_text_label.setText(automation_spec_detail_text(spec))
        elif spec.button_text:
            self._command_text_label.setText(spec.button_text)
        elif self._manual_location_radio.isChecked():
            self._command_text_label.setText(tr("Manual location entry"))
        else:
            self._command_text_label.setText("")
        self._refresh_action_buttons()

    def _on_location_mode_changed(self) -> None:
        use_picker = self._pick_from_list_radio.isChecked() and self._command_source_tabs.currentIndex() == 0
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

    def _selected_internal_target_value(self, command_id: str) -> str:
        if self._internal_target_input_mode_combo.currentData() == "text":
            return self._internal_target_edit.text().strip()
        group = str(self._internal_target_group_combo.currentData() or "A").strip().upper()
        page = int(self._internal_target_page_combo.currentData() or 1)
        slot = int(self._internal_target_slot_combo.currentData() or 1)
        if command_id == "goto" and self._internal_target_kind_combo.currentData() == "page":
            return f"{group}-{page}"
        return f"{group}-{page}-{slot}"

    def _apply_internal_target_value(self, command_id: str, value: str) -> None:
        text = str(value or "").strip()
        self._internal_target_edit.setText(text)
        parsed = self._parse_internal_target_value(command_id, text)
        if parsed is None:
            self._internal_target_input_mode_combo.setCurrentIndex(
                max(0, self._internal_target_input_mode_combo.findData("text"))
            )
            return
        group, page, slot, target_kind = parsed
        self._internal_target_input_mode_combo.setCurrentIndex(
            max(0, self._internal_target_input_mode_combo.findData("list"))
        )
        self._internal_target_kind_combo.setCurrentIndex(
            max(0, self._internal_target_kind_combo.findData(target_kind))
        )
        self._internal_target_group_combo.setCurrentIndex(
            max(0, self._internal_target_group_combo.findData(group))
        )
        self._internal_target_page_combo.setCurrentIndex(
            max(0, self._internal_target_page_combo.findData(page))
        )
        if slot is not None:
            self._internal_target_slot_combo.setCurrentIndex(
                max(0, self._internal_target_slot_combo.findData(slot))
            )

    @staticmethod
    def _parse_internal_target_value(command_id: str, value: str) -> Optional[tuple[str, int, Optional[int], str]]:
        parts = [part.strip() for part in str(value or "").strip().upper().split("-") if part.strip()]
        if command_id == "play":
            if len(parts) != 3:
                return None
            group, page_text, slot_text = parts
            if group not in _TARGET_GROUPS or not page_text.isdigit() or not slot_text.isdigit():
                return None
            return group, int(page_text), int(slot_text), "button"
        if command_id == "goto":
            if len(parts) == 2:
                group, page_text = parts
                if group not in _TARGET_GROUPS or not page_text.isdigit():
                    return None
                return group, int(page_text), None, "page"
            if len(parts) == 3:
                group, page_text, slot_text = parts
                if group not in _TARGET_GROUPS or not page_text.isdigit() or not slot_text.isdigit():
                    return None
                return group, int(page_text), int(slot_text), "button"
        return None

    def _add_selected_command_to_current_cue(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        spec = self._build_selected_command_spec()
        if not automation_spec_is_valid(spec):
            return
        action = AutomationScriptAction(
            type=(
                AUTOMATION_SCRIPT_ACTION_TYPE_INTERNAL_COMMAND
                if spec.source == AUTOMATION_COMMAND_SOURCE_INTERNAL
                else AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND
            ),
            payload=normalize_automation_spec(spec),
        )
        cue.actions = list(cue.actions or []) + [action]
        if not str(cue.comment or "").strip():
            if spec.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
                cue.comment = str(automation_script_command_display_name(spec) or "").strip()
            else:
                cue.comment = str(spec.button_text or spec.location or "").strip()
        self._rebuild_table(selected_time_ms=int(cue.time_ms), selected_command_index=len(list(cue.actions or [])) - 1)

    def _remove_selected_command(self) -> None:
        cue = self._selected_cue()
        row = self._selected_command_index_in_cue()
        if cue is None or row < 0:
            return
        actions = list(cue.actions or [])
        if row >= len(actions):
            return
        actions.pop(row)
        cue.actions = actions
        self._rebuild_table(selected_time_ms=int(cue.time_ms), selected_command_index=min(row, len(actions) - 1))

    def _move_selected_command(self, delta: int) -> None:
        cue = self._selected_cue()
        row = self._selected_command_index_in_cue()
        if cue is None or row < 0:
            return
        actions = list(cue.actions or [])
        new_index = row + int(delta)
        if row >= len(actions) or new_index < 0 or new_index >= len(actions):
            return
        actions[row], actions[new_index] = actions[new_index], actions[row]
        cue.actions = actions
        self._rebuild_table(selected_time_ms=int(cue.time_ms), selected_command_index=new_index)

    def _refresh_selected_cue_row(self) -> None:
        cue = self._selected_cue()
        if cue is None:
            return
        for index in range(self._timeline_tree.topLevelItemCount()):
            item = self._timeline_tree.topLevelItem(index)
            if item is None:
                continue
            data = item.data(0, Qt.UserRole)
            if not isinstance(data, dict) or data.get("kind") != "cue":
                continue
            if int(data.get("time_ms", -1)) != int(cue.time_ms):
                continue
            item.setText(2, str(cue.comment or ""))
            item.setText(3, automation_script_cue_command_summary(cue))
            break
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

    @staticmethod
    def _parse_timestamp(value: str) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        normalized = text.replace(".", ",")
        parts = normalized.split(",")
        if len(parts) != 2:
            return None
        time_part, millis_part = parts
        millis_part = millis_part.strip()
        clock_parts = [part.strip() for part in time_part.strip().split(":")]
        if len(clock_parts) != 3:
            return None
        if not millis_part.isdigit() or len(millis_part) != 3:
            return None
        if not all(part.isdigit() for part in clock_parts):
            return None
        hours, minutes, seconds = [int(part) for part in clock_parts]
        if minutes > 59 or seconds > 59:
            return None
        return (((hours * 60 + minutes) * 60 + seconds) * 1000) + int(millis_part)
