from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
from pyssp.vst import parse_plugin_ref

_PEDALBOARD_IMPORT_ERROR = ""
try:
    import pedalboard as _pedalboard
except Exception as exc:  # pragma: no cover - depends on runtime env
    _pedalboard = None
    _PEDALBOARD_IMPORT_ERROR = str(exc)


def is_host_available() -> bool:
    return _pedalboard is not None


def host_unavailable_reason() -> str:
    if is_host_available():
        return ""
    return _PEDALBOARD_IMPORT_ERROR or "pedalboard is not installed."


def _coerce_state_values(values: Dict[str, object]) -> Dict[str, object]:
    output: Dict[str, object] = {}
    for key, value in dict(values or {}).items():
        name = str(key or "").strip()
        if not name:
            continue
        if isinstance(value, (bool, int, float, str)):
            output[name] = value
            continue
        try:
            output[name] = float(value)
        except Exception:
            output[name] = str(value)
    return output


def load_plugin_instance(plugin_ref: str, state: Dict[str, object] | None = None):
    if _pedalboard is None:
        raise RuntimeError(host_unavailable_reason())
    file_path, plugin_name = parse_plugin_ref(plugin_ref)
    plugin = _pedalboard.load_plugin(
        str(file_path),
        plugin_name=(plugin_name or None),
        initialization_timeout=10.0,
    )
    for key, value in _coerce_state_values(state or {}).items():
        try:
            setattr(plugin, key, value)
        except Exception:
            continue
    return plugin


def plugin_parameter_specs(plugin_ref: str, state: Dict[str, object] | None = None) -> Tuple[str, List[Dict[str, object]]]:
    plugin = load_plugin_instance(plugin_ref, state=state)
    plugin_name = str(getattr(plugin, "name", "") or "").strip()
    specs: List[Dict[str, object]] = []
    params = getattr(plugin, "parameters", {}) or {}
    for key, param in dict(params).items():
        python_name = str(getattr(param, "python_name", key) or key)
        label = str(getattr(param, "label", "") or "")
        value_type = getattr(param, "type", float)
        type_name = "str"
        if value_type is bool:
            type_name = "bool"
        elif value_type is float:
            type_name = "float"
        elif value_type is int:
            type_name = "int"
        min_value = getattr(param, "min_value", None)
        max_value = getattr(param, "max_value", None)
        step_size = getattr(param, "step_size", None)
        if step_size is None:
            step_size = getattr(param, "approximate_step_size", None)
        try:
            current_value = getattr(plugin, python_name)
        except Exception:
            current_value = getattr(param, "string_value", "")
        specs.append(
            {
                "id": python_name,
                "display": str(getattr(param, "name", python_name) or python_name),
                "label": label,
                "type": type_name,
                "min": min_value,
                "max": max_value,
                "step": step_size,
                "value": current_value,
            }
        )
    specs.sort(key=lambda item: str(item.get("display", "")).lower())
    return plugin_name, specs


def extract_plugin_state(plugin) -> Dict[str, object]:
    state: Dict[str, object] = {}
    params = getattr(plugin, "parameters", {}) or {}
    for key, param in dict(params).items():
        param_id = str(getattr(param, "python_name", key) or key).strip()
        if not param_id:
            continue
        try:
            state[param_id] = getattr(plugin, param_id)
        except Exception:
            continue
    return _coerce_state_values(state)


def show_plugin_editor(plugin_ref: str, state: Dict[str, object] | None = None) -> Dict[str, object]:
    plugin = load_plugin_instance(plugin_ref, state=state)
    show = getattr(plugin, "show_editor", None)
    if not callable(show):
        raise RuntimeError("Plugin does not expose a native editor UI.")
    show()
    return extract_plugin_state(plugin)


