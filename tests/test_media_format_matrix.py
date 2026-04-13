from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from pyssp.audio_engine import can_decode_with_ffmpeg
from pyssp.ffmpeg_support import ffmpeg_available, get_ffmpeg_executable, media_has_audio_stream, probe_media_duration_ms


ASSET_MEDIA_DIR = Path(__file__).resolve().parents[1] / "pyssp" / "assets" / "system_info_probe"


def _run_ffmpeg(args: list[str]) -> bool:
    ffmpeg = get_ffmpeg_executable()
    if not ffmpeg:
        return False
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.run(cmd, capture_output=True, check=False, timeout=20)
    return proc.returncode == 0


@pytest.mark.parametrize("name", ["sample.wav", "sample.mp3", "sample.ogg", "sample.flac"])
def test_repo_sample_audio_formats_have_duration_and_audio_stream(name):
    if not ffmpeg_available():
        pytest.skip("ffmpeg not available in this environment")
    media_path = ASSET_MEDIA_DIR / name
    assert media_path.exists(), f"Missing media asset: {media_path}"
    assert probe_media_duration_ms(str(media_path)) > 0
    assert media_has_audio_stream(str(media_path)) is True
    assert can_decode_with_ffmpeg(str(media_path), timeout_ms=1200) is True


def test_generated_audio_format_matrix_from_wav(tmp_path):
    if not ffmpeg_available():
        pytest.skip("ffmpeg not available in this environment")

    source_wav = ASSET_MEDIA_DIR / "sample.wav"
    assert source_wav.exists()

    targets = {
        "gen.aiff": ["-i", str(source_wav), str(tmp_path / "gen.aiff")],
        "gen.m4a": ["-i", str(source_wav), "-c:a", "aac", str(tmp_path / "gen.m4a")],
        "gen.opus": ["-i", str(source_wav), "-c:a", "libopus", str(tmp_path / "gen.opus")],
        "gen.oga": ["-i", str(source_wav), "-c:a", "libvorbis", str(tmp_path / "gen.oga")],
    }

    generated: list[Path] = []
    for file_name, args in targets.items():
        output_path = tmp_path / file_name
        if _run_ffmpeg(args) and output_path.exists() and output_path.stat().st_size > 0:
            generated.append(output_path)

    # Different ffmpeg builds expose different encoders; require at least 2 successful formats.
    assert len(generated) >= 2

    for path in generated:
        assert probe_media_duration_ms(str(path)) > 0
        assert media_has_audio_stream(str(path)) is True
        assert can_decode_with_ffmpeg(str(path), timeout_ms=1200) is True


def test_generated_video_with_and_without_audio_are_detected(tmp_path):
    if not ffmpeg_available():
        pytest.skip("ffmpeg not available in this environment")

    with_audio = tmp_path / "with_audio.mp4"
    no_audio = tmp_path / "no_audio.mp4"

    ok_with_audio = _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x120:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=0.6",
            "-shortest",
            "-t",
            "0.6",
            str(with_audio),
        ]
    )
    ok_no_audio = _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x120:rate=10",
            "-an",
            "-t",
            "0.6",
            str(no_audio),
        ]
    )

    if not (ok_with_audio and ok_no_audio and with_audio.exists() and no_audio.exists()):
        pytest.skip("ffmpeg build cannot generate required mp4 samples")

    assert probe_media_duration_ms(str(with_audio)) > 0
    assert probe_media_duration_ms(str(no_audio)) > 0

    assert media_has_audio_stream(str(with_audio)) is True
    assert media_has_audio_stream(str(no_audio)) is False

    assert can_decode_with_ffmpeg(str(with_audio), timeout_ms=1200) is True
    assert can_decode_with_ffmpeg(str(no_audio), timeout_ms=1200) is False

