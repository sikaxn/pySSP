# `pyssp/ui/lyric_editor_dialog.py`

- Source: `pyssp/ui/lyric_editor_dialog.py`
- Module path: `pyssp.ui.lyric_editor_dialog`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `LyricEditorDialog`

- Defined at `pyssp/ui/lyric_editor_dialog.py:37`
- Bases: QDialog

#### Public Members

- `closeEvent(self, event) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:230)
- `done(self, result: int) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:238)

#### Internal Members

- `__init__(self, *, lyric_path: str, audio_path: str, audio_source: object, title: str, language: str = 'en', preferred_mode: str = 'srt', cue_start_ms: Optional[int] = None, cue_end_ms: Optional[int] = None, stop_host_playback: Optional[Callable[[], None]] = None, parent = None) -> None` [constructor] (pyssp/ui/lyric_editor_dialog.py:38)
- `_request_waveform_refresh(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:246)
- `_stop_preview_player(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:251)
- `_set_loading_state(self, loading: bool) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:257)
- `_load_preview_media(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:268)
- `_poll_media_preload_state(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:286)
- `_finalize_media_load(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:302)
- `_on_media_load_finished(self, request_id: int, ok: bool, _error: str) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:308)
- `_load_rows_from_file(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:321)
- `_append_table_row(self, start_ms: int, text: str) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:337)
- `_format_timestamp(self, ms: int) -> str` [method] (pyssp/ui/lyric_editor_dialog.py:343)
- `_parse_timestamp(self, value: str) -> Optional[int]` [method] (pyssp/ui/lyric_editor_dialog.py:356)
- `_read_rows(self) -> Optional[List[Tuple[int, str]]]` [method] (pyssp/ui/lyric_editor_dialog.py:381)
- `_write_lrc(self, rows: List[Tuple[int, str]]) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:396)
- `_write_srt(self, rows: List[Tuple[int, str]]) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:406)
- `_srt_time(ms: int) -> str` [staticmethod] (pyssp/ui/lyric_editor_dialog.py:421)
- `_add_line_at_current(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:429)
- `_toggle_rapid_editor(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:435)
- `_rapid_snapshot(self) -> Tuple[List[Tuple[str, str]], str]` [method] (pyssp/ui/lyric_editor_dialog.py:440)
- `_rapid_restore(self, snapshot: Tuple[List[Tuple[str, str]], str]) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:453)
- `_rapid_take_top_line(self) -> Optional[str]` [method] (pyssp/ui/lyric_editor_dialog.py:464)
- `_rapid_insert(self, *, line_mode: bool) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:475)
- `_rapid_undo(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:490)
- `_replace_current_line_with_blank(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:498)
- `_delete_selected_lines(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:517)
- `_sort_table_by_time(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:523)
- `_on_mode_changed(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:537)
- `_play(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:550)
- `_stop(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:572)
- `_on_slider_pressed(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:578)
- `_on_slider_released(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:581)
- `_on_slider_value_changed(self, value: int) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:585)
- `_on_position_changed(self, pos: int) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:589)
- `_on_duration_changed(self, duration: int) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:596)
- `_on_state_changed(self, _state: int) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:603)
- `_refresh_buttons(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:607)
- `_refresh_transport_times(self, position_ms: int) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:611)
- `_refresh_cue_indicator(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:622)
- `_sync_now_playing_row(self, position_ms: int) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:625)
- `_row_for_position(self, position_ms: int) -> int` [method] (pyssp/ui/lyric_editor_dialog.py:634)
- `_apply_active_row(self, row: int, *, follow: bool) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:657)
- `_hms(ms: int) -> str` [staticmethod] (pyssp/ui/lyric_editor_dialog.py:674)
- `_save(self) -> None` [method] (pyssp/ui/lyric_editor_dialog.py:681)
