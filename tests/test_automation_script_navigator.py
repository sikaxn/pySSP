from __future__ import annotations

import os

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.automation_script import (
    AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
    AutomationScript,
    AutomationScriptAction,
    AutomationScriptCue,
    save_automation_script,
)
from pyssp.ui.automation_script_navigator import AutomationScriptNavigatorWindow


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_automation_script_navigator_merges_lyrics_and_cues(qapp, tmp_path):
    script_path = tmp_path / "demo.pysspautoscript"
    lyric_path = tmp_path / "demo.lrc"
    save_automation_script(
        str(script_path),
        AutomationScript(
            notes="",
            cues=[
                AutomationScriptCue(
                    time_ms=1500,
                    comment="Intro",
                    actions=[
                        AutomationScriptAction(
                            type=AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
                            payload={"location": "1/1/1", "button_text": "Launch"},
                        )
                    ],
                )
            ],
        ),
    )
    lyric_path.write_text("[00:01.00]Verse one\n", encoding="utf-8")

    seeks: list[int] = []
    window = AutomationScriptNavigatorWindow(on_seek_to_ms=seeks.append)
    try:
        window.show()
        qapp.processEvents()

        window.update_playback_state(
            has_active_track=True,
            script_path=str(script_path),
            lyric_path=str(lyric_path),
            position_ms=1200,
            force=True,
        )
        qapp.processEvents()

        assert window._table.rowCount() == 2
        assert window._table.item(0, 1).text() == "Lyric"
        assert window._table.item(0, 2).text() == "Verse one"
        assert window._table.item(1, 1).text() == "Cue"
        assert window._table.item(1, 2).text() == "Intro"
        assert window._table.item(1, 3).text() == "1/1/1 - Launch"

        window._on_cell_clicked(1, 0)
        assert seeks == [1500]
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
