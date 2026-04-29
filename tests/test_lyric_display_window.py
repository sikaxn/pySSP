import os
import sys
from pathlib import Path

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFrame

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.ui.lyric_display import LyricDisplayWindow


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
