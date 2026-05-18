# `pyssp/launchpad.py`

- Source: `pyssp/launchpad.py`
- Module path: `pyssp.launchpad`
- API entries: `34`

## Module Docstring

No module docstring.

## Constants

### Public

- `LAUNCHPAD_PROFILE_PROGRAMMER` [constant] (pyssp/launchpad.py:10)
  Detail: Value: 'programmer'
- `LAUNCHPAD_LAYOUT_BOTTOM_SIX` [constant] (pyssp/launchpad.py:11)
  Detail: Value: 'bottom_six'
- `LAUNCHPAD_LAYOUT_TOP_SIX` [constant] (pyssp/launchpad.py:12)
  Detail: Value: 'top_six'
- `LAUNCHPAD_MODE_PROGRAMMER` [constant] (pyssp/launchpad.py:13)
  Detail: Value: 1
- `LAUNCHPAD_MODE_LIVE` [constant] (pyssp/launchpad.py:14)
  Detail: Value: 0
- `LAUNCHPAD_ACTION_NONE` [constant] (pyssp/launchpad.py:20)
  Detail: Value: ''
- `LAUNCHPAD_ACTION_SHIFT_LAYER` [constant] (pyssp/launchpad.py:21)
  Detail: Value: 'shift_layer'
- `LAUNCHPAD_SLOT_PAD_COUNT` [constant] (pyssp/launchpad.py:22)
  Detail: Value: 48
- `LAUNCHPAD_CONTROL_PAD_COUNT` [constant] (pyssp/launchpad.py:23)
  Detail: Value: 16
- `LAUNCHPAD_SHIFT_CONTROL_INDEX` [constant] (pyssp/launchpad.py:24)
  Detail: Value: 8

## Functions

### Public

- `launchpad_layout_options() -> List[LaunchpadLayoutOption]` [function] (pyssp/launchpad.py:39)
- `launchpad_profile_label(profile: str) -> str` [function] (pyssp/launchpad.py:46)
- `normalize_launchpad_profile(profile: str) -> str` [function] (pyssp/launchpad.py:52)
- `normalize_launchpad_layout(layout: str) -> str` [function] (pyssp/launchpad.py:59)
- `launchpad_programmer_note(top_row: int, left_col: int) -> int` [function] (pyssp/launchpad.py:66)
- `launchpad_page_slot_note(slot_index: int, layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX) -> int` [function] (pyssp/launchpad.py:76)
- `launchpad_control_note(control_index: int, layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX) -> int` [function] (pyssp/launchpad.py:87)
- `launchpad_page_slot_binding(slot_index: int, layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX, profile: str = LAUNCHPAD_PROFILE_PROGRAMMER, channel: int = 1, selector: str = '') -> str` [function] (pyssp/launchpad.py:98)
- `launchpad_page_bindings(layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX, profile: str = LAUNCHPAD_PROFILE_PROGRAMMER, channel: int = 1, selector: str = '') -> List[str]` [function] (pyssp/launchpad.py:117)
- `launchpad_control_binding(control_index: int, layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX, profile: str = LAUNCHPAD_PROFILE_PROGRAMMER, channel: int = 1, selector: str = '') -> str` [function] (pyssp/launchpad.py:135)
- `launchpad_control_bindings(layout: str = LAUNCHPAD_LAYOUT_BOTTOM_SIX, profile: str = LAUNCHPAD_PROFILE_PROGRAMMER, channel: int = 1, selector: str = '') -> List[str]` [function] (pyssp/launchpad.py:154)
- `is_launchpad_name(device_name: str) -> bool` [function] (pyssp/launchpad.py:172)
- `normalize_launchpad_device_key(device_name: str) -> str` [function] (pyssp/launchpad.py:177)
- `launchpad_device_family_id(device_name: str) -> Optional[int]` [function] (pyssp/launchpad.py:187)
- `launchpad_programmer_toggle_sysex(device_name: str, enabled: bool = True) -> bytes` [function] (pyssp/launchpad.py:198)
- `launchpad_find_matching_output(input_device_name: str, output_devices: Sequence[Tuple[str, str]]) -> Tuple[str, str]` [function] (pyssp/launchpad.py:206)
- `launchpad_slot_action_key(slot_index: int) -> str` [function] (pyssp/launchpad.py:240)
- `launchpad_action_slot_index(action_key: str) -> Optional[int]` [function] (pyssp/launchpad.py:245)
- `build_launchpad_action_options(action_rows: Sequence[Tuple[str, str]]) -> List[LaunchpadActionOption]` [function] (pyssp/launchpad.py:258)
- `normalize_launchpad_action_bindings(values: Sequence[str]) -> List[str]` [function] (pyssp/launchpad.py:265)
- `launchpad_rgb_color(color_hex: str) -> Tuple[int, int, int]` [function] (pyssp/launchpad.py:272)
- `launchpad_led_rgb_sysex(device_name: str, led_colors: Sequence[Tuple[int, str]]) -> bytes` [function] (pyssp/launchpad.py:285)

## Classes

### `LaunchpadLayoutOption`

- Defined at `pyssp/launchpad.py:28`

### `LaunchpadActionOption`

- Defined at `pyssp/launchpad.py:34`
