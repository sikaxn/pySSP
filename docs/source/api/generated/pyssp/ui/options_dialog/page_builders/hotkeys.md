# `pyssp/ui/options_dialog/page_builders/hotkeys.py`

- Source: `pyssp/ui/options_dialog/page_builders/hotkeys.py`
- Module path: `pyssp.ui.options_dialog.page_builders.hotkeys`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `HotkeysPageMixin`

- Defined at `pyssp/ui/options_dialog/page_builders/hotkeys.py:46`

#### Internal Members

- `_build_hotkey_page(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:47)
- `_build_midi_control_page(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:65)
- `_build_midi_settings_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:83)
- `_build_launchpad_hotkey_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:143)
- `_build_midi_system_hotkey_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:226)
- `_build_midi_system_rotary_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:239)
- `_build_rotary_invert_row(self, invert_checkbox: QCheckBox) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:327)
- `_build_rotary_option_row(self, invert_checkbox: QCheckBox, sensitivity_spin: QSpinBox) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:335)
- `_build_midi_learn_row(self, edit: MidiCaptureEdit, rotary: bool = False) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:346)
- `_build_midi_quick_action_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:364)
- `_build_midi_sound_button_hotkey_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:397)
- `_add_midi_row(self, form: QFormLayout, key: str, label: str) -> None` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:427)
- `_build_system_hotkey_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:457)
- `_build_quick_action_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:470)
- `_build_sound_button_hotkey_tab(self) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:500)
- `_add_hotkey_row(self, form: QFormLayout, key: str, label: str) -> None` [method] (pyssp/ui/options_dialog/page_builders/hotkeys.py:528)
