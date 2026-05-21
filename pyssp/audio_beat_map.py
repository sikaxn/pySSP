from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
import json
import sys
from typing import Any, Optional

import numpy as np

from pyssp.audio_engine import _decode_media_frames
from pyssp.utility_audio import normalize_time_signature

try:
    import librosa  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    librosa = None


@dataclass
class AudioBeatMap:
    bpm: float = 120.0
    time_signature_num: int = 4
    time_signature_den: int = 4
    first_downbeat_ms: int = 0
    beat_times_ms: list[int] = field(default_factory=list)
    beat_numbers: list[int] = field(default_factory=list)
    source: str = "manual"
    confidence: float = 0.0
    analysis_method: str = ""
    analysis_confidence: float = 0.0
    analysis_version: str = "1"


def normalize_audio_beat_map(raw: object) -> Optional[AudioBeatMap]:
    if raw is None:
        return None
    if isinstance(raw, AudioBeatMap):
        bpm = max(1.0, min(999.0, float(raw.bpm or 120.0)))
        numerator, denominator = normalize_time_signature(raw.time_signature_num, raw.time_signature_den)
        beat_times = sorted(max(0, int(value)) for value in list(raw.beat_times_ms or []))
        beat_numbers: list[int] = []
        for index, value in enumerate(list(raw.beat_numbers or [])):
            try:
                token = int(value)
            except Exception:
                token = ((index % max(1, numerator)) + 1)
            beat_numbers.append(max(1, min(max(1, numerator), token)))
        if beat_times and len(beat_numbers) != len(beat_times):
            beat_numbers = [((index % max(1, numerator)) + 1) for index in range(len(beat_times))]
        return AudioBeatMap(
            bpm=bpm,
            time_signature_num=numerator,
            time_signature_den=denominator,
            first_downbeat_ms=max(0, int(raw.first_downbeat_ms or 0)),
            beat_times_ms=beat_times,
            beat_numbers=beat_numbers,
            source=str(raw.source or raw.analysis_method or "manual").strip().lower() or "manual",
            confidence=max(
                0.0,
                min(
                    1.0,
                    float(
                        raw.confidence
                        if getattr(raw, "confidence", None) is not None
                        else getattr(raw, "analysis_confidence", 0.0)
                    ),
                ),
            ),
            analysis_method=str(raw.analysis_method or raw.source or "manual").strip().lower() or "manual",
            analysis_confidence=max(
                0.0,
                min(
                    1.0,
                    float(
                        raw.analysis_confidence
                        if getattr(raw, "analysis_confidence", None) is not None
                        else getattr(raw, "confidence", 0.0)
                    ),
                ),
            ),
            analysis_version=str(getattr(raw, "analysis_version", "1") or "1").strip() or "1",
        )
    if not isinstance(raw, dict):
        return None
    return normalize_audio_beat_map(
        AudioBeatMap(
            bpm=float(raw.get("bpm", 120.0) or 120.0),
            time_signature_num=int(raw.get("time_signature_num", 4) or 4),
            time_signature_den=int(raw.get("time_signature_den", 4) or 4),
            first_downbeat_ms=int(raw.get("first_downbeat_ms", 0) or 0),
            beat_times_ms=[int(value) for value in list(raw.get("beat_times_ms", []) or [])],
            beat_numbers=[int(value) for value in list(raw.get("beat_numbers", []) or [])],
            source=str(raw.get("source", "manual") or "manual"),
            confidence=float(raw.get("confidence", 0.0) or 0.0),
            analysis_method=str(raw.get("analysis_method", raw.get("source", "manual")) or "manual"),
            analysis_confidence=float(raw.get("analysis_confidence", raw.get("confidence", 0.0)) or 0.0),
            analysis_version=str(raw.get("analysis_version", "1") or "1"),
        )
    )


def audio_beat_map_to_dict(spec: Optional[AudioBeatMap]) -> dict[str, Any]:
    normalized = normalize_audio_beat_map(spec)
    if normalized is None:
        return {}
    return {
        "bpm": float(normalized.bpm),
        "time_signature_num": int(normalized.time_signature_num),
        "time_signature_den": int(normalized.time_signature_den),
        "first_downbeat_ms": int(normalized.first_downbeat_ms),
        "beat_times_ms": [int(value) for value in normalized.beat_times_ms],
        "beat_numbers": [int(value) for value in normalized.beat_numbers],
        "source": str(normalized.source or "manual"),
        "confidence": float(normalized.confidence),
        "analysis_method": str(normalized.analysis_method or normalized.source or "manual"),
        "analysis_confidence": float(normalized.analysis_confidence),
        "analysis_version": str(normalized.analysis_version or "1"),
    }


