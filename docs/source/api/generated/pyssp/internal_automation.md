# `pyssp/internal_automation.py`

- Source: `pyssp/internal_automation.py`
- Module path: `pyssp.internal_automation`
- API entries: `11`

## Module Docstring

No module docstring.

## Constants

### Public

- `INTERNAL_AUTOMATION_CATEGORY_TRANSPORT` [constant] (pyssp/internal_automation.py:8)
  Detail: Value: 'Transport'
- `INTERNAL_AUTOMATION_CATEGORY_MODE` [constant] (pyssp/internal_automation.py:9)
  Detail: Value: 'Mode'
- `INTERNAL_AUTOMATION_CATEGORY_NAVIGATION` [constant] (pyssp/internal_automation.py:10)
  Detail: Value: 'Navigation'
- `INTERNAL_AUTOMATION_CATEGORY_TARGET` [constant] (pyssp/internal_automation.py:11)
  Detail: Value: 'Target'
- `INTERNAL_AUTOMATION_CATEGORY_STAGE` [constant] (pyssp/internal_automation.py:12)
  Detail: Value: 'Stage'
- `INTERNAL_AUTOMATION_COMMANDS` [constant] (pyssp/internal_automation.py:15)
  Detail: Value: ({'id': 'play', 'label': 'Play Sound Button', 'category': INTERNAL_AUTOMATION...

## Functions

### Public

- `list_internal_automation_commands() -> list[dict[str, Any]]` [function] (pyssp/internal_automation.py:47)
- `normalize_internal_automation_command_id(raw: object) -> str` [function] (pyssp/internal_automation.py:58)
- `normalize_internal_automation_params(command_id: object, raw: object) -> dict[str, Any]` [function] (pyssp/internal_automation.py:63)
- `internal_automation_command_summary(command_id: object, params: object) -> str` [function] (pyssp/internal_automation.py:127)
- `internal_automation_dispatch(command_id: object, params: object) -> tuple[str, dict[str, Any]]` [function] (pyssp/internal_automation.py:172)
