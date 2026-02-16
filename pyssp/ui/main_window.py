from __future__ import annotations

import os
import time
import random
import configparser
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QEvent, QSize, QTimer, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAction,
    QColorDialog,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QInputDialog,
    QSlider,
    QStyle,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pyssp.audio_engine import ExternalMediaPlayer, list_output_devices, set_output_device
from pyssp.dsp import DSPConfig, normalize_config
from pyssp.set_loader import load_set_file, parse_delphi_color, parse_time_string_to_ms
from pyssp.settings_store import AppSettings, load_settings, save_settings
from pyssp.ui.dsp_window import DSPWindow
from pyssp.ui.edit_sound_button_dialog import EditSoundButtonDialog
from pyssp.ui.options_dialog import OptionsDialog
from pyssp.ui.search_window import SearchWindow

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
}


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
        return f"{elide_text(self.title, 26)}\n{format_time(self.duration_ms)}"


class SoundButton(QPushButton):
    def __init__(self, slot_index: int):
        super().__init__("")
        self.slot_index = slot_index
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(0, 0)
        self.setStyleSheet("font-size: 10pt; font-weight: bold;")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Sports Sounds Pro - pySSP")
        self.resize(1360, 900)
        self.settings: AppSettings = load_settings()

        self.current_group = "A"
        self.current_page = 0
        self.current_playing: Optional[Tuple[str, int, int]] = None
        self.current_playlist_start: Optional[int] = None
        self._auto_transition_track: Optional[Tuple[str, int, int]] = None
        self._auto_transition_done = False
        self._pending_start_request: Optional[Tuple[str, int, int]] = None
        self._pending_start_token = 0
        self.current_duration_ms = 0
        self.loop_enabled = False
        self._manual_stop_requested = False
        self.talk_active = False
        self._shift_down = False
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
        self.talk_volume_level = self.settings.talk_volume_level
        self.talk_fade_sec = self.settings.talk_fade_sec
        self.talk_blink_button = self.settings.talk_blink_button
        self.talk_shift_accelerator = self.settings.talk_shift_accelerator
        self.hotkeys_ignore_talk_level = self.settings.hotkeys_ignore_talk_level
        self.enter_key_mirrors_space = self.settings.enter_key_mirrors_space
        self.log_file_enabled = self.settings.log_file_enabled
        self.reset_all_on_startup = self.settings.reset_all_on_startup
        self.click_playing_action = self.settings.click_playing_action
        self.search_double_click_action = self.settings.search_double_click_action
        self.audio_output_device = self.settings.audio_output_device

        set_output_device(self.audio_output_device)
        self._init_audio_players()

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
        self.total_time = QLabel("00:00")
        self.elapsed_time = QLabel("00:00")
        self.remaining_time = QLabel("00:00")
        self.progress_label = QLabel("0%")
        self.left_meter = QProgressBar()
        self.right_meter = QProgressBar()
        self.seek_slider = QSlider(Qt.Horizontal)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.control_buttons: Dict[str, QPushButton] = {}
        self._is_scrubbing = False
        self._vu_levels = [0.0, 0.0]
        self._last_ui_position_ms = -1
        self._track_started_at = 0.0
        self._ignore_state_changes = 0
        self._dirty = False
        self._copied_page_buffer: Optional[dict] = None
        self._copied_slot_buffer: Optional[SoundButtonData] = None
        self._search_window: Optional[SearchWindow] = None
        self._dsp_window: Optional[DSPWindow] = None
        self._dsp_config: DSPConfig = DSPConfig()
        self._flash_slot_key: Optional[Tuple[str, int, int]] = None
        self._flash_slot_until = 0.0

        self._build_ui()
        self._update_talk_button_visual()
        self.volume_slider.setValue(self.settings.volume)
        self.player.setVolume(self.volume_slider.value())
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._update_now_playing_label("")
        self._refresh_window_title()

        self.meter_timer = QTimer(self)
        self.meter_timer.timeout.connect(self._tick_meter)
        self.meter_timer.start(60)

        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self._tick_fades)
        self.fade_timer.start(30)

        self.talk_blink_timer = QTimer(self)
        self.talk_blink_timer.timeout.connect(self._tick_talk_blink)
        self.talk_blink_timer.start(280)

        self.current_group = self.settings.last_group
        self.current_page = self.settings.last_page
        self.cue_mode = False
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._restore_last_set_on_startup()
        if self.reset_all_on_startup:
            self._reset_all_played_state()
            self._refresh_sound_grid()

    def _build_ui(self) -> None:
        self._build_menu_bar()

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        root_layout.addWidget(left_panel, 1)
        root_layout.addWidget(right_panel, 5)

    def _init_audio_players(self) -> None:
        self.player = ExternalMediaPlayer(self)
        self.player_b = ExternalMediaPlayer(self)
        self.player.setNotifyInterval(90)
        self.player_b.setNotifyInterval(90)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        new_set_action = QAction("New Set", self)
        new_set_action.setShortcut("Ctrl+N")
        new_set_action.triggered.connect(self._new_set)
        file_menu.addAction(new_set_action)

        open_set_action = QAction("Open Set", self)
        open_set_action.setShortcut("Ctrl+O")
        open_set_action.triggered.connect(self._open_set_dialog)
        file_menu.addAction(open_set_action)

        save_set_action = QAction("Save Set", self)
        save_set_action.setShortcut("Ctrl+S")
        save_set_action.triggered.connect(self._save_set)
        file_menu.addAction(save_set_action)

        save_set_at_action = QAction("Save Set At", self)
        save_set_at_action.setShortcut("Ctrl+Shift+S")
        save_set_at_action.triggered.connect(self._save_set_at)
        file_menu.addAction(save_set_at_action)

        setup_menu = self.menuBar().addMenu("Setup")
        options_action = QAction("Options", self)
        options_action.triggered.connect(self._open_options_dialog)
        setup_menu.addAction(options_action)
        search_action = QAction("Search", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self._open_find_dialog)
        self.addAction(search_action)

        tools_menu = self.menuBar().addMenu("Tools")
        tools_menu.addAction(QAction("Tools Item", self))

        log_menu = self.menuBar().addMenu("Logs")
        view_log_action = QAction("View Log", self)
        view_log_action.triggered.connect(self._view_log_file)
        log_menu.addAction(view_log_action)

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
            button = QPushButton(group)
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
                button = SoundButton(idx)
                button.clicked.connect(lambda _=False, slot=idx: self._play_slot(slot))
                button.setContextMenuPolicy(Qt.CustomContextMenu)
                button.customContextMenuRequested.connect(
                    lambda pos, slot=idx: self._show_slot_menu(slot, pos)
                )
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
            "Loop", "Next", "Button Drag", "Pause",
            "Rapid Fire", "Shuffle", "Reset Page", "STOP",
            "Talk", "Play List", "Search",
        ]
        positions = {
            "Cue": (0, 0, 1, 1),
            "Multi-Play": (0, 1, 1, 1),
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
            elif text == "Rapid Fire":
                btn.setCheckable(True)
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
            if text in {"Pause", "STOP", "Next", "Loop", "Reset Page", "Talk", "Cue", "Play List", "Shuffle", "Rapid Fire"}:
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

        transport_row = QHBoxLayout()
        transport_row.addWidget(QLabel("Jog"))
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.valueChanged.connect(self._on_seek_value_changed)
        transport_row.addWidget(self.seek_slider, 1)
        transport_row.addWidget(QLabel("Volume"))
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(90)
        self.volume_slider.setFixedWidth(140)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        transport_row.addWidget(self.volume_slider)
        right_layout.addLayout(transport_row)

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
        self.progress_label.setStyleSheet("font-size: 20pt; color: white; background: black;")
        right_layout.addWidget(self.progress_label)
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

    def _select_page(self, index: int) -> None:
        if index < 0:
            return
        if self.cue_mode:
            self.current_page = 0
            self._update_page_status()
            return
        self.current_page = index
        self.current_playlist_start = None
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_page_status()

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
            cue_item = QListWidgetItem("Cue Page")
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
                text = f"Page {self.current_group.lower()} {i + 1}"
            else:
                text = "(Blank Page)"
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
        if self.show_file_notifications:
            QMessageBox.information(self, "Page Exported", f"Exported page to:\n{file_path}")

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
            lines.append(f"activity{slot_index}={'2' if slot.played else '8'}")
            lines.append(f"co{slot_index}={to_set_color_value(slot.custom_color)}")
            if slot.copied_to_cue:
                lines.append(f"ci{slot_index}=Y")
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
        for i, button in enumerate(self.sound_buttons):
            slot = page[i]
            if slot.marker:
                button.setText(elide_text(slot.title, self.title_char_limit))
                button.setToolTip("")
            elif not slot.assigned:
                button.setText("")
                button.setToolTip("")
            else:
                button.setText(f"{elide_text(slot.title, self.title_char_limit)}\n{format_time(slot.duration_ms)}")
                button.setToolTip(slot.notes.strip())
            color = self._slot_color(slot, i)
            text_color = "white" if color in {COLORS["marker"], COLORS["missing"], COLORS["copied"]} else "black"
            button.setStyleSheet(
                "QPushButton{"
                f"background:{color};"
                f"color:{text_color};"
                "font-size:10pt;font-weight:bold;border:1px solid #94B8BA;"
                "padding:4px;"
                "}"
            )

    def _set_dirty(self, dirty: bool = True) -> None:
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self._refresh_window_title()

    def _refresh_window_title(self) -> None:
        base = "Python SSP"
        title = f"{base}    {self.current_set_path}" if self.current_set_path else base
        if self._dirty:
            title = f"{title} *"
        self.setWindowTitle(title)

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
            return COLORS["marker"]
        if slot.locked:
            return COLORS["locked"]
        if slot.missing:
            return COLORS["missing"]
        if self.current_playing == playing_key:
            return COLORS["playing"]
        if slot.played:
            return COLORS["played"]
        if slot.highlighted:
            return COLORS["highlighted"]
        if slot.copied_to_cue:
            return COLORS["copied"]
        if slot.assigned:
            if slot.custom_color:
                return slot.custom_color
            return COLORS["assigned"]
        return COLORS["empty"]

    def _show_slot_menu(self, slot_index: int, pos) -> None:
        button = self.sound_buttons[slot_index]
        page = self._current_page_slots()
        slot = page[slot_index]
        page_created = self._is_page_created(self.current_group, self.current_page)

        menu = QMenu(self)
        is_unused = (not slot.assigned) and (not slot.marker) and (not slot.title.strip()) and (not slot.notes.strip())

        if is_unused:
            add_action = menu.addAction("Add Sound Button")
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
            start_dir=start_dir,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        file_path, caption, notes = dialog.values()
        if not file_path:
            QMessageBox.information(self, "Edit Sound Button", "File is required.")
            return
        self.settings.last_sound_dir = os.path.dirname(file_path)
        self._save_settings()
        slot.file_path = file_path
        slot.title = caption or os.path.splitext(os.path.basename(file_path))[0]
        slot.notes = notes
        slot.marker = False
        slot.played = False
        slot.activity_code = "8"
        self._set_dirty(True)
        self._refresh_page_list()
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
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Sound File",
            start_dir,
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)",
        )
        if not file_path:
            return
        self.settings.last_sound_dir = os.path.dirname(file_path)
        self._save_settings()

        slot.file_path = file_path
        slot.title = os.path.splitext(os.path.basename(file_path))[0]
        slot.notes = ""
        slot.duration_ms = 0
        slot.custom_color = None
        slot.marker = False
        slot.played = False
        slot.activity_code = "8"
        self._set_dirty(True)
        self._refresh_page_list()
        self._refresh_sound_grid()

    def _verify_slot(self, slot: SoundButtonData) -> None:
        if slot.missing:
            QMessageBox.warning(self, "Missing File", f"File not found:\n{slot.file_path}")
        else:
            QMessageBox.information(self, "File Check", "Sound file exists.")

    def _play_slot(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            return
        if slot.marker:
            return
        if not slot.assigned:
            return
        if slot.missing:
            self._refresh_sound_grid()
            return

        group_key = self._view_group_key()
        playing_key = (group_key, self.current_page, slot_index)
        if self.current_playing == playing_key and self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            if self.click_playing_action == "stop_it":
                self._stop_playback()
                return
        # Invalidate any previously scheduled delayed start to avoid stale restarts.
        self._pending_start_request = None
        self._pending_start_token += 1
        old_player, new_player = self._select_transition_players()
        any_playing = old_player is not None
        mode = self._current_fade_mode()
        fade_in_on = mode in {"fade_in_only", "fade_out_then_fade_in"}
        fade_out_on = mode in {"fade_out_only", "fade_out_then_fade_in"}
        cross_mode = mode == "cross_fade"
        if (
            any_playing
            and fade_out_on
            and not cross_mode
        ):
            self._schedule_start_after_fadeout(group_key, self.current_page, slot_index)
            return

        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if playlist_enabled and self.current_playlist_start is None:
            self.current_playlist_start = slot_index
        slot.played = True
        slot.activity_code = "2"
        self._set_dirty(True)

        self.current_playing = playing_key
        self._auto_transition_track = self.current_playing
        self._auto_transition_done = False
        self._track_started_at = time.monotonic()
        # Clear stale timing from previous track so auto-transition cannot jump immediately.
        self.current_duration_ms = 0
        self._last_ui_position_ms = -1
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setValue(0)
        self.total_time.setText("00:00")
        self.elapsed_time.setText("00:00")
        self.remaining_time.setText("00:00")
        self.progress_label.setText("0%")
        self._manual_stop_requested = False
        target_volume = self._effective_master_volume()
        self._cancel_fade_for_player(self.player)
        self._cancel_fade_for_player(self.player_b)

        if cross_mode:
            self._stop_player_internal(new_player)
            if not self._try_load_media(new_player, slot):
                self.current_playing = None
                self._refresh_sound_grid()
                self._update_now_playing_label("")
                return
            new_player.setVolume(0)
            new_player.play()
            fade_seconds = self.cross_fade_sec
            self._start_fade(new_player, target_volume, fade_seconds, stop_on_complete=False)
            if old_player is not None:
                self._start_fade(old_player, 0, fade_seconds, stop_on_complete=True)
            # Keep the "primary" player bound to the newest track for UI updates.
            if self.player is not new_player:
                self._swap_primary_secondary_players()
        else:
            self._stop_player_internal(self.player_b)
            self._stop_player_internal(self.player)
            if not self._try_load_media(self.player, slot):
                self.current_playing = None
                self._refresh_sound_grid()
                self._update_now_playing_label("")
                return
            if fade_in_on:
                self.player.setVolume(0)
                self.player.play()
                self._start_fade(self.player, target_volume, self.fade_in_sec, stop_on_complete=False)
            else:
                self.player.setVolume(target_volume)
                self.player.play()

        self._refresh_sound_grid()
        self._update_now_playing_label(self._build_now_playing_text(slot))
        self._append_play_log(slot.file_path)

    def _try_load_media(self, player: ExternalMediaPlayer, slot: SoundButtonData) -> bool:
        try:
            player.setMedia(slot.file_path, dsp_config=self._dsp_config)
            return True
        except Exception as exc:
            self._stop_player_internal(player)
            title = slot.title.strip() or os.path.basename(slot.file_path) or "(unknown)"
            QMessageBox.warning(
                self,
                "Audio Load Failed",
                f"Could not play '{title}'.\n\nReason: {exc}",
            )
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
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._play_slot(slot_index)

    def _on_position_changed(self, pos: int) -> None:
        if not self._is_scrubbing:
            self.seek_slider.setValue(pos)
        if self._last_ui_position_ms >= 0 and abs(pos - self._last_ui_position_ms) < 90:
            return
        self._last_ui_position_ms = pos
        self.elapsed_time.setText(format_time(pos))
        remaining = max(0, self.current_duration_ms - pos)
        self.remaining_time.setText(format_time(remaining))
        progress = 0 if self.current_duration_ms == 0 else int((pos / self.current_duration_ms) * 100)
        self.progress_label.setText(f"{progress}%")

    def _on_duration_changed(self, duration: int) -> None:
        self.current_duration_ms = duration
        self._last_ui_position_ms = -1
        self.seek_slider.setRange(0, duration)
        self.total_time.setText(format_time(duration))
        if self.current_playing:
            group, page_index, slot_index = self.current_playing
            if group == "Q":
                if 0 <= slot_index < len(self.cue_page):
                    self.cue_page[slot_index].duration_ms = duration
            elif group in self.data and 0 <= page_index < PAGE_COUNT and 0 <= slot_index < SLOTS_PER_PAGE:
                self.data[group][page_index][slot_index].duration_ms = duration
            self._refresh_sound_grid()

    def _on_state_changed(self, _state: int) -> None:
        self._update_pause_button_label()
        if self._ignore_state_changes > 0:
            return
        if self.player.state() == ExternalMediaPlayer.StoppedState:
            last_playing = self.current_playing
            playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
            rapid_fire = bool(self.control_buttons.get("Rapid Fire") and self.control_buttons["Rapid Fire"].isChecked())
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
                self.elapsed_time.setText("00:00")
                self.remaining_time.setText("00:00")
                self.progress_label.setText("0%")
                self.seek_slider.setValue(0)
                self._update_now_playing_label("")
                self._refresh_sound_grid()
                return
            if playlist_enabled and last_playing is not None:
                if manual_stop:
                    self.current_playing = None
                    self._last_ui_position_ms = -1
                    self.elapsed_time.setText("00:00")
                    self.remaining_time.setText("00:00")
                    self.progress_label.setText("0%")
                    self.seek_slider.setValue(0)
                    self._update_now_playing_label("")
                    self._refresh_sound_grid()
                    return
                if rapid_fire:
                    self.current_playing = None
                    self._last_ui_position_ms = -1
                    self.elapsed_time.setText("00:00")
                    self.remaining_time.setText("00:00")
                    self.progress_label.setText("0%")
                    self.seek_slider.setValue(0)
                    self._update_now_playing_label("")
                    self._refresh_sound_grid()
                    return
                next_slot = self._next_playlist_slot()
                if next_slot is not None:
                    self._play_slot(next_slot)
                    return
            self.current_playing = None
            self._auto_transition_track = None
            self._auto_transition_done = False
            self._last_ui_position_ms = -1
            self.elapsed_time.setText("00:00")
            self.remaining_time.setText("00:00")
            self.progress_label.setText("0%")
            self._refresh_sound_grid()
            self.seek_slider.setValue(0)
            self._update_now_playing_label("")

    def _stop_player_internal(self, player: ExternalMediaPlayer) -> None:
        self._ignore_state_changes += 1
        try:
            player.stop()
        finally:
            self._ignore_state_changes = max(0, self._ignore_state_changes - 1)

    def _tick_meter(self) -> None:
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
        target_left = min(1.0, max(0.0, left_a + left_b))
        target_right = min(1.0, max(0.0, right_a + right_b))
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
        self.left_meter.setValue(int(max(0.0, min(100.0, self._vu_levels[0]))))
        self.right_meter.setValue(int(max(0.0, min(100.0, self._vu_levels[1]))))

    def _update_group_status(self) -> None:
        if self.cue_mode:
            self.group_status.setText("Group - Cue")
        else:
            self.group_status.setText(f"Group - {self.current_group}")

    def _update_page_status(self) -> None:
        if self.cue_mode:
            self.page_status.setText("Page - Cue")
            return
        page_name = self.page_names[self.current_group][self.current_page].strip()
        if page_name:
            self.page_status.setText(f"Page - {page_name}")
        else:
            self.page_status.setText(f"Page - {self.current_page + 1}")

    def _update_now_playing_label(self, text: str) -> None:
        if text:
            self.now_playing_label.setText(f"NOW PLAYING: {text}")
        else:
            self.now_playing_label.setText("NOW PLAYING:")

    def _build_now_playing_text(self, slot: SoundButtonData) -> str:
        title = slot.title.strip()
        if title:
            return title
        base_name = os.path.basename(slot.file_path)
        return os.path.splitext(base_name)[0]

    def _view_group_key(self) -> str:
        return "Q" if self.cue_mode else self.current_group

    def _current_page_slots(self) -> List[SoundButtonData]:
        if self.cue_mode:
            return self.cue_page
        return self.data[self.current_group][self.current_page]

    def _sync_playlist_shuffle_buttons(self) -> None:
        if self.cue_mode:
            playlist_enabled = False
            shuffle_enabled = False
        else:
            playlist_enabled = self.page_playlist_enabled[self.current_group][self.current_page]
            shuffle_enabled = self.page_shuffle_enabled[self.current_group][self.current_page]
        play_btn = self.control_buttons.get("Play List")
        shuf_btn = self.control_buttons.get("Shuffle")
        next_btn = self.control_buttons.get("Next")
        if play_btn:
            play_btn.setChecked(playlist_enabled)
        if shuf_btn:
            shuf_btn.setEnabled(playlist_enabled)
            shuf_btn.setChecked(shuffle_enabled)
        self._update_next_button_enabled()

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
        has_next = self._next_unplayed_slot_on_current_page() is not None
        next_btn.setEnabled(is_playing and has_next)

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
            base = int(base * (self.talk_volume_level / 100.0))
        return max(0, min(100, base))

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
        if not self._is_cross_fade_enabled():
            return
        if self.cue_mode:
            return
        if not self.current_playing:
            return
        if not self.page_playlist_enabled[self.current_group][self.current_page]:
            return
        rapid_fire = bool(self.control_buttons.get("Rapid Fire") and self.control_buttons["Rapid Fire"].isChecked())
        if rapid_fire:
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
                next_slot = self._next_playlist_slot()
                if next_slot is not None:
                    self._auto_transition_done = True
                    self._play_slot(next_slot)
            return

    def _swap_primary_secondary_players(self) -> None:
        try:
            self.player.positionChanged.disconnect(self._on_position_changed)
            self.player.durationChanged.disconnect(self._on_duration_changed)
            self.player.stateChanged.disconnect(self._on_state_changed)
        except TypeError:
            pass
        self.player, self.player_b = self.player_b, self.player
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)

    def _open_options_dialog(self) -> None:
        available_devices = sorted(list_output_devices(), key=lambda v: v.lower())
        dialog = OptionsDialog(
            active_group_color=self.active_group_color,
            inactive_group_color=self.inactive_group_color,
            title_char_limit=self.title_char_limit,
            show_file_notifications=self.show_file_notifications,
            fade_in_sec=self.fade_in_sec,
            cross_fade_sec=self.cross_fade_sec,
            fade_out_sec=self.fade_out_sec,
            talk_volume_level=self.talk_volume_level,
            talk_fade_sec=self.talk_fade_sec,
            talk_blink_button=self.talk_blink_button,
            talk_shift_accelerator=self.talk_shift_accelerator,
            hotkeys_ignore_talk_level=self.hotkeys_ignore_talk_level,
            enter_key_mirrors_space=self.enter_key_mirrors_space,
            log_file_enabled=self.log_file_enabled,
            reset_all_on_startup=self.reset_all_on_startup,
            click_playing_action=self.click_playing_action,
            search_double_click_action=self.search_double_click_action,
            audio_output_device=self.audio_output_device,
            available_audio_devices=available_devices,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        self.active_group_color = dialog.active_group_color
        self.inactive_group_color = dialog.inactive_group_color
        self.title_char_limit = dialog.title_limit_spin.value()
        self.show_file_notifications = dialog.notifications_checkbox.isChecked()
        self.fade_in_sec = dialog.fade_in_spin.value()
        self.cross_fade_sec = dialog.cross_fade_spin.value()
        self.fade_out_sec = dialog.fade_out_spin.value()
        self.talk_volume_level = dialog.talk_volume_spin.value()
        self.talk_fade_sec = dialog.talk_fade_spin.value()
        self.talk_blink_button = dialog.talk_blink_checkbox.isChecked()
        self.talk_shift_accelerator = dialog.shift_accel_checkbox.isChecked()
        self.hotkeys_ignore_talk_level = dialog.hotkeys_ignore_checkbox.isChecked()
        self.enter_key_mirrors_space = dialog.enter_mirror_checkbox.isChecked()
        self.log_file_enabled = dialog.log_file_checkbox.isChecked()
        self.reset_all_on_startup = dialog.reset_on_startup_checkbox.isChecked()
        self.click_playing_action = dialog.selected_click_playing_action()
        self.search_double_click_action = dialog.selected_search_double_click_action()
        if self._search_window is not None:
            self._search_window.set_double_click_action(self.search_double_click_action)
        selected_device = dialog.selected_audio_output_device()
        if selected_device != self.audio_output_device:
            if self._switch_audio_device(selected_device):
                self.audio_output_device = selected_device
        self._apply_talk_state_volume(fade=True)
        self._update_talk_button_visual()
        self._refresh_group_buttons()
        self._refresh_sound_grid()
        self._save_settings()

    def _toggle_pause(self) -> None:
        if self.player.state() == ExternalMediaPlayer.PlayingState:
            self.player.pause()
        elif self.player.state() == ExternalMediaPlayer.PausedState:
            self.player.play()
        self._update_pause_button_label()

    def _toggle_talk(self, checked: bool) -> None:
        self.talk_active = checked
        self._apply_talk_state_volume(fade=True)
        self._update_talk_button_visual()

    def _toggle_cue_mode(self, checked: bool) -> None:
        self.cue_mode = checked
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
            self._search_window = SearchWindow(self)
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
            self._dsp_window = DSPWindow(self)
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
        if flash:
            self._flash_slot_key = (self._view_group_key(), self.current_page, slot)
            self._flash_slot_until = time.monotonic() + 1.0
            self._refresh_sound_grid()
        if play:
            self._play_slot(slot)

    def _toggle_cross_auto_mode(self, checked: bool) -> None:
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
        target = self._effective_master_volume()
        fade_seconds = self.talk_fade_sec if fade else 0.0
        for player in (self.player, self.player_b):
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                self._start_fade(player, target, fade_seconds, stop_on_complete=False)

    def _switch_audio_device(self, device_name: str) -> bool:
        self._hard_stop_all()
        old_player = self.player
        old_player_b = self.player_b
        if not set_output_device(device_name):
            QMessageBox.warning(self, "Audio Device", "Could not switch to selected audio device.")
            return False
        try:
            old_player.deleteLater()
            old_player_b.deleteLater()
        except Exception:
            pass
        self._init_audio_players()
        self.player.setVolume(self._effective_master_volume())
        self.player_b.setVolume(self._effective_master_volume())
        self.current_playing = None
        self.current_duration_ms = 0
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setValue(0)
        self.total_time.setText("00:00")
        self.elapsed_time.setText("00:00")
        self.remaining_time.setText("00:00")
        self.progress_label.setText("0%")
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
            talk_button.setText("Talk")
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
        talk_button.setText("Talk*")

    def _stop_playback(self) -> None:
        self._manual_stop_requested = True
        self._pending_start_request = None
        self._pending_start_token += 1
        self._auto_transition_done = True
        if self._stop_fade_armed:
            self._stop_fade_armed = False
            self._hard_stop_all()
            self.current_playing = None
            self.current_playlist_start = None
            self.current_duration_ms = 0
            self._last_ui_position_ms = -1
            self.total_time.setText("00:00")
            self.elapsed_time.setText("00:00")
            self.remaining_time.setText("00:00")
            self.progress_label.setText("0%")
            self.seek_slider.setValue(0)
            self._vu_levels = [0.0, 0.0]
            self._refresh_sound_grid()
            self._update_now_playing_label("")
            return
        if self._is_fade_out_enabled() and self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            self._stop_fade_armed = True
            self._start_fade(self.player, 0, self.fade_out_sec, stop_on_complete=True)
            if self.player_b.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                self._start_fade(self.player_b, 0, self.fade_out_sec, stop_on_complete=True)
            return
        self._stop_fade_armed = False
        self.player.stop()
        self.player_b.stop()
        self.current_playing = None
        self.current_playlist_start = None
        self.current_duration_ms = 0
        self._last_ui_position_ms = -1
        self.total_time.setText("00:00")
        self.elapsed_time.setText("00:00")
        self.remaining_time.setText("00:00")
        self.progress_label.setText("0%")
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
        self.player.stop()
        self.player_b.stop()

    def _play_next(self) -> None:
        next_slot = self._next_unplayed_slot_on_current_page()
        if next_slot is None:
            self._update_next_button_enabled()
            return
        self._play_slot(next_slot)

    def _next_unplayed_slot_on_current_page(self) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        start_slot = -1
        current_key = self._view_group_key()
        if self.current_playing and self.current_playing[0] == current_key and self.current_playing[1] == self.current_page:
            start_slot = self.current_playing[2]
        for idx in range(start_slot + 1, SLOTS_PER_PAGE):
            slot = page[idx]
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and not slot.played:
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

    def _next_playlist_slot(self) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        if self.page_shuffle_enabled[self.current_group][self.current_page]:
            candidates = [
                idx
                for idx, slot in enumerate(page)
                if slot.assigned and not slot.marker and not slot.locked and not slot.missing and not slot.played
            ]
            if not candidates:
                if self.loop_enabled:
                    for slot in page:
                        slot.played = False
                        if slot.assigned:
                            slot.activity_code = "8"
                    self._set_dirty(True)
                    candidates = [
                        idx
                        for idx, slot in enumerate(page)
                        if slot.assigned and not slot.marker and not slot.locked and not slot.missing
                    ]
                else:
                    return None
            if not candidates:
                return None
            return random.choice(candidates)

        start = 0
        if self.current_playlist_start is not None:
            start = self.current_playlist_start
        if self.current_playing and self.current_playing[0] == self._view_group_key():
            start = self.current_playing[2] + 1

        for idx in range(start, SLOTS_PER_PAGE):
            slot = page[idx]
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and not slot.played:
                return idx
        if self.loop_enabled:
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
        if self.player.state() == ExternalMediaPlayer.PausedState:
            pause_button.setText("Resume")
            pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            pause_button.setText("Pause")
            pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def _on_seek_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_seek_released(self) -> None:
        self.player.setPosition(self.seek_slider.value())
        self._is_scrubbing = False

    def _on_seek_value_changed(self, value: int) -> None:
        if self._is_scrubbing:
            self.elapsed_time.setText(format_time(value))
            remaining = max(0, self.current_duration_ms - value)
            self.remaining_time.setText(format_time(remaining))
            progress = 0 if self.current_duration_ms == 0 else int((value / self.current_duration_ms) * 100)
            self.progress_label.setText(f"{progress}%")

    def _on_volume_changed(self, value: int) -> None:
        target = self._effective_master_volume()
        self.player.setVolume(target)
        self.player_b.setVolume(target)
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
        self.total_time.setText("00:00")
        self.elapsed_time.setText("00:00")
        self.remaining_time.setText("00:00")
        self.progress_label.setText("0%")
        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
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
                        lines.append(f"activity{slot_index}={'2' if slot.played else '8'}")
                        lines.append(f"co{slot_index}={to_set_color_value(slot.custom_color)}")
                        if slot.copied_to_cue:
                            lines.append(f"ci{slot_index}=Y")
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
            with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
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
        if self.show_file_notifications:
            QMessageBox.information(self, "Set Saved", f"Saved set file:\n{file_path}")

    def _load_set(self, file_path: str, show_message: bool = True, restore_last_position: bool = False) -> None:
        try:
            result = load_set_file(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Open Set Failed", f"Could not load set file:\n{exc}")
            return

        self._hard_stop_all()
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
        self.total_time.setText("00:00")
        self.elapsed_time.setText("00:00")
        self.remaining_time.setText("00:00")
        self.progress_label.setText("0%")
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
        self._set_dirty(False)
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
        self.settings.talk_volume_level = self.talk_volume_level
        self.settings.talk_fade_sec = self.talk_fade_sec
        self.settings.talk_blink_button = self.talk_blink_button
        self.settings.talk_shift_accelerator = self.talk_shift_accelerator
        self.settings.hotkeys_ignore_talk_level = self.hotkeys_ignore_talk_level
        self.settings.enter_key_mirrors_space = self.enter_key_mirrors_space
        self.settings.log_file_enabled = self.log_file_enabled
        self.settings.reset_all_on_startup = self.reset_all_on_startup
        self.settings.click_playing_action = self.click_playing_action
        self.settings.search_double_click_action = self.search_double_click_action
        self.settings.audio_output_device = self.audio_output_device
        save_settings(self.settings)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_page_list_item_heights()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.page_list.viewport() and event.type() == QEvent.Resize:
            self._update_page_list_item_heights()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_P and not event.isAutoRepeat():
            self._toggle_pause()
            return
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._handle_space_bar_action()
            return
        if self.enter_key_mirrors_space and not event.isAutoRepeat():
            if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
                self._handle_space_bar_action()
                return
        if event.key() == Qt.Key_Shift and self.talk_shift_accelerator and not event.isAutoRepeat():
            if not self._shift_down:
                self._shift_down = True
                talk_btn = self.control_buttons.get("Talk")
                if talk_btn:
                    talk_btn.click()
                else:
                    self._toggle_talk(not self.talk_active)
                return
        super().keyPressEvent(event)

    def _handle_space_bar_action(self) -> None:
        rapid_fire = bool(self.control_buttons.get("Rapid Fire") and self.control_buttons["Rapid Fire"].isChecked())
        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if rapid_fire and playlist_enabled:
            if self.player.state() == ExternalMediaPlayer.PlayingState:
                self.player.stop()
            else:
                next_slot = self._next_playlist_slot()
                if next_slot is not None:
                    self._play_slot(next_slot)
            return
        self._stop_playback()
        return

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key_Shift and not event.isAutoRepeat():
            self._shift_down = False
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
        self._save_settings()
        super().closeEvent(event)

    def _is_playback_in_progress(self) -> bool:
        return self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        } or self.player_b.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }


def format_time(ms: int) -> str:
    total_seconds = max(0, ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


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
