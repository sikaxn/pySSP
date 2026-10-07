from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class PlaybackV2Telemetry:
    started_at: float = field(default_factory=time.perf_counter)
    created_session_count: int = 0
    deleted_session_count: int = 0
    last_error: str = ""