def beat_phase_at_position(spec: Optional[AudioBeatMap], position_ms: int) -> tuple[int, int, int, float]:
    normalized = normalize_audio_beat_map(spec)
    if normalized is None:
        return 0, 4, 4, 0.0
    position_ms = max(0, int(position_ms))
    numerator = max(1, int(normalized.time_signature_num))
    denominator = max(1, int(normalized.time_signature_den))
    beat_times = list(normalized.beat_times_ms or [])
    beat_numbers = list(normalized.beat_numbers or [])
    if beat_times:
        idx = max(0, bisect_right(beat_times, position_ms) - 1)
        current_start = beat_times[idx]
        next_start = beat_times[idx + 1] if idx + 1 < len(beat_times) else current_start + int(round(60000.0 / max(1.0, normalized.bpm)))
        duration = max(1, next_start - current_start)
        beat_number = beat_numbers[idx] if idx < len(beat_numbers) else ((idx % numerator) + 1)
        progress = max(0.0, min(1.0, float(position_ms - current_start) / float(duration)))
        return idx, max(1, min(numerator, int(beat_number))), denominator, progress
    beat_ms = max(1.0, 60000.0 / max(1.0, normalized.bpm))
    shifted = max(0.0, float(position_ms - max(0, int(normalized.first_downbeat_ms))))
    beat_index = int(shifted / beat_ms)
    beat_number = (beat_index % numerator) + 1
    progress = max(0.0, min(1.0, (shifted % beat_ms) / beat_ms))
    return beat_index, beat_number, denominator, progress


def beat_interval_ms(spec: Optional[AudioBeatMap]) -> Optional[int]:
    normalized = normalize_audio_beat_map(spec)
    if normalized is None:
        return None
    beat_times = list(normalized.beat_times_ms or [])
    if len(beat_times) >= 2:
        intervals = np.diff(np.asarray(beat_times, dtype=np.float32))
        if intervals.size > 0:
            interval = int(round(float(np.median(intervals))))
            if interval > 0:
                return interval
    bpm = max(1.0, float(normalized.bpm or 0.0))
    if bpm <= 0.0:
        return None
    return max(1, int(round(60000.0 / bpm)))


def has_usable_smart_fade_beat_map(spec: Optional[AudioBeatMap]) -> bool:
    normalized = normalize_audio_beat_map(spec)
    if normalized is None:
        return False
    if len(list(normalized.beat_times_ms or [])) >= 2:
        return True
    method = str(normalized.analysis_method or normalized.source or "").strip().lower()
    confidence = max(float(normalized.analysis_confidence), float(normalized.confidence))
    return normalized.bpm > 0.0 and (method == "manual" or confidence >= 0.35)


