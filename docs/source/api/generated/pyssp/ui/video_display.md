# `pyssp/ui/video_display.py`

- Source: `pyssp/ui/video_display.py`
- Module path: `pyssp.ui.video_display`
- API entries: `3`

## Module Docstring

No module docstring.

## Functions

### Internal

- `_normalized_rect(spec: dict[str, int], bounds: QRect) -> QRect` [function] (pyssp/ui/video_display.py:12)

## Classes

### `VideoDisplayWidget`

- Defined at `pyssp/ui/video_display.py:26`
- Bases: QWidget

#### Public Members

- `eventFilter(self, watched, event)` [method] (pyssp/ui/video_display.py:54)
- `mouseDoubleClickEvent(self, event) -> None` [method] (pyssp/ui/video_display.py:62)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/video_display.py:69)
- `showEvent(self, event) -> None` [method] (pyssp/ui/video_display.py:76)
- `resizeEvent(self, event) -> None` [method] (pyssp/ui/video_display.py:80)
- `configure_overlay(self, *, overlay_rect: Optional[dict[str, int]] = None, show_lyric_overlay: bool = False, show_stage_alert: bool = False) -> None` [method] (pyssp/ui/video_display.py:91)
- `set_mode(self, mode: str) -> None` [method] (pyssp/ui/video_display.py:104)
- `set_video_pixmap(self, pixmap: Optional[QPixmap]) -> None` [method] (pyssp/ui/video_display.py:111)
- `set_content_pixmap(self, pixmap: Optional[QPixmap]) -> None` [method] (pyssp/ui/video_display.py:115)
- `set_backdrop_pixmap(self, pixmap: Optional[QPixmap]) -> None` [method] (pyssp/ui/video_display.py:119)
- `set_lyric_html(self, html: str) -> None` [method] (pyssp/ui/video_display.py:123)
- `set_alert_text(self, text: str) -> None` [method] (pyssp/ui/video_display.py:128)
- `configure_backdrop(self, *, show_message: bool = False, message_text: str = '') -> None` [method] (pyssp/ui/video_display.py:132)
- `paintEvent(self, _event) -> None` [method] (pyssp/ui/video_display.py:167)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None, *, allow_fullscreen_toggle: bool = False) -> None` [constructor] (pyssp/ui/video_display.py:29)
- `_install_fullscreen_filter(self, root: QWidget) -> None` [method] (pyssp/ui/video_display.py:49)
- `_toggle_fullscreen(self) -> None` [method] (pyssp/ui/video_display.py:84)
- `_draw_colour_bars(self, painter: QPainter, rect: QRect) -> None` [method] (pyssp/ui/video_display.py:137)
- `_draw_scaled_pixmap(self, painter: QPainter, rect: QRect, pixmap: QPixmap, *, keep_aspect: bool) -> None` [method] (pyssp/ui/video_display.py:145)

### `VideoDisplayWindow`

- Defined at `pyssp/ui/video_display.py:221`
- Bases: QWidget

#### Public Members

- `set_mode(self, mode: str) -> None` [method] (pyssp/ui/video_display.py:234)
- `set_video_pixmap(self, pixmap: Optional[QPixmap]) -> None` [method] (pyssp/ui/video_display.py:237)
- `set_content_pixmap(self, pixmap: Optional[QPixmap]) -> None` [method] (pyssp/ui/video_display.py:240)
- `set_backdrop_pixmap(self, pixmap: Optional[QPixmap]) -> None` [method] (pyssp/ui/video_display.py:243)
- `set_lyric_html(self, html: str) -> None` [method] (pyssp/ui/video_display.py:246)
- `set_alert_text(self, text: str) -> None` [method] (pyssp/ui/video_display.py:249)
- `configure_backdrop(self, *, show_message: bool = False, message_text: str = '') -> None` [method] (pyssp/ui/video_display.py:252)
- `configure_overlay(self, *, overlay_rect: Optional[dict[str, int]] = None, show_lyric_overlay: bool = False, show_stage_alert: bool = False) -> None` [method] (pyssp/ui/video_display.py:255)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/video_display.py:222)
