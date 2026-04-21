import os

import numpy as np

from pyssp import audio_engine


def test_load_waveform_peaks_from_disk_rejects_all_zero_cache(tmp_path, monkeypatch):
    audio_file = tmp_path / "demo.wav"
    audio_file.write_bytes(b"demo")

    cache_dir = tmp_path / "waveform_cache"
    cache_dir.mkdir()

    monkeypatch.setattr(audio_engine, "_WAVEFORM_CACHE_DIR", str(cache_dir))

    cache_file = audio_engine._waveform_cache_path(str(audio_file), 8)
    assert cache_file
    np.zeros(8, dtype=np.uint8).tofile(cache_file)

    peaks = audio_engine._load_waveform_peaks_from_disk(str(audio_file), 8)

    assert peaks is None
    assert os.path.exists(cache_file)
