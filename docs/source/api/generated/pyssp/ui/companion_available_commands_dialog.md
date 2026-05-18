# `pyssp/ui/companion_available_commands_dialog.py`

- Source: `pyssp/ui/companion_available_commands_dialog.py`
- Module path: `pyssp.ui.companion_available_commands_dialog`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `CompanionAvailableCommandsDialog`

- Defined at `pyssp/ui/companion_available_commands_dialog.py:29`
- Bases: QWidget

#### Public Members

- `minimumSizeHint(self) -> QSize` [method] (pyssp/ui/companion_available_commands_dialog.py:111)
- `sizeHint(self) -> QSize` [method] (pyssp/ui/companion_available_commands_dialog.py:114)
- `set_bypass_checked(self, checked: bool) -> None` [method] (pyssp/ui/companion_available_commands_dialog.py:117)
- `set_payload(self, payload: dict, *, hide_black_empty: bool = False, hide_navigation: bool = False) -> None` [method] (pyssp/ui/companion_available_commands_dialog.py:122)
- `selected_location(self) -> str` [method] (pyssp/ui/companion_available_commands_dialog.py:182)

#### Internal Members

- `__init__(self, parent = None) -> None` [constructor] (pyssp/ui/companion_available_commands_dialog.py:34)
- `_apply_filters(self, _text: str = '', *, hide_black_empty: bool | None = None, hide_navigation: bool | None = None) -> None` [method] (pyssp/ui/companion_available_commands_dialog.py:132)
- `_emit_selected_location_command(self, action: str) -> None` [method] (pyssp/ui/companion_available_commands_dialog.py:191)
