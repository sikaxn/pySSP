from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
import glob
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

_FFMPEG_PATH_CACHE: Optional[str] = None
_FFPROBE_PATH_CACHE: Optional[str] = None
_PATH_LOCK = threading.RLock()
_FFMPEG_SOURCE_CACHE = "none"


def _subprocess_platform_kwargs() -> dict:
    if os.name != "nt":
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

# Conservative list of container extensions typically decodable by ffmpeg.
FFMPEG_AUDIO_EXTENSIONS: List[str] = [
    ".aac",
    ".ac3",
    ".aiff",
    ".alac",
    ".amr",
    ".ape",
    ".flac",
    ".m4a",
    ".mka",
    ".mp2",
    ".mp3",
    ".mp4",
    ".mpc",
    ".ogg",
    ".oga",
    ".opus",
    ".ra",
    ".tta",
    ".wav",
    ".wma",
    ".wv",
]

FFMPEG_VIDEO_EXTENSIONS: List[str] = [
    ".asf",
    ".avi",
    ".flv",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".mxf",
    ".ogv",
    ".ts",
    ".vob",
    ".webm",
    ".wmv",
]


@dataclass(frozen=True)
class MediaProbeInfo:
    duration_ms: int = 0
    has_audio: bool = False
    has_video: bool = False
    width: int = 0
    height: int = 0
    fps: float = 0.0
    rotation_deg: int = 0


def _normalize_rotation_degrees(value: object) -> int:
    try:
        angle = int(round(float(value or 0.0)))
    except Exception:
        return 0
    normalized = angle % 360
    if normalized in {0, 90, 180, 270}:
        return normalized
    return 0


def _normalize_ext(values: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in list(values or []):
        token = str(raw or "").strip().lower()
        if not token:
            continue
        if not token.startswith("."):
            token = f".{token.lstrip('.')}"
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _candidate_bundled_bins() -> List[str]:
    candidates: List[str] = []
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    sys_mod = __import__("sys")
    meipass = str(getattr(sys_mod, "_MEIPASS", "") or "").strip()
    if meipass:
        candidates.append(os.path.join(meipass, "imageio_ffmpeg", "binaries", exe_name))
        candidates.append(os.path.join(meipass, exe_name))
        candidates.extend(glob.glob(os.path.join(meipass, "**", exe_name), recursive=True))
    if getattr(sys_mod, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys_mod.executable))
        candidates.append(os.path.join(exe_dir, "imageio_ffmpeg", "binaries", exe_name))
        candidates.append(os.path.join(exe_dir, "_internal", "imageio_ffmpeg", "binaries", exe_name))
        candidates.append(os.path.join(exe_dir, exe_name))
        candidates.extend(glob.glob(os.path.join(exe_dir, "**", exe_name), recursive=True))
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(base_dir, "bin", exe_name))
    candidates.append(os.path.join(base_dir, "..", "bin", exe_name))
    return [os.path.abspath(p) for p in candidates if str(p or "").strip()]


def _is_path_inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root)
    except Exception:
        return False


def _is_bundled_ffmpeg_path(path: str) -> bool:
    token = os.path.abspath(str(path or ""))
    if not token or (not os.path.exists(token)):
        return False
    sys_mod = __import__("sys")
    meipass = str(getattr(sys_mod, "_MEIPASS", "") or "").strip()
    if meipass and _is_path_inside(token, meipass):
        return True
    if getattr(sys_mod, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys_mod.executable))
        if _is_path_inside(token, exe_dir):
            return True
    if "imageio_ffmpeg" in token.replace("\\", "/").lower():
        return True
    return False


def ffmpeg_source() -> str:
    # One of: bundled, external, none
    _ = get_ffmpeg_executable()
    return str(_FFMPEG_SOURCE_CACHE or "none")


