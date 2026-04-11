from __future__ import annotations

from typing import Optional


_DISALLOWED_INLINE_CHARS = (";", "|", "&", "`")
_DISALLOWED_CONTROL_CHARS = ("\x00", "\n", "\r")


def unsafe_path_reason(file_path: str) -> Optional[str]:
    text = str(file_path or "")
    if not text.strip():
        return "Path is empty."
    for token in _DISALLOWED_CONTROL_CHARS:
        if token in text:
            if token == "\x00":
                return "Path contains a null byte."
            return "Path contains a newline character."
    for token in _DISALLOWED_INLINE_CHARS:
        if token in text:
            return f"Path contains disallowed character '{token}'."
    return None


def is_safe_file_path(file_path: str) -> bool:
    return unsafe_path_reason(file_path) is None
