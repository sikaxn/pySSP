from __future__ import annotations

from ..shared import *
from ..widgets import *


class PlaybackPageMixin:
    def _build_playback_page(
        self,
        max_multi_play_songs: int,
        multi_play_limit_action: str,
        playlist_play_mode: str,
        rapid_fire_play_mode: str,
        next_play_mode: str,
        playlist_loop_mode: str,
        candidate_error_action: str,
        main_transport_timeline_mode: str,
        main_jog_outside_cue_action: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.max_multi_play_spin = QSpinBox()
        self.max_multi_play_spin.setRange(1, 32)
        self.max_multi_play_spin.setValue(max(1, min(32, int(max_multi_play_songs))))
        form.addRow("Max Multi-Play Songs:", self.max_multi_play_spin)
        layout.addLayout(form)

        limit_group = QGroupBox("When max songs is reached during Multi-Play:")
        limit_layout = QVBoxLayout(limit_group)
        self.multi_play_disallow_radio = QRadioButton("Disallow more play")
        self.multi_play_stop_oldest_radio = QRadioButton("Stop the oldest")
        if multi_play_limit_action == "disallow_more_play":
            self.multi_play_disallow_radio.setChecked(True)
        else:
            self.multi_play_stop_oldest_radio.setChecked(True)
        limit_layout.addWidget(self.multi_play_disallow_radio)
        limit_layout.addWidget(self.multi_play_stop_oldest_radio)
        layout.addWidget(limit_group)

        mode_matrix_group = QGroupBox("Playback Candidate Rules:")
        mode_matrix_layout = QGridLayout(mode_matrix_group)
        mode_matrix_layout.addWidget(QLabel("Control"), 0, 0)
        mode_matrix_layout.addWidget(QLabel("Play unplayed only"), 0, 1)
        mode_matrix_layout.addWidget(QLabel("Play any (ignore red) available"), 0, 2)

        self.playlist_mode_unplayed_radio = QRadioButton("")
        self.playlist_mode_any_radio = QRadioButton("")
        self.playlist_mode_group = QButtonGroup(self)
        self.playlist_mode_group.addButton(self.playlist_mode_unplayed_radio)
        self.playlist_mode_group.addButton(self.playlist_mode_any_radio)
        if playlist_play_mode == "any_available":
            self.playlist_mode_any_radio.setChecked(True)
        else:
            self.playlist_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.playlist_mode_unplayed_radio, 1, 1)
        mode_matrix_layout.addWidget(self.playlist_mode_any_radio, 1, 2)

        self.rapid_fire_mode_unplayed_radio = QRadioButton("")
        self.rapid_fire_mode_any_radio = QRadioButton("")
        self.rapid_fire_mode_group = QButtonGroup(self)
        self.rapid_fire_mode_group.addButton(self.rapid_fire_mode_unplayed_radio)
        self.rapid_fire_mode_group.addButton(self.rapid_fire_mode_any_radio)
        if rapid_fire_play_mode == "any_available":
            self.rapid_fire_mode_any_radio.setChecked(True)
        else:
            self.rapid_fire_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.rapid_fire_mode_unplayed_radio, 2, 1)
        mode_matrix_layout.addWidget(self.rapid_fire_mode_any_radio, 2, 2)

        self.next_mode_unplayed_radio = QRadioButton("")
        self.next_mode_any_radio = QRadioButton("")
        self.next_mode_group = QButtonGroup(self)
        self.next_mode_group.addButton(self.next_mode_unplayed_radio)
        self.next_mode_group.addButton(self.next_mode_any_radio)
        if next_play_mode == "any_available":
            self.next_mode_any_radio.setChecked(True)
        else:
            self.next_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.next_mode_unplayed_radio, 3, 1)
        mode_matrix_layout.addWidget(self.next_mode_any_radio, 3, 2)

        mode_matrix_layout.addWidget(QLabel("Play List"), 1, 0)
        mode_matrix_layout.addWidget(QLabel("Rapid Fire"), 2, 0)
        mode_matrix_layout.addWidget(QLabel("Next"), 3, 0)
        layout.addWidget(mode_matrix_group)

        playlist_loop_group = QGroupBox("When Loop is enabled in Play List:")
        playlist_loop_layout = QVBoxLayout(playlist_loop_group)
        self.playlist_loop_list_radio = QRadioButton("Loop List")
        self.playlist_loop_single_radio = QRadioButton("Loop Single")
        if playlist_loop_mode == "loop_single":
            self.playlist_loop_single_radio.setChecked(True)
        else:
            self.playlist_loop_list_radio.setChecked(True)
        playlist_loop_layout.addWidget(self.playlist_loop_list_radio)
        playlist_loop_layout.addWidget(self.playlist_loop_single_radio)
        layout.addWidget(playlist_loop_group)

        candidate_error_group = QGroupBox("When Play List/Next/Rapid Fire hits audio load error (purple):")
        candidate_error_layout = QVBoxLayout(candidate_error_group)
        self.candidate_error_stop_radio = QRadioButton("Stop playback")
        self.candidate_error_keep_radio = QRadioButton("Keep playing")
        if candidate_error_action == "keep_playing":
            self.candidate_error_keep_radio.setChecked(True)
        else:
            self.candidate_error_stop_radio.setChecked(True)
        candidate_error_layout.addWidget(self.candidate_error_stop_radio)
        candidate_error_layout.addWidget(self.candidate_error_keep_radio)
        layout.addWidget(candidate_error_group)

        cue_group = QGroupBox("Main Player Timeline / Jog Display:")
        cue_layout = QVBoxLayout(cue_group)
        self.cue_timeline_cue_region_radio = QRadioButton("Relative to Cue Set Points")
        self.cue_timeline_audio_file_radio = QRadioButton("Relative to Actual Audio File")
        if main_transport_timeline_mode == "audio_file":
            self.cue_timeline_audio_file_radio.setChecked(True)
        else:
            self.cue_timeline_cue_region_radio.setChecked(True)
        cue_layout.addWidget(self.cue_timeline_cue_region_radio)
        cue_layout.addWidget(self.cue_timeline_audio_file_radio)
        layout.addWidget(cue_group)

        self.jog_outside_group = QGroupBox("When jog is outside cue area (Audio File mode):")
        jog_outside_layout = QVBoxLayout(self.jog_outside_group)
        self.jog_outside_stop_immediately_radio = QRadioButton("Stop immediately")
        self.jog_outside_ignore_cue_radio = QRadioButton("Ignore cue and play until end or stopped")
        self.jog_outside_next_cue_or_stop_radio = QRadioButton(
            "Play to next cue or stop (before start: stop at start; after stop: play to end)"
        )
        self.jog_outside_stop_cue_or_end_radio = QRadioButton(
            "Play to stop cue (before start: stop at stop cue; after stop: play to end)"
        )
        if main_jog_outside_cue_action == "ignore_cue":
            self.jog_outside_ignore_cue_radio.setChecked(True)
        elif main_jog_outside_cue_action == "next_cue_or_stop":
            self.jog_outside_next_cue_or_stop_radio.setChecked(True)
        elif main_jog_outside_cue_action == "stop_cue_or_end":
            self.jog_outside_stop_cue_or_end_radio.setChecked(True)
        else:
            self.jog_outside_stop_immediately_radio.setChecked(True)
        jog_outside_layout.addWidget(self.jog_outside_stop_immediately_radio)
        jog_outside_layout.addWidget(self.jog_outside_ignore_cue_radio)
        jog_outside_layout.addWidget(self.jog_outside_next_cue_or_stop_radio)
        jog_outside_layout.addWidget(self.jog_outside_stop_cue_or_end_radio)
        layout.addWidget(self.jog_outside_group)
        self.cue_timeline_cue_region_radio.toggled.connect(self._sync_jog_outside_group_enabled)
        self.cue_timeline_audio_file_radio.toggled.connect(self._sync_jog_outside_group_enabled)
        self._sync_jog_outside_group_enabled()

        layout.addStretch(1)
        return page

