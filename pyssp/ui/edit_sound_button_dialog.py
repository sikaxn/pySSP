from __future__ import annotations

import os
import re
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SoundHotkeyEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Optional: A-O, Q-Z, 0-9, F1-F12 (except F10)")
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
    def __init__(
        self,
        file_path: str,
        caption: str,
        notes: str,
        volume_override_pct: Optional[int] = None,
        sound_hotkey: str = "",
        start_dir: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Sound Button")
        self.resize(700, 280)
        self._start_dir = start_dir

        root = QVBoxLayout(self)
        form = QFormLayout()

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_edit = QLineEdit(file_path)
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(self.browse_btn)
        form.addRow("File", file_row)

        self.caption_edit = QLineEdit(caption)
        form.addRow("Caption", self.caption_edit)

        self.notes_edit = QLineEdit(notes)
        form.addRow("Notes", self.notes_edit)

        hk_row = QWidget()
        hk_layout = QHBoxLayout(hk_row)
        hk_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_hotkey_edit = SoundHotkeyEdit()
        self.sound_hotkey_edit.setHotkey(sound_hotkey)
        clear_hk_btn = QPushButton("Clear")
        clear_hk_btn.clicked.connect(lambda _=False: self.sound_hotkey_edit.setHotkey(""))
        hk_layout.addWidget(self.sound_hotkey_edit, 1)
        hk_layout.addWidget(clear_hk_btn)
        form.addRow("Sound Button Hot Key", hk_row)

        vol_row = QWidget()
        vol_layout = QVBoxLayout(vol_row)
        vol_layout.setContentsMargins(0, 0, 0, 0)
        vol_layout.setSpacing(4)
        self.custom_volume_checkbox = QCheckBox("Use custom playback volume")
        self.custom_volume_checkbox.setChecked(volume_override_pct is not None)
        vol_layout.addWidget(self.custom_volume_checkbox)
        self.volume_label = QLabel("")
        vol_layout.addWidget(self.volume_label)
        self.volume_slider = QSlider()
        self.volume_slider.setOrientation(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75 if volume_override_pct is None else max(0, min(100, int(volume_override_pct))))
        vol_layout.addWidget(self.volume_slider)
        form.addRow("Playback Volume", vol_row)

        def _sync_volume_label(value: int) -> None:
            self.volume_label.setText(f"{value}%")

        def _sync_slider_enabled(checked: bool) -> None:
            self.volume_slider.setEnabled(checked)
            self.volume_label.setEnabled(checked)

        self.volume_slider.valueChanged.connect(_sync_volume_label)
        self.custom_volume_checkbox.toggled.connect(_sync_slider_enabled)
        _sync_volume_label(self.volume_slider.value())
        _sync_slider_enabled(self.custom_volume_checkbox.isChecked())

        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_file(self) -> None:
        start_dir = self._start_dir
        current = self.file_edit.text().strip()
        if current:
            start_dir = os.path.dirname(current) or start_dir
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Sound File",
            start_dir,
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)",
        )
        if file_path:
            self.file_edit.setText(file_path)
            self._start_dir = os.path.dirname(file_path)

    def values(self) -> tuple[str, str, str, Optional[int], str]:
        volume_override_pct: Optional[int] = None
        if self.custom_volume_checkbox.isChecked():
            volume_override_pct = max(0, min(100, int(self.volume_slider.value())))
        return (
            self.file_edit.text().strip(),
            self.caption_edit.text().strip(),
            self.notes_edit.text().strip(),
            volume_override_pct,
            self.sound_hotkey_edit.hotkey(),
        )
