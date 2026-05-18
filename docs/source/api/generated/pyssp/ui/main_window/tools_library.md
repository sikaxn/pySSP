# `pyssp/ui/main_window/tools_library.py`

- Source: `pyssp/ui/main_window/tools_library.py`
- Module path: `pyssp.ui.main_window.tools_library`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `ToolsLibraryMixin`

- Defined at `pyssp/ui/main_window/tools_library.py:20`

#### Internal Members

- `_launchpad_cheatsheet_action_label(self, action_key: str) -> str` [method] (pyssp/ui/main_window/tools_library.py:54)
- `_launchpad_cheatsheet_cell(self, title: str, body: str, role: str = 'normal') -> QLabel` [method] (pyssp/ui/main_window/tools_library.py:58)
- `_launchpad_cheatsheet_control_text(self, control_index: int) -> tuple[str, str, str]` [method] (pyssp/ui/main_window/tools_library.py:78)
- `_build_launchpad_cheatsheet_grid(self, *, shift_layer: bool) -> QWidget` [method] (pyssp/ui/main_window/tools_library.py:95)
- `_populate_launchpad_cheatsheet_tabs(self, tabs: QTabWidget) -> None` [method] (pyssp/ui/main_window/tools_library.py:141)
- `_show_launchpad_cheatsheet(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:150)
- `_apply_launchpad_mapping_to_current_page(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:203)
- `_sports_sounds_pro_folder(self) -> str` [method] (pyssp/ui/main_window/tools_library.py:263)
- `_page_library_folder_path(self) -> str` [method] (pyssp/ui/main_window/tools_library.py:271)
- `_page_display_name(self, group: str, page_index: int) -> str` [method] (pyssp/ui/main_window/tools_library.py:274)
- `_iter_all_sound_button_entries(self, include_cue: bool = True) -> List[dict]` [method] (pyssp/ui/main_window/tools_library.py:280)
- `_iter_all_sound_button_slot_refs(self, include_cue: bool = True) -> List[dict]` [method] (pyssp/ui/main_window/tools_library.py:315)
- `_find_generated_vocal_removed_file(self, source_path: str, directory_cache: Optional[Dict[str, Dict[str, str]]] = None) -> str` [method] (pyssp/ui/main_window/tools_library.py:343)
- `_show_vocal_removed_failures(self, title: str, failures: List[str]) -> None` [method] (pyssp/ui/main_window/tools_library.py:380)
- `_print_lines(self, title: str, lines: List[str]) -> None` [method] (pyssp/ui/main_window/tools_library.py:403)
- `_open_tool_window(self, key: str, title: str, double_click_action: str, show_play_button: bool) -> ToolListWindow` [method] (pyssp/ui/main_window/tools_library.py:415)
- `_tool_match_to_line(self, match: dict) -> str` [method] (pyssp/ui/main_window/tools_library.py:440)
- `_tool_hotkey_match_to_line(self, match: dict) -> str` [method] (pyssp/ui/main_window/tools_library.py:450)
- `_tool_midi_match_to_line(self, match: dict) -> str` [method] (pyssp/ui/main_window/tools_library.py:456)
- `_tool_export_matches(self, key: str, export_format: str, base_name: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:462)
- `_print_tool_window(self, key: str, title: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:489)
- `_print_hotkey_tool_window(self, key: str, title: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:496)
- `_print_midi_tool_window(self, key: str, title: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:503)
- `_write_csv_rows(self, file_path: str, header: str, matches: List[dict]) -> None` [method] (pyssp/ui/main_window/tools_library.py:510)
- `_tool_export_sound_hotkey_matches(self, key: str, export_format: str, base_name: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:531)
- `_tool_export_sound_midi_matches(self, key: str, export_format: str, base_name: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:575)
- `_run_duplicate_check(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:619)
- `_run_verify_sound_buttons(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:661)
- `_scan_sound_button_lyrics(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:762)
- `_remove_all_linked_lyric_files(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:850)
- `_scan_sound_button_automation_scripts(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:905)
- `_remove_all_linked_automation_scripts(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1005)
- `_bulk_generate_vocal_removed_tracks(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1048)
- `_link_unlinked_vocal_removed_tracks(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1194)
- `_remove_all_linked_vocal_removed_files(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1304)
- `_diagnose_sound_button_issue(self, file_path: str) -> Optional[str]` [method] (pyssp/ui/main_window/tools_library.py:1350)
- `_path_safety_reason(self, file_path: str) -> Optional[str]` [method] (pyssp/ui/main_window/tools_library.py:1378)
- `_classify_audio_decode_issue(self, file_path: str, exc: Exception) -> str` [method] (pyssp/ui/main_window/tools_library.py:1383)
- `_audio_file_dialog_filter(self) -> str` [method] (pyssp/ui/main_window/tools_library.py:1423)
- `_verify_audio_files_before_add(self, file_paths: List[str]) -> List[dict]` [method] (pyssp/ui/main_window/tools_library.py:1429)
- `_show_audio_add_verification_results(self, matches: List[dict]) -> None` [method] (pyssp/ui/main_window/tools_library.py:1458)
- `_disable_playlist_on_all_pages(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1488)
- `_reset_all_pages_state(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1504)
- `_show_page_library_folder_path(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1525)
- `_show_set_file_and_path(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1536)
- `_export_page_and_sound_buttons_to_excel(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1552)
- `_list_sound_buttons(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1596)
- `_list_sound_button_hotkeys(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1622)
- `_list_sound_device_midi_mappings(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1655)
- `_refresh_list_sound_buttons_window(self, selected_order: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:1691)
- `_refresh_list_sound_button_hotkeys_window(self, selected_order: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:1712)
- `_refresh_list_sound_device_midi_mappings_window(self, selected_order: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:1744)
- `_browse_export_directory(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1776)
- `_run_export_buttons_from_window(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1785)
- `_clear_export_window_ref(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1810)
- `_open_local_path(self, path: str, title: str, error_prefix: str) -> bool` [method] (pyssp/ui/main_window/tools_library.py:1815)
- `_open_directory(self, path: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:1846)
- `_open_settings_folder(self) -> None` [method] (pyssp/ui/main_window/tools_library.py:1852)
- `_reveal_sound_file_in_browser(self, file_path: str) -> None` [method] (pyssp/ui/main_window/tools_library.py:1855)
