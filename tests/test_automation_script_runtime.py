from __future__ import annotations

from pyssp.automation_command import AutomationCommandSpec
from pyssp.automation_script import (
    AUTOMATION_SCRIPT_ACTION_TYPE_COMPANION_COMMAND,
    AUTOMATION_SCRIPT_ACTION_TYPE_INTERNAL_COMMAND,
    AutomationScriptAction,
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
