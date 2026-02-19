from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from pathlib import Path

from pyssp.set_loader import parse_delphi_color


def default_quick_action_keys() -> list[str]:
    values: list[str] = []
    values.extend([chr(code) for code in range(ord("A"), ord("O") + 1)])  # A..O
    values.extend([chr(code) for code in range(ord("Q"), ord("Z") + 1)])  # Q..Z (skip P)
    values.extend([str(i) for i in range(10)])  # 0..9
    values.extend([f"F{i}" for i in range(1, 12)])  # F1..F11
    values.extend(["Ins", "Del"])
    return values[:48]


def _normalize_quick_action_keys(values: list[str]) -> list[str]:
    defaults = default_quick_action_keys()
    output = [str(v or "").strip() for v in values[:48]]
    if len(output) < 48:
        output.extend(defaults[len(output):48])
    return output[:48]


@dataclass
class AppSettings:
    last_open_dir: str = ""
    last_save_dir: str = ""
    last_sound_dir: str = ""
    last_set_path: str = ""
    active_group_color: str = "#EDE8C8"
    inactive_group_color: str = "#ECECEC"
    title_char_limit: int = 26
    show_file_notifications: bool = True
    volume: int = 90
    last_group: str = "A"
    last_page: int = 0
    fade_in_sec: float = 1.0
    cross_fade_sec: float = 1.0
    fade_out_sec: float = 1.0
    fade_on_quick_action_hotkey: bool = True
    fade_on_sound_button_hotkey: bool = True
    fade_on_pause: bool = False
    fade_on_resume: bool = False
    fade_on_stop: bool = True
    fade_out_when_done_playing: bool = False
    fade_out_end_lead_sec: float = 2.0
    talk_volume_level: int = 30
    talk_fade_sec: float = 0.5
    talk_volume_mode: str = "percent_of_master"
    talk_blink_button: bool = False
    talk_shift_accelerator: bool = True
    hotkeys_ignore_talk_level: bool = False
    enter_key_mirrors_space: bool = False
    log_file_enabled: bool = False
    reset_all_on_startup: bool = False
    click_playing_action: str = "play_it_again"
    search_double_click_action: str = "find_highlight"
    set_file_encoding: str = "utf8"
    ui_language: str = "en"
    audio_output_device: str = ""
    preload_audio_enabled: bool = False
    preload_current_page_audio: bool = True
    preload_audio_memory_limit_mb: int = 512
    preload_memory_pressure_enabled: bool = True
    preload_pause_on_playback: bool = False
    max_multi_play_songs: int = 5
    multi_play_limit_action: str = "stop_oldest"
    playlist_play_mode: str = "unplayed_only"
    rapid_fire_play_mode: str = "unplayed_only"
    next_play_mode: str = "unplayed_only"
    playlist_loop_mode: str = "loop_list"
    candidate_error_action: str = "stop_playback"
    web_remote_enabled: bool = False
    web_remote_port: int = 5050
    timecode_audio_output_device: str = "none"
    timecode_midi_output_device: str = "__none__"
    timecode_mode: str = "follow_media"
    timecode_fps: float = 30.0
    timecode_mtc_fps: float = 30.0
    timecode_mtc_idle_behavior: str = "keep_stream"
    timecode_sample_rate: int = 48000
    timecode_bit_depth: int = 16
    show_timecode_panel: bool = False
    timecode_timeline_mode: str = "cue_region"
    main_transport_timeline_mode: str = "cue_region"
    main_jog_outside_cue_action: str = "stop_immediately"
    color_empty: str = "#0B868A"
    color_unplayed: str = "#B0B0B0"
    color_highlight: str = "#A6D8FF"
    color_playing: str = "#66FF33"
    color_played: str = "#FF3B30"
    color_error: str = "#7B3FB3"
    color_lock: str = "#F2D74A"
    color_place_marker: str = "#111111"
    color_copied_to_cue: str = "#2E65FF"
    color_cue_indicator: str = "#61D6FF"
    color_volume_indicator: str = "#FFD45A"
    sound_button_text_color: str = "#000000"
    hotkey_new_set_1: str = "Ctrl+N"
    hotkey_new_set_2: str = ""
    hotkey_open_set_1: str = "Ctrl+O"
    hotkey_open_set_2: str = ""
    hotkey_save_set_1: str = "Ctrl+S"
    hotkey_save_set_2: str = ""
    hotkey_save_set_as_1: str = "Ctrl+Shift+S"
    hotkey_save_set_as_2: str = ""
    hotkey_search_1: str = "Ctrl+F"
    hotkey_search_2: str = ""
    hotkey_options_1: str = ""
    hotkey_options_2: str = ""
    hotkey_play_selected_1: str = ""
    hotkey_play_selected_2: str = ""
    hotkey_pause_toggle_1: str = "P"
    hotkey_pause_toggle_2: str = ""
    hotkey_stop_playback_1: str = "Space"
    hotkey_stop_playback_2: str = "Return"
    hotkey_talk_1: str = "Shift"
    hotkey_talk_2: str = ""
    hotkey_next_group_1: str = ""
    hotkey_next_group_2: str = ""
    hotkey_prev_group_1: str = ""
    hotkey_prev_group_2: str = ""
    hotkey_next_page_1: str = ""
    hotkey_next_page_2: str = ""
    hotkey_prev_page_1: str = ""
    hotkey_prev_page_2: str = ""
    hotkey_next_sound_button_1: str = ""
    hotkey_next_sound_button_2: str = ""
    hotkey_prev_sound_button_1: str = ""
    hotkey_prev_sound_button_2: str = ""
    hotkey_multi_play_1: str = ""
    hotkey_multi_play_2: str = ""
    hotkey_go_to_playing_1: str = ""
    hotkey_go_to_playing_2: str = ""
    hotkey_loop_1: str = ""
    hotkey_loop_2: str = ""
    hotkey_next_1: str = ""
    hotkey_next_2: str = ""
    hotkey_rapid_fire_1: str = ""
    hotkey_rapid_fire_2: str = ""
    hotkey_shuffle_1: str = ""
    hotkey_shuffle_2: str = ""
    hotkey_reset_page_1: str = ""
    hotkey_reset_page_2: str = ""
    hotkey_play_list_1: str = ""
    hotkey_play_list_2: str = ""
    hotkey_fade_in_1: str = ""
    hotkey_fade_in_2: str = ""
    hotkey_cross_fade_1: str = ""
    hotkey_cross_fade_2: str = ""
    hotkey_fade_out_1: str = ""
    hotkey_fade_out_2: str = ""
    hotkey_mute_1: str = ""
    hotkey_mute_2: str = ""
    quick_action_enabled: bool = False
    quick_action_keys: list[str] = field(default_factory=default_quick_action_keys)
    sound_button_hotkey_enabled: bool = False
    sound_button_hotkey_priority: str = "system_first"
    sound_button_hotkey_go_to_playing: bool = False
    sound_button_hotkey_system_order: list[str] = field(default_factory=list)


