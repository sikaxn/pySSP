from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication, QDialog

from pyssp.ui.crash_report_dialog import CrashReportDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_crash_report_dialog_shutdown_button_quits_application(qapp, monkeypatch):
    _ = qapp
    called: list[str] = []

    monkeypatch.setattr(QApplication, "closeAllWindows", lambda self: called.append("close"))
    monkeypatch.setattr(QApplication, "quit", lambda self: called.append("quit"))

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        dialog = CrashReportDialog(type(exc), exc, exc.__traceback__)

    dialog.shutdown_button.click()

    assert dialog.result() == QDialog.Accepted
    assert called == ["close", "quit"]
