from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QEvent, QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pyssp.i18n import tr

STAGE_DISPLAY_GADGET_SPECS: List[Tuple[str, str]] = [
    ("current_time", "Current Time"),
    ("alert", "Alert"),
    ("total_time", "Total Time"),
    ("elapsed", "Elapsed"),
    ("remaining", "Remaining"),
    ("progress_bar", "Progress Bar"),
    ("song_name", "Song Name"),
    ("next_song", "Next Song"),
]
STAGE_DISPLAY_GADGET_KEYS = [key for key, _label in STAGE_DISPLAY_GADGET_SPECS]


def default_stage_display_gadgets() -> Dict[str, Dict[str, int | bool | str]]:
    return {
        "current_time": {
            "x": 1500,
            "y": 200,
            "w": 7000,
            "h": 700,
            "z": 0,
            "visible": True,
            "orientation": "horizontal",
            "hide_text": True,
            "hide_border": True,
        },
        "alert": {
            "x": 0,
            "y": 0,
            "w": 10000,
            "h": 10000,
            "z": 99,
            "visible": False,
            "orientation": "vertical",
            "hide_text": True,
            "hide_border": False,
        },
        "total_time": {
            "x": 400,
            "y": 1100,
            "w": 3000,
            "h": 1300,
            "z": 1,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "elapsed": {
            "x": 3500,
            "y": 1100,
            "w": 3000,
            "h": 1300,
            "z": 2,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "remaining": {
            "x": 6600,
            "y": 1100,
            "w": 3000,
            "h": 1300,
            "z": 3,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "progress_bar": {
            "x": 600,
            "y": 2800,
            "w": 8800,
            "h": 1100,
            "z": 4,
            "visible": True,
            "orientation": "horizontal",
            "hide_text": False,
            "hide_border": False,
        },
        "song_name": {
            "x": 500,
            "y": 4300,
            "w": 9000,
            "h": 2100,
            "z": 5,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
        "next_song": {
            "x": 500,
            "y": 6800,
            "w": 9000,
            "h": 2100,
            "z": 6,
            "visible": True,
            "orientation": "vertical",
            "hide_text": False,
            "hide_border": False,
        },
    }


def normalize_stage_display_gadgets(
    values: Optional[Dict[str, Dict[str, object]]],
    legacy_layout: Optional[List[str]] = None,
    legacy_visibility: Optional[Dict[str, bool]] = None,
) -> Dict[str, Dict[str, int | bool | str]]:
    defaults = default_stage_display_gadgets()
    raw = dict(values or {})
    for key in STAGE_DISPLAY_GADGET_KEYS:
        source = dict(raw.get(key, {})) if isinstance(raw.get(key), dict) else {}
        base = dict(defaults[key])
        x = _coerce_int(source.get("x"), int(base["x"]), 0, 9800)
        y = _coerce_int(source.get("y"), int(base["y"]), 0, 9800)
        w = _coerce_int(source.get("w"), int(base["w"]), 600, 10000)
        h = _coerce_int(source.get("h"), int(base["h"]), 500, 10000)
        z = _coerce_int(source.get("z"), int(base["z"]), 0, 100)
        visible = bool(source.get("visible", base["visible"]))
        orientation = str(source.get("orientation", base["orientation"])).strip().lower()
        if orientation not in {"horizontal", "vertical"}:
            orientation = str(base["orientation"])
        hide_text = bool(source.get("hide_text", base["hide_text"]))
        hide_border = bool(source.get("hide_border", base["hide_border"]))
        defaults[key] = {
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "z": z,
            "visible": visible,
            "orientation": orientation,
            "hide_text": hide_text,
            "hide_border": hide_border,
        }
    if legacy_layout:
        normalized_order = []
        for token in list(legacy_layout or []):
            key = str(token or "").strip().lower()
            if key in STAGE_DISPLAY_GADGET_KEYS and key not in normalized_order:
                normalized_order.append(key)
        for key in STAGE_DISPLAY_GADGET_KEYS:
            if key not in normalized_order:
                normalized_order.append(key)
        for index, key in enumerate(normalized_order):
            defaults[key]["z"] = index
    if legacy_visibility:
        for key in STAGE_DISPLAY_GADGET_KEYS:
            if key in legacy_visibility:
                defaults[key]["visible"] = bool(legacy_visibility.get(key, True))
    return defaults


def gadgets_to_legacy_layout_visibility(gadgets: Dict[str, Dict[str, object]]) -> Tuple[List[str], Dict[str, bool]]:
    normalized = normalize_stage_display_gadgets(gadgets)
    order = sorted(STAGE_DISPLAY_GADGET_KEYS, key=lambda key: int(normalized[key]["z"]))
    visibility = {key: bool(normalized[key]["visible"]) for key in STAGE_DISPLAY_GADGET_KEYS}
    return order, visibility


class _GadgetFrame(QFrame):
    changed = pyqtSignal(str)
    selected = pyqtSignal(str)

    def __init__(self, key: str, title: str, draggable: bool, parent: QWidget) -> None:
        super().__init__(parent)
        self.key = key
        self._draggable = draggable
        self._drag_mode = ""
        self._drag_offset = QPoint()
        self._drag_start_rect = QRect()
        self._start_pos = QPoint()
        self._selected = False
        self._hide_text = False
        self._hide_border = False
        self._orientation = "vertical"
        self.setObjectName(f"stage_gadget_{key}")
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)
        self._base_background = "#111111"
        self._apply_frame_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        self._layout = layout
        self.title_label = QLabel(title, self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color:#D0D0D0;")
        self.value_label = QLabel("-", self)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setWordWrap(True)
        self.value_label.setStyleSheet("color:#FFFFFF;")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label, 1)

        self._resize_handle = QFrame(self)
        self._resize_handle.setFixedSize(10, 10)
        self._resize_handle.setStyleSheet("QFrame{background:#7A7A7A;border:1px solid #A0A0A0;border-radius:2px;}")
        self._resize_handle.setVisible(draggable)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_handle.move(max(0, self.width() - 12), max(0, self.height() - 12))
        self._apply_fonts()

    def _apply_fonts(self) -> None:
        area = max(1, self.width() * self.height())
        scale = max(0.8, min(3.8, (area / 170000.0) ** 0.5))
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(max(11, int(13 * scale)))
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        value_font = QFont(self.value_label.font())
        value_font.setPointSize(max(16, int(24 * scale)))
        value_font.setBold(True)
        self.value_label.setFont(value_font)

    def apply_config(self, orientation: str, hide_text: bool, hide_border: bool) -> None:
        token = str(orientation or "").strip().lower()
        self._orientation = token if token in {"horizontal", "vertical"} else "vertical"
        self._hide_text = bool(hide_text)
        self._hide_border = bool(hide_border)
        self.title_label.setVisible(not self._hide_text)
        if self._orientation == "horizontal":
            self._layout.setDirection(QBoxLayout.LeftToRight)
            self._layout.setSpacing(14)
            self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.value_label.setAlignment(Qt.AlignCenter)
        else:
            self._layout.setDirection(QBoxLayout.TopToBottom)
            self._layout.setSpacing(8)
            self.title_label.setAlignment(Qt.AlignCenter)
            self.value_label.setAlignment(Qt.AlignCenter)
        self._apply_frame_style()
        self._apply_fonts()

    def _apply_frame_style(self) -> None:
        if self._selected:
            border = "2px solid #45A0FF"
        elif self._hide_border:
            border = "0px solid transparent"
        else:
            border = "1px solid #3A3A3A"
        self.setStyleSheet(
            f"QFrame{{background:{self._base_background}; border:{border}; border-radius:4px;}}"
            "QLabel{color:#FFFFFF;}"
        )

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_frame_style()

    def mousePressEvent(self, event) -> None:
        if not self._draggable or event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self.selected.emit(self.key)
        self.raise_()
        self._start_pos = event.globalPos()
        self._drag_start_rect = self.geometry()
        edge = 14
        if event.pos().x() >= self.width() - edge and event.pos().y() >= self.height() - edge:
            self._drag_mode = "resize"
        else:
            self._drag_mode = "move"
            self._drag_offset = event.pos()
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if not self._draggable or not (event.buttons() & Qt.LeftButton) or not self._drag_mode:
            super().mouseMoveEvent(event)
            return
        parent = self.parentWidget()
        if parent is None:
            return
        parent_rect = parent.rect()
        if self._drag_mode == "move":
            target = self.mapToParent(event.pos() - self._drag_offset)
            x = max(0, min(parent_rect.width() - self.width(), target.x()))
            y = max(0, min(parent_rect.height() - self.height(), target.y()))
            self.move(x, y)
            self.changed.emit(self.key)
        elif self._drag_mode == "resize":
            delta = event.globalPos() - self._start_pos
            new_w = max(80, self._drag_start_rect.width() + delta.x())
            new_h = max(60, self._drag_start_rect.height() + delta.y())
            max_w = max(80, parent_rect.width() - self.x())
            max_h = max(60, parent_rect.height() - self.y())
            self.resize(min(new_w, max_w), min(new_h, max_h))
            self.changed.emit(self.key)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_mode:
            self.changed.emit(self.key)
        self._drag_mode = ""
        super().mouseReleaseEvent(event)


class StageDisplayLayoutEditor(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(520, 320)
        self.setStyleSheet("background:#000000;")
        self._gadgets = default_stage_display_gadgets()
        self._widgets: Dict[str, _GadgetFrame] = {}
        self._selected_key: Optional[str] = None
        labels = dict(STAGE_DISPLAY_GADGET_SPECS)
        for key in STAGE_DISPLAY_GADGET_KEYS:
            widget = _GadgetFrame(key, labels.get(key, key), True, self)
            widget.selected.connect(self._on_widget_selected)
            widget.changed.connect(self._on_widget_changed)
            self._widgets[key] = widget

    def set_gadgets(self, gadgets: Dict[str, Dict[str, object]]) -> None:
        self._gadgets = normalize_stage_display_gadgets(gadgets)
        self._apply_geometry()

    def gadgets(self) -> Dict[str, Dict[str, int | bool | str]]:
        return normalize_stage_display_gadgets(deepcopy(self._gadgets))

    def set_gadget_visible(self, key: str, visible: bool) -> None:
        if key not in self._gadgets:
            return
        self._gadgets[key]["visible"] = bool(visible)
        self._apply_geometry()

    def set_gadget_orientation(self, key: str, orientation: str) -> None:
        if key not in self._gadgets:
            return
        token = str(orientation or "").strip().lower()
        self._gadgets[key]["orientation"] = token if token in {"horizontal", "vertical"} else "vertical"
        self._apply_geometry()

    def set_gadget_hide_text(self, key: str, hide_text: bool) -> None:
        if key not in self._gadgets:
            return
        self._gadgets[key]["hide_text"] = bool(hide_text)
        self._apply_geometry()

    def set_gadget_hide_border(self, key: str, hide_border: bool) -> None:
        if key not in self._gadgets:
            return
        self._gadgets[key]["hide_border"] = bool(hide_border)
        self._apply_geometry()

    def layer_order(self) -> List[str]:
        return sorted(STAGE_DISPLAY_GADGET_KEYS, key=lambda token: int(self._gadgets[token]["z"]))

    def set_layer_order(self, order: List[str]) -> None:
        normalized: List[str] = []
        for raw in list(order or []):
            key = str(raw or "").strip().lower()
            if key in STAGE_DISPLAY_GADGET_KEYS and key not in normalized:
                normalized.append(key)
        for key in STAGE_DISPLAY_GADGET_KEYS:
            if key not in normalized:
                normalized.append(key)
        for index, key in enumerate(normalized):
            self._gadgets[key]["z"] = index
        self._apply_geometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_geometry()

    def _apply_geometry(self) -> None:
        area = self.rect()
        for key in sorted(STAGE_DISPLAY_GADGET_KEYS, key=lambda k: int(self._gadgets[k]["z"])):
            spec = self._gadgets[key]
            widget = self._widgets[key]
            rect = _norm_to_rect(spec, area)
            widget.setGeometry(rect)
            widget.setVisible(bool(spec["visible"]))
            widget.apply_config(
                orientation=str(spec.get("orientation", "vertical")),
                hide_text=bool(spec.get("hide_text", False)),
                hide_border=bool(spec.get("hide_border", False)),
            )
            widget.raise_()

    def _on_widget_selected(self, key: str) -> None:
        self._selected_key = key
        top_z = max(int(self._gadgets[k]["z"]) for k in STAGE_DISPLAY_GADGET_KEYS)
        self._gadgets[key]["z"] = top_z + 1
        ordered = sorted(STAGE_DISPLAY_GADGET_KEYS, key=lambda token: int(self._gadgets[token]["z"]))
        for index, token in enumerate(ordered):
            self._gadgets[token]["z"] = index
        for item_key, widget in self._widgets.items():
            widget.set_selected(item_key == key)
        self._apply_geometry()

    def _on_widget_changed(self, key: str) -> None:
        widget = self._widgets.get(key)
        if widget is None:
            return
        self._gadgets[key].update(_rect_to_norm(widget.geometry(), self.rect()))


class StageDisplayWindow(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Stage Display"))
        self.resize(980, 600)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet("background:#000000; color:#FFFFFF;")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(6)
        self._canvas = StageDisplayLayoutEditor(self)
        root.addWidget(self._canvas, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self._status_value = QPushButton(tr("Not Playing"), self)
        self._status_value.setEnabled(False)
        self._status_value.setStyleSheet(
            "QPushButton{font-size:12pt; font-weight:bold; color:#F5F5F5; border:1px solid #6A6A6A; border-radius:6px; padding:2px 10px; background:#0E0E0E;}"
            "QPushButton:disabled{color:#F5F5F5;}"
        )
        footer.addWidget(self._status_value)
        root.addLayout(footer)

        for widget in self._canvas._widgets.values():
            widget._draggable = False
            widget._resize_handle.setVisible(False)
            widget.set_selected(False)

        self._status_state = "not_playing"
        self._alert_text = ""
        self._alert_active = False
        self._datetime_timer = QTimer(self)
        self._datetime_timer.timeout.connect(self._update_datetime)
        self._datetime_timer.start(1000)
        self._update_datetime()
        self._install_fullscreen_toggle_filter(self)

    def _install_fullscreen_toggle_filter(self, root: QWidget) -> None:
        root.installEventFilter(self)
        for child in root.findChildren(QWidget):
            child.installEventFilter(self)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonDblClick:
            if getattr(event, "button", lambda: None)() == Qt.LeftButton:
                self._toggle_fullscreen()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._toggle_fullscreen()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            event.accept()
            return
        super().keyPressEvent(event)

    def configure_gadgets(self, gadgets: Dict[str, Dict[str, object]]) -> None:
        self._canvas.set_gadgets(gadgets)
        self._apply_alert_visibility()

    def configure_layout(self, order: List[str], visibility: Dict[str, bool]) -> None:
        self.configure_gadgets(normalize_stage_display_gadgets({}, order, visibility))

    def update_values(
        self,
        total_time: str,
        elapsed: str,
        remaining: str,
        progress_percent: int,
        song_name: str,
        next_song: str,
        progress_text: str = "",
        progress_style: str = "",
    ) -> None:
        values = {
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "alert": self._alert_text,
            "total_time": total_time,
            "elapsed": elapsed,
            "remaining": remaining,
            "progress_bar": progress_text or f"{max(0, min(100, int(progress_percent)))}%",
            "song_name": song_name,
            "next_song": next_song,
        }
        for key, value in values.items():
            widget = self._canvas._widgets.get(key)
            if widget is not None:
                widget.value_label.setText(str(value or "-"))
                if key == "progress_bar" and progress_style:
                    widget.value_label.setStyleSheet(_strip_font_size_style(progress_style) or "color:#FFFFFF;")
                elif key == "alert":
                    widget.value_label.setStyleSheet("color:#FFD23F;")

    def set_playback_status(self, state: str) -> None:
        token = str(state or "").strip().lower()
        self._status_state = token
        if token == "playing":
            self._status_value.setText(f"> {tr('Playing')}")
        elif token == "paused":
            self._status_value.setText(f"|| {tr('Paused')}")
        else:
            self._status_value.setText(f"[] {tr('Not Playing')}")

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("Stage Display"))
        labels = dict(STAGE_DISPLAY_GADGET_SPECS)
        for key, widget in self._canvas._widgets.items():
            if key == "song_name":
                widget.title_label.setText(tr("Now Playing"))
            elif key == "next_song":
                widget.title_label.setText(tr("Next Playing"))
            else:
                widget.title_label.setText(tr(labels.get(key, key)))
        self.set_playback_status(self._status_state)
        self._update_datetime()
        self._apply_alert_visibility()

    def set_alert(self, text: str, active: bool) -> None:
        self._alert_text = str(text or "").strip()
        self._alert_active = bool(active and self._alert_text)
        alert_widget = self._canvas._widgets.get("alert")
        if alert_widget is not None:
            alert_widget.value_label.setText(self._alert_text if self._alert_active else "")
        self._apply_alert_visibility()

    def _update_datetime(self) -> None:
        current_widget = self._canvas._widgets.get("current_time")
        if current_widget is not None:
            current_widget.value_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _apply_alert_visibility(self) -> None:
        alert_widget = self._canvas._widgets.get("alert")
        if alert_widget is None:
            return
        alert_widget.setVisible(bool(self._alert_active))
        if self._alert_active:
            alert_widget.raise_()


def _coerce_int(value: object, fallback: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = int(fallback)
    return max(minimum, min(maximum, parsed))


def _norm_to_rect(spec: Dict[str, object], area: QRect) -> QRect:
    aw = max(1, area.width())
    ah = max(1, area.height())
    x = int((int(spec.get("x", 0)) / 10000.0) * aw)
    y = int((int(spec.get("y", 0)) / 10000.0) * ah)
    w = int((int(spec.get("w", 1000)) / 10000.0) * aw)
    h = int((int(spec.get("h", 1000)) / 10000.0) * ah)
    w = max(80, min(aw, w))
    h = max(60, min(ah, h))
    x = max(0, min(aw - w, x))
    y = max(0, min(ah - h, y))
    return QRect(x, y, w, h)


def _rect_to_norm(rect: QRect, area: QRect) -> Dict[str, int]:
    aw = max(1, area.width())
    ah = max(1, area.height())
    return {
        "x": max(0, min(10000, int((rect.x() / float(aw)) * 10000))),
        "y": max(0, min(10000, int((rect.y() / float(ah)) * 10000))),
        "w": max(100, min(10000, int((rect.width() / float(aw)) * 10000))),
        "h": max(100, min(10000, int((rect.height() / float(ah)) * 10000))),
    }


def _strip_font_size_style(style: str) -> str:
    text = str(style or "")
    if not text:
        return ""
    parts = [chunk.strip() for chunk in text.split(";")]
    filtered = [chunk for chunk in parts if chunk and not chunk.lower().startswith("font-size")]
    return ";".join(filtered)
