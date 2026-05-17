import time

from pyssp import audio_engine


def test_engine_output_meter_sums_active_sources_and_drops_stale():
    audio_engine._clear_engine_output_meter(101)
    audio_engine._clear_engine_output_meter(202)

    audio_engine._update_engine_output_meter(101, 0.25, 0.10, mode="post_fader")
    audio_engine._update_engine_output_meter(202, 0.30, 0.45, mode="post_fader")
    left, right = audio_engine.get_engine_output_meter_levels("post_fader")
    assert round(left, 4) == 0.55
    assert round(right, 4) == 0.55

    audio_engine._update_engine_output_meter(101, 0.0, 0.0, mode="post_fader")
    audio_engine._update_engine_output_meter(202, 0.0, 0.0, mode="post_fader")
    time.sleep(audio_engine._OUTPUT_METER_ACTIVE_WINDOW_SEC + 0.02)
    left, right = audio_engine.get_engine_output_meter_levels("post_fader")
    assert left == 0.0
    assert right == 0.0


def test_engine_output_meter_tracks_pre_and_post_fader_independently():
    audio_engine._clear_engine_output_meter(303)

    audio_engine._update_engine_output_meter(303, 0.20, 0.10, mode="pre_fader")
    audio_engine._update_engine_output_meter(303, 0.50, 0.40, mode="post_fader")

    assert audio_engine.get_engine_output_meter_levels("pre_fader") == (0.2, 0.1)
    assert audio_engine.get_engine_output_meter_levels("post_fader") == (0.5, 0.4)

    audio_engine._clear_engine_output_meter(303)
