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


def test_getting_started_dialog_shows_ndi_status_license_and_link(qapp):
    opened = {"ndi": 0}
    dialog = GettingStartedDialog(
        version_text="1.2.3",
        build_text="20260425",
        beta_build=False,
        ndi_status_text="NDI runtime is ready. (6.1.0)",
        ndi_runtime_download_url="https://ndi.link/NDIRedistV6",
        open_ndi_options=lambda: opened.__setitem__("ndi", opened["ndi"] + 1),
    )
    dialog.show()
    qapp.processEvents()

    assert "NDI runtime is ready." in dialog._ndi_status_label.text()
    assert "ndi.link/NDIRedistV6" in dialog._ndi_download_label.text()
    assert "licensed separately" in dialog._ndi_license_label.text()

    dialog._ndi_options_button.click()
    qapp.processEvents()

    assert opened["ndi"] == 1
