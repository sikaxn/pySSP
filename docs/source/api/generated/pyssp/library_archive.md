# `pyssp/library_archive.py`

- Source: `pyssp/library_archive.py`
- Module path: `pyssp.library_archive`
- API entries: `34`

## Module Docstring

No module docstring.

## Constants

### Public

- `MANIFEST_MEMBER` [constant] (pyssp/library_archive.py:30)
  Detail: Value: 'manifest.json'
- `SETTINGS_MEMBER` [constant] (pyssp/library_archive.py:31)
  Detail: Value: 'settings.ini'

## Functions

### Public

- `default_unpack_directory(package_path: str) -> str` [function] (pyssp/library_archive.py:301)
- `build_archive_audio_entries(file_paths: list[str], maintain_directory_structure: bool) -> list[PackedAudioEntry]` [function] (pyssp/library_archive.py:312)
- `build_archive_vocal_removed_entries(file_paths: list[str], maintain_directory_structure: bool) -> list[PackedAudioEntry]` [function] (pyssp/library_archive.py:316)
- `build_archive_lyric_entries(file_paths: list[str], maintain_directory_structure: bool) -> list[PackedAudioEntry]` [function] (pyssp/library_archive.py:320)
- `build_archive_automation_script_entries(file_paths: list[str], maintain_directory_structure: bool) -> list[PackedAudioEntry]` [function] (pyssp/library_archive.py:324)
- `build_manifest(set_member_name: str, audio_entries: list[PackedAudioEntry], settings_included: bool, vocal_removed_entries: Optional[list[PackedAudioEntry]] = None, lyric_entries: Optional[list[PackedAudioEntry]] = None, automation_script_entries: Optional[list[PackedAudioEntry]] = None) -> dict` [function] (pyssp/library_archive.py:355)
- `write_manifest(archive: zipfile.ZipFile, manifest: dict) -> None` [function] (pyssp/library_archive.py:406)
- `read_pyssppak_manifest(package_path: str) -> dict` [function] (pyssp/library_archive.py:410)
- `unpack_pyssppak(package_path: str, destination_dir: str, maintain_directory_structure: bool, unpack_lyrics: bool = True, unpack_automation_scripts: bool = True, progress_callback = None, is_cancelled = None) -> UnpackResult` [function] (pyssp/library_archive.py:423)
- `build_unpack_target_path(destination_dir: str, archive_member: str, maintain_directory_structure: bool, used_targets: set[str]) -> str` [function] (pyssp/library_archive.py:554)
- `rewrite_packed_set_paths(set_file_path: str, replacements: dict[str, str], vocal_removed_replacements: Optional[dict[str, str]] = None, lyric_replacements: Optional[dict[str, str]] = None, automation_script_replacements: Optional[dict[str, str]] = None, clear_missing_vocal_removed: bool = False, clear_missing_lyrics: bool = False, clear_missing_automation_scripts: bool = False) -> None` [function] (pyssp/library_archive.py:580)
- `pack_report_row_to_line(row: PackReportRow) -> str` [function] (pyssp/library_archive.py:629)
- `write_pack_report_csv(file_path: str, rows: list[PackReportRow]) -> None` [function] (pyssp/library_archive.py:636)

### Internal

- `_build_archive_entries(file_paths: list[str], maintain_directory_structure: bool, root_prefix: str) -> list[PackedAudioEntry]` [function] (pyssp/library_archive.py:331)
- `_flattened_archive_member(source_path: str, index: int, root_prefix: str = 'audio') -> str` [function] (pyssp/library_archive.py:659)
- `_structured_archive_member(source_path: str, root_prefix: str = 'audio') -> str` [function] (pyssp/library_archive.py:664)
- `_sanitize_segment(value: str) -> str` [function] (pyssp/library_archive.py:680)
- `_unique_target_path(target_path: str, used_targets: set[str]) -> str` [function] (pyssp/library_archive.py:685)
- `_report_progress(callback, current: int, total: int, label: str) -> None` [function] (pyssp/library_archive.py:697)
- `_check_cancelled(is_cancelled) -> None` [function] (pyssp/library_archive.py:702)
- `_extract_to_file(archive: zipfile.ZipFile, member: str, target_path: str) -> str` [function] (pyssp/library_archive.py:707)
- `_normalize_archive_member(member: str) -> str` [function] (pyssp/library_archive.py:715)
- `_read_text_with_fallback(file_path: str) -> tuple[str, str]` [function] (pyssp/library_archive.py:730)

## Classes

### `ArchiveOperationCancelled`

- Defined at `pyssp/library_archive.py:34`
- Bases: Exception

### `PageSelectionItem`

- Defined at `pyssp/library_archive.py:39`

### `PackedAudioEntry`

- Defined at `pyssp/library_archive.py:47`

### `PackReportRow`

- Defined at `pyssp/library_archive.py:54`

### `UnpackDialogResult`

- Defined at `pyssp/library_archive.py:64`

### `UnpackResult`

- Defined at `pyssp/library_archive.py:75`

### `PackAudioLibraryDialog`

- Defined at `pyssp/library_archive.py:85`
- Bases: QDialog

#### Public Members

- `selected_keys(self) -> list[str]` [method] (pyssp/library_archive.py:157)

#### Internal Members

- `__init__(self, items: list[PageSelectionItem], parent = None) -> None` [constructor] (pyssp/library_archive.py:86)
- `_select_all(self) -> None` [method] (pyssp/library_archive.py:145)
- `_deselect_all(self) -> None` [method] (pyssp/library_archive.py:151)

### `UnpackLibraryDialog`

- Defined at `pyssp/library_archive.py:166`
- Bases: QDialog

#### Public Members

- `values(self) -> UnpackDialogResult` [method] (pyssp/library_archive.py:243)

#### Internal Members

- `__init__(self, initial_package_path: str, initial_destination_dir: str, parent = None) -> None` [constructor] (pyssp/library_archive.py:167)
- `_browse_package(self) -> None` [method] (pyssp/library_archive.py:220)
- `_browse_destination(self) -> None` [method] (pyssp/library_archive.py:231)
- `_auto_update_destination_dir(self, package_path: str) -> None` [method] (pyssp/library_archive.py:237)

### `PackReportDialog`

- Defined at `pyssp/library_archive.py:255`
- Bases: QDialog

#### Internal Members

- `__init__(self, rows: list[PackReportRow], default_export_dir: str, parent = None) -> None` [constructor] (pyssp/library_archive.py:256)
- `_export_csv(self) -> None` [method] (pyssp/library_archive.py:286)
