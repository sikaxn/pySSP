from __future__ import annotations

import threading
import time

_LOCK = threading.RLock()
_NDI_DEBUG_PRINT_ENABLED = False
_NDI_DEBUG_IDLE_AUDIO_PACING_ENABLED = False
_NDI_DEBUG_IDLE_AUDIO_PACING_SEC = 0.001


def set_ndi_debug_options(
    *,
    print_enabled: bool,
    idle_audio_pacing_enabled: bool | None = None,
) -> None:
    global _NDI_DEBUG_PRINT_ENABLED, _NDI_DEBUG_IDLE_AUDIO_PACING_ENABLED
    with _LOCK:
        _NDI_DEBUG_PRINT_ENABLED = bool(print_enabled)
        if idle_audio_pacing_enabled is not None:
            _NDI_DEBUG_IDLE_AUDIO_PACING_ENABLED = bool(idle_audio_pacing_enabled)


def set_ndi_debug_print_enabled(enabled: bool) -> None:
    set_ndi_debug_options(print_enabled=enabled)


def ndi_debug_print_enabled() -> bool:
    with _LOCK:
        return bool(_NDI_DEBUG_PRINT_ENABLED)


def set_ndi_debug_idle_audio_pacing_enabled(enabled: bool) -> None:
    global _NDI_DEBUG_IDLE_AUDIO_PACING_ENABLED
    with _LOCK:
        _NDI_DEBUG_IDLE_AUDIO_PACING_ENABLED = bool(enabled)


def ndi_debug_idle_audio_pacing_enabled() -> bool:
    with _LOCK:
        return bool(_NDI_DEBUG_IDLE_AUDIO_PACING_ENABLED)


def apply_ndi_debug_idle_audio_pacing() -> None:
    if ndi_debug_idle_audio_pacing_enabled():
        time.sleep(_NDI_DEBUG_IDLE_AUDIO_PACING_SEC)


__all__ = [
    "apply_ndi_debug_idle_audio_pacing",
    "ndi_debug_idle_audio_pacing_enabled",
    "ndi_debug_print_enabled",
    "set_ndi_debug_idle_audio_pacing_enabled",
    "set_ndi_debug_options",
    "set_ndi_debug_print_enabled",
]
