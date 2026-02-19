import os
import sys
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.settings_store import default_quick_action_keys
from pyssp.timecode import MIDI_OUTPUT_DEVICE_NONE, TIMECODE_MODE_FOLLOW
from pyssp.ui.options_dialog import OptionsDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _build_dialog(**overrides):
    defaults = dict(OptionsDialog._DEFAULTS)
    defaults.update(overrides)
    return OptionsDialog(
        active_group_color=defaults["active_group_color"],
        inactive_group_color=defaults["inactive_group_color"],
        title_char_limit=defaults["title_char_limit"],
        show_file_notifications=defaults["show_file_notifications"],
        fade_in_sec=defaults["fade_in_sec"],
        cross_fade_sec=defaults["cross_fade_sec"],
        fade_out_sec=defaults["fade_out_sec"],
        fade_on_quick_action_hotkey=defaults["fade_on_quick_action_hotkey"],
        fade_on_sound_button_hotkey=defaults["fade_on_sound_button_hotkey"],
        fade_on_pause=defaults["fade_on_pause"],
        fade_on_resume=defaults["fade_on_resume"],
        fade_on_stop=defaults["fade_on_stop"],
        fade_out_when_done_playing=defaults["fade_out_when_done_playing"],
        fade_out_end_lead_sec=defaults["fade_out_end_lead_sec"],
        talk_volume_level=defaults["talk_volume_level"],
        talk_fade_sec=defaults["talk_fade_sec"],
        talk_volume_mode=defaults["talk_volume_mode"],
        talk_blink_button=defaults["talk_blink_button"],
        log_file_enabled=defaults["log_file_enabled"],
        reset_all_on_startup=defaults["reset_all_on_startup"],
        click_playing_action=defaults["click_playing_action"],
        search_double_click_action=defaults["search_double_click_action"],
        set_file_encoding=defaults["set_file_encoding"],
        audio_output_device="",
        available_audio_devices=["Device A", "Device B"],
        available_midi_devices=[(MIDI_OUTPUT_DEVICE_NONE, "None")],
        preload_audio_enabled=defaults["preload_audio_enabled"],
        preload_current_page_audio=defaults["preload_current_page_audio"],
        preload_audio_memory_limit_mb=defaults["preload_audio_memory_limit_mb"],
        preload_memory_pressure_enabled=defaults["preload_memory_pressure_enabled"],
        preload_pause_on_playback=defaults["preload_pause_on_playback"],
        preload_total_ram_mb=16384,
        preload_ram_cap_mb=14720,
        timecode_audio_output_device=defaults["timecode_audio_output_device"],
        timecode_midi_output_device=defaults["timecode_midi_output_device"],
        timecode_mode=defaults["timecode_mode"],
        timecode_fps=defaults["timecode_fps"],
        timecode_mtc_fps=defaults["timecode_mtc_fps"],
        timecode_mtc_idle_behavior=defaults["timecode_mtc_idle_behavior"],
        timecode_sample_rate=defaults["timecode_sample_rate"],
        timecode_bit_depth=defaults["timecode_bit_depth"],
        timecode_timeline_mode=defaults["timecode_timeline_mode"],
        max_multi_play_songs=defaults["max_multi_play_songs"],
        multi_play_limit_action=defaults["multi_play_limit_action"],
        playlist_play_mode=defaults["playlist_play_mode"],
        rapid_fire_play_mode=defaults["rapid_fire_play_mode"],
        next_play_mode=defaults["next_play_mode"],
        playlist_loop_mode=defaults["playlist_loop_mode"],
        candidate_error_action=defaults["candidate_error_action"],
        web_remote_enabled=defaults["web_remote_enabled"],
        web_remote_port=defaults["web_remote_port"],
        web_remote_url=overrides.get("web_remote_url", "http://127.0.0.1:5050/"),
        main_transport_timeline_mode=defaults["main_transport_timeline_mode"],
        main_jog_outside_cue_action=defaults["main_jog_outside_cue_action"],
        state_colors=defaults["state_colors"],
        sound_button_text_color=defaults["sound_button_text_color"],
        hotkeys=defaults["hotkeys"],
        quick_action_enabled=bool(overrides.get("quick_action_enabled", False)),
        quick_action_keys=default_quick_action_keys(),
        sound_button_hotkey_enabled=bool(overrides.get("sound_button_hotkey_enabled", False)),
        sound_button_hotkey_priority=str(overrides.get("sound_button_hotkey_priority", "system_first")),
        sound_button_hotkey_go_to_playing=bool(overrides.get("sound_button_hotkey_go_to_playing", False)),
        ui_language=defaults["ui_language"],
        initial_page=overrides.get("initial_page"),
        parent=None,
    )


