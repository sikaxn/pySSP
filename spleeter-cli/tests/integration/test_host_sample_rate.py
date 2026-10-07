import subprocess
from types import SimpleNamespace

import imageio_ffmpeg
import numpy as np
import pytest
from scipy.io import wavfile

from pyssp.ui.main_window import pages_slots


@pytest.mark.parametrize("extension", [".mp3", ".m4a", ".aac", ".ogg", ".flac"])
def test_final_encoding_preserves_22050_hz(tmp_path, monkeypatch, extension):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    monkeypatch.setattr(pages_slots, "get_ffmpeg_executable", lambda: ffmpeg)
    source = tmp_path / "stem.wav"
    output = tmp_path / ("output" + extension)
    decoded = tmp_path / "decoded.wav"
    wavfile.write(source, 22050, np.zeros((22050, 2), dtype=np.int16))
    runner = SimpleNamespace(
        _run_ffmpeg_audio_command=lambda command: subprocess.run(command, check=True)
    )
    pages_slots.PagesSlotsMixin._ffmpeg_transcode_from_wav(runner, str(source), str(output))
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(output), str(decoded)], check=True)
    assert wavfile.read(decoded)[0] == 22050


def test_encoding_rejects_unsupported_rate_instead_of_resampling(tmp_path, monkeypatch):
    monkeypatch.setattr(pages_slots, "get_ffmpeg_executable", imageio_ffmpeg.get_ffmpeg_exe)
    source = tmp_path / "stem.wav"
    wavfile.write(source, 96000, np.zeros((9600, 2), dtype=np.int16))
    runner = SimpleNamespace(
        _run_ffmpeg_audio_command=lambda command: subprocess.run(command, check=True, capture_output=True)
    )
    with pytest.raises(subprocess.CalledProcessError):
        pages_slots.PagesSlotsMixin._ffmpeg_transcode_from_wav(runner, str(source), str(tmp_path / "output.mp3"))


@pytest.mark.parametrize("sample_rate", [22050, 44100, 48000, 96000])
def test_vocal_removal_decode_preserves_source_rate_and_precision(tmp_path, monkeypatch, sample_rate):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    monkeypatch.setattr(pages_slots, "get_ffmpeg_executable", lambda: ffmpeg)
    source = tmp_path / "source.wav"
    encoded = tmp_path / "source.flac"
    decoded = tmp_path / "decoded.wav"
    # 24-bit audio exercises the precision of the intermediate WAV too.
    samples = (np.arange(sample_rate // 10, dtype=np.int32) % 1024 - 512) * 256
    wavfile.write(source, sample_rate, samples)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(source), str(encoded)], check=True)
    runner = SimpleNamespace(
        _run_ffmpeg_audio_command=lambda command: subprocess.run(command, check=True)
    )
    pages_slots.PagesSlotsMixin._ffmpeg_transcode_to_wav(runner, str(encoded), str(decoded))
    actual_rate, actual = wavfile.read(decoded)
    assert actual_rate == sample_rate
    assert actual.shape == (len(samples), 2)
    assert actual.dtype == np.float32
    # FFmpeg's mono-to-stereo conversion uses a -3 dB coefficient.
    np.testing.assert_allclose(actual[:, 0], samples / 2**31 / np.sqrt(2), atol=1e-10)
    np.testing.assert_array_equal(actual[:, 0], actual[:, 1])
