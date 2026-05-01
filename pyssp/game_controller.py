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
    import pygame._sdl2.controller as pygame_controller
except Exception:  # pragma: no cover - runtime fallback
    try:
        import pygame.controller as pygame_controller  # type: ignore[no-redef]
    except Exception:  # pragma: no cover - runtime fallback
        pygame_controller = None

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
_CONTROLLER_OBJECTS: Dict[int, object] = {}
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
            _ensure_controller_backend()
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
            _ensure_controller_backend(force_reset=True)
            _JOY_READY = True
        except Exception:
            _JOY_READY = False
    return _JOY_READY


def _ensure_controller_backend(force_reset: bool = False) -> None:
    if pygame_controller is None:
        return
    try:
        if force_reset:
            quit_fn = getattr(pygame_controller, "quit", None)
            if callable(quit_fn):
                quit_fn()
            _CONTROLLER_OBJECTS.clear()
    except Exception:
        pass
    try:
        init_fn = getattr(pygame_controller, "init", None)
        if callable(init_fn):
            init_fn()
    except Exception:
        pass


def _ensure_controller_open(joy_index: int) -> Optional[object]:
    if pygame_controller is None:
        return None
    joy_index = int(joy_index)
    existing = _CONTROLLER_OBJECTS.get(joy_index)
    if existing is not None:
        return existing
    controller_cls = getattr(pygame_controller, "Controller", None)
    if controller_cls is None:
        return None
    controller = None
    try:
        controller = controller_cls(joy_index)
    except Exception:
        controller = None
    if controller is None:
        factory = getattr(controller_cls, "from_joystick", None)
        if callable(factory):
            try:
                controller = factory(joy_index)
            except Exception:
                controller = None
    if controller is None:
        return None
    try:
        init_fn = getattr(controller, "init", None)
        if callable(init_fn):
            init_fn()
    except Exception:
        pass
    try:
        open_fn = getattr(controller, "open", None)
        if callable(open_fn):
            open_fn()
    except Exception:
        pass
    _CONTROLLER_OBJECTS[joy_index] = controller
    return controller


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


def prime_game_controller_states(
    selectors: List[str],
    axis_threshold: float,
) -> Dict[tuple[int, str], int]:
    normalized_selectors = [str(v).strip() for v in list(selectors or []) if str(v).strip()]
    states: Dict[tuple[int, str], int] = {}
    if not normalized_selectors:
        return states
    if not _ensure_joystick_init():
        return states
    try:
        pygame.event.pump()
    except Exception:
        pass
    devices = list_game_controller_devices(force_refresh=False)
    by_selector = {device.selector: index for index, device in enumerate(devices)}
    threshold = max(0.05, min(0.99, float(axis_threshold)))
    _drain_game_controller_events()
    for selector in normalized_selectors:
        joy_index = int(by_selector.get(selector, -1))
        if joy_index < 0:
            continue
        _snapshot_controller_states(selector, joy_index, threshold, states)
        _snapshot_joystick_states(joy_index, threshold, states)
    return states