def get_ffmpeg_executable() -> str:
    global _FFMPEG_PATH_CACHE, _FFMPEG_SOURCE_CACHE
    with _PATH_LOCK:
        if _FFMPEG_PATH_CACHE and os.path.exists(_FFMPEG_PATH_CACHE):
            return _FFMPEG_PATH_CACHE

        sys_mod = __import__("sys")
        frozen = bool(getattr(sys_mod, "frozen", False))

        env_path = str(os.environ.get("PYSSP_FFMPEG_PATH", "")).strip()
        if env_path and os.path.exists(env_path):
            # In frozen builds, only accept env override when it still points to bundled app files.
            if (not frozen) or _is_bundled_ffmpeg_path(env_path):
                _FFMPEG_PATH_CACHE = env_path
                _FFMPEG_SOURCE_CACHE = "bundled" if _is_bundled_ffmpeg_path(env_path) else "external"
                return _FFMPEG_PATH_CACHE

        for candidate in _candidate_bundled_bins():
            if os.path.exists(candidate):
                _FFMPEG_PATH_CACHE = os.path.abspath(candidate)
                _FFMPEG_SOURCE_CACHE = "bundled"
                return _FFMPEG_PATH_CACHE

        try:
            import imageio_ffmpeg  # type: ignore

            path = str(imageio_ffmpeg.get_ffmpeg_exe() or "").strip()
            if path and os.path.exists(path):
                _FFMPEG_PATH_CACHE = path
                _FFMPEG_SOURCE_CACHE = "bundled" if _is_bundled_ffmpeg_path(path) else "external"
                return _FFMPEG_PATH_CACHE
        except Exception:
            pass

        if frozen:
            _FFMPEG_SOURCE_CACHE = "none"
            return ""

        system_ffmpeg = shutil.which("ffmpeg") or ""
        if system_ffmpeg:
            _FFMPEG_PATH_CACHE = os.path.abspath(system_ffmpeg)
            _FFMPEG_SOURCE_CACHE = "external"
            return _FFMPEG_PATH_CACHE

        _FFMPEG_SOURCE_CACHE = "none"
        return ""


def get_ffprobe_executable() -> str:
    global _FFPROBE_PATH_CACHE
    with _PATH_LOCK:
        if _FFPROBE_PATH_CACHE and os.path.exists(_FFPROBE_PATH_CACHE):
            return _FFPROBE_PATH_CACHE

        ffmpeg_path = get_ffmpeg_executable()
        if ffmpeg_path:
            base_dir = os.path.dirname(ffmpeg_path)
            probe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
            probe_path = os.path.join(base_dir, probe_name)
            if os.path.exists(probe_path):
                _FFPROBE_PATH_CACHE = probe_path
                return _FFPROBE_PATH_CACHE

        system_ffprobe = shutil.which("ffprobe") or ""
        if system_ffprobe:
            _FFPROBE_PATH_CACHE = os.path.abspath(system_ffprobe)
            return _FFPROBE_PATH_CACHE

        return ""


def ffmpeg_available() -> bool:
    return bool(get_ffmpeg_executable())


def ffmpeg_version_text() -> str:
    ffmpeg = get_ffmpeg_executable()
    if not ffmpeg:
        return ""
    try:
        proc = subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True,
            timeout=4,
            check=False,
            **_subprocess_platform_kwargs(),
        )
    except Exception:
        return ""
    line = ""
    stdout_text = (proc.stdout or b"").decode("utf-8", errors="replace")
    for raw in stdout_text.splitlines():
        token = str(raw or "").strip()
        if token:
            line = token
            break
    return line


def ffmpeg_supported_audio_extensions() -> List[str]:
    if not ffmpeg_available():
        return []
    return _normalize_ext(FFMPEG_AUDIO_EXTENSIONS)


def ffmpeg_supported_video_extensions() -> List[str]:
    if not ffmpeg_available():
        return []
    return _normalize_ext(FFMPEG_VIDEO_EXTENSIONS)


def ffmpeg_supported_media_extensions() -> List[str]:
    return _normalize_ext([*ffmpeg_supported_audio_extensions(), *ffmpeg_supported_video_extensions()])


def probe_media_duration_ms(file_path: str) -> int:
    path = str(file_path or "").strip()
    if not path or (not os.path.exists(path)):
        return 0
    ffprobe = get_ffprobe_executable()
    if ffprobe:
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                capture_output=True,
                timeout=6,
                check=False,
                **_subprocess_platform_kwargs(),
            )
            value = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
            if value:
                seconds = max(0.0, float(value))
                return int(round(seconds * 1000.0))
        except Exception:
            pass
    ffmpeg = get_ffmpeg_executable()
    if ffmpeg:
        try:
            proc = subprocess.run(
                [ffmpeg, "-hide_banner", "-i", path],
                capture_output=True,
                timeout=6,
                check=False,
                **_subprocess_platform_kwargs(),
            )
            stdout_text = (proc.stdout or b"").decode("utf-8", errors="replace")
            stderr_text = (proc.stderr or b"").decode("utf-8", errors="replace")
            blob = "\n".join([stdout_text, stderr_text])
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", blob)
            if m:
                h = int(m.group(1))
                mnt = int(m.group(2))
                sec = float(m.group(3))
                total = (h * 3600.0) + (mnt * 60.0) + sec
                return int(round(max(0.0, total) * 1000.0))
        except Exception:
            pass
    return 0


