from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np


@dataclass
class DSPConfig:
    eq_enabled: bool = False
    eq_bands: List[int] = field(default_factory=lambda: [0] * 10)
    reverb_sec: float = 0.0
    tempo_pct: float = 0.0
    pitch_pct: float = 0.0
    plugin_paths: List[str] = field(default_factory=list)


@dataclass
class _PedalboardBackend:
    Pedalboard: object
    Gain: object
    HighShelfFilter: object
    Limiter: object
    LowShelfFilter: object
    PeakFilter: object
    Reverb: object
    load_plugin: Callable[[str], object]


def normalize_config(config: Optional[DSPConfig]) -> DSPConfig:
    if config is None:
        return DSPConfig()
    eq = list(config.eq_bands or [])
    if len(eq) < 10:
        eq.extend([0] * (10 - len(eq)))
    if len(eq) > 10:
        eq = eq[:10]
    return DSPConfig(
        eq_enabled=bool(config.eq_enabled),
        eq_bands=[int(max(-12, min(12, value))) for value in eq],
        reverb_sec=float(max(0.0, min(20.0, config.reverb_sec))),
        tempo_pct=float(max(-30.0, min(30.0, config.tempo_pct))),
        pitch_pct=float(max(-30.0, min(30.0, config.pitch_pct))),
        plugin_paths=[str(path).strip() for path in list(getattr(config, "plugin_paths", []) or []) if str(path).strip()],
    )


def has_active_processing(config: Optional[DSPConfig]) -> bool:
    cfg = normalize_config(config)
    eq_active = cfg.eq_enabled and any(v != 0 for v in cfg.eq_bands)
    external_active = bool(cfg.plugin_paths)
    return (
        eq_active
        or cfg.reverb_sec > 0.0
        or abs(cfg.tempo_pct) > 1e-9
        or abs(cfg.pitch_pct) > 1e-9
        or external_active
    )


