from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass
from typing import Callable, Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCloseEvent, QFocusEvent, QShowEvent
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import ExternalMediaPlayer, is_audio_preloaded, request_audio_preload
from pyssp.audio_beat_map import AudioBeatMap, analyze_audio_beat_map, normalize_audio_beat_map
from pyssp.audio_format_support import build_audio_file_dialog_filter
from pyssp.automation_command import (
    SOUND_BUTTON_AUTOMATION_EVENTS,
    SoundButtonAutomationConfig,
    normalize_sound_button_automation_config,
    sound_button_automation_event_label,
)
from pyssp.automation_script import AUTOMATION_SCRIPT_EXTENSION
from pyssp.automation_script import load_automation_script, save_automation_script, AutomationScript, automation_script_to_dict
from pyssp.companion_available_commands import load_companion_available_commands
from pyssp.display_focus import DISPLAY_FOCUS_LABELS, normalize_display_focus
from pyssp.i18n import localize_widget_tree, tr
from pyssp.midi_control import (
    midi_binding_to_display,
    midi_input_name_selector,
    normalize_midi_binding,
    split_midi_binding,
)
from pyssp.set_loader import normalize_slot_timecode_timeline_mode
from pyssp.ui.automation_script_editor_dialog import AutomationScriptEditorDialog
from pyssp.ui.cue_point_dialog import CuePointDialog, format_timecode, parse_timecode_to_ms
from pyssp.ui.edit_sound_button_dialog import SoundHotkeyEdit
from pyssp.ui.lyric_editor_dialog import LyricEditorDialog
from pyssp.ui.sound_button_automation_dialog import SoundButtonAutomationDialog
from pyssp.ui.timecode_setup_dialog import TimecodeOffsetEdit
from pyssp.ui.waveform_view import CueRangeIndicator, WaveformRefreshController


@dataclass
class SoundButtonEditorState:
    file_path: str = ""
    caption: str = ""
    notes: str = ""
    disable_video_loading: bool = False
    lyric_file: str = ""
    automation_script_path: str = ""
    automation_script_bypassed: bool = False
    vocal_removed_file: str = ""
    volume_override_pct: Optional[int] = None
    sound_hotkey: str = ""
    sound_midi_hotkey: str = ""
    display_focus: str = ""
    display_image_path: str = ""
    audio_beat_map: Optional[AudioBeatMap] = None
    cue_start_ms: Optional[int] = None
    cue_end_ms: Optional[int] = None
    timecode_offset_ms: Optional[int] = None
    timecode_timeline_mode: str = "global"
    sound_button_automation: Optional[SoundButtonAutomationConfig] = None


