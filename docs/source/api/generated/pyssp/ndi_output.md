# `pyssp/ndi_output.py`

- Source: `pyssp/ndi_output.py`
- Module path: `pyssp.ndi_output`
- API entries: `4`

## Module Docstring

No module docstring.

## Functions

### Internal

- `_print_ndi_error(message: str) -> None` [function] (pyssp/ndi_output.py:17)

## Classes

### `NDIOutputConfig`

- Defined at `pyssp/ndi_output.py:28`

### `NDIOutputSender`

- Defined at `pyssp/ndi_output.py:36`

#### Public Members

- `available(self) -> bool` [property] (pyssp/ndi_output.py:53)
- `configure(self, config: NDIOutputConfig) -> bool` [method] (pyssp/ndi_output.py:56)
- `stop(self) -> None` [method] (pyssp/ndi_output.py:90)
- `get_num_connections(self, timeout: float = 0.0) -> int` [method] (pyssp/ndi_output.py:101)
- `send_video_frame(self, image: QImage) -> bool` [method] (pyssp/ndi_output.py:110)
- `send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool` [method] (pyssp/ndi_output.py:119)

#### Internal Members

- `__init__(self, status: NDICapabilityStatus, *, session_factory: Optional[Callable[[str, NDIRuntimeSenderConfig], NDIRuntimeSenderSession]] = None) -> None` [constructor] (pyssp/ndi_output.py:37)
- `_try_send_audio(session: NDIRuntimeSenderSession, frames: np.ndarray, sample_rate: int) -> tuple[bool, str]` [staticmethod] (pyssp/ndi_output.py:150)
- `_is_recoverable_audio_error(message: str) -> bool` [staticmethod] (pyssp/ndi_output.py:157)
- `_recover_audio_sender(self) -> bool` [method] (pyssp/ndi_output.py:166)
- `_set_audio_error(self, message: str) -> None` [method] (pyssp/ndi_output.py:174)
- `_clear_audio_error(self) -> None` [method] (pyssp/ndi_output.py:181)

### `NDIOutputDispatcher`

- Defined at `pyssp/ndi_output.py:185`

#### Public Members

- `available(self) -> bool` [property] (pyssp/ndi_output.py:217)
- `configure(self, config: NDIOutputConfig) -> bool` [method] (pyssp/ndi_output.py:220)
- `stop(self) -> None` [method] (pyssp/ndi_output.py:238)
- `shutdown(self) -> None` [method] (pyssp/ndi_output.py:247)
- `get_num_connections(self, timeout: float = 0.0) -> int` [method] (pyssp/ndi_output.py:259)
- `send_video_frame(self, image: QImage) -> bool` [method] (pyssp/ndi_output.py:263)
- `send_audio_frames(self, frames: np.ndarray, sample_rate: int) -> bool` [method] (pyssp/ndi_output.py:271)

#### Internal Members

- `__init__(self, status: NDICapabilityStatus, *, sender_factory: Optional[Callable[[NDICapabilityStatus], NDIOutputSender]] = None, connection_poll_interval_sec: float = 0.25, max_audio_queue_blocks: int = 24) -> None` [constructor] (pyssp/ndi_output.py:186)
- `_sync_public_state(self) -> None` [method] (pyssp/ndi_output.py:288)
- `_set_audio_error(self, message: str) -> None` [method] (pyssp/ndi_output.py:297)
- `_clear_audio_error(self) -> None` [method] (pyssp/ndi_output.py:304)
- `_worker_loop(self) -> None` [method] (pyssp/ndi_output.py:307)
