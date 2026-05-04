from __future__ import annotations

import math
from typing import Optional

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyssp.i18n import tr


class _SatelliteButton(QToolButton):
    pressedChanged = pyqtSignal(int, bool)

    def __init__(self, index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.index = int(index)
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(96, 96)
        self.setAutoRaise(False)
        self.setText("")
        self.setIconSize(QSize(56, 56))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.pressedChanged.emit(self.index, True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.pressedChanged.emit(self.index, False)
        super().mouseReleaseEvent(event)


class CompanionSatelliteWindow(QWidget):
    openOptionsRequested = pyqtSignal()
    buttonPressed = pyqtSignal(int, bool)
    windowClosed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setWindowFlag(Qt.Window, True)
        self.setWindowTitle(tr("Virtual Satellite"))
        self.resize(760, 520)
        self._columns = 5
        self._rows = 3
        self._render_mode = "bitmap"
        self._buttons: list[_SatelliteButton] = []
        self._button_states: dict[int, dict[str, object]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        header_layout = QHBoxLayout()
        self.target_label = QLabel("")
        header_layout.addWidget(self.target_label, 1)
        self.options_button = QToolButton(self)
        self.options_button.setText(tr("Options"))
        self.options_button.clicked.connect(self.openOptionsRequested.emit)
        header_layout.addWidget(self.options_button)
        root.addLayout(header_layout)

        self.grid_widget = QWidget(self)
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(8)
        self.grid_layout.setVerticalSpacing(8)
        root.addWidget(self.grid_widget, 1)

        self.set_target("127.0.0.1", 16622)
        self.set_grid_size(5, 3)
        self.set_render_mode("bitmap")

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.windowClosed.emit()

    def set_target(self, host: str, port: int) -> None:
        self.target_label.setText(f"{tr('Companion Target:')} {str(host or '').strip() or '127.0.0.1'}:{int(port)}")

    def set_grid_size(self, columns: int, rows: int) -> None:
        columns = max(1, int(columns))
        rows = max(1, int(rows))
        if columns == self._columns and rows == self._rows and self._buttons:
            return
        self._columns = columns
        self._rows = rows
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons = []
        total = columns * rows
        for index in range(total):
            button = _SatelliteButton(index, self.grid_widget)
            button.pressedChanged.connect(self.buttonPressed.emit)
            row = index // columns
            col = index % columns
            self.grid_layout.addWidget(button, row, col)
            self._buttons.append(button)
            self._apply_button_state(index, self._button_states.get(index, {}))

    def set_render_mode(self, mode: str) -> None:
        token = str(mode or "").strip().lower()
        self._render_mode = token if token in {"bitmap", "styled"} else "bitmap"
        for index in range(len(self._buttons)):
            self._apply_button_state(index, self._button_states.get(index, {}))

    def set_connection_state(self, state: str, message: str) -> None:
        return

    def clear_buttons(self) -> None:
        self._button_states.clear()
        for index, _button in enumerate(self._buttons):
            self._apply_button_state(index, {})

    def update_button(self, index: int, state: dict[str, object]) -> None:
        if index < 0:
            return
        self._button_states[int(index)] = dict(state or {})
        self._apply_button_state(int(index), self._button_states[int(index)])

    def _apply_button_state(self, index: int, state: dict[str, object]) -> None:
        if index < 0 or index >= len(self._buttons):
            return
        button = self._buttons[index]
        text = str(state.get("text", "") or "").strip()
        style_parts = [
            "QToolButton{border:1px solid #6C6C6C;border-radius:6px;padding:4px;}",
            "QToolButton:pressed{border:2px solid #F59E0B;}",
        ]
        bg_color = str(state.get("color", "") or "").strip()
        if bg_color:
            style_parts.insert(0, f"QToolButton{{background:{bg_color};}}")
        text_color = str(state.get('text_color', '') or '').strip()
        if text_color:
            style_parts.insert(0, f"QToolButton{{color:{text_color};}}")
        button.setStyleSheet("".join(style_parts))
        font = button.font()
        font_size = max(0, int(state.get("font_size", 0) or 0))
        if font_size > 0:
            font.setPointSize(max(6, min(36, int(round(font_size / 6.0)))))
        button.setFont(font)
        bitmap = state.get("bitmap", b"")
        if self._render_mode == "bitmap" and isinstance(bitmap, bytes) and bitmap:
            pixmap = self._pixmap(bitmap)
            if not pixmap.isNull():
                padding = 12
                button.setToolButtonStyle(Qt.ToolButtonIconOnly)
                button.setText("")
                button.setIcon(QIcon(pixmap))
                button.setIconSize(pixmap.size())
                button.setMinimumSize(pixmap.width() + padding, pixmap.height() + padding)
                button.setMaximumSize(pixmap.width() + padding, pixmap.height() + padding)
                button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            else:
                self._apply_styled_button(button, index, text)
        else:
            self._apply_styled_button(button, index, text)
        button.setToolTip(text or f"Key {index + 1}")

    def _apply_styled_button(self, button: _SatelliteButton, index: int, text: str) -> None:
        row = (int(index) // max(1, self._columns)) + 1
        col = (int(index) % max(1, self._columns)) + 1
        axis_text = f"X{col} Y{row}"
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        button.setIcon(QIcon())
        button.setText(f"{axis_text}\n{text}" if text else axis_text)
        button.setMinimumSize(96, 96)
        button.setMaximumSize(16777215, 16777215)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _pixmap(self, bitmap: bytes) -> QPixmap:
        pixel_count = max(1, len(bitmap) // 3)
        size = int(round(math.sqrt(pixel_count)))
        if size * size * 3 != len(bitmap):
            return QPixmap()
        image = QImage(bitmap, size, size, size * 3, QImage.Format_RGB888).copy()
        return QPixmap.fromImage(image)
