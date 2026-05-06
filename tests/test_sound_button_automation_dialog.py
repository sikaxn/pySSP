from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.automation_command import (
    AutomationCommandSpec,
    SOUND_BUTTON_AUTOMATION_MODE_ADVANCED,
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
