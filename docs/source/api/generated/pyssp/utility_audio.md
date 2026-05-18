# `pyssp/utility_audio.py`

- Source: `pyssp/utility_audio.py`
- Module path: `pyssp.utility_audio`
- API entries: `25`

## Module Docstring

No module docstring.

## Constants

### Public

- `UTILITY_SOURCE_TYPE` [constant] (pyssp/utility_audio.py:9)
  Detail: Value: 'utility'
- `FILE_SOURCE_TYPE` [constant] (pyssp/utility_audio.py:10)
  Detail: Value: 'file'
- `UTILITY_UNSUPPORTED_MARKER_TEXT` [constant] (pyssp/utility_audio.py:11)
  Detail: Value: 'Unsupported utility sound button. A newer version of pySSP is required.'
- `UTILITY_MODE_BLANK` [constant] (pyssp/utility_audio.py:13)
  Detail: Value: 'blank'
- `UTILITY_MODE_PINK_NOISE` [constant] (pyssp/utility_audio.py:14)
  Detail: Value: 'pink_noise'
- `UTILITY_MODE_WAVEFORM` [constant] (pyssp/utility_audio.py:15)
  Detail: Value: 'waveform'
- `UTILITY_MODE_METRONOME` [constant] (pyssp/utility_audio.py:16)
  Detail: Value: 'metronome'
- `UTILITY_MODES` [constant] (pyssp/utility_audio.py:17)
  Detail: Value: {UTILITY_MODE_BLANK, UTILITY_MODE_PINK_NOISE, UTILITY_MODE_WAVEFORM, UTILITY_...
- `UTILITY_WAVEFORM_SINE` [constant] (pyssp/utility_audio.py:24)
  Detail: Value: 'sine'
- `UTILITY_WAVEFORM_SQUARE` [constant] (pyssp/utility_audio.py:25)
  Detail: Value: 'square'
- `UTILITY_WAVEFORM_TRIANGLE` [constant] (pyssp/utility_audio.py:26)
  Detail: Value: 'triangle'
- `UTILITY_WAVEFORM_SAWTOOTH` [constant] (pyssp/utility_audio.py:27)
  Detail: Value: 'sawtooth'
- `UTILITY_WAVEFORMS` [constant] (pyssp/utility_audio.py:28)
  Detail: Value: {UTILITY_WAVEFORM_SINE, UTILITY_WAVEFORM_SQUARE, UTILITY_WAVEFORM_TRIANGLE, U...

## Functions

### Public

- `clamp_utility_duration_ms(value: object) -> int` [function] (pyssp/utility_audio.py:47)
- `normalize_utility_mode(value: object) -> str` [function] (pyssp/utility_audio.py:55)
- `normalize_utility_waveform(value: object) -> str` [function] (pyssp/utility_audio.py:60)
- `normalize_time_signature(num: object, den: object) -> tuple[int, int]` [function] (pyssp/utility_audio.py:65)
- `normalize_utility_spec(raw: object) -> UtilitySoundSpec` [function] (pyssp/utility_audio.py:80)
- `utility_spec_to_dict(spec: Optional[UtilitySoundSpec]) -> dict[str, Any]` [function] (pyssp/utility_audio.py:115)
- `utility_source_payload(spec: Optional[UtilitySoundSpec]) -> dict[str, Any]` [function] (pyssp/utility_audio.py:120)
- `is_utility_source_payload(source: object) -> bool` [function] (pyssp/utility_audio.py:124)
- `utility_duration_hhmmssmmm(duration_ms: object) -> str` [function] (pyssp/utility_audio.py:130)
- `parse_utility_duration_hhmmssmmm(value: object) -> Optional[int]` [function] (pyssp/utility_audio.py:138)
- `utility_display_name(spec: Optional[UtilitySoundSpec]) -> str` [function] (pyssp/utility_audio.py:154)

## Classes

### `UtilitySoundSpec`

- Defined at `pyssp/utility_audio.py:37`
