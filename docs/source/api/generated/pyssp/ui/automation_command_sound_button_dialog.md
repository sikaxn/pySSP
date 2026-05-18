# `pyssp/ui/automation_command_sound_button_dialog.py`

- Source: `pyssp/ui/automation_command_sound_button_dialog.py`
- Module path: `pyssp.ui.automation_command_sound_button_dialog`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `AutomationCommandSoundButtonDialog`

- Defined at `pyssp/ui/automation_command_sound_button_dialog.py:69`
- Bases: QDialog

#### Public Members

- `values(self) -> tuple[str, str, AutomationCommandSpec, Optional[str], str, str]` [method] (pyssp/ui/automation_command_sound_button_dialog.py:429)
- `selected_location(self) -> str` [method] (pyssp/ui/automation_command_sound_button_dialog.py:441)
- `selected_button_text(self) -> str` [method] (pyssp/ui/automation_command_sound_button_dialog.py:461)
- `handle_midi_message(self, token: str, source_selector: str = '', status: int = 0, data1: int = 0, data2: int = 0) -> bool` [method] (pyssp/ui/automation_command_sound_button_dialog.py:474)

#### Internal Members

- `__init__(self, *, caption: str, notes: str, automation_spec: Optional[AutomationCommandSpec] = None, custom_color: Optional[str] = None, sound_hotkey: str = '', sound_midi_hotkey: str = '', available_midi_input_devices: Optional[list[tuple[str, str]]] = None, selected_midi_input_device_ids: Optional[list[str]] = None, companion_payload: Optional[dict] = None, internal_target_catalog: Optional[dict] = None, hide_black_empty: bool = True, language: str = 'en', selection_only: bool = False, window_title: Optional[str] = None, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/automation_command_sound_button_dialog.py:70)
- `_apply_filters(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:490)
- `_find_location_row(self, location: str) -> int` [method] (pyssp/ui/automation_command_sound_button_dialog.py:538)
- `_sync_selected_command(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:548)
- `_update_caption_auto_value(self, value: str) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:563)
- `_on_caption_text_edited(self, _text: str) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:572)
- `_on_location_mode_changed(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:575)
- `_populate_internal_command_list(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:586)
- `_page_label_for_target(self, group: str, page_number: int) -> str` [method] (pyssp/ui/automation_command_sound_button_dialog.py:596)
- `_button_label_for_target(self, group: str, page_number: int, slot_number: int) -> str` [method] (pyssp/ui/automation_command_sound_button_dialog.py:601)
- `_refresh_internal_target_page_choices(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:606)
- `_refresh_internal_target_slot_choices(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:617)
- `_selected_internal_command_id(self) -> str` [method] (pyssp/ui/automation_command_sound_button_dialog.py:632)
- `_selected_spec_from_ui(self) -> AutomationCommandSpec` [method] (pyssp/ui/automation_command_sound_button_dialog.py:638)
- `_selected_internal_params(self, command_id: str) -> dict` [method] (pyssp/ui/automation_command_sound_button_dialog.py:658)
- `_refresh_internal_form_visibility(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:691)
- `_apply_internal_spec(self, spec: AutomationCommandSpec) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:767)
- `_selected_internal_target_value(self, command_id: str) -> str` [method] (pyssp/ui/automation_command_sound_button_dialog.py:796)
- `_apply_internal_target_value(self, command_id: str, value: str) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:806)
- `_parse_internal_target_value(command_id: str, value: str) -> Optional[tuple[str, int, Optional[int], str]]` [staticmethod] (pyssp/ui/automation_command_sound_button_dialog.py:834)
- `_refresh_custom_color_button(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:856)
- `_pick_custom_color(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:870)
- `_clear_custom_color(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:877)
- `_set_midi_binding(self, token: str) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:881)
- `_start_midi_learn(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:886)
- `_on_midi_binding(self, token: str, source_selector: str = '') -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:890)
- `_apply_selection_only_mode(self) -> None` [method] (pyssp/ui/automation_command_sound_button_dialog.py:901)
