from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

from pyssp.automation_command import (
    AutomationCommandSpec,
    automation_display_name,
    automation_spec_to_dict,
    normalize_automation_spec,
)


AUTOMATION_SCRIPT_EXTENSION = ".pysspautoscript"
AUTOMATION_SCRIPT_FORMAT = "pysspautoscript"
AUTOMATION_SCRIPT_VERSION = 1
AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND = "companion_command"


@dataclass
class AutomationScriptAction:
    type: str = AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND
    payload: AutomationCommandSpec | None = None


@dataclass
class AutomationScriptCue:
    time_ms: int = 0
    comment: str = ""
    actions: list[AutomationScriptAction] | None = None


@dataclass
class AutomationScript:
    notes: str = ""
    cues: list[AutomationScriptCue] | None = None


def normalize_automation_script_action(raw: object) -> Optional[AutomationScriptAction]:
    if isinstance(raw, AutomationScriptAction):
        action_type = str(raw.type or "").strip().lower()
        payload = raw.payload
    else:
        data = dict(raw or {})
        action_type = str(data.get("type", "") or "").strip().lower()
        payload = data.get("payload")
    if action_type != AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND:
        return None
    normalized_payload = normalize_automation_spec(payload or {})
    if not normalized_payload.location:
        return None
    return AutomationScriptAction(
        type=AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
        payload=normalized_payload,
    )


def normalize_automation_script_cue(raw: object) -> Optional[AutomationScriptCue]:
    if isinstance(raw, AutomationScriptCue):
        time_ms = getattr(raw, "time_ms", 0)
        comment = getattr(raw, "comment", "")
        actions_raw = getattr(raw, "actions", None)
    else:
        data = dict(raw or {})
        time_ms = data.get("time_ms", 0)
        comment = data.get("comment", "")
        actions_raw = data.get("actions")
    try:
        normalized_time_ms = max(0, int(time_ms))
    except Exception:
        return None
    normalized_actions: list[AutomationScriptAction] = []
    for item in list(actions_raw or []):
        normalized = normalize_automation_script_action(item)
        if normalized is not None:
            normalized_actions.append(normalized)
    if not normalized_actions:
        return None
    return AutomationScriptCue(
        time_ms=normalized_time_ms,
        comment=str(comment or "").strip(),
        actions=normalized_actions,
    )


def normalize_automation_script(raw: object) -> Optional[AutomationScript]:
    if raw is None:
        return None
    if isinstance(raw, AutomationScript):
        notes = getattr(raw, "notes", "")
        cues_raw = getattr(raw, "cues", None)
    else:
        data = dict(raw or {})
        notes = data.get("notes", "")
        cues_raw = data.get("cues")
    cue_by_time: dict[int, AutomationScriptCue] = {}
    for item in list(cues_raw or []):
        normalized = normalize_automation_script_cue(item)
        if normalized is None:
            continue
        existing = cue_by_time.get(normalized.time_ms)
        if existing is None:
            cue_by_time[normalized.time_ms] = AutomationScriptCue(
                time_ms=normalized.time_ms,
                comment=normalized.comment,
                actions=list(normalized.actions or []),
            )
            continue
        if normalized.comment and not existing.comment:
            existing.comment = normalized.comment
        existing.actions = list(existing.actions or []) + list(normalized.actions or [])
    if not cue_by_time:
        return None
    cues = [cue_by_time[key] for key in sorted(cue_by_time.keys())]
    return AutomationScript(notes=str(notes or "").strip(), cues=cues)


def automation_script_action_to_dict(action: AutomationScriptAction) -> dict[str, Any]:
    normalized = normalize_automation_script_action(action)
    if normalized is None or normalized.payload is None:
        return {}
    return {
        "type": AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
        "payload": automation_spec_to_dict(normalized.payload),
    }


def automation_script_cue_to_dict(cue: AutomationScriptCue) -> dict[str, Any]:
    normalized = normalize_automation_script_cue(cue)
    if normalized is None:
        return {}
    return {
        "time_ms": int(normalized.time_ms),
        "comment": str(normalized.comment or "").strip(),
        "actions": [
            action_dict
            for action_dict in (automation_script_action_to_dict(action) for action in list(normalized.actions or []))
            if action_dict
        ],
    }


def automation_script_to_dict(script: Optional[AutomationScript]) -> dict[str, Any]:
    normalized = normalize_automation_script(script)
    return {
        "format": AUTOMATION_SCRIPT_FORMAT,
        "version": AUTOMATION_SCRIPT_VERSION,
        "notes": "" if normalized is None else str(normalized.notes or "").strip(),
        "cues": []
        if normalized is None
        else [
            cue_dict
            for cue_dict in (automation_script_cue_to_dict(cue) for cue in list(normalized.cues or []))
            if cue_dict
        ],
    }


def load_automation_script(file_path: str) -> AutomationScript:
    with open(file_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError("Automation script must be a JSON object.")
    if str(payload.get("format", "") or "").strip().lower() != AUTOMATION_SCRIPT_FORMAT:
        raise ValueError("Unsupported automation script format.")
    try:
        version = int(payload.get("version", 0))
    except Exception as exc:
        raise ValueError("Automation script version is invalid.") from exc
    if version != AUTOMATION_SCRIPT_VERSION:
        raise ValueError("Unsupported automation script version.")
    normalized = normalize_automation_script(payload)
    if normalized is None:
        return AutomationScript(notes=str(payload.get("notes", "") or "").strip(), cues=[])
    return normalized


def save_automation_script(file_path: str, script: Optional[AutomationScript]) -> None:
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    payload = automation_script_to_dict(script)
    with open(file_path, "w", encoding="utf-8", newline="") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def automation_script_cue_command_summary(cue: Optional[AutomationScriptCue]) -> str:
    normalized = normalize_automation_script_cue(cue)
    if normalized is None:
        return ""
    labels = []
    for action in list(normalized.actions or []):
        spec = normalize_automation_spec(getattr(action, "payload", None) or {})
        if spec.location:
            labels.append(automation_display_name(spec))
    return ", ".join(labels)


def find_automation_script_cue_indices(
    script: Optional[AutomationScript],
    position_ms: int,
) -> tuple[int, int]:
    normalized = normalize_automation_script(script)
    if normalized is None or not normalized.cues:
        return -1, -1
    pos = max(0, int(position_ms))
    current_index = -1
    next_index = -1
    for index, cue in enumerate(normalized.cues):
        if int(cue.time_ms) <= pos:
            current_index = index
            continue
        next_index = index
        break
    return current_index, next_index
