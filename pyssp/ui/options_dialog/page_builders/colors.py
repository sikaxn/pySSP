from __future__ import annotations

from ..shared import *
from ..widgets import *


class ColorsPageMixin:
    def _build_color_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        sound_group = QGroupBox("Sound Button States")
        sound_form = QFormLayout(sound_group)
        self._add_state_color_row(sound_form, "playing", "Playing")
        self._add_state_color_row(sound_form, "played", "Played")
        self._add_state_color_row(sound_form, "unplayed", "Unplayed")
        self._add_state_color_row(sound_form, "highlight", "Highlight")
        self._add_state_color_row(sound_form, "lock", "Lock")
        self._add_state_color_row(sound_form, "error", "Error")
        self._add_state_color_row(sound_form, "place_marker", "Place Marker")
        self._add_state_color_row(sound_form, "empty", "Empty")
        self._add_state_color_row(sound_form, "copied_to_cue", "Copied To Cue")
        layout.addWidget(sound_group)

        indicator_group = QGroupBox("Indicators")
        indicator_form = QFormLayout(indicator_group)
        self._add_state_color_row(indicator_form, "cue_indicator", "Cue Indicator")
        self._add_state_color_row(indicator_form, "volume_indicator", "Volume Indicator")
        self._add_state_color_row(indicator_form, "vocal_removed_indicator", "Vocal Removed Indicator")
        self._add_state_color_row(indicator_form, "midi_indicator", "MIDI Indicator")
        self._add_state_color_row(indicator_form, "lyric_indicator", "Lyric Indicator")
        self.sound_text_color_btn = QPushButton()
        self.sound_text_color_btn.clicked.connect(self._pick_sound_text_color)
        self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)
        indicator_form.addRow("Sound Button Text:", self.sound_text_color_btn)
        layout.addWidget(indicator_group)

        group_group = QGroupBox("Group Buttons")
        group_form = QFormLayout(group_group)
        self.active_color_btn = QPushButton()
        self.active_color_btn.clicked.connect(self._pick_active_color)
        self._refresh_color_button(self.active_color_btn, self.active_group_color)
        group_form.addRow("Active Group:", self.active_color_btn)
        self.inactive_color_btn = QPushButton()
        self.inactive_color_btn.clicked.connect(self._pick_inactive_color)
        self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)
        group_form.addRow("Inactive Group:", self.inactive_color_btn)
        layout.addWidget(group_group)

        layout.addStretch(1)
        return page

    def _add_state_color_row(self, form: QFormLayout, key: str, label: str) -> None:
        value = self.state_colors.get(key, "#FFFFFF")
        btn = QPushButton()
        self._refresh_color_button(btn, value)
        btn.clicked.connect(lambda _=None, k=key, b=btn, t=label: self._pick_state_color(k, b, t))
        self._state_color_buttons[key] = btn
        form.addRow(f"{label}:", btn)

