from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

GROUPS = list("ABCDEFGHIJ")
PAGE_COUNT = 18
SLOTS_PER_PAGE = 48

SECTION_RE = re.compile(r"^Page([A-J]?)(\d+)$", re.IGNORECASE)
CUE_SECTION_RE = re.compile(r"^PageQ(\d+)$", re.IGNORECASE)


@dataclass
class SetSlotData:
    file_path: str = ""
    title: str = ""
    notes: str = ""
    duration_ms: int = 0
    copied_to_cue: bool = False
    custom_color: Optional[str] = None
    played: bool = False
    activity_code: str = ""
    marker: bool = False
    volume_override_pct: Optional[int] = None
    cue_start_ms: Optional[int] = None
    cue_end_ms: Optional[int] = None
    sound_hotkey: str = ""


@dataclass
class SetLoadResult:
    source_path: str
    encoding: str
    pages: Dict[str, List[List[SetSlotData]]]
    page_names: Dict[str, List[str]]
    page_colors: Dict[str, List[Optional[str]]]
    page_playlist_enabled: Dict[str, List[bool]]
    page_shuffle_enabled: Dict[str, List[bool]]
    loaded_slots: int = 0


def load_set_file(file_path: str) -> SetLoadResult:
    text, encoding = _read_text_with_fallback(file_path)

    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read_string(text)

    pages = {
        group: [[SetSlotData() for _ in range(SLOTS_PER_PAGE)] for _ in range(PAGE_COUNT)]
        for group in GROUPS
    }
    page_names = {group: ["" for _ in range(PAGE_COUNT)] for group in GROUPS}
    page_colors = {group: [None for _ in range(PAGE_COUNT)] for group in GROUPS}
    page_playlist_enabled = {group: [False for _ in range(PAGE_COUNT)] for group in GROUPS}
    page_shuffle_enabled = {group: [False for _ in range(PAGE_COUNT)] for group in GROUPS}

    loaded_slots = 0
    for section_name in parser.sections():
        if CUE_SECTION_RE.match(section_name):
            continue

        page_key = _parse_page_section(section_name)
        if page_key is None:
            continue

        group, page_index = page_key
        if not (0 <= page_index < PAGE_COUNT):
            continue

        section = parser[section_name]
        page_names[group][page_index] = section.get("PageName", "").strip()
        page_colors[group][page_index] = parse_delphi_color(section.get("PageColor", "").strip())
        page_playlist_enabled[group][page_index] = section.get("PagePlay", "F").strip().upper() == "T"
        page_shuffle_enabled[group][page_index] = section.get("PageShuffle", "F").strip().upper() == "T"

        for i in range(1, SLOTS_PER_PAGE + 1):
            path = section.get(f"s{i}", "").strip()
            caption = section.get(f"c{i}", "").strip()
            name = section.get(f"n{i}", "").strip()
            title = (name or caption)
            notes = caption
            duration = parse_time_string_to_ms(section.get(f"t{i}", "").strip())
            copied = section.get(f"ci{i}", "").strip().upper() == "Y"
            custom_color = parse_delphi_color(section.get(f"co{i}", "").strip())
            activity_code = section.get(f"activity{i}", "").strip()
            played = _is_played_activity(activity_code)
            volume_override_pct = _parse_volume_pct(section.get(f"v{i}", "").strip())
            cue_start_ms, cue_end_ms = _parse_cue_points(
                section.get(f"cs{i}", "").strip(),
                section.get(f"ce{i}", "").strip(),
                duration,
            )
            sound_hotkey = _parse_sound_hotkey(section.get(f"h{i}", "").strip())
            marker = False

            if caption.endswith("%%"):
                marker = True
                if not name:
                    title = caption[:-2].strip()
                notes = caption[:-2].strip()
            if activity_code == "7":
                marker = True

            if not path and not title and not marker:
                continue

            if not title and path:
                title = os.path.splitext(os.path.basename(path))[0]

            pages[group][page_index][i - 1] = SetSlotData(
                file_path=path,
                title=title,
                notes=notes,
                duration_ms=duration,
                copied_to_cue=copied,
                custom_color=custom_color,
                played=played,
                activity_code=activity_code,
                marker=marker,
                volume_override_pct=volume_override_pct,
                cue_start_ms=cue_start_ms,
                cue_end_ms=cue_end_ms,
                sound_hotkey=sound_hotkey,
            )
            loaded_slots += 1

    return SetLoadResult(
        source_path=file_path,
        encoding=encoding,
        pages=pages,
        page_names=page_names,
        page_colors=page_colors,
        page_playlist_enabled=page_playlist_enabled,
        page_shuffle_enabled=page_shuffle_enabled,
        loaded_slots=loaded_slots,
    )


