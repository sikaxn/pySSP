from __future__ import annotations

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QVBoxLayout

from pyssp.ui import theme
from pyssp.settings_store import AppSettings
from pyssp.ui import main_window as mw
from pyssp.ui.main_window.window import MainWindow


def test_linux_has_no_system_theme(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert theme.normalize_ui_theme("system") == "bright"


def test_macos_system_appearance(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(theme.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="Dark\n"))
    assert theme.effective_ui_theme("system") == "dark"
    monkeypatch.setattr(theme.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=""))
    assert theme.effective_ui_theme("system") == "bright"


def test_windows_system_appearance(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setitem(sys.modules, "winreg", SimpleNamespace(
        HKEY_CURRENT_USER=1,
        OpenKey=lambda *_args: Key(),
        QueryValueEx=lambda *_args: (0, None),
    ))
    assert theme.effective_ui_theme("system") == "dark"


def test_qt_dark_palette_has_light_text():
    app = QApplication.instance() or QApplication([])
    theme.apply_ui_theme(app, "dark")
    try:
        palette = app.palette()
        assert palette.color(QPalette.Window).lightness() < palette.color(QPalette.WindowText).lightness()
        assert palette.color(QPalette.Base).lightness() < palette.color(QPalette.Text).lightness()
    finally:
        theme.apply_ui_theme(app, "bright")


def test_existing_styled_widgets_use_theme_text_not_old_system_colour():
    app = QApplication.instance() or QApplication([])
    theme.apply_ui_theme(app, "bright")
    panel = QFrame()
    title = QLabel("Total Time")
    title.setStyleSheet("font-size:16pt;font-weight:bold;")
    custom = QPushButton("Custom")
    custom.setStyleSheet("QPushButton{color:#FF3300;}")
    layout = QVBoxLayout(panel)
    layout.addWidget(title)
    layout.addWidget(custom)
    panel.show()
    app.processEvents()
    try:
        theme.apply_ui_theme(app, "dark")
        app.processEvents()
        assert title.palette().color(QPalette.WindowText).name().upper() == "#F2F2F2"
        assert custom.palette().color(QPalette.ButtonText).name().upper() == "#FF3300"
    finally:
        panel.close()
        theme.apply_ui_theme(app, "bright")


def test_theme_toggle_cycles_platform_choices(monkeypatch):
    class Window:
        def __init__(self):
            self.ui_theme = "bright"
            self.saved = []

        def _apply_theme_colors(self, *, refresh):
            assert refresh

        def _save_settings(self):
            self.saved.append(self.ui_theme)

    window = Window()
    monkeypatch.setattr(sys, "platform", "darwin")
    for _ in range(3):
        MainWindow._cycle_ui_theme(window)
    assert window.saved == ["dark", "system", "bright"]

    window.saved.clear()
    monkeypatch.setattr(sys, "platform", "linux")
    for _ in range(2):
        MainWindow._cycle_ui_theme(window)
    assert window.saved == ["dark", "bright"]


def test_main_window_timer_text_and_media_icons_follow_dark_mode(monkeypatch):
    class Sender:
        def __init__(self, *_args, **_kwargs):
            pass

        def set_output(self, *_args, **_kwargs):
            pass

        def set_device(self, *_args, **_kwargs):
            pass

        def update(self, *_args, **_kwargs):
            pass

        def request_resync(self):
            pass

        def shutdown(self):
            pass

    settings = AppSettings(ui_theme="bright", tips_open_on_startup=False, web_remote_enabled=False)
    monkeypatch.setattr(mw, "LtcAudioOutput", Sender)
    monkeypatch.setattr(mw, "MtcMidiOutput", Sender)
    monkeypatch.setattr(mw, "load_settings", lambda: settings)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    for name in ("_apply_web_remote_state", "_restore_last_set_on_startup", "_poll_midi_inputs",
                 "_tick_timecode_mtc", "_tick_meter", "_tick_fades", "_tick_preload_status_icon",
                 "_tick_talk_blink"):
        monkeypatch.setattr(mw.MainWindow, name, lambda self: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    app = QApplication.instance() or QApplication([])
    window = mw.MainWindow()
    window.show()
    app.processEvents()
    try:
        window.theme_button.click()
        app.processEvents()
        assert window.ui_theme == "dark"
        assert window.total_time.palette().color(QPalette.WindowText).name().upper() == "#F2F2F2"
        assert window.elapsed_time.palette().color(QPalette.WindowText).name().upper() == "#F2F2F2"
        assert window.remaining_time.palette().color(QPalette.WindowText).name().upper() == "#F2F2F2"
        total_title = next(label for label in window.findChildren(QLabel) if label.text() == "Total Time")
        assert total_title.palette().color(QPalette.WindowText).name().upper() == "#F2F2F2"
        stop_icon = window._main_control_buttons_ui["STOP"].icon().pixmap(18, 18).toImage()
        assert stop_icon.pixelColor(9, 9).name().upper() == "#F2F2F2"
    finally:
        window.close()
        theme.apply_ui_theme(app, "bright")
