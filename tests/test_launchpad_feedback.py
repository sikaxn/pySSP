from __future__ import annotations

from pyssp.ui.main_window.actions_input import ActionsInputMixin
from pyssp.ui.main_window.widgets import SoundButtonData


class _LaunchpadFeedbackHarness(ActionsInputMixin):
    def __init__(self, slot: SoundButtonData, turn_off_empty: bool) -> None:
        self._slot = slot
        self.launchpad_turn_off_empty_sound_button_lights = turn_off_empty

    def _current_page_slots(self):
        return [self._slot]

    def _launchpad_slot_blink_active(self, _slot_index: int) -> bool:
        return False

    def _slot_color(self, _slot: SoundButtonData, _slot_index: int) -> str:
        return "#0B868A"


def test_launchpad_feedback_turns_off_empty_sound_button_lights_by_default() -> None:
    harness = _LaunchpadFeedbackHarness(SoundButtonData(), True)

    assert harness._launchpad_action_feedback_color("slot:0") == "#000000"


def test_launchpad_feedback_can_keep_empty_sound_button_lights_on() -> None:
    harness = _LaunchpadFeedbackHarness(SoundButtonData(), False)

    assert harness._launchpad_action_feedback_color("slot:0") == "#0B868A"


def test_launchpad_feedback_keeps_marker_lights_visible() -> None:
    harness = _LaunchpadFeedbackHarness(SoundButtonData(marker=True), True)

    assert harness._launchpad_action_feedback_color("slot:0") == "#0B868A"
