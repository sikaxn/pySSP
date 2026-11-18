"""Route editor preview preloads to the process that owns the preview player."""

from __future__ import annotations

from pyssp.audio_engine import is_audio_preloaded, request_audio_preload


class PreviewPreload:
    def __init__(self, audio_service) -> None:
        self._process_service = (
            audio_service if callable(getattr(audio_service, "is_audio_preloaded", None)) else None
        )

    def request(self, path: str) -> None:
        if self._process_service is not None:
            self._process_service.post_runtime("preload", {
                "paths": [path], "prioritize": True, "force": True,
            })
        else:
            request_audio_preload([path], prioritize=True, force=True)

    def is_ready(self, path: str) -> bool:
        if self._process_service is not None:
            return self._process_service.is_audio_preloaded(path)
        return is_audio_preloaded(path)
