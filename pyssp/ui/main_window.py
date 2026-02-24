from __future__ import annotations

import os
import sys
import time
import random
import queue
import socket
import ipaddress
import subprocess
import re
import json
import shutil
import configparser
from datetime import datetime
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QEvent, QRect, QSize, QTimer, Qt, QMimeData, QObject, pyqtSignal, pyqtSlot, QThread, QUrl
from PyQt5.QtGui import QColor, QTextDocument, QDrag, QKeySequence, QPainter, QFont, QDesktopServices, QPixmap
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QInputDialog,
    QTabWidget,
    QSpinBox,
    QSlider,
    QShortcut,
    QStyle,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import (
    ExternalMediaPlayer,
    configure_audio_preload_cache_policy,
    enforce_audio_preload_limits,
    get_audio_preload_capacity_bytes,
    get_audio_preload_runtime_status,
    get_preload_memory_limits_mb,
    get_media_ssp_units,
    is_audio_preloaded,
    list_output_devices,
    request_audio_preload,
    set_audio_preload_paused,
    set_output_device,
    shutdown_audio_preload,
)
from pyssp.dsp import DSPConfig, normalize_config
from pyssp.set_loader import load_set_file, parse_delphi_color, parse_time_string_to_ms
from pyssp.settings_store import AppSettings, get_settings_path, load_settings, save_settings
from pyssp.i18n import apply_application_font, localize_widget_tree, normalize_language, set_current_language, tr
from pyssp.midi_control import (
    MidiInputRouter,
    list_midi_input_devices,
    midi_input_name_selector,
    normalize_midi_binding,
    split_midi_binding,
)
from pyssp.timecode import (
    LtcAudioOutput,
    MIDI_OUTPUT_DEVICE_NONE,
    MtcMidiOutput,
    MTC_IDLE_ALLOW_DARK,
    MTC_IDLE_KEEP_STREAM,
    TIMECODE_MODE_FOLLOW,
    TIMECODE_MODE_FOLLOW_FREEZE,
    TIMECODE_MODE_SYSTEM,
    TIMECODE_MODE_ZERO,
    frame_to_timecode_string,
    list_midi_output_devices,
    ms_to_timecode_string,
    nominal_fps,
)
from pyssp.ui.dsp_window import DSPWindow
from pyssp.ui.cue_point_dialog import CuePointDialog
from pyssp.ui.edit_sound_button_dialog import EditSoundButtonDialog
from pyssp.ui.options_dialog import OptionsDialog
from pyssp.ui.stage_display import (
    StageDisplayWindow as GadgetStageDisplayWindow,
    gadgets_to_legacy_layout_visibility,
    normalize_stage_display_gadgets,
)
from pyssp.ui.search_window import SearchWindow
from pyssp.ui.tips_window import TipsWindow
from pyssp.web_remote import WebRemoteServer
from pyssp.version import get_app_title_base, get_display_version

GROUPS = list("ABCDEFGHIJ")
PAGE_COUNT = 18
SLOTS_PER_PAGE = 48
GRID_ROWS = 6
GRID_COLS = 8

COLORS = {
    "empty": "#0B868A",
    "assigned": "#B0B0B0",
    "highlighted": "#A6D8FF",
    "playing": "#66FF33",
    "played": "#FF3B30",
    "missing": "#7B3FB3",
    "locked": "#F2D74A",
    "marker": "#111111",
    "copied": "#2E65FF",
    "cue_indicator": "#61D6FF",
    "volume_indicator": "#FFD45A",
    "midi_indicator": "#FF9E4A",
}

HOTKEY_DEFAULTS: Dict[str, tuple[str, str]] = {
    "new_set": ("Ctrl+N", ""),
    "open_set": ("Ctrl+O", ""),
    "save_set": ("Ctrl+S", ""),
    "save_set_as": ("Ctrl+Shift+S", ""),
    "search": ("Ctrl+F", ""),
    "options": ("", ""),
    "play_selected_pause": ("", ""),
    "play_selected": ("", ""),
    "pause_toggle": ("P", ""),
    "stop_playback": ("Space", "Return"),
    "talk": ("Shift", ""),
    "next_group": ("", ""),
    "prev_group": ("", ""),
    "next_page": ("", ""),
    "prev_page": ("", ""),
    "next_sound_button": ("", ""),
    "prev_sound_button": ("", ""),
    "multi_play": ("", ""),
    "go_to_playing": ("", ""),
    "loop": ("", ""),
    "next": ("", ""),
    "rapid_fire": ("", ""),
    "shuffle": ("", ""),
    "reset_page": ("", ""),
    "play_list": ("", ""),
    "fade_in": ("", ""),
    "cross_fade": ("", ""),
    "fade_out": ("", ""),
    "mute": ("", ""),
    "volume_up": ("", ""),
    "volume_down": ("", ""),
}

MIDI_HOTKEY_DEFAULTS: Dict[str, tuple[str, str]] = {key: ("", "") for key in HOTKEY_DEFAULTS.keys()}

SYSTEM_HOTKEY_ORDER_DEFAULT: List[str] = [
    "new_set",
    "open_set",
    "save_set",
    "save_set_as",
    "search",
    "options",
    "play_selected_pause",
    "play_selected",
    "pause_toggle",
    "stop_playback",
    "talk",
    "next_group",
    "prev_group",
    "next_page",
    "prev_page",
    "next_sound_button",
    "prev_sound_button",
    "multi_play",
    "go_to_playing",
    "loop",
    "next",
    "rapid_fire",
    "shuffle",
    "reset_page",
    "play_list",
    "fade_in",
    "cross_fade",
    "fade_out",
    "mute",
    "volume_up",
    "volume_down",
]


@dataclass
class SoundButtonData:
    file_path: str = ""
    title: str = ""
    notes: str = ""
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
    sound_hotkey: str = ""
    sound_midi_hotkey: str = ""

    @property
    def assigned(self) -> bool:
        return bool(self.file_path)

    @property
    def missing(self) -> bool:
        return self.assigned and not os.path.exists(self.file_path)

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
        suffix = f" {' '.join(parts)}" if parts else ""
        return f"{elide_text(self.title, 26)}\n{format_time(self.duration_ms)}{suffix}"


class SoundButton(QPushButton):
    def __init__(self, slot_index: int, host: "MainWindow"):
        super().__init__("")
        self._host = host
        self.slot_index = slot_index
        self._drag_start_pos = None
        self._ram_loaded = False
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
        if self._host._can_accept_sound_button_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._host._can_accept_sound_button_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:
        if not self._host._can_accept_sound_button_drop(event.mimeData()):
            event.ignore()
            return
        if self._host._handle_sound_button_drop(self.slot_index, event.mimeData()):
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

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
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


class GroupButton(QPushButton):
    def __init__(self, group: str, host: "MainWindow"):
        super().__init__(group)
        self.group = group
        self._host = host
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if self._host._can_accept_sound_button_drop(event.mimeData()):
            self._host._handle_drag_over_group(self.group)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._host._can_accept_sound_button_drop(event.mimeData()):
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
    def __init__(self, title: str, logo_path: str, parent=None) -> None:
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
        for x in range(w):
            if wave_count > 0:
                idx = int((x / float(max(1, w - 1))) * float(max(0, wave_count - 1)))
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._suspend_settings_save = True
        self.app_version_text = get_display_version()
        self.app_title_base = get_app_title_base()
        self.setWindowTitle(self.app_title_base)
        self.resize(1360, 900)
        self.settings: AppSettings = load_settings()
        self.ui_language = normalize_language(getattr(self.settings, "ui_language", "en"))
        set_current_language(self.ui_language)

        self.current_group = "A"
        self.current_page = 0
        self.current_playing: Optional[Tuple[str, int, int]] = None
        self.current_playlist_start: Optional[int] = None
        self._auto_transition_track: Optional[Tuple[str, int, int]] = None
        self._auto_transition_done = False
        self._pending_start_request: Optional[Tuple[str, int, int]] = None
        self._pending_start_token = 0
        self.current_duration_ms = 0
        self._main_progress_waveform: List[float] = []
        self._main_waveform_request_token = 0
        self.loop_enabled = False
        self._manual_stop_requested = False
        self.talk_active = False
        self._fade_jobs: List[dict] = []
        self._fade_flash_on = False
        self._last_fade_flash_toggle = 0.0
        self._stop_fade_armed = False
        self.active_group_color = self.settings.active_group_color
        self.inactive_group_color = self.settings.inactive_group_color
        self.title_char_limit = self.settings.title_char_limit
        self.show_file_notifications = self.settings.show_file_notifications
        self.fade_in_sec = self.settings.fade_in_sec
        self.cross_fade_sec = self.settings.cross_fade_sec
        self.fade_out_sec = self.settings.fade_out_sec
        self.fade_on_quick_action_hotkey = bool(self.settings.fade_on_quick_action_hotkey)
        self.fade_on_sound_button_hotkey = bool(self.settings.fade_on_sound_button_hotkey)
        self.fade_on_pause = bool(self.settings.fade_on_pause)
        self.fade_on_resume = bool(self.settings.fade_on_resume)
        self.fade_on_stop = bool(self.settings.fade_on_stop)
        self.fade_out_when_done_playing = bool(self.settings.fade_out_when_done_playing)
        self.fade_out_end_lead_sec = max(0.0, float(self.settings.fade_out_end_lead_sec))
        self.talk_volume_level = self.settings.talk_volume_level
        self.talk_fade_sec = self.settings.talk_fade_sec
        self.talk_volume_mode = (
            self.settings.talk_volume_mode
            if self.settings.talk_volume_mode in {"percent_of_master", "lower_only", "set_exact"}
            else "percent_of_master"
        )
        self.talk_blink_button = self.settings.talk_blink_button
        self.log_file_enabled = self.settings.log_file_enabled
        self.reset_all_on_startup = self.settings.reset_all_on_startup
        self.click_playing_action = self.settings.click_playing_action
        self.search_double_click_action = self.settings.search_double_click_action
        self.set_file_encoding = self.settings.set_file_encoding or "utf8"
        if self.set_file_encoding not in {"utf8", "gbk"}:
            self.set_file_encoding = "utf8"
        self.tips_open_on_startup = bool(getattr(self.settings, "tips_open_on_startup", True))
        self.audio_output_device = self.settings.audio_output_device
        _preload_total_mb, _preload_reserved_mb, _preload_cap_mb = get_preload_memory_limits_mb()
        self.preload_audio_enabled = bool(getattr(self.settings, "preload_audio_enabled", False))
        self.preload_current_page_audio = bool(getattr(self.settings, "preload_current_page_audio", True))
        self.preload_audio_memory_limit_mb = max(
            64,
            min(int(_preload_cap_mb), int(getattr(self.settings, "preload_audio_memory_limit_mb", 512))),
        )
        self.preload_memory_pressure_enabled = bool(
            getattr(self.settings, "preload_memory_pressure_enabled", True)
        )
        self.preload_pause_on_playback = bool(getattr(self.settings, "preload_pause_on_playback", False))
        self._preload_runtime_paused = False
        configure_audio_preload_cache_policy(
            self.preload_audio_enabled,
            self.preload_audio_memory_limit_mb,
            self.preload_memory_pressure_enabled,
        )
        self.max_multi_play_songs = self.settings.max_multi_play_songs
        self.multi_play_limit_action = self.settings.multi_play_limit_action
        self.playlist_play_mode = (
            self.settings.playlist_play_mode
            if self.settings.playlist_play_mode in {"unplayed_only", "any_available"}
            else "unplayed_only"
        )
        self.rapid_fire_play_mode = (
            self.settings.rapid_fire_play_mode
            if self.settings.rapid_fire_play_mode in {"unplayed_only", "any_available"}
            else "unplayed_only"
        )
        self.next_play_mode = (
            self.settings.next_play_mode
            if self.settings.next_play_mode in {"unplayed_only", "any_available"}
            else "unplayed_only"
        )
        self.playlist_loop_mode = (
            self.settings.playlist_loop_mode
            if self.settings.playlist_loop_mode in {"loop_list", "loop_single"}
            else "loop_list"
        )
        self.candidate_error_action = (
            self.settings.candidate_error_action
            if self.settings.candidate_error_action in {"stop_playback", "keep_playing"}
            else "stop_playback"
        )
        self.web_remote_enabled = self.settings.web_remote_enabled
        self.web_remote_host = "0.0.0.0"
        self.web_remote_port = max(1, min(65535, int(self.settings.web_remote_port or 5050)))
        self._local_ip_cache = "127.0.0.1"
        self._local_ip_cache_at = 0.0
        self.timecode_audio_output_device = self.settings.timecode_audio_output_device or "none"
        self.timecode_midi_output_device = self.settings.timecode_midi_output_device or MIDI_OUTPUT_DEVICE_NONE
        self.timecode_mode = self.settings.timecode_mode or TIMECODE_MODE_FOLLOW
        if self.timecode_mode not in {
            TIMECODE_MODE_ZERO,
            TIMECODE_MODE_FOLLOW,
            TIMECODE_MODE_SYSTEM,
            TIMECODE_MODE_FOLLOW_FREEZE,
        }:
            self.timecode_mode = TIMECODE_MODE_FOLLOW
        self.timecode_fps = max(1.0, float(self.settings.timecode_fps or 30.0))
        self.timecode_mtc_fps = max(1.0, float(self.settings.timecode_mtc_fps or 30.0))
        self.timecode_mtc_idle_behavior = self.settings.timecode_mtc_idle_behavior or MTC_IDLE_KEEP_STREAM
        if self.timecode_mtc_idle_behavior not in {MTC_IDLE_KEEP_STREAM, MTC_IDLE_ALLOW_DARK}:
            self.timecode_mtc_idle_behavior = MTC_IDLE_KEEP_STREAM
        self.timecode_sample_rate = int(self.settings.timecode_sample_rate or 48000)
        if self.timecode_sample_rate not in {44100, 48000, 96000}:
            self.timecode_sample_rate = 48000
        self.timecode_bit_depth = int(self.settings.timecode_bit_depth or 16)
        if self.timecode_bit_depth not in {8, 16, 32}:
            self.timecode_bit_depth = 16
        self.show_timecode_panel = bool(self.settings.show_timecode_panel)
        self.timecode_timeline_mode = (
            self.settings.timecode_timeline_mode
            if self.settings.timecode_timeline_mode in {"cue_region", "audio_file"}
            else self.settings.main_transport_timeline_mode
        )
        if self.timecode_timeline_mode not in {"cue_region", "audio_file"}:
            self.timecode_timeline_mode = "cue_region"
        self.main_transport_timeline_mode = (
            self.settings.main_transport_timeline_mode
            if self.settings.main_transport_timeline_mode in {"cue_region", "audio_file"}
            else "cue_region"
        )
        self.main_progress_display_mode = str(getattr(self.settings, "main_progress_display_mode", "progress_bar")).strip().lower()
        if self.main_progress_display_mode not in {"progress_bar", "waveform"}:
            self.main_progress_display_mode = "progress_bar"
        self.main_progress_show_text = bool(getattr(self.settings, "main_progress_show_text", True))
        self._timecode_follow_frozen_ms = 0
        if self.timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE:
            self._timecode_follow_frozen_ms = 0
        self.main_jog_outside_cue_action = (
            self.settings.main_jog_outside_cue_action
            if self.settings.main_jog_outside_cue_action
            in {"stop_immediately", "ignore_cue", "next_cue_or_stop", "stop_cue_or_end"}
            else "stop_immediately"
        )
        self.stage_display_layout = self._normalize_stage_display_layout(
            list(getattr(self.settings, "stage_display_layout", []))
        )
        self.stage_display_visibility = self._normalize_stage_display_visibility(
            {
                "current_time": bool(getattr(self.settings, "stage_display_show_current_time", True)),
                "alert": bool(getattr(self.settings, "stage_display_show_alert", False)),
                "total_time": bool(getattr(self.settings, "stage_display_show_total_time", True)),
                "elapsed": bool(getattr(self.settings, "stage_display_show_elapsed", True)),
                "remaining": bool(getattr(self.settings, "stage_display_show_remaining", True)),
                "progress_bar": bool(getattr(self.settings, "stage_display_show_progress_bar", True)),
                "song_name": bool(getattr(self.settings, "stage_display_show_song_name", True)),
                "next_song": bool(getattr(self.settings, "stage_display_show_next_song", True)),
            }
        )
        self.stage_display_gadgets = normalize_stage_display_gadgets(
            getattr(self.settings, "stage_display_gadgets", {}),
            legacy_layout=self.stage_display_layout,
            legacy_visibility=self.stage_display_visibility,
        )
        self.stage_display_layout, self.stage_display_visibility = gadgets_to_legacy_layout_visibility(
            self.stage_display_gadgets
        )
        source = str(getattr(self.settings, "stage_display_text_source", "caption")).strip().lower()
        self.stage_display_text_source = source if source in {"caption", "filename", "note"} else "caption"
        self.state_colors = {
            "empty": self.settings.color_empty,
            "assigned": self.settings.color_unplayed,
            "highlighted": self.settings.color_highlight,
            "playing": self.settings.color_playing,
            "played": self.settings.color_played,
            "missing": self.settings.color_error,
            "locked": self.settings.color_lock,
            "marker": self.settings.color_place_marker,
            "copied": self.settings.color_copied_to_cue,
            "cue_indicator": self.settings.color_cue_indicator,
            "volume_indicator": self.settings.color_volume_indicator,
            "midi_indicator": getattr(self.settings, "color_midi_indicator", "#FF9E4A"),
        }
        self.sound_button_text_color = self.settings.sound_button_text_color
        self.hotkeys: Dict[str, tuple[str, str]] = {
            "new_set": (self.settings.hotkey_new_set_1, self.settings.hotkey_new_set_2),
            "open_set": (self.settings.hotkey_open_set_1, self.settings.hotkey_open_set_2),
            "save_set": (self.settings.hotkey_save_set_1, self.settings.hotkey_save_set_2),
            "save_set_as": (self.settings.hotkey_save_set_as_1, self.settings.hotkey_save_set_as_2),
            "search": (self.settings.hotkey_search_1, self.settings.hotkey_search_2),
            "options": (self.settings.hotkey_options_1, self.settings.hotkey_options_2),
            "play_selected_pause": (
                self.settings.hotkey_play_selected_pause_1,
                self.settings.hotkey_play_selected_pause_2,
            ),
            "play_selected": (self.settings.hotkey_play_selected_1, self.settings.hotkey_play_selected_2),
            "pause_toggle": (self.settings.hotkey_pause_toggle_1, self.settings.hotkey_pause_toggle_2),
            "stop_playback": (self.settings.hotkey_stop_playback_1, self.settings.hotkey_stop_playback_2),
            "talk": (self.settings.hotkey_talk_1, self.settings.hotkey_talk_2),
            "next_group": (self.settings.hotkey_next_group_1, self.settings.hotkey_next_group_2),
            "prev_group": (self.settings.hotkey_prev_group_1, self.settings.hotkey_prev_group_2),
            "next_page": (self.settings.hotkey_next_page_1, self.settings.hotkey_next_page_2),
            "prev_page": (self.settings.hotkey_prev_page_1, self.settings.hotkey_prev_page_2),
            "next_sound_button": (self.settings.hotkey_next_sound_button_1, self.settings.hotkey_next_sound_button_2),
            "prev_sound_button": (self.settings.hotkey_prev_sound_button_1, self.settings.hotkey_prev_sound_button_2),
            "multi_play": (self.settings.hotkey_multi_play_1, self.settings.hotkey_multi_play_2),
            "go_to_playing": (self.settings.hotkey_go_to_playing_1, self.settings.hotkey_go_to_playing_2),
            "loop": (self.settings.hotkey_loop_1, self.settings.hotkey_loop_2),
            "next": (self.settings.hotkey_next_1, self.settings.hotkey_next_2),
            "rapid_fire": (self.settings.hotkey_rapid_fire_1, self.settings.hotkey_rapid_fire_2),
            "shuffle": (self.settings.hotkey_shuffle_1, self.settings.hotkey_shuffle_2),
            "reset_page": (self.settings.hotkey_reset_page_1, self.settings.hotkey_reset_page_2),
            "play_list": (self.settings.hotkey_play_list_1, self.settings.hotkey_play_list_2),
            "fade_in": (self.settings.hotkey_fade_in_1, self.settings.hotkey_fade_in_2),
            "cross_fade": (self.settings.hotkey_cross_fade_1, self.settings.hotkey_cross_fade_2),
            "fade_out": (self.settings.hotkey_fade_out_1, self.settings.hotkey_fade_out_2),
            "mute": (self.settings.hotkey_mute_1, self.settings.hotkey_mute_2),
            "volume_up": (self.settings.hotkey_volume_up_1, self.settings.hotkey_volume_up_2),
            "volume_down": (self.settings.hotkey_volume_down_1, self.settings.hotkey_volume_down_2),
        }
        self.quick_action_enabled = bool(self.settings.quick_action_enabled)
        self.quick_action_keys = list(self.settings.quick_action_keys[:48])
        if len(self.quick_action_keys) < 48:
            self.quick_action_keys.extend(["" for _ in range(48 - len(self.quick_action_keys))])
        self.sound_button_hotkey_enabled = bool(self.settings.sound_button_hotkey_enabled)
        self.sound_button_hotkey_priority = (
            self.settings.sound_button_hotkey_priority
            if self.settings.sound_button_hotkey_priority in {"system_first", "sound_button_first"}
            else "system_first"
        )
        self.sound_button_hotkey_go_to_playing = bool(self.settings.sound_button_hotkey_go_to_playing)
        self.midi_input_device_ids: List[str] = [str(v).strip() for v in self.settings.midi_input_device_ids if str(v).strip()]
        self.midi_input_device_ids = self._normalize_midi_input_selectors(self.midi_input_device_ids)
        self.midi_hotkeys: Dict[str, tuple[str, str]] = {
            "new_set": (self.settings.midi_hotkey_new_set_1, self.settings.midi_hotkey_new_set_2),
            "open_set": (self.settings.midi_hotkey_open_set_1, self.settings.midi_hotkey_open_set_2),
            "save_set": (self.settings.midi_hotkey_save_set_1, self.settings.midi_hotkey_save_set_2),
            "save_set_as": (self.settings.midi_hotkey_save_set_as_1, self.settings.midi_hotkey_save_set_as_2),
            "search": (self.settings.midi_hotkey_search_1, self.settings.midi_hotkey_search_2),
            "options": (self.settings.midi_hotkey_options_1, self.settings.midi_hotkey_options_2),
            "play_selected_pause": (
                self.settings.midi_hotkey_play_selected_pause_1,
                self.settings.midi_hotkey_play_selected_pause_2,
            ),
            "play_selected": (self.settings.midi_hotkey_play_selected_1, self.settings.midi_hotkey_play_selected_2),
            "pause_toggle": (self.settings.midi_hotkey_pause_toggle_1, self.settings.midi_hotkey_pause_toggle_2),
            "stop_playback": (self.settings.midi_hotkey_stop_playback_1, self.settings.midi_hotkey_stop_playback_2),
            "talk": (self.settings.midi_hotkey_talk_1, self.settings.midi_hotkey_talk_2),
            "next_group": (self.settings.midi_hotkey_next_group_1, self.settings.midi_hotkey_next_group_2),
            "prev_group": (self.settings.midi_hotkey_prev_group_1, self.settings.midi_hotkey_prev_group_2),
            "next_page": (self.settings.midi_hotkey_next_page_1, self.settings.midi_hotkey_next_page_2),
            "prev_page": (self.settings.midi_hotkey_prev_page_1, self.settings.midi_hotkey_prev_page_2),
            "next_sound_button": (self.settings.midi_hotkey_next_sound_button_1, self.settings.midi_hotkey_next_sound_button_2),
            "prev_sound_button": (self.settings.midi_hotkey_prev_sound_button_1, self.settings.midi_hotkey_prev_sound_button_2),
            "multi_play": (self.settings.midi_hotkey_multi_play_1, self.settings.midi_hotkey_multi_play_2),
            "go_to_playing": (self.settings.midi_hotkey_go_to_playing_1, self.settings.midi_hotkey_go_to_playing_2),
            "loop": (self.settings.midi_hotkey_loop_1, self.settings.midi_hotkey_loop_2),
            "next": (self.settings.midi_hotkey_next_1, self.settings.midi_hotkey_next_2),
            "rapid_fire": (self.settings.midi_hotkey_rapid_fire_1, self.settings.midi_hotkey_rapid_fire_2),
            "shuffle": (self.settings.midi_hotkey_shuffle_1, self.settings.midi_hotkey_shuffle_2),
            "reset_page": (self.settings.midi_hotkey_reset_page_1, self.settings.midi_hotkey_reset_page_2),
            "play_list": (self.settings.midi_hotkey_play_list_1, self.settings.midi_hotkey_play_list_2),
            "fade_in": (self.settings.midi_hotkey_fade_in_1, self.settings.midi_hotkey_fade_in_2),
            "cross_fade": (self.settings.midi_hotkey_cross_fade_1, self.settings.midi_hotkey_cross_fade_2),
            "fade_out": (self.settings.midi_hotkey_fade_out_1, self.settings.midi_hotkey_fade_out_2),
            "mute": (self.settings.midi_hotkey_mute_1, self.settings.midi_hotkey_mute_2),
            "volume_up": (self.settings.midi_hotkey_volume_up_1, self.settings.midi_hotkey_volume_up_2),
            "volume_down": (self.settings.midi_hotkey_volume_down_1, self.settings.midi_hotkey_volume_down_2),
        }
        self.midi_quick_action_enabled = bool(self.settings.midi_quick_action_enabled)
        self.midi_quick_action_bindings = [normalize_midi_binding(v) for v in self.settings.midi_quick_action_bindings[:48]]
        if len(self.midi_quick_action_bindings) < 48:
            self.midi_quick_action_bindings.extend(["" for _ in range(48 - len(self.midi_quick_action_bindings))])
        self.midi_sound_button_hotkey_enabled = bool(self.settings.midi_sound_button_hotkey_enabled)
        self.midi_sound_button_hotkey_priority = (
            self.settings.midi_sound_button_hotkey_priority
            if self.settings.midi_sound_button_hotkey_priority in {"system_first", "sound_button_first"}
            else "system_first"
        )
        self.midi_sound_button_hotkey_go_to_playing = bool(self.settings.midi_sound_button_hotkey_go_to_playing)
        self.midi_rotary_enabled = bool(getattr(self.settings, "midi_rotary_enabled", False))
        self.midi_rotary_group_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_group_binding", ""))
        self.midi_rotary_page_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_page_binding", ""))
        self.midi_rotary_sound_button_binding = normalize_midi_binding(
            getattr(self.settings, "midi_rotary_sound_button_binding", "")
        )
        self.midi_rotary_jog_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_jog_binding", ""))
        self.midi_rotary_volume_binding = normalize_midi_binding(getattr(self.settings, "midi_rotary_volume_binding", ""))
        self.midi_rotary_group_invert = bool(getattr(self.settings, "midi_rotary_group_invert", False))
        self.midi_rotary_page_invert = bool(getattr(self.settings, "midi_rotary_page_invert", False))
        self.midi_rotary_sound_button_invert = bool(getattr(self.settings, "midi_rotary_sound_button_invert", False))
        self.midi_rotary_jog_invert = bool(getattr(self.settings, "midi_rotary_jog_invert", False))
        self.midi_rotary_volume_invert = bool(getattr(self.settings, "midi_rotary_volume_invert", False))
        self.midi_rotary_group_sensitivity = max(
            1, min(20, int(getattr(self.settings, "midi_rotary_group_sensitivity", 1)))
        )
        self.midi_rotary_page_sensitivity = max(
            1, min(20, int(getattr(self.settings, "midi_rotary_page_sensitivity", 1)))
        )
        self.midi_rotary_sound_button_sensitivity = max(
            1, min(20, int(getattr(self.settings, "midi_rotary_sound_button_sensitivity", 1)))
        )
        self.midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_group_relative_mode", "auto")
        )
        self.midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_page_relative_mode", "auto")
        )
        self.midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_sound_button_relative_mode", "auto")
        )
        self.midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_jog_relative_mode", "auto")
        )
        self.midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            getattr(self.settings, "midi_rotary_volume_relative_mode", "auto")
        )
        mode = str(getattr(self.settings, "midi_rotary_volume_mode", "relative")).strip().lower()
        self.midi_rotary_volume_mode = mode if mode in {"absolute", "relative"} else "relative"
        self.midi_rotary_volume_step = max(1, min(20, int(getattr(self.settings, "midi_rotary_volume_step", 2))))
        self.midi_rotary_jog_step_ms = max(10, min(5000, int(getattr(self.settings, "midi_rotary_jog_step_ms", 250))))
        self._web_remote_server: Optional[WebRemoteServer] = None
        self._main_thread_executor = MainThreadExecutor(self)

        startup_audio_warning: Optional[str] = None
        configured_device = self.audio_output_device.strip()
        if configured_device and not set_output_device(configured_device):
            startup_audio_warning = (
                f"Configured audio device was not found:\n{configured_device}\n\n"
                "Falling back to system default output device."
            )
            self.audio_output_device = ""
            self.settings.audio_output_device = ""
        else:
            set_output_device(configured_device)
        try:
            self._init_audio_players()
        except Exception as exc:
            self._dispose_audio_players()
            set_output_device("")
            self.audio_output_device = ""
            self.settings.audio_output_device = ""
            try:
                self._init_audio_players()
            except Exception as exc2:
                self._init_silent_audio_players()
                startup_audio_warning = (
                    "Audio output failed to initialize. Running in no-audio mode.\n\n"
                    f"Primary error:\n{exc}\n\n"
                    f"Fallback error:\n{exc2}"
                )
            else:
                fallback_msg = (
                    "Audio device failed to initialize at startup.\n"
                    "Falling back to system default output device.\n\n"
                    f"Details:\n{exc}"
                )
                startup_audio_warning = f"{startup_audio_warning}\n\n{fallback_msg}" if startup_audio_warning else fallback_msg

        self.data: Dict[str, List[List[SoundButtonData]]] = {}
        self.page_names: Dict[str, List[str]] = {}
        self.page_colors: Dict[str, List[Optional[str]]] = {}
        self.page_playlist_enabled: Dict[str, List[bool]] = {}
        self.page_shuffle_enabled: Dict[str, List[bool]] = {}
        self.cue_page: List[SoundButtonData] = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self.cue_mode = False
        self.current_set_path = ""
        self._reset_set_data()

        self.group_buttons: Dict[str, QPushButton] = {}
        self.sound_buttons: List[SoundButton] = []
        self.page_list = QListWidget()
        self.group_status = QLabel("")
        self.page_status = QLabel("")
        self.now_playing_label = QLabel("")
        self.drag_mode_banner = QLabel("")
        self.timecode_multiplay_banner = QLabel("")
        self.web_remote_warning_banner = QLabel("")
        self.playback_warning_banner = QLabel("")
        self.save_notice_banner = QLabel("")
        self.status_totals_label = QLabel("")
        self.status_hover_label = QLabel("Button: -")
        self.status_now_playing_label = QLabel("Now Playing: -")
        self.timecode_status_label = QLabel("")
        self.web_remote_status_label = QLabel("")
        self.total_time = QLabel("00:00:00")
        self.preload_status_icon = QLabel("RAM")
        self.elapsed_time = QLabel("00:00:00")
        self.remaining_time = QLabel("00:00:00")
        self.progress_label = TransportProgressDisplay("0%")
        self.jog_in_label = QLabel("In 00:00:00")
        self.jog_percent_label = QLabel("0%")
        self.jog_out_label = QLabel("Out 00:00:00")
        self.left_meter = QProgressBar()
        self.right_meter = QProgressBar()
        self.seek_slider = QSlider(Qt.Horizontal)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.control_buttons: Dict[str, QPushButton] = {}
        self._is_scrubbing = False
        self._vu_levels = [0.0, 0.0]
        self._last_ui_position_ms = -1
        self._player_slot_volume_pct = 75
        self._player_b_slot_volume_pct = 75
        self._multi_players: List[ExternalMediaPlayer] = []
        self._player_slot_pct_map: Dict[int, int] = {}
        self._player_started_map: Dict[int, float] = {}
        self._player_slot_key_map: Dict[int, Tuple[str, int, int]] = {}
        self._player_end_override_ms: Dict[int, int] = {}
        self._player_ignore_cue_end: set[int] = set()
        self._active_playing_keys: set[Tuple[str, int, int]] = set()
        self._ssp_unit_cache: Dict[str, Tuple[int, int]] = {}
        self._drag_source_key: Optional[Tuple[str, int, int]] = None
        self._track_started_at = 0.0
        self._ignore_state_changes = 0
        self._dirty = False
        self._copied_page_buffer: Optional[dict] = None
        self._copied_slot_buffer: Optional[SoundButtonData] = None
        self._search_window: Optional[SearchWindow] = None
        self._dsp_window: Optional[DSPWindow] = None
        self._tool_windows: Dict[str, ToolListWindow] = {}
        self._tool_window_matches: Dict[str, List[dict]] = {}
        self._menu_actions: Dict[str, QAction] = {}
        self._runtime_hotkey_shortcuts: List[QShortcut] = []
        self._modifier_hotkey_handlers: Dict[int, List[Callable[[], None]]] = {}
        self._modifier_hotkey_down: set[int] = set()
        self._midi_router = MidiInputRouter(self._on_midi_binding_triggered)
        self._midi_action_handlers: Dict[str, Callable[[], None]] = {}
        self._midi_last_trigger_t: Dict[str, float] = {}
        self._midi_context_handler = None
        self._midi_context_block_actions = False
        self._skip_save_on_close = False
        self._export_buttons_window: Optional[QDialog] = None
        self._export_dir_edit: Optional[QLineEdit] = None
        self._export_format_combo: Optional[QComboBox] = None
        self._about_window: Optional[AboutWindowDialog] = None
        self._tips_window: Optional[TipsWindow] = None
        self._dsp_config: DSPConfig = DSPConfig()
        self._flash_slot_key: Optional[Tuple[str, int, int]] = None
        self._flash_slot_until = 0.0
        self._hotkey_selected_slot_key: Optional[Tuple[str, int, int]] = None
        self._pre_mute_volume: Optional[int] = None
        self.timecode_dock: Optional[QDockWidget] = None
        self.timecode_panel: Optional[TimecodePanel] = None
        self._mtc_sender = MtcMidiOutput(lambda: self.timecode_mtc_idle_behavior)
        self._ltc_sender = LtcAudioOutput()
        self._timecode_follow_anchor_ms = 0.0
        self._timecode_follow_anchor_t = time.perf_counter()
        self._timecode_follow_playing = False
        self._timecode_follow_intent_pending = False
        self._timecode_last_media_ms = 0.0
        self._timecode_last_media_t = 0.0
        self._timecode_event_guard_until = 0.0
        self._auto_end_fade_track: Optional[Tuple[str, int, int]] = None
        self._auto_end_fade_done = False
        self._preload_icon_blink_on = False
        self._playback_warning_token = 0
        self._save_notice_token = 0
        self._stage_display_window: Optional[GadgetStageDisplayWindow] = None
        self._hover_slot_index: Optional[int] = None
        self._stage_alert_dialog: Optional[QDialog] = None
        self._stage_alert_text_edit: Optional[QPlainTextEdit] = None
        self._stage_alert_duration_spin: Optional[QSpinBox] = None
        self._stage_alert_keep_checkbox: Optional[QCheckBox] = None
        self._stage_alert_message: str = ""
        self._stage_alert_until_monotonic: float = 0.0
        self._stage_alert_sticky: bool = False

        self._build_ui()
        self._apply_language()
        self._update_timecode_status_label()
        self._update_web_remote_status_label()
        self.statusBar().addWidget(self.status_hover_label)
        self.statusBar().addWidget(self.status_now_playing_label, 1)
        self.statusBar().addPermanentWidget(self.timecode_status_label)
        self.statusBar().addPermanentWidget(self.web_remote_status_label)
        self.statusBar().addPermanentWidget(self.status_totals_label)
        self.preload_status_icon.setAlignment(Qt.AlignCenter)
        self.preload_status_icon.setFixedSize(34, 18)
        self.preload_status_icon.setStyleSheet(
            "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#C8CDD4;border:1px solid #8C939D;border-radius:8px;}"
        )
        self.preload_status_icon.setToolTip("RAM preload idle")
        self.statusBar().addPermanentWidget(self.preload_status_icon)
        self._update_talk_button_visual()
        self.volume_slider.setValue(self.settings.volume)
        self.player.setVolume(self._effective_slot_target_volume(self._player_slot_volume_pct))
        self.player_b.setVolume(self._effective_slot_target_volume(self._player_b_slot_volume_pct))
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._update_now_playing_label("")
        self._refresh_window_title()
        self._update_status_totals()
        self._on_sound_button_hover(None)
        self._update_status_now_playing()

        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._tick_meter)
        self.meter_timer.start(60)

        self.timecode_mtc_timer = QTimer(self)
        self.timecode_mtc_timer.timeout.connect(self._tick_timecode_mtc)
        self.timecode_mtc_timer.start(10)

        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self._tick_fades)
        self.fade_timer.start(30)

        self._preload_trim_timer = QTimer(self)
        self._preload_trim_timer.timeout.connect(enforce_audio_preload_limits)
        self._preload_trim_timer.start(2000)

        self._preload_status_timer = QTimer(self)
        self._preload_status_timer.timeout.connect(self._tick_preload_status_icon)
        self._preload_status_timer.start(350)
        self._tick_preload_status_icon()

        self.talk_blink_timer = QTimer(self)
        self.talk_blink_timer.timeout.connect(self._tick_talk_blink)
        self.talk_blink_timer.start(280)

        self._midi_poll_timer = QTimer(self)
        self._midi_poll_timer.timeout.connect(self._poll_midi_inputs)
        self._midi_poll_timer.start(15)

        self.current_group = self.settings.last_group
        self.current_page = self.settings.last_page
        self.cue_mode = False
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._update_button_drag_control_state()
        self._update_button_drag_visual_state()
        self._update_timecode_multiplay_warning_banner()
        self._restore_last_set_on_startup()
        if self.reset_all_on_startup:
            self._reset_all_played_state()
            self._refresh_sound_grid()
        self._apply_web_remote_state()
        if startup_audio_warning:
            QMessageBox.warning(self, "Audio Device", startup_audio_warning)
        self._suspend_settings_save = False
        if self.tips_open_on_startup:
            QTimer.singleShot(0, lambda: self._open_tips_window(startup=True))

    def _build_ui(self) -> None:
        self._build_menu_bar()

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        self.drag_mode_banner.setVisible(False)
        self.drag_mode_banner.setWordWrap(True)
        self.drag_mode_banner.setStyleSheet(
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.drag_mode_banner)
        self.timecode_multiplay_banner.setVisible(False)
        self.timecode_multiplay_banner.setWordWrap(True)
        self.timecode_multiplay_banner.setStyleSheet(
            "QLabel{background:#FDE7E9; color:#7A0010; border:1px solid #B00020; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.timecode_multiplay_banner)
        self.web_remote_warning_banner.setVisible(False)
        self.web_remote_warning_banner.setWordWrap(True)
        self.web_remote_warning_banner.setStyleSheet(
            "QLabel{background:#FDE7E9; color:#7A0010; border:1px solid #B00020; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.web_remote_warning_banner)
        self.playback_warning_banner.setVisible(False)
        self.playback_warning_banner.setWordWrap(True)
        self.playback_warning_banner.setStyleSheet(
            "QLabel{background:#EFE3FA; color:#3F205E; border:1px solid #7B3FB3; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.playback_warning_banner)
        self.save_notice_banner.setVisible(False)
        self.save_notice_banner.setWordWrap(True)
        self.save_notice_banner.setStyleSheet(
            "QLabel{background:#E4F7E7; color:#165A20; border:1px solid #2E9B47; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.save_notice_banner)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        root_layout.addLayout(body_layout, 1)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        body_layout.addWidget(left_panel, 1)
        body_layout.addWidget(right_panel, 5)

        self._build_timecode_dock()

    def _apply_language(self) -> None:
        set_current_language(self.ui_language)
        apply_application_font(QApplication.instance(), self.ui_language)
        localize_widget_tree(self, self.ui_language)
        if self._search_window is not None:
            localize_widget_tree(self._search_window, self.ui_language)
        if self._dsp_window is not None:
            localize_widget_tree(self._dsp_window, self.ui_language)
        for window in self._tool_windows.values():
            localize_widget_tree(window, self.ui_language)
        if self._about_window is not None:
            localize_widget_tree(self._about_window, self.ui_language)
        if self._tips_window is not None:
            self._tips_window.set_language(self.ui_language)
        if self._stage_display_window is not None:
            self._stage_display_window.retranslate_ui()

    def _build_timecode_dock(self) -> None:
        self.timecode_dock = QDockWidget("Timecode", self)
        self.timecode_panel = TimecodePanel(self.timecode_dock)
        self.timecode_dock.setWidget(self.timecode_panel)
        self.timecode_dock.setAllowedAreas(Qt.NoDockWidgetArea)
        self.timecode_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        self.timecode_dock.setVisible(bool(self.show_timecode_panel))
        self.addDockWidget(Qt.RightDockWidgetArea, self.timecode_dock)
        self.timecode_dock.setFloating(True)
        self.timecode_dock.visibilityChanged.connect(self._on_timecode_dock_visibility_changed)
        self.timecode_panel.mode_combo.currentIndexChanged.connect(self._on_timecode_mode_changed)
        mode_idx = self.timecode_panel.mode_combo.findData(self.timecode_mode)
        self.timecode_panel.mode_combo.blockSignals(True)
        self.timecode_panel.mode_combo.setCurrentIndex(mode_idx if mode_idx >= 0 else 0)
        self.timecode_panel.mode_combo.blockSignals(False)
        self._refresh_timecode_panel()

    def _on_timecode_mode_changed(self, _index: int) -> None:
        if self.timecode_panel is None:
            return
        mode = str(self.timecode_panel.mode_combo.currentData() or TIMECODE_MODE_ZERO)
        if mode not in {
            TIMECODE_MODE_ZERO,
            TIMECODE_MODE_FOLLOW,
            TIMECODE_MODE_SYSTEM,
            TIMECODE_MODE_FOLLOW_FREEZE,
        }:
            mode = TIMECODE_MODE_ZERO
        if mode == TIMECODE_MODE_FOLLOW_FREEZE and self.timecode_mode != TIMECODE_MODE_FOLLOW_FREEZE:
            self._timecode_follow_frozen_ms = self._timecode_current_follow_ms()
        self.timecode_mode = mode
        self._refresh_timecode_panel()
        if not self._suspend_settings_save:
            self._save_settings()

    def _on_timecode_dock_visibility_changed(self, visible: bool) -> None:
        self.show_timecode_panel = bool(visible)
        action = self._menu_actions.get("timecode_panel")
        if action is not None:
            action.setChecked(bool(visible))
        if not self._suspend_settings_save:
            self._save_settings()

    def _toggle_timecode_panel(self) -> None:
        if self.timecode_dock is None:
            return
        self.timecode_dock.setVisible(not self.timecode_dock.isVisible())

    def _is_timecode_output_enabled(self) -> bool:
        ltc_enabled = str(self.timecode_audio_output_device or "none").strip().lower() != "none"
        mtc_enabled = str(self.timecode_midi_output_device or MIDI_OUTPUT_DEVICE_NONE).strip() != MIDI_OUTPUT_DEVICE_NONE
        return ltc_enabled or mtc_enabled

    def _update_timecode_multiplay_warning_banner(self) -> None:
        show_warning = self._is_multi_play_enabled() and self._is_timecode_output_enabled()
        if show_warning:
            self.timecode_multiplay_banner.setText(
                tr("TIMECODE ENABLED: Multi-Play is not designed for timecode. Unexpected behaviour could happen.")
            )
            self.timecode_multiplay_banner.setVisible(True)
            return
        self.timecode_multiplay_banner.setVisible(False)

    def _show_playback_warning_banner(self, text: str, timeout_ms: int = 5000) -> None:
        self._playback_warning_token += 1
        token = self._playback_warning_token
        self.playback_warning_banner.setText(str(text or "").strip())
        self.playback_warning_banner.setVisible(True)
        if timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda t=token: self._hide_playback_warning_banner(t))

    def _hide_playback_warning_banner(self, token: Optional[int] = None) -> None:
        if token is not None and token != self._playback_warning_token:
            return
        self.playback_warning_banner.setVisible(False)

    def _show_save_notice_banner(self, text: str, timeout_ms: int = 5000) -> None:
        self._save_notice_token += 1
        token = self._save_notice_token
        self.save_notice_banner.setText(str(text or "").strip())
        self.save_notice_banner.setVisible(True)
        if timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda t=token: self._hide_save_notice_banner(t))

    def _hide_save_notice_banner(self, token: Optional[int] = None) -> None:
        if token is not None and token != self._save_notice_token:
            return
        self.save_notice_banner.setVisible(False)

    def _timecode_current_follow_ms(self) -> int:
        if self.player is None:
            self._timecode_follow_anchor_ms = 0.0
            self._timecode_follow_anchor_t = time.perf_counter()
            self._timecode_follow_playing = False
            self._timecode_follow_intent_pending = False
            return 0
        is_playing = self.player.state() == ExternalMediaPlayer.PlayingState
        now = time.perf_counter()
        predicted_ms = self._timecode_follow_anchor_ms + max(0.0, (now - self._timecode_follow_anchor_t) * 1000.0)
        try:
            absolute_ms = max(0, int(self.player.enginePositionMs()))
        except Exception:
            try:
                absolute_ms = max(0, int(self.player.position()))
            except Exception:
                absolute_ms = 0
        media_ms = float(self._timecode_display_ms_from_absolute(absolute_ms))
        if not is_playing:
            if self._timecode_follow_intent_pending and self._timecode_follow_playing:
                self._timecode_follow_anchor_ms = predicted_ms
                self._timecode_follow_anchor_t = now
                return int(max(0.0, predicted_ms))
            self._timecode_follow_anchor_ms = media_ms
            self._timecode_follow_anchor_t = now
            self._timecode_follow_playing = False
            return int(media_ms)

        self._timecode_follow_anchor_ms = media_ms
        self._timecode_follow_anchor_t = now
        self._timecode_follow_playing = True
        self._timecode_follow_intent_pending = False
        self._timecode_last_media_ms = media_ms
        self._timecode_last_media_t = now
        return int(max(0.0, self._timecode_follow_anchor_ms))

    def _timecode_display_ms_from_absolute(self, absolute_ms: int) -> int:
        absolute = max(0, int(absolute_ms))
        if self.timecode_timeline_mode == "audio_file":
            return absolute
        if self.current_playing is None:
            return absolute
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return absolute
        # Do not clamp to duration here; duration may still be unknown at playback start.
        cue_start = 0 if slot.cue_start_ms is None else max(0, int(slot.cue_start_ms))
        return max(0, absolute - cue_start)

    def _timecode_output_ms(self) -> int:
        if self.timecode_mode == TIMECODE_MODE_ZERO:
            return 0
        if self.timecode_mode == TIMECODE_MODE_SYSTEM:
            now = datetime.now()
            return (
                ((now.hour * 3600 + now.minute * 60 + now.second) * 1000)
                + int(now.microsecond / 1000)
            )
        if self.timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE:
            return max(0, int(self._timecode_follow_frozen_ms))
        return self._timecode_current_follow_ms()

    def _timecode_device_text(self) -> str:
        ltc_format = (
            f"LTC {self.timecode_fps:g} fps, MTC {self.timecode_mtc_fps:g} fps "
            f"({self.timecode_mtc_idle_behavior}), {self.timecode_sample_rate} Hz, {self.timecode_bit_depth}-bit"
        )
        midi_text = "MIDI: Disabled"
        if self.timecode_midi_output_device != MIDI_OUTPUT_DEVICE_NONE:
            midi_map = {device_id: name for device_id, name in list_midi_output_devices()}
            midi_name = midi_map.get(self.timecode_midi_output_device, "Unavailable")
            midi_text = f"MIDI: {midi_name}"
        if self.timecode_audio_output_device == "follow_playback":
            return f"Output Device: Follows playback device setting ({ltc_format}) | {midi_text}"
        if self.timecode_audio_output_device == "none":
            return f"Output Device: None (muted) ({ltc_format}) | {midi_text}"
        if self.timecode_audio_output_device in {"default", ""}:
            return f"Output Device: System default ({ltc_format}) | {midi_text}"
        return f"Output Device: {self.timecode_audio_output_device} ({ltc_format}) | {midi_text}"

    def _tick_timecode_mtc(self) -> None:
        ltc_device: Optional[str]
        if self.timecode_audio_output_device == "none":
            ltc_device = None
        elif self.timecode_audio_output_device == "follow_playback":
            selected = str(self.audio_output_device or "").strip()
            ltc_device = selected if selected else None
        elif self.timecode_audio_output_device in {"default", ""}:
            ltc_device = ""
        else:
            ltc_device = str(self.timecode_audio_output_device).strip()
        self._ltc_sender.set_output(
            ltc_device,
            int(self.timecode_sample_rate),
            int(self.timecode_bit_depth),
            float(self.timecode_fps),
        )
        self._mtc_sender.set_device(self.timecode_midi_output_device)
        output_ms = self._timecode_output_ms()
        current_frame = int((max(0, output_ms) / 1000.0) * max(1.0, float(self.timecode_fps)))
        self._ltc_sender.update(
            current_frame=current_frame,
            fps=max(1.0, float(self.timecode_fps)),
        )
        self._mtc_sender.update(
            current_frame=current_frame,
            source_fps=max(1.0, float(self.timecode_fps)),
            mtc_fps=max(1.0, float(self.timecode_mtc_fps)),
        )

    def _timecode_on_playback_start(self, slot: Optional[SoundButtonData] = None) -> None:
        now = time.perf_counter()
        if now < self._timecode_event_guard_until:
            return
        start_abs = 0
        if slot is not None:
            duration_guess = max(0, int(slot.duration_ms))
            start_abs = self._cue_start_for_playback(slot, duration_guess)
        start_display = float(self._timecode_display_ms_from_absolute(start_abs))
        self._timecode_follow_anchor_ms = start_display
        self._timecode_follow_anchor_t = now
        self._timecode_follow_playing = True
        self._timecode_follow_intent_pending = True
        self._timecode_last_media_ms = start_display
        self._timecode_last_media_t = now
        print(
            f"[TCDBG] {now:.6f} timecode_start anchor_ms={start_display:.1f} "
            f"slot={(slot.title if slot else '<none>')}"
        )
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _timecode_on_playback_stop(self) -> None:
        now = time.perf_counter()
        if now < self._timecode_event_guard_until:
            return
        self._timecode_follow_anchor_ms = 0.0
        self._timecode_follow_anchor_t = now
        self._timecode_follow_playing = False
        self._timecode_follow_intent_pending = False
        self._timecode_last_media_ms = 0.0
        self._timecode_last_media_t = now
        print(f"[TCDBG] {now:.6f} timecode_stop")
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _timecode_on_playback_pause(self) -> None:
        if time.perf_counter() < self._timecode_event_guard_until:
            return
        paused_ms = float(self._timecode_current_follow_ms())
        self._timecode_follow_anchor_ms = paused_ms
        self._timecode_follow_anchor_t = time.perf_counter()
        self._timecode_follow_playing = False
        self._timecode_follow_intent_pending = False
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _timecode_on_playback_resume(self) -> None:
        if time.perf_counter() < self._timecode_event_guard_until:
            return
        resume_ms = float(self._timecode_current_follow_ms())
        self._timecode_follow_anchor_ms = resume_ms
        self._timecode_follow_anchor_t = time.perf_counter()
        self._timecode_follow_playing = True
        self._timecode_follow_intent_pending = False
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _refresh_timecode_panel(self) -> None:
        self._update_timecode_status_label()
        if self.timecode_panel is None:
            return
        mode_idx = self.timecode_panel.mode_combo.findData(self.timecode_mode)
        if mode_idx >= 0 and mode_idx != self.timecode_panel.mode_combo.currentIndex():
            self.timecode_panel.mode_combo.blockSignals(True)
            self.timecode_panel.mode_combo.setCurrentIndex(mode_idx)
            self.timecode_panel.mode_combo.blockSignals(False)
        output_ms = self._timecode_output_ms()
        self.timecode_panel.timecode_label.setText(
            ms_to_timecode_string(output_ms, nominal_fps(self.timecode_fps))
        )
        self.timecode_panel.device_label.setText(self._timecode_device_text())

    def _update_timecode_status_label(self) -> None:
        ltc_enabled = str(self.timecode_audio_output_device or "none").strip().lower() != "none"
        mtc_enabled = str(self.timecode_midi_output_device or MIDI_OUTPUT_DEVICE_NONE).strip() != MIDI_OUTPUT_DEVICE_NONE
        if self.timecode_mode == TIMECODE_MODE_ZERO:
            mode_text = "All Zero"
        elif self.timecode_mode == TIMECODE_MODE_SYSTEM:
            mode_text = "System Time"
        elif self.timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE:
            if self.timecode_timeline_mode == "audio_file":
                mode_text = "Freeze Timecode (relative to actual audio file)"
            else:
                mode_text = "Freeze Timecode (relative to cue set point)"
        else:
            if self.timecode_timeline_mode == "audio_file":
                mode_text = "Follow Media/Audio Player (relative to actual audio file)"
            else:
                mode_text = "Follow Media/Audio Player (relative to cue set point)"
        self.timecode_status_label.setText(
            f"{tr('LTC: ')}{tr('Enabled') if ltc_enabled else tr('Disabled')} | "
            f"{tr('MTC: ')}{tr('Enabled') if mtc_enabled else tr('Disabled')} | "
            f"{tr('Timecode: ')}{tr(mode_text)}"
        )

    def _init_audio_players(self) -> None:
        self.player = ExternalMediaPlayer(self)
        self.player_b = ExternalMediaPlayer(self)
        self.player.setNotifyInterval(90)
        self.player_b.setNotifyInterval(90)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)

    def _dispose_audio_players(self) -> None:
        for name in ["player", "player_b"]:
            player = getattr(self, name, None)
            if player is None:
                continue
            try:
                player.stop()
            except Exception:
                pass
            try:
                player.deleteLater()
            except Exception:
                pass
            setattr(self, name, None)

    def _init_silent_audio_players(self) -> None:
        self.player = NoAudioPlayer(self)
        self.player_b = NoAudioPlayer(self)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        new_set_action = QAction("New Set", self)
        new_set_action.triggered.connect(self._new_set)
        file_menu.addAction(new_set_action)
        self._menu_actions["new_set"] = new_set_action

        open_set_action = QAction("Open Set", self)
        open_set_action.triggered.connect(self._open_set_dialog)
        file_menu.addAction(open_set_action)
        self._menu_actions["open_set"] = open_set_action

        save_set_action = QAction("Save Set", self)
        save_set_action.triggered.connect(self._save_set)
        file_menu.addAction(save_set_action)
        self._menu_actions["save_set"] = save_set_action

        save_set_at_action = QAction("Save Set At", self)
        save_set_at_action.triggered.connect(self._save_set_at)
        file_menu.addAction(save_set_at_action)
        self._menu_actions["save_set_as"] = save_set_at_action

        file_menu.addSeparator()

        backup_settings_action = QAction("Backup pySSP Settings", self)
        backup_settings_action.triggered.connect(self._backup_pyssp_settings)
        file_menu.addAction(backup_settings_action)

        restore_settings_action = QAction("Restore pySSP Settings", self)
        restore_settings_action.triggered.connect(self._restore_pyssp_settings)
        file_menu.addAction(restore_settings_action)

        file_menu.addSeparator()

        backup_keyboard_hotkeys_action = QAction("Backup Keyboard Hotkey Bindings", self)
        backup_keyboard_hotkeys_action.triggered.connect(self._backup_keyboard_hotkey_bindings)
        file_menu.addAction(backup_keyboard_hotkeys_action)

        restore_keyboard_hotkeys_action = QAction("Restore Keyboard Hotkey Bindings", self)
        restore_keyboard_hotkeys_action.triggered.connect(self._restore_keyboard_hotkey_bindings)
        file_menu.addAction(restore_keyboard_hotkeys_action)

        file_menu.addSeparator()

        backup_midi_bindings_action = QAction("Backup MIDI Bindings", self)
        backup_midi_bindings_action.triggered.connect(self._backup_midi_bindings)
        file_menu.addAction(backup_midi_bindings_action)

        restore_midi_bindings_action = QAction("Restore MIDI Bindings", self)
        restore_midi_bindings_action.triggered.connect(self._restore_midi_bindings)
        file_menu.addAction(restore_midi_bindings_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        setup_menu = self.menuBar().addMenu("Setup")
        options_action = QAction("Options", self)
        options_action.triggered.connect(self._open_options_dialog)
        setup_menu.addAction(options_action)
        self._menu_actions["options"] = options_action

        display_menu = self.menuBar().addMenu("Display")
        show_display_action = QAction("Show Display", self)
        show_display_action.triggered.connect(self._show_stage_display)
        display_menu.addAction(show_display_action)
        stage_display_setting_action = QAction("Stage Display Setting", self)
        stage_display_setting_action.triggered.connect(lambda: self._open_options_dialog(initial_page="Display"))
        display_menu.addAction(stage_display_setting_action)
        send_alert_action = QAction("Send Alert", self)
        send_alert_action.triggered.connect(self._open_stage_alert_panel)
        display_menu.addAction(send_alert_action)

        search_action = QAction("Search", self)
        search_action.triggered.connect(self._open_find_dialog)
        self.addAction(search_action)
        self._menu_actions["search"] = search_action

        timecode_menu = self.menuBar().addMenu("Timecode")
        timecode_settings_action = QAction("Timecode Settings", self)
        timecode_settings_action.triggered.connect(self._open_timecode_settings)
        timecode_menu.addAction(timecode_settings_action)
        self._menu_actions["timecode_settings"] = timecode_settings_action
        timecode_panel_action = QAction("Timecode Panel", self)
        timecode_panel_action.setCheckable(True)
        timecode_panel_action.setChecked(bool(self.show_timecode_panel))
        timecode_panel_action.triggered.connect(self._toggle_timecode_panel)
        timecode_menu.addAction(timecode_panel_action)
        self._menu_actions["timecode_panel"] = timecode_panel_action

        tools_menu = self.menuBar().addMenu("Tools")
        duplicate_check_action = QAction("Duplicate Check", self)
        duplicate_check_action.triggered.connect(self._run_duplicate_check)
        tools_menu.addAction(duplicate_check_action)

        verify_sound_buttons_action = QAction("Verify Sound Buttons", self)
        verify_sound_buttons_action.triggered.connect(self._run_verify_sound_buttons)
        tools_menu.addAction(verify_sound_buttons_action)

        disable_playlist_all_pages_action = QAction("Disable Play List on All Pages", self)
        disable_playlist_all_pages_action.triggered.connect(self._disable_playlist_on_all_pages)
        tools_menu.addAction(disable_playlist_all_pages_action)

        tools_menu.addSeparator()

        page_library_path_action = QAction("Display Page Library Folder Path", self)
        page_library_path_action.triggered.connect(self._show_page_library_folder_path)
        tools_menu.addAction(page_library_path_action)

        set_file_path_action = QAction("Display .set File and Path", self)
        set_file_path_action.triggered.connect(self._show_set_file_and_path)
        tools_menu.addAction(set_file_path_action)

        tools_menu.addSeparator()

        export_excel_action = QAction("Export Page and Sound Buttons to Excel", self)
        export_excel_action.triggered.connect(self._export_page_and_sound_buttons_to_excel)
        tools_menu.addAction(export_excel_action)

        list_sound_buttons_action = QAction("List Sound Buttons", self)
        list_sound_buttons_action.triggered.connect(self._list_sound_buttons)
        tools_menu.addAction(list_sound_buttons_action)

        list_sound_button_hotkey_action = QAction("List Sound Button Hot Key", self)
        list_sound_button_hotkey_action.triggered.connect(self._list_sound_button_hotkeys)
        tools_menu.addAction(list_sound_button_hotkey_action)

        list_sound_device_midi_mapping_action = QAction("List Sound Device MIDI Mapping", self)
        list_sound_device_midi_mapping_action.triggered.connect(self._list_sound_device_midi_mappings)
        tools_menu.addAction(list_sound_device_midi_mapping_action)

        log_menu = self.menuBar().addMenu("Logs")
        view_log_action = QAction("View Log", self)
        view_log_action.triggered.connect(self._view_log_file)
        log_menu.addAction(view_log_action)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._open_about_window)
        help_menu.addAction(about_action)

        help_action = QAction("Help", self)
        help_action.triggered.connect(self._open_help_window)
        help_menu.addAction(help_action)

        tips_action = QAction("Tips", self)
        tips_action.triggered.connect(lambda _=False: self._open_tips_window(startup=False))
        help_menu.addAction(tips_action)

        register_action = QAction("Register", self)
        register_action.triggered.connect(self._show_register_message)
        help_menu.addAction(register_action)
        self._apply_hotkeys()

    def _show_register_message(self) -> None:
        QMessageBox.information(
            self,
            "Register",
            "pySSP is free software. No registration is required.",
        )

    def _project_root_path(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _asset_file_path(self, *parts: str) -> str:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
            bundled = os.path.join(base_dir, "pyssp", "assets", *parts)
            if os.path.exists(bundled):
                return bundled
            meipass_dir = getattr(sys, "_MEIPASS", "")
            if meipass_dir:
                candidate = os.path.join(meipass_dir, "pyssp", "assets", *parts)
                if os.path.exists(candidate):
                    return candidate
            return bundled
        return os.path.join(self._project_root_path(), "pyssp", "assets", *parts)

    def _help_index_path(self) -> str:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
            bundled = os.path.join(base_dir, "docs", "build", "html", "index.html")
            if os.path.exists(bundled):
                return bundled
            meipass_dir = getattr(sys, "_MEIPASS", "")
            if meipass_dir:
                candidate = os.path.join(meipass_dir, "docs", "build", "html", "index.html")
                if os.path.exists(candidate):
                    return candidate
            return bundled
        return os.path.join(self._project_root_path(), "docs", "build", "html", "index.html")

    def _default_backup_dir(self) -> str:
        return self.settings.last_save_dir or self.settings.last_open_dir or os.path.expanduser("~")

    @staticmethod
    def _coerce_bool(value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            token = value.strip().lower()
            if token in {"1", "true", "yes", "on"}:
                return True
            if token in {"0", "false", "no", "off"}:
                return False
        return bool(value) if value is not None else bool(default)

    @staticmethod
    def _coerce_int(value, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except Exception:
            parsed = int(default)
        return max(int(minimum), min(int(maximum), int(parsed)))

    @staticmethod
    def _normalize_stage_display_layout(values: List[str]) -> List[str]:
        valid = ["current_time", "alert", "total_time", "elapsed", "remaining", "progress_bar", "song_name", "next_song"]
        output: List[str] = []
        for raw in list(values or []):
            key = str(raw or "").strip().lower()
            if key in valid and key not in output:
                output.append(key)
        for key in valid:
            if key not in output:
                output.append(key)
        return output

    @staticmethod
    def _normalize_stage_display_visibility(values: Dict[str, bool]) -> Dict[str, bool]:
        valid = ["current_time", "alert", "total_time", "elapsed", "remaining", "progress_bar", "song_name", "next_song"]
        output: Dict[str, bool] = {}
        for key in valid:
            output[key] = bool(values.get(key, True))
        return output

    def _backup_pyssp_settings(self) -> None:
        self._save_settings()
        source = get_settings_path()
        if not source.exists():
            try:
                save_settings(self.settings)
            except Exception as exc:
                QMessageBox.critical(self, "Backup pySSP Settings", f"Could not create settings file:\n{exc}")
                return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_path = os.path.join(self._default_backup_dir(), f"pyssp_settings_backup_{stamp}.ini")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup pySSP Settings",
            initial_path,
            "INI Files (*.ini);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".ini"):
            file_path = f"{file_path}.ini"
        try:
            shutil.copy2(str(source), file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Backup pySSP Settings", f"Could not backup settings:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Backup pySSP Settings", f"Backup saved:\n{file_path}")

    def _restore_pyssp_settings(self) -> None:
        start_dir = self._default_backup_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore pySSP Settings",
            start_dir,
            "INI Files (*.ini);;All Files (*.*)",
        )
        if not file_path:
            return
        target = get_settings_path()
        try:
            shutil.copy2(file_path, str(target))
        except Exception as exc:
            QMessageBox.critical(self, "Restore pySSP Settings", f"Could not restore settings:\n{exc}")
            return
        answer = QMessageBox.question(
            self,
            "Restore pySSP Settings",
            "Settings restored.\npySSP needs restart to apply them correctly.\n\nRestart now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._skip_save_on_close = True
            self.close()
            return
        QMessageBox.information(
            self,
            "Restore pySSP Settings",
            "Settings restored to disk. Restart pySSP before making more changes.",
        )

    def _backup_keyboard_hotkey_bindings(self) -> None:
        payload = {
            "type": "pyssp_keyboard_hotkey_bindings",
            "version": 1,
            "hotkeys": {k: [v[0], v[1]] for k, v in self.hotkeys.items()},
            "quick_action_enabled": bool(self.quick_action_enabled),
            "quick_action_keys": list(self.quick_action_keys[:48]),
            "sound_button_hotkey_enabled": bool(self.sound_button_hotkey_enabled),
            "sound_button_hotkey_priority": str(self.sound_button_hotkey_priority),
            "sound_button_hotkey_go_to_playing": bool(self.sound_button_hotkey_go_to_playing),
        }
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_path = os.path.join(self._default_backup_dir(), f"keyboard_hotkeys_backup_{stamp}.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Keyboard Hotkey Bindings",
            initial_path,
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path = f"{file_path}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.critical(self, "Backup Keyboard Hotkey Bindings", f"Could not write backup file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Backup Keyboard Hotkey Bindings", f"Backup saved:\n{file_path}")

    def _restore_keyboard_hotkey_bindings(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Keyboard Hotkey Bindings",
            self._default_backup_dir(),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            QMessageBox.critical(self, "Restore Keyboard Hotkey Bindings", f"Could not read backup file:\n{exc}")
            return
        if not isinstance(payload, dict):
            QMessageBox.critical(self, "Restore Keyboard Hotkey Bindings", "Invalid backup format.")
            return

        raw_hotkeys = payload.get("hotkeys", {})
        next_hotkeys: Dict[str, tuple[str, str]] = {}
        for key in HOTKEY_DEFAULTS.keys():
            default_pair = HOTKEY_DEFAULTS.get(key, ("", ""))
            raw_pair = raw_hotkeys.get(key, default_pair) if isinstance(raw_hotkeys, dict) else default_pair
            v1 = str(raw_pair[0]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 1 else str(default_pair[0])
            v2 = str(raw_pair[1]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 2 else str(default_pair[1])
            next_hotkeys[key] = (v1, v2)

        raw_quick = payload.get("quick_action_keys", [])
        next_quick: List[str] = []
        if isinstance(raw_quick, list):
            next_quick = [str(v).strip() for v in raw_quick[:48]]
        if len(next_quick) < 48:
            next_quick.extend(["" for _ in range(48 - len(next_quick))])

        self.hotkeys = next_hotkeys
        self.quick_action_enabled = self._coerce_bool(payload.get("quick_action_enabled", self.quick_action_enabled))
        self.quick_action_keys = next_quick
        self.sound_button_hotkey_enabled = self._coerce_bool(
            payload.get("sound_button_hotkey_enabled", self.sound_button_hotkey_enabled)
        )
        priority = str(payload.get("sound_button_hotkey_priority", self.sound_button_hotkey_priority)).strip()
        self.sound_button_hotkey_priority = (
            priority if priority in {"system_first", "sound_button_first"} else "system_first"
        )
        self.sound_button_hotkey_go_to_playing = self._coerce_bool(
            payload.get("sound_button_hotkey_go_to_playing", self.sound_button_hotkey_go_to_playing)
        )
        self._apply_hotkeys()
        self._save_settings()
        QMessageBox.information(self, "Restore Keyboard Hotkey Bindings", "Keyboard hotkey bindings restored.")

    def _backup_midi_bindings(self) -> None:
        payload = {
            "type": "pyssp_midi_bindings",
            "version": 1,
            "midi_input_device_ids": list(self.midi_input_device_ids),
            "midi_hotkeys": {k: [v[0], v[1]] for k, v in self.midi_hotkeys.items()},
            "midi_quick_action_enabled": bool(self.midi_quick_action_enabled),
            "midi_quick_action_bindings": list(self.midi_quick_action_bindings[:48]),
            "midi_sound_button_hotkey_enabled": bool(self.midi_sound_button_hotkey_enabled),
            "midi_sound_button_hotkey_priority": str(self.midi_sound_button_hotkey_priority),
            "midi_sound_button_hotkey_go_to_playing": bool(self.midi_sound_button_hotkey_go_to_playing),
            "midi_rotary_enabled": bool(self.midi_rotary_enabled),
            "midi_rotary_group_binding": self.midi_rotary_group_binding,
            "midi_rotary_page_binding": self.midi_rotary_page_binding,
            "midi_rotary_sound_button_binding": self.midi_rotary_sound_button_binding,
            "midi_rotary_jog_binding": self.midi_rotary_jog_binding,
            "midi_rotary_volume_binding": self.midi_rotary_volume_binding,
            "midi_rotary_group_invert": bool(self.midi_rotary_group_invert),
            "midi_rotary_page_invert": bool(self.midi_rotary_page_invert),
            "midi_rotary_sound_button_invert": bool(self.midi_rotary_sound_button_invert),
            "midi_rotary_jog_invert": bool(self.midi_rotary_jog_invert),
            "midi_rotary_volume_invert": bool(self.midi_rotary_volume_invert),
            "midi_rotary_group_sensitivity": int(self.midi_rotary_group_sensitivity),
            "midi_rotary_page_sensitivity": int(self.midi_rotary_page_sensitivity),
            "midi_rotary_sound_button_sensitivity": int(self.midi_rotary_sound_button_sensitivity),
            "midi_rotary_group_relative_mode": self.midi_rotary_group_relative_mode,
            "midi_rotary_page_relative_mode": self.midi_rotary_page_relative_mode,
            "midi_rotary_sound_button_relative_mode": self.midi_rotary_sound_button_relative_mode,
            "midi_rotary_jog_relative_mode": self.midi_rotary_jog_relative_mode,
            "midi_rotary_volume_relative_mode": self.midi_rotary_volume_relative_mode,
            "midi_rotary_volume_mode": self.midi_rotary_volume_mode,
            "midi_rotary_volume_step": int(self.midi_rotary_volume_step),
            "midi_rotary_jog_step_ms": int(self.midi_rotary_jog_step_ms),
        }
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_path = os.path.join(self._default_backup_dir(), f"midi_bindings_backup_{stamp}.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup MIDI Bindings",
            initial_path,
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path = f"{file_path}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.critical(self, "Backup MIDI Bindings", f"Could not write backup file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Backup MIDI Bindings", f"Backup saved:\n{file_path}")

    def _restore_midi_bindings(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore MIDI Bindings",
            self._default_backup_dir(),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            QMessageBox.critical(self, "Restore MIDI Bindings", f"Could not read backup file:\n{exc}")
            return
        if not isinstance(payload, dict):
            QMessageBox.critical(self, "Restore MIDI Bindings", "Invalid backup format.")
            return

        raw_hotkeys = payload.get("midi_hotkeys", {})
        next_midi_hotkeys: Dict[str, tuple[str, str]] = {}
        for key in MIDI_HOTKEY_DEFAULTS.keys():
            raw_pair = raw_hotkeys.get(key, ("", "")) if isinstance(raw_hotkeys, dict) else ("", "")
            v1 = str(raw_pair[0]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 1 else ""
            v2 = str(raw_pair[1]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 2 else ""
            next_midi_hotkeys[key] = (normalize_midi_binding(v1), normalize_midi_binding(v2))

        raw_midi_quick = payload.get("midi_quick_action_bindings", [])
        next_midi_quick: List[str] = []
        if isinstance(raw_midi_quick, list):
            next_midi_quick = [normalize_midi_binding(str(v).strip()) for v in raw_midi_quick[:48]]
        if len(next_midi_quick) < 48:
            next_midi_quick.extend(["" for _ in range(48 - len(next_midi_quick))])

        raw_inputs = payload.get("midi_input_device_ids", [])
        midi_inputs = [str(v).strip() for v in raw_inputs] if isinstance(raw_inputs, list) else []
        self.midi_input_device_ids = self._normalize_midi_input_selectors([v for v in midi_inputs if v])
        self.midi_hotkeys = next_midi_hotkeys
        self.midi_quick_action_enabled = self._coerce_bool(
            payload.get("midi_quick_action_enabled", self.midi_quick_action_enabled)
        )
        self.midi_quick_action_bindings = next_midi_quick
        self.midi_sound_button_hotkey_enabled = self._coerce_bool(
            payload.get("midi_sound_button_hotkey_enabled", self.midi_sound_button_hotkey_enabled)
        )
        midi_prio = str(payload.get("midi_sound_button_hotkey_priority", self.midi_sound_button_hotkey_priority)).strip()
        self.midi_sound_button_hotkey_priority = (
            midi_prio if midi_prio in {"system_first", "sound_button_first"} else "system_first"
        )
        self.midi_sound_button_hotkey_go_to_playing = self._coerce_bool(
            payload.get("midi_sound_button_hotkey_go_to_playing", self.midi_sound_button_hotkey_go_to_playing)
        )
        self.midi_rotary_enabled = self._coerce_bool(payload.get("midi_rotary_enabled", self.midi_rotary_enabled))
        self.midi_rotary_group_binding = normalize_midi_binding(str(payload.get("midi_rotary_group_binding", "")))
        self.midi_rotary_page_binding = normalize_midi_binding(str(payload.get("midi_rotary_page_binding", "")))
        self.midi_rotary_sound_button_binding = normalize_midi_binding(str(payload.get("midi_rotary_sound_button_binding", "")))
        self.midi_rotary_jog_binding = normalize_midi_binding(str(payload.get("midi_rotary_jog_binding", "")))
        self.midi_rotary_volume_binding = normalize_midi_binding(str(payload.get("midi_rotary_volume_binding", "")))
        self.midi_rotary_group_invert = self._coerce_bool(payload.get("midi_rotary_group_invert", self.midi_rotary_group_invert))
        self.midi_rotary_page_invert = self._coerce_bool(payload.get("midi_rotary_page_invert", self.midi_rotary_page_invert))
        self.midi_rotary_sound_button_invert = self._coerce_bool(payload.get("midi_rotary_sound_button_invert", self.midi_rotary_sound_button_invert))
        self.midi_rotary_jog_invert = self._coerce_bool(payload.get("midi_rotary_jog_invert", self.midi_rotary_jog_invert))
        self.midi_rotary_volume_invert = self._coerce_bool(payload.get("midi_rotary_volume_invert", self.midi_rotary_volume_invert))
        self.midi_rotary_group_sensitivity = self._coerce_int(
            payload.get("midi_rotary_group_sensitivity", self.midi_rotary_group_sensitivity),
            self.midi_rotary_group_sensitivity,
            1,
            20,
        )
        self.midi_rotary_page_sensitivity = self._coerce_int(
            payload.get("midi_rotary_page_sensitivity", self.midi_rotary_page_sensitivity),
            self.midi_rotary_page_sensitivity,
            1,
            20,
        )
        self.midi_rotary_sound_button_sensitivity = self._coerce_int(
            payload.get("midi_rotary_sound_button_sensitivity", self.midi_rotary_sound_button_sensitivity),
            self.midi_rotary_sound_button_sensitivity,
            1,
            20,
        )
        self.midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_group_relative_mode", self.midi_rotary_group_relative_mode))
        )
        self.midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_page_relative_mode", self.midi_rotary_page_relative_mode))
        )
        self.midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_sound_button_relative_mode", self.midi_rotary_sound_button_relative_mode))
        )
        self.midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_jog_relative_mode", self.midi_rotary_jog_relative_mode))
        )
        self.midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_volume_relative_mode", self.midi_rotary_volume_relative_mode))
        )
        mode = str(payload.get("midi_rotary_volume_mode", self.midi_rotary_volume_mode)).strip().lower()
        self.midi_rotary_volume_mode = mode if mode in {"absolute", "relative"} else "relative"
        self.midi_rotary_volume_step = self._coerce_int(
            payload.get("midi_rotary_volume_step", self.midi_rotary_volume_step),
            self.midi_rotary_volume_step,
            1,
            20,
        )
        self.midi_rotary_jog_step_ms = self._coerce_int(
            payload.get("midi_rotary_jog_step_ms", self.midi_rotary_jog_step_ms),
            self.midi_rotary_jog_step_ms,
            10,
            5000,
        )
        self._apply_hotkeys()
        self._save_settings()
        QMessageBox.information(self, "Restore MIDI Bindings", "MIDI bindings restored.")

    def _normalized_hotkey_pair(self, action_key: str) -> tuple[str, str]:
        raw1, raw2 = self.hotkeys.get(action_key, HOTKEY_DEFAULTS.get(action_key, ("", "")))
        seq1 = self._normalize_hotkey_text(raw1)
        seq2 = self._normalize_hotkey_text(raw2)
        if seq2 == seq1:
            seq2 = ""
        return seq1, seq2

    def _normalize_hotkey_text(self, value: str) -> str:
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

    def _key_sequence_from_hotkey_text(self, value: str) -> Optional[QKeySequence]:
        text = self._normalize_hotkey_text(value)
        if not text:
            return None
        if text == "Shift":
            return QKeySequence(int(Qt.SHIFT))
        if text == "Ctrl":
            return QKeySequence(int(Qt.CTRL))
        if text == "Alt":
            return QKeySequence(int(Qt.ALT))
        if text == "Meta":
            return QKeySequence(int(Qt.META))
        return QKeySequence(text)

    def _modifier_key_from_hotkey_text(self, value: str) -> Optional[int]:
        text = self._normalize_hotkey_text(value)
        if text == "Shift":
            return int(Qt.Key_Shift)
        if text == "Ctrl":
            return int(Qt.Key_Control)
        if text == "Alt":
            return int(Qt.Key_Alt)
        if text == "Meta":
            return int(Qt.Key_Meta)
        return None

    def _apply_hotkeys(self) -> None:
        for key in ["new_set", "open_set", "save_set", "save_set_as", "search", "options"]:
            action = self._menu_actions.get(key)
            if action is None:
                continue
            h1, h2 = self._normalized_hotkey_pair(key)
            sequences: List[QKeySequence] = []
            for text in [h1, h2]:
                seq = self._key_sequence_from_hotkey_text(text)
                if seq is not None:
                    sequences.append(seq)
            action.setShortcuts(sequences)

        for sc in self._runtime_hotkey_shortcuts:
            try:
                sc.activated.disconnect()
            except Exception:
                pass
            sc.setParent(None)
            sc.deleteLater()
        self._runtime_hotkey_shortcuts = []
        self._modifier_hotkey_handlers = {}
        self._modifier_hotkey_down.clear()

        runtime_handlers = self._runtime_action_handlers()
        ordered_system_keys: List[str] = [k for k in SYSTEM_HOTKEY_ORDER_DEFAULT if k in runtime_handlers]

        sound_bindings = self._collect_sound_button_hotkey_bindings() if self.sound_button_hotkey_enabled else {}
        registered_keys: set[str] = set()

        for key in ordered_system_keys:
            handler = runtime_handlers[key]
            h1, h2 = self._normalized_hotkey_pair(key)
            for seq_text in [h1, h2]:
                key_token = self._normalize_hotkey_text(seq_text)
                if self.sound_button_hotkey_enabled and self.sound_button_hotkey_priority == "sound_button_first":
                    if key_token and key_token in sound_bindings:
                        continue
                modifier_key = self._modifier_key_from_hotkey_text(seq_text)
                if modifier_key is not None:
                    handlers = self._modifier_hotkey_handlers.setdefault(modifier_key, [])
                    if handler not in handlers:
                        handlers.append(handler)
                        key_name = self._normalize_hotkey_text(seq_text)
                        if key_name:
                            registered_keys.add(key_name)
                    continue
                seq = self._key_sequence_from_hotkey_text(seq_text)
                if seq is None:
                    continue
                shortcut = QShortcut(seq, self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.activated.connect(handler)
                self._runtime_hotkey_shortcuts.append(shortcut)
                if key_token:
                    registered_keys.add(key_token)

        if self.quick_action_enabled:
            for idx, raw in enumerate(self.quick_action_keys[:48]):
                key_token = self._normalize_hotkey_text(raw)
                if self.sound_button_hotkey_enabled and self.sound_button_hotkey_priority == "sound_button_first":
                    if key_token and key_token in sound_bindings:
                        continue
                seq = self._key_sequence_from_hotkey_text(raw)
                if seq is None:
                    continue
                shortcut = QShortcut(seq, self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.activated.connect(lambda slot=idx: self._quick_action_trigger(slot))
                self._runtime_hotkey_shortcuts.append(shortcut)
                if key_token:
                    registered_keys.add(key_token)

        if self.sound_button_hotkey_enabled:
            for key_token, slot_key in sound_bindings.items():
                if self.sound_button_hotkey_priority == "system_first" and key_token in registered_keys:
                    continue
                seq = self._key_sequence_from_hotkey_text(key_token)
                if seq is None:
                    continue
                shortcut = QShortcut(seq, self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.activated.connect(lambda sk=slot_key: self._sound_button_hotkey_trigger(sk))
                self._runtime_hotkey_shortcuts.append(shortcut)
        self._apply_midi_bindings()

    def _runtime_action_handlers(self) -> Dict[str, Callable[[], None]]:
        return {
            "play_selected_pause": self._hotkey_play_selected_pause,
            "play_selected": self._hotkey_play_selected,
            "pause_toggle": self._toggle_pause,
            "stop_playback": self._handle_space_bar_action,
            "talk": self._hotkey_toggle_talk,
            "next_group": lambda: self._hotkey_select_group_delta(1),
            "prev_group": lambda: self._hotkey_select_group_delta(-1),
            "next_page": lambda: self._hotkey_select_page_delta(1),
            "prev_page": lambda: self._hotkey_select_page_delta(-1),
            "next_sound_button": lambda: self._hotkey_select_sound_button_delta(1),
            "prev_sound_button": lambda: self._hotkey_select_sound_button_delta(-1),
            "multi_play": lambda: self._toggle_control_button("Multi-Play"),
            "go_to_playing": self._go_to_current_playing_page,
            "loop": lambda: self._toggle_control_button("Loop"),
            "next": self._play_next,
            "rapid_fire": self._on_rapid_fire_clicked,
            "shuffle": lambda: self._toggle_control_button("Shuffle"),
            "reset_page": self._reset_current_page_state,
            "play_list": lambda: self._toggle_control_button("Play List"),
            "fade_in": lambda: self._toggle_control_button("Fade In"),
            "cross_fade": lambda: self._toggle_control_button("X"),
            "fade_out": lambda: self._toggle_control_button("Fade Out"),
            "mute": self._toggle_mute_hotkey,
            "volume_up": self._volume_up_hotkey,
            "volume_down": self._volume_down_hotkey,
        }

    def _normalized_midi_pair(self, action_key: str) -> tuple[str, str]:
        raw1, raw2 = self.midi_hotkeys.get(action_key, MIDI_HOTKEY_DEFAULTS.get(action_key, ("", "")))
        return normalize_midi_binding(raw1), normalize_midi_binding(raw2)

    def _normalize_midi_input_selectors(self, selectors: List[str]) -> List[str]:
        wanted: List[str] = []
        seen: set[str] = set()
        known_names_by_id = {str(device_id): str(device_name) for device_id, device_name in list_midi_input_devices()}
        for raw in selectors:
            token = str(raw or "").strip()
            if not token:
                continue
            if token.isdigit() and token in known_names_by_id:
                token = midi_input_name_selector(known_names_by_id[token])
            if token in seen:
                continue
            seen.add(token)
            wanted.append(token)
        return wanted

    def _apply_midi_bindings(self) -> None:
        self._midi_action_handlers = {}
        self._midi_last_trigger_t = {}
        self._midi_router.set_devices(self.midi_input_device_ids)
        runtime_handlers = self._runtime_action_handlers()
        ordered_system_keys: List[str] = [k for k in SYSTEM_HOTKEY_ORDER_DEFAULT if k in runtime_handlers]
        sound_bindings = self._collect_sound_button_midi_bindings() if self.midi_sound_button_hotkey_enabled else {}
        registered_tokens: set[str] = set()

        for key in ordered_system_keys:
            handler = runtime_handlers[key]
            m1, m2 = self._normalized_midi_pair(key)
            for token in [m1, m2]:
                if not token:
                    continue
                if self.midi_sound_button_hotkey_enabled and self.midi_sound_button_hotkey_priority == "sound_button_first":
                    if token in sound_bindings:
                        continue
                self._midi_action_handlers[token] = handler
                registered_tokens.add(token)

        if self.midi_quick_action_enabled:
            for idx, raw in enumerate(self.midi_quick_action_bindings[:48]):
                token = normalize_midi_binding(raw)
                if not token:
                    continue
                if self.midi_sound_button_hotkey_enabled and self.midi_sound_button_hotkey_priority == "sound_button_first":
                    if token in sound_bindings:
                        continue
                self._midi_action_handlers[token] = (lambda slot=idx: self._quick_action_trigger(slot))
                registered_tokens.add(token)

        if self.midi_sound_button_hotkey_enabled:
            for token, slot_key in sound_bindings.items():
                if self.midi_sound_button_hotkey_priority == "system_first" and token in registered_tokens:
                    continue
                self._midi_action_handlers[token] = (lambda sk=slot_key: self._sound_button_midi_hotkey_trigger(sk))

    def _load_asset_text_file(self, *parts: str) -> str:
        file_path = self._asset_file_path(*parts)
        if not os.path.exists(file_path):
            return f"{os.path.join(*parts)} not found at:\n{file_path}"
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin1", errors="replace") as fh:
                return fh.read()
        except Exception as exc:
            return f"Could not read {os.path.join(*parts)}:\n{exc}"

    def _open_about_window(self) -> None:
        if self._about_window is None:
            self._about_window = AboutWindowDialog(
                title="About",
                logo_path=self._asset_file_path("logo2.png"),
                parent=self,
            )
            self._about_window.destroyed.connect(lambda _=None: self._clear_about_window_ref())

        about_text = self._load_asset_text_file("about", "about.md").replace("{{VERSION}}", self.app_version_text)
        credits_text = self._load_asset_text_file("about", "credits.md")
        license_text = self._load_asset_text_file("about", "license.md")
        self._about_window.set_content(about_text=about_text, credits_text=credits_text, license_text=license_text)
        self._about_window.show()
        self._about_window.raise_()
        self._about_window.activateWindow()

    def _open_help_window(self) -> None:
        help_index = self._help_index_path()
        if not os.path.exists(help_index):
            QMessageBox.warning(
                self,
                "Help Not Found",
                "Built help index not found.\n\n"
                "Build docs first by running:\n"
                "docs\\build.bat\n\n"
                f"Expected path:\n{help_index}",
            )
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(help_index)):
            QMessageBox.warning(
                self,
                "Help Open Failed",
                f"Could not open help index with the default browser.\n\nPath:\n{help_index}",
            )

    def _open_tips_window(self, startup: bool = False) -> None:
        was_visible = self._tips_window is not None and self._tips_window.isVisible()
        if self._tips_window is None:
            self._tips_window = TipsWindow(
                language=self.ui_language,
                open_on_startup=self.tips_open_on_startup,
                parent=self,
            )
            self._tips_window.openOnStartupChanged.connect(self._on_tips_open_on_startup_changed)
            self._tips_window.destroyed.connect(lambda _=None: self._clear_tips_window_ref())
        else:
            self._tips_window.set_language(self.ui_language)
            self._tips_window.set_open_on_startup(self.tips_open_on_startup)
        if not was_visible:
            self._tips_window.pick_random_tip()
        self._tips_window.show()
        if startup:
            self._position_tips_window_for_startup()
        self._tips_window.raise_()
        self._tips_window.activateWindow()

    def _on_tips_open_on_startup_changed(self, enabled: bool) -> None:
        self.tips_open_on_startup = bool(enabled)
        if not self._suspend_settings_save:
            self._save_settings()

    def _clear_about_window_ref(self) -> None:
        self._about_window = None

    def _clear_tips_window_ref(self) -> None:
        self._tips_window = None

    def _position_tips_window_for_startup(self) -> None:
        if self._tips_window is None:
            return
        tips = self._tips_window
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        main_rect = self.frameGeometry()
        width = tips.width()
        height = tips.height()
        margin = 16

        x = main_rect.right() + margin
        y = main_rect.top() + margin
        if (x + width) > (avail.x() + avail.width() - margin):
            x = main_rect.left() - width - margin
        if x < (avail.x() + margin):
            x = avail.x() + avail.width() - width - margin

        max_x = avail.x() + avail.width() - width - margin
        max_y = avail.y() + avail.height() - height - margin
        x = max(avail.x() + margin, min(x, max_x))
        y = max(avail.y() + margin, min(y, max_y))

        candidate = QRect(x, y, width, height)
        if candidate.intersects(main_rect):
            y2 = main_rect.bottom() + margin
            y = max(avail.y() + margin, min(y2, max_y))
        tips.move(x, y)

    def _sports_sounds_pro_folder(self) -> str:
        default_path = r"C:\SportsSoundsPro"
        if os.path.isdir(default_path):
            return default_path
        if self.current_set_path:
            return os.path.dirname(self.current_set_path)
        return os.path.join(os.path.expanduser("~"), "SportsSoundsPro")

    def _page_library_folder_path(self) -> str:
        return os.path.join(self._sports_sounds_pro_folder(), "PageLib")

    def _page_display_name(self, group: str, page_index: int) -> str:
        page_name = self.page_names[group][page_index].strip()
        if page_name:
            return f"{group}{page_index + 1} ({page_name})"
        return f"{group}{page_index + 1}"

    def _iter_all_sound_button_entries(self, include_cue: bool = True) -> List[dict]:
        entries: List[dict] = []
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    title = slot.title.strip() or os.path.splitext(os.path.basename(slot.file_path))[0]
                    entries.append(
                        {
                            "group": group,
                            "page": page_index,
                            "slot": slot_index,
                            "title": title,
                            "file_path": slot.file_path,
                            "location": self._page_display_name(group, page_index),
                        }
                    )
        if include_cue:
            for slot_index, slot in enumerate(self.cue_page):
                if not slot.assigned or slot.marker:
                    continue
                title = slot.title.strip() or os.path.splitext(os.path.basename(slot.file_path))[0]
                entries.append(
                    {
                        "group": "Q",
                        "page": 0,
                        "slot": slot_index,
                        "title": title,
                        "file_path": slot.file_path,
                        "location": "Cue Page",
                    }
                )
        return entries

    def _print_lines(self, title: str, lines: List[str]) -> None:
        text = "\n".join(lines).strip() or "(no items)"
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(title)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(f"Print - {title}")
        if dialog.exec_() != QDialog.Accepted:
            return
        doc = QTextDocument()
        doc.setPlainText(text)
        doc.print_(printer)

    def _open_tool_window(
        self,
        key: str,
        title: str,
        double_click_action: str,
        show_play_button: bool,
    ) -> ToolListWindow:
        window = self._tool_windows.get(key)
        if window is not None:
            window.show()
            window.raise_()
            window.activateWindow()
            return window
        window = ToolListWindow(
            title=title,
            parent=self,
            double_click_action=double_click_action,
            show_play_button=show_play_button,
        )
        window.destroyed.connect(
            lambda _=None, k=key: (self._tool_windows.pop(k, None), self._tool_window_matches.pop(k, None))
        )
        self._tool_windows[key] = window
        return window

    def _tool_match_to_line(self, match: dict) -> str:
        return (
            f"{match['location']} - Button {int(match['slot']) + 1}: "
            f"{match['title']} | {match['file_path']}"
        )

    def _tool_hotkey_match_to_line(self, match: dict) -> str:
        return (
            f"{match['location']} - Button {int(match['slot']) + 1}: "
            f"{match['sound_hotkey']} | {match['title']} | {match['file_path']}"
        )

    def _tool_midi_match_to_line(self, match: dict) -> str:
        return (
            f"{match['location']} - Button {int(match['slot']) + 1}: "
            f"{match['sound_midi_hotkey']} | {match['title']} | {match['file_path']}"
        )

    def _tool_export_matches(self, key: str, export_format: str, base_name: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        if not matches:
            QMessageBox.information(self, "Export", "No rows to export.")
            return
        export_format = "excel" if export_format == "excel" else "csv"
        ext = ".xls" if export_format == "excel" else ".csv"
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or self._sports_sounds_pro_folder()
        initial_path = os.path.join(start_dir, f"{base_name}{ext}")
        file_filter = "Excel (*.xls)" if export_format == "excel" else "CSV (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", initial_path, f"{file_filter};;All Files (*.*)")
        if not file_path:
            return
        if not file_path.lower().endswith(ext):
            file_path = f"{file_path}{ext}"
        header = "Page,Button Number,Sound Button Name,File Path"
        try:
            self._write_csv_rows(file_path, header, matches)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Export Complete", f"Exported:\n{file_path}")

    def _print_tool_window(self, key: str, title: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        lines = [self._tool_match_to_line(match) for match in matches]
        if not lines:
            lines = ["(no items)"]
        self._print_lines(title, lines)

    def _print_hotkey_tool_window(self, key: str, title: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        lines = [self._tool_hotkey_match_to_line(match) for match in matches]
        if not lines:
            lines = ["(no items)"]
        self._print_lines(title, lines)

    def _print_midi_tool_window(self, key: str, title: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        lines = [self._tool_midi_match_to_line(match) for match in matches]
        if not lines:
            lines = ["(no items)"]
        self._print_lines(title, lines)

    def _write_csv_rows(self, file_path: str, header: str, matches: List[dict]) -> None:
        def _csv_cell(value: str) -> str:
            cell = (value or "").replace("\r", " ").replace("\n", " ")
            cell = cell.replace('"', '""')
            return f'"{cell}"'

        lines = [header]
        for match in matches:
            lines.append(
                ",".join(
                    [
                        _csv_cell(str(match["location"])),
                        _csv_cell(str(int(match["slot"]) + 1)),
                        _csv_cell(str(match["title"])),
                        _csv_cell(str(match["file_path"])),
                    ]
                )
            )
        with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("\r\n".join(lines))

    def _tool_export_sound_hotkey_matches(self, key: str, export_format: str, base_name: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        if not matches:
            QMessageBox.information(self, "Export", "No rows to export.")
            return
        export_format = "excel" if export_format == "excel" else "csv"
        ext = ".xls" if export_format == "excel" else ".csv"
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or self._sports_sounds_pro_folder()
        initial_path = os.path.join(start_dir, f"{base_name}{ext}")
        file_filter = "Excel (*.xls)" if export_format == "excel" else "CSV (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", initial_path, f"{file_filter};;All Files (*.*)")
        if not file_path:
            return
        if not file_path.lower().endswith(ext):
            file_path = f"{file_path}{ext}"

        def _csv_cell(value: str) -> str:
            cell = (value or "").replace("\r", " ").replace("\n", " ")
            cell = cell.replace('"', '""')
            return f'"{cell}"'

        lines = ["Page,Button Number,Sound Hotkey,Sound Button Name,File Path"]
        for match in matches:
            lines.append(
                ",".join(
                    [
                        _csv_cell(str(match["location"])),
                        _csv_cell(str(int(match["slot"]) + 1)),
                        _csv_cell(str(match["sound_hotkey"])),
                        _csv_cell(str(match["title"])),
                        _csv_cell(str(match["file_path"])),
                    ]
                )
            )
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
                fh.write("\r\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Export Complete", f"Exported:\n{file_path}")

    def _tool_export_sound_midi_matches(self, key: str, export_format: str, base_name: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        if not matches:
            QMessageBox.information(self, "Export", "No rows to export.")
            return
        export_format = "excel" if export_format == "excel" else "csv"
        ext = ".xls" if export_format == "excel" else ".csv"
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or self._sports_sounds_pro_folder()
        initial_path = os.path.join(start_dir, f"{base_name}{ext}")
        file_filter = "Excel (*.xls)" if export_format == "excel" else "CSV (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", initial_path, f"{file_filter};;All Files (*.*)")
        if not file_path:
            return
        if not file_path.lower().endswith(ext):
            file_path = f"{file_path}{ext}"

        def _csv_cell(value: str) -> str:
            cell = (value or "").replace("\r", " ").replace("\n", " ")
            cell = cell.replace('"', '""')
            return f'"{cell}"'

        lines = ["Page,Button Number,Sound MIDI Mapping,Sound Button Name,File Path"]
        for match in matches:
            lines.append(
                ",".join(
                    [
                        _csv_cell(str(match["location"])),
                        _csv_cell(str(int(match["slot"]) + 1)),
                        _csv_cell(str(match["sound_midi_hotkey"])),
                        _csv_cell(str(match["title"])),
                        _csv_cell(str(match["file_path"])),
                    ]
                )
            )
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
                fh.write("\r\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Export Complete", f"Exported:\n{file_path}")

    def _run_duplicate_check(self) -> None:
        entries = self._iter_all_sound_button_entries(include_cue=True)
        by_path: Dict[str, List[dict]] = {}
        for entry in entries:
            file_path = str(entry["file_path"]).strip()
            if not file_path:
                continue
            key = os.path.normcase(os.path.abspath(file_path))
            by_path.setdefault(key, []).append(entry)

        duplicate_groups = [group for group in by_path.values() if len(group) > 1]
        duplicate_groups.sort(key=lambda group: str(group[0]["file_path"]).casefold())
        matches: List[dict] = []
        for group in duplicate_groups:
            duplicate_count = len(group)
            for entry in group:
                item = dict(entry)
                item["title"] = f"{entry['title']} (duplicate x{duplicate_count})"
                matches.append(item)

        window = self._open_tool_window(
            key="duplicate_check",
            title="Duplicate Check",
            double_click_action="goto",
            show_play_button=False,
        )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=None,
            export_handler=lambda fmt: self._tool_export_matches("duplicate_check", fmt, "DuplicateCheck"),
            print_handler=lambda: self._print_tool_window("duplicate_check", "Duplicate Check"),
        )
        lines = [self._tool_match_to_line(match) for match in matches]
        status = f"{len(matches)} duplicate button(s) found."
        if not lines:
            status = "No duplicate sound buttons found."
        self._tool_window_matches["duplicate_check"] = matches
        window.set_items(lines, matches=matches, status=status)
        window.show()
        window.raise_()
        window.activateWindow()

    def _run_verify_sound_buttons(self) -> None:
        matches: List[dict] = []
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    if os.path.exists(slot.file_path):
                        continue
                    title = slot.title.strip() or os.path.splitext(os.path.basename(slot.file_path))[0]
                    matches.append(
                        {
                            "group": group,
                            "page": page_index,
                            "slot": slot_index,
                            "title": title,
                            "file_path": slot.file_path,
                            "location": self._page_display_name(group, page_index),
                        }
                    )
        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned or slot.marker:
                continue
            if os.path.exists(slot.file_path):
                continue
            title = slot.title.strip() or os.path.splitext(os.path.basename(slot.file_path))[0]
            matches.append(
                {
                    "group": "Q",
                    "page": 0,
                    "slot": slot_index,
                    "title": title,
                    "file_path": slot.file_path,
                    "location": "Cue Page",
                }
            )

        self._refresh_sound_grid()
        window = self._open_tool_window(
            key="verify_sound_buttons",
            title="Verify Sound Buttons",
            double_click_action="goto",
            show_play_button=False,
        )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=None,
            export_handler=lambda fmt: self._tool_export_matches("verify_sound_buttons", fmt, "VerifySoundButtons"),
            print_handler=lambda: self._print_tool_window("verify_sound_buttons", "Verify Sound Buttons"),
        )
        lines = [self._tool_match_to_line(match) for match in matches]
        status = f"{len(matches)} invalid button(s) found."
        if not lines:
            status = "No invalid sound button paths found."
        self._tool_window_matches["verify_sound_buttons"] = matches
        window.set_items(lines, matches=matches, status=status)
        window.show()
        window.raise_()
        window.activateWindow()

    def _disable_playlist_on_all_pages(self) -> None:
        changed = False
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                if self.page_playlist_enabled[group][page_index] or self.page_shuffle_enabled[group][page_index]:
                    changed = True
                self.page_playlist_enabled[group][page_index] = False
                self.page_shuffle_enabled[group][page_index] = False
        if not changed:
            QMessageBox.information(self, "Disable Play List on All Pages", "Play List is already disabled on all pages.")
            return
        self.current_playlist_start = None
        self._set_dirty(True)
        self._sync_playlist_shuffle_buttons()
        QMessageBox.information(self, "Disable Play List on All Pages", "Play List has been disabled on all pages.")

    def _show_page_library_folder_path(self) -> None:
        path = self._page_library_folder_path()
        box = QMessageBox(self)
        box.setWindowTitle("Page Library Folder Path")
        box.setText(f"Sports Sounds Pro Page Library folder:\n{path}")
        open_btn = box.addButton("Open Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        box.exec_()
        if box.clickedButton() == open_btn:
            self._open_directory(path)

    def _show_set_file_and_path(self) -> None:
        if self.current_set_path:
            path = os.path.dirname(self.current_set_path)
            text = f"Current .set file:\n{self.current_set_path}"
        else:
            path = self.settings.last_open_dir or self._sports_sounds_pro_folder()
            text = "No .set file is currently loaded."
        box = QMessageBox(self)
        box.setWindowTitle("Display .set File and Path")
        box.setText(text)
        open_btn = box.addButton("Open Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        box.exec_()
        if box.clickedButton() == open_btn:
            self._open_directory(path)

    def _export_page_and_sound_buttons_to_excel(self) -> None:
        if self._export_buttons_window is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Export Page and Sound Buttons")
            dialog.resize(700, 190)
            dialog.setModal(False)
            dialog.setWindowModality(Qt.NonModal)
            root = QVBoxLayout(dialog)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(8)

            dir_row = QHBoxLayout()
            dir_row.addWidget(QLabel("Directory"))
            self._export_dir_edit = QLineEdit(self._sports_sounds_pro_folder())
            dir_row.addWidget(self._export_dir_edit, 1)
            browse_btn = QPushButton("Browse")
            dir_row.addWidget(browse_btn)
            root.addLayout(dir_row)

            format_row = QHBoxLayout()
            format_row.addWidget(QLabel("Format"))
            self._export_format_combo = QComboBox()
            self._export_format_combo.addItems(["Excel (.xls)", "CSV (.csv)"])
            format_row.addWidget(self._export_format_combo)
            format_row.addStretch(1)
            root.addLayout(format_row)

            button_row = QHBoxLayout()
            button_row.addStretch(1)
            export_btn = QPushButton("Export")
            close_btn = QPushButton("Close")
            button_row.addWidget(export_btn)
            button_row.addWidget(close_btn)
            root.addLayout(button_row)

            browse_btn.clicked.connect(self._browse_export_directory)
            export_btn.clicked.connect(self._run_export_buttons_from_window)
            close_btn.clicked.connect(dialog.close)
            dialog.destroyed.connect(lambda _=None: self._clear_export_window_ref())
            self._export_buttons_window = dialog
        self._export_buttons_window.show()
        self._export_buttons_window.raise_()
        self._export_buttons_window.activateWindow()

    def _list_sound_buttons(self) -> None:
        window = self._open_tool_window(
            key="list_sound_buttons",
            title="List Sound Buttons",
            double_click_action="play",
            show_play_button=True,
        )
        window.set_note("")
        if not window.order_combo.isVisible():
            window.enable_order_controls(
                options=["Group/Page sequence", "Sound Button sequence"],
                refresh_handler=self._refresh_list_sound_buttons_window,
            )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=self._play_found_match,
            export_handler=lambda fmt: self._tool_export_matches("list_sound_buttons", fmt, "ListSoundButtons"),
            print_handler=lambda: self._print_tool_window("list_sound_buttons", "List Sound Buttons"),
        )
        if not window.current_order():
            window.order_combo.setCurrentIndex(0)
        self._refresh_list_sound_buttons_window(window.current_order())
        window.show()
        window.raise_()
        window.activateWindow()

    def _list_sound_button_hotkeys(self) -> None:
        window = self._open_tool_window(
            key="list_sound_button_hotkeys",
            title="List Sound Button Hot Key",
            double_click_action="play",
            show_play_button=True,
        )
        window.set_note(
            "Note: Sound Button Hot Key only works when enabled in Options > Hotkey. "
            f"Current priority: {'Sound Button Hot Key first' if self.sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        if not window.order_combo.isVisible():
            window.enable_order_controls(
                options=["Group/Page sequence", "Hotkey sequence"],
                refresh_handler=self._refresh_list_sound_button_hotkeys_window,
            )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=self._play_found_match,
            export_handler=lambda fmt: self._tool_export_sound_hotkey_matches(
                "list_sound_button_hotkeys",
                fmt,
                "ListSoundButtonHotKeys",
            ),
            print_handler=lambda: self._print_hotkey_tool_window("list_sound_button_hotkeys", "List Sound Button Hot Key"),
        )
        if not window.current_order():
            window.order_combo.setCurrentIndex(0)
        self._refresh_list_sound_button_hotkeys_window(window.current_order())
        window.show()
        window.raise_()
        window.activateWindow()

    def _list_sound_device_midi_mappings(self) -> None:
        window = self._open_tool_window(
            key="list_sound_device_midi_mappings",
            title="List Sound Device MIDI Mapping",
            double_click_action="play",
            show_play_button=True,
        )
        window.set_note(
            "Note: Sound Button MIDI Hot Key only works when enabled in Options > Midi Control > Sound Button Hot Key. "
            f"Current priority: {'Sound Button MIDI Hot Key first' if self.midi_sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        if not window.order_combo.isVisible():
            window.enable_order_controls(
                options=["Group/Page sequence", "MIDI mapping sequence"],
                refresh_handler=self._refresh_list_sound_device_midi_mappings_window,
            )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=self._play_found_match,
            export_handler=lambda fmt: self._tool_export_sound_midi_matches(
                "list_sound_device_midi_mappings",
                fmt,
                "ListSoundDeviceMidiMappings",
            ),
            print_handler=lambda: self._print_midi_tool_window(
                "list_sound_device_midi_mappings",
                "List Sound Device MIDI Mapping",
            ),
        )
        if not window.current_order():
            window.order_combo.setCurrentIndex(0)
        self._refresh_list_sound_device_midi_mappings_window(window.current_order())
        window.show()
        window.raise_()
        window.activateWindow()

    def _refresh_list_sound_buttons_window(self, selected_order: str) -> None:
        matches: List[dict] = self._iter_all_sound_button_entries(include_cue=True)
        if selected_order == "Sound Button sequence":
            matches.sort(
                key=lambda entry: (
                    str(entry["title"]).casefold(),
                    str(entry["file_path"]).casefold(),
                    str(entry["location"]).casefold(),
                    int(entry["slot"]),
                )
            )
        window = self._tool_windows.get("list_sound_buttons")
        if window is None:
            return
        self._tool_window_matches["list_sound_buttons"] = matches
        lines = [self._tool_match_to_line(entry) for entry in matches]
        status = f"{len(matches)} sound button(s)."
        if not lines:
            status = "No sound buttons assigned."
        window.set_items(lines, matches=matches, status=status)

    def _refresh_list_sound_button_hotkeys_window(self, selected_order: str) -> None:
        matches: List[dict] = []
        for entry in self._iter_all_sound_button_entries(include_cue=True):
            slot = self._slot_for_location(str(entry["group"]), int(entry["page"]), int(entry["slot"]))
            token = self._parse_sound_hotkey(slot.sound_hotkey)
            if not token:
                continue
            item = dict(entry)
            item["sound_hotkey"] = token
            matches.append(item)
        if selected_order == "Hotkey sequence":
            matches.sort(
                key=lambda entry: (
                    str(entry["sound_hotkey"]).casefold(),
                    str(entry["location"]).casefold(),
                    int(entry["slot"]),
                )
            )
        window = self._tool_windows.get("list_sound_button_hotkeys")
        if window is None:
            return
        window.set_note(
            "Note: Sound Button Hot Key only works when enabled in Options > Hotkey. "
            f"Current priority: {'Sound Button Hot Key first' if self.sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        self._tool_window_matches["list_sound_button_hotkeys"] = matches
        lines = [self._tool_hotkey_match_to_line(entry) for entry in matches]
        status = f"{len(matches)} sound button hot key assignment(s)."
        if not lines:
            status = "No sound button hot keys assigned."
        window.set_items(lines, matches=matches, status=status)

    def _refresh_list_sound_device_midi_mappings_window(self, selected_order: str) -> None:
        matches: List[dict] = []
        for entry in self._iter_all_sound_button_entries(include_cue=True):
            slot = self._slot_for_location(str(entry["group"]), int(entry["page"]), int(entry["slot"]))
            token = normalize_midi_binding(slot.sound_midi_hotkey)
            if not token:
                continue
            item = dict(entry)
            item["sound_midi_hotkey"] = token
            matches.append(item)
        if selected_order == "MIDI mapping sequence":
            matches.sort(
                key=lambda entry: (
                    str(entry["sound_midi_hotkey"]).casefold(),
                    str(entry["location"]).casefold(),
                    int(entry["slot"]),
                )
            )
        window = self._tool_windows.get("list_sound_device_midi_mappings")
        if window is None:
            return
        window.set_note(
            "Note: Sound Button MIDI Hot Key only works when enabled in Options > Midi Control > Sound Button Hot Key. "
            f"Current priority: {'Sound Button MIDI Hot Key first' if self.midi_sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        self._tool_window_matches["list_sound_device_midi_mappings"] = matches
        lines = [self._tool_midi_match_to_line(entry) for entry in matches]
        status = f"{len(matches)} sound button MIDI mapping assignment(s)."
        if not lines:
            status = "No sound button MIDI mappings assigned."
        window.set_items(lines, matches=matches, status=status)

    def _browse_export_directory(self) -> None:
        if self._export_dir_edit is None:
            return
        start_dir = self._export_dir_edit.text().strip() or self._sports_sounds_pro_folder()
        directory = QFileDialog.getExistingDirectory(self, "Select Export Directory", start_dir)
        if not directory:
            return
        self._export_dir_edit.setText(directory)

    def _run_export_buttons_from_window(self) -> None:
        if self._export_dir_edit is None or self._export_format_combo is None:
            return
        export_dir = self._export_dir_edit.text().strip() or self._sports_sounds_pro_folder()
        os.makedirs(export_dir, exist_ok=True)
        selected = self._export_format_combo.currentText().strip().lower()
        extension = ".xls" if selected.startswith("excel") else ".csv"
        export_path = os.path.join(export_dir, f"SSPExportToExcel{extension}")
        matches = self._iter_all_sound_button_entries(include_cue=True)
        try:
            self._write_csv_rows(export_path, "Page,Button Number,Sound Button Name,File Path", matches)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = export_dir
        self._save_settings()
        box = QMessageBox(self)
        box.setWindowTitle("Export Complete")
        box.setText(f"Exported:\n{export_path}")
        open_btn = box.addButton("Open Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        box.exec_()
        if box.clickedButton() == open_btn:
            self._open_directory(export_dir)

    def _clear_export_window_ref(self) -> None:
        self._export_buttons_window = None
        self._export_dir_edit = None
        self._export_format_combo = None

    def _open_directory(self, path: str) -> None:
        if not path:
            return
        os.makedirs(path, exist_ok=True)
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:
            QMessageBox.warning(self, "Open Folder", f"Could not open folder:\n{exc}")

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        group_grid = QGridLayout()
        group_grid.setContentsMargins(0, 0, 0, 0)
        group_grid.setHorizontalSpacing(2)
        group_grid.setVerticalSpacing(2)

        for i, group in enumerate(GROUPS):
            button = GroupButton(group, self)
            button.setMinimumSize(40, 40)
            button.setStyleSheet("font-size: 18pt; font-weight: bold;")
            button.clicked.connect(lambda _=False, g=group: self._select_group(g))
            row = 0 if i < 5 else 1
            col = i % 5
            group_grid.addWidget(button, row, col)
            self.group_buttons[group] = button

        layout.addLayout(group_grid)

        self.page_list.setAlternatingRowColors(True)
        self.page_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_list.setSpacing(0)
        self.page_list.currentRowChanged.connect(self._select_page)
        self.page_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.page_list.customContextMenuRequested.connect(self._show_page_menu)
        self.page_list.setAcceptDrops(True)
        self.page_list.viewport().setAcceptDrops(True)
        self.page_list.viewport().installEventFilter(self)
        layout.addWidget(self.page_list, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top = self._build_top_controls()
        layout.addWidget(top, 1)

        grid_container = QFrame()
        grid_container.setFrameShape(QFrame.StyledPanel)
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(1)

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                idx = row * GRID_COLS + col
                button = SoundButton(idx, self)
                button.clicked.connect(lambda _=False, slot=idx: self._on_sound_button_clicked(slot))
                self.sound_buttons.append(button)
                grid_layout.addWidget(button, row, col)
        for row in range(GRID_ROWS):
            grid_layout.setRowStretch(row, 1)
        for col in range(GRID_COLS):
            grid_layout.setColumnStretch(col, 1)

        layout.addWidget(grid_container, 3)
        return panel

    def _build_top_controls(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        controls = [
            "Cue", "Multi-Play", "DSP",
            "Go To Playing",
            "Loop", "Next", "Button Drag", "Pause",
            "Rapid Fire", "Shuffle", "Reset Page", "STOP",
            "Talk", "Play List", "Search",
        ]
        positions = {
            "Cue": (0, 0, 1, 1),
            "Multi-Play": (0, 1, 1, 1),
            "Go To Playing": (0, 2, 1, 1),
            "DSP": (0, 3, 1, 1),
            "Loop": (1, 0, 1, 1),
            "Next": (1, 1, 1, 1),
            "Button Drag": (1, 2, 1, 1),
            "Pause": (1, 3, 1, 1),
            "Rapid Fire": (2, 0, 1, 1),
            "Shuffle": (2, 1, 1, 1),
            "Reset Page": (2, 2, 1, 1),
            "STOP": (2, 3, 2, 1),
            "Talk": (3, 0, 1, 1),
            "Play List": (3, 1, 1, 1),
            "Search": (3, 2, 1, 1),
        }
        ctl_grid = QGridLayout()
        ctl_grid.setContentsMargins(0, 0, 0, 0)
        ctl_grid.setSpacing(2)
        for text in controls:
            btn = QPushButton(text)
            btn.setMinimumHeight(42)
            if text == "Pause":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                btn.clicked.connect(self._toggle_pause)
            elif text == "STOP":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
                btn.clicked.connect(self._stop_playback)
                btn.setMinimumHeight(86)
            elif text == "Next":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                btn.clicked.connect(self._play_next)
                btn.setEnabled(False)
            elif text == "Cue":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_cue_mode)
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(self._show_cue_button_menu)
            elif text == "Loop":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_loop)
            elif text == "Multi-Play":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_multi_play_mode)
            elif text == "Button Drag":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_button_drag_mode)
            elif text == "Rapid Fire":
                btn.clicked.connect(self._on_rapid_fire_clicked)
            elif text == "Reset Page":
                btn.clicked.connect(self._reset_current_page_state)
            elif text == "Talk":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_talk)
            elif text == "Play List":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_playlist_mode)
            elif text == "Shuffle":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_shuffle_mode)
                btn.setEnabled(False)
            elif text == "Search":
                btn.clicked.connect(self._open_find_dialog)
            elif text == "DSP":
                btn.clicked.connect(self._open_dsp_window)
            elif text == "Go To Playing":
                btn.clicked.connect(self._go_to_current_playing_page)
            if text in {"Pause", "STOP", "Next", "Loop", "Reset Page", "Talk", "Cue", "Play List", "Shuffle", "Rapid Fire", "Multi-Play", "Button Drag"}:
                self.control_buttons[text] = btn
            row, col, row_span, col_span = positions[text]
            ctl_grid.addWidget(btn, row, col, row_span, col_span)
        left_layout.addLayout(ctl_grid)

        self.group_status.setStyleSheet("font-size: 22pt; color: #0A29E0; font-weight: bold;")
        left_layout.addWidget(self.group_status)
        self.page_status.setStyleSheet("font-size: 18pt; color: #0A29E0; font-weight: bold;")
        left_layout.addWidget(self.page_status)
        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        fade_row = QHBoxLayout()
        fade_specs = [
            ("Fade In", self._toggle_fade_in_mode, "Fade in on start"),
            ("X", self._toggle_cross_auto_mode, "Cross fade (fade out + fade in)"),
            ("Fade Out", self._toggle_fade_out_mode, "Fade out on stop/switch"),
        ]
        for label, handler, tooltip in fade_specs:
            b = QPushButton(label)
            b.setMinimumHeight(38)
            b.setCheckable(True)
            b.setToolTip(tooltip)
            b.clicked.connect(handler)
            self.control_buttons[label] = b
            fade_row.addWidget(b)
        right_layout.addLayout(fade_row)

        meter_row = QHBoxLayout()
        meter_labels = QVBoxLayout()
        meter_labels.addWidget(QLabel("Left"))
        meter_labels.addWidget(QLabel("Right"))
        meter_row.addLayout(meter_labels)

        meters = QVBoxLayout()
        self.left_meter.setRange(0, 100)
        self.right_meter.setRange(0, 100)
        self.left_meter.setTextVisible(False)
        self.right_meter.setTextVisible(False)
        meters.addWidget(self.left_meter)
        meters.addWidget(self.right_meter)
        meter_row.addLayout(meters, 1)
        right_layout.addLayout(meter_row)

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("Volume"))
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(90)
        self.volume_slider.setFixedWidth(140)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_row.addWidget(self.volume_slider)
        volume_row.addStretch(1)
        right_layout.addLayout(volume_row)

        times = QHBoxLayout()
        for title, value in [
            ("Total Time", self.total_time),
            ("Elapsed", self.elapsed_time),
            ("Remaining", self.remaining_time),
        ]:
            box = QFrame()
            box.setFrameShape(QFrame.StyledPanel)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(8, 2, 8, 2)
            label = QLabel(title)
            label.setStyleSheet("font-size: 16pt; font-weight: bold;")
            value.setStyleSheet("font-size: 30pt; font-weight: bold;")
            value.setAlignment(Qt.AlignCenter)
            box_layout.addWidget(label)
            box_layout.addWidget(value)
            times.addWidget(box, 1)
        right_layout.addLayout(times)

        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: white;")
        self.progress_label.setMinimumHeight(28)
        self.progress_label.set_display_mode(self.main_progress_display_mode)
        self.progress_label.setVisible(True)
        right_layout.addWidget(self.progress_label)

        transport_row = QHBoxLayout()
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.valueChanged.connect(self._on_seek_value_changed)
        transport_row.addWidget(self.seek_slider, 1)
        right_layout.addLayout(transport_row)

        jog_meta_row = QHBoxLayout()
        self.jog_percent_label.setAlignment(Qt.AlignCenter)
        self.jog_out_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        jog_meta_row.addWidget(self.jog_in_label)
        jog_meta_row.addStretch(1)
        jog_meta_row.addWidget(self.jog_percent_label)
        jog_meta_row.addStretch(1)
        jog_meta_row.addWidget(self.jog_out_label)
        right_layout.addLayout(jog_meta_row)

        self.now_playing_label.setStyleSheet("font-size: 10pt; color: #101010; background: #EFEFEF;")
        self.now_playing_label.setMinimumHeight(24)
        self.now_playing_label.setText("NOW PLAYING:")
        self.now_playing_label.setVisible(True)
        right_layout.addWidget(self.now_playing_label)

        layout.addWidget(left, 2)
        layout.addWidget(right, 3)
        return panel

    def _select_group(self, group: str) -> None:
        self.cue_mode = False
        self._hotkey_selected_slot_key = None
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(False)
        self.current_group = group
        self.current_page = 0
        self.current_playlist_start = None
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()

    def _select_page(self, index: int) -> None:
        if index < 0:
            return
        if self.cue_mode:
            self.current_page = 0
            self._hotkey_selected_slot_key = None
            self._update_page_status()
            self._queue_current_page_audio_preload()
            return
        self.current_page = index
        self._hotkey_selected_slot_key = None
        self.current_playlist_start = None
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_page_status()
        self._queue_current_page_audio_preload()

    def _refresh_group_buttons(self) -> None:
        for group, button in self.group_buttons.items():
            if group == self.current_group:
                button.setStyleSheet(
                    f"background: {self.active_group_color}; font-size: 18pt; font-weight: bold; border: 1px solid #7C7C7C;"
                )
            else:
                button.setStyleSheet(
                    f"background: {self.inactive_group_color}; font-size: 18pt; font-weight: bold; border: 1px solid #8A8A8A;"
                )

    def _refresh_page_list(self) -> None:
        self.page_list.blockSignals(True)
        self.page_list.clear()
        if self.cue_mode:
            cue_item = QListWidgetItem(tr("Cue Page"))
            cue_item.setTextAlignment(Qt.AlignCenter)
            self.page_list.addItem(cue_item)
            self.page_list.setCurrentRow(0)
            self._update_page_list_item_heights()
            self.page_list.blockSignals(False)
            return
        pages = self.data[self.current_group]
        for i, page in enumerate(pages):
            has_sound = any(slot.assigned for slot in page)
            page_name = self.page_names[self.current_group][i].strip()
            if page_name:
                text = page_name
            elif has_sound:
                text = f"{tr('Page ')}{self.current_group.lower()} {i + 1}"
            else:
                text = tr("(Blank Page)")
            item = QListWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            page_color = self.page_colors[self.current_group][i]
            if page_color:
                item.setBackground(QColor(page_color))
                item.setForeground(QColor("#000000" if self._is_light_color(page_color) else "#FFFFFF"))
            self.page_list.addItem(item)
        self.page_list.setCurrentRow(self.current_page)
        self._update_page_list_item_heights()
        self.page_list.blockSignals(False)

    def _update_page_list_item_heights(self) -> None:
        count = self.page_list.count()
        if count <= 0:
            return
        available = max(1, self.page_list.viewport().height())
        item_h = max(24, int(available / count))
        for i in range(count):
            item = self.page_list.item(i)
            item.setSizeHint(QSize(10, item_h))
        self.page_list.doItemsLayout()

    def _is_light_color(self, color_hex: str) -> bool:
        color = color_hex.strip()
        if len(color) != 7 or not color.startswith("#"):
            return True
        try:
            red = int(color[1:3], 16)
            green = int(color[3:5], 16)
            blue = int(color[5:7], 16)
        except ValueError:
            return True
        luminance = (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)
        return luminance >= 150.0

    def _show_page_menu(self, pos) -> None:
        if self.cue_mode:
            return
        item = self.page_list.itemAt(pos)
        row = item and self.page_list.row(item)
        if row is None or row < 0 or row >= PAGE_COUNT:
            row = self.current_page
        if row < 0 or row >= PAGE_COUNT:
            return

        page_created = self._is_page_created(self.current_group, row)
        menu = QMenu(self)

        add_action = menu.addAction("Add Page")
        add_action.setEnabled(not page_created)

        rename_action = menu.addAction("Rename Page")
        rename_action.setEnabled(page_created)

        delete_action = menu.addAction("Delete Page")
        delete_action.setEnabled(page_created)

        menu.addSeparator()
        copy_action = menu.addAction("Copy Page")
        paste_action = menu.addAction("Paste Page")
        paste_action.setEnabled(self._copied_page_buffer is not None)
        menu.addSeparator()
        import_action = menu.addAction("Import Page...")
        export_action = menu.addAction("Export Page...")
        export_action.setEnabled(page_created)
        menu.addSeparator()
        change_color_action = menu.addAction("Change Page Color...")
        clear_color_action = menu.addAction("Clear Page Color")
        clear_color_action.setEnabled(bool(self.page_colors[self.current_group][row]))

        selected = menu.exec_(self.page_list.mapToGlobal(pos))
        if selected == add_action:
            self._add_page(row)
        elif selected == rename_action:
            self._rename_page(row)
        elif selected == delete_action:
            self._delete_page(row)
        elif selected == copy_action:
            self._copy_page(row)
        elif selected == paste_action:
            self._paste_page(row)
        elif selected == import_action:
            self._import_page(row)
        elif selected == export_action:
            self._export_page(row)
        elif selected == change_color_action:
            self._change_page_color(row)
        elif selected == clear_color_action:
            self._clear_page_color(row)

    def _change_page_color(self, page_index: int) -> None:
        current = self.page_colors[self.current_group][page_index] or "#C0C0C0"
        color = QColorDialog.getColor(QColor(current), self, "Page Button Color")
        if not color.isValid():
            return
        self.page_colors[self.current_group][page_index] = color.name().upper()
        self._set_dirty(True)
        self._refresh_page_list()

    def _clear_page_color(self, page_index: int) -> None:
        if not self.page_colors[self.current_group][page_index]:
            return
        self.page_colors[self.current_group][page_index] = None
        self._set_dirty(True)
        self._refresh_page_list()

    def _is_page_blank(self, page: List[SoundButtonData]) -> bool:
        return not any(slot.assigned or slot.title for slot in page)

    def _add_page(self, page_index: int) -> None:
        name, ok = QInputDialog.getText(self, "Page Name", "Enter page name:")
        if not ok:
            return
        page_name = name.strip()
        if not page_name:
            QMessageBox.information(self, "Page Name", "Page name is required.")
            return
        self.page_names[self.current_group][page_index] = page_name
        self.current_page = page_index
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_page_status()
        self._set_dirty(True)

    def _rename_page(self, page_index: int) -> None:
        current_name = self.page_names[self.current_group][page_index].strip()
        if not current_name:
            current_name = f"Page {self.current_group.lower()} {page_index + 1}"
        name, ok = QInputDialog.getText(self, "Rename Page", "Page name:", text=current_name)
        if not ok:
            return
        self.page_names[self.current_group][page_index] = name.strip()
        self._set_dirty(True)
        self._refresh_page_list()
        if self.current_page == page_index:
            self._update_page_status()

    def _delete_page(self, page_index: int) -> None:
        answer = QMessageBox.question(
            self,
            "Delete Page",
            "Delete this page and clear all its sound buttons?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.data[self.current_group][page_index] = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self.page_names[self.current_group][page_index] = ""
        self.page_colors[self.current_group][page_index] = None
        self.page_playlist_enabled[self.current_group][page_index] = False
        self.page_shuffle_enabled[self.current_group][page_index] = False
        if self.current_page == page_index:
            self.current_playlist_start = None
            self._sync_playlist_shuffle_buttons()
            self._refresh_sound_grid()
            self._update_page_status()
        self._set_dirty(True)
        self._refresh_page_list()

    def _copy_page(self, page_index: int) -> None:
        source_page = self.data[self.current_group][page_index]
        self._copied_page_buffer = {
            "slots": [
                SoundButtonData(
                    file_path=slot.file_path,
                    title=slot.title,
                    notes=slot.notes,
                    duration_ms=slot.duration_ms,
                    custom_color=slot.custom_color,
                    highlighted=slot.highlighted,
                    played=slot.played,
                    activity_code=slot.activity_code,
                    locked=slot.locked,
                    marker=slot.marker,
                    copied_to_cue=slot.copied_to_cue,
                    load_failed=slot.load_failed,
                    volume_override_pct=slot.volume_override_pct,
                    cue_start_ms=slot.cue_start_ms,
                    cue_end_ms=slot.cue_end_ms,
                    sound_hotkey=slot.sound_hotkey,
                    sound_midi_hotkey=slot.sound_midi_hotkey,
                )
                for slot in source_page
            ],
            "page_name": self.page_names[self.current_group][page_index],
            "page_color": self.page_colors[self.current_group][page_index],
            "playlist": self.page_playlist_enabled[self.current_group][page_index],
            "shuffle": self.page_shuffle_enabled[self.current_group][page_index],
        }

    def _paste_page(self, page_index: int) -> None:
        if not self._copied_page_buffer:
            return
        self.data[self.current_group][page_index] = [
            SoundButtonData(
                file_path=slot.file_path,
                title=slot.title,
                notes=slot.notes,
                duration_ms=slot.duration_ms,
                custom_color=slot.custom_color,
                highlighted=slot.highlighted,
                played=slot.played,
                activity_code=slot.activity_code,
                locked=slot.locked,
                marker=slot.marker,
                copied_to_cue=slot.copied_to_cue,
                load_failed=slot.load_failed,
                volume_override_pct=slot.volume_override_pct,
                cue_start_ms=slot.cue_start_ms,
                cue_end_ms=slot.cue_end_ms,
                sound_hotkey=slot.sound_hotkey,
                sound_midi_hotkey=slot.sound_midi_hotkey,
            )
            for slot in self._copied_page_buffer["slots"]
        ]
        self.page_names[self.current_group][page_index] = str(self._copied_page_buffer["page_name"])
        self.page_colors[self.current_group][page_index] = self._copied_page_buffer.get("page_color")
        self.page_playlist_enabled[self.current_group][page_index] = bool(self._copied_page_buffer["playlist"])
        self.page_shuffle_enabled[self.current_group][page_index] = bool(self._copied_page_buffer["shuffle"])
        if self.current_page == page_index:
            self.current_playlist_start = None
            self._sync_playlist_shuffle_buttons()
            self._refresh_sound_grid()
            self._update_page_status()
        self._set_dirty(True)
        self._refresh_page_list()

    def _export_page(self, page_index: int) -> None:
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or os.path.expanduser("~")
        default_name = f"{self.current_group}{page_index + 1}.lib"
        initial_path = os.path.join(start_dir, default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Page Library",
            initial_path,
            "Sports Sounds Pro Page Library (*.lib);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".lib"):
            file_path = f"{file_path}.lib"
        try:
            self._write_page_library_file(file_path, self.current_group, page_index)
        except Exception as exc:
            QMessageBox.critical(self, "Export Page Failed", f"Could not export page:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        self._show_save_notice_banner(f"Page Exported: {file_path}")

    def _import_page(self, page_index: int) -> None:
        start_dir = self.settings.last_open_dir or self.settings.last_save_dir or os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Page Library",
            start_dir,
            "Sports Sounds Pro Page Library (*.lib);;All Files (*.*)",
        )
        if not file_path:
            return
        if self._is_page_created(self.current_group, page_index):
            answer = QMessageBox.question(
                self,
                "Import Page",
                "This page already has content. Replace it with imported page?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        try:
            imported = self._read_page_library_file(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Import Page Failed", f"Could not import page:\n{exc}")
            return

        self.page_names[self.current_group][page_index] = imported["page_name"]
        self.page_colors[self.current_group][page_index] = imported.get("page_color")
        self.page_playlist_enabled[self.current_group][page_index] = imported["page_playlist_enabled"]
        self.page_shuffle_enabled[self.current_group][page_index] = imported["page_shuffle_enabled"]
        self.data[self.current_group][page_index] = imported["slots"]
        self.current_page = page_index
        self.current_playlist_start = None
        self.settings.last_open_dir = os.path.dirname(file_path)
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_page_status()
        self._set_dirty(True)
        self._save_settings()

    def _write_page_library_file(self, file_path: str, group: str, page_index: int) -> None:
        lines: List[str] = [
            "[Main]",
            "CreatedBy=SportsSoundsPro Page Library",
            "",
            "[Page]",
        ]
        page_name = clean_set_value(self.page_names[group][page_index]) or " "
        lines.append(f"PageName={page_name}")
        lines.append(f"PagePlay={'T' if self.page_playlist_enabled[group][page_index] else 'F'}")
        lines.append(f"PageShuffle={'T' if self.page_shuffle_enabled[group][page_index] else 'F'}")
        lines.append(f"PageColor={to_set_color_value(self.page_colors[group][page_index])}")
        page = self.data[group][page_index]
        for slot_index, slot in enumerate(page, start=1):
            if not slot.assigned and not slot.title:
                continue
            if slot.marker:
                marker_title = clean_set_value(slot.title)
                lines.append(f"c{slot_index}={(marker_title + '%%') if marker_title else '%%'}")
                lines.append(f"t{slot_index}= ")
                lines.append(f"activity{slot_index}=7")
                lines.append(f"co{slot_index}=clBtnFace")
                continue
            title = clean_set_value(slot.title or os.path.splitext(os.path.basename(slot.file_path))[0])
            notes = clean_set_value(slot.notes or title)
            lines.append(f"c{slot_index}={notes}")
            lines.append(f"s{slot_index}={clean_set_value(slot.file_path)}")
            lines.append(f"t{slot_index}={format_set_time(slot.duration_ms)}")
            lines.append(f"n{slot_index}={title}")
            if slot.volume_override_pct is not None:
                lines.append(f"v{slot_index}={max(0, min(100, int(slot.volume_override_pct)))}")
            hotkey_code = self._encode_sound_hotkey(slot.sound_hotkey)
            if hotkey_code:
                lines.append(f"h{slot_index}={hotkey_code}")
            midi_hotkey_code = self._encode_sound_midi_hotkey(slot.sound_midi_hotkey)
            if midi_hotkey_code:
                lines.append(f"pysspmidi{slot_index}={midi_hotkey_code}")
            lines.append(f"activity{slot_index}={'2' if slot.played else '8'}")
            lines.append(f"co{slot_index}={to_set_color_value(slot.custom_color)}")
            if slot.copied_to_cue:
                lines.append(f"ci{slot_index}=Y")
            cue_start, cue_end = self._cue_time_fields_for_set(slot)
            if cue_start is not None:
                lines.append(f"pysspcuestart{slot_index}={cue_start}")
            if cue_end is not None:
                lines.append(f"pysspcueend{slot_index}={cue_end}")
        lines.append("")
        payload = "\r\n".join(lines)
        with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(payload)

    def _read_page_library_file(self, file_path: str) -> dict:
        raw = open(file_path, "rb").read()
        text = None
        for encoding in ("utf-8-sig", "utf-16", "gbk", "cp1252", "latin1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("latin1", errors="replace")

        parser = configparser.RawConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read_string(text)
        section_name = "Page"
        if not parser.has_section(section_name):
            raise ValueError("Page section not found in .lib file.")
        section = parser[section_name]

        page_name = section.get("PageName", "").strip()
        page_color = parse_delphi_color(section.get("PageColor", "").strip())
        page_playlist_enabled = section.get("PagePlay", "F").strip().upper() == "T"
        page_shuffle_enabled = section.get("PageShuffle", "F").strip().upper() == "T"
        slots = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        for i in range(1, SLOTS_PER_PAGE + 1):
            path = section.get(f"s{i}", "").strip()
            caption = section.get(f"c{i}", "").strip()
            name = section.get(f"n{i}", "").strip()
            title = (name or caption)
            notes = caption
            activity_code = section.get(f"activity{i}", "").strip()
            marker = False
            if caption.endswith("%%"):
                marker = True
                if not name:
                    title = caption[:-2].strip()
                notes = caption[:-2].strip()
            if activity_code == "7":
                marker = True
            if not path and not title and not marker:
                continue
            if not title and path:
                title = os.path.splitext(os.path.basename(path))[0]
            duration = parse_time_string_to_ms(section.get(f"t{i}", "").strip())
            color = parse_delphi_color(section.get(f"co{i}", "").strip())
            volume_override_pct = self._parse_volume_override_pct(section.get(f"v{i}", "").strip())
            sound_hotkey = self._parse_sound_hotkey(section.get(f"h{i}", "").strip())
            cue_start_raw = section.get(f"pysspcuestart{i}", "").strip()
            cue_end_raw = section.get(f"pysspcueend{i}", "").strip()
            if cue_start_raw or cue_end_raw:
                cue_start_ms = self._parse_cue_time_string_to_ms(cue_start_raw)
                cue_end_ms = self._parse_cue_time_string_to_ms(cue_end_raw)
                cue_start_ms, cue_end_ms = self._normalize_cue_points(cue_start_ms, cue_end_ms, duration)
            else:
                cue_start_ms, cue_end_ms = self._parse_cue_points(
                    section.get(f"cs{i}", "").strip(),
                    section.get(f"ce{i}", "").strip(),
                    duration,
                )
            played = activity_code == "2"
            copied = section.get(f"ci{i}", "").strip().upper() == "Y"
            slots[i - 1] = SoundButtonData(
                file_path=path,
                title=title,
                notes=notes,
                duration_ms=duration,
                custom_color=color,
                played=played,
                activity_code=activity_code or ("2" if played else "8"),
                marker=marker,
                copied_to_cue=copied,
                volume_override_pct=volume_override_pct,
                cue_start_ms=cue_start_ms,
                cue_end_ms=cue_end_ms,
                sound_hotkey=sound_hotkey,
                sound_midi_hotkey=self._parse_sound_midi_hotkey(section.get(f"pysspmidi{i}", "").strip()),
            )
        return {
            "page_name": page_name,
            "page_color": page_color,
            "page_playlist_enabled": page_playlist_enabled,
            "page_shuffle_enabled": page_shuffle_enabled,
            "slots": slots,
        }

    def _refresh_sound_grid(self) -> None:
        page = self._current_page_slots()
        sound_bindings = self._collect_sound_button_hotkey_bindings() if self.sound_button_hotkey_enabled else {}
        blocked_sound_tokens = (
            self._registered_system_and_quick_tokens()
            if self.sound_button_hotkey_enabled and self.sound_button_hotkey_priority == "system_first"
            else set()
        )
        for i, button in enumerate(self.sound_buttons):
            slot = page[i]
            button.set_ram_loaded(False)
            if slot.marker:
                button.setText(elide_text(slot.title, self.title_char_limit))
                button.setToolTip("")
            elif not slot.assigned:
                button.setText("")
                button.setToolTip("")
            else:
                button.set_ram_loaded(is_audio_preloaded(slot.file_path))
                has_cue = self._slot_has_custom_cue(slot)
                parts: List[str] = []
                if slot.volume_override_pct is not None:
                    parts.append("V")
                if has_cue:
                    parts.append("C")
                for badge in self._active_button_trigger_badges(i, slot, sound_bindings, blocked_sound_tokens):
                    parts.append(badge)
                suffix = f" {' '.join(parts)}" if parts else ""
                button.setText(f"{elide_text(slot.title, self.title_char_limit)}\n{format_time(slot.duration_ms)}{suffix}")
                button.setToolTip(slot.notes.strip())
            color = self._slot_color(slot, i)
            text_color = self.sound_button_text_color
            has_volume_override = (slot.volume_override_pct is not None) and slot.assigned and (not slot.marker)
            has_cue = self._slot_has_custom_cue(slot) and slot.assigned and (not slot.marker)
            has_midi_hotkey = bool(normalize_midi_binding(slot.sound_midi_hotkey)) and slot.assigned and (not slot.marker)
            if has_midi_hotkey and has_volume_override and has_cue:
                background = (
                    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                    f"stop:0 {self.state_colors['midi_indicator']}, stop:0.11 {self.state_colors['midi_indicator']}, "
                    f"stop:0.12 {color}, stop:0.74 {color}, "
                    f"stop:0.75 {self.state_colors['cue_indicator']}, stop:0.87 {self.state_colors['cue_indicator']}, "
                    f"stop:0.88 {self.state_colors['volume_indicator']}, stop:1 {self.state_colors['volume_indicator']})"
                )
            elif has_midi_hotkey and has_volume_override:
                background = (
                    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                    f"stop:0 {self.state_colors['midi_indicator']}, stop:0.11 {self.state_colors['midi_indicator']}, "
                    f"stop:0.12 {color}, stop:0.82 {color}, "
                    f"stop:0.83 {self.state_colors['volume_indicator']}, stop:1 {self.state_colors['volume_indicator']})"
                )
            elif has_midi_hotkey and has_cue:
                background = (
                    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                    f"stop:0 {self.state_colors['midi_indicator']}, stop:0.11 {self.state_colors['midi_indicator']}, "
                    f"stop:0.12 {color}, stop:0.82 {color}, "
                    f"stop:0.83 {self.state_colors['cue_indicator']}, stop:1 {self.state_colors['cue_indicator']})"
                )
            elif has_midi_hotkey:
                background = (
                    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                    f"stop:0 {self.state_colors['midi_indicator']}, stop:0.11 {self.state_colors['midi_indicator']}, "
                    f"stop:0.12 {color}, stop:1 {color})"
                )
            elif has_volume_override and has_cue:
                background = (
                    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                    f"stop:0 {color}, stop:0.74 {color}, "
                    f"stop:0.75 {self.state_colors['cue_indicator']}, stop:0.87 {self.state_colors['cue_indicator']}, "
                    f"stop:0.88 {self.state_colors['volume_indicator']}, stop:1 {self.state_colors['volume_indicator']})"
                )
            elif has_volume_override:
                background = (
                    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                    f"stop:0 {color}, stop:0.82 {color}, stop:0.83 {self.state_colors['volume_indicator']}, stop:1 {self.state_colors['volume_indicator']})"
                )
            elif has_cue:
                background = (
                    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                    f"stop:0 {color}, stop:0.82 {color}, stop:0.83 {self.state_colors['cue_indicator']}, stop:1 {self.state_colors['cue_indicator']})"
                )
            else:
                background = color
            button.setStyleSheet(
                "QPushButton{"
                f"background:{background};"
                f"color:{text_color};"
                f"font-size:10pt;font-weight:bold;border:{'3px solid #FFE04A' if self._hotkey_selected_slot_key == (self._view_group_key(), self.current_page, i) else '1px solid #94B8BA'};"
                "padding:4px;"
                "}"
            )
        self._update_status_totals()

    def _set_dirty(self, dirty: bool = True) -> None:
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self._refresh_window_title()

    def _refresh_window_title(self) -> None:
        base = self.app_title_base
        title = f"{base}    {self.current_set_path}" if self.current_set_path else base
        if self._dirty:
            title = f"{title} *"
        self.setWindowTitle(title)

    def _update_status_totals(self) -> None:
        total_buttons = 0
        total_ms = 0
        for slot in self._current_page_slots():
            if slot.assigned and not slot.marker:
                total_buttons += 1
                total_ms += max(0, int(slot.duration_ms))
        self.status_totals_label.setText(f"{total_buttons} {tr('button')} ({format_set_time(total_ms)})")

    def _on_sound_button_hover(self, slot_index: Optional[int]) -> None:
        self._hover_slot_index = None
        if slot_index is not None and 0 <= slot_index < SLOTS_PER_PAGE:
            self._hover_slot_index = slot_index
        self._refresh_status_hover_label()
        self._refresh_stage_display()
        if self._stage_display_window is not None and self._stage_display_window.isVisible():
            self._stage_display_window.repaint()

    def _refresh_status_hover_label(self) -> None:
        slot_index: Optional[int] = None
        if self._hover_slot_index is not None and 0 <= self._hover_slot_index < SLOTS_PER_PAGE:
            slot_index = self._hover_slot_index
        elif (not self.cue_mode) and (not self.page_playlist_enabled[self.current_group][self.current_page]):
            slot_index = self._next_slot_for_next_action(blocked=None)
        if slot_index is None:
            self.status_hover_label.setText(tr("Button: -"))
            return
        group = self._view_group_key()
        group_text = group if group == "Q" else group.upper()
        self.status_hover_label.setText(f"{tr('Button: ')}{group_text}-{self.current_page + 1}-{slot_index + 1}")

    def _format_button_key(self, slot_key: Tuple[str, int, int]) -> str:
        group, page_index, slot_index = slot_key
        group_text = group if group == "Q" else group.upper()
        return f"{group_text}-{page_index + 1}-{slot_index + 1}"

    def _update_status_now_playing(self) -> None:
        if not self._active_playing_keys:
            self.status_now_playing_label.setText(tr("Now Playing: -"))
            return
        ordered = sorted(self._active_playing_keys, key=lambda item: (item[0], item[1], item[2]))
        values = ", ".join(self._format_button_key(key) for key in ordered)
        self.status_now_playing_label.setText(f"{tr('Now Playing: ')}{values}")

    def _log_file_path(self) -> str:
        appdata = os.getenv("APPDATA")
        base = appdata if appdata else os.path.expanduser("~")
        log_dir = os.path.join(base, "pySSP")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "SportsSoundsProLog.txt")

    def _append_play_log(self, file_path: str) -> None:
        if not self.log_file_enabled or not file_path:
            return
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{stamp}\t{file_path}\n"
        try:
            with open(self._log_file_path(), "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass

    def _view_log_file(self) -> None:
        path = self._log_file_path()
        if not os.path.exists(path):
            QMessageBox.information(self, "View Log", f"No log file yet.\n{path}")
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:
            QMessageBox.warning(self, "View Log", f"Could not open log file:\n{exc}")

    def _reset_all_played_state(self) -> None:
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot in self.data[group][page_index]:
                    slot.played = False
                    if slot.assigned:
                        slot.activity_code = "8"

    def _slot_color(self, slot: SoundButtonData, index: int) -> str:
        playing_key = (self._view_group_key(), self.current_page, index)
        if self._flash_slot_key == playing_key and time.monotonic() < self._flash_slot_until:
            return "#FFF36A"
        if slot.marker:
            if slot.custom_color:
                return slot.custom_color
            return self.state_colors["marker"]
        if slot.locked:
            return self.state_colors["locked"]
        if slot.missing or slot.load_failed:
            return self.state_colors["missing"]
        if playing_key in self._active_playing_keys:
            return self.state_colors["playing"]
        if slot.played:
            return self.state_colors["played"]
        if slot.highlighted:
            return self.state_colors["highlighted"]
        if slot.copied_to_cue:
            return self.state_colors["copied"]
        if slot.assigned:
            if slot.custom_color:
                return slot.custom_color
            return self.state_colors["assigned"]
        return self.state_colors["empty"]

    def _show_slot_menu(self, slot_index: int, pos) -> None:
        button = self.sound_buttons[slot_index]
        page = self._current_page_slots()
        slot = page[slot_index]
        page_created = self._is_page_created(self.current_group, self.current_page)
        if (self._view_group_key(), self.current_page, slot_index) in self._active_playing_keys:
            # Keep direct right-click -> popup behavior, but defer by one event
            # turn so the context-menu/mouse sequence can fully unwind.
            button.setDown(False)
            QTimer.singleShot(0, lambda s=slot: self._open_playback_volume_dialog(s))
            return

        menu = QMenu(self)
        is_unused = (not slot.assigned) and (not slot.marker) and (not slot.title.strip()) and (not slot.notes.strip())

        if is_unused:
            add_action = menu.addAction(tr("Add Sound Button"))
            add_action.setEnabled(page_created)
            edit_action = menu.addAction("Edit Sound Button")
            edit_action.setEnabled(page_created)
            marker_action = menu.addAction("Insert Place Marker")
            marker_action.setEnabled(page_created)
            selected = menu.exec_(button.mapToGlobal(pos))
            if selected == add_action:
                self._pick_sound(slot_index)
            elif selected == edit_action:
                self._edit_sound_button(slot_index)
            elif selected == marker_action:
                self._insert_place_marker(slot_index)
            self._refresh_page_list()
            self._refresh_sound_grid()
            return

        if slot.marker:
            edit_marker_action = menu.addAction("Edit Place Marker")
            copy_action = menu.addAction("Copy Sound Button")
            copy_action.setEnabled(True)
            change_color_action = menu.addAction("Change Colour")
            remove_color_action = menu.addAction("Remove Colour")
            remove_color_action.setEnabled(bool(slot.custom_color))
            delete_action = menu.addAction("Delete")
            selected = menu.exec_(button.mapToGlobal(pos))
            if selected == edit_marker_action:
                self._edit_place_marker(slot_index)
            elif selected == copy_action:
                self._copied_slot_buffer = self._clone_slot(slot)
            elif selected == change_color_action:
                current = slot.custom_color or "#C0C0C0"
                color = QColorDialog.getColor(QColor(current), self, "Button Colour")
                if color.isValid():
                    slot.custom_color = color.name().upper()
                    self._set_dirty(True)
            elif selected == remove_color_action:
                slot.custom_color = None
                self._set_dirty(True)
            elif selected == delete_action:
                if self._confirm_delete_button():
                    page[slot_index] = SoundButtonData()
                    self._set_dirty(True)
            self._refresh_page_list()
            self._refresh_sound_grid()
            return

        cue_it_action = menu.addAction("Cue It")
        cue_it_action.setEnabled(slot.assigned and not self.cue_mode)
        edit_action = menu.addAction("Edit Sound Button")
        edit_action.setEnabled(page_created)
        cue_points_action = menu.addAction("Set Cue Points...")
        cue_points_action.setEnabled(slot.assigned)
        copy_action = menu.addAction("Copy Sound Button")
        copy_action.setEnabled(slot.assigned or bool(slot.title.strip()) or bool(slot.notes.strip()))
        paste_action = menu.addAction("Paste")
        paste_action.setEnabled(self._copied_slot_buffer is not None and page_created and not slot.locked)
        menu.addSeparator()
        highlight_action = menu.addAction("Highlight Off" if slot.highlighted else "Highlight On")
        lock_action = menu.addAction("Lock Off" if slot.locked else "Lock On")
        played_action = menu.addAction("Mark as Played (Red) Off" if slot.played else "Mark as Played (Red) On")
        color_action = menu.addAction("Change Button Colour")
        clear_color_action = menu.addAction("Clear Button Colour")
        clear_color_action.setEnabled(bool(slot.custom_color))
        delete_action = menu.addAction("Delete Button")
        delete_action.setEnabled(slot.assigned or bool(slot.title.strip()) or bool(slot.notes.strip()))

        selected = menu.exec_(button.mapToGlobal(pos))
        if selected == cue_it_action:
            self._cue_slot(slot)
        elif selected == edit_action:
            self._edit_sound_button(slot_index)
        elif selected == cue_points_action:
            self._edit_slot_cue_points(slot_index)
        elif selected == copy_action:
            self._copied_slot_buffer = self._clone_slot(slot)
        elif selected == paste_action:
            if self._copied_slot_buffer is not None:
                page[slot_index] = self._clone_slot(self._copied_slot_buffer)
                self._set_dirty(True)
        elif selected == highlight_action:
            slot.highlighted = not slot.highlighted
            self._set_dirty(True)
        elif selected == lock_action:
            slot.locked = not slot.locked
            self._set_dirty(True)
        elif selected == played_action:
            slot.played = not slot.played
            slot.activity_code = "2" if slot.played else "8"
            self._set_dirty(True)
        elif selected == color_action:
            current = slot.custom_color or "#C0C0C0"
            color = QColorDialog.getColor(QColor(current), self, "Button Colour")
            if color.isValid():
                slot.custom_color = color.name().upper()
                self._set_dirty(True)
        elif selected == clear_color_action:
            slot.custom_color = None
            self._set_dirty(True)
        elif selected == delete_action:
            if self._confirm_delete_button():
                page[slot_index] = SoundButtonData()
                self._set_dirty(True)

        self._refresh_page_list()
        self._refresh_sound_grid()

    def _is_button_drag_enabled(self) -> bool:
        btn = self.control_buttons.get("Button Drag")
        return bool(btn and btn.isChecked())

    def _toggle_button_drag_mode(self, checked: bool) -> None:
        btn = self.control_buttons.get("Button Drag")
        if btn:
            btn.setChecked(checked)
        if checked and self._is_playback_in_progress():
            if btn:
                btn.setChecked(False)
            self._update_button_drag_visual_state()
            return
        if not checked:
            self._drag_source_key = None
        self._update_button_drag_visual_state()

    def _on_sound_button_clicked(self, slot_index: int) -> None:
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        if not self._is_button_drag_enabled():
            self._play_slot(slot_index)
            return
        # In drag mode, click does not play; dragging handles move operations.
        return

    def _can_accept_sound_button_drop(self, mime_data: QMimeData) -> bool:
        return self._is_button_drag_enabled() and mime_data.hasFormat("application/x-pyssp-slot")

    def _build_drag_mime(self, slot_key: Tuple[str, int, int]) -> QMimeData:
        mime = QMimeData()
        mime.setData(
            "application/x-pyssp-slot",
            f"{slot_key[0]}|{slot_key[1]}|{slot_key[2]}".encode("utf-8"),
        )
        return mime

    def _parse_drag_mime(self, mime_data: QMimeData) -> Optional[Tuple[str, int, int]]:
        if not mime_data.hasFormat("application/x-pyssp-slot"):
            return None
        raw = bytes(mime_data.data("application/x-pyssp-slot")).decode("utf-8", errors="ignore")
        parts = raw.split("|")
        if len(parts) != 3:
            return None
        group = parts[0].strip().upper()
        if group not in GROUPS:
            return None
        try:
            page = int(parts[1])
            slot = int(parts[2])
        except ValueError:
            return None
        if page < 0 or page >= PAGE_COUNT or slot < 0 or slot >= SLOTS_PER_PAGE:
            return None
        return (group, page, slot)

    def _start_sound_button_drag(self, slot_index: int) -> None:
        if not self._is_button_drag_enabled() or self.cue_mode:
            return
        source_key = (self.current_group, self.current_page, slot_index)
        if not self._is_page_created(source_key[0], source_key[1]):
            return
        source_slot = self.data[source_key[0]][source_key[1]][source_key[2]]
        if source_key in self._active_playing_keys:
            QMessageBox.information(self, "Button Drag", "Cannot drag a currently playing button.")
            return
        if source_slot.locked or source_slot.marker or (not source_slot.assigned and not source_slot.title):
            return
        drag = QDrag(self.sound_buttons[slot_index])
        drag.setMimeData(self._build_drag_mime(source_key))
        drag.setPixmap(self.sound_buttons[slot_index].grab())
        drag.setHotSpot(self.sound_buttons[slot_index].rect().center())
        drag.exec_(Qt.MoveAction)

    def _handle_drag_over_group(self, group: str) -> None:
        if not self._is_button_drag_enabled() or self.cue_mode:
            return
        if group not in GROUPS:
            return
        if group == self.current_group:
            return
        self._select_group(group)

    def _handle_drag_over_page(self, page_index: int) -> bool:
        if not self._is_button_drag_enabled() or self.cue_mode:
            return False
        if page_index < 0 or page_index >= PAGE_COUNT:
            return False
        if not self._is_page_created(self.current_group, page_index):
            return False
        if page_index == self.current_page:
            return True
        self._select_page(page_index)
        return True

    def _handle_sound_button_drop(self, dest_slot_index: int, mime_data: QMimeData) -> bool:
        source_key = self._parse_drag_mime(mime_data)
        if source_key is None:
            return False
        if self.cue_mode:
            return False
        dest_key = (self.current_group, self.current_page, dest_slot_index)
        if dest_key == source_key:
            return False
        if not self._is_page_created(dest_key[0], dest_key[1]):
            QMessageBox.information(self, "Button Drag", "Cannot drag into a blank page.")
            return False
        if source_key in self._active_playing_keys or dest_key in self._active_playing_keys:
            QMessageBox.information(self, "Button Drag", "Cannot drag currently playing buttons.")
            return False

        source_slot = self.data[source_key[0]][source_key[1]][source_key[2]]
        dest_slot = self.data[dest_key[0]][dest_key[1]][dest_key[2]]
        if source_slot.locked or source_slot.marker or (not source_slot.assigned and not source_slot.title):
            return False
        if dest_slot.locked:
            QMessageBox.information(self, "Button Drag", "Destination button is locked.")
            return False

        source_clone = self._clone_slot(source_slot)
        dest_has_content = bool(dest_slot.assigned or dest_slot.title)
        if not dest_has_content:
            self.data[dest_key[0]][dest_key[1]][dest_key[2]] = source_clone
            self.data[source_key[0]][source_key[1]][source_key[2]] = SoundButtonData()
        else:
            box = QMessageBox(self)
            box.setWindowTitle("Button Drag")
            box.setText("Destination has content.")
            replace_btn = box.addButton("Replace", QMessageBox.AcceptRole)
            swap_btn = box.addButton("Swap", QMessageBox.ActionRole)
            cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
            box.exec_()
            clicked = box.clickedButton()
            if clicked == cancel_btn or clicked is None:
                return False
            if clicked == replace_btn:
                self.data[dest_key[0]][dest_key[1]][dest_key[2]] = source_clone
                self.data[source_key[0]][source_key[1]][source_key[2]] = SoundButtonData()
            elif clicked == swap_btn:
                dest_clone = self._clone_slot(dest_slot)
                self.data[dest_key[0]][dest_key[1]][dest_key[2]] = source_clone
                self.data[source_key[0]][source_key[1]][source_key[2]] = dest_clone
            else:
                return False

        self._set_dirty(True)
        self._refresh_page_list()
        self._refresh_sound_grid()
        return True

    def _insert_place_marker(self, slot_index: int) -> None:
        page = self._current_page_slots()
        note_text, ok = QInputDialog.getText(self, "Insert Place Marker", "Enter page note text:")
        if not ok:
            return
        note = note_text.strip()
        if not note:
            QMessageBox.information(self, "Insert Place Marker", "Page note text is required.")
            return
        page[slot_index] = SoundButtonData(
            title=note,
            marker=True,
            activity_code="7",
        )
        self._set_dirty(True)

    def _edit_place_marker(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        note_text, ok = QInputDialog.getText(self, "Edit Place Marker", "Page note text:", text=slot.title)
        if not ok:
            return
        note = note_text.strip()
        if not note:
            QMessageBox.information(self, "Edit Place Marker", "Page note text is required.")
            return
        slot.title = note
        slot.activity_code = "7"
        slot.marker = True
        self._set_dirty(True)

    def _confirm_delete_button(self) -> bool:
        answer = QMessageBox.question(
            self,
            "Delete Button",
            "Delete this button?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def _clone_slot(self, slot: SoundButtonData) -> SoundButtonData:
        return SoundButtonData(
            file_path=slot.file_path,
            title=slot.title,
            notes=slot.notes,
            duration_ms=slot.duration_ms,
            custom_color=slot.custom_color,
            highlighted=slot.highlighted,
            played=slot.played,
            activity_code=slot.activity_code,
            locked=slot.locked,
            marker=slot.marker,
            copied_to_cue=slot.copied_to_cue,
            load_failed=slot.load_failed,
            volume_override_pct=slot.volume_override_pct,
            cue_start_ms=slot.cue_start_ms,
            cue_end_ms=slot.cue_end_ms,
            sound_hotkey=slot.sound_hotkey,
            sound_midi_hotkey=slot.sound_midi_hotkey,
        )

    def _edit_sound_button(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            QMessageBox.information(self, "Locked", "This sound button is locked.")
            return
        start_dir = self.settings.last_sound_dir or self.settings.last_open_dir or ""
        dialog = EditSoundButtonDialog(
            file_path=slot.file_path,
            caption=slot.title,
            notes=slot.notes,
            volume_override_pct=slot.volume_override_pct,
            sound_hotkey=slot.sound_hotkey,
            sound_midi_hotkey=slot.sound_midi_hotkey,
            available_midi_input_devices=list_midi_input_devices(),
            selected_midi_input_device_ids=self.midi_input_device_ids,
            start_dir=start_dir,
            language=self.ui_language,
            parent=self,
        )
        self._midi_context_handler = dialog
        self._midi_context_block_actions = True
        accepted = dialog.exec_() == QDialog.Accepted
        self._midi_context_handler = None
        self._midi_context_block_actions = False
        if not accepted:
            return
        file_path, caption, notes, volume_override_pct, sound_hotkey, sound_midi_hotkey = dialog.values()
        if not file_path:
            QMessageBox.information(self, "Edit Sound Button", "File is required.")
            return
        conflict = self._find_sound_hotkey_conflict(sound_hotkey, (self._view_group_key(), self.current_page, slot_index))
        if conflict is not None:
            QMessageBox.warning(
                self,
                "Sound Button Hot Key",
                f"Hot key {sound_hotkey} is already assigned to {self._format_button_key(conflict)}.",
            )
            return
        midi_conflict = self._find_sound_midi_hotkey_conflict(
            sound_midi_hotkey,
            (self._view_group_key(), self.current_page, slot_index),
        )
        if midi_conflict is not None:
            QMessageBox.warning(
                self,
                "Sound Button MIDI Hot Key",
                f"MIDI key {sound_midi_hotkey} is already assigned to {self._format_button_key(midi_conflict)}.",
            )
            return
        previous_file_path = slot.file_path
        self.settings.last_sound_dir = os.path.dirname(file_path)
        self._save_settings()
        slot.file_path = file_path
        slot.title = caption or os.path.splitext(os.path.basename(file_path))[0]
        slot.notes = notes
        slot.marker = False
        slot.played = False
        slot.activity_code = "8"
        slot.load_failed = False
        slot.volume_override_pct = volume_override_pct
        slot.sound_hotkey = self._parse_sound_hotkey(sound_hotkey)
        slot.sound_midi_hotkey = self._parse_sound_midi_hotkey(sound_midi_hotkey)
        if previous_file_path != file_path:
            slot.cue_start_ms = None
            slot.cue_end_ms = None
        self._set_dirty(True)
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._apply_hotkeys()

    def _find_sound_hotkey_conflict(
        self, sound_hotkey: str, ignore_slot_key: Optional[Tuple[str, int, int]] = None
    ) -> Optional[Tuple[str, int, int]]:
        token = self._parse_sound_hotkey(sound_hotkey)
        if not token:
            return None
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if ignore_slot_key == (group, page_index, slot_index):
                        continue
                    if not slot.assigned or slot.marker:
                        continue
                    if self._parse_sound_hotkey(slot.sound_hotkey) == token:
                        return (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            key = ("Q", 0, slot_index)
            if ignore_slot_key == key:
                continue
            if not slot.assigned or slot.marker:
                continue
            if self._parse_sound_hotkey(slot.sound_hotkey) == token:
                return key
        return None

    def _find_sound_midi_hotkey_conflict(
        self, sound_hotkey: str, ignore_slot_key: Optional[Tuple[str, int, int]] = None
    ) -> Optional[Tuple[str, int, int]]:
        token = self._parse_sound_midi_hotkey(sound_hotkey)
        if not token:
            return None
        selector, message = split_midi_binding(token)

        def _matches(existing: str) -> bool:
            existing_selector, existing_message = split_midi_binding(existing)
            if not existing_message or existing_message != message:
                return False
            return (not existing_selector) or (not selector) or (existing_selector == selector)

        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if ignore_slot_key == (group, page_index, slot_index):
                        continue
                    if not slot.assigned or slot.marker:
                        continue
                    if _matches(self._parse_sound_midi_hotkey(slot.sound_midi_hotkey)):
                        return (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            key = ("Q", 0, slot_index)
            if ignore_slot_key == key:
                continue
            if not slot.assigned or slot.marker:
                continue
            if _matches(self._parse_sound_midi_hotkey(slot.sound_midi_hotkey)):
                return key
        return None

    def _edit_slot_cue_points(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            QMessageBox.information(self, "Locked", "This sound button is locked.")
            return
        if not slot.assigned or slot.marker:
            return
        # Guard against transient stop/start events while the cue dialog initializes.
        self._timecode_event_guard_until = time.perf_counter() + 0.40
        dialog = CuePointDialog(
            file_path=slot.file_path,
            title=slot.title,
            cue_start_ms=slot.cue_start_ms,
            cue_end_ms=slot.cue_end_ms,
            stop_host_playback=self._hard_stop_all,
            language=self.ui_language,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        cue_start_ms, cue_end_ms = dialog.values()
        slot.cue_start_ms = cue_start_ms
        slot.cue_end_ms = cue_end_ms
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _is_page_created(self, group: str, page_index: int) -> bool:
        if self.cue_mode:
            return True
        page_name = self.page_names[group][page_index].strip()
        if page_name:
            return True
        page = self.data[group][page_index]
        return any(slot.assigned or slot.title for slot in page)

    def _pick_sound(self, slot_index: int) -> None:
        if not self.cue_mode and not self._is_page_created(self.current_group, self.current_page):
            QMessageBox.information(self, "Create Page", "Create the page first before adding sound buttons.")
            return
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            QMessageBox.information(self, "Locked", "This sound button is locked.")
            return

        start_dir = self.settings.last_sound_dir or self.settings.last_open_dir or ""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Select Sound Files"),
            start_dir,
            tr("Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)"),
        )
        if not file_paths:
            return
        self.settings.last_sound_dir = os.path.dirname(file_paths[0])
        self._save_settings()

        changed = False
        next_file_idx = 0
        for target_index in range(slot_index, SLOTS_PER_PAGE):
            if next_file_idx >= len(file_paths):
                break
            target = page[target_index]
            is_unused = (not target.assigned) and (not target.marker) and (not target.title.strip()) and (not target.notes.strip())
            if not is_unused:
                continue
            file_path = file_paths[next_file_idx]
            next_file_idx += 1
            target.file_path = file_path
            target.title = os.path.splitext(os.path.basename(file_path))[0]
            target.notes = ""
            target.duration_ms = 0
            target.custom_color = None
            target.marker = False
            target.played = False
            target.activity_code = "8"
            target.load_failed = False
            target.cue_start_ms = None
            target.cue_end_ms = None
            changed = True

        if changed:
            self._set_dirty(True)
            self._refresh_page_list()
            self._refresh_sound_grid()

    def _verify_slot(self, slot: SoundButtonData) -> None:
        if slot.missing:
            QMessageBox.warning(self, "Missing File", f"File not found:\n{slot.file_path}")
        else:
            QMessageBox.information(self, "File Check", "Sound file exists.")

    def _slot_volume_pct(self, slot: SoundButtonData) -> int:
        if slot.volume_override_pct is None:
            return 75
        return max(0, min(100, int(slot.volume_override_pct)))

    def _parse_volume_override_pct(self, value: str) -> Optional[int]:
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError:
            return None
        return max(0, min(100, parsed))

    def _parse_sound_hotkey(self, value: str) -> str:
        raw = str(value or "").strip().upper()
        if not raw:
            return ""
        if raw.startswith("0"):
            raw = raw[1:]
        if re.fullmatch(r"F([1-9]|1[1-2])", raw):
            if raw == "F10":
                return ""
            return raw
        if re.fullmatch(r"[0-9]", raw):
            return raw
        if re.fullmatch(r"[A-OQ-Z]", raw):
            return raw
        return ""

    def _encode_sound_hotkey(self, value: str) -> str:
        token = self._parse_sound_hotkey(value)
        if not token:
            return ""
        return f"0{token}"

    def _parse_sound_midi_hotkey(self, value: str) -> str:
        return normalize_midi_binding(value)

    def _encode_sound_midi_hotkey(self, value: str) -> str:
        return self._parse_sound_midi_hotkey(value)

    def _parse_cue_points(self, start_value: str, end_value: str, duration_ms: int) -> tuple[Optional[int], Optional[int]]:
        fallback_units_per_ms = 176.4
        start_raw = self._parse_non_negative_int(start_value)
        end_raw = self._parse_non_negative_int(end_value)
        if start_raw is None and end_raw is None:
            return None, None

        start_ms = start_raw
        end_ms = end_raw
        if duration_ms > 0 and end_raw is not None and end_raw > max(duration_ms * 2, 600000):
            scale = duration_ms / float(end_raw)
            if start_raw is not None:
                start_ms = int(round(start_raw * scale))
            end_ms = duration_ms
        elif duration_ms > 0 and end_raw is None and start_raw is not None and start_raw > duration_ms:
            # Handle cs-only files where cue values are stored in SSP units.
            inferred_start_ms = int(round(start_raw / fallback_units_per_ms))
            if 0 <= inferred_start_ms <= duration_ms:
                start_ms = inferred_start_ms

        if start_ms is not None:
            start_ms = max(0, start_ms)
        if end_ms is not None:
            end_ms = max(0, end_ms)

        if duration_ms > 0:
            if start_ms is not None:
                start_ms = min(duration_ms, start_ms)
            if end_ms is not None:
                end_ms = min(duration_ms, end_ms)
        if start_ms is not None and end_ms is not None and end_ms < start_ms:
            end_ms = start_ms
        return start_ms, end_ms

    def _parse_non_negative_int(self, value: str) -> Optional[int]:
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError:
            return None
        if parsed < 0:
            return None
        return parsed

    def _normalized_slot_cues(self, slot: SoundButtonData, duration_ms: int) -> tuple[Optional[int], Optional[int]]:
        start_ms = slot.cue_start_ms
        end_ms = slot.cue_end_ms
        if start_ms is not None:
            start_ms = max(0, int(start_ms))
        if end_ms is not None:
            end_ms = max(0, int(end_ms))
        if duration_ms > 0:
            if start_ms is not None:
                start_ms = min(duration_ms, start_ms)
            if end_ms is not None:
                end_ms = min(duration_ms, end_ms)
        if start_ms is not None and end_ms is not None and end_ms < start_ms:
            end_ms = start_ms
        if start_ms == 0 and end_ms is None:
            start_ms = None
        return start_ms, end_ms

    def _slot_has_custom_cue(self, slot: SoundButtonData) -> bool:
        start_ms, end_ms = self._normalized_slot_cues(slot, max(0, int(slot.duration_ms)))
        return (end_ms is not None) or (start_ms is not None and start_ms > 0)

    def _slot_ssp_unit_scale(self, slot: SoundButtonData) -> Optional[Tuple[int, int]]:
        file_path = (slot.file_path or "").strip()
        if not file_path:
            return None
        cached = self._ssp_unit_cache.get(file_path)
        if cached is not None:
            return cached
        try:
            duration_ms, total_units = get_media_ssp_units(file_path)
        except Exception:
            return None
        if duration_ms <= 0 or total_units <= 0:
            return None
        self._ssp_unit_cache[file_path] = (duration_ms, total_units)
        return self._ssp_unit_cache[file_path]

    def _normalize_cue_points(
        self, start_ms: Optional[int], end_ms: Optional[int], duration_ms: int
    ) -> tuple[Optional[int], Optional[int]]:
        if start_ms is not None:
            start_ms = max(0, int(start_ms))
        if end_ms is not None:
            end_ms = max(0, int(end_ms))
        if duration_ms > 0:
            if start_ms is not None:
                start_ms = min(duration_ms, start_ms)
            if end_ms is not None:
                end_ms = min(duration_ms, end_ms)
        if start_ms is not None and end_ms is not None and end_ms < start_ms:
            end_ms = start_ms
        return start_ms, end_ms

    def _parse_cue_time_string_to_ms(self, value: str) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        parts = text.split(":")
        if len(parts) == 2:
            mm, ss = parts
            if mm.isdigit() and ss.isdigit():
                return (int(mm) * 60 + int(ss)) * 1000
            return None
        if len(parts) == 3:
            first, second, third = parts
            if not (first.isdigit() and second.isdigit() and third.isdigit()):
                return None
            minutes = int(first)
            seconds = int(second)
            frames_or_seconds = int(third)
            if frames_or_seconds < 30:
                return ((minutes * 60) + seconds) * 1000 + int((frames_or_seconds / 30.0) * 1000)
            return (minutes * 3600 + seconds * 60 + frames_or_seconds) * 1000
        return None

    def _format_cue_time_string(self, ms: int) -> str:
        return format_clock_time(max(0, int(ms)))

    def _cue_time_fields_for_set(self, slot: SoundButtonData) -> tuple[Optional[str], Optional[str]]:
        start_ms, end_ms = self._normalized_slot_cues(slot, max(0, int(slot.duration_ms)))
        if start_ms is None and end_ms is None:
            return None, None
        cue_start = None if start_ms is None else self._format_cue_time_string(start_ms)
        cue_end = None if end_ms is None else self._format_cue_time_string(end_ms)
        return cue_start, cue_end

    def _cue_start_for_playback(self, slot: SoundButtonData, duration_ms: int) -> int:
        start_ms, _ = self._normalized_slot_cues(slot, duration_ms)
        return 0 if start_ms is None else max(0, int(start_ms))

    def _cue_end_for_playback(self, slot: SoundButtonData, duration_ms: int) -> Optional[int]:
        _, end_ms = self._normalized_slot_cues(slot, duration_ms)
        return None if end_ms is None else max(0, int(end_ms))

    def _main_transport_bounds(self, duration_ms: Optional[int] = None) -> tuple[int, int]:
        dur = self.current_duration_ms if duration_ms is None else max(0, int(duration_ms))
        if self.main_transport_timeline_mode == "audio_file":
            return 0, dur
        if self.current_playing is None:
            return 0, dur
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return 0, dur
        low = self._cue_start_for_playback(slot, dur)
        end = self._cue_end_for_playback(slot, dur)
        high = dur if end is None else end
        low = max(0, min(dur, low))
        high = max(0, min(dur, high))
        if high < low:
            high = low
        return low, high

    def _transport_total_ms(self) -> int:
        low, high = self._main_transport_bounds()
        return max(0, high - low)

    def _transport_display_ms_for_absolute(self, absolute_ms: int) -> int:
        low, high = self._main_transport_bounds()
        clamped = max(low, min(high, int(absolute_ms)))
        return max(0, clamped - low)

    def _transport_absolute_ms_for_display(self, display_ms: int) -> int:
        low, high = self._main_transport_bounds()
        total = max(0, high - low)
        rel = max(0, min(total, int(display_ms)))
        return low + rel

    def _clear_player_cue_behavior_override(self, player: ExternalMediaPlayer) -> None:
        pid = id(player)
        self._player_end_override_ms.pop(pid, None)
        self._player_ignore_cue_end.discard(pid)

    def _seek_player_to_slot_start_cue(self, player: ExternalMediaPlayer, slot: SoundButtonData) -> None:
        start_ms = self._cue_start_for_playback(slot, max(0, int(player.duration())))
        if start_ms > 0:
            player.setPosition(start_ms)

    def _apply_main_jog_outside_cue_behavior(self, absolute_pos_ms: int) -> None:
        self._clear_player_cue_behavior_override(self.player)
        if self.main_transport_timeline_mode != "audio_file":
            return
        if self.current_playing is None:
            return
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return
        duration_ms = max(0, int(self.player.duration()))
        cue_start = self._cue_start_for_playback(slot, duration_ms)
        cue_end = self._cue_end_for_playback(slot, duration_ms)
        if cue_end is None and cue_start <= 0:
            return
        pos = max(0, int(absolute_pos_ms))
        before_start = pos < cue_start
        after_stop = (cue_end is not None) and (pos > cue_end)
        if not (before_start or after_stop):
            return

        action = self.main_jog_outside_cue_action
        if action == "stop_immediately":
            self._stop_playback()
            return
        if action == "ignore_cue":
            self._player_ignore_cue_end.add(id(self.player))
            return
        if action == "next_cue_or_stop":
            if before_start:
                self._player_end_override_ms[id(self.player)] = cue_start
            else:
                self._player_ignore_cue_end.add(id(self.player))
            return
        if action == "stop_cue_or_end":
            if before_start:
                if cue_end is None:
                    self._player_ignore_cue_end.add(id(self.player))
                else:
                    self._player_end_override_ms[id(self.player)] = cue_end
            else:
                self._player_ignore_cue_end.add(id(self.player))
            return

    def _enforce_cue_end_limits(self) -> None:
        for player in [self.player, self.player_b, *list(self._multi_players)]:
            if player.state() != ExternalMediaPlayer.PlayingState:
                continue
            slot_key = self._player_slot_key_map.get(id(player))
            if slot_key is None:
                continue
            slot = self._slot_for_key(slot_key)
            if slot is None:
                continue
            pid = id(player)
            if pid in self._player_ignore_cue_end:
                continue
            end_ms = self._player_end_override_ms.get(pid)
            if end_ms is None:
                end_ms = self._cue_end_for_playback(slot, max(0, int(player.duration())))
            if end_ms is None:
                continue
            if player.position() < end_ms:
                continue
            if player is self.player:
                player.stop()
            else:
                self._stop_single_player(player)

    def _open_playback_volume_dialog(self, slot: SoundButtonData) -> None:
        if not slot.assigned or slot.marker:
            return
        original_override = slot.volume_override_pct
        original_slot_pct = self._slot_volume_pct(slot)
        is_current_slot = False
        if self.current_playing is not None:
            current_group, current_page, current_slot = self.current_playing
            if current_group == self._view_group_key() and current_page == self.current_page:
                current_slots = self._current_page_slots()
                if 0 <= current_slot < len(current_slots) and current_slots[current_slot] is slot:
                    is_current_slot = True

        dialog = QDialog(self)
        dialog.setWindowTitle("Adjust Volume Level")
        dialog.setModal(True)
        dialog.resize(420, 150)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        value_label = QLabel("")
        root.addWidget(value_label)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(original_slot_pct)
        root.addWidget(slider)

        def _sync_label(value: int) -> None:
            value_label.setText(f"Playback Volume: {value}%")
            if is_current_slot:
                self._player_slot_volume_pct = max(0, min(100, int(value)))
                self.player.setVolume(self._effective_slot_target_volume(self._player_slot_volume_pct))

        _sync_label(slider.value())
        slider.valueChanged.connect(_sync_label)

        button_row = QHBoxLayout()
        remove_btn = QPushButton("Remove Volume Level")
        save_btn = QPushButton("Save Volume")
        cancel_btn = QPushButton("Cancel")
        button_row.addStretch(1)
        button_row.addWidget(remove_btn)
        button_row.addWidget(save_btn)
        button_row.addWidget(cancel_btn)
        root.addLayout(button_row)
        committed = {"value": False}

        def _remove() -> None:
            slot.volume_override_pct = None
            if is_current_slot:
                self._player_slot_volume_pct = 75
                self.player.setVolume(self._effective_slot_target_volume(self._player_slot_volume_pct))
            self._set_dirty(True)
            self._refresh_sound_grid()
            committed["value"] = True
            dialog.accept()

        def _save() -> None:
            value = max(0, min(100, slider.value()))
            slot.volume_override_pct = value
            if is_current_slot:
                self._player_slot_volume_pct = value
                self.player.setVolume(self._effective_slot_target_volume(self._player_slot_volume_pct))
            self._set_dirty(True)
            self._refresh_sound_grid()
            committed["value"] = True
            dialog.accept()

        def _on_finished(_result: int) -> None:
            if not committed["value"]:
                slot.volume_override_pct = original_override
                if is_current_slot:
                    self._player_slot_volume_pct = original_slot_pct
                    self.player.setVolume(self._effective_slot_target_volume(self._player_slot_volume_pct))
            self._recover_from_stuck_mouse_state()
            dialog.deleteLater()
            if getattr(self, "_active_playback_volume_dialog", None) is dialog:
                self._active_playback_volume_dialog = None

        remove_btn.clicked.connect(_remove)
        save_btn.clicked.connect(_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.finished.connect(_on_finished)
        existing = getattr(self, "_active_playback_volume_dialog", None)
        if existing is not None and existing is not dialog:
            try:
                existing.close()
            except Exception:
                pass
        self._active_playback_volume_dialog = dialog
        dialog.open()

    def _recover_from_stuck_mouse_state(self) -> None:
        # Defensive UI recovery for platform-specific pointer grab issues after
        # closing context-launched modal dialogs.
        try:
            grabber = QWidget.mouseGrabber()
            if grabber is not None:
                grabber.releaseMouse()
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            try:
                popup = app.activePopupWidget()
                if popup is not None:
                    popup.close()
            except Exception:
                pass
        for btn in self.control_buttons.values():
            btn.setDown(False)
        for btn in self.group_buttons.values():
            btn.setDown(False)
        for btn in self.sound_buttons:
            btn.setDown(False)

    def _play_slot(self, slot_index: int, allow_fade: bool = True) -> bool:
        click_t = time.perf_counter()
        if self._is_button_drag_enabled():
            self.statusBar().showMessage(tr("Playback is not allowed while Button Drag is enabled."), 2500)
            return False
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            return False
        if slot.marker:
            return False
        if not slot.assigned:
            return False
        if slot.missing:
            self._refresh_sound_grid()
            return False

        group_key = self._view_group_key()
        playing_key = (group_key, self.current_page, slot_index)
        print(
            f"[TCDBG] {click_t:.6f} play_click key={playing_key} title={(slot.title or '<untitled>')} "
            f"mode={self._current_fade_mode()} multi={self._is_multi_play_enabled()}"
        )
        self._prune_multi_players()
        force_single_play = False
        if (not self._is_multi_play_enabled()) and self._multi_players:
            # Multi-Play was previously active; a normal click should collapse playback
            # to the selected track only.
            force_single_play = True
            for extra in list(self._multi_players):
                self._stop_single_player(extra)
            self._prune_multi_players()
        if self._is_multi_play_enabled() and playing_key in self._active_playing_keys:
            self._stop_track_by_slot_key(playing_key)
            return False
        playlist_enabled_here = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if self._is_multi_play_enabled() and (not playlist_enabled_here) and self._all_active_players():
            return self._play_slot_multi(slot, playing_key)
        if self.current_playing == playing_key and self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            if self.click_playing_action == "stop_it" and not force_single_play:
                self._stop_playback()
                return False
        # Invalidate any previously scheduled delayed start to avoid stale restarts.
        self._pending_start_request = None
        self._pending_start_token += 1
        old_player, new_player = self._select_transition_players()
        any_playing = old_player is not None
        mode = self._current_fade_mode()
        if not allow_fade:
            mode = "none"
        if self._is_multi_play_enabled():
            if mode == "cross_fade":
                mode = "none"
            elif mode == "fade_out_then_fade_in":
                mode = "fade_in_only"
        fade_in_on = mode in {"fade_in_only", "fade_out_then_fade_in"}
        fade_out_on = mode in {"fade_out_only", "fade_out_then_fade_in"}
        cross_mode = mode == "cross_fade"
        if (
            any_playing
            and fade_out_on
            and not cross_mode
        ):
            print(f"[TCDBG] {time.perf_counter():.6f} delayed_start_due_to_fadeout key={playing_key}")
            self._schedule_start_after_fadeout(group_key, self.current_page, slot_index)
            return True

        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if playlist_enabled and self.current_playlist_start is None:
            self.current_playlist_start = slot_index
        slot.played = True
        slot.activity_code = "2"
        self._set_dirty(True)

        self.current_playing = playing_key
        self._manual_stop_requested = False
        self._cancel_fade_for_player(self.player)
        self._cancel_fade_for_player(self.player_b)
        slot_pct = self._slot_volume_pct(slot)

        started_playback = False
        if cross_mode:
            self._stop_player_internal(new_player)
            load_t = time.perf_counter()
            if not self._try_load_media(new_player, slot):
                print(
                    f"[TCDBG] {time.perf_counter():.6f} media_load_failed cross "
                    f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
                )
                self.current_playing = None
                self._refresh_sound_grid()
                self._update_now_playing_label("")
                return False
            print(
                f"[TCDBG] {time.perf_counter():.6f} media_load_ok cross "
                f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
            )
            if new_player is self.player:
                self._player_slot_volume_pct = slot_pct
            else:
                self._player_b_slot_volume_pct = slot_pct
            target_volume = self._effective_slot_target_volume(slot_pct)
            seek_t = time.perf_counter()
            self._seek_player_to_slot_start_cue(new_player, slot)
            print(
                f"[TCDBG] {time.perf_counter():.6f} media_seek_done cross "
                f"dt_ms={(time.perf_counter() - seek_t) * 1000.0:.1f} key={playing_key}"
            )
            new_player.setVolume(0)
            print(f"[TCDBG] {time.perf_counter():.6f} player_play cross key={playing_key}")
            new_player.play()
            started_playback = True
            self._set_player_slot_key(new_player, playing_key)
            fade_seconds = self.cross_fade_sec
            self._start_fade(new_player, target_volume, fade_seconds, stop_on_complete=False)
            if old_player is not None:
                self._start_fade(old_player, 0, fade_seconds, stop_on_complete=True)
            # Keep the "primary" player bound to the newest track for UI updates.
            if self.player is not new_player:
                self._swap_primary_secondary_players()
        else:
            self._clear_all_player_slot_keys()
            self._stop_player_internal(self.player_b)
            self._stop_player_internal(self.player)
            load_t = time.perf_counter()
            if not self._try_load_media(self.player, slot):
                print(
                    f"[TCDBG] {time.perf_counter():.6f} media_load_failed primary "
                    f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
                )
                self.current_playing = None
                self._refresh_sound_grid()
                self._update_now_playing_label("")
                return False
            print(
                f"[TCDBG] {time.perf_counter():.6f} media_load_ok primary "
                f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
            )
            self._player_slot_volume_pct = slot_pct
            target_volume = self._effective_slot_target_volume(slot_pct)
            seek_t = time.perf_counter()
            self._seek_player_to_slot_start_cue(self.player, slot)
            print(
                f"[TCDBG] {time.perf_counter():.6f} media_seek_done primary "
                f"dt_ms={(time.perf_counter() - seek_t) * 1000.0:.1f} key={playing_key}"
            )
            if fade_in_on:
                self.player.setVolume(0)
                print(f"[TCDBG] {time.perf_counter():.6f} player_play fade_in key={playing_key}")
                self.player.play()
                started_playback = True
                self._set_player_slot_key(self.player, playing_key)
                self._start_fade(self.player, target_volume, self.fade_in_sec, stop_on_complete=False)
            else:
                self.player.setVolume(target_volume)
                print(f"[TCDBG] {time.perf_counter():.6f} player_play direct key={playing_key}")
                self.player.play()
                started_playback = True
                self._set_player_slot_key(self.player, playing_key)

        if started_playback:
            self._timecode_on_playback_start(slot)
            self._prepare_transport_for_new_playback()

        self._refresh_sound_grid()
        self._update_now_playing_label(self._build_now_playing_text(slot))
        self._append_play_log(slot.file_path)
        self._mark_player_started(self.player)
        return True

    def _prepare_transport_for_new_playback(self) -> None:
        self._auto_transition_track = self.current_playing
        self._auto_transition_done = False
        self._auto_end_fade_track = self.current_playing
        self._auto_end_fade_done = False
        self._track_started_at = time.monotonic()
        # Clear stale UI timing without wiping duration loaded by setMedia().
        self._last_ui_position_ms = -1
        display_pos = self._transport_display_ms_for_absolute(0)
        total_ms = self._transport_total_ms()
        self.seek_slider.setValue(display_pos)
        self.elapsed_time.setText(format_clock_time(display_pos))
        self.remaining_time.setText(format_clock_time(max(0, total_ms - display_pos)))
        self._refresh_main_jog_meta(display_pos, total_ms)

    def _play_slot_multi(self, slot: SoundButtonData, playing_key: Tuple[str, int, int]) -> bool:
        if not self._enforce_multi_play_limit():
            return False
        extra_player = ExternalMediaPlayer(self)
        extra_player.setNotifyInterval(90)
        extra_player.setDSPConfig(self._dsp_config)
        slot_pct = self._slot_volume_pct(slot)
        try:
            if not self._try_load_media(extra_player, slot):
                extra_player.deleteLater()
                return False
            self._set_player_slot_pct(extra_player, slot_pct)
            target_volume = self._effective_slot_target_volume(slot_pct)
            self._seek_player_to_slot_start_cue(extra_player, slot)
            fade_in_on = self._is_fade_in_enabled()
            if fade_in_on and self.fade_in_sec > 0:
                extra_player.setVolume(0)
            else:
                extra_player.setVolume(target_volume)
            extra_player.play()
            if fade_in_on and self.fade_in_sec > 0:
                self._start_fade(extra_player, target_volume, self.fade_in_sec, stop_on_complete=False)
        except Exception:
            try:
                extra_player.deleteLater()
            except Exception:
                pass
            return False
        self._multi_players.append(extra_player)
        self._set_player_slot_key(extra_player, playing_key)
        self._mark_player_started(extra_player)
        slot.played = True
        slot.activity_code = "2"
        self._set_dirty(True)
        self.current_playing = playing_key
        self._refresh_sound_grid()
        self._update_now_playing_label(self._build_now_playing_text(slot))
        self._append_play_log(slot.file_path)
        return True

    def _try_load_media(self, player: ExternalMediaPlayer, slot: SoundButtonData) -> bool:
        try:
            if player is self.player:
                self._main_waveform_request_token += 1
                self._main_progress_waveform = []
                self.progress_label.set_waveform([])
            player.setMedia(slot.file_path, dsp_config=self._dsp_config)
            slot.load_failed = False
            self._hide_playback_warning_banner()
            return True
        except Exception as exc:
            slot.load_failed = True
            self._stop_player_internal(player)
            title = slot.title.strip() or os.path.basename(slot.file_path) or "(unknown)"
            self._show_playback_warning_banner(f"{tr('Audio Load Failed:')} Could not play '{title}'. Reason: {exc}")
            print(f"[pySSP] Audio load failed: {slot.file_path} | {exc}", flush=True)
            return False

    def _select_transition_players(self) -> Tuple[Optional[ExternalMediaPlayer], ExternalMediaPlayer]:
        def is_active(player: ExternalMediaPlayer) -> bool:
            return player.state() in {
                ExternalMediaPlayer.PlayingState,
                ExternalMediaPlayer.PausedState,
            }

        def score(player: ExternalMediaPlayer) -> Tuple[int, int]:
            # Prefer actively playing channel, then louder channel.
            is_playing = 1 if player.state() == ExternalMediaPlayer.PlayingState else 0
            return (is_playing, player.volume())

        a_active = is_active(self.player)
        b_active = is_active(self.player_b)

        if a_active and b_active:
            # Fade out the dominant (audible) player; reuse the other as fade-in target.
            if score(self.player) >= score(self.player_b):
                return self.player, self.player_b
            return self.player_b, self.player
        if a_active:
            return self.player, self.player_b
        if b_active:
            return self.player_b, self.player
        return None, self.player

    def _schedule_start_after_fadeout(self, group_key: str, page_index: int, slot_index: int) -> None:
        self._pending_start_request = (group_key, page_index, slot_index)
        self._pending_start_token += 1
        token = self._pending_start_token
        fade_ms = max(1, int(self.fade_out_sec * 1000))
        self._start_fade(self.player, 0, self.fade_out_sec, stop_on_complete=True)
        if self.player_b.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
            self._start_fade(self.player_b, 0, self.fade_out_sec, stop_on_complete=True)
        QTimer.singleShot(fade_ms + 30, lambda t=token: self._run_pending_start(t))

    def _run_pending_start(self, token: int) -> None:
        if token != self._pending_start_token:
            return
        request = self._pending_start_request
        if request is None:
            return
        self._pending_start_request = None
        group_key, page_index, slot_index = request
        if group_key == "Q":
            self.cue_mode = True
        else:
            self.cue_mode = False
            self.current_group = group_key
        self.current_page = max(0, min(PAGE_COUNT - 1, page_index))
        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._apply_hotkeys()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._play_slot(slot_index)

    def _on_position_changed(self, pos: int) -> None:
        display_pos = self._transport_display_ms_for_absolute(pos)
        if not self._is_scrubbing:
            self.seek_slider.setValue(display_pos)
        # Keep transport updates smooth without redrawing excessively.
        if self._last_ui_position_ms >= 0 and abs(pos - self._last_ui_position_ms) < 25:
            return
        self._last_ui_position_ms = pos
        self.elapsed_time.setText(format_clock_time(display_pos))
        total_ms = self._transport_total_ms()
        remaining = max(0, total_ms - display_pos)
        self.remaining_time.setText(format_clock_time(remaining))
        progress = 0 if total_ms == 0 else int((display_pos / total_ms) * 100)
        self._refresh_main_jog_meta(display_pos, total_ms)
        self._refresh_timecode_panel()
        self._refresh_stage_display()

    def _on_duration_changed(self, duration: int) -> None:
        self.current_duration_ms = duration
        if duration > 0 and self.main_progress_display_mode == "waveform":
            self._schedule_main_waveform_refresh(120)
        else:
            self._main_waveform_request_token += 1
            self._main_progress_waveform = []
            self.progress_label.set_waveform([])
        self._last_ui_position_ms = -1
        total_ms = self._transport_total_ms()
        self.seek_slider.setRange(0, total_ms)
        self.total_time.setText(format_clock_time(total_ms))
        if self.current_playing:
            group, page_index, slot_index = self.current_playing
            if group == "Q":
                if 0 <= slot_index < len(self.cue_page):
                    self.cue_page[slot_index].duration_ms = duration
            elif group in self.data and 0 <= page_index < PAGE_COUNT and 0 <= slot_index < SLOTS_PER_PAGE:
                self.data[group][page_index][slot_index].duration_ms = duration
            self._refresh_sound_grid()
        self._refresh_timecode_panel()
        self._refresh_stage_display()

    def _schedule_main_waveform_refresh(self, delay_ms: int = 0) -> None:
        if self.current_duration_ms <= 0:
            return
        if self.current_playing is None:
            return
        token = self._main_waveform_request_token + 1
        self._main_waveform_request_token = token
        expected_key = self.current_playing
        QTimer.singleShot(max(0, int(delay_ms)), lambda t=token, k=expected_key: self._refresh_main_waveform_if_current(t, k))

    def _refresh_main_waveform_if_current(self, token: int, expected_key: Optional[Tuple[str, int, int]]) -> None:
        if token != self._main_waveform_request_token:
            return
        if expected_key is None or self.current_playing != expected_key:
            return
        if self.current_duration_ms <= 0:
            return
        try:
            peaks = self.player.waveformPeaks(1800)
        except Exception:
            peaks = []
        if token != self._main_waveform_request_token:
            return
        if expected_key is None or self.current_playing != expected_key:
            return
        self._main_progress_waveform = list(peaks)
        self.progress_label.set_waveform(self._main_progress_waveform)

    def _on_state_changed(self, _state: int) -> None:
        print(
            f"[TCDBG] {time.perf_counter():.6f} state_changed "
            f"primary={self.player.state()} secondary={self.player_b.state()}"
        )
        self._update_pause_button_label()
        if self._ignore_state_changes > 0:
            return
        if self.player.state() == ExternalMediaPlayer.StoppedState:
            self._timecode_on_playback_stop()
            self._clear_player_slot_key(self.player)
            last_playing = self.current_playing
            playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
            manual_stop = self._manual_stop_requested
            should_loop = self.loop_enabled and last_playing is not None and not manual_stop and not playlist_enabled
            self._manual_stop_requested = False
            if should_loop:
                loop_group, loop_page, loop_slot = last_playing
                if loop_group != "Q":
                    self.current_group = loop_group
                    self.cue_mode = False
                else:
                    self.cue_mode = True
                self.current_page = loop_page
                self._refresh_group_buttons()
                self._refresh_page_list()
                self._play_slot(loop_slot)
                return
            if self._pending_start_request is not None:
                self.current_playing = None
                self._last_ui_position_ms = -1
                self.elapsed_time.setText("00:00:00")
                self.remaining_time.setText("00:00:00")
                self._set_progress_display(0)
                self.seek_slider.setValue(0)
                self._update_now_playing_label("")
                self._refresh_sound_grid()
                return
            if playlist_enabled and last_playing is not None:
                if manual_stop:
                    self.current_playing = None
                    self._last_ui_position_ms = -1
                    self.elapsed_time.setText("00:00:00")
                    self.remaining_time.setText("00:00:00")
                    self._set_progress_display(0)
                    self.seek_slider.setValue(0)
                    self._update_now_playing_label("")
                    self._refresh_sound_grid()
                    return
                blocked: set[int] = set()
                while True:
                    next_slot = self._next_playlist_slot(for_auto_advance=True, blocked=blocked)
                    if next_slot is None:
                        break
                    if self._play_slot(next_slot):
                        return
                    blocked.add(next_slot)
                    if self.candidate_error_action == "stop_playback":
                        self._stop_playback()
                        return
            self.current_playing = None
            self._auto_transition_track = None
            self._auto_transition_done = False
            self._last_ui_position_ms = -1
            self.elapsed_time.setText("00:00:00")
            self.remaining_time.setText("00:00:00")
            self._set_progress_display(0)
            self._refresh_sound_grid()
            self.seek_slider.setValue(0)
            self._update_now_playing_label("")
        self._refresh_timecode_panel()
        self._refresh_stage_display()

    def _stop_player_internal(self, player: ExternalMediaPlayer) -> None:
        self._ignore_state_changes += 1
        try:
            player.stop()
        finally:
            self._ignore_state_changes = max(0, self._ignore_state_changes - 1)

    def _tick_preload_status_icon(self) -> None:
        enabled, active_jobs = get_audio_preload_runtime_status()
        self._refresh_current_page_ram_loaded_indicators()
        if (not enabled) or active_jobs <= 0:
            self._preload_icon_blink_on = False
            self.preload_status_icon.setStyleSheet(
                "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#C8CDD4;border:1px solid #8C939D;border-radius:8px;}"
            )
            self.preload_status_icon.setToolTip("RAM preload idle")
            return
        self._preload_icon_blink_on = not self._preload_icon_blink_on
        if self._preload_icon_blink_on:
            self.preload_status_icon.setStyleSheet(
                "QLabel{font-size:9pt;font-weight:bold;color:#0B4A1F;background:#5FE088;border:1px solid #219653;border-radius:8px;}"
            )
        else:
            self.preload_status_icon.setStyleSheet(
                "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#C8CDD4;border:1px solid #8C939D;border-radius:8px;}"
            )
        self.preload_status_icon.setToolTip(f"RAM preload active ({active_jobs})")

    def _tick_meter(self) -> None:
        self._prune_multi_players()
        self._enforce_cue_end_limits()
        if self.player_b.state() == ExternalMediaPlayer.StoppedState:
            self._clear_player_slot_key(self.player_b)
        self._try_auto_fade_transition()
        self._update_next_button_enabled()
        if self._flash_slot_key and time.monotonic() >= self._flash_slot_until:
            self._flash_slot_key = None
            self._flash_slot_until = 0.0
            self._refresh_sound_grid()
        any_playing = (
            self.player.state() == ExternalMediaPlayer.PlayingState
            or self.player_b.state() == ExternalMediaPlayer.PlayingState
        )
        left_a, right_a = self.player.meterLevels()
        left_b, right_b = self.player_b.meterLevels()
        sum_left = left_a + left_b
        sum_right = right_a + right_b
        for extra in self._multi_players:
            if extra.state() == ExternalMediaPlayer.PlayingState:
                any_playing = True
            left_x, right_x = extra.meterLevels()
            sum_left += left_x
            sum_right += right_x
        target_left = min(1.0, max(0.0, sum_left))
        target_right = min(1.0, max(0.0, sum_right))
        target_left *= 100.0
        target_right *= 100.0
        attack = 0.92
        release = 0.68 if any_playing else 0.45
        if target_left >= self._vu_levels[0]:
            self._vu_levels[0] += (target_left - self._vu_levels[0]) * attack
        else:
            self._vu_levels[0] += (target_left - self._vu_levels[0]) * release
        if target_right >= self._vu_levels[1]:
            self._vu_levels[1] += (target_right - self._vu_levels[1]) * attack
        else:
            self._vu_levels[1] += (target_right - self._vu_levels[1]) * release
        self._sync_preload_pause_state(any_playing)
        self._refresh_timecode_panel()
        self.left_meter.setValue(int(max(0.0, min(100.0, self._vu_levels[0]))))
        self.right_meter.setValue(int(max(0.0, min(100.0, self._vu_levels[1]))))
        self._refresh_stage_display()

    def _update_group_status(self) -> None:
        if self.cue_mode:
            self.group_status.setText(tr("Group - Cue"))
        else:
            self.group_status.setText(f"{tr('Group - ')}{self.current_group}")

    def _update_page_status(self) -> None:
        if self.cue_mode:
            self.page_status.setText(tr("Page - Cue"))
            return
        page_name = self.page_names[self.current_group][self.current_page].strip()
        if page_name:
            self.page_status.setText(f"{tr('Page - ')}{page_name}")
        else:
            self.page_status.setText(f"{tr('Page - ')}{self.current_page + 1}")

    def _update_now_playing_label(self, text: str) -> None:
        if text:
            self.now_playing_label.setText(f"{tr('NOW PLAYING: ')}{text}")
        else:
            self.now_playing_label.setText(tr("NOW PLAYING:"))
        self._refresh_stage_display()

    def _build_now_playing_text(self, slot: SoundButtonData) -> str:
        title = slot.title.strip()
        if title:
            return title
        base_name = os.path.basename(slot.file_path)
        return os.path.splitext(base_name)[0]

    def _show_stage_display(self) -> None:
        if self._stage_display_window is None:
            self._stage_display_window = GadgetStageDisplayWindow(self)
            self._stage_display_window.destroyed.connect(self._on_stage_display_destroyed)
        self._stage_display_window.retranslate_ui()
        self._stage_display_window.configure_gadgets(self.stage_display_gadgets)
        self._refresh_stage_display()
        self._stage_display_window.show()
        self._stage_display_window.raise_()
        self._stage_display_window.activateWindow()

    def _open_stage_alert_panel(self) -> None:
        if self._stage_alert_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Send Alert")
            dialog.setModal(False)
            dialog.resize(480, 320)
            root = QVBoxLayout(dialog)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(8)
            root.addWidget(QLabel("Alert Message"))
            self._stage_alert_text_edit = QPlainTextEdit(dialog)
            self._stage_alert_text_edit.setPlaceholderText("Type alert text to show on Stage Display")
            root.addWidget(self._stage_alert_text_edit, 1)
            row = QHBoxLayout()
            self._stage_alert_keep_checkbox = QCheckBox("Keep on screen until cleared", dialog)
            self._stage_alert_keep_checkbox.setChecked(True)
            self._stage_alert_duration_spin = QSpinBox(dialog)
            self._stage_alert_duration_spin.setRange(1, 600)
            self._stage_alert_duration_spin.setValue(10)
            self._stage_alert_duration_spin.setEnabled(False)
            self._stage_alert_keep_checkbox.toggled.connect(
                lambda keep: self._stage_alert_duration_spin.setEnabled(not bool(keep))
            )
            row.addWidget(self._stage_alert_keep_checkbox)
            row.addStretch(1)
            row.addWidget(QLabel("Seconds"))
            row.addWidget(self._stage_alert_duration_spin)
            root.addLayout(row)
            buttons = QHBoxLayout()
            buttons.addStretch(1)
            send_btn = QPushButton("Send", dialog)
            clear_btn = QPushButton("Clear Alert", dialog)
            close_btn = QPushButton("Close", dialog)
            send_btn.clicked.connect(self._send_stage_alert_from_panel)
            clear_btn.clicked.connect(self._clear_stage_alert)
            close_btn.clicked.connect(dialog.close)
            buttons.addWidget(send_btn)
            buttons.addWidget(clear_btn)
            buttons.addWidget(close_btn)
            root.addLayout(buttons)
            dialog.destroyed.connect(self._on_stage_alert_dialog_destroyed)
            self._stage_alert_dialog = dialog
        if self._stage_alert_text_edit is not None and not self._stage_alert_text_edit.toPlainText().strip():
            self._stage_alert_text_edit.setPlainText(self._stage_alert_message)
        self._stage_alert_dialog.show()
        self._stage_alert_dialog.raise_()
        self._stage_alert_dialog.activateWindow()

    def _on_stage_alert_dialog_destroyed(self, _obj=None) -> None:
        self._stage_alert_dialog = None
        self._stage_alert_text_edit = None
        self._stage_alert_duration_spin = None
        self._stage_alert_keep_checkbox = None

    def _send_stage_alert_from_panel(self) -> None:
        if self._stage_alert_text_edit is None:
            return
        text = self._stage_alert_text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Send Alert", "Please enter alert text.")
            return
        keep = bool(self._stage_alert_keep_checkbox.isChecked()) if self._stage_alert_keep_checkbox is not None else True
        self._stage_alert_message = text
        self._stage_alert_sticky = keep
        if keep:
            self._stage_alert_until_monotonic = 0.0
        else:
            seconds = int(self._stage_alert_duration_spin.value()) if self._stage_alert_duration_spin is not None else 10
            self._stage_alert_until_monotonic = time.monotonic() + max(1, seconds)
        self._refresh_stage_display()

    def _clear_stage_alert(self) -> None:
        self._stage_alert_message = ""
        self._stage_alert_sticky = False
        self._stage_alert_until_monotonic = 0.0
        self._refresh_stage_display()

    def _stage_alert_active(self) -> bool:
        if not self._stage_alert_message:
            return False
        if self._stage_alert_sticky:
            return True
        if self._stage_alert_until_monotonic > 0.0 and time.monotonic() < self._stage_alert_until_monotonic:
            return True
        if self._stage_alert_until_monotonic > 0.0:
            self._stage_alert_message = ""
            self._stage_alert_until_monotonic = 0.0
            self._stage_alert_sticky = False
        return False

    def _on_stage_display_destroyed(self, _obj=None) -> None:
        self._stage_display_window = None

    def _refresh_stage_display(self) -> None:
        if self._stage_display_window is None:
            return
        if not self._stage_display_window.isVisible():
            return
        total_ms = max(0, self._transport_total_ms())
        elapsed_text = self.elapsed_time.text().strip() or "00:00:00"
        remaining_text = self.remaining_time.text().strip() or "00:00:00"
        total_text = self.total_time.text().strip() or "00:00:00"
        display_pos = 0
        try:
            display_pos = max(0, int(self.seek_slider.value()))
        except Exception:
            display_pos = 0
        progress = 0 if total_ms <= 0 else int((display_pos / float(total_ms)) * 100)
        progress_ratio = 0.0 if total_ms <= 0 else max(0.0, min(1.0, display_pos / float(total_ms)))
        cue_in_ms, cue_out_ms = self._current_transport_cue_bounds()
        song_name = "-"
        if self.current_playing is not None:
            slot = self._slot_for_key(self.current_playing)
            if slot is not None:
                song_name = self._build_stage_slot_text(slot) or "-"
        next_song = self._next_stage_song_name()
        self._stage_display_window.update_values(
            total_time=total_text,
            elapsed=elapsed_text,
            remaining=remaining_text,
            progress_percent=progress,
            song_name=song_name,
            next_song=next_song,
            progress_text=self.progress_label.text().strip(),
            progress_style=self._build_progress_bar_stylesheet(progress_ratio, cue_in_ms, cue_out_ms),
        )
        self._stage_display_window.set_alert(self._stage_alert_message, self._stage_alert_active())
        self._stage_display_window.set_playback_status(self._stage_playback_status())

    def _stage_playback_status(self) -> str:
        states = [
            self.player.state(),
            self.player_b.state(),
        ]
        for extra in self._multi_players:
            try:
                states.append(extra.state())
            except Exception:
                pass
        if any(state == ExternalMediaPlayer.PlayingState for state in states):
            return "playing"
        if any(state == ExternalMediaPlayer.PausedState for state in states):
            return "paused"
        return "not_playing"

    def _build_stage_slot_text(self, slot: SoundButtonData) -> str:
        source = str(self.stage_display_text_source or "caption").strip().lower()
        if source == "filename":
            base_name = os.path.basename(slot.file_path or "")
            if base_name:
                return base_name
        elif source == "note":
            note = str(slot.notes or "").strip()
            if note:
                return note
        title = str(slot.title or "").strip()
        if title:
            return title
        base_name = os.path.basename(slot.file_path or "")
        if base_name:
            return os.path.splitext(base_name)[0]
        return "-"

    def _next_stage_song_name(self) -> str:
        if self.cue_mode:
            return "-"
        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if not playlist_enabled:
            if self._hover_slot_index is not None and 0 <= self._hover_slot_index < SLOTS_PER_PAGE:
                next_slot = self._hover_slot_index
            else:
                next_slot = self._next_slot_for_next_action(blocked=None)
        else:
            next_slot = self._next_slot_for_next_action(blocked=None)
        if next_slot is None:
            return "-"
        slots = self.data[self.current_group][self.current_page]
        if next_slot < 0 or next_slot >= len(slots):
            return "-"
        slot = slots[next_slot]
        if not slot.assigned or slot.marker:
            return "-"
        return self._build_stage_slot_text(slot) or "-"

    def _next_slot_for_next_action(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        blocked = blocked or set()
        if playlist_enabled:
            return self._next_playlist_slot(for_auto_advance=False, blocked=blocked)
        if self.next_play_mode == "any_available":
            return self._next_available_slot_on_current_page(blocked=blocked)
        return self._next_unplayed_slot_on_current_page(blocked=blocked)

    def _next_stage_from_hover(self) -> Optional[str]:
        slot_index = self._hover_slot_index
        if slot_index is None:
            return None
        if slot_index < 0 or slot_index >= SLOTS_PER_PAGE:
            return None
        group = self._view_group_key()
        key = (group, self.current_page, slot_index)
        slot = self._slot_for_key(key)
        if slot is None:
            return None
        return self._build_stage_slot_text(slot) or "-"

    def _view_group_key(self) -> str:
        return "Q" if self.cue_mode else self.current_group

    def _current_page_slots(self) -> List[SoundButtonData]:
        if self.cue_mode:
            return self.cue_page
        return self.data[self.current_group][self.current_page]

    def _apply_audio_preload_cache_settings(self) -> None:
        configure_audio_preload_cache_policy(
            self.preload_audio_enabled,
            self.preload_audio_memory_limit_mb,
            self.preload_memory_pressure_enabled,
        )
        self._sync_preload_pause_state(self._is_playback_in_progress())
        self._queue_current_page_audio_preload()

    def _queue_current_page_audio_preload(self) -> None:
        if not self.preload_audio_enabled or not self.preload_current_page_audio:
            return
        # Cache stores float32 stereo PCM (~352.8 bytes/ms @ 44.1kHz), use this as a practical estimate.
        bytes_per_ms = 352.8
        fallback_bytes = 5 * 1024 * 1024
        candidates: List[Tuple[str, int]] = []
        for slot in self._current_page_slots():
            if not slot.assigned or slot.marker:
                continue
            path = str(slot.file_path or "").strip()
            if not path or not os.path.exists(path):
                continue
            if is_audio_preloaded(path):
                continue
            duration_ms = max(0, int(slot.duration_ms))
            estimated = int(duration_ms * bytes_per_ms) if duration_ms > 0 else fallback_bytes
            candidates.append((path, max(1, estimated)))
        if not candidates:
            return
        remaining_bytes, _effective_limit, _used_bytes = get_audio_preload_capacity_bytes()
        total_estimated = sum(size for _path, size in candidates)
        if remaining_bytes < total_estimated:
            # Constrained RAM: prioritize first couple tracks on the page.
            paths = [path for path, _size in candidates[:2]]
        else:
            paths = [path for path, _size in candidates]
        if paths:
            request_audio_preload(paths, prioritize=True)

    def _refresh_current_page_ram_loaded_indicators(self) -> None:
        page = self._current_page_slots()
        for i, button in enumerate(self.sound_buttons):
            if i >= len(page):
                button.set_ram_loaded(False)
                continue
            slot = page[i]
            if slot.assigned and not slot.marker:
                button.set_ram_loaded(is_audio_preloaded(slot.file_path))
            else:
                button.set_ram_loaded(False)

    def _sync_preload_pause_state(self, playback_active: bool) -> None:
        should_pause = bool(self.preload_pause_on_playback and playback_active)
        if should_pause == self._preload_runtime_paused:
            return
        self._preload_runtime_paused = should_pause
        set_audio_preload_paused(should_pause)
        if not should_pause:
            self._queue_current_page_audio_preload()

    def _sync_playlist_shuffle_buttons(self) -> None:
        if self.cue_mode:
            playlist_enabled = False
            shuffle_enabled = False
        else:
            playlist_enabled = self.page_playlist_enabled[self.current_group][self.current_page]
            shuffle_enabled = self.page_shuffle_enabled[self.current_group][self.current_page]
        play_btn = self.control_buttons.get("Play List")
        shuf_btn = self.control_buttons.get("Shuffle")
        loop_btn = self.control_buttons.get("Loop")
        if play_btn:
            play_btn.setChecked(playlist_enabled)
        if shuf_btn:
            shuf_btn.setEnabled(playlist_enabled)
            shuf_btn.setChecked(shuffle_enabled)
        if loop_btn:
            if playlist_enabled:
                loop_btn.setText(tr("Loop Single") if self.playlist_loop_mode == "loop_single" else tr("Loop List"))
            else:
                loop_btn.setText(tr("Loop"))
        self._update_next_button_enabled()
        self._refresh_stage_display()

    def _update_next_button_enabled(self) -> None:
        next_btn = self.control_buttons.get("Next")
        if not next_btn:
            return
        is_playing = self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        } or self.player_b.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }
        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if playlist_enabled:
            has_next = self._has_next_playlist_slot(for_auto_advance=False)
        else:
            if self.next_play_mode == "any_available":
                has_next = self._next_available_slot_on_current_page() is not None
            else:
                has_next = self._next_unplayed_slot_on_current_page() is not None
        next_btn.setEnabled(is_playing and has_next)
        self._update_button_drag_control_state()

    def _update_button_drag_control_state(self) -> None:
        drag_btn = self.control_buttons.get("Button Drag")
        if not drag_btn:
            return
        playback_active = self._is_playback_in_progress()
        if playback_active and drag_btn.isChecked():
            drag_btn.setChecked(False)
        drag_btn.setEnabled(not playback_active)
        self._update_button_drag_visual_state()

    def _update_button_drag_visual_state(self) -> None:
        enabled = self._is_button_drag_enabled()
        if enabled:
            self.drag_mode_banner.setText(
                tr("BUTTON DRAG MODE ENABLED: Playback is not allowed. ")
                + tr("Drag a sound button with the mouse, drag over Group/Page targets, then drop on a destination button.")
            )
            self.drag_mode_banner.setVisible(True)
            if self.centralWidget() is not None:
                self.centralWidget().setStyleSheet("background:#FFF9E8;")
        else:
            self.drag_mode_banner.setVisible(False)
            if self.centralWidget() is not None:
                self.centralWidget().setStyleSheet("")

    def _cue_slot(self, slot: SoundButtonData) -> None:
        for i, cue_slot in enumerate(self.cue_page):
            if not cue_slot.assigned:
                self.cue_page[i] = SoundButtonData(
                    file_path=slot.file_path,
                    title=slot.title,
                    notes=slot.notes,
                    duration_ms=slot.duration_ms,
                    custom_color=slot.custom_color,
                    played=slot.played,
                    activity_code=slot.activity_code,
                    copied_to_cue=True,
                    volume_override_pct=slot.volume_override_pct,
                    cue_start_ms=slot.cue_start_ms,
                    cue_end_ms=slot.cue_end_ms,
                    sound_hotkey=slot.sound_hotkey,
                    sound_midi_hotkey=slot.sound_midi_hotkey,
                )
                slot.copied_to_cue = True
                self._set_dirty(True)
                break
        self._refresh_sound_grid()

    def _clear_cue_page(self) -> None:
        self.cue_page = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _is_fade_in_enabled(self) -> bool:
        btn = self.control_buttons.get("Fade In")
        return bool(btn and btn.isChecked())

    def _is_cross_fade_enabled(self) -> bool:
        btn = self.control_buttons.get("X")
        return bool(btn and btn.isChecked())

    def _is_cross_mode_enabled(self) -> bool:
        return self._is_cross_fade_enabled()

    def _current_fade_mode(self) -> str:
        # Mode priority:
        # 1) Cross fade when X is enabled.
        # 2) Fade out then fade in when both fade buttons are enabled.
        # 3) Fade out only.
        # 4) Fade in only.
        # 5) No fade mode.
        if self._is_cross_fade_enabled():
            return "cross_fade"
        fade_in_on = self._is_fade_in_enabled()
        fade_out_on = self._is_fade_out_enabled()
        if fade_in_on and fade_out_on:
            return "fade_out_then_fade_in"
        if fade_out_on:
            return "fade_out_only"
        if fade_in_on:
            return "fade_in_only"
        return "none"

    def _is_fade_out_enabled(self) -> bool:
        btn = self.control_buttons.get("Fade Out")
        return bool(btn and btn.isChecked())

    def _effective_master_volume(self) -> int:
        base = self.volume_slider.value()
        if self.talk_active:
            talk_level = max(0, min(100, int(self.talk_volume_level)))
            if self.talk_volume_mode == "set_exact":
                base = talk_level
            elif self.talk_volume_mode == "lower_only":
                base = min(base, talk_level)
            else:
                base = int(base * (talk_level / 100.0))
        return max(0, min(100, base))

    def _effective_slot_target_volume(self, slot_volume_pct: int) -> int:
        master = self._effective_master_volume()
        return max(0, min(100, int(master * (max(0, min(100, slot_volume_pct)) / 100.0))))

    def _slot_pct_for_player(self, player: ExternalMediaPlayer) -> int:
        if player is self.player:
            return self._player_slot_volume_pct
        if player is self.player_b:
            return self._player_b_slot_volume_pct
        return max(0, min(100, int(self._player_slot_pct_map.get(id(player), 75))))

    def _set_player_slot_pct(self, player: ExternalMediaPlayer, slot_pct: int) -> None:
        slot_pct = max(0, min(100, int(slot_pct)))
        if player is self.player:
            self._player_slot_volume_pct = slot_pct
            return
        if player is self.player_b:
            self._player_b_slot_volume_pct = slot_pct
            return
        self._player_slot_pct_map[id(player)] = slot_pct

    def _mark_player_started(self, player: ExternalMediaPlayer) -> None:
        self._player_started_map[id(player)] = time.monotonic()

    def _set_player_slot_key(self, player: ExternalMediaPlayer, slot_key: Tuple[str, int, int]) -> None:
        pid = id(player)
        old_key = self._player_slot_key_map.get(pid)
        if old_key is not None:
            self._active_playing_keys.discard(old_key)
        self._clear_player_cue_behavior_override(player)
        self._player_slot_key_map[pid] = slot_key
        self._active_playing_keys.add(slot_key)
        self._update_status_now_playing()

    def _clear_player_slot_key(self, player: ExternalMediaPlayer) -> None:
        pid = id(player)
        key = self._player_slot_key_map.pop(pid, None)
        if key is not None:
            self._active_playing_keys.discard(key)
        self._clear_player_cue_behavior_override(player)
        self._update_status_now_playing()

    def _clear_all_player_slot_keys(self) -> None:
        self._player_slot_key_map.clear()
        self._active_playing_keys.clear()
        self._player_end_override_ms.clear()
        self._player_ignore_cue_end.clear()
        self._update_status_now_playing()

    def _is_multi_play_enabled(self) -> bool:
        btn = self.control_buttons.get("Multi-Play")
        return bool(btn and btn.isChecked())

    def _all_active_players(self) -> List[ExternalMediaPlayer]:
        active: List[ExternalMediaPlayer] = []
        for player in [self.player, self.player_b, *self._multi_players]:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                active.append(player)
        return active

    def _prune_multi_players(self) -> None:
        remaining: List[ExternalMediaPlayer] = []
        for player in self._multi_players:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                remaining.append(player)
                continue
            self._clear_player_slot_key(player)
            self._player_slot_pct_map.pop(id(player), None)
            self._player_started_map.pop(id(player), None)
            try:
                player.deleteLater()
            except Exception:
                pass
        self._multi_players = remaining

    def _enforce_multi_play_limit(self) -> bool:
        max_allowed = max(1, int(self.max_multi_play_songs))
        active_players = self._all_active_players()
        if len(active_players) < max_allowed:
            return True
        if self.multi_play_limit_action == "disallow_more_play":
            QMessageBox.information(
                self,
                "Multi-Play Limit",
                f"Maximum Multi-Play songs reached ({max_allowed}).",
            )
            return False
        oldest = min(active_players, key=lambda p: self._player_started_map.get(id(p), 0.0))
        self._stop_single_player(oldest)
        self._prune_multi_players()
        return True

    def _stop_single_player(self, player: ExternalMediaPlayer) -> None:
        self._cancel_fade_for_player(player)
        self._stop_player_internal(player)
        self._clear_player_slot_key(player)
        self._player_slot_pct_map.pop(id(player), None)
        self._player_started_map.pop(id(player), None)
        if player is self.player:
            self._player_slot_volume_pct = 75
            if self.current_playing is not None:
                self.current_playing = None
        elif player is self.player_b:
            self._player_b_slot_volume_pct = 75

    def _set_player_volume(self, player: ExternalMediaPlayer, volume: int) -> None:
        player.setVolume(max(0, min(100, int(volume))))

    def _cancel_fade_for_player(self, player: ExternalMediaPlayer) -> None:
        self._fade_jobs = [job for job in self._fade_jobs if job["player"] is not player]

    def _start_fade(
        self,
        player: ExternalMediaPlayer,
        target_volume: int,
        seconds: float,
        stop_on_complete: bool = False,
        pause_on_complete: bool = False,
        pause_resume_volume: Optional[int] = None,
    ) -> None:
        start_volume = player.volume()
        target = max(0, min(100, int(target_volume)))
        self._cancel_fade_for_player(player)
        if target == start_volume:
            if stop_on_complete and target == 0:
                player.stop()
            return
        if seconds <= 0:
            self._set_player_volume(player, target)
            if stop_on_complete:
                player.stop()
            return
        direction = "none"
        if target > start_volume:
            direction = "in"
        elif target < start_volume:
            direction = "out"
        self._fade_jobs.append(
            {
                "player": player,
                "start": start_volume,
                "end": target,
                "dir": direction,
                "started": time.monotonic(),
                "duration": max(0.01, float(seconds)),
                "stop": stop_on_complete,
                "pause": pause_on_complete,
                "pause_resume_volume": pause_resume_volume,
            }
        )

    def _tick_fades(self) -> None:
        if not self._fade_jobs:
            if self._stop_fade_armed:
                self._stop_fade_armed = False
            self._update_fade_button_flash(False)
            return
        now = time.monotonic()
        remaining: List[dict] = []
        any_stopped = False
        for job in self._fade_jobs:
            elapsed = now - job["started"]
            ratio = max(0.0, min(1.0, elapsed / job["duration"]))
            volume = int(job["start"] + (job["end"] - job["start"]) * ratio)
            self._set_player_volume(job["player"], volume)
            if ratio >= 1.0:
                if job["stop"]:
                    job["player"].stop()
                    any_stopped = True
                elif job.get("pause"):
                    job["player"].pause()
                    resume_volume = job.get("pause_resume_volume")
                    if resume_volume is not None:
                        self._set_player_volume(job["player"], int(resume_volume))
            else:
                remaining.append(job)
        self._fade_jobs = remaining
        self._update_fade_button_flash(True)
        if any_stopped:
            self._refresh_sound_grid()

    def _update_fade_button_flash(self, any_fade: bool) -> None:
        now = time.monotonic()
        if now - self._last_fade_flash_toggle >= 0.22:
            self._fade_flash_on = not self._fade_flash_on
            self._last_fade_flash_toggle = now
        flash_on = any_fade and self._fade_flash_on
        self._set_button_flash_style("Fade In", flash_on)
        self._set_button_flash_style("Fade Out", flash_on)
        self._set_button_flash_style("X", flash_on)

    def _set_button_flash_style(self, key: str, flash_on: bool) -> None:
        btn = self.control_buttons.get(key)
        if not btn:
            return
        if flash_on:
            btn.setStyleSheet("background:#FFE680; font-weight:bold;")
        else:
            btn.setStyleSheet("")

    def _try_auto_fade_transition(self) -> None:
        if (
            self.fade_out_when_done_playing
            and self.current_playing is not None
            and self.player.state() == ExternalMediaPlayer.PlayingState
            and self.current_duration_ms > 0
            and self.fade_out_sec > 0
            and self._is_fade_out_enabled()
            and (not self._is_cross_fade_enabled())
        ):
            track_key = self.current_playing
            if self._auto_end_fade_track != track_key:
                self._auto_end_fade_track = track_key
                self._auto_end_fade_done = False
            if not self._auto_end_fade_done:
                remaining_ms = max(0, self.current_duration_ms - self.player.position())
                lead_ms = max(0, int(self.fade_out_end_lead_sec * 1000))
                if remaining_ms <= lead_ms:
                    self._auto_end_fade_done = True
                    self._start_fade(self.player, 0, self.fade_out_sec, stop_on_complete=True)

        if not self._is_cross_fade_enabled():
            return
        if self.cue_mode:
            return
        if not self.current_playing:
            return
        if not self.page_playlist_enabled[self.current_group][self.current_page]:
            return
        if self.player.state() != ExternalMediaPlayer.PlayingState:
            return
        if self.current_duration_ms <= 0:
            return
        if (time.monotonic() - self._track_started_at) < 0.35:
            return

        track_key = self.current_playing
        if self._auto_transition_track != track_key:
            self._auto_transition_track = track_key
            self._auto_transition_done = False
        if self._auto_transition_done:
            return

        remaining_ms = max(0, self.current_duration_ms - self.player.position())
        if self._is_cross_fade_enabled() and self.cross_fade_sec > 0:
            if remaining_ms <= int(self.cross_fade_sec * 1000):
                blocked: set[int] = set()
                while True:
                    next_slot = self._next_playlist_slot(for_auto_advance=True, blocked=blocked)
                    if next_slot is None:
                        break
                    if self._play_slot(next_slot):
                        self._auto_transition_done = True
                        break
                    blocked.add(next_slot)
                    if self.candidate_error_action == "stop_playback":
                        self._stop_playback()
                        break
            return

    def _swap_primary_secondary_players(self) -> None:
        try:
            self.player.positionChanged.disconnect(self._on_position_changed)
            self.player.durationChanged.disconnect(self._on_duration_changed)
            self.player.stateChanged.disconnect(self._on_state_changed)
        except TypeError:
            pass
        self.player, self.player_b = self.player_b, self.player
        self._player_slot_volume_pct, self._player_b_slot_volume_pct = (
            self._player_b_slot_volume_pct,
            self._player_slot_volume_pct,
        )
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)

    def _open_timecode_settings(self) -> None:
        self._open_options_dialog(initial_page="Audio Device / Timecode")

    def _open_options_dialog(self, initial_page: Optional[str] = None) -> None:
        available_devices = sorted(list_output_devices(), key=lambda v: v.lower())
        available_midi_output_devices = list_midi_output_devices()
        total_ram_mb, _reserved_ram_mb, preload_cap_mb = get_preload_memory_limits_mb()
        dialog = OptionsDialog(
            active_group_color=self.active_group_color,
            inactive_group_color=self.inactive_group_color,
            title_char_limit=self.title_char_limit,
            show_file_notifications=self.show_file_notifications,
            fade_in_sec=self.fade_in_sec,
            cross_fade_sec=self.cross_fade_sec,
            fade_out_sec=self.fade_out_sec,
            fade_on_quick_action_hotkey=self.fade_on_quick_action_hotkey,
            fade_on_sound_button_hotkey=self.fade_on_sound_button_hotkey,
            fade_on_pause=self.fade_on_pause,
            fade_on_resume=self.fade_on_resume,
            fade_on_stop=self.fade_on_stop,
            fade_out_when_done_playing=self.fade_out_when_done_playing,
            fade_out_end_lead_sec=self.fade_out_end_lead_sec,
            talk_volume_level=self.talk_volume_level,
            talk_fade_sec=self.talk_fade_sec,
            talk_volume_mode=self.talk_volume_mode,
            talk_blink_button=self.talk_blink_button,
            log_file_enabled=self.log_file_enabled,
            reset_all_on_startup=self.reset_all_on_startup,
            click_playing_action=self.click_playing_action,
            search_double_click_action=self.search_double_click_action,
            set_file_encoding=self.set_file_encoding,
            main_progress_display_mode=self.main_progress_display_mode,
            main_progress_show_text=self.main_progress_show_text,
            audio_output_device=self.audio_output_device,
            available_audio_devices=available_devices,
            available_midi_devices=available_midi_output_devices,
            preload_audio_enabled=self.preload_audio_enabled,
            preload_current_page_audio=self.preload_current_page_audio,
            preload_audio_memory_limit_mb=self.preload_audio_memory_limit_mb,
            preload_memory_pressure_enabled=self.preload_memory_pressure_enabled,
            preload_pause_on_playback=self.preload_pause_on_playback,
            preload_total_ram_mb=total_ram_mb,
            preload_ram_cap_mb=preload_cap_mb,
            timecode_audio_output_device=self.timecode_audio_output_device,
            timecode_midi_output_device=self.timecode_midi_output_device,
            timecode_mode=self.timecode_mode,
            timecode_fps=self.timecode_fps,
            timecode_mtc_fps=self.timecode_mtc_fps,
            timecode_mtc_idle_behavior=self.timecode_mtc_idle_behavior,
            timecode_sample_rate=self.timecode_sample_rate,
            timecode_bit_depth=self.timecode_bit_depth,
            timecode_timeline_mode=self.timecode_timeline_mode,
            max_multi_play_songs=self.max_multi_play_songs,
            multi_play_limit_action=self.multi_play_limit_action,
            playlist_play_mode=self.playlist_play_mode,
            rapid_fire_play_mode=self.rapid_fire_play_mode,
            next_play_mode=self.next_play_mode,
            playlist_loop_mode=self.playlist_loop_mode,
            candidate_error_action=self.candidate_error_action,
            web_remote_enabled=self.web_remote_enabled,
            web_remote_port=self.web_remote_port,
            web_remote_url=self._web_remote_open_url(),
            main_transport_timeline_mode=self.main_transport_timeline_mode,
            main_jog_outside_cue_action=self.main_jog_outside_cue_action,
            state_colors={
                "playing": self.state_colors["playing"],
                "played": self.state_colors["played"],
                "unplayed": self.state_colors["assigned"],
                "highlight": self.state_colors["highlighted"],
                "lock": self.state_colors["locked"],
                "error": self.state_colors["missing"],
                "place_marker": self.state_colors["marker"],
                "empty": self.state_colors["empty"],
                "copied_to_cue": self.state_colors["copied"],
                "cue_indicator": self.state_colors["cue_indicator"],
                "volume_indicator": self.state_colors["volume_indicator"],
                "midi_indicator": self.state_colors["midi_indicator"],
            },
            sound_button_text_color=self.sound_button_text_color,
            hotkeys=self.hotkeys,
            quick_action_enabled=self.quick_action_enabled,
            quick_action_keys=self.quick_action_keys,
            sound_button_hotkey_enabled=self.sound_button_hotkey_enabled,
            sound_button_hotkey_priority=self.sound_button_hotkey_priority,
            sound_button_hotkey_go_to_playing=self.sound_button_hotkey_go_to_playing,
            midi_input_device_ids=self.midi_input_device_ids,
            midi_hotkeys=self.midi_hotkeys,
            midi_quick_action_enabled=self.midi_quick_action_enabled,
            midi_quick_action_bindings=self.midi_quick_action_bindings,
            midi_sound_button_hotkey_enabled=self.midi_sound_button_hotkey_enabled,
            midi_sound_button_hotkey_priority=self.midi_sound_button_hotkey_priority,
            midi_sound_button_hotkey_go_to_playing=self.midi_sound_button_hotkey_go_to_playing,
            midi_rotary_enabled=self.midi_rotary_enabled,
            midi_rotary_group_binding=self.midi_rotary_group_binding,
            midi_rotary_page_binding=self.midi_rotary_page_binding,
            midi_rotary_sound_button_binding=self.midi_rotary_sound_button_binding,
            midi_rotary_jog_binding=self.midi_rotary_jog_binding,
            midi_rotary_volume_binding=self.midi_rotary_volume_binding,
            midi_rotary_group_invert=self.midi_rotary_group_invert,
            midi_rotary_page_invert=self.midi_rotary_page_invert,
            midi_rotary_sound_button_invert=self.midi_rotary_sound_button_invert,
            midi_rotary_jog_invert=self.midi_rotary_jog_invert,
            midi_rotary_volume_invert=self.midi_rotary_volume_invert,
            midi_rotary_group_sensitivity=self.midi_rotary_group_sensitivity,
            midi_rotary_page_sensitivity=self.midi_rotary_page_sensitivity,
            midi_rotary_sound_button_sensitivity=self.midi_rotary_sound_button_sensitivity,
            midi_rotary_group_relative_mode=self.midi_rotary_group_relative_mode,
            midi_rotary_page_relative_mode=self.midi_rotary_page_relative_mode,
            midi_rotary_sound_button_relative_mode=self.midi_rotary_sound_button_relative_mode,
            midi_rotary_jog_relative_mode=self.midi_rotary_jog_relative_mode,
            midi_rotary_volume_relative_mode=self.midi_rotary_volume_relative_mode,
            midi_rotary_volume_mode=self.midi_rotary_volume_mode,
            midi_rotary_volume_step=self.midi_rotary_volume_step,
            midi_rotary_jog_step_ms=self.midi_rotary_jog_step_ms,
            stage_display_layout=self.stage_display_layout,
            stage_display_visibility=self.stage_display_visibility,
            stage_display_text_source=self.stage_display_text_source,
            stage_display_gadgets=self.stage_display_gadgets,
            ui_language=self.ui_language,
            initial_page=initial_page,
            parent=self,
        )
        self._midi_context_handler = dialog
        self._midi_context_block_actions = True
        if dialog.exec_() != QDialog.Accepted:
            self._midi_context_handler = None
            self._midi_context_block_actions = False
            return
        self._midi_context_handler = None
        self._midi_context_block_actions = False
        self.active_group_color = dialog.active_group_color
        self.inactive_group_color = dialog.inactive_group_color
        self.title_char_limit = dialog.title_limit_spin.value()
        self.fade_in_sec = dialog.fade_in_spin.value()
        self.cross_fade_sec = dialog.cross_fade_spin.value()
        self.fade_out_sec = dialog.fade_out_spin.value()
        self.fade_on_quick_action_hotkey = dialog.fade_on_quick_action_checkbox.isChecked()
        self.fade_on_sound_button_hotkey = dialog.fade_on_sound_hotkey_checkbox.isChecked()
        self.fade_on_pause = dialog.fade_on_pause_checkbox.isChecked()
        self.fade_on_resume = dialog.fade_on_resume_checkbox.isChecked()
        self.fade_on_stop = dialog.fade_on_stop_checkbox.isChecked()
        self.fade_out_when_done_playing = dialog.fade_out_when_done_checkbox.isChecked()
        self.fade_out_end_lead_sec = dialog.fade_out_end_lead_spin.value()
        self.talk_volume_level = dialog.talk_volume_spin.value()
        self.talk_fade_sec = dialog.talk_fade_spin.value()
        self.talk_volume_mode = dialog.selected_talk_volume_mode()
        self.talk_blink_button = dialog.talk_blink_checkbox.isChecked()
        self.log_file_enabled = dialog.log_file_checkbox.isChecked()
        self.reset_all_on_startup = dialog.reset_on_startup_checkbox.isChecked()
        self.click_playing_action = dialog.selected_click_playing_action()
        self.search_double_click_action = dialog.selected_search_double_click_action()
        selected_set_file_encoding = dialog.selected_set_file_encoding()
        if selected_set_file_encoding != self.set_file_encoding:
            self.set_file_encoding = selected_set_file_encoding
            self._set_dirty(True)
        else:
            self.set_file_encoding = selected_set_file_encoding
        self.max_multi_play_songs = dialog.selected_max_multi_play_songs()
        self.multi_play_limit_action = dialog.selected_multi_play_limit_action()
        self.playlist_play_mode = dialog.selected_playlist_play_mode()
        self.rapid_fire_play_mode = dialog.selected_rapid_fire_play_mode()
        self.next_play_mode = dialog.selected_next_play_mode()
        self.playlist_loop_mode = dialog.selected_playlist_loop_mode()
        self.candidate_error_action = dialog.selected_candidate_error_action()
        self.main_transport_timeline_mode = dialog.selected_main_transport_timeline_mode()
        self.main_progress_display_mode = dialog.selected_main_progress_display_mode()
        self.main_progress_show_text = dialog.selected_main_progress_show_text()
        self.progress_label.set_display_mode(self.main_progress_display_mode)
        if self.main_progress_display_mode == "waveform":
            self._schedule_main_waveform_refresh(0)
        self.main_jog_outside_cue_action = dialog.selected_main_jog_outside_cue_action()
        self._refresh_main_jog_meta(self.seek_slider.value(), self._transport_total_ms())
        self.timecode_timeline_mode = dialog.selected_timecode_timeline_mode()
        self.timecode_audio_output_device = dialog.selected_timecode_audio_output_device()
        self.timecode_midi_output_device = dialog.selected_timecode_midi_output_device()
        selected_timecode_mode = dialog.selected_timecode_mode()
        if (
            selected_timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE
            and self.timecode_mode != TIMECODE_MODE_FOLLOW_FREEZE
        ):
            self._timecode_follow_frozen_ms = self._timecode_current_follow_ms()
        self.timecode_mode = selected_timecode_mode
        self.timecode_fps = dialog.selected_timecode_fps()
        self.timecode_mtc_fps = dialog.selected_timecode_mtc_fps()
        self.timecode_mtc_idle_behavior = dialog.selected_timecode_mtc_idle_behavior()
        self.timecode_sample_rate = dialog.selected_timecode_sample_rate()
        self.timecode_bit_depth = dialog.selected_timecode_bit_depth()
        selected_colors = dialog.selected_state_colors()
        self.state_colors["playing"] = selected_colors.get("playing", self.state_colors["playing"])
        self.state_colors["played"] = selected_colors.get("played", self.state_colors["played"])
        self.state_colors["assigned"] = selected_colors.get("unplayed", self.state_colors["assigned"])
        self.state_colors["highlighted"] = selected_colors.get("highlight", self.state_colors["highlighted"])
        self.state_colors["locked"] = selected_colors.get("lock", self.state_colors["locked"])
        self.state_colors["missing"] = selected_colors.get("error", self.state_colors["missing"])
        self.state_colors["marker"] = selected_colors.get("place_marker", self.state_colors["marker"])
        self.state_colors["empty"] = selected_colors.get("empty", self.state_colors["empty"])
        self.state_colors["copied"] = selected_colors.get("copied_to_cue", self.state_colors["copied"])
        self.state_colors["cue_indicator"] = selected_colors.get("cue_indicator", self.state_colors["cue_indicator"])
        self.state_colors["volume_indicator"] = selected_colors.get(
            "volume_indicator",
            self.state_colors["volume_indicator"],
        )
        self.state_colors["midi_indicator"] = selected_colors.get("midi_indicator", self.state_colors["midi_indicator"])
        self.sound_button_text_color = dialog.selected_sound_button_text_color()
        self.hotkeys = dialog.selected_hotkeys()
        self.quick_action_enabled = dialog.selected_quick_action_enabled()
        self.quick_action_keys = dialog.selected_quick_action_keys()[:48]
        if len(self.quick_action_keys) < 48:
            self.quick_action_keys.extend(["" for _ in range(48 - len(self.quick_action_keys))])
        self.sound_button_hotkey_enabled = dialog.selected_sound_button_hotkey_enabled()
        self.sound_button_hotkey_priority = dialog.selected_sound_button_hotkey_priority()
        self.sound_button_hotkey_go_to_playing = dialog.selected_sound_button_hotkey_go_to_playing()
        self.midi_input_device_ids = dialog.selected_midi_input_devices()
        self.midi_hotkeys = dialog.selected_midi_hotkeys()
        self.midi_quick_action_enabled = dialog.selected_midi_quick_action_enabled()
        self.midi_quick_action_bindings = dialog.selected_midi_quick_action_bindings()[:48]
        if len(self.midi_quick_action_bindings) < 48:
            self.midi_quick_action_bindings.extend(["" for _ in range(48 - len(self.midi_quick_action_bindings))])
        self.midi_sound_button_hotkey_enabled = dialog.selected_midi_sound_button_hotkey_enabled()
        self.midi_sound_button_hotkey_priority = dialog.selected_midi_sound_button_hotkey_priority()
        self.midi_sound_button_hotkey_go_to_playing = dialog.selected_midi_sound_button_hotkey_go_to_playing()
        self.midi_rotary_enabled = dialog.selected_midi_rotary_enabled()
        self.midi_rotary_group_binding = normalize_midi_binding(dialog.selected_midi_rotary_group_binding())
        self.midi_rotary_page_binding = normalize_midi_binding(dialog.selected_midi_rotary_page_binding())
        self.midi_rotary_sound_button_binding = normalize_midi_binding(dialog.selected_midi_rotary_sound_button_binding())
        self.midi_rotary_jog_binding = normalize_midi_binding(dialog.selected_midi_rotary_jog_binding())
        self.midi_rotary_volume_binding = normalize_midi_binding(dialog.selected_midi_rotary_volume_binding())
        self.midi_rotary_group_invert = bool(dialog.selected_midi_rotary_group_invert())
        self.midi_rotary_page_invert = bool(dialog.selected_midi_rotary_page_invert())
        self.midi_rotary_sound_button_invert = bool(dialog.selected_midi_rotary_sound_button_invert())
        self.midi_rotary_jog_invert = bool(dialog.selected_midi_rotary_jog_invert())
        self.midi_rotary_volume_invert = bool(dialog.selected_midi_rotary_volume_invert())
        self.midi_rotary_group_sensitivity = max(1, min(20, int(dialog.selected_midi_rotary_group_sensitivity())))
        self.midi_rotary_page_sensitivity = max(1, min(20, int(dialog.selected_midi_rotary_page_sensitivity())))
        self.midi_rotary_sound_button_sensitivity = max(
            1, min(20, int(dialog.selected_midi_rotary_sound_button_sensitivity()))
        )
        self.midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_group_relative_mode()
        )
        self.midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_page_relative_mode()
        )
        self.midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_sound_button_relative_mode()
        )
        self.midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_jog_relative_mode()
        )
        self.midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_volume_relative_mode()
        )
        mode = str(dialog.selected_midi_rotary_volume_mode()).strip().lower()
        self.midi_rotary_volume_mode = mode if mode in {"absolute", "relative"} else "relative"
        self.midi_rotary_volume_step = max(1, min(20, int(dialog.selected_midi_rotary_volume_step())))
        self.midi_rotary_jog_step_ms = max(10, min(5000, int(dialog.selected_midi_rotary_jog_step_ms())))
        self.stage_display_gadgets = normalize_stage_display_gadgets(dialog.selected_stage_display_gadgets())
        self.stage_display_layout, self.stage_display_visibility = gadgets_to_legacy_layout_visibility(
            self.stage_display_gadgets
        )
        self.stage_display_text_source = dialog.selected_stage_display_text_source()
        if self._stage_display_window is not None:
            self._stage_display_window.configure_gadgets(self.stage_display_gadgets)
            self._refresh_stage_display()
        selected_ui_language = dialog.selected_ui_language()
        if selected_ui_language != self.ui_language:
            self.ui_language = selected_ui_language
            self._apply_language()
        self._apply_hotkeys()
        self.web_remote_enabled = dialog.web_remote_enabled_checkbox.isChecked()
        self.web_remote_port = max(1, min(65535, int(dialog.web_remote_port_spin.value())))
        if self._search_window is not None:
            self._search_window.set_double_click_action(self.search_double_click_action)
        selected_device = dialog.selected_audio_output_device()
        self.preload_audio_enabled = dialog.selected_preload_audio_enabled()
        self.preload_current_page_audio = dialog.selected_preload_current_page_audio()
        self.preload_audio_memory_limit_mb = dialog.selected_preload_audio_memory_limit_mb()
        self.preload_memory_pressure_enabled = dialog.selected_preload_memory_pressure_enabled()
        self.preload_pause_on_playback = dialog.selected_preload_pause_on_playback()
        self._apply_audio_preload_cache_settings()
        if selected_device != self.audio_output_device:
            if self._switch_audio_device(selected_device):
                self.audio_output_device = selected_device
        self._apply_talk_state_volume(fade=True)
        self._update_talk_button_visual()
        self._sync_playlist_shuffle_buttons()
        self._refresh_main_transport_display()
        self._refresh_timecode_panel()
        self._update_timecode_multiplay_warning_banner()
        self._refresh_group_buttons()
        self._refresh_sound_grid()
        self._apply_web_remote_state()
        self._save_settings()

    def _api_success(self, result: Optional[dict] = None, status: int = 200) -> dict:
        return {"ok": True, "status": status, "result": result or {}}

    def _api_error(self, code: str, message: str, status: int = 400) -> dict:
        return {"ok": False, "status": status, "error": {"code": code, "message": message}}

    def _parse_api_mode(self, raw: str) -> Optional[str]:
        value = str(raw or "").strip().lower()
        if value in {"enable", "on", "true", "1"}:
            return "enable"
        if value in {"disable", "off", "false", "0"}:
            return "disable"
        if value in {"toggle", "flip"}:
            return "toggle"
        return None

    def _parse_button_id(self, raw: str, require_slot: bool) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[dict]]:
        parts = [segment for segment in str(raw or "").strip().split("-") if segment]
        if not parts:
            return None, None, None, self._api_error("invalid_id", "Missing target id.")
        if len(parts) > 3:
            return None, None, None, self._api_error("invalid_id", "Target id can be group, group-page, or group-page-button.")

        group = parts[0].upper()
        if group not in GROUPS and group != "Q":
            return None, None, None, self._api_error("invalid_group", f"Unknown group '{parts[0]}'.")

        page_index: Optional[int] = None
        slot_index: Optional[int] = None
        if len(parts) >= 2:
            try:
                page_number = int(parts[1])
            except ValueError:
                return None, None, None, self._api_error("invalid_page", f"Invalid page value '{parts[1]}'.")
            if group == "Q":
                if page_number != 1:
                    return None, None, None, self._api_error("invalid_page", "Cue group only supports page 1.")
                page_index = 0
            else:
                if page_number < 1 or page_number > PAGE_COUNT:
                    return None, None, None, self._api_error("invalid_page", f"Page must be 1..{PAGE_COUNT}.")
                page_index = page_number - 1
        elif group == "Q":
            page_index = 0

        if len(parts) == 3:
            try:
                slot_number = int(parts[2])
            except ValueError:
                return None, None, None, self._api_error("invalid_button", f"Invalid button value '{parts[2]}'.")
            if slot_number < 1 or slot_number > SLOTS_PER_PAGE:
                return None, None, None, self._api_error("invalid_button", f"Button must be 1..{SLOTS_PER_PAGE}.")
            slot_index = slot_number - 1

        if require_slot and (page_index is None or slot_index is None):
            return None, None, None, self._api_error(
                "invalid_id",
                "This endpoint requires group-page-button format, e.g. a-1-1.",
            )
        return group, page_index, slot_index, None

    def _slot_for_location(self, group: str, page_index: int, slot_index: int) -> SoundButtonData:
        if group == "Q":
            return self.cue_page[slot_index]
        return self.data[group][page_index][slot_index]

    def _api_slot_state(self, group: str, page_index: int, slot_index: int) -> dict:
        slot = self._slot_for_location(group, page_index, slot_index)
        key = (group, page_index, slot_index)
        return {
            "button_id": self._format_button_key(key).lower(),
            "group": group,
            "page": page_index + 1,
            "button": slot_index + 1,
            "title": slot.title,
            "file_path": slot.file_path,
            "assigned": slot.assigned,
            "locked": slot.locked,
            "marker": slot.marker,
            "missing": slot.missing,
            "played": slot.played,
            "highlighted": slot.highlighted,
            "is_playing": key in self._active_playing_keys,
        }

    def _api_page_state(self, group: str, page_index: int) -> dict:
        page = self.cue_page if group == "Q" else self.data[group][page_index]
        assigned = sum(1 for slot in page if slot.assigned and not slot.marker)
        played = sum(1 for slot in page if slot.assigned and not slot.marker and slot.played)
        playable = sum(1 for slot in page if slot.assigned and not slot.marker and not slot.locked and not slot.missing)
        if group == "Q":
            page_name = "Cue Page"
            page_color = None
        else:
            page_name = self.page_names[group][page_index].strip()
            page_color = self.page_colors[group][page_index]
        if group == "Q":
            playlist_enabled = False
            shuffle_enabled = False
        else:
            playlist_enabled = self.page_playlist_enabled[group][page_index]
            shuffle_enabled = self.page_shuffle_enabled[group][page_index]
        return {
            "group": group,
            "page": page_index + 1,
            "page_name": page_name,
            "page_color": page_color,
            "assigned_count": assigned,
            "played_count": played,
            "playable_count": playable,
            "playlist_enabled": playlist_enabled,
            "shuffle_enabled": shuffle_enabled,
            "is_current": (self._view_group_key() == group and self.current_page == page_index),
        }

    def _api_page_buttons(self, group: str, page_index: int) -> List[dict]:
        page = self.cue_page if group == "Q" else self.data[group][page_index]
        output: List[dict] = []
        for idx, slot in enumerate(page):
            key = (group, page_index, idx)
            marker_text = slot.title.strip() if slot.marker else ""
            if slot.marker:
                display_title = marker_text
            elif slot.assigned:
                display_title = self._build_now_playing_text(slot)
            else:
                display_title = ""
            output.append(
                {
                    "button_id": self._format_button_key(key).lower(),
                    "button": idx + 1,
                    "row": (idx // GRID_COLS) + 1,
                    "col": (idx % GRID_COLS) + 1,
                    "title": display_title,
                    "marker_text": marker_text,
                    "assigned": slot.assigned,
                    "locked": slot.locked,
                    "marker": slot.marker,
                    "missing": slot.missing,
                    "played": slot.played,
                    "is_playing": key in self._active_playing_keys,
                }
            )
        return output

    def _slot_for_key(self, slot_key: Tuple[str, int, int]) -> Optional[SoundButtonData]:
        group, page_index, slot_index = slot_key
        if slot_index < 0 or slot_index >= SLOTS_PER_PAGE:
            return None
        if group == "Q":
            return self.cue_page[slot_index]
        if group not in self.data:
            return None
        if page_index < 0 or page_index >= PAGE_COUNT:
            return None
        return self.data[group][page_index][slot_index]

    def _api_player_state_name(self, player: ExternalMediaPlayer) -> str:
        state = player.state()
        if state == ExternalMediaPlayer.PlayingState:
            return "playing"
        if state == ExternalMediaPlayer.PausedState:
            return "paused"
        return "stopped"

    def _api_playing_tracks(self) -> List[dict]:
        tracks: List[dict] = []
        for player in [self.player, self.player_b, *self._multi_players]:
            player_state = player.state()
            if player_state not in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                continue
            slot_key = self._player_slot_key_map.get(id(player))
            if slot_key is None:
                continue
            slot = self._slot_for_key(slot_key)
            if slot is None:
                continue
            duration_ms = max(0, int(player.duration()))
            position_ms = max(0, int(player.position()))
            remaining_ms = max(0, duration_ms - position_ms)
            tracks.append(
                {
                    "button_id": self._format_button_key(slot_key).lower(),
                    "title": self._build_now_playing_text(slot),
                    "file_path": slot.file_path,
                    "group": slot_key[0],
                    "page": slot_key[1] + 1,
                    "button": slot_key[2] + 1,
                    "state": self._api_player_state_name(player),
                    "position_ms": position_ms,
                    "duration_ms": duration_ms,
                    "remaining_ms": remaining_ms,
                    "position": format_clock_time(position_ms),
                    "duration": format_clock_time(duration_ms),
                    "remaining": format_clock_time(remaining_ms),
                }
            )
        tracks.sort(key=lambda item: item["button_id"])
        return tracks

    def _api_state(self) -> dict:
        current_group = self._view_group_key()
        current_page = self.current_page
        playing_tracks = self._api_playing_tracks()
        return {
            "current_group": current_group,
            "current_page": current_page + 1,
            "cue_mode": self.cue_mode,
            "talk_active": self.talk_active,
            "multi_play_enabled": self._is_multi_play_enabled(),
            "fade_in_enabled": self._is_fade_in_enabled(),
            "fade_out_enabled": self._is_fade_out_enabled(),
            "crossfade_enabled": self._is_cross_fade_enabled(),
            "playlist_enabled": False if self.cue_mode else self.page_playlist_enabled[self.current_group][self.current_page],
            "shuffle_enabled": False if self.cue_mode else self.page_shuffle_enabled[self.current_group][self.current_page],
            "is_playing": bool(self._all_active_players()),
            "playing_buttons": [self._format_button_key(k).lower() for k in sorted(self._active_playing_keys)],
            "current_playing": self._format_button_key(self.current_playing).lower() if self.current_playing else None,
            "playing_tracks": playing_tracks,
            "web_remote_url": self._web_remote_open_url(),
        }

    def _resolve_local_ip(self) -> str:
        now = time.perf_counter()
        if (now - float(self._local_ip_cache_at)) < 10.0 and self._local_ip_cache:
            return self._local_ip_cache

        candidates: List[str] = []

        # Fast path: no external process; UDP connect does not send packets.
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(("8.8.8.8", 80))
                value = sock.getsockname()[0]
                if value:
                    candidates.append(value)
            finally:
                sock.close()
        except Exception:
            pass

        # Fallback: local resolver, still offline-safe.
        try:
            infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            for info in infos:
                value = info[4][0]
                if value:
                    candidates.append(value)
        except Exception:
            pass

        resolved = "127.0.0.1"
        seen = set()
        filtered: List[str] = []
        for value in candidates:
            if value in seen:
                continue
            seen.add(value)
            try:
                ip = ipaddress.ip_address(value)
                if not isinstance(ip, ipaddress.IPv4Address):
                    continue
                if ip.is_loopback or ip.is_link_local:
                    continue
                filtered.append(value)
            except ValueError:
                continue

        for value in filtered:
            try:
                if ipaddress.ip_address(value).is_private:
                    resolved = value
                    break
            except ValueError:
                continue
        if resolved == "127.0.0.1" and filtered:
            resolved = filtered[0]

        self._local_ip_cache = resolved
        self._local_ip_cache_at = now
        return resolved

    def _web_remote_open_url(self) -> str:
        host = self._resolve_local_ip()
        return f"http://{host}:{self.web_remote_port}/"

    def _api_select_location(self, group: str, page_index: Optional[int]) -> None:
        if group == "Q":
            if not self.cue_mode:
                self._toggle_cue_mode(True)
            self.current_page = 0
            self._refresh_page_list()
            self._refresh_sound_grid()
            self._update_group_status()
            self._update_page_status()
            return
        if self.cue_mode:
            self._toggle_cue_mode(False)
        if self.current_group != group:
            self._select_group(group)
        if page_index is not None and self.current_page != page_index:
            self._select_page(page_index)

    def _reset_current_page_state_no_prompt(self) -> None:
        page = self._current_page_slots()
        for slot in page:
            slot.played = False
            if slot.assigned:
                slot.activity_code = "8"
        self.current_playlist_start = None
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _force_stop_playback(self) -> None:
        self._manual_stop_requested = True
        self._stop_fade_armed = False
        self._hard_stop_all()
        self.current_playing = None
        self.current_playlist_start = None
        self.current_duration_ms = 0
        self._last_ui_position_ms = -1
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self.seek_slider.setValue(0)
        self._vu_levels = [0.0, 0.0]
        self._refresh_sound_grid()
        self._update_now_playing_label("")
        self._update_pause_button_label()

    def _apply_web_remote_state(self) -> None:
        if not self.web_remote_enabled:
            self._stop_web_remote_service()
            self._update_web_remote_status_label()
            return
        if self._web_remote_server is not None and self._web_remote_server.is_running:
            same_host = self._web_remote_server.host == self.web_remote_host
            same_port = int(self._web_remote_server.port) == int(self.web_remote_port)
            if same_host and same_port:
                self._update_web_remote_status_label()
                return
            self._stop_web_remote_service()
        self._start_web_remote_service()
        self._update_web_remote_status_label()

    def _start_web_remote_service(self) -> None:
        if self._web_remote_server is not None and self._web_remote_server.is_running:
            self._set_web_remote_warning_banner("")
            return
        if self._is_port_listening_by_other_process(self.web_remote_port):
            self._set_web_remote_warning_banner(self._web_remote_port_conflict_text())
            return
        try:
            self._web_remote_server = WebRemoteServer(
                dispatch=self._dispatch_web_remote_command_threadsafe,
                host=self.web_remote_host,
                port=self.web_remote_port,
            )
            self._web_remote_server.start()
            self._set_web_remote_warning_banner("")
            self._update_web_remote_status_label()
        except Exception as exc:
            self._stop_web_remote_service()
            self._web_remote_server = None
            self._update_web_remote_status_label()
            if self._is_web_remote_port_conflict(exc):
                self._set_web_remote_warning_banner(self._web_remote_port_conflict_text())
                return
            self._set_web_remote_warning_banner(
                f"{tr('WEB REMOTE ERROR: Could not start Web Remote service.')} {exc}"
            )

    @staticmethod
    def _is_web_remote_port_conflict(exc: Exception) -> bool:
        if isinstance(exc, OSError):
            if getattr(exc, "errno", None) in {48, 98, 10048}:
                return True
            if getattr(exc, "winerror", None) == 10048:
                return True
        message = str(exc).lower()
        return (
            "address already in use" in message
            or "only one usage of each socket address" in message
            or "winerror 10048" in message
        )

    @staticmethod
    def _is_port_listening_by_other_process(port: int) -> bool:
        try:
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        except Exception:
            return False
        pid_self = str(os.getpid())
        port_token = f":{int(port)}"
        for line in (result.stdout or "").splitlines():
            row = line.strip()
            if not row:
                continue
            parts = re.split(r"\s+", row)
            if len(parts) < 5:
                continue
            proto, local_addr, _foreign, state, pid = parts[0], parts[1], parts[2], parts[3], parts[4]
            if proto.upper() != "TCP" or state.upper() != "LISTENING":
                continue
            if not local_addr.endswith(port_token):
                continue
            if pid != pid_self:
                return True
        return False

    def _update_web_remote_status_label(self) -> None:
        state = "Enabled" if self.web_remote_enabled else "Disabled"
        self.web_remote_status_label.setText(f"{tr('Web Remote is ')}{tr(state)}")

    def _stop_web_remote_service(self) -> None:
        server = self._web_remote_server
        self._web_remote_server = None
        if not self.web_remote_enabled:
            self._set_web_remote_warning_banner("")
        if server is None:
            return
        try:
            server.stop()
        except Exception:
            pass

    def _set_web_remote_warning_banner(self, text: str) -> None:
        message = str(text or "").strip()
        self.web_remote_warning_banner.setText(message)
        self.web_remote_warning_banner.setVisible(bool(message))

    def _web_remote_port_conflict_text(self) -> str:
        return (
            f"{tr('WEB REMOTE PORT CONFLICT:')} {tr('Port')} {self.web_remote_port} {tr('is already in use.')}\n"
            f"{tr('Change port, disable Web Remote, or close the program using this port.')}\n"
            f"{tr('Restart pySSP to resolve the issue.')}"
        )

    def _dispatch_web_remote_command_threadsafe(self, command: str, params: dict) -> dict:
        try:
            return self._main_thread_executor.call(lambda: self._handle_web_remote_command(command, params))
        except queue.Empty:
            return self._api_error("timeout", "Timed out waiting for UI thread.", status=504)
        except Exception as exc:
            return self._api_error("internal_error", str(exc), status=500)

    def _handle_web_remote_command(self, command: str, params: dict) -> dict:
        cmd = str(command or "").strip().lower()
        if cmd == "health":
            return self._api_success({"service": "web-remote", "state": self._api_state()})
        if cmd == "query_all":
            return self._api_success(self._api_state())
        if cmd == "query_button":
            group, page_index, slot_index, error = self._parse_button_id(params.get("button_id", ""), require_slot=True)
            if error:
                return error
            return self._api_success(self._api_slot_state(group, page_index, slot_index))
        if cmd == "query_pagegroup":
            group = str(params.get("group_id", "")).strip().upper()
            if group not in GROUPS and group != "Q":
                return self._api_error("invalid_group", f"Unknown group '{group}'.")
            if group == "Q":
                return self._api_success({"group": "Q", "pages": [self._api_page_state("Q", 0)]})
            pages = [self._api_page_state(group, idx) for idx in range(PAGE_COUNT)]
            return self._api_success({"group": group, "pages": pages})
        if cmd == "query_page":
            group, page_index, _slot_index, error = self._parse_button_id(params.get("page_id", ""), require_slot=False)
            if error:
                return error
            if page_index is None:
                return self._api_error("invalid_page", "Page query requires group-page format, e.g. a-1.")
            page = self._api_page_state(group, page_index)
            page["buttons"] = self._api_page_buttons(group, page_index)
            return self._api_success(page)

        if cmd == "goto":
            group, page_index, slot_index, error = self._parse_button_id(params.get("target", ""), require_slot=False)
            if error:
                return error
            self._api_select_location(group, page_index)
            if slot_index is not None:
                self.sound_buttons[slot_index].setFocus()
                self._on_sound_button_hover(slot_index)
            return self._api_success({"state": self._api_state()})

        if cmd == "play":
            group, page_index, slot_index, error = self._parse_button_id(params.get("button_id", ""), require_slot=True)
            if error:
                return error
            self._api_select_location(group, page_index)
            slot = self._slot_for_location(group, page_index, slot_index)
            if slot.locked:
                return self._api_error("locked", "Button is locked.", status=409)
            if slot.marker:
                return self._api_error("marker", "Button is a marker and cannot be played.", status=409)
            if not slot.assigned:
                return self._api_error("empty", "Button has no assigned sound.", status=409)
            if slot.missing:
                return self._api_error("missing", "Sound file is missing.", status=409)
            self._play_slot(slot_index)
            pending = self._pending_start_request == (group, page_index, slot_index)
            return self._api_success(
                {
                    "button": self._api_slot_state(group, page_index, slot_index),
                    "pending_start": pending,
                    "state": self._api_state(),
                }
            )

        if cmd == "pause":
            players = self._all_active_players()
            if not players:
                return self._api_error("not_playing", "No active playback to pause.", status=409)
            changed = False
            for player in players:
                if player.state() == ExternalMediaPlayer.PlayingState:
                    player.pause()
                    changed = True
            if not changed:
                return self._api_error("already_paused", "Playback is already paused.", status=409)
            self._update_pause_button_label()
            return self._api_success({"state": self._api_state()})

        if cmd == "resume":
            players = self._all_active_players()
            if not players:
                return self._api_error("not_paused", "No paused playback to resume.", status=409)
            changed = False
            for player in players:
                if player.state() == ExternalMediaPlayer.PausedState:
                    player.play()
                    changed = True
            if not changed:
                return self._api_error("already_playing", "Playback is already playing.", status=409)
            self._update_pause_button_label()
            return self._api_success({"state": self._api_state()})

        if cmd == "stop":
            self._stop_playback()
            return self._api_success({"state": self._api_state()})

        if cmd == "forcestop":
            self._force_stop_playback()
            return self._api_success({"state": self._api_state()})

        if cmd == "rapidfire":
            blocked: set[int] = set()
            while True:
                if self.rapid_fire_play_mode == "any_available":
                    slot_index = self._random_available_slot_on_current_page(blocked=blocked)
                else:
                    slot_index = self._random_unplayed_slot_on_current_page(blocked=blocked)
                if slot_index is None:
                    return self._api_error("no_candidate", "No playable button is available on the current page.", status=409)
                if self._play_slot(slot_index):
                    key = (self._view_group_key(), self.current_page, slot_index)
                    return self._api_success({"button": self._api_slot_state(*key), "state": self._api_state()})
                blocked.add(slot_index)
                if self.candidate_error_action == "stop_playback":
                    self._stop_playback()
                    return self._api_error("audio_load_failed", "Playback stopped due to audio load error.", status=409)

        if cmd == "playnext":
            if not self._all_active_players():
                return self._api_error("not_playing", "Cannot play next when nothing is currently playing.", status=409)
            playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
            blocked: set[int] = set()
            while True:
                if playlist_enabled:
                    next_slot = self._next_playlist_slot(for_auto_advance=False, blocked=blocked)
                else:
                    if self.next_play_mode == "any_available":
                        next_slot = self._next_available_slot_on_current_page(blocked=blocked)
                    else:
                        next_slot = self._next_unplayed_slot_on_current_page(blocked=blocked)
                if next_slot is None:
                    return self._api_error("no_next", "No next track is available.", status=409)
                if self._play_slot(next_slot):
                    return self._api_success({"state": self._api_state()})
                blocked.add(next_slot)
                if self.candidate_error_action == "stop_playback":
                    self._stop_playback()
                    return self._api_error("audio_load_failed", "Playback stopped due to audio load error.", status=409)

        if cmd in {"talk", "playlist", "playlist_shuffle", "multiplay"}:
            mode = self._parse_api_mode(params.get("mode", ""))
            if mode is None:
                return self._api_error("invalid_mode", "Mode must be enable, disable, or toggle.")
            if cmd == "talk":
                new_value = (not self.talk_active) if mode == "toggle" else (mode == "enable")
                self._toggle_talk(new_value)
                return self._api_success({"talk_active": self.talk_active, "state": self._api_state()})
            if cmd == "playlist":
                if self.cue_mode and mode == "enable":
                    return self._api_error("invalid_state", "Playlist cannot be enabled in Cue mode.", status=409)
                current = self.page_playlist_enabled[self.current_group][self.current_page]
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_playlist_mode(new_value)
                actual = self.page_playlist_enabled[self.current_group][self.current_page] if not self.cue_mode else False
                return self._api_success({"playlist_enabled": actual, "state": self._api_state()})
            if cmd == "playlist_shuffle":
                if not self.page_playlist_enabled[self.current_group][self.current_page]:
                    return self._api_error("playlist_required", "Enable playlist mode before shuffle.", status=409)
                current = self.page_shuffle_enabled[self.current_group][self.current_page]
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_shuffle_mode(new_value)
                return self._api_success(
                    {"shuffle_enabled": self.page_shuffle_enabled[self.current_group][self.current_page], "state": self._api_state()}
                )
            if cmd == "multiplay":
                current = self._is_multi_play_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_multi_play_mode(new_value)
                return self._api_success({"multi_play_enabled": self._is_multi_play_enabled(), "state": self._api_state()})

        if cmd == "fade":
            kind = str(params.get("kind", "")).strip().lower()
            mode = self._parse_api_mode(params.get("mode", ""))
            if mode is None:
                return self._api_error("invalid_mode", "Mode must be enable, disable, or toggle.")
            if kind == "fadein":
                current = self._is_fade_in_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_fade_in_mode(new_value)
            elif kind == "fadeout":
                current = self._is_fade_out_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_fade_out_mode(new_value)
            elif kind == "crossfade":
                current = self._is_cross_fade_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_cross_auto_mode(new_value)
            else:
                return self._api_error("invalid_fade", "Fade type must be fadein, fadeout, or crossfade.")
            return self._api_success({"state": self._api_state()})

        if cmd == "resetpage":
            scope = str(params.get("scope", "")).strip().lower()
            if scope == "current":
                self._stop_playback()
                self._reset_current_page_state_no_prompt()
                return self._api_success({"state": self._api_state()})
            if scope == "all":
                self._stop_playback()
                self._reset_all_played_state()
                self.current_playlist_start = None
                self._set_dirty(True)
                self._refresh_sound_grid()
                return self._api_success({"state": self._api_state()})
            return self._api_error("invalid_scope", "Scope must be current or all.")

        return self._api_error("unknown_command", f"Unknown command '{command}'.", status=404)

    def _toggle_pause(self) -> None:
        if self._is_multi_play_enabled():
            players = self._all_active_players()
            any_playing = any(p.state() == ExternalMediaPlayer.PlayingState for p in players)
            any_paused = any(p.state() == ExternalMediaPlayer.PausedState for p in players)
            if any_playing:
                playing_players = [p for p in players if p.state() == ExternalMediaPlayer.PlayingState]
                self._pause_players(playing_players)
                self._timecode_on_playback_pause()
            elif any_paused:
                paused_players = [p for p in players if p.state() == ExternalMediaPlayer.PausedState]
                self._resume_players(paused_players)
                self._timecode_on_playback_resume()
        else:
            if self.player.state() == ExternalMediaPlayer.PlayingState:
                self._pause_players([self.player])
                self._timecode_on_playback_pause()
            elif self.player.state() == ExternalMediaPlayer.PausedState:
                self._resume_players([self.player])
                self._timecode_on_playback_resume()
        self._update_pause_button_label()

    def _pause_players(self, players: List[ExternalMediaPlayer]) -> None:
        playing = [p for p in players if p.state() == ExternalMediaPlayer.PlayingState]
        if not playing:
            return
        if self.fade_on_pause and self._is_fade_out_enabled() and self.fade_out_sec > 0:
            for player in playing:
                resume_target = self._effective_slot_target_volume(self._slot_pct_for_player(player))
                self._start_fade(
                    player,
                    0,
                    self.fade_out_sec,
                    stop_on_complete=False,
                    pause_on_complete=True,
                    pause_resume_volume=resume_target,
                )
            return
        for player in playing:
            player.pause()

    def _resume_players(self, players: List[ExternalMediaPlayer]) -> None:
        paused = [p for p in players if p.state() == ExternalMediaPlayer.PausedState]
        if not paused:
            return
        if self.fade_on_resume and self._is_fade_in_enabled() and self.fade_in_sec > 0:
            for player in paused:
                target = self._effective_slot_target_volume(self._slot_pct_for_player(player))
                self._set_player_volume(player, 0)
                player.play()
                self._start_fade(player, target, self.fade_in_sec, stop_on_complete=False)
            return
        for player in paused:
            player.play()

    def _toggle_talk(self, checked: bool) -> None:
        self.talk_active = checked
        self._apply_talk_state_volume(fade=True)
        self._update_talk_button_visual()

    def _toggle_cue_mode(self, checked: bool) -> None:
        self.cue_mode = checked
        self._hotkey_selected_slot_key = None
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(checked)
        self.current_page = 0
        self.current_playlist_start = None
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()

    def _show_cue_button_menu(self, pos) -> None:
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn is None:
            return
        menu = QMenu(self)
        clear_action = menu.addAction("Clear Cue")
        selected = menu.exec_(cue_btn.mapToGlobal(pos))
        if selected == clear_action:
            self._clear_cue_page()

    def _toggle_playlist_mode(self, checked: bool) -> None:
        if self.cue_mode:
            checked = False
            play_btn = self.control_buttons.get("Play List")
            if play_btn:
                play_btn.setChecked(False)
            return
        self.page_playlist_enabled[self.current_group][self.current_page] = checked
        if not checked:
            self.page_shuffle_enabled[self.current_group][self.current_page] = False
        self.current_playlist_start = None
        self._set_dirty(True)
        self._sync_playlist_shuffle_buttons()

    def _toggle_shuffle_mode(self, checked: bool) -> None:
        if self.cue_mode:
            checked = False
        if not self.page_playlist_enabled[self.current_group][self.current_page]:
            checked = False
        self.page_shuffle_enabled[self.current_group][self.current_page] = checked
        shuf_btn = self.control_buttons.get("Shuffle")
        if shuf_btn:
            shuf_btn.setChecked(checked)
        self._set_dirty(True)

    def _open_find_dialog(self) -> None:
        if self._search_window is None:
            self._search_window = SearchWindow(self, language=self.ui_language)
            self._search_window.set_handlers(
                search_handler=self._find_sound_matches,
                goto_handler=self._go_to_found_match,
                play_handler=self._play_found_match,
            )
            self._search_window.set_double_click_action(self.search_double_click_action)
            self._search_window.destroyed.connect(lambda _=None: self._clear_search_window_ref())
        self._search_window.show()
        self._search_window.raise_()
        self._search_window.activateWindow()
        self._search_window.focus_query()

    def _clear_search_window_ref(self) -> None:
        self._search_window = None

    def _open_dsp_window(self) -> None:
        if self._dsp_window is None:
            self._dsp_window = DSPWindow(self, language=self.ui_language)
            self._dsp_window.set_config(self._dsp_config)
            self._dsp_window.configChanged.connect(self._on_dsp_config_changed)
            self._dsp_window.destroyed.connect(lambda _=None: self._clear_dsp_window_ref())
        self._dsp_window.show()
        self._dsp_window.raise_()
        self._dsp_window.activateWindow()

    def _clear_dsp_window_ref(self) -> None:
        self._dsp_window = None

    def _on_dsp_config_changed(self, config: object) -> None:
        if isinstance(config, DSPConfig):
            self._dsp_config = normalize_config(config)
            self.player.setDSPConfig(self._dsp_config)
            self.player_b.setDSPConfig(self._dsp_config)

    def _go_to_found_match(self, match: dict) -> None:
        self._focus_found_slot(match, play=False, flash=True)

    def _play_found_match(self, match: dict) -> None:
        self._focus_found_slot(match, play=True, flash=True)

    def _go_to_current_playing_page(self) -> None:
        if self.current_playing is None:
            QMessageBox.information(self, "Go To Playing", "No sound is currently playing.")
            return
        group_key, page_index, _slot_index = self.current_playing
        if group_key == "Q":
            self._toggle_cue_mode(True)
            return
        if group_key not in GROUPS:
            return
        if self.cue_mode:
            self._toggle_cue_mode(False)
        self._select_group(group_key)
        self._select_page(max(0, min(PAGE_COUNT - 1, int(page_index))))

    def _find_sound_matches(self, query: str) -> List[dict]:
        terms = [part.casefold() for part in query.split() if part.strip()]
        if not terms:
            return []
        matches: List[dict] = []

        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                page = self.data[group][page_index]
                for slot_index, slot in enumerate(page):
                    if not slot.assigned:
                        continue
                    haystack = f"{slot.title} {slot.file_path} {os.path.basename(slot.file_path)}".casefold()
                    if all(term in haystack for term in terms):
                        matches.append(
                            {
                                "group": group,
                                "page": page_index,
                                "slot": slot_index,
                                "title": slot.title,
                                "file_path": slot.file_path,
                            }
                        )

        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned:
                continue
            haystack = f"{slot.title} {slot.file_path} {os.path.basename(slot.file_path)}".casefold()
            if all(term in haystack for term in terms):
                matches.append(
                    {
                        "group": "Q",
                        "page": 0,
                        "slot": slot_index,
                        "title": slot.title,
                        "file_path": slot.file_path,
                    }
                )

        return matches

    def _focus_found_slot(self, match: dict, play: bool = False, flash: bool = False) -> None:
        group = str(match.get("group", ""))
        page = int(match.get("page", 0))
        slot = int(match.get("slot", -1))
        if slot < 0 or slot >= SLOTS_PER_PAGE:
            return
        if group == "Q":
            self._toggle_cue_mode(True)
        elif group in GROUPS:
            if self.cue_mode:
                self._toggle_cue_mode(False)
            self._select_group(group)
            self._select_page(max(0, min(PAGE_COUNT - 1, page)))
        else:
            return
        self.sound_buttons[slot].setFocus()
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot)
        if flash:
            self._flash_slot_key = (self._view_group_key(), self.current_page, slot)
            self._flash_slot_until = time.monotonic() + 1.0
            self._refresh_sound_grid()
        if play:
            self._play_slot(slot)

    def _toggle_cross_auto_mode(self, checked: bool) -> None:
        if checked and self._is_multi_play_enabled():
            checked = False
        x_btn = self.control_buttons.get("X")
        if x_btn:
            x_btn.setChecked(checked)
        if checked:
            fade_in_btn = self.control_buttons.get("Fade In")
            fade_out_btn = self.control_buttons.get("Fade Out")
            if fade_in_btn:
                fade_in_btn.setChecked(False)
            if fade_out_btn:
                fade_out_btn.setChecked(False)

    def _toggle_multi_play_mode(self, checked: bool) -> None:
        multi_btn = self.control_buttons.get("Multi-Play")
        if multi_btn:
            multi_btn.setChecked(checked)
        self._update_timecode_multiplay_warning_banner()
        if checked:
            self.page_playlist_enabled[self.current_group][self.current_page] = False
            self.page_shuffle_enabled[self.current_group][self.current_page] = False
            play_btn = self.control_buttons.get("Play List")
            if play_btn:
                play_btn.setChecked(False)
            shuf_btn = self.control_buttons.get("Shuffle")
            if shuf_btn:
                shuf_btn.setChecked(False)
                shuf_btn.setEnabled(False)
            self.current_playlist_start = None
            self._set_dirty(True)
            x_btn = self.control_buttons.get("X")
            if x_btn:
                x_btn.setChecked(False)
            self._sync_playlist_shuffle_buttons()

    def _player_for_slot_key(self, slot_key: Tuple[str, int, int]) -> Optional[ExternalMediaPlayer]:
        for player in [self.player, self.player_b, *self._multi_players]:
            if self._player_slot_key_map.get(id(player)) == slot_key:
                return player
        return None

    def _stop_track_by_slot_key(self, slot_key: Tuple[str, int, int]) -> bool:
        player = self._player_for_slot_key(slot_key)
        if player is None:
            return False
        if self.fade_on_stop and self._is_fade_out_enabled() and player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            self._start_fade(player, 0, self.fade_out_sec, stop_on_complete=True)
        else:
            self._stop_single_player(player)
        if self.current_playing == slot_key:
            self.current_playing = None
        self._refresh_sound_grid()
        return True

    def _toggle_fade_in_mode(self, checked: bool) -> None:
        fade_in_btn = self.control_buttons.get("Fade In")
        if fade_in_btn:
            fade_in_btn.setChecked(checked)
        if checked:
            x_btn = self.control_buttons.get("X")
            if x_btn:
                x_btn.setChecked(False)

    def _toggle_fade_out_mode(self, checked: bool) -> None:
        fade_out_btn = self.control_buttons.get("Fade Out")
        if fade_out_btn:
            fade_out_btn.setChecked(checked)
        if checked:
            x_btn = self.control_buttons.get("X")
            if x_btn:
                x_btn.setChecked(False)

    def _apply_talk_state_volume(self, fade: bool) -> None:
        fade_seconds = self.talk_fade_sec if fade else 0.0
        for player in [self.player, self.player_b, *self._multi_players]:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                target = self._effective_slot_target_volume(self._slot_pct_for_player(player))
                self._start_fade(player, target, fade_seconds, stop_on_complete=False)

    def _switch_audio_device(self, device_name: str) -> bool:
        self._hard_stop_all()
        old_player = self.player
        old_player_b = self.player_b
        old_multi_players = list(self._multi_players)
        if not set_output_device(device_name):
            QMessageBox.warning(self, "Audio Device", "Could not switch to selected audio device.")
            return False
        self._multi_players = []
        try:
            old_player.deleteLater()
            old_player_b.deleteLater()
            for extra in old_multi_players:
                extra.deleteLater()
        except Exception:
            pass
        try:
            self._init_audio_players()
        except Exception as exc:
            self._dispose_audio_players()
            set_output_device("")
            self.audio_output_device = ""
            try:
                self._init_audio_players()
                QMessageBox.warning(
                    self,
                    "Audio Device",
                    f"Could not switch to selected audio device.\nFell back to system default.\n\nDetails:\n{exc}",
                )
            except Exception as exc2:
                self._init_silent_audio_players()
                QMessageBox.warning(
                    self,
                    "Audio Device",
                    "Audio output failed. Running in no-audio mode.\n\n"
                    f"Primary error:\n{exc}\n\nFallback error:\n{exc2}",
                )
        self.player.setVolume(self._effective_slot_target_volume(self._player_slot_volume_pct))
        self.player_b.setVolume(self._effective_slot_target_volume(self._player_b_slot_volume_pct))
        self.current_playing = None
        self.current_duration_ms = 0
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setValue(0)
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self._update_now_playing_label("")
        self._refresh_sound_grid()
        return True

    def _tick_talk_blink(self) -> None:
        if not self.talk_active:
            return
        self._update_talk_button_visual(toggle=True)

    def _update_talk_button_visual(self, toggle: bool = False) -> None:
        talk_button = self.control_buttons.get("Talk")
        if not talk_button:
            return
        if not self.talk_active:
            talk_button.setChecked(False)
            talk_button.setStyleSheet("")
            talk_button.setText(tr("Talk"))
            return
        talk_button.setChecked(True)
        if self.talk_blink_button:
            blink_on = talk_button.property("_blink_on")
            if blink_on is None:
                blink_on = False
            if toggle:
                blink_on = not bool(blink_on)
            else:
                blink_on = True
            talk_button.setProperty("_blink_on", blink_on)
            if blink_on:
                talk_button.setStyleSheet("background:#F2D74A; font-weight:bold;")
            else:
                talk_button.setStyleSheet("")
        else:
            talk_button.setProperty("_blink_on", True)
            talk_button.setStyleSheet("background:#F2D74A; font-weight:bold;")
        talk_button.setText(tr("Talk*"))

    def _stop_playback(self) -> None:
        self._manual_stop_requested = True
        self._pending_start_request = None
        self._pending_start_token += 1
        self._auto_transition_done = True
        self._auto_end_fade_track = None
        self._auto_end_fade_done = False
        # Stop timecode immediately on user intent, regardless of audio fade-out.
        self._timecode_on_playback_stop()
        active_players = self._all_active_players()
        if self._stop_fade_armed:
            self._stop_fade_armed = False
            self._hard_stop_all()
            self._player_slot_volume_pct = 75
            self._player_b_slot_volume_pct = 75
            self.current_playing = None
            self.current_playlist_start = None
            self.current_duration_ms = 0
            self._last_ui_position_ms = -1
            self.total_time.setText("00:00:00")
            self.elapsed_time.setText("00:00:00")
            self.remaining_time.setText("00:00:00")
            self._set_progress_display(0)
            self.seek_slider.setValue(0)
            self._vu_levels = [0.0, 0.0]
            self._refresh_sound_grid()
            self._update_now_playing_label("")
            return
        if self.fade_on_stop and self._is_fade_out_enabled() and active_players:
            self._stop_fade_armed = True
            self.statusBar().showMessage(
                tr("Stop fade in progress. Click Stop again to force stop (skip fade)."),
                3000,
            )
            for player in active_players:
                self._start_fade(player, 0, self.fade_out_sec, stop_on_complete=True)
            return
        self._stop_fade_armed = False
        self.player.stop()
        self.player_b.stop()
        self._timecode_on_playback_stop()
        self._clear_all_player_slot_keys()
        for extra in list(self._multi_players):
            self._stop_single_player(extra)
        self._prune_multi_players()
        self._player_started_map.clear()
        self._player_slot_pct_map.clear()
        self._player_slot_volume_pct = 75
        self._player_b_slot_volume_pct = 75
        self.current_playing = None
        self.current_playlist_start = None
        self.current_duration_ms = 0
        self._last_ui_position_ms = -1
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self.seek_slider.setValue(0)
        self._vu_levels = [0.0, 0.0]
        self._refresh_sound_grid()
        self._update_now_playing_label("")

    def _hard_stop_all(self) -> None:
        self._fade_jobs.clear()
        self._update_fade_button_flash(False)
        self._pending_start_request = None
        self._pending_start_token += 1
        self._auto_transition_done = True
        self._auto_end_fade_track = None
        self._auto_end_fade_done = False
        self.player.stop()
        self.player_b.stop()
        self._timecode_on_playback_stop()
        self._clear_all_player_slot_keys()
        for extra in list(self._multi_players):
            self._stop_single_player(extra)
        self._prune_multi_players()
        self._player_started_map.clear()
        self._player_slot_pct_map.clear()
        self._player_slot_volume_pct = 75
        self._player_b_slot_volume_pct = 75

    def _play_next(self) -> None:
        blocked: set[int] = set()
        while True:
            next_slot = self._next_slot_for_next_action(blocked=blocked)
            if next_slot is None:
                self._update_next_button_enabled()
                return
            if self._play_slot(next_slot):
                return
            blocked.add(next_slot)
            if self.candidate_error_action == "stop_playback":
                self._stop_playback()
                return

    def _has_next_playlist_slot(self, for_auto_advance: bool = False) -> bool:
        page = self._current_page_slots()
        if not page:
            return False
        valid_slots = [
            idx
            for idx, slot in enumerate(page)
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing
        ]
        if not valid_slots:
            return False
        current_idx: Optional[int] = None
        if self.current_playing and self.current_playing[0] == self._view_group_key():
            current_idx = self.current_playing[2]
        if (
            for_auto_advance
            and self.loop_enabled
            and self.playlist_loop_mode == "loop_single"
            and current_idx is not None
            and current_idx in valid_slots
        ):
            return True
        if self.playlist_play_mode == "any_available":
            if self.page_shuffle_enabled[self.current_group][self.current_page]:
                if current_idx is not None and len(valid_slots) > 1:
                    return any(idx != current_idx for idx in valid_slots)
                return bool(valid_slots)
            start = 0
            if self.current_playlist_start is not None:
                start = self.current_playlist_start
            if current_idx is not None:
                start = current_idx + 1
            for idx in range(start, SLOTS_PER_PAGE):
                if idx in valid_slots:
                    return True
            return self.loop_enabled and self.playlist_loop_mode == "loop_list" and bool(valid_slots)
        unplayed_slots = [idx for idx in valid_slots if not page[idx].played]
        if self.page_shuffle_enabled[self.current_group][self.current_page]:
            if unplayed_slots:
                return True
            return self.loop_enabled and self.playlist_loop_mode == "loop_list" and bool(valid_slots)
        start = 0
        if self.current_playlist_start is not None:
            start = self.current_playlist_start
        if current_idx is not None:
            start = current_idx + 1
        for idx in range(start, SLOTS_PER_PAGE):
            if idx in unplayed_slots:
                return True
        return self.loop_enabled and self.playlist_loop_mode == "loop_list" and bool(valid_slots)

    def _next_unplayed_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        blocked = blocked or set()
        start_slot = -1
        current_key = self._view_group_key()
        if self.current_playing and self.current_playing[0] == current_key and self.current_playing[1] == self.current_page:
            start_slot = self.current_playing[2]
        for idx in range(start_slot + 1, SLOTS_PER_PAGE):
            slot = page[idx]
            if idx in blocked:
                continue
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and not slot.played:
                return idx
        return None

    def _next_available_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        blocked = blocked or set()
        start_slot = -1
        current_key = self._view_group_key()
        if self.current_playing and self.current_playing[0] == current_key and self.current_playing[1] == self.current_page:
            start_slot = self.current_playing[2]
        for idx in range(start_slot + 1, SLOTS_PER_PAGE):
            slot = page[idx]
            if idx in blocked:
                continue
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing:
                return idx
        return None

    def _next_slot_index(self) -> Optional[int]:
        page = self._current_page_slots()
        start_slot = -1
        if self.current_playing and self.current_playing[0] == self._view_group_key() and self.current_playing[1] == self.current_page:
            start_slot = self.current_playing[2]
        for step in range(1, SLOTS_PER_PAGE + 1):
            idx = (start_slot + step) % SLOTS_PER_PAGE
            slot = page[idx]
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing:
                return idx
        return None

    def _next_playlist_slot(self, for_auto_advance: bool = False, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        blocked = blocked or set()
        valid_slots = [
            idx
            for idx, slot in enumerate(page)
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and idx not in blocked
        ]
        if not valid_slots:
            return None
        current_idx: Optional[int] = None
        if self.current_playing and self.current_playing[0] == self._view_group_key():
            current_idx = self.current_playing[2]
        if (
            for_auto_advance
            and self.loop_enabled
            and self.playlist_loop_mode == "loop_single"
            and current_idx is not None
            and current_idx in valid_slots
        ):
            return current_idx
        any_available = self.playlist_play_mode == "any_available"
        if self.page_shuffle_enabled[self.current_group][self.current_page]:
            if any_available:
                candidates = list(valid_slots)
            else:
                candidates = [idx for idx in valid_slots if not page[idx].played]
            if not candidates:
                if self.loop_enabled and self.playlist_loop_mode == "loop_list":
                    for slot in page:
                        slot.played = False
                        if slot.assigned:
                            slot.activity_code = "8"
                    self._set_dirty(True)
                    candidates = list(valid_slots)
                else:
                    return None
            if current_idx is not None and len(candidates) > 1 and current_idx in candidates:
                candidates = [idx for idx in candidates if idx != current_idx]
            if not candidates:
                return None
            return random.choice(candidates)

        start = 0
        if self.current_playlist_start is not None:
            start = self.current_playlist_start
        if current_idx is not None:
            start = current_idx + 1

        for idx in range(start, SLOTS_PER_PAGE):
            slot = page[idx]
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and (any_available or (not slot.played)):
                return idx
        if self.loop_enabled and self.playlist_loop_mode == "loop_list":
            if not any_available:
                for slot in page:
                    slot.played = False
                    if slot.assigned:
                        slot.activity_code = "8"
                self._set_dirty(True)
            for idx in range(0, SLOTS_PER_PAGE):
                slot = page[idx]
                if slot.assigned and not slot.marker and not slot.locked and not slot.missing:
                    return idx
        return None

    def _random_unplayed_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        blocked = blocked or set()
        candidates = [
            idx
            for idx, slot in enumerate(page)
            if idx not in blocked and slot.assigned and not slot.marker and not slot.locked and not slot.missing and not slot.played
        ]
        if not candidates:
            return None
        return random.choice(candidates)

    def _random_available_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        blocked = blocked or set()
        candidates = [
            idx
            for idx, slot in enumerate(page)
            if idx not in blocked and slot.assigned and not slot.marker and not slot.locked and not slot.missing
        ]
        if not candidates:
            return None
        return random.choice(candidates)

    def _on_rapid_fire_clicked(self, _checked: bool = False) -> None:
        blocked: set[int] = set()
        while True:
            if self.rapid_fire_play_mode == "any_available":
                slot_index = self._random_available_slot_on_current_page(blocked=blocked)
            else:
                slot_index = self._random_unplayed_slot_on_current_page(blocked=blocked)
            if slot_index is None:
                return
            if self._play_slot(slot_index):
                return
            blocked.add(slot_index)
            if self.candidate_error_action == "stop_playback":
                self._stop_playback()
                return

    def _toggle_loop(self, checked: bool) -> None:
        self.loop_enabled = checked
        loop_button = self.control_buttons.get("Loop")
        if loop_button:
            loop_button.setChecked(checked)

    def _reset_current_page_state(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset Page",
            "Reset this page's played state?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._stop_playback()
        page = self._current_page_slots()
        for slot in page:
            slot.played = False
            if slot.assigned:
                slot.activity_code = "8"
        self.current_playlist_start = None
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _update_pause_button_label(self) -> None:
        pause_button = self.control_buttons.get("Pause")
        if not pause_button:
            return
        if self._is_multi_play_enabled():
            players = self._all_active_players()
            any_playing = any(p.state() == ExternalMediaPlayer.PlayingState for p in players)
            any_paused = any(p.state() == ExternalMediaPlayer.PausedState for p in players)
            paused_mode = any_paused and not any_playing
        else:
            paused_mode = self.player.state() == ExternalMediaPlayer.PausedState
        if paused_mode:
            pause_button.setText("Resume")
            pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            pause_button.setText("Pause")
            pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def _on_seek_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_seek_released(self) -> None:
        absolute = self._transport_absolute_ms_for_display(self.seek_slider.value())
        self.player.setPosition(absolute)
        self._apply_main_jog_outside_cue_behavior(absolute)
        self._mtc_sender.request_resync()
        self._is_scrubbing = False

    def _on_seek_value_changed(self, value: int) -> None:
        if self._is_scrubbing:
            self.elapsed_time.setText(format_clock_time(value))
            remaining = max(0, self._transport_total_ms() - value)
            self.remaining_time.setText(format_clock_time(remaining))
            total_ms = self._transport_total_ms()
            progress = 0 if total_ms == 0 else int((value / total_ms) * 100)
            self._refresh_main_jog_meta(value, total_ms)

    def _refresh_main_transport_display(self) -> None:
        total_ms = self._transport_total_ms()
        self.seek_slider.setRange(0, total_ms)
        self.total_time.setText(format_clock_time(total_ms))
        current_abs = 0
        if self.player is not None:
            try:
                current_abs = max(0, int(self.player.position()))
            except Exception:
                current_abs = 0
        display = self._transport_display_ms_for_absolute(current_abs)
        if not self._is_scrubbing:
            self.seek_slider.setValue(display)
        self.elapsed_time.setText(format_clock_time(display))
        remaining = max(0, total_ms - display)
        self.remaining_time.setText(format_clock_time(remaining))
        progress = 0 if total_ms == 0 else int((display / total_ms) * 100)
        self._refresh_main_jog_meta(display, total_ms)
        self._refresh_timecode_panel()
        self._refresh_stage_display()

    def _refresh_main_jog_meta(self, display_ms: int, total_ms: int) -> None:
        cue_in_ms, cue_out_ms = self._current_transport_cue_bounds()
        self.jog_in_label.setText(f"In {format_clock_time(cue_in_ms)}")
        self.jog_out_label.setText(f"Out {format_clock_time(cue_out_ms)}")
        clamped = max(0, min(total_ms, int(display_ms)))
        ratio = 0.0 if total_ms == 0 else (clamped / float(total_ms))
        pct = int(ratio * 100)
        self.jog_percent_label.setText(f"{pct}%")
        self._set_progress_display(ratio, cue_in_ms, cue_out_ms)

    def _current_transport_cue_bounds(self) -> tuple[int, int]:
        low, high = self._main_transport_bounds()
        cue_in_ms = low
        cue_out_ms = high
        if self.main_transport_timeline_mode == "audio_file":
            cue_in_ms = 0
            cue_out_ms = self.current_duration_ms
            if self.current_playing is not None:
                slot = self._slot_for_key(self.current_playing)
                if slot is not None:
                    cue_in_ms = self._cue_start_for_playback(slot, self.current_duration_ms)
                    cue_end = self._cue_end_for_playback(slot, self.current_duration_ms)
                    cue_out_ms = self.current_duration_ms if cue_end is None else cue_end
        return cue_in_ms, cue_out_ms

    def _build_progress_bar_stylesheet(
        self,
        progress_ratio: float,
        cue_in_ms: Optional[int] = None,
        cue_out_ms: Optional[int] = None,
    ) -> str:
        fill_stop = max(0.0, min(1.0, float(progress_ratio)))
        base_style_prefix = (
            "QLabel{"
            "font-size:12pt;font-weight:bold;color:white;"
            "border:1px solid #3C4E58;border-radius:4px;padding:2px 8px;"
        )
        audio_file_mode = self.main_transport_timeline_mode == "audio_file" and self.current_duration_ms > 0
        if audio_file_mode:
            in_ms = 0 if cue_in_ms is None else max(0, min(self.current_duration_ms, int(cue_in_ms)))
            out_ms = self.current_duration_ms if cue_out_ms is None else max(0, min(self.current_duration_ms, int(cue_out_ms)))
            if out_ms < in_ms:
                out_ms = in_ms
            in_ratio = in_ms / float(self.current_duration_ms)
            out_ratio = out_ms / float(self.current_duration_ms)
            eps = 0.001
            played = max(0.0, min(1.0, fill_stop))
            if played <= in_ratio:
                grad = (
                    "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    f"stop:0 #747474, stop:{in_ratio:.4f} #747474, "
                    f"stop:{min(1.0, in_ratio + eps):.4f} #111111, stop:{out_ratio:.4f} #111111, "
                    f"stop:{min(1.0, out_ratio + eps):.4f} #747474, stop:1 #747474);"
                )
            elif played >= out_ratio:
                grad = (
                    "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    f"stop:0 #747474, stop:{in_ratio:.4f} #747474, "
                    f"stop:{min(1.0, in_ratio + eps):.4f} #2ECC40, stop:{out_ratio:.4f} #2ECC40, "
                    f"stop:{min(1.0, out_ratio + eps):.4f} #747474, stop:1 #747474);"
                )
            else:
                grad = (
                    "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    f"stop:0 #747474, stop:{in_ratio:.4f} #747474, "
                    f"stop:{min(1.0, in_ratio + eps):.4f} #2ECC40, stop:{played:.4f} #2ECC40, "
                    f"stop:{min(1.0, played + eps):.4f} #111111, stop:{out_ratio:.4f} #111111, "
                    f"stop:{min(1.0, out_ratio + eps):.4f} #747474, stop:1 #747474);"
                )
            return base_style_prefix + grad + "}"
        boundary = min(1.0, fill_stop + 0.002)
        return (
            base_style_prefix
            + (
                "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 #2ECC40, stop:{fill_stop:.4f} #2ECC40, "
                f"stop:{boundary:.4f} #111111, stop:1 #111111);"
            )
            + "}"
        )

    def _set_progress_display(
        self,
        progress_ratio: float,
        cue_in_ms: Optional[int] = None,
        cue_out_ms: Optional[int] = None,
    ) -> None:
        if self.current_duration_ms <= 0 and self._main_progress_waveform:
            self._main_progress_waveform = []
        fill_stop = max(0.0, min(1.0, float(progress_ratio)))
        pct = int(fill_stop * 100)
        in_ratio = 0.0
        out_ratio = 1.0
        in_ms = 0 if cue_in_ms is None else max(0, int(cue_in_ms))
        out_ms = self.current_duration_ms if cue_out_ms is None else max(0, int(cue_out_ms))
        audio_file_mode = self.main_transport_timeline_mode == "audio_file" and self.current_duration_ms > 0
        if audio_file_mode:
            in_ms = max(0, min(self.current_duration_ms, in_ms))
            out_ms = max(0, min(self.current_duration_ms, out_ms))
            if out_ms < in_ms:
                out_ms = in_ms
            in_ratio = in_ms / float(self.current_duration_ms)
            out_ratio = out_ms / float(self.current_duration_ms)

        self.progress_label.set_transport_state(fill_stop, in_ratio, out_ratio, audio_file_mode)
        self.progress_label.set_waveform(self._main_progress_waveform)

        if self.main_progress_show_text:
            if self.main_transport_timeline_mode == "audio_file":
                self.progress_label.setText(f"{pct}%   In {format_clock_time(in_ms)}   Out {format_clock_time(out_ms)}")
            else:
                self.progress_label.setText(f"{pct}%")
        else:
            self.progress_label.setText("")

        if self.main_progress_display_mode == "waveform":
            self.progress_label.setStyleSheet(
                "font-size:12pt;font-weight:bold;color:white;"
                "border:1px solid #3C4E58;border-radius:4px;padding:2px 8px;"
            )
            return

        self.progress_label.setStyleSheet(self._build_progress_bar_stylesheet(fill_stop, cue_in_ms, cue_out_ms))

    def _on_volume_changed(self, value: int) -> None:
        self.player.setVolume(self._effective_slot_target_volume(self._player_slot_volume_pct))
        self.player_b.setVolume(self._effective_slot_target_volume(self._player_b_slot_volume_pct))
        for player in self._multi_players:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                player.setVolume(self._effective_slot_target_volume(self._slot_pct_for_player(player)))
        self.settings.volume = value

    def _reset_set_data(self) -> None:
        self.data = {
            group: [[SoundButtonData() for _ in range(SLOTS_PER_PAGE)] for _ in range(PAGE_COUNT)]
            for group in GROUPS
        }
        self.page_names = {group: ["" for _ in range(PAGE_COUNT)] for group in GROUPS}
        self.page_colors = {group: [None for _ in range(PAGE_COUNT)] for group in GROUPS}
        self.page_playlist_enabled = {group: [False for _ in range(PAGE_COUNT)] for group in GROUPS}
        self.page_shuffle_enabled = {group: [False for _ in range(PAGE_COUNT)] for group in GROUPS}

    def _open_set_dialog(self) -> None:
        start_dir = self.settings.last_open_dir
        if not start_dir and self.current_set_path:
            start_dir = os.path.dirname(self.current_set_path)
        if not start_dir:
            start_dir = os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SSP Set File",
            start_dir,
            "Sports Sounds Pro Set (*.set);;All Files (*.*)",
        )
        if not file_path:
            return
        self.settings.last_open_dir = os.path.dirname(file_path)
        self._save_settings()
        self._load_set(file_path, show_message=True, restore_last_position=False)

    def _new_set(self) -> None:
        self._hard_stop_all()
        self._drag_source_key = None
        self.current_set_path = ""
        self.settings.last_set_path = ""
        self._reset_set_data()
        self.cue_page = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self.cue_mode = False
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(False)
        self.current_group = "A"
        self.current_page = 0
        self.current_playing = None
        self.current_playlist_start = None
        self.current_duration_ms = 0
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._update_now_playing_label("")
        self._set_dirty(False)
        self.seek_slider.setValue(0)
        self.seek_slider.setRange(0, 0)
        self._vu_levels = [0.0, 0.0]
        self._save_settings()

    def _save_set(self) -> None:
        if not self.current_set_path:
            self._save_set_at()
            return
        self._write_set_file(self.current_set_path)

    def _save_set_at(self) -> None:
        start_dir = self.settings.last_save_dir
        if not start_dir and self.current_set_path:
            start_dir = os.path.dirname(self.current_set_path)
        if not start_dir:
            start_dir = os.path.expanduser("~")
        default_name = os.path.basename(self.current_set_path) if self.current_set_path else "newfile.set"
        initial_path = os.path.join(start_dir, default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save SSP Set File",
            initial_path,
            "Sports Sounds Pro Set (*.set);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".set"):
            file_path = f"{file_path}.set"
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        self._write_set_file(file_path)

    def _write_set_file(self, file_path: str) -> None:
        has_custom_cues = self._has_any_custom_cues()
        try:
            lines: List[str] = [
                "[Main]",
                "CreatedBy=SportsSounds",
                f"Personalization=pySSP {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
            ]

            for group in GROUPS:
                for page_index in range(PAGE_COUNT):
                    section_name = f"Page{page_index + 1}" if group == "A" else f"Page{group}{page_index + 1}"
                    lines.append(f"[{section_name}]")
                    page_name = clean_set_value(self.page_names[group][page_index]) or " "
                    lines.append(f"PageName={page_name}")
                    lines.append(f"PagePlay={'T' if self.page_playlist_enabled[group][page_index] else 'F'}")
                    lines.append("RapidFire=F")
                    lines.append(f"PageShuffle={'T' if self.page_shuffle_enabled[group][page_index] else 'F'}")
                    lines.append(f"PageColor={to_set_color_value(self.page_colors[group][page_index])}")

                    page = self.data[group][page_index]
                    for slot_index, slot in enumerate(page, start=1):
                        if not slot.assigned and not slot.title:
                            continue
                        if slot.marker:
                            marker_title = clean_set_value(slot.title)
                            lines.append(f"c{slot_index}={(marker_title + '%%') if marker_title else '%%'}")
                            lines.append(f"t{slot_index}= ")
                            lines.append(f"activity{slot_index}=7")
                            lines.append(f"co{slot_index}=clBtnFace")
                            continue
                        title = clean_set_value(slot.title or os.path.splitext(os.path.basename(slot.file_path))[0])
                        notes = clean_set_value(slot.notes or title)
                        lines.append(f"c{slot_index}={notes}")
                        lines.append(f"s{slot_index}={clean_set_value(slot.file_path)}")
                        lines.append(f"t{slot_index}={format_set_time(slot.duration_ms)}")
                        lines.append(f"n{slot_index}={title}")
                        if slot.volume_override_pct is not None:
                            lines.append(f"v{slot_index}={max(0, min(100, int(slot.volume_override_pct)))}")
                        lines.append(f"activity{slot_index}={'2' if slot.played else '8'}")
                        lines.append(f"co{slot_index}={to_set_color_value(slot.custom_color)}")
                        if slot.copied_to_cue:
                            lines.append(f"ci{slot_index}=Y")
                        hotkey_code = self._encode_sound_hotkey(slot.sound_hotkey)
                        if hotkey_code:
                            lines.append(f"h{slot_index}={hotkey_code}")
                        midi_hotkey_code = self._encode_sound_midi_hotkey(slot.sound_midi_hotkey)
                        if midi_hotkey_code:
                            lines.append(f"pysspmidi{slot_index}={midi_hotkey_code}")
                        cue_start, cue_end = self._cue_time_fields_for_set(slot)
                        if cue_start is not None:
                            lines.append(f"pysspcuestart{slot_index}={cue_start}")
                        if cue_end is not None:
                            lines.append(f"pysspcueend{slot_index}={cue_end}")
                    lines.append("")

            lines.extend(
                [
                    "[PageQ19]",
                    "PageName=Cue",
                    "PagePlay=F",
                    "RapidFire=F",
                    "PageShuffle=F",
                    "PageColor=clBlack",
                    "",
                ]
            )

            payload = "\r\n".join(lines)
            encoding = "utf-8-sig" if self.set_file_encoding == "utf8" else "gbk"
            with open(file_path, "w", encoding=encoding, newline="") as fh:
                fh.write(payload)
        except Exception as exc:
            QMessageBox.critical(self, "Save Set Failed", f"Could not save set file:\n{exc}")
            return

        self.current_set_path = file_path
        self._set_dirty(False)
        self.settings.last_set_path = file_path
        self.settings.last_save_dir = os.path.dirname(file_path)
        self.settings.last_open_dir = os.path.dirname(file_path)
        self._save_settings()
        self._show_save_notice_banner(f"Set Saved: {file_path}")
        if has_custom_cues:
            self._show_save_notice_banner(
                "Reminder: Custom cue points saved by pySSP are not supported by original Sports Sounds Pro.",
                timeout_ms=9000,
            )

    def _load_set(self, file_path: str, show_message: bool = True, restore_last_position: bool = False) -> None:
        try:
            result = load_set_file(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Open Set Failed", f"Could not load set file:\n{exc}")
            return

        self._hard_stop_all()
        self._drag_source_key = None
        self._reset_set_data()
        self.cue_mode = False
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(False)
        self.current_playlist_start = None
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                self.page_names[group][page_index] = result.page_names[group][page_index]
                self.page_colors[group][page_index] = result.page_colors[group][page_index]
                self.page_playlist_enabled[group][page_index] = result.page_playlist_enabled[group][page_index]
                self.page_shuffle_enabled[group][page_index] = result.page_shuffle_enabled[group][page_index]
                for slot_index in range(SLOTS_PER_PAGE):
                    src = result.pages[group][page_index][slot_index]
                    self.data[group][page_index][slot_index] = SoundButtonData(
                        file_path=src.file_path,
                        title=src.title,
                        notes=src.notes,
                        duration_ms=src.duration_ms,
                        custom_color=src.custom_color,
                        played=src.played,
                        activity_code=src.activity_code,
                        marker=src.marker,
                        copied_to_cue=src.copied_to_cue,
                        volume_override_pct=src.volume_override_pct,
                        cue_start_ms=src.cue_start_ms,
                        cue_end_ms=src.cue_end_ms,
                        sound_hotkey=src.sound_hotkey,
                        sound_midi_hotkey=src.sound_midi_hotkey,
                    )

        self.current_set_path = file_path
        if restore_last_position and self.settings.last_group in GROUPS:
            self.current_group = self.settings.last_group
            self.current_page = max(0, min(PAGE_COUNT - 1, self.settings.last_page))
        else:
            self.current_group = "A"
            self.current_page = 0
        self.current_playing = None
        self.current_duration_ms = 0
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self.seek_slider.setValue(0)
        self.seek_slider.setRange(0, 0)
        self._vu_levels = [0.0, 0.0]

        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._update_now_playing_label("")
        self._set_dirty(bool(result.migrated_legacy_cues))
        self.settings.last_set_path = file_path
        self.settings.last_open_dir = os.path.dirname(file_path)
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._save_settings()

        if show_message:
            print(
                f"[pySSP] Set loaded: {file_path} | slots={result.loaded_slots} | encoding={result.encoding}",
                flush=True,
            )

    def _restore_last_set_on_startup(self) -> None:
        last_set_path = self.settings.last_set_path.strip()
        if not last_set_path:
            return
        if not os.path.exists(last_set_path):
            self.settings.last_set_path = ""
            self._save_settings()
            return
        self._load_set(last_set_path, show_message=False, restore_last_position=True)
        self._queue_current_page_audio_preload()

    def _has_any_custom_cues(self) -> bool:
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot in self.data[group][page_index]:
                    if self._slot_has_custom_cue(slot):
                        return True
        return False

    def _save_settings(self) -> None:
        self.settings.active_group_color = self.active_group_color
        self.settings.inactive_group_color = self.inactive_group_color
        self.settings.title_char_limit = self.title_char_limit
        self.settings.show_file_notifications = self.show_file_notifications
        self.settings.volume = self.volume_slider.value() if self.volume_slider is not None else self.player.volume()
        self.settings.last_set_path = self.current_set_path
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self.settings.fade_in_sec = self.fade_in_sec
        self.settings.cross_fade_sec = self.cross_fade_sec
        self.settings.fade_out_sec = self.fade_out_sec
        self.settings.fade_on_quick_action_hotkey = bool(self.fade_on_quick_action_hotkey)
        self.settings.fade_on_sound_button_hotkey = bool(self.fade_on_sound_button_hotkey)
        self.settings.fade_on_pause = bool(self.fade_on_pause)
        self.settings.fade_on_resume = bool(self.fade_on_resume)
        self.settings.fade_on_stop = bool(self.fade_on_stop)
        self.settings.fade_out_when_done_playing = bool(self.fade_out_when_done_playing)
        self.settings.fade_out_end_lead_sec = float(self.fade_out_end_lead_sec)
        self.settings.talk_volume_level = self.talk_volume_level
        self.settings.talk_fade_sec = self.talk_fade_sec
        self.settings.talk_volume_mode = self.talk_volume_mode
        self.settings.talk_blink_button = self.talk_blink_button
        self.settings.log_file_enabled = self.log_file_enabled
        self.settings.reset_all_on_startup = self.reset_all_on_startup
        self.settings.click_playing_action = self.click_playing_action
        self.settings.search_double_click_action = self.search_double_click_action
        self.settings.set_file_encoding = self.set_file_encoding
        self.settings.ui_language = self.ui_language
        self.settings.tips_open_on_startup = bool(self.tips_open_on_startup)
        self.settings.audio_output_device = self.audio_output_device
        self.settings.preload_audio_enabled = bool(self.preload_audio_enabled)
        self.settings.preload_current_page_audio = bool(self.preload_current_page_audio)
        self.settings.preload_audio_memory_limit_mb = int(self.preload_audio_memory_limit_mb)
        self.settings.preload_memory_pressure_enabled = bool(self.preload_memory_pressure_enabled)
        self.settings.preload_pause_on_playback = bool(self.preload_pause_on_playback)
        self.settings.max_multi_play_songs = self.max_multi_play_songs
        self.settings.multi_play_limit_action = self.multi_play_limit_action
        self.settings.playlist_play_mode = self.playlist_play_mode
        self.settings.rapid_fire_play_mode = self.rapid_fire_play_mode
        self.settings.next_play_mode = self.next_play_mode
        self.settings.playlist_loop_mode = self.playlist_loop_mode
        self.settings.candidate_error_action = self.candidate_error_action
        self.settings.web_remote_enabled = self.web_remote_enabled
        self.settings.web_remote_port = self.web_remote_port
        self.settings.timecode_audio_output_device = self.timecode_audio_output_device
        self.settings.timecode_midi_output_device = self.timecode_midi_output_device
        self.settings.timecode_mode = self.timecode_mode
        self.settings.timecode_fps = self.timecode_fps
        self.settings.timecode_mtc_fps = self.timecode_mtc_fps
        self.settings.timecode_mtc_idle_behavior = self.timecode_mtc_idle_behavior
        self.settings.timecode_sample_rate = self.timecode_sample_rate
        self.settings.timecode_bit_depth = self.timecode_bit_depth
        self.settings.show_timecode_panel = bool(self.show_timecode_panel)
        self.settings.timecode_timeline_mode = self.timecode_timeline_mode
        self.settings.main_transport_timeline_mode = self.main_transport_timeline_mode
        self.settings.main_progress_display_mode = self.main_progress_display_mode
        self.settings.main_progress_show_text = bool(self.main_progress_show_text)
        self.settings.main_jog_outside_cue_action = self.main_jog_outside_cue_action
        self.settings.color_empty = self.state_colors["empty"]
        self.settings.color_unplayed = self.state_colors["assigned"]
        self.settings.color_highlight = self.state_colors["highlighted"]
        self.settings.color_playing = self.state_colors["playing"]
        self.settings.color_played = self.state_colors["played"]
        self.settings.color_error = self.state_colors["missing"]
        self.settings.color_lock = self.state_colors["locked"]
        self.settings.color_place_marker = self.state_colors["marker"]
        self.settings.color_copied_to_cue = self.state_colors["copied"]
        self.settings.color_cue_indicator = self.state_colors["cue_indicator"]
        self.settings.color_volume_indicator = self.state_colors["volume_indicator"]
        self.settings.color_midi_indicator = self.state_colors["midi_indicator"]
        self.settings.sound_button_text_color = self.sound_button_text_color
        self.settings.hotkey_new_set_1 = self.hotkeys.get("new_set", ("Ctrl+N", ""))[0]
        self.settings.hotkey_new_set_2 = self.hotkeys.get("new_set", ("Ctrl+N", ""))[1]
        self.settings.hotkey_open_set_1 = self.hotkeys.get("open_set", ("Ctrl+O", ""))[0]
        self.settings.hotkey_open_set_2 = self.hotkeys.get("open_set", ("Ctrl+O", ""))[1]
        self.settings.hotkey_save_set_1 = self.hotkeys.get("save_set", ("Ctrl+S", ""))[0]
        self.settings.hotkey_save_set_2 = self.hotkeys.get("save_set", ("Ctrl+S", ""))[1]
        self.settings.hotkey_save_set_as_1 = self.hotkeys.get("save_set_as", ("Ctrl+Shift+S", ""))[0]
        self.settings.hotkey_save_set_as_2 = self.hotkeys.get("save_set_as", ("Ctrl+Shift+S", ""))[1]
        self.settings.hotkey_search_1 = self.hotkeys.get("search", ("Ctrl+F", ""))[0]
        self.settings.hotkey_search_2 = self.hotkeys.get("search", ("Ctrl+F", ""))[1]
        self.settings.hotkey_options_1 = self.hotkeys.get("options", ("", ""))[0]
        self.settings.hotkey_options_2 = self.hotkeys.get("options", ("", ""))[1]
        self.settings.hotkey_play_selected_pause_1 = self.hotkeys.get("play_selected_pause", ("", ""))[0]
        self.settings.hotkey_play_selected_pause_2 = self.hotkeys.get("play_selected_pause", ("", ""))[1]
        self.settings.hotkey_play_selected_1 = self.hotkeys.get("play_selected", ("", ""))[0]
        self.settings.hotkey_play_selected_2 = self.hotkeys.get("play_selected", ("", ""))[1]
        self.settings.hotkey_pause_toggle_1 = self.hotkeys.get("pause_toggle", ("P", ""))[0]
        self.settings.hotkey_pause_toggle_2 = self.hotkeys.get("pause_toggle", ("P", ""))[1]
        self.settings.hotkey_stop_playback_1 = self.hotkeys.get("stop_playback", ("Space", "Return"))[0]
        self.settings.hotkey_stop_playback_2 = self.hotkeys.get("stop_playback", ("Space", "Return"))[1]
        self.settings.hotkey_talk_1 = self.hotkeys.get("talk", ("", ""))[0]
        self.settings.hotkey_talk_2 = self.hotkeys.get("talk", ("", ""))[1]
        self.settings.hotkey_next_group_1 = self.hotkeys.get("next_group", ("", ""))[0]
        self.settings.hotkey_next_group_2 = self.hotkeys.get("next_group", ("", ""))[1]
        self.settings.hotkey_prev_group_1 = self.hotkeys.get("prev_group", ("", ""))[0]
        self.settings.hotkey_prev_group_2 = self.hotkeys.get("prev_group", ("", ""))[1]
        self.settings.hotkey_next_page_1 = self.hotkeys.get("next_page", ("", ""))[0]
        self.settings.hotkey_next_page_2 = self.hotkeys.get("next_page", ("", ""))[1]
        self.settings.hotkey_prev_page_1 = self.hotkeys.get("prev_page", ("", ""))[0]
        self.settings.hotkey_prev_page_2 = self.hotkeys.get("prev_page", ("", ""))[1]
        self.settings.hotkey_next_sound_button_1 = self.hotkeys.get("next_sound_button", ("", ""))[0]
        self.settings.hotkey_next_sound_button_2 = self.hotkeys.get("next_sound_button", ("", ""))[1]
        self.settings.hotkey_prev_sound_button_1 = self.hotkeys.get("prev_sound_button", ("", ""))[0]
        self.settings.hotkey_prev_sound_button_2 = self.hotkeys.get("prev_sound_button", ("", ""))[1]
        self.settings.hotkey_multi_play_1 = self.hotkeys.get("multi_play", ("", ""))[0]
        self.settings.hotkey_multi_play_2 = self.hotkeys.get("multi_play", ("", ""))[1]
        self.settings.hotkey_go_to_playing_1 = self.hotkeys.get("go_to_playing", ("", ""))[0]
        self.settings.hotkey_go_to_playing_2 = self.hotkeys.get("go_to_playing", ("", ""))[1]
        self.settings.hotkey_loop_1 = self.hotkeys.get("loop", ("", ""))[0]
        self.settings.hotkey_loop_2 = self.hotkeys.get("loop", ("", ""))[1]
        self.settings.hotkey_next_1 = self.hotkeys.get("next", ("", ""))[0]
        self.settings.hotkey_next_2 = self.hotkeys.get("next", ("", ""))[1]
        self.settings.hotkey_rapid_fire_1 = self.hotkeys.get("rapid_fire", ("", ""))[0]
        self.settings.hotkey_rapid_fire_2 = self.hotkeys.get("rapid_fire", ("", ""))[1]
        self.settings.hotkey_shuffle_1 = self.hotkeys.get("shuffle", ("", ""))[0]
        self.settings.hotkey_shuffle_2 = self.hotkeys.get("shuffle", ("", ""))[1]
        self.settings.hotkey_reset_page_1 = self.hotkeys.get("reset_page", ("", ""))[0]
        self.settings.hotkey_reset_page_2 = self.hotkeys.get("reset_page", ("", ""))[1]
        self.settings.hotkey_play_list_1 = self.hotkeys.get("play_list", ("", ""))[0]
        self.settings.hotkey_play_list_2 = self.hotkeys.get("play_list", ("", ""))[1]
        self.settings.hotkey_fade_in_1 = self.hotkeys.get("fade_in", ("", ""))[0]
        self.settings.hotkey_fade_in_2 = self.hotkeys.get("fade_in", ("", ""))[1]
        self.settings.hotkey_cross_fade_1 = self.hotkeys.get("cross_fade", ("", ""))[0]
        self.settings.hotkey_cross_fade_2 = self.hotkeys.get("cross_fade", ("", ""))[1]
        self.settings.hotkey_fade_out_1 = self.hotkeys.get("fade_out", ("", ""))[0]
        self.settings.hotkey_fade_out_2 = self.hotkeys.get("fade_out", ("", ""))[1]
        self.settings.hotkey_mute_1 = self.hotkeys.get("mute", ("", ""))[0]
        self.settings.hotkey_mute_2 = self.hotkeys.get("mute", ("", ""))[1]
        self.settings.hotkey_volume_up_1 = self.hotkeys.get("volume_up", ("", ""))[0]
        self.settings.hotkey_volume_up_2 = self.hotkeys.get("volume_up", ("", ""))[1]
        self.settings.hotkey_volume_down_1 = self.hotkeys.get("volume_down", ("", ""))[0]
        self.settings.hotkey_volume_down_2 = self.hotkeys.get("volume_down", ("", ""))[1]
        self.settings.quick_action_enabled = bool(self.quick_action_enabled)
        self.settings.quick_action_keys = list(self.quick_action_keys[:48])
        self.settings.sound_button_hotkey_enabled = bool(self.sound_button_hotkey_enabled)
        self.settings.sound_button_hotkey_priority = self.sound_button_hotkey_priority
        self.settings.sound_button_hotkey_go_to_playing = bool(self.sound_button_hotkey_go_to_playing)
        self.settings.midi_input_device_ids = list(self.midi_input_device_ids)
        self.settings.midi_hotkey_new_set_1 = self.midi_hotkeys.get("new_set", ("", ""))[0]
        self.settings.midi_hotkey_new_set_2 = self.midi_hotkeys.get("new_set", ("", ""))[1]
        self.settings.midi_hotkey_open_set_1 = self.midi_hotkeys.get("open_set", ("", ""))[0]
        self.settings.midi_hotkey_open_set_2 = self.midi_hotkeys.get("open_set", ("", ""))[1]
        self.settings.midi_hotkey_save_set_1 = self.midi_hotkeys.get("save_set", ("", ""))[0]
        self.settings.midi_hotkey_save_set_2 = self.midi_hotkeys.get("save_set", ("", ""))[1]
        self.settings.midi_hotkey_save_set_as_1 = self.midi_hotkeys.get("save_set_as", ("", ""))[0]
        self.settings.midi_hotkey_save_set_as_2 = self.midi_hotkeys.get("save_set_as", ("", ""))[1]
        self.settings.midi_hotkey_search_1 = self.midi_hotkeys.get("search", ("", ""))[0]
        self.settings.midi_hotkey_search_2 = self.midi_hotkeys.get("search", ("", ""))[1]
        self.settings.midi_hotkey_options_1 = self.midi_hotkeys.get("options", ("", ""))[0]
        self.settings.midi_hotkey_options_2 = self.midi_hotkeys.get("options", ("", ""))[1]
        self.settings.midi_hotkey_play_selected_pause_1 = self.midi_hotkeys.get("play_selected_pause", ("", ""))[0]
        self.settings.midi_hotkey_play_selected_pause_2 = self.midi_hotkeys.get("play_selected_pause", ("", ""))[1]
        self.settings.midi_hotkey_play_selected_1 = self.midi_hotkeys.get("play_selected", ("", ""))[0]
        self.settings.midi_hotkey_play_selected_2 = self.midi_hotkeys.get("play_selected", ("", ""))[1]
        self.settings.midi_hotkey_pause_toggle_1 = self.midi_hotkeys.get("pause_toggle", ("", ""))[0]
        self.settings.midi_hotkey_pause_toggle_2 = self.midi_hotkeys.get("pause_toggle", ("", ""))[1]
        self.settings.midi_hotkey_stop_playback_1 = self.midi_hotkeys.get("stop_playback", ("", ""))[0]
        self.settings.midi_hotkey_stop_playback_2 = self.midi_hotkeys.get("stop_playback", ("", ""))[1]
        self.settings.midi_hotkey_talk_1 = self.midi_hotkeys.get("talk", ("", ""))[0]
        self.settings.midi_hotkey_talk_2 = self.midi_hotkeys.get("talk", ("", ""))[1]
        self.settings.midi_hotkey_next_group_1 = self.midi_hotkeys.get("next_group", ("", ""))[0]
        self.settings.midi_hotkey_next_group_2 = self.midi_hotkeys.get("next_group", ("", ""))[1]
        self.settings.midi_hotkey_prev_group_1 = self.midi_hotkeys.get("prev_group", ("", ""))[0]
        self.settings.midi_hotkey_prev_group_2 = self.midi_hotkeys.get("prev_group", ("", ""))[1]
        self.settings.midi_hotkey_next_page_1 = self.midi_hotkeys.get("next_page", ("", ""))[0]
        self.settings.midi_hotkey_next_page_2 = self.midi_hotkeys.get("next_page", ("", ""))[1]
        self.settings.midi_hotkey_prev_page_1 = self.midi_hotkeys.get("prev_page", ("", ""))[0]
        self.settings.midi_hotkey_prev_page_2 = self.midi_hotkeys.get("prev_page", ("", ""))[1]
        self.settings.midi_hotkey_next_sound_button_1 = self.midi_hotkeys.get("next_sound_button", ("", ""))[0]
        self.settings.midi_hotkey_next_sound_button_2 = self.midi_hotkeys.get("next_sound_button", ("", ""))[1]
        self.settings.midi_hotkey_prev_sound_button_1 = self.midi_hotkeys.get("prev_sound_button", ("", ""))[0]
        self.settings.midi_hotkey_prev_sound_button_2 = self.midi_hotkeys.get("prev_sound_button", ("", ""))[1]
        self.settings.midi_hotkey_multi_play_1 = self.midi_hotkeys.get("multi_play", ("", ""))[0]
        self.settings.midi_hotkey_multi_play_2 = self.midi_hotkeys.get("multi_play", ("", ""))[1]
        self.settings.midi_hotkey_go_to_playing_1 = self.midi_hotkeys.get("go_to_playing", ("", ""))[0]
        self.settings.midi_hotkey_go_to_playing_2 = self.midi_hotkeys.get("go_to_playing", ("", ""))[1]
        self.settings.midi_hotkey_loop_1 = self.midi_hotkeys.get("loop", ("", ""))[0]
        self.settings.midi_hotkey_loop_2 = self.midi_hotkeys.get("loop", ("", ""))[1]
        self.settings.midi_hotkey_next_1 = self.midi_hotkeys.get("next", ("", ""))[0]
        self.settings.midi_hotkey_next_2 = self.midi_hotkeys.get("next", ("", ""))[1]
        self.settings.midi_hotkey_rapid_fire_1 = self.midi_hotkeys.get("rapid_fire", ("", ""))[0]
        self.settings.midi_hotkey_rapid_fire_2 = self.midi_hotkeys.get("rapid_fire", ("", ""))[1]
        self.settings.midi_hotkey_shuffle_1 = self.midi_hotkeys.get("shuffle", ("", ""))[0]
        self.settings.midi_hotkey_shuffle_2 = self.midi_hotkeys.get("shuffle", ("", ""))[1]
        self.settings.midi_hotkey_reset_page_1 = self.midi_hotkeys.get("reset_page", ("", ""))[0]
        self.settings.midi_hotkey_reset_page_2 = self.midi_hotkeys.get("reset_page", ("", ""))[1]
        self.settings.midi_hotkey_play_list_1 = self.midi_hotkeys.get("play_list", ("", ""))[0]
        self.settings.midi_hotkey_play_list_2 = self.midi_hotkeys.get("play_list", ("", ""))[1]
        self.settings.midi_hotkey_fade_in_1 = self.midi_hotkeys.get("fade_in", ("", ""))[0]
        self.settings.midi_hotkey_fade_in_2 = self.midi_hotkeys.get("fade_in", ("", ""))[1]
        self.settings.midi_hotkey_cross_fade_1 = self.midi_hotkeys.get("cross_fade", ("", ""))[0]
        self.settings.midi_hotkey_cross_fade_2 = self.midi_hotkeys.get("cross_fade", ("", ""))[1]
        self.settings.midi_hotkey_fade_out_1 = self.midi_hotkeys.get("fade_out", ("", ""))[0]
        self.settings.midi_hotkey_fade_out_2 = self.midi_hotkeys.get("fade_out", ("", ""))[1]
        self.settings.midi_hotkey_mute_1 = self.midi_hotkeys.get("mute", ("", ""))[0]
        self.settings.midi_hotkey_mute_2 = self.midi_hotkeys.get("mute", ("", ""))[1]
        self.settings.midi_hotkey_volume_up_1 = self.midi_hotkeys.get("volume_up", ("", ""))[0]
        self.settings.midi_hotkey_volume_up_2 = self.midi_hotkeys.get("volume_up", ("", ""))[1]
        self.settings.midi_hotkey_volume_down_1 = self.midi_hotkeys.get("volume_down", ("", ""))[0]
        self.settings.midi_hotkey_volume_down_2 = self.midi_hotkeys.get("volume_down", ("", ""))[1]
        self.settings.midi_quick_action_enabled = bool(self.midi_quick_action_enabled)
        self.settings.midi_quick_action_bindings = list(self.midi_quick_action_bindings[:48])
        self.settings.midi_sound_button_hotkey_enabled = bool(self.midi_sound_button_hotkey_enabled)
        self.settings.midi_sound_button_hotkey_priority = self.midi_sound_button_hotkey_priority
        self.settings.midi_sound_button_hotkey_go_to_playing = bool(self.midi_sound_button_hotkey_go_to_playing)
        self.settings.midi_rotary_enabled = bool(self.midi_rotary_enabled)
        self.settings.midi_rotary_group_binding = self.midi_rotary_group_binding
        self.settings.midi_rotary_page_binding = self.midi_rotary_page_binding
        self.settings.midi_rotary_sound_button_binding = self.midi_rotary_sound_button_binding
        self.settings.midi_rotary_jog_binding = self.midi_rotary_jog_binding
        self.settings.midi_rotary_volume_binding = self.midi_rotary_volume_binding
        self.settings.midi_rotary_group_invert = bool(self.midi_rotary_group_invert)
        self.settings.midi_rotary_page_invert = bool(self.midi_rotary_page_invert)
        self.settings.midi_rotary_sound_button_invert = bool(self.midi_rotary_sound_button_invert)
        self.settings.midi_rotary_jog_invert = bool(self.midi_rotary_jog_invert)
        self.settings.midi_rotary_volume_invert = bool(self.midi_rotary_volume_invert)
        self.settings.midi_rotary_group_sensitivity = int(self.midi_rotary_group_sensitivity)
        self.settings.midi_rotary_page_sensitivity = int(self.midi_rotary_page_sensitivity)
        self.settings.midi_rotary_sound_button_sensitivity = int(self.midi_rotary_sound_button_sensitivity)
        self.settings.midi_rotary_group_relative_mode = self.midi_rotary_group_relative_mode
        self.settings.midi_rotary_page_relative_mode = self.midi_rotary_page_relative_mode
        self.settings.midi_rotary_sound_button_relative_mode = self.midi_rotary_sound_button_relative_mode
        self.settings.midi_rotary_jog_relative_mode = self.midi_rotary_jog_relative_mode
        self.settings.midi_rotary_volume_relative_mode = self.midi_rotary_volume_relative_mode
        self.settings.midi_rotary_volume_mode = self.midi_rotary_volume_mode
        self.settings.midi_rotary_volume_step = int(self.midi_rotary_volume_step)
        self.settings.midi_rotary_jog_step_ms = int(self.midi_rotary_jog_step_ms)
        self.settings.stage_display_layout = list(self.stage_display_layout)
        self.settings.stage_display_show_current_time = bool(self.stage_display_visibility.get("current_time", True))
        self.settings.stage_display_show_alert = bool(self.stage_display_visibility.get("alert", False))
        self.settings.stage_display_show_total_time = bool(self.stage_display_visibility.get("total_time", True))
        self.settings.stage_display_show_elapsed = bool(self.stage_display_visibility.get("elapsed", True))
        self.settings.stage_display_show_remaining = bool(self.stage_display_visibility.get("remaining", True))
        self.settings.stage_display_show_progress_bar = bool(self.stage_display_visibility.get("progress_bar", True))
        self.settings.stage_display_show_song_name = bool(self.stage_display_visibility.get("song_name", True))
        self.settings.stage_display_show_next_song = bool(self.stage_display_visibility.get("next_song", True))
        self.settings.stage_display_gadgets = normalize_stage_display_gadgets(self.stage_display_gadgets)
        self.settings.stage_display_text_source = self.stage_display_text_source
        save_settings(self.settings)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_page_list_item_heights()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.page_list.viewport():
            if event.type() == QEvent.Resize:
                self._update_page_list_item_heights()
            elif event.type() == QEvent.DragEnter:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.DragMove:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if self._handle_drag_over_page(row):
                        event.acceptProposedAction()
                        return True
            elif event.type() == QEvent.Drop:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)

    def _handle_space_bar_action(self) -> None:
        self._stop_playback()
        return

    def keyPressEvent(self, event) -> None:
        if event.isAutoRepeat():
            super().keyPressEvent(event)
            return
        key = int(event.key())
        handlers = self._modifier_hotkey_handlers.get(key)
        if handlers:
            if key not in self._modifier_hotkey_down:
                self._modifier_hotkey_down.add(key)
                for handler in handlers:
                    handler()
            return
        super().keyPressEvent(event)

    def _click_control_button(self, key: str) -> None:
        button = self.control_buttons.get(key)
        if button is None or (not button.isEnabled()):
            return
        button.click()

    def _toggle_control_button(self, key: str) -> None:
        button = self.control_buttons.get(key)
        if button is None or (not button.isEnabled()) or (not button.isCheckable()):
            return
        button.click()

    def _hotkey_toggle_talk(self) -> None:
        self._toggle_control_button("Talk")

    def _hotkey_select_group_delta(self, delta: int) -> None:
        if self.cue_mode:
            self._toggle_cue_mode(False)
        try:
            idx = GROUPS.index(self.current_group)
        except ValueError:
            idx = 0
        next_idx = (idx + delta) % len(GROUPS)
        self._select_group(GROUPS[next_idx])

    def _hotkey_select_page_delta(self, delta: int) -> None:
        if self.cue_mode:
            self._toggle_cue_mode(False)
        next_page = (self.current_page + delta) % PAGE_COUNT
        self._select_page(next_page)

    def _hotkey_select_sound_button_delta(self, delta: int) -> None:
        page = self._current_page_slots()
        candidates = [i for i, slot in enumerate(page) if slot.assigned and not slot.marker]
        if not candidates:
            return
        current_index = -1
        key = self._hotkey_selected_slot_key
        if key is not None and key[0] == self._view_group_key() and key[1] == self.current_page:
            current_index = key[2]
        elif self.current_playing is not None and self.current_playing[0] == self._view_group_key() and self.current_playing[1] == self.current_page:
            current_index = self.current_playing[2]

        if current_index in candidates:
            pos = candidates.index(current_index)
            next_slot = candidates[(pos + delta) % len(candidates)]
        else:
            next_slot = candidates[0] if delta >= 0 else candidates[-1]

        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, next_slot)
        self.sound_buttons[next_slot].setFocus()
        self._on_sound_button_hover(next_slot)
        self._refresh_sound_grid()

    def _hotkey_play_selected(self) -> None:
        slot_index: Optional[int] = None
        key = self._hotkey_selected_slot_key
        if key is not None and key[0] == self._view_group_key() and key[1] == self.current_page:
            slot_index = key[2]
        else:
            for i, btn in enumerate(self.sound_buttons):
                if btn.hasFocus():
                    slot_index = i
                    break
        if slot_index is None:
            return
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        self._play_slot(slot_index)

    def _hotkey_play_selected_pause(self) -> None:
        slot_index: Optional[int] = None
        key = self._hotkey_selected_slot_key
        if key is not None and key[0] == self._view_group_key() and key[1] == self.current_page:
            slot_index = key[2]
        else:
            for i, btn in enumerate(self.sound_buttons):
                if btn.hasFocus():
                    slot_index = i
                    break
        if slot_index is None:
            return
        selected_key = (self._view_group_key(), self.current_page, slot_index)
        self._hotkey_selected_slot_key = selected_key

        selected_playing: List[ExternalMediaPlayer] = []
        selected_paused: List[ExternalMediaPlayer] = []
        for player in [self.player, self.player_b, *self._multi_players]:
            if self._player_slot_key_map.get(id(player)) != selected_key:
                continue
            state = player.state()
            if state == ExternalMediaPlayer.PlayingState:
                selected_playing.append(player)
            elif state == ExternalMediaPlayer.PausedState:
                selected_paused.append(player)

        if selected_playing:
            self._pause_players(selected_playing)
            self._timecode_on_playback_pause()
            self._update_pause_button_label()
            return
        if selected_paused:
            self._resume_players(selected_paused)
            self._update_pause_button_label()
            return
        self._play_slot(slot_index)

    def _quick_action_trigger(self, slot_index: int) -> None:
        if slot_index < 0 or slot_index >= SLOTS_PER_PAGE:
            return
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        self._play_slot(slot_index, allow_fade=self.fade_on_quick_action_hotkey)

    def _registered_system_and_quick_tokens(self) -> set[str]:
        tokens: set[str] = set()
        for key in SYSTEM_HOTKEY_ORDER_DEFAULT:
            h1, h2 = self._normalized_hotkey_pair(key)
            for seq_text in [h1, h2]:
                key_token = self._normalize_hotkey_text(seq_text)
                if not key_token:
                    continue
                modifier_key = self._modifier_key_from_hotkey_text(seq_text)
                if modifier_key is not None:
                    tokens.add(key_token)
                    continue
                seq = self._key_sequence_from_hotkey_text(seq_text)
                if seq is not None:
                    tokens.add(key_token)
        if self.quick_action_enabled:
            for raw in self.quick_action_keys[:48]:
                key_token = self._normalize_hotkey_text(raw)
                if not key_token:
                    continue
                seq = self._key_sequence_from_hotkey_text(raw)
                if seq is not None:
                    tokens.add(key_token)
        return tokens

    def _active_button_trigger_badges(
        self,
        slot_index: int,
        slot: SoundButtonData,
        sound_bindings: Dict[str, Tuple[str, int, int]],
        blocked_sound_tokens: set[str],
    ) -> List[str]:
        if not slot.assigned or slot.marker:
            return []
        badges: List[str] = []
        seen: set[str] = set()
        slot_key = (self._view_group_key(), self.current_page, slot_index)
        if self.sound_button_hotkey_enabled:
            sound_token = self._normalize_hotkey_text(self._parse_sound_hotkey(slot.sound_hotkey))
            if sound_token and sound_bindings.get(sound_token) == slot_key:
                if sound_token not in blocked_sound_tokens:
                    badge = f"[{sound_token.lower()}]"
                    badges.append(badge)
                    seen.add(badge)

        if self.quick_action_enabled and slot_index < len(self.quick_action_keys):
            quick_token = self._normalize_hotkey_text(self.quick_action_keys[slot_index])
            if quick_token and self._key_sequence_from_hotkey_text(quick_token) is not None:
                quick_blocked = (
                    self.sound_button_hotkey_enabled
                    and self.sound_button_hotkey_priority == "sound_button_first"
                    and quick_token in sound_bindings
                )
                if not quick_blocked:
                    badge = f"[{quick_token.lower()}]"
                    if badge not in seen:
                        badges.append(badge)
        return badges

    def _collect_sound_button_hotkey_bindings(self) -> Dict[str, Tuple[str, int, int]]:
        bindings: Dict[str, Tuple[str, int, int]] = {}
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    token = self._normalize_hotkey_text(self._parse_sound_hotkey(slot.sound_hotkey))
                    if not token or token in bindings:
                        continue
                    bindings[token] = (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned or slot.marker:
                continue
            token = self._normalize_hotkey_text(self._parse_sound_hotkey(slot.sound_hotkey))
            if not token or token in bindings:
                continue
            bindings[token] = ("Q", 0, slot_index)
        return bindings

    def _collect_sound_button_midi_bindings(self) -> Dict[str, Tuple[str, int, int]]:
        bindings: Dict[str, Tuple[str, int, int]] = {}
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    token = normalize_midi_binding(slot.sound_midi_hotkey)
                    if not token or token in bindings:
                        continue
                    bindings[token] = (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned or slot.marker:
                continue
            token = normalize_midi_binding(slot.sound_midi_hotkey)
            if not token or token in bindings:
                continue
            bindings[token] = ("Q", 0, slot_index)
        return bindings

    def _sound_button_hotkey_trigger(self, slot_key: Tuple[str, int, int]) -> None:
        if self._is_button_drag_enabled():
            return
        old_cue_mode = self.cue_mode
        old_group = self.current_group
        old_page = self.current_page

        group, page_index, slot_index = slot_key
        if group == "Q":
            self._toggle_cue_mode(True)
        else:
            if self.cue_mode:
                self._toggle_cue_mode(False)
            if group in GROUPS:
                self._select_group(group)
                self._select_page(max(0, min(PAGE_COUNT - 1, int(page_index))))

        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        self._play_slot(slot_index, allow_fade=self.fade_on_sound_button_hotkey)

        if self.sound_button_hotkey_go_to_playing:
            self._go_to_current_playing_page()
            return

        if old_cue_mode:
            self._toggle_cue_mode(True)
        else:
            if self.cue_mode:
                self._toggle_cue_mode(False)
            self._select_group(old_group)
            self._select_page(old_page)

    def _sound_button_midi_hotkey_trigger(self, slot_key: Tuple[str, int, int]) -> None:
        self._sound_button_hotkey_trigger(slot_key)
        if self.midi_sound_button_hotkey_go_to_playing:
            self._go_to_current_playing_page()

    def _poll_midi_inputs(self) -> None:
        try:
            self._midi_router.poll()
        except Exception:
            pass

    def _cc_binding_matches(self, configured: str, source_selector: str, cc_token: str) -> bool:
        selector, token = split_midi_binding(configured)
        if not token or token != cc_token:
            return False
        if not selector:
            return True
        return selector == source_selector

    @staticmethod
    def _normalize_midi_relative_mode(mode: str) -> str:
        token = str(mode or "").strip().lower()
        if token in {"auto", "twos_complement", "sign_magnitude", "binary_offset"}:
            return token
        return "auto"

    @staticmethod
    def _midi_cc_relative_delta(value: int, mode: str = "auto") -> int:
        v = int(value) & 0x7F
        if v == 64:
            return 0
        mode_name = MainWindow._normalize_midi_relative_mode(mode)
        if mode_name == "binary_offset":
            return v - 64
        if mode_name == "sign_magnitude":
            if 1 <= v <= 63:
                return v
            if 65 <= v <= 127:
                return -(v - 64)
            return 0
        # twos_complement and auto fallback
        if 1 <= v <= 63:
            return v
        if 65 <= v <= 127:
            return v - 128
        return 0

    @staticmethod
    def _midi_pitch_relative_delta(data1: int, data2: int) -> int:
        # Many controllers encode relative pitch as 7-bit value in data2.
        if int(data1) == 0:
            return MainWindow._midi_cc_relative_delta(data2)
        # Fallback to signed delta around center for full 14-bit pitch bend.
        value14 = (int(data1) & 0x7F) | ((int(data2) & 0x7F) << 7)
        if value14 == 8192:
            return 0
        return 1 if value14 > 8192 else -1

    def _apply_midi_rotary(self, source_selector: str, status: int, data1: int, data2: int) -> bool:
        if not self.midi_rotary_enabled:
            return False
        status = int(status) & 0xFF
        data1 = int(data1) & 0xFF
        data2 = int(data2) & 0xFF
        high = status & 0xF0
        if high not in {0xB0, 0xE0}:
            return False
        source_token = ""
        if high == 0xB0:
            source_token = normalize_midi_binding(f"{status:02X}:{data1:02X}")
        elif high == 0xE0:
            source_token = normalize_midi_binding(f"{status:02X}")
        if not source_token:
            return False
        if self._cc_binding_matches(self.midi_rotary_group_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_group_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                nav_delta = raw_delta
                if self.midi_rotary_group_invert:
                    nav_delta = -nav_delta
                effective_delta = self._midi_rotary_apply_sensitivity("group", nav_delta, self.midi_rotary_group_sensitivity)
                if effective_delta == 0:
                    return True
                self._hotkey_select_group_delta(effective_delta)
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_page_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_page_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                nav_delta = raw_delta
                if self.midi_rotary_page_invert:
                    nav_delta = -nav_delta
                effective_delta = self._midi_rotary_apply_sensitivity("page", nav_delta, self.midi_rotary_page_sensitivity)
                if effective_delta == 0:
                    return True
                self._hotkey_select_page_delta(effective_delta)
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_sound_button_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_sound_button_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                nav_delta = raw_delta
                if self.midi_rotary_sound_button_invert:
                    nav_delta = -nav_delta
                effective_delta = self._midi_rotary_apply_sensitivity(
                    "sound_button",
                    nav_delta,
                    self.midi_rotary_sound_button_sensitivity,
                )
                if effective_delta == 0:
                    return True
                self._hotkey_select_sound_button_delta(effective_delta)
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_volume_binding, source_selector, source_token):
            if self.midi_rotary_volume_mode == "absolute":
                if high == 0xB0:
                    level = int(round((max(0, min(127, int(data2))) / 127.0) * 100.0))
                else:
                    value14 = (int(data1) & 0x7F) | ((int(data2) & 0x7F) << 7)
                    level = int(round((max(0, min(16383, value14)) / 16383.0) * 100.0))
                if self.midi_rotary_volume_invert:
                    level = 100 - level
                self.volume_slider.setValue(max(0, min(100, level)))
                return True
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_volume_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                if self.midi_rotary_volume_invert:
                    raw_delta = -raw_delta
                current = int(self.volume_slider.value())
                next_level = current + (int(self.midi_rotary_volume_step) * raw_delta)
                self.volume_slider.setValue(max(0, min(100, next_level)))
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_jog_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_jog_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                if self.midi_rotary_jog_invert:
                    raw_delta = -raw_delta
                current = int(self.seek_slider.value())
                total_ms = self._transport_total_ms()
                next_display = max(0, min(total_ms, current + (int(self.midi_rotary_jog_step_ms) * raw_delta)))
                absolute = self._transport_absolute_ms_for_display(next_display)
                self.player.setPosition(max(0, int(absolute)))
                self.seek_slider.setValue(next_display)
                return True
            return False
        return False

    def _midi_rotary_apply_sensitivity(self, key: str, raw_delta: int, sensitivity: int) -> int:
        delta = int(raw_delta)
        sens = max(1, int(sensitivity))
        if sens <= 1:
            return delta
        if not hasattr(self, "_midi_rotary_nav_accum"):
            self._midi_rotary_nav_accum = {}
        accum = int(self._midi_rotary_nav_accum.get(key, 0)) + delta
        out = 0
        while accum >= sens:
            out += 1
            accum -= sens
        while accum <= -sens:
            out -= 1
            accum += sens
        self._midi_rotary_nav_accum[key] = accum
        return out

    def _on_midi_binding_triggered(
        self,
        token: str,
        source_selector: str = "",
        status: int = 0,
        data1: int = 0,
        data2: int = 0,
    ) -> None:
        context_handler = self._midi_context_handler
        if context_handler is not None:
            try:
                if bool(context_handler.handle_midi_message(token, source_selector, status, data1, data2)):
                    return
            except Exception:
                pass
        if self._midi_context_block_actions:
            return
        if self._apply_midi_rotary(source_selector, status, data1, data2):
            return
        _selector, normalized_token = split_midi_binding(token)
        if not normalized_token:
            return
        key_from_source = (
            normalize_midi_binding(f"{source_selector}|{normalized_token}")
            if source_selector
            else normalized_token
        )
        # Prefer device-specific bindings, then fall back to generic bindings.
        handler = self._midi_action_handlers.get(key_from_source) or self._midi_action_handlers.get(normalized_token)
        if handler is None:
            return
        now = time.perf_counter()
        dedupe_key = key_from_source if key_from_source in self._midi_action_handlers else normalized_token
        last = self._midi_last_trigger_t.get(dedupe_key, 0.0)
        if (now - last) < 0.06:
            return
        self._midi_last_trigger_t[dedupe_key] = now
        handler()

    def _toggle_mute_hotkey(self) -> None:
        current = int(self.volume_slider.value())
        if current > 0:
            self._pre_mute_volume = current
            self.volume_slider.setValue(0)
            return
        restore = self._pre_mute_volume if self._pre_mute_volume is not None else 90
        self.volume_slider.setValue(max(0, min(100, int(restore))))

    def _adjust_volume_hotkey(self, delta: int) -> None:
        current = int(self.volume_slider.value())
        self.volume_slider.setValue(max(0, min(100, current + int(delta))))

    def _volume_up_hotkey(self) -> None:
        self._adjust_volume_hotkey(5)

    def _volume_down_hotkey(self) -> None:
        self._adjust_volume_hotkey(-5)

    def keyReleaseEvent(self, event) -> None:
        key = int(event.key())
        if key in self._modifier_hotkey_down:
            self._modifier_hotkey_down.discard(key)
            return
        super().keyReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self._is_playback_in_progress():
            answer = QMessageBox.warning(
                self,
                "Playback In Progress",
                "Playback is in progress. Quit anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Unsaved Changes",
                "This set has unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save:
                self._save_set()
                if self._dirty:
                    event.ignore()
                    return
        self._hard_stop_all()
        try:
            self._ltc_sender.shutdown()
        except Exception:
            pass
        try:
            self._mtc_sender.shutdown()
        except Exception:
            pass
        try:
            shutdown_audio_preload()
        except Exception:
            pass
        try:
            self._midi_poll_timer.stop()
        except Exception:
            pass
        try:
            self._midi_router.close()
        except Exception:
            pass
        try:
            if self._stage_display_window is not None:
                self._stage_display_window.close()
        except Exception:
            pass
        self._stop_web_remote_service()
        if not self._skip_save_on_close:
            self._save_settings()
        super().closeEvent(event)

    def _is_playback_in_progress(self) -> bool:
        if self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            return True
        if self.player_b.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            return True
        for extra in self._multi_players:
            if extra.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                return True
        return False


def format_time(ms: int) -> str:
    total_seconds = max(0, ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def format_clock_time(ms: int) -> str:
    # Display transport using timecode-style frames.
    fps = 30
    total_ms = max(0, ms)
    total_seconds, remainder_ms = divmod(total_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    frames = min(fps - 1, int((remainder_ms / 1000.0) * fps))
    return f"{minutes:02d}:{seconds:02d}:{frames:02d}"


def format_set_time(ms: int) -> str:
    total_seconds = max(0, ms // 1000)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def clean_set_value(value: str) -> str:
    return (value or "").replace("\r", " ").replace("\n", " ").strip()


def to_set_color_value(hex_color: Optional[str]) -> str:
    if not hex_color:
        return "clBtnFace"
    color = hex_color.strip()
    if len(color) != 7 or not color.startswith("#"):
        return "clBtnFace"
    try:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
    except ValueError:
        return "clBtnFace"
    return f"$00{blue:02X}{green:02X}{red:02X}"


def elide_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."
