# `pyssp/companion_available_commands.py`

- Source: `pyssp/companion_available_commands.py`
- Module path: `pyssp.companion_available_commands`
- API entries: `13`

## Module Docstring

No module docstring.

## Functions

### Public

- `get_companion_available_commands_path() -> Path` [function] (pyssp/companion_available_commands.py:11)
- `load_companion_available_commands() -> dict[str, Any]` [function] (pyssp/companion_available_commands.py:17)
- `clear_companion_available_commands() -> dict[str, Any]` [function] (pyssp/companion_available_commands.py:33)
- `record_companion_available_command(*, location: str, text: str, key_type: str = '', color: str = '', pressed: bool = False) -> Optional[dict[str, Any]]` [function] (pyssp/companion_available_commands.py:39)
- `format_companion_available_commands(payload: Optional[dict[str, Any]] = None) -> str` [function] (pyssp/companion_available_commands.py:75)
- `list_companion_available_commands(payload: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]` [function] (pyssp/companion_available_commands.py:97)
- `is_black_empty_command(entry: dict[str, Any]) -> bool` [function] (pyssp/companion_available_commands.py:121)
- `is_navigation_command(entry: dict[str, Any]) -> bool` [function] (pyssp/companion_available_commands.py:129)

### Internal

- `_save_payload(payload: dict[str, Any]) -> None` [function] (pyssp/companion_available_commands.py:134)
- `_parse_location(location: object) -> Optional[tuple[int, int, int]]` [function] (pyssp/companion_available_commands.py:140)
- `_safe_int(raw: object, default: int = 0) -> int` [function] (pyssp/companion_available_commands.py:156)
- `_normalize_button_text(raw: object) -> str` [function] (pyssp/companion_available_commands.py:163)
- `_stamp() -> str` [function] (pyssp/companion_available_commands.py:172)
