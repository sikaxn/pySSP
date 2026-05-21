from __future__ import annotations

import os
import re
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from pyssp.audio_format_support import build_audio_file_dialog_filter
from pyssp.audio_beat_map import AudioBeatMap, normalize_audio_beat_map
from pyssp.display_focus import DISPLAY_FOCUS_LABELS, DISPLAY_FOCUS_VALUES, normalize_display_focus
from pyssp.i18n import localize_widget_tree, tr
from pyssp.midi_control import (
    midi_binding_to_display,
    midi_input_name_selector,
    normalize_midi_binding,
    split_midi_binding,
)


class SoundHotkeyEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(tr("Optional: A-O, Q-Z, 0-9, F1-F12 (except F10)"))
        self.setReadOnly(True)

    def setHotkey(self, value: str) -> None:
        self.setText(self.normalize(value))

    def hotkey(self) -> str:
        return self.normalize(self.text())

    def keyPressEvent(self, event) -> None:
        key = int(event.key())
        if key in {Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Escape}:
            self.clear()
            return
        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier):
            return
        name = self.normalize(event.text() or "")
        if not name and Qt.Key_F1 <= key <= Qt.Key_F12:
                name = f"F{key - Qt.Key_F1 + 1}"
        self.setText(self.normalize(name))

    @staticmethod
    def normalize(value: str) -> str:
        raw = str(value or "").strip().upper()
        if not raw:
            return ""
        if re.fullmatch(r"[A-OQ-Z]", raw):
            return raw
        if re.fullmatch(r"[0-9]", raw):
            return raw
        if re.fullmatch(r"F([1-9]|1[1-2])", raw):
            if raw == "F10":
                return ""
            return raw
        return ""