class RealTimeDSPProcessor:
    _EQ_FREQUENCIES = [31.0, 62.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]
    _DEFAULT_Q = 0.70710678

    def __init__(self, sample_rate: int, channels: int) -> None:
        self.sample_rate = int(sample_rate)
        self.channels = int(max(1, channels))
        self.config = DSPConfig()
        self._backend = _load_pedalboard_backend()
        self._pedalboard = None
        self._plugin_load_errors: List[str] = []
        self._rebuild_pedalboard()

    def set_config(self, config: DSPConfig) -> None:
        self.config = normalize_config(config)
        self._rebuild_pedalboard()

    def reset(self) -> None:
        board = self._pedalboard
        if board is None:
            return
        try:
            board.reset()
        except Exception:
            pass

    def process_block(self, block: np.ndarray) -> np.ndarray:
        if block.size == 0:
            return block
        out = np.asarray(block, dtype=np.float32)
        board = self._pedalboard
        if board is None:
            return np.clip(out, -1.0, 1.0).astype(np.float32, copy=False)
        try:
            input_audio = np.ascontiguousarray(out.T, dtype=np.float32)
            buffer_size = max(1, min(8192, int(len(out))))
            processed = board.process(
                input_audio,
                sample_rate=float(self.sample_rate),
                buffer_size=buffer_size,
                reset=False,
            )
            return self._coerce_output_shape(processed, expected_frames=len(out))
        except Exception:
            return np.clip(out, -1.0, 1.0).astype(np.float32, copy=False)

    def _rebuild_pedalboard(self) -> None:
        self._pedalboard = None
        self._plugin_load_errors = []
        backend = self._backend
        if backend is None:
            return
        plugins: List[object] = []
        input_gain = self._build_input_gain_plugin(backend)
        if input_gain is not None:
            plugins.append(input_gain)
        plugins.extend(self._build_eq_plugins(backend))
        reverb = self._build_reverb_plugin(backend)
        if reverb is not None:
            plugins.append(reverb)
        plugins.extend(self._build_external_plugins(backend))
        if plugins:
            limiter = backend.Limiter()
            limiter.threshold_db = -0.3
            limiter.release_ms = 50.0
            plugins.append(limiter)
            self._pedalboard = backend.Pedalboard(plugins)

    def _build_input_gain_plugin(self, backend: _PedalboardBackend) -> Optional[object]:
        headroom_db = self._recommended_headroom_db()
        if headroom_db <= 1e-6:
            return None
        gain = backend.Gain()
        gain.gain_db = -headroom_db
        return gain

    def _recommended_headroom_db(self) -> float:
        eq_boost_db = 0.0
        if self.config.eq_enabled and self.config.eq_bands:
            eq_boost_db = max(0.0, max(float(v) for v in self.config.eq_bands))
        reverb_boost_db = 3.0 if self.config.reverb_sec > 1e-9 else 0.0
        external_boost_db = 6.0 if self.config.plugin_paths else 0.0
        if eq_boost_db <= 1e-9 and reverb_boost_db <= 1e-9 and external_boost_db <= 1e-9:
            return 0.0
        return min(18.0, max(6.0, eq_boost_db + reverb_boost_db + external_boost_db))

    def _build_eq_plugins(self, backend: _PedalboardBackend) -> List[object]:
        if not self.config.eq_enabled:
            return []
        gains = [float(v) for v in self.config.eq_bands]
        plugins: List[object] = []
        if gains[0] != 0.0:
            low = backend.LowShelfFilter()
            low.cutoff_frequency_hz = float(self._EQ_FREQUENCIES[0])
            low.gain_db = gains[0]
            low.q = self._DEFAULT_Q
            plugins.append(low)
        for cutoff_hz, gain_db in zip(self._EQ_FREQUENCIES[1:9], gains[1:9]):
            if gain_db == 0.0:
                continue
            peak = backend.PeakFilter()
            peak.cutoff_frequency_hz = float(cutoff_hz)
            peak.gain_db = float(gain_db)
            peak.q = self._DEFAULT_Q
            plugins.append(peak)
        if gains[9] != 0.0:
            high = backend.HighShelfFilter()
            high.cutoff_frequency_hz = float(self._EQ_FREQUENCIES[9])
            high.gain_db = gains[9]
            high.q = self._DEFAULT_Q
            plugins.append(high)
        return plugins

    def _build_reverb_plugin(self, backend: _PedalboardBackend) -> Optional[object]:
        amount = max(0.0, min(20.0, float(self.config.reverb_sec))) / 20.0
        if amount <= 1e-9:
            return None
        reverb = backend.Reverb()
        reverb.room_size = 0.15 + (0.80 * amount)
        reverb.damping = 0.25 + (0.45 * amount)
        reverb.wet_level = 0.05 + (0.27 * amount)
        reverb.dry_level = 1.0
        reverb.width = 1.0
        reverb.freeze_mode = 0.0
        return reverb

    def _build_external_plugins(self, backend: _PedalboardBackend) -> List[object]:
        plugins: List[object] = []
        for path in self.config.plugin_paths:
            try:
                plugins.append(backend.load_plugin(path))
            except Exception as exc:
                self._plugin_load_errors.append(f"{path}: {exc}")
        return plugins

    def _coerce_output_shape(self, processed: object, expected_frames: int) -> np.ndarray:
        arr = np.asarray(processed, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr[np.newaxis, :]
        if arr.shape[0] == self.channels:
            arr = arr.T
        elif arr.shape[-1] != self.channels:
            arr = np.reshape(arr, (-1, self.channels))
        frame_count = int(arr.shape[0])
        if frame_count > expected_frames:
            arr = arr[:expected_frames, :]
        elif frame_count < expected_frames:
            pad = np.zeros((expected_frames - frame_count, self.channels), dtype=np.float32)
            arr = np.vstack((arr, pad))
        peak = float(np.max(np.abs(arr))) if arr.size else 0.0
        if peak > 1.0:
            arr = arr / peak
        return np.clip(arr, -1.0, 1.0).astype(np.float32, copy=False)


def _load_pedalboard_backend() -> Optional[_PedalboardBackend]:
    try:
        from pedalboard import (
            Gain,
            HighShelfFilter,
            Limiter,
            LowShelfFilter,
            PeakFilter,
            Pedalboard,
            Reverb,
            load_plugin,
        )

        return _PedalboardBackend(
            Pedalboard=Pedalboard,
            Gain=Gain,
            HighShelfFilter=HighShelfFilter,
            Limiter=Limiter,
            LowShelfFilter=LowShelfFilter,
            PeakFilter=PeakFilter,
            Reverb=Reverb,
            load_plugin=load_plugin,
        )
    except Exception:
        return None
