from __future__ import annotations

import platform
import traceback
from datetime import datetime
from pathlib import Path
from typing import Type

from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from pyssp.i18n import tr
from pyssp.version import get_display_version


class CrashReportDialog(QDialog):
    def __init__(self, exc_type: Type[BaseException], exc_value: BaseException, exc_tb, parent=None) -> None:
        super().__init__(parent)
        self._exc_type = exc_type
        self._exc_value = exc_value
        self._exc_tb = exc_tb
        self._traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle(tr("pySSP Error Occurred"))
        self.resize(860, 640)

        root = QVBoxLayout(self)

        message = QLabel(
            tr("pySSP hit an unexpected error and could not recover.\n"
               "Please describe what you were doing, then copy or save this report."),
            self,
        )
        message.setWordWrap(True)
        root.addWidget(message)

        desc_label = QLabel(tr("What were you doing?"), self)
        root.addWidget(desc_label)

        self.description_edit = QPlainTextEdit(self)
        self.description_edit.setPlaceholderText(tr("Describe the steps right before the error..."))
        root.addWidget(self.description_edit)

        tb_label = QLabel(tr("Error Traceback"), self)
        root.addWidget(tb_label)

        self.traceback_edit = QPlainTextEdit(self)
        self.traceback_edit.setReadOnly(True)
        self.traceback_edit.setPlainText(self._traceback_text)
        root.addWidget(self.traceback_edit, 1)

        buttons = QHBoxLayout()
        self.copy_button = QPushButton(tr("Copy Report"), self)
        self.save_button = QPushButton(tr("Save Report..."), self)
        self.close_button = QPushButton(tr("Close"), self)
        self.copy_button.clicked.connect(self._copy_report)
        self.save_button.clicked.connect(self._save_report)
        self.close_button.clicked.connect(self.accept)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.save_button)
        buttons.addStretch(1)
        buttons.addWidget(self.close_button)
        root.addLayout(buttons)

    def _build_report_text(self) -> str:
        description = self.description_edit.toPlainText().strip()
        lines = [
            "# pySSP Crash Report",
            "",
            f"Timestamp: {datetime.now().isoformat(timespec='seconds')}",
            f"App Version: {get_display_version()}",
            f"Python: {platform.python_version()}",
            f"Platform: {platform.platform()}",
            f"Qt: {QT_VERSION_STR}",
            f"PyQt: {PYQT_VERSION_STR}",
            "",
            "## Description",
            description or "(no description provided)",
            "",
            "## Traceback",
            self._traceback_text.rstrip(),
            "",
        ]
        return "\n".join(lines)

    def _copy_report(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._build_report_text())
            QMessageBox.information(self, tr("Copied"), tr("Crash report copied to clipboard."))

    def _save_report(self) -> None:
        default_name = f"pyssp-crash-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Save Crash Report"),
            str(Path.home() / default_name),
            tr("Text Files (*.txt *.log *.text)"),
        )
        if not file_path:
            return
        try:
            Path(file_path).write_text(self._build_report_text(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, tr("Save Failed"), f"{tr('Failed to save crash report.')}\n\n{exc}")

