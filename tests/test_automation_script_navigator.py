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
    toggle_states: list[bool] = []
    window = AutomationScriptNavigatorWindow(
        on_seek_to_ms=seeks.append,
        show_lyric_default=False,
        on_show_lyric_changed=toggle_states.append,
    )
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

        assert window._show_lyric_checkbox.isChecked() is False
        assert window._tree.topLevelItemCount() == 1
        assert window._tree.topLevelItem(0).text(1) == "Cue"
        assert window._tree.topLevelItem(0).text(2) == "Intro"

        window._show_lyric_checkbox.setChecked(True)
        qapp.processEvents()

        assert toggle_states == [True]
        assert window._tree.topLevelItemCount() == 2
        assert window._tree.topLevelItem(0).text(1) == "Lyric"
        assert window._tree.topLevelItem(0).text(2) == "Verse one"
        assert window._tree.topLevelItem(1).text(1) == "Cue"
        assert window._tree.topLevelItem(1).text(2) == "Intro"
        assert window._tree.topLevelItem(1).text(3) == "1/1/1 - Launch"
        assert window._tree.topLevelItem(1).childCount() == 1
        assert window._tree.topLevelItem(1).child(0).text(1) == "Command"

        window._on_item_clicked(window._tree.topLevelItem(1), 0)
        assert seeks == [1500]
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


def test_automation_script_navigator_uses_compact_width_defaults(qapp):
    window = AutomationScriptNavigatorWindow(on_seek_to_ms=lambda _ms: None)
    try:
        assert window.width() <= 560
        assert window.minimumWidth() <= 340
        assert window.sizeHint().width() <= 560
        assert window._tree.columnWidth(0) <= 100
        assert window._tree.columnWidth(1) <= 90
        assert window._tree.columnWidth(3) <= 180
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()