def media_has_audio_stream(file_path: str) -> Optional[bool]:
    path = str(file_path or "").strip()
    if not path or (not os.path.exists(path)):
        return None
    ffprobe = get_ffprobe_executable()
    if ffprobe:
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "a",
                    "-show_entries",
                    "stream=codec_type",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                capture_output=True,
                timeout=6,
                check=False,
                **_subprocess_platform_kwargs(),
            )
            values = [
                str(token or "").strip().lower()
                for token in (proc.stdout or b"").decode("utf-8", errors="replace").strip().splitlines()
                if str(token or "").strip()
            ]
            if "audio" in values:
                return True
            # Only conclude "no audio" on a successful ffprobe query.
            # If ffprobe produced empty/failed output, fall back to ffmpeg parsing.
            if proc.returncode == 0 and values:
                return False
        except Exception:
            pass
    ffmpeg = get_ffmpeg_executable()
    if ffmpeg:
        try:
            proc = subprocess.run(
                [ffmpeg, "-hide_banner", "-i", path],
                capture_output=True,
                timeout=6,
                check=False,
                **_subprocess_platform_kwargs(),
            )
            blob = "\n".join(
                [
                    (proc.stdout or b"").decode("utf-8", errors="replace"),
                    (proc.stderr or b"").decode("utf-8", errors="replace"),
                ]
            )
            return bool(re.search(r"Stream #\d+:\d+.*Audio:", blob, flags=re.IGNORECASE))
        except Exception:
            pass
    return None


def media_has_video_stream(file_path: str) -> Optional[bool]:
    path = str(file_path or "").strip()
    if not path or (not os.path.exists(path)):
        return None
    ffprobe = get_ffprobe_executable()
    if ffprobe:
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v",
                    "-show_entries",
                    "stream=codec_type",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                capture_output=True,
                timeout=6,
                check=False,
                **_subprocess_platform_kwargs(),
            )
            values = [
                str(token or "").strip().lower()
                for token in (proc.stdout or b"").decode("utf-8", errors="replace").strip().splitlines()
                if str(token or "").strip()
            ]
            if "video" in values:
                return True
            if proc.returncode == 0 and values:
                return False
        except Exception:
            pass
    ffmpeg = get_ffmpeg_executable()
    if ffmpeg:
        try:
            proc = subprocess.run(
                [ffmpeg, "-hide_banner", "-i", path],
                capture_output=True,
                timeout=6,
                check=False,
                **_subprocess_platform_kwargs(),
            )
            blob = "\n".join(
                [
                    (proc.stdout or b"").decode("utf-8", errors="replace"),
                    (proc.stderr or b"").decode("utf-8", errors="replace"),
                ]
            )
            return bool(re.search(r"Stream #\d+:\d+.*Video:", blob, flags=re.IGNORECASE))
        except Exception:
            pass
    return None


