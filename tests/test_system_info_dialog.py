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
    dialog.close()
    refresh_thread = dialog._refresh_thread
    if refresh_thread is not None:
        assert refresh_thread.wait(1000)


def test_build_system_information_text_includes_ndi_status(monkeypatch):
    monkeypatch.setattr(system_info_dialog, "list_output_devices", lambda: [])
    monkeypatch.setattr(system_info_dialog, "list_midi_input_devices", lambda force_refresh=False: [])
    monkeypatch.setattr(system_info_dialog, "_list_midi_outputs_cross_platform", lambda: [])
    monkeypatch.setattr(system_info_dialog, "_get_pygame_decoder_report", lambda register_process=None: ["ok"])
    monkeypatch.setattr(system_info_dialog, "_get_current_running_config_report", lambda: ["cfg"])
    monkeypatch.setattr(system_info_dialog, "_get_library_versions", lambda: ["lib"])
    monkeypatch.setattr(system_info_dialog, "_get_network_interfaces", lambda: [])
    monkeypatch.setattr(system_info_dialog, "ndi_status_lines", lambda: ["NDI ready", "NDI python version: 6.3.2.1"])

    text = system_info_dialog.build_system_information_text("v1.2.3")

    assert "NDI status:" in text
    assert "- NDI ready" in text
    assert "- NDI python version: 6.3.2.1" in text
