from __future__ import annotations

from PyQt5.QtWidgets import QApplication

from pyssp.audio_beat_map import AudioBeatMap
from pyssp.ui.edit_sound_button_dialog import EditSoundButtonDialog


def test_edit_sound_button_dialog_round_trips_audio_beat_map():
    app = QApplication.instance() or QApplication([])
    dialog = EditSoundButtonDialog(
        file_path="theme.mp3",
        caption="Theme",
        notes="Theme",
        audio_beat_map=AudioBeatMap(
            bpm=128.5,
            time_signature_num=3,
            time_signature_den=4,
            first_downbeat_ms=250,
            beat_times_ms=[250, 719],
            beat_numbers=[1, 2],
            source="librosa",
            confidence=0.75,
        ),
    )

    values = dialog.values()
    beat_map = values[-1]

    assert beat_map is not None
    assert beat_map.bpm == 128.5
    assert beat_map.time_signature_num == 3
    assert beat_map.first_downbeat_ms == 250
    assert app is not None


def test_edit_sound_button_dialog_clear_audio_analysis():
    app = QApplication.instance() or QApplication([])
    dialog = EditSoundButtonDialog(
        file_path="theme.mp3",
        caption="Theme",
        notes="Theme",
        audio_beat_map=AudioBeatMap(bpm=120.0),
    )

    dialog._clear_audio_analysis()
    values = dialog.values()

    assert values[-1] is None
    assert app is not None
