from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.ui.getting_started_dialog import GettingStartedDialog


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
