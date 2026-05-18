from __future__ import annotations

import time

import numpy as np

from pyssp.audio_tap_bus import SharedAudioTapBus


def test_shared_audio_tap_bus_tracks_pre_and_post_meter_modes_independently():
    bus = SharedAudioTapBus(channel_count=2, meter_active_window_sec=0.25, monitor_capacity_frames=32)

    bus.update_meter(1, 0.2, 0.1, mode="pre_fader")
    bus.update_meter(1, 0.5, 0.4, mode="post_fader")

    assert bus.get_meter_levels("pre_fader") == (0.2, 0.1)
    assert bus.get_meter_levels("post_fader") == (0.5, 0.4)


def test_shared_audio_tap_bus_drops_stale_meter_sources():
    bus = SharedAudioTapBus(channel_count=2, meter_active_window_sec=0.01, monitor_capacity_frames=32)

    bus.update_meter(1, 0.3, 0.3, mode="post_fader")
    time.sleep(0.03)

    assert bus.get_meter_levels("post_fader") == (0.0, 0.0)


def test_shared_audio_tap_bus_stores_and_drains_monitor_frames_per_mode():
    bus = SharedAudioTapBus(channel_count=2, meter_active_window_sec=0.25, monitor_capacity_frames=32)

    bus.append_monitor_frames("player-a", np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32), mode="pre_fader")
    bus.append_monitor_frames("player-a", np.asarray([[0.5, 0.6]], dtype=np.float32), mode="post_fader")

    assert bus.monitor_frame_counts("player-a") == {"pre_fader": 2, "post_fader": 1}
    assert np.allclose(
        bus.take_monitor_frames("player-a", mode="pre_fader"),
        np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32),
    )
    assert np.allclose(
        bus.take_monitor_frames("player-a", mode="post_fader"),
        np.asarray([[0.5, 0.6]], dtype=np.float32),
    )
    assert bus.monitor_frame_counts("player-a") == {"pre_fader": 0, "post_fader": 0}


def test_shared_audio_tap_bus_can_mix_and_consume_pending_monitor_frames():
    bus = SharedAudioTapBus(channel_count=2, meter_active_window_sec=0.25, monitor_capacity_frames=32)
    bus.append_monitor_frames("player-a", np.ones((6, 2), dtype=np.float32) * 0.25, mode="post_fader")
    bus.append_monitor_frames("player-b", np.ones((4, 2), dtype=np.float32) * 0.5, mode="post_fader")

    assert bus.monitor_player_ids("post_fader") == ["player-a", "player-b"]

    mixed = bus.mix_monitor_chunk(["player-a", "player-b"], target_frames=4, mode="post_fader")

    assert mixed is not None
    chunk, consume_map = mixed
    assert np.allclose(chunk, np.ones((4, 2), dtype=np.float32) * 0.75)
    assert consume_map == {"player-a": 4, "player-b": 4}

    bus.consume_monitor_frames(consume_map, mode="post_fader")

    assert bus.monitor_frame_counts("player-a") == {"pre_fader": 0, "post_fader": 2}
    assert bus.monitor_frame_counts("player-b") == {"pre_fader": 0, "post_fader": 0}
