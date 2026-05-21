from __future__ import annotations

import configparser
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from pyssp.display_focus import (
    DISPLAY_FOCUS_COLOUR_BARS,
    DISPLAY_FOCUS_FOLLOW,
    DISPLAY_FOCUS_LYRIC,
    DISPLAY_FOCUS_METRONOME,
    DISPLAY_FOCUS_NONE,
    DISPLAY_FOCUS_VIDEO,
    DISPLAY_ROUTE_SOURCE_BLANK,
    normalize_display_focus,
    normalize_display_focus_override,
    normalize_display_route_source,
    normalize_display_output_mode,
)
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


def default_midi_quick_action_bindings() -> list[str]:
    return ["" for _ in range(48)]


def _normalize_midi_quick_action_bindings(values: list[str]) -> list[str]:
    output = [str(v or "").strip() for v in values[:48]]
    if len(output) < 48:
        output.extend(["" for _ in range(48 - len(output))])
    return output[:48]


def _encode_ascii_setting(value: str) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def _decode_ascii_setting(value: str) -> str:
    raw = str(value)
    if not raw:
        return ""
    try:
        decoded = json.loads(raw)
    except Exception:
        return raw
    return decoded if isinstance(decoded, str) else raw


def default_companion_satellite_serial_suffix() -> str:
    node = int(uuid.getnode())
    return f"{node:012x}"


def _normalize_companion_satellite_serial_suffix(raw: object) -> str:
    text = str(raw or "").strip().lower()
    if text.startswith("pyssp:"):
        text = text.partition(":")[2].strip().lower()
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch in {"-", "_"})
    return cleaned or default_companion_satellite_serial_suffix()


def _normalize_companion_satellite_render_mode(raw: object) -> str:
    token = str(raw or "").strip().lower()
    return token if token in {"bitmap", "styled"} else "bitmap"


def _normalize_companion_command_mode(raw: object) -> str:
    token = str(raw or "").strip().lower()
    return token if token in {"udp", "tcp", "http"} else "tcp"


def default_stage_display_layout() -> list[str]:
    return [
        "current_time",
        "total_time",
        "elapsed",
        "remaining",
        "progress_bar",
        "song_name",
        "lyric",
        "next_song",
        "alert",
    ]


def default_video_display_lyric_overlay_rect() -> dict[str, int]:
    return {
        "x": 800,
        "y": 6800,
        "w": 8400,
        "h": 2400,
    }


def _normalize_video_display_lyric_overlay_rect(value: object) -> dict[str, int]:
    base = default_video_display_lyric_overlay_rect()
    source = dict(value) if isinstance(value, dict) else {}
    output: dict[str, int] = {}
    for key, fallback, minimum in [
        ("x", int(base["x"]), 0),
        ("y", int(base["y"]), 0),
        ("w", int(base["w"]), 600),
        ("h", int(base["h"]), 600),
    ]:
        try:
            parsed = int(source.get(key, fallback))
        except Exception:
            parsed = fallback
        output[key] = max(minimum, min(10000, parsed))
    return output


def default_supported_audio_format_extensions() -> list[str]:
    return []


def _normalize_supported_audio_format_extensions(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in list(values or []):
        token = str(raw or "").strip().lower()
        if not token:
            continue
        if not token.startswith("."):
            token = f".{token.lstrip('.')}"
        if token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


RUNTIME_LOG_MIN_MB = 16
RUNTIME_LOG_MAX_MB = 1024
DEFAULT_RUNTIME_LOG_LIMIT_MB = 256


def clamp_runtime_log_limit_mb(value: object) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = DEFAULT_RUNTIME_LOG_LIMIT_MB
    return max(RUNTIME_LOG_MIN_MB, min(RUNTIME_LOG_MAX_MB, parsed))


def default_launchpad_control_bindings() -> list[str]:
    return [
        "prev_group",
        "prev_page",
        "prev_sound_button",
        "go_to_playing",
        "play_selected",
        "play_selected_pause",
        "pause_toggle",
        "stop_playback",
        "shift_layer",
        "next_page",
        "next_sound_button",
        "loop",
        "next",
        "rapid_fire",
        "talk",
        "reset_page",
    ]


WINDOW_LAYOUT_MAIN_GRID_COLS = 4
WINDOW_LAYOUT_MAIN_GRID_ROWS = 4
WINDOW_LAYOUT_FADE_GRID_COLS = 6
WINDOW_LAYOUT_FADE_GRID_ROWS = 1

WINDOW_LAYOUT_MAIN_ORDER: list[str] = [
    "Cue",
    "Multi-Play",
    "Go To Playing",
    "DSP",
    "Loop",
    "Next",
    "Button Drag",
    "Pause",
    "Rapid Fire",
    "Shuffle",
    "Reset Page",
    "STOP",
    "Talk",
    "Play List",
    "Search",
    "Companion Bypass",
    "Internal Bypass",
    "Vocal Removed",
]
WINDOW_LAYOUT_FADE_ORDER: list[str] = [
    "Fade In",
    "X",
    "Fade Out",
    "Smart In",
    "Smart X",
    "Smart Out",
]
WINDOW_LAYOUT_ALL_BUTTONS: list[str] = [*WINDOW_LAYOUT_MAIN_ORDER, *WINDOW_LAYOUT_FADE_ORDER]

SOUND_BUTTON_VIEW_GRID = "grid"
SOUND_BUTTON_VIEW_LIST = "list"
DEFAULT_SOUND_BUTTON_LIST_COLUMN_WIDTHS: list[int] = [18, 52, 220, 190, 170, 72, 64, 72, 96, 72, 96]
DEFAULT_SOUND_BUTTON_LIST_HIDDEN_COLUMNS: list[str] = []


def normalize_sound_button_view_mode(value: object) -> str:
    token = str(value or "").strip().lower()
    return token if token in {SOUND_BUTTON_VIEW_GRID, SOUND_BUTTON_VIEW_LIST} else SOUND_BUTTON_VIEW_GRID


def clamp_sound_button_grid_columns(value: object) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = 8
    return max(1, min(512, parsed))


def clamp_sound_button_grid_rows(value: object) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = 6
    return max(1, min(512, parsed))


def clamp_sound_button_page_slot_cap(value: object) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = 48
    return max(1, min(4096, parsed))


def normalize_sound_button_list_column_widths(value: object) -> list[int]:
    defaults = list(DEFAULT_SOUND_BUTTON_LIST_COLUMN_WIDTHS)
    if isinstance(value, (list, tuple)):
        raw_values = list(value)
    else:
        raw_values = [part.strip() for part in str(value or "").split("\t")]
    widths: list[int] = []
    for idx, default in enumerate(defaults):
        try:
            parsed = int(raw_values[idx])
        except Exception:
            parsed = default
        widths.append(max(8, min(800, parsed)))
    return widths


def normalize_sound_button_list_hidden_columns(value: object, *, allowed_keys: Optional[list[str]] = None) -> list[str]:
    if allowed_keys is None:
        allowed_keys = ["ram", "index", "title", "notes", "status", "edit", "cue", "lyric", "automation", "script", "timecode"]
    allowed = {str(key).strip() for key in allowed_keys if str(key).strip()}
    if isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        raw_values = [part.strip() for part in str(value or "").split("\t")]
    hidden: list[str] = []
    for raw in raw_values:
        token = str(raw or "").strip().lower()
        if not token or token not in allowed or token in hidden:
            continue
        hidden.append(token)
    return hidden


def default_window_layout() -> dict[str, object]:
    return {
        "main": [
            {"button": "Cue", "x": 0, "y": 0, "w": 1, "h": 1},
            {"button": "Multi-Play", "x": 1, "y": 0, "w": 1, "h": 1},
            {"button": "Go To Playing", "x": 2, "y": 0, "w": 1, "h": 1},
            {"button": "DSP", "x": 3, "y": 0, "w": 1, "h": 1},
            {"button": "Loop", "x": 0, "y": 1, "w": 1, "h": 1},
            {"button": "Next", "x": 1, "y": 1, "w": 1, "h": 1},
            {"button": "Button Drag", "x": 2, "y": 1, "w": 1, "h": 1},
            {"button": "Pause", "x": 3, "y": 1, "w": 1, "h": 1},
            {"button": "Rapid Fire", "x": 0, "y": 2, "w": 1, "h": 1},
            {"button": "Shuffle", "x": 1, "y": 2, "w": 1, "h": 1},
            {"button": "Reset Page", "x": 2, "y": 2, "w": 1, "h": 1},
            {"button": "STOP", "x": 3, "y": 2, "w": 1, "h": 2},
            {"button": "Talk", "x": 0, "y": 3, "w": 1, "h": 1},
            {"button": "Play List", "x": 1, "y": 3, "w": 1, "h": 1},
            {"button": "Search", "x": 2, "y": 3, "w": 1, "h": 1},
        ],
        "fade": [
            {"button": "Fade In", "x": 0, "y": 0, "w": 1, "h": 1},
            {"button": "X", "x": 1, "y": 0, "w": 1, "h": 1},
            {"button": "Fade Out", "x": 2, "y": 0, "w": 1, "h": 1},
            {"button": "Smart In", "x": 3, "y": 0, "w": 1, "h": 1},
            {"button": "Smart X", "x": 4, "y": 0, "w": 1, "h": 1},
            {"button": "Smart Out", "x": 5, "y": 0, "w": 1, "h": 1},
        ],
        "available": [],
        "show_all_available": False,
    }


def _normalize_window_layout_items(
    values: list[dict[str, object]] | None,
    valid_buttons: set[str],
    cols: int,
    rows: int,
) -> list[dict[str, int | str]]:
    used = [[False for _ in range(cols)] for _ in range(rows)]
    normalized: list[dict[str, int | str]] = []
    raw = list(values or [])

    def can_place(px: int, py: int, pw: int, ph: int) -> bool:
        if px < 0 or py < 0 or pw < 1 or ph < 1:
            return False
        if (px + pw) > cols or (py + ph) > rows:
            return False
        for yy in range(py, py + ph):
            for xx in range(px, px + pw):
                if used[yy][xx]:
                    return False
        return True

    def place(px: int, py: int, pw: int, ph: int) -> None:
        for yy in range(py, py + ph):
            for xx in range(px, px + pw):
                used[yy][xx] = True

    def first_fit(pw: int, ph: int) -> tuple[int, int] | None:
        for yy in range(rows):
            for xx in range(cols):
                if can_place(xx, yy, pw, ph):
                    return xx, yy
        return None

    for raw_item in raw:
        if not isinstance(raw_item, dict):
            continue
        button = str(raw_item.get("button", "")).strip()
        if button not in valid_buttons:
            continue
        x = _clamp_int(_get_int(raw_item, "x", 0), 0, cols - 1)
        y = _clamp_int(_get_int(raw_item, "y", 0), 0, rows - 1)
        w = _clamp_int(_get_int(raw_item, "w", 1), 1, cols)
        h = _clamp_int(_get_int(raw_item, "h", 1), 1, rows)
        w = min(w, cols - x)
        h = min(h, rows - y)

        if not can_place(x, y, w, h):
            target = first_fit(w, h)
            if target is not None:
                x, y = target
            else:
                found = None
                for try_h in range(h, 0, -1):
                    for try_w in range(w, 0, -1):
                        target = first_fit(try_w, try_h)
                        if target is not None:
                            found = (target[0], target[1], try_w, try_h)
                            break
                    if found is not None:
                        break
                if found is None:
                    continue
                x, y, w, h = found

        place(x, y, w, h)
        normalized.append({"button": button, "x": x, "y": y, "w": w, "h": h})
    return normalized


def _convert_legacy_window_layout(
    values: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str], bool]:
    legacy_main = values.get("main")
    legacy_fade = values.get("fade")
    available_raw = values.get("available", [])
    show_all = bool(values.get("show_all_available", False))
    main_items: list[dict[str, object]] = []
    fade_items: list[dict[str, object]] = []
    if isinstance(legacy_main, dict):
        for key, spec in legacy_main.items():
            if not isinstance(spec, dict):
                continue
            main_items.append(
                {
                    "button": str(key),
                    "x": _get_int(spec, "x", 0),
                    "y": _get_int(spec, "y", 0),
                    "w": _get_int(spec, "w", 1),
                    "h": _get_int(spec, "h", 1),
                }
            )
    elif isinstance(legacy_main, list):
        main_items = [dict(item) for item in legacy_main if isinstance(item, dict)]
    if isinstance(legacy_fade, dict):
        for key, spec in legacy_fade.items():
            if not isinstance(spec, dict):
                continue
            fade_items.append(
                {
                    "button": str(key),
                    "x": _get_int(spec, "x", 0),
                    "y": _get_int(spec, "y", 0),
                    "w": _get_int(spec, "w", 1),
                    "h": _get_int(spec, "h", 1),
                }
            )
    elif isinstance(legacy_fade, list):
        fade_items = [dict(item) for item in legacy_fade if isinstance(item, dict)]
    available = []
    if isinstance(available_raw, list):
        for token in available_raw:
            value = str(token).strip()
            if value:
                available.append(value)
    return main_items, fade_items, available, show_all


def normalize_window_layout(values: dict[str, object] | None) -> dict[str, object]:
    defaults = default_window_layout()
    raw = dict(values or {})
    main_raw, fade_raw, available_raw, show_all_available = _convert_legacy_window_layout(raw)
    if not main_raw and not fade_raw:
        default_main, default_fade, default_available, default_show_all = _convert_legacy_window_layout(defaults)
        main_raw = default_main
        fade_raw = default_fade
        if not available_raw:
            available_raw = default_available
        show_all_available = default_show_all if "show_all_available" not in raw else show_all_available
    all_valid = set(WINDOW_LAYOUT_ALL_BUTTONS)
    main_items = _normalize_window_layout_items(main_raw, all_valid, WINDOW_LAYOUT_MAIN_GRID_COLS, WINDOW_LAYOUT_MAIN_GRID_ROWS)
    fade_items = _normalize_window_layout_items(fade_raw, all_valid, WINDOW_LAYOUT_FADE_GRID_COLS, WINDOW_LAYOUT_FADE_GRID_ROWS)
    available: list[str] = []
    for button in available_raw:
        token = str(button).strip()
        if token in all_valid and token not in available:
            available.append(token)
    if not bool(show_all_available):
        used = {str(item.get("button")) for item in [*main_items, *fade_items]}
        for button in WINDOW_LAYOUT_ALL_BUTTONS:
            if (button not in used) and (button not in available):
                available.append(button)
    return {
        "main": main_items,
        "fade": fade_items,
        "available": available,
        "show_all_available": bool(show_all_available),
    }


