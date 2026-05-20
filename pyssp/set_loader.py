from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from pyssp.automation_command import (
    AUTOMATION_SOURCE_TYPE,
    AutomationCommandSpec,
    AUTOMATION_UNSUPPORTED_MARKER_TEXT,
    SOUND_BUTTON_AUTOMATION_EVENTS,
    SOUND_BUTTON_AUTOMATION_EVENT_TOKENS,
    SoundButtonAutomationConfig,
    automation_display_name,
    automation_spec_from_set_fields,
    normalize_automation_spec,
    normalize_sound_button_automation_config,
)
from pyssp.midi_control import normalize_midi_binding
from pyssp.utility_audio import (
    FILE_SOURCE_TYPE,
    UTILITY_SOURCE_TYPE,
    UTILITY_COMPAT_DURATION_MS,
    UTILITY_UNSUPPORTED_MARKER_TEXT,
    UtilitySoundSpec,
    normalize_utility_spec,
    parse_utility_duration_hhmmssmmm,
)

GROUPS = list("ABCDEFGHIJ")
PAGE_COUNT = 18
SLOTS_PER_PAGE = 48

SECTION_RE = re.compile(r"^Page([A-J]?)(\d+)$", re.IGNORECASE)
CUE_SECTION_RE = re.compile(r"^PageQ(\d+)$", re.IGNORECASE)


@dataclass
class SetSlotData:
    source_type: str = FILE_SOURCE_TYPE
    file_path: str = ""
    disable_video_loading: bool = False
    vocal_removed_file: str = ""
    title: str = ""
    notes: str = ""
    lyric_file: str = ""
    automation_script_path: str = ""
    duration_ms: int = 0
    automation_spec: Optional[AutomationCommandSpec] = None
    sound_button_automation: Optional[SoundButtonAutomationConfig] = None
    automation_script_bypassed: bool = False
    utility_spec: Optional[UtilitySoundSpec] = None
    copied_to_cue: bool = False
    custom_color: Optional[str] = None
    played: bool = False
    activity_code: str = ""
    marker: bool = False
    volume_override_pct: Optional[int] = None
    cue_start_ms: Optional[int] = None
    cue_end_ms: Optional[int] = None
    timecode_offset_ms: Optional[int] = None
    timecode_timeline_mode: str = "global"
    sound_hotkey: str = ""
    sound_midi_hotkey: str = ""


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
    migrated_legacy_cues: bool = False


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
    migrated_legacy_cues = False
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

        slot_count_raw = str(section.get("pysspslotcount", "")).strip()
        try:
            slot_count = max(1, int(slot_count_raw)) if slot_count_raw else SLOTS_PER_PAGE
        except ValueError:
            slot_count = SLOTS_PER_PAGE
        pages[group][page_index] = [SetSlotData() for _ in range(slot_count)]
        for i in range(1, slot_count + 1):
            automation_slot = _parse_automation_slot_from_section(section, i)
            if automation_slot is not None:
                pages[group][page_index][i - 1] = automation_slot
                loaded_slots += 1
                continue
            utility_slot = _parse_utility_slot_from_section(section, i)
            if utility_slot is not None:
                pages[group][page_index][i - 1] = utility_slot
                loaded_slots += 1
                continue
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
            vocal_removed_file = _normalize_set_path_string(section.get(f"pysspvocalremoval{i}", "").strip())
            cue_start_ms, cue_end_ms, migrated_slot_cue = _parse_cue_points_from_section(section, i, duration)
            migrated_legacy_cues = migrated_legacy_cues or migrated_slot_cue
            sound_hotkey = _parse_sound_hotkey(section.get(f"h{i}", "").strip())
            sound_midi_hotkey = _parse_sound_midi_hotkey(section.get(f"pysspmidi{i}", "").strip())
            lyric_file = _normalize_set_path_string(section.get(f"pyssplyric{i}", "").strip())
            automation_script_path = _normalize_set_path_string(section.get(f"pysspautoscript{i}", "").strip())
            timecode_offset_ms = _parse_timecode_offset_ms(
                section.get(f"pyssptimecodeoffset{i}", "").strip()
            )
            timecode_timeline_mode = _parse_slot_timecode_timeline_mode(
                section.get(f"pyssptimecodedisplaytimeline{i}", "").strip()
            )
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
                source_type=FILE_SOURCE_TYPE,
                file_path=path,
                disable_video_loading=str(section.get(f"pysspdisablevideo{i}", "0")).strip() in {"1", "true", "True"},
                vocal_removed_file=vocal_removed_file,
                title=title,
                notes=notes,
                lyric_file=lyric_file,
                automation_script_path=automation_script_path,
                duration_ms=duration,
                automation_spec=None,
                sound_button_automation=_parse_sound_button_automation_from_section(section, i),
                automation_script_bypassed=str(section.get(f"pysspautoscriptbypass{i}", "0")).strip() in {"1", "true", "True"},
                utility_spec=None,
                copied_to_cue=copied,
                custom_color=custom_color,
                played=played,
                activity_code=activity_code,
                marker=marker,
                volume_override_pct=volume_override_pct,
                cue_start_ms=cue_start_ms,
                cue_end_ms=cue_end_ms,
                timecode_offset_ms=timecode_offset_ms,
                timecode_timeline_mode=timecode_timeline_mode,
                sound_hotkey=sound_hotkey,
                sound_midi_hotkey=sound_midi_hotkey,
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
        migrated_legacy_cues=migrated_legacy_cues,
    )


