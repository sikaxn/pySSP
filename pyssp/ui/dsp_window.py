from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from pyssp.dsp import DSPConfig
from pyssp.i18n import localize_widget_tree


class DSPWindow(QDialog):
    configChanged = pyqtSignal(object)
    EQ_FREQUENCIES: List[str] = ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]
    EQ_PRESETS: Dict[str, List[int]] = {
        "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "Rock": [4, 3, 1, -1, -2, -1, 1, 3, 4, 5],
        "Country": [2, 1, 0, -1, -1, 0, 1, 2, 2, 1],
        "Jazz": [0, 1, 2, 2, 1, 0, 1, 2, 3, 3],
        "Classical": [3, 2, 1, 0, -1, -1, 0, 1, 2, 3],
    }

    def __init__(self, parent=None, language: str = "en") -> None:
        super().__init__(parent)
        self.setWindowTitle("DSP")
        self.resize(980, 560)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        eq_group = QFrame()
        eq_group.setFrameShape(QFrame.StyledPanel)
        eq_layout = QVBoxLayout(eq_group)
        eq_layout.setContentsMargins(10, 8, 10, 8)
        eq_layout.setSpacing(8)

        eq_header = QHBoxLayout()
        eq_header.addWidget(QLabel("10-Band EQ"))
        self.eq_on_btn = QPushButton("EQ On")
        self.eq_on_btn.setCheckable(True)
        self.eq_on_btn.setChecked(True)
        self.eq_on_btn.toggled.connect(self._on_eq_toggled)
        eq_header.addWidget(self.eq_on_btn)
        eq_header.addStretch(1)
        eq_layout.addLayout(eq_header)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:"))
        for name in ("Flat", "Rock", "Country", "Jazz", "Classical"):
            btn = QPushButton(name)
            btn.clicked.connect(lambda _=False, preset=name: self._apply_eq_preset(preset))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        eq_layout.addLayout(preset_row)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        self.eq_sliders: List[QSlider] = []
        self.eq_value_labels: List[QLabel] = []
        for freq in self.EQ_FREQUENCIES:
            col = QWidget()
            col_layout = QVBoxLayout(col)
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(2)
            top_val = QLabel("0")
            top_val.setAlignment(Qt.AlignCenter)
            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setSingleStep(1)
            slider.setValue(0)
            slider.valueChanged.connect(lambda value, label=top_val: label.setText(str(value)))
            slider.valueChanged.connect(lambda _value: self._emit_config_changed())
            label = QLabel(freq)
            label.setAlignment(Qt.AlignCenter)
            col_layout.addWidget(top_val)
            col_layout.addWidget(slider, 1)
            col_layout.addWidget(label)
            slider_row.addWidget(col, 1)
            self.eq_sliders.append(slider)
            self.eq_value_labels.append(top_val)
        eq_layout.addLayout(slider_row, 1)
        root.addWidget(eq_group, 3)

        fx_group = QFrame()
        fx_group.setFrameShape(QFrame.StyledPanel)
        fx_layout = QGridLayout(fx_group)
        fx_layout.setContentsMargins(10, 8, 10, 8)
        fx_layout.setHorizontalSpacing(14)
        fx_layout.setVerticalSpacing(10)

        self.reverb_slider = QSlider(Qt.Horizontal)
        self.reverb_slider.setRange(0, 200)
        self.reverb_slider.setValue(0)
        self.reverb_value = QLabel("0.0 s")
        self.reverb_slider.valueChanged.connect(self._on_reverb_changed)
        fx_layout.addWidget(QLabel("Reverb"), 0, 0)
        fx_layout.addWidget(self.reverb_slider, 0, 1)
        fx_layout.addWidget(self.reverb_value, 0, 2)

        self.tempo_slider = QSlider(Qt.Horizontal)
        self.tempo_slider.setRange(-30, 30)
        self.tempo_slider.setValue(0)
        self.tempo_value = QLabel("0%")
        self.tempo_slider.valueChanged.connect(self._on_tempo_changed)
        tempo_reset = QPushButton("Reset")
        tempo_reset.clicked.connect(lambda: self.tempo_slider.setValue(0))
        fx_layout.addWidget(QLabel("Tempo"), 1, 0)
        fx_layout.addWidget(self.tempo_slider, 1, 1)
        fx_layout.addWidget(self.tempo_value, 1, 2)
        fx_layout.addWidget(tempo_reset, 1, 3)

        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-30, 30)
        self.pitch_slider.setValue(0)
        self.pitch_value = QLabel("0%")
        self.pitch_slider.valueChanged.connect(self._on_pitch_changed)
        pitch_reset = QPushButton("Reset")
        pitch_reset.clicked.connect(lambda: self.pitch_slider.setValue(0))
        fx_layout.addWidget(QLabel("Pitch"), 2, 0)
        fx_layout.addWidget(self.pitch_slider, 2, 1)
        fx_layout.addWidget(self.pitch_value, 2, 2)
        fx_layout.addWidget(pitch_reset, 2, 3)

        root.addWidget(fx_group, 2)
        localize_widget_tree(self, language)

    def _update_reverb_label(self, value: int) -> None:
        self.reverb_value.setText(f"{value / 10.0:.1f} s")

    def _update_eq_button_text(self, checked: bool) -> None:
        self.eq_on_btn.setText("EQ On" if checked else "EQ Off")

    def _apply_eq_preset(self, name: str) -> None:
        values = self.EQ_PRESETS.get(name, [])
        for slider, target in zip(self.eq_sliders, values):
            slider.setValue(int(target))
        self._emit_config_changed()

    def set_config(self, config: DSPConfig) -> None:
        self.eq_on_btn.setChecked(bool(config.eq_enabled))
        for slider, value in zip(self.eq_sliders, config.eq_bands):
            slider.setValue(int(max(-12, min(12, value))))
        self.reverb_slider.setValue(int(max(0, min(200, round(config.reverb_sec * 10.0)))))
        self.tempo_slider.setValue(int(max(-30, min(30, round(config.tempo_pct)))))
        self.pitch_slider.setValue(int(max(-30, min(30, round(config.pitch_pct)))))
        self._emit_config_changed()

    def current_config(self) -> DSPConfig:
        return DSPConfig(
            eq_enabled=self.eq_on_btn.isChecked(),
            eq_bands=[slider.value() for slider in self.eq_sliders],
            reverb_sec=self.reverb_slider.value() / 10.0,
            tempo_pct=float(self.tempo_slider.value()),
            pitch_pct=float(self.pitch_slider.value()),
        )

    def _on_eq_toggled(self, checked: bool) -> None:
        self._update_eq_button_text(checked)
        self._emit_config_changed()

    def _on_reverb_changed(self, value: int) -> None:
        self._update_reverb_label(value)
        self._emit_config_changed()

    def _on_tempo_changed(self, value: int) -> None:
        self.tempo_value.setText(f"{value}%")
        self._emit_config_changed()

    def _on_pitch_changed(self, value: int) -> None:
        self.pitch_value.setText(f"{value}%")
        self._emit_config_changed()

    def _emit_config_changed(self) -> None:
        self.configChanged.emit(self.current_config())
