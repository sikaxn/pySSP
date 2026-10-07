from __future__ import annotations

import time
from collections import deque
from typing import Optional

from PyQt5.QtCore import QEvent, QRect, QRectF, QSize, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QImage,
    QOpenGLContext,
    QOpenGLPixelTransferOptions,
    QOpenGLTexture,
    QOpenGLTextureBlitter,
    QPainter,
    QPen,
    QPixmap,
    QTextDocument,
)
from PyQt5.QtWidgets import QOpenGLWidget, QVBoxLayout, QWidget

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


class _VideoDisplayWidgetCommon:
    def __init__(self, parent: Optional[QWidget] = None, *, allow_fullscreen_toggle: bool = False) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        update_behavior_setter = getattr(self, "setUpdateBehavior", None)
        no_partial_update = getattr(type(self), "NoPartialUpdate", None)
        if callable(update_behavior_setter) and no_partial_update is not None:
            try:
                update_behavior_setter(no_partial_update)
            except Exception:
                pass
        self._allow_fullscreen_toggle = bool(allow_fullscreen_toggle)
        self._mode = "blank"
        self._video_image = QImage()
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
        self._show_fps_overlay = False
        self._present_fps = 0.0
        self._present_paint_times = deque()
        self._video_scaled_pixmap_cache = QPixmap()
        self._video_scaled_pixmap_target_size = QSize()
        self._video_scaled_pixmap_source_size = QSize()
        self._surface_state_key = ("blank", "")
        self._transition_duration_sec = 0.0
        self._transition_prev_frame = QImage()
        self._transition_prev_frame_size = QSize()
        self._transition_started_at = 0.0
        self._transition_progress = 1.0
        self._transition_timer = QTimer(self)
        self._transition_timer.setInterval(8)
        self._transition_timer.setTimerType(Qt.PreciseTimer)
        self._transition_timer.timeout.connect(self._tick_transition)
        self._lyric_doc = QTextDocument(self)
        self._lyric_doc.setDocumentMargin(0.0)
        self._gl_video_texture: Optional[QOpenGLTexture] = None
        self._gl_video_texture_source_size = QSize()
        self._gl_video_texture_dirty = True
        self._gl_video_blitter: Optional[QOpenGLTextureBlitter] = None
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

    def current_present_fps(self) -> float:
        return float(self._present_fps)

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
        video_image: Optional[QImage] = None,
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
        show_fps_overlay: bool = False,
        transition_key: str = "",
    ) -> None:
        token = str(mode or "blank").strip().lower()
        surface_key = (token, str(transition_key or "").strip())
        if surface_key != self._surface_state_key:
            self._begin_mode_transition()
            self._reset_present_fps_tracking()
        self._surface_state_key = surface_key
        self._mode = token
        self._video_image = QImage() if video_image is None else QImage(video_image)
        self._video_pixmap = QPixmap() if video_pixmap is None else QPixmap(video_pixmap)
        self._clear_video_scaled_pixmap_cache()
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
        show_overlay = bool(show_fps_overlay)
        if show_overlay != self._show_fps_overlay:
            self._reset_present_fps_tracking()
        self._show_fps_overlay = show_overlay
        self._lyric_doc.setHtml(self._lyric_html)
        self._gl_video_texture_dirty = True
        self.update()

    def set_mode(self, mode: str) -> None:
        token = str(mode or "blank").strip().lower()
        if token == self._mode:
            return
        self._begin_mode_transition()
        self._reset_present_fps_tracking()
        self._surface_state_key = (token, "")
        self._mode = token
        self._gl_video_texture_dirty = True
        self.update()

    def set_video_image(self, image: Optional[QImage]) -> None:
        self._video_image = QImage() if image is None else QImage(image)
        self._clear_video_scaled_pixmap_cache()
        if image is not None:
            self._video_pixmap = QPixmap()
        self._gl_video_texture_dirty = True
        self.update()

    def set_video_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self._video_pixmap = QPixmap() if pixmap is None else QPixmap(pixmap)
        self._clear_video_scaled_pixmap_cache()
        if pixmap is not None:
            self._video_image = QImage()
        self._gl_video_texture_dirty = True
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

    def snapshot_image(self) -> QImage:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return QImage()
        image = QImage(size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.black)
        painter = QPainter(image)
        self._paint_composited_frame(painter, QRect(0, 0, size.width(), size.height()))
        painter.end()
        return image

    def grab(self, rectangle: Optional[QRect] = None) -> QPixmap:
        image = self.snapshot_image()
        if image.isNull():
            return QPixmap()
        pixmap = QPixmap.fromImage(image)
        if rectangle is None:
            return pixmap
        rect = QRect(rectangle)
        if rect.isNull() or not rect.isValid():
            return pixmap
        return pixmap.copy(rect)

    def _reset_present_fps_tracking(self) -> None:
        self._present_paint_times.clear()
        self._present_fps = 0.0

    def _record_present_paint(self) -> None:
        if not self._show_fps_overlay:
            self._reset_present_fps_tracking()
            return
        now = time.monotonic()
        self._present_paint_times.append(now)
        cutoff = now - 1.0
        while self._present_paint_times and self._present_paint_times[0] < cutoff:
            self._present_paint_times.popleft()
        if len(self._present_paint_times) < 4:
            self._present_fps = 0.0
            return
        span = max(0.001, self._present_paint_times[-1] - self._present_paint_times[0])
        self._present_fps = min(240.0, max(0.0, (len(self._present_paint_times) - 1) / span))

    def _draw_fps_overlay(self, painter: QPainter, bounds: QRect) -> None:
        if not self._show_fps_overlay:
            return
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(max(10, min(20, bounds.height() // 18)))
        painter.save()
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text = f"{self._present_fps:0.1f} fps"
        text_width = metrics.horizontalAdvance(text)
        box_width = text_width + 24
        box_height = metrics.height() + 14
        box = QRect(
            bounds.right() - box_width - 16,
            bounds.y() + 16,
            box_width,
            box_height,
        )
        painter.fillRect(box, QColor(0, 0, 0, 180))
        painter.setPen(QPen(QColor("#9EF0A8")))
        painter.drawText(box.adjusted(12, 7, -12, -7), Qt.AlignCenter, text)
        painter.restore()

    def _capture_current_frame(self) -> QImage:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return QImage()
        image = QImage(size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.black)
        painter = QPainter(image)
        self._paint_surface(painter, QRect(0, 0, size.width(), size.height()))
        painter.end()
        return image

    def _paint_composited_frame(self, painter: QPainter, bounds: QRect) -> None:
        self._record_present_paint()
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
        self._draw_fps_overlay(painter, bounds)

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
        self._draw_scaled_pixmap_with_quality(painter, rect, pixmap, keep_aspect=keep_aspect, smooth=True)

    def _draw_scaled_pixmap_with_quality(
        self,
        painter: QPainter,
        rect: QRect,
        pixmap: QPixmap,
        *,
        keep_aspect: bool,
        smooth: bool,
    ) -> None:
        if pixmap.isNull():
            return
        target = self._scaled_target_rect(rect, pixmap.width(), pixmap.height(), keep_aspect=keep_aspect)
        if target.size() == pixmap.size():
            painter.drawPixmap(target.topLeft(), pixmap)
            return
        painter.setRenderHint(QPainter.SmoothPixmapTransform, bool(smooth))
        painter.drawPixmap(target, pixmap, pixmap.rect())

    def _draw_scaled_image(self, painter: QPainter, rect: QRect, image: QImage, *, keep_aspect: bool) -> None:
        self._draw_scaled_image_with_quality(painter, rect, image, keep_aspect=keep_aspect, smooth=True)

    def _draw_scaled_image_with_quality(
        self,
        painter: QPainter,
        rect: QRect,
        image: QImage,
        *,
        keep_aspect: bool,
        smooth: bool,
    ) -> None:
        if image.isNull():
            return
        target = self._scaled_target_rect(rect, image.width(), image.height(), keep_aspect=keep_aspect)
        if target.size() == image.size():
            painter.drawImage(target.topLeft(), image)
            return
        painter.setRenderHint(QPainter.SmoothPixmapTransform, bool(smooth))
        painter.drawImage(target, image)

    def _clear_video_scaled_pixmap_cache(self) -> None:
        self._video_scaled_pixmap_cache = QPixmap()
        self._video_scaled_pixmap_target_size = QSize()
        self._video_scaled_pixmap_source_size = QSize()

    def _cached_live_video_pixmap(self, rect: QRect) -> tuple[QPixmap, QRect]:
        source = self._video_pixmap
        if source.isNull():
            return QPixmap(), QRect(rect)
        target = self._scaled_target_rect(rect, source.width(), source.height(), keep_aspect=True)
        if target.size() == source.size():
            return QPixmap(source), target
        if (
            not self._video_scaled_pixmap_cache.isNull()
            and self._video_scaled_pixmap_target_size == target.size()
            and self._video_scaled_pixmap_source_size == source.size()
        ):
            return QPixmap(self._video_scaled_pixmap_cache), target
        scaled = source.scaled(
            max(1, target.width()),
            max(1, target.height()),
            Qt.IgnoreAspectRatio,
            Qt.FastTransformation,
        )
        self._video_scaled_pixmap_cache = QPixmap(scaled)
        self._video_scaled_pixmap_target_size = QSize(target.size())
        self._video_scaled_pixmap_source_size = QSize(source.size())
        return QPixmap(self._video_scaled_pixmap_cache), target

    def _draw_live_video_surface(self, painter: QPainter, rect: QRect) -> None:
        if not self._video_pixmap.isNull():
            cached, target = self._cached_live_video_pixmap(rect)
            if not cached.isNull():
                painter.drawPixmap(target.topLeft(), cached)
                return
        if not self._video_image.isNull():
            self._draw_scaled_image_with_quality(painter, rect, self._video_image, keep_aspect=True, smooth=False)

    def _gl_video_source_image(self) -> QImage:
        if not self._video_pixmap.isNull():
            return self._video_pixmap.toImage()
        return QImage(self._video_image)

    def _can_use_gl_video_fast_path(self) -> bool:
        if self._mode != "video":
            return False
        if self._show_lyric_overlay and self._lyric_html.strip():
            return False
        if self._show_stage_alert and self._alert_text:
            return False
        if self._show_backdrop_message and self._backdrop_message_text:
            return False
        if not self._transition_prev_frame.isNull():
            return False
        source = self._gl_video_source_image()
        return not source.isNull()

    @staticmethod
    def _normalized_gl_image_payload(image: QImage) -> tuple[QImage, int, int, int]:
        if image.isNull():
            return QImage(), 0, 0, 0
        format_token = image.format()
        if format_token in {QImage.Format_RGBA8888, QImage.Format_RGBA8888_Premultiplied}:
            normalized = QImage(image)
            return normalized, QOpenGLTexture.RGBA, QOpenGLTexture.UInt8, 4
        if format_token == QImage.Format_RGB888:
            normalized = QImage(image)
            return normalized, QOpenGLTexture.RGB, QOpenGLTexture.UInt8, 3
        if format_token in {QImage.Format_ARGB32, QImage.Format_ARGB32_Premultiplied, QImage.Format_RGB32}:
            normalized = QImage(image)
            return normalized, QOpenGLTexture.BGRA, QOpenGLTexture.UInt8, 4
        normalized = image.convertToFormat(QImage.Format_RGBA8888)
        return normalized, QOpenGLTexture.RGBA, QOpenGLTexture.UInt8, 4

    def _ensure_gl_video_blitter(self) -> Optional[QOpenGLTextureBlitter]:
        blitter = self._gl_video_blitter
        if blitter is None:
            blitter = QOpenGLTextureBlitter()
            self._gl_video_blitter = blitter
        if not blitter.isCreated():
            try:
                if not blitter.create():
                    return None
            except Exception:
                return None
        return blitter

    def _ensure_gl_video_texture(self, source: QImage) -> Optional[QOpenGLTexture]:
        image, source_format, source_type, bytes_per_pixel = self._normalized_gl_image_payload(source)
        if image.isNull():
            return None
        texture = self._gl_video_texture
        source_size = image.size()
        if texture is None or texture.width() != source_size.width() or texture.height() != source_size.height():
            if texture is not None:
                try:
                    texture.destroy()
                except Exception:
                    pass
            try:
                texture = QOpenGLTexture(QOpenGLTexture.Target2D)
                texture.setFormat(QOpenGLTexture.RGBA8_UNorm)
                texture.setSize(max(1, source_size.width()), max(1, source_size.height()))
                texture.allocateStorage()
                texture.setWrapMode(QOpenGLTexture.ClampToEdge)
                texture.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
            except Exception:
                self._gl_video_texture = None
                self._gl_video_texture_source_size = QSize()
                return None
            self._gl_video_texture = texture
            self._gl_video_texture_source_size = QSize(source_size)
            self._gl_video_texture_dirty = True
        if self._gl_video_texture_dirty:
            try:
                options = QOpenGLPixelTransferOptions()
                options.setAlignment(1)
                options.setRowLength(max(1, int(image.bytesPerLine() // max(1, bytes_per_pixel))))
                payload = image.constBits()
                payload.setsize(image.byteCount())
                texture.setData(source_format, source_type, payload, options)
            except Exception:
                return None
            self._gl_video_texture_dirty = False
            self._gl_video_texture_source_size = QSize(source_size)
        return texture

    def _render_gl_video_fast_path(self) -> bool:
        if not self._can_use_gl_video_fast_path():
            return False
        context = QOpenGLContext.currentContext()
        if context is None:
            return False
        blitter = self._ensure_gl_video_blitter()
        if blitter is None:
            return False
        source = self._gl_video_source_image()
        texture = self._ensure_gl_video_texture(source)
        if texture is None or not texture.isCreated():
            return False
        bounds = self.rect()
        if bounds.width() <= 0 or bounds.height() <= 0:
            return False
        try:
            functions = context.functions()
            functions.glViewport(0, 0, max(1, bounds.width()), max(1, bounds.height()))
            functions.glClearColor(0.0, 0.0, 0.0, 1.0)
            functions.glClear(0x00004000)
            target = self._scaled_target_rect(bounds, source.width(), source.height(), keep_aspect=True)
            transform = QOpenGLTextureBlitter.targetTransform(QRectF(target), bounds)
            blitter.bind()
            blitter.blit(texture.textureId(), transform, QOpenGLTextureBlitter.OriginTopLeft)
            blitter.release()
        except Exception:
            return False
        self._record_present_paint()
        if self._show_fps_overlay:
            painter = QPainter(self)
            self._draw_fps_overlay(painter, bounds)
            painter.end()
        return True

    def _paint_surface(self, painter: QPainter, bounds: QRect) -> None:
        mode = self._mode
        if mode == "white_screen":
            painter.fillRect(bounds, QColor("#FFFFFF"))
        else:
            painter.fillRect(bounds, QColor("#000000"))
        if mode == "colour_bars":
            self._draw_colour_bars(painter, bounds)
        elif mode == "video":
            self._draw_live_video_surface(painter, bounds)
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

    def _paint_widget_frame(self) -> None:
        painter = QPainter(self)
        bounds = self.rect()
        self._paint_composited_frame(painter, bounds)
        painter.end()


class VideoDisplayWidget(_VideoDisplayWidgetCommon, QOpenGLWidget):
    surfaceChanged = pyqtSignal()

    def paintGL(self) -> None:
        if self._render_gl_video_fast_path():
            return
        self._paint_widget_frame()


class OffscreenVideoDisplayWidget(_VideoDisplayWidgetCommon, QWidget):
    surfaceChanged = pyqtSignal()

    def paintEvent(self, _event) -> None:
        self._paint_widget_frame()


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

    def set_video_image(self, image: Optional[QImage]) -> None:
        self.display_widget.set_video_image(image)

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
