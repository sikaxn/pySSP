from __future__ import annotations

import threading
import time
from collections import deque
from typing import Dict, List, Tuple

import numpy as np


class SharedAudioTapBus:
    """Centralizes shared tap-side meter and monitor state for the audio engine.

    This is the first step toward a true engine-owned master bus: existing player
    callbacks can publish tap data here while downstream consumers stop owning
    their own storage and aggregation rules.
    """

    def __init__(
        self,
        *,
        channel_count: int = 2,
        meter_active_window_sec: float = 0.25,
        monitor_capacity_frames: int = 48000 * 4,
    ) -> None:
        self._channel_count = max(1, int(channel_count))
        self._meter_active_window_sec = max(0.01, float(meter_active_window_sec))
        self._monitor_capacity_frames = max(1, int(monitor_capacity_frames))
        self._lock = threading.RLock()
        self._meter_pre_sources: Dict[int, Tuple[float, float, float]] = {}
        self._meter_post_sources: Dict[int, Tuple[float, float, float]] = {}
        self._monitor_pre: Dict[str, deque[np.ndarray]] = {}
        self._monitor_post: Dict[str, deque[np.ndarray]] = {}
        self._monitor_pre_counts: Dict[str, int] = {}
        self._monitor_post_counts: Dict[str, int] = {}

    @property
    def meter_active_window_sec(self) -> float:
        return float(self._meter_active_window_sec)

    @property
    def monitor_capacity_frames(self) -> int:
        return int(self._monitor_capacity_frames)

    def _meter_store(self, mode: str) -> Dict[int, Tuple[float, float, float]]:
        token = str(mode or "post_fader").strip().lower()
        if token == "pre_fader":
            return self._meter_pre_sources
        return self._meter_post_sources

    def _monitor_store(self, mode: str) -> tuple[Dict[str, deque[np.ndarray]], Dict[str, int]]:
        token = str(mode or "post_fader").strip().lower()
        if token == "pre_fader":
            return self._monitor_pre, self._monitor_pre_counts
        return self._monitor_post, self._monitor_post_counts

    def monitor_player_ids(self, mode: str = "post_fader") -> List[str]:
        with self._lock:
            store, counts = self._monitor_store(mode)
            return [
                str(player_id)
                for player_id, queue_ref in store.items()
                if queue_ref and max(0, int(counts.get(player_id, 0))) > 0
            ]

    def get_meter_levels(self, mode: str = "post_fader") -> Tuple[float, float]:
        now = time.perf_counter()
        left = 0.0
        right = 0.0
        stale_ids: List[int] = []
        with self._lock:
            sources = self._meter_store(mode)
            for stream_id, (updated_at, src_left, src_right) in sources.items():
                if (now - float(updated_at)) > self._meter_active_window_sec:
                    stale_ids.append(int(stream_id))
                    continue
                left += max(0.0, float(src_left))
                right += max(0.0, float(src_right))
            for stream_id in stale_ids:
                sources.pop(stream_id, None)
        return min(1.0, left), min(1.0, right)

    def update_meter(self, stream_id: int, left: float, right: float, *, mode: str = "post_fader") -> None:
        with self._lock:
            self._meter_store(mode)[int(stream_id)] = (
                time.perf_counter(),
                max(0.0, float(left)),
                max(0.0, float(right)),
            )

    def clear_meter(self, stream_id: int) -> None:
        with self._lock:
            self._meter_pre_sources.pop(int(stream_id), None)
            self._meter_post_sources.pop(int(stream_id), None)

    def clear_monitor_frames(self, player_id: str = "") -> None:
        token = str(player_id or "").strip()
        with self._lock:
            if not token:
                self._monitor_pre.clear()
                self._monitor_post.clear()
                self._monitor_pre_counts.clear()
                self._monitor_post_counts.clear()
                return
            self._monitor_pre.pop(token, None)
            self._monitor_post.pop(token, None)
            self._monitor_pre_counts.pop(token, None)
            self._monitor_post_counts.pop(token, None)

    def append_monitor_frames(self, player_id: str, frames_block: np.ndarray, *, mode: str) -> None:
        token = str(player_id or "").strip()
        if not token:
            return
        block = np.asarray(frames_block, dtype=np.float32)
        if block.ndim != 2 or len(block) <= 0:
            return
        store, counts = self._monitor_store(mode)
        with self._lock:
            queue_ref = store.get(token)
            if queue_ref is None:
                queue_ref = deque()
                store[token] = queue_ref
                counts[token] = 0
            queue_ref.append(np.ascontiguousarray(block, dtype=np.float32).copy())
            counts[token] = max(0, int(counts.get(token, 0))) + int(len(block))
            while counts[token] > self._monitor_capacity_frames and queue_ref:
                dropped = np.asarray(queue_ref.popleft(), dtype=np.float32)
                counts[token] = max(0, int(counts[token]) - int(len(dropped)))

    def take_monitor_frames(self, player_id: str, max_frames: int = 0, mode: str = "post_fader") -> np.ndarray:
        token = str(player_id or "").strip()
        if not token:
            return np.zeros((0, self._channel_count), dtype=np.float32)
        store, counts = self._monitor_store(mode)
        with self._lock:
            queue_ref = store.get(token)
            if not queue_ref:
                return np.zeros((0, self._channel_count), dtype=np.float32)
            total_frames = max(0, int(counts.get(token, 0)))
            if total_frames <= 0:
                return np.zeros((0, self._channel_count), dtype=np.float32)
            target_frames = total_frames if max_frames <= 0 else min(total_frames, max(1, int(max_frames)))
            pieces: List[np.ndarray] = []
            remaining = target_frames
            channel_count = self._channel_count
            while remaining > 0 and queue_ref:
                head = np.asarray(queue_ref[0], dtype=np.float32)
                if head.ndim != 2 or len(head) <= 0:
                    queue_ref.popleft()
                    continue
                channel_count = int(head.shape[1])
                take = min(remaining, int(head.shape[0]))
                pieces.append(np.ascontiguousarray(head[:take, :], dtype=np.float32))
                remaining -= take
                if take >= int(head.shape[0]):
                    queue_ref.popleft()
                else:
                    queue_ref[0] = np.ascontiguousarray(head[take:, :], dtype=np.float32)
                counts[token] = max(0, int(counts.get(token, 0)) - take)
            if counts.get(token, 0) <= 0:
                counts[token] = 0
            if not queue_ref:
                store.pop(token, None)
                counts.pop(token, None)
            if not pieces:
                return np.zeros((0, channel_count), dtype=np.float32)
            if len(pieces) == 1:
                return pieces[0]
            return np.ascontiguousarray(np.vstack(pieces), dtype=np.float32)

    def monitor_frame_counts(self, player_id: str) -> Dict[str, int]:
        token = str(player_id or "").strip()
        if not token:
            return {"pre_fader": 0, "post_fader": 0}
        with self._lock:
            return {
                "pre_fader": max(0, int(self._monitor_pre_counts.get(token, 0))),
                "post_fader": max(0, int(self._monitor_post_counts.get(token, 0))),
            }

    def mix_monitor_chunk(
        self,
        player_ids: List[str],
        *,
        target_frames: int,
        mode: str = "post_fader",
    ) -> tuple[np.ndarray, Dict[str, int]] | None:
        if target_frames <= 0:
            return None
        with self._lock:
            store, _counts = self._monitor_store(mode)
            max_available = 0
            channel_count = self._channel_count
            for player_id in player_ids:
                queue_ref = store.get(str(player_id))
                if not queue_ref:
                    continue
                available = 0
                for piece in queue_ref:
                    block = np.asarray(piece, dtype=np.float32)
                    if block.ndim != 2 or len(block) <= 0:
                        continue
                    channel_count = int(block.shape[1])
                    available += int(block.shape[0])
                max_available = max(max_available, available)
            if max_available < int(target_frames):
                return None
            mixed = np.zeros((int(target_frames), channel_count), dtype=np.float32)
            consume_map: Dict[str, int] = {}
            for player_id in player_ids:
                queue_ref = store.get(str(player_id))
                if not queue_ref:
                    continue
                remaining = int(target_frames)
                write_offset = 0
                consumed = 0
                for piece in queue_ref:
                    if remaining <= 0:
                        break
                    block = np.asarray(piece, dtype=np.float32)
                    if block.ndim != 2 or block.shape[1] != channel_count or len(block) <= 0:
                        continue
                    take = min(remaining, int(block.shape[0]))
                    if take <= 0:
                        continue
                    mixed[write_offset : write_offset + take, :] += block[:take, :]
                    write_offset += take
                    remaining -= take
                    consumed += take
                if consumed > 0:
                    consume_map[str(player_id)] = consumed
            return mixed, consume_map

    def consume_monitor_frames(self, consume_map: Dict[str, int], mode: str = "post_fader") -> None:
        if not consume_map:
            return
        with self._lock:
            store, counts = self._monitor_store(mode)
            for player_id, requested in consume_map.items():
                queue_ref = store.get(str(player_id))
                if not queue_ref:
                    continue
                remaining = max(0, int(requested))
                while remaining > 0 and queue_ref:
                    head = np.asarray(queue_ref[0], dtype=np.float32)
                    if head.ndim != 2 or len(head) <= 0:
                        queue_ref.popleft()
                        continue
                    take = min(remaining, int(head.shape[0]))
                    remaining -= take
                    counts[str(player_id)] = max(0, int(counts.get(str(player_id), 0)) - take)
                    if take >= int(head.shape[0]):
                        queue_ref.popleft()
                    else:
                        queue_ref[0] = np.ascontiguousarray(head[take:, :], dtype=np.float32)
                if counts.get(str(player_id), 0) <= 0:
                    counts[str(player_id)] = 0
                if not queue_ref:
                    store.pop(str(player_id), None)
                    counts.pop(str(player_id), None)
