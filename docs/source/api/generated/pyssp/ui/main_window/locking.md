# `pyssp/ui/main_window/locking.py`

- Source: `pyssp/ui/main_window/locking.py`
- Module path: `pyssp.ui.main_window.locking`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `LockingMixin`

- Defined at `pyssp/ui/main_window/locking.py:9`

#### Internal Members

- `_is_playback_in_progress(self) -> bool` [method] (pyssp/ui/main_window/locking.py:10)
- `_is_locked_input_allowed(self, source: str) -> bool` [method] (pyssp/ui/main_window/locking.py:26)
- `_run_locked_input(self, source: str, handler: Callable[[], None]) -> None` [method] (pyssp/ui/main_window/locking.py:46)
- `_handle_lock_overlay_key_press(self, event) -> None` [method] (pyssp/ui/main_window/locking.py:51)
- `_handle_lock_overlay_key_release(self, event) -> None` [method] (pyssp/ui/main_window/locking.py:63)
- `_hotkey_lock_toggle(self) -> None` [method] (pyssp/ui/main_window/locking.py:68)
- `_toggle_lock_screen(self) -> None` [method] (pyssp/ui/main_window/locking.py:74)
- `_engage_lock_screen(self, automation: bool = False) -> None` [method] (pyssp/ui/main_window/locking.py:79)
- `_attempt_unlock_from_overlay(self) -> None` [method] (pyssp/ui/main_window/locking.py:91)
- `_attempt_unlock_from_hotkey(self) -> None` [method] (pyssp/ui/main_window/locking.py:111)
- `_prompt_unlock_credentials(self, require_keyword: bool) -> bool` [method] (pyssp/ui/main_window/locking.py:127)
- `_prompt_unlock_phrase(self, phrase: str, message: str, error_text: str, require_password: bool = False) -> bool` [method] (pyssp/ui/main_window/locking.py:185)
- `_release_lock_screen(self, force: bool = False) -> None` [method] (pyssp/ui/main_window/locking.py:233)
- `_sync_lock_ui_state(self) -> None` [method] (pyssp/ui/main_window/locking.py:248)