def poll_game_controller_binding(
    selectors: List[str],
    axis_threshold: float,
    last_states: Optional[Dict[tuple[int, str], int]] = None,
    debug_prefix: str = "",
    debug_flags: Optional[Dict[str, bool]] = None,
    capture_axis: bool = True,
) -> Optional[Tuple[str, int, str]]:
    normalized_selectors = [str(v).strip() for v in list(selectors or []) if str(v).strip()]
    flags = debug_flags if isinstance(debug_flags, dict) else {}
    if not normalized_selectors:
        if debug_prefix and not flags.get("no_selectors"):
            print(f"{debug_prefix} no selected controllers to watch")
            flags["no_selectors"] = True
        return None
    ready = _ensure_joystick_init()
    if not ready:
        if debug_prefix and not flags.get("backend_unavailable"):
            print(f"{debug_prefix} pygame joystick backend unavailable")
            flags["backend_unavailable"] = True
        return None
    try:
        pygame.event.pump()
    except Exception:
        pass
    devices = list_game_controller_devices(force_refresh=False)
    if debug_prefix and not flags.get("devices_listed"):
        listed = [f"{index}:{device.name} [{device.selector}]" for index, device in enumerate(devices)]
        print(f"{debug_prefix} visible devices={listed}")
        print(f"{debug_prefix} watching selectors={normalized_selectors} threshold={max(0.05, min(0.99, float(axis_threshold))):.2f}")
        flags["devices_listed"] = True
    by_selector = {device.selector: index for index, device in enumerate(devices)}
    states = last_states if isinstance(last_states, dict) else {}
    threshold = max(0.05, min(0.99, float(axis_threshold)))
    event_result = _poll_game_controller_events(
        normalized_selectors,
        by_selector,
        threshold,
        states,
        debug_prefix=debug_prefix,
        capture_axis=capture_axis,
    )
    if event_result is not None:
        if debug_prefix:
            print(f"{debug_prefix} detected event token={event_result[0]} selector={event_result[2]}")
        return event_result
    for controller_index, selector in enumerate(normalized_selectors):
        joy_index = int(by_selector.get(selector, -1))
        if joy_index < 0:
            if debug_prefix and not flags.get(f"missing::{selector}"):
                print(f"{debug_prefix} selected controller missing: {selector}")
                flags[f"missing::{selector}"] = True
            continue
        controller_obj = _ensure_controller_open(joy_index)
        if debug_prefix and controller_obj is not None and not flags.get(f"controller_open::{selector}"):
            print(f"{debug_prefix} controller backend opened selector={selector} joy_index={joy_index}")
            flags[f"controller_open::{selector}"] = True
        if debug_prefix:
            _debug_log_controller_snapshot(debug_prefix, joy_index, selector, flags)
            _debug_log_joystick_snapshot(debug_prefix, joy_index, selector, flags)
        event = _poll_controller_binding(
            selector,
            joy_index,
            controller_index,
            selector,
            threshold,
            states,
            capture_axis=capture_axis,
        )
        if event is not None:
            if debug_prefix:
                print(f"{debug_prefix} detected event token={event[0]} selector={event[2]}")
            return event
        event = _poll_joystick_binding(
            joy_index,
            controller_index,
            selector,
            threshold,
            states,
            capture_axis=capture_axis,
        )
        if event is not None:
            if debug_prefix:
                print(f"{debug_prefix} detected event token={event[0]} selector={event[2]}")
            return event
    return None


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
        selector_to_joy_index = {device.selector: index for index, device in enumerate(devices)}
        missing: List[str] = []
        event = _poll_game_controller_events(
            selectors,
            selector_to_joy_index,
            axis_threshold,
            self._last_states,
            capture_axis=True,
        )
        if event is not None:
            token, emitted_controller_index, emitted_selector = event
            self.controller_event.emit(token, emitted_controller_index, emitted_selector)
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
        event = _poll_controller_binding(
            selector,
            joy_index,
            controller_index,
            selector,
            axis_threshold,
            self._last_states,
        )
        if event is None:
            event = _poll_joystick_binding(joy_index, controller_index, selector, axis_threshold, self._last_states)
        if event is not None:
            token, emitted_controller_index, emitted_selector = event
            self.controller_event.emit(token, emitted_controller_index, emitted_selector)


