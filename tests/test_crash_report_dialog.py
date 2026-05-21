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


def test_crash_report_dialog_is_non_blocking_and_logs_open_close(qapp, caplog):
    _ = qapp
    caplog.set_level("INFO", logger="pyssp.crash")

    try:
        raise ValueError("bad data")
    except ValueError as exc:
        dialog = CrashReportDialog(type(exc), exc, exc.__traceback__)

    assert dialog.isModal() is False
    dialog.show()
    qapp.processEvents()
    dialog.close()
    qapp.processEvents()

    messages = [record.getMessage() for record in caplog.records]
    assert any("Crash report dialog opened" in message for message in messages)
    assert any("Crash report dialog closed" in message for message in messages)
