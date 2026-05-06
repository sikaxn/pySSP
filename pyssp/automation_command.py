from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


AUTOMATION_SOURCE_TYPE = "automation"
AUTOMATION_UNSUPPORTED_MARKER_TEXT = "Unsupported automation command button. A newer version of pySSP is required."
AUTOMATION_AUTO_RELEASE_IMMEDIATE = "immediate"
AUTOMATION_AUTO_RELEASE_DOWN_ONLY = "down_only"
AUTOMATION_DEFAULT_BUTTON_COLOR = "#E8C67A"


@dataclass
class AutomationCommandSpec:
    location: str = ""
    button_text: str = ""
    hold_to_release: bool = False


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
