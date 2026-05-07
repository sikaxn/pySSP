from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.ui.automation_script_editor_dialog import AutomationScriptEditorDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_automation_script_editor_constructs_and_updates_cue_indicator(qapp, tmp_path):
    path = tmp_path / "demo.pysspautoscript"
    dialog = AutomationScriptEditorDialog(
        script_path=str(path),
        audio_path="",
        audio_source="",
        title="Demo",
        lyric_path="",
        companion_payload={"updated_at": "", "pages": {}},
    )
    try:
        dialog._duration_ms = 12345
        dialog._refresh_cue_indicator()

        assert dialog._cue_indicator._duration_ms == 12345
        assert dialog._cue_indicator._start_ms is None
        assert dialog._cue_indicator._end_ms is None
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()