def _poll_joystick_binding(
    joy_index: int,
    controller_index: int,
    selector: str,
    axis_threshold: float,
    state_store: Dict[tuple[int, str], int],
    capture_axis: bool = True,
) -> Optional[Tuple[str, int, str]]:
        if not _ensure_joystick_init():
            return None
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
            previous = int(state_store.get(state_key, 0))
            state_store[state_key] = pressed
            if pressed and not previous:
                return (f"GC{controller_index}:BTN{button_index}", int(controller_index), str(selector))
        for axis_index in range(max(0, int(joy.get_numaxes()))):
            try:
                axis_value = float(joy.get_axis(axis_index))
            except Exception:
                axis_value = 0.0
            state = 1 if axis_value >= axis_threshold else (-1 if axis_value <= (-axis_threshold) else 0)
            state_key = (instance_id, f"AXIS{axis_index}")
            previous = int(state_store.get(state_key, 0))
            state_store[state_key] = state
            if (not capture_axis) or state == previous or state == 0:
                continue
            suffix = "+" if state > 0 else "-"
            return (f"GC{controller_index}:AXIS{axis_index}{suffix}", int(controller_index), str(selector))
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
                previous = int(state_store.get(state_key, 0))
                state_store[state_key] = active
                if active and not previous:
                    return (f"GC{controller_index}:HAT{hat_index}:{direction}", int(controller_index), str(selector))
        return None


def _poll_controller_binding(
    selector_key: str,
    joy_index: int,
    controller_index: int,
    selector: str,
    axis_threshold: float,
    state_store: Dict[tuple[int, str], int],
    capture_axis: bool = True,
) -> Optional[Tuple[str, int, str]]:
    if not _ensure_joystick_init():
        return None
    try:
        pygame.event.pump()
    except Exception:
        pass
    controller = _ensure_controller_open(joy_index)
    if controller is None:
        return None
    source_key = _controller_state_source_key(selector_key)
    for button_index in _controller_button_indices(controller):
        try:
            pressed = 1 if bool(controller.get_button(int(button_index))) else 0
        except Exception:
            continue
        state_key = (source_key, f"BTN{int(button_index)}")
        previous = int(state_store.get(state_key, 0))
        state_store[state_key] = pressed
        if pressed and not previous:
            return (f"GC{controller_index}:BTN{int(button_index)}", int(controller_index), str(selector))
    for axis_index in _controller_axis_indices(controller):
        try:
            axis_value = _normalize_controller_axis_value(controller.get_axis(int(axis_index)))
        except Exception:
            continue
        state = 1 if axis_value >= axis_threshold else (-1 if axis_value <= (-axis_threshold) else 0)
        state_key = (source_key, f"AXIS{int(axis_index)}")
        previous = int(state_store.get(state_key, 0))
        state_store[state_key] = state
        if capture_axis and state != 0 and state != previous:
            suffix = "+" if state > 0 else "-"
            return (f"GC{controller_index}:AXIS{int(axis_index)}{suffix}", int(controller_index), str(selector))
    return None


def _snapshot_joystick_states(
    joy_index: int,
    axis_threshold: float,
    state_store: Dict[tuple[int, str], int],
) -> None:
    if not _ensure_joystick_init():
        return
    try:
        joy = pygame.joystick.Joystick(int(joy_index))
        if not joy.get_init():
            joy.init()
    except Exception:
        return
    instance_id = int(joy.get_instance_id()) if hasattr(joy, "get_instance_id") else int(joy_index)
    for button_index in range(max(0, int(joy.get_numbuttons()))):
        try:
            pressed = 1 if bool(joy.get_button(button_index)) else 0
        except Exception:
            pressed = 0
        state_store[(instance_id, f"BTN{button_index}")] = pressed
    for axis_index in range(max(0, int(joy.get_numaxes()))):
        try:
            axis_value = float(joy.get_axis(axis_index))
        except Exception:
            axis_value = 0.0
        state = 1 if axis_value >= axis_threshold else (-1 if axis_value <= (-axis_threshold) else 0)
        state_store[(instance_id, f"AXIS{axis_index}")] = state
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
            state_store[(instance_id, f"HAT{hat_index}:{direction}")] = active


