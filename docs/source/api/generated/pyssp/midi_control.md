# `pyssp/midi_control.py`

- Source: `pyssp/midi_control.py`
- Module path: `pyssp.midi_control`
- API entries: `12`

## Module Docstring

No module docstring.

## Functions

### Public

- `midi_input_name_selector(device_name: str) -> str` [function] (pyssp/midi_control.py:62)
- `midi_input_selector_name(selector: str) -> str` [function] (pyssp/midi_control.py:66)
- `list_midi_input_devices(force_refresh: bool = False) -> List[Tuple[str, str]]` [function] (pyssp/midi_control.py:75)
- `normalize_midi_binding(value: str) -> str` [function] (pyssp/midi_control.py:104)
- `split_midi_binding(value: str) -> Tuple[str, str]` [function] (pyssp/midi_control.py:138)
- `midi_event_to_binding(status: int, data1: int, data2: int) -> str` [function] (pyssp/midi_control.py:148)
- `midi_binding_to_display(binding: str) -> str` [function] (pyssp/midi_control.py:161)

### Internal

- `_ensure_midi_init() -> bool` [function] (pyssp/midi_control.py:22)
- `_refresh_midi_backend() -> bool` [function] (pyssp/midi_control.py:37)

## Classes

### `MidiInputDevice`

- Defined at `pyssp/midi_control.py:57`

### `MidiInputRouter`

- Defined at `pyssp/midi_control.py:190`

#### Public Members

- `set_callback(self, callback: Optional[Callable[[str, str, int, int, int], None]]) -> None` [method] (pyssp/midi_control.py:203)
- `set_devices(self, device_ids: List[str], force_refresh: bool = False) -> None` [method] (pyssp/midi_control.py:206)
- `selected_device_ids(self) -> List[str]` [method] (pyssp/midi_control.py:232)
- `missing_selected_selectors(self) -> List[str]` [method] (pyssp/midi_control.py:235)
- `poll(self, max_events_per_device: int = 64) -> None` [method] (pyssp/midi_control.py:238)
- `close(self) -> None` [method] (pyssp/midi_control.py:281)
- `clear_pending(self, max_reads_per_device: int = 8, max_events_per_read: int = 128) -> None` [method] (pyssp/midi_control.py:288)

#### Internal Members

- `__init__(self, callback: Optional[Callable[[str, str, int, int, int], None]] = None) -> None` [constructor] (pyssp/midi_control.py:191)
- `_resolve_device_ids(self, selectors: List[str], force_refresh: bool = False) -> List[str]` [method] (pyssp/midi_control.py:298)
- `_resync_selected_devices(self, force_refresh: bool = False) -> None` [method] (pyssp/midi_control.py:342)
- `_open_input(self, device_id: str) -> None` [method] (pyssp/midi_control.py:348)
- `_close_input(self, device_id: str) -> None` [method] (pyssp/midi_control.py:357)
- `_verify_open_inputs_against_enumeration(self) -> None` [method] (pyssp/midi_control.py:366)
- `_recompute_missing_selectors(self) -> None` [method] (pyssp/midi_control.py:381)

### `MidiPollingThread`

- Defined at `pyssp/midi_control.py:397`
- Bases: QThread

#### Public Members

- `update_devices(self, midi_selectors: List[str], launchpad_selectors: List[str]) -> None` [method] (pyssp/midi_control.py:419)
- `stop(self) -> None` [method] (pyssp/midi_control.py:424)
- `run(self) -> None` [method] (pyssp/midi_control.py:427)

#### Internal Members

- `__init__(self, parent = None) -> None` [constructor] (pyssp/midi_control.py:402)
- `_emit_midi_event(self, token: str, selector: str, status: int, data1: int, data2: int) -> None` [method] (pyssp/midi_control.py:507)
- `_emit_launchpad_event(self, token: str, selector: str, status: int, data1: int, data2: int) -> None` [method] (pyssp/midi_control.py:510)
