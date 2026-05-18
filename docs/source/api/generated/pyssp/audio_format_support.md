# `pyssp/audio_format_support.py`

- Source: `pyssp/audio_format_support.py`
- Module path: `pyssp.audio_format_support`
- API entries: `4`

## Module Docstring

No module docstring.

## Functions

### Public

- `normalize_supported_audio_extensions(values: List[str]) -> List[str]` [function] (pyssp/audio_format_support.py:13)
- `build_audio_file_dialog_filter(supported_audio_format_extensions: List[str], allow_other_unsupported_audio_files: bool) -> str` [function] (pyssp/audio_format_support.py:29)
- `effective_audio_file_extensions(supported_audio_format_extensions: List[str], allow_other_unsupported_audio_files: bool) -> List[str]` [function] (pyssp/audio_format_support.py:47)
- `ensure_supported_audio_formats_ready(*, timeout_sec: float = 10.0, force_rescan: bool = False, set_status: Optional[Callable[[str], None]] = None, before_prompt: Optional[Callable[[], None]] = None, after_prompt: Optional[Callable[[], None]] = None) -> bool` [function] (pyssp/audio_format_support.py:59)
