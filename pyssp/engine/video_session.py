from __future__ import annotations

import logging
import subprocess
import threading
import time
from typing import Callable, Optional

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QTransform

from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.engine.types import PlaybackSessionId, VideoFrameSnapshot, VideoSessionSnapshot
from pyssp.ffmpeg_support import get_ffmpeg_executable, probe_media_info

try:
    import av as _pyav  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - exercised via optional dependency paths
    _pyav = None

_LOG = logging.getLogger("pyssp.video.session")
_SESSION_IDLE_WAIT_SEC = 0.05
_SESSION_PLAYING_WAIT_SEC = 0.01
_SESSION_SEEK_BACKOFF_MS = 250
_SESSION_MAX_FORWARD_DRIFT_MS = 750
_SESSION_MAX_DECODE_FRAMES = 180
_SESSION_FFMPEG_FRAME_TIMEOUT_SEC = 8.0


class _PyAVFrameSource:
    def __init__(self, path: str, width: int, height: int) -> None:
        self._path = str(path or "").strip()
        self._width = max(2, int(width))
        self._height = max(2, int(height))
        self._container = None
        self._stream = None
        self._decoder = None
        self._eof = False
        self._rotation_deg = 0
        self._last_selected_image = QImage()
        self._last_selected_pts_ms = 0
        self._pending_image = QImage()
        self._pending_pts_ms = -1
        self._last_decoded_pts_ms = -1
        self._last_seek_target_ms = -1

    @property
    def backend_name(self) -> str:
        return "pyav"

    @property
    def path(self) -> str:
        return self._path

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def close(self) -> None:
        container = self._container
        self._container = None
        self._stream = None
        self._decoder = None
        self._eof = False
        self._last_selected_image = QImage()
        self._last_selected_pts_ms = 0
        self._pending_image = QImage()
        self._pending_pts_ms = -1
        self._last_decoded_pts_ms = -1
        self._last_seek_target_ms = -1
        if container is not None:
            try:
                container.close()
            except Exception:
                pass

    def frame_at(self, target_ms: int) -> tuple[QImage, int]:
        self._ensure_open()
        target_ms = max(0, int(target_ms))
        if self._should_seek(target_ms):
            self._seek_to(max(0, target_ms - _SESSION_SEEK_BACKOFF_MS))
        candidate_image = QImage(self._last_selected_image)
        candidate_pts_ms = max(0, int(self._last_selected_pts_ms))
        pending_image = QImage(self._pending_image)
        pending_pts_ms = int(self._pending_pts_ms)
        if not pending_image.isNull():
            if pending_pts_ms <= target_ms or candidate_image.isNull():
                candidate_image = pending_image
                candidate_pts_ms = max(0, pending_pts_ms)
                self._pending_image = QImage()
                self._pending_pts_ms = -1
                if pending_pts_ms >= target_ms:
                    self._last_selected_image = QImage(candidate_image)
                    self._last_selected_pts_ms = max(0, int(candidate_pts_ms))
                    return QImage(candidate_image), max(0, int(candidate_pts_ms))
            else:
                self._last_selected_image = QImage(candidate_image)
                self._last_selected_pts_ms = max(0, int(candidate_pts_ms))
                return QImage(candidate_image), max(0, int(candidate_pts_ms))
        decoded = 0
        while decoded < _SESSION_MAX_DECODE_FRAMES:
            frame = self._next_frame()
            if frame is None:
                break
            decoded += 1
            pts_ms = self._frame_pts_ms(frame)
            image = self._frame_to_image(frame)
            if image.isNull():
                continue
            self._last_decoded_pts_ms = pts_ms
            if pts_ms <= target_ms:
                candidate_image = image
                candidate_pts_ms = pts_ms
                continue
            if candidate_image.isNull():
                candidate_image = image
                candidate_pts_ms = pts_ms
                break
            self._pending_image = QImage(image)
            self._pending_pts_ms = max(0, int(pts_ms))
            break
        if candidate_image.isNull():
            return QImage(), 0
        self._last_selected_image = QImage(candidate_image)
        self._last_selected_pts_ms = max(0, int(candidate_pts_ms))
        return QImage(candidate_image), max(0, int(candidate_pts_ms))

    def _ensure_open(self) -> None:
        if _pyav is None:
            raise RuntimeError("PyAV is not installed")
        if self._container is not None and self._stream is not None and self._decoder is not None:
            return
        container = _pyav.open(self._path, mode="r")
        stream = next(iter(container.streams.video), None)
        if stream is None:
            container.close()
            raise RuntimeError("No video stream found")
        try:
            stream.thread_type = "AUTO"
        except Exception:
            pass
        self._container = container
        self._stream = stream
        self._decoder = iter(container.decode(video=stream.index))
        self._eof = False
        self._rotation_deg = self._stream_rotation_deg(stream)

    def _should_seek(self, target_ms: int) -> bool:
        if self._container is None or self._stream is None or self._decoder is None:
            return True
        if self._eof and target_ms < self._last_selected_pts_ms:
            return True
        if self._last_selected_image.isNull():
            return True
        if target_ms + 40 < self._last_selected_pts_ms:
            return True
        return target_ms > (self._last_selected_pts_ms + _SESSION_MAX_FORWARD_DRIFT_MS)

    def _seek_to(self, target_ms: int) -> None:
        self._ensure_open()
        if self._container is None or self._stream is None:
            return
        seconds = max(0.0, float(target_ms) / 1000.0)
        time_base = float(self._stream.time_base) if self._stream.time_base else 0.0
        offset = 0
        if time_base > 0.0:
            offset = max(0, int(seconds / time_base))
        try:
            self._container.seek(offset, stream=self._stream, backward=True, any_frame=False)
        except Exception:
            try:
                self.close()
                self._ensure_open()
            except Exception:
                raise
        if self._container is None or self._stream is None:
            return
        self._decoder = iter(self._container.decode(video=self._stream.index))
        self._eof = False
        self._last_seek_target_ms = max(0, int(target_ms))
        self._last_selected_image = QImage()
        self._last_selected_pts_ms = max(0, int(target_ms))
        self._pending_image = QImage()
        self._pending_pts_ms = -1
        self._last_decoded_pts_ms = -1

    def _next_frame(self):
        if self._decoder is None:
            return None
        try:
            return next(self._decoder)
        except StopIteration:
            self._eof = True
            return None

    def _frame_pts_ms(self, frame) -> int:
        seconds = None
        try:
            seconds = frame.time
        except Exception:
            seconds = None
        if seconds is None:
            try:
                if frame.pts is not None and self._stream is not None and self._stream.time_base is not None:
                    seconds = float(frame.pts * self._stream.time_base)
            except Exception:
                seconds = None
        if seconds is None:
            return max(0, int(self._last_selected_pts_ms))
        return max(0, int(round(float(seconds) * 1000.0)))

    def _frame_to_image(self, frame) -> QImage:
        rgb = frame.reformat(width=self._width, height=self._height, format="rgb24")
        array = rgb.to_ndarray()
        image = QImage(
            array.data,
            max(1, int(rgb.width)),
            max(1, int(rgb.height)),
            max(1, int(rgb.width)) * 3,
            QImage.Format_RGB888,
        ).copy()
        if self._rotation_deg in {90, 180, 270}:
            transform = QTransform()
            transform.rotate(self._rotation_deg)
            image = image.transformed(transform, Qt.SmoothTransformation)
        return image

    @staticmethod
    def _stream_rotation_deg(stream) -> int:
        try:
            value = int(float(stream.metadata.get("rotate", 0) or 0))
        except Exception:
            value = 0
        if value not in {90, 180, 270}:
            return 0
        return value


