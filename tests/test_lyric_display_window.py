import os
import sys
from pathlib import Path

import pytest
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import QApplication, QFrame

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


def test_main_window_toggle_forces_lyric_refresh():
    class _WindowStub:
        def __init__(self):
            self.modes = []

        def set_transparent_mode_enabled(self, enabled: bool) -> None:
            self.modes.append(bool(enabled))

    class _Host(LyricsStageMixin):
        pass

    host = _Host()
    host.lyric_display_transparent_mode = False
    host._lyric_display_window = _WindowStub()
    host._suspend_settings_save = True
    refresh_calls = []
    sync_calls = []
    host._refresh_lyric_display = lambda force=False: refresh_calls.append(bool(force))  # type: ignore[method-assign]
    host._sync_lyric_display_controls = lambda: sync_calls.append(True)  # type: ignore[method-assign]
    host._save_settings = lambda: None  # type: ignore[method-assign]

    host._set_lyric_display_transparent_mode(True)

    assert host.lyric_display_transparent_mode is True
    assert host._lyric_display_window.modes == [True]
    assert refresh_calls == []
    assert sync_calls == [True]
