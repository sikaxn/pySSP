# `pyssp/ui/main_window/settings_archive.py`

- Source: `pyssp/ui/main_window/settings_archive.py`
- Module path: `pyssp.ui.main_window.settings_archive`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `SettingsArchiveMixin`

- Defined at `pyssp/ui/main_window/settings_archive.py:9`

#### Internal Members

- `_project_root_path(self) -> str` [method] (pyssp/ui/main_window/settings_archive.py:10)
- `_asset_file_path(self, *parts: str) -> str` [method] (pyssp/ui/main_window/settings_archive.py:13)
- `_help_index_path(self) -> str` [method] (pyssp/ui/main_window/settings_archive.py:27)
- `_help_doc_path(self, filename: str) -> str` [method] (pyssp/ui/main_window/settings_archive.py:41)
- `_default_backup_dir(self) -> str` [method] (pyssp/ui/main_window/settings_archive.py:47)
- `_coerce_bool(value, default: bool = False) -> bool` [staticmethod] (pyssp/ui/main_window/settings_archive.py:51)
- `_coerce_int(value, default: int, minimum: int, maximum: int) -> int` [staticmethod] (pyssp/ui/main_window/settings_archive.py:63)
- `_normalize_stage_display_layout(values: List[str]) -> List[str]` [staticmethod] (pyssp/ui/main_window/settings_archive.py:71)
- `_normalize_stage_display_visibility(values: Dict[str, bool]) -> Dict[str, bool]` [staticmethod] (pyssp/ui/main_window/settings_archive.py:94)
- `_backup_pyssp_settings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:111)
- `_restore_pyssp_settings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:141)
- `_pack_audio_library(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:174)
- `_unpack_audio_library(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:442)
- `_restore_packed_pyssp_settings(self, source_path: str, open_set_path: str = '') -> None` [method] (pyssp/ui/main_window/settings_archive.py:526)
- `_build_pack_page_selection_items(self) -> List[PageSelectionItem]` [method] (pyssp/ui/main_window/settings_archive.py:559)
- `_collect_pack_path_usage(self, selected_pages: set[Tuple[str, int]]) -> Dict[str, dict]` [method] (pyssp/ui/main_window/settings_archive.py:575)
- `_collect_pack_lyric_path_usage(self, selected_pages: set[Tuple[str, int]]) -> Dict[str, dict]` [method] (pyssp/ui/main_window/settings_archive.py:597)
- `_collect_pack_automation_script_path_usage(self, selected_pages: set[Tuple[str, int]]) -> Dict[str, dict]` [method] (pyssp/ui/main_window/settings_archive.py:619)
- `_collect_pack_vocal_removed_path_usage(self, selected_pages: set[Tuple[str, int]]) -> Dict[str, dict]` [method] (pyssp/ui/main_window/settings_archive.py:641)
- `_update_archive_progress(self, progress: QProgressDialog, current: int, total: int, label: str) -> None` [method] (pyssp/ui/main_window/settings_archive.py:663)
- `_encode_pack_page_key(group: str, page_index: int) -> str` [staticmethod] (pyssp/ui/main_window/settings_archive.py:670)
- `_decode_pack_page_key(value: str) -> Optional[Tuple[str, int]]` [staticmethod] (pyssp/ui/main_window/settings_archive.py:674)
- `_backup_keyboard_hotkey_bindings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:690)
- `_restore_keyboard_hotkey_bindings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:723)
- `_backup_midi_bindings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:775)
- `_restore_midi_bindings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:839)
- `_normalized_hotkey_pair(self, action_key: str) -> tuple[str, str]` [method] (pyssp/ui/main_window/settings_archive.py:977)
- `_normalize_hotkey_text(self, value: str) -> str` [method] (pyssp/ui/main_window/settings_archive.py:985)
- `_key_sequence_from_hotkey_text(self, value: str) -> Optional[QKeySequence]` [method] (pyssp/ui/main_window/settings_archive.py:1004)
- `_modifier_key_from_hotkey_text(self, value: str) -> Optional[int]` [method] (pyssp/ui/main_window/settings_archive.py:1018)
- `_apply_hotkeys(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:1030)
- `_runtime_action_handlers(self) -> Dict[str, Callable[[], None]]` [method] (pyssp/ui/main_window/settings_archive.py:1124)
- `_normalized_midi_pair(self, action_key: str) -> tuple[str, str]` [method] (pyssp/ui/main_window/settings_archive.py:1156)
- `_normalize_midi_input_selectors(self, selectors: List[str]) -> List[str]` [method] (pyssp/ui/main_window/settings_archive.py:1160)
- `_apply_midi_bindings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:1176)
- `_apply_launchpad_bindings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:1216)
- `_restore_last_set_on_startup(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:1251)
- `_has_any_custom_cues(self) -> bool` [method] (pyssp/ui/main_window/settings_archive.py:1262)
- `_save_settings(self) -> None` [method] (pyssp/ui/main_window/settings_archive.py:1270)
