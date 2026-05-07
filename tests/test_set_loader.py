from pyssp.automation_command import (
    AUTOMATION_SOURCE_TYPE,
    AUTOMATION_UNSUPPORTED_MARKER_TEXT,
    SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
)
from pyssp.set_loader import load_set_file, parse_delphi_color, parse_time_string_to_ms
from pyssp.utility_audio import FILE_SOURCE_TYPE, UTILITY_SOURCE_TYPE


def test_parse_time_mm_ss():
    assert parse_time_string_to_ms('03:20') == 200000


def test_parse_time_hh_mm_ss():
    assert parse_time_string_to_ms('01:02:03') == 3723000


def test_parse_time_invalid():
    assert parse_time_string_to_ms('abc') == 0


def test_parse_delphi_named_color():
    assert parse_delphi_color('clPurple') == '#800080'


def test_parse_delphi_bgr_hex_color():
    assert parse_delphi_color('$00FF8000') == '#0080FF'


def test_load_set_activity_marks_played(tmp_path):
    set_path = tmp_path / "activity.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "activity1=2",
                "c2=Song Two",
                "s2=C:\\\\Music\\\\song2.mp3",
                "activity2=8",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    assert result.pages["A"][0][0].played is True
    assert result.pages["A"][0][1].played is False


def test_load_set_volume_override(tmp_path):
    set_path = tmp_path / "volume.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "v1=67",
                "c2=Song Two",
                "s2=C:\\\\Music\\\\song2.mp3",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    assert result.pages["A"][0][0].volume_override_pct == 67
    assert result.pages["A"][0][1].volume_override_pct is None


def test_load_set_cue_points_in_ms(tmp_path):
    set_path = tmp_path / "cue_ms.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "t1=03:20",
                "cs1=12000",
                "ce1=30000",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.cue_start_ms == 12000
    assert slot.cue_end_ms == 30000
    assert result.migrated_legacy_cues is True


def test_load_set_cue_points_scaled_from_large_values(tmp_path):
    set_path = tmp_path / "cue_scaled.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "t1=04:00",
                "cs1=600000",
                "ce1=24000000",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.cue_start_ms == 6000
    assert slot.cue_end_ms == 240000
    assert result.migrated_legacy_cues is True


def test_load_set_cue_start_scaled_when_end_missing(tmp_path):
    set_path = tmp_path / "cue_cs_only_scaled.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "t1=03:20",
                "cs1=335161",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.cue_start_ms == 1900
    assert slot.cue_end_ms is None
    assert result.migrated_legacy_cues is True


def test_load_set_cue_points_from_pyssp_time_fields(tmp_path):
    set_path = tmp_path / "cue_pyssp_time.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "t1=03:20",
                "pysspcuestart1=00:12:15",
                "pysspcueend1=00:30:00",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.cue_start_ms == 12500
    assert slot.cue_end_ms == 30000
    assert result.migrated_legacy_cues is False


def test_load_set_prefers_pyssp_cue_fields_over_legacy_cs_ce(tmp_path):
    set_path = tmp_path / "cue_pyssp_preferred.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "t1=03:20",
                "pysspcuestart1=00:01:00",
                "pysspcueend1=00:10:00",
                "cs1=12000",
                "ce1=30000",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.cue_start_ms == 1000
    assert slot.cue_end_ms == 10000
    assert result.migrated_legacy_cues is False


def test_load_set_lyric_file_field(tmp_path):
    set_path = tmp_path / "lyrics.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "pyssplyric1=C:\\\\Lyrics\\\\song1.lrc",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.lyric_file == "C:\\Lyrics\\song1.lrc"


def test_load_set_utility_sound_button_reconstructs_source_from_pyssp_fields(tmp_path):
    set_path = tmp_path / "utility.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Unsupported utility sound button. A newer version of pySSP is required.%%",
                "n1=Unsupported utility sound button. A newer version of pySSP is required.",
                "t1= ",
                "activity1=7",
                "co1=clBtnFace",
                "pysspsourcetype1=utility",
                "pyssputilitymode1=metronome",
                "pyssputilityduration1=00:00:10:250",
                "pyssputilitytitle1=Count In",
                "pyssputilitynotes1=Utility note",
                "pyssputilitylyric1=C:\\\\Lyrics\\\\countin.lrc",
                "pyssputilitytempo1=123",
                "pyssputilitytimesig1=3/4",
                "pyssputilityplayed1=1",
                "v1=66",
                "pysspcuestart1=00:01:00",
                "pysspcueend1=00:04:00",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.source_type == UTILITY_SOURCE_TYPE
    assert slot.marker is False
    assert slot.file_path == ""
    assert slot.title == "Count In"
    assert slot.notes == "Utility note"
    assert slot.lyric_file == "C:\\Lyrics\\countin.lrc"
    assert slot.duration_ms == 10250
    assert slot.utility_spec is not None
    assert slot.utility_spec.mode == "metronome"
    assert slot.utility_spec.tempo_bpm == 123.0
    assert slot.utility_spec.time_signature_num == 3
    assert slot.utility_spec.time_signature_den == 4
    assert slot.played is True
    assert slot.volume_override_pct == 66
    assert slot.cue_start_ms == 1000
    assert slot.cue_end_ms == 4000


