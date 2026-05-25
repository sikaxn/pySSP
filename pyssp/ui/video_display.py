from __future__ import annotations

import time
from typing import Optional

from PyQt5.QtCore import QEvent, QRect, QRectF, QSize, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap, QTextDocument
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from pyssp.i18n import tr


def _normalized_rect(spec: dict[str, int], bounds: QRect) -> QRect:
    width = max(1, bounds.width())
    height = max(1, bounds.height())
    x = max(0, min(width - 1, int((int(spec.get("x", 0)) / 10000.0) * width)))
    y = max(0, min(height - 1, int((int(spec.get("y", 0)) / 10000.0) * height)))
    w = max(40, min(width, int((int(spec.get("w", 10000)) / 10000.0) * width)))
    h = max(40, min(height, int((int(spec.get("h", 10000)) / 10000.0) * height)))
    if x + w > width:
        x = max(0, width - w)
    if y + h > height:
        y = max(0, height - h)
    return QRect(x, y, w, h)


class VideoDisplayWidget(QWidget):
    surfaceChanged = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None, *, allow_fullscreen_toggle: bool = False) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self._allow_fullscreen_toggle = bool(allow_fullscreen_toggle)
        self._mode = "blank"
        self._video_pixmap = QPixmap()
        self._content_pixmap = QPixmap()
        self._backdrop_pixmap = QPixmap()
        self._lyric_html = ""
        self._overlay_rect = {"x": 800, "y": 6800, "w": 8400, "h": 2400}
        self._show_lyric_overlay = False
        self._show_stage_alert = False
        self._alert_text = ""
        self._show_backdrop_message = False
        self._backdrop_message_text = ""
        self._transition_duration_sec = 0.0
        self._transition_prev_frame = QImage()
        self._transition_prev_frame_size = QSize()
        self._transition_started_at = 0.0
        self._transition_progress = 1.0
        self._transition_timer = QTimer(self)
        self._transition_timer.setInterval(16)
        self._transition_timer.setTimerType(Qt.PreciseTimer)
        self._transition_timer.timeout.connect(self._tick_transition)
        self._lyric_doc = QTextDocument(self)
        self._lyric_doc.setDocumentMargin(0.0)
        self._install_fullscreen_filter(self)

    def _install_fullscreen_filter(self, root: QWidget) -> None:
        root.installEventFilter(self)
        for child in root.findChildren(QWidget):
            child.installEventFilter(self)

    def eventFilter(self, watched, event):
        if self._allow_fullscreen_toggle and event.type() == QEvent.MouseButtonDblClick:
            if getattr(event, "button", lambda: None)() == Qt.LeftButton:
                self._toggle_fullscreen()
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._allow_fullscreen_toggle and event.button() == Qt.LeftButton:
            self._toggle_fullscreen()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if self._allow_fullscreen_toggle and event.key() == Qt.Key_Escape and self.window().isFullScreen():
            self.window().showNormal()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.surfaceChanged.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.surfaceChanged.emit()

    def _toggle_fullscreen(self) -> None:
        target = self.window()
        if target.isFullScreen():
            target.showNormal()
        else:
            target.showFullScreen()

    def configure_overlay(
        self,
        *,
        overlay_rect: Optional[dict[str, int]] = None,
        show_lyric_overlay: bool = False,
        show_stage_alert: bool = False,
    ) -> None:
        if overlay_rect is not None:
            self._overlay_rect = dict(overlay_rect)
        self._show_lyric_overlay = bool(show_lyric_overlay)
        self._show_stage_alert = bool(show_stage_alert)
        self.update()

    def set_transition_duration_seconds(self, seconds: float) -> None:
        self._transition_duration_sec = max(0.0, float(seconds or 0.0))
        if self._transition_duration_sec <= 0.0:
            self._finish_transition()

    def is_transition_active(self) -> bool:
        return self._update_transition_progress()

    def apply_surface_state(
        self,
        *,
        mode: str,
        video_pixmap: Optional[QPixmap] = None,
        content_pixmap: Optional[QPixmap] = None,
        backdrop_pixmap: Optional[QPixmap] = None,
        lyric_html: str = "",
        overlay_rect: Optional[dict[str, int]] = None,
        show_lyric_overlay: bool = False,
        show_stage_alert: bool = False,
        alert_text: str = "",
        show_backdrop_message: bool = False,
        backdrop_message_text: str = "",
    ) -> None:
        token = str(mode or "blank").strip().lower()
        if token != self._mode:
            self._begin_mode_transition()
        self._mode = token
        self._video_pixmap = QPixmap() if video_pixmap is None else QPixmap(video_pixmap)
        self._content_pixmap = QPixmap() if content_pixmap is None else QPixmap(content_pixmap)
        self._backdrop_pixmap = QPixmap() if backdrop_pixmap is None else QPixmap(backdrop_pixmap)
        self._lyric_html = str(lyric_html or "")
        if overlay_rect is not None:
            self._overlay_rect = dict(overlay_rect)
        self._show_lyric_overlay = bool(show_lyric_overlay)
        self._show_stage_alert = bool(show_stage_alert)
        self._alert_text = str(alert_text or "").strip()
        self._show_backdrop_message = bool(show_backdrop_message)
        self._backdrop_message_text = str(backdrop_message_text or "").strip()
        self._lyric_doc.setHtml(self._lyric_html)
        self.update()

    def set_mode(self, mode: str) -> None:
        token = str(mode or "blank").strip().lower()
        if token == self._mode:
            return
        self._begin_mode_transition()
        self._mode = token
        self.update()

    def set_video_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self._video_pixmap = QPixmap() if pixmap is None else QPixmap(pixmap)
        self.update()

    def set_content_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self._content_pixmap = QPixmap() if pixmap is None else QPixmap(pixmap)
        self.update()

    def set_backdrop_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self._backdrop_pixmap = QPixmap() if pixmap is None else QPixmap(pixmap)
        self.update()

    def set_lyric_html(self, html: str) -> None:
        self._lyric_html = str(html or "")
        self._lyric_doc.setHtml(self._lyric_html)
        self.update()

    def set_alert_text(self, text: str) -> None:
        self._alert_text = str(text or "").strip()
        self.update()

    def configure_backdrop(self, *, show_message: bool = False, message_text: str = "") -> None:
        self._show_backdrop_message = bool(show_message)
        self._backdrop_message_text = str(message_text or "").strip()
        self.update()

    def _capture_current_frame(self) -> QImage:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return QImage()
        image = QImage(size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.black)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        self._paint_surface(painter, QRect(0, 0, size.width(), size.height()))
        painter.end()
        return image

    def _begin_mode_transition(self) -> None:
        if self._transition_duration_sec <= 0.0:
            self._finish_transition()
            return
        frame = self._capture_current_frame()
        if frame.isNull():
            self._finish_transition()
            return
        self._transition_prev_frame = frame
        self._transition_prev_frame_size = frame.size()
        self._transition_started_at = time.monotonic()
        self._transition_progress = 0.0
        if not self._transition_timer.isActive():
            self._transition_timer.start()

    def _update_transition_progress(self) -> bool:
        if self._transition_prev_frame.isNull():
            self._transition_progress = 1.0
            return False
        duration = max(0.0, float(self._transition_duration_sec))
        if duration <= 0.0:
            self._finish_transition()
            return False
        elapsed = max(0.0, time.monotonic() - float(self._transition_started_at))
        self._transition_progress = max(0.0, min(1.0, elapsed / duration))
        if self._transition_progress >= 1.0:
            self._finish_transition()
            return False
        return True

    def _tick_transition(self) -> None:
        self._update_transition_progress()
        self.update()

    def _finish_transition(self) -> None:
        if self._transition_timer.isActive():
            self._transition_timer.stop()
        self._transition_prev_frame = QImage()
        self._transition_prev_frame_size = QSize()
        self._transition_started_at = 0.0
        self._transition_progress = 1.0

    def _draw_colour_bars(self, painter: QPainter, rect: QRect) -> None:
        colors = ["#BEBEBE", "#BEBE00", "#00BEBE", "#00BE00", "#BE00BE", "#BE0000", "#0000BE"]
        bar_width = max(1, int(rect.width() / max(1, len(colors))))
        for idx, color_hex in enumerate(colors):
            left = rect.x() + (idx * bar_width)
            width = bar_width if idx < len(colors) - 1 else rect.right() - left + 1
            painter.fillRect(QRect(left, rect.y(), width, rect.height()), QColor(color_hex))

    @staticmethod
    def _scaled_target_rect(rect: QRect, source_width: int, source_height: int, *, keep_aspect: bool) -> QRect:
        if not keep_aspect:
            return QRect(rect)
        source_width = max(1, int(source_width))
        source_height = max(1, int(source_height))
        scale = min(rect.width() / float(source_width), rect.height() / float(source_height))
        width = max(1, int(round(source_width * scale)))
        height = max(1, int(round(source_height * scale)))
        return QRect(
            rect.x() + max(0, (rect.width() - width) // 2),
            rect.y() + max(0, (rect.height() - height) // 2),
            width,
            height,
        )

    def _draw_scaled_pixmap(self, painter: QPainter, rect: QRect, pixmap: QPixmap, *, keep_aspect: bool) -> None:
        if pixmap.isNull():
            return
        target = self._scaled_target_rect(rect, pixmap.width(), pixmap.height(), keep_aspect=keep_aspect)
        if target.size() == pixmap.size():
            painter.drawPixmap(target.topLeft(), pixmap)
            return
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(target, pixmap, pixmap.rect())

    def _draw_scaled_image(self, painter: QPainter, rect: QRect, image: QImage, *, keep_aspect: bool) -> None:
        if image.isNull():
            return
        target = self._scaled_target_rect(rect, image.width(), image.height(), keep_aspect=keep_aspect)
        if target.size() == image.size():
            painter.drawImage(target.topLeft(), image)
            return
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawImage(target, image)

    def _paint_surface(self, painter: QPainter, bounds: QRect) -> None:
        mode = self._mode
        if mode == "white_screen":
            painter.fillRect(bounds, QColor("#FFFFFF"))
        else:
            painter.fillRect(bounds, QColor("#000000"))
        if mode == "colour_bars":
            self._draw_colour_bars(painter, bounds)
        elif mode == "video":
            self._draw_scaled_pixmap(painter, bounds, self._video_pixmap, keep_aspect=True)
        elif mode == "image":
            self._draw_scaled_pixmap(painter, bounds, self._content_pixmap, keep_aspect=True)
        elif mode == "backdrop":
            self._draw_scaled_pixmap(painter, bounds, self._backdrop_pixmap, keep_aspect=False)
        elif mode in {"stage_display", "lyric_display", "metronome_display"}:
            self._draw_scaled_pixmap(painter, bounds, self._content_pixmap, keep_aspect=False)
        if mode == "video" and self._show_lyric_overlay and self._lyric_html.strip():
            overlay = _normalized_rect(self._overlay_rect, bounds)
            painter.fillRect(overlay, QColor(0, 0, 0, 70))
            self._lyric_doc.setTextWidth(float(overlay.width()))
            painter.save()
            painter.translate(overlay.topLeft())
            clip = QRect(0, 0, overlay.width(), overlay.height())
            painter.setClipRect(clip)
            self._lyric_doc.drawContents(painter, QRectF(clip))
            painter.restore()
        if mode == "video" and self._show_stage_alert and self._alert_text:
            banner = QRect(bounds.x() + 20, bounds.y() + 20, max(120, bounds.width() - 40), min(100, bounds.height() // 5))
            painter.fillRect(banner, QColor(28, 28, 28, 220))
            painter.setPen(QColor("#FFD23F"))
            painter.drawRect(banner)
            text_rect = banner.adjusted(14, 10, -14, -10)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, self._alert_text)
        if mode == "backdrop" and self._show_backdrop_message and self._backdrop_message_text:
            banner = QRect(
                bounds.x() + 40,
                bounds.bottom() - min(140, max(80, bounds.height() // 6)),
                max(180, bounds.width() - 80),
                90,
            )
            painter.fillRect(banner, QColor(0, 0, 0, 170))
            painter.setPen(QPen(QColor("#FFFFFF")))
            font = QFont(self.font())
            font.setBold(True)
            font.setPointSize(max(14, min(28, bounds.height() // 18)))
            painter.setFont(font)
            painter.drawText(
                banner.adjusted(16, 12, -16, -12),
                Qt.AlignCenter | Qt.TextWordWrap,
                self._backdrop_message_text,
            )

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        bounds = self.rect()
        self._paint_surface(painter, bounds)
        if self._update_transition_progress():
            painter.save()
            painter.setOpacity(max(0.0, min(1.0, 1.0 - float(self._transition_progress))))
            self._draw_scaled_image(
                painter,
                bounds,
                self._transition_prev_frame,
                keep_aspect=self._transition_prev_frame_size.isValid()
                and self._transition_prev_frame_size != bounds.size(),
            )
            painter.restore()


class VideoDisplayWindow(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Video Display"))
        self.resize(980, 600)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet("background:#000000;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.display_widget = VideoDisplayWidget(self, allow_fullscreen_toggle=True)
        root.addWidget(self.display_widget, 1)

    def set_mode(self, mode: str) -> None:
        self.display_widget.set_mode(mode)

    def set_transition_duration_seconds(self, seconds: float) -> None:
        self.display_widget.set_transition_duration_seconds(seconds)

    def set_video_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self.display_widget.set_video_pixmap(pixmap)

    def set_content_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self.display_widget.set_content_pixmap(pixmap)

    def set_backdrop_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self.display_widget.set_backdrop_pixmap(pixmap)

    def set_lyric_html(self, html: str) -> None:
        self.display_widget.set_lyric_html(html)

    def set_alert_text(self, text: str) -> None:
        self.display_widget.set_alert_text(text)

    def configure_backdrop(self, *, show_message: bool = False, message_text: str = "") -> None:
        self.display_widget.configure_backdrop(show_message=show_message, message_text=message_text)

    def configure_overlay(
        self,
        *,
        overlay_rect: Optional[dict[str, int]] = None,
        show_lyric_overlay: bool = False,
        show_stage_alert: bool = False,
    ) -> None:
        self.display_widget.configure_overlay(
            overlay_rect=overlay_rect,
            show_lyric_overlay=show_lyric_overlay,
            show_stage_alert=show_stage_alert,
        )


class MetronomeDisplayWindow(VideoDisplayWindow):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Metronome Display"))
