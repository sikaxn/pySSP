# `pyssp/dsp.py`

- Source: `pyssp/dsp.py`
- Module path: `pyssp.dsp`
- API entries: `6`

## Module Docstring

No module docstring.

## Functions

### Public

- `normalize_config(config: Optional[DSPConfig]) -> DSPConfig` [function] (pyssp/dsp.py:31)
- `has_active_processing(config: Optional[DSPConfig]) -> bool` [function] (pyssp/dsp.py:49)

### Internal

- `_load_pedalboard_backend() -> Optional[_PedalboardBackend]` [function] (pyssp/dsp.py:217)

## Classes

### `DSPConfig`

- Defined at `pyssp/dsp.py:10`

### `_PedalboardBackend`

- Defined at `pyssp/dsp.py:20`

### `RealTimeDSPProcessor`

- Defined at `pyssp/dsp.py:62`

#### Public Members

- `set_config(self, config: DSPConfig) -> None` [method] (pyssp/dsp.py:75)
- `reset(self) -> None` [method] (pyssp/dsp.py:79)
- `process_block(self, block: np.ndarray) -> np.ndarray` [method] (pyssp/dsp.py:88)

#### Internal Members

- `__init__(self, sample_rate: int, channels: int) -> None` [constructor] (pyssp/dsp.py:66)
- `_rebuild_pedalboard(self) -> None` [method] (pyssp/dsp.py:108)
- `_build_input_gain_plugin(self, backend: _PedalboardBackend) -> Optional[object]` [method] (pyssp/dsp.py:130)
- `_recommended_headroom_db(self) -> float` [method] (pyssp/dsp.py:138)
- `_build_eq_plugins(self, backend: _PedalboardBackend) -> List[object]` [method] (pyssp/dsp.py:148)
- `_build_reverb_plugin(self, backend: _PedalboardBackend) -> Optional[object]` [method] (pyssp/dsp.py:175)
- `_build_external_plugins(self, backend: _PedalboardBackend) -> List[object]` [method] (pyssp/dsp.py:188)
- `_coerce_output_shape(self, processed: object, expected_frames: int) -> np.ndarray` [method] (pyssp/dsp.py:197)
