# `pyssp/ui/sound_button_automation_dialog.py`

- Source: `pyssp/ui/sound_button_automation_dialog.py`
- Module path: `pyssp.ui.sound_button_automation_dialog`
- API entries: `4`

## Module Docstring

No module docstring.

## Classes

### `_CommandListEditor`

- Defined at `pyssp/ui/sound_button_automation_dialog.py:44`
- Bases: QGroupBox

#### Public Members

- `commands(self) -> list[AutomationCommandSpec]` [method] (pyssp/ui/sound_button_automation_dialog.py:96)
- `set_commands(self, commands: Optional[list[AutomationCommandSpec]]) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:103)

#### Internal Members

- `__init__(self, title: str, *, commands: Optional[list[AutomationCommandSpec]] = None, open_picker, on_changed = None, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/sound_button_automation_dialog.py:45)
- `_refresh_list(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:111)
- `_refresh_button_state(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:124)
- `_add_command(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:134)
- `_edit_selected_command(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:143)
- `_remove_selected_command(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:155)
- `_move_selected(self, delta: int) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:163)
- `_clear_commands(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:175)
- `_emit_changed(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:180)

### `_AdvancedAutomationRowDialog`

- Defined at `pyssp/ui/sound_button_automation_dialog.py:185`
- Bases: QDialog

#### Public Members

- `values(self) -> Optional[tuple[str, AutomationCommandSpec]]` [method] (pyssp/ui/sound_button_automation_dialog.py:234)

#### Internal Members

- `__init__(self, *, row_data: Optional[tuple[str, AutomationCommandSpec]] = None, open_picker, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/sound_button_automation_dialog.py:186)
- `_select_command(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:241)
- `_refresh_command_label(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:248)

### `_AdvancedAutomationTable`

- Defined at `pyssp/ui/sound_button_automation_dialog.py:258`
- Bases: QGroupBox

#### Public Members

- `rows(self) -> list[tuple[str, AutomationCommandSpec]]` [method] (pyssp/ui/sound_button_automation_dialog.py:314)
- `set_rows(self, rows: Optional[list[tuple[str, AutomationCommandSpec]]]) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:322)
- `replace_event_rows(self, event_names: tuple[str, ...], replacement_rows: list[tuple[str, AutomationCommandSpec]]) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:328)

#### Internal Members

- `__init__(self, *, rows: Optional[list[tuple[str, AutomationCommandSpec]]] = None, open_picker, on_changed = None, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/sound_button_automation_dialog.py:259)
- `_append_row(self, event_name: str, spec: AutomationCommandSpec) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:360)
- `_refresh_table(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:367)
- `_refresh_button_state(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:387)
- `_open_row_dialog(self, current: Optional[tuple[str, AutomationCommandSpec]]) -> Optional[tuple[str, AutomationCommandSpec]]` [method] (pyssp/ui/sound_button_automation_dialog.py:397)
- `_add_row(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:410)
- `_edit_selected_row(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:419)
- `_remove_selected_row(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:431)
- `_move_selected(self, delta: int) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:439)
- `_clear_rows(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:451)
- `_emit_changed(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:456)

### `SoundButtonAutomationDialog`

- Defined at `pyssp/ui/sound_button_automation_dialog.py:461`
- Bases: QDialog

#### Public Members

- `values(self) -> Optional[SoundButtonAutomationConfig]` [method] (pyssp/ui/sound_button_automation_dialog.py:569)
- `selected_mode(self) -> str` [method] (pyssp/ui/sound_button_automation_dialog.py:590)

#### Internal Members

- `__init__(self, *, config: Optional[SoundButtonAutomationConfig] = None, companion_payload: Optional[dict] = None, internal_target_catalog: Optional[dict] = None, hide_black_empty: bool = True, language: str = 'en', parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/sound_button_automation_dialog.py:462)
- `_advanced_rows_to_data(self) -> dict[str, object]` [method] (pyssp/ui/sound_button_automation_dialog.py:580)
- `_refresh_mode_ui(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:596)
- `_open_picker_dialog(self, spec: Optional[AutomationCommandSpec]) -> Optional[AutomationCommandSpec]` [method] (pyssp/ui/sound_button_automation_dialog.py:610)
- `_sync_views_for_mode(self, mode: str) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:631)
- `_simple_rows(self) -> list[tuple[str, AutomationCommandSpec]]` [method] (pyssp/ui/sound_button_automation_dialog.py:646)
- `_set_simple_editors_from_advanced_rows(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:662)
- `_on_simple_lists_changed(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:681)
- `_on_advanced_rows_changed(self) -> None` [method] (pyssp/ui/sound_button_automation_dialog.py:693)
- `_config_to_advanced_rows(config: Optional[SoundButtonAutomationConfig]) -> list[tuple[str, AutomationCommandSpec]]` [staticmethod] (pyssp/ui/sound_button_automation_dialog.py:703)
