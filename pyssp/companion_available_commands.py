from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pyssp.settings_store import get_settings_path


def get_companion_available_commands_path() -> Path:
    base = get_settings_path().parent
    base.mkdir(parents=True, exist_ok=True)
    return base / "companion_available_commands.json"


def load_companion_available_commands() -> dict[str, Any]:
    path = get_companion_available_commands_path()
    if not path.exists():
        return {"pages": {}, "updated_at": ""}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return {"pages": {}, "updated_at": ""}
    pages = payload.get("pages", {})
    if not isinstance(pages, dict):
        pages = {}
    updated_at = str(payload.get("updated_at", "") or "")
    return {"pages": pages, "updated_at": updated_at}


def clear_companion_available_commands() -> dict[str, Any]:
    payload = {"pages": {}, "updated_at": _stamp()}
    _save_payload(payload)
    return payload


def record_companion_available_command(
    *,
    location: str,
    text: str,
    key_type: str = "",
    color: str = "",
    pressed: bool = False,
) -> Optional[dict[str, Any]]:
    parsed = _parse_location(location)
    if parsed is None:
        return None
    page, row, column = parsed
    payload = load_companion_available_commands()
    pages = dict(payload.get("pages", {}) or {})
    page_key = str(page)
    page_items = dict(pages.get(page_key, {}) or {})
    slot_key = f"{row}/{column}"
    existing = dict(page_items.get(slot_key, {}) or {})
    resolved_color = str(existing.get("color", "") or "")
    if not bool(pressed):
        resolved_color = str(color or "")
    entry = {
        "page": int(page),
        "row": int(row),
        "column": int(column),
        "text": _normalize_button_text(text),
        "type": str(key_type or ""),
        "color": resolved_color,
    }
    page_items[slot_key] = entry
    pages[page_key] = page_items
    payload = {"pages": pages, "updated_at": _stamp()}
    _save_payload(payload)
    return payload


def format_companion_available_commands(payload: Optional[dict[str, Any]] = None) -> str:
    data = payload if payload is not None else load_companion_available_commands()
    pages = dict(data.get("pages", {}) or {})
    ordered_pages: dict[str, list[dict[str, Any]]] = {}
    for raw_page, raw_items in sorted(pages.items(), key=lambda item: _safe_int(item[0])):
        entries = list((raw_items or {}).values()) if isinstance(raw_items, dict) else []
        entries = sorted(
            [dict(entry or {}) for entry in entries],
            key=lambda entry: (
                _safe_int(entry.get("page")),
                _safe_int(entry.get("row")),
                _safe_int(entry.get("column")),
            ),
        )
        ordered_pages[str(raw_page)] = entries
    rendered = {
        "updated_at": str(data.get("updated_at", "") or ""),
        "pages": ordered_pages,
    }
    return json.dumps(rendered, indent=2, ensure_ascii=False)


def list_companion_available_commands(payload: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    data = payload if payload is not None else load_companion_available_commands()
    pages = dict(data.get("pages", {}) or {})
    entries: list[dict[str, Any]] = []
    for _raw_page, raw_items in sorted(pages.items(), key=lambda item: _safe_int(item[0])):
        if not isinstance(raw_items, dict):
            continue
        for entry in raw_items.values():
            if not isinstance(entry, dict):
                continue
            entries.append(
                {
                    "page": _safe_int(entry.get("page")),
                    "row": _safe_int(entry.get("row")),
                    "column": _safe_int(entry.get("column")),
                    "text": _normalize_button_text(entry.get("text", "")),
                    "type": str(entry.get("type", "") or ""),
                    "color": str(entry.get("color", "") or ""),
                }
            )
    entries.sort(key=lambda entry: (entry["page"], entry["row"], entry["column"]))
    return entries


def is_black_empty_command(entry: dict[str, Any]) -> bool:
    text = str(entry.get("text", "") or "").strip()
    color = str(entry.get("color", "") or "").strip().lower()
    if text:
        return False
    return color in {"#000000", "#000", "black"}


def is_navigation_command(entry: dict[str, Any]) -> bool:
    key_type = str(entry.get("type", "") or "").strip().upper()
    return key_type in {"PAGEUP", "PAGEDOWN", "PAGENUM"}


def _save_payload(payload: dict[str, Any]) -> None:
    path = get_companion_available_commands_path()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def _parse_location(location: object) -> Optional[tuple[int, int, int]]:
    text = str(location or "").strip()
    if not text:
        return None
    parts = text.split("/")
    if len(parts) != 3:
        return None
    try:
        page = int(parts[0])
        row = int(parts[1])
        column = int(parts[2])
    except Exception:
        return None
    return page, row, column


def _safe_int(raw: object, default: int = 0) -> int:
    try:
        return int(raw)
    except Exception:
        return int(default)


def _normalize_button_text(raw: object) -> str:
    text = str(raw or "")
    text = text.replace("\\r\\n", " ")
    text = text.replace("\\n", " ")
    text = text.replace("\\r", " ")
    text = text.replace("\r", "\n")
    return " ".join(text.split())


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()
