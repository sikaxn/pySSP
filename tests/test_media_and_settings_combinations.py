from __future__ import annotations

import configparser
import os
import wave
from pathlib import Path

import pytest

from pyssp.audio_format_support import build_audio_file_dialog_filter
from pyssp.lyrics import line_for_position, parse_lyric_file
from pyssp.set_loader import load_set_file
from pyssp.settings_store import AppSettings, load_settings, save_settings


def _write_dummy_wav(path: Path, duration_sec: float = 0.25, sample_rate: int = 22050) -> None:
    frame_count = max(1, int(duration_sec * sample_rate))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


def _set_file_path(path: Path) -> str:
    if os.name == "nt":
        return str(path).replace("\\", "\\\\")
    return str(path)


def test_dummy_audio_and_lyric_files_flow_through_set_loader_and_lyric_parser(tmp_path):
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    audio_path = media_dir / "theme_song.wav"
    lyric_path = media_dir / "theme_song.lrc"

    _write_dummy_wav(audio_path)
    lyric_path.write_text("[00:01.00]Line A\n[00:02.00]Line B\n", encoding="utf-8")

    set_path = tmp_path / "combo_media.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Theme Song",
                f"s1={_set_file_path(audio_path)}",
                f"pyssplyric1={_set_file_path(lyric_path)}",
                "pyssptimecodedisplaytimeline1=audio_file",
                "",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_set_file(str(set_path))
    slot = loaded.pages["A"][0][0]

    assert slot.file_path.endswith("theme_song.wav")
    assert slot.lyric_file.endswith("theme_song.lrc")
    assert slot.timecode_timeline_mode == "audio_file"

    lines = parse_lyric_file(slot.lyric_file)
    assert line_for_position(lines, 1100) == "Line A"
    assert line_for_position(lines, 2200) == "Line B"


@pytest.mark.parametrize(
    ("supported_exts", "allow_other", "expected_tokens"),
    [
        ([".wav", "mp3", ".WAV"], False, ["Supported Audio Files", "*.wav", "*.mp3"]),
        ([".wav", "mp3", ".WAV"], True, ["Audio Files", "*.wav", "*.mp3", "All Files (*.*)"]),
        ([], False, ["Audio Files", "*.wav", "*.mp3", "*.flac"]),
        ([], True, ["Audio Files", "*.wav", "*.mp3", "*.flac", "All Files (*.*)"]),
    ],
)
def test_audio_filter_changes_with_setting_combinations(supported_exts, allow_other, expected_tokens):
    value = build_audio_file_dialog_filter(supported_exts, allow_other)
    for token in expected_tokens:
        assert token in value


@pytest.mark.parametrize(
    (
        "new_lyric_file_format",
        "allow_other_unsupported_audio_files",
        "disable_path_safety",
        "verify_sound_file_on_add",
        "candidate_error_action",
        "main_transport_timeline_mode",
        "timecode_timeline_mode",
        "expected_format",
        "expected_candidate_error_action",
        "expected_main_timeline",
        "expected_timecode_timeline",
    ),
    [
        ("lrc", False, False, True, "keep_playing", "audio_file", "cue_region", "lrc", "keep_playing", "audio_file", "cue_region"),
        ("srt", True, True, False, "stop_playback", "cue_region", "audio_file", "srt", "stop_playback", "cue_region", "audio_file"),
        ("bogus", True, True, True, "invalid", "weird", "unknown", "srt", "stop_playback", "cue_region", "cue_region"),
    ],
)
def test_settings_combo_round_trip_with_media_related_flags(
    tmp_path,
    monkeypatch,
    disable_path_safety,
    new_lyric_file_format,
    allow_other_unsupported_audio_files,
    verify_sound_file_on_add,
    candidate_error_action,
    main_transport_timeline_mode,
    timecode_timeline_mode,
    expected_format,
    expected_candidate_error_action,
    expected_main_timeline,
    expected_timecode_timeline,
):
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)

    settings = AppSettings()
    settings.new_lyric_file_format = new_lyric_file_format
    settings.allow_other_unsupported_audio_files = allow_other_unsupported_audio_files
    settings.disable_path_safety = disable_path_safety
    settings.verify_sound_file_on_add = verify_sound_file_on_add
    settings.search_lyric_on_add_sound_button = True
    settings.supported_audio_format_extensions = [".wav", "mp3", ".WAV"]
    settings.candidate_error_action = candidate_error_action
    settings.main_transport_timeline_mode = main_transport_timeline_mode
    settings.timecode_timeline_mode = timecode_timeline_mode

    save_settings(settings)
    loaded = load_settings()

    assert loaded.new_lyric_file_format == expected_format
    assert loaded.allow_other_unsupported_audio_files is allow_other_unsupported_audio_files
    assert loaded.disable_path_safety is disable_path_safety
    assert loaded.verify_sound_file_on_add is verify_sound_file_on_add
    assert loaded.search_lyric_on_add_sound_button is True
    assert loaded.supported_audio_format_extensions == [".wav", ".mp3"]
    assert loaded.candidate_error_action == expected_candidate_error_action
    assert loaded.main_transport_timeline_mode == expected_main_timeline
    assert loaded.timecode_timeline_mode == expected_timecode_timeline


def test_timecode_timeline_empty_value_normalizes_to_cue_region():
    parser = configparser.ConfigParser()
    parser["main"] = {
        "main_transport_timeline_mode": "audio_file",
        "timecode_timeline_mode": "",
    }
    from pyssp.settings_store import _from_parser

    loaded = _from_parser(parser)
    assert loaded.main_transport_timeline_mode == "audio_file"
    assert loaded.timecode_timeline_mode == "cue_region"
