import os
import sys
from pathlib import Path

import pytest
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QApplication, QFrame, QWidget

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.ui.lyric_display import LyricDisplayWindow
from pyssp.ui.main_window.lyrics_stage import LyricsStageMixin


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_transparent_mode_does_not_apply_blackout_backgrounds(qapp):
    window = LyricDisplayWindow()
    try:
        window.set_transparent_mode_enabled(True)

        assert window.testAttribute(Qt.WA_TranslucentBackground) is True
        assert window.testAttribute(Qt.WA_NoSystemBackground) is True
        assert "background:transparent" in window.styleSheet()
        assert "background:transparent" in window._hover_surface.styleSheet()
        assert "background:rgba(0,0,0,1)" not in window.styleSheet()
        assert "background:rgba(0,0,0,1)" not in window._hover_surface.styleSheet()
        assert window._canvas.testAttribute(Qt.WA_NoSystemBackground) is True
        assert window._lyric_widget.frameShape() == QFrame.NoFrame
        assert window._lyric_widget.lineWidth() == 0
    finally:
        window.close()


def test_windowed_mode_restores_opaque_backgrounds(qapp):
    window = LyricDisplayWindow()
    try:
        window.set_transparent_mode_enabled(True)
        window.set_transparent_mode_enabled(False)

        assert window.testAttribute(Qt.WA_TranslucentBackground) is False
        assert window.testAttribute(Qt.WA_NoSystemBackground) is False
        assert "background:#000000" in window.styleSheet()
        assert "background:transparent" in window._hover_surface.styleSheet()
        assert window._canvas.testAttribute(Qt.WA_NoSystemBackground) is False
        assert window._lyric_widget.frameShape() == QFrame.Box
        assert window._lyric_widget.lineWidth() == 1
    finally:
        window.close()


def test_open_windowed_then_toggle_transparent_cleans_content_surface(qapp):
    window = LyricDisplayWindow()
    try:
        window.show()
        qapp.processEvents()

        window.set_transparent_mode_enabled(True)
        qapp.processEvents()

        assert window.isVisible() is True
        assert window.testAttribute(Qt.WA_TranslucentBackground) is True
        assert window.testAttribute(Qt.WA_NoSystemBackground) is True
        assert "background:transparent" in window.styleSheet()
        assert window._root_layout.contentsMargins().left() == 0
        assert window._canvas.testAttribute(Qt.WA_NoSystemBackground) is True
        assert "background:transparent" in window._canvas.styleSheet()
        assert window._lyric_widget.frameShape() == QFrame.NoFrame
        assert window._lyric_widget.lineWidth() == 0
        assert window.frameGeometry().width() >= window.geometry().width()
        assert window.frameGeometry().height() >= window.geometry().height()
    finally:
        window.close()


def test_toggle_transparent_preserves_current_lyric_text_and_toolbar_size(qapp):
    window = LyricDisplayWindow()
    try:
        window.show()
        qapp.processEvents()
        window.set_lyric_text("<span>Hello</span>")
        window.set_transparent_mode_enabled(True)
        window._show_hover_toolbar()
        qapp.processEvents()

        assert window._lyric_widget.value_label.text() == "<span>Hello</span>"
        assert window._last_text == "<span>Hello</span>"
        assert window._toolbar_overlay.x() == 7
        assert window._toolbar_overlay.width() == window.width() - 14
        assert window._toolbar_overlay.height() >= window._toolbar_overlay.sizeHint().height()
    finally:
        window.close()


def test_transparent_fullscreen_roundtrip_preserves_window_geometry(qapp):
    window = LyricDisplayWindow()
    try:
        window.show()
        qapp.processEvents()
        window.set_transparent_mode_enabled(True)
        qapp.processEvents()
        original_geometry = window.geometry()

        window._toggle_fullscreen()
        qapp.processEvents()
        assert window.isFullScreen() is True

        window._toggle_fullscreen()
        qapp.processEvents()

        assert window.isFullScreen() is False
        assert window.geometry() == original_geometry
        assert window.testAttribute(Qt.WA_TranslucentBackground) is True
        assert window.testAttribute(Qt.WA_NoSystemBackground) is True
    finally:
        window.close()