class _FFmpegFrameSource:
    def __init__(self, path: str, width: int, height: int) -> None:
        self._path = str(path or "").strip()
        self._width = max(2, int(width))
        self._height = max(2, int(height))
        info = probe_media_info(self._path)
        self._rotation_deg = int(getattr(info, "rotation_deg", 0) or 0)
        fps = 0.0
        try:
            fps = float(getattr(info, "fps", 0.0) or 0.0)
        except Exception:
            fps = 0.0
        if fps <= 0.0:
            self._frame_interval_ms = 33
        else:
            fps = max(15.0, min(60.0, fps))
            self._frame_interval_ms = max(16, int(round(1000.0 / fps)))
        self._last_image = QImage()
        self._last_bucket_ms = -1

    @property
    def backend_name(self) -> str:
        return "ffmpeg"

    @property
    def path(self) -> str:
        return self._path

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def close(self) -> None:
        self._last_image = QImage()
        self._last_bucket_ms = -1

    def frame_at(self, target_ms: int) -> tuple[QImage, int]:
        bucket_ms = self._bucket_ms(target_ms)
        if bucket_ms == self._last_bucket_ms and not self._last_image.isNull():
            return QImage(self._last_image), max(0, int(bucket_ms))
        ffmpeg = str(get_ffmpeg_executable() or "").strip()
        if not ffmpeg:
            raise RuntimeError("FFmpeg executable is not available")
        seconds = max(0.0, float(bucket_ms) / 1000.0)
        try:
            proc = subprocess.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-hwaccel",
                    "auto",
                    "-noautorotate",
                    "-ss",
                    f"{seconds:.3f}",
                    "-i",
                    self._path,
                    "-an",
                    "-sn",
                    "-dn",
                    "-vf",
                    f"scale={int(self._width)}:{int(self._height)}:flags=bilinear",
                    "-frames:v",
                    "1",
                    "-pix_fmt",
                    "rgb24",
                    "-f",
                    "rawvideo",
                    "-",
                ],
                capture_output=True,
                timeout=_SESSION_FFMPEG_FRAME_TIMEOUT_SEC,
                check=False,
                **_video_subprocess_platform_kwargs(),
            )
        except Exception as exc:
            raise RuntimeError(f"FFmpeg frame decode failed: {exc}") from exc
        payload = bytes(proc.stdout or b"")
        expected = max(1, int(self._width) * int(self._height) * 3)
        if proc.returncode != 0 or len(payload) < expected:
            raise RuntimeError("FFmpeg returned no video frame")
        image = QImage(
            payload,
            max(1, int(self._width)),
            max(1, int(self._height)),
            max(1, int(self._width)) * 3,
            QImage.Format_RGB888,
        ).copy()
        if self._rotation_deg in {90, 180, 270}:
            transform = QTransform()
            transform.rotate(self._rotation_deg)
            image = image.transformed(transform, Qt.SmoothTransformation)
        self._last_image = QImage(image)
        self._last_bucket_ms = bucket_ms
        return QImage(image), max(0, int(bucket_ms))

    def _bucket_ms(self, target_ms: int) -> int:
        target_ms = max(0, int(target_ms))
        interval = max(16, int(self._frame_interval_ms))
        return max(0, int(round(target_ms / float(interval)) * interval))


