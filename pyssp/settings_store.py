from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from pyssp.set_loader import parse_delphi_color


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
    talk_volume_level: int = 30
    talk_fade_sec: float = 0.5
    talk_blink_button: bool = False
    talk_shift_accelerator: bool = True
    hotkeys_ignore_talk_level: bool = False
    enter_key_mirrors_space: bool = False
    log_file_enabled: bool = False
    reset_all_on_startup: bool = False
    click_playing_action: str = "play_it_again"
    search_double_click_action: str = "find_highlight"
    audio_output_device: str = ""


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
        "talk_volume_level": str(settings.talk_volume_level),
        "talk_fade_sec": str(settings.talk_fade_sec),
        "talk_blink_button": "1" if settings.talk_blink_button else "0",
        "talk_shift_accelerator": "1" if settings.talk_shift_accelerator else "0",
        "hotkeys_ignore_talk_level": "1" if settings.hotkeys_ignore_talk_level else "0",
        "enter_key_mirrors_space": "1" if settings.enter_key_mirrors_space else "0",
        "log_file_enabled": "1" if settings.log_file_enabled else "0",
        "reset_all_on_startup": "1" if settings.reset_all_on_startup else "0",
        "click_playing_action": settings.click_playing_action,
        "search_double_click_action": settings.search_double_click_action,
        "audio_output_device": settings.audio_output_device,
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
    talk_fade_sec = _clamp_float(_get_float(section, "talk_fade_sec", 0.5), 0.0, 20.0)
    talk_volume_level = _clamp_int(_get_int(section, "talk_volume_level", 30), 0, 100)
    group = str(section.get("last_group", "A")).upper()
    if group not in "ABCDEFGHIJ":
        group = "A"
    click_playing_action = str(section.get("click_playing_action", "play_it_again")).strip().lower()
    if click_playing_action not in {"play_it_again", "stop_it"}:
        click_playing_action = "play_it_again"
    search_double_click_action = str(section.get("search_double_click_action", "find_highlight")).strip().lower()
    if search_double_click_action not in {"find_highlight", "play_highlight"}:
        search_double_click_action = "find_highlight"
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
        talk_volume_level=talk_volume_level,
        talk_fade_sec=talk_fade_sec,
        talk_blink_button=_get_bool(section, "talk_blink_button", False),
        talk_shift_accelerator=_get_bool(section, "talk_shift_accelerator", True),
        hotkeys_ignore_talk_level=_get_bool(section, "hotkeys_ignore_talk_level", False),
        enter_key_mirrors_space=_get_bool(section, "enter_key_mirrors_space", False),
        log_file_enabled=_get_bool(section, "log_file_enabled", False),
        reset_all_on_startup=_get_bool(section, "reset_all_on_startup", False),
        click_playing_action=click_playing_action,
        search_double_click_action=search_double_click_action,
        audio_output_device=str(section.get("audio_output_device", "")),
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
