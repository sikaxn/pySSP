from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.engine import video_session
from pyssp.ffmpeg_support import MediaProbeInfo


class _FakeStdout:
    def __init__(self, payloads: list[bytes]) -> None:
        self._payload = bytearray().join(payloads)
        self.read_calls: list[int] = []

    def read(self, size: int) -> bytes:
        self.read_calls.append(int(size))
        if not self._payload:
            return b""
        chunk = bytes(self._payload[:size])
        del self._payload[:size]
        return chunk

    def close(self) -> None:
        return None


class _FakePopen:
    def __init__(self, payloads: list[bytes]) -> None:
        self.stdout = _FakeStdout(payloads)
        self._terminated = False

    def poll(self):
        return 0 if self._terminated else None

    def terminate(self) -> None:
        self._terminated = True

    def wait(self, timeout: float | None = None) -> int:
        _ = timeout
        self._terminated = True
        return 0

    def kill(self) -> None:
        self._terminated = True


def _payloads(width: int, height: int, count: int) -> list[bytes]:
    frame_size = max(1, int(width) * int(height) * 3)
    output: list[bytes] = []
    for index in range(count):
        token = (index + 1) % 255
        output.append(bytes([token]) * frame_size)
    return output


def test_ffmpeg_frame_source_streams_forward_frames_without_respawn(monkeypatch):
    width = 4
    height = 2
    popen_calls: list[list[str]] = []

    monkeypatch.setattr(video_session, "probe_media_info", lambda _path: MediaProbeInfo(fps=30.0))
    monkeypatch.setattr(video_session, "get_ffmpeg_executable", lambda: "ffmpeg")

    def _fake_popen(command, **kwargs):
        _ = kwargs
        popen_calls.append(list(command))
        return _FakePopen(_payloads(width, height, 8))

    monkeypatch.setattr(video_session.subprocess, "Popen", _fake_popen)

    source = video_session._FFmpegFrameSource("clip.mp4", width, height)
    try:
        frame0, pts0 = source.frame_at(0)
        frame1, pts1 = source.frame_at(33)
        frame2, pts2 = source.frame_at(66)
    finally:
        source.close()

    assert len(popen_calls) == 1
    assert frame0.isNull() is False
    assert frame1.isNull() is False
    assert frame2.isNull() is False
    assert (pts0, pts1, pts2) == (0, 33, 66)


def test_ffmpeg_frame_source_restarts_stream_on_backward_seek(monkeypatch):
    width = 4
    height = 2
    popen_calls: list[list[str]] = []

    monkeypatch.setattr(video_session, "probe_media_info", lambda _path: MediaProbeInfo(fps=30.0))
    monkeypatch.setattr(video_session, "get_ffmpeg_executable", lambda: "ffmpeg")

    def _fake_popen(command, **kwargs):
        _ = kwargs
        popen_calls.append(list(command))
        return _FakePopen(_payloads(width, height, 8))

    monkeypatch.setattr(video_session.subprocess, "Popen", _fake_popen)

    source = video_session._FFmpegFrameSource("clip.mp4", width, height)
    try:
        _frame_a, pts_a = source.frame_at(66)
        _frame_b, pts_b = source.frame_at(0)
    finally:
        source.close()

    assert len(popen_calls) == 2
    assert pts_a == 66
    assert pts_b == 0
