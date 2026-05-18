# `pyssp/ui/stage_display.py`

- Source: `pyssp/ui/stage_display.py`
- Module path: `pyssp.ui.stage_display`
- API entries: `14`

## Module Docstring

No module docstring.

## Constants

### Public

- `STAGE_DISPLAY_GADGET_SPECS` [constant] (pyssp/ui/stage_display.py:14)
  Detail: Value: [('current_time', 'Current Time'), ('alert', 'Alert'), ('total_time', 'Total ...
- `STAGE_DISPLAY_GADGET_KEYS` [constant] (pyssp/ui/stage_display.py:27)
  Detail: Value: [key for key, _label in STAGE_DISPLAY_GADGET_SPECS]

## Functions

### Public

- `default_stage_display_gadgets() -> Dict[str, Dict[str, int | bool | str]]` [function] (pyssp/ui/stage_display.py:32)
- `normalize_stage_display_gadgets(values: Optional[Dict[str, Dict[str, object]]], legacy_layout: Optional[List[str]] = None, legacy_visibility: Optional[Dict[str, bool]] = None) -> Dict[str, Dict[str, int | bool | str]]` [function] (pyssp/ui/stage_display.py:158)
- `gadgets_to_legacy_layout_visibility(gadgets: Dict[str, Dict[str, object]]) -> Tuple[List[str], Dict[str, bool]]` [function] (pyssp/ui/stage_display.py:208)
- `bundled_display_font_family() -> str` [function] (pyssp/ui/stage_display.py:215)
- `available_display_font_families() -> List[str]` [function] (pyssp/ui/stage_display.py:239)

### Internal

- `_coerce_int(value: object, fallback: int, minimum: int, maximum: int) -> int` [function] (pyssp/ui/stage_display.py:811)
- `_norm_to_rect(spec: Dict[str, object], area: QRect) -> QRect` [function] (pyssp/ui/stage_display.py:819)
- `_rect_to_norm(rect: QRect, area: QRect) -> Dict[str, int]` [function] (pyssp/ui/stage_display.py:833)
- `_strip_font_size_style(style: str) -> str` [function] (pyssp/ui/stage_display.py:844)

## Classes

### `_GadgetFrame`

- Defined at `pyssp/ui/stage_display.py:251`
- Bases: QFrame

#### Public Members

- `resizeEvent(self, event) -> None` [method] (pyssp/ui/stage_display.py:296)
- `apply_config(self, orientation: str, hide_text: bool, hide_border: bool, *, title_font_family: str = '', title_font_size: int = 13, value_font_family: str = '', value_font_size: int = 24) -> None` [method] (pyssp/ui/stage_display.py:315)
- `set_selected(self, selected: bool) -> None` [method] (pyssp/ui/stage_display.py:366)
- `mousePressEvent(self, event) -> None` [method] (pyssp/ui/stage_display.py:370)
- `mouseMoveEvent(self, event) -> None` [method] (pyssp/ui/stage_display.py:386)
- `mouseReleaseEvent(self, event) -> None` [method] (pyssp/ui/stage_display.py:410)

#### Internal Members

- `__init__(self, key: str, title: str, draggable: bool, parent: QWidget) -> None` [constructor] (pyssp/ui/stage_display.py:255)
- `_apply_fonts(self) -> None` [method] (pyssp/ui/stage_display.py:301)
- `_apply_frame_style(self) -> None` [method] (pyssp/ui/stage_display.py:348)

### `StageDisplayLayoutEditor`

- Defined at `pyssp/ui/stage_display.py:417`
- Bases: QWidget

#### Public Members

- `set_gadgets(self, gadgets: Dict[str, Dict[str, object]]) -> None` [method] (pyssp/ui/stage_display.py:440)
- `gadgets(self) -> Dict[str, Dict[str, int | bool | str]]` [method] (pyssp/ui/stage_display.py:444)
- `set_font_settings(self, *, default_font_family: str = '', default_value_font_size: int = 24, lyric_font_family: str = '', lyric_value_font_size: int = 24) -> None` [method] (pyssp/ui/stage_display.py:447)
- `set_gadget_visible(self, key: str, visible: bool) -> None` [method] (pyssp/ui/stage_display.py:465)
- `set_gadget_orientation(self, key: str, orientation: str) -> None` [method] (pyssp/ui/stage_display.py:471)
- `set_gadget_hide_text(self, key: str, hide_text: bool) -> None` [method] (pyssp/ui/stage_display.py:478)
- `set_gadget_hide_border(self, key: str, hide_border: bool) -> None` [method] (pyssp/ui/stage_display.py:484)
- `layer_order(self) -> List[str]` [method] (pyssp/ui/stage_display.py:490)
- `set_layer_order(self, order: List[str]) -> None` [method] (pyssp/ui/stage_display.py:493)
- `resizeEvent(self, event) -> None` [method] (pyssp/ui/stage_display.py:506)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/stage_display.py:418)
- `_apply_geometry(self) -> None` [method] (pyssp/ui/stage_display.py:510)
- `_on_widget_selected(self, key: str) -> None` [method] (pyssp/ui/stage_display.py:539)
- `_on_widget_changed(self, key: str) -> None` [method] (pyssp/ui/stage_display.py:550)

### `StageDisplayWindow`

- Defined at `pyssp/ui/stage_display.py:557`
- Bases: QWidget

#### Public Members

- `eventFilter(self, watched, event)` [method] (pyssp/ui/stage_display.py:637)
- `mouseDoubleClickEvent(self, event) -> None` [method] (pyssp/ui/stage_display.py:645)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/stage_display.py:652)
- `configure_gadgets(self, gadgets: Dict[str, Dict[str, object]]) -> None` [method] (pyssp/ui/stage_display.py:659)
- `configure_layout(self, order: List[str], visibility: Dict[str, bool]) -> None` [method] (pyssp/ui/stage_display.py:664)
- `configure_font_settings(self, *, default_font_family: str = '', default_font_size: int = 24, lyric_font_family: str = '', lyric_font_size: int = 24, lyric_role_colors: Optional[Dict[str, str]] = None, lyric_role_sizes: Optional[Dict[str, int]] = None, lyric_auto_adjust_role_sizes: bool = True, lyric_role_scale_percents: Optional[Dict[str, int]] = None, lyric_role_bold: Optional[Dict[str, bool]] = None, lyric_role_italic: Optional[Dict[str, bool]] = None) -> None` [method] (pyssp/ui/stage_display.py:667)
- `update_values(self, total_time: str, elapsed: str, remaining: str, progress_percent: int, song_name: str, lyric: str, automation_comment_current: str, automation_comment_next: str, next_song: str, progress_text: str = '', progress_style: str = '') -> None` [method] (pyssp/ui/stage_display.py:718)
- `set_playback_status(self, state: str) -> None` [method] (pyssp/ui/stage_display.py:757)
- `retranslate_ui(self) -> None` [method] (pyssp/ui/stage_display.py:767)
- `set_alert(self, text: str, active: bool) -> None` [method] (pyssp/ui/stage_display.py:781)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/stage_display.py:558)
- `_install_fullscreen_toggle_filter(self, root: QWidget) -> None` [method] (pyssp/ui/stage_display.py:626)
- `_toggle_fullscreen(self) -> None` [method] (pyssp/ui/stage_display.py:631)
- `_update_datetime(self) -> None` [method] (pyssp/ui/stage_display.py:789)
- `_apply_alert_visibility(self) -> None` [method] (pyssp/ui/stage_display.py:794)
- `_apply_font_settings(self) -> None` [method] (pyssp/ui/stage_display.py:802)
