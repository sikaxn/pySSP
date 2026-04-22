from pyssp.ui.main_window import _equal_power_crossfade_volume


def test_equal_power_crossfade_volume_fades_out_with_cosine_curve():
    assert _equal_power_crossfade_volume(100, 0, 0.0) == 100
    assert _equal_power_crossfade_volume(100, 0, 1.0) == 0
    midpoint = _equal_power_crossfade_volume(100, 0, 0.5)
    assert 69 <= midpoint <= 71


def test_equal_power_crossfade_volume_fades_in_with_sine_curve():
    assert _equal_power_crossfade_volume(0, 100, 0.0) == 0
    assert _equal_power_crossfade_volume(0, 100, 1.0) == 100
    midpoint = _equal_power_crossfade_volume(0, 100, 0.5)
    assert 69 <= midpoint <= 71
