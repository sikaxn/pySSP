# `pyssp/settings_store.py`

- Source: `pyssp/settings_store.py`
- Module path: `pyssp.settings_store`
- API entries: `52`

## Module Docstring

No module docstring.

## Constants

### Public

- `WINDOW_LAYOUT_MAIN_GRID_COLS` [constant] (pyssp/settings_store.py:162)
  Detail: Value: 4
- `WINDOW_LAYOUT_MAIN_GRID_ROWS` [constant] (pyssp/settings_store.py:163)
  Detail: Value: 4
- `WINDOW_LAYOUT_FADE_GRID_COLS` [constant] (pyssp/settings_store.py:164)
  Detail: Value: 3
- `WINDOW_LAYOUT_FADE_GRID_ROWS` [constant] (pyssp/settings_store.py:165)
  Detail: Value: 1
- `WINDOW_LAYOUT_MAIN_ORDER` [constant] (pyssp/settings_store.py:167)
  Detail: Value: ['Cue', 'Multi-Play', 'Go To Playing', 'DSP', 'Loop', 'Next', 'Button Drag', ...
- `WINDOW_LAYOUT_FADE_ORDER` [constant] (pyssp/settings_store.py:187)
  Detail: Value: ['Fade In', 'X', 'Fade Out']
- `WINDOW_LAYOUT_ALL_BUTTONS` [constant] (pyssp/settings_store.py:188)
  Detail: Value: [*WINDOW_LAYOUT_MAIN_ORDER, *WINDOW_LAYOUT_FADE_ORDER]
- `SOUND_BUTTON_VIEW_GRID` [constant] (pyssp/settings_store.py:190)
  Detail: Value: 'grid'
- `SOUND_BUTTON_VIEW_LIST` [constant] (pyssp/settings_store.py:191)
  Detail: Value: 'list'
- `DEFAULT_SOUND_BUTTON_LIST_COLUMN_WIDTHS` [constant] (pyssp/settings_store.py:192)
  Detail: Value: [18, 52, 220, 190, 170, 72, 64, 72, 96, 72, 96]
- `DEFAULT_SOUND_BUTTON_LIST_HIDDEN_COLUMNS` [constant] (pyssp/settings_store.py:193)
  Detail: Value: []

## Functions

### Public

- `default_quick_action_keys() -> list[str]` [function] (pyssp/settings_store.py:13)
- `default_midi_quick_action_bindings() -> list[str]` [function] (pyssp/settings_store.py:31)
- `default_companion_satellite_serial_suffix() -> str` [function] (pyssp/settings_store.py:57)
- `default_stage_display_layout() -> list[str]` [function] (pyssp/settings_store.py:80)
- `default_video_display_lyric_overlay_rect() -> dict[str, int]` [function] (pyssp/settings_store.py:94)
- `default_supported_audio_format_extensions() -> list[str]` [function] (pyssp/settings_store.py:121)
- `default_launchpad_control_bindings() -> list[str]` [function] (pyssp/settings_store.py:141)
- `normalize_sound_button_view_mode(value: object) -> str` [function] (pyssp/settings_store.py:196)
- `clamp_sound_button_grid_columns(value: object) -> int` [function] (pyssp/settings_store.py:201)
- `clamp_sound_button_grid_rows(value: object) -> int` [function] (pyssp/settings_store.py:209)
- `clamp_sound_button_page_slot_cap(value: object) -> int` [function] (pyssp/settings_store.py:217)
- `normalize_sound_button_list_column_widths(value: object) -> list[int]` [function] (pyssp/settings_store.py:225)
- `normalize_sound_button_list_hidden_columns(value: object, *, allowed_keys: Optional[list[str]] = None) -> list[str]` [function] (pyssp/settings_store.py:241)
- `default_window_layout() -> dict[str, object]` [function] (pyssp/settings_store.py:258)
- `normalize_window_layout(values: dict[str, object] | None) -> dict[str, object]` [function] (pyssp/settings_store.py:404)
- `default_stage_display_gadgets() -> dict[str, dict[str, int | bool | str]]` [function] (pyssp/settings_store.py:436)
- `get_settings_path() -> Path` [function] (pyssp/settings_store.py:1020)
- `load_settings() -> AppSettings` [function] (pyssp/settings_store.py:1031)
- `save_settings(settings: AppSettings) -> None` [function] (pyssp/settings_store.py:1043)

### Internal

- `_normalize_quick_action_keys(values: list[str]) -> list[str]` [function] (pyssp/settings_store.py:23)
- `_normalize_midi_quick_action_bindings(values: list[str]) -> list[str]` [function] (pyssp/settings_store.py:35)
- `_encode_ascii_setting(value: str) -> str` [function] (pyssp/settings_store.py:42)
- `_decode_ascii_setting(value: str) -> str` [function] (pyssp/settings_store.py:46)
- `_normalize_companion_satellite_serial_suffix(raw: object) -> str` [function] (pyssp/settings_store.py:62)
- `_normalize_companion_satellite_render_mode(raw: object) -> str` [function] (pyssp/settings_store.py:70)
- `_normalize_companion_command_mode(raw: object) -> str` [function] (pyssp/settings_store.py:75)
- `_normalize_video_display_lyric_overlay_rect(value: object) -> dict[str, int]` [function] (pyssp/settings_store.py:103)
- `_normalize_supported_audio_format_extensions(values: list[str]) -> list[str]` [function] (pyssp/settings_store.py:125)
- `_normalize_window_layout_items(values: list[dict[str, object]] | None, valid_buttons: set[str], cols: int, rows: int) -> list[dict[str, int | str]]` [function] (pyssp/settings_store.py:287)
- `_convert_legacy_window_layout(values: dict[str, object]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str], bool]` [function] (pyssp/settings_store.py:356)
- `_normalize_stage_display_gadgets(values: dict[str, dict[str, object]] | None, fallback_layout: list[str] | None = None, fallback_visibility: dict[str, bool] | None = None) -> dict[str, dict[str, int | bool | str]]` [function] (pyssp/settings_store.py:540)
- `_from_parser(parser: configparser.ConfigParser) -> AppSettings` [function] (pyssp/settings_store.py:1506)
- `_seed_from_ssp_inf(ssp_inf_path: Path) -> AppSettings` [function] (pyssp/settings_store.py:2477)
- `_get_bool(section, key: str, default: bool) -> bool` [function] (pyssp/settings_store.py:2518)
- `_get_int(section, key: str, default: int) -> int` [function] (pyssp/settings_store.py:2523)
- `_get_float(section, key: str, default: float) -> float` [function] (pyssp/settings_store.py:2530)
- `_get_yes_no_bool(section, key: str, default: bool) -> bool` [function] (pyssp/settings_store.py:2537)
- `_clamp_int(value: int, low: int, high: int) -> int` [function] (pyssp/settings_store.py:2546)
- `_clamp_float(value: float, low: float, high: float) -> float` [function] (pyssp/settings_store.py:2550)
- `_coerce_hex(value: str, fallback: str) -> str` [function] (pyssp/settings_store.py:2554)

## Classes

### `AppSettings`

- Defined at `pyssp/settings_store.py:585`
