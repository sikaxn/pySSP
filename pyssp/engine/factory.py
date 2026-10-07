from __future__ import annotations

from typing import Any

from pyssp.playback_engine import PLAYBACK_ENGINE_V2, normalize_playback_engine

from .playback_v2 import PlaybackV2Runtime
from .runtime import MediaRuntime


def create_media_runtime(*, playback_engine_mode: object = None, **kwargs: Any) -> MediaRuntime:
    mode = normalize_playback_engine(playback_engine_mode)
    if mode == PLAYBACK_ENGINE_V2:
        return PlaybackV2Runtime(**kwargs)
    return MediaRuntime(**kwargs)
