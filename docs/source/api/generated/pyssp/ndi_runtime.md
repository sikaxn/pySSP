# `pyssp/ndi_runtime.py`

- Source: `pyssp/ndi_runtime.py`
- Module path: `pyssp.ndi_runtime`
- API entries: `10`

## Module Docstring

No module docstring.

## Functions

### Public

- `probe_runtime_version(library_path: str) -> str` [function] (pyssp/ndi_runtime.py:299)

### Internal

- `_fourcc(ch0: str, ch1: str, ch2: str, ch3: str) -> int` [function] (pyssp/ndi_runtime.py:19)
- `_fps_fraction(value: float) -> Fraction` [function] (pyssp/ndi_runtime.py:71)

## Classes

### `NDIRuntimeError`

- Defined at `pyssp/ndi_runtime.py:31`
- Bases: RuntimeError

### `_NDIlib_send_create_t`

- Defined at `pyssp/ndi_runtime.py:35`
- Bases: ctypes.Structure

### `_NDIlib_video_frame_v2_t`

- Defined at `pyssp/ndi_runtime.py:44`
- Bases: ctypes.Structure

### `_NDIlib_audio_frame_interleaved_32f_t`

- Defined at `pyssp/ndi_runtime.py:61`
- Bases: ctypes.Structure

### `_NDIRuntimeLibrary`

- Defined at `pyssp/ndi_runtime.py:84`

#### Public Members

- `acquire(cls, library_path: str) -> '_NDIRuntimeLibrary'` [classmethod] (pyssp/ndi_runtime.py:89)
- `release(self) -> None` [method] (pyssp/ndi_runtime.py:150)

#### Internal Members

- `__init__(self, library_path: str) -> None` [constructor] (pyssp/ndi_runtime.py:101)
- `_bind(self) -> None` [method] (pyssp/ndi_runtime.py:126)

### `NDIRuntimeSenderConfig`

- Defined at `pyssp/ndi_runtime.py:169`

### `NDIRuntimeSenderSession`

- Defined at `pyssp/ndi_runtime.py:177`

#### Public Members

- `version_text(self) -> str` [property] (pyssp/ndi_runtime.py:194)
- `close(self) -> None` [method] (pyssp/ndi_runtime.py:226)
- `get_num_connections(self, timeout: float = 0.0) -> int` [method] (pyssp/ndi_runtime.py:242)
- `send_video_frame(self, image: QImage) -> bool` [method] (pyssp/ndi_runtime.py:251)
- `send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool` [method] (pyssp/ndi_runtime.py:277)

#### Internal Members

- `__init__(self, library_path: str, config: NDIRuntimeSenderConfig) -> None` [constructor] (pyssp/ndi_runtime.py:178)
- `_create_sender(self)` [method] (pyssp/ndi_runtime.py:197)
- `_build_video_frame(self) -> _NDIlib_video_frame_v2_t` [method] (pyssp/ndi_runtime.py:209)
