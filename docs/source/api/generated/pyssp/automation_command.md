# `pyssp/automation_command.py`

- Source: `pyssp/automation_command.py`
- Module path: `pyssp.automation_command`
- API entries: `30`

## Module Docstring

No module docstring.

## Constants

### Public

- `AUTOMATION_SOURCE_TYPE` [constant] (pyssp/automation_command.py:14)
  Detail: Value: 'automation'
- `AUTOMATION_COMMAND_SOURCE_COMPANION` [constant] (pyssp/automation_command.py:15)
  Detail: Value: 'companion'
- `AUTOMATION_COMMAND_SOURCE_INTERNAL` [constant] (pyssp/automation_command.py:16)
  Detail: Value: 'internal'
- `AUTOMATION_UNSUPPORTED_MARKER_TEXT` [constant] (pyssp/automation_command.py:17)
  Detail: Value: 'Unsupported automation command button. A newer version of pySSP is required.'
- `AUTOMATION_AUTO_RELEASE_IMMEDIATE` [constant] (pyssp/automation_command.py:18)
  Detail: Value: 'immediate'
- `AUTOMATION_AUTO_RELEASE_DOWN_ONLY` [constant] (pyssp/automation_command.py:19)
  Detail: Value: 'down_only'
- `AUTOMATION_DEFAULT_BUTTON_COLOR` [constant] (pyssp/automation_command.py:20)
  Detail: Value: '#E8C67A'
- `SOUND_BUTTON_AUTOMATION_MODE_SIMPLE` [constant] (pyssp/automation_command.py:21)
  Detail: Value: 'simple'
- `SOUND_BUTTON_AUTOMATION_MODE_ADVANCED` [constant] (pyssp/automation_command.py:22)
  Detail: Value: 'advanced'
- `SOUND_BUTTON_AUTOMATION_EVENTS` [constant] (pyssp/automation_command.py:23)
  Detail: Value: ('on_become_playing', 'on_leave_playing', 'on_trigger', 'on_play', 'on_fade_i...
- `SOUND_BUTTON_AUTOMATION_SIMPLE_EVENTS` [constant] (pyssp/automation_command.py:50)
  Detail: Value: ('on_become_playing', 'on_leave_playing', 'on_pause', 'on_resume_complete')
- `SOUND_BUTTON_AUTOMATION_EVENT_TOKENS` [constant] (pyssp/automation_command.py:56)
  Detail: Value: {'on_become_playing': 'onbecomeplaying', 'on_leave_playing': 'onleaveplaying'...
- `SOUND_BUTTON_AUTOMATION_EVENT_LABELS` [constant] (pyssp/automation_command.py:83)
  Detail: Value: {'on_become_playing': 'When playback starts', 'on_leave_playing': 'When playb...

## Functions

### Public

- `normalize_automation_location(raw: object) -> str` [function] (pyssp/automation_command.py:153)
- `normalize_automation_spec(raw: object) -> AutomationCommandSpec` [function] (pyssp/automation_command.py:167)
- `automation_spec_to_dict(spec: Optional[AutomationCommandSpec]) -> dict[str, Any]` [function] (pyssp/automation_command.py:202)
- `automation_display_name(spec: Optional[AutomationCommandSpec]) -> str` [function] (pyssp/automation_command.py:223)
- `automation_spec_is_internal(spec: Optional[AutomationCommandSpec]) -> bool` [function] (pyssp/automation_command.py:233)
- `automation_spec_is_companion(spec: Optional[AutomationCommandSpec]) -> bool` [function] (pyssp/automation_command.py:238)
- `automation_spec_is_valid(spec: Optional[AutomationCommandSpec]) -> bool` [function] (pyssp/automation_command.py:243)
- `automation_spec_detail_text(spec: Optional[AutomationCommandSpec]) -> str` [function] (pyssp/automation_command.py:250)
- `automation_spec_from_set_fields(*, source: object = '', location: object = '', button_text: object = '', hold_to_release: object = False, internal_command: object = '', internal_params_json: object = '') -> AutomationCommandSpec` [function] (pyssp/automation_command.py:257)
- `automation_spec_to_set_fields(spec: Optional[AutomationCommandSpec]) -> dict[str, str]` [function] (pyssp/automation_command.py:294)
- `normalize_sound_button_automation_config(raw: object) -> Optional[SoundButtonAutomationConfig]` [function] (pyssp/automation_command.py:319)
- `sound_button_automation_config_to_dict(config: Optional[SoundButtonAutomationConfig]) -> dict[str, Any]` [function] (pyssp/automation_command.py:369)
- `sound_button_automation_event_label(event_name: str) -> str` [function] (pyssp/automation_command.py:388)

### Internal

- `_normalize_optional_press_spec_list(raw: object) -> Optional[list[AutomationCommandSpec]]` [function] (pyssp/automation_command.py:393)
- `_normalize_sound_button_automation_mode(raw: object) -> str` [function] (pyssp/automation_command.py:427)

## Classes

### `AutomationCommandSpec`

- Defined at `pyssp/automation_command.py:113`

### `SoundButtonAutomationConfig`

- Defined at `pyssp/automation_command.py:123`
