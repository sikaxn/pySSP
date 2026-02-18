from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes
from time import perf_counter
from typing import Callable, List, Optional, Tuple

import numpy as np
import sounddevice as sd

TIMECODE_MODE_ZERO = "zero"
TIMECODE_MODE_FOLLOW = "follow_media"
TIMECODE_MODE_SYSTEM = "system_time"
TIMECODE_MODE_FOLLOW_FREEZE = "follow_media_freeze"

MTC_IDLE_KEEP_STREAM = "keep_stream"
MTC_IDLE_ALLOW_DARK = "allow_dark"

TIME_CODE_FPS_CHOICES: List[float] = [23.976, 24.0, 25.0, 29.97, 30.0, 48.0, 50.0, 59.94, 60.0]
TIME_CODE_MTC_FPS_CHOICES: List[float] = [24.0, 25.0, 29.97, 30.0]
TIME_CODE_SAMPLE_RATES: List[int] = [44100, 48000, 96000]
TIME_CODE_BIT_DEPTHS: List[int] = [8, 16, 32]

MIDI_OUTPUT_DEVICE_NONE = "__none__"


class _MIDIIOCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.DWORD),
        ("szPname", wintypes.WCHAR * 32),
        ("wTechnology", wintypes.WORD),
        ("wVoices", wintypes.WORD),
        ("wNotes", wintypes.WORD),
        ("wChannelMask", wintypes.WORD),
        ("dwSupport", wintypes.DWORD),
    ]


class _MIDIHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_char_p),
        ("dwBufferLength", wintypes.DWORD),
        ("dwBytesRecorded", wintypes.DWORD),
        ("dwUser", ctypes.c_size_t),
        ("dwFlags", wintypes.DWORD),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_size_t),
        ("dwOffset", wintypes.DWORD),
        ("dwReserved", ctypes.c_size_t * 8),
    ]


