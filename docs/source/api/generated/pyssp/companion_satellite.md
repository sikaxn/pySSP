# `pyssp/companion_satellite.py`

- Source: `pyssp/companion_satellite.py`
- Module path: `pyssp.companion_satellite`
- API entries: `4`

## Module Docstring

No module docstring.

## Functions

### Internal

- `_parse_bool(raw: object) -> bool` [function] (pyssp/companion_satellite.py:16)
- `_decode_b64(raw: str) -> bytes` [function] (pyssp/companion_satellite.py:21)
- `_parse_line(raw_line: str) -> tuple[str, dict[str, str], str]` [function] (pyssp/companion_satellite.py:31)

## Classes

### `CompanionSatelliteClient`

- Defined at `pyssp/companion_satellite.py:52`

#### Public Members

- `default_serial_suffix() -> str` [staticmethod] (pyssp/companion_satellite.py:57)
- `is_running(self) -> bool` [property] (pyssp/companion_satellite.py:86)
- `start(self) -> None` [method] (pyssp/companion_satellite.py:90)
- `stop(self) -> None` [method] (pyssp/companion_satellite.py:99)
- `reconnect(self) -> None` [method] (pyssp/companion_satellite.py:110)
- `send_key_press(self, key: int, pressed: bool) -> bool` [method] (pyssp/companion_satellite.py:117)
- `send_change_page(self, next_page: bool) -> bool` [method] (pyssp/companion_satellite.py:124)

#### Internal Members

- `__init__(self, *, host: str, port: int, columns: int, rows: int, serial_suffix: str, on_event: SatelliteEventFn) -> None` [constructor] (pyssp/companion_satellite.py:60)
- `_emit(self, event_type: str, **payload: Any) -> None` [method] (pyssp/companion_satellite.py:129)
- `_set_socket(self, sock: Optional[socket.socket]) -> None` [method] (pyssp/companion_satellite.py:135)
- `_close_socket(self) -> None` [method] (pyssp/companion_satellite.py:139)
- `_send_line(self, line: str) -> bool` [method] (pyssp/companion_satellite.py:153)
- `_run(self) -> None` [method] (pyssp/companion_satellite.py:166)
- `_connection_loop(self, sock: socket.socket) -> None` [method] (pyssp/companion_satellite.py:199)
- `_handle_line(self, line: str) -> None` [method] (pyssp/companion_satellite.py:223)
- `_safe_int(raw: object, default: int = 0) -> int` [staticmethod] (pyssp/companion_satellite.py:267)
- `_register_device(self) -> None` [method] (pyssp/companion_satellite.py:273)
- `_normalize_serial_suffix(raw: object) -> str` [staticmethod] (pyssp/companion_satellite.py:283)
