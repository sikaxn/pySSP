from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable, Optional

from pyssp import ffmpeg_support
from pyssp.engine.types import FFmpegDecodeRequest, MediaProbeResult


class FFmpegEngineServices:
    """Expose FFmpeg probe/decode-support helpers as a runtime-owned subsystem."""

    def __init__(
        self,
        *,
        executor: Optional[ThreadPoolExecutor] = None,
        executor_factory: Optional[Callable[[], ThreadPoolExecutor]] = None,
    ) -> None:
        self._owns_executor = executor is None
        self._executor = executor or (
            executor_factory() if executor_factory is not None else ThreadPoolExecutor(max_workers=2, thread_name_prefix="pyssp-engine-ffmpeg")
        )

    def shutdown(self) -> None:
        if self._owns_executor:
            try:
                self._executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass

    def available(self) -> bool:
        return bool(ffmpeg_support.ffmpeg_available())

    def ffmpeg_executable(self) -> str:
        return str(ffmpeg_support.get_ffmpeg_executable() or "")

    def ffprobe_executable(self) -> str:
        return str(ffmpeg_support.get_ffprobe_executable() or "")

    def source(self) -> str:
        return str(ffmpeg_support.ffmpeg_source() or "none")

    def version_text(self) -> str:
        return str(ffmpeg_support.ffmpeg_version_text() or "")

    def supported_audio_extensions(self) -> list[str]:
        return list(ffmpeg_support.ffmpeg_supported_audio_extensions())

    def supported_video_extensions(self) -> list[str]:
        return list(ffmpeg_support.ffmpeg_supported_video_extensions())

    def supported_media_extensions(self) -> list[str]:
        return list(ffmpeg_support.ffmpeg_supported_media_extensions())

    def probe_duration_ms(self, path: str) -> int:
        return max(0, int(ffmpeg_support.probe_media_duration_ms(path)))

    def has_audio_stream(self, path: str) -> Optional[bool]:
        return ffmpeg_support.media_has_audio_stream(path)

    def has_video_stream(self, path: str) -> Optional[bool]:
        return ffmpeg_support.media_has_video_stream(path)

    def probe_media_info(self, path: str) -> MediaProbeResult:
        info = ffmpeg_support.probe_media_info(path)
        return MediaProbeResult(
            source_path=str(path or ""),
            duration_ms=max(0, int(getattr(info, "duration_ms", 0) or 0)),
            has_audio=bool(getattr(info, "has_audio", False)),
            has_video=bool(getattr(info, "has_video", False)),
            width=max(0, int(getattr(info, "width", 0) or 0)),
            height=max(0, int(getattr(info, "height", 0) or 0)),
            fps=max(0.0, float(getattr(info, "fps", 0.0) or 0.0)),
            rotation_deg=max(0, int(getattr(info, "rotation_deg", 0) or 0)),
        )

    def decode_request(self, request: FFmpegDecodeRequest) -> FFmpegDecodeRequest:
        return FFmpegDecodeRequest(
            path=str(request.path or ""),
            kind=str(request.kind or "audio"),
            position_ms=max(0, int(request.position_ms)),
            frame_count=max(0, int(request.frame_count)),
            sample_rate=max(1, int(request.sample_rate)),
            channels=max(1, int(request.channels)),
            width=max(0, int(request.width)),
            height=max(0, int(request.height)),
        )

    def request_media_probe(self, path: str) -> Future:
        return self._executor.submit(self.probe_media_info, path)

    def request_probe_duration_ms(self, path: str) -> Future:
        return self._executor.submit(self.probe_duration_ms, path)

    def request_stream_presence(self, path: str) -> Future:
        return self._executor.submit(
            lambda: {
                "has_audio": self.has_audio_stream(path),
                "has_video": self.has_video_stream(path),
            }
        )