def next_beat_boundary_ms(
    spec: Optional[AudioBeatMap],
    position_ms: int,
    *,
    prefer_downbeat: bool = False,
    end_limit_ms: Optional[int] = None,
    max_lookahead_beats: Optional[int] = None,
) -> Optional[int]:
    normalized = normalize_audio_beat_map(spec)
    if normalized is None or not has_usable_smart_fade_beat_map(normalized):
        return None
    position_ms = max(0, int(position_ms))
    interval_ms = beat_interval_ms(normalized)
    if interval_ms is None or interval_ms <= 0:
        return None
    numerator = max(1, int(normalized.time_signature_num or 4))
    beat_times = list(normalized.beat_times_ms or [])
    beat_numbers = list(normalized.beat_numbers or [])
    search_limit_ms = None if end_limit_ms is None else max(position_ms, int(end_limit_ms))
    search_limit_from_lookahead = position_ms + (
        max(1, int(max_lookahead_beats or max(4, numerator * 2))) * int(interval_ms)
    )
    if search_limit_ms is None:
        search_limit_ms = search_limit_from_lookahead
    else:
        search_limit_ms = min(search_limit_ms, search_limit_from_lookahead)

    def _accept(candidate_ms: int, beat_number: int) -> bool:
        if candidate_ms <= position_ms:
            return False
        if candidate_ms > search_limit_ms:
            return False
        return (not prefer_downbeat) or int(beat_number) == 1

    for index, candidate_ms in enumerate(beat_times):
        beat_number = beat_numbers[index] if index < len(beat_numbers) else ((index % numerator) + 1)
        if _accept(int(candidate_ms), int(beat_number)):
            return int(candidate_ms)

    if beat_times:
        last_time = int(beat_times[-1])
        last_beat_number = beat_numbers[-1] if beat_numbers else ((len(beat_times) - 1) % numerator) + 1
    else:
        first_downbeat = max(0, int(normalized.first_downbeat_ms or 0))
        if first_downbeat > position_ms:
            if not prefer_downbeat:
                beat_index = int(max(0, round((first_downbeat - position_ms) / float(interval_ms))))
                candidate_ms = first_downbeat + max(0, beat_index - 1) * interval_ms
                while candidate_ms <= position_ms:
                    candidate_ms += interval_ms
                if candidate_ms <= search_limit_ms:
                    return int(candidate_ms)
            if first_downbeat <= search_limit_ms:
                return int(first_downbeat)
        offset = max(0.0, float(position_ms - first_downbeat))
        passed_beats = int(offset / float(interval_ms))
        last_time = first_downbeat + (passed_beats * interval_ms)
        last_beat_number = (passed_beats % numerator) + 1

    candidate_ms = int(last_time)
    candidate_beat_number = int(last_beat_number)
    for _ in range(max(1, int(max_lookahead_beats or max(4, numerator * 2))) + numerator):
        candidate_ms += int(interval_ms)
        candidate_beat_number = (candidate_beat_number % numerator) + 1
        if _accept(candidate_ms, candidate_beat_number):
            return int(candidate_ms)
    if prefer_downbeat:
        return next_beat_boundary_ms(
            normalized,
            position_ms,
            prefer_downbeat=False,
            end_limit_ms=end_limit_ms,
            max_lookahead_beats=max_lookahead_beats,
        )
    return None


def analyze_audio_beat_map(file_path: str) -> AudioBeatMap:
    frames, _duration_ms = _decode_media_frames(str(file_path or "").strip(), prefer_ffmpeg=True)
    if frames.ndim == 1:
        mono = frames.astype(np.float32)
    else:
        mono = np.mean(frames.astype(np.float32), axis=1)
    sample_rate = 48000
    try:
        from pyssp import audio_engine as _audio_engine

        mixer_info = _audio_engine.pygame.mixer.get_init() or (_audio_engine._DEFAULT_AUDIO_SAMPLE_RATE, -16, 2)
        sample_rate = max(1, int(mixer_info[0]))
    except Exception:
        sample_rate = 48000

    if librosa is not None:
        onset_env = librosa.onset.onset_strength(y=mono, sr=sample_rate, aggregate=np.median)
        tempo, beat_times = librosa.beat.beat_track(onset_envelope=onset_env, sr=sample_rate, units="time")
        bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 0.0
        beat_times_ms = [max(0, int(round(float(value) * 1000.0))) for value in np.asarray(beat_times).reshape(-1)]
        confidence = _interval_confidence(beat_times_ms, bpm)
        numerator = _infer_meter_from_beats(onset_env, beat_times_ms, sample_rate)
        return AudioBeatMap(
            bpm=max(1.0, bpm or 120.0),
            time_signature_num=numerator,
            time_signature_den=4,
            first_downbeat_ms=beat_times_ms[0] if beat_times_ms else 0,
            beat_times_ms=beat_times_ms,
            beat_numbers=[((index % numerator) + 1) for index in range(len(beat_times_ms))],
            source="librosa",
            confidence=confidence,
            analysis_method="librosa",
            analysis_confidence=confidence,
            analysis_version="1",
        )

    return _analyze_audio_beat_map_fallback(mono, sample_rate)