def test_load_set_marker_fallback_without_utility_source_type_stays_marker(tmp_path):
    set_path = tmp_path / "utility_legacy_marker.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Unsupported utility sound button. A newer version of pySSP is required.%%",
                "n1=Unsupported utility sound button. A newer version of pySSP is required.",
                "t1= ",
                "activity1=7",
                "co1=clBtnFace",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.marker is True
    assert slot.source_type == FILE_SOURCE_TYPE
    assert slot.utility_spec is None


def test_load_set_automation_sound_button_reconstructs_source_from_pyssp_fields(tmp_path):
    set_path = tmp_path / "automation.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=T",
                "PageShuffle=F",
                f"c1={AUTOMATION_UNSUPPORTED_MARKER_TEXT}%%",
                f"n1={AUTOMATION_UNSUPPORTED_MARKER_TEXT}",
                "t1= ",
                "activity1=7",
                "co1=clBtnFace",
                f"pysspsourcetype1={AUTOMATION_SOURCE_TYPE}",
                "pysspautomationlocation1=5/1/2",
                "pysspautomationtext1=Take Camera 1",
                "pysspautomationhold1=1",
                "pysspautomationtitle1=Camera Take",
                "pysspautomationnotes1=Runs companion automation",
                "pysspautomationcolor1=$007AC6E8",
                "pysspautomationplayed1=1",
                "pysspautomationhotkey1=0F1",
                "pysspautomationmidi1=90:3C",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.source_type == AUTOMATION_SOURCE_TYPE
    assert slot.marker is False
    assert slot.file_path == ""
    assert slot.duration_ms == 0
    assert slot.title == "Camera Take"
    assert slot.notes == "Runs companion automation"
    assert slot.played is True
    assert slot.activity_code == "7"
    assert slot.custom_color == "#E8C67A"
    assert slot.sound_hotkey == "F1"
    assert slot.sound_midi_hotkey == "90:3C"
    assert slot.automation_spec is not None
    assert slot.automation_spec.location == "5/1/2"
    assert slot.automation_spec.button_text == "Take Camera 1"
    assert slot.automation_spec.hold_to_release is True


def test_load_set_sound_button_simple_automation_round_trip_fields(tmp_path):
    set_path = tmp_path / "sound_button_automation.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                "c1=Song One",
                "s1=C:\\\\Music\\\\song1.mp3",
                "pysspsbamode1=simple",
                "pyssponbecomeplayingcount1=2",
                "pyssponbecomeplayinglocation1_1=5/1/2",
                "pyssponbecomeplayingtext1_1=Start One",
                "pyssponbecomeplayinglocation1_2=5/1/3",
                "pyssponbecomeplayingtext1_2=Start Two",
                "pyssponleaveplayingcount1=1",
                "pyssponleaveplayinglocation1_1=5/1/4",
                "pyssponleaveplayingtext1_1=Stop One",
                "pysspsbabypass1=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.sound_button_automation is not None
    assert slot.sound_button_automation.mode == SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
    assert slot.sound_button_automation.on_become_playing is not None
    assert [item.location for item in slot.sound_button_automation.on_become_playing] == ["5/1/2", "5/1/3"]
    assert [item.button_text for item in slot.sound_button_automation.on_become_playing] == ["Start One", "Start Two"]
    assert slot.sound_button_automation.on_leave_playing is not None
    assert [item.location for item in slot.sound_button_automation.on_leave_playing] == ["5/1/4"]
    assert slot.sound_button_automation.bypassed is True


def test_load_set_internal_automation_slot_fields(tmp_path):
    set_path = tmp_path / "internal_automation.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                f"c1={AUTOMATION_UNSUPPORTED_MARKER_TEXT}%%",
                f"n1={AUTOMATION_UNSUPPORTED_MARKER_TEXT}",
                "t1= ",
                "activity1=7",
                "co1=clBtnFace",
                "pysspsourcetype1=automation",
                "pysspautomationsource1=internal",
                "pysspautomationinternalcommand1=volume_set",
                "pysspautomationinternalparams1={\"level\":70}",
                "pysspautomationtitle1=Set Volume 70%",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.automation_spec is not None
    assert slot.automation_spec.source == "internal"
    assert slot.automation_spec.internal_command == "volume_set"
    assert slot.automation_spec.internal_params == {"level": 70}
    assert slot.title == "Set Volume 70%"


def test_load_set_legacy_unsupported_automation_marker_stays_marker_without_pyssp_metadata(tmp_path):
    set_path = tmp_path / "automation_legacy_marker.set"
    set_path.write_text(
        "\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "PageName=Page 1",
                "PagePlay=F",
                "PageShuffle=F",
                f"c1={AUTOMATION_UNSUPPORTED_MARKER_TEXT}%%",
                f"n1={AUTOMATION_UNSUPPORTED_MARKER_TEXT}",
                "t1= ",
                "activity1=7",
                "co1=clBtnFace",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = load_set_file(str(set_path))
    slot = result.pages["A"][0][0]
    assert slot.source_type == FILE_SOURCE_TYPE
    assert slot.marker is True
    assert slot.automation_spec is None
    assert slot.title == AUTOMATION_UNSUPPORTED_MARKER_TEXT
    assert slot.notes == AUTOMATION_UNSUPPORTED_MARKER_TEXT
