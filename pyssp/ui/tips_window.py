from __future__ import annotations

from pathlib import Path
import random
from typing import List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from pyssp.i18n import normalize_language, tr


class TipsWindow(QDialog):
    openOnStartupChanged = pyqtSignal(bool)

    def __init__(self, language: str = "en", open_on_startup: bool = True, parent=None) -> None:
        super().__init__(parent)
        self._language = normalize_language(language)
        self._tips: List[str] = []
        self._tip_index = 0

        self.setWindowTitle(tr("Tips", self._language))
        self.resize(460, 200)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        tip_row = QHBoxLayout()
        tip_row.setContentsMargins(0, 0, 0, 0)
        tip_row.setSpacing(10)

        self.icon_label = QLabel(self)
        self.icon_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.icon_label.setPixmap(self._lightbulb_pixmap(34))
        tip_row.addWidget(self.icon_label, 0)

        self.tip_label = QLabel(self)
        self.tip_label.setWordWrap(True)
        self.tip_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.tip_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        tip_font = self.tip_label.font()
        tip_font.setPointSize(max(13, tip_font.pointSize() + 3))
        self.tip_label.setFont(tip_font)
        tip_row.addWidget(self.tip_label, 1)
        root.addLayout(tip_row, 1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)

        self.open_on_startup_checkbox = QCheckBox(self)
        self.open_on_startup_checkbox.setChecked(bool(open_on_startup))
        self.open_on_startup_checkbox.toggled.connect(self.openOnStartupChanged.emit)
        controls.addWidget(self.open_on_startup_checkbox)
        controls.addStretch(1)

        self.previous_button = QPushButton(self)
        self.previous_button.clicked.connect(self.show_previous_tip)
        controls.addWidget(self.previous_button)

        self.next_button = QPushButton(self)
        self.next_button.clicked.connect(self.show_next_tip)
        controls.addWidget(self.next_button)

        self.close_button = QPushButton(self)
        self.close_button.clicked.connect(self.close)
        controls.addWidget(self.close_button)
        root.addLayout(controls)

        self.set_language(self._language)

    def set_language(self, language: str) -> None:
        self._language = normalize_language(language)
        self.setWindowTitle(tr("Tips", self._language))
        self.open_on_startup_checkbox.setText(tr("Open on startup", self._language))
        self.previous_button.setText(tr("Previous", self._language))
        self.next_button.setText(tr("Next", self._language))
        self.close_button.setText(tr("Close", self._language))
        self._tips = self._load_tips(self._language)
        if self._tip_index >= len(self._tips):
            self._tip_index = 0
        self._refresh_tip_text()

    def show_next_tip(self) -> None:
        if not self._tips:
            return
        self._tip_index = (self._tip_index + 1) % len(self._tips)
        self._refresh_tip_text()

    def show_previous_tip(self) -> None:
        if not self._tips:
            return
        self._tip_index = (self._tip_index - 1) % len(self._tips)
        self._refresh_tip_text()

    def pick_random_tip(self) -> None:
        if not self._tips:
            return
        self._tip_index = random.randrange(len(self._tips))
        self._refresh_tip_text()

    def set_open_on_startup(self, value: bool) -> None:
        self.open_on_startup_checkbox.setChecked(bool(value))

    def _refresh_tip_text(self) -> None:
        if not self._tips:
            self.tip_label.setText(tr("No tips available.", self._language))
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            return
        self.tip_label.setText(self._tips[self._tip_index])
        enable_nav = len(self._tips) > 1
        self.previous_button.setEnabled(enable_nav)
        self.next_button.setEnabled(enable_nav)

    def _load_tips(self, language: str) -> List[str]:
        base = Path(__file__).resolve().parents[1] / "assets"
        candidates = [base / f"tips_{language}.txt", base / "tips_en.txt"]
        text = ""
        for path in candidates:
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                break
        chunks = [chunk.strip() for chunk in text.replace("\r\n", "\n").split("\n\n")]
        return [chunk for chunk in chunks if chunk]

    @staticmethod
    def _lightbulb_pixmap(size: int) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)

        bulb_color = QColor("#FFD54D")
        bulb_outline = QColor("#C79200")
        base_color = QColor("#666666")
        base_outline = QColor("#444444")

        bulb_w = int(size * 0.62)
        bulb_h = int(size * 0.64)
        bulb_x = (size - bulb_w) // 2
        bulb_y = int(size * 0.06)

        painter.setPen(QPen(bulb_outline, 1.5))
        painter.setBrush(bulb_color)
        painter.drawEllipse(bulb_x, bulb_y, bulb_w, bulb_h)

        neck_w = int(size * 0.24)
        neck_h = int(size * 0.12)
        neck_x = (size - neck_w) // 2
        neck_y = bulb_y + bulb_h - int(neck_h * 0.35)
        painter.setBrush(QColor("#E8BE45"))
        painter.drawRoundedRect(neck_x, neck_y, neck_w, neck_h, 2, 2)

        base_w = int(size * 0.34)
        base_h = int(size * 0.18)
        base_x = (size - base_w) // 2
        base_y = neck_y + neck_h - 1
        painter.setPen(QPen(base_outline, 1.2))
        painter.setBrush(base_color)
        painter.drawRoundedRect(base_x, base_y, base_w, base_h, 2, 2)
        painter.drawLine(base_x + 2, base_y + int(base_h * 0.35), base_x + base_w - 2, base_y + int(base_h * 0.35))
        painter.drawLine(base_x + 2, base_y + int(base_h * 0.7), base_x + base_w - 2, base_y + int(base_h * 0.7))

        painter.end()
        return pix
