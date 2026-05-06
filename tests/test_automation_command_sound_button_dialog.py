from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.ui.automation_command_sound_button_dialog import AutomationCommandSoundButtonDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _payload() -> dict:
    return {
        "updated_at": "",
        "pages": {
            "1": {
                "1/1": {"page": 1, "row": 1, "column": 1, "text": "First Button", "type": "button", "color": ""},
                "1/2": {"page": 1, "row": 1, "column": 2, "text": "Second Button", "type": "button", "color": ""},
            }
        },
    }


def _cleanup(dialog: AutomationCommandSoundButtonDialog, qapp: QApplication) -> None:
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()


def test_caption_follows_selected_command_until_user_edits(qapp):
    dialog = AutomationCommandSoundButtonDialog(
        caption="",
        notes="",
        companion_payload=_payload(),
    )
    dialog.show()
    qapp.processEvents()
    try:
        assert dialog.caption_edit.text() == "First Button"
        dialog.table.selectRow(1)
        qapp.processEvents()
        assert dialog.selected_location() == "1/1/2"
        assert dialog.selected_button_text() == "Second Button"
        assert dialog.caption_edit.text() == "Second Button"

        dialog.caption_edit.setText("Manual Caption")
        dialog._on_caption_text_edited("Manual Caption")
        dialog.table.selectRow(0)
        qapp.processEvents()

        assert dialog.selected_location() == "1/1/1"
        assert dialog.selected_button_text() == "First Button"
        assert dialog.caption_edit.text() == "Manual Caption"
    finally:
        _cleanup(dialog, qapp)


def test_manual_location_mode_uses_page_row_column_text_boxes(qapp):
    dialog = AutomationCommandSoundButtonDialog(
        caption="",
        notes="",
        companion_payload=_payload(),
    )
    dialog.show()
    qapp.processEvents()
    try:
        dialog.manual_location_radio.setChecked(True)
        dialog.manual_page_edit.setText("3")
        dialog.manual_row_edit.setText("4")
        dialog.manual_column_edit.setText("5")
        qapp.processEvents()

        caption, _notes, spec, _custom_color, _sound_hotkey, _sound_midi_hotkey = dialog.values()

        assert dialog.selected_location() == "3/4/5"
        assert dialog.selected_button_text() == ""
        assert caption == "3/4/5"
        assert spec.location == "3/4/5"
        assert spec.button_text == ""
    finally:
        _cleanup(dialog, qapp)
