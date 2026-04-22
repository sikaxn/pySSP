from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

SlotKey = Tuple[str, int, int]


@dataclass
class PlayerRuntimeRecord:
    runtime_id: int
    slot_key: SlotKey
    started_at: float


class PlaybackRuntimeTracker:
    """Track per-playback runtime ids without reusing ids for active sessions."""

    def __init__(self) -> None:
        self._next_runtime_id = 0
        self._records: Dict[int, PlayerRuntimeRecord] = {}

    def mark_started(self, player: Any, slot_key: SlotKey) -> int:
        runtime_id = int(self._next_runtime_id)
        self._next_runtime_id += 1
        self._records[id(player)] = PlayerRuntimeRecord(
            runtime_id=runtime_id,
            slot_key=slot_key,
            started_at=time.monotonic(),
        )
        return runtime_id

    def clear(self, player: Any) -> Optional[PlayerRuntimeRecord]:
        return self._records.pop(id(player), None)

    def clear_all(self) -> None:
        self._records.clear()

    def runtime_id_for(self, player: Any) -> Optional[int]:
        record = self._records.get(id(player))
        if record is None:
            return None
        return int(record.runtime_id)

    def slot_key_for(self, player: Any) -> Optional[SlotKey]:
        record = self._records.get(id(player))
        if record is None:
            return None
        return record.slot_key

    def oldest_active_player(self, players: Iterable[Any]) -> Optional[Any]:
        selected_player = None
        selected_record: Optional[PlayerRuntimeRecord] = None
        for player in players:
            record = self._records.get(id(player))
            if record is None:
                continue
            if selected_record is None or record.runtime_id < selected_record.runtime_id:
                selected_player = player
                selected_record = record
        return selected_player

    def newest_active_player(self, players: Iterable[Any]) -> Optional[Any]:
        selected_player = None
        selected_record: Optional[PlayerRuntimeRecord] = None
        for player in players:
            record = self._records.get(id(player))
            if record is None:
                continue
            if selected_record is None or record.runtime_id > selected_record.runtime_id:
                selected_player = player
                selected_record = record
        return selected_player

    def timecode_player(self, players: Iterable[Any], multi_play_enabled: bool) -> Optional[Any]:
        if multi_play_enabled:
            return self.oldest_active_player(players)
        return self.newest_active_player(players)
