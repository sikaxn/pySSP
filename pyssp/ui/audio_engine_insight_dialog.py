from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QVBoxLayout


class AudioEngineInsightDialog(QDialog):
    def __init__(self, snapshot_provider: Callable[[], str], parent=None) -> None:
        super().__init__(parent)
        self._snapshot_provider = snapshot_provider
        self.setWindowTitle("Audio Engine Insight")
        self.resize(860, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("Live audio engine player list and runtime details")
        title.setStyleSheet("QLabel{font-size:13pt;font-weight:bold;}")
        root.addWidget(title)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("QLabel{color:#50565D;}")
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self._status_label, 1)
        controls.addWidget(refresh_button)
        root.addLayout(controls)

        self._viewer = QPlainTextEdit(self)
        self._viewer.setReadOnly(True)
        self._viewer.setLineWrapMode(QPlainTextEdit.NoWrap)
        root.addWidget(self._viewer, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def refresh(self) -> None:
        try:
            text = str(self._snapshot_provider() or "").rstrip()
        except Exception as exc:
            text = f"Audio engine insight failed:\n{exc}"
        self._viewer.setPlainText(text)
        line_count = max(1, self._viewer.blockCount())
        self._status_label.setText(f"Auto refresh: 500 ms | Lines: {line_count}")
