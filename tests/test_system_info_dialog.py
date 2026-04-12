import os
import sys
import time
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.ui import system_info_dialog
from pyssp.ui.system_info_dialog import SystemInformationDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_refresh_runs_async_without_blocking_ui(qapp, monkeypatch):
    observed_versions = []

    def fake_build_system_information_text(version: str, register_probe_process=None) -> str:
        observed_versions.append(version)
        time.sleep(0.2)
        return f"system info for {version}"

    monkeypatch.setattr(system_info_dialog, "build_system_information_text", fake_build_system_information_text)

    dialog = SystemInformationDialog("v1.2.3")
    start = time.perf_counter()
    dialog.refresh()
    elapsed = time.perf_counter() - start

    assert elapsed < 0.1
    assert dialog._refresh_btn.isEnabled() is False
    assert "Refreshing system information" in dialog._text_box.toPlainText()

    deadline = time.perf_counter() + 2.0
    while time.perf_counter() < deadline:
        qapp.processEvents()
        if dialog._refresh_btn.isEnabled():
            break
        time.sleep(0.01)

    assert observed_versions == ["v1.2.3"]
    assert dialog._refresh_btn.isEnabled() is True
    assert dialog._text_box.toPlainText() == "system info for v1.2.3"
