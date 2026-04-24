from __future__ import annotations

from ..shared import *
from ..widgets import *


class TalkPageMixin:
    def _build_talk_page(
        self,
        talk_volume_level: int,
        talk_fade_sec: float,
        talk_volume_mode: str,
        talk_blink_button: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()

        self.talk_volume_spin = QSpinBox()
        self.talk_volume_spin.setRange(0, 100)
        self.talk_volume_spin.setValue(talk_volume_level)
        form.addRow("Talk Volume Level:", self.talk_volume_spin)

        self.talk_fade_spin = QDoubleSpinBox()
        self.talk_fade_spin.setRange(0.0, 20.0)
        self.talk_fade_spin.setSingleStep(0.1)
        self.talk_fade_spin.setDecimals(1)
        self.talk_fade_spin.setValue(talk_fade_sec)
        form.addRow("Talk Fade Seconds:", self.talk_fade_spin)

        self.talk_blink_checkbox = QCheckBox("Blink Talk Button")
        self.talk_blink_checkbox.setChecked(talk_blink_button)
        form.addRow("Talk Button:", self.talk_blink_checkbox)
        self.talk_mode_percent_radio = QRadioButton("Use Talk level as % of current volume")
        self.talk_mode_lower_only_radio = QRadioButton("Lower to Talk level only")
        self.talk_mode_force_radio = QRadioButton("Set exactly to Talk level")
        if talk_volume_mode == "set_exact":
            self.talk_mode_force_radio.setChecked(True)
        elif talk_volume_mode == "lower_only":
            self.talk_mode_lower_only_radio.setChecked(True)
        else:
            self.talk_mode_percent_radio.setChecked(True)

        mode_group = QGroupBox("Talk Volume Behavior")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setContentsMargins(8, 8, 8, 8)
        mode_layout.setSpacing(6)
        mode_layout.addWidget(self.talk_mode_percent_radio)
        mode_layout.addWidget(self.talk_mode_lower_only_radio)
        mode_layout.addWidget(self.talk_mode_force_radio)
        layout.addLayout(form)
        layout.addWidget(mode_group)
        layout.addStretch(1)

        return page

