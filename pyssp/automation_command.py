from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from pyssp.internal_automation import (
    internal_automation_command_summary,
    normalize_internal_automation_command_id,
    normalize_internal_automation_params,
)


AUTOMATION_SOURCE_TYPE = "automation"
AUTOMATION_COMMAND_SOURCE_COMPANION = "companion"
AUTOMATION_COMMAND_SOURCE_INTERNAL = "internal"
AUTOMATION_UNSUPPORTED_MARKER_TEXT = "Unsupported automation command button. A newer version of pySSP is required."
AUTOMATION_AUTO_RELEASE_IMMEDIATE = "immediate"
AUTOMATION_AUTO_RELEASE_DOWN_ONLY = "down_only"
AUTOMATION_DEFAULT_BUTTON_COLOR = "#E8C67A"
SOUND_BUTTON_AUTOMATION_MODE_SIMPLE = "simple"
SOUND_BUTTON_AUTOMATION_MODE_ADVANCED = "advanced"
SOUND_BUTTON_AUTOMATION_EVENTS = (
    "on_become_playing",
    "on_leave_playing",
    "on_trigger",
    "on_play",
    "on_fade_in_start",
    "on_fade_in_end",
    "on_pause_requested",
    "on_pause",
    "on_resume_requested",
    "on_resume_complete",
    "on_pause_fade_out_start",
    "on_pause_fade_out_end",
    "on_resume_fade_in_start",
    "on_resume_fade_in_end",
    "on_done_play",
    "on_end_fade_out_start",
    "on_end_fade_out_end",
    "on_stop_requested",
    "on_force_stop",
    "on_stop",
    "on_stop_fade_out_start",
    "on_stop_fade_out_end",
    "on_interrupted_by_sound_button",
    "on_interrupted_by_playback_control",
    "on_interrupted_by_app_reset",
)
SOUND_BUTTON_AUTOMATION_SIMPLE_EVENTS = (
    "on_become_playing",
    "on_leave_playing",
    "on_pause",
    "on_resume_complete",
)
SOUND_BUTTON_AUTOMATION_EVENT_TOKENS = {
    "on_become_playing": "onbecomeplaying",
    "on_leave_playing": "onleaveplaying",
    "on_trigger": "ontrigger",
    "on_play": "onplay",
    "on_fade_in_start": "onfadeinstart",
    "on_fade_in_end": "onfadeinend",
    "on_pause_requested": "onpauserequested",
    "on_pause": "onpause",
    "on_resume_requested": "onresumerequested",
    "on_resume_complete": "onresumecomplete",
    "on_pause_fade_out_start": "onpausefadeoutstart",
    "on_pause_fade_out_end": "onpausefadeoutend",
    "on_resume_fade_in_start": "onresumefadeinstart",
    "on_resume_fade_in_end": "onresumefadeinend",
    "on_done_play": "ondoneplay",
    "on_end_fade_out_start": "onendfadeoutstart",
    "on_end_fade_out_end": "onendfadeoutend",
    "on_stop_requested": "onstoprequested",
    "on_force_stop": "onforcestop",
    "on_stop": "onstop",
    "on_stop_fade_out_start": "onstopfadeoutstart",
    "on_stop_fade_out_end": "onstopfadeoutend",
    "on_interrupted_by_sound_button": "oninterruptedbysoundbutton",
    "on_interrupted_by_playback_control": "oninterruptedbyplaybackcontrol",
    "on_interrupted_by_app_reset": "oninterruptedbyappreset",
}
SOUND_BUTTON_AUTOMATION_EVENT_LABELS = {
    "on_become_playing": "When playback starts",
    "on_leave_playing": "When playback stops for any reason except pause",
    "on_trigger": "On Trigger",
    "on_play": "On Playback Start",
    "on_fade_in_start": "On Fade In Start",
    "on_fade_in_end": "On Fade In End",
    "on_pause_requested": "On Pause Requested",
    "on_pause": "On Pause Complete",
    "on_resume_requested": "On Resume Requested",
    "on_resume_complete": "On Resume Complete",
    "on_pause_fade_out_start": "On Pause Fade Out Start",
    "on_pause_fade_out_end": "On Pause Fade Out End",
    "on_resume_fade_in_start": "On Resume Fade In Start",
    "on_resume_fade_in_end": "On Resume Fade In End",
    "on_done_play": "On Done Play",
    "on_end_fade_out_start": "On End Fade Out Start",
    "on_end_fade_out_end": "On End Fade Out End",
    "on_stop_requested": "On Stop Requested",
    "on_force_stop": "On Force Stop",
    "on_stop": "On Stop Complete",
    "on_stop_fade_out_start": "On Stop Fade Out Start",
    "on_stop_fade_out_end": "On Stop Fade Out End",
    "on_interrupted_by_sound_button": "On Interrupted By Another Sound Button",
    "on_interrupted_by_playback_control": "On Interrupted By Playback Control",
    "on_interrupted_by_app_reset": "On Interrupted By App Reset / Set Load / Hard Stop",
}


