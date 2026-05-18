# `pyssp/audio_service.py`

- Source: `pyssp/audio_service.py`
- Module path: `pyssp.audio_service`
- API entries: `7`

## Module Docstring

No module docstring.

## Functions

### Internal

- `_build_media_payload(source: Any, dsp_config: Optional[DSPConfig], request_id: int) -> dict` [function] (pyssp/audio_service.py:541)
- `_payload_source(payload: dict) -> Any` [function] (pyssp/audio_service.py:551)

## Classes

### `AudioPlayerStateSnapshot`

- Defined at `pyssp/audio_service.py:16`

### `AudioStateCache`

- Defined at `pyssp/audio_service.py:24`

#### Public Members

- `ensure(self, player_id: str) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:28)
- `remove(self, player_id: str) -> None` [method] (pyssp/audio_service.py:36)
- `snapshot(self, player_id: str) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:39)
- `update_state(self, player_id: str, state: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:42)
- `update_position(self, player_id: str, position_ms: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:54)
- `update_duration(self, player_id: str, duration_ms: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:66)
- `update_volume(self, player_id: str, volume: int) -> AudioPlayerStateSnapshot` [method] (pyssp/audio_service.py:78)
- `active_playing_ids(self) -> set[str]` [method] (pyssp/audio_service.py:90)

#### Internal Members

- `__init__(self) -> None` [constructor] (pyssp/audio_service.py:25)

### `AudioService`

- Defined at `pyssp/audio_service.py:98`
- Bases: QObject

#### Public Members

- `handle_command(self, player_id: str, command: str, payload: object, result_queue: object) -> None` [method] (pyssp/audio_service.py:106)

#### Internal Members

- `__init__(self) -> None` [constructor] (pyssp/audio_service.py:126)
- `_player(self, player_id: str) -> ExternalMediaPlayer` [method] (pyssp/audio_service.py:130)
- `_dispatch(self, player_id: str, command: str, payload: dict)` [method] (pyssp/audio_service.py:136)

### `AudioServiceController`

- Defined at `pyssp/audio_service.py:245`
- Bases: QObject

#### Public Members

- `create_player(self, parent: Optional[QObject] = None) -> 'AudioPlayerProxy'` [method] (pyssp/audio_service.py:269)
- `call(self, player_id: str, command: str, payload: Optional[dict] = None, timeout: float = 2.0)` [method] (pyssp/audio_service.py:276)
- `post(self, player_id: str, command: str, payload: Optional[dict] = None) -> None` [method] (pyssp/audio_service.py:286)
- `request_async(self, player_id: str, command: str, payload: Optional[dict] = None) -> Future` [method] (pyssp/audio_service.py:289)
- `shutdown(self) -> None` [method] (pyssp/audio_service.py:296)

#### Internal Members

- `__init__(self, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/audio_service.py:252)
- `_on_service_position_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:305)
- `_on_service_duration_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:309)
- `_on_service_state_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:313)
- `_on_command_result_ready(self, token: int, ok: bool, value: object) -> None` [method] (pyssp/audio_service.py:317)

### `AudioPlayerProxy`

- Defined at `pyssp/audio_service.py:329`
- Bases: QObject

#### Public Members

- `player_id(self) -> str` [property] (pyssp/audio_service.py:355)
- `setNotifyInterval(self, interval_ms: int) -> None` [method] (pyssp/audio_service.py:364)
- `setMedia(self, source: Any, dsp_config: Optional[DSPConfig] = None) -> None` [method] (pyssp/audio_service.py:367)
- `setMediaAsync(self, source: Any, dsp_config: Optional[DSPConfig] = None) -> int` [method] (pyssp/audio_service.py:370)
- `setDSPConfig(self, dsp_config: DSPConfig) -> None` [method] (pyssp/audio_service.py:384)
- `play(self) -> None` [method] (pyssp/audio_service.py:387)
- `pause(self) -> None` [method] (pyssp/audio_service.py:392)
- `stop(self) -> None` [method] (pyssp/audio_service.py:397)
- `state(self) -> int` [method] (pyssp/audio_service.py:404)
- `setPosition(self, position_ms: int) -> None` [method] (pyssp/audio_service.py:407)
- `position(self) -> int` [method] (pyssp/audio_service.py:412)
- `enginePositionMs(self) -> int` [method] (pyssp/audio_service.py:415)
- `duration(self) -> int` [method] (pyssp/audio_service.py:418)
- `setVolume(self, volume: int) -> None` [method] (pyssp/audio_service.py:421)
- `volume(self) -> int` [method] (pyssp/audio_service.py:426)
- `setMasterVolume(self, volume: int) -> None` [method] (pyssp/audio_service.py:429)
- `masterVolume(self) -> int` [method] (pyssp/audio_service.py:432)
- `meterLevels(self) -> Tuple[float, float]` [method] (pyssp/audio_service.py:438)
- `sampleRate(self) -> int` [method] (pyssp/audio_service.py:441)
- `outputBlockSize(self) -> int` [method] (pyssp/audio_service.py:447)
- `takeOutputFrames(self, max_frames: int = 0, mode: str = 'post_fader')` [method] (pyssp/audio_service.py:453)
- `outputTapFrameCounts(self) -> Dict[str, int]` [method] (pyssp/audio_service.py:464)
- `waveformPeaks(self, sample_count: int = 1024)` [method] (pyssp/audio_service.py:473)
- `waveformPeaksAsync(self, sample_count: int = 1024)` [method] (pyssp/audio_service.py:476)
- `deleteLater(self) -> None` [method] (pyssp/audio_service.py:509)

#### Internal Members

- `__init__(self, controller: AudioServiceController, player_id: str, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/audio_service.py:339)
- `_call(self, command: str, payload: Optional[dict] = None, timeout: float = 2.0)` [method] (pyssp/audio_service.py:358)
- `_post(self, command: str, payload: Optional[dict] = None) -> None` [method] (pyssp/audio_service.py:361)
- `_on_position_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:517)
- `_on_duration_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:523)
- `_on_state_changed(self, player_id: str, value: int) -> None` [method] (pyssp/audio_service.py:529)
- `_on_media_load_finished(self, player_id: str, request_id: int, ok: bool, error: str) -> None` [method] (pyssp/audio_service.py:535)
