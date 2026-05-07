from __future__ import annotations

import os
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyssp.i18n import localize_widget_tree, tr
from pyssp.midi_control import (
    midi_binding_to_display,
    midi_input_name_selector,
    normalize_midi_binding,
    split_midi_binding,
)
from pyssp.ui.edit_sound_button_dialog import SoundHotkeyEdit
from pyssp.utility_audio import (
    UTILITY_MODE_BLANK,
    UTILITY_MODE_METRONOME,
    UTILITY_MODE_PINK_NOISE,
    UTILITY_MODE_WAVEFORM,
    UTILITY_WAVEFORM_SAWTOOTH,
    UTILITY_WAVEFORM_SINE,
    UTILITY_WAVEFORM_SQUARE,
    UTILITY_WAVEFORM_TRIANGLE,
    UtilitySoundSpec,
    normalize_utility_spec,
)


class UtilitySoundButtonDialog(QDialog):
    def __init__(
        self,
        *,
        caption: str,
        notes: str,
        lyric_file: str = "",
        utility_spec: Optional[UtilitySoundSpec] = None,
        volume_override_pct: Optional[int] = None,
        sound_hotkey: str = "",
        sound_midi_hotkey: str = "",
        available_midi_input_devices: Optional[list[tuple[str, str]]] = None,
        selected_midi_input_device_ids: Optional[list[str]] = None,
        start_dir: str = "",
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Utility Sound Button"))
        self.resize(760, 420)
        self._start_dir = start_dir
        self._form: Optional[QFormLayout] = None
        spec = normalize_utility_spec(utility_spec or UtilitySoundSpec())

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._form = form

        self.caption_edit = QLineEdit(caption)
        form.addRow(tr("Caption"), self.caption_edit)

        self.notes_edit = QLineEdit(notes)
        form.addRow(tr("Notes"), self.notes_edit)

        lyric_row = QWidget()
        lyric_layout = QHBoxLayout(lyric_row)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        self.lyric_file_edit = QLineEdit(lyric_file)
        lyric_browse_btn = QPushButton(tr("Browse"))
        lyric_browse_btn.clicked.connect(self._browse_lyric_file)
        lyric_clear_btn = QPushButton(tr("Clear"))
        lyric_clear_btn.clicked.connect(lambda _=False: self.lyric_file_edit.setText(""))
        lyric_layout.addWidget(self.lyric_file_edit, 1)
        lyric_layout.addWidget(lyric_browse_btn)
        lyric_layout.addWidget(lyric_clear_btn)
        form.addRow(tr("Lyric File"), lyric_row)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem(tr("Blank (No Sound)"), UTILITY_MODE_BLANK)
        self.mode_combo.addItem(tr("Pink Noise"), UTILITY_MODE_PINK_NOISE)
        self.mode_combo.addItem(tr("Waveform Generator"), UTILITY_MODE_WAVEFORM)
        self.mode_combo.addItem(tr("Metronome"), UTILITY_MODE_METRONOME)
        self._set_combo_data(self.mode_combo, spec.mode, UTILITY_MODE_BLANK)
        form.addRow(tr("Mode"), self.mode_combo)

        duration_row = QWidget()
        duration_layout = QGridLayout(duration_row)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setHorizontalSpacing(6)
        self.hours_spin = self._make_spin(0, 24)
        self.minutes_spin = self._make_spin(0, 59)
        self.seconds_spin = self._make_spin(0, 59)
        self.millis_spin = self._make_spin(0, 999)
        total_ms = max(1, int(spec.duration_ms))
        hours, rem = divmod(total_ms, 3600 * 1000)
        minutes, rem = divmod(rem, 60 * 1000)
        seconds, millis = divmod(rem, 1000)
        self.hours_spin.setValue(min(24, hours))
        self.minutes_spin.setValue(minutes)
        self.seconds_spin.setValue(seconds)
        self.millis_spin.setValue(millis)
        duration_layout.addWidget(QLabel("HH"), 0, 0)
        duration_layout.addWidget(self.hours_spin, 0, 1)
        duration_layout.addWidget(QLabel("MM"), 0, 2)
        duration_layout.addWidget(self.minutes_spin, 0, 3)
        duration_layout.addWidget(QLabel("SS"), 0, 4)
        duration_layout.addWidget(self.seconds_spin, 0, 5)
        duration_layout.addWidget(QLabel("ms"), 0, 6)
        duration_layout.addWidget(self.millis_spin, 0, 7)
        form.addRow(tr("Duration"), duration_row)

        self.waveform_type_combo = QComboBox()
        self.waveform_type_combo.addItem(tr("Sine"), UTILITY_WAVEFORM_SINE)
        self.waveform_type_combo.addItem(tr("Square"), UTILITY_WAVEFORM_SQUARE)
        self.waveform_type_combo.addItem(tr("Triangle"), UTILITY_WAVEFORM_TRIANGLE)
        self.waveform_type_combo.addItem(tr("Sawtooth"), UTILITY_WAVEFORM_SAWTOOTH)
        self._set_combo_data(self.waveform_type_combo, spec.waveform_type, UTILITY_WAVEFORM_SINE)
        form.addRow(tr("Waveform"), self.waveform_type_combo)

        self.frequency_spin = QSpinBox()
        self.frequency_spin.setRange(1, 24000)
        self.frequency_spin.setValue(max(1, min(24000, int(round(spec.frequency_hz)))))
        self.frequency_spin.setSuffix(" Hz")
        form.addRow(tr("Frequency"), self.frequency_spin)

        self.tempo_spin = QSpinBox()
        self.tempo_spin.setRange(1, 999)
        self.tempo_spin.setValue(max(1, min(999, int(round(spec.tempo_bpm)))))
        self.tempo_spin.setSuffix(" BPM")
        form.addRow(tr("Tempo"), self.tempo_spin)

        timesig_row = QWidget()
        timesig_layout = QHBoxLayout(timesig_row)
        timesig_layout.setContentsMargins(0, 0, 0, 0)
        self.timesig_num_spin = self._make_spin(1, 32)
        self.timesig_num_spin.setValue(spec.time_signature_num)
        self.timesig_den_combo = QComboBox()
        for value in [1, 2, 4, 8, 16]:
            self.timesig_den_combo.addItem(str(value), value)
        self._set_combo_data(self.timesig_den_combo, spec.time_signature_den, 4)
        timesig_layout.addWidget(self.timesig_num_spin)
        timesig_layout.addWidget(QLabel("/"))
        timesig_layout.addWidget(self.timesig_den_combo)
        timesig_layout.addStretch(1)
        form.addRow(tr("Time Signature"), timesig_row)

        hk_row = QWidget()
        hk_layout = QHBoxLayout(hk_row)
        hk_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_hotkey_edit = SoundHotkeyEdit()
        self.sound_hotkey_edit.setHotkey(sound_hotkey)
        clear_hk_btn = QPushButton(tr("Clear"))
        clear_hk_btn.clicked.connect(lambda _=False: self.sound_hotkey_edit.setHotkey(""))
        hk_layout.addWidget(self.sound_hotkey_edit, 1)
        hk_layout.addWidget(clear_hk_btn)
        form.addRow(tr("Sound Button Hot Key"), hk_row)

        midi_hk_row = QWidget()
        midi_hk_layout = QHBoxLayout(midi_hk_row)
        midi_hk_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_midi_hotkey_edit = QLineEdit()
        self.sound_midi_hotkey_edit.setReadOnly(True)
        self._set_midi_binding(sound_midi_hotkey)
        learn_midi_btn = QPushButton(tr("Learn"))
        clear_midi_btn = QPushButton(tr("Clear"))
        learn_midi_btn.clicked.connect(self._start_midi_learn)
        clear_midi_btn.clicked.connect(lambda _=False: self._set_midi_binding(""))
        midi_hk_layout.addWidget(self.sound_midi_hotkey_edit, 1)
        midi_hk_layout.addWidget(learn_midi_btn)
        midi_hk_layout.addWidget(clear_midi_btn)
        form.addRow(tr("Sound Button MIDI Hot Key"), midi_hk_row)

        self._midi_binding = normalize_midi_binding(sound_midi_hotkey)
        self._midi_learning = False
        selected_ids = [str(v).strip() for v in (selected_midi_input_device_ids or []) if str(v).strip()]
        available_by_id = {
            str(device_id).strip(): str(device_name).strip()
            for device_id, device_name in (available_midi_input_devices or [])
        }
        allowed: set[str] = set()
        for value in selected_ids:
            if value.startswith("name::"):
                allowed.add(value)
            elif value in available_by_id:
                allowed.add(midi_input_name_selector(available_by_id[value]))
        self._allowed_midi_selectors = allowed

        vol_row = QWidget()
        vol_layout = QVBoxLayout(vol_row)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setSpacing(4)
        self.custom_volume_checkbox = QCheckBox(tr("Use custom playback volume"))
        self.custom_volume_checkbox.setChecked(volume_override_pct is not None)
        vol_layout.addWidget(self.custom_volume_checkbox)
        self.volume_label = QLabel("")
        vol_layout.addWidget(self.volume_label)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75 if volume_override_pct is None else max(0, min(100, int(volume_override_pct))))
        vol_layout.addWidget(self.volume_slider)
        form.addRow(tr("Playback Volume"), vol_row)

        def _sync_volume_label(value: int) -> None:
            self.volume_label.setText(f"{value}%")

        def _sync_slider_enabled(checked: bool) -> None:
            self.volume_slider.setEnabled(checked)
            self.volume_label.setEnabled(checked)

        self.volume_slider.valueChanged.connect(_sync_volume_label)
        self.custom_volume_checkbox.toggled.connect(_sync_slider_enabled)
        _sync_volume_label(self.volume_slider.value())
        _sync_slider_enabled(self.custom_volume_checkbox.isChecked())

        self.mode_combo.currentIndexChanged.connect(self._refresh_mode_visibility)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._refresh_mode_visibility()
        localize_widget_tree(self, language)

    def values(self) -> tuple[str, str, str, UtilitySoundSpec, Optional[int], str, str]:
        volume_override_pct: Optional[int] = None
        if self.custom_volume_checkbox.isChecked():
            volume_override_pct = max(0, min(100, int(self.volume_slider.value())))
        duration_ms = (
            (int(self.hours_spin.value()) * 3600 * 1000)
            + (int(self.minutes_spin.value()) * 60 * 1000)
            + (int(self.seconds_spin.value()) * 1000)
            + int(self.millis_spin.value())
        )
        spec = normalize_utility_spec(
            {
                "mode": self.mode_combo.currentData(),
                "duration_ms": duration_ms,
                "waveform_type": self.waveform_type_combo.currentData(),
                "frequency_hz": self.frequency_spin.value(),
                "tempo_bpm": self.tempo_spin.value(),
                "time_signature_num": self.timesig_num_spin.value(),
                "time_signature_den": self.timesig_den_combo.currentData(),
            }
        )
        return (
            self.caption_edit.text().strip(),
            self.notes_edit.text().strip(),
            self.lyric_file_edit.text().strip(),
            spec,
            volume_override_pct,
            self.sound_hotkey_edit.hotkey(),
            self._midi_binding,
        )

    def handle_midi_message(
        self,
        token: str,
        source_selector: str = "",
        status: int = 0,
        data1: int = 0,
        data2: int = 0,
    ) -> bool:
        if not self._midi_learning:
            return False
        if self._allowed_midi_selectors:
            if not source_selector or source_selector not in self._allowed_midi_selectors:
                return False
        self._on_midi_binding(token, source_selector)
        return True

    def _refresh_mode_visibility(self) -> None:
        mode = str(self.mode_combo.currentData() or UTILITY_MODE_BLANK)
        waveform_visible = mode == UTILITY_MODE_WAVEFORM
        metronome_visible = mode == UTILITY_MODE_METRONOME
        for widget in [self.waveform_type_combo, self.frequency_spin]:
            label = self._form.labelForField(widget) if self._form is not None else None
            if label is not None:
                label.setVisible(waveform_visible)
            widget.setVisible(waveform_visible)
        for widget in [self.tempo_spin]:
            label = self._form.labelForField(widget) if self._form is not None else None
            if label is not None:
                label.setVisible(metronome_visible)
            widget.setVisible(metronome_visible)
        label = self._form.labelForField(self.timesig_num_spin) if self._form is not None else None
        if label is not None:
            label.setVisible(metronome_visible)
        parent = self.timesig_num_spin.parentWidget()
        if parent is not None:
            parent.setVisible(metronome_visible)

    def _browse_lyric_file(self) -> None:
        start_dir = self._start_dir
        current = self.lyric_file_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Lyric File"),
            start_dir,
            tr("Lyric Files (*.lrc *.srt);;All Files (*.*)"),
        )
        if file_path:
            self.lyric_file_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def _set_midi_binding(self, token: str) -> None:
        normalized = normalize_midi_binding(token)
        self._midi_binding = normalized
        self.sound_midi_hotkey_edit.setText(midi_binding_to_display(normalized) if normalized else "")

    def _start_midi_learn(self) -> None:
        self._midi_learning = True
        self.sound_midi_hotkey_edit.setStyleSheet("QLineEdit{border:2px solid #2E65FF;}")

    def _on_midi_binding(self, token: str, source_selector: str = "") -> None:
        if not self._midi_learning:
            return
        _prev_selector, normalized_token = split_midi_binding(token)
        if source_selector:
            self._set_midi_binding(f"{source_selector}|{normalized_token}")
        else:
            self._set_midi_binding(normalized_token)
        self._midi_learning = False
        self.sound_midi_hotkey_edit.setStyleSheet("")

    @staticmethod
    def _make_spin(low: int, high: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(int(low), int(high))
        return spin

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: object, fallback: object) -> None:
        target = value
        for idx in range(combo.count()):
            if combo.itemData(idx) == target:
                combo.setCurrentIndex(idx)
                return
        for idx in range(combo.count()):
            if combo.itemData(idx) == fallback:
                combo.setCurrentIndex(idx)
                return