def _probe_media_info_with_ffmpeg(path: str) -> MediaProbeInfo:
    ffmpeg = get_ffmpeg_executable()
    if not ffmpeg:
        return MediaProbeInfo()
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", path],
            capture_output=True,
            timeout=8,
            check=False,
            **_subprocess_platform_kwargs(),
        )
    except Exception:
        return MediaProbeInfo()
    blob = "\n".join(
        [
            (proc.stdout or b"").decode("utf-8", errors="replace"),
            (proc.stderr or b"").decode("utf-8", errors="replace"),
        ]
    )
    duration_ms = 0
    has_audio = bool(re.search(r"Stream #\d+:\d+.*Audio:", blob, flags=re.IGNORECASE))
    has_video = bool(re.search(r"Stream #\d+:\d+.*Video:", blob, flags=re.IGNORECASE))
    width = 0
    height = 0
    fps = 0.0
    rotation_deg = 0
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", blob)
    if duration_match:
        try:
            hours = int(duration_match.group(1))
            minutes = int(duration_match.group(2))
            seconds = float(duration_match.group(3))
            duration_ms = int(round(max(0.0, (hours * 3600.0) + (minutes * 60.0) + seconds) * 1000.0))
        except Exception:
            duration_ms = 0
    video_match = re.search(
        r"Stream #\d+:\d+.*Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?)\s+fps",
        blob,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if video_match:
        try:
            width = max(0, int(video_match.group(1)))
            height = max(0, int(video_match.group(2)))
            fps = max(0.0, float(video_match.group(3)))
        except Exception:
            width = 0
            height = 0
            fps = 0.0
    rotation_match = re.search(r"rotation of\s*(-?\d+(?:\.\d+)?)\s*degrees", blob, flags=re.IGNORECASE)
    if rotation_match:
        rotation_deg = _normalize_rotation_degrees(rotation_match.group(1))
    if not rotation_deg:
        display_matrix_match = re.search(r"rotation[:=]\s*(-?\d+(?:\.\d+)?)", blob, flags=re.IGNORECASE)
        if display_matrix_match:
            rotation_deg = _normalize_rotation_degrees(display_matrix_match.group(1))
    return MediaProbeInfo(
        duration_ms=max(0, int(duration_ms)),
        has_audio=bool(has_audio),
        has_video=bool(has_video),
        width=max(0, int(width)),
        height=max(0, int(height)),
        fps=max(0.0, float(fps)),
        rotation_deg=rotation_deg,
    )


def probe_media_info(file_path: str) -> MediaProbeInfo:
    path = str(file_path or "").strip()
    if not path or (not os.path.exists(path)):
        return MediaProbeInfo()
    ffprobe = get_ffprobe_executable()
    if ffprobe:
        try:
            proc = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration:stream=codec_type,width,height,avg_frame_rate,r_frame_rate:stream_tags=rotate:stream_side_data=rotation",
                    "-of",
                    "json",
                    path,
                ],
                capture_output=True,
                timeout=8,
                check=False,
                **_subprocess_platform_kwargs(),
            )
            payload = json.loads((proc.stdout or b"{}").decode("utf-8", errors="replace") or "{}")
            format_info = payload.get("format", {}) if isinstance(payload, dict) else {}
            streams = payload.get("streams", []) if isinstance(payload, dict) else []
            duration_ms = 0
            try:
                duration_ms = int(round(max(0.0, float(format_info.get("duration", 0.0) or 0.0)) * 1000.0))
            except Exception:
                duration_ms = 0
            has_audio = False
            has_video = False
            width = 0
            height = 0
            fps = 0.0
            rotation_deg = 0
            for stream in list(streams or []):
                if not isinstance(stream, dict):
                    continue
                codec_type = str(stream.get("codec_type", "") or "").strip().lower()
                if codec_type == "audio":
                    has_audio = True
                elif codec_type == "video":
                    has_video = True
                    width = max(width, int(stream.get("width", 0) or 0))
                    height = max(height, int(stream.get("height", 0) or 0))
                    raw_rate = str(stream.get("avg_frame_rate", "") or stream.get("r_frame_rate", "") or "").strip()
                    if raw_rate and raw_rate != "0/0":
                        try:
                            if "/" in raw_rate:
                                num_text, den_text = raw_rate.split("/", 1)
                                den = float(den_text or 0.0)
                                if den > 0.0:
                                    fps = max(fps, float(num_text or 0.0) / den)
                            else:
                                fps = max(fps, float(raw_rate))
                        except Exception:
                            pass
                    tags = stream.get("tags", {}) if isinstance(stream.get("tags", {}), dict) else {}
                    if not rotation_deg:
                        rotation_deg = _normalize_rotation_degrees(tags.get("rotate", 0))
                    if not rotation_deg:
                        side_data_list = stream.get("side_data_list", [])
                        for side_data in list(side_data_list or []):
                            if not isinstance(side_data, dict):
                                continue
                            rotation_deg = _normalize_rotation_degrees(side_data.get("rotation", 0))
                            if rotation_deg:
                                break
            if duration_ms or has_audio or has_video:
                return MediaProbeInfo(
                    duration_ms=max(0, int(duration_ms)),
                    has_audio=bool(has_audio),
                    has_video=bool(has_video),
                    width=max(0, int(width)),
                    height=max(0, int(height)),
                    fps=max(0.0, float(fps)),
                    rotation_deg=rotation_deg,
                )
        except Exception:
            pass
    fallback = _probe_media_info_with_ffmpeg(path)
    if fallback.duration_ms or fallback.has_audio or fallback.has_video or fallback.width or fallback.height or fallback.fps:
        return fallback
    return MediaProbeInfo(
        duration_ms=probe_media_duration_ms(path),
        has_audio=bool(media_has_audio_stream(path)),
        has_video=bool(media_has_video_stream(path)),
    )


