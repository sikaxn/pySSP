# Shared Audio Tap Bus API

`pyssp.audio_tap_bus.SharedAudioTapBus` is the first engine-owned shared state object extracted from `pyssp/audio_engine.py`.

Its current role is intentionally narrow:

- centralize output meter aggregation
- centralize per-player monitor frame queues
- preserve existing `pre_fader` / `post_fader` semantics
- provide one stable seam for future master-bus and shared-render work

## Current API

### Constructor

```python
SharedAudioTapBus(
    *,
    channel_count: int = 2,
    meter_active_window_sec: float = 0.25,
    monitor_capacity_frames: int = 48000 * 4,
)
```

### Meter methods

- `get_meter_levels(mode: str = "post_fader") -> tuple[float, float]`
- `update_meter(stream_id: int, left: float, right: float, *, mode: str = "post_fader") -> None`
- `clear_meter(stream_id: int) -> None`

Behavior:

- meters are tracked independently for `pre_fader` and `post_fader`
- stale sources expire by `meter_active_window_sec`
- summed output is clamped to `0.0..1.0` per channel

### Monitor-frame methods

- `clear_monitor_frames(player_id: str = "") -> None`
- `append_monitor_frames(player_id: str, frames_block: np.ndarray, *, mode: str) -> None`
- `take_monitor_frames(player_id: str, max_frames: int = 0, mode: str = "post_fader") -> np.ndarray`
- `monitor_frame_counts(player_id: str) -> dict[str, int]`
- `monitor_player_ids(mode: str = "post_fader") -> list[str]`
- `mix_monitor_chunk(player_ids: list[str], *, target_frames: int, mode: str = "post_fader") -> tuple[np.ndarray, dict[str, int]] | None`
- `consume_monitor_frames(consume_map: dict[str, int], mode: str = "post_fader") -> None`

Behavior:

- monitor queues are tracked independently for `pre_fader` and `post_fader`
- frames are stored per `player_id`
- oldest monitor frames are dropped when capacity is exceeded
- `max_frames <= 0` drains all available queued frames for that mode
- mix/consume methods allow shared-bus consumers such as NDI to read pending audio without keeping a second UI-owned buffer layer

## Current integration point

`pyssp/audio_engine.py` still owns playback and hardware output, but now delegates shared meter/monitor storage to `SharedAudioTapBus`.

Current shared-bus consumers:

- engine-level output meter aggregation
- per-player monitor-frame storage
- NDI audio chunk mixing/consumption through bus-backed helpers in `pyssp.audio_engine`

This is a foundation step only. It does **not** yet create a single hardware render stream or a true engine-owned master mix bus.

## Intended follow-on work

- move NDI consumption from UI-side per-player remixing to shared engine taps
- move additional tap/tail state out of `ExternalMediaPlayer`
- introduce a true engine-owned mix/master bus above these shared tap primitives