@dataclass
class AutomationCommandSpec:
    source: str = AUTOMATION_COMMAND_SOURCE_COMPANION
    location: str = ""
    button_text: str = ""
    hold_to_release: bool = False
    internal_command: str = ""
    internal_params: dict[str, Any] | None = None


@dataclass
class SoundButtonAutomationConfig:
    mode: str = SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
    bypassed: bool = False
    on_become_playing: list[AutomationCommandSpec] | None = None
    on_leave_playing: list[AutomationCommandSpec] | None = None
    on_trigger: list[AutomationCommandSpec] | None = None
    on_play: list[AutomationCommandSpec] | None = None
    on_fade_in_start: list[AutomationCommandSpec] | None = None
    on_fade_in_end: list[AutomationCommandSpec] | None = None
    on_pause_requested: list[AutomationCommandSpec] | None = None
    on_pause: list[AutomationCommandSpec] | None = None
    on_resume_requested: list[AutomationCommandSpec] | None = None
    on_resume_complete: list[AutomationCommandSpec] | None = None
    on_pause_fade_out_start: list[AutomationCommandSpec] | None = None
    on_pause_fade_out_end: list[AutomationCommandSpec] | None = None
    on_resume_fade_in_start: list[AutomationCommandSpec] | None = None
    on_resume_fade_in_end: list[AutomationCommandSpec] | None = None
    on_done_play: list[AutomationCommandSpec] | None = None
    on_end_fade_out_start: list[AutomationCommandSpec] | None = None
    on_end_fade_out_end: list[AutomationCommandSpec] | None = None
    on_stop_requested: list[AutomationCommandSpec] | None = None
    on_force_stop: list[AutomationCommandSpec] | None = None
    on_stop: list[AutomationCommandSpec] | None = None
    on_stop_fade_out_start: list[AutomationCommandSpec] | None = None
    on_stop_fade_out_end: list[AutomationCommandSpec] | None = None
    on_interrupted_by_sound_button: list[AutomationCommandSpec] | None = None
    on_interrupted_by_playback_control: list[AutomationCommandSpec] | None = None
    on_interrupted_by_app_reset: list[AutomationCommandSpec] | None = None


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
        data = {
            "source": raw.source,
            "location": raw.location,
            "button_text": raw.button_text,
            "hold_to_release": raw.hold_to_release,
            "internal_command": raw.internal_command,
            "internal_params": raw.internal_params,
        }
    else:
        data = dict(raw or {})
    source = str(data.get("source", "") or "").strip().lower()
    if source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
        return AutomationCommandSpec(
            source=AUTOMATION_COMMAND_SOURCE_INTERNAL,
            location="",
            button_text="",
            hold_to_release=False,
            internal_command=normalize_internal_automation_command_id(data.get("internal_command", "")),
            internal_params=normalize_internal_automation_params(
                data.get("internal_command", ""),
                data.get("internal_params", {}),
            ),
        )
    return AutomationCommandSpec(
        source=AUTOMATION_COMMAND_SOURCE_COMPANION,
        location=normalize_automation_location(data.get("location", "")),
        button_text=str(data.get("button_text", "") or "").strip(),
        hold_to_release=bool(data.get("hold_to_release", False)),
        internal_command="",
        internal_params=None,
    )


def automation_spec_to_dict(spec: Optional[AutomationCommandSpec]) -> dict[str, Any]:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    if normalized.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
        return {
            "source": AUTOMATION_COMMAND_SOURCE_INTERNAL,
            "location": "",
            "button_text": "",
            "hold_to_release": False,
            "internal_command": normalized.internal_command,
            "internal_params": dict(normalized.internal_params or {}),
        }
    return {
        "source": AUTOMATION_COMMAND_SOURCE_COMPANION,
        "location": normalized.location,
        "button_text": normalized.button_text,
        "hold_to_release": bool(normalized.hold_to_release),
        "internal_command": "",
        "internal_params": {},
    }


def automation_display_name(spec: Optional[AutomationCommandSpec]) -> str:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    if normalized.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
        return internal_automation_command_summary(
            normalized.internal_command,
            normalized.internal_params or {},
        )
    return normalized.button_text or normalized.location


