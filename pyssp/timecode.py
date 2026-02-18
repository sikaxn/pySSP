from __future__ import annotations

import ctypes
from ctypes import wintypes
from time import perf_counter
from typing import Callable, List, Optional, Tuple

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

    def close(self) -> None:
        if not self._opened or not self._winmm:
            return
        self._winmm.midiOutReset(self._handle)
        self._winmm.midiOutClose(self._handle)
        self._opened = False


def list_midi_output_devices() -> List[Tuple[str, str]]:
    midi = WinMMMidiOut()
    return midi.list_devices() if midi.available() else []


class MtcMidiOutput:
    def __init__(self, idle_behavior_provider: Optional[Callable[[], str]] = None) -> None:
        self.idle_behavior_provider = idle_behavior_provider or (lambda: MTC_IDLE_KEEP_STREAM)
        self._midi = WinMMMidiOut()
        self._device = MIDI_OUTPUT_DEVICE_NONE
        self._opened = False
        self._qf_index = 0
        self._next_send_t = perf_counter()
        self._last_source_frame = 0
        self._last_mtc_frame = 0
        self._has_sent = False
        self._latched_mtc_frame = 0

    def set_device(self, device_id: str) -> None:
        target = str(device_id or MIDI_OUTPUT_DEVICE_NONE)
        if target == self._device:
            return
        self.stop()
        self._device = target
        if self._device == MIDI_OUTPUT_DEVICE_NONE:
            return
        if not self._midi.available():
            return
        try:
            self._opened = self._midi.open(int(self._device))
        except (TypeError, ValueError):
            self._opened = False
        self._qf_index = 0
        self._next_send_t = perf_counter()
        self._last_source_frame = 0
        self._last_mtc_frame = 0
        self._has_sent = False
        self._latched_mtc_frame = 0

    def stop(self) -> None:
        self._midi.close()
        self._opened = False
        self._device = MIDI_OUTPUT_DEVICE_NONE
        self._qf_index = 0
        self._has_sent = False

    def request_resync(self) -> None:
        # Force next update cycle to restart quarter-frame cadence immediately.
        self._qf_index = 0
        self._has_sent = False
        self._next_send_t = 0.0

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

    def update(self, current_frame: int, source_fps: float, mtc_fps: float) -> None:
        if not self._opened:
            return
        now = perf_counter()
        source_fps = max(0.001, float(source_fps))
        mtc_speed_fps = self._coerce_mtc_speed_fps(float(mtc_fps))
        fps = self._nominal_mtc_fps(mtc_speed_fps)
        current_source_frame = max(0, int(current_frame))
        current_mtc_frame = int(((current_source_frame * mtc_speed_fps) / source_fps) + 1e-6)
        interval = 1.0 / (mtc_speed_fps * 4.0)
        if now < self._next_send_t:
            return

        allow_dark_on_idle = str(self.idle_behavior_provider()) == MTC_IDLE_ALLOW_DARK
        if allow_dark_on_idle and self._has_sent and current_mtc_frame == self._last_mtc_frame:
            self._next_send_t = now + interval
            self._last_source_frame = current_source_frame
            return

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
