from __future__ import annotations

from pyssp.audio_beat_map import (
    AudioBeatMap,
    beat_phase_at_position,
    has_usable_smart_fade_beat_map,
    next_beat_boundary_ms,
    normalize_audio_beat_map,
)


def test_normalize_audio_beat_map_clamps_and_fills_beat_numbers():
    normalized = normalize_audio_beat_map(
        {
            "bpm": 128.5,
            "time_signature_num": 3,
            "time_signature_den": 4,
            "first_downbeat_ms": 250,
            "beat_times_ms": [250, 719, 1188],
            "beat_numbers": [],
            "source": "librosa",
            "confidence": 2.0,
        }
    )

    assert normalized is not None
    assert normalized.time_signature_num == 3
    assert normalized.beat_numbers == [1, 2, 3]
    assert normalized.confidence == 1.0
    assert normalized.analysis_method == "librosa"
    assert normalized.analysis_confidence == 1.0


def test_beat_phase_at_position_uses_explicit_beat_map():
    spec = AudioBeatMap(
        bpm=128.0,
        time_signature_num=4,
        time_signature_den=4,
        first_downbeat_ms=100,
        beat_times_ms=[100, 600, 1100, 1600],
        beat_numbers=[1, 2, 3, 4],
        source="manual",
        confidence=1.0,
    )

    beat_index, beat_number, denominator, progress = beat_phase_at_position(spec, 850)

    assert beat_index == 1
    assert beat_number == 2
    assert denominator == 4
    assert 0.4 < progress < 0.6


def test_next_beat_boundary_uses_explicit_beats_and_downbeat_preference():
    spec = AudioBeatMap(
        bpm=120.0,
        time_signature_num=4,
        time_signature_den=4,
        first_downbeat_ms=100,
        beat_times_ms=[100, 600, 1100, 1600, 2100, 2600, 3100, 3600],
        beat_numbers=[1, 2, 3, 4, 1, 2, 3, 4],
        source="librosa",
        confidence=0.9,
        analysis_method="librosa",
        analysis_confidence=0.9,
    )

    assert next_beat_boundary_ms(spec, 1150) == 1600
    assert next_beat_boundary_ms(spec, 1150, prefer_downbeat=True) == 2100


def test_next_beat_boundary_falls_back_to_bpm_grid_when_explicit_beats_missing():
    spec = AudioBeatMap(
        bpm=120.0,
        time_signature_num=4,
        time_signature_den=4,
        first_downbeat_ms=0,
        beat_times_ms=[],
        beat_numbers=[],
        source="manual",
        confidence=0.0,
        analysis_method="manual",
        analysis_confidence=0.0,
    )

    assert has_usable_smart_fade_beat_map(spec) is True
    assert next_beat_boundary_ms(spec, 750) == 1000
