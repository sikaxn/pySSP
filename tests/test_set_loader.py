from pyssp.set_loader import load_set_file, parse_delphi_color, parse_time_string_to_ms


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
