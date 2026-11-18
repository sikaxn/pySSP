from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from pyssp.audio_process_service import (
    ProcessAudioServiceController,
    ProcessLtcAudioOutput,
    ProcessMtcMidiOutput,
)
from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.settings_store import AppSettings
from pyssp.timecode import TIMECODE_MODE_FOLLOW


def test_audio_and_timecode_worker_runs_while_ui_holds_gil():
    app = QApplication.instance() or QApplication([])
    controller = ProcessAudioServiceController()
    try:
        player = controller.create_player()
        assert controller.call(player.player_id, "state", timeout=15.0) == ExternalMediaPlayer.StoppedState
        assert controller._process.pid != os.getpid()

        finished = []
        player.mediaLoadFinished.connect(lambda request_id, ok, error: finished.append((request_id, ok, error)))
        request_id = player.setMediaAsync({
            "source_type": "utility",
            "utility_spec": {"mode": "blank", "duration_ms": 5000},
        })
        deadline = time.monotonic() + 5.0
        while not finished and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert finished == [(request_id, True, "")]
        player.play()
        assert controller.call(player.player_id, "state") == ExternalMediaPlayer.PlayingState
        player.setVolume(100)
        player.setVolumeRamp(0, 0.25)

        controller.set_timecode_config({
            "mode": TIMECODE_MODE_FOLLOW, "reference_player_id": player.player_id, "cue_start_ms": 0,
            "offset_ms": 1200, "frozen_ms": 0, "fps": 30.0, "mtc_fps": 30.0,
            "idle_behavior": "keep_stream", "ltc_device": None,
            "mtc_device": "__none__", "sample_rate": 48000, "bit_depth": 16,
        })
        first_frame, first_running = 0, False
        deadline = time.monotonic() + 2.0
        while not first_running and time.monotonic() < deadline:
            first_frame, first_running = controller.call("__runtime__", "timecode_snapshot")
            time.sleep(0.01)
        assert first_running

        ltc = ProcessLtcAudioOutput(controller)
        mtc = ProcessMtcMidiOutput(controller, lambda: "keep_stream")
        ltc.set_output(None, 48000, 16, 30.0)
        mtc.set_device("__none__")
        ltc.update(100, 30.0, running=True)
        mtc.update(100, 30.0, 30.0, running=True)

        original_interval = sys.getswitchinterval()
        try:
            sys.setswitchinterval(1.0)
            start = time.monotonic()
            while time.monotonic() - start < 0.45:
                pass
            end = time.monotonic()
        finally:
            sys.setswitchinterval(original_interval)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            app.processEvents()
            if len([t for t in controller._worker_meter_times if start < t < end]) >= 3:
                break
            time.sleep(0.01)
        assert len([t for t in controller._worker_meter_times if start < t < end]) >= 3
        assert controller.call(player.player_id, "volume") == 0
        last_frame, last_running = controller.call("__runtime__", "timecode_snapshot")
        assert last_running and last_frame >= first_frame + 5
    finally:
        controller.shutdown()
        player.deleteLater()
        app.processEvents()


def test_unexpected_worker_exit_is_reported_once():
    app = QApplication.instance() or QApplication([])
    controller = ProcessAudioServiceController()
    failures = []
    controller.serviceFailed.connect(failures.append)
    try:
        controller.ensure_ready()
        controller._process.terminate()
        controller._process.join(timeout=2.0)
        deadline = time.monotonic() + 1.0
        while not failures and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()
        assert len(failures) == 1
        assert "stopped unexpectedly" in failures[0]
        assert controller.request_async("__runtime__", "timecode_snapshot").exception()
    finally:
        controller.shutdown()


def test_main_window_uses_isolated_output_on_native_runtime(monkeypatch):
    from pyssp.ui import main_window as mw

    app = QApplication.instance() or QApplication([])
    settings = AppSettings(tips_open_on_startup=False, web_remote_enabled=False)
    monkeypatch.setattr(mw, "load_settings", lambda: settings)
    monkeypatch.setattr(mw, "ensure_audio_decoder_ready", lambda: None)
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())
    window = mw.MainWindow(isolated_audio=True)
    try:
        app.processEvents()
        assert isinstance(window._audio_service, ProcessAudioServiceController)
        assert window._audio_service._process.is_alive()
        assert isinstance(window._ltc_sender, ProcessLtcAudioOutput)
        assert isinstance(window._mtc_sender, ProcessMtcMidiOutput)
        assert window._audio_service.call(window.player.player_id, "state") == ExternalMediaPlayer.StoppedState
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()


def test_theme_and_options_do_not_interrupt_isolated_timecode(monkeypatch):
    from pyssp.ui import main_window as mw

    app = QApplication.instance() or QApplication([])
    settings = AppSettings(tips_open_on_startup=False, web_remote_enabled=False)
    monkeypatch.setattr(mw, "load_settings", lambda: settings)
    monkeypatch.setattr(mw, "ensure_audio_decoder_ready", lambda: None)
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())
    monkeypatch.setattr(mw.OptionsDialog, "exec_", lambda self: 0)
    window = mw.MainWindow(isolated_audio=True)
    try:
        player = window.player
        finished = []
        player.mediaLoadFinished.connect(lambda _id, ok, _error: finished.append(ok))
        player.setMediaAsync({
            "source_type": "utility", "utility_spec": {"mode": "blank", "duration_ms": 5000},
        })
        deadline = time.monotonic() + 5.0
        while not finished and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert finished == [True]
        player.play()
        window._audio_service.set_timecode_config({
            "mode": TIMECODE_MODE_FOLLOW, "reference_player_id": player.player_id,
            "cue_start_ms": 0, "offset_ms": 0, "frozen_ms": 0,
            "fps": 30.0, "mtc_fps": 30.0, "idle_behavior": "keep_stream",
            "ltc_device": None, "mtc_device": "__none__", "sample_rate": 48000,
            "bit_depth": 16,
        })
        first_frame, _running = window._audio_service.call("__runtime__", "timecode_snapshot")
        window._cycle_ui_theme()
        window._open_options_dialog(initial_page="Audio Device & Timecode")
        last_frame, running = window._audio_service.call("__runtime__", "timecode_snapshot")
        assert running and last_frame > first_frame
        assert window._audio_service.call(player.player_id, "state") == ExternalMediaPlayer.PlayingState
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()
