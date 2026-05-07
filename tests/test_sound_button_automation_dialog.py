from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.automation_command import (
    AutomationCommandSpec,
    SOUND_BUTTON_AUTOMATION_MODE_ADVANCED,
    SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
    SoundButtonAutomationConfig,
)
from pyssp.ui.sound_button_automation_dialog import SoundButtonAutomationDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _cleanup(dialog: SoundButtonAutomationDialog, qapp: QApplication) -> None:
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()


def test_advanced_mode_uses_trigger_command_table(qapp):
    dialog = SoundButtonAutomationDialog(
        config=SoundButtonAutomationConfig(
            mode=SOUND_BUTTON_AUTOMATION_MODE_ADVANCED,
            on_become_playing=[AutomationCommandSpec(location="1/1/1", button_text="Start")],
            on_play=[AutomationCommandSpec(location="1/1/2", button_text="Play")],
            on_pause=[AutomationCommandSpec(location="1/1/3", button_text="Pause")],
            on_done_play=[AutomationCommandSpec(location="1/1/4", button_text="Done")],
            on_stop=[AutomationCommandSpec(location="1/1/5", button_text="Stop")],
        ),
    )
    dialog.show()
    qapp.processEvents()
    try:
        assert dialog.selected_mode() == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED
        assert dialog.advanced_table.table.columnCount() == 2
        assert dialog.advanced_table.table.horizontalHeaderItem(0).text() == "Trigger"
        assert dialog.advanced_table.table.horizontalHeaderItem(1).text() == "Command"
        assert dialog.advanced_table.table.rowCount() == 5
    finally:
        _cleanup(dialog, qapp)


def test_advanced_mode_groups_rows_back_into_trigger_lists(qapp):
    dialog = SoundButtonAutomationDialog()
    dialog.show()
    qapp.processEvents()
    try:
        dialog.mode_combo.setCurrentIndex(1)
        dialog.advanced_table._rows = [
            ("on_pause", AutomationCommandSpec(location="5/1/4", button_text="Pause One")),
            ("on_play", AutomationCommandSpec(location="5/1/2", button_text="Play One")),
            ("on_play", AutomationCommandSpec(location="5/1/3", button_text="Play Two")),
            ("on_stop", AutomationCommandSpec(location="5/1/5", button_text="Stop One")),
            ("on_leave_playing", AutomationCommandSpec(location="5/1/6", button_text="Leave One")),
        ]
        dialog.advanced_table._refresh_table()
        dialog._on_advanced_rows_changed()
        qapp.processEvents()

        values = dialog.values()

        assert values is not None
        assert values.mode == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED
        assert [item.location for item in values.on_play or []] == ["5/1/2", "5/1/3"]
        assert [item.location for item in values.on_pause or []] == ["5/1/4"]
        assert [item.location for item in values.on_stop or []] == ["5/1/5"]
        assert [item.location for item in values.on_leave_playing or []] == ["5/1/6"]
    finally:
        _cleanup(dialog, qapp)


def test_simple_mode_updates_advanced_rows_when_toggled(qapp):
    dialog = SoundButtonAutomationDialog(
        config=SoundButtonAutomationConfig(
            mode=SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
            on_become_playing=[AutomationCommandSpec(location="2/1/1", button_text="Simple Start")],
            on_leave_playing=[AutomationCommandSpec(location="2/1/2", button_text="Simple Stop")],
            on_pause=[AutomationCommandSpec(location="2/1/5", button_text="Simple Pause")],
            on_resume_complete=[AutomationCommandSpec(location="2/1/6", button_text="Simple Resume")],
        ),
    )
    dialog.show()
    qapp.processEvents()
    try:
        dialog.simple_start_editor.set_commands(
            [AutomationCommandSpec(location="2/1/3", button_text="Edited Start")]
        )
        dialog.simple_stop_editor.set_commands(
            [AutomationCommandSpec(location="2/1/4", button_text="Edited Stop")]
        )
        dialog.simple_pause_editor.set_commands(
            [AutomationCommandSpec(location="2/1/7", button_text="Edited Pause")]
        )
        dialog.simple_resume_editor.set_commands(
            [AutomationCommandSpec(location="2/1/8", button_text="Edited Resume")]
        )
        dialog._on_simple_lists_changed()
        dialog.mode_combo.setCurrentIndex(1)
        qapp.processEvents()

        rows = dialog.advanced_table.rows()

        assert dialog.selected_mode() == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED
        assert ("on_become_playing", AutomationCommandSpec(location="2/1/3", button_text="Edited Start")) in rows
        assert ("on_leave_playing", AutomationCommandSpec(location="2/1/4", button_text="Edited Stop")) in rows
        assert ("on_pause", AutomationCommandSpec(location="2/1/7", button_text="Edited Pause")) in rows
        assert ("on_resume_complete", AutomationCommandSpec(location="2/1/8", button_text="Edited Resume")) in rows
    finally:
        _cleanup(dialog, qapp)


def test_advanced_mode_preserves_extra_rows_when_switching_to_simple_and_back(qapp):
    dialog = SoundButtonAutomationDialog(
        config=SoundButtonAutomationConfig(
            mode=SOUND_BUTTON_AUTOMATION_MODE_ADVANCED,
            on_become_playing=[AutomationCommandSpec(location="3/1/1", button_text="Start")],
            on_trigger=[AutomationCommandSpec(location="3/1/2", button_text="Trigger")],
            on_stop=[AutomationCommandSpec(location="3/1/3", button_text="Stop")],
        ),
    )
    dialog.show()
    qapp.processEvents()
    try:
        dialog.mode_combo.setCurrentIndex(0)
        qapp.processEvents()
        assert [item.location for item in dialog.simple_start_editor.commands()] == ["3/1/1"]
        assert dialog.simple_pause_editor.commands() == []
        assert dialog.simple_resume_editor.commands() == []

        dialog.mode_combo.setCurrentIndex(1)
        qapp.processEvents()

        rows = dialog.advanced_table.rows()
        assert ("on_trigger", AutomationCommandSpec(location="3/1/2", button_text="Trigger")) in rows
        assert ("on_stop", AutomationCommandSpec(location="3/1/3", button_text="Stop")) in rows
    finally:
        _cleanup(dialog, qapp)


def test_dialog_preserves_bypass_checkbox_in_values(qapp):
    dialog = SoundButtonAutomationDialog(
        config=SoundButtonAutomationConfig(
            mode=SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
            bypassed=True,
            on_become_playing=[AutomationCommandSpec(location="4/1/1", button_text="Start")],
        ),
    )
    dialog.show()
    qapp.processEvents()
    try:
        assert dialog.bypass_checkbox.isChecked() is True
        values = dialog.values()
        assert values is not None
        assert values.bypassed is True
        dialog.bypass_checkbox.setChecked(False)
        values = dialog.values()
        assert values is not None
        assert values.bypassed is False
    finally:
        _cleanup(dialog, qapp)
