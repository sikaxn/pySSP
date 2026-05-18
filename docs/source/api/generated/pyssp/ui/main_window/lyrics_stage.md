# `pyssp/ui/main_window/lyrics_stage.py`

- Source: `pyssp/ui/main_window/lyrics_stage.py`
- Module path: `pyssp.ui.main_window.lyrics_stage`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `LyricsStageMixin`

- Defined at `pyssp/ui/main_window/lyrics_stage.py:9`

#### Internal Members

- `_update_now_playing_label(self, text: str) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:10)
- `_update_main_lyric_label(self, text: str) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:21)
- `_toggle_lyric_force_blank(self, checked: bool = False) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:37)
- `_set_lyric_force_blank(self, blank: bool) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:40)
- `_sync_lyric_display_controls(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:49)
- `_create_lyric_display_window(self) -> LyricDisplayWindow` [method] (pyssp/ui/main_window/lyrics_stage.py:66)
- `_configure_lyric_display_window(self, window: Optional[LyricDisplayWindow] = None) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:76)
- `_capture_lyric_display_window_state(self) -> dict[str, object]` [method] (pyssp/ui/main_window/lyrics_stage.py:96)
- `_restore_lyric_display_window_state(self, window: LyricDisplayWindow, state: dict[str, object]) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:115)
- `_recreate_lyric_display_window(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:133)
- `_set_lyric_display_transparent_mode(self, enabled: bool) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:146)
- `_toggle_lyric_display_transparent_mode(self, checked: bool = False) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:159)
- `_hotkey_toggle_lyric_display_transparent_mode(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:162)
- `_adjust_lyric_display_font_size(self, delta: int) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:165)
- `_main_ui_current_lyric_text(self) -> str` [method] (pyssp/ui/main_window/lyrics_stage.py:185)
- `_lyric_position_ms_for_key(self, slot_key: Optional[Tuple[str, int, int]]) -> int` [method] (pyssp/ui/main_window/lyrics_stage.py:203)
- `_build_now_playing_text(self, slot: SoundButtonData) -> str` [method] (pyssp/ui/main_window/lyrics_stage.py:220)
- `_show_stage_display(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:241)
- `_open_lyric_display(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:264)
- `_on_lyric_display_destroyed(self, window = None) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:273)
- `_open_lyric_navigator(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:279)
- `_open_automation_script_navigator(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:287)
- `_seek_to_lyric_timestamp(self, position_ms: int) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:295)
- `_refresh_lyric_display(self, force: bool = False) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:301)
- `_open_stage_alert_panel(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:350)
- `_on_stage_alert_dialog_destroyed(self, _obj = None) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:398)
- `_send_stage_alert_from_panel(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:404)
- `_set_stage_alert(self, text: str, keep: bool = True, seconds: int = 10) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:415)
- `_clear_stage_alert(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:427)
- `_stage_alert_active(self) -> bool` [method] (pyssp/ui/main_window/lyrics_stage.py:430)
- `_on_stage_display_destroyed(self, _obj = None) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:443)
- `_refresh_stage_display(self) -> None` [method] (pyssp/ui/main_window/lyrics_stage.py:446)
- `_stage_playback_status(self) -> str` [method] (pyssp/ui/main_window/lyrics_stage.py:494)
- `_build_stage_slot_text(self, slot: SoundButtonData) -> str` [method] (pyssp/ui/main_window/lyrics_stage.py:510)
- `_next_stage_song_name(self) -> str` [method] (pyssp/ui/main_window/lyrics_stage.py:528)
- `_stage_display_current_lyric(self) -> str` [method] (pyssp/ui/main_window/lyrics_stage.py:549)
- `_load_stage_lyric_lines(self, lyric_path: str) -> tuple[List[LyricLine], str]` [method] (pyssp/ui/main_window/lyrics_stage.py:576)
- `_stage_display_lyric_role_styles(self) -> dict[str, dict[str, object]]` [method] (pyssp/ui/main_window/lyrics_stage.py:596)
