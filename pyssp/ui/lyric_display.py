from __future__ import annotations

import os
from typing import Callable, List, Optional

from PyQt5.QtCore import QEvent, QPoint, QTimer, Qt
from PyQt5.QtWidgets import QAction, QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from pyssp.i18n import tr
from pyssp.lyrics import LyricLine, lyric_segments_around_position, lyric_segments_to_html, parse_lyric_file
from pyssp.ui.stage_display import StageDisplayLayoutEditor, normalize_stage_display_gadgets


class LyricDisplayWindow(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        on_toggle_transparent_mode: Optional[Callable[[bool], None]] = None,
        on_adjust_font_size: Optional[Callable[[int], None]] = None,
        on_open_settings: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Lyric Display"))
        self.resize(980, 520)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_NoSystemBackground, False)

        self._transparent_mode_enabled = False
        self._on_toggle_transparent_mode = on_toggle_transparent_mode
        self._on_adjust_font_size = on_adjust_font_size
        self._on_open_settings = on_open_settings

        self._toolbar_hide_timer = QTimer(self)
        self._toolbar_hide_timer.setSingleShot(True)
        self._toolbar_hide_timer.setInterval(1000)
        self._toolbar_hide_timer.timeout.connect(self._hide_hover_toolbar)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(6)
        self._root_layout = root

        self._toolbar_overlay = QWidget(self)
        self._toolbar_overlay.setVisible(False)
        self._toolbar_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self._toolbar_overlay.setAttribute(Qt.WA_TranslucentBackground, True)
        self._toolbar_overlay.setAttribute(Qt.WA_NoSystemBackground, True)
        self._toolbar_overlay.setStyleSheet("background:transparent;")
        toolbar_row = QHBoxLayout(self._toolbar_overlay)
        toolbar_row.setContentsMargins(0, 0, 0, 0)
        toolbar_row.setSpacing(6)
        toolbar_style = (
            "QPushButton{background:rgba(20,20,20,220); color:#FFFFFF; border:1px solid rgba(255,255,255,120);"
            "border-radius:4px; padding:4px 10px;}"
            "QPushButton:hover{background:rgba(40,40,40,235);}"
        )
        self._toolbar_hint_label = QLabel(self._toolbar_overlay)
        self._toolbar_hint_label.setVisible(False)
        self._toolbar_hint_label.setStyleSheet(
            "QLabel{background:rgba(20,20,20,220); color:#FFFFFF; border:1px solid rgba(255,255,255,120);"
            "border-radius:4px; padding:4px 10px;}"
        )
        toolbar_row.addWidget(self._toolbar_hint_label, 0, Qt.AlignVCenter)
        toolbar_row.addStretch(1)
        self._font_size_down_button = QPushButton("-", self._toolbar_overlay)
        self._font_size_down_button.setVisible(False)
        self._font_size_down_button.setCursor(Qt.PointingHandCursor)
        self._font_size_down_button.setStyleSheet(toolbar_style)
        self._font_size_down_button.clicked.connect(lambda: self._handle_toolbar_font_adjust(-2))
        toolbar_row.addWidget(self._font_size_down_button, 0, Qt.AlignTop)

        self._font_size_up_button = QPushButton("+", self._toolbar_overlay)
        self._font_size_up_button.setVisible(False)
        self._font_size_up_button.setCursor(Qt.PointingHandCursor)
        self._font_size_up_button.setStyleSheet(toolbar_style)
        self._font_size_up_button.clicked.connect(lambda: self._handle_toolbar_font_adjust(2))
        toolbar_row.addWidget(self._font_size_up_button, 0, Qt.AlignTop)

        self._settings_button = QPushButton("", self._toolbar_overlay)
        self._settings_button.setVisible(False)
        self._settings_button.setCursor(Qt.PointingHandCursor)
        self._settings_button.setStyleSheet(toolbar_style)
        self._settings_button.clicked.connect(self._handle_toolbar_settings_clicked)
        toolbar_row.addWidget(self._settings_button, 0, Qt.AlignTop)

        self._fullscreen_button = QPushButton("", self._toolbar_overlay)
        self._fullscreen_button.setVisible(False)
        self._fullscreen_button.setCursor(Qt.PointingHandCursor)
        self._fullscreen_button.setStyleSheet(toolbar_style)
        self._fullscreen_button.clicked.connect(self._toggle_fullscreen)
        toolbar_row.addWidget(self._fullscreen_button, 0, Qt.AlignTop)

        self._transparent_toggle_button = QPushButton("", self._toolbar_overlay)
        self._transparent_toggle_button.setVisible(False)
        self._transparent_toggle_button.setCursor(Qt.PointingHandCursor)
        self._transparent_toggle_button.setStyleSheet(toolbar_style)
        self._transparent_toggle_button.clicked.connect(self._handle_toolbar_toggle_clicked)
        toolbar_row.addWidget(self._transparent_toggle_button, 0, Qt.AlignTop)

        self._canvas = StageDisplayLayoutEditor(self)
        root.addWidget(self._canvas, 1)
        self._canvas.setMouseTracking(True)
        self._canvas.setAttribute(Qt.WA_StyledBackground, True)
        for widget in self._canvas._widgets.values():
            widget._draggable = False
            widget._resize_handle.setVisible(False)
            widget.set_selected(False)
            widget.setMouseTracking(True)
            widget.setAttribute(Qt.WA_StyledBackground, True)
            widget.title_label.setMouseTracking(True)
            widget.value_label.setMouseTracking(True)

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
            self._lyric_widget.title_label.setVisible(False)

        self._install_fullscreen_toggle_filter(self)

        self._cache_path: str = ""
        self._cache_mtime: float = -1.0
        self._cache_lines: List[LyricLine] = []
        self._cache_error: str = ""
        self._last_text: str = ""
        self._font_family: str = ""
        self._font_size: int = 36
        self._show_not_playing_message = True
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
        self._apply_window_chrome()
        self._apply_font_settings()

    def set_lyric_text(self, text: str) -> None:
        if self._lyric_widget is None:
            return
        self._lyric_widget.value_label.setText(str(text or ""))

    def set_transparent_mode_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._transparent_mode_enabled:
            self._apply_window_chrome()
            return
        self._transparent_mode_enabled = enabled
        self._hide_hover_toolbar()
        self._apply_window_chrome()

    def configure_display_settings(
        self,
        *,
        font_family: str = "",
        font_size: int = 36,
        show_not_playing_message: bool = True,
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
        self._show_not_playing_message = bool(show_not_playing_message)
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
            text = "No sound is currently playing." if self._show_not_playing_message else ""
        else:
            path = str(lyric_path or "").strip()
            if not path:
                text = "No lyric file assigned for this sound." if self._show_not_playing_message else ""
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
            self._lyric_widget.title_label.setVisible(False)
        self._refresh_toolbar_text()

    def _apply_font_settings(self) -> None:
        self._canvas.set_font_settings(
            default_font_family=self._font_family,
            default_value_font_size=self._font_size,
            lyric_font_family=self._font_family,
            lyric_value_font_size=self._font_size,
        )
        if self._transparent_mode_enabled:
            self._refresh_transparent_visuals()

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
            child.setMouseTracking(True)
            child.installEventFilter(self)

    def _is_toolbar_widget(self, watched) -> bool:
        if watched is None:
            return False
        if watched is self._toolbar_overlay:
            return True
        if watched is self._toolbar_hint_label:
            return True
        if watched in {
            self._font_size_down_button,
            self._font_size_up_button,
            self._settings_button,
            self._fullscreen_button,
            self._transparent_toggle_button,
        }:
            return True
        try:
            return watched.parentWidget() is self._toolbar_overlay
        except Exception:
            return False

    def _refresh_toolbar_text(self) -> None:
        self._settings_button.setText(tr("Settings"))
        self._fullscreen_button.setText(tr("Windowed") if self.isFullScreen() else tr("Full Screen"))
        self._transparent_toggle_button.setText(
            tr("Turn Off Transparent Mode") if self._transparent_mode_enabled else tr("Turn On Transparent Mode")
        )
        self._toolbar_hint_label.setText(tr("Turn off transparent mode to move or resize this window."))

    def _show_hover_toolbar(self) -> None:
        self._refresh_toolbar_text()
        self._toolbar_hint_label.setVisible(bool(self._transparent_mode_enabled))
        self._font_size_down_button.setVisible(True)
        self._font_size_up_button.setVisible(True)
        self._settings_button.setVisible(True)
        self._fullscreen_button.setVisible(True)
        self._transparent_toggle_button.setVisible(True)
        self._toolbar_overlay.setVisible(True)
        self._font_size_down_button.raise_()
        self._font_size_up_button.raise_()
        self._settings_button.raise_()
        self._fullscreen_button.raise_()
        self._transparent_toggle_button.raise_()
        self._reposition_overlays()
        self._toolbar_hide_timer.start()
        self._toolbar_overlay.update()
        self.update(self._toolbar_overlay.geometry())

    def _hide_hover_toolbar(self) -> None:
        overlay_rect = self._toolbar_overlay.geometry()
        self._toolbar_hide_timer.stop()
        self._toolbar_hint_label.setVisible(False)
        self._font_size_down_button.setVisible(False)
        self._font_size_up_button.setVisible(False)
        self._settings_button.setVisible(False)
        self._fullscreen_button.setVisible(False)
        self._transparent_toggle_button.setVisible(False)
        self._toolbar_overlay.setVisible(False)
        self.update(overlay_rect)
        self._canvas.update()

    def _handle_toolbar_toggle_clicked(self) -> None:
        checked = not bool(self._transparent_mode_enabled)
        if callable(self._on_toggle_transparent_mode):
            self._on_toggle_transparent_mode(checked)
        else:
            self.set_transparent_mode_enabled(checked)
        self._show_hover_toolbar()

    def _handle_toolbar_font_adjust(self, delta: int) -> None:
        if callable(self._on_adjust_font_size):
            self._on_adjust_font_size(int(delta))
        else:
            self.configure_display_settings(font_size=max(10, self._font_size + int(delta)))
        self._show_hover_toolbar()

    def _handle_toolbar_settings_clicked(self) -> None:
        if callable(self._on_open_settings):
            self._on_open_settings()
        self._show_hover_toolbar()

    def _refresh_transparent_visuals(self) -> None:
        self._canvas.setAttribute(Qt.WA_TranslucentBackground, True)
        self._canvas.setAttribute(Qt.WA_NoSystemBackground, True)
        self._canvas.setAutoFillBackground(False)
        self._canvas.setStyleSheet("background:transparent; border:none;")
        if self._lyric_widget is not None:
            self._lyric_widget.setAttribute(Qt.WA_TranslucentBackground, True)
            self._lyric_widget.setAttribute(Qt.WA_NoSystemBackground, True)
            self._lyric_widget.setAutoFillBackground(False)
            self._lyric_widget._base_background = "rgba(0,0,0,0)"
            self._lyric_widget.apply_config(
                orientation="vertical",
                hide_text=True,
                hide_border=True,
                title_font_family=self._font_family,
                title_font_size=max(8, int(round(self._font_size * 0.55))),
                value_font_family=self._font_family,
                value_font_size=self._font_size,
            )
            self._lyric_widget.title_label.setVisible(False)
            self._lyric_widget.setStyleSheet(
                "QFrame{background:transparent; border:none; border-radius:0px;}"
                "QLabel{background:transparent; border:none; color:#FFFFFF;}"
            )

    def _apply_window_chrome(self) -> None:
        if self._transparent_mode_enabled:
            flags = Qt.Window | Qt.FramelessWindowHint
            if hasattr(Qt, "NoDropShadowWindowHint"):
                flags |= Qt.NoDropShadowWindowHint
            if self.windowFlags() != flags:
                was_visible = self.isVisible()
                self.setWindowFlags(flags)
                if was_visible:
                    self.show()
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)
            self.setStyleSheet("background:transparent; color:#FFFFFF;")
            self._refresh_transparent_visuals()
        else:
            flags = Qt.Window
            if self.windowFlags() != flags:
                was_visible = self.isVisible()
                self.setWindowFlags(flags)
                if was_visible:
                    self.show()
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            self.setAttribute(Qt.WA_NoSystemBackground, False)
            self.setStyleSheet("background:#000000; color:#FFFFFF;")
            self._canvas.setAttribute(Qt.WA_TranslucentBackground, False)
            self._canvas.setAttribute(Qt.WA_NoSystemBackground, False)
            self._canvas.setStyleSheet("background:#000000; border:0px solid transparent;")
            if self._lyric_widget is not None:
                self._lyric_widget.setAttribute(Qt.WA_TranslucentBackground, False)
                self._lyric_widget.setAttribute(Qt.WA_NoSystemBackground, False)
                self._lyric_widget._base_background = "#111111"
                self._lyric_widget.apply_config(
                    orientation="vertical",
                    hide_text=True,
                    hide_border=False,
                    title_font_family=self._font_family,
                    title_font_size=max(8, int(round(self._font_size * 0.55))),
                    value_font_family=self._font_family,
                    value_font_size=self._font_size,
                )
                self._lyric_widget.title_label.setVisible(False)
                self._lyric_widget.setStyleSheet("")
        self._refresh_toolbar_text()
        self._reposition_overlays()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reposition_overlays()

    def _reposition_overlays(self) -> None:
        toolbar_width = max(240, self.width() - 28)
        self._toolbar_overlay.setGeometry(14, 10, toolbar_width, 34)
        if self._toolbar_overlay.isVisible():
            self._toolbar_overlay.raise_()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._apply_window_chrome()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.MouseButtonDblClick:
            if self._is_toolbar_widget(watched):
                return False
            if getattr(event, "button", lambda: None)() == Qt.LeftButton:
                self._toggle_fullscreen()
                event.accept()
                return True
        if event.type() == QEvent.MouseMove:
            self._show_hover_toolbar()
        elif event.type() in {QEvent.Leave, QEvent.HoverLeave}:
            self._toolbar_hide_timer.start()
        return super().eventFilter(watched, event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._toolbar_overlay.isVisible():
            local_pos = event.pos()
            if self._toolbar_overlay.geometry().contains(local_pos):
                event.ignore()
                return
        if event.button() == Qt.LeftButton:
            self._toggle_fullscreen()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            self._apply_window_chrome()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        transparent_action = QAction(tr("Lyric Display Transparent Mode"), self)
        transparent_action.setCheckable(True)
        transparent_action.setChecked(bool(self._transparent_mode_enabled))
        settings_action = QAction(tr("Lyric Display Setting"), self)
        menu.addAction(transparent_action)
        menu.addAction(settings_action)
        chosen = menu.exec_(event.globalPos())
        if chosen == transparent_action:
            checked = bool(transparent_action.isChecked())
            if callable(self._on_toggle_transparent_mode):
                self._on_toggle_transparent_mode(checked)
            else:
                self.set_transparent_mode_enabled(checked)
        elif chosen == settings_action and callable(self._on_open_settings):
            self._on_open_settings()
