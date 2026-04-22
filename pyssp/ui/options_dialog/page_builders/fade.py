from __future__ import annotations

from ..shared import *
from ..widgets import *


class FadePageMixin:
    def _build_delay_page(
        self,
        fade_in_sec: float,
        cross_fade_sec: float,
        fade_out_sec: float,
        fade_on_quick_action_hotkey: bool,
        fade_on_sound_button_hotkey: bool,
        fade_on_pause: bool,
        fade_on_resume: bool,
        fade_on_stop: bool,
        fade_out_when_done_playing: bool,
        fade_out_end_lead_sec: float,
        vocal_removed_toggle_fade_mode: str,
        vocal_removed_toggle_custom_sec: float,
        vocal_removed_toggle_always_sec: float,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        trigger_group = QGroupBox("Fader Trigger")
        trigger_layout = QVBoxLayout(trigger_group)

        self.fade_on_quick_action_checkbox = QCheckBox("Allow fader on Quick Action key active")
        self.fade_on_quick_action_checkbox.setChecked(bool(fade_on_quick_action_hotkey))
        trigger_layout.addWidget(self.fade_on_quick_action_checkbox)

        self.fade_on_sound_hotkey_checkbox = QCheckBox("Allow fader on Sound Button hot key active")
        self.fade_on_sound_hotkey_checkbox.setChecked(bool(fade_on_sound_button_hotkey))
        trigger_layout.addWidget(self.fade_on_sound_hotkey_checkbox)

        self.fade_on_pause_checkbox = QCheckBox("Fade on Pause")
        self.fade_on_pause_checkbox.setChecked(bool(fade_on_pause))
        trigger_layout.addWidget(self.fade_on_pause_checkbox)

        self.fade_on_resume_checkbox = QCheckBox("Fade on Resume (when paused)")
        self.fade_on_resume_checkbox.setChecked(bool(fade_on_resume))
        trigger_layout.addWidget(self.fade_on_resume_checkbox)

        self.fade_on_stop_checkbox = QCheckBox("Fade on Stop")
        self.fade_on_stop_checkbox.setChecked(bool(fade_on_stop))
        trigger_layout.addWidget(self.fade_on_stop_checkbox)

        self.fade_on_stop_note = QLabel("During fade, click Stop again to force stop (skip fade).")
        self.fade_on_stop_note.setWordWrap(True)
        self.fade_on_stop_note.setStyleSheet("color:#666666;")
        trigger_layout.addWidget(self.fade_on_stop_note)
        self.fade_dependency_note = QLabel("Note: These options work only when the matching Fade In/Fade Out control is active.")
        self.fade_dependency_note.setWordWrap(True)
        self.fade_dependency_note.setStyleSheet("color:#666666;")
        trigger_layout.addWidget(self.fade_dependency_note)
        layout.addWidget(trigger_group)

        timing_group = QGroupBox("Fade Timing")
        timing_form = QFormLayout(timing_group)

        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0.0, 20.0)
        self.fade_in_spin.setSingleStep(0.1)
        self.fade_in_spin.setDecimals(1)
        self.fade_in_spin.setValue(fade_in_sec)
        timing_form.addRow("Fade In Seconds:", self.fade_in_spin)

        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0.0, 20.0)
        self.fade_out_spin.setSingleStep(0.1)
        self.fade_out_spin.setDecimals(1)
        self.fade_out_spin.setValue(fade_out_sec)
        timing_form.addRow("Fade Out Seconds:", self.fade_out_spin)

        self.fade_out_when_done_checkbox = QCheckBox("Fade out when done playing")
        self.fade_out_when_done_checkbox.setChecked(bool(fade_out_when_done_playing))
        timing_form.addRow("", self.fade_out_when_done_checkbox)

        self.fade_out_end_lead_spin = QDoubleSpinBox()
        self.fade_out_end_lead_spin.setRange(0.0, 30.0)
        self.fade_out_end_lead_spin.setSingleStep(0.1)
        self.fade_out_end_lead_spin.setDecimals(1)
        self.fade_out_end_lead_spin.setValue(float(fade_out_end_lead_sec))
        timing_form.addRow("Length from end to start Fade Out:", self.fade_out_end_lead_spin)

        self.cross_fade_spin = QDoubleSpinBox()
        self.cross_fade_spin.setRange(0.0, 20.0)
        self.cross_fade_spin.setSingleStep(0.1)
        self.cross_fade_spin.setDecimals(1)
        self.cross_fade_spin.setValue(cross_fade_sec)
        timing_form.addRow("Cross Fade Seconds:", self.cross_fade_spin)
        layout.addWidget(timing_group)

        vocal_group = QGroupBox("Fade During Vocal Removed / Original Track Conversion")
        vocal_form = QFormLayout(vocal_group)
        self.vocal_removed_toggle_fade_group = QButtonGroup(self)

        self.vocal_removed_follow_cross_fade_radio = QRadioButton(
            "Follow Cross Fade (X, use Cross Fade Seconds)"
        )
        self.vocal_removed_toggle_fade_group.addButton(self.vocal_removed_follow_cross_fade_radio)
        vocal_form.addRow("", self.vocal_removed_follow_cross_fade_radio)

        self.vocal_removed_follow_cross_fade_custom_radio = QRadioButton(
            "Follow Cross Fade (X), but use custom seconds"
        )
        self.vocal_removed_toggle_fade_group.addButton(self.vocal_removed_follow_cross_fade_custom_radio)
        custom_row = QWidget()
        custom_layout = QHBoxLayout(custom_row)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.addWidget(self.vocal_removed_follow_cross_fade_custom_radio)
        self.vocal_removed_toggle_custom_spin = QDoubleSpinBox()
        self.vocal_removed_toggle_custom_spin.setRange(0.0, 20.0)
        self.vocal_removed_toggle_custom_spin.setSingleStep(0.1)
        self.vocal_removed_toggle_custom_spin.setDecimals(1)
        self.vocal_removed_toggle_custom_spin.setValue(float(vocal_removed_toggle_custom_sec))
        custom_layout.addWidget(self.vocal_removed_toggle_custom_spin)
        custom_layout.addWidget(QLabel("sec"))
        custom_layout.addStretch(1)
        vocal_form.addRow("", custom_row)

        self.vocal_removed_never_fade_radio = QRadioButton("Never fade")
        self.vocal_removed_toggle_fade_group.addButton(self.vocal_removed_never_fade_radio)
        vocal_form.addRow("", self.vocal_removed_never_fade_radio)

        self.vocal_removed_always_fade_radio = QRadioButton("Always fade")
        self.vocal_removed_toggle_fade_group.addButton(self.vocal_removed_always_fade_radio)
        always_row = QWidget()
        always_layout = QHBoxLayout(always_row)
        always_layout.setContentsMargins(0, 0, 0, 0)
        always_layout.addWidget(self.vocal_removed_always_fade_radio)
        self.vocal_removed_toggle_always_spin = QDoubleSpinBox()
        self.vocal_removed_toggle_always_spin.setRange(0.0, 20.0)
        self.vocal_removed_toggle_always_spin.setSingleStep(0.1)
        self.vocal_removed_toggle_always_spin.setDecimals(1)
        self.vocal_removed_toggle_always_spin.setValue(float(vocal_removed_toggle_always_sec))
        always_layout.addWidget(self.vocal_removed_toggle_always_spin)
        always_layout.addWidget(QLabel("sec"))
        always_layout.addStretch(1)
        vocal_form.addRow("", always_row)

        if vocal_removed_toggle_fade_mode == "follow_cross_fade_custom":
            self.vocal_removed_follow_cross_fade_custom_radio.setChecked(True)
        elif vocal_removed_toggle_fade_mode == "never":
            self.vocal_removed_never_fade_radio.setChecked(True)
        elif vocal_removed_toggle_fade_mode == "always":
            self.vocal_removed_always_fade_radio.setChecked(True)
        else:
            self.vocal_removed_follow_cross_fade_radio.setChecked(True)

        self.vocal_removed_toggle_fade_group.buttonToggled.connect(self._sync_vocal_removed_toggle_fade_enabled)
        self._sync_vocal_removed_toggle_fade_enabled()
        layout.addWidget(vocal_group)
        layout.addStretch(1)

        self.fade_out_when_done_checkbox.toggled.connect(self._sync_fade_out_end_lead_enabled)
        self._sync_fade_out_end_lead_enabled()
        return page

    def _sync_fade_out_end_lead_enabled(self) -> None:
        self.fade_out_end_lead_spin.setEnabled(self.fade_out_when_done_checkbox.isChecked())

    def _sync_vocal_removed_toggle_fade_enabled(self) -> None:
        self.vocal_removed_toggle_custom_spin.setEnabled(
            self.vocal_removed_follow_cross_fade_custom_radio.isChecked()
        )
        self.vocal_removed_toggle_always_spin.setEnabled(self.vocal_removed_always_fade_radio.isChecked())

