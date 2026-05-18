# `pyssp/ui/main_window/timecode.py`

- Source: `pyssp/ui/main_window/timecode.py`
- Module path: `pyssp.ui.main_window.timecode`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `TimecodeMixin`

- Defined at `pyssp/ui/main_window/timecode.py:9`

#### Internal Members

- `_build_timecode_dock(self) -> None` [method] (pyssp/ui/main_window/timecode.py:10)
- `_on_timecode_mode_changed(self, _index: int) -> None` [method] (pyssp/ui/main_window/timecode.py:36)
- `_on_timecode_dock_visibility_changed(self, visible: bool) -> None` [method] (pyssp/ui/main_window/timecode.py:54)
- `_toggle_timecode_panel(self) -> None` [method] (pyssp/ui/main_window/timecode.py:63)
- `_is_timecode_output_enabled(self) -> bool` [method] (pyssp/ui/main_window/timecode.py:71)
- `_update_timecode_multiplay_warning_banner(self) -> None` [method] (pyssp/ui/main_window/timecode.py:76)
- `_show_playback_warning_banner(self, text: str, timeout_ms: int = 5000) -> None` [method] (pyssp/ui/main_window/timecode.py:86)
- `_hide_playback_warning_banner(self, token: Optional[int] = None) -> None` [method] (pyssp/ui/main_window/timecode.py:94)
- `_show_save_notice_banner(self, text: str, timeout_ms: int = 5000) -> None` [method] (pyssp/ui/main_window/timecode.py:99)
- `_hide_save_notice_banner(self, token: Optional[int] = None) -> None` [method] (pyssp/ui/main_window/timecode.py:107)
- `_show_info_notice_banner(self, text: str, timeout_ms: int = 5000) -> None` [method] (pyssp/ui/main_window/timecode.py:112)
- `_hide_info_notice_banner(self, token: Optional[int] = None) -> None` [method] (pyssp/ui/main_window/timecode.py:120)
- `_timecode_current_follow_ms(self) -> int` [method] (pyssp/ui/main_window/timecode.py:125)
- `_timecode_reference_context(self) -> Tuple[Optional[ExternalMediaPlayer], Optional[Tuple[str, int, int]]]` [method] (pyssp/ui/main_window/timecode.py:162)
- `_newest_active_playing_key(self) -> Optional[Tuple[str, int, int]]` [method] (pyssp/ui/main_window/timecode.py:180)
- `_refresh_current_playing_from_active_players(self) -> None` [method] (pyssp/ui/main_window/timecode.py:199)
- `_timecode_display_ms_from_absolute(self, absolute_ms: int, slot_key: Optional[Tuple[str, int, int]] = None) -> int` [method] (pyssp/ui/main_window/timecode.py:202)
- `_effective_slot_timecode_timeline_mode(self, slot: SoundButtonData) -> str` [method] (pyssp/ui/main_window/timecode.py:224)
- `_timecode_output_ms(self) -> int` [method] (pyssp/ui/main_window/timecode.py:233)
- `_timecode_device_text(self) -> str` [method] (pyssp/ui/main_window/timecode.py:250)
- `_tick_timecode_mtc(self) -> None` [method] (pyssp/ui/main_window/timecode.py:268)
- `_timecode_on_playback_start(self, slot: Optional[SoundButtonData] = None) -> None` [method] (pyssp/ui/main_window/timecode.py:298)
- `_timecode_on_playback_stop(self) -> None` [method] (pyssp/ui/main_window/timecode.py:320)
- `_timecode_on_playback_pause(self) -> None` [method] (pyssp/ui/main_window/timecode.py:334)
- `_timecode_on_playback_resume(self) -> None` [method] (pyssp/ui/main_window/timecode.py:345)
- `_refresh_timecode_panel(self) -> None` [method] (pyssp/ui/main_window/timecode.py:356)
- `_update_timecode_status_label(self) -> None` [method] (pyssp/ui/main_window/timecode.py:371)
