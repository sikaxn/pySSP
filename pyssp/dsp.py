from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


@dataclass
class DSPConfig:
    eq_enabled: bool = True
    eq_bands: List[int] = field(default_factory=lambda: [0] * 10)
    reverb_sec: float = 0.0
    tempo_pct: float = 0.0
    pitch_pct: float = 0.0


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
    )


def has_active_processing(config: Optional[DSPConfig]) -> bool:
    cfg = normalize_config(config)
    eq_active = cfg.eq_enabled and any(v != 0 for v in cfg.eq_bands)
    return eq_active or cfg.reverb_sec > 0.0 or abs(cfg.tempo_pct) > 1e-9 or abs(cfg.pitch_pct) > 1e-9


class RealTimeDSPProcessor:
    _CENTERS = np.array([31.0, 62.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0], dtype=np.float32)

    def __init__(self, sample_rate: int, channels: int) -> None:
        self.sample_rate = int(sample_rate)
        self.channels = int(max(1, channels))
        self.config = DSPConfig()

        self._eq_curve_cache: dict[Tuple[int, Tuple[int, ...], bool], np.ndarray] = {}
        self._reverb_buffer = np.zeros((1, self.channels), dtype=np.float32)
        self._reverb_write_index = 0
        self._set_reverb_buffer_size(0.0)

    def set_config(self, config: DSPConfig) -> None:
        self.config = normalize_config(config)
        self._set_reverb_buffer_size(self.config.reverb_sec)

    def process_block(self, block: np.ndarray) -> np.ndarray:
        if block.size == 0:
            return block
        out = block.astype(np.float32, copy=True)

        if self.config.eq_enabled and any(v != 0 for v in self.config.eq_bands):
            out = self._apply_eq(out)
        if self.config.reverb_sec > 1e-9:
            out = self._apply_reverb(out)

        peak = float(np.max(np.abs(out)))
        if peak > 1.0:
            out = out / peak
        return out

    def _apply_eq(self, block: np.ndarray) -> np.ndarray:
        n = int(len(block))
        if n <= 8:
            return block

        key = (n, tuple(int(v) for v in self.config.eq_bands), bool(self.config.eq_enabled))
        curve = self._eq_curve_cache.get(key)
        if curve is None:
            curve = self._build_eq_curve(n)
            self._eq_curve_cache[key] = curve

        out = np.empty_like(block)
        for ch in range(block.shape[1]):
            spec = np.fft.rfft(block[:, ch])
            spec *= curve
            out[:, ch] = np.fft.irfft(spec, n=n).astype(np.float32)
        return out

    def _build_eq_curve(self, n: int) -> np.ndarray:
        freqs = np.fft.rfftfreq(n, d=1.0 / float(self.sample_rate)).astype(np.float32)
        safe_freqs = np.clip(freqs, self._CENTERS[0], self._CENTERS[-1])
        log_centers = np.log2(self._CENTERS)
        log_freqs = np.log2(safe_freqs)
        gains = np.array([float(v) for v in self.config.eq_bands], dtype=np.float32)
        gain_db = np.interp(log_freqs, log_centers, gains, left=gains[0], right=gains[-1]).astype(np.float32)
        return np.power(10.0, gain_db / 20.0).astype(np.float32)

    def _set_reverb_buffer_size(self, reverb_sec: float) -> None:
        # Keep the delay network short/fast; slider controls decay amount, not initial delay.
        max_delay = int(max(1, self.sample_rate * (0.20 + (0.60 * max(0.0, min(20.0, reverb_sec)) / 20.0))))
        if max_delay <= 1:
            self._reverb_buffer = np.zeros((1, self.channels), dtype=np.float32)
            self._reverb_write_index = 0
            return
        if len(self._reverb_buffer) == max_delay:
            return
        self._reverb_buffer = np.zeros((max_delay, self.channels), dtype=np.float32)
        self._reverb_write_index = 0

    def _apply_reverb(self, block: np.ndarray) -> np.ndarray:
        amount = max(0.0, min(20.0, self.config.reverb_sec)) / 20.0
        if amount <= 1e-9:
            return block
        wet = 0.10 + (0.72 * amount)
        feedback = 0.12 + (0.34 * amount)
        dilation = 0.95 + (1.05 * amount)
        base_taps_ms = (21.0, 37.0, 61.0, 89.0)
        tap_gains = (0.78, 0.56, 0.39, 0.28)
        tap_samples = [
            max(1, min(len(self._reverb_buffer) - 1, int(self.sample_rate * ((ms * dilation) / 1000.0))))
            for ms in base_taps_ms
        ]

        n = len(block)
        buf_len = len(self._reverb_buffer)
        write_idx = (self._reverb_write_index + np.arange(n)) % buf_len
        echo = np.zeros_like(block)
        for delay, gain in zip(tap_samples, tap_gains):
            read_idx = (write_idx - delay) % buf_len
            echo += self._reverb_buffer[read_idx] * float(gain)
        out = block + (echo * wet)
        # Keep loop gain stable to prevent runaway feedback buildup.
        feedback_in = block + (echo * feedback)
        self._reverb_buffer[write_idx] = np.tanh(feedback_in * 0.9).astype(np.float32)
        self._reverb_write_index = int((self._reverb_write_index + n) % buf_len)
        return out
