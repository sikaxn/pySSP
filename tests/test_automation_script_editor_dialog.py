from __future__ import annotations

import os

import pytest
from PyQt5.QtCore import Qt
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
        assert bool(dialog.windowFlags() & Qt.WindowMaximizeButtonHint)
        assert dialog._notes_edit.maximumWidth() == 260
        dialog._duration_ms = 12345
        dialog._refresh_cue_indicator()

        assert dialog._cue_indicator._duration_ms == 12345
        assert dialog._cue_indicator._start_ms is None
        assert dialog._cue_indicator._end_ms is None
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()


def test_automation_script_editor_adds_inline_command_to_selected_cue(qapp, tmp_path):
    path = tmp_path / "demo.pysspautoscript"
    dialog = AutomationScriptEditorDialog(
        script_path=str(path),
        audio_path="",
        audio_source="",
        title="Demo",
        lyric_path="",
        companion_payload={
            "updated_at": "",
            "pages": {
                "1": {
                    "1/1": {
                        "page": 1,
                        "row": 1,
                        "column": 1,
                        "text": "Intro",
                        "type": "BUTTON",
                        "color": "#112233",
                    }
                }
            },
        },
    )
    try:
        dialog.show()
        qapp.processEvents()

        dialog._slider.setValue(1500)
        dialog._add_cue_at_current()
        qapp.processEvents()

        assert dialog._selected_cue() is not None
        assert dialog._command_table.rowCount() == 1
        assert dialog._command_table.item(0, 2).background().color().name() == "#112233"

        dialog._command_table.selectRow(0)
        dialog._add_selected_command_to_current_cue()
        qapp.processEvents()

        cue = dialog._selected_cue()
        assert cue is not None
        assert len(list(cue.actions or [])) == 1
        assert dialog._cue_commands_table.rowCount() == 1
        assert dialog._table.item(dialog._table.currentRow(), 2).text() == "Intro"
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()
