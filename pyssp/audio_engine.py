from __future__ import annotations

import ctypes
import atexit
import hashlib
import io
import os
import shutil
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

import numpy as np
import pygame
import sounddevice as sd
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from pyssp.dsp import DSPConfig, RealTimeDSPProcessor, normalize_config
from pyssp.ffmpeg_support import FFmpegPCMStream, ffmpeg_available, probe_media_duration_ms

_DECODER_READY = False
_NEXT_STREAM_ID = 0
_CHANNEL_COUNT = 2
_REQUESTED_DEVICE = ""
_DECODER_LOCK = threading.RLock()
_PRELOAD_LOCK = threading.RLock()
_PRELOAD_ENABLED = False
_PRELOAD_LIMIT_BYTES = 256 * 1024 * 1024
_PRELOAD_PRESSURE_ENABLED = True
_PRELOAD_PAUSED = False
_PRELOAD_CACHE: "OrderedDict[str, Tuple[np.ndarray, int, int]]" = OrderedDict()
_FORCED_MEDIA_CACHE: "OrderedDict[str, Tuple[np.ndarray, int, int]]" = OrderedDict()
_PRELOAD_CACHE_BYTES = 0
_PRELOAD_TASKS: Dict[str, Future] = {}
_PRELOAD_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pyssp-audio-preload")
_WAVEFORM_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pyssp-waveform")
_WAVEFORM_CACHE_LOCK = threading.RLock()
_WAVEFORM_CACHE_DIR = ""
_WAVEFORM_CACHE_VERSION = "v1"
_WAVEFORM_PRELOAD_SAMPLE_COUNTS: Tuple[int, ...] = (1800, 1024)
_WAVEFORM_CACHE_LIMIT_MB_MIN = 128
_WAVEFORM_CACHE_LIMIT_MB_MAX = 16 * 1024
_WAVEFORM_CACHE_LIMIT_BYTES = 1024 * 1024 * 1024


def _shutdown_preload_executor() -> None:
    try:
        _PRELOAD_EXECUTOR.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass


def _shutdown_waveform_executor() -> None:
    try:
        _WAVEFORM_EXECUTOR.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass


atexit.register(_shutdown_preload_executor)
atexit.register(_shutdown_waveform_executor)


def shutdown_audio_preload() -> None:
    global _PRELOAD_ENABLED, _PRELOAD_CACHE_BYTES, _PRELOAD_PAUSED
    with _PRELOAD_LOCK:
        _PRELOAD_ENABLED = False
        _PRELOAD_PAUSED = False
        for future in list(_PRELOAD_TASKS.values()):
            try:
                future.cancel()
            except Exception:
                pass
        _PRELOAD_TASKS.clear()
        _PRELOAD_CACHE.clear()
        _FORCED_MEDIA_CACHE.clear()
        _PRELOAD_CACHE_BYTES = 0
    _shutdown_preload_executor()
    _shutdown_waveform_executor()


def _default_waveform_cache_dir() -> str:
    local_appdata = os.getenv("LOCALAPPDATA")
    appdata = os.getenv("APPDATA")
    if local_appdata:
        base = local_appdata
    elif appdata:
        base = appdata
    else:
        base = tempfile.gettempdir()
    return os.path.join(base, "pySSP", "temp", "waveform_cache")


def _normalize_waveform_cache_limit_mb(limit_mb: int) -> int:
    raw = int(limit_mb)
    return max(_WAVEFORM_CACHE_LIMIT_MB_MIN, min(_WAVEFORM_CACHE_LIMIT_MB_MAX, raw))


def get_waveform_cache_limit_bounds_mb() -> Tuple[int, int]:
    return _WAVEFORM_CACHE_LIMIT_MB_MIN, _WAVEFORM_CACHE_LIMIT_MB_MAX


