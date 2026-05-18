# `pyssp/ui/options_dialog/page_builders/video_display.py`

- Source: `pyssp/ui/options_dialog/page_builders/video_display.py`
- Module path: `pyssp.ui.options_dialog.page_builders.video_display`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `VideoDisplayPageMixin`

- Defined at `pyssp/ui/options_dialog/page_builders/video_display.py:7`

#### Internal Members

- `_build_video_display_page(self, *, mode_playing: str, mode_idle: str, use_default_backdrop: bool, backdrop_path: str, show_backdrop_message: bool, show_lyric_overlay: bool, show_stage_alert: bool, lyric_overlay_rect: Dict[str, int], lyric_font_family: str, lyric_font_size: int, lyric_previous_line_count: int, lyric_next_line_count: int, lyric_role_colors: Dict[str, str], lyric_auto_adjust_role_sizes: bool, lyric_role_scale_percents: Dict[str, int], lyric_role_sizes: Dict[str, int], lyric_role_bold: Dict[str, bool], lyric_role_italic: Dict[str, bool], ndi_status_text: str, ndi_download_url: str, ndi_ready: bool, ndi_output_enabled: bool, ndi_output_name: str, ndi_output_mode_playing: str, ndi_output_mode_idle: str, ndi_output_resolution_mode: str, ndi_output_width: int, ndi_output_height: int, ndi_output_fps: int, ndi_output_audio_enabled: bool, ndi_output_audio_tap_mode: str) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/video_display.py:8)
- `_sync_video_display_lyric_role_size_mode(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/video_display.py:339)
- `_sync_video_display_backdrop_controls(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/video_display.py:348)
- `_sync_ndi_controls(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/video_display.py:353)
- `_sync_ndi_route_controls(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/video_display.py:376)
- `_browse_video_display_backdrop_path(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/video_display.py:390)
