from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import re
import time
from typing import Dict, List, Optional, Tuple

try:
    import pygame
except Exception:  # pragma: no cover - runtime fallback
    pygame = None

try:
    from PyQt5.QtCore import QThread, pyqtSignal
except Exception:  # pragma: no cover - allow non-GUI imports
    class _FallbackSignal:
        def connect(self, *_args, **_kwargs) -> None:
            return None

        def emit(self, *_args, **_kwargs) -> None:
            return None

    class QThread:  # type: ignore[override]
        def __init__(self, parent=None) -> None:
            _ = parent

    def pyqtSignal(*_args, **_kwargs):  # type: ignore[misc]
        return _FallbackSignal()


_JOY_INIT_LOCK = Lock()
_JOY_READY = False
_JOY_NAME_SELECTOR_PREFIX = "name::"
_JOY_EVENT_RE = re.compile(r"^GC(\d+):(BTN(\d+)|AXIS(\d+)([+-])|HAT(\d+):(UP|DOWN|LEFT|RIGHT))$")


@dataclass(frozen=True)
class GameControllerDevice:
    selector: str
    name: str
    ordinal: int


def _ensure_joystick_init() -> bool:
    global _JOY_READY
    if pygame is None:
        return False
    with _JOY_INIT_LOCK:
        if _JOY_READY:
            return True
        try:
            if not pygame.get_init():
                pygame.init()
            pygame.joystick.init()
            _JOY_READY = True
        except Exception:
            _JOY_READY = False
    return _JOY_READY


def _refresh_joystick_backend() -> bool:
    global _JOY_READY
    if pygame is None:
        return False
    with _JOY_INIT_LOCK:
        try:
            if pygame.joystick.get_init():
                pygame.joystick.quit()
        except Exception:
            pass
        try:
            if not pygame.get_init():
                pygame.init()
            pygame.joystick.init()
            _JOY_READY = True
        except Exception:
            _JOY_READY = False
    return _JOY_READY


def game_controller_name_selector(device_name: str, ordinal: int) -> str:
    return f"{_JOY_NAME_SELECTOR_PREFIX}{str(device_name or '').strip()}::{max(0, int(ordinal))}"


def game_controller_selector_parts(selector: str) -> tuple[str, int]:
    raw = str(selector or "").strip()
    if not raw.startswith(_JOY_NAME_SELECTOR_PREFIX):
        return "", -1
    payload = raw[len(_JOY_NAME_SELECTOR_PREFIX):]
    name, sep, ordinal_text = payload.rpartition("::")
    if not sep:
        return payload.strip(), 0
    try:
        ordinal = int(ordinal_text)
    except ValueError:
        ordinal = 0
    return name.strip(), max(0, ordinal)


def list_game_controller_devices(force_refresh: bool = False) -> List[GameControllerDevice]:
    ready = _refresh_joystick_backend() if force_refresh else _ensure_joystick_init()
    if not ready:
        return []
    try:
        pygame.event.pump()
    except Exception:
        pass
    devices: List[GameControllerDevice] = []
    name_counts: Dict[str, int] = {}
    try:
        count = int(pygame.joystick.get_count())
    except Exception:
        return []
    for index in range(max(0, count)):
        try:
            joy = pygame.joystick.Joystick(index)
            if not joy.get_init():
                joy.init()
            name = str(joy.get_name() or f"Controller {index}").strip()
        except Exception:
            continue
        ordinal = int(name_counts.get(name, 0))
        name_counts[name] = ordinal + 1
        devices.append(
            GameControllerDevice(
                selector=game_controller_name_selector(name, ordinal),
                name=name,
                ordinal=ordinal,
            )
        )
    return devices


def normalize_game_controller_binding(value: str) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    match = _JOY_EVENT_RE.fullmatch(raw)
    if not match:
        return ""
    controller_index = max(0, int(match.group(1)))
    button = match.group(3)
    axis = match.group(4)
    axis_dir = match.group(5)
    hat = match.group(6)
    hat_dir = match.group(7)
    if button is not None:
        return f"GC{controller_index}:BTN{max(0, int(button))}"
    if axis is not None and axis_dir in {"+", "-"}:
        return f"GC{controller_index}:AXIS{max(0, int(axis))}{axis_dir}"
    if hat is not None and hat_dir in {"UP", "DOWN", "LEFT", "RIGHT"}:
        return f"GC{controller_index}:HAT{max(0, int(hat))}:{hat_dir}"
    return ""


def game_controller_binding_to_display(binding: str) -> str:
    normalized = normalize_game_controller_binding(binding)
    if not normalized:
        return ""
    match = _JOY_EVENT_RE.fullmatch(normalized)
    if match is None:
        return normalized
    controller_index = int(match.group(1))
    button = match.group(3)
    axis = match.group(4)
    axis_dir = match.group(5)
    hat = match.group(6)
    hat_dir = match.group(7)
    if button is not None:
        return f"Controller {controller_index} Button {int(button)}"
    if axis is not None and axis_dir:
        direction = "Positive" if axis_dir == "+" else "Negative"
        return f"Controller {controller_index} Axis {int(axis)} {direction}"
    if hat is not None and hat_dir:
        return f"Controller {controller_index} Hat {int(hat)} {hat_dir.title()}"
    return normalized


