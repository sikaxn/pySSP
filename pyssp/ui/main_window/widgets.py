from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *

__all__ = [
    "SoundButtonData",
    "SoundButton",
    "NowPlayingLabel",
    "GroupButton",
    "ToolListWindow",
    "AboutWindowDialog",
    "TimecodePanel",
    "DbfsMeterScale",
    "DbfsMeter",
    "StageDisplayWindow",
    "NoAudioPlayer",
    "TransportProgressDisplay",
    "MainThreadExecutor",
    "LockScreenOverlay",
]

@dataclass
class SoundButtonData:
    file_path: str = ""
    vocal_removed_file: str = ""
    title: str = ""
    notes: str = ""
    lyric_file: str = ""
    duration_ms: int = 0
    custom_color: Optional[str] = None
    highlighted: bool = False
    played: bool = False
    activity_code: str = ""
    locked: bool = False
    marker: bool = False
    copied_to_cue: bool = False
    load_failed: bool = False
    volume_override_pct: Optional[int] = None
    cue_start_ms: Optional[int] = None
    cue_end_ms: Optional[int] = None
    timecode_offset_ms: Optional[int] = None
    timecode_timeline_mode: str = "global"
    sound_hotkey: str = ""
    sound_midi_hotkey: str = ""

    @property
    def assigned(self) -> bool:
        return bool(self.file_path)

    @property
    def missing(self) -> bool:
        return self.assigned and not os.path.exists(str(self.file_path or "").strip())

    def display_text(self) -> str:
        if self.marker:
            return ""
        if not self.assigned:
            return ""
        parts: List[str] = []
        if self.volume_override_pct is not None:
            parts.append("V")
        has_cue = (self.cue_end_ms is not None) or ((self.cue_start_ms is not None) and int(self.cue_start_ms) > 0)
        if has_cue:
            parts.append("C")
        has_timecode = (self.timecode_offset_ms is not None and int(self.timecode_offset_ms) > 0) or (
            self.timecode_timeline_mode in {"audio_file", "cue_region"}
        )
        if has_timecode:
            parts.append("T")
        suffix = " ".join(parts)
        return format_sound_button_label(self.title, self.duration_ms, suffix, 26)


class SoundButton(QPushButton):
    def __init__(self, slot_index: int, host: "MainWindow"):
        super().__init__("")
        self._host = host
        self.slot_index = slot_index
        self._drag_start_pos = None
        self._ram_loaded = False
        self._top_indicator_color: Optional[str] = None
        self._bottom_indicator_colors: List[str] = []
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(0, 0)
        self.setStyleSheet("font-size: 10pt; font-weight: bold;")
        self.setAcceptDrops(True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._drag_start_pos is not None
            and (event.buttons() & Qt.LeftButton)
            and self._host._is_button_drag_enabled()
        ):
            if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self._host._start_sound_button_drag(self.slot_index)
                self._drag_start_pos = None
                return
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event) -> None:
        self._host._show_slot_menu(self.slot_index, event.pos())
        event.accept()

    def dragEnterEvent(self, event) -> None:
        if self._host._can_accept_sound_button_drop(event.mimeData()) or self._host._can_accept_sound_file_drop(
            event.mimeData()
        ):
            self._host._set_sound_button_drop_target(self.slot_index)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._host._can_accept_sound_button_drop(event.mimeData()) or self._host._can_accept_sound_file_drop(
            event.mimeData()
        ):
            self._host._set_sound_button_drop_target(self.slot_index)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._host._clear_sound_button_drop_target()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:
        if not (
            self._host._can_accept_sound_button_drop(event.mimeData())
            or self._host._can_accept_sound_file_drop(event.mimeData())
        ):
            self._host._clear_sound_button_drop_target()
            event.ignore()
            return
        dropped = self._host._handle_sound_button_drop(self.slot_index, event.mimeData())
        self._host._clear_sound_button_drop_target()
        if dropped:
            event.acceptProposedAction()
            return
        event.ignore()

    def enterEvent(self, event) -> None:
        self._host._on_sound_button_hover(self.slot_index)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._host._on_sound_button_hover(None)
        super().leaveEvent(event)

    def set_ram_loaded(self, loaded: bool) -> None:
        loaded_flag = bool(loaded)
        if loaded_flag == self._ram_loaded:
            return
        self._ram_loaded = loaded_flag
        self.update()

    def set_indicator_colors(self, top_color: Optional[str], bottom_colors: List[str]) -> None:
        normalized_top = str(top_color).strip() if top_color else None
        normalized_bottom = [str(color).strip() for color in bottom_colors if str(color).strip()]
        if normalized_top == self._top_indicator_color and normalized_bottom == self._bottom_indicator_colors:
            return
        self._top_indicator_color = normalized_top
        self._bottom_indicator_colors = normalized_bottom
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        stripe_painter = QPainter(self)
        stripe_painter.setRenderHint(QPainter.Antialiasing, False)
        stripe_painter.setPen(Qt.NoPen)
        top_margin = 1
        side_margin = 1
        top_height = max(3, min(8, int(round(self.height() * 0.11))))
        bottom_height = max(4, min(10, int(round(self.height() * 0.12))))
        if self._top_indicator_color:
            stripe_painter.setBrush(QColor(self._top_indicator_color))
            stripe_painter.drawRect(
                side_margin,
                top_margin,
                max(1, self.width() - (side_margin * 2)),
                top_height,
            )
        if self._bottom_indicator_colors:
            stripe_area_width = max(1, self.width() - (side_margin * 2))
            stripe_y = max(top_margin, self.height() - bottom_height - top_margin)
            count = len(self._bottom_indicator_colors)
            for idx, color in enumerate(self._bottom_indicator_colors):
                start_x = side_margin + int(round((stripe_area_width * idx) / count))
                end_x = side_margin + int(round((stripe_area_width * (idx + 1)) / count))
                stripe_painter.setBrush(QColor(color))
                stripe_painter.drawRect(start_x, stripe_y, max(1, end_x - start_x), bottom_height)
        stripe_painter.end()
        if not self._ram_loaded:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2ED573"))
        d = 8
        x = max(2, self.width() - d - 3)
        y = max(2, self.height() - d - 3)
        p.drawEllipse(x, y, d, d)
        p.end()


