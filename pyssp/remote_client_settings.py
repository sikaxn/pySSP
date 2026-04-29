from __future__ import annotations

import configparser
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from pyssp.ui.stage_display import normalize_stage_display_gadgets


def _default_stage_gadgets() -> dict[str, dict[str, int | bool | str]]:
    return normalize_stage_display_gadgets({})


@dataclass
class RemoteClientSettings:
    server_host: str = "127.0.0.1"
    server_http_port: int = 5050
    lyric_display_transparent_mode: bool = False
    lyric_display_show_not_playing_message: bool = True
    lyric_display_font_family: str = ""
    lyric_display_font_size: int = 36
    lyric_display_previous_line_count: int = 0
    lyric_display_next_line_count: int = 0
    lyric_display_played_color: str = "#A0A0A0"
    lyric_display_current_color: str = "#FFD400"
    lyric_display_next_color: str = "#FFFFFF"
    lyric_display_auto_adjust_role_sizes: bool = True
    lyric_display_played_scale_percent: int = 70
    lyric_display_current_scale_percent: int = 115
    lyric_display_next_scale_percent: int = 90
    lyric_display_played_text_size: int = 24
    lyric_display_current_text_size: int = 40
    lyric_display_next_text_size: int = 32
    lyric_display_played_bold: bool = True
    lyric_display_current_bold: bool = True
    lyric_display_next_bold: bool = True
    lyric_display_played_italic: bool = False
    lyric_display_current_italic: bool = False
    lyric_display_next_italic: bool = False
    stage_display_open_on_startup: bool = False
    stage_display_gadgets: dict[str, dict[str, int | bool | str]] = field(default_factory=_default_stage_gadgets)
    stage_display_font_family: str = ""
    stage_display_font_size: int = 24
    stage_display_lyric_font_family: str = ""
    stage_display_lyric_font_size: int = 24
    stage_display_lyric_previous_line_count: int = 0
    stage_display_lyric_next_line_count: int = 0
    stage_display_lyric_played_color: str = "#A0A0A0"
    stage_display_lyric_current_color: str = "#FFD400"
    stage_display_lyric_next_color: str = "#FFFFFF"
    stage_display_lyric_auto_adjust_role_sizes: bool = True
    stage_display_lyric_played_scale_percent: int = 70
    stage_display_lyric_current_scale_percent: int = 115
    stage_display_lyric_next_scale_percent: int = 90
    stage_display_lyric_played_text_size: int = 18
    stage_display_lyric_current_text_size: int = 28
    stage_display_lyric_next_text_size: int = 22
    stage_display_lyric_played_bold: bool = True
    stage_display_lyric_current_bold: bool = True
    stage_display_lyric_next_bold: bool = True
    stage_display_lyric_played_italic: bool = False
    stage_display_lyric_current_italic: bool = False
    stage_display_lyric_next_italic: bool = False

    @property
    def server_ws_port(self) -> int:
        return int(self.server_http_port) + 1


def get_remote_client_settings_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata)
    else:
        base = Path.home() / ".config"
    settings_dir = base / "pySSP Remote Client"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "settings.ini"


def load_remote_client_settings(path: Path | None = None) -> RemoteClientSettings:
    settings_path = path or get_remote_client_settings_path()
    if not settings_path.exists():
        settings = RemoteClientSettings()
        save_remote_client_settings(settings, path=settings_path)
        return settings
    parser = configparser.ConfigParser()
    parser.read(settings_path, encoding="utf-8")
    return _from_parser(parser)


