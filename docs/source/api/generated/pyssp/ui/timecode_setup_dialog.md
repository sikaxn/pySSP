# `pyssp/ui/timecode_setup_dialog.py`

- Source: `pyssp/ui/timecode_setup_dialog.py`
- Module path: `pyssp.ui.timecode_setup_dialog`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `TimecodeOffsetEdit`

- Defined at `pyssp/ui/timecode_setup_dialog.py:23`
- Bases: QLineEdit

#### Public Members

- `parse_offset_ms(cls, value: str, fps: float = 30.0) -> Optional[int]` [classmethod] (pyssp/ui/timecode_setup_dialog.py:34)
- `format_offset_ms(cls, offset_ms: Optional[int], fps: float = 30.0) -> str` [classmethod] (pyssp/ui/timecode_setup_dialog.py:53)
- `set_offset_ms(self, offset_ms: Optional[int]) -> None` [method] (pyssp/ui/timecode_setup_dialog.py:73)
- `offset_ms(self) -> Optional[int]` [method] (pyssp/ui/timecode_setup_dialog.py:76)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/timecode_setup_dialog.py:79)
- `focusOutEvent(self, event) -> None` [method] (pyssp/ui/timecode_setup_dialog.py:90)

#### Internal Members

- `__init__(self, offset_ms: Optional[int] = None, fps: float = 30.0, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/timecode_setup_dialog.py:26)

### `TimecodeSetupDialog`

- Defined at `pyssp/ui/timecode_setup_dialog.py:99`
- Bases: QDialog

#### Public Members

- `values(self) -> tuple[Optional[int], str]` [method] (pyssp/ui/timecode_setup_dialog.py:173)

#### Internal Members

- `__init__(self, offset_ms: Optional[int], timeline_mode: str, fps: float = 30.0, language: str = 'en', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/timecode_setup_dialog.py:100)
- `_nudge_offset_ms(self, delta_ms: int) -> None` [method] (pyssp/ui/timecode_setup_dialog.py:167)
