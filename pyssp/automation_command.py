from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


AUTOMATION_SOURCE_TYPE = "automation"
AUTOMATION_UNSUPPORTED_MARKER_TEXT = "Unsupported automation command button. A newer version of pySSP is required."
AUTOMATION_AUTO_RELEASE_IMMEDIATE = "immediate"
AUTOMATION_AUTO_RELEASE_DOWN_ONLY = "down_only"
AUTOMATION_DEFAULT_BUTTON_COLOR = "#E8C67A"
SOUND_BUTTON_AUTOMATION_MODE_SIMPLE = "simple"
SOUND_BUTTON_AUTOMATION_MODE_ADVANCED = "advanced"
SOUND_BUTTON_AUTOMATION_EVENTS = (
    "on_become_playing",
    "on_leave_playing",
    "on_play",
    "on_pause",
    "on_done_play",
    "on_stop",
)
SOUND_BUTTON_AUTOMATION_EVENT_TOKENS = {
    "on_become_playing": "onbecomeplaying",
    "on_leave_playing": "onleaveplaying",
    "on_play": "onplay",
    "on_pause": "onpause",
    "on_done_play": "ondoneplay",
    "on_stop": "onstop",
}
SOUND_BUTTON_AUTOMATION_EVENT_LABELS = {
    "on_become_playing": "When playback starts",
    "on_leave_playing": "When playback stops for any reason",
    "on_play": "On Play",
    "on_pause": "On Pause",
    "on_done_play": "On Done Play",
    "on_stop": "On Stop",
}


@dataclass
class AutomationCommandSpec:
    location: str = ""
    button_text: str = ""
    hold_to_release: bool = False


@dataclass
class SoundButtonAutomationConfig:
    mode: str = SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
    on_become_playing: list[AutomationCommandSpec] | None = None
    on_leave_playing: list[AutomationCommandSpec] | None = None
    on_play: list[AutomationCommandSpec] | None = None
    on_pause: list[AutomationCommandSpec] | None = None
    on_done_play: list[AutomationCommandSpec] | None = None
    on_stop: list[AutomationCommandSpec] | None = None


def normalize_automation_location(raw: object) -> str:
    text = str(raw or "").strip()
    parts = text.split("/")
    if len(parts) != 3:
        return ""
    normalized: list[str] = []
    for part in parts:
        token = str(part or "").strip()
        if not token or (not token.isdigit()):
            return ""
        normalized.append(str(int(token)))
    return "/".join(normalized)


def normalize_automation_spec(raw: object) -> AutomationCommandSpec:
    if isinstance(raw, AutomationCommandSpec):
        return AutomationCommandSpec(
            location=normalize_automation_location(raw.location),
            button_text=str(raw.button_text or "").strip(),
            hold_to_release=bool(raw.hold_to_release),
        )
    data = dict(raw or {})
    return AutomationCommandSpec(
        location=normalize_automation_location(data.get("location", "")),
        button_text=str(data.get("button_text", "") or "").strip(),
        hold_to_release=bool(data.get("hold_to_release", False)),
    )


def automation_spec_to_dict(spec: Optional[AutomationCommandSpec]) -> dict[str, Any]:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    return {
        "location": normalized.location,
        "button_text": normalized.button_text,
        "hold_to_release": bool(normalized.hold_to_release),
    }


def automation_display_name(spec: Optional[AutomationCommandSpec]) -> str:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    return normalized.button_text or normalized.location


def normalize_sound_button_automation_config(raw: object) -> Optional[SoundButtonAutomationConfig]:
    if raw is None:
        return None
    if isinstance(raw, SoundButtonAutomationConfig):
        mode = str(getattr(raw, "mode", "") or "").strip().lower()
        values = {
            event_name: _normalize_optional_press_spec_list(getattr(raw, event_name, None))
            for event_name in SOUND_BUTTON_AUTOMATION_EVENTS
        }
    else:
        data = dict(raw or {})
        mode = str(data.get("mode", "") or "").strip().lower()
        values = {
            event_name: _normalize_optional_press_spec_list(data.get(event_name))
            for event_name in SOUND_BUTTON_AUTOMATION_EVENTS
        }
    if not any(values.values()):
        return None
    if mode == SOUND_BUTTON_AUTOMATION_MODE_SIMPLE:
        if not values.get("on_become_playing") and values.get("on_play"):
            values["on_become_playing"] = list(values["on_play"])
        if not values.get("on_leave_playing"):
            merged_leave: list[AutomationCommandSpec] = []
            for event_name in ("on_pause", "on_done_play", "on_stop"):
                merged_leave.extend(list(values.get(event_name) or []))
            values["on_leave_playing"] = merged_leave or None
    elif mode == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED:
        if not values.get("on_play") and values.get("on_become_playing"):
            values["on_play"] = list(values["on_become_playing"])
        if not values.get("on_stop") and values.get("on_leave_playing"):
            values["on_stop"] = list(values["on_leave_playing"])
    else:
        mode = (
            SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
            if values.get("on_become_playing") or values.get("on_leave_playing")
            else SOUND_BUTTON_AUTOMATION_MODE_ADVANCED
        )
    return SoundButtonAutomationConfig(mode=mode, **values)


def sound_button_automation_config_to_dict(
    config: Optional[SoundButtonAutomationConfig],
) -> dict[str, Any]:
    normalized = normalize_sound_button_automation_config(config)
    payload: dict[str, Any] = {
        "mode": SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
        if normalized is None
        else _normalize_sound_button_automation_mode(normalized.mode)
    }
    for event_name in SOUND_BUTTON_AUTOMATION_EVENTS:
        payload[event_name] = (
            None
            if normalized is None or not getattr(normalized, event_name)
            else [automation_spec_to_dict(spec) for spec in getattr(normalized, event_name)]
        )
    return payload


def sound_button_automation_event_label(event_name: str) -> str:
    token = str(event_name or "").strip().lower()
    return SOUND_BUTTON_AUTOMATION_EVENT_LABELS.get(token, token)


def _normalize_optional_press_spec_list(raw: object) -> Optional[list[AutomationCommandSpec]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        items = list(raw)
    elif isinstance(raw, tuple):
        items = list(raw)
    else:
        items = [raw]
    normalized_items: list[AutomationCommandSpec] = []
    for item in items:
        normalized = normalize_automation_spec(item)
        if not normalized.location:
            continue
        normalized_items.append(
            AutomationCommandSpec(
                location=normalized.location,
                button_text=normalized.button_text,
                hold_to_release=False,
            )
        )
    return normalized_items or None


def _normalize_sound_button_automation_mode(raw: object) -> str:
    token = str(raw or "").strip().lower()
    if token == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED:
        return SOUND_BUTTON_AUTOMATION_MODE_ADVANCED
    return SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