def _video_subprocess_platform_kwargs() -> dict:
    if __import__("os").name != "nt":
        return {}
    kwargs: dict = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    try:
        startup = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        startup.wShowWindow = 0
        kwargs["startupinfo"] = startup
    except Exception:
        pass
    return kwargs


def _create_frame_source(path: str, width: int, height: int):
    if _pyav is not None:
        return _PyAVFrameSource(path, width, height)
    return _FFmpegFrameSource(path, width, height)


class UnifiedVideoSession:
    def __init__(
        self,
        session_id: PlaybackSessionId,
        *,
        state_getter: Callable[[], int],
        position_getter: Callable[[], int],
        duration_getter: Callable[[], int],
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._session_id = str(session_id)
        self._state_getter = state_getter
        self._position_getter = position_getter
        self._duration_getter = duration_getter
        self._clock = clock or time.perf_counter
        self._condition = threading.Condition()
        self._shutdown = False
        self._configured_path = ""
        self._configured_width = 0
        self._configured_height = 0
        self._configured_position_ms = 0
        self._force_refresh = False
        self._prime_requested = False
        self._current_frame = QImage()
        self._current_frame_pts_ms = 0
        self._current_state = ExternalMediaPlayer.StoppedState
        self._current_position_ms = 0
        self._current_duration_ms = 0
        self._primed = False
        self._error = ""
        self._backend_name = "pyav" if _pyav is not None else "ffmpeg"
        self._worker = threading.Thread(
            target=self._run,
            name=f"pyssp-video-session-{self._session_id}",
            daemon=True,
        )
        self._worker.start()

    def configure(
        self,
        source_path: str,
        *,
        position_ms: int = 0,
        width: int = 0,
        height: int = 0,
        force: bool = False,
    ) -> bool:
        candidate = str(source_path or "").strip()
        if not candidate:
            self.clear()
            return False
        with self._condition:
            self._configured_path = candidate
            self._configured_width = max(2, int(width) or 640)
            self._configured_height = max(2, int(height) or 360)
            self._configured_position_ms = max(0, int(position_ms))
            self._force_refresh = self._force_refresh or bool(force)
            self._prime_requested = True
            self._error = ""
            self._condition.notify_all()
        return True

    def prime(self, position_ms: Optional[int] = None) -> bool:
        with self._condition:
            if not self._configured_path:
                return False
            if position_ms is not None:
                self._configured_position_ms = max(0, int(position_ms))
            self._prime_requested = True
            self._condition.notify_all()
        return True

    def clear(self) -> bool:
        with self._condition:
            self._configured_path = ""
            self._configured_width = 0
            self._configured_height = 0
            self._configured_position_ms = 0
            self._force_refresh = False
            self._prime_requested = False
            self._current_frame = QImage()
            self._current_frame_pts_ms = 0
            self._primed = False
            self._error = ""
            self._condition.notify_all()
        return True

    def snapshot(self) -> VideoSessionSnapshot:
        with self._condition:
            return VideoSessionSnapshot(
                session_id=self._session_id,
                source_path=str(self._configured_path or ""),
                configured=bool(self._configured_path),
                primed=bool(self._primed and not self._current_frame.isNull()),
                state=int(self._current_state),
                position_ms=max(0, int(self._current_position_ms)),
                duration_ms=max(0, int(self._current_duration_ms)),
                frame_pts_ms=max(0, int(self._current_frame_pts_ms)),
                frame_width=max(0, int(self._current_frame.width())),
                frame_height=max(0, int(self._current_frame.height())),
                backend_name=str(self._backend_name or ""),
                error=str(self._error or ""),
            )

    def current_frame(self) -> VideoFrameSnapshot:
        with self._condition:
            image = QImage(self._current_frame)
            return VideoFrameSnapshot(
                session_id=self._session_id,
                source_path=str(self._configured_path or ""),
                pts_ms=max(0, int(self._current_frame_pts_ms)),
                ready=not image.isNull(),
                image=image,
            )

    def shutdown(self) -> None:
        with self._condition:
            self._shutdown = True
            self._condition.notify_all()
        try:
            self._worker.join(timeout=1.5)
        except Exception:
            pass

    def _run(self) -> None:
        frame_source = None
        last_target_key: tuple[str, int, int, int, int, bool] | None = None
        while True:
            with self._condition:
                while not self._shutdown and not self._configured_path:
                    self._condition.wait(timeout=_SESSION_IDLE_WAIT_SEC)
                if self._shutdown:
                    break
                path = str(self._configured_path or "")
                width = max(2, int(self._configured_width or 640))
                height = max(2, int(self._configured_height or 360))
                requested_position_ms = max(0, int(self._configured_position_ms))
                force_refresh = bool(self._force_refresh)
                prime_requested = bool(self._prime_requested)
            try:
                state = int(self._state_getter())
            except Exception:
                state = ExternalMediaPlayer.StoppedState
            try:
                duration_ms = max(0, int(self._duration_getter()))
            except Exception:
                duration_ms = 0
            try:
                transport_position_ms = max(0, int(self._position_getter()))
            except Exception:
                transport_position_ms = requested_position_ms
            target_ms = transport_position_ms
            if state != ExternalMediaPlayer.PlayingState:
                target_ms = requested_position_ms if prime_requested or transport_position_ms <= 0 else transport_position_ms
            target_key = (path, width, height, state, target_ms, prime_requested)
            if (
                not force_refresh
                and last_target_key == target_key
                and state != ExternalMediaPlayer.PlayingState
                and prime_requested is False
            ):
                with self._condition:
                    self._current_state = state
                    self._current_position_ms = transport_position_ms
                    self._current_duration_ms = duration_ms
                    self._condition.wait(timeout=_SESSION_IDLE_WAIT_SEC)
                continue
            try:
                if frame_source is None or frame_source.path != path or frame_source.width != width or frame_source.height != height:
                    if frame_source is not None:
                        frame_source.close()
                    frame_source = _create_frame_source(path, width, height)
                    self._backend_name = frame_source.backend_name
                image, pts_ms = frame_source.frame_at(target_ms)
                error = ""
            except Exception as exc:
                image = QImage()
                pts_ms = 0
                error = str(exc)
                if frame_source is not None:
                    try:
                        frame_source.close()
                    except Exception:
                        pass
                    frame_source = None
                _LOG.debug("Video session %s frame decode failed: %s", self._session_id, exc, exc_info=True)
            with self._condition:
                self._current_state = state
                self._current_position_ms = transport_position_ms
                self._current_duration_ms = duration_ms
                self._current_frame = QImage(image)
                self._current_frame_pts_ms = max(0, int(pts_ms))
                self._primed = not image.isNull()
                self._error = error
                self._force_refresh = False
                if self._primed:
                    self._prime_requested = False
            last_target_key = target_key
            with self._condition:
                if self._shutdown:
                    break
                wait_sec = _SESSION_PLAYING_WAIT_SEC if state == ExternalMediaPlayer.PlayingState else _SESSION_IDLE_WAIT_SEC
                self._condition.wait(timeout=wait_sec)
        if frame_source is not None:
            frame_source.close()