def test_hide_hover_toolbar_repaints_exposed_canvas_region(qapp, monkeypatch):
    window = LyricDisplayWindow()
    try:
        window.show()
        qapp.processEvents()
        window.set_transparent_mode_enabled(True)
        window._show_hover_toolbar()
        qapp.processEvents()

        repaints = []
        updates = []
        expected_rect = QRect(1, 2, 3, 4)
        monkeypatch.setattr(window, "_overlay_exposed_canvas_rect", lambda _rect: expected_rect)
        monkeypatch.setattr(window._canvas, "update", lambda rect=None: updates.append(rect), raising=False)
        monkeypatch.setattr(window._canvas, "repaint", lambda rect=None: repaints.append(rect), raising=False)

        window._hide_hover_toolbar()

        assert window._toolbar_overlay.isVisible() is False
        assert updates == [expected_rect]
        assert repaints == [expected_rect]
    finally:
        window.close()


def test_windowed_fullscreen_toggle_roundtrip(qapp):
    window = LyricDisplayWindow()
    try:
        window.show()
        qapp.processEvents()
        original_geometry = window.geometry()

        window._toggle_fullscreen()
        qapp.processEvents()

        assert window.isFullScreen() is True

        window._toggle_fullscreen()
        qapp.processEvents()

        assert window.isFullScreen() is False
        assert window.geometry() == original_geometry
    finally:
        window.close()


def test_transparent_fullscreen_toggle_roundtrip(qapp):
    window = LyricDisplayWindow()
    try:
        window.show()
        qapp.processEvents()
        window.set_transparent_mode_enabled(True)
        qapp.processEvents()
        original_geometry = window.geometry()

        window._toggle_fullscreen()
        qapp.processEvents()

        assert window.isFullScreen() is True

        window._toggle_fullscreen()
        qapp.processEvents()

        assert window.isFullScreen() is False
        assert window.geometry() == original_geometry
    finally:
        window.close()


def test_main_window_toggle_recreates_open_lyric_window(qapp):
    class _Host(QWidget, LyricsStageMixin):
        pass

    host = _Host()
    host.lyric_display_transparent_mode = False
    host.lyric_display_font_family = ""
    host.lyric_display_font_size = 36
    host.lyric_display_show_not_playing_message = True
    host.lyric_display_previous_line_count = 0
    host.lyric_display_next_line_count = 0
    host.lyric_display_role_colors = {
        "played": "#A0A0A0",
        "current": "#FFD400",
        "next": "#FFFFFF",
    }
    host.lyric_display_role_sizes = {
        "played": 24,
        "current": 40,
        "next": 32,
    }
    host.lyric_display_auto_adjust_role_sizes = True
    host.lyric_display_role_scale_percents = {
        "played": 70,
        "current": 115,
        "next": 90,
    }
    host.lyric_display_role_bold = {
        "played": True,
        "current": True,
        "next": True,
    }
    host.lyric_display_role_italic = {
        "played": False,
        "current": False,
        "next": False,
    }
    host._lyric_display_window = None
    host._suspend_settings_save = True
    refresh_calls = []
    sync_calls = []
    host._refresh_lyric_display = lambda force=False: refresh_calls.append(bool(force))  # type: ignore[method-assign]
    host._sync_lyric_display_controls = lambda: sync_calls.append(True)  # type: ignore[method-assign]
    host._save_settings = lambda: None  # type: ignore[method-assign]
    host._open_options_dialog = lambda initial_page=None: None  # type: ignore[method-assign]

    try:
        host._open_lyric_display()
        qapp.processEvents()
        original_window = host._lyric_display_window
        original_window.setGeometry(40, 50, 700, 400)
        qapp.processEvents()
        refresh_calls.clear()
        sync_calls.clear()

        host._set_lyric_display_transparent_mode(True)
        qapp.processEvents()

        assert host.lyric_display_transparent_mode is True
        assert host._lyric_display_window is not None
        assert host._lyric_display_window is not original_window
        assert host._lyric_display_window.isVisible() is True
        assert host._lyric_display_window.geometry() == QRect(40, 50, 700, 400)
        assert host._lyric_display_window._transparent_mode_enabled is True
        assert refresh_calls == [True]
        assert sync_calls == [True]
    finally:
        if host._lyric_display_window is not None:
            host._lyric_display_window.close()
        host.close()