class FFmpegPCMStream:
    def __init__(self, file_path: str, sample_rate: int = 44100, channels: int = 2) -> None:
        self.file_path = str(file_path or "").strip()
        self.sample_rate = max(8000, int(sample_rate))
        self.channels = max(1, int(channels))
        self._proc: Optional[subprocess.Popen[bytes]] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=64)
        self._pending = np.zeros((0, self.channels), dtype=np.float32)
        self._lock = threading.RLock()
        self._running = False
        self._eof = False

    def start(self, start_ms: int = 0) -> None:
        self.close()
        ffmpeg = get_ffmpeg_executable()
        if not ffmpeg:
            raise RuntimeError("ffmpeg not available")
        if not self.file_path or (not os.path.exists(self.file_path)):
            raise FileNotFoundError(self.file_path or "")

        cmd: List[str] = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
        ]
        if start_ms > 0:
            cmd.extend(["-ss", f"{max(0, int(start_ms)) / 1000.0:.3f}"])
        cmd.extend(
            [
                "-i",
                self.file_path,
                "-vn",
                "-sn",
                "-dn",
                "-ac",
                str(self.channels),
                "-ar",
                str(self.sample_rate),
                "-f",
                "f32le",
                "pipe:1",
            ]
        )
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            **_subprocess_platform_kwargs(),
        )
        self._running = True
        self._eof = False
        self._pending = np.zeros((0, self.channels), dtype=np.float32)
        self._reader_thread = threading.Thread(target=self._reader_loop, name="pyssp-ffmpeg-stream", daemon=True)
        self._reader_thread.start()

    def seek(self, start_ms: int) -> None:
        self.start(start_ms=max(0, int(start_ms)))

    def _reader_loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            with self._lock:
                self._eof = True
                self._running = False
            return
        bytes_per_frame = self.channels * 4
        chunk_frames = 2048
        chunk_bytes = chunk_frames * bytes_per_frame
        try:
            while True:
                with self._lock:
                    if not self._running:
                        break
                raw = proc.stdout.read(chunk_bytes)
                if not raw:
                    break
                usable = len(raw) - (len(raw) % bytes_per_frame)
                if usable <= 0:
                    continue
                frames = np.frombuffer(raw[:usable], dtype=np.float32).reshape((-1, self.channels)).copy()
                placed = False
                while not placed:
                    with self._lock:
                        if not self._running:
                            return
                    try:
                        self._queue.put(frames, timeout=0.08)
                        placed = True
                    except queue.Full:
                        continue
        finally:
            with self._lock:
                self._eof = True
                self._running = False

    def read_frames(self, frame_count: int) -> Tuple[np.ndarray, int, bool]:
        need = max(1, int(frame_count))
        out = np.zeros((need, self.channels), dtype=np.float32)
        wrote = 0

        if len(self._pending) > 0:
            take = min(need, len(self._pending))
            out[:take, :] = self._pending[:take, :]
            wrote += take
            if take < len(self._pending):
                self._pending = self._pending[take:, :]
            else:
                self._pending = np.zeros((0, self.channels), dtype=np.float32)

        while wrote < need:
            try:
                block = self._queue.get_nowait()
            except queue.Empty:
                break
            if len(block) <= 0:
                continue
            take = min(need - wrote, len(block))
            out[wrote : wrote + take, :] = block[:take, :]
            wrote += take
            if take < len(block):
                self._pending = block[take:, :]
                break

        # Give decoder a brief chance to produce the first chunk to avoid
        # immediate-start underruns on very first callback.
        if wrote <= 0:
            with self._lock:
                should_wait = self._running and (not self._eof)
            if should_wait:
                try:
                    block = self._queue.get(timeout=0.03)
                except queue.Empty:
                    block = None
                if block is not None and len(block) > 0:
                    take = min(need, len(block))
                    out[:take, :] = block[:take, :]
                    wrote = take
                    if take < len(block):
                        self._pending = block[take:, :]

        with self._lock:
            eof = bool(self._eof) and self._queue.empty() and (len(self._pending) == 0)
        return out, wrote, eof

    def close(self) -> None:
        thread: Optional[threading.Thread] = None
        proc: Optional[subprocess.Popen[bytes]] = None
        with self._lock:
            self._running = False
            thread = self._reader_thread
            self._reader_thread = None
            proc = self._proc
            self._proc = None
            self._eof = True
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=0.4)
            except Exception:
                pass
        if thread is not None and thread.is_alive():
            try:
                thread.join(timeout=0.4)
            except Exception:
                pass
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        self._pending = np.zeros((0, self.channels), dtype=np.float32)
