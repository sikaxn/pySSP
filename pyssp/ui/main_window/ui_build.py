from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *

DOCK_LAYOUT_STATE_VERSION = 4
SOUND_BUTTON_GRID_MIN_WIDTH = 88
SOUND_BUTTON_GRID_TARGET_WIDTH = 132
SOUND_BUTTON_LIST_MIN_WIDTHS: Dict[str, int] = {
    "ram": 12,
    "index": 40,
    "title": 120,
    "notes": 96,
    "status": 110,
    "edit": 56,
    "cue": 48,
    "lyric": 56,
    "automation": 72,
    "script": 56,
    "timecode": 72,
}


class UiBuildMixin:
    def _build_ui(self) -> None:
        self._build_menu_bar()
        self.installEventFilter(self)
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.AllowNestedDocks
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AnimatedDocks
            | QMainWindow.GroupedDragging
        )
        self._build_dock_canvas()
        self._apply_dock_drag_feedback_style()

        self.group_dock = self._create_panel_dock("Group", "group_widget_dock", self._build_group_widget())
        self.page_dock = self._create_panel_dock("Pages", "page_widget_dock", self._build_page_widget())
        self.sound_buttons_dock = self._create_panel_dock(
            "Sound Buttons",
            "sound_button_widget_dock",
            self._build_sound_button_widget(),
        )
        self.status_display_dock = self._create_panel_dock(
            "Status Display",
            "status_display_widget_dock",
            self._build_status_display_widget(),
        )
        self.main_button_dock = self._create_panel_dock(
            "Main Buttons",
            "main_button_widget_dock",
            self._build_main_button_widget(),
        )
        self.fade_button_dock = self._create_panel_dock(
            "Fade Buttons",
            "fade_button_widget_dock",
            self._build_fade_button_widget(),
        )
        self.meter_volume_dock = self._create_panel_dock(
            "VU Meter and Volume",
            "vu_meter_volume_widget_dock",
            self._build_meter_volume_widget(),
        )
        self.time_transport_dock = self._create_panel_dock(
            "Time and Transport",
            "time_transport_widget_dock",
            self._build_time_transport_widget(),
        )

        self._build_auxiliary_tool_docks()
        self._build_saved_divider_docks()
        self._build_timecode_dock()
        self._build_video_control_dock()
        self._apply_top_control_layout()
        if not self._restore_saved_dock_layout():
            self._apply_default_dock_layout()
        self._build_window_menu()
        self._sync_window_layout_lock_ui()

    def _build_dock_canvas(self) -> None:
        canvas = QWidget(self)
        canvas.setObjectName("dock_canvas")
        canvas.setContextMenuPolicy(Qt.CustomContextMenu)
        canvas.customContextMenuRequested.connect(self._show_canvas_context_menu)
        self.setCentralWidget(canvas)
        canvas.hide()
        self._dock_canvas = canvas

    def _apply_dock_drag_feedback_style(self) -> None:
        style = (
            "QRubberBand{"
            "border:2px solid #2E8BFF;"
            "background:rgba(46,139,255,0.18);"
            "}"
            "QMainWindow::separator{"
            "background:rgba(46,139,255,0.10);"
            "width:6px;"
            "height:6px;"
            "}"
            "QMainWindow::separator:hover{"
            "background:rgba(46,139,255,0.30);"
            "}"
        )
        current = str(self.styleSheet() or "").strip()
        if style not in current:
            self.setStyleSheet(f"{current}\n{style}".strip())

    def _configure_banner_label(self, label: QLabel, stylesheet: str) -> None:
        label.setVisible(False)
        label.setWordWrap(True)
        label.setStyleSheet(stylesheet)

    def _build_sound_button_legend_widget(self) -> QWidget:
        self.button_legend_label = QWidget()
        self.button_legend_label.setContentsMargins(0, 0, 0, 0)
        self.button_legend_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._button_legend_layout = QVBoxLayout(self.button_legend_label)
        self._button_legend_layout.setContentsMargins(2, 0, 2, 0)
        self._button_legend_layout.setSpacing(2)
        self._refresh_button_legend_label()
        self.button_legend_label.setVisible(bool(self.show_colour_legend))
        return self.button_legend_label

    def _build_main_warning_banner_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._configure_banner_label(
            self.drag_mode_banner,
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.drag_mode_banner)
        self._configure_banner_label(
            self.timecode_multiplay_banner,
            "QLabel{background:#FDE7E9; color:#7A0010; border:1px solid #B00020; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.timecode_multiplay_banner)
        self._configure_banner_label(
            self.web_remote_warning_banner,
            "QLabel{background:#FDE7E9; color:#7A0010; border:1px solid #B00020; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.web_remote_warning_banner)
        self._configure_banner_label(
            self.midi_connection_warning_banner,
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.midi_connection_warning_banner)
        self._configure_banner_label(
            self.vocal_removed_warning_banner,
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.vocal_removed_warning_banner)
        self._configure_banner_label(
            self.playback_warning_banner,
            "QLabel{background:#EFE3FA; color:#3F205E; border:1px solid #7B3FB3; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.playback_warning_banner)
        self._configure_banner_label(
            self.save_notice_banner,
            "QLabel{background:#E4F7E7; color:#165A20; border:1px solid #2E9B47; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.save_notice_banner)
        self._configure_banner_label(
            self.info_notice_banner,
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; padding:6px; font-weight:bold;}",
        )
        layout.addWidget(self.info_notice_banner)
        return panel

    def _create_panel_dock(self, title: str, object_name: str, widget: QWidget, *, fixed: bool = False) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(object_name)
        dock.setAllowedAreas(Qt.TopDockWidgetArea if fixed else Qt.AllDockWidgetAreas)
        if fixed:
            dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        else:
            dock.setFeatures(self._dock_features_for(dock))
        dock.setWidget(widget)
        if not fixed:
            dock.setContextMenuPolicy(Qt.CustomContextMenu)
            dock.customContextMenuRequested.connect(lambda pos, target=dock: self._show_dock_context_menu(target, pos))
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(
                lambda pos, target=dock, source=widget: self._show_dock_context_menu(target, pos, source_widget=source)
            )
            dock.dockLocationChanged.connect(lambda _area, target=dock: self._handle_dock_runtime_layout_change())
            dock.topLevelChanged.connect(
                lambda floating, target=dock: self._handle_dock_top_level_changed(target, bool(floating))
            )
            dock.visibilityChanged.connect(lambda _visible, target=dock: self._handle_dock_runtime_layout_change())
        return dock

    def _build_window_menu(self) -> None:
        if self._window_menu is None:
            self._window_menu = self.menuBar().addMenu("Window")
        else:
            self._window_menu.clear()

        restore_default_action = QAction("Restore Default Layout", self)
        restore_default_action.triggered.connect(self._restore_default_dock_layout)
        self._window_menu.addAction(restore_default_action)
        self._window_menu.addSeparator()

        self._sound_button_view_grid_action = QAction("Sound Buttons Grid View", self)
        self._sound_button_view_grid_action.setCheckable(True)
        self._sound_button_view_grid_action.triggered.connect(
            lambda checked=False: self._set_sound_button_view_mode("grid") if checked else None
        )
        self._window_menu.addAction(self._sound_button_view_grid_action)

        self._sound_button_view_list_action = QAction("Sound Buttons List View", self)
        self._sound_button_view_list_action.setCheckable(True)
        self._sound_button_view_list_action.triggered.connect(
            lambda checked=False: self._set_sound_button_view_mode("list") if checked else None
        )
        self._window_menu.addAction(self._sound_button_view_list_action)
        self._window_menu.addSeparator()

        self._remove_blank_space_action = QAction("Remove Blank Space", self)
        self._remove_blank_space_action.triggered.connect(self._remove_blank_dock_space)
        self._window_menu.addAction(self._remove_blank_space_action)

        self._add_horizontal_divider_action = QAction("Add Horizontal Divider", self)
        self._add_horizontal_divider_action.triggered.connect(
            lambda _=False: self._create_global_divider(Qt.Vertical)
        )
        self._window_menu.addAction(self._add_horizontal_divider_action)

        self._add_vertical_divider_action = QAction("Add Vertical Divider", self)
        self._add_vertical_divider_action.triggered.connect(
            lambda _=False: self._create_global_divider(Qt.Horizontal)
        )
        self._window_menu.addAction(self._add_vertical_divider_action)

        self._clear_all_standalone_action = QAction("Clear All Standalone Mode", self)
        self._clear_all_standalone_action.triggered.connect(self._clear_all_standalone_modes)
        self._window_menu.addAction(self._clear_all_standalone_action)

        self._layout_lock_action = QAction("Lock Window Layout", self)
        self._layout_lock_action.setCheckable(True)
        self._layout_lock_action.triggered.connect(self._toggle_window_layout_lock)
        self._window_menu.addAction(self._layout_lock_action)
        self._window_menu.addSeparator()

        for dock in self._window_menu_docks():
            if dock is None:
                continue
            action = dock.toggleViewAction()
            action.setText(dock.windowTitle())
            self._window_menu.addAction(action)
        self._sync_sound_button_view_mode_actions()
        self._sync_window_layout_lock_ui()

    def _sync_sound_button_view_mode_actions(self) -> None:
        mode = str(getattr(self, "sound_button_view_mode", "grid") or "grid").strip().lower()
        if mode not in {"grid", "list"}:
            mode = "grid"
        grid_action = getattr(self, "_sound_button_view_grid_action", None)
        list_action = getattr(self, "_sound_button_view_list_action", None)
        if grid_action is not None:
            grid_action.blockSignals(True)
            grid_action.setChecked(mode == "grid")
            grid_action.blockSignals(False)
        if list_action is not None:
            list_action.blockSignals(True)
            list_action.setChecked(mode == "list")
            list_action.blockSignals(False)

    def _set_sound_button_view_mode(self, mode: str, *, persist: bool = True) -> None:
        normalized = str(mode or "").strip().lower()
        if normalized not in {"grid", "list"}:
            normalized = "grid"
        if str(getattr(self, "sound_button_view_mode", "grid") or "grid").strip().lower() == normalized:
            self._sync_sound_button_view_mode_actions()
            return
        self.sound_button_view_mode = normalized
        rebuild_panel = getattr(self, "_rebuild_sound_button_panel", None)
        if callable(rebuild_panel):
            rebuild_panel()
        reveal_priority_slot = getattr(self, "_reveal_current_page_priority_slot", None)
        if callable(reveal_priority_slot):
            reveal_priority_slot()
        self._sync_sound_button_view_mode_actions()
        if persist:
            self._save_settings()

    def _park_hidden_dock(self, dock: Optional[QDockWidget]) -> None:
        if dock is None:
            return
        try:
            if not dock.isFloating():
                dock.setFloating(True)
        except Exception:
            pass
        dock.hide()

    def _window_menu_docks(self) -> List[QDockWidget]:
        docks = [
            self.group_dock,
            self.page_dock,
            self.sound_buttons_dock,
            self.status_display_dock,
            self.main_button_dock,
            self.fade_button_dock,
            self.meter_volume_dock,
            self.time_transport_dock,
            self.lyric_navigator_dock,
            self.automation_script_navigator_dock,
            self.available_commands_dock,
            self.timecode_dock,
            self.video_control_dock,
        ]
        docks.extend(self._divider_docks.get(name) for name in self.dock_dividers)
        return [dock for dock in docks if dock is not None]

    def _is_standalone_dock(self, dock: Optional[QDockWidget]) -> bool:
        if dock is None:
            return False
        return str(dock.objectName() or "").strip() in set(self.standalone_docks)

    def _show_dock_context_menu(
        self,
        dock: QDockWidget,
        pos,
        *,
        source_widget: Optional[QWidget] = None,
    ) -> None:
        if bool(getattr(self, "window_layout_locked", False)):
            return
        host = source_widget if source_widget is not None else dock
        menu = QMenu(host)
        standalone_action = QAction("Standalone Mode", menu)
        standalone_action.setCheckable(True)
        standalone_action.setChecked(self._is_standalone_dock(dock))
        standalone_action.triggered.connect(
            lambda checked=False, target=dock: self._set_dock_standalone_mode(target, bool(checked))
        )
        menu.addAction(standalone_action)
        menu.addSeparator()
        horizontal_divider_action = QAction("Create Horizontal Divider", menu)
        horizontal_divider_action.triggered.connect(
            lambda _=False, target=dock: self._create_divider_from_dock(target, Qt.Vertical)
        )
        menu.addAction(horizontal_divider_action)
        vertical_divider_action = QAction("Create Vertical Divider", menu)
        vertical_divider_action.triggered.connect(
            lambda _=False, target=dock: self._create_divider_from_dock(target, Qt.Horizontal)
        )
        menu.addAction(vertical_divider_action)
        menu.addSeparator()
        restore_default_action = QAction("Restore Default Layout", menu)
        restore_default_action.triggered.connect(self._restore_default_dock_layout)
        menu.addAction(restore_default_action)
        menu.exec_(host.mapToGlobal(pos))

    def _show_canvas_context_menu(self, pos) -> None:
        if self._dock_canvas is None or bool(getattr(self, "window_layout_locked", False)):
            return
        menu = QMenu(self._dock_canvas)
        horizontal_divider_action = QAction("Create Horizontal Divider", menu)
        horizontal_divider_action.triggered.connect(lambda _=False: self._create_global_divider(Qt.Vertical))
        menu.addAction(horizontal_divider_action)
        vertical_divider_action = QAction("Create Vertical Divider", menu)
        vertical_divider_action.triggered.connect(lambda _=False: self._create_global_divider(Qt.Horizontal))
        menu.addAction(vertical_divider_action)
        menu.addSeparator()
        remove_blank_space_action = QAction("Remove Blank Space", menu)
        remove_blank_space_action.triggered.connect(self._remove_blank_dock_space)
        menu.addAction(remove_blank_space_action)
        menu.exec_(self._dock_canvas.mapToGlobal(pos))

    def _build_saved_divider_docks(self) -> None:
        for name in list(self.dock_dividers):
            self._ensure_divider_dock(name)

    def _build_auxiliary_tool_docks(self) -> None:
        self._lyric_navigator_window = LyricNavigatorWindow(
            on_seek_to_ms=self._seek_to_lyric_timestamp,
            language=self.ui_language,
            parent=self,
        )
        self.lyric_navigator_dock = self._create_panel_dock(
            "Lyric Navigator",
            "lyric_navigator_widget_dock",
            self._lyric_navigator_window,
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.lyric_navigator_dock)
        self._park_hidden_dock(self.lyric_navigator_dock)

        self._automation_script_navigator_window = AutomationScriptNavigatorWindow(
            on_seek_to_ms=self._seek_to_lyric_timestamp,
            show_lyric_default=bool(getattr(self, "automation_script_editor_show_lyric", False)),
            on_show_lyric_changed=self._set_automation_script_editor_show_lyric,
            companion_bypass=bool(getattr(self, "companion_bypass", False)),
            internal_bypass=bool(getattr(self, "internal_bypass", False)),
            on_companion_bypass_changed=self._toggle_companion_bypass,
            on_internal_bypass_changed=self._toggle_internal_bypass,
            language=self.ui_language,
            parent=self,
        )
        self.automation_script_navigator_dock = self._create_panel_dock(
            "Automation Script Navigator",
            "automation_script_navigator_widget_dock",
            self._automation_script_navigator_window,
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.automation_script_navigator_dock)
        self._park_hidden_dock(self.automation_script_navigator_dock)

        self._companion_available_commands_dialog = CompanionAvailableCommandsDialog(self)
        self._companion_available_commands_dialog.clear_button.clicked.connect(self._clear_companion_available_commands)
        self._companion_available_commands_dialog.hide_black_empty_checkbox.toggled.connect(
            self._set_companion_available_commands_filter_black_empty
        )
        self._companion_available_commands_dialog.hide_navigation_checkbox.toggled.connect(
            self._refresh_companion_available_commands_dialog
        )
        self._companion_available_commands_dialog.bypassToggled.connect(self._toggle_companion_bypass)
        self._companion_available_commands_dialog.locationCommandRequested.connect(
            self._send_companion_location_command_async
        )
        self._companion_available_commands_dialog.openVirtualSatelliteRequested.connect(self._open_virtual_satellite)
        self.available_commands_dock = self._create_panel_dock(
            "Available Commands",
            "available_commands_widget_dock",
            self._companion_available_commands_dialog,
        )
        self.addDockWidget(Qt.RightDockWidgetArea, self.available_commands_dock)
        self._park_hidden_dock(self.available_commands_dock)

    def _divider_title(self, object_name: str) -> str:
        suffix = str(object_name or "").rsplit("_", 1)[-1]
        return f"Divider {suffix}" if suffix.isdigit() else "Divider"

    def _build_divider_widget(self, title: str) -> QWidget:
        widget = QFrame()
        widget.setFrameShape(QFrame.StyledPanel)
        widget.setMinimumSize(36, 36)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#666666; font-size:9pt;")
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addStretch(1)
        return widget

    def _ensure_divider_dock(self, object_name: str) -> QDockWidget:
        existing = self._divider_docks.get(object_name)
        if existing is not None:
            return existing
        title = self._divider_title(object_name)
        dock = self._create_panel_dock(title, object_name, self._build_divider_widget(title))
        self._divider_docks[object_name] = dock
        return dock

    def _next_divider_object_name(self) -> str:
        index = 1
        existing = set(self.dock_dividers) | set(self._divider_docks.keys())
        while True:
            candidate = f"divider_widget_dock_{index}"
            if candidate not in existing:
                return candidate
            index += 1

    def _create_divider_from_dock(self, target: QDockWidget, orientation) -> None:
        if bool(getattr(self, "window_layout_locked", False)):
            return
        object_name = self._next_divider_object_name()
        dock = self._ensure_divider_dock(object_name)
        self.dock_dividers.append(object_name)
        if target.isFloating():
            dock.setFloating(True)
            target_rect = target.geometry()
            width = max(120, target_rect.width() // 3)
            height = max(100, target_rect.height() // 3)
            if orientation == Qt.Horizontal:
                dock.setGeometry(target_rect.right() + 20, target_rect.top(), width, target_rect.height())
            else:
                dock.setGeometry(target_rect.left(), target_rect.bottom() + 20, target_rect.width(), height)
            dock.show()
        else:
            area = self.dockWidgetArea(target)
            if area == Qt.NoDockWidgetArea:
                area = Qt.RightDockWidgetArea
            self.addDockWidget(area, dock)
            self.splitDockWidget(target, dock, orientation)
            dock.show()
        self._build_window_menu()
        self._handle_dock_runtime_layout_change()
        if not self._suspend_settings_save:
            self._save_settings()

    def _create_global_divider(self, orientation) -> None:
        if bool(getattr(self, "window_layout_locked", False)):
            return
        object_name = self._next_divider_object_name()
        dock = self._ensure_divider_dock(object_name)
        self.dock_dividers.append(object_name)
        if orientation == Qt.Vertical:
            area = Qt.BottomDockWidgetArea
        else:
            area = Qt.RightDockWidgetArea
        self.addDockWidget(area, dock)
        dock.show()
        self._build_window_menu()
        self._handle_dock_runtime_layout_change()
        if not self._suspend_settings_save:
            self._save_settings()

    def _create_divider_on_canvas(self, orientation) -> None:
        self._create_global_divider(orientation)

    def _remove_all_divider_docks(self) -> None:
        for name, dock in list(self._divider_docks.items()):
            try:
                self.removeDockWidget(dock)
            except Exception:
                pass
            dock.hide()
            dock.deleteLater()
        self._divider_docks.clear()
        self.dock_dividers = []

    def _all_known_docks(self) -> List[QDockWidget]:
        docks = [
            self.notice_dock,
            self.group_dock,
            self.page_dock,
            self.sound_buttons_dock,
            self.status_display_dock,
            self.main_button_dock,
            self.fade_button_dock,
            self.meter_volume_dock,
            self.time_transport_dock,
            self.lyric_navigator_dock,
            self.automation_script_navigator_dock,
            self.available_commands_dock,
            self.timecode_dock,
            self.video_control_dock,
        ]
        docks.extend(self._divider_docks.values())
        return [dock for dock in docks if dock is not None]

    def _clear_active_dock_layout(self) -> None:
        for dock in self._all_known_docks():
            if dock is None:
                continue
            try:
                self.removeDockWidget(dock)
            except Exception:
                pass
        if self.notice_dock is not None:
            self.addDockWidget(Qt.TopDockWidgetArea, self.notice_dock)
        self._sync_dock_canvas_visibility()

    def _core_layout_docks(self) -> List[QDockWidget]:
        return [
            self.group_dock,
            self.page_dock,
            self.sound_buttons_dock,
            self.status_display_dock,
            self.main_button_dock,
            self.fade_button_dock,
            self.meter_volume_dock,
            self.time_transport_dock,
        ]

    def _apply_default_dock_layout(self) -> None:
        self._clear_active_dock_layout()
        for dock in self._core_layout_docks():
            if dock is not None:
                dock.setAllowedAreas(Qt.AllDockWidgetAreas)
                dock.setFloating(False)
                dock.show()
        for dock in [self.lyric_navigator_dock, self.automation_script_navigator_dock, self.available_commands_dock]:
            if dock is not None:
                self._park_hidden_dock(dock)
        if self.timecode_dock is not None:
            if self.show_timecode_panel:
                self.timecode_dock.setFloating(False)
                self.timecode_dock.show()
            else:
                self._park_hidden_dock(self.timecode_dock)
        if self.video_control_dock is not None:
            if self.show_video_control_panel:
                self.video_control_dock.setFloating(False)
                self.video_control_dock.show()
            else:
                self._park_hidden_dock(self.video_control_dock)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.group_dock)
        self.splitDockWidget(self.group_dock, self.main_button_dock, Qt.Horizontal)
        self.splitDockWidget(self.group_dock, self.page_dock, Qt.Vertical)
        self.splitDockWidget(self.main_button_dock, self.sound_buttons_dock, Qt.Vertical)
        self.splitDockWidget(self.main_button_dock, self.fade_button_dock, Qt.Horizontal)
        self.splitDockWidget(self.main_button_dock, self.status_display_dock, Qt.Vertical)
        self.splitDockWidget(self.fade_button_dock, self.meter_volume_dock, Qt.Vertical)
        self.splitDockWidget(self.meter_volume_dock, self.time_transport_dock, Qt.Vertical)

        self._apply_default_dock_sizes()
        changed = False
        for dock in self._core_layout_docks():
            if dock is not None and dock.isFloating():
                dock.setFloating(False)
                changed = True
        if changed:
            self._apply_default_dock_sizes()
        self._sync_dock_canvas_visibility()

    def _apply_default_dock_sizes(self) -> None:
        self.resizeDocks(
            [self.group_dock, self.main_button_dock],
            [180, 1180],
            Qt.Horizontal,
        )
        self.resizeDocks([self.group_dock, self.page_dock], [85, 655], Qt.Vertical)
        self.resizeDocks([self.main_button_dock, self.fade_button_dock], [860, 260], Qt.Horizontal)
        self.resizeDocks([self.main_button_dock, self.status_display_dock], [170, 80], Qt.Vertical)
        self.resizeDocks(
            [self.fade_button_dock, self.meter_volume_dock, self.time_transport_dock],
            [55, 75, 120],
            Qt.Vertical,
        )
        self.resizeDocks([self.main_button_dock, self.sound_buttons_dock], [250, 650], Qt.Vertical)

    def _restore_saved_dock_layout(self) -> bool:
        raw = str(getattr(self, "dock_layout_state", "") or "").strip()
        if not raw:
            return False
        try:
            state = QByteArray.fromBase64(raw.encode("ascii"))
        except Exception:
            return False
        if state.isEmpty():
            return False
        restored = bool(self.restoreState(state, DOCK_LAYOUT_STATE_VERSION))
        if restored:
            self._sync_dock_canvas_visibility()
            return True
        self.dock_layout_state = ""
        return False

    def _capture_dock_layout_state(self) -> str:
        try:
            encoded = self.saveState(DOCK_LAYOUT_STATE_VERSION).toBase64()
            return bytes(encoded).decode("ascii")
        except Exception:
            return ""

    def _sync_live_dock_layout_state(self) -> None:
        self._dock_layout_save_pending = False
        self.dock_layout_state = self._capture_dock_layout_state()

    def _visible_docked_docks(self) -> List[QDockWidget]:
        return [
            dock
            for dock in self._all_known_docks()
            if dock is not None and dock is not self.notice_dock and dock.isVisible() and not dock.isFloating()
        ]

    def _sync_dock_canvas_visibility(self) -> None:
        if self._dock_canvas is None:
            return
        if self._visible_docked_docks():
            self._dock_canvas.hide()
        else:
            self._dock_canvas.show()

    def _handle_dock_top_level_changed(self, dock: Optional[QDockWidget], floating: bool) -> None:
        if dock is not None and floating and dock.isVisible():
            name = str(dock.objectName() or "").strip()
            if name and name not in self.standalone_docks:
                self.standalone_docks = [*self.standalone_docks, name]
                self._apply_dock_mode(dock)
        self._handle_dock_runtime_layout_change()

    def _handle_dock_runtime_layout_change(self) -> None:
        self._sync_dock_canvas_visibility()
        self._schedule_dock_layout_save()

    def _remove_blank_dock_space(self) -> None:
        if bool(getattr(self, "window_layout_locked", False)):
            return
        self._sync_dock_canvas_visibility()
        self._sync_live_dock_layout_state()
        if not self._suspend_settings_save:
            self._save_settings()

    def _schedule_dock_layout_save(self) -> None:
        if self._suspend_settings_save or self._dock_layout_save_pending:
            return
        self._dock_layout_save_pending = True
        QTimer.singleShot(0, self._commit_dock_layout_state)

    def _commit_dock_layout_state(self) -> None:
        self._sync_live_dock_layout_state()
        if not self._suspend_settings_save:
            self._save_settings()

    def _restore_default_dock_layout(self) -> None:
        self._remove_all_divider_docks()
        self.show_timecode_panel = False
        self.show_video_control_panel = False
        self.standalone_docks = []
        if self.timecode_dock is not None:
            self.timecode_dock.hide()
        if self.video_control_dock is not None:
            self.video_control_dock.hide()
        self.dock_layout_state = ""
        self._apply_default_dock_layout()
        self.standalone_docks = []
        self._apply_saved_dock_modes()
        self._build_window_menu()
        self._handle_dock_runtime_layout_change()
        if not self._suspend_settings_save:
            self._save_settings()

    def _dock_features_for(self, dock: Optional[QDockWidget]) -> QDockWidget.DockWidgetFeatures:
        if bool(getattr(self, "window_layout_locked", False)):
            return QDockWidget.NoDockWidgetFeatures
        if self._is_standalone_dock(dock):
            return QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable
        return (
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )

    def _apply_saved_dock_modes(self) -> None:
        for dock in self._window_menu_docks():
            if dock is None:
                continue
            self._apply_dock_mode(dock)

    def _apply_dock_mode(self, dock: QDockWidget) -> None:
        standalone = self._is_standalone_dock(dock)
        if standalone:
            dock.setAllowedAreas(Qt.NoDockWidgetArea)
            if not dock.isFloating():
                dock.setFloating(True)
        else:
            dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        dock.setFeatures(self._dock_features_for(dock))

    def _set_dock_standalone_mode(self, dock: Optional[QDockWidget], enabled: bool) -> None:
        if dock is None or bool(getattr(self, "window_layout_locked", False)):
            return
        name = str(dock.objectName() or "").strip()
        if not name:
            return
        updated = [value for value in self.standalone_docks if value != name]
        if enabled:
            updated.append(name)
        self.standalone_docks = updated
        self._apply_dock_mode(dock)
        self._handle_dock_runtime_layout_change()
        if not self._suspend_settings_save:
            self._save_settings()

    def _clear_all_standalone_modes(self) -> None:
        if bool(getattr(self, "window_layout_locked", False)):
            return
        if not self.standalone_docks:
            return
        self.standalone_docks = []
        self._apply_saved_dock_modes()
        self._handle_dock_runtime_layout_change()
        if not self._suspend_settings_save:
            self._save_settings()

    def _sync_window_layout_lock_ui(self) -> None:
        for dock in self._window_menu_docks():
            if dock is None:
                continue
            self._apply_dock_mode(dock)
        if self._dock_canvas is not None:
            self._dock_canvas.setContextMenuPolicy(
                Qt.NoContextMenu if bool(self.window_layout_locked) else Qt.CustomContextMenu
            )
        locked = bool(self.window_layout_locked)
        for action in [
            getattr(self, "_remove_blank_space_action", None),
            getattr(self, "_add_horizontal_divider_action", None),
            getattr(self, "_add_vertical_divider_action", None),
            getattr(self, "_clear_all_standalone_action", None),
        ]:
            if action is not None:
                action.setEnabled(not locked)
        if self._layout_lock_action is not None:
            self._layout_lock_action.blockSignals(True)
            self._layout_lock_action.setChecked(bool(self.window_layout_locked))
            self._layout_lock_action.blockSignals(False)

    def _toggle_window_layout_lock(self, checked: bool) -> None:
        self.window_layout_locked = bool(checked)
        self._sync_window_layout_lock_ui()
        if not self._suspend_settings_save:
            self._save_settings()

    def _is_separator_drag_event(self, pos) -> bool:
        try:
            point = pos if hasattr(pos, "x") and hasattr(pos, "y") else None
            if point is None:
                return False
            if self.childAt(point) is not None:
                return False
            docks = self._visible_docked_docks()
            if len(docks) < 2:
                return False
            tolerance = 8
            for dock in docks:
                rect = dock.geometry()
                if abs(point.x() - rect.right()) <= tolerance and rect.top() - tolerance <= point.y() <= rect.bottom() + tolerance:
                    return True
                if abs(point.y() - rect.bottom()) <= tolerance and rect.left() - tolerance <= point.x() <= rect.right() + tolerance:
                    return True
            return False
        except Exception:
            return False

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
        if self._getting_started_window is not None:
            self._getting_started_window.set_language(self.ui_language)
        if self._tips_window is not None:
            self._tips_window.set_language(self.ui_language)
        if self._stage_display_window is not None:
            self._stage_display_window.retranslate_ui()
        self._refresh_button_legend_label()

    def _refresh_button_legend_label(self) -> None:
        while self._button_legend_layout.count():
            item = self._button_legend_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        title = QLabel(tr("Button Legend:"))
        title.setStyleSheet("color:#666666; font-size:9pt; font-weight:600;")
        title_layout.addWidget(title)
        title_layout.addStretch(1)
        self._button_legend_layout.addWidget(title_row)

        items = [
            (self.state_colors["playing"], tr("Now Playing")),
            (self.state_colors["played"], tr("Played")),
            (self.state_colors["assigned"], tr("Unplayed")),
            (self.state_colors["cue_indicator"], tr("Cue Stripe")),
            (self.state_colors["volume_indicator"], tr("Volume Stripe")),
            (self.state_colors["vocal_removed_indicator"], tr("Vocal Removed Stripe")),
            (self.state_colors["lyric_indicator"], tr("Lyric Stripe")),
            (self.state_colors["automation_indicator"], tr("Automation Stripe")),
            (self.state_colors["automation_indicator_bypassed"], tr("Automation Bypassed Stripe")),
            (self.state_colors["automation_script_indicator"], tr("Automation Script Stripe")),
            (
                self.state_colors["automation_script_indicator_bypassed"],
                tr("Automation Script Bypassed Stripe"),
            ),
            (TIMECODE_SLOT_INDICATOR_COLOR, tr("Timecode Stripe")),
            (self.state_colors["midi_indicator"], tr("MIDI Top Stripe")),
        ]
        split_index = (len(items) + 1) // 2
        for row_items in (items[:split_index], items[split_index:]):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            for color, label_text in row_items:
                item_widget = QWidget()
                item_layout = QHBoxLayout(item_widget)
                item_layout.setContentsMargins(0, 0, 0, 0)
                item_layout.setSpacing(4)

                dot = QLabel("")
                dot.setFixedSize(10, 10)
                dot.setStyleSheet(
                    "QLabel{"
                    f"background:{str(color or '#000000')};"
                    "border:1px solid #666666;"
                    "border-radius:5px;"
                    "}"
                )
                text = QLabel(label_text)
                text.setStyleSheet("color:#666666; font-size:9pt;")

                item_layout.addWidget(dot)
                item_layout.addWidget(text)
                row_layout.addWidget(item_widget)
            row_layout.addStretch(1)
            self._button_legend_layout.addWidget(row_widget)

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

        pack_audio_library_action = QAction(tr("Pack Audio Library"), self)
        pack_audio_library_action.triggered.connect(self._pack_audio_library)
        file_menu.addAction(pack_audio_library_action)

        unpack_audio_library_action = QAction(tr("Unpack Audio Library"), self)
        unpack_audio_library_action.triggered.connect(self._unpack_audio_library)
        file_menu.addAction(unpack_audio_library_action)

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
        preferences_action: Optional[QAction] = None
        if sys.platform == "darwin":
            preferences_action = QAction("Preferences", self)
            preferences_action.triggered.connect(self._open_options_dialog)
            setup_menu.addAction(preferences_action)
        setup_menu.addAction(options_action)
        configure_preferences_menu_actions(
            options_action,
            preferences_action,
            platform_name=sys.platform,
        )
        self._menu_actions["options"] = options_action
        open_web_remote_action = QAction("Open Web Remote", self)
        open_web_remote_action.triggered.connect(self._open_web_remote)
        setup_menu.addAction(open_web_remote_action)

        display_menu = self.menuBar().addMenu("Display")
        show_display_action = QAction("Show Stage Display", self)
        show_display_action.triggered.connect(self._show_stage_display)
        display_menu.addAction(show_display_action)
        send_alert_action = QAction("Send Alert", self)
        send_alert_action.triggered.connect(self._open_stage_alert_panel)
        display_menu.addAction(send_alert_action)
        lyric_display_action = QAction("Open Lyric Display", self)
        lyric_display_action.triggered.connect(self._open_lyric_display)
        display_menu.addAction(lyric_display_action)
        video_display_action = QAction("Open Video Display", self)
        video_display_action.triggered.connect(self._open_video_display)
        display_menu.addAction(video_display_action)
        display_settings_action = QAction("Stage and Lyric Display Setting", self)
        display_settings_action.triggered.connect(lambda: self._open_options_dialog(initial_page="Stage and Lyric Display"))
        display_menu.addAction(display_settings_action)
        video_settings_action = QAction("Video Display Setting", self)
        video_settings_action.triggered.connect(lambda: self._open_options_dialog(initial_page="Video Display"))
        display_menu.addAction(video_settings_action)
        self._lyric_display_transparent_mode_action = QAction("Lyric Display Transparent Mode", self)
        self._lyric_display_transparent_mode_action.setCheckable(True)
        self._lyric_display_transparent_mode_action.setChecked(bool(self.lyric_display_transparent_mode))
        self._lyric_display_transparent_mode_action.triggered.connect(self._toggle_lyric_display_transparent_mode)
        display_menu.addAction(self._lyric_display_transparent_mode_action)
        web_lyric_display_menu = display_menu.addMenu("Web Lyric Display")
        web_lyric_caption_action = QAction("Caption", self)
        web_lyric_caption_action.triggered.connect(lambda: self._open_web_lyric_display("caption"))
        web_lyric_display_menu.addAction(web_lyric_caption_action)
        web_lyric_overhead_action = QAction("Overhead", self)
        web_lyric_overhead_action.triggered.connect(lambda: self._open_web_lyric_display("overhead"))
        web_lyric_display_menu.addAction(web_lyric_overhead_action)
        web_lyric_banner_action = QAction("Banner", self)
        web_lyric_banner_action.triggered.connect(lambda: self._open_web_lyric_display("banner"))
        web_lyric_display_menu.addAction(web_lyric_banner_action)
        web_lyric_vmix_action = QAction("vMix Overlay", self)
        web_lyric_vmix_action.triggered.connect(lambda: self._open_web_lyric_display("vmixoverlay"))
        web_lyric_display_menu.addAction(web_lyric_vmix_action)
        self._lyric_blank_toggle_action = QAction("Blank Lyric", self)
        self._lyric_blank_toggle_action.setCheckable(True)
        self._lyric_blank_toggle_action.triggered.connect(lambda checked=False: self._set_lyric_force_blank(bool(checked)))
        display_menu.addAction(self._lyric_blank_toggle_action)
        self._sync_lyric_display_controls()
        self._build_navigation_menu()

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
        video_control_panel_action = QAction("Video Control Panel", self)
        video_control_panel_action.setCheckable(True)
        video_control_panel_action.setChecked(bool(self.show_video_control_panel))
        video_control_panel_action.triggered.connect(self._toggle_video_control_panel)
        timecode_menu.addAction(video_control_panel_action)
        self._menu_actions["video_control_panel"] = video_control_panel_action

        tools_menu = self.menuBar().addMenu("Tools")
        show_colour_legend_action = QAction("Show Colour Legend", self)
        show_colour_legend_action.setCheckable(True)
        show_colour_legend_action.setChecked(bool(self.show_colour_legend))
        show_colour_legend_action.triggered.connect(self._toggle_colour_legend)
        tools_menu.addAction(show_colour_legend_action)
        self._menu_actions["show_colour_legend"] = show_colour_legend_action

        tools_menu.addSeparator()

        duplicate_check_action = QAction("Duplicate Check", self)
        duplicate_check_action.triggered.connect(self._run_duplicate_check)
        tools_menu.addAction(duplicate_check_action)

        verify_sound_buttons_action = QAction("Verify Sound Buttons", self)
        verify_sound_buttons_action.triggered.connect(self._run_verify_sound_buttons)
        tools_menu.addAction(verify_sound_buttons_action)

        scan_sound_button_lyrics_action = QAction("Scan Sound Buttons Lyrics", self)
        scan_sound_button_lyrics_action.triggered.connect(self._scan_sound_button_lyrics)
        tools_menu.addAction(scan_sound_button_lyrics_action)

        lyric_navigator_action = QAction("Lyric Navigator", self)
        lyric_navigator_action.triggered.connect(self._open_lyric_navigator)
        tools_menu.addAction(lyric_navigator_action)

        remove_linked_lyrics_action = QAction("Remove All Linked Lyric File", self)
        remove_linked_lyrics_action.triggered.connect(self._remove_all_linked_lyric_files)
        tools_menu.addAction(remove_linked_lyrics_action)

        bulk_generate_vocal_removed_action = QAction("Bulk Generate Vocal Removed Track", self)
        bulk_generate_vocal_removed_action.triggered.connect(self._bulk_generate_vocal_removed_tracks)
        tools_menu.addAction(bulk_generate_vocal_removed_action)

        link_unlinked_vocal_removed_action = QAction("Link Unlinked Vocal Removed Track", self)
        link_unlinked_vocal_removed_action.triggered.connect(self._link_unlinked_vocal_removed_tracks)
        tools_menu.addAction(link_unlinked_vocal_removed_action)

        remove_linked_vocal_removed_action = QAction("Unlink All Vocal Removed Track", self)
        remove_linked_vocal_removed_action.triggered.connect(self._remove_all_linked_vocal_removed_files)
        tools_menu.addAction(remove_linked_vocal_removed_action)

        disable_playlist_all_pages_action = QAction("Disable Play List on All Pages", self)
        disable_playlist_all_pages_action.triggered.connect(self._disable_playlist_on_all_pages)
        tools_menu.addAction(disable_playlist_all_pages_action)
        reset_all_pages_action = QAction("Reset All Pages", self)
        reset_all_pages_action.triggered.connect(self._reset_all_pages_state)
        tools_menu.addAction(reset_all_pages_action)

        tools_menu.addSeparator()

        clear_waveform_cache_action = QAction("Clear Waveform Cache", self)
        clear_waveform_cache_action.triggered.connect(self._clear_waveform_cache_now)
        tools_menu.addAction(clear_waveform_cache_action)

        open_settings_folder_action = QAction("Open Settings Folder", self)
        open_settings_folder_action.triggered.connect(self._open_settings_folder)
        tools_menu.addAction(open_settings_folder_action)

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

        scan_sound_button_automation_scripts_action = QAction(tr("Scan Sound Button Automation Scripts"), self)
        scan_sound_button_automation_scripts_action.triggered.connect(self._scan_sound_button_automation_scripts)
        tools_menu.addAction(scan_sound_button_automation_scripts_action)

        remove_all_linked_automation_scripts_action = QAction(tr("Remove All Linked Automation Scripts"), self)
        remove_all_linked_automation_scripts_action.triggered.connect(self._remove_all_linked_automation_scripts)
        tools_menu.addAction(remove_all_linked_automation_scripts_action)

        launchpad_cheatsheet_action = QAction("Launchpad Cheat Sheet", self)
        launchpad_cheatsheet_action.triggered.connect(self._show_launchpad_cheatsheet)
        tools_menu.addAction(launchpad_cheatsheet_action)

        companion_menu = self.menuBar().addMenu(tr("Automation"))
        open_virtual_satellite_action = QAction(tr("Open Virtual Satellite"), self)
        open_virtual_satellite_action.triggered.connect(self._open_virtual_satellite)
        companion_menu.addAction(open_virtual_satellite_action)
        self._menu_actions["open_virtual_satellite"] = open_virtual_satellite_action
        available_commands_action = QAction(tr("Available Commands"), self)
        available_commands_action.triggered.connect(self._open_companion_available_commands)
        companion_menu.addAction(available_commands_action)
        self._menu_actions["companion_available_commands"] = available_commands_action
        automation_script_navigator_action = QAction(tr("Automation Script Navigator"), self)
        automation_script_navigator_action.triggered.connect(self._open_automation_script_navigator)
        companion_menu.addAction(automation_script_navigator_action)
        self._menu_actions["automation_script_navigator"] = automation_script_navigator_action
        bypass_action = QAction(tr("Bypass Companion Commands"), self)
        bypass_action.setCheckable(True)
        bypass_action.setChecked(bool(self.companion_bypass))
        bypass_action.triggered.connect(self._toggle_companion_bypass)
        companion_menu.addAction(bypass_action)
        self._menu_actions["companion_bypass"] = bypass_action
        internal_bypass_action = QAction(tr("Bypass Internal Commands"), self)
        internal_bypass_action.setCheckable(True)
        internal_bypass_action.setChecked(bool(self.internal_bypass))
        internal_bypass_action.triggered.connect(self._toggle_internal_bypass)
        companion_menu.addAction(internal_bypass_action)
        self._menu_actions["internal_bypass"] = internal_bypass_action
        companion_menu.addSeparator()
        open_companion_satellite_options_action = QAction(tr("Open Automation Setup"), self)
        open_companion_satellite_options_action.triggered.connect(self._open_companion_satellite_options)
        companion_menu.addAction(open_companion_satellite_options_action)
        self._menu_actions["open_companion_satellite_options"] = open_companion_satellite_options_action

        log_menu = self.menuBar().addMenu("Logs")
        view_log_action = QAction("View Log", self)
        view_log_action.triggered.connect(self._view_log_file)
        log_menu.addAction(view_log_action)

        self._build_window_menu()
        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._open_about_window)
        application_about_action: Optional[QAction] = None
        if sys.platform == "darwin":
            application_about_action = QAction("About", self)
            application_about_action.triggered.connect(self._open_about_window)
            help_menu.addAction(application_about_action)
        help_menu.addAction(about_action)
        configure_about_menu_actions(
            about_action,
            application_about_action,
            platform_name=sys.platform,
        )
        system_info_action = QAction("System Information", self)
        system_info_action.triggered.connect(self._open_system_information_window)
        help_menu.addAction(system_info_action)
        audio_engine_insight_action = QAction("Audio Engine Insight", self)
        audio_engine_insight_action.triggered.connect(self._open_audio_engine_insight_window)
        help_menu.addAction(audio_engine_insight_action)

        help_action = QAction("Help", self)
        help_action.triggered.connect(self._open_help_window)
        help_menu.addAction(help_action)

        getting_started_action = QAction("Getting Started", self)
        getting_started_action.triggered.connect(lambda _=False: self._open_getting_started_window(startup=False))
        help_menu.addAction(getting_started_action)

        latest_version_action = QAction("Get the Latest Version", self)
        latest_version_action.triggered.connect(self._open_latest_version_page)
        help_menu.addAction(latest_version_action)
        website_action = QAction("Website", self)
        website_action.triggered.connect(self._open_website_page)
        help_menu.addAction(website_action)

        tips_action = QAction("Tips", self)
        tips_action.triggered.connect(lambda _=False: self._open_tips_window(startup=False))
        help_menu.addAction(tips_action)

        register_action = QAction("Register", self)
        register_action.triggered.connect(self._show_register_message)
        help_menu.addAction(register_action)

        if not getattr(sys, "frozen", False):
            debug_crash_action = QAction("Crash for Debug", self)
            debug_crash_action.triggered.connect(self._trigger_debug_crash)
            help_menu.addAction(debug_crash_action)
        if sys.platform != "darwin":
            self.lock_screen_button = self._create_lock_screen_button(self.menuBar(), auto_raise=True)
            self.menuBar().setCornerWidget(self.lock_screen_button, Qt.TopRightCorner)
        self._apply_hotkeys()

    def _build_navigation_menu(self) -> None:
        if self._navigation_menu is None:
            self._navigation_menu = self.menuBar().addMenu("Navigation")
        else:
            self._navigation_menu.clear()

        previous_group_action = QAction("Previous Group", self)
        previous_group_action.triggered.connect(lambda _=False: self._hotkey_select_group_delta(-1))
        self._navigation_menu.addAction(previous_group_action)

        next_group_action = QAction("Next Group", self)
        next_group_action.triggered.connect(lambda _=False: self._hotkey_select_group_delta(1))
        self._navigation_menu.addAction(next_group_action)

        self._navigation_menu.addSeparator()

        previous_page_action = QAction("Previous Page", self)
        previous_page_action.triggered.connect(lambda _=False: self._hotkey_select_page_delta(-1))
        self._navigation_menu.addAction(previous_page_action)

        next_page_action = QAction("Next Page", self)
        next_page_action.triggered.connect(lambda _=False: self._hotkey_select_page_delta(1))
        self._navigation_menu.addAction(next_page_action)

        home_page_action = QAction("Home Page", self)
        home_page_action.triggered.connect(lambda _=False: self._navigate_to_page(0))
        self._navigation_menu.addAction(home_page_action)

        self._navigation_menu.addSeparator()

        self._navigation_group_menu = self._navigation_menu.addMenu("Groups")
        self._navigation_group_actions = {}
        for group in GROUPS:
            action = QAction(group, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, value=group: self._navigate_to_group(value))
            self._navigation_group_menu.addAction(action)
            self._navigation_group_actions[group] = action

        self._navigation_page_menu = self._navigation_menu.addMenu("Pages")
        self._navigation_page_actions = {}
        for page_index in range(PAGE_COUNT):
            action = QAction("", self)
            action.setCheckable(True)
            action.triggered.connect(lambda _=False, value=page_index: self._navigate_to_page(value))
            self._navigation_page_menu.addAction(action)
            self._navigation_page_actions[page_index] = action

        self._sync_navigation_menu_state()

    def _navigate_to_group(self, group: str) -> None:
        if self.cue_mode:
            self._toggle_cue_mode(False)
        self._select_group(group)

    def _navigate_to_page(self, page_index: int) -> None:
        if self.cue_mode:
            self._toggle_cue_mode(False)
        self._select_page(page_index)

    def _navigation_page_action_text(self, page_index: int) -> str:
        return f"{page_index + 1}. {self._page_display_name(self.current_group, page_index)}"

    def _sync_navigation_menu_state(self) -> None:
        for group, action in self._navigation_group_actions.items():
            action.blockSignals(True)
            action.setChecked(group == self.current_group)
            action.blockSignals(False)
        for page_index, action in self._navigation_page_actions.items():
            action.blockSignals(True)
            action.setText(self._navigation_page_action_text(page_index))
            action.setChecked((not self.cue_mode) and page_index == self.current_page)
            action.blockSignals(False)

    def _create_lock_screen_button(self, parent: QWidget, *, auto_raise: bool) -> QToolButton:
        button = QToolButton(parent)
        button.setCheckable(True)
        button.setAutoRaise(bool(auto_raise))
        button.setIcon(QIcon(build_lock_icon()))
        button.setIconSize(QSize(18, 18))
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.clicked.connect(self._on_lock_screen_button_clicked)
        return button

    def _on_lock_screen_button_clicked(self) -> None:
        if sys.platform == "darwin":
            QTimer.singleShot(0, self._toggle_lock_screen)
            return
        self._toggle_lock_screen()

    def _show_register_message(self) -> None:
        QMessageBox.information(
            self,
            "Register",
            "pySSP is free software. No registration is required.",
        )

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
                version_text=self.app_version_text,
                website_url=self._website_url(),
                parent=self,
            )
            self._about_window.destroyed.connect(lambda _=None: self._clear_about_window_ref())

        about_text = self._load_asset_text_file("about", "about.md").replace("{{VERSION}}", self.app_version_text)
        credits_text = self._load_asset_text_file("about", "credits.md")
        license_text = self._load_asset_text_file("about", "license.md")
        ndi_status = getattr(self, "_ndi_status", None)
        ndi_backend = str(getattr(ndi_status, "ndi_backend_name", "cyndilib") or "cyndilib")
        ndi_version = str(getattr(ndi_status, "ndi_python_version", "not installed") or "not installed")
        ndi_state = str(getattr(ndi_status, "availability_reason", "unknown") or "unknown")
        about_text += (
            "\n\n---\n\n"
            "## NDI Output\n\n"
            f"- `{ndi_backend}` version: `{ndi_version}`\n"
            f"- Runtime status: `{ndi_state}`\n"
            f"- Download: {NDI_DOWNLOAD_URL}\n"
            "- NDI SDK/runtime is separately licensed and may need to be installed on the target machine.\n"
        )
        self._about_window.set_version_and_website(
            self.app_version_text,
            self._website_url(),
            self.app_build_text,
        )
        self._about_window.set_content(about_text=about_text, credits_text=credits_text, license_text=license_text)
        self._about_window.show()
        self._about_window.raise_()
        self._about_window.activateWindow()

    def _open_system_information_window(self) -> None:
        if self._is_playback_in_progress():
            answer = QMessageBox.question(
                self,
                tr("System Information"),
                tr("Opening System Information during playback may interrupt playback. Do you want to continue?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        if self._system_info_window is None:
            self._system_info_window = SystemInformationDialog(
                app_version_text=self.app_version_text,
                app_build_text=self.app_build_text,
                parent=self,
            )
            self._system_info_window.destroyed.connect(lambda _=None: self._clear_system_info_window_ref())
        self._system_info_window.set_app_version_text(self.app_version_text)
        self._system_info_window.set_app_build_text(self.app_build_text)
        self._system_info_window.refresh()
        self._system_info_window.show()
        self._system_info_window.raise_()
        self._system_info_window.activateWindow()

    def _open_audio_engine_insight_window(self) -> None:
        if self._audio_engine_insight_window is None:
            self._audio_engine_insight_window = AudioEngineInsightDialog(
                snapshot_provider=self._audio_engine_insight_snapshot_data,
                parent=self,
            )
            self._audio_engine_insight_window.destroyed.connect(
                lambda _=None: self._clear_audio_engine_insight_window_ref()
            )
        self._audio_engine_insight_window.refresh()
        self._audio_engine_insight_window.show()
        self._audio_engine_insight_window.raise_()
        self._audio_engine_insight_window.activateWindow()

    def _audio_engine_insight_snapshot_data(self) -> dict:
        ref_player, ref_key = self._timecode_reference_context()
        engine_left, engine_right = get_engine_output_meter_levels()
        ffmpeg_path = str(get_ffmpeg_executable() or "").strip()
        ffprobe_path = str(get_ffprobe_executable() or "").strip()
        current_video_slot = None
        current_video_probe = MediaProbeInfo()
        try:
            current_video_slot, current_video_probe = self._current_video_slot_and_probe()
        except Exception:
            current_video_slot, current_video_probe = None, MediaProbeInfo()
        ndi_sender = getattr(self, "_ndi_sender", None)
        ndi_audio_players = []
        try:
            ndi_audio_players = list(getattr(self, "_ndi_audio_players", lambda: [])() or [])
        except Exception:
            ndi_audio_players = []
        ndi_audio_player_labels = [self._audio_player_label(player) for player in ndi_audio_players]
        ndi_buffer_frames = self._ndi_audio_buffer_frame_summary()
        summary = [
            ("audio_output_device", self.audio_output_device or "default"),
            ("timecode_audio_output_device", self.timecode_audio_output_device or "none"),
            ("timecode_mode", self.timecode_mode),
            ("multi_play_enabled", self._is_multi_play_enabled()),
            ("active_playing_keys", len(self._active_playing_keys)),
            ("current_playing", self.current_playing),
            ("fade_jobs", len(self._fade_jobs)),
            ("global_volume", self.volume_slider.value() if self.volume_slider is not None else 100),
            ("dsp_config", self._describe_dsp_config(self._dsp_config)),
            ("engine_output_meter", f"({engine_left:.4f}, {engine_right:.4f})"),
            ("timecode_reference", "none" if ref_player is None else f"{self._audio_player_label(ref_player)} slot={ref_key}"),
            ("ffmpeg_available", ffmpeg_available()),
            ("ffmpeg_source", ffmpeg_source()),
            ("ffmpeg_path", ffmpeg_path or "not found"),
            ("ffprobe_path", ffprobe_path or "not found"),
            ("ffmpeg_version", ffmpeg_version_text() or "unknown"),
            ("ndi_enabled", bool(getattr(self, "ndi_output_enabled", False))),
            ("ndi_ready", bool(getattr(getattr(self, "_ndi_status", None), "ready", False))),
            ("ndi_backend", str(getattr(getattr(self, "_ndi_status", None), "ndi_backend_name", "cyndilib") or "cyndilib")),
            ("ndi_status", str(getattr(getattr(self, "_ndi_status", None), "availability_reason", "unknown"))),
            ("ndi_source_name", str(getattr(self, "ndi_output_name", "pyssp-video") or "pyssp-video")),
            ("ndi_route_mode", getattr(self, "_active_ndi_route_mode", lambda: "unknown")()),
            ("ndi_audio_enabled", bool(getattr(self, "ndi_output_audio_enabled", True))),
            ("ndi_audio_tap_mode", str(getattr(self, "ndi_output_audio_tap_mode", "post_fader") or "post_fader")),
            ("ndi_connection_count", int(getattr(ndi_sender, "get_num_connections", lambda _timeout=0.0: 0)(0.0))),
            ("ndi_audio_player_labels", ndi_audio_player_labels),
            ("ndi_audio_player_count", len(ndi_audio_player_labels)),
            ("ndi_audio_buffer_frames", ndi_buffer_frames),
            ("ndi_audio_send_count", int(getattr(ndi_sender, "_audio_send_count", 0) or 0)),
            ("ndi_audio_drop_count", int(getattr(ndi_sender, "_audio_drop_count", 0) or 0)),
            ("ndi_audio_recovery_count", int(getattr(ndi_sender, "_audio_recovery_count", 0) or 0)),
            ("ndi_last_audio_mode", str(getattr(getattr(self, "_ndi_sender", None), "_last_audio_mode", "") or "")),
            ("ndi_last_audio_error", str(getattr(getattr(self, "_ndi_sender", None), "_last_audio_error", "") or "")),
            ("video_route_mode", getattr(self, "_active_video_route_mode", lambda: "unknown")()),
            ("video_targets_visible", bool(getattr(self, "_video_display_target_visible", lambda: False)())),
            ("video_transport_revision", int(getattr(self, "_video_transport_revision", 0) or 0)),
            ("current_video_slot", None if current_video_slot is None else str(current_video_slot.file_path or "").strip()),
            (
                "current_video_probe",
                (
                    f"video={bool(current_video_probe.has_video)} "
                    f"audio={bool(current_video_probe.has_audio)} "
                    f"size={int(current_video_probe.width)}x{int(current_video_probe.height)} "
                    f"fps={float(current_video_probe.fps):.2f} "
                    f"duration_ms={int(current_video_probe.duration_ms)} "
                    f"rotation={int(current_video_probe.rotation_deg)}"
                ),
            ),
        ]
        player_records: List[dict] = []
        runtime_players = self._insight_runtime_players()
        for index, player in enumerate(runtime_players):
            player_records.append(self._audio_player_insight_record(player, index))
        return {"summary": summary, "players": player_records}

    def _insight_runtime_players(self) -> List[ExternalMediaPlayer]:
        players: List[ExternalMediaPlayer] = [self.player, self.player_b, *self._multi_players]
        for primary in [self.player, self.player_b, *self._multi_players]:
            shadow = self._shadow_player_for(primary)
            if shadow is not None:
                players.append(shadow)
        return players

    def _audio_player_label(self, player: object) -> str:
        if player is self.player:
            return "primary"
        if player is self.player_b:
            return "secondary"
        if player in self._multi_players:
            try:
                return f"multi[{self._multi_players.index(player)}]"
            except Exception:
                return "multi"
        for primary in [self.player, self.player_b, *self._multi_players]:
            shadow = self._shadow_player_for(primary)
            if shadow is player:
                return f"{self._audio_player_label(primary)}_shadow"
        return "player"

    def _describe_dsp_config(self, config: Optional[DSPConfig]) -> str:
        cfg = normalize_config(config)
        return (
            f"eq_enabled={cfg.eq_enabled}, "
            f"eq_bands={cfg.eq_bands}, "
            f"reverb_sec={cfg.reverb_sec}, "
            f"tempo_pct={cfg.tempo_pct}, "
            f"pitch_pct={cfg.pitch_pct}, "
            f"plugin_paths={cfg.plugin_paths}"
        )

    def _audio_player_insight_record(self, player: object, index: int) -> dict:
        label = self._audio_player_label(player)
        pid = id(player)
        ndi_audio_players = []
        try:
            ndi_audio_players = list(getattr(self, "_ndi_audio_players", lambda: [])() or [])
        except Exception:
            ndi_audio_players = []
        is_ndi_audio_player = player in ndi_audio_players
        slot_key = self._player_slot_key_map.get(pid)
        if slot_key is None:
            for primary in [self.player, self.player_b, *self._multi_players]:
                shadow = self._shadow_player_for(primary)
                if shadow is player:
                    slot_key = self._player_slot_key_map.get(id(primary))
                    break
        slot = self._slot_for_key(slot_key) if slot_key is not None else None
        runtime_id = self._playback_runtime.runtime_id_for(player)
        meter = getattr(player, "meterLevels", lambda: (0.0, 0.0))()
        try:
            state_name = self._api_player_state_name(player)  # type: ignore[arg-type]
        except Exception:
            state_name = "unknown"
        try:
            engine_pos = int(getattr(player, "enginePositionMs", lambda: 0)())
        except Exception:
            engine_pos = 0
        try:
            position_ms = int(getattr(player, "position", lambda: 0)())
        except Exception:
            position_ms = 0
        try:
            duration_ms = int(getattr(player, "duration", lambda: 0)())
        except Exception:
            duration_ms = 0
        try:
            volume = int(getattr(player, "volume", lambda: 0)())
        except Exception:
            volume = 0
        try:
            sample_rate = int(getattr(player, "sampleRate", lambda: 0)())
        except Exception:
            sample_rate = 0
        try:
            tap_counts = dict(getattr(player, "outputTapFrameCounts", lambda: {"pre_fader": 0, "post_fader": 0})())
        except Exception:
            tap_counts = {"pre_fader": 0, "post_fader": 0}
        title = "" if slot is None else self._build_now_playing_text(slot)
        file_path = "" if slot is None else str(slot.file_path or "").strip()
        media_probe = MediaProbeInfo()
        if file_path:
            try:
                media_probe = probe_media_info(file_path)
            except Exception:
                media_probe = MediaProbeInfo()
        details = [
            ("index", index),
            ("label", label),
            ("object_id", pid),
            ("runtime_id", runtime_id if runtime_id is not None else "inactive"),
            ("state", state_name),
            ("slot_key", slot_key),
            ("title", title),
            ("file_path", file_path),
            ("source_type", "" if slot is None else slot.source_type),
            ("disable_video_loading", False if slot is None else bool(getattr(slot, "disable_video_loading", False))),
            ("volume", volume),
            ("sample_rate", sample_rate),
            ("slot_volume_pct", self._slot_pct_for_player(player)),
            ("duration_ms", duration_ms),
            ("position_ms", position_ms),
            ("engine_position_ms", engine_pos),
            ("remaining_ms", max(0, duration_ms - position_ms)),
            ("streaming_mode", bool(getattr(player, "_streaming_mode", False))),
            ("media_path", getattr(player, "_media_path", "")),
            ("media_probe_has_audio", bool(media_probe.has_audio)),
            ("media_probe_has_video", bool(media_probe.has_video)),
            ("media_probe_width", int(media_probe.width)),
            ("media_probe_height", int(media_probe.height)),
            ("media_probe_fps", float(media_probe.fps)),
            ("media_probe_duration_ms", int(media_probe.duration_ms)),
            ("media_probe_rotation_deg", int(media_probe.rotation_deg)),
            ("cue_end_override_ms", self._player_end_override_ms.get(pid)),
            ("ignore_cue_end", pid in self._player_ignore_cue_end),
            ("started_at_monotonic", self._player_started_map.get(pid)),
            ("is_ndi_audio_player", is_ndi_audio_player),
            ("tap_pre_fader_frames", max(0, int(tap_counts.get("pre_fader", 0) or 0))),
            ("tap_post_fader_frames", max(0, int(tap_counts.get("post_fader", 0) or 0))),
            ("meter_levels", meter),
            ("dsp_config", self._describe_dsp_config(getattr(player, "_dsp_config", None))),
        ]
        return {
            "index": index,
            "label": label,
            "runtime_id": runtime_id if runtime_id is not None else "inactive",
            "state": state_name,
            "title": title,
            "details": details,
        }

    def _ndi_audio_buffer_frame_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        buffers = getattr(self, "_ndi_audio_player_buffers", {})
        if not isinstance(buffers, dict):
            return summary
        for player in self._insight_runtime_players():
            pending = np.asarray(buffers.get(id(player)), dtype=np.float32)
            if pending.ndim != 2:
                continue
            summary[self._audio_player_label(player)] = max(0, int(len(pending)))
        return summary

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

    def _open_getting_started_docs_page(self) -> None:
        target = self._help_doc_path("startup.html")
        if os.path.exists(target):
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(target)):
                QMessageBox.warning(
                    self,
                    "Help Open Failed",
                    f"Could not open help page with the default browser.\n\nPath:\n{target}",
                )
            return
        self._open_help_window()

    def _open_latest_version_page(self) -> None:
        releases_url = QUrl("https://github.com/sikaxn/pySSP/releases")
        if not QDesktopServices.openUrl(releases_url):
            QMessageBox.warning(
                self,
                "Help Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{releases_url.toString()}",
            )

    def _trigger_debug_crash(self) -> None:
        nonsense = None
        nonsense.setWindowTitle("This should crash")

    def _website_url(self) -> str:
        return "https://pyssp.studenttechsupport.com/"

    def _open_website_page(self) -> None:
        website_url = QUrl(self._website_url())
        if not QDesktopServices.openUrl(website_url):
            QMessageBox.warning(
                self,
                "Help Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{website_url.toString()}",
            )

    def _clear_getting_started_window_ref(self) -> None:
        self._getting_started_window = None

    def _open_audio_device_options(self) -> None:
        self._open_options_dialog(initial_page="Audio Device & Timecode")

    def _getting_started_image_path(self, *parts: str) -> str:
        docs_source = os.path.join(self._project_root_path(), "docs", "source", "images", *parts)
        if os.path.exists(docs_source):
            return docs_source
        docs_built = os.path.join(os.path.dirname(self._help_index_path()), "_images", *parts)
        if os.path.exists(docs_built):
            return docs_built
        basename = os.path.basename(os.path.join(*parts))
        docs_built_flat = os.path.join(os.path.dirname(self._help_index_path()), "_images", basename)
        if os.path.exists(docs_built_flat):
            return docs_built_flat
        return docs_source

    def _open_getting_started_window(self, startup: bool = False) -> None:
        if self._getting_started_window is None:
            self._getting_started_window = GettingStartedDialog(
                language=self.ui_language,
                version_text=self.app_version_text,
                build_text=self.app_build_text,
                beta_build=is_beta_version(self.app_version_text),
                splash_image_path=self._asset_file_path("logo2.png"),
                add_page_image_path=self._getting_started_image_path("getting_started", "add_page.png"),
                drag_file_image_path=self._getting_started_image_path("getting_started", "drag_file_to_sound_button.png"),
                open_audio_device_options=self._open_audio_device_options,
                open_latest_version_page=self._open_latest_version_page,
                open_docs_page=self._open_getting_started_docs_page,
                open_options_page=self._open_options_dialog,
                open_about_window=self._open_about_window,
                parent=self,
            )
            self._getting_started_window.destroyed.connect(lambda _=None: self._clear_getting_started_window_ref())
        if not startup:
            self._getting_started_window.reset_to_first_page()
        self._getting_started_window.show()
        if startup:
            self._getting_started_window.raise_()
            self._getting_started_window.activateWindow()
        else:
            self._getting_started_window.raise_()
            self._getting_started_window.activateWindow()

    def _open_web_lyric_display(self, view_name: str) -> None:
        target = str(view_name or "").strip().lower()
        if target not in {"caption", "overhead", "banner", "vmixoverlay"}:
            return
        if not self._require_web_remote_enabled(tr("Web Lyric Display")):
            return
        base = self._web_remote_open_url().rstrip("/")
        url = QUrl(f"{base}/lyric/{target}/?ws_port={int(self._preferred_web_remote_ws_port())}&ws_path=/ws")
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(
                self,
                "Web Lyric Display Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{url.toString()}",
            )

    def _open_web_remote(self) -> None:
        if not self._require_web_remote_enabled(tr("Open Web Remote")):
            return
        url = QUrl(self._web_remote_open_url())
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(
                self,
                "Web Remote Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{url.toString()}",
            )

    def _require_web_remote_enabled(self, feature_name: str) -> bool:
        if self.web_remote_enabled:
            return True
        template = tr("Web Remote is not enabled. Please enable Web Remote for {feature} to work.")
        feature = str(feature_name or "").strip() or tr("Web Remote")
        self._show_playback_warning_banner(template.format(feature=feature))
        return False

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

    def _clear_audio_engine_insight_window_ref(self) -> None:
        self._audio_engine_insight_window = None

    def _clear_system_info_window_ref(self) -> None:
        self._system_info_window = None

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

    def _build_group_widget(self) -> QWidget:
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
        layout.addStretch(1)
        return panel

    def _build_page_widget(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
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

    def _build_sound_button_widget(self) -> QWidget:
        panel = QWidget()
        root = QVBoxLayout(panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.sound_button_stack = QStackedWidget(panel)
        root.addWidget(self.sound_button_stack, 1)

        self.sound_button_grid_widget = QFrame()
        self.sound_button_grid_widget.setFrameShape(QFrame.StyledPanel)
        self.sound_button_grid_layout = QGridLayout(self.sound_button_grid_widget)
        self.sound_button_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_button_grid_layout.setSpacing(1)
        self.sound_button_grid_scroll = QScrollArea(panel)
        self.sound_button_grid_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sound_button_grid_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sound_button_grid_scroll.setWidgetResizable(False)
        self.sound_button_grid_scroll.setWidget(self.sound_button_grid_widget)
        self.sound_button_stack.addWidget(self.sound_button_grid_scroll)

        self.sound_button_list_container = QWidget(panel)
        list_root = QVBoxLayout(self.sound_button_list_container)
        list_root.setContentsMargins(0, 0, 0, 0)
        list_root.setSpacing(2)
        self.sound_button_list_header = SoundButtonListHeaderRow(self)
        list_root.addWidget(self.sound_button_list_header, 0)
        self.sound_button_list_widget = QWidget()
        self.sound_button_list_layout = QVBoxLayout(self.sound_button_list_widget)
        self.sound_button_list_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_button_list_layout.setSpacing(2)
        self.sound_button_list_layout.addStretch(1)
        self.sound_button_list_scroll = QScrollArea(self.sound_button_list_container)
        self.sound_button_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sound_button_list_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.sound_button_list_scroll.setWidgetResizable(True)
        self.sound_button_list_scroll.setWidget(self.sound_button_list_widget)
        list_root.addWidget(self.sound_button_list_scroll, 1)
        self.sound_button_stack.addWidget(self.sound_button_list_container)

        root.addWidget(self._build_sound_button_legend_widget(), 0)

        self._rebuild_sound_button_panel()
        QTimer.singleShot(0, lambda: self._refresh_sound_button_panel_after_show(0))
        return panel

    def _refresh_sound_button_panel_after_show(self, attempt: int = 0) -> None:
        if self.sound_button_stack is None or self.sound_button_grid_scroll is None:
            return
        viewport_width = max(0, int(self.sound_button_grid_scroll.viewport().width()))
        if viewport_width <= 0:
            if attempt < 5:
                QTimer.singleShot(20, lambda attempt=attempt + 1: self._refresh_sound_button_panel_after_show(attempt))
            return
        self._rebuild_sound_button_panel()
        if attempt < 5:
            QTimer.singleShot(40, lambda attempt=attempt + 1: self._refresh_sound_button_panel_after_show(attempt))

    def _ensure_sound_button_widgets(self, count: int) -> None:
        target = max(0, int(count))
        while len(self.sound_buttons) < target:
            idx = len(self.sound_buttons)
            button = SoundButton(idx, self)
            button.pressed.connect(lambda slot=idx: self._on_sound_button_pressed(slot))
            button.released.connect(lambda slot=idx: self._on_sound_button_released(slot))
            button.clicked.connect(lambda _=False, slot=idx: self._on_sound_button_clicked(slot))
            self.sound_buttons.append(button)
        while len(self.sound_button_list_rows) < target:
            idx = len(self.sound_button_list_rows)
            row = SoundButtonListRow(idx, self)
            self.sound_button_list_rows.append(row)
        self._apply_sound_button_list_column_widths()

    def _sound_button_list_column_width_map(self) -> Dict[str, int]:
        widths = normalize_sound_button_list_column_widths(
            getattr(self, "sound_button_list_column_widths", list(DEFAULT_SOUND_BUTTON_LIST_COLUMN_WIDTHS))
        )
        self.sound_button_list_column_widths = widths
        return {
            key: widths[idx]
            for idx, key in enumerate(SOUND_BUTTON_LIST_COLUMN_KEYS)
            if idx < len(widths)
        }

    def _sound_button_list_hidden_column_set(self) -> set[str]:
        hidden = normalize_sound_button_list_hidden_columns(
            getattr(self, "sound_button_list_hidden_columns", list(DEFAULT_SOUND_BUTTON_LIST_HIDDEN_COLUMNS))
        )
        self.sound_button_list_hidden_columns = hidden
        return set(hidden)

    def _visible_sound_button_list_column_keys(self) -> List[str]:
        hidden = self._sound_button_list_hidden_column_set()
        return [key for key in SOUND_BUTTON_LIST_COLUMN_KEYS if key not in hidden]

    def _effective_sound_button_grid_columns(self, total_slots: Optional[int] = None, viewport_width: Optional[int] = None) -> int:
        resolved_total = self._effective_page_slot_count() if total_slots is None else max(1, int(total_slots))
        configured_columns = max(1, int(getattr(self, "sound_button_grid_columns", 8) or 8))
        if viewport_width is None and self.sound_button_grid_scroll is not None:
            viewport_width = int(self.sound_button_grid_scroll.viewport().width())
        available_width = max(0, int(viewport_width or 0))
        if available_width <= 0:
            return min(configured_columns, resolved_total)
        spacing = 1
        columns_that_fit = max(1, (available_width + spacing) // (SOUND_BUTTON_GRID_TARGET_WIDTH + spacing))
        return max(1, min(configured_columns, resolved_total, columns_that_fit))

    def _sound_button_list_content_width(self) -> int:
        widths = self._sound_button_list_column_width_map()
        visible_keys = self._visible_sound_button_list_column_keys()
        spacing = 6
        outer_margins = 12
        return outer_margins + sum(int(widths.get(key, 72)) for key in visible_keys) + (
            max(0, len(visible_keys) - 1) * spacing
        )

    def _effective_sound_button_list_width_map(self) -> Dict[str, int]:
        preferred = self._sound_button_list_column_width_map()
        visible_keys = self._visible_sound_button_list_column_keys()
        if not visible_keys:
            return preferred
        minimums = {key: int(SOUND_BUTTON_LIST_MIN_WIDTHS.get(key, 24)) for key in SOUND_BUTTON_LIST_COLUMN_KEYS}
        available_width = 0
        if self.sound_button_list_scroll is not None:
            available_width = max(0, int(self.sound_button_list_scroll.viewport().width()))
        if available_width <= 0:
            return preferred
        spacing = 6
        outer_margins = 12
        fixed_overhead = outer_margins + (max(0, len(visible_keys) - 1) * spacing)
        target_budget = max(0, available_width - fixed_overhead)
        preferred_total = sum(int(preferred.get(key, 72)) for key in visible_keys)
        minimum_total = sum(int(minimums.get(key, 24)) for key in visible_keys)
        if target_budget <= minimum_total:
            return minimums
        if target_budget <= preferred_total:
            shrinkable = {
                key: max(0, int(preferred.get(key, 72)) - int(minimums.get(key, 24)))
                for key in visible_keys
            }
            shrink_total = sum(shrinkable.values())
            required_shrink = preferred_total - target_budget
            widths = {key: int(preferred.get(key, 72)) for key in SOUND_BUTTON_LIST_COLUMN_KEYS}
            if shrink_total > 0 and required_shrink > 0:
                reductions: Dict[str, int] = {}
                for key in visible_keys:
                    reductions[key] = min(
                        shrinkable[key],
                        int(round((shrinkable[key] / shrink_total) * required_shrink)),
                    )
                applied = sum(reductions.values())
                if applied < required_shrink:
                    remainder = required_shrink - applied
                    for key in sorted(visible_keys, key=lambda name: shrinkable[name], reverse=True):
                        if remainder <= 0:
                            break
                        room = shrinkable[key] - reductions[key]
                        if room <= 0:
                            continue
                        extra = min(room, remainder)
                        reductions[key] += extra
                        remainder -= extra
                for key in visible_keys:
                    widths[key] = max(minimums[key], widths[key] - reductions[key])
            return widths
        widths = {key: int(preferred.get(key, 72)) for key in SOUND_BUTTON_LIST_COLUMN_KEYS}
        extra = target_budget - preferred_total
        elastic_keys = [key for key in ["title", "notes", "status"] if key in visible_keys]
        if extra > 0 and elastic_keys:
            share, remainder = divmod(extra, len(elastic_keys))
            for index, key in enumerate(elastic_keys):
                widths[key] += share + (1 if index < remainder else 0)
        return widths

    def _apply_sound_button_list_column_widths(self) -> None:
        widths = self._effective_sound_button_list_width_map()
        hidden_columns = self._sound_button_list_hidden_column_set()
        if isinstance(self.sound_button_list_header, SoundButtonListHeaderRow):
            self.sound_button_list_header.apply_column_widths(widths, hidden_columns)
        for row in getattr(self, "sound_button_list_rows", []):
            if isinstance(row, SoundButtonListRow):
                row.apply_column_widths(widths, hidden_columns)
        if self.sound_button_list_widget is not None:
            visible_keys = self._visible_sound_button_list_column_keys()
            content_width = 12 + sum(int(widths.get(key, 72)) for key in visible_keys) + (
                max(0, len(visible_keys) - 1) * 6
            )
            self.sound_button_list_widget.setMinimumWidth(content_width)
            self.sound_button_list_widget.resize(content_width, self.sound_button_list_widget.height())
            if self.sound_button_list_header is not None:
                self.sound_button_list_header.setMinimumWidth(content_width)
                self.sound_button_list_header.resize(content_width, self.sound_button_list_header.height())

    def _set_sound_button_list_column_widths(self, widths: object, *, persist: bool = True) -> None:
        self.sound_button_list_column_widths = normalize_sound_button_list_column_widths(widths)
        self._apply_sound_button_list_column_widths()
        if persist:
            save_settings = getattr(self, "_save_settings", None)
            if callable(save_settings):
                save_settings()

    def _set_sound_button_list_column_width_for_key(self, key: str, width: int, *, persist: bool = True) -> None:
        if key not in SOUND_BUTTON_LIST_COLUMN_KEYS:
            return
        widths = list(normalize_sound_button_list_column_widths(self.sound_button_list_column_widths))
        index = SOUND_BUTTON_LIST_COLUMN_KEYS.index(key)
        widths[index] = max(int(SOUND_BUTTON_LIST_MIN_WIDTHS.get(key, 8)), min(800, int(width)))
        self._set_sound_button_list_column_widths(widths, persist=persist)

    def _set_sound_button_list_hidden_columns(self, hidden_columns: object, *, persist: bool = True) -> None:
        self.sound_button_list_hidden_columns = normalize_sound_button_list_hidden_columns(hidden_columns)
        self._apply_sound_button_list_column_widths()
        if persist:
            save_settings = getattr(self, "_save_settings", None)
            if callable(save_settings):
                save_settings()

    def _show_sound_button_list_header_menu(self, global_pos) -> None:
        menu = QMenu(self)
        reset_action = QAction("Reset Column Widths", menu)
        reset_action.triggered.connect(
            lambda _=False: self._set_sound_button_list_column_widths(list(DEFAULT_SOUND_BUTTON_LIST_COLUMN_WIDTHS))
        )
        menu.addAction(reset_action)
        menu.exec_(global_pos)

    def _rebuild_sound_button_panel(self) -> None:
        if self.sound_button_stack is None or self.sound_button_grid_layout is None or self.sound_button_list_layout is None:
            return
        total_slots = self._effective_page_slot_count(self._current_page_slots())
        self._ensure_sound_button_widgets(total_slots)
        columns = self._effective_sound_button_grid_columns(total_slots)
        rows = self._runtime_sound_button_grid_rows()

        self._clear_layout_only(self.sound_button_grid_layout)
        for row in range(rows):
            self.sound_button_grid_layout.setRowStretch(row, 1)
        for col in range(columns):
            self.sound_button_grid_layout.setColumnStretch(col, 1)
        for idx in range(total_slots):
            row = idx // columns
            col = idx % columns
            button = self.sound_buttons[idx]
            button.slot_index = idx
            self.sound_button_grid_layout.addWidget(button, row, col)
            button.show()
        self._update_sound_button_grid_geometry(total_slots, columns, rows)

        while self.sound_button_list_layout.count():
            item = self.sound_button_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self.sound_button_list_layout.setSpacing(2)
        page = self._current_page_slots()
        hide_empty = bool(getattr(self, "sound_button_list_hide_empty", False))
        for idx in range(total_slots):
            slot = self._slot_at(page, idx)
            if hide_empty and not slot.assigned and not slot.title and not slot.marker:
                continue
            row = self.sound_button_list_rows[idx]
            row.slot_index = idx
            self.sound_button_list_layout.addWidget(row)
            row.show()
        self.sound_button_list_layout.addStretch(1)
        self._apply_sound_button_list_column_widths()

        if str(getattr(self, "sound_button_view_mode", "grid")) == "list":
            self.sound_button_stack.setCurrentWidget(self.sound_button_list_container)
        else:
            self.sound_button_stack.setCurrentWidget(self.sound_button_grid_scroll)

    def _update_sound_button_grid_geometry(
        self,
        total_slots: Optional[int] = None,
        columns: Optional[int] = None,
        rows: Optional[int] = None,
    ) -> None:
        if self.sound_button_grid_widget is None or self.sound_button_grid_scroll is None:
            return
        resolved_total = self._effective_page_slot_count() if total_slots is None else max(1, int(total_slots))
        resolved_columns = self._effective_sound_button_grid_columns(
            resolved_total,
            int(self.sound_button_grid_scroll.viewport().width()),
        ) if columns is None else max(1, int(columns))
        resolved_visible_rows = self._runtime_sound_button_grid_rows() if rows is None else max(1, int(rows))
        actual_rows = max(resolved_visible_rows, (resolved_total + resolved_columns - 1) // resolved_columns)
        viewport_width = max(0, self.sound_button_grid_scroll.viewport().width())
        grid_layout = self.sound_button_grid_layout
        if grid_layout is None:
            return
        if viewport_width <= 0:
            return
        rendered_columns = 0
        try:
            rendered_columns = max(
                0,
                max(
                    (
                        int(grid_layout.getItemPosition(index)[1]) + int(grid_layout.getItemPosition(index)[3])
                        for index in range(grid_layout.count())
                    ),
                    default=0,
                ),
            )
        except Exception:
            rendered_columns = 0
        if rendered_columns != resolved_columns:
            self._rebuild_sound_button_panel()
            return
        margins = grid_layout.contentsMargins()
        spacing = max(0, int(grid_layout.horizontalSpacing()))
        total_spacing = max(0, resolved_columns - 1) * spacing
        natural_width = margins.left() + margins.right() + total_spacing + (resolved_columns * SOUND_BUTTON_GRID_TARGET_WIDTH)
        usable_width = max(0, viewport_width - margins.left() - margins.right() - total_spacing)
        if resolved_columns <= 0:
            return
        if viewport_width > 0:
            if viewport_width >= natural_width:
                cell_width = max(SOUND_BUTTON_GRID_TARGET_WIDTH, usable_width // resolved_columns)
            else:
                cell_width = max(SOUND_BUTTON_GRID_MIN_WIDTH, usable_width // resolved_columns)
        else:
            cell_width = SOUND_BUTTON_GRID_TARGET_WIDTH
        target_width = margins.left() + margins.right() + total_spacing + (resolved_columns * cell_width)
        button_height = 84
        for col in range(resolved_columns):
            grid_layout.setColumnMinimumWidth(col, cell_width)
        content_height = max(1, actual_rows) * button_height
        self.sound_button_grid_widget.setMinimumSize(target_width, content_height)
        self.sound_button_grid_widget.resize(target_width, content_height)

    def _build_main_button_widget(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self._main_control_grid_layout = QGridLayout()
        self._main_control_grid_layout.setContentsMargins(0, 0, 0, 0)
        self._main_control_grid_layout.setSpacing(2)
        self._main_control_buttons_ui: Dict[str, QPushButton] = {}
        self._control_button_instances: Dict[str, List[QPushButton]] = {}
        self._control_button_clones: List[QPushButton] = []
        for text in WINDOW_LAYOUT_MAIN_ORDER:
            btn = QPushButton(text)
            btn.setMinimumHeight(42)
            if text == "Pause":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                btn.clicked.connect(self._toggle_pause)
            elif text == "STOP":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
                btn.clicked.connect(self._stop_playback)
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
            elif text == "Vocal Removed":
                btn.setCheckable(True)
                btn.setToolTip("")
                btn.clicked.connect(self._toggle_global_vocal_removed_mode)
            elif text == "Companion Bypass":
                btn.setCheckable(True)
                btn.setChecked(bool(self.companion_bypass))
                btn.clicked.connect(self._toggle_companion_bypass)
            elif text == "Internal Bypass":
                btn.setCheckable(True)
                btn.setChecked(bool(self.internal_bypass))
                btn.clicked.connect(self._toggle_internal_bypass)
            if text in {"Pause", "STOP", "Next", "Loop", "Reset Page", "Talk", "Cue", "Play List", "Shuffle", "Rapid Fire", "Multi-Play", "Button Drag", "Vocal Removed", "Companion Bypass", "Internal Bypass"}:
                self.control_buttons[text] = btn
            self._main_control_buttons_ui[text] = btn
            btn.toggled.connect(lambda _checked=False, key=text: self._sync_control_button_instances(key))
            btn.clicked.connect(lambda _checked=False, key=text: self._sync_control_button_instances(key))
        layout.addLayout(self._main_control_grid_layout)
        return panel

    def _build_status_display_widget(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        layout.addWidget(self._build_main_warning_banner_panel(), 0)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        self.page_status.setStyleSheet("font-size: 13pt; color: #0A29E0; font-weight: bold;")
        self.page_status.setWordWrap(False)
        page_status_scroll = QScrollArea()
        page_status_scroll.setWidgetResizable(True)
        page_status_scroll.setFrameShape(QFrame.NoFrame)
        page_status_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page_status_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page_status_scroll.setWidget(self.page_status)
        page_status_scroll.setMinimumHeight(30)
        page_status_scroll.setMaximumHeight(34)
        status_row.addWidget(page_status_scroll, 1)
        layout.addLayout(status_row)
        self.now_playing_label.set_now_playing_text("NOW PLAYING:", "")
        self.now_playing_label.setVisible(True)
        self.now_playing_label.setFixedHeight(40)
        layout.addWidget(self.now_playing_label)
        self.main_lyric_label.set_now_playing_text("LYRIC:", "")
        self.main_lyric_label.setVisible(True)
        self.main_lyric_label.setFixedHeight(42)
        self.main_lyric_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lyric_row = QHBoxLayout()
        lyric_row.setContentsMargins(0, 0, 0, 0)
        lyric_row.setSpacing(6)
        lyric_row.addWidget(self.main_lyric_label, 1)
        self.lyric_navigator_button = QPushButton("Lyric Navigator")
        self.lyric_navigator_button.setMinimumHeight(36)
        self.lyric_navigator_button.clicked.connect(self._open_lyric_navigator)
        lyric_row.addWidget(self.lyric_navigator_button, 0)
        self.lyric_blank_toggle_button = QPushButton("Blank Lyric")
        self.lyric_blank_toggle_button.setMinimumHeight(36)
        self.lyric_blank_toggle_button.setCheckable(True)
        self.lyric_blank_toggle_button.clicked.connect(self._toggle_lyric_force_blank)
        lyric_row.addWidget(self.lyric_blank_toggle_button, 0)
        self._sync_lyric_display_controls()
        layout.addLayout(lyric_row)
        layout.addStretch(1)
        return panel

    def _build_fade_button_widget(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self._fade_control_grid_layout = QGridLayout()
        self._fade_control_grid_layout.setContentsMargins(0, 0, 0, 0)
        self._fade_control_grid_layout.setSpacing(2)
        self._fade_control_buttons_ui: Dict[str, QPushButton] = {}
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
            self._fade_control_buttons_ui[label] = b
            b.toggled.connect(lambda _checked=False, key=label: self._sync_control_button_instances(key))
            b.clicked.connect(lambda _checked=False, key=label: self._sync_control_button_instances(key))
        layout.addLayout(self._fade_control_grid_layout)
        return panel

    def _build_meter_volume_widget(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        meter_row = QHBoxLayout()
        meter_labels = QVBoxLayout()
        meter_labels.addWidget(QLabel("dBFS"))
        meter_labels.addWidget(QLabel("Left"))
        meter_labels.addWidget(QLabel("Right"))
        meter_row.addLayout(meter_labels)

        meters = QVBoxLayout()
        meters.setSpacing(3)
        meters.addWidget(self.meter_scale)
        meters.addWidget(self.left_meter)
        meters.addWidget(self.right_meter)
        meter_row.addLayout(meters, 1)
        layout.addLayout(meter_row)

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("Volume"))
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(90)
        self.volume_slider.setFixedWidth(140)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_row.addWidget(self.volume_slider)
        volume_row.addStretch(1)
        layout.addLayout(volume_row)
        layout.addStretch(1)
        return panel

    def _build_time_transport_widget(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

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
        layout.addLayout(times)

        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: white;")
        self.progress_label.setMinimumHeight(28)
        self.progress_label.set_display_mode(self.main_progress_display_mode)
        self.progress_label.setVisible(True)
        layout.addWidget(self.progress_label)

        transport_row = QHBoxLayout()
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.valueChanged.connect(self._on_seek_value_changed)
        transport_row.addWidget(self.seek_slider, 1)
        layout.addLayout(transport_row)

        jog_meta_row = QHBoxLayout()
        self.jog_percent_label.setAlignment(Qt.AlignCenter)
        self.jog_out_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        jog_meta_row.addWidget(self.jog_in_label)
        jog_meta_row.addStretch(1)
        jog_meta_row.addWidget(self.jog_percent_label)
        jog_meta_row.addStretch(1)
        jog_meta_row.addWidget(self.jog_out_label)
        layout.addLayout(jog_meta_row)
        return panel

    @staticmethod
    def _clear_layout_only(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue

    def _make_control_button_clone(self, key: str) -> QPushButton:
        primary = self.control_buttons.get(key)
        if primary is None:
            primary = self._main_control_buttons_ui.get(key)
        if primary is None:
            primary = self._fade_control_buttons_ui.get(key)
        btn = QPushButton(key)
        if primary is None:
            return btn
        btn.setCheckable(primary.isCheckable())
        btn.setToolTip(primary.toolTip())
        if primary.icon().isNull() is False:
            btn.setIcon(primary.icon())
        btn.clicked.connect(lambda _checked=False, token=key: self._click_named_button(token))
        return btn

    def _click_named_button(self, key: str) -> None:
        primary = self.control_buttons.get(key)
        if primary is None:
            primary = self._main_control_buttons_ui.get(key)
        if primary is None:
            primary = self._fade_control_buttons_ui.get(key)
        if primary is None or (not primary.isEnabled()):
            return
        primary.click()

    def _sync_control_button_instances(self, key: Optional[str] = None) -> None:
        keys = [key] if key else list(self._control_button_instances.keys())
        for token in keys:
            if not token:
                continue
            primary = self.control_buttons.get(token)
            if primary is None:
                primary = self._main_control_buttons_ui.get(token)
            if primary is None:
                primary = self._fade_control_buttons_ui.get(token)
            if primary is None:
                continue
            for inst in self._control_button_instances.get(token, []):
                if inst is primary:
                    continue
                inst.blockSignals(True)
                inst.setCheckable(primary.isCheckable())
                if primary.isCheckable():
                    inst.setChecked(primary.isChecked())
                inst.setEnabled(primary.isEnabled())
                inst.setText(primary.text())
                inst.setToolTip(primary.toolTip())
                inst.setStyleSheet(primary.styleSheet())
                inst.setIcon(primary.icon())
                inst.blockSignals(False)
        try:
            self._refresh_launchpad_feedback(force=False)
        except Exception:
            pass

    def _apply_top_control_layout(self) -> None:
        if not hasattr(self, "_main_control_grid_layout") or not hasattr(self, "_fade_control_grid_layout"):
            return
        normalized = normalize_window_layout(self.window_layout)
        self.window_layout = normalized
        self._clear_layout_only(self._main_control_grid_layout)
        self._clear_layout_only(self._fade_control_grid_layout)
        self._control_button_instances = {key: [] for key in [*WINDOW_LAYOUT_MAIN_ORDER, *WINDOW_LAYOUT_FADE_ORDER]}
        for clone in list(self._control_button_clones):
            clone.setParent(None)
            clone.deleteLater()
        self._control_button_clones = []

        for key, btn in self._main_control_buttons_ui.items():
            btn.hide()
            self._control_button_instances.setdefault(key, []).append(btn)
        for key, btn in self._fade_control_buttons_ui.items():
            btn.hide()
            self._control_button_instances.setdefault(key, []).append(btn)

        all_keys = [*WINDOW_LAYOUT_MAIN_ORDER, *WINDOW_LAYOUT_FADE_ORDER]
        used_main: Dict[str, int] = {}
        for item in list(normalized.get("main", [])):
            if not isinstance(item, dict):
                continue
            key = str(item.get("button", "")).strip()
            if key not in all_keys:
                continue
            use_count = used_main.get(key, 0)
            used_main[key] = use_count + 1
            if use_count == 0:
                btn = self._main_control_buttons_ui.get(key)
                if btn is None:
                    btn = self._fade_control_buttons_ui.get(key)
            else:
                btn = self._make_control_button_clone(key)
                self._control_button_clones.append(btn)
                self._control_button_instances.setdefault(key, []).append(btn)
            if btn is None:
                continue
            btn.setMinimumHeight(42 * max(1, int(item.get("h", 1))))
            self._main_control_grid_layout.addWidget(
                btn,
                int(item.get("y", 0)),
                int(item.get("x", 0)),
                int(item.get("h", 1)),
                int(item.get("w", 1)),
            )
            btn.show()

        used_fade: Dict[str, int] = {}
        for item in list(normalized.get("fade", [])):
            if not isinstance(item, dict):
                continue
            key = str(item.get("button", "")).strip()
            if key not in all_keys:
                continue
            use_count = used_fade.get(key, 0)
            used_fade[key] = use_count + 1
            if use_count == 0:
                btn = self._fade_control_buttons_ui.get(key)
                if btn is None:
                    btn = self._main_control_buttons_ui.get(key)
            else:
                btn = self._make_control_button_clone(key)
                self._control_button_clones.append(btn)
                self._control_button_instances.setdefault(key, []).append(btn)
            if btn is None:
                continue
            btn.setMinimumHeight(38 * max(1, int(item.get("h", 1))))
            self._fade_control_grid_layout.addWidget(
                btn,
                int(item.get("y", 0)),
                int(item.get("x", 0)),
                int(item.get("h", 1)),
                int(item.get("w", 1)),
            )
            btn.show()
        self._sync_control_button_instances()

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

    def resizeEvent(self, event) -> None:
        QMainWindow.resizeEvent(self, event)
        self._update_page_list_item_heights()
        update_grid_geometry = getattr(self, "_update_sound_button_grid_geometry", None)
        if callable(update_grid_geometry):
            update_grid_geometry()
        update_list_widths = getattr(self, "_apply_sound_button_list_column_widths", None)
        if callable(update_list_widths):
            update_list_widths()
        if self._lock_screen_overlay is not None:
            self._lock_screen_overlay.sync_geometry(rebuild_targets=self._ui_locked)

    def eventFilter(self, obj, event) -> bool:
        if obj is self and bool(getattr(self, "window_layout_locked", False)):
            if event.type() in {
                QEvent.MouseButtonPress,
                QEvent.MouseButtonRelease,
                QEvent.MouseMove,
                QEvent.MouseButtonDblClick,
            }:
                if self._is_separator_drag_event(event.pos()):
                    return True
        if obj is self.page_list.viewport():
            if event.type() == QEvent.Resize:
                self._update_page_list_item_heights()
            elif event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if 0 <= row < PAGE_COUNT:
                        self._page_drag_source_key = (self.current_group, row)
                        self._page_drag_start_pos = event.pos()
                    else:
                        self._page_drag_source_key = None
                        self._page_drag_start_pos = None
            elif event.type() == QEvent.MouseMove:
                if (
                    self._page_drag_start_pos is not None
                    and (event.buttons() & Qt.LeftButton)
                    and self._is_button_drag_enabled()
                    and self._page_drag_source_key is not None
                ):
                    if (event.pos() - self._page_drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                        source_group, source_page = self._page_drag_source_key
                        if source_group == self.current_group:
                            self._start_page_button_drag(source_page)
                        self._page_drag_start_pos = None
                        self._page_drag_source_key = None
                        return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._page_drag_start_pos = None
                self._page_drag_source_key = None
            elif event.type() == QEvent.DragEnter:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
                if self._can_accept_page_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.DragMove:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if self._handle_drag_over_page(row):
                        event.acceptProposedAction()
                        return True
                if self._can_accept_page_button_drop(event.mimeData()):
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if self._handle_drag_over_page(row, require_created=False):
                        event.acceptProposedAction()
                        return True
            elif event.type() == QEvent.Drop:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
                if self._can_accept_page_button_drop(event.mimeData()):
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if self._handle_page_button_drop(row, event.mimeData()):
                        event.acceptProposedAction()
                        return True
        return QMainWindow.eventFilter(self, obj, event)
