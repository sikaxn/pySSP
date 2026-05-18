# `pyssp/ui/options_dialog/state_logic.py`

- Source: `pyssp/ui/options_dialog/state_logic.py`
- Module path: `pyssp.ui.options_dialog.state_logic`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `StateLogicMixin`

- Defined at `pyssp/ui/options_dialog/state_logic.py:7`

#### Internal Members

- `_refresh_color_button(self, button: QPushButton, color_hex: str) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:8)
- `_pick_active_color(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:18)
- `_pick_inactive_color(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:24)
- `_pick_state_color(self, key: str, button: QPushButton, label: str) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:30)
- `_pick_sound_text_color(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:38)
- `_pick_lyric_role_color(self, scope: str, role: str) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:44)
- `_restore_defaults_current_page(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:79)
- `_restore_language_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:138)
- `_restore_general_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:144)
- `_restore_lock_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:184)
- `_restore_color_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:212)
- `_restore_display_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:226)
- `_restore_video_display_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:320)
- `_restore_window_layout_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:411)
- `_restore_hotkey_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:439)
- `_restore_midi_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:458)
- `_normalize_hotkey_for_conflict(self, raw: str) -> str` [method] (pyssp/ui/options_dialog/state_logic.py:530)
- `_validate_lock_page(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:549)
- `_sync_ok_button_state(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:578)
- `_validate_hotkey_conflicts(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:589)
- `_validate_midi_conflicts(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:657)
- `_describe_conflict_target(self, key: str, slot_index: int) -> str` [method] (pyssp/ui/options_dialog/state_logic.py:736)
- `_restore_delay_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:741)
- `_restore_playback_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:767)
- `_restore_audio_device_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:819)
- `_restore_preload_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:874)
- `_restore_talk_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:895)
- `_restore_web_remote_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:908)
- `_restore_companion_satellite_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:922)
- `_restore_lyric_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:951)
- `_restore_audio_format_defaults(self) -> None` [method] (pyssp/ui/options_dialog/state_logic.py:1024)
