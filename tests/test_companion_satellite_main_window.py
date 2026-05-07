from __future__ import annotations

import os
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication, QMainWindow

from pyssp.settings_store import AppSettings
from pyssp.ui.main_window import companion_satellite as companion_satellite_module
from pyssp.ui import main_window as mw


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _cleanup_window(window, qapp: QApplication) -> None:
    try:
        satellite_window = getattr(window, "_companion_satellite_window", None)
        if satellite_window is not None:
            satellite_window.close()
    except Exception:
        pass
    try:
        window.hide()
        QMainWindow.close(window)
    except Exception:
        pass
    qapp.processEvents()


def test_main_window_exposes_companion_menu_actions(qapp, monkeypatch):
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
    settings.web_remote_enabled = False
    settings.companion_satellite_enabled = False
    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_apply_companion_satellite_state", lambda self: None)
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
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_companion_satellite_client", lambda self: None)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        assert "open_virtual_satellite" in window._menu_actions
        assert "open_companion_satellite_options" in window._menu_actions
        assert "companion_available_commands" in window._menu_actions
        assert "companion_bypass" in window._menu_actions
        assert window._menu_actions["companion_bypass"].isCheckable() is True
        opened = {"page": None}
        monkeypatch.setattr(
            window,
            "_open_options_dialog",
            lambda initial_page=None: opened.__setitem__("page", initial_page),
        )
        window._menu_actions["open_companion_satellite_options"].trigger()
        assert opened["page"] == "Automation"
        window._menu_actions["companion_available_commands"].trigger()
        assert window._companion_available_commands_dialog is not None
    finally:
        _cleanup_window(window, qapp)

def test_available_commands_filter_checkbox_updates_main_window_state(qapp, monkeypatch):
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
    settings.web_remote_enabled = False
    settings.companion_satellite_enabled = False
    settings.companion_available_commands_filter_black_empty = True
    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_apply_companion_satellite_state", lambda self: None)
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
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_companion_satellite_client", lambda self: None)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._open_companion_available_commands()
        dialog = window._companion_available_commands_dialog
        assert dialog is not None
        assert dialog.hide_black_empty_checkbox.isChecked() is True
        dialog.hide_black_empty_checkbox.setChecked(False)
        qapp.processEvents()
        assert window.companion_available_commands_filter_black_empty is False
    finally:
        _cleanup_window(window, qapp)


def test_companion_bypass_blocks_remote_command_send(qapp, monkeypatch):
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
    settings.web_remote_enabled = False
    settings.companion_satellite_enabled = False
    settings.companion_bypass = True
    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_apply_companion_satellite_state", lambda self: None)
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
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_companion_satellite_client", lambda self: None)
    sent_calls = []
    monkeypatch.setattr(
        companion_satellite_module,
        "send_companion_location_command",
        lambda **kwargs: sent_calls.append(kwargs),
        raising=False,
    )
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    notices = []
    try:
        monkeypatch.setattr(window, "_show_info_notice_banner", notices.append)
        window._send_companion_location_command_async("5/1/2", "press")

        assert sent_calls == []
        assert notices == ["Companion commands are bypassed. Command will not go through."]
        assert window.companion_satellite_status_icon.text() == "SAT (Bypassed)"
    finally:
        _cleanup_window(window, qapp)


def test_companion_location_command_sends_without_satellite_connection_and_handles_failure(
    qapp, monkeypatch
):
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

    class _ImmediateThread:
        def __init__(self, *, target=None, **_kwargs):
            self._target = target

        def start(self):
            if self._target is not None:
                self._target()

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.web_remote_enabled = False
    settings.companion_satellite_enabled = False
    settings.companion_satellite_host = "companion.local"
    settings.companion_command_mode = "udp"
    settings.companion_command_tcp_port = 16759
    settings.companion_command_udp_port = 19001
    settings.companion_command_http_port = 8000
    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_apply_companion_satellite_state", lambda self: None)
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
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_companion_satellite_client", lambda self: None)
    monkeypatch.setattr(
        companion_satellite_module,
        "threading",
        type("_Threading", (), {"Thread": _ImmediateThread}),
        raising=False,
    )
    sent_calls = []

    def _failing_sender(**kwargs):
        sent_calls.append(kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(
        companion_satellite_module,
        "send_companion_location_command",
        _failing_sender,
        raising=False,
    )
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    notices = []
    try:
        window._main_thread_executor.call = lambda fn, timeout=8.0: fn()
        monkeypatch.setattr(window, "_show_info_notice_banner", notices.append)
        window._companion_satellite_client = None

        window._send_companion_location_command_async("5/1/2", "down")

        assert sent_calls == [
            {
                "host": "companion.local",
                "mode": "udp",
                "tcp_port": 16759,
                "udp_port": 19001,
                "http_port": 8000,
                "location": "5/1/2",
                "action": "down",
            }
        ]
        assert notices == ["Companion command failed: boom"]
    finally:
        _cleanup_window(window, qapp)
