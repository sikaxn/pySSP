# `pyssp/timecode.py`

- Source: `pyssp/timecode.py`
- Module path: `pyssp.timecode`
- API entries: `26`

## Module Docstring

No module docstring.

## Constants

### Public

- `TIMECODE_MODE_ZERO` [constant] (pyssp/timecode.py:20)
  Detail: Value: 'zero'
- `TIMECODE_MODE_FOLLOW` [constant] (pyssp/timecode.py:21)
  Detail: Value: 'follow_media'
- `TIMECODE_MODE_SYSTEM` [constant] (pyssp/timecode.py:22)
  Detail: Value: 'system_time'
- `TIMECODE_MODE_FOLLOW_FREEZE` [constant] (pyssp/timecode.py:23)
  Detail: Value: 'follow_media_freeze'
- `MTC_IDLE_KEEP_STREAM` [constant] (pyssp/timecode.py:25)
  Detail: Value: 'keep_stream'
- `MTC_IDLE_ALLOW_DARK` [constant] (pyssp/timecode.py:26)
  Detail: Value: 'allow_dark'
- `TIME_CODE_FPS_CHOICES` [constant] (pyssp/timecode.py:28)
  Detail: Value: [23.976, 24.0, 25.0, 29.97, 30.0, 48.0, 50.0, 59.94, 60.0]
- `TIME_CODE_MTC_FPS_CHOICES` [constant] (pyssp/timecode.py:29)
  Detail: Value: [24.0, 25.0, 29.97, 30.0]
- `TIME_CODE_SAMPLE_RATES` [constant] (pyssp/timecode.py:30)
  Detail: Value: [44100, 48000, 96000]
- `TIME_CODE_BIT_DEPTHS` [constant] (pyssp/timecode.py:31)
  Detail: Value: [8, 16, 32]
- `MIDI_OUTPUT_DEVICE_NONE` [constant] (pyssp/timecode.py:33)
  Detail: Value: '__none__'

## Functions

### Public

- `list_midi_output_devices() -> List[Tuple[str, str]]` [function] (pyssp/timecode.py:428)
- `encode_ltc_bits(frame_number: int, fps: int) -> list[int]` [function] (pyssp/timecode.py:461)
- `nominal_fps(display_fps: float) -> int` [function] (pyssp/timecode.py:867)
- `frame_to_timecode_parts(frame_number: int, fps: int) -> tuple[int, int, int, int]` [function] (pyssp/timecode.py:878)
- `frame_to_timecode_string(frame_number: int, fps: int) -> str` [function] (pyssp/timecode.py:892)
- `ms_to_timecode_string(position_ms: int, display_fps: float) -> str` [function] (pyssp/timecode.py:897)

### Internal

- `_ensure_pygame_midi_init() -> bool` [function] (pyssp/timecode.py:43)
- `_find_output_device_index(device_name: str) -> Optional[int]` [function] (pyssp/timecode.py:436)
- `_set_bcd(bits: list[int], offset: int, value: int, width: int) -> None` [function] (pyssp/timecode.py:456)

## Classes

### `_CoreMidiOut`

- Defined at `pyssp/timecode.py:58`

#### Public Members

- `available(self) -> bool` [method] (pyssp/timecode.py:113)
- `list_devices(self) -> List[Tuple[str, str]]` [method] (pyssp/timecode.py:154)
- `open(self, device_id) -> bool` [method] (pyssp/timecode.py:170)
- `send_short(self, status: int, data1: int = 0, data2: int = 0) -> None` [method] (pyssp/timecode.py:223)
- `send_long(self, payload: bytes) -> None` [method] (pyssp/timecode.py:226)
- `close(self) -> None` [method] (pyssp/timecode.py:229)

#### Internal Members

