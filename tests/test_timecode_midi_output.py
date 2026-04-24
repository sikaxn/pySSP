from __future__ import annotations

import ctypes

from pyssp import timecode


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