def test_playback_timeline_toggle_controls_jog_group(qapp):
    dialog = _build_dialog(main_transport_timeline_mode="cue_region", main_jog_outside_cue_action="stop_immediately")
    assert dialog.selected_main_transport_timeline_mode() == "cue_region"
    assert dialog.jog_outside_group.isEnabled() is False

    dialog.cue_timeline_audio_file_radio.setChecked(True)
    dialog._sync_jog_outside_group_enabled()
    dialog.jog_outside_next_cue_or_stop_radio.setChecked(True)

    assert dialog.selected_main_transport_timeline_mode() == "audio_file"
    assert dialog.jog_outside_group.isEnabled() is True
    assert dialog.selected_main_jog_outside_cue_action() == "next_cue_or_stop"


def test_restore_defaults_playback_page_resets_controls(qapp):
    dialog = _build_dialog(initial_page="Playback")
    dialog.cue_timeline_audio_file_radio.setChecked(True)
    dialog.jog_outside_stop_cue_or_end_radio.setChecked(True)
    dialog.candidate_error_keep_radio.setChecked(True)

    dialog.page_list.setCurrentRow(5)
    dialog._restore_defaults_current_page()

    assert dialog.selected_main_transport_timeline_mode() == "cue_region"
    assert dialog.selected_main_jog_outside_cue_action() == "stop_immediately"
    assert dialog.selected_candidate_error_action() == "stop_playback"
    assert dialog.jog_outside_group.isEnabled() is False


def test_web_remote_url_label_tracks_port_changes(qapp):
    dialog = _build_dialog(web_remote_url="http://10.0.0.55:5050/")
    dialog.web_remote_port_spin.setValue(6060)
    assert "http://10.0.0.55:6060/" in dialog.web_remote_url_value.text()
    dialog.web_remote_enabled_checkbox.setChecked(True)
    assert dialog.web_remote_enabled_checkbox.isChecked() is True


def test_hotkey_conflict_disables_ok_button(qapp):
    dialog = _build_dialog()
    dialog._hotkey_edits["new_set"][0].setText("Ctrl+N")
    dialog._hotkey_edits["open_set"][0].setText("Ctrl+N")
    dialog._validate_hotkey_conflicts()
    assert dialog.ok_button.isEnabled() is False
    assert dialog.hotkey_warning_label.text().strip() != ""

    dialog._hotkey_edits["open_set"][0].setText("Ctrl+O")
    dialog._validate_hotkey_conflicts()
    assert dialog.ok_button.isEnabled() is True


def test_selected_value_methods_follow_toggles(qapp):
    dialog = _build_dialog()
    dialog.search_dbl_play_radio.setChecked(True)
    dialog.playing_click_stop_radio.setChecked(True)
    dialog.set_file_encoding_gbk_radio.setChecked(True)
    dialog.playlist_mode_any_radio.setChecked(True)
    dialog.rapid_fire_mode_any_radio.setChecked(True)
    dialog.next_mode_any_radio.setChecked(True)
    dialog.playlist_loop_single_radio.setChecked(True)
    dialog.multi_play_disallow_radio.setChecked(True)
    dialog.candidate_error_keep_radio.setChecked(True)
    dialog.timecode_timeline_audio_file_radio.setChecked(True)
    dialog.timecode_mode_combo.setCurrentIndex(dialog.timecode_mode_combo.findData(TIMECODE_MODE_FOLLOW))

    assert dialog.selected_search_double_click_action() == "play_highlight"
    assert dialog.selected_click_playing_action() == "stop_it"
    assert dialog.selected_set_file_encoding() == "gbk"
    assert dialog.selected_playlist_play_mode() == "any_available"
    assert dialog.selected_rapid_fire_play_mode() == "any_available"
    assert dialog.selected_next_play_mode() == "any_available"
    assert dialog.selected_playlist_loop_mode() == "loop_single"
    assert dialog.selected_multi_play_limit_action() == "disallow_more_play"
    assert dialog.selected_candidate_error_action() == "keep_playing"
    assert dialog.selected_timecode_timeline_mode() == "audio_file"
