from __future__ import annotations

import os

import pytest
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication

from pyssp.ui.getting_started_dialog import GettingStartedDialog
from pyssp.ui.theme import apply_ui_theme


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_getting_started_dialog_hides_beta_page_for_non_beta(qapp):
    dialog = GettingStartedDialog(
        version_text="1.2.3",
        build_text="20260425",
        beta_build=False,
    )
    assert dialog._stack.count() == 4


def test_getting_started_dialog_shows_close_only_on_last_page(qapp):
    dialog = GettingStartedDialog(
        version_text="1.2.3b1",
        build_text="20260425",
        beta_build=True,
    )
    dialog.show()
    qapp.processEvents()

    assert dialog._stack.count() == 5
    assert dialog._next_button.isVisible() is True
    assert dialog._close_button.isVisible() is False

    while dialog._stack.currentIndex() < (dialog._stack.count() - 1):
        dialog._advance_page()
        qapp.processEvents()

    assert dialog._next_button.isVisible() is False
    assert dialog._close_button.isVisible() is True


def test_getting_started_dialog_follows_live_palette(qapp):
    dialog = GettingStartedDialog(version_text="1.2.3", build_text="20260425", beta_build=True)
    dialog.show()
    try:
        apply_ui_theme(qapp, "dark")
        qapp.processEvents()
        assert dialog.palette().color(QPalette.Window).name().upper() == "#24272D"
        assert dialog.grab().toImage().pixelColor(10, 10).name().upper() == "#24272D"
        assert dialog._welcome_title.palette().color(QPalette.WindowText).lightness() > 160
        assert dialog._version_label.palette().color(QPalette.WindowText).lightness() > 160
        assert dialog._beta_body.palette().color(QPalette.WindowText).lightness() > 160
        assert dialog._next_button.palette().color(QPalette.ButtonText).lightness() > 160
        apply_ui_theme(qapp, "bright")
        qapp.processEvents()
        assert dialog.palette().color(QPalette.Window).name().upper() == "#FFFDF7"
        assert dialog.grab().toImage().pixelColor(10, 10).name().upper() == "#FFFDF7"
    finally:
        apply_ui_theme(qapp, "bright")
        dialog.close()


def test_getting_started_opens_dark_on_every_page(qapp):
    apply_ui_theme(qapp, "dark")
    dialog = GettingStartedDialog(version_text="1.2.3", build_text="20260425", beta_build=True)
    dialog.show()
    try:
        for index in range(dialog._stack.count()):
            dialog._stack.setCurrentIndex(index)
            dialog._sync_buttons()
            qapp.processEvents()
            assert dialog.grab().toImage().pixelColor(10, 10).name().upper() == "#24272D"
        assert "background:#30343B" in dialog._version_label.parentWidget().styleSheet()
        assert dialog._finish_title.palette().color(QPalette.WindowText).lightness() > 160
    finally:
        dialog.close()
        apply_ui_theme(qapp, "bright")