def _read_text_with_fallback(file_path: str) -> tuple[str, str]:
    raw = open(file_path, "rb").read()
    for encoding in ("utf-8-sig", "utf-16", "gbk", "cp1252", "latin1"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("latin1", errors="replace"), "latin1-replace"


def _normalize_set_path_string(value: str) -> str:
    text = str(value or "").strip()
    if re.match(r"^[A-Za-z]:\\\\", text):
        return text.replace("\\\\", "\\")
    if text.startswith("\\\\\\\\"):
        return text.replace("\\\\", "\\")
    return text


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


def _parse_utility_slot_from_section(
    section: configparser.SectionProxy,
    slot_index: int,
) -> Optional[SetSlotData]:
    source_type = str(section.get(f"pysspsourcetype{slot_index}", "")).strip().lower()
    if source_type != UTILITY_SOURCE_TYPE:
        return None
    duration_ms = parse_utility_duration_hhmmssmmm(section.get(f"pyssputilityduration{slot_index}", "").strip())
    infinite = str(section.get(f"pyssputilityinfinite{slot_index}", "0")).strip() in {"1", "true", "True"}
    spec = normalize_utility_spec(
        {
            "mode": section.get(f"pyssputilitymode{slot_index}", "").strip(),
            "duration_ms": (
                UTILITY_COMPAT_DURATION_MS if duration_ms is None and infinite else (1000 if duration_ms is None else duration_ms)
            ),
            "infinite": infinite,
            "waveform_type": section.get(f"pyssputilitywaveform{slot_index}", "").strip(),
            "frequency_hz": section.get(f"pyssputilityfreq{slot_index}", "").strip(),
            "tempo_bpm": section.get(f"pyssputilitytempo{slot_index}", "").strip(),
            "time_signature_num": _parse_time_signature_part(
                section.get(f"pyssputilitytimesig{slot_index}", "").strip(), 0
            ),
            "time_signature_den": _parse_time_signature_part(
                section.get(f"pyssputilitytimesig{slot_index}", "").strip(), 1
            ),
        }
    )
    title = _normalize_set_path_string(section.get(f"pyssputilitytitle{slot_index}", "").strip())
    notes = _normalize_set_path_string(section.get(f"pyssputilitynotes{slot_index}", "").strip())
    lyric_file = _normalize_set_path_string(
        section.get(f"pyssputilitylyric{slot_index}", "").strip()
        or section.get(f"pyssplyric{slot_index}", "").strip()
    )
    automation_script_path = _normalize_set_path_string(
        section.get(f"pysspautoscript{slot_index}", "").strip()
        or section.get(f"pyssputilityautoscript{slot_index}", "").strip()
    )
    activity_code = section.get(f"activity{slot_index}", "").strip()
    played = str(section.get(f"pyssputilityplayed{slot_index}", "0")).strip() in {"1", "true", "True"}
    cue_start_ms, cue_end_ms, migrated_slot_cue = _parse_cue_points_from_section(
        section,
        slot_index,
        spec.duration_ms,
    )
    _ = migrated_slot_cue
    return SetSlotData(
        source_type=UTILITY_SOURCE_TYPE,
        file_path="",
        vocal_removed_file="",
        title=title or UTILITY_UNSUPPORTED_MARKER_TEXT,
        notes=notes,
        lyric_file=lyric_file,
        automation_script_path=automation_script_path,
        duration_ms=spec.duration_ms,
        automation_spec=None,
        sound_button_automation=_parse_sound_button_automation_from_section(section, slot_index),
        automation_script_bypassed=str(section.get(f"pysspautoscriptbypass{slot_index}", "0")).strip() in {"1", "true", "True"},
        utility_spec=spec,
        copied_to_cue=section.get(f"ci{slot_index}", "").strip().upper() == "Y",
        custom_color=parse_delphi_color(section.get(f"co{slot_index}", "").strip()),
        played=played,
        activity_code=activity_code or ("2" if played else "8"),
        marker=False,
        volume_override_pct=_parse_volume_pct(section.get(f"v{slot_index}", "").strip()),
        cue_start_ms=cue_start_ms,
        cue_end_ms=cue_end_ms,
        timecode_offset_ms=_parse_timecode_offset_ms(section.get(f"pyssptimecodeoffset{slot_index}", "").strip()),
        timecode_timeline_mode=_parse_slot_timecode_timeline_mode(
            section.get(f"pyssptimecodedisplaytimeline{slot_index}", "").strip()
        ),
        sound_hotkey=_parse_sound_hotkey(section.get(f"h{slot_index}", "").strip()),
        sound_midi_hotkey=_parse_sound_midi_hotkey(section.get(f"pysspmidi{slot_index}", "").strip()),
    )


def _parse_automation_slot_from_section(
    section: configparser.SectionProxy,
    slot_index: int,
) -> Optional[SetSlotData]:
    source_type = str(section.get(f"pysspsourcetype{slot_index}", "")).strip().lower()
    if source_type != AUTOMATION_SOURCE_TYPE:
        return None
    spec = automation_spec_from_set_fields(
        source=section.get(f"pysspautomationsource{slot_index}", "").strip(),
        location=section.get(f"pysspautomationlocation{slot_index}", "").strip(),
        button_text=section.get(f"pysspautomationtext{slot_index}", "").strip(),
        hold_to_release=str(section.get(f"pysspautomationhold{slot_index}", "0")).strip() in {"1", "true", "True"},
        internal_command=section.get(f"pysspautomationinternalcommand{slot_index}", "").strip(),
        internal_params_json=section.get(f"pysspautomationinternalparams{slot_index}", "").strip(),
    )
    title = _normalize_set_path_string(section.get(f"pysspautomationtitle{slot_index}", "").strip())
    notes = _normalize_set_path_string(section.get(f"pysspautomationnotes{slot_index}", "").strip())
    custom_color = parse_delphi_color(section.get(f"pysspautomationcolor{slot_index}", "").strip())
    activity_code = section.get(f"activity{slot_index}", "").strip()
    played = str(section.get(f"pysspautomationplayed{slot_index}", "0")).strip() in {"1", "true", "True"}
    return SetSlotData(
        source_type=AUTOMATION_SOURCE_TYPE,
        file_path="",
        vocal_removed_file="",
        title=title or automation_display_name(spec) or AUTOMATION_UNSUPPORTED_MARKER_TEXT,
        notes=notes,
        lyric_file="",
        automation_script_path="",
        duration_ms=0,
        automation_spec=spec,
        sound_button_automation=None,
        automation_script_bypassed=False,
        utility_spec=None,
        copied_to_cue=section.get(f"ci{slot_index}", "").strip().upper() == "Y",
        custom_color=custom_color,
        played=played,
        activity_code=activity_code or ("2" if played else "8"),
        marker=False,
        volume_override_pct=None,
        cue_start_ms=None,
        cue_end_ms=None,
        timecode_offset_ms=None,
        timecode_timeline_mode="global",
        sound_hotkey=_parse_sound_hotkey(section.get(f"pysspautomationhotkey{slot_index}", "").strip()),
        sound_midi_hotkey=_parse_sound_midi_hotkey(section.get(f"pysspautomationmidi{slot_index}", "").strip()),
    )


def _parse_time_signature_part(value: str, index: int) -> int:
    parts = [part.strip() for part in str(value or "").strip().split("/", 1)]
    if len(parts) != 2:
        return 0
    try:
        return int(parts[index])
    except Exception:
        return 0


def _parse_sound_button_automation_from_section(
    section: configparser.SectionProxy,
    slot_index: int,
) -> Optional[SoundButtonAutomationConfig]:
    data: dict[str, object] = {
        "mode": str(section.get(f"pysspsbamode{slot_index}", "") or "").strip().lower(),
        "bypassed": str(section.get(f"pysspsbabypass{slot_index}", "0") or "").strip() in {"1", "true", "True"},
    }
    for event_name in SOUND_BUTTON_AUTOMATION_EVENTS:
        token = SOUND_BUTTON_AUTOMATION_EVENT_TOKENS[event_name]
        count_raw = str(section.get(f"pyssp{token}count{slot_index}", "") or "").strip()
        try:
            count = max(0, int(count_raw))
        except Exception:
            count = 0
        items: list[dict[str, object]] = []
        for command_index in range(1, count + 1):
            spec = automation_spec_from_set_fields(
                source=section.get(f"pyssp{token}source{slot_index}_{command_index}", "").strip(),
                location=section.get(f"pyssp{token}location{slot_index}_{command_index}", "").strip(),
                button_text=section.get(f"pyssp{token}text{slot_index}_{command_index}", "").strip(),
                hold_to_release=False,
                internal_command=section.get(f"pyssp{token}internalcommand{slot_index}_{command_index}", "").strip(),
                internal_params_json=section.get(f"pyssp{token}internalparams{slot_index}_{command_index}", "").strip(),
            )
            normalized_spec = normalize_automation_spec(spec)
            if not (normalized_spec.location or normalized_spec.internal_command):
                continue
            items.append(normalized_spec)
        data[event_name] = items
    return normalize_sound_button_automation_config(data)


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
    fallback_units_per_ms = 176.4
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
    elif duration_ms > 0 and end_raw is None and start_raw is not None and start_raw > duration_ms:
        # Some sets store cue starts as SSP units even when ce* is missing.
        # If cs* exceeds media duration, attempt units->ms conversion.
        inferred_start_ms = int(round(start_raw / fallback_units_per_ms))
        if 0 <= inferred_start_ms <= duration_ms:
            start_ms = inferred_start_ms

    return _normalize_cue_points(start_ms, end_ms, duration_ms)


def _parse_cue_points_from_section(
    section: configparser.SectionProxy, slot_index: int, duration_ms: int
) -> tuple[Optional[int], Optional[int], bool]:
    start_time_value = section.get(f"pysspcuestart{slot_index}", "").strip()
    end_time_value = section.get(f"pysspcueend{slot_index}", "").strip()
    if start_time_value or end_time_value:
        start_ms = _parse_cue_time_string_to_ms(start_time_value)
        end_ms = _parse_cue_time_string_to_ms(end_time_value)
        start_ms, end_ms = _normalize_cue_points(start_ms, end_ms, duration_ms)
        return start_ms, end_ms, False

    start_ms, end_ms = _parse_cue_points(
        section.get(f"cs{slot_index}", "").strip(),
        section.get(f"ce{slot_index}", "").strip(),
        duration_ms,
    )
    return start_ms, end_ms, (start_ms is not None or end_ms is not None)


def _normalize_cue_points(
    start_ms: Optional[int], end_ms: Optional[int], duration_ms: int
) -> tuple[Optional[int], Optional[int]]:
    if start_ms is not None:
        start_ms = max(0, int(start_ms))
    if end_ms is not None:
        end_ms = max(0, int(end_ms))

    if duration_ms > 0:
        if start_ms is not None:
            start_ms = min(duration_ms, start_ms)
        if end_ms is not None:
            end_ms = min(duration_ms, end_ms)

    if start_ms is not None and end_ms is not None and end_ms < start_ms:
        end_ms = start_ms
    return start_ms, end_ms


def _parse_cue_time_string_to_ms(value: str) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) == 2:
        mm, ss = parts
        if mm.isdigit() and ss.isdigit():
            return (int(mm) * 60 + int(ss)) * 1000
        return None
    if len(parts) == 3:
        first, second, third = parts
        if not (first.isdigit() and second.isdigit() and third.isdigit()):
            return None
        minutes = int(first)
        seconds = int(second)
        frames_or_seconds = int(third)
        # Prefer mm:ss:ff at 30 fps for pyssp cue fields, then fall back to hh:mm:ss.
        if frames_or_seconds < 30:
            return ((minutes * 60) + seconds) * 1000 + int((frames_or_seconds / 30.0) * 1000)
        return (minutes * 3600 + seconds * 60 + frames_or_seconds) * 1000
    return None


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


