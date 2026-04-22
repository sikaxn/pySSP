from __future__ import annotations

from .shared import *

__all__ = [
    "WINDOW_LAYOUT_DRAG_MIME",
    "_GridLayoutButton",
    "_AvailableButtonsList",
    "_GridLayoutCanvas",
    "HotkeyCaptureEdit",
    "MidiCaptureEdit",
]

class _GridLayoutButton(QFrame):
    delete_requested = pyqtSignal(str)

    def __init__(self, uid: str, key: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.uid = uid
        self.key = key
        self._label = QLabel(key, self)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setStyleSheet("color:#FFFFFF;")
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._drag_mode = ""
        self._drag_start_local = QPoint()
        self._start_pos = QPoint()
        self._start_rect = QRect()
        self.setCursor(Qt.OpenHandCursor)
        self.setStyleSheet(
            "QFrame{background:#2E415A;border:1px solid #7CA2D1;border-radius:4px;}"
            "QLabel{font-weight:bold;}"
        )
        self._resize_handle = QFrame(self)
        self._resize_handle.setFixedSize(10, 10)
        self._resize_handle.setStyleSheet("QFrame{background:#A8C4E8;border:1px solid #D6E4F8;border-radius:2px;}")
        self._resize_handle.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._delete_btn = QPushButton("x", self)
        self._delete_btn.setFixedSize(16, 16)
        self._delete_btn.setStyleSheet(
            "QPushButton{background:#A33A3A;color:#FFFFFF;border:1px solid #C66A6A;border-radius:8px;font-weight:bold;padding:0px;}"
            "QPushButton:hover{background:#B74747;}"
        )
        self._delete_btn.clicked.connect(lambda _=False: self.delete_requested.emit(self.uid))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._label.setGeometry(self.rect().adjusted(6, 4, -6, -4))
        self._resize_handle.move(max(0, self.width() - 12), max(0, self.height() - 12))
        self._delete_btn.move(max(0, self.width() - 18), 2)
        font = QFont(self._label.font())
        font.setPointSize(max(8, min(11, int(min(self.width(), self.height()) / 14))))
        self._label.setFont(font)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self.raise_()
        self._drag_start_local = event.pos()
        self._start_pos = event.globalPos()
        self._start_rect = self.geometry()
        edge = 14
        if event.pos().x() >= self.width() - edge and event.pos().y() >= self.height() - edge:
            self._drag_mode = "resize"
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self._drag_mode = "move"
            self.setCursor(Qt.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.LeftButton) or not self._drag_mode:
            super().mouseMoveEvent(event)
            return
        parent = self.parentWidget()
        if not isinstance(parent, _GridLayoutCanvas):
            return
        if self._drag_mode == "resize":
            delta = event.globalPos() - self._start_pos
            parent.update_item_from_pixel_rect(
                self.uid,
                QRect(
                    self._start_rect.x(),
                    self._start_rect.y(),
                    max(36, self._start_rect.width() + delta.x()),
                    max(26, self._start_rect.height() + delta.y()),
                ),
            )
            event.accept()
            return
        if (event.globalPos() - self._start_pos).manhattanLength() < 6:
            return
        payload = parent.payload_for_uid(self.uid)
        if payload is None:
            return
        mime = QMimeData()
        mime.setData(WINDOW_LAYOUT_DRAG_MIME, json.dumps(payload).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(self.rect().center())
        # The source widget may be deleted during drop handling; do not touch `self` after exec_.
        self._drag_mode = ""
        self.setCursor(Qt.OpenHandCursor)
        drag.exec_(Qt.MoveAction | Qt.CopyAction, Qt.MoveAction)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_mode = ""
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)


class _AvailableButtonsList(QListWidget):
    dropped = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setViewMode(QListWidget.IconMode)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListWidget.Adjust)
        self.setGridSize(QSize(110, 44))
        self.setIconSize(QSize(1, 1))
        self.setSpacing(6)
        self.setStyleSheet(
            "QListWidget{background:#15191E;border:1px solid #303A45;padding:6px;}"
            "QListWidget::item{border:none;background:transparent;}"
            "QListWidget::item:selected{background:transparent;}"
        )

    class _Tile(QFrame):
        def __init__(self, label: str, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)
            self.setStyleSheet(
                "QFrame{background:#2E415A;border:1px solid #7CA2D1;border-radius:4px;}"
                "QLabel{color:#FFFFFF;font-weight:bold;}"
            )
            text = QLabel(str(label), self)
            text.setAlignment(Qt.AlignCenter)
            text.setWordWrap(True)
            root = QVBoxLayout(self)
            root.setContentsMargins(6, 4, 6, 4)
            root.addWidget(text, 1)

    def set_buttons(self, buttons: List[str]) -> None:
        self.clear()
        for token in buttons:
            item = QListWidgetItem(str(token))
            item.setSizeHint(QSize(104, 36))
            self.addItem(item)
            self.setItemWidget(item, self._Tile(str(token), self))

    def buttons(self) -> List[str]:
        return [self.item(i).text() for i in range(self.count()) if self.item(i) is not None]

    def startDrag(self, supportedActions) -> None:
        item = self.currentItem()
        if item is None:
            return
        payload = {"source": "available", "source_zone": "available", "uid": "", "button": item.text(), "w": 1, "h": 1}
        mime = QMimeData()
        mime.setData(WINDOW_LAYOUT_DRAG_MIME, json.dumps(payload).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction, Qt.CopyAction)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(WINDOW_LAYOUT_DRAG_MIME):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(WINDOW_LAYOUT_DRAG_MIME):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        raw = bytes(event.mimeData().data(WINDOW_LAYOUT_DRAG_MIME)).decode("utf-8", errors="ignore")
        if raw:
            self.dropped.emit(raw)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class _GridLayoutCanvas(QWidget):
    changed = pyqtSignal()
    dropped = pyqtSignal(str, int, int)

    def __init__(self, zone_name: str, columns: int, rows: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.zone_name = str(zone_name)
        self._columns = max(1, int(columns))
        self._rows = max(1, int(rows))
        self._items: List[Dict[str, object]] = []
        self._blocks: Dict[str, _GridLayoutButton] = {}
        self._uid_counter = 0
        self._drag_hover_cell: Optional[tuple[int, int]] = None
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        self.setStyleSheet("background:#15191E;")

    def set_items(self, values: List[Dict[str, object]]) -> None:
        self._items = []
        for raw in list(values or []):
            if not isinstance(raw, dict):
                continue
            button = str(raw.get("button", "")).strip()
            if not button:
                continue
            self._uid_counter += 1
            self._items.append(
                {
                    "uid": str(raw.get("uid", f"{self.zone_name}_{self._uid_counter}")),
                    "button": button,
                    "x": int(raw.get("x", 0)),
                    "y": int(raw.get("y", 0)),
                    "w": max(1, int(raw.get("w", 1))),
                    "h": max(1, int(raw.get("h", 1))),
                }
            )
        self._normalize_items()
        self._apply_geometry()

    def export_items(self) -> List[Dict[str, int | str]]:
        out: List[Dict[str, int | str]] = []
        for item in self._items:
            out.append(
                {
                    "button": str(item["button"]),
                    "x": int(item["x"]),
                    "y": int(item["y"]),
                    "w": int(item["w"]),
                    "h": int(item["h"]),
                }
            )
        return out

    def payload_for_uid(self, uid: str) -> Optional[Dict[str, object]]:
        for item in self._items:
            if str(item.get("uid", "")) == str(uid):
                return {
                    "source": "canvas",
                    "source_zone": self.zone_name,
                    "uid": str(item["uid"]),
                    "button": str(item["button"]),
                    "w": int(item["w"]),
                    "h": int(item["h"]),
                }
        return None

    def get_item(self, uid: str) -> Optional[Dict[str, object]]:
        for item in self._items:
            if str(item.get("uid", "")) == str(uid):
                return dict(item)
        return None

    def occupied_item_at(self, x: int, y: int, exclude_uid: str = "") -> Optional[Dict[str, object]]:
        gx = int(x)
        gy = int(y)
        for item in self._items:
            if exclude_uid and str(item.get("uid", "")) == str(exclude_uid):
                continue
            ix = int(item.get("x", 0))
            iy = int(item.get("y", 0))
            iw = int(item.get("w", 1))
            ih = int(item.get("h", 1))
            if gx >= ix and gx < (ix + iw) and gy >= iy and gy < (iy + ih):
                return dict(item)
        return None

    def remove_uid(self, uid: str) -> Optional[Dict[str, object]]:
        for idx, item in enumerate(self._items):
            if str(item.get("uid", "")) == str(uid):
                removed = self._items.pop(idx)
                self._apply_geometry()
                self.changed.emit()
                return removed
        return None

    def upsert_item(
        self,
        uid: str,
        button: str,
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> None:
        clamped_x = max(0, min(self._columns - 1, int(x)))
        clamped_y = max(0, min(self._rows - 1, int(y)))
        clamped_w = max(1, min(self._columns - clamped_x, int(w)))
        clamped_h = max(1, min(self._rows - clamped_y, int(h)))
        for item in self._items:
            if str(item.get("uid", "")) == str(uid):
                item["button"] = str(button)
                item["x"] = clamped_x
                item["y"] = clamped_y
                item["w"] = clamped_w
                item["h"] = clamped_h
                self._apply_geometry()
                self.changed.emit()
                return
        self._items.append(
            {
                "uid": str(uid),
                "button": str(button),
                "x": clamped_x,
                "y": clamped_y,
                "w": clamped_w,
                "h": clamped_h,
            }
        )
        self._apply_geometry()
        self.changed.emit()

    def add_item(
        self,
        button: str,
        x: int,
        y: int,
        w: int,
        h: int,
        uid: Optional[str] = None,
    ) -> str:
        self._uid_counter += 1
        token = str(uid or f"{self.zone_name}_{self._uid_counter}")
        self._items.append({"uid": token, "button": str(button), "x": int(x), "y": int(y), "w": max(1, int(w)), "h": max(1, int(h))})
        self._normalize_items()
        self._apply_geometry()
        self.changed.emit()
        return token

    def remove_all_by_button(self, button: str, exclude_uid: str = "") -> List[Dict[str, object]]:
        removed: List[Dict[str, object]] = []
        keep: List[Dict[str, object]] = []
        for item in self._items:
            if str(item.get("button", "")) == str(button) and (
                not exclude_uid or str(item.get("uid", "")) != str(exclude_uid)
            ):
                removed.append(item)
            else:
                keep.append(item)
        if removed:
            self._items = keep
            self._apply_geometry()
            self.changed.emit()
        return removed

    def has_button(self, button: str) -> bool:
        return any(str(item.get("button", "")) == str(button) for item in self._items)

    def update_item_from_pixel_rect(self, uid: str, rect: QRect) -> None:
        area = self._content_rect()
        if area.width() <= 0 or area.height() <= 0:
            return
        cell_w = area.width() / float(self._columns)
        cell_h = area.height() / float(self._rows)
        for item in self._items:
            if str(item.get("uid", "")) != str(uid):
                continue
            item["x"] = int(round((rect.x() - area.x()) / cell_w))
            item["y"] = int(round((rect.y() - area.y()) / cell_h))
            item["w"] = max(1, int(round(rect.width() / cell_w)))
            item["h"] = max(1, int(round(rect.height() / cell_h)))
            break
        self._normalize_items()
        self._apply_geometry()
        self.changed.emit()

    def snap_to_grid(self, pos: QPoint) -> tuple[int, int]:
        area = self._content_rect()
        if area.width() <= 0 or area.height() <= 0:
            return 0, 0
        cell_w = area.width() / float(self._columns)
        cell_h = area.height() / float(self._rows)
        x = int(round((pos.x() - area.x()) / cell_w))
        y = int(round((pos.y() - area.y()) / cell_h))
        return x, y

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_geometry()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        area = self._content_rect()
        if area.width() <= 0 or area.height() <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        pen = QPen(QColor("#303A45"))
        pen.setWidth(1)
        painter.setPen(pen)
        cell_w = area.width() / float(self._columns)
        cell_h = area.height() / float(self._rows)
        for col in range(self._columns + 1):
            x = int(area.x() + round(col * cell_w))
            painter.drawLine(x, area.y(), x, area.bottom())
        for row in range(self._rows + 1):
            y = int(area.y() + round(row * cell_h))
            painter.drawLine(area.x(), y, area.right(), y)
        if self._drag_hover_cell is not None:
            hx = int(max(0, min(self._columns - 1, self._drag_hover_cell[0])))
            hy = int(max(0, min(self._rows - 1, self._drag_hover_cell[1])))
            x = int(area.x() + round(hx * cell_w))
            y = int(area.y() + round(hy * cell_h))
            w = int(round(cell_w))
            h = int(round(cell_h))
            painter.fillRect(QRect(x + 1, y + 1, max(2, w - 2), max(2, h - 2)), QColor(102, 163, 255, 70))
            hi_pen = QPen(QColor("#66A3FF"))
            hi_pen.setWidth(2)
            painter.setPen(hi_pen)
            painter.drawRect(QRect(x + 1, y + 1, max(2, w - 2), max(2, h - 2)))

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(WINDOW_LAYOUT_DRAG_MIME):
            self._drag_hover_cell = self.snap_to_grid(event.pos())
            self.update()
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(WINDOW_LAYOUT_DRAG_MIME):
            self._drag_hover_cell = self.snap_to_grid(event.pos())
            self.update()
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dragLeaveEvent(self, event) -> None:
        self._drag_hover_cell = None
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        self._drag_hover_cell = None
        self.update()
        raw = bytes(event.mimeData().data(WINDOW_LAYOUT_DRAG_MIME)).decode("utf-8", errors="ignore")
        if raw:
            self.dropped.emit(raw, event.pos().x(), event.pos().y())
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _content_rect(self) -> QRect:
        return self.rect().adjusted(8, 8, -8, -8)

    def _normalize_items(self) -> None:
        used = [[False for _ in range(self._columns)] for _ in range(self._rows)]
        out: List[Dict[str, object]] = []

        def can_place(px: int, py: int, pw: int, ph: int) -> bool:
            if px < 0 or py < 0 or pw < 1 or ph < 1:
                return False
            if (px + pw) > self._columns or (py + ph) > self._rows:
                return False
            for yy in range(py, py + ph):
                for xx in range(px, px + pw):
                    if used[yy][xx]:
                        return False
            return True

        def occupy(px: int, py: int, pw: int, ph: int) -> None:
            for yy in range(py, py + ph):
                for xx in range(px, px + pw):
                    used[yy][xx] = True

        def first_fit(pw: int, ph: int) -> Optional[tuple[int, int]]:
            for yy in range(self._rows):
                for xx in range(self._columns):
                    if can_place(xx, yy, pw, ph):
                        return xx, yy
            return None

        for item in list(self._items):
            x = max(0, min(self._columns - 1, int(item.get("x", 0))))
            y = max(0, min(self._rows - 1, int(item.get("y", 0))))
            w = max(1, min(self._columns, int(item.get("w", 1))))
            h = max(1, min(self._rows, int(item.get("h", 1))))
            w = min(w, self._columns - x)
            h = min(h, self._rows - y)
            if not can_place(x, y, w, h):
                target = first_fit(w, h)
                if target is None:
                    fallback = first_fit(1, 1)
                    if fallback is None:
                        continue
                    x, y = fallback
                    w, h = 1, 1
                else:
                    x, y = target
            occupy(x, y, w, h)
            out.append(
                {
                    "uid": str(item.get("uid", "")),
                    "button": str(item.get("button", "")),
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                }
            )
        self._items = out

    def _apply_geometry(self) -> None:
        area = self._content_rect()
        if area.width() <= 0 or area.height() <= 0:
            return
        cell_w = area.width() / float(self._columns)
        cell_h = area.height() / float(self._rows)
        live_uids = set()
        for item in self._items:
            uid = str(item["uid"])
            live_uids.add(uid)
            block = self._blocks.get(uid)
            if block is None:
                block = _GridLayoutButton(uid, str(item["button"]), self)
                block.delete_requested.connect(self.remove_uid)
                self._blocks[uid] = block
            x = int(area.x() + round(int(item["x"]) * cell_w))
            y = int(area.y() + round(int(item["y"]) * cell_h))
            w = int(round(int(item["w"]) * cell_w))
            h = int(round(int(item["h"]) * cell_h))
            block.key = str(item["button"])
            block._label.setText(str(item["button"]))
            block.setGeometry(QRect(x + 2, y + 2, max(36, w - 4), max(26, h - 4)))
            block.show()
        stale = [uid for uid in self._blocks.keys() if uid not in live_uids]
        for uid in stale:
            widget = self._blocks.pop(uid)
            widget.setParent(None)
            widget.deleteLater()


class HotkeyCaptureEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Press key")
        self.setReadOnly(True)

    def hotkey(self) -> str:
        return self.text().strip()

    def setHotkey(self, value: str) -> None:
        text = str(value or "").strip()
        self.setText(self._normalize_text(text))

    def keyPressEvent(self, event) -> None:
        key = int(event.key())
        if key in {Qt.Key_Tab, Qt.Key_Backtab}:
            super().keyPressEvent(event)
            return
        if key in {Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Escape}:
            self.clear()
            return

        modifiers = event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier)
        text = self._build_hotkey_text(key, modifiers)
        if text:
            self.setText(text)

    def _build_hotkey_text(self, key: int, modifiers: Qt.KeyboardModifiers) -> str:
        if key == Qt.Key_Shift and modifiers == Qt.ShiftModifier:
            return "Shift"
        if key == Qt.Key_Control and modifiers == Qt.ControlModifier:
            return "Ctrl"
        if key == Qt.Key_Alt and modifiers == Qt.AltModifier:
            return "Alt"
        if key == Qt.Key_Meta and modifiers == Qt.MetaModifier:
            return "Meta"
        seq = QKeySequence(int(key) | int(modifiers)).toString().strip()
        return self._normalize_text(seq)

    def _normalize_text(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        aliases = {
            "control": "Ctrl",
            "ctrl": "Ctrl",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Meta",
            "win": "Meta",
            "super": "Meta",
        }
        lower = raw.lower()
        if lower in aliases:
            return aliases[lower]
        normalized = QKeySequence(raw).toString().strip()
        return normalized or raw


class MidiCaptureEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Unassigned")
        self.setReadOnly(True)
        self._binding = ""

    def binding(self) -> str:
        return self._binding

    def setBinding(self, value: str) -> None:
        token = normalize_midi_binding(value)
        self._binding = token
        self.setText(midi_binding_to_display(token) if token else "")

