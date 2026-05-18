# `pyssp/ffmpeg_support.py`

- Source: `pyssp/ffmpeg_support.py`
- Module path: `pyssp.ffmpeg_support`
- API entries: `23`

## Module Docstring

No module docstring.

## Constants

### Public

- `FFMPEG_AUDIO_EXTENSIONS` [constant] (pyssp/ffmpeg_support.py:36)
  Detail: Value: ['.aac', '.ac3', '.aiff', '.alac', '.amr', '.ape', '.flac', '.m4a', '.mka', '...
- `FFMPEG_VIDEO_EXTENSIONS` [constant] (pyssp/ffmpeg_support.py:60)
  Detail: Value: ['.asf', '.avi', '.flv', '.m2ts', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '....

## Functions

### Public

- `ffmpeg_source() -> str` [function] (pyssp/ffmpeg_support.py:164)
- `get_ffmpeg_executable() -> str` [function] (pyssp/ffmpeg_support.py:170)
- `get_ffprobe_executable() -> str` [function] (pyssp/ffmpeg_support.py:218)
- `ffmpeg_available() -> bool` [function] (pyssp/ffmpeg_support.py:241)
- `ffmpeg_version_text() -> str` [function] (pyssp/ffmpeg_support.py:245)
- `ffmpeg_supported_audio_extensions() -> List[str]` [function] (pyssp/ffmpeg_support.py:269)
- `ffmpeg_supported_video_extensions() -> List[str]` [function] (pyssp/ffmpeg_support.py:275)
- `ffmpeg_supported_media_extensions() -> List[str]` [function] (pyssp/ffmpeg_support.py:281)
- `probe_media_duration_ms(file_path: str) -> int` [function] (pyssp/ffmpeg_support.py:285)
- `media_has_audio_stream(file_path: str) -> Optional[bool]` [function] (pyssp/ffmpeg_support.py:339)
- `media_has_video_stream(file_path: str) -> Optional[bool]` [function] (pyssp/ffmpeg_support.py:399)
- `probe_media_info(file_path: str) -> MediaProbeInfo` [function] (pyssp/ffmpeg_support.py:525)

### Internal

- `_subprocess_platform_kwargs() -> dict` [function] (pyssp/ffmpeg_support.py:22)
- `_normalize_rotation_degrees(value: object) -> int` [function] (pyssp/ffmpeg_support.py:92)
- `_normalize_ext(values: List[str]) -> List[str]` [function] (pyssp/ffmpeg_support.py:103)
- `_candidate_bundled_bins() -> List[str]` [function] (pyssp/ffmpeg_support.py:119)
- `_is_path_inside(path: str, root: str) -> bool` [function] (pyssp/ffmpeg_support.py:140)
- `_is_bundled_ffmpeg_path(path: str) -> bool` [function] (pyssp/ffmpeg_support.py:147)
- `_probe_media_info_with_ffmpeg(path: str) -> MediaProbeInfo` [function] (pyssp/ffmpeg_support.py:457)

## Classes

### `MediaProbeInfo`

- Defined at `pyssp/ffmpeg_support.py:82`

### `FFmpegPCMStream`

- Defined at `pyssp/ffmpeg_support.py:617`

#### Public Members

- `start(self, start_ms: int = 0) -> None` [method] (pyssp/ffmpeg_support.py:630)
- `seek(self, start_ms: int) -> None` [method] (pyssp/ffmpeg_support.py:676)
- `read_frames(self, frame_count: int) -> Tuple[np.ndarray, int, bool]` [method] (pyssp/ffmpeg_support.py:716)
- `close(self) -> None` [method] (pyssp/ffmpeg_support.py:765)

#### Internal Members

- `__init__(self, file_path: str, sample_rate: int = 44100, channels: int = 2) -> None` [constructor] (pyssp/ffmpeg_support.py:618)
- `_reader_loop(self) -> None` [method] (pyssp/ffmpeg_support.py:679)
