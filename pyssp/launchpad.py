from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional, Sequence, Tuple

from pyssp.midi_control import normalize_midi_binding


LAUNCHPAD_PROFILE_PROGRAMMER = "programmer"
LAUNCHPAD_LAYOUT_BOTTOM_SIX = "bottom_six"
LAUNCHPAD_LAYOUT_TOP_SIX = "top_six"
LAUNCHPAD_MODE_PROGRAMMER = 1
LAUNCHPAD_MODE_LIVE = 0

_NOVATION_SYSEX_HEADER = bytes([0xF0, 0x00, 0x20, 0x29, 0x02])
_NOVATION_SYSEX_END = bytes([0xF7])
_LAUNCHPAD_DEVICE_ID_X = 0x0C
_LAUNCHPAD_DEVICE_ID_MINI_MK3 = 0x0D
LAUNCHPAD_ACTION_NONE = ""
LAUNCHPAD_ACTION_SHIFT_LAYER = "shift_layer"
LAUNCHPAD_SLOT_PAD_COUNT = 48
LAUNCHPAD_CONTROL_PAD_COUNT = 16
LAUNCHPAD_SHIFT_CONTROL_INDEX = 8


@dataclass(frozen=True)
class LaunchpadLayoutOption:
    key: str
    label: str


@dataclass(frozen=True)
class LaunchpadActionOption:
    key: str
    label: str


def launchpad_layout_options() -> List[LaunchpadLayoutOption]:
    return [
        LaunchpadLayoutOption(LAUNCHPAD_LAYOUT_BOTTOM_SIX, "Bottom 6 rows"),
        LaunchpadLayoutOption(LAUNCHPAD_LAYOUT_TOP_SIX, "Top 6 rows"),
    ]


def launchpad_profile_label(profile: str) -> str:
    if str(profile or "").strip().lower() == LAUNCHPAD_PROFILE_PROGRAMMER:
        return "Launchpad Programmer Mode"
    return "Launchpad"


def normalize_launchpad_profile(profile: str) -> str:
    token = str(profile or "").strip().lower()
    if token == LAUNCHPAD_PROFILE_PROGRAMMER:
        return token
    return LAUNCHPAD_PROFILE_PROGRAMMER


def normalize_launchpad_layout(layout: str) -> str:
    token = str(layout or "").strip().lower()
    if token in {LAUNCHPAD_LAYOUT_BOTTOM_SIX, LAUNCHPAD_LAYOUT_TOP_SIX}:
        return token
    return LAUNCHPAD_LAYOUT_BOTTOM_SIX


def launchpad_programmer_note(top_row: int, left_col: int) -> int:
    row = int(top_row)
    col = int(left_col)
    if row < 0 or row >= 8:
        raise ValueError(f"Launchpad row out of range: {row}")
    if col < 0 or col >= 8:
        raise ValueError(f"Launchpad column out of range: {col}")
    return ((8 - row) * 10) + (col + 1)


def launchpad_page_slot_note(slot_index: int, layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX) -> int:
    index = int(slot_index)
    if index < 0 or index >= LAUNCHPAD_SLOT_PAD_COUNT:
        raise ValueError(f"pySSP slot out of range: {index}")
    normalized_layout = normalize_launchpad_layout(layout)
    slot_row = index // 8
    slot_col = index % 8
    row_offset = 2 if normalized_layout == LAUNCHPAD_LAYOUT_BOTTOM_SIX else 0
    return launchpad_programmer_note(row_offset + slot_row, slot_col)


def launchpad_control_note(control_index: int, layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX) -> int:
    index = int(control_index)
    if index < 0 or index >= LAUNCHPAD_CONTROL_PAD_COUNT:
        raise ValueError(f"Launchpad control pad out of range: {index}")
    normalized_layout = normalize_launchpad_layout(layout)
    control_row = index // 8
    control_col = index % 8
    row_offset = 0 if normalized_layout == LAUNCHPAD_LAYOUT_BOTTOM_SIX else 6
    return launchpad_programmer_note(row_offset + control_row, control_col)


def launchpad_page_slot_binding(
    slot_index: int,
    layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX,
    profile: str = LAUNCHPAD_PROFILE_PROGRAMMER,
    channel: int = 1,
    selector: str = "",
) -> str:
    normalized_profile = normalize_launchpad_profile(profile)
    if normalized_profile != LAUNCHPAD_PROFILE_PROGRAMMER:
        raise ValueError(f"Unsupported Launchpad profile: {profile}")
    midi_channel = max(1, min(16, int(channel)))
    status = 0x90 + (midi_channel - 1)
    note = launchpad_page_slot_note(slot_index, layout=layout)
    base = f"{status:02X}:{note:02X}"
    if str(selector or "").strip():
        return normalize_midi_binding(f"{selector}|{base}")
    return normalize_midi_binding(base)


def launchpad_page_bindings(
    layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX,
    profile: str = LAUNCHPAD_PROFILE_PROGRAMMER,
    channel: int = 1,
    selector: str = "",
) -> List[str]:
    return [
        launchpad_page_slot_binding(
            slot_index=i,
            layout=layout,
            profile=profile,
            channel=channel,
            selector=selector,
        )
        for i in range(LAUNCHPAD_SLOT_PAD_COUNT)
    ]


def launchpad_control_binding(
    control_index: int,
    layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX,
    profile: str = LAUNCHPAD_PROFILE_PROGRAMMER,
    channel: int = 1,
    selector: str = "",
) -> str:
    normalized_profile = normalize_launchpad_profile(profile)
    if normalized_profile != LAUNCHPAD_PROFILE_PROGRAMMER:
        raise ValueError(f"Unsupported Launchpad profile: {profile}")
    midi_channel = max(1, min(16, int(channel)))
    status = 0x90 + (midi_channel - 1)
    note = launchpad_control_note(control_index, layout=layout)
    base = f"{status:02X}:{note:02X}"
    if str(selector or "").strip():
        return normalize_midi_binding(f"{selector}|{base}")
    return normalize_midi_binding(base)


