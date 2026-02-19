import configparser
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.settings_store import _from_parser


def test_timecode_and_main_timeline_modes_are_independent():
    parser = configparser.ConfigParser()
    parser["main"] = {
        "timecode_timeline_mode": "audio_file",
        "main_transport_timeline_mode": "cue_region",
    }
    settings = _from_parser(parser)
    assert settings.timecode_timeline_mode == "audio_file"
    assert settings.main_transport_timeline_mode == "cue_region"


def test_timecode_timeline_mode_falls_back_to_main_when_missing():
    parser = configparser.ConfigParser()
    parser["main"] = {
        "main_transport_timeline_mode": "audio_file",
    }
    settings = _from_parser(parser)
    assert settings.timecode_timeline_mode == "audio_file"
