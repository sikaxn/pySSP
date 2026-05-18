# `pyssp/ui/automation_script_editor_dialog.py`

- Source: `pyssp/ui/automation_script_editor_dialog.py`
- Module path: `pyssp.ui.automation_script_editor_dialog`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `AutomationScriptEditorDialog`

- Defined at `pyssp/ui/automation_script_editor_dialog.py:78`
- Bases: QDialog

#### Public Members

- `closeEvent(self, event) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:558)
- `done(self, result: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:566)

#### Internal Members

- `__init__(self, *, script_path: str, audio_path: str, audio_source: object, title: str, lyric_path: str = '', cue_start_ms: Optional[int] = None, cue_end_ms: Optional[int] = None, companion_payload: Optional[dict] = None, internal_target_catalog: Optional[dict] = None, hide_black_empty: bool = True, show_lyric_default: bool = False, on_show_lyric_changed: Optional[Callable[[bool], None]] = None, language: str = 'en', stop_host_playback: Optional[Callable[[], None]] = None, parent = None) -> None` [constructor] (pyssp/ui/automation_script_editor_dialog.py:79)
- `_load_script(self) -> AutomationScript` [method] (pyssp/ui/automation_script_editor_dialog.py:574)
- `_load_lyric_lines(self) -> List[LyricLine]` [method] (pyssp/ui/automation_script_editor_dialog.py:592)
- `_stop_preview_player(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:600)
- `_request_waveform_refresh(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:606)
- `_set_loading_state(self, loading: bool) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:611)
- `_load_preview_media(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:619)
- `_poll_media_preload_state(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:637)
- `_finalize_media_load(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:652)
- `_on_media_load_finished(self, request_id: int, ok: bool, _error: str) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:658)
- `_on_duration_changed(self, duration: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:671)
- `_on_state_changed(self, _state: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:677)
- `_on_position_changed(self, position: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:680)
- `_refresh_transport_times(self, position_ms: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:687)
- `_refresh_cue_indicator(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:695)
- `_play(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:698)
- `_stop(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:709)
- `_on_slider_pressed(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:713)
- `_on_slider_released(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:716)
- `_on_slider_value_changed(self, value: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:720)
- `_selected_tree_item(self) -> Optional[QTreeWidgetItem]` [method] (pyssp/ui/automation_script_editor_dialog.py:725)
- `_on_show_lyric_toggled(self, checked: bool) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:729)
- `_selected_row_data(self) -> Optional[dict]` [method] (pyssp/ui/automation_script_editor_dialog.py:737)
- `_selected_cue(self) -> Optional[AutomationScriptCue]` [method] (pyssp/ui/automation_script_editor_dialog.py:744)
- `_selected_command_index_in_cue(self) -> int` [method] (pyssp/ui/automation_script_editor_dialog.py:751)
- `_cue_for_time(self, time_ms: int) -> Optional[AutomationScriptCue]` [method] (pyssp/ui/automation_script_editor_dialog.py:760)
- `_ensure_cue(self, time_ms: int) -> AutomationScriptCue` [method] (pyssp/ui/automation_script_editor_dialog.py:767)
- `_rebuild_table(self, selected_time_ms: Optional[int] = None, selected_command_index: int = -1) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:777)
- `_tint_tree_item(self, item: QTreeWidgetItem, color: QColor) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:882)
- `_set_active_row(self, row: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:886)
- `_highlight_row_for_position(self, position_ms: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:906)
- `_on_tree_clicked(self, item: QTreeWidgetItem, _column: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:918)
- `_on_tree_selection_changed(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:925)
- `_refresh_cue_editor(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:929)
- `_refresh_action_buttons(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:949)
- `_add_cue_at_current(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:965)
- `_add_cue_at_selected_lyric(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:969)
- `_delete_selected_cue(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:976)
- `_on_cue_comment_changed(self, text: str) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:983)
- `_on_cue_timestamp_edited(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:992)
- `_shift_selected_cue_time(self, delta_ms: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1004)
- `_move_cue_to_time(self, cue: AutomationScriptCue, target_ms: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1010)
- `_apply_command_filters(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1030)
- `_find_command_row(self, location: str) -> int` [method] (pyssp/ui/automation_script_editor_dialog.py:1074)
- `_selected_command_location_from_table(self) -> str` [method] (pyssp/ui/automation_script_editor_dialog.py:1084)
- `_selected_command_text_from_table(self) -> str` [method] (pyssp/ui/automation_script_editor_dialog.py:1093)
- `_populate_internal_command_list(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1102)
- `_page_label_for_target(self, group: str, page_number: int) -> str` [method] (pyssp/ui/automation_script_editor_dialog.py:1111)
- `_button_label_for_target(self, group: str, page_number: int, slot_number: int) -> str` [method] (pyssp/ui/automation_script_editor_dialog.py:1116)
- `_refresh_internal_target_page_choices(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1121)
- `_refresh_internal_target_slot_choices(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1132)
- `_selected_internal_command_id(self) -> str` [method] (pyssp/ui/automation_script_editor_dialog.py:1147)
- `_selected_internal_params(self, command_id: str) -> dict` [method] (pyssp/ui/automation_script_editor_dialog.py:1153)
- `_refresh_internal_form_visibility(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1186)
- `_build_selected_command_spec(self) -> AutomationCommandSpec` [method] (pyssp/ui/automation_script_editor_dialog.py:1262)
- `_sync_selected_command(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1292)
- `_on_location_mode_changed(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1307)
- `_selected_internal_target_value(self, command_id: str) -> str` [method] (pyssp/ui/automation_script_editor_dialog.py:1320)
- `_apply_internal_target_value(self, command_id: str, value: str) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1330)
- `_parse_internal_target_value(command_id: str, value: str) -> Optional[tuple[str, int, Optional[int], str]]` [staticmethod] (pyssp/ui/automation_script_editor_dialog.py:1358)
- `_add_selected_command_to_current_cue(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1380)
- `_remove_selected_command(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1403)
- `_move_selected_command(self, delta: int) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1415)
- `_refresh_selected_cue_row(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1428)
- `_save(self) -> None` [method] (pyssp/ui/automation_script_editor_dialog.py:1446)
- `_lyric_text_for_time(self, time_ms: int) -> str` [method] (pyssp/ui/automation_script_editor_dialog.py:1463)
- `_format_clock_time(ms: int) -> str` [staticmethod] (pyssp/ui/automation_script_editor_dialog.py:1470)
- `_format_timestamp(ms: int) -> str` [staticmethod] (pyssp/ui/automation_script_editor_dialog.py:1478)
- `_parse_timestamp(value: str) -> Optional[int]` [staticmethod] (pyssp/ui/automation_script_editor_dialog.py:1487)
