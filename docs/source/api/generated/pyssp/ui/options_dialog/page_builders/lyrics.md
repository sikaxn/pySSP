# `pyssp/ui/options_dialog/page_builders/lyrics.py`

- Source: `pyssp/ui/options_dialog/page_builders/lyrics.py`
- Module path: `pyssp.ui.options_dialog.page_builders.lyrics`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `LyricsPageMixin`

- Defined at `pyssp/ui/options_dialog/page_builders/lyrics.py:7`

#### Internal Members

- `_build_lyric_page(self, main_ui_lyric_display_mode: str, lyric_display_transparent_mode: bool, lyric_display_show_not_playing_message: bool, search_lyric_on_add_sound_button: bool, new_lyric_file_format: str, lyric_display_font_family: str, lyric_display_font_size: int, lyric_display_previous_line_count: int, lyric_display_next_line_count: int) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/lyrics.py:8)
- `_populate_display_font_combo(self, combo: QComboBox, selected_family: str) -> None` [method] (pyssp/ui/options_dialog/page_builders/lyrics.py:153)
- `_build_role_style_row(self, *widgets: QWidget) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/lyrics.py:172)
- `_sync_lyric_role_size_mode(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/lyrics.py:182)
- `_rescan_supported_audio_formats(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/lyrics.py:197)