def launchpad_control_bindings(
    layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX,
    profile: str = LAUNCHPAD_PROFILE_PROGRAMMER,
    channel: int = 1,
    selector: str = "",
) -> List[str]:
    return [
        launchpad_control_binding(
            control_index=i,
            layout=layout,
            profile=profile,
            channel=channel,
            selector=selector,
        )
        for i in range(LAUNCHPAD_CONTROL_PAD_COUNT)
    ]


def is_launchpad_name(device_name: str) -> bool:
    token = str(device_name or "").strip().lower()
    return ("launchpad" in token) or ("lpx" in token) or ("lpm" in token)


def normalize_launchpad_device_key(device_name: str) -> str:
    token = str(device_name or "").strip().lower()
    if not token:
        return ""
    token = re.sub(r"\b(midi|daw|in|out|input|output|port|usb)\b", " ", token)
    token = re.sub(r"[^a-z0-9]+", " ", token)
    token = " ".join(part for part in token.split() if part)
    return token


def launchpad_device_family_id(device_name: str) -> Optional[int]:
    token = normalize_launchpad_device_key(device_name)
    if not token:
        return None
    if ("launchpad x" in token) or ("lpx" in token):
        return _LAUNCHPAD_DEVICE_ID_X
    if ("launchpad mini" in token) or ("lpm" in token):
        return _LAUNCHPAD_DEVICE_ID_MINI_MK3
    return None


def launchpad_programmer_toggle_sysex(device_name: str, enabled: bool = True) -> bytes:
    family_id = launchpad_device_family_id(device_name)
    if family_id is None:
        return b""
    mode = LAUNCHPAD_MODE_PROGRAMMER if enabled else LAUNCHPAD_MODE_LIVE
    return bytes([*_NOVATION_SYSEX_HEADER, family_id, 0x0E, mode, *_NOVATION_SYSEX_END])


def launchpad_find_matching_output(
    input_device_name: str,
    output_devices: Sequence[Tuple[str, str]],
) -> Tuple[str, str]:
    input_name = str(input_device_name or "").strip()
    if not input_name:
        return "", ""
    input_key = normalize_launchpad_device_key(input_name)
    best_match: Tuple[str, str] = ("", "")
    best_score = -1
    for device_id, device_name in output_devices:
        output_name = str(device_name or "").strip()
        if not is_launchpad_name(output_name):
            continue
        score = 0
        output_key = normalize_launchpad_device_key(output_name)
        if output_name.lower() == input_name.lower():
            score += 100
        if input_key and output_key:
            if output_key == input_key:
                score += 80
            elif input_key in output_key or output_key in input_key:
                score += 50
            input_parts = set(input_key.split())
            output_parts = set(output_key.split())
            score += len(input_parts & output_parts) * 5
        if "daw" not in output_name.lower():
            score += 3
        if score > best_score:
            best_match = (str(device_id), output_name)
            best_score = score
    return best_match


def launchpad_slot_action_key(slot_index: int) -> str:
    index = max(0, min(LAUNCHPAD_SLOT_PAD_COUNT - 1, int(slot_index)))
    return f"slot:{index}"


def launchpad_action_slot_index(action_key: str) -> Optional[int]:
    raw = str(action_key or "").strip().lower()
    if not raw.startswith("slot:"):
        return None
    try:
        value = int(raw.split(":", 1)[1])
    except Exception:
        return None
    if 0 <= value < LAUNCHPAD_SLOT_PAD_COUNT:
        return value
    return None


def build_launchpad_action_options(action_rows: Sequence[Tuple[str, str]]) -> List[LaunchpadActionOption]:
    options: List[LaunchpadActionOption] = [LaunchpadActionOption(LAUNCHPAD_ACTION_NONE, "(None)")]
    for key, label in action_rows:
        options.append(LaunchpadActionOption(str(key), str(label)))
    return options


def normalize_launchpad_action_bindings(values: Sequence[str]) -> List[str]:
    output = [str(value or "").strip() for value in list(values or [])[:LAUNCHPAD_CONTROL_PAD_COUNT]]
    if len(output) < LAUNCHPAD_CONTROL_PAD_COUNT:
        output.extend(["" for _ in range(LAUNCHPAD_CONTROL_PAD_COUNT - len(output))])
    return output


def launchpad_rgb_color(color_hex: str) -> Tuple[int, int, int]:
    raw = str(color_hex or "").strip()
    if len(raw) != 7 or not raw.startswith("#"):
        return (0, 0, 0)
    try:
        red = int(raw[1:3], 16)
        green = int(raw[3:5], 16)
        blue = int(raw[5:7], 16)
    except ValueError:
        return (0, 0, 0)
    return (int(round((red / 255.0) * 127.0)), int(round((green / 255.0) * 127.0)), int(round((blue / 255.0) * 127.0)))


def launchpad_led_rgb_sysex(device_name: str, led_colors: Sequence[Tuple[int, str]]) -> bytes:
    family_id = launchpad_device_family_id(device_name)
    if family_id is None:
        return b""
    payload = bytearray([*_NOVATION_SYSEX_HEADER, family_id, 0x03])
    for led_index, color_hex in led_colors:
        red, green, blue = launchpad_rgb_color(color_hex)
        payload.extend([0x03, int(led_index) & 0x7F, red & 0x7F, green & 0x7F, blue & 0x7F])
    payload.extend(_NOVATION_SYSEX_END)
    return bytes(payload)