class NowPlayingLabel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._prefix = "NOW PLAYING:"
        self._value = ""
        self._value_html_override: Optional[str] = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(1)
        self._prefix_label = QLabel(self._prefix, self)
        self._prefix_label.setStyleSheet("color:#0A29E0; font-weight:700; font-size:11pt;")
        self._value_label = QLabel("", self)
        self._value_label.setStyleSheet("color:#101010; font-size:11pt;")
        self._value_label.setWordWrap(True)
        self._value_label.setTextFormat(Qt.RichText)
        self._value_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._value_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._value_label.setMinimumWidth(0)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setWidget(self._value_label)
        root.addWidget(self._prefix_label)
        root.addWidget(self._scroll, 1)
        line_h = self.fontMetrics().lineSpacing()
        self.setFixedHeight((line_h * 3) + 10)

    def set_now_playing_text(self, prefix: str, value: str) -> None:
        self._prefix = prefix
        self._value = value
        self._value_html_override = None
        self._refresh_text()

    def set_now_playing_html(self, prefix: str, value_html: str) -> None:
        self._prefix = prefix
        self._value = ""
        self._value_html_override = str(value_html or "")
        self._refresh_text()

    @staticmethod
    def _to_wrapped_html(value: str) -> str:
        escaped = html.escape(str(value or ""))
        escaped = escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")
        for token in ["/", "\\", "_", "-", ".", ":"]:
            escaped = escaped.replace(token, f"{token}<wbr/>")
        return escaped

    def _refresh_text(self) -> None:
        self._prefix_label.setText(self._prefix)
        if self._value_html_override is not None:
            self._value_label.setText(self._value_html_override)
        else:
            self._value_label.setText(self._to_wrapped_html(self._value))


class GroupButton(QPushButton):
    def __init__(self, group: str, host: "MainWindow"):
        super().__init__(group)
        self.group = group
        self._host = host
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if self._host._can_accept_sound_button_drop(event.mimeData()) or self._host._can_accept_page_button_drop(
            event.mimeData()
        ):
            self._host._handle_drag_over_group(self.group)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._host._can_accept_sound_button_drop(event.mimeData()) or self._host._can_accept_page_button_drop(
            event.mimeData()
        ):
            self._host._handle_drag_over_group(self.group)
            event.acceptProposedAction()
            return
        event.ignore()

class ToolListWindow(QDialog):
    def __init__(
        self,
        title: str,
        parent=None,
        double_click_action: str = "goto",
        show_play_button: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(980, 640)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)

        self._goto_handler: Optional[Callable[[dict], None]] = None
        self._play_handler: Optional[Callable[[dict], None]] = None
        self._export_handler: Optional[Callable[[str], None]] = None
        self._print_handler: Optional[Callable[[], None]] = None
        self._refresh_handler: Optional[Callable[[str], None]] = None
        self._double_click_action = "play" if double_click_action == "play" else "goto"

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Order"))
        self.order_combo = QComboBox()
        self.order_combo.setVisible(False)
        top_row.addWidget(self.order_combo)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setVisible(False)
        top_row.addWidget(self.refresh_btn)
        top_row.addStretch(1)
        root.addLayout(top_row)

        self.note_label = QLabel("")
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet("color:#555555;")
        self.note_label.setVisible(False)
        root.addWidget(self.note_label)

        self.results_list = QListWidget()
        self.results_list.itemActivated.connect(self._on_item_activated)
        root.addWidget(self.results_list, 1)

        self.status_label = QLabel("")
        root.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.goto_btn = QPushButton("Go To Selected")
        self.play_btn = QPushButton("Play")
        self.export_excel_btn = QPushButton("Export Excel")
        self.export_csv_btn = QPushButton("Export CSV")
        self.print_btn = QPushButton("Print")
        self.close_btn = QPushButton("Close")
        button_row.addWidget(self.goto_btn)
        if show_play_button:
            button_row.addWidget(self.play_btn)
        else:
            self.play_btn.setVisible(False)
        button_row.addWidget(self.export_excel_btn)
        button_row.addWidget(self.export_csv_btn)
        button_row.addWidget(self.print_btn)
        button_row.addWidget(self.close_btn)
        root.addLayout(button_row)

        self.goto_btn.clicked.connect(self.go_to_selected)
        self.play_btn.clicked.connect(self.play_selected)
        self.export_excel_btn.clicked.connect(lambda: self._export("excel"))
        self.export_csv_btn.clicked.connect(lambda: self._export("csv"))
        self.print_btn.clicked.connect(self._print)
        self.close_btn.clicked.connect(self.close)

    def set_handlers(
        self,
        goto_handler: Callable[[dict], None],
        play_handler: Optional[Callable[[dict], None]],
        export_handler: Callable[[str], None],
        print_handler: Callable[[], None],
    ) -> None:
        self._goto_handler = goto_handler
        self._play_handler = play_handler
        self._export_handler = export_handler
        self._print_handler = print_handler

    def enable_order_controls(self, options: List[str], refresh_handler: Callable[[str], None]) -> None:
        self.order_combo.clear()
        self.order_combo.addItems(options)
        self.order_combo.setVisible(True)
        self.refresh_btn.setVisible(True)
        self._refresh_handler = refresh_handler
        self.order_combo.currentTextChanged.connect(self._refresh_from_order)
        self.refresh_btn.clicked.connect(self._refresh_from_order)

    def current_order(self) -> str:
        return self.order_combo.currentText().strip()

    def set_items(self, lines: List[str], matches: Optional[List[Optional[dict]]] = None, status: str = "") -> None:
        self.results_list.clear()
        for i, line in enumerate(lines):
            item = QListWidgetItem(line)
            if matches and i < len(matches):
                item.setData(Qt.UserRole, matches[i])
            self.results_list.addItem(item)
        self.status_label.setText(status)

    def set_note(self, text: str) -> None:
        value = str(text or "").strip()
        self.note_label.setText(value)
        self.note_label.setVisible(bool(value))

    def go_to_selected(self) -> None:
        if self._goto_handler is None:
            return
        match = self._selected_match()
        if match is None:
            return
        self._goto_handler(match)

    def play_selected(self) -> None:
        if self._play_handler is None:
            return
        match = self._selected_match()
        if match is None:
            return
        self._play_handler(match)

    def _export(self, export_format: str) -> None:
        if self._export_handler is None:
            return
        self._export_handler(export_format)

    def _print(self) -> None:
        if self._print_handler is None:
            return
        self._print_handler()

    def _refresh_from_order(self, _value: str = "") -> None:
        if self._refresh_handler is None:
            return
        self._refresh_handler(self.current_order())

    def _on_item_activated(self, _item) -> None:
        if self._double_click_action == "play":
            self.play_selected()
            return
        self.go_to_selected()

    def _selected_match(self) -> Optional[dict]:
        item = self.results_list.currentItem()
        if item is None:
            return None
        match = item.data(Qt.UserRole)
        if not isinstance(match, dict):
            return None
        return match


