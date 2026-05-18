# `pyssp/audio_service.py`

- Source: `pyssp/audio_service.py`
- Module path: `pyssp.audio_service`
- API entries: `7`

## Module Docstring

No module docstring.

## Functions

### Internal

- `_build_media_payload(source: Any, dsp_config: Optional[DSPConfig], request_id: int) -> dict` [function] (pyssp/audio_service.py:585)
- `_payload_source(payload: dict) -> Any` [function] (pyssp/audio_service.py:595)

## Classes

### `AudioPlayerStateSnapshot`

- Defined at `pyssp/audio_service.py:17`

### `AudioStateCache`

- Defined at `pyssp/audio_service.py:25`

#### Public Members

- `ensure(self, player_id: str) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:29)
- `remove(self, player_id: str) -> None` [method] (pyssp/audio_service.py:37)
- `snapshot(self, player_id: str) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:40)
- `update_state(self, player_id: str, state: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:43)
- `update_position(self, player_id: str, position_ms: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:55)
- `update_duration(self, player_id: str, duration_ms: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:67)
- `update_volume(self, player_id: str, volume: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:79)
- `active_playing_ids(self) -> set[str]` [method] (pyssp/audio_service.py:91)

#### Internal Members

- `__init__(self) -> None` [constructor] (pyssp/audio_service.py:26)

### `AudioService`

- Defined at `pyssp/audio_service.py:99`
- Bases: QObject

#### Public Members

- `handle_command(self, player_id: str, command: str, payload: object, result_queue: object) -> None` [method] (pyssp/audio_service.py:107)

#### Internal Members

- `__init__(self, runtime: Optional[MediaRuntime] = None) -> None` [constructor] (pyssp/audio_service.py:127)
- `_player(self, player_id: str) -> ExternalMediaPlayer` [method] (pyssp/audio_service.py:131)
- `_dispatch(self, player_id: str, command: str, payload: dict)` [method] (pyssp/audio_service.py:134)

### `AudioServiceController`

- Defined at `pyssp/audio_service.py:245`
- Bases: QObject

#### Public Members

- `create_player(self, parent: Optional[QObject] = None) -> 'AudioPlayerProxy'` [method] (pyssp/audio_service.py:269)
- `call(self, player_id: str, command: str, payload: Optional[dict] = None, timeout: float = 2.0)` [method] (pyssp/audio_service.py:276)
- `post(self, player_id: str, command: str, payload: Optional[dict] = None) -> None` [method] (pyssp/audio_service.py:286)
- `request_async(self, player_id: str, command: str, payload: Optional[dict] = None) -> Future` [method] (pyssp/audio_service.py:289)
- `shutdown(self) -> None` [method] (pyssp/audio_service.py:296)
- `transport_snapshot(self) -> TransportSnapshot` [method] (pyssp/audio_service.py:305)
- `engine_diagnostics_snapshot(self) -> EngineDiagnosticsSnapshot` [method] (pyssp/audio_service.py:317)
- `set_multi_play_enabled(self, enabled: bool) -> None` [method] (pyssp/audio_service.py:334)
- `runtime_session_snapshots(self) -> tuple[RuntimeSessionSnapshot, ...]` [method] (pyssp/audio_service.py:337)
- `set_session_slot_key(self, player_id: str, slot_key: Optional[tuple[str, int, int]]) -> None` [method] (pyssp/audio_service.py:345)

#### Internal Members

- `__init__(self, parent: Optional[QObject] = None, runtime: Optional[MediaRuntime] = None) -> None` [constructor] (pyssp/audio_service.py:252)
- `_on_service_position_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:349)
- `_on_service_duration_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:353)
- `_on_service_state_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:357)
- `_on_command_result_ready(self, token: int, ok: bool, value: object) -> None` [method] (pyssp/audio_service.py:361)

### `AudioPlayerProxy`

- Defined at `pyssp/audio_service.py:373`
- Bases: QObject

#### Public Members

- `player_id(self) -> str` [property] (pyssp/audio_service.py:399)
- `setNotifyInterval(self, interval_ms: int) -> None` [method] (pyssp/audio_service.py:408)
- `setMedia(self, source: Any, dsp_config: Optional[DSPConfig] = None) -> None` [method] (pyssp/audio_service.py:411)
- `setMediaAsync(self, source: Any, dsp_config: Optional[DSPConfig] = None) -> int` [method] (pyssp/audio_service.py:414)
- `setDSPConfig(self, dsp_config: DSPConfig) -> None` [method] (pyssp/audio_service.py:428)
- `play(self) -> None` [method] (pyssp/audio_service.py:431)
- `pause(self) -> None` [method] (pyssp/audio_service.py:436)
- `stop(self) -> None` [method] (pyssp/audio_service.py:441)
- `state(self) -> int` [method] (pyssp/audio_service.py:448)
- `setPosition(self, position_ms: int) -> None` [method] (pyssp/audio_service.py:451)
- `position(self) -> int` [method] (pyssp/audio_service.py:456)
- `enginePositionMs(self) -> int` [method] (pyssp/audio_service.py:459)
- `duration(self) -> int` [method] (pyssp/audio_service.py:462)
- `setVolume(self, volume: int) -> None` [method] (pyssp/audio_service.py:465)
- `volume(self) -> int` [method] (pyssp/audio_service.py:470)
- `setMasterVolume(self, volume: int) -> None` [method] (pyssp/audio_service.py:473)
- `masterVolume(self) -> int` [method] (pyssp/audio_service.py:476)
- `meterLevels(self) -> Tuple[float, float]` [method] (pyssp/audio_service.py:482)
- `sampleRate(self) -> int` [method] (pyssp/audio_service.py:485)
- `outputBlockSize(self) -> int` [method] (pyssp/audio_service.py:491)
- `takeOutputFrames(self, max_frames: int = 0, mode: str = 'post_fader')` [method] (pyssp/audio_service.py:497)
- `outputTapFrameCounts(self) -> Dict[str, int]` [method] (pyssp/audio_service.py:508)
- `waveformPeaks(self, sample_count: int = 1024)` [method] (pyssp/audio_service.py:517)
- `waveformPeaksAsync(self, sample_count: int = 1024)` [method] (pyssp/audio_service.py:520)
- `deleteLater(self) -> None` [method] (pyssp/audio_service.py:553)

#### Internal Members

- `__init__(self, controller: AudioServiceController, player_id: str, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/audio_service.py:383)
- `_call(self, command: str, payload: Optional[dict] = None, timeout: float = 2.0)` [method] (pyssp/audio_service.py:402)
- `_post(self, command: str, payload: Optional[dict] = None) -> None` [method] (pyssp/audio_service.py:405)
- `_on_position_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:561)
- `_on_duration_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:567)
- `_on_state_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:573)
- `_on_media_load_finished(self, player_id: str, request_id: int, ok: bool, error: str) -> None` [method] (pyssp/audio_service.py:579)
