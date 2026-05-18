# `pyssp/ui/options_dialog/device_midi.py`

- Source: `pyssp/ui/options_dialog/device_midi.py`
- Module path: `pyssp.ui.options_dialog.device_midi`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `DeviceMidiMixin`

- Defined at `pyssp/ui/options_dialog/device_midi.py:7`

#### Public Members

- `handle_midi_message(self, token: str, source_selector: str = '', status: int = 0, data1: int = 0, data2: int = 0) -> bool` [method] (pyssp/ui/options_dialog/device_midi.py:235)

#### Internal Members

- `_populate_launchpad_device_combo(self) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:8)
- `_populate_launchpad_output_combo(self) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:31)
- `_sync_launchpad_controls(self) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:54)
- `_refresh_midi_input_devices(self, force_refresh: bool = False) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:71)
- `_checked_midi_input_device_ids(self) -> List[str]` [method] (pyssp/ui/options_dialog/device_midi.py:158)
- `_checked_midi_input_device_names(self) -> List[str]` [method] (pyssp/ui/options_dialog/device_midi.py:176)
- `_on_midi_input_selection_changed(self, _item = None) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:190)
- `_start_midi_learning(self, target: MidiCaptureEdit) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:194)
- `_start_midi_rotary_learning(self, target: MidiCaptureEdit) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:205)
- `_on_midi_binding_captured(self, token: str, source_selector: str = '') -> None` [method] (pyssp/ui/options_dialog/device_midi.py:223)
- `_set_midi_info(self, text: str) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:320)
- `_normalize_midi_relative_mode(value: str) -> str` [staticmethod] (pyssp/ui/options_dialog/device_midi.py:333)
- `_decode_relative_delta(value: int, mode: str) -> int` [staticmethod] (pyssp/ui/options_dialog/device_midi.py:340)
- `_infer_midi_relative_mode(self, forward_values: List[int], backward_values: List[int]) -> str` [method] (pyssp/ui/options_dialog/device_midi.py:360)
- `_set_midi_rotary_relative_mode_for_target(self, target: MidiCaptureEdit, mode: str) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:383)
- `_set_combo_data_or_default(self, combo: QComboBox, selected_data, default_data) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:396)
- `_set_combo_float_or_default(self, combo: QComboBox, selected_value: float, default_value: float) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:404)
- `_populate_audio_devices(self, devices: List[str], selected_device: str) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:427)
- `_refresh_audio_devices(self) -> None` [method] (pyssp/ui/options_dialog/device_midi.py:443)
