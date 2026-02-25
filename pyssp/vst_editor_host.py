from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import threading
import time
from typing import Dict

from pyssp.vst_host import extract_plugin_state, load_plugin_instance


def _center_windows_for_current_process(stop_event: threading.Event) -> None:
    if os.name != "nt":
        return
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    pid = int(kernel32.GetCurrentProcessId())
    moved: set[int] = set()
    enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    while not stop_event.is_set():
        handles: list[int] = []

        def _enum_callback(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            owner_pid = ctypes.c_ulong(0)
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
            if int(owner_pid.value) != pid:
                return True
            handles.append(int(hwnd))
            return True

        user32.EnumWindows(enum_proc_type(_enum_callback), 0)
        screen_w = int(user32.GetSystemMetrics(0))
        screen_h = int(user32.GetSystemMetrics(1))
        for hwnd in handles:
            if hwnd in moved:
                continue
            rect = ctypes.wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                continue
            w = int(rect.right - rect.left)
            h = int(rect.bottom - rect.top)
            if w <= 100 or h <= 80:
                continue
            x = max(0, int((screen_w - w) / 2))
            y = max(0, int((screen_h - h) / 2))
            user32.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010)
            moved.add(hwnd)
        time.sleep(0.1)


def _read_state(path: str) -> Dict[str, object]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            decoded = json.load(fh)
        if isinstance(decoded, dict):
            return {str(k): v for k, v in decoded.items()}
    except Exception:
        return {}
    return {}


def _write_result(path: str, data: Dict[str, object]) -> None:
    if not path:
        return
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--state-file", default="")
    parser.add_argument("--result-file", default="")
    args = parser.parse_args()

    state = _read_state(str(args.state_file or "").strip())
    stop_event = threading.Event()
    mover = threading.Thread(target=_center_windows_for_current_process, args=(stop_event,), daemon=True)
    mover.start()
    try:
        plugin = load_plugin_instance(str(args.plugin), state=state)
        show = getattr(plugin, "show_editor", None)
        if not callable(show):
            raise RuntimeError("Plugin does not expose a native editor UI.")
        show()
        result = {"state": extract_plugin_state(plugin)}
        _write_result(str(args.result_file or ""), result)
        return 0
    except Exception as exc:
        _write_result(str(args.result_file or ""), {"error": str(exc)})
        return 1
    finally:
        stop_event.set()


if __name__ == "__main__":
    raise SystemExit(main())
