# `pyssp/engine/runtime.py`

- Source: `pyssp/engine/runtime.py`
- Module path: `pyssp.engine.runtime`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `_SessionRecord`

- Defined at `pyssp/engine/runtime.py:37`

### `MediaRuntime`

- Defined at `pyssp/engine/runtime.py:48`
- Summary: Own the current media runtime while legacy players remain the execution node.

#### Public Members

- `ffmpeg(self) -> FFmpegEngineServices` [property] (pyssp/engine/runtime.py:76)
- `has_session(self, session_id: PlaybackSessionId) -> bool` [method] (pyssp/engine/runtime.py:79)
- `create_legacy_session(self, session_id: PlaybackSessionId) -> ExternalMediaPlayer` [method] (pyssp/engine/runtime.py:83)
- `player_for_session(self, session_id: PlaybackSessionId) -> ExternalMediaPlayer` [method] (pyssp/engine/runtime.py:101)
- `delete_session(self, session_id: PlaybackSessionId) -> bool` [method] (pyssp/engine/runtime.py:108)
- `set_session_slot_key(self, session_id: PlaybackSessionId, slot_key: Optional[tuple[str, int, int]]) -> bool` [method] (pyssp/engine/runtime.py:124)
- `session_snapshots(self) -> tuple[RuntimeSessionSnapshot, ...]` [method] (pyssp/engine/runtime.py:132)
- `shutdown(self) -> None` [method] (pyssp/engine/runtime.py:148)
- `set_multi_play_enabled(self, enabled: bool) -> None` [method] (pyssp/engine/runtime.py:155)
- `transport_snapshot(self) -> TransportSnapshot` [method] (pyssp/engine/runtime.py:159)
- `diagnostics_snapshot(self) -> EngineDiagnosticsSnapshot` [method] (pyssp/engine/runtime.py:163)
- `probe_media(self, path: str) -> MediaProbeResult` [method] (pyssp/engine/runtime.py:179)

#### Internal Members

- `__init__(self, *, player_factory: Optional[Callable[[], ExternalMediaPlayer]] = None, ffmpeg_services: Optional[FFmpegEngineServices] = None, audio_bus_ids: tuple[AudioBusId, ...] = _DEFAULT_AUDIO_BUS_IDS, video_destination_ids: tuple[VideoDestinationId, ...] = _DEFAULT_VIDEO_DESTINATION_IDS, clock: Optional[Callable[[], float]] = None) -> None` [constructor] (pyssp/engine/runtime.py:56)
- `_on_position_changed(self, session_id: PlaybackSessionId, value: int) -> None` [method] (pyssp/engine/runtime.py:182)
- `_on_duration_changed(self, session_id: PlaybackSessionId, value: int) -> None` [method] (pyssp/engine/runtime.py:189)
- `_on_state_changed(self, session_id: PlaybackSessionId, value: int) -> None` [method] (pyssp/engine/runtime.py:196)
- `_transport_snapshot_locked(self) -> TransportSnapshot` [method] (pyssp/engine/runtime.py:210)
- `_record_is_active(record: _SessionRecord) -> bool` [staticmethod] (pyssp/engine/runtime.py:236)
