# `pyssp/set_loader.py`

- Source: `pyssp/set_loader.py`
- Module path: `pyssp.set_loader`
- API entries: `31`

## Module Docstring

No module docstring.

## Constants

### Public

- `GROUPS` [constant] (pyssp/set_loader.py:31)
  Detail: Value: list('ABCDEFGHIJ')
- `PAGE_COUNT` [constant] (pyssp/set_loader.py:32)
  Detail: Value: 18
- `SLOTS_PER_PAGE` [constant] (pyssp/set_loader.py:33)
  Detail: Value: 48
- `SECTION_RE` [constant] (pyssp/set_loader.py:35)
  Detail: Value: re.compile('^Page([A-J]?)(\\d+)$', re.IGNORECASE)
- `CUE_SECTION_RE` [constant] (pyssp/set_loader.py:36)
  Detail: Value: re.compile('^PageQ(\\d+)$', re.IGNORECASE)

## Functions

### Public

- `load_set_file(file_path: str) -> SetLoadResult` [function] (pyssp/set_loader.py:81)
- `parse_time_string_to_ms(value: str) -> int` [function] (pyssp/set_loader.py:245)
- `parse_delphi_color(value: str) -> Optional[str]` [function] (pyssp/set_loader.py:416)
- `parse_timecode_offset_ms(value: str) -> Optional[int]` [function] (pyssp/set_loader.py:594)
- `format_timecode_offset_hhmmss(seconds: Optional[int], fps: float = 30.0) -> Optional[str]` [function] (pyssp/set_loader.py:598)
- `normalize_slot_timecode_timeline_mode(value: str) -> str` [function] (pyssp/set_loader.py:624)

### Internal

- `_read_text_with_fallback(file_path: str) -> tuple[str, str]` [function] (pyssp/set_loader.py:216)
- `_normalize_set_path_string(value: str) -> str` [function] (pyssp/set_loader.py:226)
- `_parse_page_section(name: str) -> Optional[tuple[str, int]]` [function] (pyssp/set_loader.py:235)
- `_parse_utility_slot_from_section(section: configparser.SectionProxy, slot_index: int) -> Optional[SetSlotData]` [function] (pyssp/set_loader.py:260)
- `_parse_automation_slot_from_section(section: configparser.SectionProxy, slot_index: int) -> Optional[SetSlotData]` [function] (pyssp/set_loader.py:325)
- `_parse_time_signature_part(value: str, index: int) -> int` [function] (pyssp/set_loader.py:373)
- `_parse_sound_button_automation_from_section(section: configparser.SectionProxy, slot_index: int) -> Optional[SoundButtonAutomationConfig]` [function] (pyssp/set_loader.py:383)
- `_is_played_activity(value: str) -> bool` [function] (pyssp/set_loader.py:459)
- `_parse_volume_pct(value: str) -> Optional[int]` [function] (pyssp/set_loader.py:465)
- `_parse_cue_points(start_value: str, end_value: str, duration_ms: int) -> tuple[Optional[int], Optional[int]]` [function] (pyssp/set_loader.py:475)
- `_parse_cue_points_from_section(section: configparser.SectionProxy, slot_index: int, duration_ms: int) -> tuple[Optional[int], Optional[int], bool]` [function] (pyssp/set_loader.py:499)
- `_normalize_cue_points(start_ms: Optional[int], end_ms: Optional[int], duration_ms: int) -> tuple[Optional[int], Optional[int]]` [function] (pyssp/set_loader.py:518)
- `_parse_cue_time_string_to_ms(value: str) -> Optional[int]` [function] (pyssp/set_loader.py:537)
- `_parse_non_negative_int(value: str) -> Optional[int]` [function] (pyssp/set_loader.py:561)
- `_parse_sound_hotkey(value: str) -> str` [function] (pyssp/set_loader.py:573)
- `_parse_sound_midi_hotkey(value: str) -> str` [function] (pyssp/set_loader.py:590)
- `_parse_timecode_offset_ms(value: str) -> Optional[int]` [function] (pyssp/set_loader.py:628)
- `_parse_slot_timecode_timeline_mode(value: str) -> str` [function] (pyssp/set_loader.py:647)

## Classes

### `SetSlotData`

- Defined at `pyssp/set_loader.py:40`

### `SetLoadResult`

- Defined at `pyssp/set_loader.py:69`
