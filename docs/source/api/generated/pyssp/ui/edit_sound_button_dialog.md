# `pyssp/ui/edit_sound_button_dialog.py`

- Source: `pyssp/ui/edit_sound_button_dialog.py`
- Module path: `pyssp.ui.edit_sound_button_dialog`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `SoundHotkeyEdit`

- Defined at `pyssp/ui/edit_sound_button_dialog.py:32`
- Bases: QLineEdit

#### Public Members

- `setHotkey(self, value: str) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:38)
- `hotkey(self) -> str` [method] (pyssp/ui/edit_sound_button_dialog.py:41)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:44)
- `normalize(value: str) -> str` [staticmethod] (pyssp/ui/edit_sound_button_dialog.py:57)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/edit_sound_button_dialog.py:33)

### `EditSoundButtonDialog`

- Defined at `pyssp/ui/edit_sound_button_dialog.py:72`
- Bases: QDialog

#### Public Members

- `values(self) -> tuple[str, str, str, bool, str, str, str, Optional[int], str, str]` [method] (pyssp/ui/edit_sound_button_dialog.py:251)
- `handle_midi_message(self, token: str, source_selector: str = '', status: int = 0, data1: int = 0, data2: int = 0) -> bool` [method] (pyssp/ui/edit_sound_button_dialog.py:336)

#### Internal Members

- `__init__(self, file_path: str, caption: str, notes: str, disable_video_loading: bool = False, lyric_file: str = '', automation_script_path: str = '', vocal_removed_file: str = '', volume_override_pct: Optional[int] = None, sound_hotkey: str = '', sound_midi_hotkey: str = '', available_midi_input_devices: Optional[list[tuple[str, str]]] = None, selected_midi_input_device_ids: Optional[list[str]] = None, start_dir: str = '', language: str = 'en', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/edit_sound_button_dialog.py:75)
- `_browse_file(self) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:236)
- `_browse_lyric_file(self) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:268)
- `_browse_vocal_removed_file(self) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:283)
- `_browse_automation_script_file(self) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:298)
- `_request_regenerate_vocal_removed(self) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:313)
- `_set_midi_binding(self, token: str) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:316)
- `_start_midi_learn(self) -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:321)
- `_on_midi_binding(self, token: str, source_selector: str = '') -> None` [method] (pyssp/ui/edit_sound_button_dialog.py:325)
