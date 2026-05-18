# `pyssp/companion_remote_control.py`

- Source: `pyssp/companion_remote_control.py`
- Module path: `pyssp.companion_remote_control`
- API entries: `6`

## Module Docstring

No module docstring.

## Functions

### Public

- `normalize_companion_command_mode(raw: object) -> str` [function] (pyssp/companion_remote_control.py:8)
- `normalize_companion_command_action(raw: object) -> str` [function] (pyssp/companion_remote_control.py:13)
- `send_companion_location_command(*, host: str, mode: str, tcp_port: int, udp_port: int, http_port: int, location: str, action: str, timeout: float = 2.0) -> tuple[bool, str]` [function] (pyssp/companion_remote_control.py:18)

### Internal

- `_send_tcp(host: str, port: int, location: str, action: str, *, timeout: float) -> tuple[bool, str]` [function] (pyssp/companion_remote_control.py:42)
- `_send_udp(host: str, port: int, location: str, action: str, *, timeout: float) -> tuple[bool, str]` [function] (pyssp/companion_remote_control.py:52)
- `_send_http(host: str, port: int, location: str, action: str, *, timeout: float) -> tuple[bool, str]` [function] (pyssp/companion_remote_control.py:63)
