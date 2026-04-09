from pyssp.lyrics import line_for_position, parse_lyric_file


def test_parse_lrc_and_pick_line(tmp_path):
    path = tmp_path / "song.lrc"
    path.write_text(
        "\n".join(
            [
                "[00:01.00]Line One",
                "[00:02.50]Line Two",
            ]
        ),
        encoding="utf-8",
    )
    lines = parse_lyric_file(str(path))
    assert line_for_position(lines, 1000) == "Line One"
    assert line_for_position(lines, 2500) == "Line Two"


def test_parse_srt_and_pick_line(tmp_path):
    path = tmp_path / "song.srt"
    path.write_text(
        "\n".join(
            [
                "1",
                "00:00:01,000 --> 00:00:02,000",
                "Hello",
                "",
                "2",
                "00:00:03,000 --> 00:00:04,500",
                "World",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = parse_lyric_file(str(path))
    assert line_for_position(lines, 1500) == "Hello"
    assert line_for_position(lines, 3500) == "World"


def test_parse_lrc_gbk_chinese(tmp_path):
    path = tmp_path / "cn_gbk.lrc"
    raw = "\n".join(
        [
            "[00:01.00]春风十里",
            "[00:02.00]报新年",
        ]
    )
    path.write_bytes(raw.encode("gbk"))
    lines = parse_lyric_file(str(path))
    assert line_for_position(lines, 1000) == "春风十里"
    assert line_for_position(lines, 2000) == "报新年"


def test_parse_lrc_utf16_chinese(tmp_path):
    path = tmp_path / "cn_utf16.lrc"
    raw = "\n".join(
        [
            "[00:01.00]春风十里",
            "[00:02.00]报新年",
        ]
    )
    path.write_text(raw, encoding="utf-16")
    lines = parse_lyric_file(str(path))
    assert line_for_position(lines, 1000) == "春风十里"
    assert line_for_position(lines, 2000) == "报新年"


def test_parse_lrc_cp1252_western_text(tmp_path):
    path = tmp_path / "en_cp1252.lrc"
    raw = "\n".join(
        [
            "[00:01.00]Because of you - I'm afraid",
            "[00:02.00]I lose my way",
        ]
    )
    path.write_bytes(raw.encode("cp1252"))
    lines = parse_lyric_file(str(path))
    assert line_for_position(lines, 1000) == "Because of you - I'm afraid"
    assert line_for_position(lines, 2000) == "I lose my way"


def test_line_for_position_uses_nearest_line(tmp_path):
    path = tmp_path / "nearest.lrc"
    path.write_text(
        "\n".join(
            [
                "[00:10.00]A",
                "[00:20.00]B",
            ]
        ),
        encoding="utf-8",
    )
    lines = parse_lyric_file(str(path))
    assert line_for_position(lines, 0) == ""
    assert line_for_position(lines, 15000) == "A"
    assert line_for_position(lines, 25000) == "B"


def test_parse_lrc_offset(tmp_path):
    path = tmp_path / "offset.lrc"
    path.write_text(
        "\n".join(
            [
                "[offset:1000]",
                "[00:01.00]Line",
            ]
        ),
        encoding="utf-8",
    )
    lines = parse_lyric_file(str(path))
    assert line_for_position(lines, 1500) == "Line"
    assert line_for_position(lines, 2000) == "Line"
