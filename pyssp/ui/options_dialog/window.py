from __future__ import annotations

from .shared import *
from .widgets import *
from .device_midi import DeviceMidiMixin
from .layout_helpers import LayoutHelpersMixin
from .page_builders import PageBuilderMixin
from .selections import SelectionMixin
from .state_logic import StateLogicMixin

class OptionsDialog(
    PageBuilderMixin,
    LayoutHelpersMixin,
    SelectionMixin,
    DeviceMidiMixin,
    StateLogicMixin,
    QDialog,
):
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
        ("lock_toggle", "Lock / Unlock"),
        ("open_hide_lyric_navigator", "Open / Hide Lyric Navigator"),
    ]

    _DEFAULTS = {
        "active_group_color": "#EDE8C8",
        "inactive_group_color": "#ECECEC",
        "title_char_limit": 26,
        "show_file_notifications": True,
        "now_playing_display_mode": "caption",
        "main_ui_lyric_display_mode": "always",
        "search_lyric_on_add_sound_button": True,
        "new_lyric_file_format": "srt",
        "supported_audio_format_extensions": [],
        "verify_sound_file_on_add": True,
        "allow_other_unsupported_audio_files": False,
        "disable_path_safety": False,
        "log_file_enabled": False,
        "reset_all_on_startup": False,
        "click_playing_action": "play_it_again",
        "search_double_click_action": "find_highlight",
        "set_file_encoding": "utf8",
        "main_progress_display_mode": "progress_bar",
        "main_progress_show_text": True,
        "ui_language": "en",
        "lock_allow_quit": True,
        "lock_allow_system_hotkeys": False,
        "lock_allow_quick_action_hotkeys": False,
        "lock_allow_sound_button_hotkeys": False,
        "lock_allow_midi_control": True,
        "lock_auto_allow_quit": True,
        "lock_auto_allow_midi_control": True,
        "lock_unlock_method": "click_3_random_points",
        "lock_require_password": False,
        "lock_password": "",
        "lock_restart_state": "unlock_on_restart",
        "preload_audio_enabled": False,
        "preload_current_page_audio": True,
        "preload_audio_memory_limit_mb": 512,
        "preload_memory_pressure_enabled": True,
        "preload_pause_on_playback": True,
        "preload_use_ffmpeg": True,
        "waveform_cache_limit_mb": 1024,
        "waveform_cache_clear_on_launch": True,
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
        "vocal_removed_toggle_fade_mode": "follow_cross_fade",
        "vocal_removed_toggle_custom_sec": 1.0,
        "vocal_removed_toggle_always_sec": 1.0,
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
        "web_remote_ws_port": 5051,
        "timecode_audio_output_device": "none",
        "timecode_midi_output_device": MIDI_OUTPUT_DEVICE_NONE,
        "timecode_mode": TIMECODE_MODE_FOLLOW,
        "timecode_fps": 30.0,
        "timecode_mtc_fps": 30.0,
        "timecode_mtc_idle_behavior": MTC_IDLE_KEEP_STREAM,
        "timecode_sample_rate": 48000,
        "timecode_bit_depth": 16,
        "timecode_timeline_mode": "cue_region",
        "soundbutton_timecode_offset_enabled": True,
        "respect_soundbutton_timecode_timeline_setting": True,
        "state_colors": {
            "playing": "#66FF33",
            "played": "#FF3B30",
            "unplayed": "#B0B0B0",
            "highlight": "#A6D8FF",
            "lock": "#F2D74A",
            "error": "#7B3FB3",
            "place_marker": "#D0D0D0",
            "empty": "#0B868A",
            "copied_to_cue": "#2E65FF",
            "cue_indicator": "#61D6FF",
            "volume_indicator": "#FFD45A",
            "vocal_removed_indicator": "#8E7CFF",
            "midi_indicator": "#FF9E4A",
            "lyric_indicator": "#57C3A4",
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
            "lock_toggle": ("Ctrl+L", ""),
            "open_hide_lyric_navigator": ("", ""),
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
            "lyric",
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
            "lyric": True,
            "next_song": True,
        },
        "stage_display_text_source": "caption",
        "stage_display_gadgets": normalize_stage_display_gadgets(None),
        "window_layout": default_window_layout(),
    }
    _DISPLAY_OPTION_SPECS = STAGE_DISPLAY_GADGET_SPECS

    def __init__(
        self,
        active_group_color: str,
        inactive_group_color: str,
        title_char_limit: int,
        show_file_notifications: bool,
        now_playing_display_mode: str,
        main_ui_lyric_display_mode: str,
        search_lyric_on_add_sound_button: bool,
        new_lyric_file_format: str,
        supported_audio_format_extensions: List[str],
        verify_sound_file_on_add: bool,
        allow_other_unsupported_audio_files: bool,
        disable_path_safety: bool,
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
        *,
        vocal_removed_toggle_fade_mode: str = "follow_cross_fade",
        vocal_removed_toggle_custom_sec: float = 1.0,
        vocal_removed_toggle_always_sec: float = 1.0,
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
        soundbutton_timecode_offset_enabled: bool,
        respect_soundbutton_timecode_timeline_setting: bool,
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
        window_layout: Optional[Dict[str, object]],
        ui_language: str,
        lock_allow_quit: bool,
        lock_allow_system_hotkeys: bool,
        lock_allow_quick_action_hotkeys: bool,
        lock_allow_sound_button_hotkeys: bool,
        lock_allow_midi_control: bool,
        lock_auto_allow_quit: bool,
        lock_auto_allow_midi_control: bool,
        lock_unlock_method: str,
        lock_require_password: bool,
        lock_password: str,
        lock_restart_state: str,
        preload_use_ffmpeg: bool = True,
        waveform_cache_limit_mb: int = 1024,
        waveform_cache_clear_on_launch: bool = True,
        is_playback_or_loading_active: Optional[Callable[[], bool]] = None,
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
        self._lock_existing_password = str(lock_password or "")
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
        self._window_layout = normalize_window_layout(window_layout)
        self._window_layout_drop_in_progress = False
        self._window_layout_capture_pending = False
        self._main_ui_lyric_display_mode = (
            str(main_ui_lyric_display_mode or "").strip().lower()
            if str(main_ui_lyric_display_mode or "").strip().lower() in {"always", "when_available", "never"}
            else "always"
        )
        self._search_lyric_on_add_sound_button = bool(search_lyric_on_add_sound_button)
        self._new_lyric_file_format = (
            str(new_lyric_file_format or "").strip().lower()
            if str(new_lyric_file_format or "").strip().lower() in {"srt", "lrc"}
            else "srt"
        )
        self._supported_audio_format_extensions = [
            str(token).strip().lower()
            for token in supported_audio_format_extensions
            if str(token).strip()
        ]
        self._verify_sound_file_on_add = bool(verify_sound_file_on_add)
        self._allow_other_unsupported_audio_files = bool(allow_other_unsupported_audio_files)
        self._disable_path_safety = bool(disable_path_safety)
        self._is_playback_or_loading_active = is_playback_or_loading_active
        self._hotkey_labels: Dict[str, str] = {key: label for key, label in self._HOTKEY_ROWS}
        self.hotkey_warning_label: Optional[QLabel] = None
        self.ok_button: Optional[QPushButton] = None
        self.state_colors = dict(state_colors)
        self._state_color_buttons: Dict[str, QPushButton] = {}
        self._available_audio_devices = list(available_audio_devices)
        self._available_midi_devices = list(available_midi_devices)

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
                now_playing_display_mode=now_playing_display_mode,
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
            "Lock Screen",
            self._mono_icon("lock"),
            self._build_lock_screen_page(
                lock_allow_quit=lock_allow_quit,
                lock_allow_system_hotkeys=lock_allow_system_hotkeys,
                lock_allow_quick_action_hotkeys=lock_allow_quick_action_hotkeys,
                lock_allow_sound_button_hotkeys=lock_allow_sound_button_hotkeys,
                lock_allow_midi_control=lock_allow_midi_control,
                lock_auto_allow_quit=lock_auto_allow_quit,
                lock_auto_allow_midi_control=lock_auto_allow_midi_control,
                lock_unlock_method=lock_unlock_method,
                lock_require_password=lock_require_password,
                lock_password=lock_password,
                lock_restart_state=lock_restart_state,
            ),
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
            "Stage Display",
            self._mono_icon("projector"),
            self._build_display_page(),
        )
        self._add_page(
            "Lyric",
            self._mono_icon("lyric"),
            self._build_lyric_page(
                main_ui_lyric_display_mode=self._main_ui_lyric_display_mode,
                search_lyric_on_add_sound_button=self._search_lyric_on_add_sound_button,
                new_lyric_file_format=self._new_lyric_file_format,
            ),
        )
        self._add_page(
            "Window Layout",
            self._mono_icon("layout"),
            self._build_window_layout_page(),
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
                vocal_removed_toggle_fade_mode=vocal_removed_toggle_fade_mode,
                vocal_removed_toggle_custom_sec=vocal_removed_toggle_custom_sec,
                vocal_removed_toggle_always_sec=vocal_removed_toggle_always_sec,
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
            "Audio Device & Timecode",
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
                soundbutton_timecode_offset_enabled=soundbutton_timecode_offset_enabled,
                respect_soundbutton_timecode_timeline_setting=respect_soundbutton_timecode_timeline_setting,
            ),
        )
        self._add_page(
            "Audio Loading & Format",
            self._mono_icon("ram"),
            self._build_audio_preload_page(
                preload_audio_enabled=preload_audio_enabled,
                preload_current_page_audio=preload_current_page_audio,
                preload_audio_memory_limit_mb=preload_audio_memory_limit_mb,
                preload_memory_pressure_enabled=preload_memory_pressure_enabled,
                preload_pause_on_playback=preload_pause_on_playback,
                preload_use_ffmpeg=preload_use_ffmpeg,
                waveform_cache_limit_mb=waveform_cache_limit_mb,
                waveform_cache_clear_on_launch=waveform_cache_clear_on_launch,
                preload_total_ram_mb=preload_total_ram_mb,
                preload_ram_cap_mb=preload_ram_cap_mb,
                supported_audio_format_extensions=self._supported_audio_format_extensions,
                verify_sound_file_on_add=self._verify_sound_file_on_add,
                allow_other_unsupported_audio_files=self._allow_other_unsupported_audio_files,
                disable_path_safety=self._disable_path_safety,
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
        self._validate_lock_page()
        localize_widget_tree(self, self._ui_language)



__all__ = ["OptionsDialog"]