class VSTChainHost:
    def __init__(self, sample_rate: int, channels: int, block_size: int = 1024) -> None:
        self._sample_rate = max(1, int(sample_rate))
        self._channels = max(1, int(channels))
        self._block_size = max(1, int(block_size))
        self._enabled = False
        self._chain: List[str] = []
        self._chain_enabled: List[bool] = []
        self._plugin_cache: Dict[str, object] = {}

    def configure(
        self,
        enabled: bool,
        chain: List[str],
        chain_enabled: List[bool],
        plugin_state: Dict[str, Dict[str, object]],
    ) -> None:
        self._enabled = bool(enabled)
        if not is_host_available():
            self._chain = []
            self._chain_enabled = []
            self._plugin_cache.clear()
            return
        state_map = dict(plugin_state or {})
        normalized_chain = [str(v).strip() for v in chain if str(v).strip()]
        normalized_enabled = [bool(v) for v in list(chain_enabled)]
        if len(normalized_enabled) < len(normalized_chain):
            normalized_enabled.extend([True for _ in range(len(normalized_chain) - len(normalized_enabled))])
        elif len(normalized_enabled) > len(normalized_chain):
            normalized_enabled = normalized_enabled[: len(normalized_chain)]

        next_cache: Dict[str, object] = {}
        for path in normalized_chain:
            plugin = self._plugin_cache.get(path, None)
            if plugin is None:
                plugin = load_plugin_instance(path, state=state_map.get(path, {}))
            else:
                for key, value in _coerce_state_values(state_map.get(path, {})).items():
                    try:
                        setattr(plugin, key, value)
                    except Exception:
                        continue
            if bool(getattr(plugin, "is_instrument", False)):
                continue
            next_cache[path] = plugin
        self._plugin_cache = next_cache
        self._chain = [p for p in normalized_chain if p in self._plugin_cache]
        self._chain_enabled = []
        for idx, path in enumerate(normalized_chain):
            if path in self._plugin_cache:
                self._chain_enabled.append(normalized_enabled[idx] if idx < len(normalized_enabled) else True)

    def process_block(self, block: np.ndarray) -> np.ndarray:
        if not self._enabled or not self._chain:
            return block
        if block.ndim != 2:
            return block
        frame_count = int(block.shape[0])
        if frame_count <= 0:
            return block
        audio = np.asarray(block.T, dtype=np.float32, order="C")
        for index, plugin_path in enumerate(self._chain):
            if not (self._chain_enabled[index] if index < len(self._chain_enabled) else True):
                continue
            plugin = self._plugin_cache.get(plugin_path, None)
            if plugin is None:
                continue
            audio = plugin.process(audio, float(self._sample_rate), buffer_size=self._block_size, reset=False)
            audio = np.asarray(audio, dtype=np.float32)
            if audio.ndim == 1:
                audio = audio.reshape(1, -1)
        if audio.shape[0] < self._channels:
            pad = np.zeros((self._channels - audio.shape[0], audio.shape[1]), dtype=np.float32)
            audio = np.vstack((audio, pad))
        if audio.shape[0] > self._channels:
            audio = audio[: self._channels, :]
        out = np.asarray(audio.T, dtype=np.float32)
        if out.shape[0] < frame_count:
            pad = np.zeros((frame_count - out.shape[0], self._channels), dtype=np.float32)
            out = np.vstack((out, pad))
        elif out.shape[0] > frame_count:
            out = out[:frame_count, :]
        if not np.all(np.isfinite(out)):
            out = np.nan_to_num(out, copy=False)
        out = np.clip(out, -4.0, 4.0)
        return out

    @staticmethod
    def normalize_plugin_state_map(state_map: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
        result: Dict[str, Dict[str, object]] = {}
        for path, state in dict(state_map or {}).items():
            plugin_path = str(path or "").strip()
            if not plugin_path or not isinstance(state, dict):
                continue
            cleaned = _coerce_state_values(state)
            result[plugin_path] = cleaned
        return result

    @staticmethod
    def coerce_numeric(value: object, fallback: float = 0.0) -> float:
        try:
            parsed = float(value)
        except Exception:
            return float(fallback)
        if not math.isfinite(parsed):
            return float(fallback)
        return parsed
