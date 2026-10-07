from __future__ import annotations

PLAYBACK_ENGINE_LEGACY = "legacy"
PLAYBACK_ENGINE_V2 = "v2"

_PLAYBACK_ENGINE_OPTIONS: tuple[tuple[str, str], ...] = (
    (PLAYBACK_ENGINE_LEGACY, "Legacy"),
    (PLAYBACK_ENGINE_V2, "Playback V2 (Experimental)"),
)


def normalize_playback_engine(value: object, *, default: str = PLAYBACK_ENGINE_LEGACY) -> str:
    token = str(value or "").strip().lower()
    valid = {PLAYBACK_ENGINE_LEGACY, PLAYBACK_ENGINE_V2}
    if token in valid:
        return token
    fallback = str(default or PLAYBACK_ENGINE_LEGACY).strip().lower()
    return fallback if fallback in valid else PLAYBACK_ENGINE_LEGACY


def playback_engine_options() -> tuple[tuple[str, str], ...]:
    return _PLAYBACK_ENGINE_OPTIONS


def playback_engine_label(value: object) -> str:
    token = normalize_playback_engine(value)
    for engine_id, label in _PLAYBACK_ENGINE_OPTIONS:
        if engine_id == token:
            return label
    return "Legacy"