def _snapshot_controller_states(
    selector_key: str,
    joy_index: int,
    axis_threshold: float,
    state_store: Dict[tuple[int, str], int],
) -> None:
    if not _ensure_joystick_init():
        return
    try:
        pygame.event.pump()
    except Exception:
        pass
    controller = _ensure_controller_open(joy_index)
    if controller is None:
        return
    source_key = _controller_state_source_key(selector_key)
    for button_index in _controller_button_indices(controller):
        try:
            pressed = 1 if bool(controller.get_button(int(button_index))) else 0
        except Exception:
            continue
        state_store[(source_key, f"BTN{int(button_index)}")] = pressed
    for axis_index in _controller_axis_indices(controller):
        try:
            axis_value = _normalize_controller_axis_value(controller.get_axis(int(axis_index)))
        except Exception:
            continue
        state = 1 if axis_value >= axis_threshold else (-1 if axis_value <= (-axis_threshold) else 0)
        state_store[(source_key, f"AXIS{int(axis_index)}")] = state


def _drain_game_controller_events() -> None:
    if pygame is None:
        return
    try:
        pygame.event.get()
    except Exception:
        pass


def _poll_game_controller_events(
    selectors: List[str],
    selector_to_joy_index: Dict[str, int],
    axis_threshold: float,
    state_store: Dict[tuple[int, str], int],
    debug_prefix: str = "",
    capture_axis: bool = True,
) -> Optional[Tuple[str, int, str]]:
    if pygame is None:
        return None
    try:
        events = pygame.event.get()
    except Exception:
        return None
    selected_by_instance_id: Dict[int, Tuple[int, str]] = {}
    selected_by_joy_id: Dict[int, Tuple[int, str]] = {}
    for controller_index, selector in enumerate(selectors):
        joy_index = int(selector_to_joy_index.get(selector, -1))
        if joy_index < 0:
            continue
        try:
            joy = pygame.joystick.Joystick(joy_index)
            if not joy.get_init():
                joy.init()
            instance_id = int(joy.get_instance_id()) if hasattr(joy, "get_instance_id") else joy_index
        except Exception:
            instance_id = joy_index
        selected_by_instance_id[instance_id] = (controller_index, selector)
        selected_by_joy_id[joy_index] = (controller_index, selector)
    for event in events:
        event_type = int(getattr(event, "type", -1))
        if debug_prefix and event_type in {
            getattr(pygame, "JOYBUTTONDOWN", -1000),
            getattr(pygame, "JOYAXISMOTION", -1001),
            getattr(pygame, "JOYHATMOTION", -1002),
            getattr(pygame, "CONTROLLERBUTTONDOWN", -1003),
            getattr(pygame, "CONTROLLERAXISMOTION", -1004),
        }:
            print(f"{debug_prefix} raw event={event}")
        source = _selected_source_for_event(event, selected_by_instance_id, selected_by_joy_id)
        if source is None:
            continue
        controller_index, selector = source
        source_key = _controller_state_source_key(selector)
        if event_type == getattr(pygame, "JOYBUTTONDOWN", None):
            button_index = int(getattr(event, "button", -1))
            if button_index >= 0:
                return (f"GC{controller_index}:BTN{button_index}", controller_index, selector)
        if event_type == getattr(pygame, "CONTROLLERBUTTONDOWN", None):
            button_index = int(getattr(event, "button", -1))
            if button_index >= 0:
                state_store[(source_key, f"BTN{button_index}")] = 1
                return (f"GC{controller_index}:BTN{button_index}", controller_index, selector)
        if event_type == getattr(pygame, "JOYAXISMOTION", None):
            axis_index = int(getattr(event, "axis", -1))
            axis_value = float(getattr(event, "value", 0.0))
            if axis_index >= 0:
                state = 1 if axis_value >= axis_threshold else (-1 if axis_value <= (-axis_threshold) else 0)
                state_key = (_event_source_id(event), f"AXIS{axis_index}")
                previous = int(state_store.get(state_key, 0))
                state_store[state_key] = state
                if capture_axis and state != 0 and state != previous:
                    suffix = "+" if state > 0 else "-"
                    return (f"GC{controller_index}:AXIS{axis_index}{suffix}", controller_index, selector)
        if event_type == getattr(pygame, "CONTROLLERAXISMOTION", None):
            axis_index = int(getattr(event, "axis", -1))
            axis_value = float(getattr(event, "value", 0.0))
            if axis_index >= 0:
                state = 1 if axis_value >= axis_threshold else (-1 if axis_value <= (-axis_threshold) else 0)
                state_key = (source_key, f"AXIS{axis_index}")
                previous = int(state_store.get(state_key, 0))
                state_store[state_key] = state
                if capture_axis and state != 0 and state != previous:
                    suffix = "+" if state > 0 else "-"
                    return (f"GC{controller_index}:AXIS{axis_index}{suffix}", controller_index, selector)
        if event_type == getattr(pygame, "JOYHATMOTION", None):
            hat_index = int(getattr(event, "hat", 0))
            value = getattr(event, "value", (0, 0))
            try:
                hat_x, hat_y = int(value[0]), int(value[1])
            except Exception:
                hat_x, hat_y = (0, 0)
            directions = {
                "UP": 1 if hat_y > 0 else 0,
                "DOWN": 1 if hat_y < 0 else 0,
                "LEFT": 1 if hat_x < 0 else 0,
                "RIGHT": 1 if hat_x > 0 else 0,
            }
            for direction, active in directions.items():
                state_key = (_event_source_id(event), f"HAT{hat_index}:{direction}")
                previous = int(state_store.get(state_key, 0))
                state_store[state_key] = active
                if active and not previous:
                    return (f"GC{controller_index}:HAT{hat_index}:{direction}", controller_index, selector)
    return None


