# `pyssp/audio_runtime.py`

- Source: `pyssp/audio_runtime.py`
- Module path: `pyssp.audio_runtime`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `PlayerRuntimeRecord`

- Defined at `pyssp/audio_runtime.py:11`

### `PlaybackRuntimeTracker`

- Defined at `pyssp/audio_runtime.py:17`
- Summary: Track per-playback runtime ids without reusing ids for active sessions.

#### Public Members

- `mark_started(self, player: Any, slot_key: SlotKey) -> int` [method] (pyssp/audio_runtime.py:24)
- `clear(self, player: Any) -> Optional[PlayerRuntimeRecord]` [method] (pyssp/audio_runtime.py:34)
- `clear_all(self) -> None` [method] (pyssp/audio_runtime.py:37)
- `runtime_id_for(self, player: Any) -> Optional[int]` [method] (pyssp/audio_runtime.py:40)
- `slot_key_for(self, player: Any) -> Optional[SlotKey]` [method] (pyssp/audio_runtime.py:46)
- `oldest_active_player(self, players: Iterable[Any]) -> Optional[Any]` [method] (pyssp/audio_runtime.py:52)
- `newest_active_player(self, players: Iterable[Any]) -> Optional[Any]` [method] (pyssp/audio_runtime.py:64)
- `timecode_player(self, players: Iterable[Any], multi_play_enabled: bool) -> Optional[Any]` [method] (pyssp/audio_runtime.py:76)

#### Internal Members

- `__init__(self) -> None` [constructor] (pyssp/audio_runtime.py:20)
