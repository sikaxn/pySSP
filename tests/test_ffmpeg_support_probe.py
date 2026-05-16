from __future__ import annotations

from types import SimpleNamespace

from pyssp import ffmpeg_support


def test_probe_media_info_falls_back_to_ffmpeg_stream_metadata(monkeypatch, tmp_path):
    media_path = tmp_path / "sample.mp4"
    media_path.write_bytes(b"not-real-media")

    blob = "\n".join(
        [
            "  Duration: 00:00:40.17, start: 0.000000, bitrate: 2651 kb/s",
            "  Stream #0:0(und): Video: h264 (High), yuv420p(progressive), 1920x1080 [SAR 1:1 DAR 16:9], 2524 kb/s, 23.98 fps, 23.98 tbr, 24k tbn (default)",
            "  Stream #0:1(und): Audio: aac (LC), 48000 Hz, stereo, fltp, 126 kb/s (default)",
        ]
    ).encode("utf-8")

    monkeypatch.setattr(ffmpeg_support, "get_ffprobe_executable", lambda: "")
    monkeypatch.setattr(ffmpeg_support, "get_ffmpeg_executable", lambda: "ffmpeg")

    def _fake_run(cmd, capture_output, timeout, check, **kwargs):
        assert cmd[:3] == ["ffmpeg", "-hide_banner", "-i"]
        return SimpleNamespace(stdout=b"", stderr=blob, returncode=1)

    monkeypatch.setattr(ffmpeg_support.subprocess, "run", _fake_run)

    info = ffmpeg_support.probe_media_info(str(media_path))

    assert info.duration_ms == 40170
    assert info.has_audio is True
    assert info.has_video is True
    assert info.width == 1920
    assert info.height == 1080
    assert abs(info.fps - 23.98) < 0.01
