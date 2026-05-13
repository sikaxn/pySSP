from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.ui.lyric_navigator import LyricNavigatorWindow


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_lyric_navigator_uses_compact_width_defaults(qapp):
    window = LyricNavigatorWindow(on_seek_to_ms=lambda _ms: None)
    try:
        assert window.width() <= 500
        assert window.minimumWidth() <= 320
        assert window.sizeHint().width() <= 500
        assert window._table.columnWidth(0) <= 100
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
