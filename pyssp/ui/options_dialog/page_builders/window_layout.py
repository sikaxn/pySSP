from __future__ import annotations

from ..shared import *
from ..widgets import *


class WindowLayoutPageMixin:
    def _build_window_layout_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        tabs = QTabWidget(page)
        tabs.addTab(self._build_sound_button_layout_tab(), "Sound Buttons")
        tabs.addTab(self._build_button_layout_tab(), "Button Layout")
        layout.addWidget(tabs, 1)
        return page

    def _build_sound_button_layout_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        mode_group = QGroupBox("Sound Button View")
        mode_layout = QVBoxLayout(mode_group)
        self.sound_button_view_grid_radio = QRadioButton("Show sound buttons as grid")
        self.sound_button_view_list_radio = QRadioButton("Show sound buttons as list")
        if str(getattr(self, "_sound_button_view_mode", "grid")) == "list":
            self.sound_button_view_list_radio.setChecked(True)
        else:
            self.sound_button_view_grid_radio.setChecked(True)
        mode_layout.addWidget(self.sound_button_view_grid_radio)
        mode_layout.addWidget(self.sound_button_view_list_radio)
        layout.addWidget(mode_group)

        grid_group = QGroupBox("Grid Size")
        grid_layout = QFormLayout(grid_group)
        self.sound_button_grid_columns_spin = QSpinBox(grid_group)
        self.sound_button_grid_columns_spin.setRange(1, 512)
        self.sound_button_grid_columns_spin.setValue(int(getattr(self, "_sound_button_grid_columns", 8)))
        self.sound_button_grid_rows_spin = QSpinBox(grid_group)
        self.sound_button_grid_rows_spin.setRange(1, 512)
        self.sound_button_grid_rows_spin.setValue(int(getattr(self, "_sound_button_grid_rows", 6)))
        self.sound_button_page_slot_cap_spin = QSpinBox(grid_group)
        self.sound_button_page_slot_cap_spin.setRange(1, 4096)
        self.sound_button_page_slot_cap_spin.setValue(int(getattr(self, "_sound_button_page_slot_cap", 48)))
        grid_layout.addRow("Columns", self.sound_button_grid_columns_spin)
        grid_layout.addRow("Rows", self.sound_button_grid_rows_spin)
        grid_layout.addRow("Page Slot Cap", self.sound_button_page_slot_cap_spin)
        layout.addWidget(grid_group)

        self.sound_button_list_hide_empty_checkbox = QCheckBox("Hide empty sound buttons in list view")
        self.sound_button_list_hide_empty_checkbox.setChecked(bool(getattr(self, "_sound_button_list_hide_empty", False)))
        layout.addWidget(self.sound_button_list_hide_empty_checkbox)

        list_columns_group = QGroupBox("List View Columns")
        list_columns_layout = QGridLayout(list_columns_group)
        self.sound_button_list_column_checkboxes = {}
        hidden_columns = set(getattr(self, "_sound_button_list_hidden_columns", []))
        for index, key in enumerate(SOUND_BUTTON_LIST_COLUMN_KEYS):
            checkbox = QCheckBox(f"Show {SOUND_BUTTON_LIST_COLUMN_LABELS[key]}")
            checkbox.setChecked(key not in hidden_columns)
            self.sound_button_list_column_checkboxes[key] = checkbox
            list_columns_layout.addWidget(checkbox, index // 2, index % 2)
        layout.addWidget(list_columns_group)
        layout.addStretch(1)
        return page

    def _build_button_layout_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        tip = QLabel("Drag blocks to move buttons. Drag bottom-right corner to resize. Layout is snapped to the grid.")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        main_group = QGroupBox("Main Buttons (4 x 4)")
        main_layout = QVBoxLayout(main_group)
        self.window_layout_main_editor = _GridLayoutCanvas(
            "main",
            WINDOW_LAYOUT_MAIN_GRID_COLS,
            WINDOW_LAYOUT_MAIN_GRID_ROWS,
            main_group,
        )
        self.window_layout_main_editor.setMinimumHeight(280)
        self.window_layout_main_editor.set_items(list(self._window_layout.get("main", [])))
        self.window_layout_main_editor.changed.connect(self._capture_window_layout_from_editor)
        self.window_layout_main_editor.dropped.connect(
            lambda payload, x, y: self._handle_window_layout_drop("main", payload, x, y)
        )
        main_layout.addWidget(self.window_layout_main_editor)
        layout.addWidget(main_group, 1)

        fade_group = QGroupBox("Fade Buttons (6 x 1)")
        fade_layout = QVBoxLayout(fade_group)
        self.window_layout_fade_editor = _GridLayoutCanvas(
            "fade",
            WINDOW_LAYOUT_FADE_GRID_COLS,
            WINDOW_LAYOUT_FADE_GRID_ROWS,
            fade_group,
        )
        self.window_layout_fade_editor.setMinimumHeight(96)
        self.window_layout_fade_editor.set_items(list(self._window_layout.get("fade", [])))
        self.window_layout_fade_editor.changed.connect(self._capture_window_layout_from_editor)
        self.window_layout_fade_editor.dropped.connect(
            lambda payload, x, y: self._handle_window_layout_drop("fade", payload, x, y)
        )
        fade_layout.addWidget(self.window_layout_fade_editor)
        layout.addWidget(fade_group, 0)

        available_group = QGroupBox("Available Buttons")
        available_layout = QVBoxLayout(available_group)
        self.window_layout_show_all_checkbox = QCheckBox("Show all buttons")
        self.window_layout_show_all_checkbox.setChecked(bool(self._window_layout.get("show_all_available", False)))
        self.window_layout_show_all_checkbox.toggled.connect(self._on_window_layout_show_all_toggled)
        available_layout.addWidget(self.window_layout_show_all_checkbox)
        button_row = QHBoxLayout()
        self.window_layout_clear_all_btn = QPushButton("Clear All")
        self.window_layout_clear_all_btn.clicked.connect(self._clear_all_window_layout_buttons)
        button_row.addWidget(self.window_layout_clear_all_btn)
        button_row.addStretch(1)
        available_layout.addLayout(button_row)
        self.window_layout_available_list = _AvailableButtonsList()
        self.window_layout_available_list.setMinimumHeight(120)
        self.window_layout_available_list.dropped.connect(
            lambda payload: self._handle_window_layout_drop("available", payload, -1, -1)
        )
        available_layout.addWidget(self.window_layout_available_list)
        layout.addWidget(available_group, 0)

        self._refresh_window_layout_available_list()
        layout.addStretch(1)
        return page

