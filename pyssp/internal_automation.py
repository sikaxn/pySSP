from __future__ import annotations

from typing import Any

from pyssp.display_focus import DISPLAY_ROUTE_SOURCE_LABELS, normalize_display_route_source
from pyssp.i18n import tr


INTERNAL_AUTOMATION_CATEGORY_TRANSPORT = "Transport"
INTERNAL_AUTOMATION_CATEGORY_MODE = "Mode"
INTERNAL_AUTOMATION_CATEGORY_NAVIGATION = "Navigation"
INTERNAL_AUTOMATION_CATEGORY_TARGET = "Target"
INTERNAL_AUTOMATION_CATEGORY_STAGE = "Stage"


INTERNAL_AUTOMATION_COMMANDS: tuple[dict[str, Any], ...] = (
    {"id": "play", "label": "Play Sound Button", "category": INTERNAL_AUTOMATION_CATEGORY_TARGET},
    {"id": "goto", "label": "Go To Page", "category": INTERNAL_AUTOMATION_CATEGORY_TARGET},
    {"id": "pause", "label": "Pause Playback", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "resume", "label": "Resume Playback", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "stop", "label": "Stop Playback", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "forcestop", "label": "Force Stop Playback", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "rapidfire", "label": "Rapid Fire", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "playnext", "label": "Play Next", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "playselected", "label": "Play Selected", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "playselectedpause", "label": "Play Selected / Pause", "category": INTERNAL_AUTOMATION_CATEGORY_TRANSPORT},
    {"id": "mute", "label": "Toggle Mute", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "lock", "label": "Lock Screen", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "automation_lock", "label": "Automation Lock", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "unlock", "label": "Unlock Screen", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "lyric_display", "label": "Lyric Display", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "video_display", "label": "Video Display Routing", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "vocal_removed", "label": "Vocal Removed", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "talk", "label": "Talk Mode", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "playlist", "label": "Playlist", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "playlist_shuffle", "label": "Playlist Shuffle", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "multiplay", "label": "Multi Play", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "fade", "label": "Fade", "category": INTERNAL_AUTOMATION_CATEGORY_MODE},
    {"id": "resetpage", "label": "Reset Page", "category": INTERNAL_AUTOMATION_CATEGORY_NAVIGATION},
    {"id": "navigate", "label": "Navigate", "category": INTERNAL_AUTOMATION_CATEGORY_NAVIGATION},
    {"id": "volume_set", "label": "Set Volume", "category": INTERNAL_AUTOMATION_CATEGORY_TARGET},
    {"id": "seek", "label": "Seek Transport", "category": INTERNAL_AUTOMATION_CATEGORY_TARGET},
    {"id": "alert", "label": "Stage Alert", "category": INTERNAL_AUTOMATION_CATEGORY_STAGE},
)

_COMMANDS_BY_ID = {str(item["id"]): dict(item) for item in INTERNAL_AUTOMATION_COMMANDS}


def list_internal_automation_commands() -> list[dict[str, Any]]:
    return [
        {
            **dict(item),
            "label": tr(str(item.get("label", "") or "")),
            "category": tr(str(item.get("category", "") or "")),
        }
        for item in INTERNAL_AUTOMATION_COMMANDS
    ]


def normalize_internal_automation_command_id(raw: object) -> str:
    token = str(raw or "").strip().lower()
    return token if token in _COMMANDS_BY_ID else ""


def normalize_internal_automation_params(command_id: object, raw: object) -> dict[str, Any]:
    cmd = normalize_internal_automation_command_id(command_id)
    data = dict(raw or {})
    if not cmd:
        return {}
    if cmd == "lyric_display":
        mode = str(data.get("mode", "") or "").strip().lower()
        return {"mode": mode if mode in {"show", "blank", "toggle"} else "show"}
    if cmd == "video_display":
        action = str(data.get("action", "") or "").strip().lower()
        if action not in {"set_source_override", "set_source_only", "follow"}:
            action = "follow"
        if action == "follow":
            mode = str(data.get("mode", "") or "").strip().lower()
            return {"action": "follow", "mode": mode if mode in {"enable", "disable", "toggle"} else "toggle"}
        source = normalize_display_route_source(
            str(data.get("source", "") or "").strip().lower(),
            default="backdrop",
        )
        return {"action": action, "source": source}
    if cmd in {"vocal_removed", "talk", "playlist", "playlist_shuffle", "multiplay"}:
        mode = str(data.get("mode", "") or "").strip().lower()
        return {"mode": mode if mode in {"enable", "disable", "toggle"} else "toggle"}
    if cmd == "fade":
        kind = str(data.get("kind", "") or "").strip().lower()
        mode = str(data.get("mode", "") or "").strip().lower()
        return {
            "kind": kind if kind in {"fadein", "fadeout", "crossfade"} else "fadein",
            "mode": mode if mode in {"enable", "disable", "toggle"} else "toggle",
        }
    if cmd == "resetpage":
        scope = str(data.get("scope", "") or "").strip().lower()
        return {"scope": scope if scope in {"current", "all"} else "current"}
    if cmd == "navigate":
        target = str(data.get("target", "") or "").strip().lower()
        direction = str(data.get("direction", "") or "").strip().lower()
        return {
            "target": target if target in {"group", "page", "sound_button"} else "page",
            "direction": direction if direction in {"next", "prev"} else "next",
        }
    if cmd == "play":
        return {"button_id": str(data.get("button_id", "") or "").strip().lower()}
    if cmd == "goto":
        return {"target": str(data.get("target", "") or "").strip().lower()}
    if cmd == "volume_set":
        try:
            level = int(data.get("level", 0))
        except Exception:
            level = 0
        return {"level": max(0, min(100, level))}
    if cmd == "seek":
        mode = str(data.get("seek_mode", data.get("mode", "")) or "").strip().lower()
        if mode == "time":
            return {"seek_mode": "time", "time": str(data.get("time", "") or "").strip()}
        try:
            percent = float(data.get("percent", 0))
        except Exception:
            percent = 0.0
        return {"seek_mode": "percent", "percent": max(0.0, min(100.0, percent))}
    if cmd == "alert":
        alert_mode = str(data.get("alert_mode", data.get("mode", "")) or "").strip().lower()
        if alert_mode == "clear":
            return {"alert_mode": "clear"}
        try:
            seconds = int(data.get("seconds", 10))
        except Exception:
            seconds = 10
        return {
            "alert_mode": "show",
            "text": str(data.get("text", "") or "").strip(),
            "keep": bool(data.get("keep", True)),
            "seconds": max(1, min(600, seconds)),
        }
    return {}