class WinMMMidiOut:
    def __init__(self) -> None:
        self._winmm = None
        self._handle = wintypes.HANDLE()
        self._opened = False
        try:
            dword_ptr = getattr(wintypes, "DWORD_PTR", ctypes.c_size_t)
            self._winmm = ctypes.WinDLL("winmm")
            self._winmm.midiOutGetNumDevs.restype = wintypes.UINT
            self._winmm.midiOutGetDevCapsW.argtypes = [wintypes.UINT, ctypes.POINTER(_MIDIIOCAPSW), wintypes.UINT]
            self._winmm.midiOutGetDevCapsW.restype = wintypes.UINT
            self._winmm.midiOutOpen.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.UINT, dword_ptr, dword_ptr, wintypes.DWORD]
            self._winmm.midiOutOpen.restype = wintypes.UINT
            self._winmm.midiOutShortMsg.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            self._winmm.midiOutShortMsg.restype = wintypes.UINT
            self._winmm.midiOutReset.argtypes = [wintypes.HANDLE]
            self._winmm.midiOutReset.restype = wintypes.UINT
            self._winmm.midiOutClose.argtypes = [wintypes.HANDLE]
            self._winmm.midiOutClose.restype = wintypes.UINT
            self._winmm.midiOutPrepareHeader.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MIDIHDR), wintypes.UINT]
            self._winmm.midiOutPrepareHeader.restype = wintypes.UINT
            self._winmm.midiOutLongMsg.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MIDIHDR), wintypes.UINT]
            self._winmm.midiOutLongMsg.restype = wintypes.UINT
            self._winmm.midiOutUnprepareHeader.argtypes = [wintypes.HANDLE, ctypes.POINTER(_MIDIHDR), wintypes.UINT]
            self._winmm.midiOutUnprepareHeader.restype = wintypes.UINT
        except Exception:
            self._winmm = None

    def available(self) -> bool:
        return self._winmm is not None

    def list_devices(self) -> List[Tuple[str, str]]:
        if not self._winmm:
            return []
        count = int(self._winmm.midiOutGetNumDevs())
        devices: List[Tuple[str, str]] = []
        for idx in range(count):
            caps = _MIDIIOCAPSW()
            if self._winmm.midiOutGetDevCapsW(idx, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
                devices.append((str(idx), str(caps.szPname)))
        return devices

    def open(self, device_id: int) -> bool:
        if not self._winmm:
            return False
        self.close()
        result = self._winmm.midiOutOpen(ctypes.byref(self._handle), int(device_id), 0, 0, 0)
        self._opened = result == 0
        return self._opened

    def send_short(self, status: int, data1: int = 0, data2: int = 0) -> None:
        if not self._opened or not self._winmm:
            return
        message = (int(status) & 0xFF) | ((int(data1) & 0xFF) << 8) | ((int(data2) & 0xFF) << 16)
        self._winmm.midiOutShortMsg(self._handle, message)

    def send_long(self, payload: bytes) -> None:
        if not self._opened or not self._winmm:
            return
        data = bytes(payload or b"")
        if not data:
            return
        buf = ctypes.create_string_buffer(data)
        hdr = _MIDIHDR()
        hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
        hdr.dwBufferLength = len(data)
        hdr.dwBytesRecorded = len(data)
        size = ctypes.sizeof(_MIDIHDR)
        if self._winmm.midiOutPrepareHeader(self._handle, ctypes.byref(hdr), size) != 0:
            return
        try:
            if self._winmm.midiOutLongMsg(self._handle, ctypes.byref(hdr), size) != 0:
                return
            deadline = perf_counter() + 0.08
            while perf_counter() < deadline and (hdr.dwFlags & 0x00000001) != 0:
                time.sleep(0.001)
        finally:
            self._winmm.midiOutUnprepareHeader(self._handle, ctypes.byref(hdr), size)

    def close(self) -> None:
        if not self._opened or not self._winmm:
            return
        self._winmm.midiOutReset(self._handle)
        self._winmm.midiOutClose(self._handle)
        self._opened = False


def list_midi_output_devices() -> List[Tuple[str, str]]:
    midi = WinMMMidiOut()
    return midi.list_devices() if midi.available() else []


def _find_output_device_index(device_name: str) -> Optional[int]:
    target = str(device_name or "").strip().casefold()
    if not target:
        return None
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        if int(dev.get("max_output_channels", 0)) <= 0:
            continue
        name = str(dev.get("name", "")).strip().casefold()
        if name == target:
            return idx
    for idx, dev in enumerate(devices):
        if int(dev.get("max_output_channels", 0)) <= 0:
            continue
        name = str(dev.get("name", "")).strip().casefold()
        if target in name:
            return idx
    raise ValueError(f"Output device not found: {device_name}")


def _set_bcd(bits: list[int], offset: int, value: int, width: int) -> None:
    for index in range(width):
        bits[offset + index] = (value >> index) & 0x1


def encode_ltc_bits(frame_number: int, fps: int) -> list[int]:
    bits = [0] * 80
    hours, minutes, seconds, frames = frame_to_timecode_parts(frame_number, fps)
    _set_bcd(bits, 0, frames % 10, 4)
    _set_bcd(bits, 8, frames // 10, 2)
    _set_bcd(bits, 16, seconds % 10, 4)
    _set_bcd(bits, 24, seconds // 10, 3)
    _set_bcd(bits, 32, minutes % 10, 4)
    _set_bcd(bits, 40, minutes // 10, 3)
    _set_bcd(bits, 48, hours % 10, 4)
    _set_bcd(bits, 56, hours // 10, 2)
    # LSB-first write of 0xBFFC yields canonical LTC sync pattern.
    sync_word = 0xBFFC
    for index in range(16):
        bits[64 + index] = (sync_word >> index) & 0x1
    return bits


class LtcAudioOutput:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stream: Optional[sd.OutputStream] = None
        self._enabled = False
        self._device_name = ""
        self._device_index: Optional[int] = None
        self._sample_rate = 48000
        self._bit_depth = 16
        self._dtype = "int16"
        self._amplitude = 9000
        self._fps = 30.0
        self._nominal_fps = 30
        self._samples_per_half_bit = max(1, int(self._sample_rate / (self._fps * 160.0)))
        self._samples_per_bit = self._samples_per_half_bit * 2
        self._current_frame = 0
        self._current_bits = encode_ltc_bits(0, self._nominal_fps)
        self._bit_index = 0
        self._sample_in_bit = 0
        self._signal = 1
        self._frame_boundary_requested = True

    @staticmethod
    def _dtype_and_amplitude(bit_depth: int) -> tuple[str, int]:
        if int(bit_depth) == 8:
            return "uint8", 60
        if int(bit_depth) == 32:
            return "int32", 500000000
        return "int16", 9000

    def _apply_timing_locked(self) -> None:
        fps = max(1.0, float(self._fps))
        self._nominal_fps = nominal_fps(fps)
        self._samples_per_half_bit = max(1, int(self._sample_rate / (fps * 160.0)))
        self._samples_per_bit = self._samples_per_half_bit * 2

    def _close_stream_locked(self) -> None:
        if self._stream is None:
            return
        try:
            self._stream.stop()
        except Exception:
            pass
        try:
            self._stream.close()
        except Exception:
            pass
        self._stream = None

    def _open_stream_locked(self) -> None:
        self._close_stream_locked()
        try:
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype=self._dtype,
                callback=self._audio_callback,
                device=self._device_index,
                latency="low",
            )
            self._stream.start()
        except Exception:
            self._stream = None
            self._enabled = False

    def set_output(self, device_name: Optional[str], sample_rate: int, bit_depth: int, fps: float) -> None:
        with self._lock:
            if device_name is None:
                self._enabled = False
                self._close_stream_locked()
                return
            target = str(device_name).strip()
            new_sr = int(sample_rate) if int(sample_rate) > 0 else 48000
            new_bd = int(bit_depth)
            new_fps = max(1.0, float(fps))
            new_dtype, new_amp = self._dtype_and_amplitude(new_bd)
            cfg_changed = (
                target != self._device_name
                or new_sr != self._sample_rate
                or new_bd != self._bit_depth
                or new_dtype != self._dtype
            )
            self._device_name = target
            self._sample_rate = new_sr
            self._bit_depth = new_bd
            self._dtype = new_dtype
            self._amplitude = new_amp
            self._fps = new_fps
            self._apply_timing_locked()
            if cfg_changed:
                if target:
                    try:
                        self._device_index = _find_output_device_index(target)
                    except Exception:
                        self._device_index = None
                        self._enabled = False
                        self._close_stream_locked()
                        return
                else:
                    self._device_index = None
                self._open_stream_locked()
            self._enabled = self._stream is not None

    def update(self, current_frame: int, fps: float) -> None:
        with self._lock:
            self._current_frame = max(0, int(current_frame))
            new_fps = max(1.0, float(fps))
            if abs(new_fps - self._fps) > 0.0001:
                self._fps = new_fps
                self._apply_timing_locked()

    def request_resync(self) -> None:
        with self._lock:
            self._bit_index = 0
            self._sample_in_bit = 0
            self._frame_boundary_requested = True

    def shutdown(self) -> None:
        with self._lock:
            self._enabled = False
            self._close_stream_locked()

    def _audio_callback(self, outdata, frames, _time_info, _status) -> None:
        with self._lock:
            if (not self._enabled) or self._stream is None:
                outdata.fill(0)
                return
            if self._dtype == "uint8":
                out = np.full((frames,), 128, dtype=np.uint8)
            else:
                out = np.zeros((frames,), dtype=outdata.dtype)
            for i in range(frames):
                if self._frame_boundary_requested:
                    self._current_bits = encode_ltc_bits(self._current_frame, self._nominal_fps)
                    self._frame_boundary_requested = False
                bit_value = self._current_bits[self._bit_index]
                if self._sample_in_bit == 0:
                    self._signal *= -1
                if bit_value and self._sample_in_bit == self._samples_per_half_bit:
                    self._signal *= -1
                if self._dtype == "uint8":
                    val = 128 + (self._amplitude if self._signal > 0 else -self._amplitude)
                    out[i] = np.uint8(max(0, min(255, int(val))))
                else:
                    out[i] = self._amplitude if self._signal > 0 else -self._amplitude
                self._sample_in_bit += 1
                if self._sample_in_bit >= self._samples_per_bit:
                    self._sample_in_bit = 0
                    self._bit_index += 1
                    if self._bit_index >= 80:
                        self._bit_index = 0
                        self._frame_boundary_requested = True
            outdata[:, 0] = out


class MtcMidiOutput:
    def __init__(self, idle_behavior_provider: Optional[Callable[[], str]] = None) -> None:
        self.idle_behavior_provider = idle_behavior_provider or (lambda: MTC_IDLE_KEEP_STREAM)
        self._midi = WinMMMidiOut()
        self._device = MIDI_OUTPUT_DEVICE_NONE
        self._opened_device = MIDI_OUTPUT_DEVICE_NONE
        self._opened = False
        self._send_enabled = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, name="pySSP-MTC", daemon=True)
        self._qf_index = 0
        self._next_send_t = perf_counter()
        self._last_source_frame = 0
        self._last_mtc_frame = 0
        self._has_sent = False
        self._latched_mtc_frame = 0
        self._source_anchor_frame = 0.0
        self._source_anchor_t = perf_counter()
        self._source_fps = 30.0
        self._mtc_fps = 30.0
        self._resync_requested = False
        self._last_full_frame_t = 0.0
        self._last_motion_t = perf_counter()
        self._dark_idle_grace_s = 0.35
        self._thread.start()

    def set_device(self, device_id: str) -> None:
        target = str(device_id or MIDI_OUTPUT_DEVICE_NONE)
        with self._lock:
            if target == self._device:
                return
            self._device = target
            if self._device == MIDI_OUTPUT_DEVICE_NONE:
                # Keep the OS MIDI handle open while the app runs; just stop sending.
                self._send_enabled = False
            elif self._midi.available():
                if self._opened and self._opened_device == self._device:
                    self._send_enabled = True
                else:
                    self._midi.close()
                    self._opened = False
                    try:
                        self._opened = self._midi.open(int(self._device))
                    except (TypeError, ValueError):
                        self._opened = False
                    if self._opened:
                        self._opened_device = self._device
                        self._send_enabled = True
                    else:
                        self._opened_device = MIDI_OUTPUT_DEVICE_NONE
                        self._send_enabled = False
            else:
                self._send_enabled = False
            self._qf_index = 0
            self._next_send_t = perf_counter()
            self._last_source_frame = 0
            self._last_mtc_frame = 0
            self._has_sent = False
            self._latched_mtc_frame = 0
            self._resync_requested = True
            self._last_full_frame_t = 0.0
            self._last_motion_t = perf_counter()

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=0.6)
        with self._lock:
            self._midi.close()
            self._opened = False
            self._opened_device = MIDI_OUTPUT_DEVICE_NONE
            self._send_enabled = False
            self._device = MIDI_OUTPUT_DEVICE_NONE
            self._qf_index = 0
            self._has_sent = False

    def request_resync(self) -> None:
        # Force next update cycle to restart quarter-frame cadence immediately.
        with self._lock:
            self._resync_requested = True
            self._qf_index = 0
            self._has_sent = False
            self._next_send_t = 0.0
            self._last_full_frame_t = 0.0
            self._last_motion_t = perf_counter()

    @staticmethod
    def _coerce_mtc_speed_fps(configured_fps: float) -> float:
        fps = max(0.001, float(configured_fps))
        options = [24.0, 25.0, 29.97, 30.0]
        return min(options, key=lambda option: abs(option - fps))

    @staticmethod
    def _nominal_mtc_fps(mtc_speed_fps: float) -> int:
        if abs(mtc_speed_fps - 24.0) < 0.05:
            return 24
        if abs(mtc_speed_fps - 25.0) < 0.05:
            return 25
        return 30

    @staticmethod
    def _rate_code(fps: int, speed_fps: float) -> int:
        if fps == 24:
            return 0
        if fps == 25:
            return 1
        if fps == 30:
            if abs(speed_fps - 29.97) < 0.05:
                return 2
            return 3
        return 3

    @staticmethod
    def _quarter_frame_data(frame_number: int, fps: int, speed_fps: float, qf_type: int) -> int:
        total_frames_day = 24 * 60 * 60 * max(1, fps)
        frame_number = max(0, int(frame_number)) % total_frames_day
        frames = frame_number % fps
        total_seconds = frame_number // fps
        seconds = total_seconds % 60
        total_minutes = total_seconds // 60
        minutes = total_minutes % 60
        hours = (total_minutes // 60) % 24
        if qf_type == 0:
            value = frames & 0x0F
        elif qf_type == 1:
            value = (frames >> 4) & 0x01
        elif qf_type == 2:
            value = seconds & 0x0F
        elif qf_type == 3:
            value = (seconds >> 4) & 0x03
        elif qf_type == 4:
            value = minutes & 0x0F
        elif qf_type == 5:
            value = (minutes >> 4) & 0x03
        elif qf_type == 6:
            value = hours & 0x0F
        else:
            rate_code = MtcMidiOutput._rate_code(fps, speed_fps)
            value = ((rate_code & 0x03) << 1) | ((hours >> 4) & 0x01)
        return ((qf_type & 0x07) << 4) | (value & 0x0F)

    def _send_full_frame(self, frame_number: int, fps: int, speed_fps: float, now: float) -> None:
        if not self._opened:
            return
        total_frames_day = 24 * 60 * 60 * max(1, fps)
        frame_number = max(0, int(frame_number)) % total_frames_day
        frames = frame_number % fps
        total_seconds = frame_number // fps
        seconds = total_seconds % 60
        total_minutes = total_seconds // 60
        minutes = total_minutes % 60
        hours = (total_minutes // 60) % 24
        rate_code = self._rate_code(fps, speed_fps)
        hr_byte = (hours & 0x1F) | ((rate_code & 0x03) << 5)
        payload = bytes([0xF0, 0x7F, 0x7F, 0x01, 0x01, hr_byte, minutes & 0x3F, seconds & 0x3F, frames & 0x1F, 0xF7])
        self._midi.send_long(payload)
        self._last_full_frame_t = now

    def update(self, current_frame: int, source_fps: float, mtc_fps: float) -> None:
        now = perf_counter()
        with self._lock:
            self._source_anchor_frame = max(0.0, float(current_frame))
            self._source_anchor_t = now
            self._source_fps = max(0.001, float(source_fps))
            self._mtc_fps = max(0.001, float(mtc_fps))

    def _run(self) -> None:
        while not self._stop_event.is_set():
            now = perf_counter()
            with self._lock:
                opened = self._opened and self._send_enabled
                if not opened:
                    sleep_s = 0.01
                else:
                    elapsed = max(0.0, now - self._source_anchor_t)
                    source_fps = self._source_fps
                    current_source_frame = int(max(0.0, self._source_anchor_frame + (elapsed * source_fps)))
                    mtc_speed_fps = self._coerce_mtc_speed_fps(float(self._mtc_fps))
                    fps = self._nominal_mtc_fps(mtc_speed_fps)
                    current_mtc_frame = int(((current_source_frame * mtc_speed_fps) / source_fps) + 1e-6)
                    interval = 1.0 / (mtc_speed_fps * 4.0)
                    if current_source_frame != self._last_source_frame:
                        self._last_motion_t = now
                    if self._resync_requested:
                        self._resync_requested = False
                        self._qf_index = 0
                        self._has_sent = False
                        self._next_send_t = now
                        self._latched_mtc_frame = current_mtc_frame
                        self._send_full_frame(current_mtc_frame, fps, mtc_speed_fps, now)
                        # Prime decoders immediately with a complete quarter-frame cycle.
                        for qf_type in range(8):
                            data1 = self._quarter_frame_data(self._latched_mtc_frame, fps, mtc_speed_fps, qf_type)
                            self._midi.send_short(0xF1, data1, 0)
                        self._qf_index = 0
                        self._last_source_frame = current_source_frame
                        self._last_mtc_frame = current_mtc_frame
                        self._has_sent = True
                        self._next_send_t = now + interval
                        self._last_motion_t = now
                    if now < self._next_send_t:
                        sleep_s = min(0.002, max(0.0004, self._next_send_t - now))
                    else:
                        allow_dark_on_idle = str(self.idle_behavior_provider()) == MTC_IDLE_ALLOW_DARK
                        dark_idle = (
                            allow_dark_on_idle
                            and self._has_sent
                            and current_mtc_frame == self._last_mtc_frame
                            and (now - self._last_motion_t) >= self._dark_idle_grace_s
                        )
                        if dark_idle:
                            self._next_send_t = now + interval
                            self._last_source_frame = current_source_frame
                            sleep_s = 0.001
                        else:
                            if self._qf_index == 0:
                                self._latched_mtc_frame = current_mtc_frame
                            data1 = self._quarter_frame_data(self._latched_mtc_frame, fps, mtc_speed_fps, self._qf_index)
                            self._midi.send_short(0xF1, data1, 0)
                            self._qf_index = (self._qf_index + 1) % 8
                            self._last_source_frame = current_source_frame
                            self._last_mtc_frame = current_mtc_frame
                            self._has_sent = True
                            self._next_send_t += interval
                            if self._next_send_t < now - interval:
                                self._next_send_t = now + interval
                            if (now - self._last_full_frame_t) >= 1.0:
                                self._send_full_frame(current_mtc_frame, fps, mtc_speed_fps, now)
                            sleep_s = 0.0007
            time.sleep(sleep_s)


def nominal_fps(display_fps: float) -> int:
    fps = float(display_fps or 30.0)
    if abs(fps - 23.976) < 0.01:
        return 24
    if abs(fps - 29.97) < 0.01:
        return 30
    if abs(fps - 59.94) < 0.01:
        return 60
    return max(1, int(round(fps)))


def frame_to_timecode_parts(frame_number: int, fps: int) -> tuple[int, int, int, int]:
    fps = max(1, int(fps))
    frame_number = max(0, int(frame_number))
    total_frames_day = 24 * 60 * 60 * fps
    frame_number %= total_frames_day
    frames = frame_number % fps
    total_seconds = frame_number // fps
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = (total_minutes // 60) % 24
    return hours, minutes, seconds, frames


def frame_to_timecode_string(frame_number: int, fps: int) -> str:
    hours, minutes, seconds, frames = frame_to_timecode_parts(frame_number, fps)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def ms_to_timecode_string(position_ms: int, display_fps: float) -> str:
    fps = max(1.0, float(display_fps or 30.0))
    frame_number = int((max(0, int(position_ms)) / 1000.0) * fps)
    return frame_to_timecode_string(frame_number, nominal_fps(fps))
