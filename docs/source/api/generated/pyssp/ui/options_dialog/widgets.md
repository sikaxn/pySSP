# `pyssp/ui/options_dialog/widgets.py`

- Source: `pyssp/ui/options_dialog/widgets.py`
- Module path: `pyssp.ui.options_dialog.widgets`
- API entries: `5`

## Module Docstring

No module docstring.

## Classes

### `_GridLayoutButton`

- Defined at `pyssp/ui/options_dialog/widgets.py:14`
- Bases: QFrame

#### Public Members

- `resizeEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:47)
- `mousePressEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:56)
- `mouseMoveEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:73)
- `mouseReleaseEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:110)

#### Internal Members

- `__init__(self, uid: str, key: str, parent: QWidget) -> None` [constructor] (pyssp/ui/options_dialog/widgets.py:17)

### `_AvailableButtonsList`

- Defined at `pyssp/ui/options_dialog/widgets.py:116`
- Bases: QListWidget

#### Public Members

- `set_buttons(self, buttons: List[str]) -> None` [method] (pyssp/ui/options_dialog/widgets.py:151)
- `buttons(self) -> List[str]` [method] (pyssp/ui/options_dialog/widgets.py:159)
- `startDrag(self, supportedActions) -> None` [method] (pyssp/ui/options_dialog/widgets.py:162)
- `dragEnterEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:173)
- `dragMoveEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:179)
- `dropEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:185)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/options_dialog/widgets.py:119)

### `_GridLayoutCanvas`

- Defined at `pyssp/ui/options_dialog/widgets.py:194`
- Bases: QWidget

#### Public Members

- `set_items(self, values: List[Dict[str, object]]) -> None` [method] (pyssp/ui/options_dialog/widgets.py:211)
- `export_items(self) -> List[Dict[str, int | str]]` [method] (pyssp/ui/options_dialog/widgets.py:233)
- `payload_for_uid(self, uid: str) -> Optional[Dict[str, object]]` [method] (pyssp/ui/options_dialog/widgets.py:247)
- `get_item(self, uid: str) -> Optional[Dict[str, object]]` [method] (pyssp/ui/options_dialog/widgets.py:260)
- `occupied_item_at(self, x: int, y: int, exclude_uid: str = '') -> Optional[Dict[str, object]]` [method] (pyssp/ui/options_dialog/widgets.py:266)
- `remove_uid(self, uid: str) -> Optional[Dict[str, object]]` [method] (pyssp/ui/options_dialog/widgets.py:280)
- `upsert_item(self, uid: str, button: str, x: int, y: int, w: int, h: int) -> None` [method] (pyssp/ui/options_dialog/widgets.py:289)
- `add_item(self, button: str, x: int, y: int, w: int, h: int, uid: Optional[str] = None) -> str` [method] (pyssp/ui/options_dialog/widgets.py:325)
- `remove_all_by_button(self, button: str, exclude_uid: str = '') -> List[Dict[str, object]]` [method] (pyssp/ui/options_dialog/widgets.py:342)
- `has_button(self, button: str) -> bool` [method] (pyssp/ui/options_dialog/widgets.py:358)
- `update_item_from_pixel_rect(self, uid: str, rect: QRect) -> None` [method] (pyssp/ui/options_dialog/widgets.py:361)
- `snap_to_grid(self, pos: QPoint) -> tuple[int, int]` [method] (pyssp/ui/options_dialog/widgets.py:379)
- `resizeEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:389)
- `paintEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:393)
- `dragEnterEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:424)
- `dragMoveEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:432)
- `dragLeaveEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:440)
- `dropEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:445)

#### Internal Members

- `__init__(self, zone_name: str, columns: int, rows: int, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/options_dialog/widgets.py:198)
- `_content_rect(self) -> QRect` [method] (pyssp/ui/options_dialog/widgets.py:455)
- `_normalize_items(self) -> None` [method] (pyssp/ui/options_dialog/widgets.py:458)
- `_apply_geometry(self) -> None` [method] (pyssp/ui/options_dialog/widgets.py:515)

### `HotkeyCaptureEdit`

- Defined at `pyssp/ui/options_dialog/widgets.py:545`
- Bases: QLineEdit

#### Public Members

- `hotkey(self) -> str` [method] (pyssp/ui/options_dialog/widgets.py:551)
- `setHotkey(self, value: str) -> None` [method] (pyssp/ui/options_dialog/widgets.py:554)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/options_dialog/widgets.py:558)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/options_dialog/widgets.py:546)
- `_build_hotkey_text(self, key: int, modifiers: Qt.KeyboardModifiers) -> str` [method] (pyssp/ui/options_dialog/widgets.py:572)
- `_normalize_text(self, value: str) -> str` [method] (pyssp/ui/options_dialog/widgets.py:584)

### `MidiCaptureEdit`

- Defined at `pyssp/ui/options_dialog/widgets.py:604`
- Bases: QLineEdit

#### Public Members

- `binding(self) -> str` [method] (pyssp/ui/options_dialog/widgets.py:611)
- `setBinding(self, value: str) -> None` [method] (pyssp/ui/options_dialog/widgets.py:614)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/options_dialog/widgets.py:605)
