from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.settings_store import AppSettings
from pyssp.ui import main_window as mw


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.monkey
def test_audio_engine_insight_snapshot_contains_player_sections(qapp, monkeypatch):
    _ = qapp

    class _DummyLtcSender:
        def set_output(self, *_args, **_kwargs):
            return None

        def update(self, *_args, **_kwargs):
            return None

        def request_resync(self):
            return None

        def shutdown(self):
            return None

    class _DummyMtcSender:
        def __init__(self, *_args, **_kwargs):
            pass

        def set_device(self, *_args, **_kwargs):
            return None

        def update(self, *_args, **_kwargs):
            return None

        def request_resync(self):
            return None

        def shutdown(self):
            return None

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw, "load_settings", lambda: settings)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)

    window = mw.MainWindow()
    try:
        window.player.play()
        window._set_player_slot_key(window.player, ("A", 0, 0))
        window._mark_player_started(window.player)
        snapshot = window._audio_engine_insight_snapshot_data()
        assert snapshot["summary"]
        assert snapshot["players"]
        assert snapshot["players"][0]["label"] == "primary"
        assert snapshot["players"][0]["runtime_id"] == 0
        assert snapshot["players"][0]["state"] == "playing"
    finally:
        window.close()
