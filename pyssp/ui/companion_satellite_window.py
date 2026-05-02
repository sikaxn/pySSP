from __future__ import annotations

import math
from typing import Optional

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
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
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
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
    startRequested = pyqtSignal()
    stopRequested = pyqtSignal()
    reconnectRequested = pyqtSignal()
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
        self._buttons: list[_SatelliteButton] = []
        self._button_states: dict[int, dict[str, object]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self.target_label = QLabel("")
        self.grid_label = QLabel("")
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        root.addWidget(self.target_label)
        root.addWidget(self.grid_label)
        root.addWidget(self.status_label)

        actions_layout = QHBoxLayout()
        self.start_button = QPushButton(tr("Start"))
        self.stop_button = QPushButton(tr("Stop"))
        self.reconnect_button = QPushButton(tr("Reconnect"))
        self.options_button = QPushButton(tr("Open Companion Satellite Options"))
        self.start_button.clicked.connect(self.startRequested.emit)
        self.stop_button.clicked.connect(self.stopRequested.emit)
        self.reconnect_button.clicked.connect(self.reconnectRequested.emit)
        self.options_button.clicked.connect(self.openOptionsRequested.emit)
        actions_layout.addWidget(self.start_button)
        actions_layout.addWidget(self.stop_button)
        actions_layout.addWidget(self.reconnect_button)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.options_button)
        root.addLayout(actions_layout)

        self.grid_widget = QWidget(self)
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(8)
        self.grid_layout.setVerticalSpacing(8)
        root.addWidget(self.grid_widget, 1)

        self.set_target("127.0.0.1", 16622)
        self.set_grid_size(5, 3)
        self.set_connection_state("stopped", "")

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.windowClosed.emit()

    def set_target(self, host: str, port: int) -> None:
        self.target_label.setText(f"{tr('Companion Target:')} {str(host or '').strip() or '127.0.0.1'}:{int(port)}")

    def set_grid_size(self, columns: int, rows: int) -> None:
        columns = max(1, int(columns))
        rows = max(1, int(rows))
        if columns == self._columns and rows == self._rows and self._buttons:
            self.grid_label.setText(f"{tr('Grid Size:')} {columns} x {rows}")
            return
        self._columns = columns
        self._rows = rows
        self.grid_label.setText(f"{tr('Grid Size:')} {columns} x {rows}")
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

    def set_connection_state(self, state: str, message: str) -> None:
        state_text = str(state or "").strip().lower()
        labels = {
            "connected": tr("Connected"),
            "connecting": tr("Connecting"),
            "reconnecting": tr("Reconnecting"),
            "disconnected": tr("Disconnected"),
            "error": tr("Error"),
            "stopped": tr("Stopped"),
        }
        label = labels.get(state_text, tr("Unknown"))
        text = f"{tr('Connection Status:')} {label}"
        if message:
            text = f"{text} ({message})"
        self.status_label.setText(text)
        active = state_text in {"connected", "connecting", "reconnecting"}
        self.start_button.setEnabled(not active)
        self.stop_button.setEnabled(active)
        self.reconnect_button.setEnabled(active)

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
        button.setText(text)
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
        if isinstance(bitmap, bytes) and bitmap:
            button.setIcon(self._pixmap_icon(bitmap))
        else:
            button.setIcon(QIcon())
        button.setToolTip(text or f"Key {index + 1}")

    def _pixmap_icon(self, bitmap: bytes) -> QIcon:
        pixel_count = max(1, len(bitmap) // 3)
        size = int(round(math.sqrt(pixel_count)))
        if size * size * 3 != len(bitmap):
            return QIcon()
        image = QImage(bitmap, size, size, size * 3, QImage.Format_RGB888).copy()
        return QIcon(QPixmap.fromImage(image))
