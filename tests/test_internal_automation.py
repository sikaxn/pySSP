from pyssp.internal_automation import (
    internal_automation_command_summary,
    internal_automation_dispatch,
    normalize_internal_automation_params,
)


def test_video_display_internal_command_normalizes_actions_and_values():
    assert normalize_internal_automation_params(
        "video_display",
        {"action": "set_source_override", "source": "stage_display"},
    ) == {"action": "set_source_override", "source": "stage_display"}
    assert normalize_internal_automation_params(
        "video_display",
        {"action": "set_source_only", "source": "bad-value"},
    ) == {"action": "set_source_only", "source": "backdrop"}
    assert normalize_internal_automation_params(
        "video_display",
        {"action": "follow", "mode": "disable"},
    ) == {"action": "follow", "mode": "disable"}
    assert normalize_internal_automation_params(
        "video_display",
        {"action": "follow", "mode": "bad-value"},
    ) == {"action": "follow", "mode": "toggle"}


def test_video_display_internal_command_summary_is_human_readable():
    assert (
        internal_automation_command_summary(
            "video_display",
            {"action": "set_source_override", "source": "stage_display"},
        )
        == "Video Display Routing: Set Source Stage Display and Disable Follow"
    )
    assert (
        internal_automation_command_summary(
            "video_display",
            {"action": "set_source_only", "source": "backdrop"},
        )
        == "Video Display Routing: Set Source Backdrop"
    )
    assert (
        internal_automation_command_summary(
            "video_display",
            {"action": "follow", "mode": "toggle"},
        )
        == "Video Display Routing: Toggle Follow Sound Button Display Focus"
    )


def test_video_display_internal_command_dispatches_to_shared_remote_command():
    assert internal_automation_dispatch(
        "video_display",
        {"action": "set_source_only", "source": "image"},
    ) == ("video_display", {"action": "set_source_only", "source": "image"})
    assert internal_automation_dispatch(
        "video_display",
        {"action": "follow", "mode": "enable"},
    ) == ("video_display", {"action": "follow", "mode": "enable"})
