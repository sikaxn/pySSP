import configparser
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.settings_store import _decode_ascii_setting, _encode_ascii_setting, _from_parser


def test_timecode_and_main_timeline_modes_are_independent():
    parser = configparser.ConfigParser()
    parser["main"] = {
        "timecode_timeline_mode": "audio_file",
        "main_transport_timeline_mode": "cue_region",
    }
    settings = _from_parser(parser)
    assert settings.timecode_timeline_mode == "audio_file"
    assert settings.main_transport_timeline_mode == "cue_region"


def test_timecode_timeline_mode_falls_back_to_main_when_missing():
    parser = configparser.ConfigParser()
    parser["main"] = {
        "main_transport_timeline_mode": "audio_file",
    }
    settings = _from_parser(parser)
    assert settings.timecode_timeline_mode == "audio_file"


def test_main_progress_display_mode_is_loaded_and_validated():
    parser = configparser.ConfigParser()
    parser["main"] = {"main_progress_display_mode": "waveform"}
    settings = _from_parser(parser)
    assert settings.main_progress_display_mode == "waveform"

    parser["main"]["main_progress_display_mode"] = "invalid-mode"
    settings = _from_parser(parser)
    assert settings.main_progress_display_mode == "progress_bar"


def test_main_progress_show_text_defaults_true_and_loads_false():
    parser = configparser.ConfigParser()
    parser["main"] = {}
    settings = _from_parser(parser)
    assert settings.main_progress_show_text is True

    parser["main"]["main_progress_show_text"] = "0"
    settings = _from_parser(parser)
    assert settings.main_progress_show_text is False


def test_lock_screen_settings_default_false_and_load_true():
    parser = configparser.ConfigParser()
    parser["main"] = {}
    settings = _from_parser(parser)
    assert settings.lock_allow_quit is True
    assert settings.lock_allow_system_hotkeys is False
    assert settings.lock_allow_quick_action_hotkeys is False
    assert settings.lock_allow_sound_button_hotkeys is False
    assert settings.lock_allow_midi_control is True
    assert settings.lock_auto_allow_quit is True
    assert settings.lock_auto_allow_midi_control is True
    assert settings.lock_unlock_method == "click_3_random_points"
    assert settings.lock_require_password is False
    assert settings.lock_password == ""
    assert settings.lock_restart_state == "unlock_on_restart"
    assert settings.lock_was_locked_on_exit is False
    assert settings.hotkey_lock_toggle_1 == "Ctrl+L"
    assert settings.hotkey_lock_toggle_2 == ""

    parser["main"] = {
        "lock_allow_quit": "1",
        "lock_allow_system_hotkeys": "1",
        "lock_allow_quick_action_hotkeys": "1",
        "lock_allow_sound_button_hotkeys": "1",
        "lock_allow_midi_control": "1",
        "lock_auto_allow_quit": "0",
        "lock_auto_allow_midi_control": "0",
        "lock_unlock_method": "slide_to_unlock",
        "lock_require_password": "1",
        "lock_password": "secret",
        "lock_restart_state": "lock_on_restart",
        "lock_was_locked_on_exit": "1",
    }
    settings = _from_parser(parser)
    assert settings.lock_allow_quit is True
    assert settings.lock_allow_system_hotkeys is True
    assert settings.lock_allow_quick_action_hotkeys is True
    assert settings.lock_allow_sound_button_hotkeys is True
    assert settings.lock_allow_midi_control is True
    assert settings.lock_auto_allow_quit is False
    assert settings.lock_auto_allow_midi_control is False
    assert settings.lock_unlock_method == "slide_to_unlock"
    assert settings.lock_require_password is True
    assert settings.lock_password == "secret"
    assert settings.lock_restart_state == "lock_on_restart"
    assert settings.lock_was_locked_on_exit is True


def test_blank_password_keeps_password_unlock_flag_on_load():
    parser = configparser.ConfigParser()
    parser["main"] = {
        "lock_require_password": "1",
        "lock_password": "",
    }
    settings = _from_parser(parser)
    assert settings.lock_require_password is True
    assert settings.lock_password == ""


def test_ascii_password_encoding_preserves_space_only_password():
    encoded = _encode_ascii_setting("    ")
    assert encoded.startswith('"')
    assert _decode_ascii_setting(encoded) == "    "
