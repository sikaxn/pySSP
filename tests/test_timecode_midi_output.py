from __future__ import annotations

import ctypes
import numpy as np

from pyssp import timecode


def test_ltc_callback_matches_bitstream_across_output_buffers():
    sender = timecode.LtcAudioOutput()
    sender._stream = object()
    sender._enabled = True
    sender._samples_per_half_bit = 2
    sender._samples_per_bit = 4
    sender.update(12, 30.0, running=False)

    expected = []
    signal = 1
    for bit in timecode.encode_ltc_bits(12, 30):
        signal *= -1
        expected.extend([signal * sender._amplitude] * 2)
        if bit:
            signal *= -1
        expected.extend([signal * sender._amplitude] * 2)

    chunks = []
    for frames in (97, 123, 100):
        out = np.empty((frames, 1), dtype=np.int16)
        sender._audio_callback(out, frames, None, None)
        chunks.extend(out[:, 0].tolist())
    assert chunks == expected


def test_ltc_and_mtc_anchor_can_freeze_during_ui_stall(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(timecode, "perf_counter", lambda: now[0])
    sender = timecode.LtcAudioOutput()
    sender._stream = object()
    sender._enabled = True
    sender.update(10, 30.0, running=True)
    now[0] += 0.11
    out = np.empty((1, 1), dtype=np.int16)
    sender._audio_callback(out, 1, None, None)
    assert sender._current_bits == timecode.encode_ltc_bits(13, 30)

    sender.update(10, 30.0, running=False)
    sender.request_resync()
    now[0] += 0.5
    sender._audio_callback(out, 1, None, None)
    assert sender._current_bits == timecode.encode_ltc_bits(10, 30)

    mtc = timecode.MtcMidiOutput()
    try:
        mtc.update(10, 30.0, 30.0, running=False)
        assert mtc._source_running is False
    finally:
        mtc.shutdown()


class _FakePygameMidi:
    def __init__(self) -> None:
        self.initialized = False
        self.opened_output = None
        self.short_messages = []
        self.long_messages = []

    def init(self) -> None:
        self.initialized = True

    def get_count(self) -> int:
        return 3

    def get_device_info(self, idx: int):
        devices = [
            (b"CoreMIDI", b"Launchpad X LPX MIDI Out", 1, 0, 0),
            (b"CoreMIDI", b"Launchpad X LPX MIDI In", 0, 1, 0),
            (b"CoreMIDI", b"Other MIDI In", 0, 1, 0),
        ]
        return devices[idx]

    def time(self) -> int:
        return 123

    def Output(self, device_id: int):
        self.opened_output = _FakePygameOutput(self, device_id)
        return self.opened_output


class _FakePygameOutput:
    def __init__(self, backend: _FakePygameMidi, device_id: int) -> None:
        self.backend = backend
        self.device_id = device_id
        self.closed = False

    def write_short(self, status: int, data1: int, data2: int) -> None:
        self.backend.short_messages.append((self.device_id, status, data1, data2))

    def write_sys_ex(self, when: int, payload: bytes) -> None:
        self.backend.long_messages.append((self.device_id, when, bytes(payload)))

    def close(self) -> None:
        self.closed = True


def test_midi_output_uses_pygame_backend_when_winmm_is_unavailable(monkeypatch) -> None:
    fake = _FakePygameMidi()
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()), raising=False)
    monkeypatch.setattr(timecode, "pg_midi", fake)
    monkeypatch.setattr(timecode, "_PYGAME_MIDI_READY", False)

    midi = timecode.MidiOutput()

    assert midi.available() is True
    assert midi.list_devices() == [("1", "Launchpad X LPX MIDI In"), ("2", "Other MIDI In")]
    assert midi.open(1) is True

    midi.send_short(0xF1, 0x7F, 0)
    midi.send_long(bytes([0xF0, 0x7E, 0xF7]))
    midi.close()

    assert fake.short_messages == [(1, 0xF1, 0x7F, 0)]
    assert fake.long_messages == [(1, 123, bytes([0xF0, 0x7E, 0xF7]))]
    assert fake.opened_output.closed is True


def test_midi_output_prefers_coremidi_backend_for_prefixed_devices(monkeypatch) -> None:
    class _FakeCoreMidiOut:
        def __init__(self) -> None:
            self._opened = False
            self.short_messages = []
            self.long_messages = []
            created.append(self)

        def available(self) -> bool:
            return True

        def list_devices(self):
            return [("coremidi:0", "Launchpad X LPX MIDI In")]

        def open(self, device_id) -> bool:
            self._opened = str(device_id) == "coremidi:0"
            return self._opened

        def send_short(self, status: int, data1: int, data2: int) -> None:
            self.short_messages.append((status, data1, data2))

        def send_long(self, payload: bytes) -> None:
            self.long_messages.append(bytes(payload))

        def close(self) -> None:
            self._opened = False

    created = []
    monkeypatch.setattr(timecode, "_CoreMidiOut", _FakeCoreMidiOut)
    midi = timecode.MidiOutput()

    assert midi.list_devices() == [("coremidi:0", "Launchpad X LPX MIDI In")]
    assert midi.open("coremidi:0") is True
    midi.send_short(0xF1, 0x01, 0)
    midi.send_long(bytes([0xF0, 0x7E, 0xF7]))
    midi.close()

    core = created[0]
    assert core.short_messages == [(0xF1, 0x01, 0)]
    assert core.long_messages == [bytes([0xF0, 0x7E, 0xF7])]
    assert core._opened is False
