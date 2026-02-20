from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import time
from typing import Callable, Dict, List, Optional, Tuple

try:
    import pygame.midi as pg_midi
except Exception:  # pragma: no cover - dependency/runtime fallback
    pg_midi = None


_MIDI_INIT_LOCK = Lock()
_MIDI_READY = False
_MIDI_NAME_SELECTOR_PREFIX = "name::"
_MIDI_BINDING_DEVICE_SEPARATOR = "|"


def _ensure_midi_init() -> bool:
    global _MIDI_READY
    if pg_midi is None:
        return False
    with _MIDI_INIT_LOCK:
        if _MIDI_READY:
            return True
        try:
            pg_midi.init()
            _MIDI_READY = True
        except Exception:
            _MIDI_READY = False
    return _MIDI_READY


def _refresh_midi_backend() -> bool:
    global _MIDI_READY
    if pg_midi is None:
        return False
    with _MIDI_INIT_LOCK:
        try:
            if _MIDI_READY:
                pg_midi.quit()
        except Exception:
            pass
        _MIDI_READY = False
        try:
            pg_midi.init()
            _MIDI_READY = True
        except Exception:
            _MIDI_READY = False
    return _MIDI_READY


@dataclass(frozen=True)
class MidiInputDevice:
    device_id: str
    name: str


def midi_input_name_selector(device_name: str) -> str:
    return f"{_MIDI_NAME_SELECTOR_PREFIX}{str(device_name or '').strip()}"


def midi_input_selector_name(selector: str) -> str:
    raw = str(selector or "").strip()
    if not raw:
        return ""
    if raw.startswith(_MIDI_NAME_SELECTOR_PREFIX):
        return raw[len(_MIDI_NAME_SELECTOR_PREFIX):].strip()
    return ""


def list_midi_input_devices(force_refresh: bool = False) -> List[Tuple[str, str]]:
    # Avoid backend quit/re-init while devices may be actively polled; this can crash pygame.midi
    # on some systems. Keep refresh semantics as a lightweight re-enumeration.
    _ = bool(force_refresh)
    ready = _ensure_midi_init()
    if not ready:
        return []
    devices: List[Tuple[str, str]] = []
    try:
        count = int(pg_midi.get_count())
    except Exception:
        return []
    for idx in range(max(0, count)):
        try:
            info = pg_midi.get_device_info(idx)
        except Exception:
            continue
        if not info or len(info) < 5:
            continue
        is_input = int(info[2]) == 1
        if not is_input:
            continue
        name = bytes(info[1]).decode(errors="ignore").strip() if isinstance(info[1], (bytes, bytearray)) else str(info[1])
        devices.append((str(idx), name or f"MIDI Input {idx}"))
    return devices


def normalize_midi_binding(value: str) -> str:
    raw_full = str(value or "").strip()
    if not raw_full:
        return ""
    selector = ""
    raw = raw_full
    if _MIDI_BINDING_DEVICE_SEPARATOR in raw_full:
        left, right = raw_full.split(_MIDI_BINDING_DEVICE_SEPARATOR, 1)
        left = str(left).strip()
        right = str(right).strip()
        if right:
            selector = left
            raw = right
    raw = raw.upper()
    if not raw:
        return ""
    parts = [part.strip() for part in raw.split(":") if part.strip()]
    if not parts:
        return ""
    normalized_parts: List[str] = []
    for part in parts[:3]:
        try:
            n = int(part, 16)
        except ValueError:
            return ""
        if n < 0 or n > 255:
            return ""
        normalized_parts.append(f"{n:02X}")
    token = ":".join(normalized_parts)
    if not selector:
        return token
    return f"{selector}{_MIDI_BINDING_DEVICE_SEPARATOR}{token}"


def split_midi_binding(value: str) -> Tuple[str, str]:
    normalized = normalize_midi_binding(value)
    if not normalized:
        return "", ""
    if _MIDI_BINDING_DEVICE_SEPARATOR in normalized:
        selector, token = normalized.split(_MIDI_BINDING_DEVICE_SEPARATOR, 1)
        return str(selector).strip(), str(token).strip()
    return "", normalized


def midi_event_to_binding(status: int, data1: int, data2: int) -> str:
    status = int(status) & 0xFF
    data1 = int(data1) & 0xFF
    data2 = int(data2) & 0xFF
    if status < 0x80:
        return ""
    # Only listen to key-down style events:
    # Note On (0x9n) with velocity > 0.
    if (status & 0xF0) == 0x90 and data2 > 0:
        return f"{status:02X}:{data1:02X}"
    return ""


def midi_binding_to_display(binding: str) -> str:
    selector, token = split_midi_binding(binding)
    if not token:
        return ""
    parts = token.split(":")
    try:
        status = int(parts[0], 16)
    except ValueError:
        return token
    if len(parts) >= 2:
        value = int(parts[1], 16)
        high = status & 0xF0
        channel = (status & 0x0F) + 1
        if high == 0x90:
            return f"Note On ch{channel} #{value}"
        if high == 0x80:
            return f"Note Off ch{channel} #{value}"
        if high == 0xB0:
            return f"CC ch{channel} #{value}"
        if high == 0xC0:
            return f"Program ch{channel} #{value}"
        base = token
        return f"[{selector}] {base}" if selector else base
    if status >= 0xF0:
        base = f"System {token}"
        return f"[{selector}] {base}" if selector else base
    return f"[{selector}] {token}" if selector else token


