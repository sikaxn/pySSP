from __future__ import annotations

from pyssp.ui import main_window as mw
from pyssp.ui.main_window import MainWindow, SLOTS_PER_PAGE, _equal_power_crossfade_volume


def test_main_window_import_surface_stays_compatible():
    assert MainWindow is mw.MainWindow
    assert SLOTS_PER_PAGE == mw.SLOTS_PER_PAGE
    assert _equal_power_crossfade_volume is mw._equal_power_crossfade_volume


def test_main_window_module_exposes_monkeypatch_targets():
    assert hasattr(mw, "QFileDialog")
    assert hasattr(mw, "LtcAudioOutput")
    assert hasattr(mw, "MtcMidiOutput")
    assert hasattr(mw, "load_settings")
    assert hasattr(mw, "save_settings")
    assert hasattr(mw, "set_output_device")
    assert hasattr(mw, "configure_audio_preload_cache_policy")
    assert hasattr(mw, "configure_waveform_disk_cache")
    assert hasattr(mw, "shutdown_audio_preload")
