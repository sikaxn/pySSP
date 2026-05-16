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