def default_stage_display_gadgets() -> dict[str, dict[str, int | bool | str]]:
    return {
        "current_time": {
            "x": 1500,
            "y": 200,
            "w": 7000,
            "h": 700,
            "z": 0,
            "visible": True,
            "orientation": "horizontal",
            "hide_text": True,
            "hide_border": True,
        },
        "alert": {
            "x": 0,
            "y": 0,
            "w": 10000,
            "h": 10000,
            "z": 99,
            "visible": False,
            "orientation": "vertical",
            "hide_text": True,
            "hide_border": False,
        },
        "total_time": {
            "x": 400,
            "y": 1100,
            "w": 3000,
            "h": 1300,
            "z": 1,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "elapsed": {
            "x": 3500,
            "y": 1100,
            "w": 3000,
            "h": 1300,
            "z": 2,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "remaining": {
            "x": 6600,
            "y": 1100,
            "w": 3000,
            "h": 1300,
            "z": 3,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "progress_bar": {
            "x": 600,
            "y": 2800,
            "w": 8800,
            "h": 1100,
            "z": 4,
            "visible": True,
            "orientation": "horizontal",
            "hide_text": False,
            "hide_border": False,
        },
        "song_name": {
            "x": 500,
            "y": 4300,
            "w": 9000,
            "h": 1500,
            "z": 5,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "lyric": {
            "x": 500,
            "y": 5900,
            "w": 9000,
            "h": 1700,
            "z": 6,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "next_song": {
            "x": 500,
            "y": 7700,
            "w": 9000,
            "h": 1300,
            "z": 7,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
    }


def _normalize_stage_display_gadgets(
    values: dict[str, dict[str, object]] | None,
    fallback_layout: list[str] | None = None,
    fallback_visibility: dict[str, bool] | None = None,
) -> dict[str, dict[str, int | bool | str]]:
    defaults = default_stage_display_gadgets()
    raw = dict(values or {})
    keys = list(defaults.keys())
    for key in keys:
        source = dict(raw.get(key, {})) if isinstance(raw.get(key), dict) else {}
        base = defaults[key]
        defaults[key] = {
            "x": _clamp_int(_get_int(source, "x", int(base["x"])), 0, 9800),
            "y": _clamp_int(_get_int(source, "y", int(base["y"])), 0, 9800),
            "w": _clamp_int(_get_int(source, "w", int(base["w"])), 600, 10000),
            "h": _clamp_int(_get_int(source, "h", int(base["h"])), 500, 10000),
            "z": _clamp_int(_get_int(source, "z", int(base["z"])), 0, 100),
            "visible": bool(source.get("visible", base["visible"])),
            "orientation": (
                str(source.get("orientation", base["orientation"])).strip().lower()
                if str(source.get("orientation", base["orientation"])).strip().lower() in {"horizontal", "vertical"}
                else str(base["orientation"])
            ),
            "hide_text": bool(source.get("hide_text", base["hide_text"])),
            "hide_border": bool(source.get("hide_border", base["hide_border"])),
        }
    if fallback_layout:
        ordered: list[str] = []
        for token in fallback_layout:
            key = str(token or "").strip().lower()
            if key in keys and key not in ordered:
                ordered.append(key)
        for key in keys:
            if key not in ordered:
                ordered.append(key)
        for index, key in enumerate(ordered):
            defaults[key]["z"] = index
    if fallback_visibility:
        for key in keys:
            if key in fallback_visibility:
                defaults[key]["visible"] = bool(fallback_visibility.get(key, True))
    return defaults


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
    now_playing_display_mode: str = "caption"
    main_ui_lyric_display_mode: str = "always"
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
    search_lyric_on_add_sound_button: bool = True
    new_lyric_file_format: str = "srt"
    warn_dual_automation_sources: bool = True
    automation_script_editor_show_lyric: bool = False
    supported_audio_format_extensions: list[str] = field(default_factory=default_supported_audio_format_extensions)
    verify_sound_file_on_add: bool = True
    allow_other_unsupported_audio_files: bool = False
    disable_path_safety: bool = False
    lock_allow_quit: bool = True
    lock_allow_system_hotkeys: bool = False
    lock_allow_quick_action_hotkeys: bool = False
    lock_allow_sound_button_hotkeys: bool = False
    lock_allow_midi_control: bool = True
    lock_auto_allow_quit: bool = True
    lock_auto_allow_midi_control: bool = True
    lock_unlock_method: str = "click_3_random_points"
    lock_require_password: bool = False
    lock_password: str = ""
    lock_restart_state: str = "unlock_on_restart"
    lock_was_locked_on_exit: bool = False
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
    vocal_removed_toggle_fade_mode: str = "follow_cross_fade"
    vocal_removed_toggle_custom_sec: float = 1.0
    vocal_removed_toggle_always_sec: float = 1.0
    talk_volume_level: int = 30
    talk_fade_sec: float = 0.5
    talk_volume_mode: str = "percent_of_master"
    talk_blink_button: bool = False
    talk_shift_accelerator: bool = True
    hotkeys_ignore_talk_level: bool = False
    enter_key_mirrors_space: bool = False
    log_file_enabled: bool = True
    runtime_log_enabled: bool = True
    runtime_log_limit_mb: int = DEFAULT_RUNTIME_LOG_LIMIT_MB
    reset_all_on_startup: bool = False
    click_playing_action: str = "play_it_again"
    search_double_click_action: str = "find_highlight"
    set_file_encoding: str = "utf8"
    ui_language: str = "en"
    app_version: str = ""
    app_build_id: str = ""
    tips_open_on_startup: bool = True
    audio_output_device: str = ""
    preload_audio_enabled: bool = False
    preload_current_page_audio: bool = True
    preload_audio_memory_limit_mb: int = 512
    preload_memory_pressure_enabled: bool = True
    preload_pause_on_playback: bool = True
    preload_use_ffmpeg: bool = True
    preload_video_enabled: bool = False
    waveform_cache_limit_mb: int = 1024
    waveform_cache_clear_on_launch: bool = True
    max_multi_play_songs: int = 5
    multi_play_limit_action: str = "stop_oldest"
    playlist_play_mode: str = "unplayed_only"
    rapid_fire_play_mode: str = "unplayed_only"
    next_play_mode: str = "unplayed_only"
    playlist_loop_mode: str = "loop_list"
    automation_command_buttons_follow_playback_controls: bool = False
    automation_command_button_auto_release_mode: str = "immediate"
    utility_sound_buttons_follow_playback_controls: bool = True
    candidate_error_action: str = "stop_playback"
    web_remote_enabled: bool = False
    web_remote_port: int = 5050
    web_remote_ws_port: int = 5051
    web_remote_https_enabled: bool = False
    web_remote_https_port: int = 5052
    web_remote_wss_port: int = 5053
    web_remote_enforce_https: bool = False
    web_remote_require_authentication: bool = False
    web_remote_username: str = "admin"
    web_remote_password: str = ""
    web_remote_guest_view_enabled: bool = False
    companion_satellite_host: str = "127.0.0.1"
    companion_satellite_port: int = 16622
    companion_satellite_enabled: bool = False
    companion_bypass: bool = False
    internal_bypass: bool = False
    companion_satellite_columns: int = 8
    companion_satellite_rows: int = 4
    companion_satellite_render_mode: str = "bitmap"
    companion_satellite_serial_suffix: str = field(default_factory=default_companion_satellite_serial_suffix)
    companion_command_mode: str = "tcp"
    companion_command_tcp_port: int = 16759
    companion_command_udp_port: int = 16759
    companion_command_http_port: int = 8000
    companion_available_commands_filter_black_empty: bool = True
    timecode_audio_output_device: str = "none"
    timecode_midi_output_device: str = "__none__"
    timecode_mode: str = "follow_media"
    timecode_fps: float = 30.0
    timecode_mtc_fps: float = 30.0
    timecode_mtc_idle_behavior: str = "keep_stream"
    timecode_sample_rate: int = 48000
    timecode_bit_depth: int = 16
    show_timecode_panel: bool = False
    show_video_control_panel: bool = False
    show_colour_legend: bool = True
    timecode_timeline_mode: str = "cue_region"
    soundbutton_timecode_offset_enabled: bool = True
    respect_soundbutton_timecode_timeline_setting: bool = True
    main_transport_timeline_mode: str = "cue_region"
    main_progress_display_mode: str = "progress_bar"
    main_progress_show_text: bool = True
    meter_output_tap_mode: str = "post_fader"
    sound_button_view_mode: str = SOUND_BUTTON_VIEW_GRID
    sound_button_grid_columns: int = 8
    sound_button_grid_rows: int = 6
    sound_button_page_slot_cap: int = 48
    sound_button_list_hide_empty: bool = False
    sound_button_list_hidden_columns: list[str] = field(
        default_factory=lambda: list(DEFAULT_SOUND_BUTTON_LIST_HIDDEN_COLUMNS)
    )
    sound_button_list_column_widths: list[int] = field(
        default_factory=lambda: list(DEFAULT_SOUND_BUTTON_LIST_COLUMN_WIDTHS)
    )
    main_jog_outside_cue_action: str = "stop_immediately"
    color_empty: str = "#0B868A"
    color_unplayed: str = "#B0B0B0"
    color_highlight: str = "#A6D8FF"
    color_playing: str = "#66FF33"
    color_played: str = "#FF3B30"
    color_error: str = "#7B3FB3"
    color_lock: str = "#F2D74A"
    color_place_marker: str = "#D0D0D0"
    color_copied_to_cue: str = "#2E65FF"
    color_cue_indicator: str = "#61D6FF"
    color_volume_indicator: str = "#FFD45A"
    color_vocal_removed_indicator: str = "#8E7CFF"
    color_midi_indicator: str = "#FF9E4A"
    color_lyric_indicator: str = "#57C3A4"
    color_video_indicator: str = "#FF5E7A"
    color_automation_indicator: str = "#49C16D"
    color_automation_indicator_bypassed: str = "#9A9A9A"
    color_automation_script_indicator: str = "#2E8BFF"
    color_automation_script_indicator_bypassed: str = "#708090"
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
    hotkey_play_selected_pause_1: str = ""
    hotkey_play_selected_pause_2: str = ""
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
    hotkey_volume_up_1: str = ""
    hotkey_volume_up_2: str = ""
    hotkey_volume_down_1: str = ""
    hotkey_volume_down_2: str = ""
    hotkey_lock_toggle_1: str = "Ctrl+L"
    hotkey_lock_toggle_2: str = ""
    hotkey_open_hide_lyric_navigator_1: str = ""
    hotkey_open_hide_lyric_navigator_2: str = ""
    hotkey_toggle_lyric_display_transparent_mode_1: str = ""
    hotkey_toggle_lyric_display_transparent_mode_2: str = ""
    quick_action_enabled: bool = False
    quick_action_keys: list[str] = field(default_factory=default_quick_action_keys)
    sound_button_hotkey_enabled: bool = False
    sound_button_hotkey_priority: str = "system_first"
    sound_button_hotkey_go_to_playing: bool = False
    sound_button_hotkey_system_order: list[str] = field(default_factory=list)
    midi_input_device_ids: list[str] = field(default_factory=list)
    launchpad_enabled: bool = False
    launchpad_device_selector: str = ""
    launchpad_output_device_id: str = ""
    launchpad_layout: str = "bottom_six"
    launchpad_turn_off_empty_sound_button_lights: bool = True
    launchpad_control_bindings: list[str] = field(default_factory=default_launchpad_control_bindings)
    midi_hotkey_new_set_1: str = ""
    midi_hotkey_new_set_2: str = ""
    midi_hotkey_open_set_1: str = ""
    midi_hotkey_open_set_2: str = ""
    midi_hotkey_save_set_1: str = ""
    midi_hotkey_save_set_2: str = ""
    midi_hotkey_save_set_as_1: str = ""
    midi_hotkey_save_set_as_2: str = ""
    midi_hotkey_search_1: str = ""
    midi_hotkey_search_2: str = ""
    midi_hotkey_options_1: str = ""
    midi_hotkey_options_2: str = ""
    midi_hotkey_play_selected_pause_1: str = ""
    midi_hotkey_play_selected_pause_2: str = ""
    midi_hotkey_play_selected_1: str = ""
    midi_hotkey_play_selected_2: str = ""
    midi_hotkey_pause_toggle_1: str = ""
    midi_hotkey_pause_toggle_2: str = ""
    midi_hotkey_stop_playback_1: str = ""
    midi_hotkey_stop_playback_2: str = ""
    midi_hotkey_talk_1: str = ""
    midi_hotkey_talk_2: str = ""
    midi_hotkey_next_group_1: str = ""
    midi_hotkey_next_group_2: str = ""
    midi_hotkey_prev_group_1: str = ""
    midi_hotkey_prev_group_2: str = ""
    midi_hotkey_next_page_1: str = ""
    midi_hotkey_next_page_2: str = ""
    midi_hotkey_prev_page_1: str = ""
    midi_hotkey_prev_page_2: str = ""
    midi_hotkey_next_sound_button_1: str = ""
    midi_hotkey_next_sound_button_2: str = ""
    midi_hotkey_prev_sound_button_1: str = ""
    midi_hotkey_prev_sound_button_2: str = ""
    midi_hotkey_multi_play_1: str = ""
    midi_hotkey_multi_play_2: str = ""
    midi_hotkey_go_to_playing_1: str = ""
    midi_hotkey_go_to_playing_2: str = ""
    midi_hotkey_loop_1: str = ""
    midi_hotkey_loop_2: str = ""
    midi_hotkey_next_1: str = ""
    midi_hotkey_next_2: str = ""
    midi_hotkey_rapid_fire_1: str = ""
    midi_hotkey_rapid_fire_2: str = ""
    midi_hotkey_shuffle_1: str = ""
    midi_hotkey_shuffle_2: str = ""
    midi_hotkey_reset_page_1: str = ""
    midi_hotkey_reset_page_2: str = ""
    midi_hotkey_play_list_1: str = ""
    midi_hotkey_play_list_2: str = ""
    midi_hotkey_fade_in_1: str = ""
    midi_hotkey_fade_in_2: str = ""
    midi_hotkey_cross_fade_1: str = ""
    midi_hotkey_cross_fade_2: str = ""
    midi_hotkey_fade_out_1: str = ""
    midi_hotkey_fade_out_2: str = ""
    midi_hotkey_mute_1: str = ""
    midi_hotkey_mute_2: str = ""
    midi_hotkey_volume_up_1: str = ""
    midi_hotkey_volume_up_2: str = ""
    midi_hotkey_volume_down_1: str = ""
    midi_hotkey_volume_down_2: str = ""
    midi_hotkey_lock_toggle_1: str = ""
    midi_hotkey_lock_toggle_2: str = ""
    midi_hotkey_open_hide_lyric_navigator_1: str = ""
    midi_hotkey_open_hide_lyric_navigator_2: str = ""
    midi_hotkey_toggle_lyric_display_transparent_mode_1: str = ""
    midi_hotkey_toggle_lyric_display_transparent_mode_2: str = ""
    midi_quick_action_enabled: bool = False
    midi_quick_action_bindings: list[str] = field(default_factory=default_midi_quick_action_bindings)
    midi_sound_button_hotkey_enabled: bool = False
    midi_sound_button_hotkey_priority: str = "system_first"
    midi_sound_button_hotkey_go_to_playing: bool = False
    midi_rotary_enabled: bool = False
    midi_rotary_group_binding: str = ""
    midi_rotary_page_binding: str = ""
    midi_rotary_sound_button_binding: str = ""
    midi_rotary_jog_binding: str = ""
    midi_rotary_volume_binding: str = ""
    midi_rotary_group_invert: bool = False
    midi_rotary_page_invert: bool = False
    midi_rotary_sound_button_invert: bool = False
    midi_rotary_jog_invert: bool = False
    midi_rotary_volume_invert: bool = False
    midi_rotary_group_sensitivity: int = 1
    midi_rotary_page_sensitivity: int = 1
    midi_rotary_sound_button_sensitivity: int = 1
    midi_rotary_group_relative_mode: str = "auto"
    midi_rotary_page_relative_mode: str = "auto"
    midi_rotary_sound_button_relative_mode: str = "auto"
    midi_rotary_jog_relative_mode: str = "auto"
    midi_rotary_volume_relative_mode: str = "auto"
    midi_rotary_volume_mode: str = "relative"
    midi_rotary_volume_step: int = 2
    midi_rotary_jog_step_ms: int = 250
    stage_display_layout: list[str] = field(default_factory=default_stage_display_layout)
    stage_display_show_current_time: bool = True
    stage_display_show_alert: bool = False
    stage_display_show_total_time: bool = True
    stage_display_show_elapsed: bool = True
    stage_display_show_remaining: bool = True
    stage_display_show_progress_bar: bool = True
    stage_display_show_song_name: bool = True
    stage_display_show_lyric: bool = True
    stage_display_show_next_song: bool = True
    stage_display_gadgets: dict[str, dict[str, int | bool | str]] = field(default_factory=default_stage_display_gadgets)
    stage_display_text_source: str = "caption"
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
    video_display_mode_playing: str = DISPLAY_FOCUS_FOLLOW
    video_display_mode_idle: str = "blank"
    display_focus_default_video: str = DISPLAY_FOCUS_VIDEO
    display_focus_default_audio: str = DISPLAY_FOCUS_NONE
    display_focus_default_audio_with_lyric: str = DISPLAY_FOCUS_LYRIC
    display_focus_default_utility_blank: str = DISPLAY_FOCUS_NONE
    display_focus_default_utility_noise: str = DISPLAY_FOCUS_COLOUR_BARS
    display_focus_default_utility_tone: str = DISPLAY_FOCUS_COLOUR_BARS
    display_focus_default_utility_metronome: str = DISPLAY_FOCUS_METRONOME
    display_focus_default_automation: str = DISPLAY_FOCUS_NONE
    video_display_use_default_backdrop: bool = True
    video_display_backdrop_path: str = ""
    video_display_show_backdrop_message: bool = True
    video_display_show_lyric_overlay: bool = False
    video_display_show_stage_alert: bool = False
    video_display_lyric_overlay_rect: dict[str, int] = field(default_factory=default_video_display_lyric_overlay_rect)
    video_display_lyric_font_family: str = ""
    video_display_lyric_font_size: int = 36
    video_display_lyric_previous_line_count: int = 0
    video_display_lyric_next_line_count: int = 0
    video_display_lyric_played_color: str = "#A0A0A0"
    video_display_lyric_current_color: str = "#FFD400"
    video_display_lyric_next_color: str = "#FFFFFF"
    video_display_lyric_auto_adjust_role_sizes: bool = True
    video_display_lyric_played_scale_percent: int = 70
    video_display_lyric_current_scale_percent: int = 115
    video_display_lyric_next_scale_percent: int = 90
    video_display_lyric_played_text_size: int = 24
    video_display_lyric_current_text_size: int = 40
    video_display_lyric_next_text_size: int = 32
    video_display_lyric_played_bold: bool = True
    video_display_lyric_current_bold: bool = True
    video_display_lyric_next_bold: bool = True
    video_display_lyric_played_italic: bool = False
    video_display_lyric_current_italic: bool = False
    video_display_lyric_next_italic: bool = False
    ndi_output_enabled: bool = False
    ndi_output_name: str = "pyssp-video"
    ndi_output_mode_playing: str = DISPLAY_FOCUS_FOLLOW
    ndi_output_mode_idle: str = "backdrop"
    ndi_output_resolution_mode: str = "source"
    ndi_output_width: int = 1920
    ndi_output_height: int = 1080
    ndi_output_fps: int = 30
    ndi_output_audio_enabled: bool = True
    ndi_output_audio_tap_mode: str = "post_fader"
    ndi_debug_print_enabled: bool = False
    ndi_debug_idle_audio_pacing_enabled: bool = True
    ndi_output_group: str = "Public"
    ndi_output_discovery_servers: str = ""
    ndi_output_allowed_adapters: str = ""
    ndi_output_multicast_enabled: bool = False
    ndi_output_multicast_ttl: int = 1
    ndi_output_multicast_netmask: str = "255.255.0.0"
    ndi_output_multicast_netprefix: str = "239.255.0.0"
    window_layout: dict[str, object] = field(default_factory=default_window_layout)
    window_layout_locked: bool = False
    dock_layout_state: str = ""
    dock_dividers: list[str] = field(default_factory=list)
    standalone_docks: list[str] = field(default_factory=list)


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
        "now_playing_display_mode": settings.now_playing_display_mode,
        "main_ui_lyric_display_mode": settings.main_ui_lyric_display_mode,
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
        "search_lyric_on_add_sound_button": "1" if settings.search_lyric_on_add_sound_button else "0",
        "new_lyric_file_format": settings.new_lyric_file_format,
        "warn_dual_automation_sources": "1" if settings.warn_dual_automation_sources else "0",
        "automation_script_editor_show_lyric": "1" if settings.automation_script_editor_show_lyric else "0",
        "supported_audio_format_extensions": "\t".join(
            _normalize_supported_audio_format_extensions(settings.supported_audio_format_extensions)
        ),
        "verify_sound_file_on_add": "1" if settings.verify_sound_file_on_add else "0",
        "allow_other_unsupported_audio_files": "1" if settings.allow_other_unsupported_audio_files else "0",
        "disable_path_safety": "1" if settings.disable_path_safety else "0",
        "lock_allow_quit": "1" if settings.lock_allow_quit else "0",
        "lock_allow_system_hotkeys": "1" if settings.lock_allow_system_hotkeys else "0",
        "lock_allow_quick_action_hotkeys": "1" if settings.lock_allow_quick_action_hotkeys else "0",
        "lock_allow_sound_button_hotkeys": "1" if settings.lock_allow_sound_button_hotkeys else "0",
        "lock_allow_midi_control": "1" if settings.lock_allow_midi_control else "0",
        "lock_auto_allow_quit": "1" if settings.lock_auto_allow_quit else "0",
        "lock_auto_allow_midi_control": "1" if settings.lock_auto_allow_midi_control else "0",
        "lock_unlock_method": settings.lock_unlock_method,
        "lock_require_password": "1" if settings.lock_require_password else "0",
        "lock_password": _encode_ascii_setting(settings.lock_password),
        "lock_restart_state": settings.lock_restart_state,
        "lock_was_locked_on_exit": "1" if settings.lock_was_locked_on_exit else "0",
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
        "vocal_removed_toggle_fade_mode": settings.vocal_removed_toggle_fade_mode,
        "vocal_removed_toggle_custom_sec": str(settings.vocal_removed_toggle_custom_sec),
        "vocal_removed_toggle_always_sec": str(settings.vocal_removed_toggle_always_sec),
        "talk_volume_level": str(settings.talk_volume_level),
        "talk_fade_sec": str(settings.talk_fade_sec),
        "talk_volume_mode": settings.talk_volume_mode,
        "talk_blink_button": "1" if settings.talk_blink_button else "0",
        "talk_shift_accelerator": "1" if settings.talk_shift_accelerator else "0",
        "hotkeys_ignore_talk_level": "1" if settings.hotkeys_ignore_talk_level else "0",
        "enter_key_mirrors_space": "1" if settings.enter_key_mirrors_space else "0",
        "log_file_enabled": "1" if settings.log_file_enabled else "0",
        "runtime_log_enabled": "1" if settings.runtime_log_enabled else "0",
        "runtime_log_limit_mb": str(clamp_runtime_log_limit_mb(settings.runtime_log_limit_mb)),
        "reset_all_on_startup": "1" if settings.reset_all_on_startup else "0",
        "click_playing_action": settings.click_playing_action,
        "search_double_click_action": settings.search_double_click_action,
        "set_file_encoding": settings.set_file_encoding,
        "ui_language": settings.ui_language,
        "app_version": settings.app_version,
        "app_build_id": settings.app_build_id,
        "tips_open_on_startup": "1" if settings.tips_open_on_startup else "0",
        "audio_output_device": settings.audio_output_device,
        "preload_audio_enabled": "1" if settings.preload_audio_enabled else "0",
        "preload_current_page_audio": "1" if settings.preload_current_page_audio else "0",
        "preload_audio_memory_limit_mb": str(settings.preload_audio_memory_limit_mb),
        "preload_memory_pressure_enabled": "1" if settings.preload_memory_pressure_enabled else "0",
        "preload_pause_on_playback": "1" if settings.preload_pause_on_playback else "0",
        "preload_use_ffmpeg": "1" if settings.preload_use_ffmpeg else "0",
        "preload_video_enabled": "1" if settings.preload_video_enabled else "0",
        "waveform_cache_limit_mb": str(settings.waveform_cache_limit_mb),
        "waveform_cache_clear_on_launch": "1" if settings.waveform_cache_clear_on_launch else "0",
        "max_multi_play_songs": str(settings.max_multi_play_songs),
        "multi_play_limit_action": settings.multi_play_limit_action,
        "playlist_play_mode": settings.playlist_play_mode,
        "rapid_fire_play_mode": settings.rapid_fire_play_mode,
        "next_play_mode": settings.next_play_mode,
        "playlist_loop_mode": settings.playlist_loop_mode,
        "automation_command_buttons_follow_playback_controls": (
            "1" if settings.automation_command_buttons_follow_playback_controls else "0"
        ),
        "automation_command_button_auto_release_mode": str(
            settings.automation_command_button_auto_release_mode or "immediate"
        ),
        "utility_sound_buttons_follow_playback_controls": "1" if settings.utility_sound_buttons_follow_playback_controls else "0",
        "candidate_error_action": settings.candidate_error_action,
        "web_remote_enabled": "1" if settings.web_remote_enabled else "0",
        "web_remote_port": str(settings.web_remote_port),
        "web_remote_ws_port": str(settings.web_remote_ws_port),
        "web_remote_https_enabled": "1" if settings.web_remote_https_enabled else "0",
        "web_remote_https_port": str(settings.web_remote_https_port),
        "web_remote_wss_port": str(settings.web_remote_wss_port),
        "web_remote_enforce_https": "1" if settings.web_remote_enforce_https else "0",
        "web_remote_require_authentication": "1" if settings.web_remote_require_authentication else "0",
        "web_remote_username": _encode_ascii_setting(settings.web_remote_username),
        "web_remote_password": _encode_ascii_setting(settings.web_remote_password),
        "web_remote_guest_view_enabled": "1" if settings.web_remote_guest_view_enabled else "0",
        "companion_satellite_host": settings.companion_satellite_host,
        "companion_satellite_port": str(settings.companion_satellite_port),
        "companion_satellite_enabled": "1" if settings.companion_satellite_enabled else "0",
        "companion_bypass": "1" if settings.companion_bypass else "0",
        "internal_bypass": "1" if settings.internal_bypass else "0",
        "companion_satellite_columns": str(settings.companion_satellite_columns),
        "companion_satellite_rows": str(settings.companion_satellite_rows),
        "companion_satellite_render_mode": _normalize_companion_satellite_render_mode(
            settings.companion_satellite_render_mode
        ),
        "companion_satellite_serial_suffix": _normalize_companion_satellite_serial_suffix(
            settings.companion_satellite_serial_suffix
        ),
        "companion_command_mode": _normalize_companion_command_mode(settings.companion_command_mode),
        "companion_command_tcp_port": str(settings.companion_command_tcp_port),
        "companion_command_udp_port": str(settings.companion_command_udp_port),
        "companion_command_http_port": str(settings.companion_command_http_port),
        "companion_available_commands_filter_black_empty": (
            "1" if settings.companion_available_commands_filter_black_empty else "0"
        ),
        "timecode_audio_output_device": settings.timecode_audio_output_device,
        "timecode_midi_output_device": settings.timecode_midi_output_device,
        "timecode_mode": settings.timecode_mode,
        "timecode_fps": str(settings.timecode_fps),
        "timecode_mtc_fps": str(settings.timecode_mtc_fps),
        "timecode_mtc_idle_behavior": settings.timecode_mtc_idle_behavior,
        "timecode_sample_rate": str(settings.timecode_sample_rate),
        "timecode_bit_depth": str(settings.timecode_bit_depth),
        "show_timecode_panel": "1" if settings.show_timecode_panel else "0",
        "show_video_control_panel": "1" if settings.show_video_control_panel else "0",
        "show_colour_legend": "1" if settings.show_colour_legend else "0",
        "timecode_timeline_mode": settings.timecode_timeline_mode,
        "soundbutton_timecode_offset_enabled": "1" if settings.soundbutton_timecode_offset_enabled else "0",
        "respect_soundbutton_timecode_timeline_setting": (
            "1" if settings.respect_soundbutton_timecode_timeline_setting else "0"
        ),
        "main_transport_timeline_mode": settings.main_transport_timeline_mode,
        "main_progress_display_mode": settings.main_progress_display_mode,
        "main_progress_show_text": "1" if settings.main_progress_show_text else "0",
        "meter_output_tap_mode": str(settings.meter_output_tap_mode or "post_fader").strip().lower(),
        "sound_button_view_mode": normalize_sound_button_view_mode(settings.sound_button_view_mode),
        "sound_button_grid_columns": str(clamp_sound_button_grid_columns(settings.sound_button_grid_columns)),
        "sound_button_grid_rows": str(clamp_sound_button_grid_rows(settings.sound_button_grid_rows)),
        "sound_button_page_slot_cap": str(clamp_sound_button_page_slot_cap(settings.sound_button_page_slot_cap)),
        "sound_button_list_hide_empty": "1" if settings.sound_button_list_hide_empty else "0",
        "sound_button_list_hidden_columns": "\t".join(
            normalize_sound_button_list_hidden_columns(settings.sound_button_list_hidden_columns)
        ),
        "sound_button_list_column_widths": "\t".join(
            str(value) for value in normalize_sound_button_list_column_widths(settings.sound_button_list_column_widths)
        ),
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
        "color_vocal_removed_indicator": settings.color_vocal_removed_indicator,
        "color_midi_indicator": settings.color_midi_indicator,
        "color_lyric_indicator": settings.color_lyric_indicator,
        "color_video_indicator": settings.color_video_indicator,
        "color_automation_indicator": settings.color_automation_indicator,
        "color_automation_indicator_bypassed": settings.color_automation_indicator_bypassed,
        "color_automation_script_indicator": settings.color_automation_script_indicator,
        "color_automation_script_indicator_bypassed": settings.color_automation_script_indicator_bypassed,
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
        "hotkey_play_selected_pause_1": settings.hotkey_play_selected_pause_1,
        "hotkey_play_selected_pause_2": settings.hotkey_play_selected_pause_2,
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
        "hotkey_volume_up_1": settings.hotkey_volume_up_1,
        "hotkey_volume_up_2": settings.hotkey_volume_up_2,
        "hotkey_volume_down_1": settings.hotkey_volume_down_1,
        "hotkey_volume_down_2": settings.hotkey_volume_down_2,
        "hotkey_lock_toggle_1": settings.hotkey_lock_toggle_1,
        "hotkey_lock_toggle_2": settings.hotkey_lock_toggle_2,
        "hotkey_open_hide_lyric_navigator_1": settings.hotkey_open_hide_lyric_navigator_1,
        "hotkey_open_hide_lyric_navigator_2": settings.hotkey_open_hide_lyric_navigator_2,
        "hotkey_toggle_lyric_display_transparent_mode_1": settings.hotkey_toggle_lyric_display_transparent_mode_1,
        "hotkey_toggle_lyric_display_transparent_mode_2": settings.hotkey_toggle_lyric_display_transparent_mode_2,
        "quick_action_enabled": "1" if settings.quick_action_enabled else "0",
        "quick_action_keys": "\t".join(_normalize_quick_action_keys(settings.quick_action_keys)),
        "sound_button_hotkey_enabled": "1" if settings.sound_button_hotkey_enabled else "0",
        "sound_button_hotkey_priority": settings.sound_button_hotkey_priority,
        "sound_button_hotkey_go_to_playing": "1" if settings.sound_button_hotkey_go_to_playing else "0",
        "sound_button_hotkey_system_order": "\t".join(settings.sound_button_hotkey_system_order),
        "midi_input_device_ids": "\t".join(settings.midi_input_device_ids),
        "launchpad_enabled": "1" if settings.launchpad_enabled else "0",
        "launchpad_device_selector": settings.launchpad_device_selector,
        "launchpad_output_device_id": settings.launchpad_output_device_id,
        "launchpad_layout": settings.launchpad_layout,
        "launchpad_turn_off_empty_sound_button_lights": "1" if settings.launchpad_turn_off_empty_sound_button_lights else "0",
        "launchpad_control_bindings": "\t".join(settings.launchpad_control_bindings[:16]),
        "midi_hotkey_new_set_1": settings.midi_hotkey_new_set_1,
        "midi_hotkey_new_set_2": settings.midi_hotkey_new_set_2,
        "midi_hotkey_open_set_1": settings.midi_hotkey_open_set_1,
        "midi_hotkey_open_set_2": settings.midi_hotkey_open_set_2,
        "midi_hotkey_save_set_1": settings.midi_hotkey_save_set_1,
        "midi_hotkey_save_set_2": settings.midi_hotkey_save_set_2,
        "midi_hotkey_save_set_as_1": settings.midi_hotkey_save_set_as_1,
        "midi_hotkey_save_set_as_2": settings.midi_hotkey_save_set_as_2,
        "midi_hotkey_search_1": settings.midi_hotkey_search_1,
        "midi_hotkey_search_2": settings.midi_hotkey_search_2,
        "midi_hotkey_options_1": settings.midi_hotkey_options_1,
        "midi_hotkey_options_2": settings.midi_hotkey_options_2,
        "midi_hotkey_play_selected_pause_1": settings.midi_hotkey_play_selected_pause_1,
        "midi_hotkey_play_selected_pause_2": settings.midi_hotkey_play_selected_pause_2,
        "midi_hotkey_play_selected_1": settings.midi_hotkey_play_selected_1,
        "midi_hotkey_play_selected_2": settings.midi_hotkey_play_selected_2,
        "midi_hotkey_pause_toggle_1": settings.midi_hotkey_pause_toggle_1,
        "midi_hotkey_pause_toggle_2": settings.midi_hotkey_pause_toggle_2,
        "midi_hotkey_stop_playback_1": settings.midi_hotkey_stop_playback_1,
        "midi_hotkey_stop_playback_2": settings.midi_hotkey_stop_playback_2,
        "midi_hotkey_talk_1": settings.midi_hotkey_talk_1,
        "midi_hotkey_talk_2": settings.midi_hotkey_talk_2,
        "midi_hotkey_next_group_1": settings.midi_hotkey_next_group_1,
        "midi_hotkey_next_group_2": settings.midi_hotkey_next_group_2,
        "midi_hotkey_prev_group_1": settings.midi_hotkey_prev_group_1,
        "midi_hotkey_prev_group_2": settings.midi_hotkey_prev_group_2,
        "midi_hotkey_next_page_1": settings.midi_hotkey_next_page_1,
        "midi_hotkey_next_page_2": settings.midi_hotkey_next_page_2,
        "midi_hotkey_prev_page_1": settings.midi_hotkey_prev_page_1,
        "midi_hotkey_prev_page_2": settings.midi_hotkey_prev_page_2,
        "midi_hotkey_next_sound_button_1": settings.midi_hotkey_next_sound_button_1,
        "midi_hotkey_next_sound_button_2": settings.midi_hotkey_next_sound_button_2,
        "midi_hotkey_prev_sound_button_1": settings.midi_hotkey_prev_sound_button_1,
        "midi_hotkey_prev_sound_button_2": settings.midi_hotkey_prev_sound_button_2,
        "midi_hotkey_multi_play_1": settings.midi_hotkey_multi_play_1,
        "midi_hotkey_multi_play_2": settings.midi_hotkey_multi_play_2,
        "midi_hotkey_go_to_playing_1": settings.midi_hotkey_go_to_playing_1,
        "midi_hotkey_go_to_playing_2": settings.midi_hotkey_go_to_playing_2,
        "midi_hotkey_loop_1": settings.midi_hotkey_loop_1,
        "midi_hotkey_loop_2": settings.midi_hotkey_loop_2,
        "midi_hotkey_next_1": settings.midi_hotkey_next_1,
        "midi_hotkey_next_2": settings.midi_hotkey_next_2,
        "midi_hotkey_rapid_fire_1": settings.midi_hotkey_rapid_fire_1,
        "midi_hotkey_rapid_fire_2": settings.midi_hotkey_rapid_fire_2,
        "midi_hotkey_shuffle_1": settings.midi_hotkey_shuffle_1,
        "midi_hotkey_shuffle_2": settings.midi_hotkey_shuffle_2,
        "midi_hotkey_reset_page_1": settings.midi_hotkey_reset_page_1,
        "midi_hotkey_reset_page_2": settings.midi_hotkey_reset_page_2,
        "midi_hotkey_play_list_1": settings.midi_hotkey_play_list_1,
        "midi_hotkey_play_list_2": settings.midi_hotkey_play_list_2,
        "midi_hotkey_fade_in_1": settings.midi_hotkey_fade_in_1,
        "midi_hotkey_fade_in_2": settings.midi_hotkey_fade_in_2,
        "midi_hotkey_cross_fade_1": settings.midi_hotkey_cross_fade_1,
        "midi_hotkey_cross_fade_2": settings.midi_hotkey_cross_fade_2,
        "midi_hotkey_fade_out_1": settings.midi_hotkey_fade_out_1,
        "midi_hotkey_fade_out_2": settings.midi_hotkey_fade_out_2,
        "midi_hotkey_mute_1": settings.midi_hotkey_mute_1,
        "midi_hotkey_mute_2": settings.midi_hotkey_mute_2,
        "midi_hotkey_volume_up_1": settings.midi_hotkey_volume_up_1,
        "midi_hotkey_volume_up_2": settings.midi_hotkey_volume_up_2,
        "midi_hotkey_volume_down_1": settings.midi_hotkey_volume_down_1,
        "midi_hotkey_volume_down_2": settings.midi_hotkey_volume_down_2,
        "midi_hotkey_lock_toggle_1": settings.midi_hotkey_lock_toggle_1,
        "midi_hotkey_lock_toggle_2": settings.midi_hotkey_lock_toggle_2,
        "midi_hotkey_open_hide_lyric_navigator_1": settings.midi_hotkey_open_hide_lyric_navigator_1,
        "midi_hotkey_open_hide_lyric_navigator_2": settings.midi_hotkey_open_hide_lyric_navigator_2,
        "midi_hotkey_toggle_lyric_display_transparent_mode_1": settings.midi_hotkey_toggle_lyric_display_transparent_mode_1,
        "midi_hotkey_toggle_lyric_display_transparent_mode_2": settings.midi_hotkey_toggle_lyric_display_transparent_mode_2,
        "midi_quick_action_enabled": "1" if settings.midi_quick_action_enabled else "0",
        "midi_quick_action_bindings": "\t".join(_normalize_midi_quick_action_bindings(settings.midi_quick_action_bindings)),
        "midi_sound_button_hotkey_enabled": "1" if settings.midi_sound_button_hotkey_enabled else "0",
        "midi_sound_button_hotkey_priority": settings.midi_sound_button_hotkey_priority,
        "midi_sound_button_hotkey_go_to_playing": "1" if settings.midi_sound_button_hotkey_go_to_playing else "0",
        "midi_rotary_enabled": "1" if settings.midi_rotary_enabled else "0",
        "midi_rotary_group_binding": settings.midi_rotary_group_binding,
        "midi_rotary_page_binding": settings.midi_rotary_page_binding,
        "midi_rotary_sound_button_binding": settings.midi_rotary_sound_button_binding,
        "midi_rotary_jog_binding": settings.midi_rotary_jog_binding,
        "midi_rotary_volume_binding": settings.midi_rotary_volume_binding,
        "midi_rotary_group_invert": "1" if settings.midi_rotary_group_invert else "0",
        "midi_rotary_page_invert": "1" if settings.midi_rotary_page_invert else "0",
        "midi_rotary_sound_button_invert": "1" if settings.midi_rotary_sound_button_invert else "0",
        "midi_rotary_jog_invert": "1" if settings.midi_rotary_jog_invert else "0",
        "midi_rotary_volume_invert": "1" if settings.midi_rotary_volume_invert else "0",
        "midi_rotary_group_sensitivity": str(settings.midi_rotary_group_sensitivity),
        "midi_rotary_page_sensitivity": str(settings.midi_rotary_page_sensitivity),
        "midi_rotary_sound_button_sensitivity": str(settings.midi_rotary_sound_button_sensitivity),
        "midi_rotary_group_relative_mode": settings.midi_rotary_group_relative_mode,
        "midi_rotary_page_relative_mode": settings.midi_rotary_page_relative_mode,
        "midi_rotary_sound_button_relative_mode": settings.midi_rotary_sound_button_relative_mode,
        "midi_rotary_jog_relative_mode": settings.midi_rotary_jog_relative_mode,
        "midi_rotary_volume_relative_mode": settings.midi_rotary_volume_relative_mode,
        "midi_rotary_volume_mode": settings.midi_rotary_volume_mode,
        "midi_rotary_volume_step": str(settings.midi_rotary_volume_step),
        "midi_rotary_jog_step_ms": str(settings.midi_rotary_jog_step_ms),
        "stage_display_layout": "\t".join(default_stage_display_layout() if not settings.stage_display_layout else settings.stage_display_layout),
        "stage_display_show_current_time": "1" if settings.stage_display_show_current_time else "0",
        "stage_display_show_alert": "1" if settings.stage_display_show_alert else "0",
        "stage_display_show_total_time": "1" if settings.stage_display_show_total_time else "0",
        "stage_display_show_elapsed": "1" if settings.stage_display_show_elapsed else "0",
        "stage_display_show_remaining": "1" if settings.stage_display_show_remaining else "0",
        "stage_display_show_progress_bar": "1" if settings.stage_display_show_progress_bar else "0",
        "stage_display_show_song_name": "1" if settings.stage_display_show_song_name else "0",
        "stage_display_show_lyric": "1" if settings.stage_display_show_lyric else "0",
        "stage_display_show_next_song": "1" if settings.stage_display_show_next_song else "0",
        "stage_display_gadgets": json.dumps(
            _normalize_stage_display_gadgets(settings.stage_display_gadgets),
            separators=(",", ":"),
        ),
        "stage_display_text_source": settings.stage_display_text_source,
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
        "video_display_mode_playing": normalize_display_focus_override(
            settings.video_display_mode_playing,
            default=DISPLAY_FOCUS_FOLLOW,
        ),
        "video_display_mode_idle": str(settings.video_display_mode_idle or "blank").strip().lower(),
        "display_focus_default_video": normalize_display_focus(
            settings.display_focus_default_video,
            default=DISPLAY_FOCUS_VIDEO,
        ),
        "display_focus_default_audio": normalize_display_focus(
            settings.display_focus_default_audio,
            default=DISPLAY_FOCUS_NONE,
        ),
        "display_focus_default_audio_with_lyric": normalize_display_focus(
            settings.display_focus_default_audio_with_lyric,
            default=DISPLAY_FOCUS_LYRIC,
        ),
        "display_focus_default_utility_blank": normalize_display_focus(
            settings.display_focus_default_utility_blank,
            default=DISPLAY_FOCUS_NONE,
        ),
        "display_focus_default_utility_noise": normalize_display_focus(
            settings.display_focus_default_utility_noise,
            default=DISPLAY_FOCUS_COLOUR_BARS,
        ),
        "display_focus_default_utility_tone": normalize_display_focus(
            settings.display_focus_default_utility_tone,
            default=DISPLAY_FOCUS_COLOUR_BARS,
        ),
        "display_focus_default_utility_metronome": normalize_display_focus(
            settings.display_focus_default_utility_metronome,
            default=DISPLAY_FOCUS_METRONOME,
        ),
        "display_focus_default_automation": normalize_display_focus(
            settings.display_focus_default_automation,
            default=DISPLAY_FOCUS_NONE,
        ),
        "video_display_use_default_backdrop": "1" if settings.video_display_use_default_backdrop else "0",
        "video_display_backdrop_path": _encode_ascii_setting(settings.video_display_backdrop_path),
        "video_display_show_backdrop_message": "1" if settings.video_display_show_backdrop_message else "0",
        "video_display_show_lyric_overlay": "1" if settings.video_display_show_lyric_overlay else "0",
        "video_display_show_stage_alert": "1" if settings.video_display_show_stage_alert else "0",
        "video_display_lyric_overlay_rect": json.dumps(
            _normalize_video_display_lyric_overlay_rect(settings.video_display_lyric_overlay_rect),
            separators=(",", ":"),
        ),
        "video_display_lyric_font_family": settings.video_display_lyric_font_family,
        "video_display_lyric_font_size": str(settings.video_display_lyric_font_size),
        "video_display_lyric_previous_line_count": str(settings.video_display_lyric_previous_line_count),
        "video_display_lyric_next_line_count": str(settings.video_display_lyric_next_line_count),
        "video_display_lyric_played_color": settings.video_display_lyric_played_color,
        "video_display_lyric_current_color": settings.video_display_lyric_current_color,
        "video_display_lyric_next_color": settings.video_display_lyric_next_color,
        "video_display_lyric_auto_adjust_role_sizes": "1" if settings.video_display_lyric_auto_adjust_role_sizes else "0",
        "video_display_lyric_played_scale_percent": str(settings.video_display_lyric_played_scale_percent),
        "video_display_lyric_current_scale_percent": str(settings.video_display_lyric_current_scale_percent),
        "video_display_lyric_next_scale_percent": str(settings.video_display_lyric_next_scale_percent),
        "video_display_lyric_played_text_size": str(settings.video_display_lyric_played_text_size),
        "video_display_lyric_current_text_size": str(settings.video_display_lyric_current_text_size),
        "video_display_lyric_next_text_size": str(settings.video_display_lyric_next_text_size),
        "video_display_lyric_played_bold": "1" if settings.video_display_lyric_played_bold else "0",
        "video_display_lyric_current_bold": "1" if settings.video_display_lyric_current_bold else "0",
        "video_display_lyric_next_bold": "1" if settings.video_display_lyric_next_bold else "0",
        "video_display_lyric_played_italic": "1" if settings.video_display_lyric_played_italic else "0",
        "video_display_lyric_current_italic": "1" if settings.video_display_lyric_current_italic else "0",
        "video_display_lyric_next_italic": "1" if settings.video_display_lyric_next_italic else "0",
        "ndi_output_enabled": "1" if settings.ndi_output_enabled else "0",
        "ndi_output_name": _encode_ascii_setting(settings.ndi_output_name),
        "ndi_output_mode_playing": normalize_display_focus_override(
            settings.ndi_output_mode_playing,
            default=DISPLAY_FOCUS_FOLLOW,
        ),
        "ndi_output_mode_idle": str(settings.ndi_output_mode_idle or "backdrop").strip().lower(),
        "ndi_output_resolution_mode": str(settings.ndi_output_resolution_mode or "source").strip().lower(),
        "ndi_output_width": str(max(2, int(settings.ndi_output_width))),
        "ndi_output_height": str(max(2, int(settings.ndi_output_height))),
        "ndi_output_fps": str(max(1, int(settings.ndi_output_fps))),
        "ndi_output_audio_enabled": "1" if settings.ndi_output_audio_enabled else "0",
        "ndi_output_audio_tap_mode": str(settings.ndi_output_audio_tap_mode or "post_fader").strip().lower(),
        "ndi_debug_print_enabled": "1" if settings.ndi_debug_print_enabled else "0",
        "ndi_debug_idle_audio_pacing_enabled": "1" if settings.ndi_debug_idle_audio_pacing_enabled else "0",
        "ndi_output_group": _encode_ascii_setting(str(settings.ndi_output_group or "Public").strip() or "Public"),
        "ndi_output_discovery_servers": _encode_ascii_setting(str(settings.ndi_output_discovery_servers or "").strip()),
        "ndi_output_allowed_adapters": _encode_ascii_setting(str(settings.ndi_output_allowed_adapters or "").strip()),
        "ndi_output_multicast_enabled": "1" if settings.ndi_output_multicast_enabled else "0",
        "ndi_output_multicast_ttl": str(max(1, min(255, int(settings.ndi_output_multicast_ttl)))),
        "ndi_output_multicast_netmask": _encode_ascii_setting(str(settings.ndi_output_multicast_netmask or "255.255.0.0").strip() or "255.255.0.0"),
        "ndi_output_multicast_netprefix": _encode_ascii_setting(str(settings.ndi_output_multicast_netprefix or "239.255.0.0").strip() or "239.255.0.0"),
        "window_layout": json.dumps(
            normalize_window_layout(settings.window_layout),
            separators=(",", ":"),
        ),
        "window_layout_locked": "1" if settings.window_layout_locked else "0",
        "dock_layout_state": str(settings.dock_layout_state or "").strip(),
        "dock_dividers": json.dumps([str(value).strip() for value in list(settings.dock_dividers or []) if str(value).strip()]),
        "standalone_docks": json.dumps([str(value).strip() for value in list(settings.standalone_docks or []) if str(value).strip()]),
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
    vocal_removed_toggle_fade_mode = str(section.get("vocal_removed_toggle_fade_mode", "follow_cross_fade")).strip().lower()
    if vocal_removed_toggle_fade_mode not in {
        "follow_cross_fade",
        "follow_cross_fade_custom",
        "never",
        "always",
    }:
        vocal_removed_toggle_fade_mode = "follow_cross_fade"
    vocal_removed_toggle_custom_sec = _clamp_float(
        _get_float(section, "vocal_removed_toggle_custom_sec", 1.0),
        0.0,
        20.0,
    )
    vocal_removed_toggle_always_sec = _clamp_float(
        _get_float(section, "vocal_removed_toggle_always_sec", 1.0),
        0.0,
        20.0,
    )
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
    now_playing_display_mode = str(section.get("now_playing_display_mode", "caption")).strip().lower()
    if now_playing_display_mode not in {"filename", "filepath", "caption", "note", "caption_note"}:
        now_playing_display_mode = "caption"
    main_ui_lyric_display_mode = str(section.get("main_ui_lyric_display_mode", "always")).strip().lower()
    if main_ui_lyric_display_mode not in {"always", "when_available", "never"}:
        main_ui_lyric_display_mode = "always"
    lyric_display_transparent_mode = _get_bool(section, "lyric_display_transparent_mode", False)
    lyric_display_show_not_playing_message = _get_bool(section, "lyric_display_show_not_playing_message", True)
    lyric_display_font_family = str(section.get("lyric_display_font_family", "")).strip()
    lyric_display_font_size = _clamp_int(_get_int(section, "lyric_display_font_size", 36), 10, 240)
    lyric_display_previous_line_count = _clamp_int(_get_int(section, "lyric_display_previous_line_count", 0), 0, 20)
    lyric_display_next_line_count = _clamp_int(_get_int(section, "lyric_display_next_line_count", 0), 0, 20)
    lyric_display_played_color = _coerce_hex(str(section.get("lyric_display_played_color", "#A0A0A0")), "#A0A0A0")
    lyric_display_current_color = _coerce_hex(str(section.get("lyric_display_current_color", "#FFD400")), "#FFD400")
    lyric_display_next_color = _coerce_hex(str(section.get("lyric_display_next_color", "#FFFFFF")), "#FFFFFF")
    lyric_display_auto_adjust_role_sizes = _get_bool(section, "lyric_display_auto_adjust_role_sizes", True)
    lyric_display_played_scale_percent = _clamp_int(_get_int(section, "lyric_display_played_scale_percent", 70), 25, 300)
    lyric_display_current_scale_percent = _clamp_int(_get_int(section, "lyric_display_current_scale_percent", 115), 25, 300)
    lyric_display_next_scale_percent = _clamp_int(_get_int(section, "lyric_display_next_scale_percent", 90), 25, 300)
    lyric_display_played_text_size = _clamp_int(_get_int(section, "lyric_display_played_text_size", 24), 8, 240)
    lyric_display_current_text_size = _clamp_int(_get_int(section, "lyric_display_current_text_size", 40), 8, 240)
    lyric_display_next_text_size = _clamp_int(_get_int(section, "lyric_display_next_text_size", 32), 8, 240)
    lyric_display_played_bold = _get_bool(section, "lyric_display_played_bold", True)
    lyric_display_current_bold = _get_bool(section, "lyric_display_current_bold", True)
    lyric_display_next_bold = _get_bool(section, "lyric_display_next_bold", True)
    lyric_display_played_italic = _get_bool(section, "lyric_display_played_italic", False)
    lyric_display_current_italic = _get_bool(section, "lyric_display_current_italic", False)
    lyric_display_next_italic = _get_bool(section, "lyric_display_next_italic", False)
    video_display_mode_playing = normalize_display_focus_override(
        section.get("video_display_mode_playing", DISPLAY_FOCUS_FOLLOW),
        default=DISPLAY_FOCUS_FOLLOW,
    )
    video_display_mode_idle = normalize_display_route_source(
        str(section.get("video_display_mode_idle", DISPLAY_ROUTE_SOURCE_BLANK)).strip().lower(),
        default=DISPLAY_ROUTE_SOURCE_BLANK,
    )
    display_focus_default_video = normalize_display_focus(
        section.get("display_focus_default_video", DISPLAY_FOCUS_VIDEO),
        default=DISPLAY_FOCUS_VIDEO,
    )
    display_focus_default_audio = normalize_display_focus(
        section.get("display_focus_default_audio", DISPLAY_FOCUS_NONE),
        default=DISPLAY_FOCUS_NONE,
    )
    display_focus_default_audio_with_lyric = normalize_display_focus(
        section.get("display_focus_default_audio_with_lyric", DISPLAY_FOCUS_LYRIC),
        default=DISPLAY_FOCUS_LYRIC,
    )
    display_focus_default_utility_blank = normalize_display_focus(
        section.get("display_focus_default_utility_blank", DISPLAY_FOCUS_NONE),
        default=DISPLAY_FOCUS_NONE,
    )
    display_focus_default_utility_noise = normalize_display_focus(
        section.get("display_focus_default_utility_noise", DISPLAY_FOCUS_COLOUR_BARS),
        default=DISPLAY_FOCUS_COLOUR_BARS,
    )
    display_focus_default_utility_tone = normalize_display_focus(
        section.get("display_focus_default_utility_tone", DISPLAY_FOCUS_COLOUR_BARS),
        default=DISPLAY_FOCUS_COLOUR_BARS,
    )
    display_focus_default_utility_metronome = normalize_display_focus(
        section.get("display_focus_default_utility_metronome", DISPLAY_FOCUS_METRONOME),
        default=DISPLAY_FOCUS_METRONOME,
    )
    display_focus_default_automation = normalize_display_focus(
        section.get("display_focus_default_automation", DISPLAY_FOCUS_NONE),
        default=DISPLAY_FOCUS_NONE,
    )
    video_display_use_default_backdrop = _get_bool(section, "video_display_use_default_backdrop", True)
    video_display_backdrop_path = _decode_ascii_setting(str(section.get("video_display_backdrop_path", ""))).strip()
    video_display_show_backdrop_message = _get_bool(section, "video_display_show_backdrop_message", True)
    video_display_show_lyric_overlay = _get_bool(section, "video_display_show_lyric_overlay", False)
    video_display_show_stage_alert = _get_bool(section, "video_display_show_stage_alert", False)
    raw_video_display_lyric_overlay_rect = str(section.get("video_display_lyric_overlay_rect", "")).strip()
    parsed_video_display_lyric_overlay_rect: dict[str, int] = default_video_display_lyric_overlay_rect()
    if raw_video_display_lyric_overlay_rect:
        try:
            decoded_video_display_lyric_overlay_rect = json.loads(raw_video_display_lyric_overlay_rect)
        except Exception:
            decoded_video_display_lyric_overlay_rect = {}
        parsed_video_display_lyric_overlay_rect = _normalize_video_display_lyric_overlay_rect(
            decoded_video_display_lyric_overlay_rect
        )
    video_display_lyric_font_family = str(section.get("video_display_lyric_font_family", "")).strip()
    video_display_lyric_font_size = _clamp_int(_get_int(section, "video_display_lyric_font_size", 36), 10, 240)
    video_display_lyric_previous_line_count = _clamp_int(
        _get_int(section, "video_display_lyric_previous_line_count", 0),
        0,
        20,
    )
    video_display_lyric_next_line_count = _clamp_int(_get_int(section, "video_display_lyric_next_line_count", 0), 0, 20)
    video_display_lyric_played_color = _coerce_hex(str(section.get("video_display_lyric_played_color", "#A0A0A0")), "#A0A0A0")
    video_display_lyric_current_color = _coerce_hex(str(section.get("video_display_lyric_current_color", "#FFD400")), "#FFD400")
    video_display_lyric_next_color = _coerce_hex(str(section.get("video_display_lyric_next_color", "#FFFFFF")), "#FFFFFF")
    video_display_lyric_auto_adjust_role_sizes = _get_bool(section, "video_display_lyric_auto_adjust_role_sizes", True)
    video_display_lyric_played_scale_percent = _clamp_int(
        _get_int(section, "video_display_lyric_played_scale_percent", 70),
        25,
        300,
    )
    video_display_lyric_current_scale_percent = _clamp_int(
        _get_int(section, "video_display_lyric_current_scale_percent", 115),
        25,
        300,
    )
    video_display_lyric_next_scale_percent = _clamp_int(
        _get_int(section, "video_display_lyric_next_scale_percent", 90),
        25,
        300,
    )
    video_display_lyric_played_text_size = _clamp_int(_get_int(section, "video_display_lyric_played_text_size", 24), 8, 240)
    video_display_lyric_current_text_size = _clamp_int(_get_int(section, "video_display_lyric_current_text_size", 40), 8, 240)
    video_display_lyric_next_text_size = _clamp_int(_get_int(section, "video_display_lyric_next_text_size", 32), 8, 240)
    video_display_lyric_played_bold = _get_bool(section, "video_display_lyric_played_bold", True)
    video_display_lyric_current_bold = _get_bool(section, "video_display_lyric_current_bold", True)
    video_display_lyric_next_bold = _get_bool(section, "video_display_lyric_next_bold", True)
    video_display_lyric_played_italic = _get_bool(section, "video_display_lyric_played_italic", False)
    video_display_lyric_current_italic = _get_bool(section, "video_display_lyric_current_italic", False)
    video_display_lyric_next_italic = _get_bool(section, "video_display_lyric_next_italic", False)
    ndi_output_enabled = _get_bool(section, "ndi_output_enabled", False)
    ndi_output_name = _decode_ascii_setting(str(section.get("ndi_output_name", "pyssp-video"))).strip() or "pyssp-video"
    ndi_output_mode_playing = normalize_display_focus_override(
        section.get("ndi_output_mode_playing", DISPLAY_FOCUS_FOLLOW),
        default=DISPLAY_FOCUS_FOLLOW,
    )
    ndi_output_mode_idle = normalize_display_route_source(
        str(section.get("ndi_output_mode_idle", "backdrop")).strip().lower(),
        default="backdrop",
    )
    ndi_output_resolution_mode = str(section.get("ndi_output_resolution_mode", "source")).strip().lower()
    if ndi_output_resolution_mode not in {"source", "720p", "1080p", "custom"}:
        ndi_output_resolution_mode = "source"
    ndi_output_width = _clamp_int(_get_int(section, "ndi_output_width", 1920), 2, 8192)
    ndi_output_height = _clamp_int(_get_int(section, "ndi_output_height", 1080), 2, 8192)
    ndi_output_fps = _clamp_int(_get_int(section, "ndi_output_fps", 30), 1, 120)
    ndi_output_audio_enabled = _get_bool(section, "ndi_output_audio_enabled", True)
    ndi_output_audio_tap_mode = str(section.get("ndi_output_audio_tap_mode", "post_fader")).strip().lower()
    if ndi_output_audio_tap_mode not in {"pre_fader", "post_fader"}:
        ndi_output_audio_tap_mode = "post_fader"
    ndi_debug_print_enabled = _get_bool(section, "ndi_debug_print_enabled", False)
    ndi_debug_idle_audio_pacing_enabled = _get_bool(section, "ndi_debug_idle_audio_pacing_enabled", True)
    ndi_output_group = _decode_ascii_setting(str(section.get("ndi_output_group", "Public"))).strip() or "Public"
    ndi_output_discovery_servers = _decode_ascii_setting(str(section.get("ndi_output_discovery_servers", ""))).strip()
    ndi_output_allowed_adapters = _decode_ascii_setting(str(section.get("ndi_output_allowed_adapters", ""))).strip()
    ndi_output_multicast_enabled = _get_bool(section, "ndi_output_multicast_enabled", False)
    ndi_output_multicast_ttl = _clamp_int(_get_int(section, "ndi_output_multicast_ttl", 1), 1, 255)
    ndi_output_multicast_netmask = (
        _decode_ascii_setting(str(section.get("ndi_output_multicast_netmask", "255.255.0.0"))).strip() or "255.255.0.0"
    )
    ndi_output_multicast_netprefix = (
        _decode_ascii_setting(str(section.get("ndi_output_multicast_netprefix", "239.255.0.0"))).strip() or "239.255.0.0"
    )
    search_lyric_on_add_sound_button = _get_bool(section, "search_lyric_on_add_sound_button", True)
    new_lyric_file_format = str(section.get("new_lyric_file_format", "srt")).strip().lower()
    if new_lyric_file_format not in {"srt", "lrc"}:
        new_lyric_file_format = "srt"
    warn_dual_automation_sources = _get_bool(section, "warn_dual_automation_sources", True)
    automation_script_editor_show_lyric = _get_bool(section, "automation_script_editor_show_lyric", False)
    supported_audio_format_extensions = _normalize_supported_audio_format_extensions(
        [item.strip() for item in str(section.get("supported_audio_format_extensions", "")).split("\t") if item.strip()]
    )
    verify_sound_file_on_add = _get_bool(section, "verify_sound_file_on_add", True)
    allow_other_unsupported_audio_files = _get_bool(section, "allow_other_unsupported_audio_files", False)
    disable_path_safety = _get_bool(section, "disable_path_safety", False)
    set_file_encoding = str(section.get("set_file_encoding", "utf8")).strip().lower()
    if set_file_encoding not in {"utf8", "gbk"}:
        set_file_encoding = "utf8"
    ui_language = str(section.get("ui_language", "en")).strip().lower()
    if ui_language not in {"en", "zh", "zh_cn", "zh-cn"}:
        ui_language = "en"
    tips_open_on_startup = _get_bool(section, "tips_open_on_startup", True)
    max_multi_play_songs = _clamp_int(_get_int(section, "max_multi_play_songs", 5), 1, 32)
    preload_audio_memory_limit_mb = _clamp_int(_get_int(section, "preload_audio_memory_limit_mb", 512), 64, 1048576)
    waveform_cache_limit_mb = _clamp_int(_get_int(section, "waveform_cache_limit_mb", 1024), 128, 16384)
    preload_video_enabled = _get_bool(section, "preload_video_enabled", False)
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
    automation_command_buttons_follow_playback_controls = _get_bool(
        section,
        "automation_command_buttons_follow_playback_controls",
        False,
    )
    automation_command_button_auto_release_mode = str(
        section.get("automation_command_button_auto_release_mode", "immediate")
    ).strip().lower()
    if automation_command_button_auto_release_mode not in {"immediate", "down_only"}:
        automation_command_button_auto_release_mode = "immediate"
    utility_sound_buttons_follow_playback_controls = _get_bool(
        section,
        "utility_sound_buttons_follow_playback_controls",
        True,
    )
    candidate_error_action = str(section.get("candidate_error_action", "stop_playback")).strip().lower()
    if candidate_error_action not in {"stop_playback", "keep_playing"}:
        candidate_error_action = "stop_playback"
    web_remote_port = _clamp_int(_get_int(section, "web_remote_port", 5050), 1, 65532)
    web_remote_ws_port = _clamp_int(_get_int(section, "web_remote_ws_port", web_remote_port + 1), 1, 65535)
    web_remote_https_enabled = _get_bool(section, "web_remote_https_enabled", False)
    web_remote_https_port = _clamp_int(_get_int(section, "web_remote_https_port", web_remote_port + 2), 1, 65535)
    web_remote_wss_port = _clamp_int(_get_int(section, "web_remote_wss_port", web_remote_port + 3), 1, 65535)
    web_remote_enforce_https = _get_bool(section, "web_remote_enforce_https", False)
    web_remote_require_authentication = _get_bool(section, "web_remote_require_authentication", False)
    web_remote_username = _decode_ascii_setting(str(section.get("web_remote_username", '"admin"'))).strip() or "admin"
    web_remote_password = _decode_ascii_setting(str(section.get("web_remote_password", "")))
    web_remote_guest_view_enabled = _get_bool(section, "web_remote_guest_view_enabled", False)
    if web_remote_enforce_https:
        web_remote_https_enabled = True
    companion_satellite_host = str(section.get("companion_satellite_host", "127.0.0.1")).strip() or "127.0.0.1"
    companion_satellite_port = _clamp_int(_get_int(section, "companion_satellite_port", 16622), 1, 65535)
    legacy_companion_satellite_start_mode = str(section.get("companion_satellite_start_mode", "manual")).strip().lower()
    companion_satellite_enabled = _get_bool(
        section,
        "companion_satellite_enabled",
        legacy_companion_satellite_start_mode == "auto",
    )
    companion_bypass = _get_bool(section, "companion_bypass", False)
    internal_bypass = _get_bool(section, "internal_bypass", False)
    companion_satellite_columns = _clamp_int(_get_int(section, "companion_satellite_columns", 8), 1, 12)
    companion_satellite_rows = _clamp_int(_get_int(section, "companion_satellite_rows", 4), 1, 8)
    companion_satellite_render_mode = _normalize_companion_satellite_render_mode(
        section.get("companion_satellite_render_mode", "bitmap")
    )
    companion_satellite_serial_suffix = _normalize_companion_satellite_serial_suffix(
        section.get("companion_satellite_serial_suffix", default_companion_satellite_serial_suffix())
    )
    companion_command_mode = _normalize_companion_command_mode(section.get("companion_command_mode", "tcp"))
    companion_command_tcp_port = _clamp_int(_get_int(section, "companion_command_tcp_port", 16759), 1, 65535)
    companion_command_udp_port = _clamp_int(_get_int(section, "companion_command_udp_port", 16759), 1, 65535)
    companion_command_http_port = _clamp_int(_get_int(section, "companion_command_http_port", 8000), 1, 65535)
    companion_available_commands_filter_black_empty = _get_bool(
        section,
        "companion_available_commands_filter_black_empty",
        True,
    )
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
    soundbutton_timecode_offset_enabled = _get_bool(section, "soundbutton_timecode_offset_enabled", True)
    respect_soundbutton_timecode_timeline_setting = _get_bool(
        section,
        "respect_soundbutton_timecode_timeline_setting",
        True,
    )
    timeline_mode_raw = str(
        section.get("main_transport_timeline_mode", section.get("cue_editor_timeline_mode", "cue_region"))
    ).strip().lower()
    if timeline_mode_raw not in {"cue_region", "audio_file"}:
        timeline_mode_raw = "cue_region"
    main_progress_display_mode = str(section.get("main_progress_display_mode", "progress_bar")).strip().lower()
    if main_progress_display_mode not in {"progress_bar", "waveform"}:
        main_progress_display_mode = "progress_bar"
    main_progress_show_text = _get_bool(section, "main_progress_show_text", True)
    meter_output_tap_mode = str(section.get("meter_output_tap_mode", "post_fader")).strip().lower()
    if meter_output_tap_mode not in {"pre_fader", "post_fader"}:
        meter_output_tap_mode = "post_fader"
    sound_button_view_mode = normalize_sound_button_view_mode(section.get("sound_button_view_mode", SOUND_BUTTON_VIEW_GRID))
    sound_button_grid_columns = clamp_sound_button_grid_columns(section.get("sound_button_grid_columns", 8))
    sound_button_grid_rows = clamp_sound_button_grid_rows(section.get("sound_button_grid_rows", 6))
    sound_button_page_slot_cap = clamp_sound_button_page_slot_cap(section.get("sound_button_page_slot_cap", 48))
    sound_button_list_hide_empty = _get_bool(section, "sound_button_list_hide_empty", False)
    sound_button_list_hidden_columns = normalize_sound_button_list_hidden_columns(
        section.get("sound_button_list_hidden_columns", "")
    )
    sound_button_list_column_widths = normalize_sound_button_list_column_widths(
        section.get("sound_button_list_column_widths", "")
    )
    outside_action = str(section.get("main_jog_outside_cue_action", "stop_immediately")).strip().lower()
    if outside_action not in {
        "stop_immediately",
        "ignore_cue",
        "next_cue_or_stop",
        "stop_cue_or_end",
    }:
        outside_action = "stop_immediately"
    lock_unlock_method = str(section.get("lock_unlock_method", "click_3_random_points")).strip().lower()
    if lock_unlock_method not in {"click_3_random_points", "click_one_button", "slide_to_unlock"}:
        lock_unlock_method = "click_3_random_points"
    lock_password = _decode_ascii_setting(str(section.get("lock_password", "")))
    lock_require_password = _get_bool(section, "lock_require_password", False)
    lock_restart_state = str(section.get("lock_restart_state", "unlock_on_restart")).strip().lower()
    if lock_restart_state not in {"unlock_on_restart", "lock_on_restart"}:
        lock_restart_state = "unlock_on_restart"
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
    midi_input_device_ids = [item.strip() for item in str(section.get("midi_input_device_ids", "")).split("\t") if item.strip()]
    launchpad_enabled = _get_bool(section, "launchpad_enabled", False)
    launchpad_device_selector = str(section.get("launchpad_device_selector", "")).strip()
    launchpad_output_device_id = str(section.get("launchpad_output_device_id", "")).strip()
    launchpad_layout = str(section.get("launchpad_layout", "bottom_six")).strip().lower()
    if launchpad_layout not in {"bottom_six", "top_six"}:
        launchpad_layout = "bottom_six"
    launchpad_turn_off_empty_sound_button_lights = _get_bool(
        section,
        "launchpad_turn_off_empty_sound_button_lights",
        True,
    )
    launchpad_control_raw = str(section.get("launchpad_control_bindings", "")).strip()
    if launchpad_control_raw:
        launchpad_control_bindings = [str(item or "").strip() for item in launchpad_control_raw.split("\t")[:16]]
        if len(launchpad_control_bindings) < 16:
            launchpad_control_bindings.extend(["" for _ in range(16 - len(launchpad_control_bindings))])
    else:
        legacy_launchpad_action_raw = str(section.get("launchpad_action_bindings", "")).strip()
        if legacy_launchpad_action_raw:
            launchpad_control_bindings = [
                item
                for item in [str(item or "").strip() for item in legacy_launchpad_action_raw.split("\t")[:48]]
                if item and (not item.startswith("slot:"))
            ][:16]
            defaults = default_launchpad_control_bindings()
            if len(launchpad_control_bindings) < 16:
                launchpad_control_bindings.extend(defaults[len(launchpad_control_bindings):16])
        else:
            launchpad_control_bindings = default_launchpad_control_bindings()
    midi_quick_action_raw = str(section.get("midi_quick_action_bindings", "")).strip()
    if midi_quick_action_raw:
        midi_quick_action_bindings = _normalize_midi_quick_action_bindings(midi_quick_action_raw.split("\t"))
    else:
        midi_quick_action_bindings = default_midi_quick_action_bindings()
    midi_sound_button_hotkey_priority = str(section.get("midi_sound_button_hotkey_priority", "system_first")).strip().lower()
    if midi_sound_button_hotkey_priority not in {"system_first", "sound_button_first"}:
        midi_sound_button_hotkey_priority = "system_first"
    midi_rotary_volume_mode = str(section.get("midi_rotary_volume_mode", "relative")).strip().lower()
    if midi_rotary_volume_mode not in {"absolute", "relative"}:
        midi_rotary_volume_mode = "relative"
    midi_rotary_group_sensitivity = _clamp_int(_get_int(section, "midi_rotary_group_sensitivity", 1), 1, 20)
    midi_rotary_page_sensitivity = _clamp_int(_get_int(section, "midi_rotary_page_sensitivity", 1), 1, 20)
    midi_rotary_sound_button_sensitivity = _clamp_int(_get_int(section, "midi_rotary_sound_button_sensitivity", 1), 1, 20)
    rotary_relative_modes = {"auto", "twos_complement", "sign_magnitude", "binary_offset"}
    midi_rotary_group_relative_mode = str(section.get("midi_rotary_group_relative_mode", "auto")).strip().lower()
    if midi_rotary_group_relative_mode not in rotary_relative_modes:
        midi_rotary_group_relative_mode = "auto"
    midi_rotary_page_relative_mode = str(section.get("midi_rotary_page_relative_mode", "auto")).strip().lower()
    if midi_rotary_page_relative_mode not in rotary_relative_modes:
        midi_rotary_page_relative_mode = "auto"
    midi_rotary_sound_button_relative_mode = str(section.get("midi_rotary_sound_button_relative_mode", "auto")).strip().lower()
    if midi_rotary_sound_button_relative_mode not in rotary_relative_modes:
        midi_rotary_sound_button_relative_mode = "auto"
    midi_rotary_jog_relative_mode = str(section.get("midi_rotary_jog_relative_mode", "auto")).strip().lower()
    if midi_rotary_jog_relative_mode not in rotary_relative_modes:
        midi_rotary_jog_relative_mode = "auto"
    midi_rotary_volume_relative_mode = str(section.get("midi_rotary_volume_relative_mode", "auto")).strip().lower()
    if midi_rotary_volume_relative_mode not in rotary_relative_modes:
        midi_rotary_volume_relative_mode = "auto"
    midi_rotary_volume_step = _clamp_int(_get_int(section, "midi_rotary_volume_step", 2), 1, 20)
    midi_rotary_jog_step_ms = _clamp_int(_get_int(section, "midi_rotary_jog_step_ms", 250), 10, 5000)
    valid_stage_layout_ids = {
        "current_time",
        "alert",
        "total_time",
        "elapsed",
        "remaining",
        "progress_bar",
        "song_name",
        "lyric",
        "next_song",
    }
    stage_display_layout = [
        str(v).strip().lower()
        for v in str(section.get("stage_display_layout", "")).split("\t")
        if str(v).strip().lower() in valid_stage_layout_ids
    ]
    if not stage_display_layout:
        stage_display_layout = default_stage_display_layout()
    else:
        for default_id in default_stage_display_layout():
            if default_id not in stage_display_layout:
                stage_display_layout.append(default_id)
    stage_display_text_source = str(section.get("stage_display_text_source", "caption")).strip().lower()
    if stage_display_text_source not in {"caption", "filename", "note"}:
        stage_display_text_source = "caption"
    stage_display_font_family = str(section.get("stage_display_font_family", "")).strip()
    stage_display_font_size = _clamp_int(_get_int(section, "stage_display_font_size", 24), 10, 240)
    stage_display_lyric_font_family = str(section.get("stage_display_lyric_font_family", "")).strip()
    stage_display_lyric_font_size = _clamp_int(_get_int(section, "stage_display_lyric_font_size", 24), 10, 240)
    stage_display_lyric_previous_line_count = _clamp_int(
        _get_int(section, "stage_display_lyric_previous_line_count", 0),
        0,
        20,
    )
    stage_display_lyric_next_line_count = _clamp_int(
        _get_int(section, "stage_display_lyric_next_line_count", 0),
        0,
        20,
    )
    stage_display_lyric_played_color = _coerce_hex(
        str(section.get("stage_display_lyric_played_color", "#A0A0A0")),
        "#A0A0A0",
    )
    stage_display_lyric_current_color = _coerce_hex(
        str(section.get("stage_display_lyric_current_color", "#FFD400")),
        "#FFD400",
    )
    stage_display_lyric_next_color = _coerce_hex(
        str(section.get("stage_display_lyric_next_color", "#FFFFFF")),
        "#FFFFFF",
    )
    stage_display_lyric_auto_adjust_role_sizes = _get_bool(section, "stage_display_lyric_auto_adjust_role_sizes", True)
    stage_display_lyric_played_scale_percent = _clamp_int(
        _get_int(section, "stage_display_lyric_played_scale_percent", 70),
        25,
        300,
    )
    stage_display_lyric_current_scale_percent = _clamp_int(
        _get_int(section, "stage_display_lyric_current_scale_percent", 115),
        25,
        300,
    )
    stage_display_lyric_next_scale_percent = _clamp_int(
        _get_int(section, "stage_display_lyric_next_scale_percent", 90),
        25,
        300,
    )
    stage_display_lyric_played_text_size = _clamp_int(
        _get_int(section, "stage_display_lyric_played_text_size", 18),
        8,
        240,
    )
    stage_display_lyric_current_text_size = _clamp_int(
        _get_int(section, "stage_display_lyric_current_text_size", 28),
        8,
        240,
    )
    stage_display_lyric_next_text_size = _clamp_int(
        _get_int(section, "stage_display_lyric_next_text_size", 22),
        8,
        240,
    )
    stage_display_lyric_played_bold = _get_bool(section, "stage_display_lyric_played_bold", True)
    stage_display_lyric_current_bold = _get_bool(section, "stage_display_lyric_current_bold", True)
    stage_display_lyric_next_bold = _get_bool(section, "stage_display_lyric_next_bold", True)
    stage_display_lyric_played_italic = _get_bool(section, "stage_display_lyric_played_italic", False)
    stage_display_lyric_current_italic = _get_bool(section, "stage_display_lyric_current_italic", False)
    stage_display_lyric_next_italic = _get_bool(section, "stage_display_lyric_next_italic", False)
    raw_stage_display_gadgets = str(section.get("stage_display_gadgets", "")).strip()
    parsed_stage_display_gadgets: dict[str, dict[str, object]] = {}
    if raw_stage_display_gadgets:
        try:
            decoded = json.loads(raw_stage_display_gadgets)
            if isinstance(decoded, dict):
                parsed_stage_display_gadgets = {
                    str(k): dict(v) for k, v in decoded.items() if isinstance(v, dict)
                }
        except Exception:
            parsed_stage_display_gadgets = {}
    stage_display_visibility = {
        "current_time": _get_bool(section, "stage_display_show_current_time", True),
        "alert": _get_bool(section, "stage_display_show_alert", False),
        "total_time": _get_bool(section, "stage_display_show_total_time", True),
        "elapsed": _get_bool(section, "stage_display_show_elapsed", True),
        "remaining": _get_bool(section, "stage_display_show_remaining", True),
        "progress_bar": _get_bool(section, "stage_display_show_progress_bar", True),
        "song_name": _get_bool(section, "stage_display_show_song_name", True),
        "lyric": _get_bool(section, "stage_display_show_lyric", True),
        "next_song": _get_bool(section, "stage_display_show_next_song", True),
    }
    stage_display_gadgets = _normalize_stage_display_gadgets(
        parsed_stage_display_gadgets,
        fallback_layout=stage_display_layout,
        fallback_visibility=stage_display_visibility,
    )
    raw_window_layout = str(section.get("window_layout", "")).strip()
    parsed_window_layout: dict[str, object] = {}
    if raw_window_layout:
        try:
            decoded = json.loads(raw_window_layout)
            if isinstance(decoded, dict):
                parsed_window_layout = {str(k): v for k, v in decoded.items()}
        except Exception:
            parsed_window_layout = {}
    window_layout = normalize_window_layout(parsed_window_layout)
    raw_dock_dividers = str(section.get("dock_dividers", "")).strip()
    dock_dividers: list[str] = []
    if raw_dock_dividers:
        try:
            decoded = json.loads(raw_dock_dividers)
            if isinstance(decoded, list):
                dock_dividers = [str(value).strip() for value in decoded if str(value).strip()]
        except Exception:
            dock_dividers = []
    raw_standalone_docks = str(section.get("standalone_docks", "")).strip()
    standalone_docks: list[str] = []
    if raw_standalone_docks:
        try:
            decoded = json.loads(raw_standalone_docks)
            if isinstance(decoded, list):
                standalone_docks = [str(value).strip() for value in decoded if str(value).strip()]
        except Exception:
            standalone_docks = []
    return AppSettings(
        last_open_dir=str(section.get("last_open_dir", "")),
        last_save_dir=str(section.get("last_save_dir", "")),
        last_sound_dir=str(section.get("last_sound_dir", "")),
        last_set_path=str(section.get("last_set_path", "")),
        active_group_color=_coerce_hex(str(section.get("active_group_color", "#EDE8C8")), "#EDE8C8"),
        inactive_group_color=_coerce_hex(str(section.get("inactive_group_color", "#ECECEC")), "#ECECEC"),
        title_char_limit=title_limit,
        show_file_notifications=_get_bool(section, "show_file_notifications", True),
        now_playing_display_mode=now_playing_display_mode,
        main_ui_lyric_display_mode=main_ui_lyric_display_mode,
        lyric_display_transparent_mode=lyric_display_transparent_mode,
        lyric_display_show_not_playing_message=lyric_display_show_not_playing_message,
        lyric_display_font_family=lyric_display_font_family,
        lyric_display_font_size=lyric_display_font_size,
        lyric_display_previous_line_count=lyric_display_previous_line_count,
        lyric_display_next_line_count=lyric_display_next_line_count,
        lyric_display_played_color=lyric_display_played_color,
        lyric_display_current_color=lyric_display_current_color,
        lyric_display_next_color=lyric_display_next_color,
        lyric_display_auto_adjust_role_sizes=lyric_display_auto_adjust_role_sizes,
        lyric_display_played_scale_percent=lyric_display_played_scale_percent,
        lyric_display_current_scale_percent=lyric_display_current_scale_percent,
        lyric_display_next_scale_percent=lyric_display_next_scale_percent,
        lyric_display_played_text_size=lyric_display_played_text_size,
        lyric_display_current_text_size=lyric_display_current_text_size,
        lyric_display_next_text_size=lyric_display_next_text_size,
        lyric_display_played_bold=lyric_display_played_bold,
        lyric_display_current_bold=lyric_display_current_bold,
        lyric_display_next_bold=lyric_display_next_bold,
        lyric_display_played_italic=lyric_display_played_italic,
        lyric_display_current_italic=lyric_display_current_italic,
        lyric_display_next_italic=lyric_display_next_italic,
        search_lyric_on_add_sound_button=search_lyric_on_add_sound_button,
        new_lyric_file_format=new_lyric_file_format,
        warn_dual_automation_sources=warn_dual_automation_sources,
        automation_script_editor_show_lyric=automation_script_editor_show_lyric,
        supported_audio_format_extensions=supported_audio_format_extensions,
        verify_sound_file_on_add=verify_sound_file_on_add,
        allow_other_unsupported_audio_files=allow_other_unsupported_audio_files,
        disable_path_safety=disable_path_safety,
        lock_allow_quit=_get_bool(section, "lock_allow_quit", True),
        lock_allow_system_hotkeys=_get_bool(section, "lock_allow_system_hotkeys", False),
        lock_allow_quick_action_hotkeys=_get_bool(section, "lock_allow_quick_action_hotkeys", False),
        lock_allow_sound_button_hotkeys=_get_bool(section, "lock_allow_sound_button_hotkeys", False),
        lock_allow_midi_control=_get_bool(section, "lock_allow_midi_control", True),
        lock_auto_allow_quit=_get_bool(section, "lock_auto_allow_quit", True),
        lock_auto_allow_midi_control=_get_bool(section, "lock_auto_allow_midi_control", True),
        lock_unlock_method=lock_unlock_method,
        lock_require_password=lock_require_password,
        lock_password=lock_password,
        lock_restart_state=lock_restart_state,
        lock_was_locked_on_exit=_get_bool(section, "lock_was_locked_on_exit", False),
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
        vocal_removed_toggle_fade_mode=vocal_removed_toggle_fade_mode,
        vocal_removed_toggle_custom_sec=vocal_removed_toggle_custom_sec,
        vocal_removed_toggle_always_sec=vocal_removed_toggle_always_sec,
        talk_volume_level=talk_volume_level,
        talk_fade_sec=talk_fade_sec,
        talk_volume_mode=talk_volume_mode,
        talk_blink_button=_get_bool(section, "talk_blink_button", False),
        talk_shift_accelerator=_get_bool(section, "talk_shift_accelerator", True),
        hotkeys_ignore_talk_level=_get_bool(section, "hotkeys_ignore_talk_level", False),
        enter_key_mirrors_space=_get_bool(section, "enter_key_mirrors_space", False),
        log_file_enabled=_get_bool(section, "log_file_enabled", True),
        runtime_log_enabled=_get_bool(section, "runtime_log_enabled", True),
        runtime_log_limit_mb=clamp_runtime_log_limit_mb(_get_int(section, "runtime_log_limit_mb", DEFAULT_RUNTIME_LOG_LIMIT_MB)),
        reset_all_on_startup=_get_bool(section, "reset_all_on_startup", False),
        click_playing_action=click_playing_action,
        search_double_click_action=search_double_click_action,
        set_file_encoding=set_file_encoding,
        ui_language="zh_cn" if ui_language in {"zh", "zh_cn", "zh-cn"} else "en",
        app_version=str(section.get("app_version", "")).strip(),
        app_build_id=str(section.get("app_build_id", "")).strip(),
        tips_open_on_startup=tips_open_on_startup,
        audio_output_device=str(section.get("audio_output_device", "")),
        preload_audio_enabled=_get_bool(section, "preload_audio_enabled", False),
        preload_current_page_audio=_get_bool(section, "preload_current_page_audio", True),
        preload_audio_memory_limit_mb=preload_audio_memory_limit_mb,
        preload_memory_pressure_enabled=_get_bool(section, "preload_memory_pressure_enabled", True),
        preload_pause_on_playback=_get_bool(section, "preload_pause_on_playback", True),
        preload_use_ffmpeg=_get_bool(section, "preload_use_ffmpeg", True),
        preload_video_enabled=preload_video_enabled,
        waveform_cache_limit_mb=waveform_cache_limit_mb,
        waveform_cache_clear_on_launch=_get_bool(section, "waveform_cache_clear_on_launch", True),
        max_multi_play_songs=max_multi_play_songs,
        multi_play_limit_action=multi_play_limit_action,
        playlist_play_mode=playlist_play_mode,
        rapid_fire_play_mode=rapid_fire_play_mode,
        next_play_mode=next_play_mode,
        playlist_loop_mode=playlist_loop_mode,
        automation_command_buttons_follow_playback_controls=automation_command_buttons_follow_playback_controls,
        automation_command_button_auto_release_mode=automation_command_button_auto_release_mode,
        utility_sound_buttons_follow_playback_controls=utility_sound_buttons_follow_playback_controls,
        candidate_error_action=candidate_error_action,
        web_remote_enabled=_get_bool(section, "web_remote_enabled", False),
        web_remote_port=web_remote_port,
        web_remote_ws_port=web_remote_ws_port,
        web_remote_https_enabled=web_remote_https_enabled,
        web_remote_https_port=web_remote_https_port,
        web_remote_wss_port=web_remote_wss_port,
        web_remote_enforce_https=web_remote_enforce_https,
        web_remote_require_authentication=web_remote_require_authentication,
        web_remote_username=web_remote_username,
        web_remote_password=web_remote_password,
        web_remote_guest_view_enabled=web_remote_guest_view_enabled,
        companion_satellite_host=companion_satellite_host,
        companion_satellite_port=companion_satellite_port,
        companion_satellite_enabled=companion_satellite_enabled,
        companion_bypass=companion_bypass,
        internal_bypass=internal_bypass,
        companion_satellite_columns=companion_satellite_columns,
        companion_satellite_rows=companion_satellite_rows,
        companion_satellite_render_mode=companion_satellite_render_mode,
        companion_satellite_serial_suffix=companion_satellite_serial_suffix,
        companion_command_mode=companion_command_mode,
        companion_command_tcp_port=companion_command_tcp_port,
        companion_command_udp_port=companion_command_udp_port,
        companion_command_http_port=companion_command_http_port,
        companion_available_commands_filter_black_empty=companion_available_commands_filter_black_empty,
        timecode_audio_output_device=timecode_audio_output_device,
        timecode_midi_output_device=timecode_midi_output_device,
        timecode_mode=timecode_mode,
        timecode_fps=timecode_fps,
        timecode_mtc_fps=timecode_mtc_fps,
        timecode_mtc_idle_behavior=timecode_mtc_idle_behavior,
        timecode_sample_rate=timecode_sample_rate,
        timecode_bit_depth=timecode_bit_depth,
        show_timecode_panel=_get_bool(section, "show_timecode_panel", False),
        show_video_control_panel=_get_bool(section, "show_video_control_panel", False),
        show_colour_legend=_get_bool(section, "show_colour_legend", True),
        timecode_timeline_mode=timecode_timeline_mode_raw,
        soundbutton_timecode_offset_enabled=soundbutton_timecode_offset_enabled,
        respect_soundbutton_timecode_timeline_setting=respect_soundbutton_timecode_timeline_setting,
        main_transport_timeline_mode=timeline_mode_raw,
        main_progress_display_mode=main_progress_display_mode,
        main_progress_show_text=main_progress_show_text,
        meter_output_tap_mode=meter_output_tap_mode,
        sound_button_view_mode=sound_button_view_mode,
        sound_button_grid_columns=sound_button_grid_columns,
        sound_button_grid_rows=sound_button_grid_rows,
        sound_button_page_slot_cap=sound_button_page_slot_cap,
        sound_button_list_hide_empty=sound_button_list_hide_empty,
        sound_button_list_hidden_columns=sound_button_list_hidden_columns,
        sound_button_list_column_widths=sound_button_list_column_widths,
        main_jog_outside_cue_action=outside_action,
        color_empty=_coerce_hex(str(section.get("color_empty", "#0B868A")), "#0B868A"),
        color_unplayed=_coerce_hex(str(section.get("color_unplayed", "#B0B0B0")), "#B0B0B0"),
        color_highlight=_coerce_hex(str(section.get("color_highlight", "#A6D8FF")), "#A6D8FF"),
        color_playing=_coerce_hex(str(section.get("color_playing", "#66FF33")), "#66FF33"),
        color_played=_coerce_hex(str(section.get("color_played", "#FF3B30")), "#FF3B30"),
        color_error=_coerce_hex(str(section.get("color_error", "#7B3FB3")), "#7B3FB3"),
        color_lock=_coerce_hex(str(section.get("color_lock", "#F2D74A")), "#F2D74A"),
        color_place_marker=_coerce_hex(str(section.get("color_place_marker", "#D0D0D0")), "#D0D0D0"),
        color_copied_to_cue=_coerce_hex(str(section.get("color_copied_to_cue", "#2E65FF")), "#2E65FF"),
        color_cue_indicator=_coerce_hex(str(section.get("color_cue_indicator", "#61D6FF")), "#61D6FF"),
        color_volume_indicator=_coerce_hex(str(section.get("color_volume_indicator", "#FFD45A")), "#FFD45A"),
        color_vocal_removed_indicator=_coerce_hex(
            str(section.get("color_vocal_removed_indicator", "#8E7CFF")),
            "#8E7CFF",
        ),
        color_midi_indicator=_coerce_hex(str(section.get("color_midi_indicator", "#FF9E4A")), "#FF9E4A"),
        color_lyric_indicator=_coerce_hex(str(section.get("color_lyric_indicator", "#57C3A4")), "#57C3A4"),
        color_video_indicator=_coerce_hex(str(section.get("color_video_indicator", "#FF5E7A")), "#FF5E7A"),
        color_automation_indicator=_coerce_hex(str(section.get("color_automation_indicator", "#49C16D")), "#49C16D"),
        color_automation_indicator_bypassed=_coerce_hex(
            str(section.get("color_automation_indicator_bypassed", "#9A9A9A")),
            "#9A9A9A",
        ),
        color_automation_script_indicator=_coerce_hex(
            str(section.get("color_automation_script_indicator", "#2E8BFF")),
            "#2E8BFF",
        ),
        color_automation_script_indicator_bypassed=_coerce_hex(
            str(section.get("color_automation_script_indicator_bypassed", "#708090")),
            "#708090",
        ),
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
        hotkey_play_selected_pause_1=str(section.get("hotkey_play_selected_pause_1", "")).strip(),
        hotkey_play_selected_pause_2=str(section.get("hotkey_play_selected_pause_2", "")).strip(),
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
        hotkey_volume_up_1=str(section.get("hotkey_volume_up_1", "")).strip(),
        hotkey_volume_up_2=str(section.get("hotkey_volume_up_2", "")).strip(),
        hotkey_volume_down_1=str(section.get("hotkey_volume_down_1", "")).strip(),
        hotkey_volume_down_2=str(section.get("hotkey_volume_down_2", "")).strip(),
        hotkey_lock_toggle_1=str(section.get("hotkey_lock_toggle_1", "Ctrl+L")).strip(),
        hotkey_lock_toggle_2=str(section.get("hotkey_lock_toggle_2", "")).strip(),
        hotkey_open_hide_lyric_navigator_1=str(section.get("hotkey_open_hide_lyric_navigator_1", "")).strip(),
        hotkey_open_hide_lyric_navigator_2=str(section.get("hotkey_open_hide_lyric_navigator_2", "")).strip(),
        hotkey_toggle_lyric_display_transparent_mode_1=str(section.get("hotkey_toggle_lyric_display_transparent_mode_1", "")).strip(),
        hotkey_toggle_lyric_display_transparent_mode_2=str(section.get("hotkey_toggle_lyric_display_transparent_mode_2", "")).strip(),
        quick_action_enabled=_get_bool(section, "quick_action_enabled", False),
        quick_action_keys=quick_action_keys,
        sound_button_hotkey_enabled=_get_bool(section, "sound_button_hotkey_enabled", False),
        sound_button_hotkey_priority=sound_button_hotkey_priority,
        sound_button_hotkey_go_to_playing=_get_bool(section, "sound_button_hotkey_go_to_playing", False),
        sound_button_hotkey_system_order=sound_button_hotkey_system_order,
        midi_input_device_ids=midi_input_device_ids,
        launchpad_enabled=launchpad_enabled,
        launchpad_device_selector=launchpad_device_selector,
        launchpad_output_device_id=launchpad_output_device_id,
        launchpad_layout=launchpad_layout,
        launchpad_turn_off_empty_sound_button_lights=launchpad_turn_off_empty_sound_button_lights,
        launchpad_control_bindings=launchpad_control_bindings,
        midi_hotkey_new_set_1=str(section.get("midi_hotkey_new_set_1", "")).strip(),
        midi_hotkey_new_set_2=str(section.get("midi_hotkey_new_set_2", "")).strip(),
        midi_hotkey_open_set_1=str(section.get("midi_hotkey_open_set_1", "")).strip(),
        midi_hotkey_open_set_2=str(section.get("midi_hotkey_open_set_2", "")).strip(),
        midi_hotkey_save_set_1=str(section.get("midi_hotkey_save_set_1", "")).strip(),
        midi_hotkey_save_set_2=str(section.get("midi_hotkey_save_set_2", "")).strip(),
        midi_hotkey_save_set_as_1=str(section.get("midi_hotkey_save_set_as_1", "")).strip(),
        midi_hotkey_save_set_as_2=str(section.get("midi_hotkey_save_set_as_2", "")).strip(),
        midi_hotkey_search_1=str(section.get("midi_hotkey_search_1", "")).strip(),
        midi_hotkey_search_2=str(section.get("midi_hotkey_search_2", "")).strip(),
        midi_hotkey_options_1=str(section.get("midi_hotkey_options_1", "")).strip(),
        midi_hotkey_options_2=str(section.get("midi_hotkey_options_2", "")).strip(),
        midi_hotkey_play_selected_pause_1=str(section.get("midi_hotkey_play_selected_pause_1", "")).strip(),
        midi_hotkey_play_selected_pause_2=str(section.get("midi_hotkey_play_selected_pause_2", "")).strip(),
        midi_hotkey_play_selected_1=str(section.get("midi_hotkey_play_selected_1", "")).strip(),
        midi_hotkey_play_selected_2=str(section.get("midi_hotkey_play_selected_2", "")).strip(),
        midi_hotkey_pause_toggle_1=str(section.get("midi_hotkey_pause_toggle_1", "")).strip(),
        midi_hotkey_pause_toggle_2=str(section.get("midi_hotkey_pause_toggle_2", "")).strip(),
        midi_hotkey_stop_playback_1=str(section.get("midi_hotkey_stop_playback_1", "")).strip(),
        midi_hotkey_stop_playback_2=str(section.get("midi_hotkey_stop_playback_2", "")).strip(),
        midi_hotkey_talk_1=str(section.get("midi_hotkey_talk_1", "")).strip(),
        midi_hotkey_talk_2=str(section.get("midi_hotkey_talk_2", "")).strip(),
        midi_hotkey_next_group_1=str(section.get("midi_hotkey_next_group_1", "")).strip(),
        midi_hotkey_next_group_2=str(section.get("midi_hotkey_next_group_2", "")).strip(),
        midi_hotkey_prev_group_1=str(section.get("midi_hotkey_prev_group_1", "")).strip(),
        midi_hotkey_prev_group_2=str(section.get("midi_hotkey_prev_group_2", "")).strip(),
        midi_hotkey_next_page_1=str(section.get("midi_hotkey_next_page_1", "")).strip(),
        midi_hotkey_next_page_2=str(section.get("midi_hotkey_next_page_2", "")).strip(),
        midi_hotkey_prev_page_1=str(section.get("midi_hotkey_prev_page_1", "")).strip(),
        midi_hotkey_prev_page_2=str(section.get("midi_hotkey_prev_page_2", "")).strip(),
        midi_hotkey_next_sound_button_1=str(section.get("midi_hotkey_next_sound_button_1", "")).strip(),
        midi_hotkey_next_sound_button_2=str(section.get("midi_hotkey_next_sound_button_2", "")).strip(),
        midi_hotkey_prev_sound_button_1=str(section.get("midi_hotkey_prev_sound_button_1", "")).strip(),
        midi_hotkey_prev_sound_button_2=str(section.get("midi_hotkey_prev_sound_button_2", "")).strip(),
        midi_hotkey_multi_play_1=str(section.get("midi_hotkey_multi_play_1", "")).strip(),
        midi_hotkey_multi_play_2=str(section.get("midi_hotkey_multi_play_2", "")).strip(),
        midi_hotkey_go_to_playing_1=str(section.get("midi_hotkey_go_to_playing_1", "")).strip(),
        midi_hotkey_go_to_playing_2=str(section.get("midi_hotkey_go_to_playing_2", "")).strip(),
        midi_hotkey_loop_1=str(section.get("midi_hotkey_loop_1", "")).strip(),
        midi_hotkey_loop_2=str(section.get("midi_hotkey_loop_2", "")).strip(),
        midi_hotkey_next_1=str(section.get("midi_hotkey_next_1", "")).strip(),
        midi_hotkey_next_2=str(section.get("midi_hotkey_next_2", "")).strip(),
        midi_hotkey_rapid_fire_1=str(section.get("midi_hotkey_rapid_fire_1", "")).strip(),
        midi_hotkey_rapid_fire_2=str(section.get("midi_hotkey_rapid_fire_2", "")).strip(),
        midi_hotkey_shuffle_1=str(section.get("midi_hotkey_shuffle_1", "")).strip(),
        midi_hotkey_shuffle_2=str(section.get("midi_hotkey_shuffle_2", "")).strip(),
        midi_hotkey_reset_page_1=str(section.get("midi_hotkey_reset_page_1", "")).strip(),
        midi_hotkey_reset_page_2=str(section.get("midi_hotkey_reset_page_2", "")).strip(),
        midi_hotkey_play_list_1=str(section.get("midi_hotkey_play_list_1", "")).strip(),
        midi_hotkey_play_list_2=str(section.get("midi_hotkey_play_list_2", "")).strip(),
        midi_hotkey_fade_in_1=str(section.get("midi_hotkey_fade_in_1", "")).strip(),
        midi_hotkey_fade_in_2=str(section.get("midi_hotkey_fade_in_2", "")).strip(),
        midi_hotkey_cross_fade_1=str(section.get("midi_hotkey_cross_fade_1", "")).strip(),
        midi_hotkey_cross_fade_2=str(section.get("midi_hotkey_cross_fade_2", "")).strip(),
        midi_hotkey_fade_out_1=str(section.get("midi_hotkey_fade_out_1", "")).strip(),
        midi_hotkey_fade_out_2=str(section.get("midi_hotkey_fade_out_2", "")).strip(),
        midi_hotkey_mute_1=str(section.get("midi_hotkey_mute_1", "")).strip(),
        midi_hotkey_mute_2=str(section.get("midi_hotkey_mute_2", "")).strip(),
        midi_hotkey_volume_up_1=str(section.get("midi_hotkey_volume_up_1", "")).strip(),
        midi_hotkey_volume_up_2=str(section.get("midi_hotkey_volume_up_2", "")).strip(),
        midi_hotkey_volume_down_1=str(section.get("midi_hotkey_volume_down_1", "")).strip(),
        midi_hotkey_volume_down_2=str(section.get("midi_hotkey_volume_down_2", "")).strip(),
        midi_hotkey_lock_toggle_1=str(section.get("midi_hotkey_lock_toggle_1", "")).strip(),
        midi_hotkey_lock_toggle_2=str(section.get("midi_hotkey_lock_toggle_2", "")).strip(),
        midi_hotkey_open_hide_lyric_navigator_1=str(section.get("midi_hotkey_open_hide_lyric_navigator_1", "")).strip(),
        midi_hotkey_open_hide_lyric_navigator_2=str(section.get("midi_hotkey_open_hide_lyric_navigator_2", "")).strip(),
        midi_hotkey_toggle_lyric_display_transparent_mode_1=str(section.get("midi_hotkey_toggle_lyric_display_transparent_mode_1", "")).strip(),
        midi_hotkey_toggle_lyric_display_transparent_mode_2=str(section.get("midi_hotkey_toggle_lyric_display_transparent_mode_2", "")).strip(),
        midi_quick_action_enabled=_get_bool(section, "midi_quick_action_enabled", False),
        midi_quick_action_bindings=midi_quick_action_bindings,
        midi_sound_button_hotkey_enabled=_get_bool(section, "midi_sound_button_hotkey_enabled", False),
        midi_sound_button_hotkey_priority=midi_sound_button_hotkey_priority,
        midi_sound_button_hotkey_go_to_playing=_get_bool(section, "midi_sound_button_hotkey_go_to_playing", False),
        midi_rotary_enabled=_get_bool(section, "midi_rotary_enabled", False),
        midi_rotary_group_binding=str(section.get("midi_rotary_group_binding", "")).strip(),
        midi_rotary_page_binding=str(section.get("midi_rotary_page_binding", "")).strip(),
        midi_rotary_sound_button_binding=str(section.get("midi_rotary_sound_button_binding", "")).strip(),
        midi_rotary_jog_binding=str(section.get("midi_rotary_jog_binding", "")).strip(),
        midi_rotary_volume_binding=str(section.get("midi_rotary_volume_binding", "")).strip(),
        midi_rotary_group_invert=_get_bool(section, "midi_rotary_group_invert", False),
        midi_rotary_page_invert=_get_bool(section, "midi_rotary_page_invert", False),
        midi_rotary_sound_button_invert=_get_bool(section, "midi_rotary_sound_button_invert", False),
        midi_rotary_jog_invert=_get_bool(section, "midi_rotary_jog_invert", False),
        midi_rotary_volume_invert=_get_bool(section, "midi_rotary_volume_invert", False),
        midi_rotary_group_sensitivity=midi_rotary_group_sensitivity,
        midi_rotary_page_sensitivity=midi_rotary_page_sensitivity,
        midi_rotary_sound_button_sensitivity=midi_rotary_sound_button_sensitivity,
        midi_rotary_group_relative_mode=midi_rotary_group_relative_mode,
        midi_rotary_page_relative_mode=midi_rotary_page_relative_mode,
        midi_rotary_sound_button_relative_mode=midi_rotary_sound_button_relative_mode,
        midi_rotary_jog_relative_mode=midi_rotary_jog_relative_mode,
        midi_rotary_volume_relative_mode=midi_rotary_volume_relative_mode,
        midi_rotary_volume_mode=midi_rotary_volume_mode,
        midi_rotary_volume_step=midi_rotary_volume_step,
        midi_rotary_jog_step_ms=midi_rotary_jog_step_ms,
        stage_display_layout=stage_display_layout,
        stage_display_show_current_time=stage_display_visibility["current_time"],
        stage_display_show_alert=stage_display_visibility["alert"],
        stage_display_show_total_time=stage_display_visibility["total_time"],
        stage_display_show_elapsed=stage_display_visibility["elapsed"],
        stage_display_show_remaining=stage_display_visibility["remaining"],
        stage_display_show_progress_bar=stage_display_visibility["progress_bar"],
        stage_display_show_song_name=stage_display_visibility["song_name"],
        stage_display_show_lyric=stage_display_visibility["lyric"],
        stage_display_show_next_song=stage_display_visibility["next_song"],
        stage_display_gadgets=stage_display_gadgets,
        stage_display_text_source=stage_display_text_source,
        stage_display_font_family=stage_display_font_family,
        stage_display_font_size=stage_display_font_size,
        stage_display_lyric_font_family=stage_display_lyric_font_family,
        stage_display_lyric_font_size=stage_display_lyric_font_size,
        stage_display_lyric_previous_line_count=stage_display_lyric_previous_line_count,
        stage_display_lyric_next_line_count=stage_display_lyric_next_line_count,
        stage_display_lyric_played_color=stage_display_lyric_played_color,
        stage_display_lyric_current_color=stage_display_lyric_current_color,
        stage_display_lyric_next_color=stage_display_lyric_next_color,
        stage_display_lyric_auto_adjust_role_sizes=stage_display_lyric_auto_adjust_role_sizes,
        stage_display_lyric_played_scale_percent=stage_display_lyric_played_scale_percent,
        stage_display_lyric_current_scale_percent=stage_display_lyric_current_scale_percent,
        stage_display_lyric_next_scale_percent=stage_display_lyric_next_scale_percent,
        stage_display_lyric_played_text_size=stage_display_lyric_played_text_size,
        stage_display_lyric_current_text_size=stage_display_lyric_current_text_size,
        stage_display_lyric_next_text_size=stage_display_lyric_next_text_size,
        stage_display_lyric_played_bold=stage_display_lyric_played_bold,
        stage_display_lyric_current_bold=stage_display_lyric_current_bold,
        stage_display_lyric_next_bold=stage_display_lyric_next_bold,
        stage_display_lyric_played_italic=stage_display_lyric_played_italic,
        stage_display_lyric_current_italic=stage_display_lyric_current_italic,
        stage_display_lyric_next_italic=stage_display_lyric_next_italic,
        video_display_mode_playing=video_display_mode_playing,
        video_display_mode_idle=video_display_mode_idle,
        display_focus_default_video=display_focus_default_video,
        display_focus_default_audio=display_focus_default_audio,
        display_focus_default_audio_with_lyric=display_focus_default_audio_with_lyric,
        display_focus_default_utility_blank=display_focus_default_utility_blank,
        display_focus_default_utility_noise=display_focus_default_utility_noise,
        display_focus_default_utility_tone=display_focus_default_utility_tone,
        display_focus_default_utility_metronome=display_focus_default_utility_metronome,
        display_focus_default_automation=display_focus_default_automation,
        video_display_use_default_backdrop=video_display_use_default_backdrop,
        video_display_backdrop_path=video_display_backdrop_path,
        video_display_show_backdrop_message=video_display_show_backdrop_message,
        video_display_show_lyric_overlay=video_display_show_lyric_overlay,
        video_display_show_stage_alert=video_display_show_stage_alert,
        video_display_lyric_overlay_rect=parsed_video_display_lyric_overlay_rect,
        video_display_lyric_font_family=video_display_lyric_font_family,
        video_display_lyric_font_size=video_display_lyric_font_size,
        video_display_lyric_previous_line_count=video_display_lyric_previous_line_count,
        video_display_lyric_next_line_count=video_display_lyric_next_line_count,
        video_display_lyric_played_color=video_display_lyric_played_color,
        video_display_lyric_current_color=video_display_lyric_current_color,
        video_display_lyric_next_color=video_display_lyric_next_color,
        video_display_lyric_auto_adjust_role_sizes=video_display_lyric_auto_adjust_role_sizes,
        video_display_lyric_played_scale_percent=video_display_lyric_played_scale_percent,
        video_display_lyric_current_scale_percent=video_display_lyric_current_scale_percent,
        video_display_lyric_next_scale_percent=video_display_lyric_next_scale_percent,
        video_display_lyric_played_text_size=video_display_lyric_played_text_size,
        video_display_lyric_current_text_size=video_display_lyric_current_text_size,
        video_display_lyric_next_text_size=video_display_lyric_next_text_size,
        video_display_lyric_played_bold=video_display_lyric_played_bold,
        video_display_lyric_current_bold=video_display_lyric_current_bold,
        video_display_lyric_next_bold=video_display_lyric_next_bold,
        video_display_lyric_played_italic=video_display_lyric_played_italic,
        video_display_lyric_current_italic=video_display_lyric_current_italic,
        video_display_lyric_next_italic=video_display_lyric_next_italic,
        ndi_output_enabled=ndi_output_enabled,
        ndi_output_name=ndi_output_name,
        ndi_output_mode_playing=ndi_output_mode_playing,
        ndi_output_mode_idle=ndi_output_mode_idle,
        ndi_output_resolution_mode=ndi_output_resolution_mode,
        ndi_output_width=ndi_output_width,
        ndi_output_height=ndi_output_height,
        ndi_output_fps=ndi_output_fps,
        ndi_output_audio_enabled=ndi_output_audio_enabled,
        ndi_output_audio_tap_mode=ndi_output_audio_tap_mode,
        ndi_debug_print_enabled=ndi_debug_print_enabled,
        ndi_debug_idle_audio_pacing_enabled=ndi_debug_idle_audio_pacing_enabled,
        ndi_output_group=ndi_output_group,
        ndi_output_discovery_servers=ndi_output_discovery_servers,
        ndi_output_allowed_adapters=ndi_output_allowed_adapters,
        ndi_output_multicast_enabled=ndi_output_multicast_enabled,
        ndi_output_multicast_ttl=ndi_output_multicast_ttl,
        ndi_output_multicast_netmask=ndi_output_multicast_netmask,
        ndi_output_multicast_netprefix=ndi_output_multicast_netprefix,
        window_layout=window_layout,
        window_layout_locked=_get_bool(section, "window_layout_locked", False),
        dock_layout_state=str(section.get("dock_layout_state", "")).strip(),
        dock_dividers=dock_dividers,
        standalone_docks=standalone_docks,
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