def get_settings_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata)
    else:
        base = Path.home() / ".config"
    settings_dir = base / "pySSP"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "settings.ini"


def load_settings() -> AppSettings:
    settings_path = get_settings_path()
    if settings_path.exists():
        parser = configparser.ConfigParser()
        parser.read(settings_path, encoding="utf-8")
        return _from_parser(parser)

    seed = _seed_from_ssp_inf(Path(r"C:\SportsSoundsPro\SSP.inf"))
    save_settings(seed)
    return seed


def save_settings(settings: AppSettings) -> None:
    parser = configparser.ConfigParser()
    parser["main"] = {
        "last_open_dir": settings.last_open_dir,
        "last_save_dir": settings.last_save_dir,
        "last_sound_dir": settings.last_sound_dir,
        "last_set_path": settings.last_set_path,
        "active_group_color": settings.active_group_color,
        "inactive_group_color": settings.inactive_group_color,
        "title_char_limit": str(settings.title_char_limit),
        "show_file_notifications": "1" if settings.show_file_notifications else "0",
        "volume": str(settings.volume),
        "last_group": settings.last_group,
        "last_page": str(settings.last_page),
        "fade_in_sec": str(settings.fade_in_sec),
        "cross_fade_sec": str(settings.cross_fade_sec),
        "fade_out_sec": str(settings.fade_out_sec),
        "fade_on_quick_action_hotkey": "1" if settings.fade_on_quick_action_hotkey else "0",
        "fade_on_sound_button_hotkey": "1" if settings.fade_on_sound_button_hotkey else "0",
        "fade_on_pause": "1" if settings.fade_on_pause else "0",
        "fade_on_resume": "1" if settings.fade_on_resume else "0",
        "fade_on_stop": "1" if settings.fade_on_stop else "0",
        "fade_out_when_done_playing": "1" if settings.fade_out_when_done_playing else "0",
        "fade_out_end_lead_sec": str(settings.fade_out_end_lead_sec),
        "talk_volume_level": str(settings.talk_volume_level),
        "talk_fade_sec": str(settings.talk_fade_sec),
        "talk_volume_mode": settings.talk_volume_mode,
        "talk_blink_button": "1" if settings.talk_blink_button else "0",
        "talk_shift_accelerator": "1" if settings.talk_shift_accelerator else "0",
        "hotkeys_ignore_talk_level": "1" if settings.hotkeys_ignore_talk_level else "0",
        "enter_key_mirrors_space": "1" if settings.enter_key_mirrors_space else "0",
        "log_file_enabled": "1" if settings.log_file_enabled else "0",
        "reset_all_on_startup": "1" if settings.reset_all_on_startup else "0",
        "click_playing_action": settings.click_playing_action,
        "search_double_click_action": settings.search_double_click_action,
        "set_file_encoding": settings.set_file_encoding,
        "ui_language": settings.ui_language,
        "audio_output_device": settings.audio_output_device,
        "preload_audio_enabled": "1" if settings.preload_audio_enabled else "0",
        "preload_current_page_audio": "1" if settings.preload_current_page_audio else "0",
        "preload_audio_memory_limit_mb": str(settings.preload_audio_memory_limit_mb),
        "preload_memory_pressure_enabled": "1" if settings.preload_memory_pressure_enabled else "0",
        "preload_pause_on_playback": "1" if settings.preload_pause_on_playback else "0",
        "max_multi_play_songs": str(settings.max_multi_play_songs),
        "multi_play_limit_action": settings.multi_play_limit_action,
        "playlist_play_mode": settings.playlist_play_mode,
        "rapid_fire_play_mode": settings.rapid_fire_play_mode,
        "next_play_mode": settings.next_play_mode,
        "playlist_loop_mode": settings.playlist_loop_mode,
        "candidate_error_action": settings.candidate_error_action,
        "web_remote_enabled": "1" if settings.web_remote_enabled else "0",
        "web_remote_port": str(settings.web_remote_port),
        "timecode_audio_output_device": settings.timecode_audio_output_device,
        "timecode_midi_output_device": settings.timecode_midi_output_device,
        "timecode_mode": settings.timecode_mode,
        "timecode_fps": str(settings.timecode_fps),
        "timecode_mtc_fps": str(settings.timecode_mtc_fps),
        "timecode_mtc_idle_behavior": settings.timecode_mtc_idle_behavior,
        "timecode_sample_rate": str(settings.timecode_sample_rate),
        "timecode_bit_depth": str(settings.timecode_bit_depth),
        "show_timecode_panel": "1" if settings.show_timecode_panel else "0",
        "timecode_timeline_mode": settings.timecode_timeline_mode,
        "main_transport_timeline_mode": settings.main_transport_timeline_mode,
        "main_jog_outside_cue_action": settings.main_jog_outside_cue_action,
        "color_empty": settings.color_empty,
        "color_unplayed": settings.color_unplayed,
        "color_highlight": settings.color_highlight,
        "color_playing": settings.color_playing,
        "color_played": settings.color_played,
        "color_error": settings.color_error,
        "color_lock": settings.color_lock,
        "color_place_marker": settings.color_place_marker,
        "color_copied_to_cue": settings.color_copied_to_cue,
        "color_cue_indicator": settings.color_cue_indicator,
        "color_volume_indicator": settings.color_volume_indicator,
        "sound_button_text_color": settings.sound_button_text_color,
        "hotkey_new_set_1": settings.hotkey_new_set_1,
        "hotkey_new_set_2": settings.hotkey_new_set_2,
        "hotkey_open_set_1": settings.hotkey_open_set_1,
        "hotkey_open_set_2": settings.hotkey_open_set_2,
        "hotkey_save_set_1": settings.hotkey_save_set_1,
        "hotkey_save_set_2": settings.hotkey_save_set_2,
        "hotkey_save_set_as_1": settings.hotkey_save_set_as_1,
        "hotkey_save_set_as_2": settings.hotkey_save_set_as_2,
        "hotkey_search_1": settings.hotkey_search_1,
        "hotkey_search_2": settings.hotkey_search_2,
        "hotkey_options_1": settings.hotkey_options_1,
        "hotkey_options_2": settings.hotkey_options_2,
        "hotkey_play_selected_1": settings.hotkey_play_selected_1,
        "hotkey_play_selected_2": settings.hotkey_play_selected_2,
        "hotkey_pause_toggle_1": settings.hotkey_pause_toggle_1,
        "hotkey_pause_toggle_2": settings.hotkey_pause_toggle_2,
        "hotkey_stop_playback_1": settings.hotkey_stop_playback_1,
        "hotkey_stop_playback_2": settings.hotkey_stop_playback_2,
        "hotkey_talk_1": settings.hotkey_talk_1,
        "hotkey_talk_2": settings.hotkey_talk_2,
        "hotkey_next_group_1": settings.hotkey_next_group_1,
        "hotkey_next_group_2": settings.hotkey_next_group_2,
        "hotkey_prev_group_1": settings.hotkey_prev_group_1,
        "hotkey_prev_group_2": settings.hotkey_prev_group_2,
        "hotkey_next_page_1": settings.hotkey_next_page_1,
        "hotkey_next_page_2": settings.hotkey_next_page_2,
        "hotkey_prev_page_1": settings.hotkey_prev_page_1,
        "hotkey_prev_page_2": settings.hotkey_prev_page_2,
        "hotkey_next_sound_button_1": settings.hotkey_next_sound_button_1,
        "hotkey_next_sound_button_2": settings.hotkey_next_sound_button_2,
        "hotkey_prev_sound_button_1": settings.hotkey_prev_sound_button_1,
        "hotkey_prev_sound_button_2": settings.hotkey_prev_sound_button_2,
        "hotkey_multi_play_1": settings.hotkey_multi_play_1,
        "hotkey_multi_play_2": settings.hotkey_multi_play_2,
        "hotkey_go_to_playing_1": settings.hotkey_go_to_playing_1,
        "hotkey_go_to_playing_2": settings.hotkey_go_to_playing_2,
        "hotkey_loop_1": settings.hotkey_loop_1,
        "hotkey_loop_2": settings.hotkey_loop_2,
        "hotkey_next_1": settings.hotkey_next_1,
        "hotkey_next_2": settings.hotkey_next_2,
        "hotkey_rapid_fire_1": settings.hotkey_rapid_fire_1,
        "hotkey_rapid_fire_2": settings.hotkey_rapid_fire_2,
        "hotkey_shuffle_1": settings.hotkey_shuffle_1,
        "hotkey_shuffle_2": settings.hotkey_shuffle_2,
        "hotkey_reset_page_1": settings.hotkey_reset_page_1,
        "hotkey_reset_page_2": settings.hotkey_reset_page_2,
        "hotkey_play_list_1": settings.hotkey_play_list_1,
        "hotkey_play_list_2": settings.hotkey_play_list_2,
        "hotkey_fade_in_1": settings.hotkey_fade_in_1,
        "hotkey_fade_in_2": settings.hotkey_fade_in_2,
        "hotkey_cross_fade_1": settings.hotkey_cross_fade_1,
        "hotkey_cross_fade_2": settings.hotkey_cross_fade_2,
        "hotkey_fade_out_1": settings.hotkey_fade_out_1,
        "hotkey_fade_out_2": settings.hotkey_fade_out_2,
        "hotkey_mute_1": settings.hotkey_mute_1,
        "hotkey_mute_2": settings.hotkey_mute_2,
        "quick_action_enabled": "1" if settings.quick_action_enabled else "0",
        "quick_action_keys": "\t".join(_normalize_quick_action_keys(settings.quick_action_keys)),
        "sound_button_hotkey_enabled": "1" if settings.sound_button_hotkey_enabled else "0",
        "sound_button_hotkey_priority": settings.sound_button_hotkey_priority,
        "sound_button_hotkey_go_to_playing": "1" if settings.sound_button_hotkey_go_to_playing else "0",
        "sound_button_hotkey_system_order": "\t".join(settings.sound_button_hotkey_system_order),
    }
    with open(get_settings_path(), "w", encoding="utf-8") as fh:
        parser.write(fh)


