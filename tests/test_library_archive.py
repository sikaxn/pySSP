import zipfile
from pathlib import Path

from pyssp.library_archive import (
    build_archive_audio_entries,
    build_manifest,
    build_unpack_target_path,
    default_unpack_directory,
    rewrite_packed_set_paths,
    unpack_pyssppak,
    write_manifest,
)


def test_build_archive_audio_entries_keeps_names_unique():
    entries = build_archive_audio_entries(
        [
            r"C:\audio\intro.mp3",
            r"D:\other\intro.mp3",
            r"D:\other\crowd!.wav",
        ],
        maintain_directory_structure=False,
    )

    assert len(entries) == 3
    assert len({entry.archive_member for entry in entries}) == 3
    assert entries[0].archive_member.startswith("audio/001_")
    assert entries[1].archive_member.startswith("audio/002_")
    assert entries[2].archive_member.endswith("crowd_.wav")


def test_rewrite_packed_set_paths_updates_slot_paths(tmp_path):
    set_path = tmp_path / "library.set"
    set_path.write_text(
        "\r\n".join(
            [
                "[Main]",
                "CreatedBy=SportsSounds",
                "",
                "[Page1]",
                "s1=audio/001_song.mp3",
                "s2=audio/002_song.wav",
                "c1=Song 1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    rewrite_packed_set_paths(
        str(set_path),
        {
            "audio/001_song.mp3": r"C:\dump\audio\001_song.mp3",
            "audio/002_song.wav": r"C:\dump\audio\002_song.wav",
        },
    )

    text = set_path.read_text(encoding="utf-8")
    assert r"s1=C:\dump\audio\001_song.mp3" in text
    assert r"s2=C:\dump\audio\002_song.wav" in text


def test_write_and_unpack_pyssppak_round_trip(tmp_path):
    source_set = tmp_path / "source.set"
    source_set.write_text("[Main]\r\nCreatedBy=SportsSounds\r\n", encoding="utf-8")
    source_audio = tmp_path / "song.mp3"
    source_audio.write_bytes(b"fake-audio")
    source_settings = tmp_path / "settings.ini"
    source_settings.write_text("[main]\nvolume=50\n", encoding="utf-8")

    audio_entries = build_archive_audio_entries([str(source_audio)], maintain_directory_structure=False)
    package_path = tmp_path / "library.pyssppak"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(str(source_audio), arcname=audio_entries[0].archive_member)
        archive.write(str(source_set), arcname="library.set")
        archive.write(str(source_settings), arcname="settings.ini")
        write_manifest(archive, build_manifest("library.set", audio_entries, settings_included=True))

    output_dir = tmp_path / "unpacked"
    result = unpack_pyssppak(str(package_path), str(output_dir), maintain_directory_structure=False)

    assert Path(result.extracted_set_path).exists()
    assert Path(result.extracted_settings_path).exists()
    assert "audio/001_song.mp3" in result.audio_path_map
    assert Path(result.audio_path_map["audio/001_song.mp3"]).read_bytes() == b"fake-audio"


def test_build_archive_audio_entries_can_preserve_structure():
    entries = build_archive_audio_entries([r"C:\Show\FX\crowd.wav"], maintain_directory_structure=True)
    assert entries[0].archive_member == "audio/C/Show/FX/crowd.wav"


def test_unpack_target_path_flattens_when_requested(tmp_path):
    used_targets: set[str] = set()
    target_a = build_unpack_target_path(str(tmp_path), "audio/C/Show/FX/crowd.wav", False, used_targets)
    target_b = build_unpack_target_path(str(tmp_path), "audio/D/Alt/crowd.wav", False, used_targets)

    assert target_a.endswith(r"audio\crowd.wav")
    assert target_b.endswith(r"audio\crowd_2.wav")


def test_default_unpack_directory_uses_pyssp_config_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    path = default_unpack_directory("/tmp/pyssp_audio_library_20260228_214421.pyssppak")

    assert Path(path) == (tmp_path / ".config" / "pyssp" / "unpack" / "pyssp_audio_library_20260228_214421").resolve()
