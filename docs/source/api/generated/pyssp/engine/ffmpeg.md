# `pyssp/engine/ffmpeg.py`

- Source: `pyssp/engine/ffmpeg.py`
- Module path: `pyssp.engine.ffmpeg`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `FFmpegEngineServices`

- Defined at `pyssp/engine/ffmpeg.py:10`
- Summary: Expose FFmpeg probe/decode-support helpers as a runtime-owned subsystem.

#### Public Members

- `shutdown(self) -> None` [method] (pyssp/engine/ffmpeg.py:24)
- `available(self) -> bool` [method] (pyssp/engine/ffmpeg.py:31)
- `ffmpeg_executable(self) -> str` [method] (pyssp/engine/ffmpeg.py:34)
- `ffprobe_executable(self) -> str` [method] (pyssp/engine/ffmpeg.py:37)
- `source(self) -> str` [method] (pyssp/engine/ffmpeg.py:40)
- `version_text(self) -> str` [method] (pyssp/engine/ffmpeg.py:43)
- `supported_audio_extensions(self) -> list[str]` [method] (pyssp/engine/ffmpeg.py:46)
- `supported_video_extensions(self) -> list[str]` [method] (pyssp/engine/ffmpeg.py:49)
- `supported_media_extensions(self) -> list[str]` [method] (pyssp/engine/ffmpeg.py:52)
- `probe_duration_ms(self, path: str) -> int` [method] (pyssp/engine/ffmpeg.py:55)
- `has_audio_stream(self, path: str) -> Optional[bool]` [method] (pyssp/engine/ffmpeg.py:58)
- `has_video_stream(self, path: str) -> Optional[bool]` [method] (pyssp/engine/ffmpeg.py:61)
- `probe_media_info(self, path: str) -> MediaProbeResult` [method] (pyssp/engine/ffmpeg.py:64)
- `decode_request(self, request: FFmpegDecodeRequest) -> FFmpegDecodeRequest` [method] (pyssp/engine/ffmpeg.py:77)
- `request_media_probe(self, path: str) -> Future` [method] (pyssp/engine/ffmpeg.py:89)
- `request_probe_duration_ms(self, path: str) -> Future` [method] (pyssp/engine/ffmpeg.py:92)
- `request_stream_presence(self, path: str) -> Future` [method] (pyssp/engine/ffmpeg.py:95)

#### Internal Members

- `__init__(self, *, executor: Optional[ThreadPoolExecutor] = None, executor_factory: Optional[Callable[[], ThreadPoolExecutor]] = None) -> None` [constructor] (pyssp/engine/ffmpeg.py:13)
