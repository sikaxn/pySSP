import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication, QMainWindow

from pyssp.ui.main_window.ui_build import UiBuildMixin


class FullscreenWindow(UiBuildMixin, QMainWindow):
    def resizeEvent(self, event):
        QMainWindow.resizeEvent(self, event)

    def __init__(self):
        QMainWindow.__init__(self)
        self._ui_locked = False
        self.fullscreen_button = self._create_fullscreen_button(self, auto_raise=True)


@pytest.mark.parametrize("maximized", [False, True])
def test_fullscreen_button_restores_previous_window_state(maximized):
    app = QApplication.instance() or QApplication([])
    window = FullscreenWindow()
    window.resize(800, 600)
    window.showMaximized() if maximized else window.show()
    app.processEvents()
    original_geometry = window.normalGeometry()
    try:
        window.fullscreen_button.click()
        app.processEvents()
        assert window.isFullScreen()
        assert window.fullscreen_button.isChecked()
        assert window.fullscreen_button.toolTip() == "Windowed"

        window.fullscreen_button.click()
        app.processEvents()
        assert not window.isFullScreen()
        assert window.isMaximized() == maximized
        assert not window.fullscreen_button.isChecked()
        assert window.normalGeometry() == original_geometry
        assert window.fullscreen_button.toolTip() == "Full Screen"

        window._ui_locked = True
        window._toggle_fullscreen()
        assert not window.isFullScreen()
    finally:
        window.close()


def test_fullscreen_button_tracks_external_window_state_changes():
    app = QApplication.instance() or QApplication([])
    window = FullscreenWindow()
    try:
        window.showFullScreen()
        app.processEvents()
        assert window.fullscreen_button.isChecked()
        window.showNormal()
        app.processEvents()
        assert not window.fullscreen_button.isChecked()
    finally:
        window.close()