class GameControllerPollingThread(QThread):
    controller_event = pyqtSignal(str, int, str)
    status_changed = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._state_lock = Lock()
        self._running = True
        self._device_selectors: List[str] = []
        self._axis_threshold = 0.5
        self._last_states: Dict[tuple[int, str], int] = {}
        self._last_status_signature: tuple[str, ...] = ()
        self._last_force_refresh_t = 0.0

    def update_config(self, device_selectors: List[str], axis_threshold: float) -> None:
        with self._state_lock:
            self._device_selectors = [str(v).strip() for v in list(device_selectors or []) if str(v).strip()]
            self._axis_threshold = max(0.05, min(0.99, float(axis_threshold)))

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            with self._state_lock:
                selectors = list(self._device_selectors)
                axis_threshold = float(self._axis_threshold)
            missing: List[str] = []
            if selectors:
                missing = self._poll_selected_devices(selectors, axis_threshold)
            if tuple(missing) != self._last_status_signature:
                self._last_status_signature = tuple(missing)
                self.status_changed.emit(list(missing))
            if selectors and (time.perf_counter() - self._last_force_refresh_t) >= 5.0:
                self._last_force_refresh_t = time.perf_counter()
                try:
                    _refresh_joystick_backend()
                except Exception:
                    pass
            time.sleep(0.01)

    def _poll_selected_devices(self, selectors: List[str], axis_threshold: float) -> List[str]:
        devices = list_game_controller_devices(force_refresh=False)
        by_selector = {device.selector: device for device in devices}
        missing: List[str] = []
        for controller_index, selector in enumerate(selectors):
            device = by_selector.get(selector)
            if device is None:
                missing.append(selector)
                continue
            try:
                devices_now = list_game_controller_devices(force_refresh=False)
                current = next((item for item in devices_now if item.selector == selector), None)
                if current is None:
                    missing.append(selector)
                    continue
                joy_index = next(
                    (idx for idx, item in enumerate(devices_now) if item.selector == selector),
                    -1,
                )
                if joy_index < 0:
                    missing.append(selector)
                    continue
                self._poll_joystick(joy_index, controller_index, selector, axis_threshold)
            except Exception:
                missing.append(selector)
        return missing

    def _poll_joystick(self, joy_index: int, controller_index: int, selector: str, axis_threshold: float) -> None:
        if not _ensure_joystick_init():
            return
        try:
            pygame.event.pump()
        except Exception:
            pass
        joy = pygame.joystick.Joystick(int(joy_index))
        if not joy.get_init():
            joy.init()
        instance_id = int(joy.get_instance_id()) if hasattr(joy, "get_instance_id") else int(joy_index)
        for button_index in range(max(0, int(joy.get_numbuttons()))):
            try:
                pressed = 1 if bool(joy.get_button(button_index)) else 0
            except Exception:
                pressed = 0
            state_key = (instance_id, f"BTN{button_index}")
            previous = int(self._last_states.get(state_key, 0))
            self._last_states[state_key] = pressed
            if pressed and not previous:
                self.controller_event.emit(
                    f"GC{controller_index}:BTN{button_index}",
                    int(controller_index),
                    str(selector),
                )
        for axis_index in range(max(0, int(joy.get_numaxes()))):
            try:
                axis_value = float(joy.get_axis(axis_index))
            except Exception:
                axis_value = 0.0
            state = 1 if axis_value >= axis_threshold else (-1 if axis_value <= (-axis_threshold) else 0)
            state_key = (instance_id, f"AXIS{axis_index}")
            previous = int(self._last_states.get(state_key, 0))
            self._last_states[state_key] = state
            if state == previous or state == 0:
                continue
            suffix = "+" if state > 0 else "-"
            self.controller_event.emit(
                f"GC{controller_index}:AXIS{axis_index}{suffix}",
                int(controller_index),
                str(selector),
            )
        for hat_index in range(max(0, int(joy.get_numhats()))):
            try:
                hat_x, hat_y = joy.get_hat(hat_index)
            except Exception:
                hat_x, hat_y = (0, 0)
            directions = {
                "UP": 1 if hat_y > 0 else 0,
                "DOWN": 1 if hat_y < 0 else 0,
                "LEFT": 1 if hat_x < 0 else 0,
                "RIGHT": 1 if hat_x > 0 else 0,
            }
            for direction, active in directions.items():
                state_key = (instance_id, f"HAT{hat_index}:{direction}")
                previous = int(self._last_states.get(state_key, 0))
                self._last_states[state_key] = active
                if active and not previous:
                    self.controller_event.emit(
                        f"GC{controller_index}:HAT{hat_index}:{direction}",
                        int(controller_index),
                        str(selector),
                    )