class EditSoundButtonDialog(QDialog):
    REGENERATE_RESULT = 1001
    ANALYZE_BPM_RESULT = 1002

    def __init__(
        self,
        file_path: str,
        caption: str,
        notes: str,
        disable_video_loading: bool = False,
        lyric_file: str = "",
        automation_script_path: str = "",
        vocal_removed_file: str = "",
        volume_override_pct: Optional[int] = None,
        sound_hotkey: str = "",
        sound_midi_hotkey: str = "",
        display_focus: str = "",
        display_image_path: str = "",
        audio_beat_map: Optional[AudioBeatMap] = None,
        available_midi_input_devices: Optional[list[tuple[str, str]]] = None,
        selected_midi_input_device_ids: Optional[list[str]] = None,
        start_dir: str = "",
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Edit Sound Button"))
        self.resize(760, 320)
        self._start_dir = start_dir

        root = QVBoxLayout(self)
        form = QFormLayout()

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_edit = QLineEdit(file_path)
        self.browse_btn = QPushButton(tr("Browse"))
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(self.browse_btn)
        form.addRow(tr("File"), file_row)

        self.disable_video_loading_checkbox = QCheckBox(tr("Do not load video"))
        self.disable_video_loading_checkbox.setChecked(bool(disable_video_loading))
        form.addRow("", self.disable_video_loading_checkbox)

        self.caption_edit = QLineEdit(caption)
        form.addRow(tr("Caption"), self.caption_edit)

        self.notes_edit = QLineEdit(notes)
        form.addRow(tr("Notes"), self.notes_edit)

        self.display_focus_combo = QComboBox()
        for value in [
            "none",
            "video",
            "image",
            "lyric_display",
            "stage_display",
            "backdrop",
            "white_screen",
            "colour_bars",
            "metronome_display",
        ]:
            self.display_focus_combo.addItem(DISPLAY_FOCUS_LABELS.get(value, value), value)
        normalized_display_focus = normalize_display_focus(display_focus, allow_empty=True, default="none")
        focus_index = self.display_focus_combo.findData(normalized_display_focus or "none")
        self.display_focus_combo.setCurrentIndex(focus_index if focus_index >= 0 else 0)
        form.addRow(tr("Display Focus"), self.display_focus_combo)

        display_image_row = QWidget()
        display_image_layout = QHBoxLayout(display_image_row)
        display_image_layout.setContentsMargins(0, 0, 0, 0)
        self.display_image_edit = QLineEdit(display_image_path)
        self.display_image_browse_btn = QPushButton(tr("Browse"))
        self.display_image_browse_btn.clicked.connect(self._browse_display_image_file)
        self.display_image_clear_btn = QPushButton(tr("Clear"))
        self.display_image_clear_btn.clicked.connect(lambda _=False: self.display_image_edit.setText(""))
        display_image_layout.addWidget(self.display_image_edit, 1)
        display_image_layout.addWidget(self.display_image_browse_btn)
        display_image_layout.addWidget(self.display_image_clear_btn)
        form.addRow(tr("Display Image"), display_image_row)

        normalized_audio_beat_map = normalize_audio_beat_map(audio_beat_map)
        self._audio_beat_times_ms = [] if normalized_audio_beat_map is None else list(normalized_audio_beat_map.beat_times_ms)
        self._audio_beat_numbers = [] if normalized_audio_beat_map is None else list(normalized_audio_beat_map.beat_numbers)
        self._audio_beat_source = "" if normalized_audio_beat_map is None else str(normalized_audio_beat_map.source or "")
        self._audio_beat_confidence = 0.0 if normalized_audio_beat_map is None else float(normalized_audio_beat_map.confidence or 0.0)
        self._audio_analysis_method = "" if normalized_audio_beat_map is None else str(normalized_audio_beat_map.analysis_method or "")
        self._audio_analysis_confidence = (
            0.0 if normalized_audio_beat_map is None else float(normalized_audio_beat_map.analysis_confidence or 0.0)
        )
        self._audio_analysis_version = "" if normalized_audio_beat_map is None else str(normalized_audio_beat_map.analysis_version or "")
        self.audio_metronome_enabled_checkbox = QCheckBox(tr("Enable metronome timing for this audio"))
        self.audio_metronome_enabled_checkbox.setChecked(normalized_audio_beat_map is not None)
        form.addRow("", self.audio_metronome_enabled_checkbox)

        self.audio_bpm_spin = QDoubleSpinBox()
        self.audio_bpm_spin.setRange(1.0, 999.0)
        self.audio_bpm_spin.setDecimals(2)
        self.audio_bpm_spin.setSingleStep(0.25)
        self.audio_bpm_spin.setValue(120.0 if normalized_audio_beat_map is None else float(normalized_audio_beat_map.bpm))
        form.addRow(tr("Metronome BPM"), self.audio_bpm_spin)

        self.audio_timesig_num_spin = QSpinBox()
        self.audio_timesig_num_spin.setRange(1, 12)
        self.audio_timesig_num_spin.setValue(4 if normalized_audio_beat_map is None else int(normalized_audio_beat_map.time_signature_num))
        form.addRow(tr("Beats Per Bar"), self.audio_timesig_num_spin)

        self.audio_timesig_den_combo = QComboBox()
        for value in (2, 4, 8, 16):
            self.audio_timesig_den_combo.addItem(str(value), value)
        target_denominator = 4 if normalized_audio_beat_map is None else int(normalized_audio_beat_map.time_signature_den)
        denominator_index = self.audio_timesig_den_combo.findData(target_denominator)
        self.audio_timesig_den_combo.setCurrentIndex(denominator_index if denominator_index >= 0 else 1)
        form.addRow(tr("Beat Unit"), self.audio_timesig_den_combo)

        self.audio_downbeat_offset_spin = QSpinBox()
        self.audio_downbeat_offset_spin.setRange(0, 24 * 60 * 60 * 1000)
        self.audio_downbeat_offset_spin.setSingleStep(10)
        self.audio_downbeat_offset_spin.setValue(0 if normalized_audio_beat_map is None else int(normalized_audio_beat_map.first_downbeat_ms))
        form.addRow(tr("First Downbeat ms"), self.audio_downbeat_offset_spin)

        analysis_row = QWidget()
        analysis_layout = QHBoxLayout(analysis_row)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        self.audio_analysis_status_label = QLabel("")
        self.audio_analyze_btn = QPushButton(tr("Analyze BPM"))
        self.audio_analyze_btn.clicked.connect(self._request_analyze_bpm)
        self.audio_clear_analysis_btn = QPushButton(tr("Clear"))
        self.audio_clear_analysis_btn.clicked.connect(self._clear_audio_analysis)
        analysis_layout.addWidget(self.audio_analysis_status_label, 1)
        analysis_layout.addWidget(self.audio_analyze_btn)
        analysis_layout.addWidget(self.audio_clear_analysis_btn)
        form.addRow(tr("Analysis"), analysis_row)

        vocal_row = QWidget()
        vocal_layout = QHBoxLayout(vocal_row)
        vocal_layout.setContentsMargins(0, 0, 0, 0)
        self.vocal_removed_file_edit = QLineEdit(vocal_removed_file)
        self.vocal_removed_browse_btn = QPushButton(tr("Browse"))
        self.vocal_removed_browse_btn.clicked.connect(self._browse_vocal_removed_file)
        self.vocal_removed_regen_btn = QPushButton(tr("Regenerate"))
        self.vocal_removed_regen_btn.clicked.connect(self._request_regenerate_vocal_removed)
        self.vocal_removed_clear_btn = QPushButton(tr("Clear"))
        self.vocal_removed_clear_btn.clicked.connect(lambda _=False: self.vocal_removed_file_edit.setText(""))
        vocal_layout.addWidget(self.vocal_removed_file_edit, 1)
        vocal_layout.addWidget(self.vocal_removed_browse_btn)
        vocal_layout.addWidget(self.vocal_removed_regen_btn)
        vocal_layout.addWidget(self.vocal_removed_clear_btn)
        form.addRow(tr("Vocal Removed File"), vocal_row)

        lyric_row = QWidget()
        lyric_layout = QHBoxLayout(lyric_row)
        lyric_layout.setContentsMargins(0, 0, 0, 0)
        self.lyric_file_edit = QLineEdit(lyric_file)
        self.lyric_browse_btn = QPushButton(tr("Browse"))
        self.lyric_browse_btn.clicked.connect(self._browse_lyric_file)
        self.lyric_clear_btn = QPushButton(tr("Clear"))
        self.lyric_clear_btn.clicked.connect(lambda _=False: self.lyric_file_edit.setText(""))
        lyric_layout.addWidget(self.lyric_file_edit, 1)
        lyric_layout.addWidget(self.lyric_browse_btn)
        lyric_layout.addWidget(self.lyric_clear_btn)
        form.addRow(tr("Lyric File"), lyric_row)

        script_row = QWidget()
        script_layout = QHBoxLayout(script_row)
        script_layout.setContentsMargins(0, 0, 0, 0)
        self.automation_script_edit = QLineEdit(automation_script_path)
        self.automation_script_browse_btn = QPushButton(tr("Browse"))
        self.automation_script_browse_btn.clicked.connect(self._browse_automation_script_file)
        self.automation_script_clear_btn = QPushButton(tr("Clear"))
        self.automation_script_clear_btn.clicked.connect(lambda _=False: self.automation_script_edit.setText(""))
        script_layout.addWidget(self.automation_script_edit, 1)
        script_layout.addWidget(self.automation_script_browse_btn)
        script_layout.addWidget(self.automation_script_clear_btn)
        form.addRow(tr("Automation Script"), script_row)

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
        available_by_id = {str(device_id).strip(): str(device_name).strip() for device_id, device_name in (available_midi_input_devices or [])}
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
        self.volume_slider = QSlider()
        self.volume_slider.setOrientation(Qt.Horizontal)
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
        self.display_focus_combo.currentIndexChanged.connect(self._sync_display_focus_controls)
        self.audio_metronome_enabled_checkbox.toggled.connect(self._sync_audio_beat_controls)
        self.audio_metronome_enabled_checkbox.toggled.connect(lambda _checked=False: self._refresh_audio_analysis_status())
        _sync_volume_label(self.volume_slider.value())
        _sync_slider_enabled(self.custom_volume_checkbox.isChecked())
        self._sync_display_focus_controls()
        self._sync_audio_beat_controls()
        self._refresh_audio_analysis_status()

        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        localize_widget_tree(self, language)

    def _browse_file(self) -> None:
        start_dir = self._start_dir
        current = self.file_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Sound File"),
            start_dir,
            build_audio_file_dialog_filter([], True),
        )
        if file_path:
            self.file_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def values(self) -> tuple[str, str, str, bool, str, str, str, Optional[int], str, str, str, str, Optional[AudioBeatMap]]:
        volume_override_pct: Optional[int] = None
        if self.custom_volume_checkbox.isChecked():
            volume_override_pct = max(0, min(100, int(self.volume_slider.value())))
        return (
            self.file_edit.text().strip(),
            self.caption_edit.text().strip(),
            self.notes_edit.text().strip(),
            bool(self.disable_video_loading_checkbox.isChecked()),
            self.vocal_removed_file_edit.text().strip(),
            self.lyric_file_edit.text().strip(),
            self.automation_script_edit.text().strip(),
            volume_override_pct,
            self.sound_hotkey_edit.hotkey(),
            self._midi_binding,
            normalize_display_focus(str(self.display_focus_combo.currentData() or ""), default="none"),
            self.display_image_edit.text().strip(),
            self._audio_beat_map_from_inputs(),
        )

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

    def _browse_vocal_removed_file(self) -> None:
        start_dir = self._start_dir
        current = self.vocal_removed_file_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Vocal Removed File"),
            start_dir,
            tr("Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)"),
        )
        if file_path:
            self.vocal_removed_file_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def _browse_automation_script_file(self) -> None:
        start_dir = self._start_dir
        current = self.automation_script_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Automation Script"),
            start_dir,
            tr("Automation Script Files (*.pysspautoscript);;All Files (*.*)"),
        )
        if file_path:
            self.automation_script_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def _browse_display_image_file(self) -> None:
        start_dir = self._start_dir
        current = self.display_image_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Select Display Image"),
            start_dir,
            tr("Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*.*)"),
        )
        if file_path:
            self.display_image_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def _sync_display_focus_controls(self) -> None:
        mode = normalize_display_focus(str(self.display_focus_combo.currentData() or ""), default="none")
        enabled = mode == "image"
        self.display_image_edit.setEnabled(enabled)
        self.display_image_browse_btn.setEnabled(enabled)
        self.display_image_clear_btn.setEnabled(enabled)
        if not enabled:
            self.display_image_edit.setText(self.display_image_edit.text().strip())

    def _sync_audio_beat_controls(self) -> None:
        enabled = bool(self.audio_metronome_enabled_checkbox.isChecked())
        for widget in (
            self.audio_bpm_spin,
            self.audio_timesig_num_spin,
            self.audio_timesig_den_combo,
            self.audio_downbeat_offset_spin,
            self.audio_clear_analysis_btn,
        ):
            widget.setEnabled(enabled)

    def _refresh_audio_analysis_status(self) -> None:
        if not self._audio_beat_times_ms:
            if self.audio_metronome_enabled_checkbox.isChecked():
                self.audio_analysis_status_label.setText(tr("Manual timing"))
            else:
                self.audio_analysis_status_label.setText(tr("No analysis"))
            return
        source = str(self._audio_analysis_method or self._audio_beat_source or "analysis").replace("_", " ").strip().title()
        confidence = int(
            round(
                max(
                    0.0,
                    min(
                        1.0,
                        float(self._audio_analysis_confidence or self._audio_beat_confidence or 0.0),
                    ),
                )
                * 100.0
            )
        )
        self.audio_analysis_status_label.setText(
            f"{source}: {len(self._audio_beat_times_ms)} beats, {confidence}%"
        )

    def _audio_beat_map_from_inputs(self) -> Optional[AudioBeatMap]:
        if not self.audio_metronome_enabled_checkbox.isChecked():
            return None
        denominator = int(self.audio_timesig_den_combo.currentData() or 4)
        return normalize_audio_beat_map(
            AudioBeatMap(
                bpm=float(self.audio_bpm_spin.value()),
                time_signature_num=int(self.audio_timesig_num_spin.value()),
                time_signature_den=denominator,
                first_downbeat_ms=int(self.audio_downbeat_offset_spin.value()),
                beat_times_ms=list(self._audio_beat_times_ms),
                beat_numbers=list(self._audio_beat_numbers),
                source=str(self._audio_beat_source or "manual"),
                confidence=float(self._audio_beat_confidence or 0.0),
                analysis_method=str(self._audio_analysis_method or self._audio_beat_source or "manual"),
                analysis_confidence=float(self._audio_analysis_confidence or self._audio_beat_confidence or 0.0),
                analysis_version=str(self._audio_analysis_version or "1"),
            )
        )

    def _request_regenerate_vocal_removed(self) -> None:
        self.done(self.REGENERATE_RESULT)

    def _request_analyze_bpm(self) -> None:
        self.done(self.ANALYZE_BPM_RESULT)

    def _clear_audio_analysis(self) -> None:
        self.audio_metronome_enabled_checkbox.setChecked(False)
        self.audio_bpm_spin.setValue(120.0)
        self.audio_timesig_num_spin.setValue(4)
        denominator_index = self.audio_timesig_den_combo.findData(4)
        self.audio_timesig_den_combo.setCurrentIndex(denominator_index if denominator_index >= 0 else 0)
        self.audio_downbeat_offset_spin.setValue(0)
        self._audio_beat_times_ms = []
        self._audio_beat_numbers = []
        self._audio_beat_source = ""
        self._audio_beat_confidence = 0.0
        self._audio_analysis_method = ""
        self._audio_analysis_confidence = 0.0
        self._audio_analysis_version = ""
        self._refresh_audio_analysis_status()

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
            if not source_selector:
                return False
            if source_selector not in self._allowed_midi_selectors:
                return False
        self._on_midi_binding(token, source_selector)
        return True