def get_waveform_cache_limit_mb() -> int:
    with _WAVEFORM_CACHE_LOCK:
        return max(1, int(_WAVEFORM_CACHE_LIMIT_BYTES // (1024 * 1024)))


def get_waveform_cache_dir() -> str:
    with _WAVEFORM_CACHE_LOCK:
        return str(_WAVEFORM_CACHE_DIR or "")


def prepare_waveform_disk_cache(cache_dir: str = "", clear_existing: bool = False, limit_mb: Optional[int] = None) -> str:
    global _WAVEFORM_CACHE_DIR, _WAVEFORM_CACHE_LIMIT_BYTES
    with _WAVEFORM_CACHE_LOCK:
        requested = str(cache_dir or "").strip()
        target = requested or str(_WAVEFORM_CACHE_DIR or "").strip() or _default_waveform_cache_dir()
        target = os.path.abspath(target)
        if limit_mb is not None:
            _WAVEFORM_CACHE_LIMIT_BYTES = _normalize_waveform_cache_limit_mb(int(limit_mb)) * 1024 * 1024
        if clear_existing and os.path.isdir(target):
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception:
                pass
        try:
            os.makedirs(target, exist_ok=True)
        except Exception:
            target = ""
        _WAVEFORM_CACHE_DIR = target
        _enforce_waveform_cache_limit_locked()
    return target


def configure_waveform_disk_cache(limit_mb: int, cache_dir: str = "") -> str:
    return prepare_waveform_disk_cache(cache_dir=cache_dir, clear_existing=False, limit_mb=limit_mb)


def clear_waveform_disk_cache() -> bool:
    with _WAVEFORM_CACHE_LOCK:
        target = str(_WAVEFORM_CACHE_DIR or "").strip()
        if not target:
            return False
        if os.path.isdir(target):
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception:
                return False
        try:
            os.makedirs(target, exist_ok=True)
        except Exception:
            return False
    return True


def get_waveform_cache_usage_bytes() -> int:
    with _WAVEFORM_CACHE_LOCK:
        return _waveform_cache_usage_bytes_locked()


def _waveform_cache_usage_bytes_locked() -> int:
    target = str(_WAVEFORM_CACHE_DIR or "").strip()
    if not target or (not os.path.isdir(target)):
        return 0
    total = 0
    try:
        for name in os.listdir(target):
            if not name.lower().endswith(".wpk"):
                continue
            path = os.path.join(target, name)
            if not os.path.isfile(path):
                continue
            total += int(os.path.getsize(path))
    except Exception:
        return total
    return total


def _enforce_waveform_cache_limit_locked() -> None:
    target = str(_WAVEFORM_CACHE_DIR or "").strip()
    if not target or (not os.path.isdir(target)):
        return
    limit = max(1, int(_WAVEFORM_CACHE_LIMIT_BYTES))
    entries: List[Tuple[float, str, int]] = []
    total = 0
    try:
        for name in os.listdir(target):
            if not name.lower().endswith(".wpk"):
                continue
            path = os.path.join(target, name)
            if not os.path.isfile(path):
                continue
            size = int(os.path.getsize(path))
            mtime = float(os.path.getmtime(path))
            entries.append((mtime, path, size))
            total += size
    except Exception:
        return
    if total <= limit:
        return
    entries.sort(key=lambda item: item[0])
    for _mtime, path, size in entries:
        if total <= limit:
            break
        try:
            os.remove(path)
            total = max(0, total - int(size))
        except Exception:
            continue


def _waveform_cache_path(file_path: str, sample_count: int) -> str:
    if not _WAVEFORM_CACHE_DIR:
        return ""
    path = str(file_path or "").strip()
    if not path:
        return ""
    try:
        stat = os.stat(path)
    except Exception:
        return ""
    norm = _normalize_cache_key(path)
    digest_source = (
        f"{_WAVEFORM_CACHE_VERSION}|{norm}|{int(stat.st_size)}|{int(getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1e9)))}"
        f"|{max(1, int(sample_count))}"
    )
    digest = hashlib.sha1(digest_source.encode("utf-8", errors="ignore")).hexdigest()
    return os.path.join(_WAVEFORM_CACHE_DIR, f"{digest}.wpk")


def _load_waveform_peaks_from_disk(file_path: str, sample_count: int) -> Optional[List[float]]:
    with _WAVEFORM_CACHE_LOCK:
        cache_file = _waveform_cache_path(file_path, sample_count)
    if not cache_file or not os.path.exists(cache_file):
        return None
    try:
        payload = np.fromfile(cache_file, dtype=np.uint8)
    except Exception:
        return None
    expected = max(1, int(sample_count))
    if len(payload) != expected:
        return None
    return (payload.astype(np.float32) / 255.0).tolist()


def _save_waveform_peaks_to_disk(file_path: str, sample_count: int, peaks: List[float]) -> None:
    if not peaks:
        return
    with _WAVEFORM_CACHE_LOCK:
        cache_file = _waveform_cache_path(file_path, sample_count)
    if not cache_file:
        return
    try:
        arr = np.asarray(peaks, dtype=np.float32)
        arr = np.clip(arr, 0.0, 1.0)
        quantized = (arr * 255.0).astype(np.uint8)
        expected = max(1, int(sample_count))
        if len(quantized) != expected:
            return
        tmp_file = f"{cache_file}.tmp-{os.getpid()}-{threading.get_ident()}"
        quantized.tofile(tmp_file)
        os.replace(tmp_file, cache_file)
        with _WAVEFORM_CACHE_LOCK:
            _enforce_waveform_cache_limit_locked()
    except Exception:
        try:
            if "tmp_file" in locals() and tmp_file and os.path.exists(tmp_file):
                os.remove(tmp_file)
        except Exception:
            pass


def _prime_waveform_disk_cache_from_frames(file_path: str, frames: np.ndarray) -> None:
    path = str(file_path or "").strip()
    if not path or frames is None or len(frames) <= 0:
        return
    for raw_points in _WAVEFORM_PRELOAD_SAMPLE_COUNTS:
        points = max(1, int(raw_points))
        if _load_waveform_peaks_from_disk(path, points) is not None:
            continue
        peaks = _compute_waveform_peaks_from_frames(frames, points)
        _save_waveform_peaks_to_disk(path, points, peaks)


class _NullOutputStream:
    def start(self) -> None:
        return

    def stop(self) -> None:
        return

    def close(self) -> None:
        return


def _ensure_decoder() -> None:
    global _DECODER_READY
    with _DECODER_LOCK:
        if _DECODER_READY and pygame.mixer.get_init():
            return
        if not pygame.get_init():
            pygame.init()
        if not pygame.mixer.get_init():
            original_driver = os.environ.get("SDL_AUDIODRIVER")
            init_errors: List[str] = []
            for driver in [original_driver, "wasapi", "directsound", "winmm", "dummy"]:
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.quit()
                    if driver:
                        os.environ["SDL_AUDIODRIVER"] = driver
                    elif "SDL_AUDIODRIVER" in os.environ:
                        del os.environ["SDL_AUDIODRIVER"]
                    pygame.mixer.init(frequency=44100, size=-16, channels=_CHANNEL_COUNT)
                    break
                except Exception as exc:
                    init_errors.append(f"{driver or 'default'}: {exc}")
            if not pygame.mixer.get_init():
                raise pygame.error("Unable to initialize pygame mixer: " + " | ".join(init_errors))
        _DECODER_READY = True


def _allocate_stream_id() -> int:
    global _NEXT_STREAM_ID
    stream_id = _NEXT_STREAM_ID
    _NEXT_STREAM_ID += 1
    return stream_id


def list_output_devices() -> List[str]:
    names: List[str] = []
    try:
        devices = sd.query_devices()
    except Exception:
        devices = []
    for dev in devices:
        try:
            if int(dev.get("max_output_channels", 0)) > 0:
                name = str(dev.get("name", "")).strip()
                if name:
                    names.append(name)
        except Exception:
            continue
    return _dedupe(names)


def set_output_device(device_name: str) -> bool:
    global _REQUESTED_DEVICE
    target = (device_name or "").strip()
    if not target:
        _REQUESTED_DEVICE = ""
        return True
    try:
        _find_output_device_index(target)
    except Exception:
        return False
    _REQUESTED_DEVICE = target
    return True


def _find_output_device_index(device_name: str) -> Optional[int]:
    target = (device_name or "").strip().casefold()
    if not target:
        return None
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if int(dev.get("max_output_channels", 0)) <= 0:
            continue
        name = str(dev.get("name", "")).strip().casefold()
        if name == target:
            return i
    raise ValueError(f"Output device not found: {device_name}")


def _normalize_device_names(raw_names) -> List[str]:
    result: List[str] = []
    for raw in raw_names:
        if isinstance(raw, bytes):
            name = raw.decode("utf-8", errors="replace")
        else:
            name = str(raw)
        name = name.strip()
        if name:
            result.append(name)
    return result


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def get_media_ssp_units(file_path: str) -> Tuple[int, int]:
    _ensure_decoder()
    sound = _load_sound_with_fallback(file_path)
    raw_units = len(sound.get_raw())
    duration_ms = int(max(0.0, float(sound.get_length())) * 1000.0)
    return duration_ms, max(0, int(raw_units))


def configure_audio_preload_cache(enabled: bool, memory_limit_mb: int) -> None:
    configure_audio_preload_cache_policy(enabled=enabled, memory_limit_mb=memory_limit_mb, pressure_enabled=True)


def configure_audio_preload_cache_policy(enabled: bool, memory_limit_mb: int, pressure_enabled: bool) -> None:
    global _PRELOAD_ENABLED, _PRELOAD_LIMIT_BYTES, _PRELOAD_CACHE_BYTES, _PRELOAD_PRESSURE_ENABLED, _PRELOAD_PAUSED
    _total_mb, _reserve_mb, max_limit_mb = get_preload_memory_limits_mb()
    limit_mb = max(64, min(int(max_limit_mb), int(memory_limit_mb)))
    with _PRELOAD_LOCK:
        _PRELOAD_ENABLED = bool(enabled)
        _PRELOAD_LIMIT_BYTES = limit_mb * 1024 * 1024
        _PRELOAD_PRESSURE_ENABLED = bool(pressure_enabled)
        if not _PRELOAD_ENABLED:
            _PRELOAD_PAUSED = False
        if not _PRELOAD_ENABLED:
            for future in list(_PRELOAD_TASKS.values()):
                try:
                    future.cancel()
                except Exception:
                    pass
            _PRELOAD_TASKS.clear()
            _PRELOAD_CACHE.clear()
            _FORCED_MEDIA_CACHE.clear()
            _PRELOAD_CACHE_BYTES = 0
            return
        _evict_preload_cache_locked()


def enforce_audio_preload_limits() -> None:
    with _PRELOAD_LOCK:
        if not _PRELOAD_ENABLED:
            return
        _evict_preload_cache_locked()


def get_preload_memory_limits_mb() -> Tuple[int, int, int]:
    total_bytes, _available_bytes = _system_memory_bytes()
    if total_bytes <= 0:
        return 4096, 410, 3686
    reserve_bytes = _memory_reserve_bytes(total_bytes)
    max_limit_bytes = max(128 * 1024 * 1024, total_bytes - reserve_bytes)
    total_mb = max(256, int(total_bytes // (1024 * 1024)))
    reserve_mb = max(128, int(reserve_bytes // (1024 * 1024)))
    max_limit_mb = max(128, int(max_limit_bytes // (1024 * 1024)))
    return total_mb, reserve_mb, max_limit_mb


def get_audio_preload_runtime_status() -> Tuple[bool, int]:
    with _PRELOAD_LOCK:
        active = 0
        for future in _PRELOAD_TASKS.values():
            try:
                if not future.done():
                    active += 1
            except Exception:
                continue
        return bool(_PRELOAD_ENABLED), int(active)


def get_audio_preload_capacity_bytes() -> Tuple[int, int, int]:
    with _PRELOAD_LOCK:
        effective_limit = _effective_limit_bytes_locked()
        used = max(0, int(_PRELOAD_CACHE_BYTES))
        remaining = max(0, int(effective_limit) - used)
        return remaining, int(effective_limit), used


def is_audio_preloaded(file_path: str) -> bool:
    path = _normalize_cache_key(file_path)
    if not path:
        return False
    with _PRELOAD_LOCK:
        return (path in _FORCED_MEDIA_CACHE) or (path in _PRELOAD_CACHE)


def can_stream_without_preload(file_path: str) -> bool:
    path = str(file_path or "").strip()
    return bool(path) and os.path.exists(path) and ffmpeg_available()


def can_decode_with_ffmpeg(file_path: str, timeout_ms: int = 180) -> bool:
    path = str(file_path or "").strip()
    if not can_stream_without_preload(path):
        return False
    mixer_info = pygame.mixer.get_init() or (44100, -16, 2)
    sample_rate = int(mixer_info[0])
    channels = int(mixer_info[2])
    decoder: Optional[FFmpegPCMStream] = None
    deadline = time.perf_counter() + (max(40, int(timeout_ms)) / 1000.0)
    try:
        decoder = FFmpegPCMStream(path, sample_rate=sample_rate, channels=channels)
        decoder.start(0)
        while time.perf_counter() < deadline:
            _block, wrote, eof = decoder.read_frames(1024)
            if wrote > 0:
                return True
            if eof:
                return False
    except Exception:
        return False
    finally:
        if decoder is not None:
            try:
                decoder.close()
            except Exception:
                pass
    # Decoder started but did not emit frames in the short probe window.
    # Treat known-duration files as playable to avoid false negatives.
    return probe_media_duration_ms(path) > 0


def request_audio_preload(file_paths: List[str], prioritize: bool = False, force: bool = False) -> None:
    with _PRELOAD_LOCK:
        if ((not _PRELOAD_ENABLED) and (not force)) or (_PRELOAD_PAUSED and (not force)):
            return
    normalized: List[str] = []
    wanted: set[str] = set()
    for raw_path in file_paths:
        path = _normalize_cache_key(raw_path)
        if not path:
            continue
        if not os.path.exists(path):
            continue
        if path in wanted:
            continue
        wanted.add(path)
        normalized.append(path)
    if prioritize:
        with _PRELOAD_LOCK:
            for task_path, future in list(_PRELOAD_TASKS.items()):
                if task_path in wanted:
                    continue
                try:
                    if not future.done():
                        future.cancel()
                except Exception:
                    pass
                _PRELOAD_TASKS.pop(task_path, None)
    for path in normalized:
        with _PRELOAD_LOCK:
            cached = _PRELOAD_CACHE.get(path)
            if cached is not None:
                continue
            future = _PRELOAD_TASKS.get(path)
            if future is not None and not future.done():
                continue
            future = _PRELOAD_EXECUTOR.submit(_preload_path_worker, path, bool(force))
            _PRELOAD_TASKS[path] = future

            def _clear_task(done_future, cache_path=path) -> None:
                with _PRELOAD_LOCK:
                    active = _PRELOAD_TASKS.get(cache_path)
                    if active is done_future:
                        _PRELOAD_TASKS.pop(cache_path, None)

            future.add_done_callback(_clear_task)


def _preload_path_worker(file_path: str, force: bool = False) -> None:
    with _PRELOAD_LOCK:
        if ((not _PRELOAD_ENABLED) and (not force)) or (_PRELOAD_PAUSED and (not force)):
            return
    try:
        frames, duration_ms = _decode_media_frames(file_path)
    except Exception:
        return
    _prime_waveform_disk_cache_from_frames(file_path, frames)
    _store_preload_entry(file_path, frames, duration_ms, force=force)


def set_audio_preload_paused(paused: bool) -> None:
    global _PRELOAD_PAUSED
    with _PRELOAD_LOCK:
        _PRELOAD_PAUSED = bool(paused)
        if _PRELOAD_PAUSED:
            for future in list(_PRELOAD_TASKS.values()):
                try:
                    future.cancel()
                except Exception:
                    pass


def _store_preload_entry(file_path: str, frames: np.ndarray, duration_ms: int, force: bool = False) -> None:
    global _PRELOAD_CACHE_BYTES
    size_bytes = int(frames.nbytes)
    with _PRELOAD_LOCK:
        if force:
            _FORCED_MEDIA_CACHE[file_path] = (frames, int(duration_ms), size_bytes)
            _FORCED_MEDIA_CACHE.move_to_end(file_path)
            while len(_FORCED_MEDIA_CACHE) > 2:
                _FORCED_MEDIA_CACHE.popitem(last=False)
        if (not _PRELOAD_ENABLED) and (not force):
            return
        existing = _PRELOAD_CACHE.get(file_path)
        if existing is not None:
            _PRELOAD_CACHE_BYTES = max(0, _PRELOAD_CACHE_BYTES - int(existing[2]))
        if size_bytes > _PRELOAD_LIMIT_BYTES:
            return
        _PRELOAD_CACHE[file_path] = (frames, int(duration_ms), size_bytes)
        _PRELOAD_CACHE_BYTES += size_bytes
        _evict_preload_cache_locked()


def _evict_preload_cache_locked() -> None:
    global _PRELOAD_CACHE_BYTES
    effective_limit = _effective_limit_bytes_locked()
    while _PRELOAD_CACHE and _PRELOAD_CACHE_BYTES > effective_limit:
        _old_path, (_old_frames, _old_duration_ms, old_size) = _PRELOAD_CACHE.popitem(last=False)
        _PRELOAD_CACHE_BYTES = max(0, _PRELOAD_CACHE_BYTES - int(old_size))


def _effective_limit_bytes_locked() -> int:
    effective_limit = int(_PRELOAD_LIMIT_BYTES)
    if _PRELOAD_PRESSURE_ENABLED:
        total_bytes, available_bytes = _system_memory_bytes()
        # If runtime memory metrics are unavailable (observed on some macOS environments),
        # keep the configured preload limit instead of forcing it to zero.
        if total_bytes > 0 and available_bytes > 0:
            reserve_bytes = _memory_reserve_bytes(total_bytes)
            pressure_limit = max(0, int(available_bytes - reserve_bytes))
            effective_limit = min(effective_limit, pressure_limit)
    return max(0, int(effective_limit))


def _memory_reserve_bytes(total_bytes: int) -> int:
    if total_bytes <= 0:
        return 128 * 1024 * 1024
    return max(int(total_bytes * 0.10), 128 * 1024 * 1024)


def _system_memory_bytes() -> Tuple[int, int]:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys), int(stat.ullAvailPhys)
        except Exception:
            pass
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        phys_pages = int(os.sysconf("SC_PHYS_PAGES"))
        avail_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        return max(0, page_size * phys_pages), max(0, page_size * avail_pages)
    except Exception:
        return 0, 0


def _normalize_cache_key(file_path: str) -> str:
    if not file_path:
        return ""
    return os.path.normcase(os.path.abspath(str(file_path)))


def _bytes_to_frames(raw: bytes, sample_size: int, channels: int) -> Optional[np.ndarray]:
    if channels <= 0:
        return None
    if sample_size in (-16, 16):
        src = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_size == 8:
        src = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_size == -8:
        src = np.frombuffer(raw, dtype=np.int8).astype(np.float32) / 128.0
    elif sample_size in (-32, 32):
        src = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        return None
    frame_count = int(len(src) // channels)
    if frame_count <= 0:
        return None
    src = src[: frame_count * channels]
    return src.reshape((frame_count, channels))


def _decode_media_frames(file_path: str) -> Tuple[np.ndarray, int]:
    _ensure_decoder()
    sound = _load_sound_with_fallback(file_path)
    raw = sound.get_raw()
    mixer_info = pygame.mixer.get_init() or (44100, -16, 2)
    sample_rate = int(mixer_info[0])
    sample_size = int(mixer_info[1])
    channels = int(mixer_info[2])
    frames = _bytes_to_frames(raw, sample_size, channels)
    if frames is None:
        raise ValueError("Unsupported mixer sample format for streaming DSP")
    duration_ms = int((len(frames) / float(sample_rate)) * 1000.0)
    return frames, duration_ms


def _load_sound_with_fallback(file_path: str):
    try:
        return pygame.mixer.Sound(file_path)
    except Exception as direct_exc:
        if not str(file_path or "").lower().endswith(".mp3"):
            raise
        try:
            raw = open(file_path, "rb").read()
        except Exception:
            raise direct_exc
        offset = _find_mp3_frame_sync_offset(raw)
        if offset <= 0:
            raise direct_exc
        try:
            return pygame.mixer.Sound(file=io.BytesIO(raw[offset:]))
        except Exception as fallback_exc:
            message = f"{direct_exc}; mp3 fallback from byte offset {offset} failed: {fallback_exc}"
            raise type(direct_exc)(message) from fallback_exc


def _find_mp3_frame_sync_offset(raw: bytes) -> int:
    if not raw or len(raw) < 2:
        return -1

    start = 0
    if len(raw) >= 10 and raw[:3] == b"ID3":
        flags = raw[5]
        size = ((raw[6] & 0x7F) << 21) | ((raw[7] & 0x7F) << 14) | ((raw[8] & 0x7F) << 7) | (raw[9] & 0x7F)
        start = 10 + int(size)
        if flags & 0x10:
            start += 10
        start = min(start, max(0, len(raw) - 2))

    for i in range(max(0, start), len(raw) - 1):
        if raw[i] != 0xFF:
            continue
        b1 = raw[i + 1]
        if (b1 & 0xE0) != 0xE0:
            continue
        return i
    return -1


def _peek_cached_media_frames(file_path: str) -> Optional[Tuple[np.ndarray, int]]:
    cache_key = _normalize_cache_key(file_path)
    if not cache_key:
        return None
    with _PRELOAD_LOCK:
        forced = _FORCED_MEDIA_CACHE.get(cache_key)
        if forced is not None:
            return forced[0], int(forced[1])
        cached = _PRELOAD_CACHE.get(cache_key)
        if cached is not None:
            return cached[0], int(cached[1])
    return None


def _load_media_frames(file_path: str) -> Tuple[np.ndarray, int]:
    cache_key = _normalize_cache_key(file_path)
    if cache_key:
        with _PRELOAD_LOCK:
            forced = _FORCED_MEDIA_CACHE.pop(cache_key, None)
            if forced is not None:
                return forced[0], int(forced[1])
            cached = _PRELOAD_CACHE.get(cache_key)
            if cached is not None:
                return cached[0], int(cached[1])
    frames, duration_ms = _decode_media_frames(file_path)
    if cache_key:
        _store_preload_entry(cache_key, frames, duration_ms)
    return frames, duration_ms


def _compute_waveform_peaks_from_frames(frames: Optional[np.ndarray], sample_count: int = 1024) -> List[float]:
    points = max(1, int(sample_count))
    if frames is None or len(frames) <= 0:
        return []

    if frames.shape[1] > 1:
        mono = np.max(np.abs(frames), axis=1)
    else:
        mono = np.abs(frames[:, 0])
    frame_count = int(len(mono))
    if frame_count <= 0:
        return []

    peaks = np.zeros(points, dtype=np.float32)
    if frame_count <= points:
        for i in range(frame_count):
            peaks[i] = float(mono[i])
    else:
        edges = np.linspace(0, frame_count, points + 1, dtype=np.int64)
        for i in range(points):
            start = int(edges[i])
            end = int(edges[i + 1])
            if end <= start:
                end = min(frame_count, start + 1)
            segment = mono[start:end]
            peaks[i] = float(np.max(segment)) if len(segment) > 0 else 0.0

    peak_max = float(np.max(peaks)) if len(peaks) > 0 else 0.0
    if peak_max > 0.0:
        peaks /= peak_max
    return peaks.tolist()


def _compute_waveform_peaks_from_path(file_path: str, sample_count: int = 1024) -> List[float]:
    path = str(file_path or "").strip()
    if not path:
        return []
    points = max(1, int(sample_count))
    cached_peaks = _load_waveform_peaks_from_disk(path, points)
    if cached_peaks is not None:
        return cached_peaks
    frames: Optional[np.ndarray]
    cached = _peek_cached_media_frames(path)
    if cached is not None:
        frames = cached[0]
    else:
        try:
            frames, _duration_ms = _decode_media_frames(path)
        except Exception:
            return []
    peaks = _compute_waveform_peaks_from_frames(frames, points)
    _save_waveform_peaks_to_disk(path, points, peaks)
    return peaks


class ExternalMediaPlayer(QObject):
    StoppedState = 0
    PlayingState = 1
    PausedState = 2

    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        _ensure_decoder()

        self._stream_id = _allocate_stream_id()
        self._media_path = ""
        self._state = self.StoppedState
        self._duration_ms = 0
        self._position_ms = 0
        self._volume = 100
        self._started_at = 0.0
        self._meter_levels: Tuple[float, float] = (0.0, 0.0)

        mixer_info = pygame.mixer.get_init() or (44100, -16, 2)
        self._sample_rate = int(mixer_info[0])
        self._sample_size = int(mixer_info[1])
        self._channels = int(mixer_info[2])

        self._source_frames: Optional[np.ndarray] = None
        self._stream_decoder: Optional[FFmpegPCMStream] = None
        self._streaming_mode = False
        self._stream_pending = np.zeros((0, self._channels), dtype=np.float32)
        self._source_pos = 0.0
        self._source_pos_anchor = 0.0
        self._source_pos_anchor_t = time.perf_counter()
        self._source_pos_anchor_tempo = 1.0
        self._ended = False
        self._dsp_config = DSPConfig()
        self._dsp_processor = RealTimeDSPProcessor(self._sample_rate, self._channels)

        self._lock = threading.RLock()
        self._stream = self._create_stream()
        self._stream.start()

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(100)
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start()

    def setNotifyInterval(self, interval_ms: int) -> None:
        self._poll_timer.setInterval(max(20, int(interval_ms)))

    def setMedia(self, file_path: str, dsp_config: Optional[DSPConfig] = None) -> None:
        self.stop()
        frames: Optional[np.ndarray] = None
        duration_ms = 0
        use_streaming = False
        new_decoder: Optional[FFmpegPCMStream] = None

        cached = _peek_cached_media_frames(file_path)
        if cached is not None:
            frames, duration_ms = cached
        elif ffmpeg_available():
            new_decoder = FFmpegPCMStream(file_path, sample_rate=self._sample_rate, channels=self._channels)
            new_decoder.start(0)
            duration_ms = max(0, int(probe_media_duration_ms(file_path)))
            use_streaming = True
        else:
            frames, duration_ms = _load_media_frames(file_path)

        with self._lock:
            old_decoder = self._stream_decoder
            self._stream_decoder = None
            self._streaming_mode = False
            self._stream_pending = np.zeros((0, self._channels), dtype=np.float32)
            self._media_path = file_path
            self._source_frames = frames
            if use_streaming and new_decoder is not None:
                self._stream_decoder = new_decoder
                self._streaming_mode = True
            self._source_pos = 0.0
            self._source_pos_anchor = 0.0
            self._source_pos_anchor_t = time.perf_counter()
            self._source_pos_anchor_tempo = self._tempo_ratio_locked()
            self._duration_ms = int(duration_ms)
            self._position_ms = 0
            self._ended = False
            if dsp_config is not None:
                self._dsp_config = normalize_config(dsp_config)
                self._dsp_processor.set_config(self._dsp_config)
        if old_decoder is not None:
            try:
                old_decoder.close()
            except Exception:
                pass

        self.durationChanged.emit(self._duration_ms)
        self.positionChanged.emit(0)

    def setDSPConfig(self, dsp_config: DSPConfig) -> None:
        cfg = normalize_config(dsp_config)
        with self._lock:
            self._dsp_config = cfg
            self._dsp_processor.set_config(cfg)

    def play(self) -> None:
        with self._lock:
            if (self._source_frames is None) and (not self._streaming_mode):
                return
            if self._state == self.PlayingState:
                return
            self._started_at = time.monotonic() - (self._position_ms / 1000.0)
            self._source_pos_anchor = self._source_pos
            self._source_pos_anchor_t = time.perf_counter()
            self._source_pos_anchor_tempo = self._tempo_ratio_locked()
            self._set_state_locked(self.PlayingState)

    def pause(self) -> None:
        with self._lock:
            if self._state != self.PlayingState:
                return
            if self._streaming_mode:
                self._position_ms = int((self._source_pos / float(self._sample_rate)) * 1000.0)
            else:
                self._position_ms = self._position_from_source_pos_locked()
            self._source_pos_anchor = self._source_pos
            self._source_pos_anchor_t = time.perf_counter()
            self._source_pos_anchor_tempo = self._tempo_ratio_locked()
            self._set_state_locked(self.PausedState)

    def stop(self) -> None:
        decoder_to_seek: Optional[FFmpegPCMStream] = None
        with self._lock:
            decoder_to_seek = self._stream_decoder if self._streaming_mode else None
            self._stream_pending = np.zeros((0, self._channels), dtype=np.float32)
            self._source_pos = 0.0
            self._source_pos_anchor = 0.0
            self._source_pos_anchor_t = time.perf_counter()
            self._source_pos_anchor_tempo = self._tempo_ratio_locked()
            self._position_ms = 0
            self._ended = False
            self._set_state_locked(self.StoppedState)
        if decoder_to_seek is not None:
            try:
                decoder_to_seek.seek(0)
            except Exception:
                pass
        self.positionChanged.emit(0)

    def state(self) -> int:
        with self._lock:
            return self._state

    def setPosition(self, position_ms: int) -> None:
        decoder_to_seek: Optional[FFmpegPCMStream] = None
        target = 0
        with self._lock:
            target = max(0, min(int(position_ms), self._duration_ms))
            self._position_ms = target
            if self._source_frames is not None:
                self._source_pos = (target / 1000.0) * self._sample_rate
                self._source_pos = max(0.0, min(self._source_pos, float(len(self._source_frames))))
                self._source_pos_anchor = self._source_pos
                self._source_pos_anchor_t = time.perf_counter()
                self._source_pos_anchor_tempo = self._tempo_ratio_locked()
                self._ended = False
            elif self._streaming_mode and self._stream_decoder is not None:
                decoder_to_seek = self._stream_decoder
                self._stream_pending = np.zeros((0, self._channels), dtype=np.float32)
                self._source_pos = (target / 1000.0) * self._sample_rate
                self._source_pos_anchor = self._source_pos
                self._source_pos_anchor_t = time.perf_counter()
                self._source_pos_anchor_tempo = 1.0
                self._ended = False
        if decoder_to_seek is not None:
            try:
                decoder_to_seek.seek(target)
            except Exception:
                with self._lock:
                    self._ended = True
        self.positionChanged.emit(target)

    def position(self) -> int:
        with self._lock:
            return self._position_ms

    def enginePositionMs(self) -> int:
        with self._lock:
            if self._duration_ms <= 0:
                if self._streaming_mode:
                    return max(0, int((self._source_pos / float(self._sample_rate)) * 1000.0))
                return 0
            pos_samples = self._source_pos
            if self._state == self.PlayingState and self._source_frames is not None:
                elapsed = max(0.0, time.perf_counter() - self._source_pos_anchor_t)
                pos_samples = self._source_pos_anchor + (elapsed * self._sample_rate * self._source_pos_anchor_tempo)
                pos_samples = max(0.0, min(float(len(self._source_frames)), pos_samples))
            pos_ms = int((pos_samples / float(self._sample_rate)) * 1000.0)
            return max(0, min(pos_ms, self._duration_ms))

    def duration(self) -> int:
        with self._lock:
            return self._duration_ms

    def setVolume(self, volume: int) -> None:
        with self._lock:
            self._volume = max(0, min(100, int(volume)))

    def volume(self) -> int:
        with self._lock:
            return self._volume

    def meterLevels(self) -> Tuple[float, float]:
        with self._lock:
            return self._meter_levels

    def waveformPeaks(self, sample_count: int = 1024) -> List[float]:
        with self._lock:
            frames = self._source_frames
            media_path = str(self._media_path or "").strip()
        points = max(1, int(sample_count))
        if frames is not None:
            if media_path:
                cached_peaks = _load_waveform_peaks_from_disk(media_path, points)
                if cached_peaks is not None:
                    return cached_peaks
            peaks = _compute_waveform_peaks_from_frames(frames, points)
            if media_path:
                _save_waveform_peaks_to_disk(media_path, points, peaks)
            return peaks
        return _compute_waveform_peaks_from_path(media_path, points)

    def waveformPeaksAsync(self, sample_count: int = 1024) -> Future:
        with self._lock:
            frames = self._source_frames
            media_path = str(self._media_path or "").strip()
        points = max(1, int(sample_count))
        if frames is not None:
            return _WAVEFORM_EXECUTOR.submit(self._waveform_from_frames_with_cache, media_path, frames, points)
        return _WAVEFORM_EXECUTOR.submit(_compute_waveform_peaks_from_path, media_path, points)

    @staticmethod
    def _waveform_from_frames_with_cache(file_path: str, frames: np.ndarray, sample_count: int) -> List[float]:
        path = str(file_path or "").strip()
        points = max(1, int(sample_count))
        if path:
            cached_peaks = _load_waveform_peaks_from_disk(path, points)
            if cached_peaks is not None:
                return cached_peaks
        peaks = _compute_waveform_peaks_from_frames(frames, points)
        if path:
            _save_waveform_peaks_to_disk(path, points, peaks)
        return peaks

    def _create_stream(self):
        device_index = None
        if _REQUESTED_DEVICE:
            try:
                device_index = _find_output_device_index(_REQUESTED_DEVICE)
            except Exception:
                device_index = None
        try:
            return sd.OutputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="float32",
                callback=self._audio_callback,
                device=device_index,
                blocksize=1024,
                latency="low",
            )
        except Exception:
            return _NullOutputStream()

    def _audio_callback(self, outdata, frames, _time_info, status) -> None:
        if status:
            pass
        outdata.fill(0.0)
        with self._lock:
            if self._state != self.PlayingState:
                self._meter_levels = (0.0, 0.0)
                return
            if (self._source_frames is None) and (not self._streaming_mode):
                self._meter_levels = (0.0, 0.0)
                return

            if self._streaming_mode:
                block, consumed_frames, stream_eof = self._read_stream_block_locked(frames)
                if consumed_frames <= 0 and stream_eof:
                    self._ended = True
                    if self._duration_ms > 0:
                        self._position_ms = self._duration_ms
                    else:
                        self._position_ms = int((self._source_pos / float(self._sample_rate)) * 1000.0)
                    return
                tempo_ratio = 1.0
                user_pitch_ratio = max(0.7, min(1.3, 1.0 + (self._dsp_config.pitch_pct / 100.0)))
                effective_pitch_ratio = user_pitch_ratio
            else:
                block = self._read_source_block_locked(frames)
                consumed_frames = len(block) if block is not None else 0
                stream_eof = False
                tempo_ratio = max(0.7, min(1.3, 1.0 + (self._dsp_config.tempo_pct / 100.0)))
                user_pitch_ratio = max(0.7, min(1.3, 1.0 + (self._dsp_config.pitch_pct / 100.0)))
                effective_pitch_ratio = user_pitch_ratio / tempo_ratio

            if block is None:
                self._ended = True
                self._position_ms = self._duration_ms
                return

            if abs(effective_pitch_ratio - 1.0) > 1e-4:
                block = self._apply_pitch_ratio_block(block, effective_pitch_ratio)

            block = self._dsp_processor.process_block(block)
            block *= (self._volume / 100.0)

            n = min(len(block), frames)
            outdata[:n, :] = block[:n, :]
            if n > 0:
                peaks = np.max(np.abs(outdata[:n, :]), axis=0)
                if len(peaks) >= 2:
                    self._meter_levels = (float(peaks[0]), float(peaks[1]))
                elif len(peaks) == 1:
                    mono = float(peaks[0])
                    self._meter_levels = (mono, mono)
            else:
                self._meter_levels = (0.0, 0.0)
            if n < frames:
                outdata[n:, :] = 0.0
                if self._streaming_mode:
                    self._ended = bool(stream_eof)
                else:
                    self._ended = True
                    self._source_pos = float(len(self._source_frames)) if self._source_frames is not None else 0.0

            if self._streaming_mode:
                self._source_pos += float(consumed_frames)
                self._position_ms = int((self._source_pos / float(self._sample_rate)) * 1000.0)
                if self._duration_ms > 0:
                    self._position_ms = max(0, min(self._position_ms, self._duration_ms))
            else:
                self._position_ms = self._position_from_source_pos_locked()
            self._source_pos_anchor = self._source_pos
            self._source_pos_anchor_t = time.perf_counter()
            self._source_pos_anchor_tempo = tempo_ratio

    def _read_source_block_locked(self, frames: int) -> Optional[np.ndarray]:
        assert self._source_frames is not None
        src = self._source_frames
        n_src = len(src)
        if n_src <= 1:
            return None

        tempo_ratio = max(0.7, min(1.3, 1.0 + (self._dsp_config.tempo_pct / 100.0)))
        idx = self._source_pos + (np.arange(frames, dtype=np.float32) * tempo_ratio)
        valid = idx < (n_src - 1)
        if not np.any(valid):
            return None

        valid_count = int(np.count_nonzero(valid))
        idx_valid = idx[:valid_count]
        i0 = np.floor(idx_valid).astype(np.int64)
        frac = (idx_valid - i0).astype(np.float32)
        i1 = np.minimum(i0 + 1, n_src - 1)
        s0 = src[i0]
        s1 = src[i1]
        block = (s0 * (1.0 - frac[:, None])) + (s1 * frac[:, None])
        if valid_count < frames:
            pad = np.zeros((frames - valid_count, self._channels), dtype=np.float32)
            block = np.vstack((block, pad))

        self._source_pos += float(frames) * tempo_ratio
        if self._source_pos >= float(n_src - 1):
            self._source_pos = float(n_src)
        return block.astype(np.float32, copy=False)

    def _read_stream_block_locked(self, frames: int) -> Tuple[Optional[np.ndarray], int, bool]:
        decoder = self._stream_decoder
        if decoder is None:
            return None, 0, True
        block, consumed, eof = decoder.read_frames(frames)
        if consumed <= 0 and eof:
            return None, 0, True
        return block, int(consumed), bool(eof)

    def _tempo_ratio_locked(self) -> float:
        return max(0.7, min(1.3, 1.0 + (self._dsp_config.tempo_pct / 100.0)))

    def _apply_pitch_ratio_block(self, block: np.ndarray, ratio: float) -> np.ndarray:
        if len(block) <= 1:
            return block
        ratio = max(0.5, min(1.6, float(ratio)))
        src_x = np.arange(len(block), dtype=np.float32)
        dst_x = np.clip(src_x * ratio, 0.0, float(len(block) - 1))
        out = np.empty_like(block)
        for ch in range(block.shape[1]):
            out[:, ch] = np.interp(dst_x, src_x, block[:, ch]).astype(np.float32)
        return out

    def _bytes_to_frames(self, raw: bytes, sample_size: int, channels: int) -> Optional[np.ndarray]:
        return _bytes_to_frames(raw, sample_size, channels)

    def _position_from_source_pos_locked(self) -> int:
        if self._duration_ms <= 0:
            return 0
        pos = int((self._source_pos / float(self._sample_rate)) * 1000.0)
        return max(0, min(pos, self._duration_ms))

    def _poll(self) -> None:
        emit_pos: Optional[int] = None
        with self._lock:
            if self._state == self.PlayingState:
                if self._ended:
                    self._ended = False
                    if self._duration_ms > 0:
                        self._position_ms = self._duration_ms
                    else:
                        self._position_ms = int((self._source_pos / float(self._sample_rate)) * 1000.0)
                    emit_pos = self._position_ms
                    self._set_state_locked(self.StoppedState)
                else:
                    emit_pos = self._position_ms
        if emit_pos is not None:
            self.positionChanged.emit(emit_pos)

    def _set_state_locked(self, new_state: int) -> None:
        if new_state != self._state:
            self._state = new_state
            self.stateChanged.emit(new_state)

    def __del__(self) -> None:
        try:
            if hasattr(self, "_stream_decoder") and self._stream_decoder is not None:
                self._stream_decoder.close()
        except Exception:
            pass
        try:
            if hasattr(self, "_stream") and self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
