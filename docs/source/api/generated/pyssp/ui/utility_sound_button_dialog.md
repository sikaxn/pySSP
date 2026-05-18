# `pyssp/ui/utility_sound_button_dialog.py`

- Source: `pyssp/ui/utility_sound_button_dialog.py`
- Module path: `pyssp.ui.utility_sound_button_dialog`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `UtilitySoundButtonDialog`

- Defined at `pyssp/ui/utility_sound_button_dialog.py:47`
- Bases: QDialog

#### Public Members

- `values(self) -> tuple[str, str, str, str, UtilitySoundSpec, Optional[int], str, str]` [method] (pyssp/ui/utility_sound_button_dialog.py:244)
- `handle_midi_message(self, token: str, source_selector: str = '', status: int = 0, data1: int = 0, data2: int = 0) -> bool` [method] (pyssp/ui/utility_sound_button_dialog.py:273)

#### Internal Members

- `__init__(self, *, caption: str, notes: str, lyric_file: str = '', automation_script_path: str = '', utility_spec: Optional[UtilitySoundSpec] = None, volume_override_pct: Optional[int] = None, sound_hotkey: str = '', sound_midi_hotkey: str = '', available_midi_input_devices: Optional[list[tuple[str, str]]] = None, selected_midi_input_device_ids: Optional[list[str]] = None, start_dir: str = '', language: str = 'en', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/utility_sound_button_dialog.py:48)
- `_refresh_mode_visibility(self) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:289)
- `_browse_lyric_file(self) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:310)
- `_browse_automation_script_file(self) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:325)
- `_set_midi_binding(self, token: str) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:340)
- `_start_midi_learn(self) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:345)
- `_on_midi_binding(self, token: str, source_selector: str = '') -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:349)
- `_make_spin(low: int, high: int) -> QSpinBox` [staticmethod] (pyssp/ui/utility_sound_button_dialog.py:361)
- `_nudge_duration_ms(self, delta_ms: int) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:366)
- `_set_combo_data(combo: QComboBox, value: object, fallback: object) -> None` [staticmethod] (pyssp/ui/utility_sound_button_dialog.py:373)

### `UtilityDurationEdit`

- Defined at `pyssp/ui/utility_sound_button_dialog.py:385`
- Bases: QLineEdit

#### Public Members

- `parse_duration_ms(cls, value: str) -> Optional[int]` [classmethod] (pyssp/ui/utility_sound_button_dialog.py:395)
- `format_duration_ms(cls, duration_ms: Optional[int]) -> str` [classmethod] (pyssp/ui/utility_sound_button_dialog.py:411)
- `set_duration_ms(self, duration_ms: Optional[int]) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:419)
- `duration_ms(self) -> Optional[int]` [method] (pyssp/ui/utility_sound_button_dialog.py:422)
- `keyPressEvent(self, event) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:425)
- `focusOutEvent(self, event) -> None` [method] (pyssp/ui/utility_sound_button_dialog.py:436)

#### Internal Members

- `__init__(self, duration_ms: Optional[int] = None, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/utility_sound_button_dialog.py:388)
