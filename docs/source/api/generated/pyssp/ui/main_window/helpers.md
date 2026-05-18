# `pyssp/ui/main_window/helpers.py`

- Source: `pyssp/ui/main_window/helpers.py`
- Module path: `pyssp.ui.main_window.helpers`
- API entries: `11`

## Module Docstring

No module docstring.

## Functions

### Public

- `build_lock_icon(size: int = 18, color: str = '#202020') -> QPixmap` [function] (pyssp/ui/main_window/helpers.py:18)
- `format_time(ms: int) -> str` [function] (pyssp/ui/main_window/helpers.py:54)
- `format_clock_time(ms: int) -> str` [function] (pyssp/ui/main_window/helpers.py:60)
- `format_set_time(ms: int) -> str` [function] (pyssp/ui/main_window/helpers.py:70)
- `wrap_text_lines(value: str, max_chars: int, max_lines: int) -> List[str]` [function] (pyssp/ui/main_window/helpers.py:88)
- `format_sound_button_label(title: str, duration_ms: int, suffix: str, max_chars: int) -> str` [function] (pyssp/ui/main_window/helpers.py:136)
- `clean_set_value(value: str) -> str` [function] (pyssp/ui/main_window/helpers.py:144)
- `to_set_color_value(hex_color: Optional[str]) -> str` [function] (pyssp/ui/main_window/helpers.py:148)
- `elide_text(value: str, max_chars: int) -> str` [function] (pyssp/ui/main_window/helpers.py:163)

### Internal

- `_equal_power_crossfade_volume(start: int, end: int, ratio: float) -> int` [function] (pyssp/ui/main_window/helpers.py:41)
- `_tokenize_wrapped_text(value: str) -> List[str]` [function] (pyssp/ui/main_window/helpers.py:79)
