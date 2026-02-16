from __future__ import annotations

import os
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class EditSoundButtonDialog(QDialog):
    def __init__(
        self,
        file_path: str,
        caption: str,
        notes: str,
        start_dir: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Sound Button")
        self.resize(640, 220)
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

    def values(self) -> tuple[str, str, str]:
        return (
            self.file_edit.text().strip(),
            self.caption_edit.text().strip(),
            self.notes_edit.text().strip(),
        )
