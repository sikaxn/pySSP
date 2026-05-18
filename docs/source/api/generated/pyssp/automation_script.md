# `pyssp/automation_script.py`

- Source: `pyssp/automation_script.py`
- Module path: `pyssp.automation_script`
- API entries: `19`

## Module Docstring

No module docstring.

## Constants

### Public

- `AUTOMATION_SCRIPT_EXTENSION` [constant] (pyssp/automation_script.py:18)
  Detail: Value: '.pysspautoscript'
- `AUTOMATION_SCRIPT_FORMAT` [constant] (pyssp/automation_script.py:19)
  Detail: Value: 'pysspautoscript'
- `AUTOMATION_SCRIPT_VERSION` [constant] (pyssp/automation_script.py:20)
  Detail: Value: 1
- `AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND` [constant] (pyssp/automation_script.py:21)
  Detail: Value: 'companion_command'
- `AUTOMATION_SCRIPT_ACTION_TYPE_INTERNAL_COMMAND` [constant] (pyssp/automation_script.py:22)
  Detail: Value: 'internal_command'

## Functions

### Public

- `normalize_automation_script_action(raw: object) -> Optional[AutomationScriptAction]` [function] (pyssp/automation_script.py:44)
- `normalize_automation_script_cue(raw: object) -> Optional[AutomationScriptCue]` [function] (pyssp/automation_script.py:83)
- `normalize_automation_script(raw: object) -> Optional[AutomationScript]` [function] (pyssp/automation_script.py:111)
- `automation_script_action_to_dict(action: AutomationScriptAction) -> dict[str, Any]` [function] (pyssp/automation_script.py:143)
- `automation_script_cue_to_dict(cue: AutomationScriptCue) -> dict[str, Any]` [function] (pyssp/automation_script.py:153)
- `automation_script_to_dict(script: Optional[AutomationScript]) -> dict[str, Any]` [function] (pyssp/automation_script.py:168)
- `load_automation_script(file_path: str) -> AutomationScript` [function] (pyssp/automation_script.py:184)
- `save_automation_script(file_path: str, script: Optional[AutomationScript]) -> None` [function] (pyssp/automation_script.py:203)
- `automation_script_cue_command_summary(cue: Optional[AutomationScriptCue]) -> str` [function] (pyssp/automation_script.py:211)
- `automation_script_command_display_name(spec: Optional[AutomationCommandSpec]) -> str` [function] (pyssp/automation_script.py:223)
- `find_automation_script_cue_indices(script: Optional[AutomationScript], position_ms: int) -> tuple[int, int]` [function] (pyssp/automation_script.py:230)

## Classes

### `AutomationScriptAction`

- Defined at `pyssp/automation_script.py:26`

### `AutomationScriptCue`

- Defined at `pyssp/automation_script.py:32`

### `AutomationScript`

- Defined at `pyssp/automation_script.py:39`
