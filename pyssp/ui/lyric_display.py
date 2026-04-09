from __future__ import annotations

import os
from typing import List, Optional

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from pyssp.i18n import tr
from pyssp.lyrics import LyricLine, line_for_position, parse_lyric_file
from pyssp.ui.stage_display import StageDisplayLayoutEditor, normalize_stage_display_gadgets


class LyricDisplayWindow(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Lyric Display"))
        self.resize(980, 520)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet("background:#000000; color:#FFFFFF;")

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(6)

        self._canvas = StageDisplayLayoutEditor(self)
        root.addWidget(self._canvas, 1)
        for widget in self._canvas._widgets.values():
            widget._draggable = False
            widget._resize_handle.setVisible(False)
            widget.set_selected(False)

        lyric_only = normalize_stage_display_gadgets({})
        for key, spec in lyric_only.items():
            spec["visible"] = key == "lyric"
            spec["hide_text"] = key == "lyric"
            spec["hide_border"] = False
            if key == "lyric":
                spec["x"] = 0
                spec["y"] = 0
                spec["w"] = 10000
                spec["h"] = 10000
                spec["orientation"] = "vertical"
                spec["z"] = 99
            else:
                spec["z"] = 0
        self._canvas.set_gadgets(lyric_only)

        self._lyric_widget = self._canvas._widgets.get("lyric")
        if self._lyric_widget is not None:
            self._lyric_widget.title_label.setText(tr("Lyric"))
        self._install_fullscreen_toggle_filter(self)

        self._cache_path: str = ""
        self._cache_mtime: float = -1.0
        self._cache_lines: List[LyricLine] = []
        self._cache_error: str = ""
        self._last_text: str = ""

    def set_lyric_text(self, text: str) -> None:
        if self._lyric_widget is None:
            return
        self._lyric_widget.value_label.setText(str(text or ""))

    def update_playback_state(
        self,
        *,
        has_active_track: bool,
        lyric_path: str,
        position_ms: int,
        force: bool = False,
    ) -> None:
        text = ""
        if not has_active_track:
            text = "No sound is currently playing."
        else:
            path = str(lyric_path or "").strip()
            if not path:
                text = "No lyric file assigned for this sound."
            elif not os.path.exists(path):
                text = f"Lyric file not found:\n{path}"
            else:
                lines, error = self._load_lyric_lines(path)
                if error:
                    text = error
                elif not lines:
                    text = "No lyrics were found in this file."
                else:
                    text = line_for_position(lines, max(0, int(position_ms))) or ""

        if force or text != self._last_text:
            self._last_text = text
            self.set_lyric_text(text)

    def _load_lyric_lines(self, lyric_path: str) -> tuple[List[LyricLine], str]:
        mtime = -1.0
        try:
            mtime = os.path.getmtime(lyric_path)
        except OSError:
            return [], f"Lyric file not found:\n{lyric_path}"
        if lyric_path == self._cache_path and abs(mtime - self._cache_mtime) < 0.0001:
            return self._cache_lines, self._cache_error
        try:
            lines = parse_lyric_file(lyric_path)
            error = ""
        except Exception as exc:
            lines = []
            error = f"Failed to read lyric file:\n{exc}"
        self._cache_path = lyric_path
        self._cache_mtime = mtime
        self._cache_lines = lines
        self._cache_error = error
        return lines, error

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("Lyric Display"))
        if self._lyric_widget is not None:
            self._lyric_widget.title_label.setText(tr("Lyric"))

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