def _parse_sound_midi_hotkey(value: str) -> str:
    return normalize_midi_binding(value)


def parse_timecode_offset_ms(value: str) -> Optional[int]:
    return _parse_timecode_offset_ms(value)


def format_timecode_offset_hhmmss(seconds: Optional[int], fps: float = 30.0) -> Optional[str]:
    if seconds is None:
        return None
    total_ms = max(0, int(seconds))
    if total_ms <= 0:
        return None
    safe_fps = max(1.0, float(fps))
    total_seconds = total_ms // 1000
    rem_ms = total_ms % 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    frames = int(round((rem_ms / 1000.0) * safe_fps))
    fps_int = max(1, int(round(safe_fps)))
    if frames >= fps_int:
        frames = 0
        secs += 1
        if secs >= 60:
            secs = 0
            minutes += 1
            if minutes >= 60:
                minutes = 0
                hours += 1
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


def normalize_slot_timecode_timeline_mode(value: str) -> str:
    return _parse_slot_timecode_timeline_mode(value)


def _parse_timecode_offset_ms(value: str) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) not in {3, 4}:
        return None
    if not all(part.isdigit() for part in parts):
        return None
    hh, mm, ss = (int(parts[0]), int(parts[1]), int(parts[2]))
    ff = int(parts[3]) if len(parts) == 4 else 0
    if mm > 59 or ss > 59 or ff < 0 or ff > 59:
        return None
    # Use 30fps to keep compatibility with pySSP cue/timecode style fields.
    total_ms = ((hh * 3600) + (mm * 60) + ss) * 1000
    total_ms += int((ff / 30.0) * 1000)
    return total_ms if total_ms > 0 else None


def _parse_slot_timecode_timeline_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    if mode in {"audio_file", "cue_region"}:
        return mode
    return "global"