def internal_automation_command_summary(command_id: object, params: object) -> str:
    cmd = normalize_internal_automation_command_id(command_id)
    data = normalize_internal_automation_params(cmd, params)
    if not cmd:
        return ""
    base = tr(str(_COMMANDS_BY_ID.get(cmd, {}).get("label", cmd) or cmd))
    if cmd == "lyric_display":
        mode = tr(str(data.get("mode", "")).capitalize())
        return f"{mode} {tr('Lyrics')}"
    if cmd == "video_display":
        action = str(data.get("action", "") or "").strip().lower()
        if action == "follow":
            mode = tr(str(data.get("mode", "toggle") or "toggle").capitalize())
            return f"{base}: {mode} {tr('Follow Sound Button Display Focus')}"
        source = DISPLAY_ROUTE_SOURCE_LABELS.get(str(data.get("source", "") or "").strip().lower(), tr("Backdrop"))
        if action == "set_source_override":
            return f"{base}: {tr('Set Source')} {tr(source)} {tr('and Disable Follow')}"
        return f"{base}: {tr('Set Source')} {tr(source)}"
    if cmd in {"vocal_removed", "talk", "playlist", "playlist_shuffle", "multiplay"}:
        mode = tr(str(data.get("mode", "")).capitalize())
        return f"{mode} {base}"
    if cmd == "fade":
        mode = tr(str(data.get("mode", "")).capitalize())
        kind_map = {"fadein": tr("Fade In"), "fadeout": tr("Fade Out"), "crossfade": tr("Crossfade")}
        kind = kind_map.get(str(data.get("kind", "")).strip().lower(), tr("Fade In"))
        return f"{mode} {kind}"
    if cmd == "resetpage":
        scope = tr(str(data.get("scope", "")).capitalize())
        return f"{tr('Reset')} {scope} {tr('Page')}"
    if cmd == "navigate":
        direction = tr("Next") if str(data.get("direction", "")).strip().lower() == "next" else tr("Previous")
        target_map = {"group": tr("Group"), "page": tr("Page"), "sound_button": tr("Sound Button")}
        target = target_map.get(str(data.get("target", "")).strip().lower(), tr("Page"))
        return f"{tr('Navigate To')} {direction} {target}"
    if cmd == "play":
        button_id = str(data.get("button_id", "") or "").strip().upper()
        return f"{tr('Play')} {button_id}" if button_id else base
    if cmd == "goto":
        target = str(data.get("target", "") or "").strip().upper()
        return f"{tr('Go To')} {target}" if target else base
    if cmd == "volume_set":
        return f"{tr('Set Volume')} {int(data.get('level', 0))}%"
    if cmd == "seek":
        if str(data.get("seek_mode", "")) == "time":
            return f"{tr('Seek To')} {str(data.get('time', '') or '').strip()}"
        return f"{tr('Seek To')} {float(data.get('percent', 0.0)):g}%"
    if cmd == "alert":
        if str(data.get("alert_mode", "")) == "clear":
            return tr("Clear Stage Alert")
        text = str(data.get("text", "") or "").strip()
        return f"{tr('Show Stage Alert')}: {text}" if text else tr("Show Stage Alert")
    return base


def internal_automation_dispatch(command_id: object, params: object) -> tuple[str, dict[str, Any]]:
    cmd = normalize_internal_automation_command_id(command_id)
    data = normalize_internal_automation_params(cmd, params)
    if not cmd:
        return "", {}
    if cmd == "seek":
        if str(data.get("seek_mode", "")) == "time":
            return "seek", {"time": str(data.get("time", "") or "").strip()}
        return "seek", {"percent": data.get("percent", 0.0)}
    if cmd == "alert":
        if str(data.get("alert_mode", "")) == "clear":
            return "alert", {"clear": True}
        return "alert", {
            "text": str(data.get("text", "") or "").strip(),
            "keep": bool(data.get("keep", True)),
            "seconds": int(data.get("seconds", 10)),
        }
    if cmd == "video_display":
        return "video_display", dict(data)
    return cmd, dict(data)
