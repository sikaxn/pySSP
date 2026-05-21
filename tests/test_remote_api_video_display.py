from __future__ import annotations

from pyssp.display_focus import DISPLAY_FOCUS_FOLLOW, normalize_display_route_source
from pyssp.ui.main_window.remote_api import RemoteApiMixin
from pyssp.ui.main_window.video_display import VideoDisplayMixin


class _FakeCheckbox:
    def __init__(self) -> None:
        self.checked = False

    def blockSignals(self, _blocked: bool) -> None:
        return None

    def setChecked(self, value: bool) -> None:
        self.checked = bool(value)

    def isChecked(self) -> bool:
        return bool(self.checked)


class _FakeCombo:
    def __init__(self, values: list[str]) -> None:
        self._values = list(values)
        self._index = 0

    def blockSignals(self, _blocked: bool) -> None:
        return None

    def findData(self, value: str) -> int:
        try:
            return self._values.index(value)
        except ValueError:
            return -1

    def setCurrentIndex(self, index: int) -> None:
        self._index = max(0, min(int(index), len(self._values) - 1))

    def currentData(self) -> str:
        return self._values[self._index]


class _VideoDisplayRemoteHarness(VideoDisplayMixin, RemoteApiMixin):
    def __init__(self) -> None:
        self.video_display_mode_playing = DISPLAY_FOCUS_FOLLOW
        self.video_display_mode_idle = "blank"
        self.ndi_output_mode_playing = DISPLAY_FOCUS_FOLLOW
        self.ndi_output_mode_idle = "backdrop"
        self.video_follow_sound_button_focus_checkbox = _FakeCheckbox()
        self.video_route_combo = _FakeCombo(
            [
                "video",
                "image",
                "lyric_display",
                "stage_display",
                "metronome_display",
                "backdrop",
                "blank",
                "white_screen",
                "colour_bars",
            ]
        )
        self.refresh_calls: list[bool] = []

    def _active_video_route_mode(self) -> str:
        if self._video_display_follow_sound_button_focus_enabled():
            return normalize_display_route_source(self.video_display_mode_idle, default="blank")
        return normalize_display_route_source(self.video_display_mode_playing, default="blank")

    def _refresh_video_display(self, force: bool = False) -> None:
        self.refresh_calls.append(bool(force))

    def _api_state(self) -> dict:
        return {
            "marker": "state",
            **self._video_display_route_state_payload(),
        }


def test_remote_api_video_display_set_source_override_updates_all_route_fields():
    host = _VideoDisplayRemoteHarness()

    result = host._handle_web_remote_command(
        "video_display",
        {"action": "set_source_override", "source": "stage_display"},
    )

    assert result["ok"] is True
    assert host.video_display_mode_playing == "stage_display"
    assert host.video_display_mode_idle == "stage_display"
    assert host.ndi_output_mode_playing == "stage_display"
    assert host.ndi_output_mode_idle == "stage_display"
    assert host.video_follow_sound_button_focus_checkbox.isChecked() is False
    assert host.video_route_combo.currentData() == "stage_display"
    assert result["result"]["video_display_follow_sound_button_focus"] is False
    assert result["result"]["video_display_manual_source"] == "stage_display"
    assert result["result"]["video_display_active_source"] == "stage_display"
    assert result["result"]["state"]["marker"] == "state"
    assert host.refresh_calls == [True]


def test_remote_api_video_display_set_source_only_preserves_follow_state():
    host = _VideoDisplayRemoteHarness()

    result = host._handle_web_remote_command(
        "video_display",
        {"action": "set_source_only", "source": "image"},
    )

    assert result["ok"] is True
    assert host.video_display_mode_playing == DISPLAY_FOCUS_FOLLOW
    assert host.video_display_mode_idle == "image"
    assert host.ndi_output_mode_playing == DISPLAY_FOCUS_FOLLOW
    assert host.ndi_output_mode_idle == "image"
    assert host.video_follow_sound_button_focus_checkbox.isChecked() is True
    assert host.video_route_combo.currentData() == "image"
    assert result["result"]["video_display_follow_sound_button_focus"] is True
    assert result["result"]["video_display_manual_source"] == "image"
    assert result["result"]["video_display_active_source"] == "image"


def test_remote_api_video_display_follow_enable_disable_and_toggle():
    host = _VideoDisplayRemoteHarness()
    host.video_display_mode_idle = "backdrop"
    host.ndi_output_mode_idle = "backdrop"

    disabled = host._handle_web_remote_command("video_display", {"action": "follow", "mode": "disable"})
    assert disabled["ok"] is True
    assert host.video_display_mode_playing == "backdrop"
    assert host.ndi_output_mode_playing == "backdrop"
    assert host.video_follow_sound_button_focus_checkbox.isChecked() is False

    enabled = host._handle_web_remote_command("video_display", {"action": "follow", "mode": "enable"})
    assert enabled["ok"] is True
    assert host.video_display_mode_playing == DISPLAY_FOCUS_FOLLOW
    assert host.ndi_output_mode_playing == DISPLAY_FOCUS_FOLLOW
    assert host.video_follow_sound_button_focus_checkbox.isChecked() is True

    toggled = host._handle_web_remote_command("video_display", {"action": "follow", "mode": "toggle"})
    assert toggled["ok"] is True
    assert host.video_display_mode_playing == "backdrop"
    assert host.ndi_output_mode_playing == "backdrop"
    assert host.video_follow_sound_button_focus_checkbox.isChecked() is False


def test_remote_api_video_display_rejects_invalid_source_and_mode():
    host = _VideoDisplayRemoteHarness()

    bad_action = host._handle_web_remote_command(
        "video_display",
        {"action": "not-an-action", "source": "stage_display"},
    )
    assert bad_action["ok"] is False
    assert bad_action["error"]["code"] == "invalid_action"

    bad_source = host._handle_web_remote_command(
        "video_display",
        {"action": "set_source_override", "source": "not-a-route"},
    )
    assert bad_source["ok"] is False
    assert bad_source["error"]["code"] == "invalid_source"

    bad_mode = host._handle_web_remote_command(
        "video_display",
        {"action": "follow", "mode": "not-a-mode"},
    )
    assert bad_mode["ok"] is False
    assert bad_mode["error"]["code"] == "invalid_mode"