class AboutWindowDialog(QDialog):
    def __init__(self, title: str, logo_path: str, version_text: str = "", website_url: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)

        self._cover_pixmap = QPixmap(logo_path)
        self._target_cover_width = 360
        if not self._cover_pixmap.isNull():
            self._target_cover_width = max(320, min(420, self._cover_pixmap.width() // 4))

        self.resize(self._target_cover_width + 24, 460)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self.cover_label = QLabel(self)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setMinimumHeight(90)
        self.cover_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self.cover_label)
        self._refresh_cover_pixmap()

        self.notice_label = QLabel(
            "pySSP is an independent project and is not affiliated with the original Sports Sounds Pro (SSP).",
            self,
        )
        self.notice_label.setAlignment(Qt.AlignCenter)
        self.notice_label.setWordWrap(True)
        root.addWidget(self.notice_label)
        self.version_label = QLabel("", self)
        self.version_label.setAlignment(Qt.AlignCenter)
        self.version_label.setWordWrap(True)
        root.addWidget(self.version_label)
        self.build_label = QLabel("", self)
        self.build_label.setAlignment(Qt.AlignCenter)
        self.build_label.setWordWrap(True)
        root.addWidget(self.build_label)
        self.website_label = QLabel("", self)
        self.website_label.setAlignment(Qt.AlignCenter)
        self.website_label.setWordWrap(True)
        self.website_label.setOpenExternalLinks(True)
        self.website_label.setTextFormat(Qt.RichText)
        self.website_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        root.addWidget(self.website_label)
        self.set_version_and_website(version_text, website_url)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        self.about_viewer = self._build_tab_textbox()
        self.credits_viewer = self._build_tab_textbox()
        self.license_viewer = self._build_tab_textbox(no_wrap=True)

        self.tabs.addTab(self.about_viewer, "About")
        self.tabs.addTab(self.credits_viewer, "Credits")
        self.tabs.addTab(self.license_viewer, "License")

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_row.addWidget(close_btn)
        root.addLayout(button_row)

    def _build_tab_textbox(self, no_wrap: bool = False) -> QPlainTextEdit:
        textbox = QPlainTextEdit(self)
        textbox.setReadOnly(True)
        textbox.setLineWrapMode(QPlainTextEdit.NoWrap if no_wrap else QPlainTextEdit.WidgetWidth)
        return textbox

    def _refresh_cover_pixmap(self) -> None:
        if self._cover_pixmap.isNull():
            self.cover_label.setText("logo2.png not found")
            return
        scaled = self._cover_pixmap.scaled(
            min(self.cover_label.width(), self._target_cover_width),
            max(self.cover_label.height(), 180),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.cover_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_cover_pixmap()

    def set_content(self, about_text: str, credits_text: str, license_text: str) -> None:
        self.about_viewer.setPlainText(about_text)
        self.credits_viewer.setPlainText(credits_text)
        self.license_viewer.setPlainText(license_text)

    def set_version_and_website(self, version_text: str, website_url: str, build_text: str = "") -> None:
        version_value = str(version_text or "").strip()
        if version_value:
            self.version_label.setText(f"{tr('Version:')} {version_value}")
            self.version_label.setVisible(True)
        else:
            self.version_label.setText("")
            self.version_label.setVisible(False)
        build_value = str(build_text or "").strip()
        if build_value:
            self.build_label.setText(f"{tr('Build:')} {build_value}")
            self.build_label.setVisible(True)
        else:
            self.build_label.setText("")
            self.build_label.setVisible(False)
        site = str(website_url or "").strip()
        if site:
            safe_site = html.escape(site, quote=True)
            self.website_label.setText(f'<a href="{safe_site}">{safe_site}</a>')
            self.website_label.setVisible(True)
        else:
            self.website_label.setText("")
            self.website_label.setVisible(False)


class TimecodePanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        mode_group = QFrame(self)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.addWidget(QLabel("Timecode Mode"))
        self.mode_combo = QComboBox(mode_group)
        self.mode_combo.addItem("All Zero", TIMECODE_MODE_ZERO)
        self.mode_combo.addItem("Follow Media/Audio Player", TIMECODE_MODE_FOLLOW)
        self.mode_combo.addItem("System Time", TIMECODE_MODE_SYSTEM)
        self.mode_combo.addItem("Pause Sync (Freeze While Playback Continues)", TIMECODE_MODE_FOLLOW_FREEZE)
        mode_layout.addWidget(self.mode_combo)
        root.addWidget(mode_group)

        current_group = QFrame(self)
        current_layout = QVBoxLayout(current_group)
        current_layout.setContentsMargins(0, 0, 0, 0)
        current_layout.addWidget(QLabel("Current Output"))
        self.timecode_label = QLabel("00:00:00:00", current_group)
        font = self.timecode_label.font()
        font.setPointSize(max(font.pointSize() + 6, 14))
        font.setBold(True)
        self.timecode_label.setFont(font)
        self.timecode_label.setAlignment(Qt.AlignCenter)
        current_layout.addWidget(self.timecode_label)
        self.device_label = QLabel("", current_group)
        self.device_label.setWordWrap(True)
        current_layout.addWidget(self.device_label)
        root.addWidget(current_group)
        root.addStretch(1)


class DbfsMeterScale(QWidget):
    TICKS = (-60, -24, -12, -6, 0)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(18)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip("Meter scale in dBFS")

    @staticmethod
    def _db_to_ratio(db_value: int) -> float:
        clamped = max(-60.0, min(0.0, float(db_value)))
        return (clamped + 60.0) / 60.0

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect().adjusted(1, 0, -1, -1)
        if rect.width() <= 0 or rect.height() <= 0:
            painter.end()
            return

        painter.setPen(QColor("#7F8C97"))
        for db_value in self.TICKS:
            x = rect.left() + int(round(rect.width() * self._db_to_ratio(db_value)))
            painter.drawLine(x, rect.bottom() - 6, x, rect.bottom())
            label_left = max(rect.left(), min(x - 16, rect.right() - 31))
            label_rect = QRect(label_left, rect.top(), 32, rect.height() - 6)
            painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignVCenter, str(db_value))

        painter.end()


class DbfsMeter(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._level = 0.0
        self.setMinimumHeight(16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setToolTip("Peak meter with dBFS scale")

    @staticmethod
    def _db_to_ratio(db_value: float) -> float:
        clamped = max(-60.0, min(0.0, db_value))
        return (clamped + 60.0) / 60.0

    @staticmethod
    def _level_to_ratio(level: float) -> float:
        if level <= 0.000001:
            return 0.0
        db_value = 20.0 * math.log10(max(0.000001, min(1.0, float(level))))
        return DbfsMeter._db_to_ratio(db_value)

    def setLevel(self, level: float) -> None:
        next_level = max(0.0, min(1.0, float(level)))
        if abs(next_level - self._level) < 0.001:
            return
        self._level = next_level
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        rect = self.rect().adjusted(0, 1, -1, -1)
        if rect.width() <= 1 or rect.height() <= 1:
            painter.end()
            return

        painter.fillRect(rect, QColor("#11161B"))
        zone_specs = [
            (-60.0, -12.0, QColor("#17341D")),
            (-12.0, -6.0, QColor("#574A16")),
            (-6.0, 0.0, QColor("#5A1E1B")),
        ]
        for start_db, end_db, color in zone_specs:
            start_x = rect.left() + int(round(rect.width() * self._db_to_ratio(start_db)))
            end_x = rect.left() + int(round(rect.width() * self._db_to_ratio(end_db)))
            if end_x > start_x:
                painter.fillRect(QRect(start_x, rect.top(), end_x - start_x, rect.height()), color)

        fill_width = int(round(rect.width() * self._level_to_ratio(self._level)))
        fill_specs = [
            (-60.0, -12.0, QColor("#2ECF5A")),
            (-12.0, -6.0, QColor("#F3C746")),
            (-6.0, 0.0, QColor("#E05243")),
        ]
        for start_db, end_db, color in fill_specs:
            start_x = rect.left() + int(round(rect.width() * self._db_to_ratio(start_db)))
            end_x = rect.left() + int(round(rect.width() * self._db_to_ratio(end_db)))
            clipped_end_x = min(rect.left() + fill_width, end_x)
            if clipped_end_x > start_x:
                painter.fillRect(QRect(start_x, rect.top(), clipped_end_x - start_x, rect.height()), color)

        painter.setPen(QColor("#6B7783"))
        for db_value in DbfsMeterScale.TICKS:
            x = rect.left() + int(round(rect.width() * self._db_to_ratio(float(db_value))))
            painter.drawLine(x, rect.top(), x, rect.bottom())

        painter.setPen(QColor("#8C939D"))
        painter.drawRect(rect)
        painter.end()


class StageDisplayWindow(QWidget):
    DISPLAY_LABELS = {
        "total_time": "Total Time",
        "elapsed": "Elapsed",
        "remaining": "Remaining",
        "progress_bar": "Progress",
        "song_name": "Song",
        "next_song": "Next Song",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Stage Display"))
        self.resize(980, 600)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet("background:#000000; color:#FFFFFF;")
        self._order = list(self.DISPLAY_LABELS.keys())
        self._visibility = {key: True for key in self.DISPLAY_LABELS.keys()}

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)
        self._outer_layout = root
        self._datetime_label = QLabel("", self)
        self._datetime_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._datetime_label.setStyleSheet("font-size:20pt; font-weight:bold; color:#E6E6E6;")
        root.addWidget(self._datetime_label, 0, Qt.AlignLeft | Qt.AlignTop)

        center = QWidget(self)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(18)
        center_layout.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._center_layout = center_layout
        self._rows: Dict[str, QWidget] = {}
        self._value_labels: Dict[str, QLabel] = {}
        self._title_labels: Dict[str, QLabel] = {}
        self._time_value_labels: List[QLabel] = []
        self._song_value_labels: List[QLabel] = []
        self._song_raw_values: Dict[str, str] = {"song_name": "-", "next_song": "-"}
        self._song_base_pt = 48
        self._song_text_boxes: Dict[str, QFrame] = {}
        self._status_state = "not_playing"

        times_row = QWidget(center)
        times_layout = QHBoxLayout(times_row)
        times_layout.setContentsMargins(0, 0, 0, 0)
        times_layout.setSpacing(28)
        self._times_layout = times_layout
        for key in ["total_time", "elapsed", "remaining"]:
            panel = QFrame(times_row)
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(0, 0, 0, 0)
            panel_layout.setSpacing(4)
            title_label = QLabel(self.DISPLAY_LABELS[key], panel)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-size:20pt; font-weight:bold; color:#D0D0D0;")
            value = QLabel("-", panel)
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("font-size:44pt; font-weight:bold; color:#FFFFFF;")
            panel_layout.addWidget(title_label)
            panel_layout.addWidget(value)
            self._rows[key] = panel
            self._value_labels[key] = value
            self._title_labels[key] = title_label
            self._time_value_labels.append(value)
            times_layout.addWidget(panel)
        center_layout.addWidget(times_row, 0, Qt.AlignHCenter)
        self._times_row = times_row

        progress_row = QFrame(center)
        progress_layout = QVBoxLayout(progress_row)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        progress_title = QLabel(self.DISPLAY_LABELS["progress_bar"], progress_row)
        progress_title.setAlignment(Qt.AlignCenter)
        progress_title.setStyleSheet("font-size:20pt; font-weight:bold; color:#D0D0D0;")
        progress = QLabel("0%", progress_row)
        progress.setAlignment(Qt.AlignCenter)
        progress.setMinimumWidth(760)
        progress.setMinimumHeight(46)
        progress.setStyleSheet("font-size:12pt; font-weight:bold; color:white;")
        progress_layout.addWidget(progress_title)
        progress_layout.addWidget(progress)
        self._rows["progress_bar"] = progress_row
        self._value_labels["progress_bar"] = progress
        self._title_labels["progress_bar"] = progress_title
        self._progress_bar = progress
        center_layout.addWidget(progress_row, 0, Qt.AlignHCenter)

        for key in ["song_name", "next_song"]:
            row = QFrame(center)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)
            title_text = tr("Now Playing") if key == "song_name" else tr("Next Playing")
            title_label = QLabel(title_text, row)
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet("font-size:20pt; font-weight:bold; color:#D0D0D0;")
            text_box = QFrame(row)
            text_box.setFrameShape(QFrame.NoFrame)
            box_layout = QVBoxLayout(text_box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(0)
            value = QLabel("-", text_box)
            value.setAlignment(Qt.AlignCenter)
            value.setWordWrap(False)
            value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            value.setStyleSheet("font-size:48pt; font-weight:bold; color:#FFFFFF;")
            box_layout.addWidget(value)
            row_layout.addWidget(title_label)
            row_layout.addWidget(text_box, 1)
            self._rows[key] = row
            self._value_labels[key] = value
            self._title_labels[key] = title_label
            self._song_value_labels.append(value)
            self._song_text_boxes[key] = text_box
            center_layout.addWidget(row, 0, Qt.AlignHCenter)

        root.addWidget(center, 1)
        footer = QWidget(self)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        self._status_value = QPushButton(tr("Not Playing"), footer)
        self._status_value.setEnabled(False)
        self._status_base_style = (
            "QPushButton{font-size:16pt; font-weight:bold; color:#F5F5F5; border:1px solid #6A6A6A; border-radius:8px; padding:4px 12px; background:#0E0E0E;}"
            "QPushButton:disabled{color:#F5F5F5;}"
        )
        self._status_value.setStyleSheet(self._status_base_style)
        footer_layout.addWidget(self._status_value, 0, Qt.AlignRight)
        root.addWidget(footer, 0)
        self._footer_layout = footer_layout
        self._root_layout = center_layout
        self._datetime_timer = QTimer(self)
        self._datetime_timer.timeout.connect(self._update_datetime)
        self._datetime_timer.start(1000)
        self._update_datetime()
        self._apply_layout()
        self._apply_responsive_sizes()
        self.retranslate_ui()

    def configure_layout(self, order: List[str], visibility: Dict[str, bool]) -> None:
        valid = [key for key in order if key in self._rows]
        for key in self.DISPLAY_LABELS.keys():
            if key not in valid:
                valid.append(key)
        self._order = valid
        self._visibility = {key: bool(visibility.get(key, True)) for key in self.DISPLAY_LABELS.keys()}
        self._apply_layout()

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
            "total_time": total_time,
            "elapsed": elapsed,
            "remaining": remaining,
        }
        for key, value in values.items():
            label = self._value_labels.get(key)
            if isinstance(label, QLabel):
                label.setText(value)
        self._song_raw_values["song_name"] = str(song_name or "-")
        self._song_raw_values["next_song"] = str(next_song or "-")
        self._apply_song_text_fit()
        progress = self._value_labels.get("progress_bar")
        if isinstance(progress, QLabel):
            pct = max(0, min(100, int(progress_percent)))
            progress.setText(str(progress_text or f"{pct}%"))
            if progress_style:
                progress.setStyleSheet(progress_style)
            elif "border" not in progress.styleSheet():
                progress.setStyleSheet(
                    "QLabel{font-size:12pt;font-weight:bold;color:white;border:1px solid #3C4E58;border-radius:4px;padding:2px 8px;"
                    "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2ECC40, stop:0.5 #2ECC40, stop:0.502 #111111, stop:1 #111111);}"
                )

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            event.accept()
            return
        super().keyPressEvent(event)

    def _apply_layout(self) -> None:
        for key, row in self._rows.items():
            row.setVisible(bool(self._visibility.get(key, True)))
        times_visible = any(
            bool(self._visibility.get(key, True))
            for key in ["total_time", "elapsed", "remaining"]
        )
        self._times_row.setVisible(times_visible)

    def _update_datetime(self) -> None:
        self._datetime_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_sizes()

    def _apply_responsive_sizes(self) -> None:
        w = max(640, self.width())
        h = max(360, self.height())
        scale = max(0.65, min(3.2, min(w / 1280.0, h / 720.0)))

        margin = int(18 * scale)
        self._outer_layout.setContentsMargins(margin, margin, margin, margin)
        self._outer_layout.setSpacing(max(10, int(14 * scale)))
        self._center_layout.setSpacing(max(10, int(18 * scale)))
        self._times_layout.setSpacing(max(12, int(28 * scale)))
        self._footer_layout.setSpacing(max(6, int(10 * scale)))

        date_pt = max(12, int(20 * scale))
        title_pt = max(12, int(20 * scale))
        time_pt = max(16, int(44 * scale))
        song_pt = max(18, int(48 * scale))
        progress_pt = max(12, int(20 * scale))
        progress_height = max(24, int(46 * scale))
        progress_width = max(280, int(w * 0.72))
        radius = max(4, int(6 * scale))
        status_pt = max(10, int(16 * scale))
        song_box_width = max(320, int(w * 0.90))
        song_box_height = max(80, int(h * 0.15))

        self._datetime_label.setStyleSheet(
            f"font-size:{date_pt}pt; font-weight:bold; color:#E6E6E6;"
        )
        for label in self._title_labels.values():
            label.setStyleSheet(
                f"font-size:{title_pt}pt; font-weight:bold; color:#D0D0D0;"
            )
        for label in self._time_value_labels:
            label.setStyleSheet(
                f"font-size:{time_pt}pt; font-weight:bold; color:#FFFFFF;"
            )
        for label in self._song_value_labels:
            label.setStyleSheet(
                f"font-size:{song_pt}pt; font-weight:bold; color:#FFFFFF;"
            )
        self._song_base_pt = song_pt
        for key in ["song_name", "next_song"]:
            box = self._song_text_boxes.get(key)
            if box is not None:
                box.setFixedSize(song_box_width, song_box_height)
        self._progress_bar.setMinimumHeight(progress_height)
        self._progress_bar.setMinimumWidth(progress_width)
        self._status_value.setStyleSheet(
            "QPushButton{"
            f"font-size:{status_pt}pt; font-weight:bold; color:#F5F5F5; border:1px solid #6A6A6A; border-radius:{max(6, int(8 * scale))}px; padding:4px 12px; background:#0E0E0E;"
            "}"
            "QPushButton:disabled{color:#F5F5F5;}"
        )
        self._status_base_style = self._status_value.styleSheet()
        self._apply_song_text_fit()

    def set_playback_status(self, state: str) -> None:
        token = str(state or "").strip().lower()
        self._status_state = token
        if token == "playing":
            self._status_value.setText(f"> {tr('Playing')}")
            self._status_value.setStyleSheet(
                self._status_base_style
                + "QPushButton{background:#1E5E2D;border-color:#4FBF6A;}"
            )
        elif token == "paused":
            self._status_value.setText(f"|| {tr('Paused')}")
            self._status_value.setStyleSheet(
                self._status_base_style
                + "QPushButton{background:#5A4A12;border-color:#E0C14A;}"
            )
        else:
            self._status_value.setText(f"[] {tr('Not Playing')}")
            self._status_value.setStyleSheet(
                self._status_base_style
                + "QPushButton{background:#3C1B1B;border-color:#B56161;}"
            )

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("Stage Display"))
        for key, label in self._title_labels.items():
            if key == "song_name":
                label.setText(tr("Now Playing"))
                continue
            if key == "next_song":
                label.setText(tr("Next Playing"))
                continue
            source = self.DISPLAY_LABELS.get(key, key)
            label.setText(tr(source))
        self.set_playback_status(self._status_state)

    def _apply_song_text_fit(self) -> None:
        for key in ["song_name", "next_song"]:
            label = self._value_labels.get(key)
            if not isinstance(label, QLabel):
                continue
            text_box = self._song_text_boxes.get(key)
            if text_box is None:
                continue
            raw = str(self._song_raw_values.get(key, "-") or "-")
            label.setText(raw)
            target_width = max(120, text_box.width() - 16)
            target_height = max(40, text_box.height() - 8)
            min_pt = 8
            base_font = QFont(label.font())
            base_font.setPointSize(max(min_pt, int(self._song_base_pt)))
            label.setFont(base_font)
            fit_pt = base_font.pointSize()
            while fit_pt > min_pt:
                metrics = label.fontMetrics()
                rect = metrics.boundingRect(
                    0,
                    0,
                    target_width,
                    target_height,
                    int(Qt.AlignCenter | Qt.TextWordWrap),
                    raw,
                )
                if rect.width() <= target_width and rect.height() <= target_height:
                    break
                fit_pt -= 1
                next_font = QFont(base_font)
                next_font.setPointSize(fit_pt)
                label.setFont(next_font)
            label.setWordWrap(True)


class NoAudioPlayer(QObject):
    StoppedState = 0
    PlayingState = 1
    PausedState = 2

    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._state = self.StoppedState
        self._duration_ms = 0
        self._position_ms = 0
        self._volume = 100

    def setNotifyInterval(self, interval_ms: int) -> None:
        _ = interval_ms

    def setMedia(self, file_path: str, dsp_config: Optional[DSPConfig] = None) -> None:
        _ = (file_path, dsp_config)
        self._duration_ms = 0
        self._position_ms = 0
        self.durationChanged.emit(0)
        self.positionChanged.emit(0)

    def setDSPConfig(self, dsp_config: DSPConfig) -> None:
        _ = dsp_config

    def play(self) -> None:
        self._state = self.PlayingState
        self.stateChanged.emit(self._state)

    def pause(self) -> None:
        self._state = self.PausedState
        self.stateChanged.emit(self._state)

    def stop(self) -> None:
        self._state = self.StoppedState
        self._position_ms = 0
        self.stateChanged.emit(self._state)
        self.positionChanged.emit(0)

    def state(self) -> int:
        return self._state

    def setPosition(self, position_ms: int) -> None:
        self._position_ms = max(0, int(position_ms))
        self.positionChanged.emit(self._position_ms)

    def position(self) -> int:
        return self._position_ms

    def duration(self) -> int:
        return self._duration_ms

    def setVolume(self, volume: int) -> None:
        self._volume = max(0, min(100, int(volume)))

    def volume(self) -> int:
        return self._volume

    def meterLevels(self) -> Tuple[float, float]:
        return (0.0, 0.0)

    def waveformPeaks(self, sample_count: int = 1024) -> List[float]:
        _ = sample_count
        return []


class TransportProgressDisplay(QLabel):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._display_mode = "progress_bar"
        self._progress_ratio = 0.0
        self._cue_in_ratio = 0.0
        self._cue_out_ratio = 1.0
        self._audio_file_mode = False
        self._waveform: List[float] = []

    def set_display_mode(self, mode: str) -> None:
        token = str(mode or "").strip().lower()
        if token not in {"progress_bar", "waveform"}:
            token = "progress_bar"
        if token == self._display_mode:
            return
        self._display_mode = token
        self.update()

    def display_mode(self) -> str:
        return self._display_mode

    def set_waveform(self, peaks: List[float]) -> None:
        cleaned: List[float] = []
        for value in list(peaks or []):
            try:
                amp = float(value)
            except Exception:
                amp = 0.0
            cleaned.append(max(0.0, min(1.0, amp)))
        self._waveform = cleaned
        if self._display_mode == "waveform":
            self.update()

    def set_transport_state(
        self,
        progress_ratio: float,
        cue_in_ratio: float,
        cue_out_ratio: float,
        audio_file_mode: bool,
    ) -> None:
        self._progress_ratio = max(0.0, min(1.0, float(progress_ratio)))
        in_ratio = max(0.0, min(1.0, float(cue_in_ratio)))
        out_ratio = max(0.0, min(1.0, float(cue_out_ratio)))
        if out_ratio < in_ratio:
            out_ratio = in_ratio
        self._cue_in_ratio = in_ratio
        self._cue_out_ratio = out_ratio
        self._audio_file_mode = bool(audio_file_mode)
        if self._display_mode == "waveform":
            self.update()

    def paintEvent(self, event) -> None:
        if self._display_mode != "waveform":
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        w = max(1, self.width())
        h = max(1, self.height())
        center = h // 2
        max_half = max(1, (h // 2) - 3)

        playable_bg = QColor("#1A222A")
        unplayable_bg = QColor("#11161B")
        played_bg = QColor("#1B3724")
        played_wave = QColor("#2ECC40")
        playable_wave = QColor("#B9D7EA")
        unplayable_wave = QColor("#5E7586")
        border = QColor("#3C4E58")

        in_x = int(round(self._cue_in_ratio * (w - 1)))
        out_x = int(round(self._cue_out_ratio * (w - 1)))
        play_x = int(round(self._progress_ratio * (w - 1)))
        if out_x < in_x:
            out_x = in_x

        painter.fillRect(0, 0, w, h, unplayable_bg if self._audio_file_mode else playable_bg)
        if self._audio_file_mode:
            painter.fillRect(in_x, 0, max(1, out_x - in_x + 1), h, playable_bg)

        if self._audio_file_mode:
            played_left = max(in_x, 0)
            played_right = min(out_x, play_x)
        else:
            played_left = 0
            played_right = max(0, play_x)
        if played_right >= played_left:
            painter.fillRect(played_left, 0, max(1, played_right - played_left + 1), h, played_bg)

        wave = self._waveform
        wave_count = len(wave)
        sample_start_ratio = 0.0
        sample_end_ratio = 1.0
        if (not self._audio_file_mode) and (self._cue_out_ratio > self._cue_in_ratio):
            sample_start_ratio = self._cue_in_ratio
            sample_end_ratio = self._cue_out_ratio
        for x in range(w):
            if wave_count > 0:
                x_ratio = x / float(max(1, w - 1))
                sample_ratio = sample_start_ratio + ((sample_end_ratio - sample_start_ratio) * x_ratio)
                idx = int(round(sample_ratio * float(max(0, wave_count - 1))))
                idx = max(0, min(wave_count - 1, idx))
                amp = wave[idx]
            else:
                amp = 0.0
            half = max(1, int(round(amp * max_half)))
            if self._audio_file_mode and (x < in_x or x > out_x):
                wave_color = unplayable_wave
            elif x <= play_x:
                wave_color = played_wave
            else:
                wave_color = playable_wave
            painter.setPen(wave_color)
            painter.drawLine(x, center - half, x, center + half)

        painter.setPen(QColor("#FFD54F"))
        painter.drawLine(play_x, 0, play_x, h - 1)
        painter.setPen(border)
        painter.drawRect(0, 0, w - 1, h - 1)
        text = self.text()
        if text:
            text_rect = self.rect().adjusted(6, 2, -6, -2)
            metrics = painter.fontMetrics()
            width = min(text_rect.width(), metrics.horizontalAdvance(text) + 14)
            height = min(text_rect.height(), metrics.height() + 8)
            bubble = QRect(
                text_rect.center().x() - (width // 2),
                text_rect.center().y() - (height // 2),
                max(1, width),
                max(1, height),
            )
            painter.fillRect(bubble, QColor(0, 0, 0, 150))

            painter.setPen(QColor(0, 0, 0, 220))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                painter.drawText(text_rect.translated(dx, dy), int(self.alignment()), text)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(text_rect, int(self.alignment()), text)
        painter.end()


class MainThreadExecutor(QObject):
    _execute = pyqtSignal(object, object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._execute.connect(self._on_execute, Qt.QueuedConnection)

    @pyqtSlot(object, object)
    def _on_execute(self, fn, result_queue) -> None:
        try:
            result_queue.put((True, fn()))
        except Exception as exc:
            result_queue.put((False, exc))

    def call(self, fn, timeout: float = 8.0):
        if QThread.currentThread() == self.thread():
            return fn()
        result_queue: "queue.Queue[Tuple[bool, object]]" = queue.Queue(maxsize=1)
        self._execute.emit(fn, result_queue)
        ok, value = result_queue.get(timeout=timeout)
        if ok:
            return value
        raise value


class LockScreenOverlay(QWidget):
    unlocked = pyqtSignal()

    def __init__(self, host: "MainWindow") -> None:
        super().__init__(host)
        self._host = host
        self._mode = "click_3_random_points"
        self._radius = 40
        self._targets: List[Tuple[int, int]] = []
        self._completed: set[int] = set()
        self._fixed_button_rect = QRect()
        self._slide_track_rect = QRect()
        self._slide_handle_x = 0
        self._slide_dragging = False
        self._slide_drag_offset = 0
        self.hide()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def activate_lock(self) -> None:
        self._mode = str(getattr(self._host, "lock_unlock_method", "click_3_random_points")).strip().lower()
        self._completed.clear()
        self.sync_geometry(rebuild_targets=True)
        self.show()
        self.raise_()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self.update()

    def deactivate_lock(self) -> None:
        self.hide()
        self._completed.clear()
        self._slide_dragging = False

    def reset_unlock_progress(self) -> None:
        self._completed.clear()
        self._slide_dragging = False
        if self._mode == "slide_to_unlock" and (not self._slide_track_rect.isNull()):
            self._slide_handle_x = self._slide_track_rect.left() + 4
        self.update()

    def sync_geometry(self, rebuild_targets: bool = False) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setGeometry(parent.rect())
        if rebuild_targets:
            self._rebuild_unlock_geometry()

    def _rebuild_unlock_geometry(self) -> None:
        if self._mode == "click_one_button":
            self._rebuild_fixed_button()
        elif self._mode == "slide_to_unlock":
            self._rebuild_slide_unlock()
        else:
            self._rebuild_targets()

    def _rebuild_targets(self) -> None:
        width = max(360, self.width())
        height = max(260, self.height())
        self._radius = max(28, min(56, int(min(width, height) * 0.06)))
        margin = self._radius + 28
        min_x = margin
        max_x = max(min_x, width - margin)
        min_y = max(margin + 34, int(height * 0.22))
        max_y = max(min_y, height - margin)
        min_dist_sq = max(1, int((self._radius * 3.1) ** 2))
        targets: List[Tuple[int, int]] = []
        attempts = 0
        while len(targets) < 3 and attempts < 300:
            attempts += 1
            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)
            if all(((x - px) ** 2) + ((y - py) ** 2) >= min_dist_sq for px, py in targets):
                targets.append((x, y))
        fallback = [
            (int(width * 0.24), int(height * 0.42)),
            (int(width * 0.52), int(height * 0.70)),
            (int(width * 0.78), int(height * 0.48)),
        ]
        for point in fallback:
            if len(targets) >= 3:
                break
            targets.append(point)
        self._targets = targets[:3]
        self._completed.clear()
        self.update()

    def _rebuild_fixed_button(self) -> None:
        width = max(360, self.width())
        height = max(260, self.height())
        button_w = min(280, max(180, int(width * 0.24)))
        button_h = 60
        self._fixed_button_rect = QRect(
            int((width - button_w) / 2),
            int(height * 0.66),
            button_w,
            button_h,
        )
        self.update()

    def _rebuild_slide_unlock(self) -> None:
        width = max(360, self.width())
        height = max(260, self.height())
        track_w = min(420, max(220, int(width * 0.4)))
        track_h = 56
        self._slide_track_rect = QRect(
            int((width - track_w) / 2),
            int(height * 0.66),
            track_w,
            track_h,
        )
        self._slide_handle_x = self._slide_track_rect.left() + 4
        self._slide_dragging = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            event.accept()
            return
        pos = event.pos()
        if self._mode == "click_one_button":
            if self._fixed_button_rect.contains(pos):
                self.unlocked.emit()
            event.accept()
            return
        if self._mode == "slide_to_unlock":
            handle = self._slide_handle_rect()
            if handle.contains(pos):
                self._slide_dragging = True
                self._slide_drag_offset = pos.x() - handle.left()
            event.accept()
            return
        for index, (center_x, center_y) in enumerate(self._targets):
            if index in self._completed:
                continue
            if ((pos.x() - center_x) ** 2) + ((pos.y() - center_y) ** 2) <= (self._radius ** 2):
                self._completed.add(index)
                if len(self._completed) >= len(self._targets):
                    self.unlocked.emit()
                self.update()
                event.accept()
                return
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._mode != "slide_to_unlock" or (not self._slide_dragging):
            event.accept()
            return
        handle = self._slide_handle_rect()
        min_x = self._slide_track_rect.left() + 4
        max_x = self._slide_track_rect.right() - handle.width() - 3
        next_x = max(min_x, min(max_x, event.pos().x() - self._slide_drag_offset))
        self._slide_handle_x = next_x
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._mode != "slide_to_unlock":
            event.accept()
            return
        if self._slide_dragging:
            handle = self._slide_handle_rect()
            threshold = self._slide_track_rect.right() - handle.width() - 12
            if self._slide_handle_x >= threshold:
                self._slide_dragging = False
                self.unlocked.emit()
                event.accept()
                return
            self._slide_dragging = False
            self._slide_handle_x = self._slide_track_rect.left() + 4
            self.update()
        event.accept()

    def keyPressEvent(self, event) -> None:
        self._host._handle_lock_overlay_key_press(event)
        event.accept()

    def keyReleaseEvent(self, event) -> None:
        self._host._handle_lock_overlay_key_release(event)
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 118))

        automation_locked = bool(getattr(self._host, "_automation_locked", False))
        panel_width = min(max(320, self.width() - 80), 620)
        panel_height = 120 if automation_locked else 84
        panel_x = int((self.width() - panel_width) / 2)
        panel_y = 28
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(14, 18, 24, 190))
        painter.drawRoundedRect(panel_x, panel_y, panel_width, panel_height, 12, 12)

        painter.setPen(QColor("#F4F7FB"))
        title_font = QFont(self.font())
        title_font.setPointSize(14)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(panel_x, panel_y + 16, panel_width, 28, Qt.AlignHCenter | Qt.AlignVCenter, tr("Screen Locked"))

        body_font = QFont(self.font())
        body_font.setPointSize(10)
        painter.setFont(body_font)
        painter.setPen(QColor("#D6DBE3"))
        helper_text = tr("Click all 3 targets to unlock.")
        if self._mode == "click_one_button":
            helper_text = tr("Click the unlock button to continue.")
        elif self._mode == "slide_to_unlock":
            helper_text = tr("Slide all the way to unlock.")
        painter.drawText(
            panel_x + 18,
            panel_y + 42,
            panel_width - 36,
            34,
            Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextWordWrap,
            helper_text,
        )
        if automation_locked:
            warning_rect = QRect(panel_x + 18, panel_y + 76, panel_width - 36, 32)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#C13F29"))
            painter.drawRoundedRect(warning_rect, 8, 8)
            painter.setPen(QColor("#FFF5F3"))
            painter.drawText(
                warning_rect.adjusted(10, 0, -10, 0),
                Qt.AlignCenter | Qt.TextWordWrap,
                tr("Automation lock is active. pySSP is expected to be controlled remotely. Unlock only for troubleshooting when you are sure."),
            )

        label_font = QFont(self.font())
        label_font.setPointSize(11)
        label_font.setBold(True)
        if self._mode == "click_one_button":
            painter.setPen(QPen(QColor("#F4F7FB"), 2))
            painter.setBrush(QColor(255, 255, 255, 54))
            painter.drawRoundedRect(self._fixed_button_rect, 10, 10)
            painter.setFont(label_font)
            painter.setPen(QColor("#F4F7FB"))
            painter.drawText(self._fixed_button_rect, Qt.AlignCenter, tr("Unlock"))
        elif self._mode == "slide_to_unlock":
            painter.setPen(QPen(QColor("#F4F7FB"), 2))
            painter.setBrush(QColor(255, 255, 255, 34))
            painter.drawRoundedRect(self._slide_track_rect, 18, 18)
            painter.setFont(label_font)
            painter.setPen(QColor("#D6DBE3"))
            painter.drawText(self._slide_track_rect, Qt.AlignCenter, tr("Slide to Unlock"))
            handle = self._slide_handle_rect()
            painter.setPen(QPen(QColor("#52D080"), 2))
            painter.setBrush(QColor("#52D080"))
            painter.drawRoundedRect(handle, 18, 18)
            painter.setPen(QColor("#0F1115"))
            painter.drawText(handle, Qt.AlignCenter, ">")
        else:
            for index, (center_x, center_y) in enumerate(self._targets):
                hit = index in self._completed
                fill = QColor(82, 208, 128, 165) if hit else QColor(255, 255, 255, 54)
                border = QColor("#52D080") if hit else QColor("#F4F7FB")
                painter.setPen(QPen(border, 2))
                painter.setBrush(fill)
                painter.drawEllipse(center_x - self._radius, center_y - self._radius, self._radius * 2, self._radius * 2)
                painter.setFont(label_font)
                painter.setPen(QColor("#0F1115") if hit else QColor("#F4F7FB"))
                painter.drawText(
                    center_x - self._radius,
                    center_y - self._radius,
                    self._radius * 2,
                    self._radius * 2,
                    Qt.AlignCenter,
                    str(index + 1),
                )
        painter.end()
        super().paintEvent(event)

    def _slide_handle_rect(self) -> QRect:
        if self._slide_track_rect.isNull():
            return QRect()
        handle_w = 72
        inset = 4
        return QRect(
            self._slide_handle_x,
            self._slide_track_rect.top() + inset,
            handle_w,
            self._slide_track_rect.height() - (inset * 2),
        )


