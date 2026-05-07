from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

from pyssp.i18n import tr


UTILITY_SOURCE_TYPE = "utility"
FILE_SOURCE_TYPE = "file"
UTILITY_UNSUPPORTED_MARKER_TEXT = "Unsupported utility sound button. A newer version of pySSP is required."

UTILITY_MODE_BLANK = "blank"
UTILITY_MODE_PINK_NOISE = "pink_noise"
UTILITY_MODE_WAVEFORM = "waveform"
UTILITY_MODE_METRONOME = "metronome"
UTILITY_MODES = {
    UTILITY_MODE_BLANK,
    UTILITY_MODE_PINK_NOISE,
    UTILITY_MODE_WAVEFORM,
    UTILITY_MODE_METRONOME,
}

UTILITY_WAVEFORM_SINE = "sine"
UTILITY_WAVEFORM_SQUARE = "square"
UTILITY_WAVEFORM_TRIANGLE = "triangle"
UTILITY_WAVEFORM_SAWTOOTH = "sawtooth"
UTILITY_WAVEFORMS = {
    UTILITY_WAVEFORM_SINE,
    UTILITY_WAVEFORM_SQUARE,
    UTILITY_WAVEFORM_TRIANGLE,
    UTILITY_WAVEFORM_SAWTOOTH,
}


@dataclass(frozen=True)
class UtilitySoundSpec:
    mode: str = UTILITY_MODE_BLANK
    duration_ms: int = 1000
    waveform_type: str = UTILITY_WAVEFORM_SINE
    frequency_hz: float = 440.0
    tempo_bpm: float = 120.0
    time_signature_num: int = 4
    time_signature_den: int = 4


def clamp_utility_duration_ms(value: object) -> int:
    try:
        raw = int(value)
    except Exception:
        raw = 1000
    return max(1, min(24 * 60 * 60 * 1000, raw))


def normalize_utility_mode(value: object) -> str:
    token = str(value or "").strip().lower()
    return token if token in UTILITY_MODES else UTILITY_MODE_BLANK


def normalize_utility_waveform(value: object) -> str:
    token = str(value or "").strip().lower()
    return token if token in UTILITY_WAVEFORMS else UTILITY_WAVEFORM_SINE


def normalize_time_signature(num: object, den: object) -> tuple[int, int]:
    try:
        numerator = int(num)
    except Exception:
        numerator = 4
    try:
        denominator = int(den)
    except Exception:
        denominator = 4
    numerator = max(1, min(32, numerator))
    if denominator not in {1, 2, 4, 8, 16}:
        denominator = 4
    return numerator, denominator


def normalize_utility_spec(raw: object) -> UtilitySoundSpec:
    if isinstance(raw, UtilitySoundSpec):
        return UtilitySoundSpec(
            mode=normalize_utility_mode(raw.mode),
            duration_ms=clamp_utility_duration_ms(raw.duration_ms),
            waveform_type=normalize_utility_waveform(raw.waveform_type),
            frequency_hz=max(1.0, min(24000.0, float(raw.frequency_hz))),
            tempo_bpm=max(1.0, min(999.0, float(raw.tempo_bpm))),
            time_signature_num=normalize_time_signature(raw.time_signature_num, raw.time_signature_den)[0],
            time_signature_den=normalize_time_signature(raw.time_signature_num, raw.time_signature_den)[1],
        )
    payload = raw if isinstance(raw, dict) else {}
    numerator, denominator = normalize_time_signature(
        payload.get("time_signature_num", 4),
        payload.get("time_signature_den", 4),
    )
    try:
        frequency_hz = float(payload.get("frequency_hz", 440.0))
    except Exception:
        frequency_hz = 440.0
    try:
        tempo_bpm = float(payload.get("tempo_bpm", 120.0))
    except Exception:
        tempo_bpm = 120.0
    return UtilitySoundSpec(
        mode=normalize_utility_mode(payload.get("mode", UTILITY_MODE_BLANK)),
        duration_ms=clamp_utility_duration_ms(payload.get("duration_ms", 1000)),
        waveform_type=normalize_utility_waveform(payload.get("waveform_type", UTILITY_WAVEFORM_SINE)),
        frequency_hz=max(1.0, min(24000.0, frequency_hz)),
        tempo_bpm=max(1.0, min(999.0, tempo_bpm)),
        time_signature_num=numerator,
        time_signature_den=denominator,
    )


def utility_spec_to_dict(spec: Optional[UtilitySoundSpec]) -> dict[str, Any]:
    normalized = normalize_utility_spec(spec or UtilitySoundSpec())
    return asdict(normalized)


def utility_source_payload(spec: Optional[UtilitySoundSpec]) -> dict[str, Any]:
    return {"source_type": UTILITY_SOURCE_TYPE, "utility_spec": utility_spec_to_dict(spec)}


def is_utility_source_payload(source: object) -> bool:
    if not isinstance(source, dict):
        return False
    return str(source.get("source_type", "")).strip().lower() == UTILITY_SOURCE_TYPE


def utility_duration_hhmmssmmm(duration_ms: object) -> str:
    total = clamp_utility_duration_ms(duration_ms)
    hours, rem = divmod(total, 3600 * 1000)
    minutes, rem = divmod(rem, 60 * 1000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{millis:03d}"


def parse_utility_duration_hhmmssmmm(value: object) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) != 4 or any(not part.isdigit() for part in parts):
        return None
    hours, minutes, seconds, millis = [int(part) for part in parts]
    if minutes >= 60 or seconds >= 60 or millis >= 1000:
        return None
    total = (((hours * 60) + minutes) * 60 + seconds) * 1000 + millis
    if total <= 0 or total > (24 * 60 * 60 * 1000):
        return None
    return total


def utility_display_name(spec: Optional[UtilitySoundSpec]) -> str:
    normalized = normalize_utility_spec(spec or UtilitySoundSpec())
    if normalized.mode == UTILITY_MODE_BLANK:
        return tr("Blank")
    if normalized.mode == UTILITY_MODE_PINK_NOISE:
        return tr("Pink Noise")
    if normalized.mode == UTILITY_MODE_WAVEFORM:
        waveform_label = {
            UTILITY_WAVEFORM_SINE: tr("Sine"),
            UTILITY_WAVEFORM_SQUARE: tr("Square"),
            UTILITY_WAVEFORM_TRIANGLE: tr("Triangle"),
            UTILITY_WAVEFORM_SAWTOOTH: tr("Sawtooth"),
        }.get(normalized.waveform_type, tr("Sine"))
        return f"{waveform_label} {int(round(normalized.frequency_hz))} Hz"
    return (
        f"{tr('Metronome')} {normalized.tempo_bpm:.0f} BPM "
        f"{normalized.time_signature_num}/{normalized.time_signature_den}"
    )
