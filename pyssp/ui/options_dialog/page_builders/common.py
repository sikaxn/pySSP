from __future__ import annotations

from ..shared import *
from ..widgets import *


class CommonPageBuilderMixin:
    def _add_page(self, title: str, icon, page: QWidget) -> None:
        self.stack.addWidget(page)
        item = QListWidgetItem(icon, title)
        self.page_list.addItem(item)

    def select_page(self, title: Optional[str]) -> bool:
        needle = str(title or "").strip().lower()
        if needle == "display":
            needle = "stage display"
        if needle == "audio device / timecode":
            needle = "audio device & timecode"
        if needle in {"audio preload", "audio format"}:
            needle = "audio loading & format"
        if not needle:
            return False
        for index in range(self.page_list.count()):
            item = self.page_list.item(index)
            if item is None:
                continue
            if item.text().strip().lower() == needle:
                self.page_list.setCurrentRow(index)
                return True
        return False

    def _mono_icon(self, kind: str) -> QIcon:
        size = 22
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor("#000000"))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if kind == "info":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.setBrush(QColor("#000000"))
            p.drawEllipse(QRectF(10, 6, 2, 2))
            p.drawRoundedRect(QRectF(10, 9, 2, 7), 1, 1)
        elif kind == "keyboard":
            p.drawRoundedRect(QRectF(2.5, 5, 17, 12), 2, 2)
            for y in [8, 11, 14]:
                p.drawLine(5, y, 17, y)
            p.drawLine(8, 8, 8, 14)
            p.drawLine(12, 8, 12, 14)
            p.drawLine(16, 8, 16, 14)
        elif kind == "display":
            p.drawRoundedRect(QRectF(3, 3, 16, 12), 1.5, 1.5)
            p.drawLine(8, 18, 14, 18)
            p.drawLine(11, 15, 11, 18)
        elif kind == "projector":
            p.drawRoundedRect(QRectF(3, 5, 16, 10), 2, 2)
            p.drawEllipse(QRectF(6, 8, 3, 3))
            p.drawLine(7, 15, 5, 19)
            p.drawLine(15, 15, 17, 19)
            p.drawLine(9, 19, 13, 19)
        elif kind == "layout":
            p.drawRect(QRectF(3, 3, 16, 16))
            p.drawLine(9, 3, 9, 19)
            p.drawLine(15, 3, 15, 19)
            p.drawLine(3, 9, 19, 9)
            p.drawLine(3, 15, 19, 15)
        elif kind == "clock":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.drawLine(11, 11, 11, 6)
            p.drawLine(11, 11, 15, 13)
        elif kind == "play":
            tri = QPolygonF([QPointF(7, 5), QPointF(17, 11), QPointF(7, 17)])
            p.drawPolygon(tri)
        elif kind == "speaker":
            body = QPolygonF([QPointF(4, 9), QPointF(8, 9), QPointF(12, 6), QPointF(12, 16), QPointF(8, 13), QPointF(4, 13)])
            p.drawPolygon(body)
            p.drawArc(QRectF(12, 7, 5, 8), -40 * 16, 80 * 16)
            p.drawArc(QRectF(12, 5, 8, 12), -40 * 16, 80 * 16)
        elif kind == "gear":
            p.drawEllipse(QRectF(7, 7, 8, 8))
            p.drawLine(11, 3, 11, 6)
            p.drawLine(11, 16, 11, 19)
            p.drawLine(3, 11, 6, 11)
            p.drawLine(16, 11, 19, 11)
            p.drawLine(QPointF(5.2, 5.2), QPointF(7.3, 7.3))
            p.drawLine(QPointF(14.7, 14.7), QPointF(16.8, 16.8))
            p.drawLine(QPointF(5.2, 16.8), QPointF(7.3, 14.7))
            p.drawLine(QPointF(14.7, 7.3), QPointF(16.8, 5.2))
        elif kind == "mic":
            p.drawRoundedRect(QRectF(8, 4, 6, 10), 3, 3)
            p.drawLine(11, 14, 11, 18)
            p.drawLine(8, 18, 14, 18)
            p.drawArc(QRectF(6, 10, 10, 8), 200 * 16, 140 * 16)
        elif kind == "wireless":
            p.drawEllipse(QRectF(10, 14, 2, 2))
            p.drawArc(QRectF(7, 11, 8, 8), 35 * 16, 110 * 16)
            p.drawArc(QRectF(5, 9, 12, 12), 35 * 16, 110 * 16)
            p.drawArc(QRectF(3, 7, 16, 16), 35 * 16, 110 * 16)
        elif kind == "lyric":
            p.drawRoundedRect(QRectF(4, 3, 14, 16), 1.5, 1.5)
            p.drawLine(7, 8, 15, 8)
            p.drawLine(7, 11, 15, 11)
            p.drawLine(7, 14, 12, 14)
            p.drawEllipse(QRectF(13, 14, 3, 3))
        elif kind == "ram":
            p.drawRoundedRect(QRectF(4, 6, 14, 10), 1.5, 1.5)
            p.drawLine(6, 9, 16, 9)
            p.drawLine(6, 12, 16, 12)
            for x in [5, 8, 11, 14, 17]:
                p.drawLine(x, 4, x, 6)
                p.drawLine(x, 16, x, 18)
        elif kind == "earth":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.drawArc(QRectF(5, 3, 12, 16), 90 * 16, 180 * 16)
            p.drawArc(QRectF(5, 3, 12, 16), 270 * 16, 180 * 16)
            p.drawLine(3, 11, 19, 11)
            p.drawArc(QRectF(3, 6, 16, 10), 0, 180 * 16)
            p.drawArc(QRectF(3, 6, 16, 10), 180 * 16, 180 * 16)
        elif kind == "piano":
            p.drawRoundedRect(QRectF(3, 4, 16, 14), 1.5, 1.5)
            p.drawLine(6, 4, 6, 18)
            p.drawLine(10, 4, 10, 18)
            p.drawLine(14, 4, 14, 18)
            p.setBrush(QColor("#000000"))
            p.drawRect(QRectF(5, 4, 2, 7))
            p.drawRect(QRectF(9, 4, 2, 7))
            p.drawRect(QRectF(13, 4, 2, 7))
        elif kind == "lock":
            p.drawRoundedRect(QRectF(6, 10, 10, 8), 1.5, 1.5)
            p.drawArc(QRectF(7, 4, 8, 9), 0, 180 * 16)

        p.end()
        return QIcon(pix)

