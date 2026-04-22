from pyssp import audio_engine


def test_compute_waveform_peaks_from_path_prefers_ffmpeg_decode(monkeypatch):
    calls = {"decode": 0, "prefer_ffmpeg": []}

    monkeypatch.setattr(audio_engine, "_load_waveform_peaks_from_disk", lambda _path, _points: None)
    monkeypatch.setattr(audio_engine, "_peek_cached_media_frames", lambda _path: None)
    monkeypatch.setattr(audio_engine, "_save_waveform_peaks_to_disk", lambda _path, _points, _peaks: None)

    def _decode(_path, prefer_ffmpeg=False):
        calls["decode"] += 1
        calls["prefer_ffmpeg"].append(bool(prefer_ffmpeg))
        return audio_engine.np.array([[0.0, 0.0], [0.5, -0.5], [1.0, -1.0]], dtype=audio_engine.np.float32), 100

    monkeypatch.setattr(audio_engine, "_decode_media_frames", _decode)

    peaks = audio_engine._compute_waveform_peaks_from_path("demo.mp3", sample_count=8)

    assert calls["decode"] == 1
    assert calls["prefer_ffmpeg"] == [True]
    assert peaks
    assert max(peaks) == 1.0
