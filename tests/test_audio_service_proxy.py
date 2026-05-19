from __future__ import annotations

import queue
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from pyssp.audio_service import AudioPlayerProxy, AudioServiceController, AudioStateCache
from pyssp.engine.types import EngineDiagnosticsSnapshot, RuntimeSessionSnapshot, TransportSnapshot, VideoDestinationSnapshot


class _FakeAudioController(QObject):
    positionChanged = pyqtSignal(str, int)
    durationChanged = pyqtSignal(str, int)
    stateChanged = pyqtSignal(str, int)
    mediaLoadFinished = pyqtSignal(str, int, bool, str)

    def __init__(self) -> None:
        super().__init__()
        self.state_cache = AudioStateCache()
        self.posts: list[tuple[str, str, dict]] = []
        self.calls: list[tuple[str, str, dict | None, float]] = []

    def post(self, player_id: str, command: str, payload: dict | None = None) -> None:
        self.posts.append((str(player_id), str(command), dict(payload or {})))

    def call(self, player_id: str, command: str, payload: dict | None = None, timeout: float = 2.0):
        self.calls.append((str(player_id), str(command), payload, float(timeout)))
        if command == "sampleRate":
            return 48000
        if command == "outputBlockSize":
            return 1024
        if command == "takeOutputFrames":
            return np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
        if command == "outputTapFrameCounts":
            return {"pre_fader": 12, "post_fader": 34}
        raise AssertionError(f"Unexpected blocking call: {command}")


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_proxy_set_media_async_posts_request_without_blocking_call() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    request_id = player.setMediaAsync("song.wav")

    assert request_id >= 1_000_000
    assert controller.calls == []
    assert controller.posts[-1] == (
        "player-test",
        "setMediaAsyncRequest",
        {"file_path": "song.wav", "dsp_config": None, "request_id": request_id},
    )


def test_proxy_hot_state_reads_use_cache_without_blocking_call() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    player.setPosition(1234)
    assert player.position() == 1234
    assert player.enginePositionMs() == 1234
    assert player.meterLevels() == (0.0, 0.0)
    assert controller.calls == []


def test_proxy_set_media_async_supports_structured_utility_source() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    source = {
        "source_type": "utility",
        "utility_spec": {"mode": "blank", "duration_ms": 5000},
    }
    request_id = player.setMediaAsync(source)

    assert controller.calls == []
    assert controller.posts[-1] == (
        "player-test",
        "setMediaAsyncRequest",
        {"source": source, "file_path": "", "dsp_config": None, "request_id": request_id},
    )


def test_proxy_exposes_sample_rate_and_output_tap_frames_via_controller() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    sample_rate = player.sampleRate()
    block_size = player.outputBlockSize()
    frames = player.takeOutputFrames(max_frames=4, mode="pre_fader")

    assert sample_rate == 48000
    assert block_size == 1024
    assert np.allclose(frames, np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32))
    assert controller.calls == [
        ("player-test", "sampleRate", None, 0.5),
        ("player-test", "outputBlockSize", None, 0.5),
        ("player-test", "takeOutputFrames", {"max_frames": 4, "mode": "pre_fader"}, 0.5),
    ]


def test_proxy_exposes_output_tap_frame_counts_via_controller() -> None:
    _app()
    controller = _FakeAudioController()
    player = AudioPlayerProxy(controller, "player-test")

    counts = player.outputTapFrameCounts()

    assert counts == {"pre_fader": 12, "post_fader": 34}
    assert controller.calls == [
        ("player-test", "outputTapFrameCounts", None, 0.5),
    ]


def test_runtime_session_snapshots_returns_cached_value_on_timeout() -> None:
    controller = AudioServiceController.__new__(AudioServiceController)
    cached = RuntimeSessionSnapshot(
        session_id="player-1",
        runtime_id=7,
        started_at=12.5,
        state=1,
        position_ms=1200,
        duration_ms=5000,
        slot_key=("A", 0, 1),
    )
    controller._last_runtime_session_snapshots = (cached,)
    controller.call = lambda *args, **kwargs: (_ for _ in ()).throw(queue.Empty())

    result = AudioServiceController.runtime_session_snapshots(controller)

    assert result == (cached,)


def test_transport_snapshot_returns_cached_value_on_timeout() -> None:
    controller = AudioServiceController.__new__(AudioServiceController)
    cached = TransportSnapshot(
        generated_at=12.5,
        reference_session_id="player-1",
        active_session_ids=("player-1",),
        playing_session_ids=("player-1",),
        multi_play_enabled=True,
        position_ms=1234,
        duration_ms=5000,
        state=1,
    )
    controller._last_transport_snapshot = cached
    controller.call = lambda *args, **kwargs: (_ for _ in ()).throw(queue.Empty())

    result = AudioServiceController.transport_snapshot(controller)

    assert result == cached


def test_engine_diagnostics_snapshot_returns_cached_value_on_timeout() -> None:
    controller = AudioServiceController.__new__(AudioServiceController)
    cached = EngineDiagnosticsSnapshot(
        generated_at=12.5,
        session_count=1,
        active_session_ids=("player-1",),
        playing_session_ids=("player-1",),
        reference_session_id="player-1",
        ffmpeg_available=True,
        ffmpeg_source="bundled",
        ffmpeg_version="test",
        audio_bus_ids=(),
        video_destination_ids=(),
        render_core="runtime_shared_mix_graph_v1",
        audio_output_stream_active=True,
        audio_output_sample_rate=48000,
        audio_output_channels=2,
        audio_output_blocksize=1024,
        local_video_runtime_enabled=True,
    )
    controller._last_engine_diagnostics_snapshot = cached
    controller.call = lambda *args, **kwargs: (_ for _ in ()).throw(queue.Empty())

    result = AudioServiceController.engine_diagnostics_snapshot(controller)

    assert result == cached


def test_video_destination_snapshots_return_cached_value_on_timeout() -> None:
    controller = AudioServiceController.__new__(AudioServiceController)
    cached = VideoDestinationSnapshot(
        destination_id="ndi_program",
        enabled=True,
        route_mode="video",
        source_name="pyssp-video",
        width=1920,
        height=1080,
        fps=30.0,
        audio_enabled=True,
        audio_tap_mode="post_fader",
        groups="Public",
        discovery_servers="",
        allowed_adapters=(),
        multicast_enabled=False,
        multicast_ttl=1,
        multicast_netmask="255.255.0.0",
        multicast_netprefix="239.255.0.0",
        sender_ready=True,
        connection_count=1,
        has_current_frame=True,
        current_frame_width=1920,
        current_frame_height=1080,
        last_video_pts_ms=0,
        last_video_source_path="",
        frame_submit_count=1,
        video_send_count=1,
        audio_send_count=1,
        audio_drop_count=0,
        audio_recovery_count=0,
        last_audio_sample_rate=48000,
        last_audio_channel_count=2,
    )
    controller._last_video_destination_snapshots = (cached,)
    controller.call = lambda *args, **kwargs: (_ for _ in ()).throw(queue.Empty())

    result = AudioServiceController.video_destination_snapshots(controller)

    assert result == (cached,)
