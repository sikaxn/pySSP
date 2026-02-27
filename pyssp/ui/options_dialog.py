from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import urlparse

import threading

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QLineEdit,
    QScrollArea,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyssp.settings_store import default_quick_action_keys
from pyssp.i18n import localize_widget_tree, normalize_language, tr
from pyssp.midi_control import (
    list_midi_input_devices,
    midi_binding_to_display,
    midi_input_name_selector,
    midi_input_selector_name,
    normalize_midi_binding,
    split_midi_binding,
)
from pyssp.timecode import (
    MIDI_OUTPUT_DEVICE_NONE,
    MTC_IDLE_KEEP_STREAM,
    TIMECODE_MODE_FOLLOW,
    TIMECODE_MODE_FOLLOW_FREEZE,
    TIMECODE_MODE_SYSTEM,
    TIMECODE_MODE_ZERO,
    TIME_CODE_BIT_DEPTHS,
    TIME_CODE_FPS_CHOICES,
    TIME_CODE_MTC_FPS_CHOICES,
    TIME_CODE_SAMPLE_RATES,
    list_midi_output_devices,
)
from pyssp.ui.stage_display import (
    STAGE_DISPLAY_GADGET_SPECS,
    StageDisplayLayoutEditor,
    gadgets_to_legacy_layout_visibility,
    normalize_stage_display_gadgets,
)
from pyssp.vst import effective_vst_directories, is_vst_supported, plugin_display_name, scan_vst_plugins


class HotkeyCaptureEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Press key")
        self.setReadOnly(True)

    def hotkey(self) -> str:
        return self.text().strip()

    def setHotkey(self, value: str) -> None:
        text = str(value or "").strip()
        self.setText(self._normalize_text(text))

    def keyPressEvent(self, event) -> None:
        key = int(event.key())
        if key in {Qt.Key_Tab, Qt.Key_Backtab}:
            super().keyPressEvent(event)
            return
        if key in {Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Escape}:
            self.clear()
            return

        modifiers = event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier)
        text = self._build_hotkey_text(key, modifiers)
        if text:
            self.setText(text)

    def _build_hotkey_text(self, key: int, modifiers: Qt.KeyboardModifiers) -> str:
        if key == Qt.Key_Shift and modifiers == Qt.ShiftModifier:
            return "Shift"
        if key == Qt.Key_Control and modifiers == Qt.ControlModifier:
            return "Ctrl"
        if key == Qt.Key_Alt and modifiers == Qt.AltModifier:
            return "Alt"
        if key == Qt.Key_Meta and modifiers == Qt.MetaModifier:
            return "Meta"
        seq = QKeySequence(int(key) | int(modifiers)).toString().strip()
        return self._normalize_text(seq)

    def _normalize_text(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        aliases = {
            "control": "Ctrl",
            "ctrl": "Ctrl",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Meta",
            "win": "Meta",
            "super": "Meta",
        }
        lower = raw.lower()
        if lower in aliases:
            return aliases[lower]
        normalized = QKeySequence(raw).toString().strip()
        return normalized or raw


class MidiCaptureEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Unassigned")
        self.setReadOnly(True)
        self._binding = ""

    def binding(self) -> str:
        return self._binding

    def setBinding(self, value: str) -> None:
        token = normalize_midi_binding(value)
        self._binding = token
        self.setText(midi_binding_to_display(token) if token else "")


class OptionsDialog(QDialog):
    vstScanFinished = pyqtSignal(object)
    _HOTKEY_ROWS = [
        ("new_set", "New Set"),
        ("open_set", "Open Set"),
        ("save_set", "Save Set"),
        ("save_set_as", "Save Set As"),
        ("search", "Search"),
        ("options", "Options"),
        ("play_selected_pause", "Play Selected / Pause"),
        ("play_selected", "Play Selected"),
        ("pause_toggle", "Pause/Resume"),
        ("stop_playback", "Stop Playback"),
        ("talk", "Talk"),
        ("next_group", "Next Group"),
        ("prev_group", "Previous Group"),
        ("next_page", "Next Page"),
        ("prev_page", "Previous Page"),
        ("next_sound_button", "Next Sound Button"),
        ("prev_sound_button", "Previous Sound Button"),
        ("multi_play", "Multi-Play"),
        ("go_to_playing", "Go To Playing"),
        ("loop", "Loop"),
        ("next", "Next"),
        ("rapid_fire", "Rapid Fire"),
        ("shuffle", "Shuffle"),
        ("reset_page", "Reset Page"),
        ("play_list", "Play List"),
        ("fade_in", "Fade In"),
        ("cross_fade", "X (Cross Fade)"),
        ("fade_out", "Fade Out"),
        ("mute", "Mute"),
        ("volume_up", "Volume Up"),
        ("volume_down", "Volume Down"),
    ]

    _DEFAULTS = {
        "active_group_color": "#EDE8C8",
        "inactive_group_color": "#ECECEC",
        "title_char_limit": 26,
        "show_file_notifications": True,
        "log_file_enabled": False,
        "reset_all_on_startup": False,
        "click_playing_action": "play_it_again",
        "search_double_click_action": "find_highlight",
        "set_file_encoding": "utf8",
        "main_progress_display_mode": "progress_bar",
        "main_progress_show_text": True,
        "ui_language": "en",
        "vst_enabled": False,
        "vst_directories": effective_vst_directories([]),
        "vst_known_plugins": [],
        "vst_enabled_plugins": [],
        "vst_chain": [],
        "vst_plugin_state": {},
        "preload_audio_enabled": False,
        "preload_current_page_audio": True,
        "preload_audio_memory_limit_mb": 512,
        "preload_memory_pressure_enabled": True,
        "preload_pause_on_playback": False,
        "fade_in_sec": 1.0,
        "cross_fade_sec": 1.0,
        "fade_out_sec": 1.0,
        "fade_on_quick_action_hotkey": True,
        "fade_on_sound_button_hotkey": True,
        "fade_on_pause": False,
        "fade_on_resume": False,
        "fade_on_stop": True,
        "fade_out_when_done_playing": False,
        "fade_out_end_lead_sec": 2.0,
        "max_multi_play_songs": 5,
        "multi_play_limit_action": "stop_oldest",
        "playlist_play_mode": "unplayed_only",
        "rapid_fire_play_mode": "unplayed_only",
        "next_play_mode": "unplayed_only",
        "playlist_loop_mode": "loop_list",
        "candidate_error_action": "stop_playback",
        "main_transport_timeline_mode": "cue_region",
        "main_jog_outside_cue_action": "stop_immediately",
        "talk_volume_level": 30,
        "talk_fade_sec": 0.5,
        "talk_volume_mode": "percent_of_master",
        "talk_blink_button": False,
        "web_remote_enabled": False,
        "web_remote_port": 5050,
        "timecode_audio_output_device": "none",
        "timecode_midi_output_device": MIDI_OUTPUT_DEVICE_NONE,
        "timecode_mode": TIMECODE_MODE_FOLLOW,
        "timecode_fps": 30.0,
        "timecode_mtc_fps": 30.0,
        "timecode_mtc_idle_behavior": MTC_IDLE_KEEP_STREAM,
        "timecode_sample_rate": 48000,
        "timecode_bit_depth": 16,
        "timecode_timeline_mode": "cue_region",
        "state_colors": {
            "playing": "#66FF33",
            "played": "#FF3B30",
            "unplayed": "#B0B0B0",
            "highlight": "#A6D8FF",
            "lock": "#F2D74A",
            "error": "#7B3FB3",
            "place_marker": "#111111",
            "empty": "#0B868A",
            "copied_to_cue": "#2E65FF",
            "cue_indicator": "#61D6FF",
            "volume_indicator": "#FFD45A",
            "midi_indicator": "#FF9E4A",
        },
        "sound_button_text_color": "#000000",
        "hotkeys": {
            "new_set": ("Ctrl+N", ""),
            "open_set": ("Ctrl+O", ""),
            "save_set": ("Ctrl+S", ""),
            "save_set_as": ("Ctrl+Shift+S", ""),
            "search": ("Ctrl+F", ""),
            "options": ("", ""),
            "play_selected_pause": ("", ""),
            "play_selected": ("", ""),
            "pause_toggle": ("P", ""),
            "stop_playback": ("Space", "Return"),
            "talk": ("Shift", ""),
            "next_group": ("", ""),
            "prev_group": ("", ""),
            "next_page": ("", ""),
            "prev_page": ("", ""),
            "next_sound_button": ("", ""),
            "prev_sound_button": ("", ""),
            "multi_play": ("", ""),
            "go_to_playing": ("", ""),
            "loop": ("", ""),
            "next": ("", ""),
            "rapid_fire": ("", ""),
            "shuffle": ("", ""),
            "reset_page": ("", ""),
            "play_list": ("", ""),
            "fade_in": ("", ""),
            "cross_fade": ("", ""),
            "fade_out": ("", ""),
            "mute": ("", ""),
            "volume_up": ("", ""),
            "volume_down": ("", ""),
        },
        "sound_button_hotkey_enabled": False,
        "sound_button_hotkey_priority": "system_first",
        "sound_button_hotkey_go_to_playing": False,
        "midi_input_device_ids": [],
        "midi_hotkeys": {},
        "midi_quick_action_enabled": False,
        "midi_quick_action_bindings": ["" for _ in range(48)],
        "midi_sound_button_hotkey_enabled": False,
        "midi_sound_button_hotkey_priority": "system_first",
        "midi_sound_button_hotkey_go_to_playing": False,
        "midi_rotary_enabled": False,
        "midi_rotary_group_binding": "",
        "midi_rotary_page_binding": "",
        "midi_rotary_sound_button_binding": "",
        "midi_rotary_jog_binding": "",
        "midi_rotary_volume_binding": "",
        "midi_rotary_group_invert": False,
        "midi_rotary_page_invert": False,
        "midi_rotary_sound_button_invert": False,
        "midi_rotary_jog_invert": False,
        "midi_rotary_volume_invert": False,
        "midi_rotary_group_sensitivity": 1,
        "midi_rotary_page_sensitivity": 1,
        "midi_rotary_sound_button_sensitivity": 1,
        "midi_rotary_group_relative_mode": "auto",
        "midi_rotary_page_relative_mode": "auto",
        "midi_rotary_sound_button_relative_mode": "auto",
        "midi_rotary_jog_relative_mode": "auto",
        "midi_rotary_volume_relative_mode": "auto",
        "midi_rotary_volume_mode": "relative",
        "midi_rotary_volume_step": 2,
        "midi_rotary_jog_step_ms": 250,
        "stage_display_layout": [
            "current_time",
            "total_time",
            "elapsed",
            "remaining",
            "progress_bar",
            "song_name",
            "next_song",
            "alert",
        ],
        "stage_display_visibility": {
            "current_time": True,
            "alert": False,
            "total_time": True,
            "elapsed": True,
            "remaining": True,
            "progress_bar": True,
            "song_name": True,
            "next_song": True,
        },
        "stage_display_text_source": "caption",
        "stage_display_gadgets": normalize_stage_display_gadgets(None),
    }
    _DISPLAY_OPTION_SPECS = STAGE_DISPLAY_GADGET_SPECS

    def __init__(
        self,
        active_group_color: str,
        inactive_group_color: str,
        title_char_limit: int,
        show_file_notifications: bool,
        fade_in_sec: float,
        cross_fade_sec: float,
        fade_out_sec: float,
        fade_on_quick_action_hotkey: bool,
        fade_on_sound_button_hotkey: bool,
        fade_on_pause: bool,
        fade_on_resume: bool,
        fade_on_stop: bool,
        fade_out_when_done_playing: bool,
        fade_out_end_lead_sec: float,
        talk_volume_level: int,
        talk_fade_sec: float,
        talk_volume_mode: str,
        talk_blink_button: bool,
        log_file_enabled: bool,
        reset_all_on_startup: bool,
        click_playing_action: str,
        search_double_click_action: str,
        set_file_encoding: str,
        main_progress_display_mode: str,
        main_progress_show_text: bool,
        audio_output_device: str,
        vst_enabled: bool,
        vst_directories: List[str],
        vst_known_plugins: List[str],
        vst_enabled_plugins: List[str],
        vst_chain: List[str],
        vst_plugin_state: Dict[str, Dict[str, object]],
        available_audio_devices: List[str],
        available_midi_devices: List[tuple[str, str]],
        preload_audio_enabled: bool,
        preload_current_page_audio: bool,
        preload_audio_memory_limit_mb: int,
        preload_memory_pressure_enabled: bool,
        preload_pause_on_playback: bool,
        preload_total_ram_mb: int,
        preload_ram_cap_mb: int,
        timecode_audio_output_device: str,
        timecode_midi_output_device: str,
        timecode_mode: str,
        timecode_fps: float,
        timecode_mtc_fps: float,
        timecode_mtc_idle_behavior: str,
        timecode_sample_rate: int,
        timecode_bit_depth: int,
        timecode_timeline_mode: str,
        max_multi_play_songs: int,
        multi_play_limit_action: str,
        playlist_play_mode: str,
        rapid_fire_play_mode: str,
        next_play_mode: str,
        playlist_loop_mode: str,
        candidate_error_action: str,
        web_remote_enabled: bool,
        web_remote_port: int,
        web_remote_url: str,
        main_transport_timeline_mode: str,
        main_jog_outside_cue_action: str,
        state_colors: Dict[str, str],
        sound_button_text_color: str,
        hotkeys: Dict[str, tuple[str, str]],
        quick_action_enabled: bool,
        quick_action_keys: List[str],
        sound_button_hotkey_enabled: bool,
        sound_button_hotkey_priority: str,
        sound_button_hotkey_go_to_playing: bool,
        midi_input_device_ids: List[str],
        midi_hotkeys: Dict[str, tuple[str, str]],
        midi_quick_action_enabled: bool,
        midi_quick_action_bindings: List[str],
        midi_sound_button_hotkey_enabled: bool,
        midi_sound_button_hotkey_priority: str,
        midi_sound_button_hotkey_go_to_playing: bool,
        midi_rotary_enabled: bool,
        midi_rotary_group_binding: str,
        midi_rotary_page_binding: str,
        midi_rotary_sound_button_binding: str,
        midi_rotary_jog_binding: str,
        midi_rotary_volume_binding: str,
        midi_rotary_group_invert: bool,
        midi_rotary_page_invert: bool,
        midi_rotary_sound_button_invert: bool,
        midi_rotary_jog_invert: bool,
        midi_rotary_volume_invert: bool,
        midi_rotary_group_sensitivity: int,
        midi_rotary_page_sensitivity: int,
        midi_rotary_sound_button_sensitivity: int,
        midi_rotary_group_relative_mode: str,
        midi_rotary_page_relative_mode: str,
        midi_rotary_sound_button_relative_mode: str,
        midi_rotary_jog_relative_mode: str,
        midi_rotary_volume_relative_mode: str,
        midi_rotary_volume_mode: str,
        midi_rotary_volume_step: int,
        midi_rotary_jog_step_ms: int,
        stage_display_layout: List[str],
        stage_display_visibility: Dict[str, bool],
        stage_display_text_source: str,
        ui_language: str,
        stage_display_gadgets: Optional[Dict[str, Dict[str, object]]] = None,
        initial_page: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setModal(True)
        self.resize(760, 520)

        self.active_group_color = active_group_color
        self.inactive_group_color = inactive_group_color
        self.sound_button_text_color = sound_button_text_color
        self._hotkeys = dict(hotkeys)
        self._hotkey_edits: Dict[str, tuple[HotkeyCaptureEdit, HotkeyCaptureEdit]] = {}
        self._quick_action_enabled = bool(quick_action_enabled)
        self._quick_action_edits: List[HotkeyCaptureEdit] = []
        qa_defaults = default_quick_action_keys()
        self._quick_action_keys = list(quick_action_keys)[:48]
        if len(self._quick_action_keys) < 48:
            self._quick_action_keys.extend(qa_defaults[len(self._quick_action_keys):48])
        self._sound_button_hotkey_enabled = bool(sound_button_hotkey_enabled)
        self._sound_button_hotkey_priority = (
            sound_button_hotkey_priority if sound_button_hotkey_priority in {"system_first", "sound_button_first"} else "system_first"
        )
        self._sound_button_hotkey_go_to_playing = bool(sound_button_hotkey_go_to_playing)
        self._midi_input_device_ids = [str(v).strip() for v in midi_input_device_ids if str(v).strip()]
        self._midi_hotkeys = dict(midi_hotkeys)
        self._midi_hotkey_edits: Dict[str, tuple[MidiCaptureEdit, MidiCaptureEdit]] = {}
        self._midi_quick_action_enabled = bool(midi_quick_action_enabled)
        self._midi_quick_action_edits: List[MidiCaptureEdit] = []
        self._midi_quick_action_bindings = [normalize_midi_binding(v) for v in list(midi_quick_action_bindings)[:48]]
        if len(self._midi_quick_action_bindings) < 48:
            self._midi_quick_action_bindings.extend(["" for _ in range(48 - len(self._midi_quick_action_bindings))])
        self._midi_sound_button_hotkey_enabled = bool(midi_sound_button_hotkey_enabled)
        self._midi_sound_button_hotkey_priority = (
            midi_sound_button_hotkey_priority
            if midi_sound_button_hotkey_priority in {"system_first", "sound_button_first"}
            else "system_first"
        )
        self._midi_sound_button_hotkey_go_to_playing = bool(midi_sound_button_hotkey_go_to_playing)
        self._midi_rotary_enabled = bool(midi_rotary_enabled)
        self._midi_rotary_group_binding = normalize_midi_binding(midi_rotary_group_binding)
        self._midi_rotary_page_binding = normalize_midi_binding(midi_rotary_page_binding)
        self._midi_rotary_sound_button_binding = normalize_midi_binding(midi_rotary_sound_button_binding)
        self._midi_rotary_jog_binding = normalize_midi_binding(midi_rotary_jog_binding)
        self._midi_rotary_volume_binding = normalize_midi_binding(midi_rotary_volume_binding)
        self._midi_rotary_group_invert = bool(midi_rotary_group_invert)
        self._midi_rotary_page_invert = bool(midi_rotary_page_invert)
        self._midi_rotary_sound_button_invert = bool(midi_rotary_sound_button_invert)
        self._midi_rotary_jog_invert = bool(midi_rotary_jog_invert)
        self._midi_rotary_volume_invert = bool(midi_rotary_volume_invert)
        self._midi_rotary_group_sensitivity = max(1, min(20, int(midi_rotary_group_sensitivity)))
        self._midi_rotary_page_sensitivity = max(1, min(20, int(midi_rotary_page_sensitivity)))
        self._midi_rotary_sound_button_sensitivity = max(1, min(20, int(midi_rotary_sound_button_sensitivity)))
        self._midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(midi_rotary_group_relative_mode)
        self._midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(midi_rotary_page_relative_mode)
        self._midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(midi_rotary_sound_button_relative_mode)
        self._midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(midi_rotary_jog_relative_mode)
        self._midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(midi_rotary_volume_relative_mode)
        self._midi_rotary_volume_mode = (
            str(midi_rotary_volume_mode).strip().lower()
            if str(midi_rotary_volume_mode).strip().lower() in {"absolute", "relative"}
            else "relative"
        )
        self._midi_rotary_volume_step = max(1, min(20, int(midi_rotary_volume_step)))
        self._midi_rotary_jog_step_ms = max(10, min(5000, int(midi_rotary_jog_step_ms)))
        self._learning_midi_rotary_target: Optional[MidiCaptureEdit] = None
        self._learning_midi_rotary_state: Optional[dict] = None
        self._midi_warning_label: Optional[QLabel] = None
        self._midi_has_conflict = False
        self._learning_midi_target: Optional[MidiCaptureEdit] = None
        self._ui_language = normalize_language(ui_language)
        self._stage_display_layout = self._normalize_stage_display_layout(stage_display_layout)
        self._stage_display_visibility = self._normalize_stage_display_visibility(stage_display_visibility)
        self._stage_display_gadgets = normalize_stage_display_gadgets(
            stage_display_gadgets,
            legacy_layout=self._stage_display_layout,
            legacy_visibility=self._stage_display_visibility,
        )
        self._stage_display_text_source = (
            str(stage_display_text_source or "").strip().lower()
            if str(stage_display_text_source or "").strip().lower() in {"caption", "filename", "note"}
            else "caption"
        )
        self._hotkey_labels: Dict[str, str] = {key: label for key, label in self._HOTKEY_ROWS}
        self.hotkey_warning_label: Optional[QLabel] = None
        self.state_colors = dict(state_colors)
        self._state_color_buttons: Dict[str, QPushButton] = {}
        self._available_audio_devices = list(available_audio_devices)
        self._available_midi_devices = list(available_midi_devices)
        self._vst_scan_in_progress = False
        self.vstScanFinished.connect(self._on_vst_scan_finished)
        self._vst_supported = is_vst_supported()
        self._vst_enabled = bool(vst_enabled) and self._vst_supported
        self._vst_directories = effective_vst_directories(vst_directories)
        self._vst_known_plugins = [str(v).strip() for v in vst_known_plugins if str(v).strip()]
        self._vst_enabled_plugins = {str(v).strip() for v in vst_enabled_plugins if str(v).strip()}
        self._vst_chain = [str(v).strip() for v in vst_chain if str(v).strip()]
        self._vst_plugin_state: Dict[str, Dict[str, object]] = {
            str(k).strip(): dict(v)
            for k, v in dict(vst_plugin_state or {}).items()
            if str(k).strip() and isinstance(v, dict)
        }

        root_layout = QVBoxLayout(self)
        content = QHBoxLayout()
        root_layout.addLayout(content, 1)

        self.page_list = QListWidget()
        self.page_list.setIconSize(QSize(22, 22))
        self.page_list.setMinimumWidth(210)
        self.page_list.setMaximumWidth(240)
        self.page_list.setFrameShape(QFrame.StyledPanel)
        content.addWidget(self.page_list)

        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)

        self._add_page(
            "General",
            self._mono_icon("info"),
            self._build_general_page(
                title_char_limit=title_char_limit,
                show_file_notifications=show_file_notifications,
                log_file_enabled=log_file_enabled,
                reset_all_on_startup=reset_all_on_startup,
                click_playing_action=click_playing_action,
                search_double_click_action=search_double_click_action,
                set_file_encoding=set_file_encoding,
                main_progress_display_mode=main_progress_display_mode,
                main_progress_show_text=main_progress_show_text,
            ),
        )
        self._add_page(
            "Language",
            self._mono_icon("earth"),
            self._build_language_page(self._ui_language),
        )
        self._add_page(
            "Hotkey",
            self._mono_icon("keyboard"),
            self._build_hotkey_page(),
        )
        self._add_page(
            "Midi Control",
            self._mono_icon("piano"),
            self._build_midi_control_page(),
        )
        self._add_page(
            "Colour",
            self._mono_icon("display"),
            self._build_color_page(),
        )
        self._add_page(
            "Display",
            self._mono_icon("projector"),
            self._build_display_page(),
        )
        self._add_page(
            "Fade",
            self._mono_icon("clock"),
            self._build_delay_page(
                fade_in_sec=fade_in_sec,
                cross_fade_sec=cross_fade_sec,
                fade_out_sec=fade_out_sec,
                fade_on_quick_action_hotkey=fade_on_quick_action_hotkey,
                fade_on_sound_button_hotkey=fade_on_sound_button_hotkey,
                fade_on_pause=fade_on_pause,
                fade_on_resume=fade_on_resume,
                fade_on_stop=fade_on_stop,
                fade_out_when_done_playing=fade_out_when_done_playing,
                fade_out_end_lead_sec=fade_out_end_lead_sec,
            ),
        )
        self._add_page(
            "Playback",
            self._mono_icon("play"),
            self._build_playback_page(
                max_multi_play_songs=max_multi_play_songs,
                multi_play_limit_action=multi_play_limit_action,
                playlist_play_mode=playlist_play_mode,
                rapid_fire_play_mode=rapid_fire_play_mode,
                next_play_mode=next_play_mode,
                playlist_loop_mode=playlist_loop_mode,
                candidate_error_action=candidate_error_action,
                main_transport_timeline_mode=main_transport_timeline_mode,
                main_jog_outside_cue_action=main_jog_outside_cue_action,
            ),
        )
        self._add_page(
            "DSP / Plugin",
            self._mono_icon("rack"),
            self._build_vst_plugin_page(),
        )
        self._add_page(
            "Audio Device / Timecode",
            self._mono_icon("speaker"),
            self._build_audio_device_page(
                audio_output_device=audio_output_device,
                available_audio_devices=available_audio_devices,
                available_midi_devices=available_midi_devices,
                timecode_audio_output_device=timecode_audio_output_device,
                timecode_midi_output_device=timecode_midi_output_device,
                timecode_mode=timecode_mode,
                timecode_fps=timecode_fps,
                timecode_mtc_fps=timecode_mtc_fps,
                timecode_mtc_idle_behavior=timecode_mtc_idle_behavior,
                timecode_sample_rate=timecode_sample_rate,
                timecode_bit_depth=timecode_bit_depth,
                timecode_timeline_mode=timecode_timeline_mode,
            ),
        )
        self._add_page(
            "Audio Preload",
            self._mono_icon("ram"),
            self._build_audio_preload_page(
                preload_audio_enabled=preload_audio_enabled,
                preload_current_page_audio=preload_current_page_audio,
                preload_audio_memory_limit_mb=preload_audio_memory_limit_mb,
                preload_memory_pressure_enabled=preload_memory_pressure_enabled,
                preload_pause_on_playback=preload_pause_on_playback,
                preload_total_ram_mb=preload_total_ram_mb,
                preload_ram_cap_mb=preload_ram_cap_mb,
            ),
        )
        self._add_page(
            "Talk",
            self._mono_icon("mic"),
            self._build_talk_page(
                talk_volume_level=talk_volume_level,
                talk_fade_sec=talk_fade_sec,
                talk_volume_mode=talk_volume_mode,
                talk_blink_button=talk_blink_button,
            ),
        )
        self._add_page(
            "Web Remote",
            self._mono_icon("wireless"),
            self._build_web_remote_page(
                web_remote_enabled=web_remote_enabled,
                web_remote_port=web_remote_port,
                web_remote_url=web_remote_url,
            ),
        )
        self.page_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        if not self.select_page(initial_page):
            self.page_list.setCurrentRow(0)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.restore_defaults_btn = buttons.addButton("Restore Defaults (This Page)", QDialogButtonBox.ResetRole)
        self.restore_defaults_btn.clicked.connect(self._restore_defaults_current_page)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)
        self._validate_hotkey_conflicts()
        self._validate_midi_conflicts()
        localize_widget_tree(self, self._ui_language)

    def _add_page(self, title: str, icon, page: QWidget) -> None:
        self.stack.addWidget(page)
        item = QListWidgetItem(icon, title)
        item.setData(Qt.UserRole, title.strip().lower())
        self.page_list.addItem(item)

    def select_page(self, title: Optional[str]) -> bool:
        needle = str(title or "").strip().lower()
        if not needle:
            return False
        for index in range(self.page_list.count()):
            item = self.page_list.item(index)
            if item is None:
                continue
            if item.text().strip().lower() == needle:
                self.page_list.setCurrentRow(index)
                return True
        return False

    def _mono_icon(self, kind: str) -> QIcon:
        size = 22
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor("#000000"))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if kind == "info":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.setBrush(QColor("#000000"))
            p.drawEllipse(QRectF(10, 6, 2, 2))
            p.drawRoundedRect(QRectF(10, 9, 2, 7), 1, 1)
        elif kind == "keyboard":
            p.drawRoundedRect(QRectF(2.5, 5, 17, 12), 2, 2)
            for y in [8, 11, 14]:
                p.drawLine(5, y, 17, y)
            p.drawLine(8, 8, 8, 14)
            p.drawLine(12, 8, 12, 14)
            p.drawLine(16, 8, 16, 14)
        elif kind == "display":
            p.drawRoundedRect(QRectF(3, 3, 16, 12), 1.5, 1.5)
            p.drawLine(8, 18, 14, 18)
            p.drawLine(11, 15, 11, 18)
        elif kind == "projector":
            p.drawRoundedRect(QRectF(3, 5, 16, 10), 2, 2)
            p.drawEllipse(QRectF(6, 8, 3, 3))
            p.drawLine(7, 15, 5, 19)
            p.drawLine(15, 15, 17, 19)
            p.drawLine(9, 19, 13, 19)
        elif kind == "clock":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.drawLine(11, 11, 11, 6)
            p.drawLine(11, 11, 15, 13)
        elif kind == "play":
            tri = QPolygonF([QPointF(7, 5), QPointF(17, 11), QPointF(7, 17)])
            p.drawPolygon(tri)
        elif kind == "speaker":
            body = QPolygonF([QPointF(4, 9), QPointF(8, 9), QPointF(12, 6), QPointF(12, 16), QPointF(8, 13), QPointF(4, 13)])
            p.drawPolygon(body)
            p.drawArc(QRectF(12, 7, 5, 8), -40 * 16, 80 * 16)
            p.drawArc(QRectF(12, 5, 8, 12), -40 * 16, 80 * 16)
        elif kind == "mic":
            p.drawRoundedRect(QRectF(8, 4, 6, 10), 3, 3)
            p.drawLine(11, 14, 11, 18)
            p.drawLine(8, 18, 14, 18)
            p.drawArc(QRectF(6, 10, 10, 8), 200 * 16, 140 * 16)
        elif kind == "wireless":
            p.drawEllipse(QRectF(10, 14, 2, 2))
            p.drawArc(QRectF(7, 11, 8, 8), 35 * 16, 110 * 16)
            p.drawArc(QRectF(5, 9, 12, 12), 35 * 16, 110 * 16)
            p.drawArc(QRectF(3, 7, 16, 16), 35 * 16, 110 * 16)
        elif kind == "ram":
            p.drawRoundedRect(QRectF(4, 6, 14, 10), 1.5, 1.5)
            p.drawLine(6, 9, 16, 9)
            p.drawLine(6, 12, 16, 12)
            for x in [5, 8, 11, 14, 17]:
                p.drawLine(x, 4, x, 6)
                p.drawLine(x, 16, x, 18)
        elif kind == "rack":
            p.drawRoundedRect(QRectF(3, 4, 16, 14), 1.5, 1.5)
            p.drawLine(6, 8, 16, 8)
            p.drawLine(6, 12, 16, 12)
            p.drawLine(6, 16, 16, 16)
            p.drawEllipse(QRectF(4, 7, 1.5, 1.5))
            p.drawEllipse(QRectF(4, 11, 1.5, 1.5))
            p.drawEllipse(QRectF(4, 15, 1.5, 1.5))
        elif kind == "earth":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.drawArc(QRectF(5, 3, 12, 16), 90 * 16, 180 * 16)
            p.drawArc(QRectF(5, 3, 12, 16), 270 * 16, 180 * 16)
            p.drawLine(3, 11, 19, 11)
            p.drawArc(QRectF(3, 6, 16, 10), 0, 180 * 16)
            p.drawArc(QRectF(3, 6, 16, 10), 180 * 16, 180 * 16)
        elif kind == "piano":
            p.drawRoundedRect(QRectF(3, 4, 16, 14), 1.5, 1.5)
            p.drawLine(6, 4, 6, 18)
            p.drawLine(10, 4, 10, 18)
            p.drawLine(14, 4, 14, 18)
            p.setBrush(QColor("#000000"))
            p.drawRect(QRectF(5, 4, 2, 7))
            p.drawRect(QRectF(9, 4, 2, 7))
            p.drawRect(QRectF(13, 4, 2, 7))

        p.end()
        return QIcon(pix)

    def _build_general_page(
        self,
        title_char_limit: int,
        show_file_notifications: bool,
        log_file_enabled: bool,
        reset_all_on_startup: bool,
        click_playing_action: str,
        search_double_click_action: str,
        set_file_encoding: str,
        main_progress_display_mode: str,
        main_progress_show_text: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.title_limit_spin = QSpinBox()
        self.title_limit_spin.setRange(8, 80)
        self.title_limit_spin.setValue(title_char_limit)
        form.addRow("Button Title Max Chars:", self.title_limit_spin)

        self.log_file_checkbox = QCheckBox("Enable playback log file (SportsSoundsProLog.txt)")
        self.log_file_checkbox.setChecked(log_file_enabled)
        form.addRow("Log File:", self.log_file_checkbox)

        self.reset_on_startup_checkbox = QCheckBox("Reset ALL on Start-up")
        self.reset_on_startup_checkbox.setChecked(reset_all_on_startup)
        form.addRow("Startup:", self.reset_on_startup_checkbox)

        encoding_group = QGroupBox(".set Save Encoding")
        encoding_layout = QVBoxLayout(encoding_group)
        self.set_file_encoding_utf8_radio = QRadioButton("UTF-8")
        self.set_file_encoding_gbk_radio = QRadioButton("GBK (Chinese)")
        if str(set_file_encoding).strip().lower() == "gbk":
            self.set_file_encoding_gbk_radio.setChecked(True)
        else:
            self.set_file_encoding_utf8_radio.setChecked(True)
        encoding_layout.addWidget(self.set_file_encoding_utf8_radio)
        encoding_layout.addWidget(self.set_file_encoding_gbk_radio)
        encoding_note = QLabel(
            "GBK note: if song title, notes, file path, etc include Chinese characters, "
            "GBK has better compatibility with original SSP."
        )
        encoding_note.setWordWrap(True)
        encoding_layout.addWidget(encoding_note)
        layout.addWidget(encoding_group)
        layout.addLayout(form)

        click_group = QGroupBox("Clicking on a Playing Sound will:")
        click_layout = QVBoxLayout(click_group)
        self.playing_click_play_again_radio = QRadioButton("Play It Again")
        self.playing_click_stop_radio = QRadioButton("Stop It")
        if click_playing_action == "stop_it":
            self.playing_click_stop_radio.setChecked(True)
        else:
            self.playing_click_play_again_radio.setChecked(True)
        click_layout.addWidget(self.playing_click_play_again_radio)
        click_layout.addWidget(self.playing_click_stop_radio)
        layout.addWidget(click_group)

        search_group = QGroupBox("Search Double-Click will:")
        search_layout = QVBoxLayout(search_group)
        self.search_dbl_find_radio = QRadioButton("Find (Highlight)")
        self.search_dbl_play_radio = QRadioButton("Play and Highlight")
        if search_double_click_action == "play_highlight":
            self.search_dbl_play_radio.setChecked(True)
        else:
            self.search_dbl_find_radio.setChecked(True)
        search_layout.addWidget(self.search_dbl_find_radio)
        search_layout.addWidget(self.search_dbl_play_radio)
        layout.addWidget(search_group)

        transport_group = QGroupBox("Main Transport Display")
        transport_layout = QVBoxLayout(transport_group)
        self.main_progress_display_progress_bar_radio = QRadioButton("Display Progress Bar")
        self.main_progress_display_waveform_radio = QRadioButton("Display Waveform")
        mode_token = str(main_progress_display_mode or "").strip().lower()
        if mode_token not in {"progress_bar", "waveform"}:
            mode_token = "progress_bar"
        if mode_token == "waveform":
            self.main_progress_display_waveform_radio.setChecked(True)
        else:
            self.main_progress_display_progress_bar_radio.setChecked(True)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.main_progress_display_progress_bar_radio)
        mode_row.addWidget(self.main_progress_display_waveform_radio)
        mode_row.addStretch(1)
        transport_layout.addLayout(mode_row)
        waveform_note = QLabel(
            "If Main Transport uses Waveform display, it is recommended to enable Audio Preload for better performance."
        )
        waveform_note.setWordWrap(True)
        transport_layout.addWidget(waveform_note)
        self.main_progress_show_text_checkbox = QCheckBox("Show transport text on progress display")
        self.main_progress_show_text_checkbox.setChecked(bool(main_progress_show_text))
        transport_layout.addWidget(self.main_progress_show_text_checkbox)
        layout.addWidget(transport_group)
        layout.addStretch(1)
        return page

    def _build_language_page(self, ui_language: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.ui_language_combo = QComboBox()
        self.ui_language_combo.addItem("English", "en")
        self.ui_language_combo.addItem("Chinese (Simplified)", "zh_cn")
        index = self.ui_language_combo.findData(normalize_language(ui_language))
        self.ui_language_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("UI Language", self.ui_language_combo)
        layout.addLayout(form)
        note = QLabel("App language (requires reopen dialogs/windows to fully refresh).")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _build_hotkey_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        tabs = QTabWidget()
        tabs.addTab(self._build_system_hotkey_tab(), "System Hotkey")
        tabs.addTab(self._build_quick_action_tab(), "Quick Action Key")
        tabs.addTab(self._build_sound_button_hotkey_tab(), "Sound Button Hot Key")
        layout.addWidget(tabs, 1)
        self.hotkey_warning_label = QLabel("")
        self.hotkey_warning_label.setWordWrap(True)
        self.hotkey_warning_label.setStyleSheet("color:#B00020; font-weight:bold;")
        self.hotkey_warning_label.setVisible(False)
        layout.addWidget(self.hotkey_warning_label)
        note = QLabel("Each operation supports two hotkeys. You can clear either key.")
        note.setWordWrap(True)
        layout.addWidget(note)
        return page

    def _build_midi_control_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        tabs = QTabWidget()
        tabs.addTab(self._build_midi_settings_tab(), "Midi Setting")
        tabs.addTab(self._build_midi_system_hotkey_tab(), "System Hotkey")
        tabs.addTab(self._build_midi_system_rotary_tab(), "System Rotary")
        tabs.addTab(self._build_midi_quick_action_tab(), "Quick Action Key")
        tabs.addTab(self._build_midi_sound_button_hotkey_tab(), "Sound Button Hot Key")
        layout.addWidget(tabs, 1)
        self._midi_warning_label = QLabel("")
        self._midi_warning_label.setWordWrap(True)
        self._midi_warning_label.setStyleSheet("color:#B00020; font-weight:bold;")
        self._midi_warning_label.setVisible(False)
        layout.addWidget(self._midi_warning_label)
        return page

    def _build_midi_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        hint = QLabel("Select one or more MIDI input devices. pySSP will listen on all selected devices.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.midi_input_list = QListWidget()
        self.midi_input_list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.midi_input_list, 1)
        button_row = QHBoxLayout()
        self.midi_refresh_btn = QPushButton("Refresh")
        self.midi_refresh_btn.clicked.connect(lambda: self._refresh_midi_input_devices(force_refresh=True))
        button_row.addWidget(self.midi_refresh_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        mtc_group = QGroupBox("MIDI Timecode (MTC)")
        mtc_group.setEnabled(False)
        mtc_layout = QVBoxLayout(mtc_group)
        mtc_note = QLabel("Configure MTC output in Audio Device / Timecode.")
        mtc_note.setWordWrap(True)
        mtc_layout.addWidget(mtc_note)
        layout.addWidget(mtc_group)
        self._refresh_midi_input_devices()
        return page

    def _build_midi_system_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for key, label in self._HOTKEY_ROWS:
            self._add_midi_row(form, key, label)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_midi_system_rotary_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.midi_rotary_enabled_checkbox = QCheckBox("Enable System Rotary MIDI Control")
        self.midi_rotary_enabled_checkbox.setChecked(self._midi_rotary_enabled)
        layout.addWidget(self.midi_rotary_enabled_checkbox)

        form = QFormLayout()
        self.midi_rotary_group_edit = MidiCaptureEdit()
        self.midi_rotary_group_edit.setBinding(self._midi_rotary_group_binding)
        form.addRow("Group Rotary:", self._build_midi_learn_row(self.midi_rotary_group_edit, rotary=True))
        self.midi_rotary_group_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_group_invert_checkbox.setChecked(self._midi_rotary_group_invert)
        self.midi_rotary_group_sensitivity_spin = QSpinBox()
        self.midi_rotary_group_sensitivity_spin.setRange(1, 20)
        self.midi_rotary_group_sensitivity_spin.setValue(self._midi_rotary_group_sensitivity)
        form.addRow(
            "Group Options:",
            self._build_rotary_option_row(self.midi_rotary_group_invert_checkbox, self.midi_rotary_group_sensitivity_spin),
        )

        self.midi_rotary_page_edit = MidiCaptureEdit()
        self.midi_rotary_page_edit.setBinding(self._midi_rotary_page_binding)
        form.addRow("Page Rotary:", self._build_midi_learn_row(self.midi_rotary_page_edit, rotary=True))
        self.midi_rotary_page_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_page_invert_checkbox.setChecked(self._midi_rotary_page_invert)
        self.midi_rotary_page_sensitivity_spin = QSpinBox()
        self.midi_rotary_page_sensitivity_spin.setRange(1, 20)
        self.midi_rotary_page_sensitivity_spin.setValue(self._midi_rotary_page_sensitivity)
        form.addRow(
            "Page Options:",
            self._build_rotary_option_row(self.midi_rotary_page_invert_checkbox, self.midi_rotary_page_sensitivity_spin),
        )

        self.midi_rotary_sound_button_edit = MidiCaptureEdit()
        self.midi_rotary_sound_button_edit.setBinding(self._midi_rotary_sound_button_binding)
        form.addRow("Sound Button Rotary:", self._build_midi_learn_row(self.midi_rotary_sound_button_edit, rotary=True))
        self.midi_rotary_sound_button_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_sound_button_invert_checkbox.setChecked(self._midi_rotary_sound_button_invert)
        self.midi_rotary_sound_button_sensitivity_spin = QSpinBox()
        self.midi_rotary_sound_button_sensitivity_spin.setRange(1, 20)
        self.midi_rotary_sound_button_sensitivity_spin.setValue(self._midi_rotary_sound_button_sensitivity)
        form.addRow(
            "Sound Button Options:",
            self._build_rotary_option_row(
                self.midi_rotary_sound_button_invert_checkbox,
                self.midi_rotary_sound_button_sensitivity_spin,
            ),
        )

        self.midi_rotary_volume_edit = MidiCaptureEdit()
        self.midi_rotary_volume_edit.setBinding(self._midi_rotary_volume_binding)
        form.addRow("Volume Control:", self._build_midi_learn_row(self.midi_rotary_volume_edit, rotary=True))
        self.midi_rotary_volume_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_volume_invert_checkbox.setChecked(self._midi_rotary_volume_invert)
        form.addRow("Volume Options:", self._build_rotary_invert_row(self.midi_rotary_volume_invert_checkbox))

        self.midi_rotary_jog_edit = MidiCaptureEdit()
        self.midi_rotary_jog_edit.setBinding(self._midi_rotary_jog_binding)
        form.addRow("Jog Control:", self._build_midi_learn_row(self.midi_rotary_jog_edit, rotary=True))
        self.midi_rotary_jog_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_jog_invert_checkbox.setChecked(self._midi_rotary_jog_invert)
        form.addRow("Jog Options:", self._build_rotary_invert_row(self.midi_rotary_jog_invert_checkbox))

        self.midi_rotary_volume_mode_combo = QComboBox()
        self.midi_rotary_volume_mode_combo.addItem("Relative (rotary encoder)", "relative")
        self.midi_rotary_volume_mode_combo.addItem("Absolute (slider/fader)", "absolute")
        self._set_combo_data_or_default(self.midi_rotary_volume_mode_combo, self._midi_rotary_volume_mode, "relative")
        form.addRow("Volume Mode:", self.midi_rotary_volume_mode_combo)

        self.midi_rotary_volume_step_spin = QSpinBox()
        self.midi_rotary_volume_step_spin.setRange(1, 20)
        self.midi_rotary_volume_step_spin.setValue(self._midi_rotary_volume_step)
        form.addRow("Volume Relative Step:", self.midi_rotary_volume_step_spin)

        self.midi_rotary_jog_step_spin = QSpinBox()
        self.midi_rotary_jog_step_spin.setRange(10, 5000)
        self.midi_rotary_jog_step_spin.setSuffix(" ms")
        self.midi_rotary_jog_step_spin.setValue(self._midi_rotary_jog_step_ms)
        form.addRow("Jog Relative Step:", self.midi_rotary_jog_step_spin)

        layout.addLayout(form)
        note = QLabel("Rotary learns Control Change (CC) by control number. For direction, pySSP uses CC value.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _build_rotary_invert_row(self, invert_checkbox: QCheckBox) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(invert_checkbox)
        row_layout.addStretch(1)
        return row

    def _build_rotary_option_row(self, invert_checkbox: QCheckBox, sensitivity_spin: QSpinBox) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(invert_checkbox)
        row_layout.addSpacing(8)
        row_layout.addWidget(QLabel("Sensitivity:"))
        row_layout.addWidget(sensitivity_spin)
        row_layout.addStretch(1)
        return row

    def _build_midi_learn_row(self, edit: MidiCaptureEdit, rotary: bool = False) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        learn_btn = QPushButton("Learn")
        clear_btn = QPushButton("Clear")
        learn_btn.setFixedWidth(62)
        clear_btn.setFixedWidth(56)
        if rotary:
            learn_btn.clicked.connect(lambda _=False, e=edit: self._start_midi_rotary_learning(e))
        else:
            learn_btn.clicked.connect(lambda _=False, e=edit: self._start_midi_learning(e))
        clear_btn.clicked.connect(lambda _=False, e=edit: e.setBinding(""))
        row_layout.addWidget(edit, 1)
        row_layout.addWidget(learn_btn)
        row_layout.addWidget(clear_btn)
        return row

    def _build_midi_quick_action_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.midi_quick_action_enabled_checkbox = QCheckBox("Enable MIDI Quick Action")
        self.midi_quick_action_enabled_checkbox.setChecked(self._midi_quick_action_enabled)
        self.midi_quick_action_enabled_checkbox.toggled.connect(self._validate_midi_conflicts)
        layout.addWidget(self.midi_quick_action_enabled_checkbox)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for i in range(48):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            edit = MidiCaptureEdit()
            edit.setBinding(self._midi_quick_action_bindings[i])
            edit.textChanged.connect(self._validate_midi_conflicts)
            learn_btn = QPushButton("Learn")
            clear_btn = QPushButton("Clear")
            learn_btn.setFixedWidth(62)
            clear_btn.setFixedWidth(56)
            learn_btn.clicked.connect(lambda _=False, e=edit: self._start_midi_learning(e))
            clear_btn.clicked.connect(lambda _=False, e=edit: e.setBinding(""))
            row_layout.addWidget(edit, 1)
            row_layout.addWidget(learn_btn)
            row_layout.addWidget(clear_btn)
            self._midi_quick_action_edits.append(edit)
            form.addRow(f"Button {i + 1}:", row)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_vst_plugin_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.vst_enabled_checkbox = QCheckBox("Enable VST Plugin")
        self.vst_enabled_checkbox.setChecked(bool(self._vst_enabled))
        layout.addWidget(self.vst_enabled_checkbox)

        if not self._vst_supported:
            not_supported = QLabel("VST plugin support is available on Windows only.")
            not_supported.setWordWrap(True)
            layout.addWidget(not_supported)

        dir_group = QGroupBox("VST Directories")
        dir_layout = QVBoxLayout(dir_group)
        self.vst_dir_list = QListWidget()
        self.vst_dir_list.setSelectionMode(QAbstractItemView.SingleSelection)
        dir_layout.addWidget(self.vst_dir_list, 1)
        dir_btn_row = QHBoxLayout()
        self.vst_dir_add_btn = QPushButton("Add Directory")
        self.vst_dir_add_btn.clicked.connect(self._add_vst_directory)
        self.vst_dir_remove_btn = QPushButton("Remove Selected")
        self.vst_dir_remove_btn.clicked.connect(self._remove_vst_directory)
        dir_btn_row.addWidget(self.vst_dir_add_btn)
        dir_btn_row.addWidget(self.vst_dir_remove_btn)
        dir_btn_row.addStretch(1)
        dir_layout.addLayout(dir_btn_row)
        layout.addWidget(dir_group, 1)

        plugins_group = QGroupBox("Plugins")
        plugins_layout = QVBoxLayout(plugins_group)
        plugin_btn_row = QHBoxLayout()
        self.vst_scan_btn = QPushButton("Scan")
        self.vst_scan_btn.clicked.connect(self._scan_vst_plugins_clicked)
        plugin_btn_row.addWidget(self.vst_scan_btn)
        plugin_btn_row.addStretch(1)
        plugins_layout.addLayout(plugin_btn_row)

        self.vst_plugin_list = QListWidget()
        self.vst_plugin_list.setSelectionMode(QAbstractItemView.SingleSelection)
        plugins_layout.addWidget(self.vst_plugin_list, 1)
        self.vst_scan_status = QLabel("")
        self.vst_scan_status.setWordWrap(True)
        plugins_layout.addWidget(self.vst_scan_status)
        layout.addWidget(plugins_group, 2)

        self._refresh_vst_directory_list()
        self._refresh_vst_plugin_list()
        self._sync_vst_controls_enabled()
        layout.addStretch(1)
        return page

    def _sync_vst_controls_enabled(self) -> None:
        enabled = bool(self._vst_supported)
        self.vst_enabled_checkbox.setEnabled(enabled)
        self.vst_dir_add_btn.setEnabled(enabled)
        self.vst_dir_remove_btn.setEnabled(enabled)
        self.vst_scan_btn.setEnabled(enabled and (not self._vst_scan_in_progress))
        self.vst_plugin_list.setEnabled(enabled)

    def _refresh_vst_directory_list(self) -> None:
        self.vst_dir_list.clear()
        for directory in self._vst_directories:
            self.vst_dir_list.addItem(directory)

    def _refresh_vst_plugin_list(self) -> None:
        try:
            self.vst_plugin_list.itemChanged.disconnect(self._on_vst_plugin_toggled)
        except Exception:
            pass
        self.vst_plugin_list.clear()
        enabled_set = {str(v).strip() for v in self._vst_enabled_plugins}
        for plugin_path in self._vst_known_plugins:
            item = QListWidgetItem(plugin_display_name(plugin_path) or plugin_path)
            item.setData(Qt.UserRole, plugin_path)
            item.setToolTip(plugin_path)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if plugin_path in enabled_set else Qt.Unchecked)
            self.vst_plugin_list.addItem(item)
        self.vst_plugin_list.itemChanged.connect(self._on_vst_plugin_toggled)
        self.vst_scan_status.setText(f"Detected plugins: {len(self._vst_known_plugins)}")

    def _add_vst_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select VST Directory")
        if not selected:
            return
        normalized = str(selected).strip()
        if not normalized:
            return
        current = effective_vst_directories(self._vst_directories + [normalized])
        self._vst_directories = current
        self._refresh_vst_directory_list()

    def _remove_vst_directory(self) -> None:
        row = self.vst_dir_list.currentRow()
        if row < 0:
            return
        if row < len(self._vst_directories):
            self._vst_directories.pop(row)
            self._refresh_vst_directory_list()

    def _scan_vst_plugins_clicked(self) -> None:
        if not self._vst_supported:
            self.vst_scan_status.setText("VST scanning is available on Windows only.")
            return
        if self._vst_scan_in_progress:
            return
        self._vst_scan_in_progress = True
        self.vst_scan_status.setText("Scanning plugins... pySSP remains responsive.")
        self._sync_vst_controls_enabled()

        directories = list(self._vst_directories)

        def _worker() -> None:
            try:
                scanned = scan_vst_plugins(directories)
            except Exception:
                scanned = []
            self.vstScanFinished.emit(scanned)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_vst_scan_finished(self, scanned: object) -> None:
        self._vst_scan_in_progress = False
        refs = [str(v).strip() for v in list(scanned or []) if str(v).strip()]
        self._vst_known_plugins = refs
        known = set(self._vst_known_plugins)
        self._vst_enabled_plugins = {p for p in self._vst_enabled_plugins if p in known}
        self._vst_chain = [p for p in self._vst_chain if p in known]
        self._vst_plugin_state = {
            p: dict(v) for p, v in self._vst_plugin_state.items() if p in known and isinstance(v, dict)
        }
        self._refresh_vst_plugin_list()
        self._sync_vst_controls_enabled()

    def _on_vst_plugin_toggled(self, _item: QListWidgetItem) -> None:
        enabled: set[str] = set()
        for index in range(self.vst_plugin_list.count()):
            item = self.vst_plugin_list.item(index)
            if item is None:
                continue
            plugin_path = str(item.data(Qt.UserRole) or "").strip()
            if not plugin_path:
                continue
            if item.checkState() == Qt.Checked:
                enabled.add(plugin_path)
        self._vst_enabled_plugins = enabled

    def _build_midi_sound_button_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.midi_sound_button_hotkey_enabled_checkbox = QCheckBox("Enable Sound Button MIDI Hot Key")
        self.midi_sound_button_hotkey_enabled_checkbox.setChecked(self._midi_sound_button_hotkey_enabled)
        layout.addWidget(self.midi_sound_button_hotkey_enabled_checkbox)

        prio_group = QGroupBox("Priority")
        prio_layout = QVBoxLayout(prio_group)
        self.midi_sound_hotkey_priority_sound_first_radio = QRadioButton("Sound Button MIDI Hot Key has highest priority")
        self.midi_sound_hotkey_priority_system_first_radio = QRadioButton(
            "System MIDI Hotkey and Quick Action have highest priority"
        )
        if self._midi_sound_button_hotkey_priority == "sound_button_first":
            self.midi_sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.midi_sound_hotkey_priority_system_first_radio.setChecked(True)
        prio_layout.addWidget(self.midi_sound_hotkey_priority_sound_first_radio)
        prio_layout.addWidget(self.midi_sound_hotkey_priority_system_first_radio)
        layout.addWidget(prio_group)

        self.midi_sound_button_go_to_playing_checkbox = QCheckBox("Go To Playing after trigger")
        self.midi_sound_button_go_to_playing_checkbox.setChecked(self._midi_sound_button_hotkey_go_to_playing)
        layout.addWidget(self.midi_sound_button_go_to_playing_checkbox)
        note = QLabel("Assign per-button MIDI hotkeys in Edit Sound Button.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _add_midi_row(self, form: QFormLayout, key: str, label: str) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        edit1 = MidiCaptureEdit()
        edit2 = MidiCaptureEdit()
        v1, v2 = self._midi_hotkeys.get(key, ("", ""))
        edit1.setBinding(v1)
        edit2.setBinding(v2)
        learn1 = QPushButton("Learn")
        clear1 = QPushButton("Clear")
        learn2 = QPushButton("Learn")
        clear2 = QPushButton("Clear")
        for btn in (learn1, clear1, learn2, clear2):
            btn.setFixedWidth(56 if btn.text() == "Clear" else 62)
        learn1.clicked.connect(lambda _=False, e=edit1: self._start_midi_learning(e))
        clear1.clicked.connect(lambda _=False, e=edit1: e.setBinding(""))
        learn2.clicked.connect(lambda _=False, e=edit2: self._start_midi_learning(e))
        clear2.clicked.connect(lambda _=False, e=edit2: e.setBinding(""))
        edit1.textChanged.connect(self._validate_midi_conflicts)
        edit2.textChanged.connect(self._validate_midi_conflicts)
        row_layout.addWidget(edit1, 1)
        row_layout.addWidget(learn1)
        row_layout.addWidget(clear1)
        row_layout.addWidget(edit2, 1)
        row_layout.addWidget(learn2)
        row_layout.addWidget(clear2)
        self._midi_hotkey_edits[key] = (edit1, edit2)
        form.addRow(f"{label}:", row)

    def _build_system_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for key, label in self._HOTKEY_ROWS:
            self._add_hotkey_row(form, key, label)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_quick_action_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.quick_action_enabled_checkbox = QCheckBox("Enable Quick Action Key (assign broadcast short key)")
        self.quick_action_enabled_checkbox.setChecked(self._quick_action_enabled)
        self.quick_action_enabled_checkbox.toggled.connect(self._validate_hotkey_conflicts)
        layout.addWidget(self.quick_action_enabled_checkbox)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for i in range(48):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            edit = HotkeyCaptureEdit()
            edit.setHotkey(self._quick_action_keys[i])
            edit.textChanged.connect(self._validate_hotkey_conflicts)
            clear_btn = QPushButton("Clear")
            clear_btn.setFixedWidth(56)
            clear_btn.clicked.connect(lambda _=False, e=edit: e.setHotkey(""))
            row_layout.addWidget(edit)
            row_layout.addWidget(clear_btn)
            self._quick_action_edits.append(edit)
            form.addRow(f"Button {i + 1}:", row)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_sound_button_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.sound_button_hotkey_enabled_checkbox = QCheckBox("Enable Sound Button Hot Key")
        self.sound_button_hotkey_enabled_checkbox.setChecked(self._sound_button_hotkey_enabled)
        self.sound_button_hotkey_enabled_checkbox.toggled.connect(self._validate_hotkey_conflicts)
        layout.addWidget(self.sound_button_hotkey_enabled_checkbox)

        prio_group = QGroupBox("Priority")
        prio_layout = QVBoxLayout(prio_group)
        self.sound_hotkey_priority_sound_first_radio = QRadioButton("Sound Button Hot Key has highest priority")
        self.sound_hotkey_priority_system_first_radio = QRadioButton(
            "System Hotkey and Quick Action Key have highest priority"
        )
        if self._sound_button_hotkey_priority == "sound_button_first":
            self.sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.sound_hotkey_priority_system_first_radio.setChecked(True)
        prio_layout.addWidget(self.sound_hotkey_priority_sound_first_radio)
        prio_layout.addWidget(self.sound_hotkey_priority_system_first_radio)
        layout.addWidget(prio_group)

        self.sound_button_go_to_playing_checkbox = QCheckBox("Go To Playing after trigger")
        self.sound_button_go_to_playing_checkbox.setChecked(self._sound_button_hotkey_go_to_playing)
        layout.addWidget(self.sound_button_go_to_playing_checkbox)
        layout.addStretch(1)
        return page

    def _add_hotkey_row(self, form: QFormLayout, key: str, label: str) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        edit1 = HotkeyCaptureEdit()
        edit2 = HotkeyCaptureEdit()
        clear1 = QPushButton("Clear")
        clear2 = QPushButton("Clear")
        clear1.setFixedWidth(56)
        clear2.setFixedWidth(56)
        v1, v2 = self._hotkeys.get(key, ("", ""))
        edit1.setHotkey(v1)
        edit2.setHotkey(v2)
        clear1.clicked.connect(lambda _=False, e=edit1: e.setHotkey(""))
        clear2.clicked.connect(lambda _=False, e=edit2: e.setHotkey(""))
        edit1.textChanged.connect(self._validate_hotkey_conflicts)
        edit2.textChanged.connect(self._validate_hotkey_conflicts)
        row_layout.addWidget(edit1)
        row_layout.addWidget(clear1)
        row_layout.addWidget(edit2)
        row_layout.addWidget(clear2)
        self._hotkey_edits[key] = (edit1, edit2)
        form.addRow(f"{label}:", row)

    def _build_color_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        sound_group = QGroupBox("Sound Button States")
        sound_form = QFormLayout(sound_group)
        self._add_state_color_row(sound_form, "playing", "Playing")
        self._add_state_color_row(sound_form, "played", "Played")
        self._add_state_color_row(sound_form, "unplayed", "Unplayed")
        self._add_state_color_row(sound_form, "highlight", "Highlight")
        self._add_state_color_row(sound_form, "lock", "Lock")
        self._add_state_color_row(sound_form, "error", "Error")
        self._add_state_color_row(sound_form, "place_marker", "Place Marker")
        self._add_state_color_row(sound_form, "empty", "Empty")
        self._add_state_color_row(sound_form, "copied_to_cue", "Copied To Cue")
        layout.addWidget(sound_group)

        indicator_group = QGroupBox("Indicators")
        indicator_form = QFormLayout(indicator_group)
        self._add_state_color_row(indicator_form, "cue_indicator", "Cue Indicator")
        self._add_state_color_row(indicator_form, "volume_indicator", "Volume Indicator")
        self._add_state_color_row(indicator_form, "midi_indicator", "MIDI Indicator")
        self.sound_text_color_btn = QPushButton()
        self.sound_text_color_btn.clicked.connect(self._pick_sound_text_color)
        self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)
        indicator_form.addRow("Sound Button Text:", self.sound_text_color_btn)
        layout.addWidget(indicator_group)

        group_group = QGroupBox("Group Buttons")
        group_form = QFormLayout(group_group)
        self.active_color_btn = QPushButton()
        self.active_color_btn.clicked.connect(self._pick_active_color)
        self._refresh_color_button(self.active_color_btn, self.active_group_color)
        group_form.addRow("Active Group:", self.active_color_btn)
        self.inactive_color_btn = QPushButton()
        self.inactive_color_btn.clicked.connect(self._pick_inactive_color)
        self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)
        group_form.addRow("Inactive Group:", self.inactive_color_btn)
        layout.addWidget(group_group)

        layout.addStretch(1)
        return page

    def _add_state_color_row(self, form: QFormLayout, key: str, label: str) -> None:
        value = self.state_colors.get(key, "#FFFFFF")
        btn = QPushButton()
        self._refresh_color_button(btn, value)
        btn.clicked.connect(lambda _=None, k=key, b=btn, t=label: self._pick_state_color(k, b, t))
        self._state_color_buttons[key] = btn
        form.addRow(f"{label}:", btn)

    def _build_delay_page(
        self,
        fade_in_sec: float,
        cross_fade_sec: float,
        fade_out_sec: float,
        fade_on_quick_action_hotkey: bool,
        fade_on_sound_button_hotkey: bool,
        fade_on_pause: bool,
        fade_on_resume: bool,
        fade_on_stop: bool,
        fade_out_when_done_playing: bool,
        fade_out_end_lead_sec: float,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        trigger_group = QGroupBox("Fader Trigger")
        trigger_layout = QVBoxLayout(trigger_group)

        self.fade_on_quick_action_checkbox = QCheckBox("Allow fader on Quick Action key active")
        self.fade_on_quick_action_checkbox.setChecked(bool(fade_on_quick_action_hotkey))
        trigger_layout.addWidget(self.fade_on_quick_action_checkbox)

        self.fade_on_sound_hotkey_checkbox = QCheckBox("Allow fader on Sound Button hot key active")
        self.fade_on_sound_hotkey_checkbox.setChecked(bool(fade_on_sound_button_hotkey))
        trigger_layout.addWidget(self.fade_on_sound_hotkey_checkbox)

        self.fade_on_pause_checkbox = QCheckBox("Fade on Pause")
        self.fade_on_pause_checkbox.setChecked(bool(fade_on_pause))
        trigger_layout.addWidget(self.fade_on_pause_checkbox)

        self.fade_on_resume_checkbox = QCheckBox("Fade on Resume (when paused)")
        self.fade_on_resume_checkbox.setChecked(bool(fade_on_resume))
        trigger_layout.addWidget(self.fade_on_resume_checkbox)

        self.fade_on_stop_checkbox = QCheckBox("Fade on Stop")
        self.fade_on_stop_checkbox.setChecked(bool(fade_on_stop))
        trigger_layout.addWidget(self.fade_on_stop_checkbox)

        self.fade_on_stop_note = QLabel("During fade, click Stop again to force stop (skip fade).")
        self.fade_on_stop_note.setWordWrap(True)
        self.fade_on_stop_note.setStyleSheet("color:#666666;")
        trigger_layout.addWidget(self.fade_on_stop_note)
        self.fade_dependency_note = QLabel("Note: These options work only when the matching Fade In/Fade Out control is active.")
        self.fade_dependency_note.setWordWrap(True)
        self.fade_dependency_note.setStyleSheet("color:#666666;")
        trigger_layout.addWidget(self.fade_dependency_note)
        layout.addWidget(trigger_group)

        timing_group = QGroupBox("Fade Timing")
        timing_form = QFormLayout(timing_group)

        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0.0, 20.0)
        self.fade_in_spin.setSingleStep(0.1)
        self.fade_in_spin.setDecimals(1)
        self.fade_in_spin.setValue(fade_in_sec)
        timing_form.addRow("Fade In Seconds:", self.fade_in_spin)

        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0.0, 20.0)
        self.fade_out_spin.setSingleStep(0.1)
        self.fade_out_spin.setDecimals(1)
        self.fade_out_spin.setValue(fade_out_sec)
        timing_form.addRow("Fade Out Seconds:", self.fade_out_spin)

        self.fade_out_when_done_checkbox = QCheckBox("Fade out when done playing")
        self.fade_out_when_done_checkbox.setChecked(bool(fade_out_when_done_playing))
        timing_form.addRow("", self.fade_out_when_done_checkbox)

        self.fade_out_end_lead_spin = QDoubleSpinBox()
        self.fade_out_end_lead_spin.setRange(0.0, 30.0)
        self.fade_out_end_lead_spin.setSingleStep(0.1)
        self.fade_out_end_lead_spin.setDecimals(1)
        self.fade_out_end_lead_spin.setValue(float(fade_out_end_lead_sec))
        timing_form.addRow("Length from end to start Fade Out:", self.fade_out_end_lead_spin)

        self.cross_fade_spin = QDoubleSpinBox()
        self.cross_fade_spin.setRange(0.0, 20.0)
        self.cross_fade_spin.setSingleStep(0.1)
        self.cross_fade_spin.setDecimals(1)
        self.cross_fade_spin.setValue(cross_fade_sec)
        timing_form.addRow("Cross Fade Seconds:", self.cross_fade_spin)
        layout.addWidget(timing_group)
        layout.addStretch(1)

        self.fade_out_when_done_checkbox.toggled.connect(self._sync_fade_out_end_lead_enabled)
        self._sync_fade_out_end_lead_enabled()
        return page

    def _sync_fade_out_end_lead_enabled(self) -> None:
        self.fade_out_end_lead_spin.setEnabled(self.fade_out_when_done_checkbox.isChecked())

    def _build_playback_page(
        self,
        max_multi_play_songs: int,
        multi_play_limit_action: str,
        playlist_play_mode: str,
        rapid_fire_play_mode: str,
        next_play_mode: str,
        playlist_loop_mode: str,
        candidate_error_action: str,
        main_transport_timeline_mode: str,
        main_jog_outside_cue_action: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.max_multi_play_spin = QSpinBox()
        self.max_multi_play_spin.setRange(1, 32)
        self.max_multi_play_spin.setValue(max(1, min(32, int(max_multi_play_songs))))
        form.addRow("Max Multi-Play Songs:", self.max_multi_play_spin)
        layout.addLayout(form)

        limit_group = QGroupBox("When max songs is reached during Multi-Play:")
        limit_layout = QVBoxLayout(limit_group)
        self.multi_play_disallow_radio = QRadioButton("Disallow more play")
        self.multi_play_stop_oldest_radio = QRadioButton("Stop the oldest")
        if multi_play_limit_action == "disallow_more_play":
            self.multi_play_disallow_radio.setChecked(True)
        else:
            self.multi_play_stop_oldest_radio.setChecked(True)
        limit_layout.addWidget(self.multi_play_disallow_radio)
        limit_layout.addWidget(self.multi_play_stop_oldest_radio)
        layout.addWidget(limit_group)

        mode_matrix_group = QGroupBox("Playback Candidate Rules:")
        mode_matrix_layout = QGridLayout(mode_matrix_group)
        mode_matrix_layout.addWidget(QLabel("Control"), 0, 0)
        mode_matrix_layout.addWidget(QLabel("Play unplayed only"), 0, 1)
        mode_matrix_layout.addWidget(QLabel("Play any (ignore red) available"), 0, 2)

        self.playlist_mode_unplayed_radio = QRadioButton("")
        self.playlist_mode_any_radio = QRadioButton("")
        self.playlist_mode_group = QButtonGroup(self)
        self.playlist_mode_group.addButton(self.playlist_mode_unplayed_radio)
        self.playlist_mode_group.addButton(self.playlist_mode_any_radio)
        if playlist_play_mode == "any_available":
            self.playlist_mode_any_radio.setChecked(True)
        else:
            self.playlist_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.playlist_mode_unplayed_radio, 1, 1)
        mode_matrix_layout.addWidget(self.playlist_mode_any_radio, 1, 2)

        self.rapid_fire_mode_unplayed_radio = QRadioButton("")
        self.rapid_fire_mode_any_radio = QRadioButton("")
        self.rapid_fire_mode_group = QButtonGroup(self)
        self.rapid_fire_mode_group.addButton(self.rapid_fire_mode_unplayed_radio)
        self.rapid_fire_mode_group.addButton(self.rapid_fire_mode_any_radio)
        if rapid_fire_play_mode == "any_available":
            self.rapid_fire_mode_any_radio.setChecked(True)
        else:
            self.rapid_fire_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.rapid_fire_mode_unplayed_radio, 2, 1)
        mode_matrix_layout.addWidget(self.rapid_fire_mode_any_radio, 2, 2)

        self.next_mode_unplayed_radio = QRadioButton("")
        self.next_mode_any_radio = QRadioButton("")
        self.next_mode_group = QButtonGroup(self)
        self.next_mode_group.addButton(self.next_mode_unplayed_radio)
        self.next_mode_group.addButton(self.next_mode_any_radio)
        if next_play_mode == "any_available":
            self.next_mode_any_radio.setChecked(True)
        else:
            self.next_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.next_mode_unplayed_radio, 3, 1)
        mode_matrix_layout.addWidget(self.next_mode_any_radio, 3, 2)

        mode_matrix_layout.addWidget(QLabel("Play List"), 1, 0)
        mode_matrix_layout.addWidget(QLabel("Rapid Fire"), 2, 0)
        mode_matrix_layout.addWidget(QLabel("Next"), 3, 0)
        layout.addWidget(mode_matrix_group)

        playlist_loop_group = QGroupBox("When Loop is enabled in Play List:")
        playlist_loop_layout = QVBoxLayout(playlist_loop_group)
        self.playlist_loop_list_radio = QRadioButton("Loop List")
        self.playlist_loop_single_radio = QRadioButton("Loop Single")
        if playlist_loop_mode == "loop_single":
            self.playlist_loop_single_radio.setChecked(True)
        else:
            self.playlist_loop_list_radio.setChecked(True)
        playlist_loop_layout.addWidget(self.playlist_loop_list_radio)
        playlist_loop_layout.addWidget(self.playlist_loop_single_radio)
        layout.addWidget(playlist_loop_group)

        candidate_error_group = QGroupBox("When Play List/Next/Rapid Fire hits audio load error (purple):")
        candidate_error_layout = QVBoxLayout(candidate_error_group)
        self.candidate_error_stop_radio = QRadioButton("Stop playback")
        self.candidate_error_keep_radio = QRadioButton("Keep playing")
        if candidate_error_action == "keep_playing":
            self.candidate_error_keep_radio.setChecked(True)
        else:
            self.candidate_error_stop_radio.setChecked(True)
        candidate_error_layout.addWidget(self.candidate_error_stop_radio)
        candidate_error_layout.addWidget(self.candidate_error_keep_radio)
        layout.addWidget(candidate_error_group)

        cue_group = QGroupBox("Main Player Timeline / Jog Display:")
        cue_layout = QVBoxLayout(cue_group)
        self.cue_timeline_cue_region_radio = QRadioButton("Relative to Cue Set Points")
        self.cue_timeline_audio_file_radio = QRadioButton("Relative to Actual Audio File")
        if main_transport_timeline_mode == "audio_file":
            self.cue_timeline_audio_file_radio.setChecked(True)
        else:
            self.cue_timeline_cue_region_radio.setChecked(True)
        cue_layout.addWidget(self.cue_timeline_cue_region_radio)
        cue_layout.addWidget(self.cue_timeline_audio_file_radio)
        layout.addWidget(cue_group)

        self.jog_outside_group = QGroupBox("When jog is outside cue area (Audio File mode):")
        jog_outside_layout = QVBoxLayout(self.jog_outside_group)
        self.jog_outside_stop_immediately_radio = QRadioButton("Stop immediately")
        self.jog_outside_ignore_cue_radio = QRadioButton("Ignore cue and play until end or stopped")
        self.jog_outside_next_cue_or_stop_radio = QRadioButton(
            "Play to next cue or stop (before start: stop at start; after stop: play to end)"
        )
        self.jog_outside_stop_cue_or_end_radio = QRadioButton(
            "Play to stop cue (before start: stop at stop cue; after stop: play to end)"
        )
        if main_jog_outside_cue_action == "ignore_cue":
            self.jog_outside_ignore_cue_radio.setChecked(True)
        elif main_jog_outside_cue_action == "next_cue_or_stop":
            self.jog_outside_next_cue_or_stop_radio.setChecked(True)
        elif main_jog_outside_cue_action == "stop_cue_or_end":
            self.jog_outside_stop_cue_or_end_radio.setChecked(True)
        else:
            self.jog_outside_stop_immediately_radio.setChecked(True)
        jog_outside_layout.addWidget(self.jog_outside_stop_immediately_radio)
        jog_outside_layout.addWidget(self.jog_outside_ignore_cue_radio)
        jog_outside_layout.addWidget(self.jog_outside_next_cue_or_stop_radio)
        jog_outside_layout.addWidget(self.jog_outside_stop_cue_or_end_radio)
        layout.addWidget(self.jog_outside_group)
        self.cue_timeline_cue_region_radio.toggled.connect(self._sync_jog_outside_group_enabled)
        self.cue_timeline_audio_file_radio.toggled.connect(self._sync_jog_outside_group_enabled)
        self._sync_jog_outside_group_enabled()

        layout.addStretch(1)
        return page

    def _build_audio_device_page(
        self,
        audio_output_device: str,
        available_audio_devices: List[str],
        available_midi_devices: List[tuple[str, str]],
        timecode_audio_output_device: str,
        timecode_midi_output_device: str,
        timecode_mode: str,
        timecode_fps: float,
        timecode_mtc_fps: float,
        timecode_mtc_idle_behavior: str,
        timecode_sample_rate: int,
        timecode_bit_depth: int,
        timecode_timeline_mode: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        playback_group = QGroupBox("Audio Playback")
        playback_layout = QVBoxLayout(playback_group)
        row = QHBoxLayout()
        row.addWidget(QLabel("Playback Device:"))
        self.audio_device_combo = QComboBox()
        row.addWidget(self.audio_device_combo, 1)
        self.audio_refresh_button = QPushButton("Refresh")
        self.audio_refresh_button.clicked.connect(self._refresh_audio_devices)
        row.addWidget(self.audio_refresh_button)
        playback_layout.addLayout(row)

        self.audio_device_hint = QLabel("")
        playback_layout.addWidget(self.audio_device_hint)
        layout.addWidget(playback_group)

        self._populate_audio_devices(available_audio_devices, audio_output_device)

        mode_group = QGroupBox("Timecode Mode")
        mode_form = QFormLayout(mode_group)
        self.timecode_mode_combo = QComboBox()
        self.timecode_mode_combo.addItem("All Zero", TIMECODE_MODE_ZERO)
        self.timecode_mode_combo.addItem("Follow Media/Audio Player", TIMECODE_MODE_FOLLOW)
        self.timecode_mode_combo.addItem("System Time", TIMECODE_MODE_SYSTEM)
        self.timecode_mode_combo.addItem("Pause Sync (Freeze While Playback Continues)", TIMECODE_MODE_FOLLOW_FREEZE)
        mode_form.addRow("Mode:", self.timecode_mode_combo)
        layout.addWidget(mode_group)

        timeline_group = QGroupBox("Timecode Display Timeline")
        timeline_layout = QVBoxLayout(timeline_group)
        self.timecode_timeline_cue_region_radio = QRadioButton("Relative to Cue Set Points")
        self.timecode_timeline_audio_file_radio = QRadioButton("Relative to Actual Audio File")
        if timecode_timeline_mode == "audio_file":
            self.timecode_timeline_audio_file_radio.setChecked(True)
        else:
            self.timecode_timeline_cue_region_radio.setChecked(True)
        timeline_layout.addWidget(self.timecode_timeline_cue_region_radio)
        timeline_layout.addWidget(self.timecode_timeline_audio_file_radio)
        layout.addWidget(timeline_group)

        ltc_group = QGroupBox("SMPTE Timecode (LTC)")
        ltc_form = QFormLayout(ltc_group)
        self.timecode_output_combo = QComboBox()
        self.timecode_output_combo.addItem("Follow playback device setting", "follow_playback")
        self.timecode_output_combo.addItem("Use system default", "default")
        self.timecode_output_combo.addItem("None (mute output)", "none")
        for name in available_audio_devices:
            self.timecode_output_combo.addItem(name, name)
        ltc_form.addRow("Output Device:", self.timecode_output_combo)

        self.timecode_fps_combo = QComboBox()
        for fps in TIME_CODE_FPS_CHOICES:
            self.timecode_fps_combo.addItem(f"{fps:g} fps", float(fps))
        ltc_form.addRow("Frame Rate:", self.timecode_fps_combo)

        self.timecode_sample_rate_combo = QComboBox()
        for sample_rate in TIME_CODE_SAMPLE_RATES:
            self.timecode_sample_rate_combo.addItem(f"{sample_rate} Hz", int(sample_rate))
        ltc_form.addRow("Sample Rate:", self.timecode_sample_rate_combo)

        self.timecode_bit_depth_combo = QComboBox()
        for bit_depth in TIME_CODE_BIT_DEPTHS:
            self.timecode_bit_depth_combo.addItem(f"{bit_depth}-bit", int(bit_depth))
        ltc_form.addRow("Bit Depth:", self.timecode_bit_depth_combo)
        layout.addWidget(ltc_group)

        mtc_group = QGroupBox("MIDI Timecode (MTC)")
        mtc_form = QFormLayout(mtc_group)
        self.timecode_midi_output_combo = QComboBox()
        self.timecode_midi_output_combo.addItem("None (disabled)", MIDI_OUTPUT_DEVICE_NONE)
        for device_id, device_name in available_midi_devices:
            self.timecode_midi_output_combo.addItem(device_name, device_id)
        mtc_form.addRow("MIDI Output Device:", self.timecode_midi_output_combo)

        self.timecode_mtc_fps_combo = QComboBox()
        for fps in TIME_CODE_MTC_FPS_CHOICES:
            self.timecode_mtc_fps_combo.addItem(f"{fps:g} fps", float(fps))
        mtc_form.addRow("Frame Rate:", self.timecode_mtc_fps_combo)

        self.timecode_mtc_idle_behavior_combo = QComboBox()
        self.timecode_mtc_idle_behavior_combo.addItem("Keep stream alive (no dark)", "keep_stream")
        self.timecode_mtc_idle_behavior_combo.addItem("Allow dark when idle", "allow_dark")
        mtc_form.addRow("Idle Behavior:", self.timecode_mtc_idle_behavior_combo)
        layout.addWidget(mtc_group)

        self._set_combo_data_or_default(self.timecode_output_combo, timecode_audio_output_device, "none")
        self._set_combo_data_or_default(self.timecode_mode_combo, timecode_mode, TIMECODE_MODE_FOLLOW)
        self._set_combo_float_or_default(self.timecode_fps_combo, float(timecode_fps), 30.0)
        self._set_combo_float_or_default(self.timecode_mtc_fps_combo, float(timecode_mtc_fps), 30.0)
        self._set_combo_data_or_default(self.timecode_mtc_idle_behavior_combo, timecode_mtc_idle_behavior, "keep_stream")
        self._set_combo_data_or_default(self.timecode_sample_rate_combo, int(timecode_sample_rate), 48000)
        self._set_combo_data_or_default(self.timecode_bit_depth_combo, int(timecode_bit_depth), 16)
        self._set_combo_data_or_default(self.timecode_midi_output_combo, timecode_midi_output_device, MIDI_OUTPUT_DEVICE_NONE)

        layout.addStretch(1)
        return page

    def _build_audio_preload_page(
        self,
        preload_audio_enabled: bool,
        preload_current_page_audio: bool,
        preload_audio_memory_limit_mb: int,
        preload_memory_pressure_enabled: bool,
        preload_pause_on_playback: bool,
        preload_total_ram_mb: int,
        preload_ram_cap_mb: int,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._preload_slider_step_mb = 128
        total_mb = max(512, int(preload_total_ram_mb))
        cap_mb = max(128, min(int(preload_ram_cap_mb), total_mb))
        cap_steps = max(1, cap_mb // self._preload_slider_step_mb)
        cap_mb = cap_steps * self._preload_slider_step_mb
        selected_mb = max(128, min(int(preload_audio_memory_limit_mb), cap_mb))
        selected_steps = max(1, selected_mb // self._preload_slider_step_mb)
        selected_mb = selected_steps * self._preload_slider_step_mb
        reserve_mb = max(128, int(total_mb - cap_mb))
        self._preload_ram_cap_mb = cap_mb

        options_group = QGroupBox("Behavior")
        options_form = QFormLayout(options_group)
        self.preload_audio_enabled_checkbox = QCheckBox("Enable audio preload cache")
        self.preload_audio_enabled_checkbox.setChecked(bool(preload_audio_enabled))
        options_form.addRow(self.preload_audio_enabled_checkbox)

        self.preload_current_page_checkbox = QCheckBox("Preload current page first")
        self.preload_current_page_checkbox.setChecked(bool(preload_current_page_audio))
        options_form.addRow(self.preload_current_page_checkbox)

        self.preload_memory_pressure_checkbox = QCheckBox("Auto-free cache when other apps use RAM (FIFO)")
        self.preload_memory_pressure_checkbox.setChecked(bool(preload_memory_pressure_enabled))
        options_form.addRow(self.preload_memory_pressure_checkbox)
        self.preload_pause_on_playback_checkbox = QCheckBox("Pause audio preload during playback")
        self.preload_pause_on_playback_checkbox.setChecked(bool(preload_pause_on_playback))
        options_form.addRow(self.preload_pause_on_playback_checkbox)
        layout.addWidget(options_group)

        ram_group = QGroupBox("RAM Limit")
        ram_layout = QVBoxLayout(ram_group)
        self.preload_ram_info_label = QLabel(
            f"System RAM: {total_mb} MB | Reserved: {reserve_mb} MB | Max Cache Limit: {cap_mb} MB"
        )
        self.preload_ram_info_label.setWordWrap(True)
        ram_layout.addWidget(self.preload_ram_info_label)

        self.preload_memory_slider = QSlider(Qt.Horizontal)
        self.preload_memory_slider.setRange(1, cap_steps)
        self.preload_memory_slider.setSingleStep(1)
        self.preload_memory_slider.setPageStep(1)
        self.preload_memory_slider.setValue(selected_steps)
        self.preload_memory_slider.valueChanged.connect(self._update_preload_slider_label)
        ram_layout.addWidget(self.preload_memory_slider)

        self.preload_memory_value_label = QLabel("")
        ram_layout.addWidget(self.preload_memory_value_label)
        self._update_preload_slider_label()
        layout.addWidget(ram_group)

        layout.addStretch(1)
        return page

    def _update_preload_slider_label(self) -> None:
        value = int(self.preload_memory_slider.value())
        selected_mb = value * int(self._preload_slider_step_mb)
        self.preload_memory_value_label.setText(f"Selected Cache Limit: {selected_mb} MB")

    def _build_talk_page(
        self,
        talk_volume_level: int,
        talk_fade_sec: float,
        talk_volume_mode: str,
        talk_blink_button: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()

        self.talk_volume_spin = QSpinBox()
        self.talk_volume_spin.setRange(0, 100)
        self.talk_volume_spin.setValue(talk_volume_level)
        form.addRow("Talk Volume Level:", self.talk_volume_spin)

        self.talk_fade_spin = QDoubleSpinBox()
        self.talk_fade_spin.setRange(0.0, 20.0)
        self.talk_fade_spin.setSingleStep(0.1)
        self.talk_fade_spin.setDecimals(1)
        self.talk_fade_spin.setValue(talk_fade_sec)
        form.addRow("Talk Fade Seconds:", self.talk_fade_spin)

        self.talk_blink_checkbox = QCheckBox("Blink Talk Button")
        self.talk_blink_checkbox.setChecked(talk_blink_button)
        form.addRow("Talk Button:", self.talk_blink_checkbox)
        self.talk_mode_percent_radio = QRadioButton("Use Talk level as % of current volume")
        self.talk_mode_lower_only_radio = QRadioButton("Lower to Talk level only")
        self.talk_mode_force_radio = QRadioButton("Set exactly to Talk level")
        if talk_volume_mode == "set_exact":
            self.talk_mode_force_radio.setChecked(True)
        elif talk_volume_mode == "lower_only":
            self.talk_mode_lower_only_radio.setChecked(True)
        else:
            self.talk_mode_percent_radio.setChecked(True)

        mode_group = QGroupBox("Talk Volume Behavior")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setContentsMargins(8, 8, 8, 8)
        mode_layout.setSpacing(6)
        mode_layout.addWidget(self.talk_mode_percent_radio)
        mode_layout.addWidget(self.talk_mode_lower_only_radio)
        mode_layout.addWidget(self.talk_mode_force_radio)
        layout.addLayout(form)
        layout.addWidget(mode_group)
        layout.addStretch(1)

        return page

    def _build_web_remote_page(self, web_remote_enabled: bool, web_remote_port: int, web_remote_url: str) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.web_remote_enabled_checkbox = QCheckBox("Enable Web Remote (Flask API)")
        self.web_remote_enabled_checkbox.setChecked(web_remote_enabled)
        form.addRow("Web Remote:", self.web_remote_enabled_checkbox)
        self.web_remote_port_spin = QSpinBox()
        self.web_remote_port_spin.setRange(1, 65535)
        self.web_remote_port_spin.setValue(max(1, min(65535, int(web_remote_port))))
        form.addRow("Port:", self.web_remote_port_spin)
        parsed = urlparse(web_remote_url.strip() or "http://127.0.0.1:5050/")
        self._web_remote_url_scheme = parsed.scheme or "http"
        self._web_remote_url_host = parsed.hostname or "127.0.0.1"
        self.web_remote_url_value = QLabel("")
        self.web_remote_url_value.setOpenExternalLinks(True)
        self.web_remote_url_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.web_remote_url_value.setWordWrap(True)
        form.addRow("Open URL:", self.web_remote_url_value)
        self._set_web_remote_url_label(self._build_web_remote_url_text(self.web_remote_port_spin.value()))
        self.web_remote_port_spin.valueChanged.connect(
            lambda value: self._set_web_remote_url_label(self._build_web_remote_url_text(int(value)))
        )
        return page

    @classmethod
    def _normalize_stage_display_layout(cls, values: List[str]) -> List[str]:
        gadgets = normalize_stage_display_gadgets({}, legacy_layout=values)
        order, _visibility = gadgets_to_legacy_layout_visibility(gadgets)
        return order

    @classmethod
    def _normalize_stage_display_visibility(cls, values: Dict[str, bool]) -> Dict[str, bool]:
        gadgets = normalize_stage_display_gadgets({}, legacy_visibility=values)
        _order, visibility = gadgets_to_legacy_layout_visibility(gadgets)
        return visibility

    def _build_display_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        source_form = QFormLayout()
        self.display_text_source_combo = QComboBox()
        self.display_text_source_combo.addItem("Caption", "caption")
        self.display_text_source_combo.addItem("Filename", "filename")
        self.display_text_source_combo.addItem("Note", "note")
        self._set_combo_data_or_default(self.display_text_source_combo, self._stage_display_text_source, "caption")
        source_form.addRow("Now/Next Text Source:", self.display_text_source_combo)
        layout.addLayout(source_form)

        tip = QLabel("Drag and resize gadgets in the preview. Toggle visibility, then save to apply to Stage Display.")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        body = QHBoxLayout()
        toggles = QGroupBox("Gadgets")
        toggles_layout = QGridLayout(toggles)
        toggles_layout.setContentsMargins(6, 6, 6, 6)
        toggles_layout.setHorizontalSpacing(6)
        toggles_layout.setVerticalSpacing(4)
        self._display_gadget_table_layout = toggles_layout
        self._display_gadget_checks: Dict[str, QCheckBox] = {}
        self._display_alert_edit_visibility_button: Optional[QPushButton] = None
        self._display_gadget_hide_text_checks: Dict[str, QCheckBox] = {}
        self._display_gadget_hide_border_checks: Dict[str, QCheckBox] = {}
        self._display_gadget_orientation_combos: Dict[str, QComboBox] = {}
        self._display_gadget_name_labels: Dict[str, QLabel] = {}
        self._display_gadget_visibility_widgets: Dict[str, QWidget] = {}
        self._display_gadget_layer_cells: Dict[str, QWidget] = {}
        self._display_gadget_layer_labels: Dict[str, QLabel] = {}
        self._display_gadget_layer_up_buttons: Dict[str, QPushButton] = {}
        self._display_gadget_layer_down_buttons: Dict[str, QPushButton] = {}
        labels = dict(self._DISPLAY_OPTION_SPECS)
        header_style = "font-weight:bold; color:#666666;"
        for col, text in enumerate(["Gadget", "Visible / Edit", "Hide Text", "Hide Border", "Orientation", "Layer"]):
            header = QLabel(text)
            header.setStyleSheet(header_style)
            header.setMaximumHeight(18)
            toggles_layout.addWidget(header, 0, col)
        for row, (key, _label) in enumerate(self._DISPLAY_OPTION_SPECS, start=1):
            name_label = QLabel(labels.get(key, key))
            toggles_layout.addWidget(name_label, row, 0)
            self._display_gadget_name_labels[key] = name_label
            if key == "alert":
                edit_button = QPushButton("")
                edit_button.clicked.connect(lambda _=False: self._toggle_alert_edit_visibility())
                toggles_layout.addWidget(edit_button, row, 1)
                self._display_alert_edit_visibility_button = edit_button
                self._display_gadget_visibility_widgets[key] = edit_button
            else:
                checkbox = QCheckBox(labels.get(key, key))
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("visible", True)))
                checkbox.toggled.connect(
                    lambda checked, token=key: self.display_layout_editor.set_gadget_visible(token, bool(checked))
                )
                checkbox.setText("")
                toggles_layout.addWidget(checkbox, row, 1)
                self._display_gadget_checks[key] = checkbox
                self._display_gadget_visibility_widgets[key] = checkbox

            hide_text_checkbox = QCheckBox("")
            hide_text_checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_text", False)))
            hide_text_checkbox.toggled.connect(
                lambda checked, token=key: self.display_layout_editor.set_gadget_hide_text(token, bool(checked))
            )
            toggles_layout.addWidget(hide_text_checkbox, row, 2)
            self._display_gadget_hide_text_checks[key] = hide_text_checkbox

            hide_border_checkbox = QCheckBox("")
            hide_border_checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_border", False)))
            hide_border_checkbox.toggled.connect(
                lambda checked, token=key: self.display_layout_editor.set_gadget_hide_border(token, bool(checked))
            )
            toggles_layout.addWidget(hide_border_checkbox, row, 3)
            self._display_gadget_hide_border_checks[key] = hide_border_checkbox

            orientation_combo = QComboBox()
            orientation_combo.addItem("Horizontal", "horizontal")
            orientation_combo.addItem("Vertical", "vertical")
            token = str(self._stage_display_gadgets.get(key, {}).get("orientation", "vertical")).strip().lower()
            if token not in {"horizontal", "vertical"}:
                token = "vertical"
            orientation_combo.setCurrentIndex(max(0, orientation_combo.findData(token)))
            orientation_combo.currentIndexChanged.connect(
                lambda _idx, combo=orientation_combo, gadget_key=key: self.display_layout_editor.set_gadget_orientation(
                    gadget_key,
                    str(combo.currentData() or "vertical"),
                )
            )
            toggles_layout.addWidget(orientation_combo, row, 4)
            self._display_gadget_orientation_combos[key] = orientation_combo

            layer_cell = QWidget()
            layer_cell_layout = QHBoxLayout(layer_cell)
            layer_cell_layout.setContentsMargins(0, 0, 0, 0)
            layer_cell_layout.setSpacing(4)
            up_btn = QPushButton("Up")
            down_btn = QPushButton("Down")
            layer_label = QLabel("")
            layer_label.setAlignment(Qt.AlignCenter)
            up_btn.clicked.connect(lambda _=False, token=key: self._move_display_layer(token, -1))
            down_btn.clicked.connect(lambda _=False, token=key: self._move_display_layer(token, 1))
            layer_cell_layout.addWidget(up_btn)
            layer_cell_layout.addWidget(down_btn)
            layer_cell_layout.addWidget(layer_label)
            toggles_layout.addWidget(layer_cell, row, 5)
            self._display_gadget_layer_cells[key] = layer_cell
            self._display_gadget_layer_labels[key] = layer_label
            self._display_gadget_layer_up_buttons[key] = up_btn
            self._display_gadget_layer_down_buttons[key] = down_btn

        self._sync_alert_edit_button_text()
        self._refresh_display_layer_table()
        body.addWidget(toggles, 0)

        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.display_layout_editor = StageDisplayLayoutEditor()
        self.display_layout_editor.set_gadgets(self._stage_display_gadgets)
        self._refresh_display_layer_table()
        preview_layout.addWidget(self.display_layout_editor, 1)
        body.addWidget(preview_group, 1)
        layout.addLayout(body, 1)

        note = QLabel("Next Song is shown when playlist mode is enabled on the active page.")
        note.setWordWrap(True)
        layout.addWidget(note)
        alert_note = QLabel("Alert gadget is always hidden on live Stage Display until an alert is sent.")
        alert_note.setWordWrap(True)
        alert_note.setStyleSheet("color:#888888;")
        layout.addWidget(alert_note)
        return page

    def _refresh_display_layer_table(self) -> None:
        if not hasattr(self, "display_layout_editor"):
            return
        base_order = self.display_layout_editor.layer_order()
        ordered = list(reversed(base_order))
        total = len(ordered)
        for idx, key in enumerate(ordered):
            row = idx + 1
            name_label = self._display_gadget_name_labels.get(key)
            vis_widget = self._display_gadget_visibility_widgets.get(key)
            hide_text_widget = self._display_gadget_hide_text_checks.get(key)
            hide_border_widget = self._display_gadget_hide_border_checks.get(key)
            orient_widget = self._display_gadget_orientation_combos.get(key)
            layer_cell = self._display_gadget_layer_cells.get(key)
            layer_label = self._display_gadget_layer_labels.get(key)
            up_btn = self._display_gadget_layer_up_buttons.get(key)
            down_btn = self._display_gadget_layer_down_buttons.get(key)
            if name_label is not None:
                self._display_gadget_table_layout.addWidget(name_label, row, 0)
            if vis_widget is not None:
                self._display_gadget_table_layout.addWidget(vis_widget, row, 1)
            if hide_text_widget is not None:
                self._display_gadget_table_layout.addWidget(hide_text_widget, row, 2)
            if hide_border_widget is not None:
                self._display_gadget_table_layout.addWidget(hide_border_widget, row, 3)
            if orient_widget is not None:
                self._display_gadget_table_layout.addWidget(orient_widget, row, 4)
            if layer_cell is not None:
                self._display_gadget_table_layout.addWidget(layer_cell, row, 5)
            if up_btn is None or down_btn is None or layer_label is None:
                continue
            layer_label.setText(f"{idx + 1}/{total}")
            up_btn.setEnabled(idx > 0)
            down_btn.setEnabled(idx < (total - 1))

    def _move_display_layer(self, key: str, delta: int) -> None:
        if not hasattr(self, "display_layout_editor"):
            return
        ordered = list(reversed(self.display_layout_editor.layer_order()))
        if key not in ordered:
            return
        idx = ordered.index(key)
        target = idx + int(delta)
        if target < 0 or target >= len(ordered):
            return
        ordered[idx], ordered[target] = ordered[target], ordered[idx]
        self.display_layout_editor.set_layer_order(list(reversed(ordered)))
        self._stage_display_gadgets = self.display_layout_editor.gadgets()
        self._refresh_display_layer_table()

    def _toggle_alert_edit_visibility(self) -> None:
        current = bool(self.display_layout_editor.gadgets().get("alert", {}).get("visible", False))
        next_value = not current
        self._stage_display_gadgets["alert"]["visible"] = next_value
        self.display_layout_editor.set_gadget_visible("alert", next_value)
        self._sync_alert_edit_button_text()

    def _sync_alert_edit_button_text(self) -> None:
        if self._display_alert_edit_visibility_button is None:
            return
        if hasattr(self, "display_layout_editor"):
            visible = bool(self.display_layout_editor.gadgets().get("alert", {}).get("visible", False))
        else:
            visible = bool(self._stage_display_gadgets.get("alert", {}).get("visible", False))
        self._display_alert_edit_visibility_button.setText("Hide for Edit" if visible else "Show for Edit")

    def _build_web_remote_url_text(self, port: int) -> str:
        return f"{self._web_remote_url_scheme}://{self._web_remote_url_host}:{port}/"

    def _set_web_remote_url_label(self, url: str) -> None:
        self.web_remote_url_value.setText(f'<a href="{url}">{url}</a>')

    def selected_click_playing_action(self) -> str:
        if self.playing_click_stop_radio.isChecked():
            return "stop_it"
        return "play_it_again"

    def selected_search_double_click_action(self) -> str:
        if self.search_dbl_play_radio.isChecked():
            return "play_highlight"
        return "find_highlight"

    def selected_set_file_encoding(self) -> str:
        if self.set_file_encoding_gbk_radio.isChecked():
            return "gbk"
        return "utf8"

    def selected_main_progress_display_mode(self) -> str:
        if self.main_progress_display_waveform_radio.isChecked():
            return "waveform"
        return "progress_bar"

    def selected_main_progress_show_text(self) -> bool:
        return bool(self.main_progress_show_text_checkbox.isChecked())

    def selected_ui_language(self) -> str:
        return normalize_language(str(self.ui_language_combo.currentData() or "en"))

    def selected_audio_output_device(self) -> str:
        return str(self.audio_device_combo.currentData() or "")

    def selected_vst_enabled(self) -> bool:
        return bool(self._vst_supported and self.vst_enabled_checkbox.isChecked())

    def selected_vst_directories(self) -> List[str]:
        dirs: List[str] = []
        for index in range(self.vst_dir_list.count()):
            item = self.vst_dir_list.item(index)
            if item is None:
                continue
            token = str(item.text() or "").strip()
            if token:
                dirs.append(token)
        return effective_vst_directories(dirs)

    def selected_vst_known_plugins(self) -> List[str]:
        plugins: List[str] = []
        for index in range(self.vst_plugin_list.count()):
            item = self.vst_plugin_list.item(index)
            if item is None:
                continue
            token = str(item.data(Qt.UserRole) or "").strip()
            if token:
                plugins.append(token)
        return plugins

    def selected_vst_enabled_plugins(self) -> List[str]:
        enabled: List[str] = []
        for index in range(self.vst_plugin_list.count()):
            item = self.vst_plugin_list.item(index)
            if item is None:
                continue
            token = str(item.data(Qt.UserRole) or "").strip()
            if token and item.checkState() == Qt.Checked:
                enabled.append(token)
        return enabled

    def selected_vst_chain(self) -> List[str]:
        known = set(self.selected_vst_known_plugins())
        chain: List[str] = []
        for plugin_path in self._vst_chain:
            token = str(plugin_path or "").strip()
            if token and token in known:
                chain.append(token)
        return chain

    def selected_vst_plugin_state(self) -> Dict[str, Dict[str, object]]:
        known = set(self.selected_vst_known_plugins())
        output: Dict[str, Dict[str, object]] = {}
        for plugin_path, state in self._vst_plugin_state.items():
            token = str(plugin_path or "").strip()
            if not token or token not in known:
                continue
            if not isinstance(state, dict):
                continue
            output[token] = dict(state)
        return output

    def selected_timecode_audio_output_device(self) -> str:
        return str(self.timecode_output_combo.currentData() or "none")

    def selected_preload_audio_enabled(self) -> bool:
        return bool(self.preload_audio_enabled_checkbox.isChecked())

    def selected_preload_current_page_audio(self) -> bool:
        return bool(self.preload_current_page_checkbox.isChecked())

    def selected_preload_audio_memory_limit_mb(self) -> int:
        step_mb = int(self._preload_slider_step_mb)
        selected_mb = max(step_mb, int(self.preload_memory_slider.value()) * step_mb)
        return max(128, min(int(self._preload_ram_cap_mb), selected_mb))

    def selected_preload_memory_pressure_enabled(self) -> bool:
        return bool(self.preload_memory_pressure_checkbox.isChecked())

    def selected_preload_pause_on_playback(self) -> bool:
        return bool(self.preload_pause_on_playback_checkbox.isChecked())

    def selected_timecode_midi_output_device(self) -> str:
        return str(self.timecode_midi_output_combo.currentData() or MIDI_OUTPUT_DEVICE_NONE)

    def selected_timecode_mode(self) -> str:
        value = str(self.timecode_mode_combo.currentData() or TIMECODE_MODE_FOLLOW)
        if value not in {TIMECODE_MODE_ZERO, TIMECODE_MODE_FOLLOW, TIMECODE_MODE_SYSTEM, TIMECODE_MODE_FOLLOW_FREEZE}:
            return TIMECODE_MODE_FOLLOW
        return value

    def selected_timecode_fps(self) -> float:
        try:
            return float(self.timecode_fps_combo.currentData())
        except (TypeError, ValueError):
            return 30.0

    def selected_timecode_mtc_fps(self) -> float:
        try:
            return float(self.timecode_mtc_fps_combo.currentData())
        except (TypeError, ValueError):
            return 30.0

    def selected_timecode_mtc_idle_behavior(self) -> str:
        value = str(self.timecode_mtc_idle_behavior_combo.currentData() or "keep_stream")
        return value if value in {"keep_stream", "allow_dark"} else "keep_stream"

    def selected_timecode_sample_rate(self) -> int:
        try:
            return int(self.timecode_sample_rate_combo.currentData())
        except (TypeError, ValueError):
            return 48000

    def selected_timecode_bit_depth(self) -> int:
        try:
            return int(self.timecode_bit_depth_combo.currentData())
        except (TypeError, ValueError):
            return 16

    def selected_timecode_timeline_mode(self) -> str:
        if self.timecode_timeline_audio_file_radio.isChecked():
            return "audio_file"
        return "cue_region"

    def selected_max_multi_play_songs(self) -> int:
        return max(1, min(32, int(self.max_multi_play_spin.value())))

    def selected_multi_play_limit_action(self) -> str:
        if self.multi_play_disallow_radio.isChecked():
            return "disallow_more_play"
        return "stop_oldest"

    def selected_playlist_play_mode(self) -> str:
        if self.playlist_mode_any_radio.isChecked():
            return "any_available"
        return "unplayed_only"

    def selected_rapid_fire_play_mode(self) -> str:
        if self.rapid_fire_mode_any_radio.isChecked():
            return "any_available"
        return "unplayed_only"

    def selected_next_play_mode(self) -> str:
        if self.next_mode_any_radio.isChecked():
            return "any_available"
        return "unplayed_only"

    def selected_playlist_loop_mode(self) -> str:
        if self.playlist_loop_single_radio.isChecked():
            return "loop_single"
        return "loop_list"

    def selected_candidate_error_action(self) -> str:
        if self.candidate_error_keep_radio.isChecked():
            return "keep_playing"
        return "stop_playback"

    def selected_main_transport_timeline_mode(self) -> str:
        if self.cue_timeline_audio_file_radio.isChecked():
            return "audio_file"
        return "cue_region"

    def selected_main_jog_outside_cue_action(self) -> str:
        if self.jog_outside_ignore_cue_radio.isChecked():
            return "ignore_cue"
        if self.jog_outside_next_cue_or_stop_radio.isChecked():
            return "next_cue_or_stop"
        if self.jog_outside_stop_cue_or_end_radio.isChecked():
            return "stop_cue_or_end"
        return "stop_immediately"

    def selected_stage_display_layout(self) -> List[str]:
        order, _visibility = gadgets_to_legacy_layout_visibility(self.selected_stage_display_gadgets())
        return order

    def selected_stage_display_visibility(self) -> Dict[str, bool]:
        _order, visibility = gadgets_to_legacy_layout_visibility(self.selected_stage_display_gadgets())
        return visibility

    def selected_stage_display_gadgets(self) -> Dict[str, Dict[str, int | bool]]:
        if not hasattr(self, "display_layout_editor"):
            return normalize_stage_display_gadgets(
                self._stage_display_gadgets,
                legacy_layout=self._stage_display_layout,
                legacy_visibility=self._stage_display_visibility,
            )
        return normalize_stage_display_gadgets(self.display_layout_editor.gadgets())

    def selected_stage_display_text_source(self) -> str:
        token = str(self.display_text_source_combo.currentData() or "caption").strip().lower()
        if token not in {"caption", "filename", "note"}:
            return "caption"
        return token

    def selected_state_colors(self) -> Dict[str, str]:
        return dict(self.state_colors)

    def selected_sound_button_text_color(self) -> str:
        return self.sound_button_text_color

    def selected_talk_volume_mode(self) -> str:
        if self.talk_mode_force_radio.isChecked():
            return "set_exact"
        if self.talk_mode_lower_only_radio.isChecked():
            return "lower_only"
        return "percent_of_master"

    def selected_hotkeys(self) -> Dict[str, tuple[str, str]]:
        result: Dict[str, tuple[str, str]] = {}
        for key, (edit1, edit2) in self._hotkey_edits.items():
            s1 = edit1.hotkey()
            s2 = edit2.hotkey()
            result[key] = (s1, s2)
        return result

    def selected_midi_input_devices(self) -> List[str]:
        return self._checked_midi_input_device_ids()

    def selected_midi_hotkeys(self) -> Dict[str, tuple[str, str]]:
        result: Dict[str, tuple[str, str]] = {}
        for key, (edit1, edit2) in self._midi_hotkey_edits.items():
            result[key] = (edit1.binding(), edit2.binding())
        return result

    def selected_midi_quick_action_enabled(self) -> bool:
        return bool(self.midi_quick_action_enabled_checkbox.isChecked())

    def selected_midi_quick_action_bindings(self) -> List[str]:
        return [edit.binding() for edit in self._midi_quick_action_edits]

    def selected_midi_sound_button_hotkey_enabled(self) -> bool:
        return bool(self.midi_sound_button_hotkey_enabled_checkbox.isChecked())

    def selected_midi_sound_button_hotkey_priority(self) -> str:
        if self.midi_sound_hotkey_priority_sound_first_radio.isChecked():
            return "sound_button_first"
        return "system_first"

    def selected_midi_sound_button_hotkey_go_to_playing(self) -> bool:
        return bool(self.midi_sound_button_go_to_playing_checkbox.isChecked())

    def selected_midi_rotary_enabled(self) -> bool:
        return bool(self.midi_rotary_enabled_checkbox.isChecked())

    def selected_midi_rotary_group_binding(self) -> str:
        return self.midi_rotary_group_edit.binding()

    def selected_midi_rotary_page_binding(self) -> str:
        return self.midi_rotary_page_edit.binding()

    def selected_midi_rotary_sound_button_binding(self) -> str:
        return self.midi_rotary_sound_button_edit.binding()

    def selected_midi_rotary_jog_binding(self) -> str:
        return self.midi_rotary_jog_edit.binding()

    def selected_midi_rotary_volume_binding(self) -> str:
        return self.midi_rotary_volume_edit.binding()

    def selected_midi_rotary_group_invert(self) -> bool:
        return bool(self.midi_rotary_group_invert_checkbox.isChecked())

    def selected_midi_rotary_page_invert(self) -> bool:
        return bool(self.midi_rotary_page_invert_checkbox.isChecked())

    def selected_midi_rotary_sound_button_invert(self) -> bool:
        return bool(self.midi_rotary_sound_button_invert_checkbox.isChecked())

    def selected_midi_rotary_jog_invert(self) -> bool:
        return bool(self.midi_rotary_jog_invert_checkbox.isChecked())

    def selected_midi_rotary_volume_invert(self) -> bool:
        return bool(self.midi_rotary_volume_invert_checkbox.isChecked())

    def selected_midi_rotary_group_sensitivity(self) -> int:
        return int(self.midi_rotary_group_sensitivity_spin.value())

    def selected_midi_rotary_page_sensitivity(self) -> int:
        return int(self.midi_rotary_page_sensitivity_spin.value())

    def selected_midi_rotary_sound_button_sensitivity(self) -> int:
        return int(self.midi_rotary_sound_button_sensitivity_spin.value())

    def selected_midi_rotary_group_relative_mode(self) -> str:
        return self._midi_rotary_group_relative_mode

    def selected_midi_rotary_page_relative_mode(self) -> str:
        return self._midi_rotary_page_relative_mode

    def selected_midi_rotary_sound_button_relative_mode(self) -> str:
        return self._midi_rotary_sound_button_relative_mode

    def selected_midi_rotary_jog_relative_mode(self) -> str:
        return self._midi_rotary_jog_relative_mode

    def selected_midi_rotary_volume_relative_mode(self) -> str:
        return self._midi_rotary_volume_relative_mode

    def selected_midi_rotary_volume_mode(self) -> str:
        return str(self.midi_rotary_volume_mode_combo.currentData() or "relative")

    def selected_midi_rotary_volume_step(self) -> int:
        return int(self.midi_rotary_volume_step_spin.value())

    def selected_midi_rotary_jog_step_ms(self) -> int:
        return int(self.midi_rotary_jog_step_spin.value())

    def selected_quick_action_enabled(self) -> bool:
        return bool(self.quick_action_enabled_checkbox.isChecked())

    def selected_quick_action_keys(self) -> List[str]:
        return [edit.hotkey() for edit in self._quick_action_edits]

    def selected_sound_button_hotkey_enabled(self) -> bool:
        return bool(self.sound_button_hotkey_enabled_checkbox.isChecked())

    def selected_sound_button_hotkey_priority(self) -> str:
        if self.sound_hotkey_priority_sound_first_radio.isChecked():
            return "sound_button_first"
        return "system_first"

    def selected_sound_button_hotkey_go_to_playing(self) -> bool:
        return bool(self.sound_button_go_to_playing_checkbox.isChecked())

    def _sync_jog_outside_group_enabled(self) -> None:
        enabled = self.cue_timeline_audio_file_radio.isChecked()
        self.jog_outside_group.setEnabled(enabled)

    def _refresh_midi_input_devices(self, force_refresh: bool = False) -> None:
        current_ids = set(self._checked_midi_input_device_ids() or self._midi_input_device_ids)
        current_names = set(self._checked_midi_input_device_names())
        for selector in current_ids:
            name = midi_input_selector_name(selector)
            if name:
                current_names.add(name)
        try:
            self.midi_input_list.itemChanged.disconnect(self._on_midi_input_selection_changed)
        except Exception:
            pass
        self.midi_input_list.clear()
        for device_id, device_name in list_midi_input_devices(force_refresh=force_refresh):
            selector = midi_input_name_selector(device_name)
            item = QListWidgetItem(device_name)
            item.setData(Qt.UserRole, selector)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            checked = (selector in current_ids) or (str(device_name).strip() in current_names) or (str(device_id) in current_ids)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.midi_input_list.addItem(item)
        self.midi_input_list.itemChanged.connect(self._on_midi_input_selection_changed)
        self._on_midi_input_selection_changed()

    def _checked_midi_input_device_ids(self) -> List[str]:
        selected: List[str] = []
        seen: set[str] = set()
        if not hasattr(self, "midi_input_list"):
            return selected
        for i in range(self.midi_input_list.count()):
            item = self.midi_input_list.item(i)
            if item is None:
                continue
            if item.checkState() == Qt.Checked:
                device_id = str(item.data(Qt.UserRole) or "").strip()
                if device_id and device_id not in seen:
                    seen.add(device_id)
                    selected.append(device_id)
        return selected

    def _checked_midi_input_device_names(self) -> List[str]:
        selected: List[str] = []
        if not hasattr(self, "midi_input_list"):
            return selected
        for i in range(self.midi_input_list.count()):
            item = self.midi_input_list.item(i)
            if item is None:
                continue
            if item.checkState() == Qt.Checked:
                name = str(item.text() or "").strip()
                if name:
                    selected.append(name)
        return selected

    def _on_midi_input_selection_changed(self, _item=None) -> None:
        ids = self._checked_midi_input_device_ids()
        self._midi_input_device_ids = ids

    def _start_midi_learning(self, target: MidiCaptureEdit) -> None:
        self._set_midi_info("")
        if self._learning_midi_rotary_target is not None and self._learning_midi_rotary_target is not target:
            self._learning_midi_rotary_target.setStyleSheet("")
            self._learning_midi_rotary_target = None
            self._learning_midi_rotary_state = None
        if self._learning_midi_target is not None and self._learning_midi_target is not target:
            self._learning_midi_target.setStyleSheet("")
        self._learning_midi_target = target
        target.setStyleSheet("QLineEdit{border:2px solid #2E65FF;}")

    def _start_midi_rotary_learning(self, target: MidiCaptureEdit) -> None:
        if self._learning_midi_target is not None and self._learning_midi_target is not target:
            self._learning_midi_target.setStyleSheet("")
            self._learning_midi_target = None
        if self._learning_midi_rotary_target is not None and self._learning_midi_rotary_target is not target:
            self._learning_midi_rotary_target.setStyleSheet("")
        self._learning_midi_rotary_target = target
        self._learning_midi_rotary_state = {
            "selector": "",
            "status": -1,
            "data1": -1,
            "phase": "forward",
            "forward": [],
            "backward": [],
        }
        self._set_midi_info("Rotary learn: turn encoder forward several ticks, then backward several ticks.")
        target.setStyleSheet("QLineEdit{border:2px solid #2E65FF;}")

    def _on_midi_binding_captured(self, token: str, source_selector: str = "") -> None:
        if self._learning_midi_target is None:
            return
        _prev_selector, normalized_token = split_midi_binding(token)
        if source_selector:
            self._learning_midi_target.setBinding(f"{source_selector}|{normalized_token}")
        else:
            self._learning_midi_target.setBinding(normalized_token)
        self._learning_midi_target.setStyleSheet("")
        self._learning_midi_target = None
        self._validate_midi_conflicts()

    def handle_midi_message(
        self,
        token: str,
        source_selector: str = "",
        status: int = 0,
        data1: int = 0,
        data2: int = 0,
    ) -> bool:
        if self._learning_midi_rotary_target is not None:
            status = int(status) & 0xFF
            data1 = int(data1) & 0xFF
            data2 = int(data2) & 0xFF
            base = ""
            high = status & 0xF0
            state = self._learning_midi_rotary_state or {
                "selector": "",
                "status": -1,
                "data1": -1,
                "phase": "forward",
                "forward": [],
                "backward": [],
            }
            if high == 0xB0:
                base = normalize_midi_binding(f"{status:02X}:{data1:02X}")
                bound_selector = str(state.get("selector", "") or "")
                bound_status = int(state.get("status", -1))
                bound_data1 = int(state.get("data1", -1))
                if bound_status < 0:
                    state["selector"] = str(source_selector or "")
                    state["status"] = status
                    state["data1"] = data1
                else:
                    if str(source_selector or "") != bound_selector:
                        return True
                    if status != bound_status or data1 != bound_data1:
                        return True
                phase = str(state.get("phase", "forward"))
                if data2 != 64:
                    if phase == "forward":
                        state["forward"].append(data2)
                        if len(state["forward"]) >= 4:
                            state["phase"] = "backward"
                            self._set_midi_info("Rotary learn: now turn backward several ticks.")
                    else:
                        state["backward"].append(data2)
                self._learning_midi_rotary_state = state
                if len(state["forward"]) >= 4 and len(state["backward"]) >= 4:
                    mode = self._infer_midi_relative_mode(
                        [int(v) for v in state["forward"]],
                        [int(v) for v in state["backward"]],
                    )
                    value = f"{source_selector}|{base}" if source_selector else base
                    self._learning_midi_rotary_target.setBinding(value)
                    self._set_midi_rotary_relative_mode_for_target(self._learning_midi_rotary_target, mode)
                    self._learning_midi_rotary_target.setStyleSheet("")
                    self._learning_midi_rotary_target = None
                    self._learning_midi_rotary_state = None
                    self._set_midi_info(f"Rotary learn complete. Relative mode: {mode}.")
                    self._validate_midi_conflicts()
                return True
            elif high == 0xE0:
                # Pitch Bend encoders/wheels: bind by status(channel).
                base = normalize_midi_binding(f"{status:02X}")
            if base:
                value = f"{source_selector}|{base}" if source_selector else base
                self._learning_midi_rotary_target.setBinding(value)
                self._set_midi_rotary_relative_mode_for_target(self._learning_midi_rotary_target, "auto")
                self._learning_midi_rotary_target.setStyleSheet("")
                self._learning_midi_rotary_target = None
                self._learning_midi_rotary_state = None
                self._set_midi_info("Rotary learn complete.")
                self._validate_midi_conflicts()
                return True
            return False
        if self._learning_midi_target is None:
            return False
        selected = set(self._midi_input_device_ids)
        if selected:
            if not source_selector:
                return False
            if source_selector not in selected:
                return False
        self._on_midi_binding_captured(token, source_selector)
        return True

    def _set_midi_info(self, text: str) -> None:
        if self._midi_warning_label is None:
            return
        message = str(text or "").strip()
        if message:
            self._midi_warning_label.setStyleSheet("color:#1E4FAF; font-weight:bold;")
            self._midi_warning_label.setText(message)
            self._midi_warning_label.setVisible(True)
            return
        self._midi_warning_label.setVisible(False)
        self._midi_warning_label.setText("")

    @staticmethod
    def _normalize_midi_relative_mode(value: str) -> str:
        mode = str(value or "").strip().lower()
        if mode in {"auto", "twos_complement", "sign_magnitude", "binary_offset"}:
            return mode
        return "auto"

    @staticmethod
    def _decode_relative_delta(value: int, mode: str) -> int:
        v = int(value) & 0x7F
        if v == 64:
            return 0
        mode_name = OptionsDialog._normalize_midi_relative_mode(mode)
        if mode_name == "binary_offset":
            return v - 64
        if mode_name == "sign_magnitude":
            if 1 <= v <= 63:
                return v
            if 65 <= v <= 127:
                return -(v - 64)
            return 0
        # twos_complement and auto fallback
        if 1 <= v <= 63:
            return v
        if 65 <= v <= 127:
            return v - 128
        return 0

    def _infer_midi_relative_mode(self, forward_values: List[int], backward_values: List[int]) -> str:
        modes = ["twos_complement", "sign_magnitude", "binary_offset"]
        best_mode = "auto"
        best_score = None
        for mode in modes:
            f = [self._decode_relative_delta(v, mode) for v in forward_values]
            b = [self._decode_relative_delta(v, mode) for v in backward_values]
            sign_penalty = (sum(1 for d in f if d <= 0) + sum(1 for d in b if d >= 0)) * 1000
            f_abs = [abs(d) for d in f if d > 0]
            b_abs = [abs(d) for d in b if d < 0]
            if not f_abs or not b_abs:
                score = sign_penalty + 99999
            else:
                mean_f = sum(f_abs) / float(len(f_abs))
                mean_b = sum(b_abs) / float(len(b_abs))
                symmetry_penalty = abs(mean_f - mean_b) * 20.0
                size_penalty = max(0.0, mean_f - 12.0) * 8.0 + max(0.0, mean_b - 12.0) * 8.0
                score = sign_penalty + symmetry_penalty + size_penalty
            if best_score is None or score < best_score:
                best_score = score
                best_mode = mode
        return best_mode

    def _set_midi_rotary_relative_mode_for_target(self, target: MidiCaptureEdit, mode: str) -> None:
        normalized = self._normalize_midi_relative_mode(mode)
        if target is self.midi_rotary_group_edit:
            self._midi_rotary_group_relative_mode = normalized
        elif target is self.midi_rotary_page_edit:
            self._midi_rotary_page_relative_mode = normalized
        elif target is self.midi_rotary_sound_button_edit:
            self._midi_rotary_sound_button_relative_mode = normalized
        elif target is self.midi_rotary_jog_edit:
            self._midi_rotary_jog_relative_mode = normalized
        elif target is self.midi_rotary_volume_edit:
            self._midi_rotary_volume_relative_mode = normalized

    def _set_combo_data_or_default(self, combo: QComboBox, selected_data, default_data) -> None:
        index = combo.findData(selected_data)
        if index < 0:
            index = combo.findData(default_data)
        if index < 0:
            index = 0
        combo.setCurrentIndex(index)

    def _set_combo_float_or_default(self, combo: QComboBox, selected_value: float, default_value: float) -> None:
        index = -1
        for i in range(combo.count()):
            data = combo.itemData(i)
            try:
                if abs(float(data) - float(selected_value)) <= 0.002:
                    index = i
                    break
            except (TypeError, ValueError):
                continue
        if index < 0:
            for i in range(combo.count()):
                data = combo.itemData(i)
                try:
                    if abs(float(data) - float(default_value)) <= 0.002:
                        index = i
                        break
                except (TypeError, ValueError):
                    continue
        if index < 0:
            index = 0
        combo.setCurrentIndex(index)

    def _populate_audio_devices(self, devices: List[str], selected_device: str) -> None:
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("System Default", "")
        for name in devices:
            self.audio_device_combo.addItem(name, name)
        selected_index = 0
        for i in range(self.audio_device_combo.count()):
            if str(self.audio_device_combo.itemData(i)) == selected_device:
                selected_index = i
                break
        self.audio_device_combo.setCurrentIndex(selected_index)
        if devices:
            self.audio_device_hint.setText(f"{tr('Detected ')}{len(devices)}{tr(' output device(s).')}")
        else:
            self.audio_device_hint.setText(tr("No explicit device list detected. System Default will be used."))

    def _refresh_audio_devices(self) -> None:
        selected = self.selected_audio_output_device()
        selected_timecode = self.selected_timecode_audio_output_device()
        selected_timecode_midi = self.selected_timecode_midi_output_device()
        try:
            from pyssp.audio_engine import list_output_devices

            devices = list_output_devices()
        except Exception:
            devices = []
        self._available_audio_devices = list(devices)
        self._populate_audio_devices(self._available_audio_devices, selected)
        self.timecode_output_combo.clear()
        self.timecode_output_combo.addItem("Follow playback device setting", "follow_playback")
        self.timecode_output_combo.addItem("Use system default", "default")
        self.timecode_output_combo.addItem("None (mute output)", "none")
        for name in self._available_audio_devices:
            self.timecode_output_combo.addItem(name, name)
        self._set_combo_data_or_default(self.timecode_output_combo, selected_timecode, "none")
        self.timecode_midi_output_combo.clear()
        self.timecode_midi_output_combo.addItem("None (disabled)", MIDI_OUTPUT_DEVICE_NONE)
        for device_id, device_name in list_midi_output_devices():
            self.timecode_midi_output_combo.addItem(device_name, device_id)
        self._set_combo_data_or_default(
            self.timecode_midi_output_combo,
            selected_timecode_midi,
            MIDI_OUTPUT_DEVICE_NONE,
        )
        localize_widget_tree(self, self._ui_language)

    def _refresh_color_button(self, button: QPushButton, color_hex: str) -> None:
        button.setText(color_hex)
        button.setStyleSheet(
            "QPushButton{"
            f"background:{color_hex};"
            "border:1px solid #6C6C6C;"
            "min-height:26px;"
            "}"
        )

    def _pick_active_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.active_group_color), self, tr("Active Button Color"))
        if selected.isValid():
            self.active_group_color = selected.name().upper()
            self._refresh_color_button(self.active_color_btn, self.active_group_color)

    def _pick_inactive_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.inactive_group_color), self, tr("Inactive Button Color"))
        if selected.isValid():
            self.inactive_group_color = selected.name().upper()
            self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)

    def _pick_state_color(self, key: str, button: QPushButton, label: str) -> None:
        current = self.state_colors.get(key, "#FFFFFF")
        selected = QColorDialog.getColor(QColor(current), self, f"{tr(label)} {tr('Color')}")
        if selected.isValid():
            value = selected.name().upper()
            self.state_colors[key] = value
            self._refresh_color_button(button, value)

    def _pick_sound_text_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.sound_button_text_color), self, tr("Sound Button Text Color"))
        if selected.isValid():
            self.sound_button_text_color = selected.name().upper()
            self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)

    def _restore_defaults_current_page(self) -> None:
        idx = self.page_list.currentRow()
        item = self.page_list.item(idx) if idx >= 0 else None
        page_name = str(item.data(Qt.UserRole) if item is not None else "").strip().lower()
        if page_name == "general":
            self._restore_general_defaults()
            return
        if page_name == "language":
            self._restore_language_defaults()
            return
        if page_name == "hotkey":
            self._restore_hotkey_defaults()
            return
        if page_name == "midi control":
            self._restore_midi_defaults()
            return
        if page_name == "colour":
            self._restore_color_defaults()
            return
        if page_name == "display":
            self._restore_display_defaults()
            return
        if page_name == "fade":
            self._restore_delay_defaults()
            return
        if page_name == "playback":
            self._restore_playback_defaults()
            return
        if page_name == "dsp / plugin":
            self._restore_vst_defaults()
            return
        if page_name == "audio device / timecode":
            self._restore_audio_device_defaults()
            return
        if page_name == "audio preload":
            self._restore_preload_defaults()
            return
        if page_name == "talk":
            self._restore_talk_defaults()
            return
        if page_name == "web remote":
            self._restore_web_remote_defaults()
            return

    def _restore_language_defaults(self) -> None:
        d = self._DEFAULTS
        target = normalize_language(str(d.get("ui_language", "en")))
        index = self.ui_language_combo.findData(target)
        self.ui_language_combo.setCurrentIndex(index if index >= 0 else 0)

    def _restore_general_defaults(self) -> None:
        d = self._DEFAULTS
        self.title_limit_spin.setValue(int(d["title_char_limit"]))
        self.log_file_checkbox.setChecked(bool(d["log_file_enabled"]))
        self.reset_on_startup_checkbox.setChecked(bool(d["reset_all_on_startup"]))
        if str(d["set_file_encoding"]).strip().lower() == "gbk":
            self.set_file_encoding_gbk_radio.setChecked(True)
        else:
            self.set_file_encoding_utf8_radio.setChecked(True)
        if d["click_playing_action"] == "stop_it":
            self.playing_click_stop_radio.setChecked(True)
        else:
            self.playing_click_play_again_radio.setChecked(True)
        if d["search_double_click_action"] == "play_highlight":
            self.search_dbl_play_radio.setChecked(True)
        else:
            self.search_dbl_find_radio.setChecked(True)
        mode_token = str(d.get("main_progress_display_mode", "progress_bar")).strip().lower()
        if mode_token == "waveform":
            self.main_progress_display_waveform_radio.setChecked(True)
        else:
            self.main_progress_display_progress_bar_radio.setChecked(True)
        self.main_progress_show_text_checkbox.setChecked(bool(d.get("main_progress_show_text", True)))

    def _restore_color_defaults(self) -> None:
        d = self._DEFAULTS
        self.active_group_color = str(d["active_group_color"])
        self.inactive_group_color = str(d["inactive_group_color"])
        self._refresh_color_button(self.active_color_btn, self.active_group_color)
        self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)
        for key, value in dict(d["state_colors"]).items():
            self.state_colors[key] = value
            btn = self._state_color_buttons.get(key)
            if btn is not None:
                self._refresh_color_button(btn, value)
        self.sound_button_text_color = str(d["sound_button_text_color"])
        self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)

    def _restore_display_defaults(self) -> None:
        d = self._DEFAULTS
        self._stage_display_layout = self._normalize_stage_display_layout(list(d.get("stage_display_layout", [])))
        self._stage_display_visibility = self._normalize_stage_display_visibility(dict(d.get("stage_display_visibility", {})))
        self._stage_display_gadgets = normalize_stage_display_gadgets(
            d.get("stage_display_gadgets"),
            legacy_layout=self._stage_display_layout,
            legacy_visibility=self._stage_display_visibility,
        )
        self._set_combo_data_or_default(
            self.display_text_source_combo,
            str(d.get("stage_display_text_source", "caption")),
            "caption",
        )
        if hasattr(self, "display_layout_editor"):
            self.display_layout_editor.set_gadgets(self._stage_display_gadgets)
        if hasattr(self, "_display_gadget_checks"):
            for key, checkbox in self._display_gadget_checks.items():
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("visible", True)))
        if hasattr(self, "_display_gadget_hide_text_checks"):
            for key, checkbox in self._display_gadget_hide_text_checks.items():
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_text", False)))
        if hasattr(self, "_display_gadget_hide_border_checks"):
            for key, checkbox in self._display_gadget_hide_border_checks.items():
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_border", False)))
        if hasattr(self, "_display_gadget_orientation_combos"):
            for key, combo in self._display_gadget_orientation_combos.items():
                token = str(self._stage_display_gadgets.get(key, {}).get("orientation", "vertical")).strip().lower()
                if token not in {"horizontal", "vertical"}:
                    token = "vertical"
                combo.setCurrentIndex(max(0, combo.findData(token)))
        self._refresh_display_layer_table()
        self._sync_alert_edit_button_text()

    def _restore_hotkey_defaults(self) -> None:
        d = self._DEFAULTS
        defaults = dict(d["hotkeys"])
        for key, (edit1, edit2) in self._hotkey_edits.items():
            val1, val2 = defaults.get(key, ("", ""))
            edit1.setHotkey(val1)
            edit2.setHotkey(val2)
        self.quick_action_enabled_checkbox.setChecked(False)
        qa_defaults = default_quick_action_keys()
        for i, edit in enumerate(self._quick_action_edits):
            edit.setHotkey(qa_defaults[i] if i < len(qa_defaults) else "")
        self.sound_button_hotkey_enabled_checkbox.setChecked(bool(d["sound_button_hotkey_enabled"]))
        if str(d["sound_button_hotkey_priority"]) == "sound_button_first":
            self.sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.sound_hotkey_priority_system_first_radio.setChecked(True)
        self.sound_button_go_to_playing_checkbox.setChecked(bool(d["sound_button_hotkey_go_to_playing"]))
        self._validate_hotkey_conflicts()

    def _restore_midi_defaults(self) -> None:
        d = self._DEFAULTS
        self._midi_input_device_ids = list(d.get("midi_input_device_ids", []))
        self._refresh_midi_input_devices()
        defaults = dict(d.get("midi_hotkeys", {}))
        for key, (edit1, edit2) in self._midi_hotkey_edits.items():
            v1, v2 = defaults.get(key, ("", ""))
            edit1.setBinding(v1)
            edit2.setBinding(v2)
        self.midi_quick_action_enabled_checkbox.setChecked(bool(d.get("midi_quick_action_enabled", False)))
        midi_quick_defaults = list(d.get("midi_quick_action_bindings", [""] * 48))
        for i, edit in enumerate(self._midi_quick_action_edits):
            edit.setBinding(midi_quick_defaults[i] if i < len(midi_quick_defaults) else "")
        self.midi_sound_button_hotkey_enabled_checkbox.setChecked(bool(d.get("midi_sound_button_hotkey_enabled", False)))
        if str(d.get("midi_sound_button_hotkey_priority", "system_first")) == "sound_button_first":
            self.midi_sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.midi_sound_hotkey_priority_system_first_radio.setChecked(True)
        self.midi_sound_button_go_to_playing_checkbox.setChecked(bool(d.get("midi_sound_button_hotkey_go_to_playing", False)))
        self.midi_rotary_enabled_checkbox.setChecked(bool(d.get("midi_rotary_enabled", False)))
        self.midi_rotary_group_edit.setBinding(str(d.get("midi_rotary_group_binding", "")))
        self.midi_rotary_page_edit.setBinding(str(d.get("midi_rotary_page_binding", "")))
        self.midi_rotary_sound_button_edit.setBinding(str(d.get("midi_rotary_sound_button_binding", "")))
        self.midi_rotary_jog_edit.setBinding(str(d.get("midi_rotary_jog_binding", "")))
        self.midi_rotary_volume_edit.setBinding(str(d.get("midi_rotary_volume_binding", "")))
        self.midi_rotary_group_invert_checkbox.setChecked(bool(d.get("midi_rotary_group_invert", False)))
        self.midi_rotary_page_invert_checkbox.setChecked(bool(d.get("midi_rotary_page_invert", False)))
        self.midi_rotary_sound_button_invert_checkbox.setChecked(bool(d.get("midi_rotary_sound_button_invert", False)))
        self.midi_rotary_jog_invert_checkbox.setChecked(bool(d.get("midi_rotary_jog_invert", False)))
        self.midi_rotary_volume_invert_checkbox.setChecked(bool(d.get("midi_rotary_volume_invert", False)))
        self.midi_rotary_group_sensitivity_spin.setValue(int(d.get("midi_rotary_group_sensitivity", 1)))
        self.midi_rotary_page_sensitivity_spin.setValue(int(d.get("midi_rotary_page_sensitivity", 1)))
        self.midi_rotary_sound_button_sensitivity_spin.setValue(int(d.get("midi_rotary_sound_button_sensitivity", 1)))
        self._midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_group_relative_mode", "auto"))
        )
        self._midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_page_relative_mode", "auto"))
        )
        self._midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_sound_button_relative_mode", "auto"))
        )
        self._midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_jog_relative_mode", "auto"))
        )
        self._midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_volume_relative_mode", "auto"))
        )
        self._set_combo_data_or_default(self.midi_rotary_volume_mode_combo, str(d.get("midi_rotary_volume_mode", "relative")), "relative")
        self.midi_rotary_volume_step_spin.setValue(int(d.get("midi_rotary_volume_step", 2)))
        self.midi_rotary_jog_step_spin.setValue(int(d.get("midi_rotary_jog_step_ms", 250)))
        self._validate_midi_conflicts()

    def _normalize_hotkey_for_conflict(self, raw: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return ""
        aliases = {
            "control": "Ctrl",
            "ctrl": "Ctrl",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Meta",
            "win": "Meta",
            "super": "Meta",
        }
        lower = text.lower()
        if lower in aliases:
            return aliases[lower]
        canonical = QKeySequence(text).toString().strip()
        return canonical or text

    def _validate_hotkey_conflicts(self) -> None:
        seen: Dict[str, tuple[str, int]] = {}
        conflicts: List[str] = []
        conflict_cells: set[tuple[str, int]] = set()
        for key, (edit1, edit2) in self._hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                token = self._normalize_hotkey_for_conflict(edit.hotkey())
                if not token:
                    continue
                if token in seen:
                    prev_key, prev_slot_index = seen[token]
                    conflict_cells.add((prev_key, prev_slot_index))
                    conflict_cells.add((key, slot_index))
                    left = f"{tr(self._hotkey_labels.get(prev_key, prev_key))} ({prev_slot_index})"
                    right = f"{tr(self._hotkey_labels.get(key, key))} ({slot_index})"
                    conflicts.append(f"{token}: {left} {tr('and')} {right}")
                else:
                    seen[token] = (key, slot_index)

        quick_enabled = bool(self.quick_action_enabled_checkbox.isChecked())
        quick_conflict_rows: set[int] = set()
        if quick_enabled:
            for idx, edit in enumerate(self._quick_action_edits):
                token = self._normalize_hotkey_for_conflict(edit.hotkey())
                if not token:
                    continue
                mark = ("quick_action", idx + 1)
                if token in seen:
                    prev_key, prev_slot_index = seen[token]
                    conflict_cells.add((prev_key, prev_slot_index))
                    conflicts.append(
                        f"{token}: {self._describe_conflict_target(prev_key, prev_slot_index)} {tr('and')} {tr('Quick Action')} ({idx + 1})"
                    )
                    quick_conflict_rows.add(idx)
                    if prev_key == "quick_action":
                        quick_conflict_rows.add(max(0, prev_slot_index - 1))
                else:
                    seen[token] = mark

        for idx, edit in enumerate(self._quick_action_edits):
            if quick_enabled and idx in quick_conflict_rows:
                edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
            else:
                edit.setStyleSheet("")

        for key, (edit1, edit2) in self._hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                if (key, slot_index) in conflict_cells:
                    edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
                else:
                    edit.setStyleSheet("")

        has_conflict = bool(conflicts)
        if self.ok_button is not None:
            midi_conflict = bool(self._midi_has_conflict)
            self.ok_button.setEnabled((not has_conflict) and (not midi_conflict))
        if self.hotkey_warning_label is None:
            return
        if not has_conflict:
            self.hotkey_warning_label.setVisible(False)
            self.hotkey_warning_label.setText("")
            return
        display = "; ".join(conflicts[:4])
        if len(conflicts) > 4:
            display += f"; +{len(conflicts) - 4} {tr('more')}"
        self.hotkey_warning_label.setText(f"{tr('Hotkey conflict detected. Fix duplicates before saving.')} {display}")
        self.hotkey_warning_label.setVisible(True)

    def _validate_midi_conflicts(self) -> None:
        seen: Dict[str, List[tuple[str, int, str]]] = {}
        conflicts: List[str] = []
        conflict_cells: set[tuple[str, int]] = set()
        for key, (edit1, edit2) in self._midi_hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                token = normalize_midi_binding(edit.binding())
                if not token:
                    continue
                selector, msg = split_midi_binding(token)
                entries = seen.setdefault(msg, [])
                for prev_key, prev_slot_index, prev_selector in entries:
                    if (
                        (not prev_selector)
                        or (not selector)
                        or (prev_selector == selector)
                    ):
                        conflict_cells.add((prev_key, prev_slot_index))
                        conflict_cells.add((key, slot_index))
                        left = f"{tr(self._hotkey_labels.get(prev_key, prev_key))} ({prev_slot_index})"
                        right = f"{tr(self._hotkey_labels.get(key, key))} ({slot_index})"
                        conflicts.append(f"{token}: {left} {tr('and')} {right}")
                entries.append((key, slot_index, selector))

        quick_enabled = bool(self.midi_quick_action_enabled_checkbox.isChecked())
        quick_conflict_rows: set[int] = set()
        if quick_enabled:
            for idx, edit in enumerate(self._midi_quick_action_edits):
                token = normalize_midi_binding(edit.binding())
                if not token:
                    continue
                selector, msg = split_midi_binding(token)
                entries = seen.setdefault(msg, [])
                row_has_conflict = False
                for prev_key, prev_slot_index, prev_selector in entries:
                    if (
                        (not prev_selector)
                        or (not selector)
                        or (prev_selector == selector)
                    ):
                        conflict_cells.add((prev_key, prev_slot_index))
                        conflicts.append(
                            f"{token}: {self._describe_conflict_target(prev_key, prev_slot_index)} {tr('and')} {tr('Quick Action')} ({idx + 1})"
                        )
                        row_has_conflict = True
                        if prev_key == "midi_quick_action":
                            quick_conflict_rows.add(max(0, prev_slot_index - 1))
                if row_has_conflict:
                    quick_conflict_rows.add(idx)
                entries.append(("midi_quick_action", idx + 1, selector))

        for idx, edit in enumerate(self._midi_quick_action_edits):
            if quick_enabled and idx in quick_conflict_rows:
                edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
            elif self._learning_midi_target is not edit:
                edit.setStyleSheet("")
        for key, (edit1, edit2) in self._midi_hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                if (key, slot_index) in conflict_cells:
                    edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
                elif self._learning_midi_target is not edit:
                    edit.setStyleSheet("")

        has_conflict = bool(conflicts)
        self._midi_has_conflict = has_conflict
        if self._midi_warning_label is not None:
            if has_conflict:
                display = "; ".join(conflicts[:4])
                if len(conflicts) > 4:
                    display += f"; +{len(conflicts) - 4} {tr('more')}"
                self._midi_warning_label.setStyleSheet("color:#B00020; font-weight:bold;")
                self._midi_warning_label.setText(f"MIDI conflict detected. Fix duplicates before saving. {display}")
                self._midi_warning_label.setVisible(True)
            else:
                if self._learning_midi_rotary_target is None:
                    self._midi_warning_label.setVisible(False)
                    self._midi_warning_label.setText("")
        if self.ok_button is not None and self.hotkey_warning_label is not None:
            keyboard_conflict = self.hotkey_warning_label.isVisible()
            self.ok_button.setEnabled((not keyboard_conflict) and (not has_conflict))

    def _describe_conflict_target(self, key: str, slot_index: int) -> str:
        if key in {"quick_action", "midi_quick_action"}:
            return f"{tr('Quick Action')} ({slot_index})"
        return f"{tr(self._hotkey_labels.get(key, key))} ({slot_index})"

    def _restore_delay_defaults(self) -> None:
        d = self._DEFAULTS
        self.fade_on_quick_action_checkbox.setChecked(bool(d["fade_on_quick_action_hotkey"]))
        self.fade_on_sound_hotkey_checkbox.setChecked(bool(d["fade_on_sound_button_hotkey"]))
        self.fade_on_pause_checkbox.setChecked(bool(d["fade_on_pause"]))
        self.fade_on_resume_checkbox.setChecked(bool(d["fade_on_resume"]))
        self.fade_on_stop_checkbox.setChecked(bool(d["fade_on_stop"]))
        self.fade_in_spin.setValue(float(d["fade_in_sec"]))
        self.fade_out_spin.setValue(float(d["fade_out_sec"]))
        self.fade_out_when_done_checkbox.setChecked(bool(d["fade_out_when_done_playing"]))
        self.fade_out_end_lead_spin.setValue(float(d["fade_out_end_lead_sec"]))
        self.cross_fade_spin.setValue(float(d["cross_fade_sec"]))
        self._sync_fade_out_end_lead_enabled()

    def _restore_playback_defaults(self) -> None:
        d = self._DEFAULTS
        self.max_multi_play_spin.setValue(int(d["max_multi_play_songs"]))
        if d["multi_play_limit_action"] == "disallow_more_play":
            self.multi_play_disallow_radio.setChecked(True)
        else:
            self.multi_play_stop_oldest_radio.setChecked(True)
        if str(d["playlist_play_mode"]) == "any_available":
            self.playlist_mode_any_radio.setChecked(True)
        else:
            self.playlist_mode_unplayed_radio.setChecked(True)
        if str(d["rapid_fire_play_mode"]) == "any_available":
            self.rapid_fire_mode_any_radio.setChecked(True)
        else:
            self.rapid_fire_mode_unplayed_radio.setChecked(True)
        if str(d["next_play_mode"]) == "any_available":
            self.next_mode_any_radio.setChecked(True)
        else:
            self.next_mode_unplayed_radio.setChecked(True)
        if str(d["playlist_loop_mode"]) == "loop_single":
            self.playlist_loop_single_radio.setChecked(True)
        else:
            self.playlist_loop_list_radio.setChecked(True)
        if str(d["candidate_error_action"]) == "keep_playing":
            self.candidate_error_keep_radio.setChecked(True)
        else:
            self.candidate_error_stop_radio.setChecked(True)
        if d["main_transport_timeline_mode"] == "audio_file":
            self.cue_timeline_audio_file_radio.setChecked(True)
        else:
            self.cue_timeline_cue_region_radio.setChecked(True)
        action = str(d["main_jog_outside_cue_action"])
        if action == "ignore_cue":
            self.jog_outside_ignore_cue_radio.setChecked(True)
        elif action == "next_cue_or_stop":
            self.jog_outside_next_cue_or_stop_radio.setChecked(True)
        elif action == "stop_cue_or_end":
            self.jog_outside_stop_cue_or_end_radio.setChecked(True)
        else:
            self.jog_outside_stop_immediately_radio.setChecked(True)
        self._sync_jog_outside_group_enabled()

    def _restore_vst_defaults(self) -> None:
        d = self._DEFAULTS
        self.vst_enabled_checkbox.setChecked(bool(d.get("vst_enabled", False)) and self._vst_supported)
        self._vst_directories = effective_vst_directories(list(d.get("vst_directories", [])))
        self._vst_known_plugins = [str(v).strip() for v in list(d.get("vst_known_plugins", [])) if str(v).strip()]
        self._vst_enabled_plugins = {str(v).strip() for v in list(d.get("vst_enabled_plugins", [])) if str(v).strip()}
        self._vst_chain = [str(v).strip() for v in list(d.get("vst_chain", [])) if str(v).strip()]
        self._vst_plugin_state = {
            str(k).strip(): dict(v)
            for k, v in dict(d.get("vst_plugin_state", {})).items()
            if str(k).strip() and isinstance(v, dict)
        }
        self._refresh_vst_directory_list()
        self._refresh_vst_plugin_list()
        self._sync_vst_controls_enabled()

    def _restore_audio_device_defaults(self) -> None:
        d = self._DEFAULTS
        self._set_combo_data_or_default(self.audio_device_combo, "", "")
        self._set_combo_data_or_default(
            self.timecode_output_combo,
            str(d["timecode_audio_output_device"]),
            "none",
        )
        self._set_combo_data_or_default(
            self.timecode_mode_combo,
            str(d["timecode_mode"]),
            TIMECODE_MODE_FOLLOW,
        )
        self._set_combo_float_or_default(
            self.timecode_fps_combo,
            float(d["timecode_fps"]),
            30.0,
        )
        self._set_combo_float_or_default(
            self.timecode_mtc_fps_combo,
            float(d["timecode_mtc_fps"]),
            30.0,
        )
        self._set_combo_data_or_default(
            self.timecode_mtc_idle_behavior_combo,
            str(d["timecode_mtc_idle_behavior"]),
            "keep_stream",
        )
        self._set_combo_data_or_default(
            self.timecode_midi_output_combo,
            str(d["timecode_midi_output_device"]),
            MIDI_OUTPUT_DEVICE_NONE,
        )
        self._set_combo_data_or_default(
            self.timecode_sample_rate_combo,
            int(d["timecode_sample_rate"]),
            48000,
        )
        self._set_combo_data_or_default(
            self.timecode_bit_depth_combo,
            int(d["timecode_bit_depth"]),
            16,
        )
        if str(d["timecode_timeline_mode"]) == "audio_file":
            self.timecode_timeline_audio_file_radio.setChecked(True)
        else:
            self.timecode_timeline_cue_region_radio.setChecked(True)

    def _restore_preload_defaults(self) -> None:
        d = self._DEFAULTS
        self.preload_audio_enabled_checkbox.setChecked(bool(d["preload_audio_enabled"]))
        self.preload_current_page_checkbox.setChecked(bool(d["preload_current_page_audio"]))
        self.preload_memory_pressure_checkbox.setChecked(bool(d["preload_memory_pressure_enabled"]))
        self.preload_pause_on_playback_checkbox.setChecked(bool(d["preload_pause_on_playback"]))
        step_mb = int(self._preload_slider_step_mb)
        target_mb = max(step_mb, min(int(self._preload_ram_cap_mb), int(d["preload_audio_memory_limit_mb"])))
        self.preload_memory_slider.setValue(max(1, target_mb // step_mb))
        self._update_preload_slider_label()

    def _restore_talk_defaults(self) -> None:
        d = self._DEFAULTS
        self.talk_volume_spin.setValue(int(d["talk_volume_level"]))
        self.talk_fade_spin.setValue(float(d["talk_fade_sec"]))
        self.talk_blink_checkbox.setChecked(bool(d["talk_blink_button"]))
        mode = str(d["talk_volume_mode"])
        if mode == "set_exact":
            self.talk_mode_force_radio.setChecked(True)
        elif mode == "lower_only":
            self.talk_mode_lower_only_radio.setChecked(True)
        else:
            self.talk_mode_percent_radio.setChecked(True)

    def _restore_web_remote_defaults(self) -> None:
        d = self._DEFAULTS
        self.web_remote_enabled_checkbox.setChecked(bool(d["web_remote_enabled"]))
        self.web_remote_port_spin.setValue(int(d["web_remote_port"]))