def save_remote_client_settings(settings: RemoteClientSettings, path: Path | None = None) -> None:
    parser = configparser.ConfigParser()
    parser["main"] = {
        "server_host": str(settings.server_host or "127.0.0.1").strip() or "127.0.0.1",
        "server_http_port": str(_clamp_int(int(settings.server_http_port), 1, 65534)),
        "lyric_display_transparent_mode": "1" if settings.lyric_display_transparent_mode else "0",
        "lyric_display_show_not_playing_message": "1" if settings.lyric_display_show_not_playing_message else "0",
        "lyric_display_font_family": settings.lyric_display_font_family,
        "lyric_display_font_size": str(settings.lyric_display_font_size),
        "lyric_display_previous_line_count": str(settings.lyric_display_previous_line_count),
        "lyric_display_next_line_count": str(settings.lyric_display_next_line_count),
        "lyric_display_played_color": settings.lyric_display_played_color,
        "lyric_display_current_color": settings.lyric_display_current_color,
        "lyric_display_next_color": settings.lyric_display_next_color,
        "lyric_display_auto_adjust_role_sizes": "1" if settings.lyric_display_auto_adjust_role_sizes else "0",
        "lyric_display_played_scale_percent": str(settings.lyric_display_played_scale_percent),
        "lyric_display_current_scale_percent": str(settings.lyric_display_current_scale_percent),
        "lyric_display_next_scale_percent": str(settings.lyric_display_next_scale_percent),
        "lyric_display_played_text_size": str(settings.lyric_display_played_text_size),
        "lyric_display_current_text_size": str(settings.lyric_display_current_text_size),
        "lyric_display_next_text_size": str(settings.lyric_display_next_text_size),
        "lyric_display_played_bold": "1" if settings.lyric_display_played_bold else "0",
        "lyric_display_current_bold": "1" if settings.lyric_display_current_bold else "0",
        "lyric_display_next_bold": "1" if settings.lyric_display_next_bold else "0",
        "lyric_display_played_italic": "1" if settings.lyric_display_played_italic else "0",
        "lyric_display_current_italic": "1" if settings.lyric_display_current_italic else "0",
        "lyric_display_next_italic": "1" if settings.lyric_display_next_italic else "0",
        "stage_display_open_on_startup": "1" if settings.stage_display_open_on_startup else "0",
        "stage_display_gadgets": json.dumps(normalize_stage_display_gadgets(settings.stage_display_gadgets), ensure_ascii=True),
        "stage_display_font_family": settings.stage_display_font_family,
        "stage_display_font_size": str(settings.stage_display_font_size),
        "stage_display_lyric_font_family": settings.stage_display_lyric_font_family,
        "stage_display_lyric_font_size": str(settings.stage_display_lyric_font_size),
        "stage_display_lyric_previous_line_count": str(settings.stage_display_lyric_previous_line_count),
        "stage_display_lyric_next_line_count": str(settings.stage_display_lyric_next_line_count),
        "stage_display_lyric_played_color": settings.stage_display_lyric_played_color,
        "stage_display_lyric_current_color": settings.stage_display_lyric_current_color,
        "stage_display_lyric_next_color": settings.stage_display_lyric_next_color,
        "stage_display_lyric_auto_adjust_role_sizes": "1" if settings.stage_display_lyric_auto_adjust_role_sizes else "0",
        "stage_display_lyric_played_scale_percent": str(settings.stage_display_lyric_played_scale_percent),
        "stage_display_lyric_current_scale_percent": str(settings.stage_display_lyric_current_scale_percent),
        "stage_display_lyric_next_scale_percent": str(settings.stage_display_lyric_next_scale_percent),
        "stage_display_lyric_played_text_size": str(settings.stage_display_lyric_played_text_size),
        "stage_display_lyric_current_text_size": str(settings.stage_display_lyric_current_text_size),
        "stage_display_lyric_next_text_size": str(settings.stage_display_lyric_next_text_size),
        "stage_display_lyric_played_bold": "1" if settings.stage_display_lyric_played_bold else "0",
        "stage_display_lyric_current_bold": "1" if settings.stage_display_lyric_current_bold else "0",
        "stage_display_lyric_next_bold": "1" if settings.stage_display_lyric_next_bold else "0",
        "stage_display_lyric_played_italic": "1" if settings.stage_display_lyric_played_italic else "0",
        "stage_display_lyric_current_italic": "1" if settings.stage_display_lyric_current_italic else "0",
        "stage_display_lyric_next_italic": "1" if settings.stage_display_lyric_next_italic else "0",
    }
    settings_path = path or get_remote_client_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with settings_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)


