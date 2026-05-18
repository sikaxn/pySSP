# `pyssp/audio_tap_bus.py`

- Source: `pyssp/audio_tap_bus.py`
- Module path: `pyssp.audio_tap_bus`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `SharedAudioTapBus`

- Defined at `pyssp/audio_tap_bus.py:11`
- Summary: Centralizes shared tap-side meter and monitor state for the audio engine.

#### Public Members

- `meter_active_window_sec(self) -> float` [property] (pyssp/audio_tap_bus.py:38)
- `monitor_capacity_frames(self) -> int` [property] (pyssp/audio_tap_bus.py:42)
- `monitor_player_ids(self, mode: str = 'post_fader') -> List[str]` [method] (pyssp/audio_tap_bus.py:57)
- `get_meter_levels(self, mode: str = 'post_fader') -> Tuple[float, float]` [method] (pyssp/audio_tap_bus.py:66)
- `update_meter(self, stream_id: int, left: float, right: float, *, mode: str = 'post_fader') -> None` [method] (pyssp/audio_tap_bus.py:83)
- `clear_meter(self, stream_id: int) -> None` [method] (pyssp/audio_tap_bus.py:91)
- `clear_monitor_frames(self, player_id: str = '') -> None` [method] (pyssp/audio_tap_bus.py:96)
- `append_monitor_frames(self, player_id: str, frames_block: np.ndarray, *, mode: str) -> None` [method] (pyssp/audio_tap_bus.py:110)
- `take_monitor_frames(self, player_id: str, max_frames: int = 0, mode: str = 'post_fader') -> np.ndarray` [method] (pyssp/audio_tap_bus.py:130)
- `monitor_frame_counts(self, player_id: str) -> Dict[str, int]` [method] (pyssp/audio_tap_bus.py:171)
- `mix_monitor_chunk(self, player_ids: List[str], *, target_frames: int, mode: str = 'post_fader') -> tuple[np.ndarray, Dict[str, int]] | None` [method] (pyssp/audio_tap_bus.py:181)
- `consume_monitor_frames(self, consume_map: Dict[str, int], mode: str = 'post_fader') -> None` [method] (pyssp/audio_tap_bus.py:234)

#### Internal Members

- `__init__(self, *, channel_count: int = 2, meter_active_window_sec: float = 0.25, monitor_capacity_frames: int = 48000 * 4) -> None` [constructor] (pyssp/audio_tap_bus.py:19)
- `_meter_store(self, mode: str) -> Dict[int, Tuple[float, float, float]]` [method] (pyssp/audio_tap_bus.py:45)
- `_monitor_store(self, mode: str) -> tuple[Dict[str, deque[np.ndarray]], Dict[str, int]]` [method] (pyssp/audio_tap_bus.py:51)
