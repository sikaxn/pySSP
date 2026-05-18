# `pyssp/ui/dsp_window.py`

- Source: `pyssp/ui/dsp_window.py`
- Module path: `pyssp.ui.dsp_window`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `DSPWindow`

- Defined at `pyssp/ui/dsp_window.py:22`
- Bases: QDialog

#### Public Members

- `set_config(self, config: DSPConfig) -> None` [method] (pyssp/ui/dsp_window.py:152)
- `current_config(self) -> DSPConfig` [method] (pyssp/ui/dsp_window.py:161)

#### Internal Members

- `__init__(self, parent = None, language: str = 'en') -> None` [constructor] (pyssp/ui/dsp_window.py:33)
- `_update_reverb_label(self, value: int) -> None` [method] (pyssp/ui/dsp_window.py:140)
- `_update_eq_button_text(self, checked: bool) -> None` [method] (pyssp/ui/dsp_window.py:143)
- `_apply_eq_preset(self, name: str) -> None` [method] (pyssp/ui/dsp_window.py:146)
- `_on_eq_toggled(self, checked: bool) -> None` [method] (pyssp/ui/dsp_window.py:170)
- `_on_reverb_changed(self, value: int) -> None` [method] (pyssp/ui/dsp_window.py:174)
- `_on_tempo_changed(self, value: int) -> None` [method] (pyssp/ui/dsp_window.py:178)
- `_on_pitch_changed(self, value: int) -> None` [method] (pyssp/ui/dsp_window.py:182)
- `_emit_config_changed(self) -> None` [method] (pyssp/ui/dsp_window.py:186)