def _read_text_with_fallback(file_path: str) -> tuple[str, str]:
    raw = open(file_path, "rb").read()
    for encoding in ("utf-8-sig", "utf-16", "gbk", "cp1252", "latin1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1", errors="replace"), "latin1-replace"


def _parse_page_section(name: str) -> Optional[tuple[str, int]]:
    match = SECTION_RE.match(name)
    if not match:
        return None

    group = match.group(1).upper() or "A"
    page_index = int(match.group(2)) - 1
    return group, page_index


def parse_time_string_to_ms(value: str) -> int:
    if not value:
        return 0
    parts = value.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        if minutes.isdigit() and seconds.isdigit():
            return (int(minutes) * 60 + int(seconds)) * 1000
    if len(parts) == 3:
        hours, minutes, seconds = parts
        if hours.isdigit() and minutes.isdigit() and seconds.isdigit():
            return (int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000
    return 0


def parse_delphi_color(value: str) -> Optional[str]:
    if not value:
        return None

    color = value.strip()
    if not color:
        return None

    named = {
        "clBlack": "#000000",
        "clMaroon": "#800000",
        "clGreen": "#008000",
        "clOlive": "#808000",
        "clNavy": "#000080",
        "clPurple": "#800080",
        "clTeal": "#008080",
        "clGray": "#808080",
        "clSilver": "#C0C0C0",
        "clRed": "#FF0000",
        "clLime": "#00FF00",
        "clYellow": "#FFFF00",
        "clBlue": "#0000FF",
        "clFuchsia": "#FF00FF",
        "clAqua": "#00FFFF",
        "clWhite": "#FFFFFF",
        "clBtnFace": None,
    }
    if color in named:
        return named[color]

    if color.startswith("$") and len(color) == 9:
        try:
            value_int = int(color[1:], 16)
        except ValueError:
            return None
        red = value_int & 0xFF
        green = (value_int >> 8) & 0xFF
        blue = (value_int >> 16) & 0xFF
        return f"#{red:02X}{green:02X}{blue:02X}"

    return None


def _is_played_activity(value: str) -> bool:
    # Sports Sounds Pro writes activity codes per slot.
    # In observed .set files, "2" corresponds to a previously played (red) slot.
    return value.strip() == "2"


def _parse_volume_pct(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return max(0, min(100, parsed))


def _parse_cue_points(start_value: str, end_value: str, duration_ms: int) -> tuple[Optional[int], Optional[int]]:
    start_raw = _parse_non_negative_int(start_value)
    end_raw = _parse_non_negative_int(end_value)
    if start_raw is None and end_raw is None:
        return None, None

    start_ms = start_raw
    end_ms = end_raw
    if duration_ms > 0 and end_raw is not None and end_raw > max(duration_ms * 2, 600000):
        scale = duration_ms / float(end_raw)
        if start_raw is not None:
            start_ms = int(round(start_raw * scale))
        end_ms = duration_ms

    if start_ms is not None:
        start_ms = max(0, start_ms)
    if end_ms is not None:
        end_ms = max(0, end_ms)

    if duration_ms > 0:
        if start_ms is not None:
            start_ms = min(duration_ms, start_ms)
        if end_ms is not None:
            end_ms = min(duration_ms, end_ms)

    if start_ms is not None and end_ms is not None and end_ms < start_ms:
        end_ms = start_ms
    return start_ms, end_ms


def _parse_non_negative_int(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    if parsed < 0:
        return None
    return parsed


def _parse_sound_hotkey(value: str) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    if raw.startswith("0"):
        raw = raw[1:]
    if re.fullmatch(r"F([1-9]|1[1-2])", raw):
        if raw == "F10":
            return ""
        return raw
    if re.fullmatch(r"[0-9]", raw):
        return raw
    if re.fullmatch(r"[A-OQ-Z]", raw):
        return raw
    return ""