def _analyze_audio_beat_map_fallback(mono: np.ndarray, sample_rate: int) -> AudioBeatMap:
    hop = 512
    mono = np.asarray(mono, dtype=np.float32).reshape(-1)
    if mono.size <= hop:
        return AudioBeatMap(source="fallback", confidence=0.0, analysis_method="fallback", analysis_confidence=0.0)
    frame_count = mono.size // hop
    window = mono[: frame_count * hop].reshape(frame_count, hop)
    rms = np.sqrt(np.mean(np.square(window), axis=1))
    novelty = np.maximum(0.0, np.diff(rms, prepend=rms[:1]))
    novelty -= float(np.mean(novelty))
    novelty = np.maximum(0.0, novelty)
    if float(np.max(novelty) or 0.0) <= 0.0:
        return AudioBeatMap(source="fallback", confidence=0.0, analysis_method="fallback", analysis_confidence=0.0)
    novelty /= float(np.max(novelty))
    min_bpm = 60.0
    max_bpm = 200.0
    min_lag = max(1, int((60.0 / max_bpm) * sample_rate / hop))
    max_lag = max(min_lag + 1, int((60.0 / min_bpm) * sample_rate / hop))
    autocorr = np.correlate(novelty, novelty, mode="full")[len(novelty) - 1 :]
    lag = min_lag + int(np.argmax(autocorr[min_lag:max_lag]))
    bpm = 60.0 * sample_rate / float(max(1, lag * hop))
    beat_times_ms = _fallback_beat_times_from_lag(novelty, lag, hop, sample_rate)
    confidence = _interval_confidence(beat_times_ms, bpm)
    numerator = _infer_meter_from_beats(novelty, beat_times_ms, sample_rate, envelope_hop=hop)
    return AudioBeatMap(
        bpm=max(1.0, min(999.0, bpm)),
        time_signature_num=numerator,
        time_signature_den=4,
        first_downbeat_ms=beat_times_ms[0] if beat_times_ms else 0,
        beat_times_ms=beat_times_ms,
        beat_numbers=[((index % numerator) + 1) for index in range(len(beat_times_ms))],
        source="fallback",
        confidence=confidence,
        analysis_method="fallback",
        analysis_confidence=confidence,
        analysis_version="1",
    )


def _fallback_beat_times_from_lag(novelty: np.ndarray, lag: int, hop: int, sample_rate: int) -> list[int]:
    if lag <= 0 or novelty.size <= lag:
        return []
    seed = int(np.argmax(novelty[: max(1, lag * 2)]))
    positions = [seed]
    cursor = seed + lag
    while cursor < novelty.size:
        lo = max(0, cursor - max(1, lag // 4))
        hi = min(novelty.size, cursor + max(2, lag // 4))
        local = novelty[lo:hi]
        if local.size <= 0:
            break
        positions.append(lo + int(np.argmax(local)))
        cursor += lag
    deduped: list[int] = []
    for frame in positions:
        if not deduped or abs(frame - deduped[-1]) > max(1, lag // 3):
            deduped.append(frame)
    return [max(0, int(round((frame * hop * 1000.0) / float(sample_rate)))) for frame in deduped]


def _interval_confidence(beat_times_ms: list[int], bpm: float) -> float:
    if len(beat_times_ms) < 3 or bpm <= 0.0:
        return 0.0
    intervals = np.diff(np.asarray(beat_times_ms, dtype=np.float32))
    mean = float(np.mean(intervals) or 0.0)
    if mean <= 0.0:
        return 0.0
    variation = float(np.std(intervals) / mean)
    coverage = min(1.0, float(len(intervals)) / 16.0)
    return max(0.0, min(1.0, (1.0 - min(1.0, variation)) * coverage))


def _infer_meter_from_beats(
    envelope: np.ndarray,
    beat_times_ms: list[int],
    sample_rate: int,
    *,
    envelope_hop: int = 512,
) -> int:
    if len(beat_times_ms) < 6:
        return 4
    beat_frames = [max(0, int(round((float(value) / 1000.0) * sample_rate / float(envelope_hop)))) for value in beat_times_ms]
    strengths: list[float] = []
    for frame in beat_frames:
        lo = max(0, frame - 1)
        hi = min(len(envelope), frame + 2)
        strengths.append(float(np.max(envelope[lo:hi])) if hi > lo else 0.0)
    best_meter = 4
    best_score = float("-inf")
    for candidate in (3, 4, 6):
        buckets = [[] for _ in range(candidate)]
        for index, strength in enumerate(strengths):
            buckets[index % candidate].append(strength)
        means = [float(np.mean(bucket)) if bucket else 0.0 for bucket in buckets]
        if not means:
            continue
        score = means[0] - float(np.mean(means[1:])) if len(means) > 1 else means[0]
        if score > best_score:
            best_score = score
            best_meter = candidate
    return best_meter


def analyze_audio_beat_map_cli(argv: Optional[list[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv)
    if len(args) < 2:
        print("Usage: analyze-audio-beat-map <file_path>", file=sys.stderr)
        return 2
    file_path = str(args[1] or "").strip()
    if not file_path:
        print("Missing file path.", file=sys.stderr)
        return 2
    try:
        result = analyze_audio_beat_map(file_path)
        print(json.dumps(audio_beat_map_to_dict(result), separators=(",", ":")))
        return 0
    except Exception as exc:
        print(str(exc or "Audio BPM analysis failed."), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(analyze_audio_beat_map_cli())
