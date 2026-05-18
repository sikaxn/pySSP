# `pyssp/ui/cue_point_dialog.py`

- Source: `pyssp/ui/cue_point_dialog.py`
- Module path: `pyssp.ui.cue_point_dialog`
- API entries: `3`

## Module Docstring

No module docstring.

## Functions

### Public

- `format_timecode(ms: int) -> str` [function] (pyssp/ui/cue_point_dialog.py:593)
- `parse_timecode_to_ms(value: str) -> Optional[int]` [function] (pyssp/ui/cue_point_dialog.py:602)

## Classes

### `CuePointDialog`

- Defined at `pyssp/ui/cue_point_dialog.py:29`
- Bases: QDialog

#### Public Members

- `closeEvent(self, event) -> None` [method] (pyssp/ui/cue_point_dialog.py:200)
- `done(self, result: int) -> None` [method] (pyssp/ui/cue_point_dialog.py:206)
- `values(self) -> tuple[Optional[int], Optional[int]]` [method] (pyssp/ui/cue_point_dialog.py:212)

#### Internal Members

- `__init__(self, file_path: str, audio_source: object, title: str, cue_start_ms: Optional[int], cue_end_ms: Optional[int], stop_host_playback: Optional[Callable[[], None]] = None, language: str = 'en', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/cue_point_dialog.py:30)
- `_set_loading_state(self, loading: bool) -> None` [method] (pyssp/ui/cue_point_dialog.py:215)
- `_load_media_preview(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:230)
- `_stop_async_load_watch(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:249)
- `_stop_waveform_watch(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:253)
- `_request_waveform_refresh(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:257)
- `_poll_media_preload_state(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:262)
- `_finalize_media_load(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:278)
- `_on_media_load_finished(self, request_id: int, ok: bool, error: str) -> None` [method] (pyssp/ui/cue_point_dialog.py:287)
- `_play(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:307)
- `_stop(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:323)
- `_preview(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:331)
- `_stop_preview_player(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:349)
- `_on_position_changed(self, pos: int) -> None` [method] (pyssp/ui/cue_point_dialog.py:355)
- `_on_duration_changed(self, duration: int) -> None` [method] (pyssp/ui/cue_point_dialog.py:360)
- `_on_state_changed(self, _state: int) -> None` [method] (pyssp/ui/cue_point_dialog.py:369)
- `_on_slider_pressed(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:374)
- `_on_slider_released(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:377)
- `_on_slider_value_changed(self, value: int) -> None` [method] (pyssp/ui/cue_point_dialog.py:381)
- `_set_start_from_current(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:386)
- `_set_end_from_current(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:394)
- `_reset_start(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:402)
- `_reset_end(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:410)
- `_clear_cues(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:418)
- `_commit_start_timecode(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:427)
- `_commit_end_timecode(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:450)
- `_normalize_cues(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:473)
- `_refresh_timecode_edits(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:487)
- `_effective_bounds(self) -> tuple[int, int]` [method] (pyssp/ui/cue_point_dialog.py:495)
- `_to_relative_ms(self, absolute_ms: int) -> int` [method] (pyssp/ui/cue_point_dialog.py:509)
- `_to_absolute_ms(self, relative_ms: int) -> int` [method] (pyssp/ui/cue_point_dialog.py:515)
- `_apply_jog_bounds(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:521)
- `_refresh_transport_times(self, position_ms: int) -> None` [method] (pyssp/ui/cue_point_dialog.py:532)
- `_refresh_cue_indicator(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:544)
- `_refresh_jog_meta(self, elapsed_ms: int, total_ms: int) -> None` [method] (pyssp/ui/cue_point_dialog.py:547)
- `_enforce_end_limit(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:560)
- `_set_mode(self, mode: str) -> None` [method] (pyssp/ui/cue_point_dialog.py:573)
- `_refresh_transport_buttons(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:577)
- `_save(self) -> None` [method] (pyssp/ui/cue_point_dialog.py:582)
