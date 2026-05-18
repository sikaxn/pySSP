# `pyssp/ui/automation_script_navigator.py`

- Source: `pyssp/ui/automation_script_navigator.py`
- Module path: `pyssp.ui.automation_script_navigator`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `AutomationScriptNavigatorWindow`

- Defined at `pyssp/ui/automation_script_navigator.py:31`
- Bases: QWidget

#### Public Members

- `minimumSizeHint(self) -> QSize` [method] (pyssp/ui/automation_script_navigator.py:119)
- `sizeHint(self) -> QSize` [method] (pyssp/ui/automation_script_navigator.py:122)
- `retranslate_ui(self, language: str = 'en') -> None` [method] (pyssp/ui/automation_script_navigator.py:125)
- `clear(self) -> None` [method] (pyssp/ui/automation_script_navigator.py:133)
- `update_playback_state(self, *, has_active_track: bool, script_path: str, lyric_path: str = '', position_ms: int, companion_bypass: Optional[bool] = None, internal_bypass: Optional[bool] = None, force: bool = False) -> None` [method] (pyssp/ui/automation_script_navigator.py:142)
- `set_companion_bypass(self, bypassed: bool) -> None` [method] (pyssp/ui/automation_script_navigator.py:226)
- `set_internal_bypass(self, bypassed: bool) -> None` [method] (pyssp/ui/automation_script_navigator.py:236)

#### Internal Members

- `__init__(self, *, on_seek_to_ms: Callable[[int], None], show_lyric_default: bool = False, on_show_lyric_changed: Optional[Callable[[bool], None]] = None, companion_bypass: bool = False, internal_bypass: bool = False, on_companion_bypass_changed: Optional[Callable[[bool], None]] = None, on_internal_bypass_changed: Optional[Callable[[bool], None]] = None, language: str = 'en', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/automation_script_navigator.py:32)
- `_on_show_lyric_toggled(self, checked: bool) -> None` [method] (pyssp/ui/automation_script_navigator.py:246)
- `_on_companion_bypass_toggled(self, checked: bool) -> None` [method] (pyssp/ui/automation_script_navigator.py:261)
- `_on_internal_bypass_toggled(self, checked: bool) -> None` [method] (pyssp/ui/automation_script_navigator.py:266)
- `_refresh_toggle_button_style(button: QPushButton, active_color: str, inactive_color: str) -> None` [staticmethod] (pyssp/ui/automation_script_navigator.py:272)
- `_load_rows(self, script_path: str, lyric_path: str) -> tuple[List[dict], str]` [method] (pyssp/ui/automation_script_navigator.py:285)
- `_highlight_row(self, row: int) -> None` [method] (pyssp/ui/automation_script_navigator.py:351)
- `_on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None` [method] (pyssp/ui/automation_script_navigator.py:364)
- `_row_index_for_position(self, position_ms: int) -> int` [method] (pyssp/ui/automation_script_navigator.py:372)
- `_format_timestamp(ms: int) -> str` [staticmethod] (pyssp/ui/automation_script_navigator.py:382)
