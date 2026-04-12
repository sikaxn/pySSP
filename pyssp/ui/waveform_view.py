from __future__ import annotations

from concurrent.futures import Future
from typing import Callable, List, Optional

import numpy as np
from PyQt5.QtCore import QObject, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from pyssp.audio_engine import ExternalMediaPlayer

class CueRangeIndicator(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._duration_ms = 0
        self._start_ms: Optional[int] = None
        self._end_ms: Optional[int] = None
        self._position_ms = 0
        self._waveform = np.array([], dtype=np.float32)
        self._loading = False
        self._loading_text = "Loading waveform..."
        self.setMinimumHeight(72)

    def sizeHint(self) -> QSize:
        return QSize(360, 80)

    def set_values(self, duration_ms: int, start_ms: Optional[int], end_ms: Optional[int]) -> None:
        self._duration_ms = max(0, int(duration_ms))
        self._start_ms = None if start_ms is None else max(0, int(start_ms))
        self._end_ms = None if end_ms is None else max(0, int(end_ms))
        self.update()

    def set_position(self, position_ms: int) -> None:
        self._position_ms = max(0, int(position_ms))
        self.update()

    def set_waveform(self, peaks: List[float]) -> None:
        if not peaks:
            self._waveform = np.array([], dtype=np.float32)
            self.update()
            return
        arr = np.asarray(peaks, dtype=np.float32)
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        arr = np.clip(arr, 0.0, 1.0)
        self._waveform = arr
        self.update()

    def set_loading(self, loading: bool, text: str = "Loading waveform...") -> None:
        self._loading = bool(loading)
        self._loading_text = str(text or "").strip() or "Loading waveform..."
        self.update()

    def _x_for_ms(self, value_ms: int, width: int) -> int:
        if self._duration_ms <= 0 or width <= 1:
            return 0
        ratio = max(0.0, min(1.0, value_ms / float(self._duration_ms)))
        return int(round(ratio * (width - 1)))

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        w = max(1, self.width())
        h = max(1, self.height())

        painter.fillRect(0, 0, w, h, QColor("#141A1F"))
        if self._loading:
            painter.setPen(QColor("#8AA6B8"))
            painter.drawRect(0, 0, w - 1, h - 1)
            painter.setPen(QColor("#D8E3EA"))
            painter.drawText(self.rect(), int(Qt.AlignCenter), self._loading_text)
            painter.end()
            return
        if self._duration_ms <= 0:
            painter.end()
            return

        start = 0 if self._start_ms is None else max(0, int(self._start_ms))
        end = self._duration_ms if self._end_ms is None else max(0, int(self._end_ms))
        if end < start:
            end = start
        start = min(start, self._duration_ms)
        end = min(end, self._duration_ms)
        x1 = self._x_for_ms(start, w)
        x2 = self._x_for_ms(end, w)
        if x2 < x1:
            x2 = x1
        painter.fillRect(x1, 0, max(1, x2 - x1 + 1), h, QColor("#253B4B"))

        if len(self._waveform) > 0:
            center = h // 2
            max_half = max(1, (h // 2) - 2)
            bright_wave_pen = QPen(QColor("#B9D7EA"))
            bright_wave_pen.setWidth(1)
            dim_wave_pen = QPen(QColor("#5E7586"))
            dim_wave_pen.setWidth(1)
            wave_count = len(self._waveform)
            for x in range(w):
                painter.setPen(bright_wave_pen if x1 <= x <= x2 else dim_wave_pen)
                idx = int((x / float(max(1, w - 1))) * float(max(0, wave_count - 1)))
                amp = float(self._waveform[idx])
                half = max(1, int(round(amp * max_half)))
                painter.drawLine(x, center - half, x, center + half)

        if self._start_ms is not None:
            x = self._x_for_ms(start, w)
            in_pen = QPen(QColor("#00C853"))
            in_pen.setWidth(2)
            painter.setPen(in_pen)
            painter.drawLine(x, 0, x, h - 1)
        if self._end_ms is not None:
            x = self._x_for_ms(end, w)
            out_pen = QPen(QColor("#FF5252"))
            out_pen.setWidth(2)
            painter.setPen(out_pen)
            painter.drawLine(x, 0, x, h - 1)

        playhead_x = self._x_for_ms(self._position_ms, w)
        playhead_pen = QPen(QColor("#FFD54F"))
        playhead_pen.setWidth(1)
        painter.setPen(playhead_pen)
        painter.drawLine(playhead_x, 0, playhead_x, h - 1)

        border_pen = QPen(QColor("#45535E"))
        border_pen.setWidth(1)
        painter.setPen(border_pen)
        painter.drawRect(0, 0, w - 1, h - 1)

        if self._start_ms is not None:
            painter.setPen(QColor("#00C853"))
            painter.drawText(4, 14, "In")
        if self._end_ms is not None:
            text = "Out"
            text_w = painter.fontMetrics().horizontalAdvance(text)
            painter.setPen(QColor("#FF5252"))
            painter.drawText(max(2, w - text_w - 4), 14, text)
        painter.end()


class WaveformRefreshController(QObject):
    def __init__(
        self,
        *,
        on_peaks: Callable[[List[float]], None],
        is_valid: Optional[Callable[[], bool]] = None,
        sample_count: int = 1800,
        interval_ms: int = 50,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._on_peaks = on_peaks
        self._is_valid = is_valid
        self._sample_count = max(1, int(sample_count))
        self._token = 0
        self._future: Optional[Future] = None
        self._player: Optional[ExternalMediaPlayer] = None
        self._duration_ms = 0
        self._pending_token = 0
        self._timer = QTimer(self)
        self._timer.setInterval(max(10, int(interval_ms)))
        self._timer.timeout.connect(self._poll)

    def stop(self) -> None:
        self._token += 1
        self._pending_token = 0
        self._future = None
        self._player = None
        self._duration_ms = 0
        if self._timer.isActive():
            self._timer.stop()

    def request(self, *, player: ExternalMediaPlayer, duration_ms: int) -> None:
        self.stop()
        self._duration_ms = max(0, int(duration_ms))
        if self._duration_ms <= 0:
            self._on_peaks([])
            return
        self._player = player
        self._token += 1
        self._submit(self._token)

    def _submit(self, token: int) -> None:
        player = self._player
        if player is None or token != self._token:
            return
        try:
            self._future = player.waveformPeaksAsync(self._sample_count)
        except Exception:
            self._future = None
            self._on_peaks([])
            return
        self._pending_token = token
        if not self._timer.isActive():
            self._timer.start()

    def _poll(self) -> None:
        future = self._future
        if future is None:
            self._timer.stop()
            return
        if not future.done():
            return
        self._future = None
        if self._pending_token != self._token:
            self._timer.stop()
            return
        if self._duration_ms <= 0:
            self._timer.stop()
            return
        if self._is_valid is not None and (not bool(self._is_valid())):
            self._timer.stop()
            return
        try:
            peaks = list(future.result())
        except Exception:
            peaks = []
        self._on_peaks(peaks)
        self._timer.stop()