class MidiInputRouter:
    def __init__(self, callback: Optional[Callable[[str, str, int, int, int], None]] = None) -> None:
        self._callback = callback
        self._inputs: Dict[str, object] = {}
        self._selected_device_ids: List[str] = []
        self._selector_name_hints: Dict[str, str] = {}
        self._last_resync_t = 0.0
        self._resolved_names_by_id: Dict[str, str] = {}

    def set_callback(self, callback: Optional[Callable[[str, str, int, int, int], None]]) -> None:
        self._callback = callback

    def set_devices(self, device_ids: List[str], force_refresh: bool = False) -> None:
        wanted = []
        seen_wanted: set[str] = set()
        for raw in device_ids:
            token = str(raw).strip()
            if (not token) or (token in seen_wanted):
                continue
            seen_wanted.add(token)
            wanted.append(token)
        wanted_concrete = self._resolve_device_ids(wanted, force_refresh=force_refresh)
        wanted_set = set(wanted_concrete)
        for device_id in list(self._inputs.keys()):
            if device_id in wanted_set:
                continue
            self._close_input(device_id)
        for device_id in wanted_concrete:
            if device_id in self._inputs:
                continue
            self._open_input(device_id)
        self._selected_device_ids = wanted

    def selected_device_ids(self) -> List[str]:
        return list(self._selected_device_ids)

    def poll(self, max_events_per_device: int = 64) -> None:
        callback = self._callback
        if callback is None:
            return
        # If selection exists but no active devices, periodically resync from current hardware.
        if self._selected_device_ids and not self._inputs:
            now = time.perf_counter()
            if (now - self._last_resync_t) >= 0.75:
                self._last_resync_t = now
                self._resync_selected_devices(force_refresh=False)
        for device_id, inp in list(self._inputs.items()):
            try:
                # Using read() directly avoids pygame.midi poll() crashes observed on
                # some hotplug/driver states. read() is non-blocking and returns [] when idle.
                events = inp.read(max(1, int(max_events_per_device)))
                if not events:
                    continue
            except Exception:
                self._close_input(device_id)
                self._resync_selected_devices(force_refresh=False)
                continue
            for event in events:
                if not event or len(event) < 1:
                    continue
                data = event[0]
                if not data or len(data) < 3:
                    continue
                status = int(data[0]) & 0xFF
                data1 = int(data[1]) & 0xFF
                data2 = int(data[2]) & 0xFF
                token = midi_event_to_binding(status, data1, data2)
                device_name = str(self._resolved_names_by_id.get(device_id, "")).strip()
                selector = midi_input_name_selector(device_name) if device_name else ""
                print(
                    f"[MIDI] device={device_name or device_id} selector={selector or '<none>'} raw={status:02X}:{data1:02X}:{data2:02X} binding={token or '<none>'}",
                    flush=True,
                )
                callback(token, selector, status, data1, data2)

    def close(self) -> None:
        for device_id in list(self._inputs.keys()):
            self._close_input(device_id)
        self._selected_device_ids = []

    def clear_pending(self, max_reads_per_device: int = 8, max_events_per_read: int = 128) -> None:
        for _device_id, inp in list(self._inputs.items()):
            for _ in range(max(1, int(max_reads_per_device))):
                try:
                    events = inp.read(max(1, int(max_events_per_read)))
                except Exception:
                    break
                if not events:
                    break

    def _resolve_device_ids(self, selectors: List[str], force_refresh: bool = False) -> List[str]:
        listed = list_midi_input_devices(force_refresh=force_refresh)
        by_id: Dict[str, str] = {}
        by_name: Dict[str, List[str]] = {}
        for device_id, device_name in listed:
            did = str(device_id).strip()
            dname = str(device_name).strip()
            if not did:
                continue
            by_id[did] = dname
            by_name.setdefault(dname, []).append(did)
        self._resolved_names_by_id = dict(by_id)

        resolved: List[str] = []
        seen: set[str] = set()
        for selector in selectors:
            token = str(selector).strip()
            if not token:
                continue
            name_token = midi_input_selector_name(token)
            concrete: List[str] = []
            if name_token:
                concrete = list(by_name.get(name_token, []))
            elif token in by_id:
                concrete = [token]
            elif token in by_name:
                concrete = list(by_name.get(token, []))
            elif token.isdigit():
                hinted_name = str(self._selector_name_hints.get(token, "")).strip()
                if hinted_name:
                    concrete = list(by_name.get(hinted_name, []))
            for device_id in concrete:
                if device_id in seen:
                    continue
                seen.add(device_id)
                resolved.append(device_id)
                name = str(by_id.get(device_id, "")).strip()
                if name and token.isdigit():
                    self._selector_name_hints[token] = name
        return resolved

    def _resync_selected_devices(self, force_refresh: bool = False) -> None:
        try:
            self.set_devices(self._selected_device_ids, force_refresh=force_refresh)
        except Exception:
            pass

    def _open_input(self, device_id: str) -> None:
        if not _ensure_midi_init():
            return
        try:
            inp = pg_midi.Input(int(device_id))
        except Exception:
            return
        self._inputs[device_id] = inp

    def _close_input(self, device_id: str) -> None:
        inp = self._inputs.pop(device_id, None)
        if inp is None:
            return
        try:
            inp.close()
        except Exception:
            pass
