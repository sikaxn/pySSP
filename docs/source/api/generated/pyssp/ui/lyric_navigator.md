# `pyssp/ui/lyric_navigator.py`

- Source: `pyssp/ui/lyric_navigator.py`
- Module path: `pyssp.ui.lyric_navigator`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `LyricNavigatorWindow`

- Defined at `pyssp/ui/lyric_navigator.py:13`
- Bases: QWidget

#### Public Members

- `minimumSizeHint(self) -> QSize` [method] (pyssp/ui/lyric_navigator.py:60)
- `sizeHint(self) -> QSize` [method] (pyssp/ui/lyric_navigator.py:63)
- `retranslate_ui(self, language: str = 'en') -> None` [method] (pyssp/ui/lyric_navigator.py:66)
- `clear(self) -> None` [method] (pyssp/ui/lyric_navigator.py:71)
- `update_playback_state(self, *, has_active_track: bool, lyric_path: str, position_ms: int, force: bool = False) -> None` [method] (pyssp/ui/lyric_navigator.py:79)

#### Internal Members

- `__init__(self, *, on_seek_to_ms: Callable[[int], None], language: str = 'en', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/lyric_navigator.py:14)
- `_load_lyric_lines(self, lyric_path: str) -> tuple[List[LyricLine], str]` [method] (pyssp/ui/lyric_navigator.py:127)
- `_highlight_row_for_position(self, position_ms: int) -> None` [method] (pyssp/ui/lyric_navigator.py:147)
- `_on_cell_clicked(self, row: int, _column: int) -> None` [method] (pyssp/ui/lyric_navigator.py:171)
- `_format_timestamp(path: str, ms: int) -> str` [staticmethod] (pyssp/ui/lyric_navigator.py:179)
