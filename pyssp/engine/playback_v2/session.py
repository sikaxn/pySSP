from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.engine.types import PlaybackSessionId

if TYPE_CHECKING:
    from pyssp.engine.video_session import UnifiedVideoSession


@dataclass
class PlaybackV2SessionState:
    session_id: PlaybackSessionId
    player: ExternalMediaPlayer
    video_session: "UnifiedVideoSession"
    created_at: float = field(default_factory=time.perf_counter)
    started_order: int = -1
    started_at: float = 0.0
    state: int = ExternalMediaPlayer.StoppedState
    position_ms: int = 0
    duration_ms: int = 0
    slot_key: Optional[tuple[str, int, int]] = None
