import time

from pyssp import audio_engine


def test_engine_output_meter_sums_active_sources_and_drops_stale():
    audio_engine._clear_engine_output_meter(101)
    audio_engine._clear_engine_output_meter(202)

    audio_engine._update_engine_output_meter(101, 0.25, 0.10)
    audio_engine._update_engine_output_meter(202, 0.30, 0.45)
    left, right = audio_engine.get_engine_output_meter_levels()
    assert round(left, 4) == 0.55
    assert round(right, 4) == 0.55

    audio_engine._update_engine_output_meter(101, 0.0, 0.0)
    audio_engine._update_engine_output_meter(202, 0.0, 0.0)
    time.sleep(audio_engine._OUTPUT_METER_ACTIVE_WINDOW_SEC + 0.02)
    left, right = audio_engine.get_engine_output_meter_levels()
    assert left == 0.0
    assert right == 0.0
