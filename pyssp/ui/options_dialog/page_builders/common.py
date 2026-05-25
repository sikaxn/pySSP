from __future__ import annotations

from ..shared import *
from ..widgets import *


_DISPLAY_OPTIONS_PAGE_TITLE = "Display"
_DISPLAY_OPTIONS_TAB_LABELS = {
    "video": "Video Display",
    "stage": "Stage Display",
    "lyric": "Lyric Display",
}


class CommonPageBuilderMixin:
    def _add_page(self, title: str, icon, page: QWidget) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(page)
        self.stack.addWidget(scroll)
        item = QListWidgetItem(icon, title)
        item.setData(SOURCE_TEXT_ROLE, title)
        self.page_list.addItem(item)

    def _build_display_options_page(self, *, video_page: QWidget, stage_page: QWidget, lyric_page: QWidget) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.display_options_tabs = QTabWidget()
        self._display_options_tab_keys = []
        for key, tab_page in [
            ("video", video_page),
            ("stage", stage_page),
            ("lyric", lyric_page),
        ]:
            label = _DISPLAY_OPTIONS_TAB_LABELS[key]
            self.display_options_tabs.addTab(tab_page, label)
            tab_index = self.display_options_tabs.count() - 1
            self.display_options_tabs.tabBar().setTabData(tab_index, label)
            self._display_options_tab_keys.append(key)
        layout.addWidget(self.display_options_tabs)
        return page

    def _select_display_options_tab(self, key: str) -> None:
        tabs = getattr(self, "display_options_tabs", None)
        tab_keys = list(getattr(self, "_display_options_tab_keys", []))
        if not isinstance(tabs, QTabWidget) or not tab_keys:
            return
        token = str(key or "").strip().lower()
        tab_key = "video"
        if token in {"stage", "stage display", "stage and lyric display", "stage and lyric display setting"}:
            tab_key = "stage"
        elif token in {"lyric", "lyric display", "lyric display setting"}:
            tab_key = "lyric"
        elif token in {"video", "video display", "video display setting"}:
            tab_key = "video"
        if tab_key not in tab_keys:
            return
        tabs.setCurrentIndex(tab_keys.index(tab_key))

    def _current_display_options_tab_key(self) -> str:
        tabs = getattr(self, "display_options_tabs", None)
        tab_keys = list(getattr(self, "_display_options_tab_keys", []))
        if not isinstance(tabs, QTabWidget) or not tab_keys:
            return "video"
        index = max(0, min(tabs.currentIndex(), len(tab_keys) - 1))
        return str(tab_keys[index])

    def select_page(self, title: Optional[str]) -> bool:
        needle = str(title or "").strip().lower()
        display_tab_key = ""
        if needle == "display":
            needle = _DISPLAY_OPTIONS_PAGE_TITLE.lower()
            display_tab_key = "video"
        elif needle in {"stage", "stage display", "stage and lyric display", "stage and lyric display setting"}:
            needle = _DISPLAY_OPTIONS_PAGE_TITLE.lower()
            display_tab_key = "stage"
        elif needle in {"lyric", "lyric display", "lyric display setting"}:
            needle = _DISPLAY_OPTIONS_PAGE_TITLE.lower()
            display_tab_key = "lyric"
        elif needle in {"video", "video display", "video display setting"}:
            needle = _DISPLAY_OPTIONS_PAGE_TITLE.lower()
            display_tab_key = "video"
        if needle in {"companion satellite", "automation setup"}:
            needle = "automation"
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
            source_text = str(item.data(SOURCE_TEXT_ROLE) or item.text() or "").strip().lower()
            if source_text == needle:
                self.page_list.setCurrentRow(index)
                if display_tab_key:
                    self._select_display_options_tab(display_tab_key)
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
        elif kind == "robot":
            p.drawRoundedRect(QRectF(5, 6, 12, 10), 2, 2)
            p.drawLine(11, 3, 11, 6)
            p.drawEllipse(QRectF(10, 2, 2, 2))
            p.drawEllipse(QRectF(8, 9, 2, 2))
            p.drawEllipse(QRectF(12, 9, 2, 2))
            p.drawLine(9, 13, 13, 13)
            p.drawLine(5, 10, 3, 10)
            p.drawLine(17, 10, 19, 10)
            p.drawLine(8, 16, 7, 19)
            p.drawLine(14, 16, 15, 19)
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
