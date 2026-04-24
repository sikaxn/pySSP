from __future__ import annotations

from ..shared import *
from ..widgets import *


class LanguagePageMixin:
    def _build_language_page(self, ui_language: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.ui_language_combo = QComboBox()
        self.ui_language_combo.addItem("English", "en")
        self.ui_language_combo.addItem("Chinese (Simplified)", "zh_cn")
        index = self.ui_language_combo.findData(normalize_language(ui_language))
        self.ui_language_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("UI Language", self.ui_language_combo)
        layout.addLayout(form)
        note = QLabel("App language (requires reopen dialogs/windows to fully refresh).")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

