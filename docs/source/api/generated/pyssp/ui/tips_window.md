# `pyssp/ui/tips_window.py`

- Source: `pyssp/ui/tips_window.py`
- Module path: `pyssp.ui.tips_window`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `TipsWindow`

- Defined at `pyssp/ui/tips_window.py:14`
- Bases: QDialog

#### Public Members

- `set_language(self, language: str) -> None` [method] (pyssp/ui/tips_window.py:76)
- `show_next_tip(self) -> None` [method] (pyssp/ui/tips_window.py:88)
- `show_previous_tip(self) -> None` [method] (pyssp/ui/tips_window.py:94)
- `pick_random_tip(self) -> None` [method] (pyssp/ui/tips_window.py:100)
- `set_open_on_startup(self, value: bool) -> None` [method] (pyssp/ui/tips_window.py:106)

#### Internal Members

- `__init__(self, language: str = 'en', open_on_startup: bool = True, parent = None) -> None` [constructor] (pyssp/ui/tips_window.py:17)
- `_refresh_tip_text(self) -> None` [method] (pyssp/ui/tips_window.py:109)
- `_load_tips(self, language: str) -> List[str]` [method] (pyssp/ui/tips_window.py:120)
- `_lightbulb_pixmap(size: int) -> QPixmap` [staticmethod] (pyssp/ui/tips_window.py:132)
