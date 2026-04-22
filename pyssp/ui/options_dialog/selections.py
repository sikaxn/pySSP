from __future__ import annotations

from .shared import *
from .widgets import *


class SelectionMixin:
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

    def selected_now_playing_display_mode(self) -> str:
        if self.now_playing_filename_radio.isChecked():
            return "filename"
        if self.now_playing_filepath_radio.isChecked():
            return "filepath"
        if self.now_playing_note_radio.isChecked():
            return "note"
        if self.now_playing_caption_note_radio.isChecked():
            return "caption_note"
        return "caption"

    def selected_main_ui_lyric_display_mode(self) -> str:
        if self.main_ui_lyric_display_when_available_radio.isChecked():
            return "when_available"
        if self.main_ui_lyric_display_never_radio.isChecked():
            return "never"
        return "always"

    def selected_search_lyric_on_add_sound_button(self) -> bool:
        return bool(self.search_lyric_on_add_sound_button_checkbox.isChecked())

    def selected_new_lyric_file_format(self) -> str:
        value = str(self.new_lyric_file_format_combo.currentData() or "srt").strip().lower()
        return value if value in {"srt", "lrc"} else "srt"

    def selected_supported_audio_format_extensions(self) -> List[str]:
        text = str(self.supported_audio_format_extensions_value.text() or "").strip()
        if (not text) or text in {"(none detected)", tr("(none detected)")}:
            return []
        output: List[str] = []
        for token in text.split(","):
            value = str(token or "").strip().lower()
            if value:
                output.append(value)
        return output

    def selected_verify_sound_file_on_add(self) -> bool:
        return bool(self.verify_sound_file_on_add_checkbox.isChecked())

    def selected_allow_other_unsupported_audio_files(self) -> bool:
        return bool(self.allow_other_unsupported_audio_files_checkbox.isChecked())

    def selected_disable_path_safety(self) -> bool:
        return bool(self.disable_path_safety_checkbox.isChecked())

    def selected_ui_language(self) -> str:
        return normalize_language(str(self.ui_language_combo.currentData() or "en"))

    def selected_audio_output_device(self) -> str:
        return str(self.audio_device_combo.currentData() or "")

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

    def selected_preload_use_ffmpeg(self) -> bool:
        return bool(self.preload_use_ffmpeg_checkbox.isChecked())

    def selected_waveform_cache_limit_mb(self) -> int:
        step_mb = int(self._waveform_cache_slider_step_mb)
        raw = int(self.waveform_cache_size_input.value())
        selected_mb = (max(step_mb, raw) // step_mb) * step_mb
        return max(self._waveform_cache_min_mb, min(self._waveform_cache_max_mb, selected_mb))

    def selected_waveform_cache_clear_on_launch(self) -> bool:
        return bool(self.waveform_cache_clear_on_launch_checkbox.isChecked())

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

    def selected_soundbutton_timecode_offset_enabled(self) -> bool:
        return bool(self.soundbutton_timecode_offset_enabled_checkbox.isChecked())

    def selected_respect_soundbutton_timecode_timeline_setting(self) -> bool:
        return bool(self.respect_soundbutton_timecode_timeline_setting_checkbox.isChecked())

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

    def selected_vocal_removed_toggle_fade_mode(self) -> str:
        if self.vocal_removed_follow_cross_fade_custom_radio.isChecked():
            return "follow_cross_fade_custom"
        if self.vocal_removed_never_fade_radio.isChecked():
            return "never"
        if self.vocal_removed_always_fade_radio.isChecked():
            return "always"
        return "follow_cross_fade"

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

    def selected_window_layout(self) -> Dict[str, object]:
        if (
            hasattr(self, "window_layout_main_editor")
            and hasattr(self, "window_layout_fade_editor")
            and hasattr(self, "window_layout_available_list")
            and hasattr(self, "window_layout_show_all_checkbox")
        ):
            return normalize_window_layout(
                {
                    "main": self.window_layout_main_editor.export_items(),
                    "fade": self.window_layout_fade_editor.export_items(),
                    "available": self.window_layout_available_list.buttons(),
                    "show_all_available": bool(self.window_layout_show_all_checkbox.isChecked()),
                }
            )
        return normalize_window_layout(deepcopy(self._window_layout))

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

    def selected_lock_allow_quit(self) -> bool:
        return bool(self.lock_allow_quit_checkbox.isChecked())

    def selected_lock_allow_system_hotkeys(self) -> bool:
        return bool(self.lock_allow_system_hotkeys_checkbox.isChecked())

    def selected_lock_allow_quick_action_hotkeys(self) -> bool:
        return bool(self.lock_allow_quick_action_hotkeys_checkbox.isChecked())

    def selected_lock_allow_sound_button_hotkeys(self) -> bool:
        return bool(self.lock_allow_sound_button_hotkeys_checkbox.isChecked())

    def selected_lock_allow_midi_control(self) -> bool:
        return bool(self.lock_allow_midi_control_checkbox.isChecked())

    def selected_lock_auto_allow_quit(self) -> bool:
        return bool(self.lock_auto_allow_quit_checkbox.isChecked())

    def selected_lock_auto_allow_midi_control(self) -> bool:
        return bool(self.lock_auto_allow_midi_control_checkbox.isChecked())

    def selected_lock_unlock_method(self) -> str:
        if self.lock_method_fixed_button_radio.isChecked():
            return "click_one_button"
        if self.lock_method_slide_radio.isChecked():
            return "slide_to_unlock"
        return "click_3_random_points"

    def selected_lock_require_password(self) -> bool:
        return bool(self.lock_require_password_checkbox.isChecked())

    def selected_lock_password(self) -> str:
        password = str(self.lock_password_edit.text())
        verify = str(self.lock_password_verify_edit.text())
        if password or verify:
            return password
        return self._lock_existing_password

    def selected_lock_restart_state(self) -> str:
        if self.lock_restart_lock_radio.isChecked():
            return "lock_on_restart"
        return "unlock_on_restart"

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

