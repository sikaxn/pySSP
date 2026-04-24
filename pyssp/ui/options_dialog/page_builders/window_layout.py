from __future__ import annotations

from ..shared import *
from ..widgets import *


class WindowLayoutPageMixin:
    def _build_window_layout_page(self) -> QWidget:
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

        fade_group = QGroupBox("Fade Buttons (3 x 1)")
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