class SoundButtonEditorWindow(QDialog):
    def __init__(
        self,
        *,
        host,
        slot_key: tuple[str, int, int],
        slot_title: str,
        state: SoundButtonEditorState,
        available_midi_input_devices: Optional[list[tuple[str, str]]] = None,
        selected_midi_input_device_ids: Optional[list[str]] = None,
        start_dir: str = "",
        language: str = "en",
        on_save: Optional[Callable[[SoundButtonEditorState], Optional[SoundButtonEditorState]]] = None,
        on_closed: Optional[Callable[[tuple[str, int, int]], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setModal(False)
        self.resize(920, 700)
        self._host = host
        self._slot_key = slot_key
        self._slot_title = str(slot_title or "").strip()
        self._start_dir = str(start_dir or "").strip()
        self._language = str(language or "en")
        self._on_save = on_save
        self._on_closed = on_closed
        self._state = SoundButtonEditorState()
        self._dirty = False
        self._loading_state = False
        self._duration_ms = 0
        self._is_scrubbing = False
        self._is_loading_media = False
        self._load_wait_started = 0.0
        self._load_wait_timeout_sec = 120.0
        self._media_load_request_id = 0
        self._waveform_refresh: Optional[WaveformRefreshController] = None

        self._midi_binding = ""
        self._midi_learning = False
        selected_ids = [str(v).strip() for v in (selected_midi_input_device_ids or []) if str(v).strip()]
        available_by_id = {
            str(device_id).strip(): str(device_name).strip()
            for device_id, device_name in (available_midi_input_devices or [])
        }
        allowed: set[str] = set()
        for value in selected_ids:
            if value.startswith("name::"):
                allowed.add(value)
            elif value in available_by_id:
                allowed.add(midi_input_name_selector(available_by_id[value]))
        self._allowed_midi_selectors = allowed

        root = QVBoxLayout(self)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        root.addWidget(self.summary_label)

        self._build_shared_player(root)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        self._build_general_tab()
        self._build_cue_tab()
        self._build_timecode_tab()
        self._build_lyric_tab()
        self._build_button_automation_tab()
        self._build_automation_script_tab()

        button_row = QHBoxLayout()
        self.save_button = QPushButton(tr("Save"))
        self.close_button = QPushButton(tr("Close"))
        button_row.addStretch(1)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.close_button)
        root.addLayout(button_row)

        self.save_button.clicked.connect(self._save)
        self.close_button.clicked.connect(self.close)

        self._load_state(state)
        localize_widget_tree(self, self._language)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._dirty:
            answer = QMessageBox.question(
                self,
                tr("Edit Sound Button"),
                tr("You have unsaved changes. Close this editor?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        try:
            self._player.stop()
        except Exception:
            pass
        if self._load_poll_timer.isActive():
            self._load_poll_timer.stop()
        if self._waveform_refresh is not None:
            self._waveform_refresh.stop()
        if callable(self._on_closed):
            self._on_closed(self._slot_key)
        super().closeEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        if hasattr(self._host, "_midi_context_handler"):
            self._host._midi_context_handler = self
        super().focusInEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        if hasattr(self._host, "_midi_context_handler"):
            self._host._midi_context_handler = self
        super().showEvent(event)

    def handle_midi_message(
        self,
        token: str,
        source_selector: str = "",
        status: int = 0,
        data1: int = 0,
        data2: int = 0,
    ) -> bool:
        if not self._midi_learning:
            return False
        if self._allowed_midi_selectors:
            if not source_selector or source_selector not in self._allowed_midi_selectors:
                return False
        _status = status
        _data1 = data1
        _data2 = data2
        self._on_midi_binding(token, source_selector)
        return True

    def values(self) -> SoundButtonEditorState:
        volume_override_pct: Optional[int] = None
        if self.custom_volume_checkbox.isChecked():
            volume_override_pct = max(0, min(100, int(self.volume_slider.value())))
        cue_start_ms = parse_timecode_to_ms(self.cue_start_edit.text().strip())
        cue_end_ms = parse_timecode_to_ms(self.cue_end_edit.text().strip())
        if cue_start_ms is None and self.cue_start_edit.text().strip():
            cue_start_ms = -1
        if cue_end_ms is None and self.cue_end_edit.text().strip():
            cue_end_ms = -1
        timecode_offset_ms = self.timecode_offset_edit.offset_ms()
        if timecode_offset_ms is not None and int(timecode_offset_ms) <= 0:
            timecode_offset_ms = None
        timecode_timeline_mode = "global"
        if self.timecode_timeline_audio_file_radio.isChecked():
            timecode_timeline_mode = "audio_file"
        elif self.timecode_timeline_cue_region_radio.isChecked():
            timecode_timeline_mode = "cue_region"
        return SoundButtonEditorState(
            file_path=self.file_edit.text().strip(),
            caption=self.caption_edit.text().strip(),
            notes=self.notes_edit.text().strip(),
            disable_video_loading=bool(self.disable_video_loading_checkbox.isChecked()),
            lyric_file=self.lyric_file_edit.text().strip(),
            automation_script_path=self.automation_script_edit.text().strip(),
            automation_script_bypassed=bool(self.automation_script_bypass_checkbox.isChecked()),
            vocal_removed_file=self.vocal_removed_file_edit.text().strip(),
            volume_override_pct=volume_override_pct,
            sound_hotkey=self.sound_hotkey_edit.hotkey(),
            sound_midi_hotkey=self._midi_binding,
            display_focus=normalize_display_focus(str(self.display_focus_combo.currentData() or ""), default="none"),
            display_image_path=self.display_image_edit.text().strip(),
            audio_beat_map=self._audio_beat_map_from_inputs(),
            cue_start_ms=None if cue_start_ms in {None, -1} else cue_start_ms,
            cue_end_ms=None if cue_end_ms in {None, -1} else cue_end_ms,
            timecode_offset_ms=timecode_offset_ms,
            timecode_timeline_mode=normalize_slot_timecode_timeline_mode(timecode_timeline_mode),
            sound_button_automation=normalize_sound_button_automation_config(self._state.sound_button_automation),
        )

    def _build_general_tab(self) -> None:
        page = QWidget(self)
        root = QVBoxLayout(page)
        form = QFormLayout()

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_edit = QLineEdit()
        self.browse_btn = QPushButton(tr("Browse"))
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(self.browse_btn)
        form.addRow(tr("File"), file_row)

        self.disable_video_loading_checkbox = QCheckBox(tr("Do not load video"))
        form.addRow("", self.disable_video_loading_checkbox)

        self.caption_edit = QLineEdit()
        form.addRow(tr("Caption"), self.caption_edit)

        self.notes_edit = QLineEdit()
        form.addRow(tr("Notes"), self.notes_edit)

        self.display_focus_combo = QComboBox()
        for value in [
            "none",
            "video",
            "image",
            "lyric_display",
            "stage_display",
            "backdrop",
            "white_screen",
            "colour_bars",
            "metronome_display",
        ]:
            self.display_focus_combo.addItem(DISPLAY_FOCUS_LABELS.get(value, value), value)
        form.addRow(tr("Display Focus"), self.display_focus_combo)

        display_image_row = QWidget()
        display_image_layout = QHBoxLayout(display_image_row)
        display_image_layout.setContentsMargins(0, 0, 0, 0)
        self.display_image_edit = QLineEdit()
        self.display_image_browse_btn = QPushButton(tr("Browse"))
        self.display_image_clear_btn = QPushButton(tr("Clear"))
        self.display_image_browse_btn.clicked.connect(self._browse_display_image_file)
        self.display_image_clear_btn.clicked.connect(lambda _=False: self.display_image_edit.setText(""))
        display_image_layout.addWidget(self.display_image_edit, 1)
        display_image_layout.addWidget(self.display_image_browse_btn)
        display_image_layout.addWidget(self.display_image_clear_btn)
        form.addRow(tr("Display Image"), display_image_row)

        vocal_row = QWidget()
        vocal_layout = QHBoxLayout(vocal_row)
        vocal_layout.setContentsMargins(0, 0, 0, 0)
        self.vocal_removed_file_edit = QLineEdit()
        self.vocal_removed_browse_btn = QPushButton(tr("Browse"))
        self.vocal_removed_regen_btn = QPushButton(tr("Regenerate"))
        self.vocal_removed_clear_btn = QPushButton(tr("Clear"))
        self.vocal_removed_browse_btn.clicked.connect(self._browse_vocal_removed_file)
        self.vocal_removed_regen_btn.clicked.connect(self._regenerate_vocal_removed)
        self.vocal_removed_clear_btn.clicked.connect(lambda _=False: self.vocal_removed_file_edit.setText(""))
        vocal_layout.addWidget(self.vocal_removed_file_edit, 1)
        vocal_layout.addWidget(self.vocal_removed_browse_btn)
        vocal_layout.addWidget(self.vocal_removed_regen_btn)
        vocal_layout.addWidget(self.vocal_removed_clear_btn)
        form.addRow(tr("Vocal Removed File"), vocal_row)

        hk_row = QWidget()
        hk_layout = QHBoxLayout(hk_row)
        hk_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_hotkey_edit = SoundHotkeyEdit()
        clear_hk_btn = QPushButton(tr("Clear"))
        clear_hk_btn.clicked.connect(lambda _=False: self.sound_hotkey_edit.setHotkey(""))
        hk_layout.addWidget(self.sound_hotkey_edit, 1)
        hk_layout.addWidget(clear_hk_btn)
        form.addRow(tr("Sound Button Hot Key"), hk_row)

        midi_hk_row = QWidget()
        midi_hk_layout = QHBoxLayout(midi_hk_row)
        midi_hk_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_midi_hotkey_edit = QLineEdit()
        self.sound_midi_hotkey_edit.setReadOnly(True)
        learn_midi_btn = QPushButton(tr("Learn"))
        clear_midi_btn = QPushButton(tr("Clear"))
        learn_midi_btn.clicked.connect(self._start_midi_learn)
        clear_midi_btn.clicked.connect(lambda _=False: self._set_midi_binding(""))
        midi_hk_layout.addWidget(self.sound_midi_hotkey_edit, 1)
        midi_hk_layout.addWidget(learn_midi_btn)
        midi_hk_layout.addWidget(clear_midi_btn)
        form.addRow(tr("Sound Button MIDI Hot Key"), midi_hk_row)

        vol_row = QWidget()
        vol_layout = QVBoxLayout(vol_row)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setSpacing(4)
        self.custom_volume_checkbox = QCheckBox(tr("Use custom playback volume"))
        self.volume_label = QLabel("")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        vol_layout.addWidget(self.custom_volume_checkbox)
        vol_layout.addWidget(self.volume_label)
        vol_layout.addWidget(self.volume_slider)
        form.addRow(tr("Playback Volume"), vol_row)

        metronome_group = QGroupBox(tr("Metronome"))
        metronome_form = QFormLayout(metronome_group)
        self.audio_metronome_enabled_checkbox = QCheckBox(tr("Enable metronome timing for this audio"))
        metronome_form.addRow("", self.audio_metronome_enabled_checkbox)
        self.audio_bpm_edit = QLineEdit()
        metronome_form.addRow(tr("Metronome BPM"), self.audio_bpm_edit)
        self.audio_timesig_num_edit = QLineEdit()
        metronome_form.addRow(tr("Beats Per Bar"), self.audio_timesig_num_edit)
        self.audio_timesig_den_combo = QComboBox()
        for value in (2, 4, 8, 16):
            self.audio_timesig_den_combo.addItem(str(value), value)
        metronome_form.addRow(tr("Beat Unit"), self.audio_timesig_den_combo)
        self.audio_downbeat_offset_edit = QLineEdit()
        metronome_form.addRow(tr("First Downbeat ms"), self.audio_downbeat_offset_edit)
        analysis_row = QWidget()
        analysis_layout = QHBoxLayout(analysis_row)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        self.audio_analysis_status_label = QLabel("")
        self.audio_analyze_btn = QPushButton(tr("Analyze BPM"))
        self.audio_clear_analysis_btn = QPushButton(tr("Clear"))
        self.audio_analyze_btn.clicked.connect(self._analyze_bpm)
        self.audio_clear_analysis_btn.clicked.connect(self._clear_audio_analysis)
        analysis_layout.addWidget(self.audio_analysis_status_label, 1)
        analysis_layout.addWidget(self.audio_analyze_btn)
        analysis_layout.addWidget(self.audio_clear_analysis_btn)
        metronome_form.addRow(tr("Analysis"), analysis_row)

        root.addLayout(form)
        root.addWidget(metronome_group)
        root.addStretch(1)
        self.tabs.addTab(page, tr("General"))

        def _sync_volume_label(value: int) -> None:
            self.volume_label.setText(f"{value}%")

        def _sync_slider_enabled(checked: bool) -> None:
            self.volume_slider.setEnabled(checked)
            self.volume_label.setEnabled(checked)

        self.volume_slider.valueChanged.connect(_sync_volume_label)
        self.custom_volume_checkbox.toggled.connect(_sync_slider_enabled)
        self.display_focus_combo.currentIndexChanged.connect(self._sync_display_focus_controls)
        self.audio_metronome_enabled_checkbox.toggled.connect(self._sync_audio_beat_controls)
        self.audio_metronome_enabled_checkbox.toggled.connect(lambda _=False: self._refresh_audio_analysis_status())
        _sync_volume_label(self.volume_slider.value())
        _sync_slider_enabled(False)

        for signal in (
            self.file_edit.textChanged,
            self.caption_edit.textChanged,
            self.notes_edit.textChanged,
            self.disable_video_loading_checkbox.toggled,
            self.display_focus_combo.currentIndexChanged,
            self.display_image_edit.textChanged,
            self.vocal_removed_file_edit.textChanged,
            self.custom_volume_checkbox.toggled,
            self.volume_slider.valueChanged,
            self.audio_metronome_enabled_checkbox.toggled,
            self.audio_bpm_edit.textChanged,
            self.audio_timesig_num_edit.textChanged,
            self.audio_timesig_den_combo.currentIndexChanged,
            self.audio_downbeat_offset_edit.textChanged,
        ):
            signal.connect(self._mark_dirty)
        self.file_edit.editingFinished.connect(self._load_shared_preview_media)

    def _build_cue_tab(self) -> None:
        page = QWidget(self)
        self.cue_tab_page = page
        root = QVBoxLayout(page)
        note = QLabel(tr("Edit quick cue values here, or open the full cue editor for waveform-based editing."))
        note.setWordWrap(True)
        root.addWidget(note)

        form = QFormLayout()
        self.cue_start_edit = QLineEdit()
        self.cue_start_edit.setPlaceholderText("mm:ss:ff")
        self.cue_end_edit = QLineEdit()
        self.cue_end_edit.setPlaceholderText("mm:ss:ff")
        form.addRow(tr("Start Cue"), self.cue_start_edit)
        form.addRow(tr("End Cue"), self.cue_end_edit)
        root.addLayout(form)

        button_row = QHBoxLayout()
        self.cue_clear_button = QPushButton(tr("Clear Cue"))
        self.cue_open_button = QPushButton(tr("Open Cue Editor"))
        button_row.addWidget(self.cue_clear_button)
        button_row.addWidget(self.cue_open_button)
        button_row.addStretch(1)
        root.addLayout(button_row)

        self.cue_status_label = QLabel("")
        self.cue_status_label.setWordWrap(True)
        root.addWidget(self.cue_status_label)
        root.addStretch(1)
        self.tabs.addTab(page, tr("Cue"))

        self.cue_clear_button.clicked.connect(self._clear_cues)
        self.cue_open_button.clicked.connect(self._open_cue_editor)
        self.cue_start_edit.textChanged.connect(self._mark_dirty)
        self.cue_end_edit.textChanged.connect(self._mark_dirty)
        self.cue_start_edit.textChanged.connect(self._refresh_cue_status)
        self.cue_end_edit.textChanged.connect(self._refresh_cue_status)
        self.cue_start_edit.textChanged.connect(self._refresh_shared_cue_indicator)
        self.cue_end_edit.textChanged.connect(self._refresh_shared_cue_indicator)

    def _build_timecode_tab(self) -> None:
        page = QWidget(self)
        self.timecode_tab_page = page
        root = QVBoxLayout(page)
        form = QFormLayout()

        offset_row = QWidget()
        offset_layout = QHBoxLayout(offset_row)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        self.timecode_offset_edit = TimecodeOffsetEdit(None, fps=30.0, parent=self)
        self.timecode_offset_up_btn = QPushButton("▲")
        self.timecode_offset_down_btn = QPushButton("▼")
        self.timecode_clear_btn = QPushButton(tr("Clear"))
        self.timecode_offset_up_btn.clicked.connect(lambda _=False: self._nudge_timecode_offset(1000))
        self.timecode_offset_down_btn.clicked.connect(lambda _=False: self._nudge_timecode_offset(-1000))
        self.timecode_clear_btn.clicked.connect(lambda _=False: self.timecode_offset_edit.set_offset_ms(0))
        offset_layout.addWidget(self.timecode_offset_edit, 1)
        offset_layout.addWidget(self.timecode_offset_up_btn)
        offset_layout.addWidget(self.timecode_offset_down_btn)
        offset_layout.addWidget(self.timecode_clear_btn)
        form.addRow(tr("Offset"), offset_row)

        self.timecode_timeline_global_radio = QRadioButton(tr("Respect global setting"))
        self.timecode_timeline_audio_file_radio = QRadioButton(tr("Relative to actual audio file"))
        self.timecode_timeline_cue_region_radio = QRadioButton(tr("Relative to cue set point"))
        self.timecode_timeline_group = QButtonGroup(self)
        self.timecode_timeline_group.addButton(self.timecode_timeline_global_radio)
        self.timecode_timeline_group.addButton(self.timecode_timeline_audio_file_radio)
        self.timecode_timeline_group.addButton(self.timecode_timeline_cue_region_radio)
        mode_row = QWidget()
        mode_layout = QVBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.addWidget(self.timecode_timeline_global_radio)
        mode_layout.addWidget(self.timecode_timeline_audio_file_radio)
        mode_layout.addWidget(self.timecode_timeline_cue_region_radio)
        form.addRow(tr("Timecode Display Timeline"), mode_row)

        root.addLayout(form)
        self.timecode_status_label = QLabel("")
        self.timecode_status_label.setWordWrap(True)
        root.addWidget(self.timecode_status_label)
        root.addStretch(1)
        self.tabs.addTab(page, tr("Timecode"))

        self.timecode_offset_edit.textChanged.connect(self._mark_dirty)
        self.timecode_offset_edit.textChanged.connect(self._refresh_timecode_status)
        self.timecode_timeline_global_radio.toggled.connect(self._mark_dirty)
        self.timecode_timeline_audio_file_radio.toggled.connect(self._mark_dirty)
        self.timecode_timeline_cue_region_radio.toggled.connect(self._mark_dirty)
        self.timecode_timeline_global_radio.toggled.connect(self._refresh_timecode_status)
        self.timecode_timeline_audio_file_radio.toggled.connect(self._refresh_timecode_status)
        self.timecode_timeline_cue_region_radio.toggled.connect(self._refresh_timecode_status)

    def _build_lyric_tab(self) -> None:
        page = QWidget(self)
        self.lyric_tab_page = page
        root = QVBoxLayout(page)

        note = QLabel(tr("Lyric files stay external. Link, create, or open the file from here without leaving the sound button editor."))
        note.setWordWrap(True)
        root.addWidget(note)

        form = QFormLayout()
        lyric_row = QWidget()
        lyric_layout = QHBoxLayout(lyric_row)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        self.lyric_file_edit = QLineEdit()
        self.lyric_browse_btn = QPushButton(tr("Browse"))
        self.lyric_clear_btn = QPushButton(tr("Clear"))
        self.lyric_browse_btn.clicked.connect(self._browse_lyric_file)
        self.lyric_clear_btn.clicked.connect(lambda _=False: self.lyric_file_edit.setText(""))
        lyric_layout.addWidget(self.lyric_file_edit, 1)
        lyric_layout.addWidget(self.lyric_browse_btn)
        lyric_layout.addWidget(self.lyric_clear_btn)
        form.addRow(tr("Lyric File"), lyric_row)
        root.addLayout(form)

        action_row = QHBoxLayout()
        self.lyric_scan_btn = QPushButton(tr("Scan Match"))
        self.lyric_create_btn = QPushButton(tr("Create"))
        self.lyric_open_btn = QPushButton(tr("Open Lyric Editor"))
        action_row.addWidget(self.lyric_scan_btn)
        action_row.addWidget(self.lyric_create_btn)
        action_row.addWidget(self.lyric_open_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        self.lyric_status_label = QLabel("")
        self.lyric_status_label.setWordWrap(True)
        root.addWidget(self.lyric_status_label)
        self.lyric_player_context_label = QLabel("")
        self.lyric_player_context_label.setWordWrap(True)
        root.addWidget(self.lyric_player_context_label)
        lyric_editor_actions = QHBoxLayout()
        self.lyric_reload_btn = QPushButton(tr("Load File"))
        self.lyric_save_btn = QPushButton(tr("Save File"))
        self.lyric_advanced_btn = QPushButton(tr("Open Advanced Lyric Editor"))
        lyric_editor_actions.addWidget(self.lyric_reload_btn)
        lyric_editor_actions.addWidget(self.lyric_save_btn)
        lyric_editor_actions.addWidget(self.lyric_advanced_btn)
        lyric_editor_actions.addStretch(1)
        root.addLayout(lyric_editor_actions)
        self.lyric_text_edit = QPlainTextEdit()
        self.lyric_text_edit.setPlaceholderText(tr("Linked lyric file contents appear here."))
        root.addWidget(self.lyric_text_edit, 1)
        root.addStretch(1)
        self.tabs.addTab(page, tr("Lyric"))

        self.lyric_scan_btn.clicked.connect(self._scan_matching_lyric)
        self.lyric_create_btn.clicked.connect(self._create_lyric_file)
        self.lyric_open_btn.clicked.connect(self._open_lyric_editor)
        self.lyric_reload_btn.clicked.connect(self._load_lyric_text_from_linked_path)
        self.lyric_save_btn.clicked.connect(self._save_lyric_text_to_linked_path)
        self.lyric_advanced_btn.clicked.connect(self._open_lyric_editor)
        self.lyric_file_edit.textChanged.connect(self._mark_dirty)
        self.lyric_file_edit.textChanged.connect(self._refresh_lyric_status)
        self.lyric_text_edit.textChanged.connect(self._mark_dirty)
        self.lyric_file_edit.editingFinished.connect(lambda: self._load_lyric_text_from_linked_path(force=True))

    def _build_button_automation_tab(self) -> None:
        page = QWidget(self)
        self.button_automation_tab_page = page
        root = QVBoxLayout(page)

        button_automation_group = QGroupBox(tr("Sound Button Automation"))
        button_automation_layout = QVBoxLayout(button_automation_group)
        self.button_automation_summary = QLabel("")
        self.button_automation_summary.setWordWrap(True)
        button_automation_layout.addWidget(self.button_automation_summary)
        button_automation_action_row = QHBoxLayout()
        self.button_automation_edit_btn = QPushButton(tr("Edit Sound Button Automation"))
        self.button_automation_clear_btn = QPushButton(tr("Clear"))
        button_automation_action_row.addWidget(self.button_automation_edit_btn)
        button_automation_action_row.addWidget(self.button_automation_clear_btn)
        button_automation_action_row.addStretch(1)
        button_automation_layout.addLayout(button_automation_action_row)
        self.button_automation_player_context_label = QLabel("")
        self.button_automation_player_context_label.setWordWrap(True)
        button_automation_layout.addWidget(self.button_automation_player_context_label)
        root.addWidget(button_automation_group)
        root.addStretch(1)
        self.tabs.addTab(page, tr("Button Automation"))

        self.button_automation_edit_btn.clicked.connect(self._edit_sound_button_automation)
        self.button_automation_clear_btn.clicked.connect(self._clear_sound_button_automation)

    def _build_automation_script_tab(self) -> None:
        page = QWidget(self)
        self.automation_script_tab_page = page
        root = QVBoxLayout(page)

        script_group = QGroupBox(tr("Automation Script"))
        script_layout = QVBoxLayout(script_group)
        script_form = QFormLayout()
        script_row = QWidget()
        path_layout = QHBoxLayout(script_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        self.automation_script_edit = QLineEdit()
        self.automation_script_browse_btn = QPushButton(tr("Browse"))
        self.automation_script_clear_btn = QPushButton(tr("Clear"))
        self.automation_script_browse_btn.clicked.connect(self._browse_automation_script_file)
        self.automation_script_clear_btn.clicked.connect(lambda _=False: self.automation_script_edit.setText(""))
        path_layout.addWidget(self.automation_script_edit, 1)
        path_layout.addWidget(self.automation_script_browse_btn)
        path_layout.addWidget(self.automation_script_clear_btn)
        script_form.addRow(tr("Automation Script"), script_row)
        script_layout.addLayout(script_form)
        self.automation_script_bypass_checkbox = QCheckBox(tr("Bypass linked automation script"))
        script_layout.addWidget(self.automation_script_bypass_checkbox)
        script_action_row = QHBoxLayout()
        self.automation_script_scan_btn = QPushButton(tr("Scan Match"))
        self.automation_script_create_btn = QPushButton(tr("Create"))
        self.automation_script_open_btn = QPushButton(tr("Open Automation Script Editor"))
        script_action_row.addWidget(self.automation_script_scan_btn)
        script_action_row.addWidget(self.automation_script_create_btn)
        script_action_row.addWidget(self.automation_script_open_btn)
        script_action_row.addStretch(1)
        script_layout.addLayout(script_action_row)
        self.automation_status_label = QLabel("")
        self.automation_status_label.setWordWrap(True)
        script_layout.addWidget(self.automation_status_label)
        self.automation_script_player_context_label = QLabel("")
        self.automation_script_player_context_label.setWordWrap(True)
        script_layout.addWidget(self.automation_script_player_context_label)
        script_editor_actions = QHBoxLayout()
        self.automation_script_reload_btn = QPushButton(tr("Load File"))
        self.automation_script_save_btn = QPushButton(tr("Save File"))
        self.automation_script_pretty_btn = QPushButton(tr("Format JSON"))
        self.automation_script_advanced_btn = QPushButton(tr("Open Advanced Automation Editor"))
        script_editor_actions.addWidget(self.automation_script_reload_btn)
        script_editor_actions.addWidget(self.automation_script_save_btn)
        script_editor_actions.addWidget(self.automation_script_pretty_btn)
        script_editor_actions.addWidget(self.automation_script_advanced_btn)
        script_editor_actions.addStretch(1)
        script_layout.addLayout(script_editor_actions)
        self.automation_script_text_edit = QPlainTextEdit()
        self.automation_script_text_edit.setPlaceholderText(tr("Linked automation script JSON appears here."))
        script_layout.addWidget(self.automation_script_text_edit, 1)
        root.addWidget(script_group)
        root.addStretch(1)
        self.tabs.addTab(page, tr("Automation Script"))

        self.automation_script_scan_btn.clicked.connect(self._scan_matching_automation_script)
        self.automation_script_create_btn.clicked.connect(self._create_automation_script_file)
        self.automation_script_open_btn.clicked.connect(self._open_automation_script_editor)
        self.automation_script_reload_btn.clicked.connect(self._load_automation_script_text_from_linked_path)
        self.automation_script_save_btn.clicked.connect(self._save_automation_script_text_to_linked_path)
        self.automation_script_pretty_btn.clicked.connect(self._format_automation_script_json)
        self.automation_script_advanced_btn.clicked.connect(self._open_automation_script_editor)
        self.automation_script_edit.textChanged.connect(self._mark_dirty)
        self.automation_script_bypass_checkbox.toggled.connect(self._mark_dirty)
        self.automation_script_edit.textChanged.connect(self._refresh_automation_status)
        self.automation_script_bypass_checkbox.toggled.connect(self._refresh_automation_status)
        self.automation_script_text_edit.textChanged.connect(self._mark_dirty)
        self.automation_script_edit.editingFinished.connect(
            lambda: self._load_automation_script_text_from_linked_path(force=True)
        )

    def _build_shared_player(self, root: QVBoxLayout) -> None:
        audio_service = getattr(self._host, "_audio_service", None)
        if audio_service is not None:
            self._player = audio_service.create_player(self)
        else:
            self._player = ExternalMediaPlayer(self)
        self._player.setNotifyInterval(40)
        self._player.positionChanged.connect(self._on_player_position_changed)
        self._player.durationChanged.connect(self._on_player_duration_changed)
        self._player.stateChanged.connect(self._on_player_state_changed)
        self._player.mediaLoadFinished.connect(self._on_player_media_load_finished)

        self._load_poll_timer = QTimer(self)
        self._load_poll_timer.setInterval(30)
        self._load_poll_timer.timeout.connect(self._poll_media_preload_state)

        player_box = QGroupBox(tr("Shared Preview"))
        player_root = QVBoxLayout(player_box)
        transport = QHBoxLayout()
        self.player_play_btn = QPushButton(tr("Play"))
        self.player_stop_btn = QPushButton(tr("Stop"))
        transport.addWidget(self.player_play_btn)
        transport.addWidget(self.player_stop_btn)
        transport.addStretch(1)
        self.player_total_label = QLabel(f"{tr('Total')} 00:00:00")
        self.player_elapsed_label = QLabel(f"{tr('Elapsed')} 00:00:00")
        self.player_remaining_label = QLabel(f"{tr('Remaining')} 00:00:00")
        transport.addWidget(self.player_total_label)
        transport.addWidget(self.player_elapsed_label)
        transport.addWidget(self.player_remaining_label)
        player_root.addLayout(transport)
        self.player_slider = QSlider(Qt.Horizontal)
        self.player_slider.setRange(0, 0)
        player_root.addWidget(self.player_slider)
        self.player_cue_indicator = CueRangeIndicator()
        player_root.addWidget(self.player_cue_indicator)
        self._waveform_refresh = WaveformRefreshController(
            on_peaks=self.player_cue_indicator.set_waveform,
            is_valid=lambda: self._duration_ms > 0,
            sample_count=1800,
            parent=self,
        )
        self.player_status_label = QLabel(tr("Select a sound file to preview it across all tabs."))
        self.player_status_label.setWordWrap(True)
        player_root.addWidget(self.player_status_label)
        root.addWidget(player_box)

        self.player_play_btn.clicked.connect(self._toggle_player_playback)
        self.player_stop_btn.clicked.connect(self._stop_shared_player)
        self.player_slider.sliderPressed.connect(self._on_player_slider_pressed)
        self.player_slider.sliderReleased.connect(self._on_player_slider_released)
        self.player_slider.valueChanged.connect(self._on_player_slider_value_changed)
        self._refresh_player_transport(0)
        self._refresh_player_buttons()
        self._refresh_shared_cue_indicator()

    def _load_state(self, state: SoundButtonEditorState) -> None:
        self._loading_state = True
        self._state = SoundButtonEditorState(
            file_path=str(state.file_path or "").strip(),
            caption=str(state.caption or "").strip(),
            notes=str(state.notes or "").strip(),
            disable_video_loading=bool(state.disable_video_loading),
            lyric_file=str(state.lyric_file or "").strip(),
            automation_script_path=str(state.automation_script_path or "").strip(),
            automation_script_bypassed=bool(state.automation_script_bypassed),
            vocal_removed_file=str(state.vocal_removed_file or "").strip(),
            volume_override_pct=state.volume_override_pct,
            sound_hotkey=str(state.sound_hotkey or "").strip(),
            sound_midi_hotkey=normalize_midi_binding(state.sound_midi_hotkey),
            display_focus=normalize_display_focus(state.display_focus, allow_empty=True, default="none"),
            display_image_path=str(state.display_image_path or "").strip(),
            audio_beat_map=normalize_audio_beat_map(state.audio_beat_map),
            cue_start_ms=state.cue_start_ms,
            cue_end_ms=state.cue_end_ms,
            timecode_offset_ms=state.timecode_offset_ms,
            timecode_timeline_mode=normalize_slot_timecode_timeline_mode(state.timecode_timeline_mode),
            sound_button_automation=normalize_sound_button_automation_config(state.sound_button_automation),
        )

        normalized = self._state.audio_beat_map
        self._audio_beat_times_ms = [] if normalized is None else list(normalized.beat_times_ms)
        self._audio_beat_numbers = [] if normalized is None else list(normalized.beat_numbers)
        self._audio_beat_source = "" if normalized is None else str(normalized.source or "")
        self._audio_beat_confidence = 0.0 if normalized is None else float(normalized.confidence or 0.0)
        self._audio_analysis_method = "" if normalized is None else str(normalized.analysis_method or "")
        self._audio_analysis_confidence = 0.0 if normalized is None else float(normalized.analysis_confidence or 0.0)
        self._audio_analysis_version = "" if normalized is None else str(normalized.analysis_version or "")

        self.file_edit.setText(self._state.file_path)
        self.caption_edit.setText(self._state.caption)
        self.notes_edit.setText(self._state.notes)
        self.disable_video_loading_checkbox.setChecked(self._state.disable_video_loading)
        self.lyric_file_edit.setText(self._state.lyric_file)
        self.automation_script_edit.setText(self._state.automation_script_path)
        self.automation_script_bypass_checkbox.setChecked(self._state.automation_script_bypassed)
        self.vocal_removed_file_edit.setText(self._state.vocal_removed_file)
        self.sound_hotkey_edit.setHotkey(self._state.sound_hotkey)
        self._set_midi_binding(self._state.sound_midi_hotkey)
        self.display_image_edit.setText(self._state.display_image_path)
        focus_index = self.display_focus_combo.findData(self._state.display_focus or "none")
        self.display_focus_combo.setCurrentIndex(focus_index if focus_index >= 0 else 0)
        self.custom_volume_checkbox.setChecked(self._state.volume_override_pct is not None)
        self.volume_slider.setValue(75 if self._state.volume_override_pct is None else int(self._state.volume_override_pct))

        self.audio_metronome_enabled_checkbox.setChecked(normalized is not None)
        self.audio_bpm_edit.setText("120.0" if normalized is None else f"{float(normalized.bpm):.2f}")
        self.audio_timesig_num_edit.setText("4" if normalized is None else str(int(normalized.time_signature_num)))
        denominator = 4 if normalized is None else int(normalized.time_signature_den)
        denominator_index = self.audio_timesig_den_combo.findData(denominator)
        self.audio_timesig_den_combo.setCurrentIndex(denominator_index if denominator_index >= 0 else 1)
        self.audio_downbeat_offset_edit.setText("0" if normalized is None else str(int(normalized.first_downbeat_ms)))

        self.cue_start_edit.setText("" if self._state.cue_start_ms is None else format_timecode(self._state.cue_start_ms))
        self.cue_end_edit.setText("" if self._state.cue_end_ms is None else format_timecode(self._state.cue_end_ms))
        self.timecode_offset_edit.set_offset_ms(self._state.timecode_offset_ms)
        if self._state.timecode_timeline_mode == "audio_file":
            self.timecode_timeline_audio_file_radio.setChecked(True)
        elif self._state.timecode_timeline_mode == "cue_region":
            self.timecode_timeline_cue_region_radio.setChecked(True)
        else:
            self.timecode_timeline_global_radio.setChecked(True)

        self._loading_state = False
        self._dirty = False
        self._refresh_audio_analysis_status()
        self._sync_audio_beat_controls()
        self._sync_display_focus_controls()
        self._refresh_cue_status()
        self._refresh_timecode_status()
        self._refresh_lyric_status()
        self._refresh_automation_status()
        self._refresh_button_automation_summary()
        self._refresh_shared_player_context()
        self._refresh_summary()
        self._refresh_title()
        self._load_lyric_text_from_linked_path(force=True)
        self._load_automation_script_text_from_linked_path(force=True)
        self._load_shared_preview_media()

    def _mark_dirty(self, *_args) -> None:
        if self._loading_state:
            return
        self._dirty = True
        self._refresh_title()
        self._refresh_summary()

    def _refresh_title(self) -> None:
        suffix = f" - {self._slot_title}" if self._slot_title else ""
        dirty = " *" if self._dirty else ""
        self.setWindowTitle(f"{tr('Edit Sound Button')}{suffix}{dirty}")

    def _refresh_summary(self) -> None:
        file_name = os.path.basename(self.file_edit.text().strip()) or tr("(no file)")
        lyric = tr("linked") if self.lyric_file_edit.text().strip() else tr("none")
        script = tr("linked") if self.automation_script_edit.text().strip() else tr("none")
        self.summary_label.setText(
            tr("Editing {file_name}. Lyric: {lyric}. Automation Script: {script}. Save keeps this window open.").format(
                file_name=file_name,
                lyric=lyric,
                script=script,
            )
        )

    def _refresh_cue_status(self) -> None:
        start_text = self.cue_start_edit.text().strip()
        end_text = self.cue_end_edit.text().strip()
        start_ms = parse_timecode_to_ms(start_text) if start_text else None
        end_ms = parse_timecode_to_ms(end_text) if end_text else None
        if (start_text and start_ms is None) or (end_text and end_ms is None):
            self.cue_status_label.setText(tr("Cue format must be mm:ss or mm:ss:ff."))
            return
        if start_ms is not None and end_ms is not None and end_ms < start_ms:
            self.cue_status_label.setText(tr("End cue cannot be earlier than start cue."))
            return
        if start_ms is None and end_ms is None:
            self.cue_status_label.setText(tr("No cue override. Playback uses the full file."))
            return
        self.cue_status_label.setText(tr("Cue is set. Use the full cue editor for waveform preview and scrubbing."))

    def _refresh_timecode_status(self) -> None:
        offset_ms = self.timecode_offset_edit.offset_ms()
        if offset_ms is None:
            self.timecode_status_label.setText(tr("Offset format must be HH:MM:SS:FF."))
            return
        if self.timecode_timeline_audio_file_radio.isChecked():
            mode = tr("actual audio file")
        elif self.timecode_timeline_cue_region_radio.isChecked():
            mode = tr("cue set point")
        else:
            mode = tr("global setting")
        self.timecode_status_label.setText(
            tr("Timecode uses {mode} with offset {offset}.").format(
                mode=mode,
                offset=self.timecode_offset_edit.text().strip() or "00:00:00:00",
            )
        )

    def _refresh_lyric_status(self) -> None:
        path = self.lyric_file_edit.text().strip()
        if not path:
            self.lyric_status_label.setText(tr("No lyric file linked."))
            return
        if os.path.exists(path):
            self.lyric_status_label.setText(tr("Linked lyric file exists and can be opened from this tab."))
            return
        self.lyric_status_label.setText(tr("Linked lyric file does not exist yet. Create it or choose another path."))

    def _refresh_automation_status(self) -> None:
        path = self.automation_script_edit.text().strip()
        messages: list[str] = []
        if path:
            if os.path.exists(path):
                messages.append(tr("Automation script file exists."))
            else:
                messages.append(tr("Automation script file does not exist yet."))
        else:
            messages.append(tr("No automation script linked."))
        if self.automation_script_bypass_checkbox.isChecked():
            messages.append(tr("Script bypass is enabled."))
        self.automation_status_label.setText(" ".join(messages))

    def _refresh_shared_player_context(self) -> None:
        current = format_timecode(max(0, int(self.player_slider.value())))
        cue_start_ms = parse_timecode_to_ms(self.cue_start_edit.text().strip()) if hasattr(self, "cue_start_edit") else None
        cue_end_ms = parse_timecode_to_ms(self.cue_end_edit.text().strip()) if hasattr(self, "cue_end_edit") else None
        cue_start_text = format_timecode(cue_start_ms) if cue_start_ms is not None else tr("start")
        cue_end_text = format_timecode(cue_end_ms) if cue_end_ms is not None else tr("end")
        text = tr("Shared preview position: {current}. Cue range: {start} to {end}.").format(
            current=current,
            start=cue_start_text,
            end=cue_end_text,
        )
        if hasattr(self, "lyric_player_context_label"):
            self.lyric_player_context_label.setText(text)
        if hasattr(self, "button_automation_player_context_label"):
            self.button_automation_player_context_label.setText(text)
        if hasattr(self, "automation_script_player_context_label"):
            self.automation_script_player_context_label.setText(text)

    def _current_file_path(self) -> str:
        file_edit = getattr(self, "file_edit", None)
        if file_edit is not None:
            try:
                return str(file_edit.text() or "").strip()
            except Exception:
                pass
        return str(getattr(self._state, "file_path", "") or "").strip()

    def _refresh_player_transport(self, position_ms: int) -> None:
        total = max(0, int(self._duration_ms))
        elapsed = max(0, min(total, int(position_ms)))
        remaining = max(0, total - elapsed)
        self.player_total_label.setText(f"{tr('Total')} {format_timecode(total)}")
        self.player_elapsed_label.setText(f"{tr('Elapsed')} {format_timecode(elapsed)}")
        self.player_remaining_label.setText(f"{tr('Remaining')} {format_timecode(remaining)}")
        self.player_cue_indicator.set_position(elapsed)
        self._refresh_shared_player_context()

    def _refresh_shared_cue_indicator(self) -> None:
        cue_start_ms = parse_timecode_to_ms(self.cue_start_edit.text().strip()) if hasattr(self, "cue_start_edit") else None
        cue_end_ms = parse_timecode_to_ms(self.cue_end_edit.text().strip()) if hasattr(self, "cue_end_edit") else None
        self.player_cue_indicator.set_values(self._duration_ms, cue_start_ms, cue_end_ms)
        self._refresh_shared_player_context()

    def _refresh_player_buttons(self) -> None:
        ready = (not self._is_loading_media) and bool(self._current_file_path())
        self.player_play_btn.setEnabled(ready)
        self.player_stop_btn.setEnabled(ready)
        self.player_slider.setEnabled(ready)
        playing = self._player.state() == ExternalMediaPlayer.PlayingState
        self.player_play_btn.setText(tr("Pause") if playing else tr("Play"))

    def _load_shared_preview_media(self) -> None:
        self._duration_ms = 0
        self.player_slider.setRange(0, 0)
        self.player_slider.setValue(0)
        self.player_cue_indicator.set_waveform([])
        self._refresh_player_transport(0)
        self._refresh_player_buttons()
        file_path = self._current_file_path()
        self.player_status_label.setText(tr("Loading preview...") if file_path else tr("Select a sound file to preview it across all tabs."))
        self._is_loading_media = bool(file_path)
        if self._load_poll_timer.isActive():
            self._load_poll_timer.stop()
        if not file_path:
            self._is_loading_media = False
            self._refresh_player_buttons()
            return
        self._load_wait_started = 0.0
        try:
            request_audio_preload([file_path], prioritize=True, force=True)
        except Exception:
            pass
        if is_audio_preloaded(file_path):
            self._finalize_player_media_load()
            return
        self._load_wait_started = time.perf_counter()
        self._load_poll_timer.start()

    def _poll_media_preload_state(self) -> None:
        if not self._is_loading_media:
            self._load_poll_timer.stop()
            return
        file_path = self._current_file_path()
        if not file_path:
            self._load_poll_timer.stop()
            self._is_loading_media = False
            self._refresh_player_buttons()
            return
        elapsed = max(0.0, time.perf_counter() - self._load_wait_started)
        if is_audio_preloaded(file_path) or elapsed >= self._load_wait_timeout_sec:
            self._load_poll_timer.stop()
            self._finalize_player_media_load()

    def _finalize_player_media_load(self) -> None:
        file_path = self._current_file_path()
        if not file_path:
            self._is_loading_media = False
            self._refresh_player_buttons()
            return
        try:
            self._media_load_request_id = int(self._player.setMediaAsync(file_path))
        except Exception as exc:
            self._is_loading_media = False
            self.player_status_label.setText(f"{tr('Could not load preview:')} {exc}")
            self._refresh_player_buttons()

    def _on_player_media_load_finished(self, request_id: int, ok: bool, error: str) -> None:
        if int(request_id) != int(self._media_load_request_id):
            return
        self._is_loading_media = False
        if not ok:
            self.player_status_label.setText(f"{tr('Could not load preview:')} {error or tr('Unknown error')}")
            self._refresh_player_buttons()
            return
        self._duration_ms = max(0, int(self._player.duration()))
        self.player_slider.setRange(0, self._duration_ms)
        self.player_status_label.setText(tr("Shared preview is ready."))
        if self._waveform_refresh is not None:
            self._waveform_refresh.request(player=self._player, duration_ms=self._duration_ms)
        self._refresh_shared_cue_indicator()
        self._refresh_player_transport(self._player.position())
        self._refresh_player_buttons()

    def _on_player_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = max(0, int(duration_ms))
        self.player_slider.setRange(0, self._duration_ms)
        self._refresh_shared_cue_indicator()
        self._refresh_player_transport(self._player.position())

    def _on_player_position_changed(self, position_ms: int) -> None:
        pos = max(0, int(position_ms))
        if not self._is_scrubbing:
            self.player_slider.blockSignals(True)
            self.player_slider.setValue(pos)
            self.player_slider.blockSignals(False)
        self._refresh_player_transport(pos)

    def _on_player_state_changed(self, _state: int) -> None:
        self._refresh_player_buttons()

    def _toggle_player_playback(self) -> None:
        if self._is_loading_media:
            return
        state = self._player.state()
        if state == ExternalMediaPlayer.PlayingState:
            self._player.pause()
            return
        self._player.play()

    def _stop_shared_player(self) -> None:
        self._player.stop()
        self._player.setPosition(0)
        self._refresh_player_transport(0)

    def _on_player_slider_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_player_slider_released(self) -> None:
        self._is_scrubbing = False
        self._player.setPosition(max(0, int(self.player_slider.value())))

    def _on_player_slider_value_changed(self, value: int) -> None:
        if self._is_scrubbing:
            self._refresh_player_transport(value)

    def _refresh_button_automation_summary(self) -> None:
        config = normalize_sound_button_automation_config(self._state.sound_button_automation)
        if config is None:
            self.button_automation_summary.setText(tr("No sound button automation configured."))
            return
        populated: list[str] = []
        for event_name in SOUND_BUTTON_AUTOMATION_EVENTS:
            commands = list(getattr(config, event_name, None) or [])
            if commands:
                populated.append(f"{tr(sound_button_automation_event_label(event_name))}: {len(commands)}")
        summary = ", ".join(populated[:6])
        if len(populated) > 6:
            summary = f"{summary}, +{len(populated) - 6}"
        mode = str(getattr(config, "mode", "simple") or "simple").strip().lower()
        bypassed = tr("Bypassed") if bool(getattr(config, "bypassed", False)) else tr("Active")
        self.button_automation_summary.setText(
            tr("Mode: {mode}. Status: {status}. {summary}").format(
                mode=mode,
                status=bypassed,
                summary=summary or tr("No triggers configured."),
            )
        )

    def _sync_display_focus_controls(self) -> None:
        mode = normalize_display_focus(str(self.display_focus_combo.currentData() or ""), default="none")
        enabled = mode == "image"
        self.display_image_edit.setEnabled(enabled)
        self.display_image_browse_btn.setEnabled(enabled)
        self.display_image_clear_btn.setEnabled(enabled)

    def _sync_audio_beat_controls(self) -> None:
        enabled = bool(self.audio_metronome_enabled_checkbox.isChecked())
        for widget in (
            self.audio_bpm_edit,
            self.audio_timesig_num_edit,
            self.audio_timesig_den_combo,
            self.audio_downbeat_offset_edit,
            self.audio_clear_analysis_btn,
        ):
            widget.setEnabled(enabled)

    def _refresh_audio_analysis_status(self) -> None:
        if not self._audio_beat_times_ms:
            if self.audio_metronome_enabled_checkbox.isChecked():
                self.audio_analysis_status_label.setText(tr("Manual timing"))
            else:
                self.audio_analysis_status_label.setText(tr("No analysis"))
            return
        source = str(self._audio_analysis_method or self._audio_beat_source or "analysis").replace("_", " ").strip().title()
        confidence = int(round(max(0.0, min(1.0, float(self._audio_analysis_confidence or self._audio_beat_confidence or 0.0))) * 100.0))
        self.audio_analysis_status_label.setText(f"{source}: {len(self._audio_beat_times_ms)} beats, {confidence}%")

    def _audio_beat_map_from_inputs(self) -> Optional[AudioBeatMap]:
        if not self.audio_metronome_enabled_checkbox.isChecked():
            return None
        try:
            bpm = float(self.audio_bpm_edit.text().strip() or "120.0")
        except ValueError:
            bpm = 120.0
        try:
            time_signature_num = int(self.audio_timesig_num_edit.text().strip() or "4")
        except ValueError:
            time_signature_num = 4
        try:
            first_downbeat_ms = int(self.audio_downbeat_offset_edit.text().strip() or "0")
        except ValueError:
            first_downbeat_ms = 0
        denominator = int(self.audio_timesig_den_combo.currentData() or 4)
        return normalize_audio_beat_map(
            AudioBeatMap(
                bpm=max(1.0, bpm),
                time_signature_num=max(1, time_signature_num),
                time_signature_den=denominator,
                first_downbeat_ms=max(0, first_downbeat_ms),
                beat_times_ms=list(self._audio_beat_times_ms),
                beat_numbers=list(self._audio_beat_numbers),
                source=str(self._audio_beat_source or "manual"),
                confidence=float(self._audio_beat_confidence or 0.0),
                analysis_method=str(self._audio_analysis_method or self._audio_beat_source or "manual"),
                analysis_confidence=float(self._audio_analysis_confidence or self._audio_beat_confidence or 0.0),
                analysis_version=str(self._audio_analysis_version or "1"),
            )
        )

    def _clear_audio_analysis(self) -> None:
        self.audio_metronome_enabled_checkbox.setChecked(False)
        self.audio_bpm_edit.setText("120.0")
        self.audio_timesig_num_edit.setText("4")
        denominator_index = self.audio_timesig_den_combo.findData(4)
        self.audio_timesig_den_combo.setCurrentIndex(denominator_index if denominator_index >= 0 else 0)
        self.audio_downbeat_offset_edit.setText("0")
        self._audio_beat_times_ms = []
        self._audio_beat_numbers = []
        self._audio_beat_source = ""
        self._audio_beat_confidence = 0.0
        self._audio_analysis_method = ""
        self._audio_analysis_confidence = 0.0
        self._audio_analysis_version = ""
        self._refresh_audio_analysis_status()
        self._mark_dirty()

    def _set_midi_binding(self, token: str) -> None:
        normalized = normalize_midi_binding(token)
        self._midi_binding = normalized
        self.sound_midi_hotkey_edit.setText(midi_binding_to_display(normalized) if normalized else "")

    def _start_midi_learn(self) -> None:
        self._midi_learning = True
        self.sound_midi_hotkey_edit.setStyleSheet("QLineEdit{border:2px solid #2E65FF;}")

    def _on_midi_binding(self, token: str, source_selector: str = "") -> None:
        if not self._midi_learning:
            return
        _prev_selector, normalized_token = split_midi_binding(token)
        if source_selector:
            self._set_midi_binding(f"{source_selector}|{normalized_token}")
        else:
            self._set_midi_binding(normalized_token)
        self._midi_learning = False
        self.sound_midi_hotkey_edit.setStyleSheet("")
        self._mark_dirty()

    def _browse_file(self) -> None:
        start_dir = self._start_dir
        current = self.file_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Sound File"),
            start_dir,
            build_audio_file_dialog_filter([], True),
        )
        if file_path:
            self.file_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)
            self._load_shared_preview_media()

    def _browse_lyric_file(self) -> None:
        start_dir = self._start_dir
        current = self.lyric_file_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Lyric File"),
            start_dir,
            tr("Lyric Files (*.lrc *.srt);;All Files (*.*)"),
        )
        if file_path:
            self.lyric_file_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)
            self._load_lyric_text_from_linked_path(force=True)

    def _browse_vocal_removed_file(self) -> None:
        start_dir = self._start_dir
        current = self.vocal_removed_file_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Vocal Removed File"),
            start_dir,
            tr("Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)"),
        )
        if file_path:
            self.vocal_removed_file_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def _browse_automation_script_file(self) -> None:
        start_dir = self._start_dir
        current = self.automation_script_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Automation Script"),
            start_dir,
            tr("Automation Script Files (*.pysspautoscript);;All Files (*.*)"),
        )
        if file_path:
            self.automation_script_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)
            self._load_automation_script_text_from_linked_path(force=True)

    def _browse_display_image_file(self) -> None:
        start_dir = self._start_dir
        current = self.display_image_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Display Image"),
            start_dir,
            tr("Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*.*)"),
        )
        if file_path:
            self.display_image_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def _regenerate_vocal_removed(self) -> None:
        generator = getattr(self._host, "_generate_vocal_removed_file_for_slot", None)
        if not callable(generator):
            return
        path = generator(self.file_edit.text().strip(), self.vocal_removed_file_edit.text().strip())
        if path:
            self.vocal_removed_file_edit.setText(path)
            self._mark_dirty()

    def _analyze_bpm(self) -> None:
        file_path = self.file_edit.text().strip()
        if not file_path:
            QMessageBox.information(self, tr("Analyze BPM"), tr("Select a file before BPM analysis."))
            return
        try:
            audio_beat_map = analyze_audio_beat_map(file_path)
        except Exception as exc:
            QMessageBox.warning(self, tr("Analyze BPM"), f"{tr('Could not analyze BPM.')}\n\n{exc}")
            return
        self._load_state(
            SoundButtonEditorState(
                **{
                    **self.values().__dict__,
                    "audio_beat_map": audio_beat_map,
                }
            )
        )
        self._dirty = True
        self._refresh_title()
        self._refresh_summary()

    def _clear_cues(self) -> None:
        self.cue_start_edit.setText("")
        self.cue_end_edit.setText("")
        self._mark_dirty()

    def _open_cue_editor(self) -> None:
        file_path = self.file_edit.text().strip()
        if not file_path:
            QMessageBox.information(self, tr("Set Cue Points"), tr("Select a file before opening the cue editor."))
            return
        dialog = CuePointDialog(
            file_path=file_path,
            audio_source=file_path,
            title=self.caption_edit.text().strip() or os.path.basename(file_path),
            cue_start_ms=self.values().cue_start_ms,
            cue_end_ms=self.values().cue_end_ms,
            stop_host_playback=getattr(self._host, "_hard_stop_all", None),
            language=self._language,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        cue_start_ms, cue_end_ms = dialog.values()
        self.cue_start_edit.setText("" if cue_start_ms is None else format_timecode(cue_start_ms))
        self.cue_end_edit.setText("" if cue_end_ms is None else format_timecode(cue_end_ms))
        self._mark_dirty()

    def _nudge_timecode_offset(self, delta_ms: int) -> None:
        current = self.timecode_offset_edit.offset_ms()
        if current is None:
            current = 0
        self.timecode_offset_edit.set_offset_ms(max(0, int(current) + int(delta_ms)))
        self._mark_dirty()

    def _scan_matching_lyric(self) -> None:
        file_path = self.file_edit.text().strip()
        if not file_path:
            QMessageBox.information(self, tr("Lyric"), tr("Select a file before scanning for a lyric file."))
            return
        finder = getattr(self._host, "_find_matching_lyric_file", None)
        candidate = finder(file_path) if callable(finder) else ""
        if not candidate:
            QMessageBox.information(self, tr("Lyric"), tr("No matching lyric file was found."))
            return
        self.lyric_file_edit.setText(candidate)
        self._load_lyric_text_from_linked_path(force=True)
        self._mark_dirty()

    def _scan_matching_automation_script(self) -> None:
        file_path = self.file_edit.text().strip()
        if not file_path:
            QMessageBox.information(self, tr("Automation Script"), tr("Select a file before scanning for an automation script."))
            return
        finder = getattr(self._host, "_find_matching_automation_script_file", None)
        candidate = finder(file_path) if callable(finder) else ""
        if not candidate:
            QMessageBox.information(self, tr("Automation Script"), tr("No matching automation script was found."))
            return
        self.automation_script_edit.setText(candidate)
        self._load_automation_script_text_from_linked_path(force=True)
        self._mark_dirty()

    def _create_lyric_file(self) -> str:
        path = self._create_linked_file(kind="lyric")
        if path:
            self.lyric_file_edit.setText(path)
            self._load_lyric_text_from_linked_path(force=True)
            self._mark_dirty()
        return path

    def _create_automation_script_file(self) -> str:
        path = self._create_linked_file(kind="automation_script")
        if path:
            self.automation_script_edit.setText(path)
            self._load_automation_script_text_from_linked_path(force=True)
            self._mark_dirty()
        return path

    def _load_lyric_text_from_linked_path(self, *, force: bool = False) -> None:
        path = self.lyric_file_edit.text().strip()
        if not force and self.lyric_text_edit.document().isModified():
            return
        if not path or not os.path.exists(path):
            self.lyric_text_edit.blockSignals(True)
            self.lyric_text_edit.setPlainText("")
            self.lyric_text_edit.document().setModified(False)
            self.lyric_text_edit.blockSignals(False)
            return
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            QMessageBox.warning(self, tr("Lyric"), f"{tr('Failed to load lyric file:')}\n{exc}")
            return
        self.lyric_text_edit.blockSignals(True)
        self.lyric_text_edit.setPlainText(text)
        self.lyric_text_edit.document().setModified(False)
        self.lyric_text_edit.blockSignals(False)

    def _save_lyric_text_to_linked_path(self) -> bool:
        path = self.lyric_file_edit.text().strip()
        if not path:
            path = self._create_lyric_file()
            if not path:
                return False
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8-sig", newline="") as fh:
                fh.write(self.lyric_text_edit.toPlainText())
        except OSError as exc:
            QMessageBox.warning(self, tr("Lyric"), f"{tr('Failed to save lyric file:')}\n{exc}")
            return False
        self.lyric_text_edit.document().setModified(False)
        self._refresh_lyric_status()
        return True

    def _automation_script_template_payload(self) -> str:
        payload = automation_script_to_dict(AutomationScript(notes="", cues=[]))
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    def _load_automation_script_text_from_linked_path(self, *, force: bool = False) -> None:
        path = self.automation_script_edit.text().strip()
        if not force and self.automation_script_text_edit.document().isModified():
            return
        if not path or not os.path.exists(path):
            self.automation_script_text_edit.blockSignals(True)
            self.automation_script_text_edit.setPlainText(self._automation_script_template_payload() if path else "")
            self.automation_script_text_edit.document().setModified(False)
            self.automation_script_text_edit.blockSignals(False)
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            QMessageBox.warning(self, tr("Automation Script"), f"{tr('Failed to load automation script:')}\n{exc}")
            return
        self.automation_script_text_edit.blockSignals(True)
        self.automation_script_text_edit.setPlainText(text)
        self.automation_script_text_edit.document().setModified(False)
        self.automation_script_text_edit.blockSignals(False)

    def _format_automation_script_json(self) -> None:
        raw = self.automation_script_text_edit.toPlainText().strip()
        if not raw:
            self.automation_script_text_edit.setPlainText(self._automation_script_template_payload())
            self.automation_script_text_edit.document().setModified(True)
            self._mark_dirty()
            return
        try:
            payload = json.loads(raw)
        except Exception as exc:
            QMessageBox.warning(self, tr("Automation Script"), f"{tr('Automation script JSON is invalid:')}\n{exc}")
            return
        self.automation_script_text_edit.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        self.automation_script_text_edit.document().setModified(True)
        self._mark_dirty()

    def _save_automation_script_text_to_linked_path(self) -> bool:
        path = self.automation_script_edit.text().strip()
        if not path:
            path = self._create_automation_script_file()
            if not path:
                return False
        raw = self.automation_script_text_edit.toPlainText().strip()
        if not raw:
            try:
                save_automation_script(path, AutomationScript(notes="", cues=[]))
            except Exception as exc:
                QMessageBox.warning(self, tr("Automation Script"), f"{tr('Failed to save automation script:')}\n{exc}")
                return False
            self._load_automation_script_text_from_linked_path(force=True)
            self._refresh_automation_status()
            return True
        try:
            payload = json.loads(raw)
        except Exception as exc:
            QMessageBox.warning(self, tr("Automation Script"), f"{tr('Automation script JSON is invalid:')}\n{exc}")
            return False
        if not isinstance(payload, dict):
            QMessageBox.warning(self, tr("Automation Script"), tr("Automation script JSON must be an object."))
            return False
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            load_automation_script(path)
        except Exception as exc:
            QMessageBox.warning(self, tr("Automation Script"), f"{tr('Failed to save automation script:')}\n{exc}")
            return False
        self.automation_script_text_edit.document().setModified(False)
        self._refresh_automation_status()
        return True

    def _create_linked_file(self, *, kind: str) -> str:
        file_path = self.file_edit.text().strip()
        audio_dir = os.path.dirname(file_path) or self._start_dir or "."
        base_name = self.caption_edit.text().strip() or (os.path.splitext(os.path.basename(file_path))[0] if file_path else "new_file")
        if kind == "lyric":
            default_ext = ".lrc" if str(getattr(self._host, "new_lyric_file_format", "lrc")).strip().lower() == "lrc" else ".srt"
            if default_ext == ".lrc":
                file_filter = tr("LRC Files (*.lrc);;SRT Files (*.srt);;All Files (*.*)")
            else:
                file_filter = tr("SRT Files (*.srt);;LRC Files (*.lrc);;All Files (*.*)")
            title = tr("Create Lyric File")
        else:
            default_ext = AUTOMATION_SCRIPT_EXTENSION
            file_filter = tr("Automation Script Files (*.pysspautoscript);;All Files (*.*)")
            title = tr("Create Automation Script")
        suggestion = os.path.join(audio_dir, f"{base_name}{default_ext}")
        save_path, _ = QFileDialog.getSaveFileName(self, title, suggestion, file_filter)
        save_path = str(save_path or "").strip()
        if not save_path:
            return ""
        if kind == "lyric":
            if not save_path.lower().endswith((".lrc", ".srt")):
                save_path = f"{save_path}{default_ext}"
        elif not save_path.lower().endswith(default_ext):
            save_path = f"{save_path}{default_ext}"
        try:
            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            if not os.path.exists(save_path):
                encoding = "utf-8" if kind == "automation_script" else "utf-8-sig"
                newline = "\n" if kind == "automation_script" else ""
                with open(save_path, "w", encoding=encoding, newline=newline) as fh:
                    fh.write("")
        except OSError as exc:
            QMessageBox.warning(self, title, f"{tr('Failed to create file:')}\n{exc}")
            return ""
        self._start_dir = os.path.dirname(save_path) or self._start_dir
        return save_path

    def _ensure_lyric_path(self) -> str:
        linked_path = self.lyric_file_edit.text().strip()
        if linked_path and os.path.exists(linked_path):
            return linked_path
        if linked_path and not os.path.exists(linked_path):
            answer = QMessageBox.question(
                self,
                tr("Lyric Editor"),
                tr("Linked lyric file does not exist.\n\nCreate this file now?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Yes:
                created = self._create_lyric_file() or linked_path
                if created:
                    self.lyric_file_edit.setText(created)
                    return created
            return ""
        finder = getattr(self._host, "_find_matching_lyric_file", None)
        candidate = finder(self.file_edit.text().strip()) if callable(finder) else ""
        if candidate:
            use_candidate = QMessageBox.question(
                self,
                tr("Lyric Editor"),
                tr("A matching lyric file was found. Link it now?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if use_candidate == QMessageBox.Yes:
                self.lyric_file_edit.setText(candidate)
                return candidate
        answer = QMessageBox.question(
            self,
            tr("Lyric Editor"),
            tr("This sound has no lyric linked. Create a lyric file now?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return ""
        created = self._create_linked_file(kind="lyric")
        if created:
            self.lyric_file_edit.setText(created)
        return created

    def _ensure_automation_script_path(self) -> str:
        linked_path = self.automation_script_edit.text().strip()
        if linked_path and os.path.exists(linked_path):
            return linked_path
        if linked_path and not os.path.exists(linked_path):
            answer = QMessageBox.question(
                self,
                tr("Automation Script Editor"),
                tr("Linked automation script does not exist.\n\nCreate this file now?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Yes:
                created = self._create_automation_script_file() or linked_path
                if created:
                    self.automation_script_edit.setText(created)
                    return created
            return ""
        finder = getattr(self._host, "_find_matching_automation_script_file", None)
        candidate = finder(self.file_edit.text().strip()) if callable(finder) else ""
        if candidate:
            use_candidate = QMessageBox.question(
                self,
                tr("Automation Script Editor"),
                tr("A matching automation script was found. Link it now?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if use_candidate == QMessageBox.Yes:
                self.automation_script_edit.setText(candidate)
                return candidate
        answer = QMessageBox.question(
            self,
            tr("Automation Script Editor"),
            tr("This sound has no automation script linked. Create one now?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return ""
        created = self._create_linked_file(kind="automation_script")
        if created:
            self.automation_script_edit.setText(created)
        return created

    def _open_lyric_editor(self) -> None:
        lyric_path = self._ensure_lyric_path()
        if not lyric_path:
            return
        file_path = self.file_edit.text().strip()
        preferred_mode = "lrc" if os.path.splitext(lyric_path)[1].lower() == ".lrc" else "srt"
        dialog = LyricEditorDialog(
            lyric_path=lyric_path,
            audio_path=file_path,
            audio_source=file_path,
            title=self.caption_edit.text().strip(),
            language=self._language,
            preferred_mode=preferred_mode,
            cue_start_ms=self.values().cue_start_ms,
            cue_end_ms=self.values().cue_end_ms,
            stop_host_playback=getattr(self._host, "_hard_stop_all", None),
            parent=self,
        )
        dialog.exec_()

    def _open_automation_script_editor(self) -> None:
        script_path = self._ensure_automation_script_path()
        if not script_path:
            return
        file_path = self.file_edit.text().strip()
        dialog = AutomationScriptEditorDialog(
            script_path=script_path,
            audio_path=file_path,
            audio_source=file_path,
            title=self.caption_edit.text().strip(),
            lyric_path=self.lyric_file_edit.text().strip(),
            cue_start_ms=self.values().cue_start_ms,
            cue_end_ms=self.values().cue_end_ms,
            companion_payload=load_companion_available_commands(),
            internal_target_catalog=getattr(self._host, "_internal_automation_target_catalog", lambda: {})(),
            hide_black_empty=bool(getattr(self._host, "companion_available_commands_filter_black_empty", True)),
            show_lyric_default=bool(getattr(self._host, "automation_script_editor_show_lyric", False)),
            on_show_lyric_changed=getattr(self._host, "_set_automation_script_editor_show_lyric", None),
            language=self._language,
            stop_host_playback=getattr(self._host, "_hard_stop_all", None),
            parent=self,
        )
        dialog.exec_()

    def _edit_sound_button_automation(self) -> None:
        dialog = SoundButtonAutomationDialog(
            config=self._state.sound_button_automation,
            companion_payload=load_companion_available_commands(),
            internal_target_catalog=getattr(self._host, "_internal_automation_target_catalog", lambda: {})(),
            hide_black_empty=bool(getattr(self._host, "companion_available_commands_filter_black_empty", True)),
            language=self._language,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        self._state.sound_button_automation = normalize_sound_button_automation_config(dialog.values())
        self._refresh_button_automation_summary()
        self._refresh_automation_status()
        self._mark_dirty()

    def _clear_sound_button_automation(self) -> None:
        self._state.sound_button_automation = None
        self._refresh_button_automation_summary()
        self._mark_dirty()

    def _save(self) -> None:
        cue_start_text = self.cue_start_edit.text().strip()
        cue_end_text = self.cue_end_edit.text().strip()
        cue_start_ms = parse_timecode_to_ms(cue_start_text) if cue_start_text else None
        cue_end_ms = parse_timecode_to_ms(cue_end_text) if cue_end_text else None
        if cue_start_text and cue_start_ms is None:
            QMessageBox.warning(self, tr("Edit Sound Button"), tr("Start cue format must be mm:ss or mm:ss:ff."))
            self.tabs.setCurrentWidget(self.cue_tab_page)
            return
        if cue_end_text and cue_end_ms is None:
            QMessageBox.warning(self, tr("Edit Sound Button"), tr("End cue format must be mm:ss or mm:ss:ff."))
            self.tabs.setCurrentWidget(self.cue_tab_page)
            return
        if cue_start_ms is not None and cue_end_ms is not None and cue_end_ms < cue_start_ms:
            QMessageBox.warning(self, tr("Edit Sound Button"), tr("End cue cannot be earlier than start cue."))
            self.tabs.setCurrentWidget(self.cue_tab_page)
            return
        if self.timecode_offset_edit.offset_ms() is None:
            QMessageBox.warning(self, tr("Edit Sound Button"), tr("Timecode offset must use HH:MM:SS:FF format."))
            self.tabs.setCurrentWidget(self.timecode_tab_page)
            return
        if self.lyric_file_edit.text().strip() and not self._save_lyric_text_to_linked_path():
            self.tabs.setCurrentWidget(self.lyric_tab_page)
            return
        if self.automation_script_edit.text().strip() and not self._save_automation_script_text_to_linked_path():
            self.tabs.setCurrentWidget(self.automation_script_tab_page)
            return
        if not callable(self._on_save):
            self._dirty = False
            self._refresh_title()
            return
        state = self.values()
        normalized = self._on_save(state)
        if normalized is None:
            return
        self._load_state(normalized)
