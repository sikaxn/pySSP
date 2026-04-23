from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *
from .actions_input import ActionsInputMixin
from .locking import LockingMixin
from .lyrics_stage import LyricsStageMixin
from .pages_slots import PagesSlotsMixin
from .playback import PlaybackMixin
from .remote_api import RemoteApiMixin
from .settings_archive import SettingsArchiveMixin
from .timecode import TimecodeMixin
from .tools_library import ToolsLibraryMixin
from .ui_build import UiBuildMixin


class MainWindow(
    UiBuildMixin,
    TimecodeMixin,
    SettingsArchiveMixin,
    ToolsLibraryMixin,
    PagesSlotsMixin,
    PlaybackMixin,
    LyricsStageMixin,
    RemoteApiMixin,
    ActionsInputMixin,
    LockingMixin,
    QMainWindow,
):
    def __init__(self) -> None:
        super().__init__()
        self._suspend_settings_save = True
        self.app_version_text = get_display_version()
        self.app_build_text = get_display_build_id()
        self.app_title_base = get_app_title_base()
        self.setWindowTitle(self.app_title_base)
        self.resize(1360, 900)
        self.settings: AppSettings = load_settings()
        self.ui_language = normalize_language(getattr(self.settings, "ui_language", "en"))
        set_current_language(self.ui_language)

        self.current_group = "A"
        self.current_page = 0
        self.current_playing: Optional[Tuple[str, int, int]] = None
        self.current_playlist_start: Optional[int] = None
        self._auto_transition_track: Optional[Tuple[str, int, int]] = None
        self._auto_transition_done = False
        self._pending_start_request: Optional[Tuple[str, int, int]] = None
        self._pending_start_token = 0
        self._pending_deferred_audio_request: Optional[Tuple[str, int, int, str, float]] = None
        self._pending_deferred_audio_token = 0
        self._pending_player_media_loads: Dict[int, dict] = {}
        self.current_duration_ms = 0
        self._main_progress_waveform: List[float] = []
        self._main_waveform_request_token = 0
        self._main_waveform_future: Optional[Future] = None
        self._main_waveform_future_token = 0
        self._main_waveform_future_key: Optional[Tuple[str, int, int]] = None
        self.loop_enabled = False
        self.play_vocal_removed_tracks = False
        self._manual_stop_requested = False
        self.talk_active = False
        self._fade_jobs: List[dict] = []
        self._vocal_toggle_fade_jobs: Dict[int, dict] = {}
        self._player_mix_volume_map: Dict[int, int] = {}
        self._vocal_shadow_players: Dict[int, ExternalMediaPlayer] = {}
        self._fade_flash_on = False
        self._last_fade_flash_toggle = 0.0
        self._stop_fade_armed = False
        self.active_group_color = self.settings.active_group_color
        self.inactive_group_color = self.settings.inactive_group_color
        self.title_char_limit = self.settings.title_char_limit
        self.show_file_notifications = self.settings.show_file_notifications
        self.lock_allow_quit = bool(getattr(self.settings, "lock_allow_quit", False))
        self.lock_allow_system_hotkeys = bool(getattr(self.settings, "lock_allow_system_hotkeys", False))
        self.lock_allow_quick_action_hotkeys = bool(getattr(self.settings, "lock_allow_quick_action_hotkeys", False))
        self.lock_allow_sound_button_hotkeys = bool(getattr(self.settings, "lock_allow_sound_button_hotkeys", False))
        self.lock_allow_midi_control = bool(getattr(self.settings, "lock_allow_midi_control", False))
        self.lock_auto_allow_quit = bool(getattr(self.settings, "lock_auto_allow_quit", True))
        self.lock_auto_allow_midi_control = bool(getattr(self.settings, "lock_auto_allow_midi_control", True))
        self.lock_unlock_method = str(getattr(self.settings, "lock_unlock_method", "click_3_random_points")).strip().lower()
        if self.lock_unlock_method not in {"click_3_random_points", "click_one_button", "slide_to_unlock"}:
            self.lock_unlock_method = "click_3_random_points"
        self.lock_require_password = bool(getattr(self.settings, "lock_require_password", False))
        self.lock_password = str(getattr(self.settings, "lock_password", ""))
        self.lock_restart_state = str(getattr(self.settings, "lock_restart_state", "unlock_on_restart")).strip().lower()
        if self.lock_restart_state not in {"unlock_on_restart", "lock_on_restart"}:
            self.lock_restart_state = "unlock_on_restart"
        self.fade_in_sec = self.settings.fade_in_sec
        self.cross_fade_sec = self.settings.cross_fade_sec
        self.fade_out_sec = self.settings.fade_out_sec
        self.fade_on_quick_action_hotkey = bool(self.settings.fade_on_quick_action_hotkey)
        self.fade_on_sound_button_hotkey = bool(self.settings.fade_on_sound_button_hotkey)
        self.fade_on_pause = bool(self.settings.fade_on_pause)
        self.fade_on_resume = bool(self.settings.fade_on_resume)
        self.fade_on_stop = bool(self.settings.fade_on_stop)
        self.fade_out_when_done_playing = bool(self.settings.fade_out_when_done_playing)
        self.fade_out_end_lead_sec = max(0.0, float(self.settings.fade_out_end_lead_sec))
        self.vocal_removed_toggle_fade_mode = str(
            getattr(self.settings, "vocal_removed_toggle_fade_mode", "follow_cross_fade")
        ).strip().lower()
        if self.vocal_removed_toggle_fade_mode not in {
            "follow_cross_fade",
            "follow_cross_fade_custom",
            "never",
            "always",
        }:
            self.vocal_removed_toggle_fade_mode = "follow_cross_fade"
        self.vocal_removed_toggle_custom_sec = max(
            0.0,
            min(20.0, float(getattr(self.settings, "vocal_removed_toggle_custom_sec", 1.0))),
        )
        self.vocal_removed_toggle_always_sec = max(
            0.0,
            min(20.0, float(getattr(self.settings, "vocal_removed_toggle_always_sec", 1.0))),
        )
        self.talk_volume_level = self.settings.talk_volume_level
        self.talk_fade_sec = self.settings.talk_fade_sec
        self.talk_volume_mode = (
            self.settings.talk_volume_mode
            if self.settings.talk_volume_mode in {"percent_of_master", "lower_only", "set_exact"}
            else "percent_of_master"
        )
        self.talk_blink_button = self.settings.talk_blink_button
        self.log_file_enabled = self.settings.log_file_enabled
        self.reset_all_on_startup = self.settings.reset_all_on_startup
        self.click_playing_action = self.settings.click_playing_action
        self.search_double_click_action = self.settings.search_double_click_action
        self.set_file_encoding = self.settings.set_file_encoding or "utf8"
        if self.set_file_encoding not in {"utf8", "gbk"}:
            self.set_file_encoding = "utf8"
        self.tips_open_on_startup = bool(getattr(self.settings, "tips_open_on_startup", True))
        self.audio_output_device = self.settings.audio_output_device
        _preload_total_mb, _preload_reserved_mb, _preload_cap_mb = get_preload_memory_limits_mb()
        self.preload_audio_enabled = bool(getattr(self.settings, "preload_audio_enabled", False))
        self.preload_current_page_audio = bool(getattr(self.settings, "preload_current_page_audio", True))
        self.preload_audio_memory_limit_mb = max(
            64,
            min(int(_preload_cap_mb), int(getattr(self.settings, "preload_audio_memory_limit_mb", 512))),
        )
        self.preload_memory_pressure_enabled = bool(
            getattr(self.settings, "preload_memory_pressure_enabled", True)
        )
        self.preload_pause_on_playback = bool(getattr(self.settings, "preload_pause_on_playback", True))
        self.preload_use_ffmpeg = bool(getattr(self.settings, "preload_use_ffmpeg", True))
        self.waveform_cache_limit_mb = max(128, min(16384, int(getattr(self.settings, "waveform_cache_limit_mb", 1024))))
        self.waveform_cache_clear_on_launch = bool(getattr(self.settings, "waveform_cache_clear_on_launch", True))
        self._preload_runtime_paused = False
        configure_audio_preload_cache_policy(
            self.preload_audio_enabled,
            self.preload_audio_memory_limit_mb,
            self.preload_memory_pressure_enabled,
            self.preload_use_ffmpeg,
        )
        configure_waveform_disk_cache(self.waveform_cache_limit_mb)
        self.max_multi_play_songs = self.settings.max_multi_play_songs
        self.multi_play_limit_action = self.settings.multi_play_limit_action
        self.playlist_play_mode = (
            self.settings.playlist_play_mode
            if self.settings.playlist_play_mode in {"unplayed_only", "any_available"}
            else "unplayed_only"
        )
        self.rapid_fire_play_mode = (
            self.settings.rapid_fire_play_mode
            if self.settings.rapid_fire_play_mode in {"unplayed_only", "any_available"}
            else "unplayed_only"
        )
        self.next_play_mode = (
            self.settings.next_play_mode
            if self.settings.next_play_mode in {"unplayed_only", "any_available"}
            else "unplayed_only"
        )
        self.playlist_loop_mode = (
            self.settings.playlist_loop_mode
            if self.settings.playlist_loop_mode in {"loop_list", "loop_single"}
            else "loop_list"
        )
        self.candidate_error_action = (
            self.settings.candidate_error_action
            if self.settings.candidate_error_action in {"stop_playback", "keep_playing"}
            else "stop_playback"
        )
        self.web_remote_enabled = self.settings.web_remote_enabled
        self.web_remote_host = "0.0.0.0"
        self.web_remote_port = max(1, min(65534, int(self.settings.web_remote_port or 5050)))
        self.web_remote_ws_port = int(self.web_remote_port) + 1
        self._local_ip_cache = "127.0.0.1"
        self._local_ip_cache_at = 0.0
        self.timecode_audio_output_device = self.settings.timecode_audio_output_device or "none"
        self.timecode_midi_output_device = self.settings.timecode_midi_output_device or MIDI_OUTPUT_DEVICE_NONE
        self.timecode_mode = self.settings.timecode_mode or TIMECODE_MODE_FOLLOW
        if self.timecode_mode not in {
            TIMECODE_MODE_ZERO,
            TIMECODE_MODE_FOLLOW,
            TIMECODE_MODE_SYSTEM,
            TIMECODE_MODE_FOLLOW_FREEZE,
        }:
            self.timecode_mode = TIMECODE_MODE_FOLLOW
        self.timecode_fps = max(1.0, float(self.settings.timecode_fps or 30.0))
        self.timecode_mtc_fps = max(1.0, float(self.settings.timecode_mtc_fps or 30.0))
        self.timecode_mtc_idle_behavior = self.settings.timecode_mtc_idle_behavior or MTC_IDLE_KEEP_STREAM
        if self.timecode_mtc_idle_behavior not in {MTC_IDLE_KEEP_STREAM, MTC_IDLE_ALLOW_DARK}:
            self.timecode_mtc_idle_behavior = MTC_IDLE_KEEP_STREAM
        self.timecode_sample_rate = int(self.settings.timecode_sample_rate or 48000)
        if self.timecode_sample_rate not in {44100, 48000, 96000}:
            self.timecode_sample_rate = 48000
        self.timecode_bit_depth = int(self.settings.timecode_bit_depth or 16)
        if self.timecode_bit_depth not in {8, 16, 32}:
            self.timecode_bit_depth = 16
        self.show_timecode_panel = bool(self.settings.show_timecode_panel)
        self.show_colour_legend = bool(getattr(self.settings, "show_colour_legend", True))
        self.timecode_timeline_mode = (
            self.settings.timecode_timeline_mode
            if self.settings.timecode_timeline_mode in {"cue_region", "audio_file"}
            else self.settings.main_transport_timeline_mode
        )
        if self.timecode_timeline_mode not in {"cue_region", "audio_file"}:
            self.timecode_timeline_mode = "cue_region"
        self.soundbutton_timecode_offset_enabled = bool(
            getattr(self.settings, "soundbutton_timecode_offset_enabled", True)
        )
        self.respect_soundbutton_timecode_timeline_setting = bool(
            getattr(self.settings, "respect_soundbutton_timecode_timeline_setting", True)
        )
        self.main_transport_timeline_mode = (
            self.settings.main_transport_timeline_mode
            if self.settings.main_transport_timeline_mode in {"cue_region", "audio_file"}
            else "cue_region"
        )
        self.main_progress_display_mode = str(getattr(self.settings, "main_progress_display_mode", "progress_bar")).strip().lower()
        if self.main_progress_display_mode not in {"progress_bar", "waveform"}:
            self.main_progress_display_mode = "progress_bar"
        self.main_progress_show_text = bool(getattr(self.settings, "main_progress_show_text", True))
        self._timecode_follow_frozen_ms = 0
        if self.timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE:
            self._timecode_follow_frozen_ms = 0
        self.main_jog_outside_cue_action = (
            self.settings.main_jog_outside_cue_action
            if self.settings.main_jog_outside_cue_action
            in {"stop_immediately", "ignore_cue", "next_cue_or_stop", "stop_cue_or_end"}
            else "stop_immediately"
        )
        self.stage_display_layout = self._normalize_stage_display_layout(
            list(getattr(self.settings, "stage_display_layout", []))
        )
        self.stage_display_visibility = self._normalize_stage_display_visibility(
            {
                "current_time": bool(getattr(self.settings, "stage_display_show_current_time", True)),
                "alert": bool(getattr(self.settings, "stage_display_show_alert", False)),
                "total_time": bool(getattr(self.settings, "stage_display_show_total_time", True)),
                "elapsed": bool(getattr(self.settings, "stage_display_show_elapsed", True)),
                "remaining": bool(getattr(self.settings, "stage_display_show_remaining", True)),
                "progress_bar": bool(getattr(self.settings, "stage_display_show_progress_bar", True)),
                "song_name": bool(getattr(self.settings, "stage_display_show_song_name", True)),
                "lyric": bool(getattr(self.settings, "stage_display_show_lyric", True)),
                "next_song": bool(getattr(self.settings, "stage_display_show_next_song", True)),
            }
        )
        self.stage_display_gadgets = normalize_stage_display_gadgets(
            getattr(self.settings, "stage_display_gadgets", {}),
            legacy_layout=self.stage_display_layout,
            legacy_visibility=self.stage_display_visibility,
        )
        self.stage_display_layout, self.stage_display_visibility = gadgets_to_legacy_layout_visibility(
            self.stage_display_gadgets
        )
        source = str(getattr(self.settings, "stage_display_text_source", "caption")).strip().lower()
        self.stage_display_text_source = source if source in {"caption", "filename", "note"} else "caption"
        now_playing_mode = str(getattr(self.settings, "now_playing_display_mode", "caption")).strip().lower()
        self.now_playing_display_mode = (
            now_playing_mode
            if now_playing_mode in {"filename", "filepath", "caption", "note", "caption_note"}
            else "caption"
        )
        lyric_mode = str(getattr(self.settings, "main_ui_lyric_display_mode", "always")).strip().lower()
        self.main_ui_lyric_display_mode = (
            lyric_mode if lyric_mode in {"always", "when_available", "never"} else "always"
        )
        self.search_lyric_on_add_sound_button = bool(
            getattr(self.settings, "search_lyric_on_add_sound_button", True)
        )
        new_lyric_fmt = str(getattr(self.settings, "new_lyric_file_format", "srt")).strip().lower()
        self.new_lyric_file_format = new_lyric_fmt if new_lyric_fmt in {"srt", "lrc"} else "srt"
        self.supported_audio_format_extensions = normalize_supported_audio_extensions(
            list(getattr(self.settings, "supported_audio_format_extensions", []))
        )
        self.verify_sound_file_on_add = bool(getattr(self.settings, "verify_sound_file_on_add", True))
        self.allow_other_unsupported_audio_files = bool(
            getattr(self.settings, "allow_other_unsupported_audio_files", False)
        )
        self.disable_path_safety = bool(getattr(self.settings, "disable_path_safety", False))
        self.window_layout = normalize_window_layout(getattr(self.settings, "window_layout", None))
        self.state_colors = {
            "empty": self.settings.color_empty,
            "assigned": self.settings.color_unplayed,
            "highlighted": self.settings.color_highlight,
            "playing": self.settings.color_playing,
            "played": self.settings.color_played,
            "missing": self.settings.color_error,
            "locked": self.settings.color_lock,
            "marker": self.settings.color_place_marker,
            "copied": self.settings.color_copied_to_cue,
            "cue_indicator": self.settings.color_cue_indicator,
            "volume_indicator": self.settings.color_volume_indicator,
            "vocal_removed_indicator": getattr(self.settings, "color_vocal_removed_indicator", "#8E7CFF"),
            "midi_indicator": getattr(self.settings, "color_midi_indicator", "#FF9E4A"),
            "lyric_indicator": getattr(self.settings, "color_lyric_indicator", "#57C3A4"),
        }
        # Migrate legacy default marker color so marker text remains readable.
        if str(self.settings.color_place_marker).strip().upper() == "#111111":
            self.settings.color_place_marker = COLORS["marker"]
            self.state_colors["marker"] = COLORS["marker"]
            try:
                save_settings(self.settings)
            except OSError:
                pass
        self.sound_button_text_color = self.settings.sound_button_text_color
        self.hotkeys: Dict[str, tuple[str, str]] = {
            "new_set": (self.settings.hotkey_new_set_1, self.settings.hotkey_new_set_2),
            "open_set": (self.settings.hotkey_open_set_1, self.settings.hotkey_open_set_2),
            "save_set": (self.settings.hotkey_save_set_1, self.settings.hotkey_save_set_2),
            "save_set_as": (self.settings.hotkey_save_set_as_1, self.settings.hotkey_save_set_as_2),
            "search": (self.settings.hotkey_search_1, self.settings.hotkey_search_2),
            "options": (self.settings.hotkey_options_1, self.settings.hotkey_options_2),
            "play_selected_pause": (
                self.settings.hotkey_play_selected_pause_1,
                self.settings.hotkey_play_selected_pause_2,
            ),
            "play_selected": (self.settings.hotkey_play_selected_1, self.settings.hotkey_play_selected_2),
            "pause_toggle": (self.settings.hotkey_pause_toggle_1, self.settings.hotkey_pause_toggle_2),
            "stop_playback": (self.settings.hotkey_stop_playback_1, self.settings.hotkey_stop_playback_2),
            "talk": (self.settings.hotkey_talk_1, self.settings.hotkey_talk_2),
            "next_group": (self.settings.hotkey_next_group_1, self.settings.hotkey_next_group_2),
            "prev_group": (self.settings.hotkey_prev_group_1, self.settings.hotkey_prev_group_2),
            "next_page": (self.settings.hotkey_next_page_1, self.settings.hotkey_next_page_2),
            "prev_page": (self.settings.hotkey_prev_page_1, self.settings.hotkey_prev_page_2),
            "next_sound_button": (self.settings.hotkey_next_sound_button_1, self.settings.hotkey_next_sound_button_2),
            "prev_sound_button": (self.settings.hotkey_prev_sound_button_1, self.settings.hotkey_prev_sound_button_2),
            "multi_play": (self.settings.hotkey_multi_play_1, self.settings.hotkey_multi_play_2),
            "go_to_playing": (self.settings.hotkey_go_to_playing_1, self.settings.hotkey_go_to_playing_2),
            "loop": (self.settings.hotkey_loop_1, self.settings.hotkey_loop_2),
            "next": (self.settings.hotkey_next_1, self.settings.hotkey_next_2),
            "rapid_fire": (self.settings.hotkey_rapid_fire_1, self.settings.hotkey_rapid_fire_2),
            "shuffle": (self.settings.hotkey_shuffle_1, self.settings.hotkey_shuffle_2),
            "reset_page": (self.settings.hotkey_reset_page_1, self.settings.hotkey_reset_page_2),
            "play_list": (self.settings.hotkey_play_list_1, self.settings.hotkey_play_list_2),
            "fade_in": (self.settings.hotkey_fade_in_1, self.settings.hotkey_fade_in_2),
            "cross_fade": (self.settings.hotkey_cross_fade_1, self.settings.hotkey_cross_fade_2),
            "fade_out": (self.settings.hotkey_fade_out_1, self.settings.hotkey_fade_out_2),
            "mute": (self.settings.hotkey_mute_1, self.settings.hotkey_mute_2),
            "volume_up": (self.settings.hotkey_volume_up_1, self.settings.hotkey_volume_up_2),
            "volume_down": (self.settings.hotkey_volume_down_1, self.settings.hotkey_volume_down_2),
            "lock_toggle": (self.settings.hotkey_lock_toggle_1, self.settings.hotkey_lock_toggle_2),
            "open_hide_lyric_navigator": (
                self.settings.hotkey_open_hide_lyric_navigator_1,
                self.settings.hotkey_open_hide_lyric_navigator_2,
            ),
        }
        self.quick_action_enabled = bool(self.settings.quick_action_enabled)
        self.quick_action_keys = list(self.settings.quick_action_keys[:48])
        if len(self.quick_action_keys) < 48:
            self.quick_action_keys.extend(["" for _ in range(48 - len(self.quick_action_keys))])
        self.sound_button_hotkey_enabled = bool(self.settings.sound_button_hotkey_enabled)
        self.sound_button_hotkey_priority = (
            self.settings.sound_button_hotkey_priority
            if self.settings.sound_button_hotkey_priority in {"system_first", "sound_button_first"}
            else "system_first"
        )
        self.sound_button_hotkey_go_to_playing = bool(self.settings.sound_button_hotkey_go_to_playing)
        self.midi_input_device_ids: List[str] = [str(v).strip() for v in self.settings.midi_input_device_ids if str(v).strip()]
        self.midi_input_device_ids = self._normalize_midi_input_selectors(self.midi_input_device_ids)
        self.launchpad_enabled = bool(getattr(self.settings, "launchpad_enabled", False))
        self.launchpad_device_selector = str(getattr(self.settings, "launchpad_device_selector", "")).strip()
        self.launchpad_output_device_id = str(getattr(self.settings, "launchpad_output_device_id", "")).strip()
        self.launchpad_layout = normalize_launchpad_layout(getattr(self.settings, "launchpad_layout", "bottom_six"))
        self.launchpad_control_bindings = [str(value or "").strip() for value in getattr(self.settings, "launchpad_control_bindings", [])[:16]]
        if len(self.launchpad_control_bindings) < 16:
            self.launchpad_control_bindings.extend(["" for _ in range(16 - len(self.launchpad_control_bindings))])
        if self.launchpad_enabled and self.launchpad_device_selector:
            self.midi_input_device_ids = [
                selector for selector in self.midi_input_device_ids if str(selector).strip() != self.launchpad_device_selector
            ]
        self.midi_hotkeys: Dict[str, tuple[str, str]] = {
            "new_set": (self.settings.midi_hotkey_new_set_1, self.settings.midi_hotkey_new_set_2),
            "open_set": (self.settings.midi_hotkey_open_set_1, self.settings.midi_hotkey_open_set_2),
            "save_set": (self.settings.midi_hotkey_save_set_1, self.settings.midi_hotkey_save_set_2),
            "save_set_as": (self.settings.midi_hotkey_save_set_as_1, self.settings.midi_hotkey_save_set_as_2),
            "search": (self.settings.midi_hotkey_search_1, self.settings.midi_hotkey_search_2),
            "options": (self.settings.midi_hotkey_options_1, self.settings.midi_hotkey_options_2),
            "play_selected_pause": (
                self.settings.midi_hotkey_play_selected_pause_1,
                self.settings.midi_hotkey_play_selected_pause_2,
            ),
            "play_selected": (self.settings.midi_hotkey_play_selected_1, self.settings.midi_hotkey_play_selected_2),
            "pause_toggle": (self.settings.midi_hotkey_pause_toggle_1, self.settings.midi_hotkey_pause_toggle_2),
            "stop_playback": (self.settings.midi_hotkey_stop_playback_1, self.settings.midi_hotkey_stop_playback_2),
            "talk": (self.settings.midi_hotkey_talk_1, self.settings.midi_hotkey_talk_2),
            "next_group": (self.settings.midi_hotkey_next_group_1, self.settings.midi_hotkey_next_group_2),
            "prev_group": (self.settings.midi_hotkey_prev_group_1, self.settings.midi_hotkey_prev_group_2),
            "next_page": (self.settings.midi_hotkey_next_page_1, self.settings.midi_hotkey_next_page_2),
            "prev_page": (self.settings.midi_hotkey_prev_page_1, self.settings.midi_hotkey_prev_page_2),
            "next_sound_button": (self.settings.midi_hotkey_next_sound_button_1, self.settings.midi_hotkey_next_sound_button_2),
            "prev_sound_button": (self.settings.midi_hotkey_prev_sound_button_1, self.settings.midi_hotkey_prev_sound_button_2),
            "multi_play": (self.settings.midi_hotkey_multi_play_1, self.settings.midi_hotkey_multi_play_2),
            "go_to_playing": (self.settings.midi_hotkey_go_to_playing_1, self.settings.midi_hotkey_go_to_playing_2),
            "loop": (self.settings.midi_hotkey_loop_1, self.settings.midi_hotkey_loop_2),
            "next": (self.settings.midi_hotkey_next_1, self.settings.midi_hotkey_next_2),
            "rapid_fire": (self.settings.midi_hotkey_rapid_fire_1, self.settings.midi_hotkey_rapid_fire_2),
            "shuffle": (self.settings.midi_hotkey_shuffle_1, self.settings.midi_hotkey_shuffle_2),
            "reset_page": (self.settings.midi_hotkey_reset_page_1, self.settings.midi_hotkey_reset_page_2),
            "play_list": (self.settings.midi_hotkey_play_list_1, self.settings.midi_hotkey_play_list_2),
            "fade_in": (self.settings.midi_hotkey_fade_in_1, self.settings.midi_hotkey_fade_in_2),
            "cross_fade": (self.settings.midi_hotkey_cross_fade_1, self.settings.midi_hotkey_cross_fade_2),
            "fade_out": (self.settings.midi_hotkey_fade_out_1, self.settings.midi_hotkey_fade_out_2),
            "mute": (self.settings.midi_hotkey_mute_1, self.settings.midi_hotkey_mute_2),
            "volume_up": (self.settings.midi_hotkey_volume_up_1, self.settings.midi_hotkey_volume_up_2),
            "volume_down": (self.settings.midi_hotkey_volume_down_1, self.settings.midi_hotkey_volume_down_2),
            "lock_toggle": (self.settings.midi_hotkey_lock_toggle_1, self.settings.midi_hotkey_lock_toggle_2),
            "open_hide_lyric_navigator": (
                self.settings.midi_hotkey_open_hide_lyric_navigator_1,
                self.settings.midi_hotkey_open_hide_lyric_navigator_2,
            ),
        }
        self.midi_quick_action_enabled = bool(self.settings.midi_quick_action_enabled)
        self.midi_quick_action_bindings = [normalize_midi_binding(v) for v in self.settings.midi_quick_action_bindings[:48]]
        if len(self.midi_quick_action_bindings) < 48:
            self.midi_quick_action_bindings.extend(["" for _ in range(48 - len(self.midi_quick_action_bindings))])
        self.midi_sound_button_hotkey_enabled = bool(self.settings.midi_sound_button_hotkey_enabled)
        self.midi_sound_button_hotkey_priority = (
            self.settings.midi_sound_button_hotkey_priority
            if self.settings.midi_sound_button_hotkey_priority in {"system_first", "sound_button_first"}
            else "system_first"
        )
        self.midi_sound_button_hotkey_go_to_playing = bool(self.settings.midi_sound_button_hotkey_go_to_playing)
        self.midi_rotary_enabled = bool(getattr(self.settings, "midi_rotary_enabled", False))
        self.midi_rotary_group_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_group_binding", ""))
        self.midi_rotary_page_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_page_binding", ""))
        self.midi_rotary_sound_button_binding = normalize_midi_binding(
            getattr(self.settings, "midi_rotary_sound_button_binding", "")
        )
        self.midi_rotary_jog_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_jog_binding", ""))
        self.midi_rotary_volume_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_volume_binding", ""))
        self.midi_rotary_group_invert = bool(getattr(self.settings, "midi_rotary_group_invert", False))
        self.midi_rotary_page_invert = bool(getattr(self.settings, "midi_rotary_page_invert", False))
        self.midi_rotary_sound_button_invert = bool(getattr(self.settings, "midi_rotary_sound_button_invert", False))
        self.midi_rotary_jog_invert = bool(getattr(self.settings, "midi_rotary_jog_invert", False))
        self.midi_rotary_volume_invert = bool(getattr(self.settings, "midi_rotary_volume_invert", False))
        self.midi_rotary_group_sensitivity = max(
            1, min(20, int(getattr(self.settings, "midi_rotary_group_sensitivity", 1)))
        )
        self.midi_rotary_page_sensitivity = max(
            1, min(20, int(getattr(self.settings, "midi_rotary_page_sensitivity", 1)))
        )
        self.midi_rotary_sound_button_sensitivity = max(
            1, min(20, int(getattr(self.settings, "midi_rotary_sound_button_sensitivity", 1)))
        )
        self.midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_group_relative_mode", "auto")
        )
        self.midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_page_relative_mode", "auto")
        )
        self.midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_sound_button_relative_mode", "auto")
        )
        self.midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_jog_relative_mode", "auto")
        )
        self.midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_volume_relative_mode", "auto")
        )
        mode = str(getattr(self.settings, "midi_rotary_volume_mode", "relative")).strip().lower()
        self.midi_rotary_volume_mode = mode if mode in {"absolute", "relative"} else "relative"
        self.midi_rotary_volume_step = max(1, min(20, int(getattr(self.settings, "midi_rotary_volume_step", 2))))
        self.midi_rotary_jog_step_ms = max(10, min(5000, int(getattr(self.settings, "midi_rotary_jog_step_ms", 250))))
        self._web_remote_server: Optional[WebRemoteServer] = None
        self._main_thread_executor = MainThreadExecutor(self)

        startup_audio_warning: Optional[str] = None
        configured_device = self.audio_output_device.strip()
        if configured_device and not set_output_device(configured_device):
            startup_audio_warning = (
                f"Configured audio device was not found:\n{configured_device}\n\n"
                "Falling back to system default output device."
            )
            self.audio_output_device = ""
            self.settings.audio_output_device = ""
        else:
            set_output_device(configured_device)
        try:
            self._init_audio_players()
        except Exception as exc:
            self._dispose_audio_players()
            set_output_device("")
            self.audio_output_device = ""
            self.settings.audio_output_device = ""
            try:
                self._init_audio_players()
            except Exception as exc2:
                self._init_silent_audio_players()
                startup_audio_warning = (
                    "Audio output failed to initialize. Running in no-audio mode.\n\n"
                    f"Primary error:\n{exc}\n\n"
                    f"Fallback error:\n{exc2}"
                )
            else:
                fallback_msg = (
                    "Audio device failed to initialize at startup.\n"
                    "Falling back to system default output device.\n\n"
                    f"Details:\n{exc}"
                )
                startup_audio_warning = f"{startup_audio_warning}\n\n{fallback_msg}" if startup_audio_warning else fallback_msg

        self.data: Dict[str, List[List[SoundButtonData]]] = {}
        self.page_names: Dict[str, List[str]] = {}
        self.page_colors: Dict[str, List[Optional[str]]] = {}
        self.page_playlist_enabled: Dict[str, List[bool]] = {}
        self.page_shuffle_enabled: Dict[str, List[bool]] = {}
        self.cue_page: List[SoundButtonData] = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self.cue_mode = False
        self.current_set_path = ""
        self._reset_set_data()

        self.group_buttons: Dict[str, QPushButton] = {}
        self.sound_buttons: List[SoundButton] = []
        self.page_list = QListWidget()
        self.group_status = QLabel("")
        self.page_status = QLabel("")
        self.now_playing_label = NowPlayingLabel()
        self.main_lyric_label = NowPlayingLabel()
        self.drag_mode_banner = QLabel("")
        self.timecode_multiplay_banner = QLabel("")
        self.web_remote_warning_banner = QLabel("")
        self.midi_connection_warning_banner = QLabel("")
        self.vocal_removed_warning_banner = QLabel("")
        self.playback_warning_banner = QLabel("")
        self.save_notice_banner = QLabel("")
        self.info_notice_banner = QLabel("")
        self.status_totals_label = QLabel("")
        self.status_hover_label = QLabel("Button: -")
        self.status_now_playing_label = QLabel("Now Playing: -")
        self.timecode_status_label = QLabel("")
        self.web_remote_status_label = QLabel("")
        self.total_time = QLabel("00:00:00")
        self.preload_status_icon = QLabel("RAM")
        self.elapsed_time = QLabel("00:00:00")
        self.remaining_time = QLabel("00:00:00")
        self.progress_label = TransportProgressDisplay("0%")
        self.jog_in_label = QLabel("In 00:00:00")
        self.jog_percent_label = QLabel("0%")
        self.jog_out_label = QLabel("Out 00:00:00")
        self.left_meter = DbfsMeter()
        self.right_meter = DbfsMeter()
        self.meter_scale = DbfsMeterScale()
        self.seek_slider = QSlider(Qt.Horizontal)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.control_buttons: Dict[str, QPushButton] = {}
        self._is_scrubbing = False
        self._vu_levels = [0.0, 0.0]
        self._last_ui_position_ms = -1
        self._player_slot_volume_pct = 75
        self._player_b_slot_volume_pct = 75
        self._multi_players: List[ExternalMediaPlayer] = []
        self._player_slot_pct_map: Dict[int, int] = {}
        self._player_started_map: Dict[int, float] = {}
        self._player_slot_key_map: Dict[int, Tuple[str, int, int]] = {}
        self._playback_runtime = PlaybackRuntimeTracker()
        self._player_end_override_ms: Dict[int, int] = {}
        self._player_ignore_cue_end: set[int] = set()
        self._active_playing_keys: set[Tuple[str, int, int]] = set()
        self._ssp_unit_cache: Dict[str, Tuple[int, int]] = {}
        self._drag_source_key: Optional[Tuple[str, int, int]] = None
        self._drag_target_slot_key: Optional[Tuple[str, int, int]] = None
        self._page_drag_source_key: Optional[Tuple[str, int]] = None
        self._page_drag_start_pos = None
        self._track_started_at = 0.0
        self._ignore_state_changes = 0
        self._dirty = False
        self._copied_page_buffer: Optional[dict] = None
        self._copied_slot_buffer: Optional[SoundButtonData] = None
        self._search_window: Optional[SearchWindow] = None
        self._dsp_window: Optional[DSPWindow] = None
        self._tool_windows: Dict[str, ToolListWindow] = {}
        self._tool_window_matches: Dict[str, List[dict]] = {}
        self._menu_actions: Dict[str, QAction] = {}
        self._runtime_hotkey_shortcuts: List[QShortcut] = []
        self._modifier_hotkey_handlers: Dict[int, List[Callable[[], None]]] = {}
        self._modifier_hotkey_down: set[int] = set()
        self._ui_locked = False
        self._automation_locked = False
        self._lock_screen_overlay: Optional[LockScreenOverlay] = None
        self.lock_screen_button: Optional[QToolButton] = None
        self._midi_poll_thread = MidiPollingThread(self)
        self._midi_poll_thread.midi_event.connect(self._on_midi_binding_triggered)
        self._midi_poll_thread.launchpad_event.connect(self._on_launchpad_binding_triggered)
        self._midi_poll_thread.status_changed.connect(self._on_midi_poll_status)
        self._midi_action_handlers: Dict[str, Callable[[], None]] = {}
        self._launchpad_action_handlers: Dict[str, Callable[[], None]] = {}
        self._launchpad_last_trigger_t: Dict[str, float] = {}
        self._midi_last_trigger_t: Dict[str, float] = {}
        self._midi_context_handler = None
        self._midi_context_block_actions = False
        self._midi_missing_selectors: set[str] = set()
        self._launchpad_missing_selectors: set[str] = set()
        self._launchpad_output_missing = False
        self._skip_save_on_close = False
        self._export_buttons_window: Optional[QDialog] = None
        self._export_dir_edit: Optional[QLineEdit] = None
        self._export_format_combo: Optional[QComboBox] = None
        self._about_window: Optional[AboutWindowDialog] = None
        self._audio_engine_insight_window: Optional[AudioEngineInsightDialog] = None
        self._system_info_window: Optional[SystemInformationDialog] = None
        self._tips_window: Optional[TipsWindow] = None
        self._dsp_config: DSPConfig = DSPConfig()
        self._flash_slot_key: Optional[Tuple[str, int, int]] = None
        self._flash_slot_until = 0.0
        self._hotkey_selected_slot_key: Optional[Tuple[str, int, int]] = None
        self._pre_mute_volume: Optional[int] = None
        self.timecode_dock: Optional[QDockWidget] = None
        self.timecode_panel: Optional[TimecodePanel] = None
        self._mtc_sender = MtcMidiOutput(lambda: self.timecode_mtc_idle_behavior)
        self._ltc_sender = LtcAudioOutput()
        self._timecode_follow_anchor_ms = 0.0
        self._timecode_follow_anchor_t = time.perf_counter()
        self._timecode_follow_playing = False
        self._timecode_follow_intent_pending = False
        self._timecode_last_media_ms = 0.0
        self._timecode_last_media_t = 0.0
        self._timecode_event_guard_until = 0.0
        self._auto_end_fade_track: Optional[Tuple[str, int, int]] = None
        self._auto_end_fade_done = False
        self._preload_icon_blink_on = False
        self._playback_warning_token = 0
        self._save_notice_token = 0
        self._info_notice_token = 0
        self._midi_connection_warning_token = 0
        self._stage_display_window: Optional[GadgetStageDisplayWindow] = None
        self._stage_lyric_cache_path: str = ""
        self._stage_lyric_cache_mtime: float = -1.0
        self._stage_lyric_cache_lines: List[LyricLine] = []
        self._stage_lyric_cache_error: str = ""
        self._lyric_display_window: Optional[LyricDisplayWindow] = None
        self._lyric_navigator_window: Optional[LyricNavigatorWindow] = None
        self._lyric_force_blank = False
        self._lyric_blank_toggle_action: Optional[QAction] = None
        self._hover_slot_index: Optional[int] = None
        self._stage_alert_dialog: Optional[QDialog] = None
        self._stage_alert_text_edit: Optional[QPlainTextEdit] = None
        self._stage_alert_duration_spin: Optional[QSpinBox] = None
        self._stage_alert_keep_checkbox: Optional[QCheckBox] = None
        self._stage_alert_message: str = ""
        self._stage_alert_until_monotonic: float = 0.0
        self._stage_alert_sticky: bool = False
        self._launchpad_output = WinMMMidiOut()
        self._launchpad_output_device_id = MIDI_OUTPUT_DEVICE_NONE
        self._launchpad_output_device_name = ""
        self._launchpad_last_feedback_signature: tuple = ()
        self._launchpad_action_keys: Dict[str, str] = {}
        self._launchpad_blink_on = True
        self._launchpad_reset_hold_token = ""
        self._launchpad_reset_hold_started_t = 0.0
        self._launchpad_reset_hold_fired = False

        self._build_ui()
        self._lock_screen_overlay = LockScreenOverlay(self)
        self._lock_screen_overlay.unlocked.connect(self._attempt_unlock_from_overlay)
        self._midi_poll_thread.start()
        self._apply_language()
        self._apply_launchpad_output_state()
        self._update_timecode_status_label()
        self._update_web_remote_status_label()
        self._sync_lock_ui_state()
        if self.lock_restart_state == "lock_on_restart" and bool(getattr(self.settings, "lock_was_locked_on_exit", False)):
            self._engage_lock_screen()
        self.statusBar().addWidget(self.status_hover_label)
        self.statusBar().addWidget(self.status_now_playing_label, 1)
        self.statusBar().addPermanentWidget(self.timecode_status_label)
        self.statusBar().addPermanentWidget(self.web_remote_status_label)
        self.statusBar().addPermanentWidget(self.status_totals_label)
        self.preload_status_icon.setAlignment(Qt.AlignCenter)
        self.preload_status_icon.setFixedSize(34, 18)
        self.preload_status_icon.setStyleSheet(
            "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#C8CDD4;border:1px solid #8C939D;border-radius:8px;}"
        )
        self.preload_status_icon.setToolTip("RAM preload idle")
        self.statusBar().addPermanentWidget(self.preload_status_icon)
        if sys.platform == "darwin":
            self.lock_screen_button = self._create_lock_screen_button(self.statusBar(), auto_raise=False)
            self.lock_screen_button.setMinimumSize(28, 20)
            self.statusBar().addPermanentWidget(self.lock_screen_button)
            self._sync_lock_ui_state()
        self._update_talk_button_visual()
        self.volume_slider.setValue(self.settings.volume)
        self._set_player_volume(self.player, self._effective_slot_target_volume(self._player_slot_volume_pct))
        self._set_player_volume(self.player_b, self._effective_slot_target_volume(self._player_b_slot_volume_pct))
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._update_now_playing_label("")
        self._refresh_window_title()
        self._update_status_totals()
        self._on_sound_button_hover(None)
        self._update_status_now_playing()

        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._tick_meter)
        self.meter_timer.start(60)

        self.timecode_mtc_timer = QTimer(self)
        self.timecode_mtc_timer.timeout.connect(self._tick_timecode_mtc)
        self.timecode_mtc_timer.start(10)

        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self._tick_fades)
        self.fade_timer.start(30)

        self._preload_trim_timer = QTimer(self)
        self._preload_trim_timer.timeout.connect(enforce_audio_preload_limits)
        self._preload_trim_timer.start(2000)

        self._preload_status_timer = QTimer(self)
        self._preload_status_timer.timeout.connect(self._tick_preload_status_icon)
        self._preload_status_timer.start(350)
        self._tick_preload_status_icon()

        self.talk_blink_timer = QTimer(self)
        self.talk_blink_timer.timeout.connect(self._tick_talk_blink)
        self.talk_blink_timer.start(280)

        self.current_group = self.settings.last_group
        self.current_page = self.settings.last_page
        self.cue_mode = False
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._update_button_drag_control_state()
        self._update_button_drag_visual_state()
        self._update_timecode_multiplay_warning_banner()
        self._restore_last_set_on_startup()
        if self.reset_all_on_startup:
            self._reset_all_played_state()
            self._refresh_sound_grid()
        self._apply_web_remote_state()
        if startup_audio_warning:
            QMessageBox.warning(self, "Audio Device", startup_audio_warning)
        self._suspend_settings_save = False
        if self.tips_open_on_startup:
            QTimer.singleShot(0, lambda: self._open_tips_window(startup=True))



__all__ = ["MainWindow"]