def automation_spec_is_internal(spec: Optional[AutomationCommandSpec]) -> bool:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    return normalized.source == AUTOMATION_COMMAND_SOURCE_INTERNAL and bool(normalized.internal_command)


def automation_spec_is_companion(spec: Optional[AutomationCommandSpec]) -> bool:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    return normalized.source == AUTOMATION_COMMAND_SOURCE_COMPANION and bool(normalized.location)


def automation_spec_is_valid(spec: Optional[AutomationCommandSpec]) -> bool:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    if normalized.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
        return bool(normalized.internal_command)
    return bool(normalized.location)


def automation_spec_detail_text(spec: Optional[AutomationCommandSpec]) -> str:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    if normalized.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
        return normalized.internal_command
    return normalized.location


def automation_spec_from_set_fields(
    *,
    source: object = "",
    location: object = "",
    button_text: object = "",
    hold_to_release: object = False,
    internal_command: object = "",
    internal_params_json: object = "",
) -> AutomationCommandSpec:
    source_token = str(source or "").strip().lower()
    if source_token == AUTOMATION_COMMAND_SOURCE_INTERNAL:
        params: dict[str, Any] = {}
        raw_json = str(internal_params_json or "").strip()
        if raw_json:
            try:
                parsed = json.loads(raw_json)
                if isinstance(parsed, dict):
                    params = dict(parsed)
            except Exception:
                params = {}
        return normalize_automation_spec(
            {
                "source": AUTOMATION_COMMAND_SOURCE_INTERNAL,
                "internal_command": internal_command,
                "internal_params": params,
            }
        )
    return normalize_automation_spec(
        {
            "source": AUTOMATION_COMMAND_SOURCE_COMPANION,
            "location": location,
            "button_text": button_text,
            "hold_to_release": hold_to_release,
        }
    )


def automation_spec_to_set_fields(spec: Optional[AutomationCommandSpec]) -> dict[str, str]:
    normalized = normalize_automation_spec(spec or AutomationCommandSpec())
    if normalized.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
        return {
            "source": AUTOMATION_COMMAND_SOURCE_INTERNAL,
            "location": "",
            "button_text": "",
            "hold_to_release": "0",
            "internal_command": normalized.internal_command,
            "internal_params_json": json.dumps(
                dict(normalized.internal_params or {}),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }
    return {
        "source": AUTOMATION_COMMAND_SOURCE_COMPANION,
        "location": normalized.location,
        "button_text": normalized.button_text,
        "hold_to_release": "1" if normalized.hold_to_release else "0",
        "internal_command": "",
        "internal_params_json": "",
    }


def normalize_sound_button_automation_config(raw: object) -> Optional[SoundButtonAutomationConfig]:
    if raw is None:
        return None
    if isinstance(raw, SoundButtonAutomationConfig):
        mode = str(getattr(raw, "mode", "") or "").strip().lower()
        bypassed = bool(getattr(raw, "bypassed", False))
        values = {
            event_name: _normalize_optional_press_spec_list(getattr(raw, event_name, None))
            for event_name in SOUND_BUTTON_AUTOMATION_EVENTS
        }
    else:
        data = dict(raw or {})
        mode = str(data.get("mode", "") or "").strip().lower()
        bypassed = bool(data.get("bypassed", False))
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
            for event_name in (
                "on_done_play",
                "on_end_fade_out_end",
                "on_stop",
                "on_stop_fade_out_end",
                "on_interrupted_by_sound_button",
                "on_interrupted_by_playback_control",
                "on_interrupted_by_app_reset",
            ):
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
    return SoundButtonAutomationConfig(mode=mode, bypassed=bypassed, **values)


def sound_button_automation_config_to_dict(
    config: Optional[SoundButtonAutomationConfig],
) -> dict[str, Any]:
    normalized = normalize_sound_button_automation_config(config)
    payload: dict[str, Any] = {
        "mode": SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
        if normalized is None
        else _normalize_sound_button_automation_mode(normalized.mode)
    }
    payload["bypassed"] = False if normalized is None else bool(normalized.bypassed)
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
        if not automation_spec_is_valid(normalized):
            continue
        if normalized.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
            normalized_items.append(
                AutomationCommandSpec(
                    source=AUTOMATION_COMMAND_SOURCE_INTERNAL,
                    internal_command=normalized.internal_command,
                    internal_params=dict(normalized.internal_params or {}),
                )
            )
            continue
        normalized_items.append(
            AutomationCommandSpec(
                source=AUTOMATION_COMMAND_SOURCE_COMPANION,
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