def _from_parser(parser: configparser.ConfigParser) -> RemoteClientSettings:
    section = parser["main"] if parser.has_section("main") else {}
    gadgets_raw = str(section.get("stage_display_gadgets", "")).strip()
    try:
        gadgets = json.loads(gadgets_raw) if gadgets_raw else {}
    except Exception:
        gadgets = {}
    return RemoteClientSettings(
        server_host=str(section.get("server_host", "127.0.0.1")).strip() or "127.0.0.1",
        server_http_port=_clamp_int(_get_int(section, "server_http_port", 5050), 1, 65534),
        lyric_display_transparent_mode=_get_bool(section, "lyric_display_transparent_mode", False),
        lyric_display_show_not_playing_message=_get_bool(section, "lyric_display_show_not_playing_message", True),
        lyric_display_font_family=str(section.get("lyric_display_font_family", "")).strip(),
        lyric_display_font_size=_clamp_int(_get_int(section, "lyric_display_font_size", 36), 10, 240),
        lyric_display_previous_line_count=_clamp_int(_get_int(section, "lyric_display_previous_line_count", 0), 0, 20),
        lyric_display_next_line_count=_clamp_int(_get_int(section, "lyric_display_next_line_count", 0), 0, 20),
        lyric_display_played_color=_coerce_hex(str(section.get("lyric_display_played_color", "#A0A0A0")), "#A0A0A0"),
        lyric_display_current_color=_coerce_hex(str(section.get("lyric_display_current_color", "#FFD400")), "#FFD400"),
        lyric_display_next_color=_coerce_hex(str(section.get("lyric_display_next_color", "#FFFFFF")), "#FFFFFF"),
        lyric_display_auto_adjust_role_sizes=_get_bool(section, "lyric_display_auto_adjust_role_sizes", True),
        lyric_display_played_scale_percent=_clamp_int(_get_int(section, "lyric_display_played_scale_percent", 70), 25, 300),
        lyric_display_current_scale_percent=_clamp_int(_get_int(section, "lyric_display_current_scale_percent", 115), 25, 300),
        lyric_display_next_scale_percent=_clamp_int(_get_int(section, "lyric_display_next_scale_percent", 90), 25, 300),
        lyric_display_played_text_size=_clamp_int(_get_int(section, "lyric_display_played_text_size", 24), 8, 240),
        lyric_display_current_text_size=_clamp_int(_get_int(section, "lyric_display_current_text_size", 40), 8, 240),
        lyric_display_next_text_size=_clamp_int(_get_int(section, "lyric_display_next_text_size", 32), 8, 240),
        lyric_display_played_bold=_get_bool(section, "lyric_display_played_bold", True),
        lyric_display_current_bold=_get_bool(section, "lyric_display_current_bold", True),
        lyric_display_next_bold=_get_bool(section, "lyric_display_next_bold", True),
        lyric_display_played_italic=_get_bool(section, "lyric_display_played_italic", False),
        lyric_display_current_italic=_get_bool(section, "lyric_display_current_italic", False),
        lyric_display_next_italic=_get_bool(section, "lyric_display_next_italic", False),
        stage_display_open_on_startup=_get_bool(section, "stage_display_open_on_startup", False),
        stage_display_gadgets=normalize_stage_display_gadgets(gadgets),
        stage_display_font_family=str(section.get("stage_display_font_family", "")).strip(),
        stage_display_font_size=_clamp_int(_get_int(section, "stage_display_font_size", 24), 10, 240),
        stage_display_lyric_font_family=str(section.get("stage_display_lyric_font_family", "")).strip(),
        stage_display_lyric_font_size=_clamp_int(_get_int(section, "stage_display_lyric_font_size", 24), 10, 240),
        stage_display_lyric_previous_line_count=_clamp_int(_get_int(section, "stage_display_lyric_previous_line_count", 0), 0, 20),
        stage_display_lyric_next_line_count=_clamp_int(_get_int(section, "stage_display_lyric_next_line_count", 0), 0, 20),
        stage_display_lyric_played_color=_coerce_hex(str(section.get("stage_display_lyric_played_color", "#A0A0A0")), "#A0A0A0"),
        stage_display_lyric_current_color=_coerce_hex(str(section.get("stage_display_lyric_current_color", "#FFD400")), "#FFD400"),
        stage_display_lyric_next_color=_coerce_hex(str(section.get("stage_display_lyric_next_color", "#FFFFFF")), "#FFFFFF"),
        stage_display_lyric_auto_adjust_role_sizes=_get_bool(section, "stage_display_lyric_auto_adjust_role_sizes", True),
        stage_display_lyric_played_scale_percent=_clamp_int(_get_int(section, "stage_display_lyric_played_scale_percent", 70), 25, 300),
        stage_display_lyric_current_scale_percent=_clamp_int(_get_int(section, "stage_display_lyric_current_scale_percent", 115), 25, 300),
        stage_display_lyric_next_scale_percent=_clamp_int(_get_int(section, "stage_display_lyric_next_scale_percent", 90), 25, 300),
        stage_display_lyric_played_text_size=_clamp_int(_get_int(section, "stage_display_lyric_played_text_size", 18), 8, 240),
        stage_display_lyric_current_text_size=_clamp_int(_get_int(section, "stage_display_lyric_current_text_size", 28), 8, 240),
        stage_display_lyric_next_text_size=_clamp_int(_get_int(section, "stage_display_lyric_next_text_size", 22), 8, 240),
        stage_display_lyric_played_bold=_get_bool(section, "stage_display_lyric_played_bold", True),
        stage_display_lyric_current_bold=_get_bool(section, "stage_display_lyric_current_bold", True),
        stage_display_lyric_next_bold=_get_bool(section, "stage_display_lyric_next_bold", True),
        stage_display_lyric_played_italic=_get_bool(section, "stage_display_lyric_played_italic", False),
        stage_display_lyric_current_italic=_get_bool(section, "stage_display_lyric_current_italic", False),
        stage_display_lyric_next_italic=_get_bool(section, "stage_display_lyric_next_italic", False),
    )


def _get_bool(section, key: str, default: bool) -> bool:
    raw = str(section.get(key, "1" if default else "0")).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _get_int(section, key: str, default: int) -> int:
    try:
        return int(str(section.get(key, str(default))).strip())
    except Exception:
        return default


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _coerce_hex(value: str, fallback: str) -> str:
    token = str(value or "").strip()
    if len(token) == 7 and token.startswith("#"):
        try:
            int(token[1:], 16)
            return token.upper()
        except ValueError:
            return fallback
    return fallback
