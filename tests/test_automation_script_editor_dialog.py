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
    lyric_path = tmp_path / "demo.lrc"
    lyric_path.write_text("[00:01.00]Verse one\n", encoding="utf-8")
    dialog = AutomationScriptEditorDialog(
        script_path=str(path),
        audio_path="",
        audio_source="",
        title="Demo",
        lyric_path=str(lyric_path),
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
        assert dialog._timeline_tree.topLevelItemCount() == 1

        dialog._command_table.selectRow(0)
        dialog._add_selected_command_to_current_cue()
        qapp.processEvents()

        cue = dialog._selected_cue()
        assert cue is not None
        assert len(list(cue.actions or [])) == 1
        assert cue.comment == "Intro"

        cue_item = dialog._timeline_tree.currentItem()
        assert cue_item is not None
        if cue_item.parent() is not None:
            cue_item = cue_item.parent()
        assert cue_item.text(1) == "Cue"
        assert cue_item.text(2) == "Intro"
        assert cue_item.text(3) == "1/1/1 - Intro"
        assert cue_item.childCount() == 1
        assert cue_item.child(0).text(1) == "Command"
        assert cue_item.child(0).text(2) == "1/1/1 - Intro"
        assert cue_item.child(0).text(3) == "Normal"
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()


def test_automation_script_editor_hides_lyrics_by_default_and_persists_toggle(qapp, tmp_path):
    path = tmp_path / "demo.pysspautoscript"
    lyric_path = tmp_path / "demo.lrc"
    lyric_path.write_text("[00:01.00]Verse one\n", encoding="utf-8")
    states: list[bool] = []
    dialog = AutomationScriptEditorDialog(
        script_path=str(path),
        audio_path="",
        audio_source="",
        title="Demo",
        lyric_path=str(lyric_path),
        companion_payload={"updated_at": "", "pages": {}},
        show_lyric_default=False,
        on_show_lyric_changed=states.append,
    )
    try:
        assert dialog._show_lyric_checkbox.isChecked() is False
        assert dialog._timeline_tree.topLevelItemCount() == 0
        dialog._show_lyric_checkbox.setChecked(True)
        qapp.processEvents()
        assert states == [True]
        assert dialog._timeline_tree.topLevelItemCount() == 1
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()