def _controller_button_indices(controller: object) -> List[int]:
    mapping = _controller_mapping_dict(controller)
    discovered: set[int] = set()
    for raw_value in mapping.values():
        token = str(raw_value or "").strip().lower()
        if token.startswith("b") and token[1:].isdigit():
            discovered.add(max(0, int(token[1:])))
    if discovered:
        upper = max(discovered)
        return list(range(upper + 1))
    return list(range(16))


def _controller_axis_indices(controller: object) -> List[int]:
    mapping = _controller_mapping_dict(controller)
    discovered: set[int] = set()
    for raw_value in mapping.values():
        token = str(raw_value or "").strip().lower()
        if token.startswith("a") and token[1:].isdigit():
            discovered.add(max(0, int(token[1:])))
    if discovered:
        upper = max(discovered)
        return list(range(upper + 1))
    return list(range(6))


def _controller_mapping_dict(controller: object) -> Dict[str, str]:
    try:
        mapping = controller.get_mapping()
    except Exception:
        return {}
    if not isinstance(mapping, dict):
        return {}
    return {str(k): str(v) for k, v in mapping.items()}


def _controller_state_source_key(selector: str) -> str:
    return f"controller::{str(selector or '').strip()}"


def _controller_source_id(controller: object, fallback: int) -> int:
    try:
        controller_id = int(getattr(controller, "id", fallback))
        return controller_id
    except Exception:
        return int(fallback)


def _normalize_controller_axis_value(value: object) -> float:
    try:
        numeric = float(value)
    except Exception:
        return 0.0
    if abs(numeric) > 1.0:
        numeric /= 32767.0
    return max(-1.0, min(1.0, numeric))


def _event_source_id(event) -> int:
    for attr in ("instance_id", "joy", "which"):
        value = getattr(event, attr, None)
        if value is not None:
            try:
                return int(value)
            except Exception:
                pass
    return -1


def _selected_source_for_event(
    event,
    selected_by_instance_id: Dict[int, Tuple[int, str]],
    selected_by_joy_id: Dict[int, Tuple[int, str]],
) -> Optional[Tuple[int, str]]:
    instance_id = getattr(event, "instance_id", None)
    if instance_id is not None:
        try:
            match = selected_by_instance_id.get(int(instance_id))
            if match is not None:
                return match
        except Exception:
            pass
    for attr in ("joy", "which"):
        value = getattr(event, attr, None)
        if value is None:
            continue
        try:
            match = selected_by_joy_id.get(int(value))
            if match is not None:
                return match
        except Exception:
            pass
    return None


