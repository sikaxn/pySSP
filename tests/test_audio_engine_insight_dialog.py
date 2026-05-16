from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.ffmpeg_support import MediaProbeInfo
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
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())
    monkeypatch.setattr(mw, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(mw, "ffmpeg_source", lambda: "bundled")
    monkeypatch.setattr(mw, "ffmpeg_version_text", lambda: "ffmpeg version test")
    monkeypatch.setattr(mw, "get_ffmpeg_executable", lambda: r"C:\ffmpeg.exe")
    monkeypatch.setattr(mw, "get_ffprobe_executable", lambda: "")
    monkeypatch.setattr(
        mw,
        "probe_media_info",
        lambda _path: MediaProbeInfo(
            duration_ms=40170,
            has_audio=True,
            has_video=True,
            width=1920,
            height=1080,
            fps=23.98,
            rotation_deg=0,
        ),
    )
    monkeypatch.setattr(
        "pyssp.ui.main_window.video_display.probe_media_info",
        lambda _path: MediaProbeInfo(
            duration_ms=40170,
            has_audio=True,
            has_video=True,
            width=1920,
            height=1080,
            fps=23.98,
            rotation_deg=0,
        ),
    )

    window = mw.MainWindow()
    try:
        window.data["A"][0][0] = mw.SoundButtonData(file_path="clip.mp4", title="Clip", duration_ms=40170)
        window.player.play()
        window._set_player_slot_key(window.player, ("A", 0, 0))
        window._mark_player_started(window.player)
        window.current_playing = ("A", 0, 0)
        snapshot = window._audio_engine_insight_snapshot_data()
        assert snapshot["summary"]
        assert snapshot["players"]
        assert snapshot["players"][0]["label"] == "primary"
        assert snapshot["players"][0]["runtime_id"] == 0
        assert snapshot["players"][0]["state"] == "playing"
        summary_map = dict(snapshot["summary"])
        assert summary_map["ffmpeg_available"] is True
        assert summary_map["ffmpeg_source"] == "bundled"
        assert summary_map["ffmpeg_path"] == r"C:\ffmpeg.exe"
        assert summary_map["ffprobe_path"] == "not found"
        assert summary_map["ffmpeg_version"] == "ffmpeg version test"
        assert "size=1920x1080" in summary_map["current_video_probe"]
        details_map = dict(snapshot["players"][0]["details"])
        assert details_map["file_path"] == "clip.mp4"
        assert details_map["media_probe_has_video"] is True
        assert details_map["media_probe_width"] == 1920
        assert details_map["media_probe_height"] == 1080
    finally:
        window.close()