def _from_parser(parser: configparser.ConfigParser) -> AppSettings:
    section = parser["main"] if parser.has_section("main") else {}
    volume = _clamp_int(_get_int(section, "volume", 90), 0, 100)
    title_limit = _clamp_int(_get_int(section, "title_char_limit", 26), 8, 80)
    page = _clamp_int(_get_int(section, "last_page", 0), 0, 17)
    fade_in_sec = _clamp_float(_get_float(section, "fade_in_sec", 1.0), 0.0, 20.0)
    cross_fade_sec = _clamp_float(_get_float(section, "cross_fade_sec", 1.0), 0.0, 20.0)
    fade_out_sec = _clamp_float(_get_float(section, "fade_out_sec", 1.0), 0.0, 20.0)
    fade_on_quick_action_hotkey = _get_bool(section, "fade_on_quick_action_hotkey", True)
    fade_on_sound_button_hotkey = _get_bool(section, "fade_on_sound_button_hotkey", True)
    fade_on_pause = _get_bool(section, "fade_on_pause", False)
    fade_on_resume = _get_bool(section, "fade_on_resume", False)
    fade_on_stop = _get_bool(section, "fade_on_stop", True)
    fade_out_when_done_playing = _get_bool(section, "fade_out_when_done_playing", False)
    fade_out_end_lead_sec = _clamp_float(_get_float(section, "fade_out_end_lead_sec", 2.0), 0.0, 30.0)
    talk_fade_sec = _clamp_float(_get_float(section, "talk_fade_sec", 0.5), 0.0, 20.0)
    talk_volume_level = _clamp_int(_get_int(section, "talk_volume_level", 30), 0, 100)
    talk_volume_mode = str(section.get("talk_volume_mode", "percent_of_master")).strip().lower()
    if talk_volume_mode not in {"percent_of_master", "lower_only", "set_exact"}:
        talk_volume_mode = "percent_of_master"
    group = str(section.get("last_group", "A")).upper()
    if group not in "ABCDEFGHIJ":
        group = "A"
    click_playing_action = str(section.get("click_playing_action", "play_it_again")).strip().lower()
    if click_playing_action not in {"play_it_again", "stop_it"}:
        click_playing_action = "play_it_again"
    search_double_click_action = str(section.get("search_double_click_action", "find_highlight")).strip().lower()
    if search_double_click_action not in {"find_highlight", "play_highlight"}:
        search_double_click_action = "find_highlight"
    set_file_encoding = str(section.get("set_file_encoding", "utf8")).strip().lower()
    if set_file_encoding not in {"utf8", "gbk"}:
        set_file_encoding = "utf8"
    ui_language = str(section.get("ui_language", "en")).strip().lower()
    if ui_language not in {"en", "zh", "zh_cn", "zh-cn"}:
        ui_language = "en"
    max_multi_play_songs = _clamp_int(_get_int(section, "max_multi_play_songs", 5), 1, 32)
    preload_audio_memory_limit_mb = _clamp_int(_get_int(section, "preload_audio_memory_limit_mb", 512), 64, 1048576)
    multi_play_limit_action = str(section.get("multi_play_limit_action", "stop_oldest")).strip().lower()
    if multi_play_limit_action not in {"disallow_more_play", "stop_oldest"}:
        multi_play_limit_action = "stop_oldest"
    playlist_play_mode = str(section.get("playlist_play_mode", "unplayed_only")).strip().lower()
    if playlist_play_mode not in {"unplayed_only", "any_available"}:
        playlist_play_mode = "unplayed_only"
    rapid_fire_play_mode = str(section.get("rapid_fire_play_mode", "unplayed_only")).strip().lower()
    if rapid_fire_play_mode not in {"unplayed_only", "any_available"}:
        rapid_fire_play_mode = "unplayed_only"
    next_play_mode = str(section.get("next_play_mode", "unplayed_only")).strip().lower()
    if next_play_mode not in {"unplayed_only", "any_available"}:
        next_play_mode = "unplayed_only"
    playlist_loop_mode = str(section.get("playlist_loop_mode", "loop_list")).strip().lower()
    if playlist_loop_mode not in {"loop_list", "loop_single"}:
        playlist_loop_mode = "loop_list"
    candidate_error_action = str(section.get("candidate_error_action", "stop_playback")).strip().lower()
    if candidate_error_action not in {"stop_playback", "keep_playing"}:
        candidate_error_action = "stop_playback"
    web_remote_port = _clamp_int(_get_int(section, "web_remote_port", 5050), 1, 65535)
    timecode_audio_output_device = str(section.get("timecode_audio_output_device", "none")).strip()
    timecode_midi_output_device = str(section.get("timecode_midi_output_device", "__none__")).strip()
    timecode_mode = str(section.get("timecode_mode", "follow_media")).strip().lower()
    if timecode_mode not in {"zero", "follow_media", "system_time", "follow_media_freeze"}:
        timecode_mode = "follow_media"
    timecode_fps = _clamp_float(_get_float(section, "timecode_fps", 30.0), 1.0, 120.0)
    timecode_mtc_fps = _clamp_float(_get_float(section, "timecode_mtc_fps", 30.0), 1.0, 120.0)
    timecode_mtc_idle_behavior = str(section.get("timecode_mtc_idle_behavior", "keep_stream")).strip().lower()
    if timecode_mtc_idle_behavior not in {"keep_stream", "allow_dark"}:
        timecode_mtc_idle_behavior = "keep_stream"
    timecode_sample_rate = _clamp_int(_get_int(section, "timecode_sample_rate", 48000), 8000, 192000)
    if timecode_sample_rate not in {44100, 48000, 96000}:
        timecode_sample_rate = 48000
    timecode_bit_depth = _clamp_int(_get_int(section, "timecode_bit_depth", 16), 8, 32)
    if timecode_bit_depth not in {8, 16, 32}:
        timecode_bit_depth = 16
    timecode_timeline_mode_raw = str(
        section.get("timecode_timeline_mode", section.get("main_transport_timeline_mode", "cue_region"))
    ).strip().lower()
    if timecode_timeline_mode_raw not in {"cue_region", "audio_file"}:
        timecode_timeline_mode_raw = "cue_region"
    timeline_mode_raw = str(
        section.get("main_transport_timeline_mode", section.get("cue_editor_timeline_mode", "cue_region"))
    ).strip().lower()
    if timeline_mode_raw not in {"cue_region", "audio_file"}:
        timeline_mode_raw = "cue_region"
    outside_action = str(section.get("main_jog_outside_cue_action", "stop_immediately")).strip().lower()
    if outside_action not in {
        "stop_immediately",
        "ignore_cue",
        "next_cue_or_stop",
        "stop_cue_or_end",
    }:
        outside_action = "stop_immediately"
    sound_button_hotkey_priority = str(section.get("sound_button_hotkey_priority", "system_first")).strip().lower()
    if sound_button_hotkey_priority not in {"system_first", "sound_button_first"}:
        sound_button_hotkey_priority = "system_first"
    sound_button_hotkey_system_order = [
        item.strip() for item in str(section.get("sound_button_hotkey_system_order", "")).split("\t") if item.strip()
    ]
    quick_action_raw = str(section.get("quick_action_keys", "")).strip()
    if quick_action_raw:
        quick_action_keys = _normalize_quick_action_keys(quick_action_raw.split("\t"))
    else:
        quick_action_keys = default_quick_action_keys()
    return AppSettings(
        last_open_dir=str(section.get("last_open_dir", "")),
        last_save_dir=str(section.get("last_save_dir", "")),
        last_sound_dir=str(section.get("last_sound_dir", "")),
        last_set_path=str(section.get("last_set_path", "")),
        active_group_color=_coerce_hex(str(section.get("active_group_color", "#EDE8C8")), "#EDE8C8"),
        inactive_group_color=_coerce_hex(str(section.get("inactive_group_color", "#ECECEC")), "#ECECEC"),
        title_char_limit=title_limit,
        show_file_notifications=_get_bool(section, "show_file_notifications", True),
        volume=volume,
        last_group=group,
        last_page=page,
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
        talk_volume_level=talk_volume_level,
        talk_fade_sec=talk_fade_sec,
        talk_volume_mode=talk_volume_mode,
        talk_blink_button=_get_bool(section, "talk_blink_button", False),
        talk_shift_accelerator=_get_bool(section, "talk_shift_accelerator", True),
        hotkeys_ignore_talk_level=_get_bool(section, "hotkeys_ignore_talk_level", False),
        enter_key_mirrors_space=_get_bool(section, "enter_key_mirrors_space", False),
        log_file_enabled=_get_bool(section, "log_file_enabled", False),
        reset_all_on_startup=_get_bool(section, "reset_all_on_startup", False),
        click_playing_action=click_playing_action,
        search_double_click_action=search_double_click_action,
        set_file_encoding=set_file_encoding,
        ui_language="zh_cn" if ui_language in {"zh", "zh_cn", "zh-cn"} else "en",
        audio_output_device=str(section.get("audio_output_device", "")),
        preload_audio_enabled=_get_bool(section, "preload_audio_enabled", False),
        preload_current_page_audio=_get_bool(section, "preload_current_page_audio", True),
        preload_audio_memory_limit_mb=preload_audio_memory_limit_mb,
        preload_memory_pressure_enabled=_get_bool(section, "preload_memory_pressure_enabled", True),
        preload_pause_on_playback=_get_bool(section, "preload_pause_on_playback", False),
        max_multi_play_songs=max_multi_play_songs,
        multi_play_limit_action=multi_play_limit_action,
        playlist_play_mode=playlist_play_mode,
        rapid_fire_play_mode=rapid_fire_play_mode,
        next_play_mode=next_play_mode,
        playlist_loop_mode=playlist_loop_mode,
        candidate_error_action=candidate_error_action,
        web_remote_enabled=_get_bool(section, "web_remote_enabled", False),
        web_remote_port=web_remote_port,
        timecode_audio_output_device=timecode_audio_output_device,
        timecode_midi_output_device=timecode_midi_output_device,
        timecode_mode=timecode_mode,
        timecode_fps=timecode_fps,
        timecode_mtc_fps=timecode_mtc_fps,
        timecode_mtc_idle_behavior=timecode_mtc_idle_behavior,
        timecode_sample_rate=timecode_sample_rate,
        timecode_bit_depth=timecode_bit_depth,
        show_timecode_panel=_get_bool(section, "show_timecode_panel", False),
        timecode_timeline_mode=timecode_timeline_mode_raw,
        main_transport_timeline_mode=timeline_mode_raw,
        main_jog_outside_cue_action=outside_action,
        color_empty=_coerce_hex(str(section.get("color_empty", "#0B868A")), "#0B868A"),
        color_unplayed=_coerce_hex(str(section.get("color_unplayed", "#B0B0B0")), "#B0B0B0"),
        color_highlight=_coerce_hex(str(section.get("color_highlight", "#A6D8FF")), "#A6D8FF"),
        color_playing=_coerce_hex(str(section.get("color_playing", "#66FF33")), "#66FF33"),
        color_played=_coerce_hex(str(section.get("color_played", "#FF3B30")), "#FF3B30"),
        color_error=_coerce_hex(str(section.get("color_error", "#7B3FB3")), "#7B3FB3"),
        color_lock=_coerce_hex(str(section.get("color_lock", "#F2D74A")), "#F2D74A"),
        color_place_marker=_coerce_hex(str(section.get("color_place_marker", "#111111")), "#111111"),
        color_copied_to_cue=_coerce_hex(str(section.get("color_copied_to_cue", "#2E65FF")), "#2E65FF"),
        color_cue_indicator=_coerce_hex(str(section.get("color_cue_indicator", "#61D6FF")), "#61D6FF"),
        color_volume_indicator=_coerce_hex(str(section.get("color_volume_indicator", "#FFD45A")), "#FFD45A"),
        sound_button_text_color=_coerce_hex(str(section.get("sound_button_text_color", "#000000")), "#000000"),
        hotkey_new_set_1=str(section.get("hotkey_new_set_1", "Ctrl+N")).strip(),
        hotkey_new_set_2=str(section.get("hotkey_new_set_2", "")).strip(),
        hotkey_open_set_1=str(section.get("hotkey_open_set_1", "Ctrl+O")).strip(),
        hotkey_open_set_2=str(section.get("hotkey_open_set_2", "")).strip(),
        hotkey_save_set_1=str(section.get("hotkey_save_set_1", "Ctrl+S")).strip(),
        hotkey_save_set_2=str(section.get("hotkey_save_set_2", "")).strip(),
        hotkey_save_set_as_1=str(section.get("hotkey_save_set_as_1", "Ctrl+Shift+S")).strip(),
        hotkey_save_set_as_2=str(section.get("hotkey_save_set_as_2", "")).strip(),
        hotkey_search_1=str(section.get("hotkey_search_1", "Ctrl+F")).strip(),
        hotkey_search_2=str(section.get("hotkey_search_2", "")).strip(),
        hotkey_options_1=str(section.get("hotkey_options_1", "")).strip(),
        hotkey_options_2=str(section.get("hotkey_options_2", "")).strip(),
        hotkey_play_selected_1=str(section.get("hotkey_play_selected_1", "")).strip(),
        hotkey_play_selected_2=str(section.get("hotkey_play_selected_2", "")).strip(),
        hotkey_pause_toggle_1=str(section.get("hotkey_pause_toggle_1", "P")).strip(),
        hotkey_pause_toggle_2=str(section.get("hotkey_pause_toggle_2", "")).strip(),
        hotkey_stop_playback_1=str(section.get("hotkey_stop_playback_1", "Space")).strip(),
        hotkey_stop_playback_2=str(section.get("hotkey_stop_playback_2", "Return")).strip(),
        hotkey_talk_1=str(section.get("hotkey_talk_1", "Shift")).strip(),
        hotkey_talk_2=str(section.get("hotkey_talk_2", "")).strip(),
        hotkey_next_group_1=str(section.get("hotkey_next_group_1", "")).strip(),
        hotkey_next_group_2=str(section.get("hotkey_next_group_2", "")).strip(),
        hotkey_prev_group_1=str(section.get("hotkey_prev_group_1", "")).strip(),
        hotkey_prev_group_2=str(section.get("hotkey_prev_group_2", "")).strip(),
        hotkey_next_page_1=str(section.get("hotkey_next_page_1", "")).strip(),
        hotkey_next_page_2=str(section.get("hotkey_next_page_2", "")).strip(),
        hotkey_prev_page_1=str(section.get("hotkey_prev_page_1", "")).strip(),
        hotkey_prev_page_2=str(section.get("hotkey_prev_page_2", "")).strip(),
        hotkey_next_sound_button_1=str(section.get("hotkey_next_sound_button_1", "")).strip(),
        hotkey_next_sound_button_2=str(section.get("hotkey_next_sound_button_2", "")).strip(),
        hotkey_prev_sound_button_1=str(section.get("hotkey_prev_sound_button_1", "")).strip(),
        hotkey_prev_sound_button_2=str(section.get("hotkey_prev_sound_button_2", "")).strip(),
        hotkey_multi_play_1=str(section.get("hotkey_multi_play_1", "")).strip(),
        hotkey_multi_play_2=str(section.get("hotkey_multi_play_2", "")).strip(),
        hotkey_go_to_playing_1=str(section.get("hotkey_go_to_playing_1", "")).strip(),
        hotkey_go_to_playing_2=str(section.get("hotkey_go_to_playing_2", "")).strip(),
        hotkey_loop_1=str(section.get("hotkey_loop_1", "")).strip(),
        hotkey_loop_2=str(section.get("hotkey_loop_2", "")).strip(),
        hotkey_next_1=str(section.get("hotkey_next_1", "")).strip(),
        hotkey_next_2=str(section.get("hotkey_next_2", "")).strip(),
        hotkey_rapid_fire_1=str(section.get("hotkey_rapid_fire_1", "")).strip(),
        hotkey_rapid_fire_2=str(section.get("hotkey_rapid_fire_2", "")).strip(),
        hotkey_shuffle_1=str(section.get("hotkey_shuffle_1", "")).strip(),
        hotkey_shuffle_2=str(section.get("hotkey_shuffle_2", "")).strip(),
        hotkey_reset_page_1=str(section.get("hotkey_reset_page_1", "")).strip(),
        hotkey_reset_page_2=str(section.get("hotkey_reset_page_2", "")).strip(),
        hotkey_play_list_1=str(section.get("hotkey_play_list_1", "")).strip(),
        hotkey_play_list_2=str(section.get("hotkey_play_list_2", "")).strip(),
        hotkey_fade_in_1=str(section.get("hotkey_fade_in_1", "")).strip(),
        hotkey_fade_in_2=str(section.get("hotkey_fade_in_2", "")).strip(),
        hotkey_cross_fade_1=str(section.get("hotkey_cross_fade_1", "")).strip(),
        hotkey_cross_fade_2=str(section.get("hotkey_cross_fade_2", "")).strip(),
        hotkey_fade_out_1=str(section.get("hotkey_fade_out_1", "")).strip(),
        hotkey_fade_out_2=str(section.get("hotkey_fade_out_2", "")).strip(),
        hotkey_mute_1=str(section.get("hotkey_mute_1", "")).strip(),
        hotkey_mute_2=str(section.get("hotkey_mute_2", "")).strip(),
        quick_action_enabled=_get_bool(section, "quick_action_enabled", False),
        quick_action_keys=quick_action_keys,
        sound_button_hotkey_enabled=_get_bool(section, "sound_button_hotkey_enabled", False),
        sound_button_hotkey_priority=sound_button_hotkey_priority,
        sound_button_hotkey_go_to_playing=_get_bool(section, "sound_button_hotkey_go_to_playing", False),
        sound_button_hotkey_system_order=sound_button_hotkey_system_order,
    )