def _debug_log_joystick_snapshot(debug_prefix: str, joy_index: int, selector: str, flags: Dict[str, object]) -> None:
    if not debug_prefix:
        return
    try:
        joy = pygame.joystick.Joystick(int(joy_index))
        if not joy.get_init():
            joy.init()
    except Exception as exc:
        key = f"snapshot_error::{selector}"
        if not flags.get(key):
            print(f"{debug_prefix} snapshot error selector={selector} error={exc!r}")
            flags[key] = True
        return
    try:
        button_count = max(0, int(joy.get_numbuttons()))
        axis_count = max(0, int(joy.get_numaxes()))
        hat_count = max(0, int(joy.get_numhats()))
        buttons = [index for index in range(button_count) if bool(joy.get_button(index))]
        axes = []
        for index in range(axis_count):
            value = float(joy.get_axis(index))
            if abs(value) >= 0.05:
                axes.append((index, round(value, 3)))
        hats = []
        for index in range(hat_count):
            value = tuple(int(v) for v in joy.get_hat(index))
            if value != (0, 0):
                hats.append((index, value))
    except Exception as exc:
        key = f"snapshot_read_error::{selector}"
        if not flags.get(key):
            print(f"{debug_prefix} snapshot read error selector={selector} error={exc!r}")
            flags[key] = True
        return
    info_key = f"snapshot_info::{selector}"
    if not flags.get(info_key):
        print(
            f"{debug_prefix} controller info selector={selector} "
            f"buttons={button_count} axes={axis_count} hats={hat_count}"
        )
        flags[info_key] = True
    signature = (tuple(buttons), tuple(axes), tuple(hats))
    previous_signature = flags.get(f"snapshot_sig::{selector}")
    if signature != previous_signature:
        print(
            f"{debug_prefix} snapshot selector={selector} "
            f"buttons={buttons} axes={axes} hats={hats}"
        )
        flags[f"snapshot_sig::{selector}"] = signature


def _debug_log_controller_snapshot(debug_prefix: str, joy_index: int, selector: str, flags: Dict[str, object]) -> None:
    if not debug_prefix:
        return
    controller = _ensure_controller_open(joy_index)
    if controller is None:
        key = f"controller_snapshot_missing::{selector}"
        if not flags.get(key):
            print(f"{debug_prefix} controller snapshot unavailable selector={selector}")
            flags[key] = True
        return
    try:
        button_indices = _controller_button_indices(controller)
        axis_indices = _controller_axis_indices(controller)
        buttons = [index for index in button_indices if bool(controller.get_button(int(index)))]
        axes = []
        for index in axis_indices:
            value = _normalize_controller_axis_value(controller.get_axis(int(index)))
            if abs(value) >= 0.05:
                axes.append((int(index), round(value, 3)))
    except Exception as exc:
        key = f"controller_snapshot_error::{selector}"
        if not flags.get(key):
            print(f"{debug_prefix} controller snapshot error selector={selector} error={exc!r}")
            flags[key] = True
        return
    info_key = f"controller_snapshot_info::{selector}"
    if not flags.get(info_key):
        print(
            f"{debug_prefix} controller snapshot info selector={selector} "
            f"buttons={len(button_indices)} axes={len(axis_indices)} mapping={_controller_mapping_dict(controller)}"
        )
        flags[info_key] = True
    signature = (tuple(buttons), tuple(axes))
    previous_signature = flags.get(f"controller_snapshot_sig::{selector}")
    if signature != previous_signature:
        print(
            f"{debug_prefix} controller snapshot selector={selector} "
            f"buttons={buttons} axes={axes}"
        )
        flags[f"controller_snapshot_sig::{selector}"] = signature
