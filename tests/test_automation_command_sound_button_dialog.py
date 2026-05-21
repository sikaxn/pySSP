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


def _select_internal_command(dialog: AutomationCommandSoundButtonDialog, command_id: str) -> None:
    dialog.source_tabs.setCurrentIndex(1)
    for row in range(dialog.internal_command_list.count()):
        item = dialog.internal_command_list.item(row)
        if item is not None and item.data(256) == command_id:
            dialog.internal_command_list.setCurrentRow(row)
            return


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


def test_internal_command_tab_returns_internal_spec(qapp):
    dialog = AutomationCommandSoundButtonDialog(
        caption="",
        notes="",
        companion_payload=_payload(),
    )
    dialog.show()
    qapp.processEvents()
    try:
        _select_internal_command(dialog, "volume_set")
        qapp.processEvents()
        dialog.internal_volume_spin.setValue(75)
        qapp.processEvents()

        caption, _notes, spec, _custom_color, _sound_hotkey, _sound_midi_hotkey = dialog.values()

        assert spec.source == "internal"
        assert spec.internal_command == "volume_set"
        assert spec.internal_params == {"level": 75}
        assert caption == "Set Volume 75%"
    finally:
        _cleanup(dialog, qapp)


def test_internal_play_command_supports_list_target_picker(qapp):
    dialog = AutomationCommandSoundButtonDialog(
        caption="",
        notes="",
        companion_payload=_payload(),
        internal_target_catalog={
            "page_labels": {"B-3": "B-3 - Chorus"},
            "button_labels": {"B-3-5": "B-3-5 - Lead Vocal"},
        },
    )
    dialog.show()
    qapp.processEvents()
    try:
        _select_internal_command(dialog, "play")
        qapp.processEvents()
        dialog.internal_target_input_mode_combo.setCurrentIndex(
            max(0, dialog.internal_target_input_mode_combo.findData("list"))
        )
        dialog.internal_target_group_combo.setCurrentIndex(
            max(0, dialog.internal_target_group_combo.findData("B"))
        )
        dialog.internal_target_page_combo.setCurrentIndex(
            max(0, dialog.internal_target_page_combo.findData(3))
        )
        dialog.internal_target_slot_combo.setCurrentIndex(
            max(0, dialog.internal_target_slot_combo.findData(5))
        )
        qapp.processEvents()

        assert dialog.internal_target_page_combo.currentText() == "B-3 - Chorus"
        assert dialog.internal_target_slot_combo.currentText() == "B-3-5 - Lead Vocal"

        _caption, _notes, spec, _custom_color, _sound_hotkey, _sound_midi_hotkey = dialog.values()

        assert spec.source == "internal"
        assert spec.internal_command == "play"
        assert spec.internal_params == {"button_id": "b-3-5"}
    finally:
        _cleanup(dialog, qapp)


def test_internal_goto_command_supports_list_page_picker(qapp):
    dialog = AutomationCommandSoundButtonDialog(
        caption="",
        notes="",
        companion_payload=_payload(),
        internal_target_catalog={
            "page_labels": {"C-7": "C-7 - Bridge"},
        },
    )
    dialog.show()
    qapp.processEvents()
    try:
        _select_internal_command(dialog, "goto")
        qapp.processEvents()
        dialog.internal_target_input_mode_combo.setCurrentIndex(
            max(0, dialog.internal_target_input_mode_combo.findData("list"))
        )
        dialog.internal_target_kind_combo.setCurrentIndex(
            max(0, dialog.internal_target_kind_combo.findData("page"))
        )
        dialog.internal_target_group_combo.setCurrentIndex(
            max(0, dialog.internal_target_group_combo.findData("C"))
        )
        dialog.internal_target_page_combo.setCurrentIndex(
            max(0, dialog.internal_target_page_combo.findData(7))
        )
        qapp.processEvents()

        assert dialog.internal_target_page_combo.currentText() == "C-7 - Bridge"

        _caption, _notes, spec, _custom_color, _sound_hotkey, _sound_midi_hotkey = dialog.values()

        assert spec.source == "internal"
        assert spec.internal_command == "goto"
        assert spec.internal_params == {"target": "c-7"}
    finally:
        _cleanup(dialog, qapp)


def test_internal_target_commands_appear_first(qapp):
    dialog = AutomationCommandSoundButtonDialog(
        caption="",
        notes="",
        companion_payload=_payload(),
    )
    dialog.show()
    qapp.processEvents()
    try:
        dialog.source_tabs.setCurrentIndex(1)
        qapp.processEvents()
        assert dialog.internal_command_list.item(0).data(256) == "play"
        assert dialog.internal_command_list.item(1).data(256) == "goto"
    finally:
        _cleanup(dialog, qapp)


def test_internal_video_display_command_supports_action_specific_fields(qapp):
    dialog = AutomationCommandSoundButtonDialog(
        caption="",
        notes="",
        companion_payload=_payload(),
    )
    dialog.show()
    qapp.processEvents()
    try:
        _select_internal_command(dialog, "video_display")
        qapp.processEvents()

        assert dialog.internal_video_display_action_combo.isVisible() is True
        assert dialog.internal_video_display_follow_mode_combo.isVisible() is True
        assert dialog.internal_video_display_source_combo.isVisible() is False

        dialog.internal_video_display_action_combo.setCurrentIndex(
            max(0, dialog.internal_video_display_action_combo.findData("set_source_override"))
        )
        dialog.internal_video_display_source_combo.setCurrentIndex(
            max(0, dialog.internal_video_display_source_combo.findData("stage_display"))
        )
        qapp.processEvents()

        assert dialog.internal_video_display_source_combo.isVisible() is True
        assert dialog.internal_video_display_follow_mode_combo.isVisible() is False

        caption, _notes, spec, _custom_color, _sound_hotkey, _sound_midi_hotkey = dialog.values()

        assert spec.source == "internal"
        assert spec.internal_command == "video_display"
        assert spec.internal_params == {"action": "set_source_override", "source": "stage_display"}
        assert caption == "Video Display Routing: Set Source Stage Display and Disable Follow"

        dialog.internal_video_display_action_combo.setCurrentIndex(
            max(0, dialog.internal_video_display_action_combo.findData("follow"))
        )
        dialog.internal_video_display_follow_mode_combo.setCurrentIndex(
            max(0, dialog.internal_video_display_follow_mode_combo.findData("toggle"))
        )
        qapp.processEvents()

        _caption, _notes, spec, _custom_color, _sound_hotkey, _sound_midi_hotkey = dialog.values()
        assert spec.internal_params == {"action": "follow", "mode": "toggle"}
    finally:
        _cleanup(dialog, qapp)