- `__init__(self) -> None` [constructor] (pyssp/timecode.py:59)
- `_configure_api(self) -> None` [method] (pyssp/timecode.py:76)
- `_cf_string(self, value: str) -> ctypes.c_void_p` [method] (pyssp/timecode.py:116)
- `_release(self, value: ctypes.c_void_p) -> None` [method] (pyssp/timecode.py:127)
- `_endpoint_property(self, endpoint: int, property_name: str) -> str` [method] (pyssp/timecode.py:134)
- `_send_bytes(self, payload: bytes) -> None` [method] (pyssp/timecode.py:202)

### `_MIDIIOCAPSW`

- Defined at `pyssp/timecode.py:247`
- Bases: ctypes.Structure

### `_MIDIHDR`

- Defined at `pyssp/timecode.py:261`
- Bases: ctypes.Structure

### `MidiOutput`

- Defined at `pyssp/timecode.py:275`

#### Public Members

- `available(self) -> bool` [method] (pyssp/timecode.py:305)
- `list_devices(self) -> List[Tuple[str, str]]` [method] (pyssp/timecode.py:308)
- `open(self, device_id) -> bool` [method] (pyssp/timecode.py:341)
- `send_short(self, status: int, data1: int = 0, data2: int = 0) -> None` [method] (pyssp/timecode.py:360)
- `send_long(self, payload: bytes) -> None` [method] (pyssp/timecode.py:377)
- `close(self) -> None` [method] (pyssp/timecode.py:411)

#### Internal Members

- `__init__(self) -> None` [constructor] (pyssp/timecode.py:276)

### `LtcAudioOutput`

- Defined at `pyssp/timecode.py:479`

#### Public Members

- `set_output(self, device_name: Optional[str], sample_rate: int, bit_depth: int, fps: float) -> None` [method] (pyssp/timecode.py:544)
- `update(self, current_frame: int, fps: float) -> None` [method] (pyssp/timecode.py:582)
- `request_resync(self) -> None` [method] (pyssp/timecode.py:590)
- `shutdown(self) -> None` [method] (pyssp/timecode.py:596)

#### Internal Members

- `__init__(self) -> None` [constructor] (pyssp/timecode.py:480)
- `_dtype_and_amplitude(bit_depth: int) -> tuple[str, int]` [staticmethod] (pyssp/timecode.py:502)
- `_apply_timing_locked(self) -> None` [method] (pyssp/timecode.py:509)
- `_close_stream_locked(self) -> None` [method] (pyssp/timecode.py:515)
- `_open_stream_locked(self) -> None` [method] (pyssp/timecode.py:528)
- `_audio_callback(self, outdata, frames, _time_info, _status) -> None` [method] (pyssp/timecode.py:601)

### `MtcMidiOutput`

- Defined at `pyssp/timecode.py:634`

#### Public Members

- `set_device(self, device_id: str) -> None` [method] (pyssp/timecode.py:661)
- `shutdown(self) -> None` [method] (pyssp/timecode.py:698)
- `request_resync(self) -> None` [method] (pyssp/timecode.py:711)
- `update(self, current_frame: int, source_fps: float, mtc_fps: float) -> None` [method] (pyssp/timecode.py:793)

#### Internal Members

- `__init__(self, idle_behavior_provider: Optional[Callable[[], str]] = None) -> None` [constructor] (pyssp/timecode.py:635)
- `_coerce_mtc_speed_fps(configured_fps: float) -> float` [staticmethod] (pyssp/timecode.py:722)
- `_nominal_mtc_fps(mtc_speed_fps: float) -> int` [staticmethod] (pyssp/timecode.py:728)
- `_rate_code(fps: int, speed_fps: float) -> int` [staticmethod] (pyssp/timecode.py:736)
- `_quarter_frame_data(frame_number: int, fps: int, speed_fps: float, qf_type: int) -> int` [staticmethod] (pyssp/timecode.py:748)
- `_send_full_frame(self, frame_number: int, fps: int, speed_fps: float, now: float) -> None` [method] (pyssp/timecode.py:776)
- `_run(self) -> None` [method] (pyssp/timecode.py:801)