def _seed_from_ssp_inf(ssp_inf_path: Path) -> AppSettings:
    settings = AppSettings()
    if not ssp_inf_path.exists():
        return settings

    parser = configparser.ConfigParser()
    try:
        parser.read(ssp_inf_path, encoding="utf-8")
    except UnicodeDecodeError:
        parser.read(ssp_inf_path, encoding="latin1")
    if not parser.has_section("Main"):
        return settings

    section = parser["Main"]
    auto_open = str(section.get("AutoOpen", "")).strip()
    if auto_open:
        settings.last_set_path = auto_open
        settings.last_open_dir = str(Path(auto_open).parent)
        settings.last_save_dir = str(Path(auto_open).parent)

    active = parse_delphi_color(str(section.get("ActiveButtonColor", "")).strip())
    if active:
        settings.active_group_color = active

    volume = _clamp_int(_get_int(section, "Volume", settings.volume), 0, 100)
    settings.volume = volume
    settings.fade_in_sec = _clamp_float(_get_float(section, "FadeInSec", settings.fade_in_sec), 0.0, 20.0)
    settings.cross_fade_sec = _clamp_float(_get_float(section, "CrossFadeSec", settings.cross_fade_sec), 0.0, 20.0)
    settings.fade_out_sec = _clamp_float(_get_float(section, "FadeOutSec", settings.fade_out_sec), 0.0, 20.0)
    settings.talk_volume_level = _clamp_int(_get_int(section, "VoiceOverVolume", settings.talk_volume_level), 0, 100)
    settings.talk_fade_sec = _clamp_float(_get_float(section, "VoiceOverSec", settings.talk_fade_sec), 0.0, 20.0)
    settings.talk_blink_button = _get_yes_no_bool(section, "VoiceOverBlink", settings.talk_blink_button)
    settings.talk_shift_accelerator = _get_yes_no_bool(section, "ShiftKey", settings.talk_shift_accelerator)
    settings.hotkeys_ignore_talk_level = _get_yes_no_bool(section, "HKOverTalk", settings.hotkeys_ignore_talk_level)

    group_num = _clamp_int(_get_int(section, "Group", 1), 1, 10)
    settings.last_group = "ABCDEFGHIJ"[group_num - 1]
    settings.last_page = _clamp_int(_get_int(section, "Page", 1) - 1, 0, 17)
    return settings


def _get_bool(section, key: str, default: bool) -> bool:
    raw = str(section.get(key, "1" if default else "0")).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _get_int(section, key: str, default: int) -> int:
    try:
        return int(str(section.get(key, str(default))).strip())
    except ValueError:
        return default


def _get_float(section, key: str, default: float) -> float:
    try:
        return float(str(section.get(key, str(default))).strip())
    except ValueError:
        return default


def _get_yes_no_bool(section, key: str, default: bool) -> bool:
    raw = str(section.get(key, "YES" if default else "NO")).strip().upper()
    if raw == "YES":
        return True
    if raw == "NO":
        return False
    return default


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def _clamp_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _coerce_hex(value: str, fallback: str) -> str:
    color = value.strip()
    if len(color) == 7 and color.startswith("#"):
        try:
            int(color[1:], 16)
            return color.upper()
        except ValueError:
            return fallback
    return fallback
