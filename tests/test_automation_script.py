from __future__ import annotations

import json

import pytest

from pyssp.automation_command import AutomationCommandSpec
from pyssp.automation_script import (
    AUTOMATION_SCRIPT_FORMAT,
    AUTOMATION_SCRIPT_VERSION,
    AutomationScript,
    AutomationScriptAction,
    AutomationScriptCue,
    automation_script_to_dict,
    load_automation_script,
    save_automation_script,
)


def test_automation_script_round_trip_merges_duplicate_timestamps(tmp_path):
    script = AutomationScript(
        notes="demo",
        cues=[
            AutomationScriptCue(
                time_ms=1000,
                comment="Intro",
                actions=[
                    AutomationScriptAction(
                        payload=AutomationCommandSpec(location="1/2/3", button_text="One")
                    )
                ],
            ),
            AutomationScriptCue(
                time_ms=1000,
                comment="",
                actions=[
                    AutomationScriptAction(
                        payload=AutomationCommandSpec(location="1/2/4", button_text="Two")
                    )
                ],
            ),
        ],
    )
    path = tmp_path / "demo.pysspautoscript"

    save_automation_script(str(path), script)
    loaded = load_automation_script(str(path))

    assert loaded.notes == "demo"
    assert loaded.cues is not None
    assert len(loaded.cues) == 1
    assert loaded.cues[0].time_ms == 1000
    assert loaded.cues[0].comment == "Intro"
    assert [action.payload.location for action in loaded.cues[0].actions or []] == ["1/2/3", "1/2/4"]


def test_automation_script_rejects_unsupported_version(tmp_path):
    path = tmp_path / "bad.pysspautoscript"
    path.write_text(
        json.dumps(
            {
                "format": AUTOMATION_SCRIPT_FORMAT,
                "version": AUTOMATION_SCRIPT_VERSION + 1,
                "notes": "",
                "cues": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported automation script version"):
        load_automation_script(str(path))


def test_automation_script_to_dict_keeps_empty_script_shape():
    payload = automation_script_to_dict(AutomationScript(notes="", cues=[]))

    assert payload == {
        "format": AUTOMATION_SCRIPT_FORMAT,
        "version": AUTOMATION_SCRIPT_VERSION,
        "notes": "",
        "cues": [],
    }
