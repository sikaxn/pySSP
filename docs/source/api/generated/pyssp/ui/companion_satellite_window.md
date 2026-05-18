# `pyssp/ui/companion_satellite_window.py`

- Source: `pyssp/ui/companion_satellite_window.py`
- Module path: `pyssp.ui.companion_satellite_window`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `_SatelliteButton`

- Defined at `pyssp/ui/companion_satellite_window.py:21`
- Bases: QToolButton

#### Public Members

- `mousePressEvent(self, event) -> None` [method] (pyssp/ui/companion_satellite_window.py:34)
- `mouseReleaseEvent(self, event) -> None` [method] (pyssp/ui/companion_satellite_window.py:39)

#### Internal Members

- `__init__(self, index: int, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/companion_satellite_window.py:24)

### `CompanionSatelliteWindow`

- Defined at `pyssp/ui/companion_satellite_window.py:45`
- Bases: QWidget

#### Public Members

- `closeEvent(self, event) -> None` [method] (pyssp/ui/companion_satellite_window.py:118)
- `set_target(self, host: str, port: int) -> None` [method] (pyssp/ui/companion_satellite_window.py:122)
- `set_grid_size(self, columns: int, rows: int) -> None` [method] (pyssp/ui/companion_satellite_window.py:125)
- `set_render_mode(self, mode: str) -> None` [method] (pyssp/ui/companion_satellite_window.py:148)
- `set_connection_state(self, state: str, message: str) -> None` [method] (pyssp/ui/companion_satellite_window.py:156)
- `clear_buttons(self) -> None` [method] (pyssp/ui/companion_satellite_window.py:159)
- `update_button(self, index: int, state: dict[str, object]) -> None` [method] (pyssp/ui/companion_satellite_window.py:165)
- `current_page(self) -> Optional[int]` [method] (pyssp/ui/companion_satellite_window.py:172)
- `current_page_button_states(self) -> list[dict[str, object]]` [method] (pyssp/ui/companion_satellite_window.py:188)

#### Internal Members

- `__init__(self, parent: Optional[QWidget] = None) -> None` [constructor] (pyssp/ui/companion_satellite_window.py:53)
- `_apply_button_state(self, index: int, state: dict[str, object]) -> None` [method] (pyssp/ui/companion_satellite_window.py:208)
- `_apply_styled_button(self, button: _SatelliteButton, index: int, text: str) -> None` [method] (pyssp/ui/companion_satellite_window.py:247)
- `_refresh_current_page_label(self) -> None` [method] (pyssp/ui/companion_satellite_window.py:257)
- `_pixmap(self, bitmap: bytes) -> QPixmap` [method] (pyssp/ui/companion_satellite_window.py:261)
