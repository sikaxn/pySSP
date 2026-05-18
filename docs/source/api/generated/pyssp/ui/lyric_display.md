# `pyssp/ui/lyric_display.py`

- Source: `pyssp/ui/lyric_display.py`
- Module path: `pyssp.ui.lyric_display`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `LyricDisplayWindow`

- Defined at `pyssp/ui/lyric_display.py:14`
- Bases: QWidget

#### Public Members

- `set_lyric_text(self, text: str) -> None` [method] (pyssp/ui/lyric_display.py:178)
- `set_transparent_mode_enabled(self, enabled: bool) -> None` [method] (pyssp/ui/lyric_display.py:184)
- `configure_display_settings(self, *, font_family: str = '', font_size: int = 36, show_not_playing_message: bool = True, previous_line_count: int = 0, next_line_count: int = 0, role_colors: Optional[dict[str, str]] = None, role_sizes: Optional[dict[str, int]] = None, auto_adjust_role_sizes: bool = True, role_scale_percents: Optional[dict[str, int]] = None, role_bold: Optional[dict[str, bool]] = None, role_italic: Optional[dict[str, bool]] = None) -> None` [method] (pyssp/ui/lyric_display.py:194)
- `update_playback_state(self, *, has_active_track: bool, lyric_path: str, position_ms: int, force_blank: bool = False, force: bool = False) -> None` [method] (pyssp/ui/lyric_display.py:247)
- `retranslate_ui(self) -> None` [method] (pyssp/ui/lyric_display.py:309)
- `resizeEvent(self, event) -> None` [method] (pyssp/ui/lyric_display.py:581)
- `eventFilter(self, watched, event)` [method] (pyssp/ui/lyric_display.py:620)
- `mouseDoubleClickEvent(self, event) -> None` [method] (pyssp/ui/lyric_display.py:634)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/lyric_display.py:646)
- `contextMenuEvent(self, event) -> None` [method] (pyssp/ui/lyric_display.py:659)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None, *, on_toggle_transparent_mode: Optional[Callable[[bool], None]] = None, on_adjust_font_size: Optional[Callable[[int], None]] = None, on_open_settings: Optional[Callable[[], None]] = None) -> None` [constructor] (pyssp/ui/lyric_display.py:15)
- `_load_lyric_lines(self, lyric_path: str) -> tuple[List[LyricLine], str]` [method] (pyssp/ui/lyric_display.py:289)
- `_apply_font_settings(self) -> None` [method] (pyssp/ui/lyric_display.py:316)
- `_resolved_role_styles(self) -> dict[str, dict[str, object]]` [method] (pyssp/ui/lyric_display.py:326)
- `_install_fullscreen_toggle_filter(self, root: QWidget) -> None` [method] (pyssp/ui/lyric_display.py:344)
- `_is_toolbar_widget(self, watched) -> bool` [method] (pyssp/ui/lyric_display.py:350)
- `_refresh_toolbar_text(self) -> None` [method] (pyssp/ui/lyric_display.py:370)
- `_show_hover_toolbar(self) -> None` [method] (pyssp/ui/lyric_display.py:378)
- `_hide_hover_toolbar(self) -> None` [method] (pyssp/ui/lyric_display.py:397)
- `_handle_toolbar_toggle_clicked(self) -> None` [method] (pyssp/ui/lyric_display.py:412)
- `_handle_toolbar_font_adjust(self, delta: int) -> None` [method] (pyssp/ui/lyric_display.py:420)
- `_handle_toolbar_settings_clicked(self) -> None` [method] (pyssp/ui/lyric_display.py:427)
- `_refresh_transparent_visuals(self) -> None` [method] (pyssp/ui/lyric_display.py:432)
- `_refresh_windowed_visuals(self) -> None` [method] (pyssp/ui/lyric_display.py:458)
- `_capture_window_state(self) -> dict[str, object]` [method] (pyssp/ui/lyric_display.py:481)
- `_restore_window_state(self, state: dict[str, object]) -> None` [method] (pyssp/ui/lyric_display.py:492)
- `_normalize_transparent_native_surface(self) -> None` [method] (pyssp/ui/lyric_display.py:520)
- `_apply_window_chrome(self) -> None` [method] (pyssp/ui/lyric_display.py:531)
- `_reposition_overlays(self) -> None` [method] (pyssp/ui/lyric_display.py:585)
- `_overlay_exposed_canvas_rect(self, overlay_rect: QRect) -> QRect` [method] (pyssp/ui/lyric_display.py:597)
- `_toggle_fullscreen(self) -> None` [method] (pyssp/ui/lyric_display.py:608)
