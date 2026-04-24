from __future__ import annotations

from ..shared import *
from ..widgets import *


class AudioDevicesPageMixin:
    def _build_audio_device_page(
        self,
        audio_output_device: str,
        available_audio_devices: List[str],
        available_midi_devices: List[tuple[str, str]],
        timecode_audio_output_device: str,
        timecode_midi_output_device: str,
        timecode_mode: str,
        timecode_fps: float,
        timecode_mtc_fps: float,
        timecode_mtc_idle_behavior: str,
        timecode_sample_rate: int,
        timecode_bit_depth: int,
        timecode_timeline_mode: str,
        soundbutton_timecode_offset_enabled: bool,
        respect_soundbutton_timecode_timeline_setting: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        playback_group = QGroupBox("Audio Playback")
        playback_layout = QVBoxLayout(playback_group)
        row = QHBoxLayout()
        row.addWidget(QLabel("Playback Device:"))
        self.audio_device_combo = QComboBox()
        row.addWidget(self.audio_device_combo, 1)
        self.audio_refresh_button = QPushButton("Refresh")
        self.audio_refresh_button.clicked.connect(self._refresh_audio_devices)
        row.addWidget(self.audio_refresh_button)
        playback_layout.addLayout(row)

        self.audio_device_hint = QLabel("")
        playback_layout.addWidget(self.audio_device_hint)
        layout.addWidget(playback_group)

        self._populate_audio_devices(available_audio_devices, audio_output_device)

        mode_group = QGroupBox("Timecode Mode")
        mode_form = QFormLayout(mode_group)
        self.timecode_mode_combo = QComboBox()
        self.timecode_mode_combo.addItem("All Zero", TIMECODE_MODE_ZERO)
        self.timecode_mode_combo.addItem("Follow Media/Audio Player", TIMECODE_MODE_FOLLOW)
        self.timecode_mode_combo.addItem("System Time", TIMECODE_MODE_SYSTEM)
        self.timecode_mode_combo.addItem("Pause Sync (Freeze While Playback Continues)", TIMECODE_MODE_FOLLOW_FREEZE)
        mode_form.addRow("Mode:", self.timecode_mode_combo)
        layout.addWidget(mode_group)

        timeline_group = QGroupBox("Timecode Display Timeline")
        timeline_layout = QVBoxLayout(timeline_group)
        self.timecode_timeline_cue_region_radio = QRadioButton("Relative to Cue Set Points")
        self.timecode_timeline_audio_file_radio = QRadioButton("Relative to Actual Audio File")
        if timecode_timeline_mode == "audio_file":
            self.timecode_timeline_audio_file_radio.setChecked(True)
        else:
            self.timecode_timeline_cue_region_radio.setChecked(True)
        timeline_layout.addWidget(self.timecode_timeline_cue_region_radio)
        timeline_layout.addWidget(self.timecode_timeline_audio_file_radio)
        self.soundbutton_timecode_offset_enabled_checkbox = QCheckBox("Enable soundbutton timecode offset")
        self.soundbutton_timecode_offset_enabled_checkbox.setChecked(bool(soundbutton_timecode_offset_enabled))
        timeline_layout.addWidget(self.soundbutton_timecode_offset_enabled_checkbox)
        self.respect_soundbutton_timecode_timeline_setting_checkbox = QCheckBox(
            "Respect soundbutton timecode display timeline setting"
        )
        self.respect_soundbutton_timecode_timeline_setting_checkbox.setChecked(
            bool(respect_soundbutton_timecode_timeline_setting)
        )
        timeline_layout.addWidget(self.respect_soundbutton_timecode_timeline_setting_checkbox)
        layout.addWidget(timeline_group)

        ltc_group = QGroupBox("SMPTE Timecode (LTC)")
        ltc_form = QFormLayout(ltc_group)
        self.timecode_output_combo = QComboBox()
        self.timecode_output_combo.addItem("Follow playback device setting", "follow_playback")
        self.timecode_output_combo.addItem("Use system default", "default")
        self.timecode_output_combo.addItem("None (mute output)", "none")
        for name in available_audio_devices:
            self.timecode_output_combo.addItem(name, name)
        ltc_form.addRow("Output Device:", self.timecode_output_combo)

        self.timecode_fps_combo = QComboBox()
        for fps in TIME_CODE_FPS_CHOICES:
            self.timecode_fps_combo.addItem(f"{fps:g} fps", float(fps))
        ltc_form.addRow("Frame Rate:", self.timecode_fps_combo)

        self.timecode_sample_rate_combo = QComboBox()
        for sample_rate in TIME_CODE_SAMPLE_RATES:
            self.timecode_sample_rate_combo.addItem(f"{sample_rate} Hz", int(sample_rate))
        ltc_form.addRow("Sample Rate:", self.timecode_sample_rate_combo)

        self.timecode_bit_depth_combo = QComboBox()
        for bit_depth in TIME_CODE_BIT_DEPTHS:
            self.timecode_bit_depth_combo.addItem(f"{bit_depth}-bit", int(bit_depth))
        ltc_form.addRow("Bit Depth:", self.timecode_bit_depth_combo)
        layout.addWidget(ltc_group)

        mtc_group = QGroupBox("MIDI Timecode (MTC)")
        mtc_form = QFormLayout(mtc_group)
        self.timecode_midi_output_combo = QComboBox()
        self.timecode_midi_output_combo.addItem("None (disabled)", MIDI_OUTPUT_DEVICE_NONE)
        for device_id, device_name in available_midi_devices:
            self.timecode_midi_output_combo.addItem(device_name, device_id)
        self.timecode_midi_output_combo.currentIndexChanged.connect(
            lambda _index: self._refresh_midi_input_devices(force_refresh=False)
        )
        mtc_form.addRow("MIDI Output Device:", self.timecode_midi_output_combo)

        self.timecode_mtc_fps_combo = QComboBox()
        for fps in TIME_CODE_MTC_FPS_CHOICES:
            self.timecode_mtc_fps_combo.addItem(f"{fps:g} fps", float(fps))
        mtc_form.addRow("Frame Rate:", self.timecode_mtc_fps_combo)

        self.timecode_mtc_idle_behavior_combo = QComboBox()
        self.timecode_mtc_idle_behavior_combo.addItem("Keep stream alive (no dark)", "keep_stream")
        self.timecode_mtc_idle_behavior_combo.addItem("Allow dark when idle", "allow_dark")
        mtc_form.addRow("Idle Behavior:", self.timecode_mtc_idle_behavior_combo)
        layout.addWidget(mtc_group)

        self._set_combo_data_or_default(self.timecode_output_combo, timecode_audio_output_device, "none")
        self._set_combo_data_or_default(self.timecode_mode_combo, timecode_mode, TIMECODE_MODE_FOLLOW)
        self._set_combo_float_or_default(self.timecode_fps_combo, float(timecode_fps), 30.0)
        self._set_combo_float_or_default(self.timecode_mtc_fps_combo, float(timecode_mtc_fps), 30.0)
        self._set_combo_data_or_default(self.timecode_mtc_idle_behavior_combo, timecode_mtc_idle_behavior, "keep_stream")
        self._set_combo_data_or_default(self.timecode_sample_rate_combo, int(timecode_sample_rate), 48000)
        self._set_combo_data_or_default(self.timecode_bit_depth_combo, int(timecode_bit_depth), 16)
        self._set_combo_data_or_default(self.timecode_midi_output_combo, timecode_midi_output_device, MIDI_OUTPUT_DEVICE_NONE)

        layout.addStretch(1)
        return page

