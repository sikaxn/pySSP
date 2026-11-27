from __future__ import annotations

from types import SimpleNamespace

import pytest

from pyssp.automation_command import AutomationCommandSpec
from pyssp.automation_script import (
    AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
    AUTOMATION_SCRIPT_ACTION_TYPE_INTERNAL_COMMAND,
    AutomationScript,
    AutomationScriptAction,
    AutomationScriptCue,
)
from pyssp.ui.main_window.companion_satellite import CompanionSatelliteMixin


def test_build_automation_script_specs_accepts_automation_command_spec_payload():
    actions = [
        AutomationScriptAction(
            type=AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
            payload=AutomationCommandSpec(location="1/2/3", button_text="Intro"),
        )
    ]

    specs = CompanionSatelliteMixin._build_automation_script_specs(object(), actions)

    assert len(specs) == 1
    assert specs[0].location == "1/2/3"
    assert specs[0].button_text == "Intro"
    assert specs[0].hold_to_release is False


def test_build_automation_script_specs_accepts_internal_payload():
    actions = [
        AutomationScriptAction(
            type=AUTOMATION_SCRIPT_ACTION_TYPE_INTERNAL_COMMAND,
            payload=AutomationCommandSpec(
                source="internal",
                internal_command="volume_set",
                internal_params={"level": 80},
            ),
        )
    ]

    specs = CompanionSatelliteMixin._build_automation_script_specs(object(), actions)

    assert len(specs) == 1
    assert specs[0].source == "internal"
    assert specs[0].internal_command == "volume_set"
    assert specs[0].internal_params == {"level": 80}


class _ScriptRuntime(CompanionSatelliteMixin):
    def __init__(self):
        self._automation_script_runtime = {}
        self.slot = SimpleNamespace(
            automation_script_path="test.pysspautoscript",
            automation_script_bypassed=False,
        )
        self.script = AutomationScript(
            cues=[
                AutomationScriptCue(
                    time_ms=time_ms,
                    actions=[
                        AutomationScriptAction(payload=AutomationCommandSpec(location=location))
                    ],
                )
                for time_ms, location in [(0, "11/3/7"), (500, "11/1/6"), (1000, "11/1/4")]
            ]
        )
        self.executed = []

    def _slot_for_key(self, _slot_key):
        return self.slot

    def _slot_has_automation_script(self, _slot):
        return True

    def _load_automation_script_cached(self, _path):
        return self.script, ""

    def _execute_automation_command_specs(self, specs):
        self.executed.extend(spec.location for spec in specs)
        return True


@pytest.mark.parametrize("start_ms", [0, 500])
def test_playback_start_executes_cue_at_start_once(start_ms):
    runtime = _ScriptRuntime()
    player = SimpleNamespace(position=lambda: start_ms)

    runtime._prime_automation_script_player(player, ("A", 0, 0))

    first_location = "11/3/7" if start_ms == 0 else "11/1/6"
    assert runtime.executed == [first_location]

    for position_ms in sorted([start_ms, start_ms + 90, 500, 1000, 1000]):
        player.position = lambda pos=position_ms: pos
        runtime._process_automation_script_player(player)

    expected = ["11/3/7", "11/1/6", "11/1/4"] if start_ms == 0 else ["11/1/6", "11/1/4"]
    assert runtime.executed == expected


def test_seeking_resync_does_not_execute_cues_at_or_before_seek_target():
    runtime = _ScriptRuntime()
    player = SimpleNamespace(position=lambda: 0)
    runtime._prime_automation_script_player(player, ("A", 0, 0))
    runtime.executed.clear()

    player.position = lambda: 500
    runtime._resync_automation_script_player_for_position(player, 500)
    runtime._process_automation_script_player(player)
    assert runtime.executed == []

    player.position = lambda: 1000
    runtime._process_automation_script_player(player)
    assert runtime.executed == ["11/1/4"]
