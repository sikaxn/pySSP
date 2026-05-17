from __future__ import annotations

import threading

import numpy as np

from pyssp.audio_engine import ExternalMediaPlayer


def test_take_output_frames_reads_pre_and_post_fader_buffers_independently():
    player = ExternalMediaPlayer.__new__(ExternalMediaPlayer)
    player._lock = threading.RLock()
    player._channels = 2
    player._output_tap_pre_frames = np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    player._output_tap_post_frames = np.asarray([[0.5, 0.6], [0.7, 0.8]], dtype=np.float32)

    pre = player.takeOutputFrames(mode="pre_fader")
    post = player.takeOutputFrames(mode="post_fader")

    assert np.allclose(pre, np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32))
    assert np.allclose(post, np.asarray([[0.5, 0.6], [0.7, 0.8]], dtype=np.float32))
    assert player.takeOutputFrames(mode="pre_fader").shape == (0, 2)
    assert player.takeOutputFrames(mode="post_fader").shape == (0, 2)


def test_audio_callback_pre_fader_keeps_program_gain_when_master_is_zero():
    player = ExternalMediaPlayer.__new__(ExternalMediaPlayer)
    player._lock = threading.RLock()
    player._channels = 2
    player._state = ExternalMediaPlayer.PlayingState
    player._sample_rate = 48000
    player._stream_id = 1
    player._source_frames = np.ones((4, 2), dtype=np.float32)
    player._streaming_mode = False
    player._utility_spec = None
    player._dsp_config = type("_Cfg", (), {"pitch_pct": 0.0, "tempo_pct": 0.0})()
    player._dsp_active = False
    player._volume = 50
    player._master_volume = 0
    player._duration_ms = 1000
    player._position_ms = 0
    player._source_pos = 0.0
    player._source_pos_anchor = 0.0
    player._source_pos_anchor_t = 0.0
    player._source_pos_anchor_tempo = 1.0
    player._ended = False
    player._meter_levels = (0.0, 0.0)
    player._recent_output_frames = np.zeros((0, 2), dtype=np.float32)
    player._last_output_frame = np.zeros((2,), dtype=np.float32)
    player._output_tap_pre_frames = np.zeros((0, 2), dtype=np.float32)
    player._output_tap_post_frames = np.zeros((0, 2), dtype=np.float32)
    player._output_tap_capacity_frames = 4096
    player._output_monitor_id = ""
    player._declick_enabled = False
    player._declick_frames = 0
    player._declick_fade_in_remaining = 0
    player._pending_dsp_config = None
    player._stream_pending = np.zeros((0, 2), dtype=np.float32)
    player._fresh_media_start_pending = False
    player._tempo_ratio_locked = lambda: 1.0
    player._position_from_source_pos_locked = lambda: 0
    player._read_source_block_locked = lambda frames: np.ones((frames, 2), dtype=np.float32)
    player._apply_pending_dsp_config_locked = lambda: None
    player._emit_declick_tail_locked = lambda outdata, frames: False

    outdata = np.zeros((4, 2), dtype=np.float32)
    player._audio_callback(outdata, 4, None, None)

    pre = player.takeOutputFrames(mode="pre_fader")
    post = player.takeOutputFrames(mode="post_fader")

    assert np.allclose(pre, np.ones((4, 2), dtype=np.float32) * 0.5)
    assert np.allclose(post, np.zeros((4, 2), dtype=np.float32))
    assert np.allclose(outdata, np.zeros((4, 2), dtype=np.float32))
