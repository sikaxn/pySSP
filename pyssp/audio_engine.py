from __future__ import annotations

import ctypes
import atexit
import os
import sys
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
_PRELOAD_CACHE_BYTES = 0
_PRELOAD_TASKS: Dict[str, Future] = {}
_PRELOAD_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pyssp-audio-preload")


def _shutdown_preload_executor() -> None:
    try:
        _PRELOAD_EXECUTOR.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass


atexit.register(_shutdown_preload_executor)


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
        _PRELOAD_CACHE_BYTES = 0
    _shutdown_preload_executor()


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
    sound = pygame.mixer.Sound(file_path)
    raw_units = len(sound.get_raw())
    duration_ms = int(max(0.0, float(sound.get_length())) * 1000.0)
    return duration_ms, max(0, int(raw_units))


def configure_audio_preload_cache(enabled: bool, memory_limit_mb: int) -> None:
    configure_audio_preload_cache_policy(enabled=enabled, memory_limit_mb=memory_limit_mb, pressure_enabled=True)


def configure_audio_preload_cache_policy(enabled: bool, memory_limit_mb: int, pressure_enabled: bool) -> None:
    global _PRELOAD_ENABLED, _PRELOAD_LIMIT_BYTES, _PRELOAD_CACHE_BYTES, _PRELOAD_PRESSURE_ENABLED, _PRELOAD_PAUSED
    limit_mb = max(64, min(8192, int(memory_limit_mb)))
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


def request_audio_preload(file_paths: List[str]) -> None:
    with _PRELOAD_LOCK:
        if (not _PRELOAD_ENABLED) or _PRELOAD_PAUSED:
            return
    for raw_path in file_paths:
        path = _normalize_cache_key(raw_path)
        if not path:
            continue
        if not os.path.exists(path):
            continue
        with _PRELOAD_LOCK:
            cached = _PRELOAD_CACHE.get(path)
            if cached is not None:
                continue
            future = _PRELOAD_TASKS.get(path)
            if future is not None and not future.done():
                continue
            future = _PRELOAD_EXECUTOR.submit(_preload_path_worker, path)
            _PRELOAD_TASKS[path] = future

            def _clear_task(done_future, cache_path=path) -> None:
                with _PRELOAD_LOCK:
                    active = _PRELOAD_TASKS.get(cache_path)
                    if active is done_future:
                        _PRELOAD_TASKS.pop(cache_path, None)

            future.add_done_callback(_clear_task)


def _preload_path_worker(file_path: str) -> None:
    with _PRELOAD_LOCK:
        if (not _PRELOAD_ENABLED) or _PRELOAD_PAUSED:
            return
    try:
        frames, duration_ms = _decode_media_frames(file_path)
    except Exception:
        return
    _store_preload_entry(file_path, frames, duration_ms)


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


def _store_preload_entry(file_path: str, frames: np.ndarray, duration_ms: int) -> None:
    global _PRELOAD_CACHE_BYTES
    size_bytes = int(frames.nbytes)
    with _PRELOAD_LOCK:
        if not _PRELOAD_ENABLED:
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
    effective_limit = int(_PRELOAD_LIMIT_BYTES)
    if _PRELOAD_PRESSURE_ENABLED:
        total_bytes, available_bytes = _system_memory_bytes()
        reserve_bytes = _memory_reserve_bytes(total_bytes)
        pressure_limit = max(0, int(available_bytes - reserve_bytes))
        effective_limit = min(effective_limit, pressure_limit)
    while _PRELOAD_CACHE and _PRELOAD_CACHE_BYTES > effective_limit:
        _old_path, (_old_frames, _old_duration_ms, old_size) = _PRELOAD_CACHE.popitem(last=False)
        _PRELOAD_CACHE_BYTES = max(0, _PRELOAD_CACHE_BYTES - int(old_size))


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
    sound = pygame.mixer.Sound(file_path)
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


def _load_media_frames(file_path: str) -> Tuple[np.ndarray, int]:
    cache_key = _normalize_cache_key(file_path)
    if cache_key:
        with _PRELOAD_LOCK:
            if _PRELOAD_ENABLED:
                cached = _PRELOAD_CACHE.get(cache_key)
                if cached is not None:
                    return cached[0], int(cached[1])
    frames, duration_ms = _decode_media_frames(file_path)
    if cache_key:
        _store_preload_entry(cache_key, frames, duration_ms)
    return frames, duration_ms


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
        frames, duration_ms = _load_media_frames(file_path)

        with self._lock:
            self._media_path = file_path
            self._source_frames = frames
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

        self.durationChanged.emit(self._duration_ms)
        self.positionChanged.emit(0)

    def setDSPConfig(self, dsp_config: DSPConfig) -> None:
        cfg = normalize_config(dsp_config)
        with self._lock:
            self._dsp_config = cfg
            self._dsp_processor.set_config(cfg)

    def play(self) -> None:
        with self._lock:
            if self._source_frames is None:
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
            self._position_ms = self._position_from_source_pos_locked()
            self._source_pos_anchor = self._source_pos
            self._source_pos_anchor_t = time.perf_counter()
            self._source_pos_anchor_tempo = self._tempo_ratio_locked()
            self._set_state_locked(self.PausedState)

    def stop(self) -> None:
        with self._lock:
            self._source_pos = 0.0
            self._source_pos_anchor = 0.0
            self._source_pos_anchor_t = time.perf_counter()
            self._source_pos_anchor_tempo = self._tempo_ratio_locked()
            self._position_ms = 0
            self._ended = False
            self._set_state_locked(self.StoppedState)
        self.positionChanged.emit(0)

    def state(self) -> int:
        with self._lock:
            return self._state

    def setPosition(self, position_ms: int) -> None:
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
        self.positionChanged.emit(target)

    def position(self) -> int:
        with self._lock:
            return self._position_ms

    def enginePositionMs(self) -> int:
        with self._lock:
            if self._duration_ms <= 0:
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
            if self._source_frames is None:
                self._meter_levels = (0.0, 0.0)
                return

            block = self._read_source_block_locked(frames)
            if block is None:
                self._ended = True
                self._position_ms = self._duration_ms
                return

            tempo_ratio = max(0.7, min(1.3, 1.0 + (self._dsp_config.tempo_pct / 100.0)))
            user_pitch_ratio = max(0.7, min(1.3, 1.0 + (self._dsp_config.pitch_pct / 100.0)))
            effective_pitch_ratio = user_pitch_ratio / tempo_ratio
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
                self._ended = True
                self._source_pos = float(len(self._source_frames))

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
                    self._position_ms = self._duration_ms
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
            if hasattr(self, "_stream") and self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
