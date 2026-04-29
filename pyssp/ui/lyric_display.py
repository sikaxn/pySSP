from __future__ import annotations

import os
from typing import List, Optional

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from pyssp.i18n import tr
from pyssp.lyrics import LyricLine, lyric_segments_around_position, lyric_segments_to_html, parse_lyric_file
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
        self._font_family: str = ""
        self._font_size: int = 36
        self._previous_line_count: int = 0
        self._next_line_count: int = 0
        self._role_colors = {
            "played": "#A0A0A0",
            "current": "#FFD400",
            "next": "#FFFFFF",
        }
        self._role_sizes = {
            "played": 24,
            "current": 40,
            "next": 32,
        }
        self._auto_adjust_role_sizes = True
        self._role_scale_percents = {
            "played": 70,
            "current": 115,
            "next": 90,
        }
        self._role_bold = {
            "played": True,
            "current": True,
            "next": True,
        }
        self._role_italic = {
            "played": False,
            "current": False,
            "next": False,
        }
        self._apply_font_settings()

    def set_lyric_text(self, text: str) -> None:
        if self._lyric_widget is None:
            return
        self._lyric_widget.value_label.setText(str(text or ""))

    def configure_display_settings(
        self,
        *,
        font_family: str = "",
        font_size: int = 36,
        previous_line_count: int = 0,
        next_line_count: int = 0,
        role_colors: Optional[dict[str, str]] = None,
        role_sizes: Optional[dict[str, int]] = None,
        auto_adjust_role_sizes: bool = True,
        role_scale_percents: Optional[dict[str, int]] = None,
        role_bold: Optional[dict[str, bool]] = None,
        role_italic: Optional[dict[str, bool]] = None,
    ) -> None:
        self._font_family = str(font_family or "").strip()
        self._font_size = max(10, int(font_size))
        self._previous_line_count = max(0, int(previous_line_count))
        self._next_line_count = max(0, int(next_line_count))
        if role_colors is not None:
            self._role_colors = {
                "played": str(role_colors.get("played", "#A0A0A0") or "#A0A0A0").strip() or "#A0A0A0",
                "current": str(role_colors.get("current", "#FFD400") or "#FFD400").strip() or "#FFD400",
                "next": str(role_colors.get("next", "#FFFFFF") or "#FFFFFF").strip() or "#FFFFFF",
            }
        if role_sizes is not None:
            self._role_sizes = {
                "played": max(8, int(role_sizes.get("played", 24))),
                "current": max(8, int(role_sizes.get("current", 40))),
                "next": max(8, int(role_sizes.get("next", 32))),
            }
        self._auto_adjust_role_sizes = bool(auto_adjust_role_sizes)
        if role_scale_percents is not None:
            self._role_scale_percents = {
                "played": max(25, min(300, int(role_scale_percents.get("played", 70)))),
                "current": max(25, min(300, int(role_scale_percents.get("current", 115)))),
                "next": max(25, min(300, int(role_scale_percents.get("next", 90)))),
            }
        if role_bold is not None:
            self._role_bold = {
                "played": bool(role_bold.get("played", True)),
                "current": bool(role_bold.get("current", True)),
                "next": bool(role_bold.get("next", True)),
            }
        if role_italic is not None:
            self._role_italic = {
                "played": bool(role_italic.get("played", False)),
                "current": bool(role_italic.get("current", False)),
                "next": bool(role_italic.get("next", False)),
            }
        self._apply_font_settings()

    def update_playback_state(
        self,
        *,
        has_active_track: bool,
        lyric_path: str,
        position_ms: int,
        force_blank: bool = False,
        force: bool = False,
    ) -> None:
        text = ""
        if force_blank:
            text = ""
        elif not has_active_track:
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
                    segments = lyric_segments_around_position(
                        lines,
                        max(0, int(position_ms)),
                        self._previous_line_count,
                        self._next_line_count,
                    )
                    text = lyric_segments_to_html(
                        segments,
                        font_family=self._font_family,
                        role_styles=self._resolved_role_styles(),
                    )

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

    def _apply_font_settings(self) -> None:
        self._canvas.set_font_settings(
            default_font_family=self._font_family,
            default_value_font_size=self._font_size,
            lyric_font_family=self._font_family,
            lyric_value_font_size=self._font_size,
        )

    def _resolved_role_styles(self) -> dict[str, dict[str, object]]:
        if self._auto_adjust_role_sizes:
            sizes = {
                key: max(8, int(round(self._font_size * (self._role_scale_percents.get(key, 100) / 100.0))))
                for key in ("played", "current", "next")
            }
        else:
            sizes = dict(self._role_sizes)
        return {
            key: {
                "size": int(sizes[key]),
                "color": self._role_colors[key],
                "bold": self._role_bold[key],
                "italic": self._role_italic[key],
            }
            for key in ("played", "current", "next")
        }

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
