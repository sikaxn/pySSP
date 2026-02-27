from __future__ import annotations

import os
from typing import Callable, List, Optional

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)
from pyssp.i18n import localize_widget_tree


class SearchWindow(QDialog):
    def __init__(self, parent=None, language: str = "en") -> None:
        super().__init__(parent)
        self.setWindowTitle("Find Sound File")
        self.resize(860, 520)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)

        self._search_handler: Optional[Callable[[str], List[dict]]] = None
        self._goto_handler: Optional[Callable[[dict], None]] = None
        self._play_handler: Optional[Callable[[dict], None]] = None
        self._double_click_action = "find_highlight"

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Keywords"))
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Type words from title or file path")
        input_row.addWidget(self.query_edit, 1)
        root.addLayout(input_row)

        self.results_list = QListWidget()
        root.addWidget(self.results_list, 1)

        self.status_label = QLabel("Enter keywords and click Search.")
        root.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.goto_btn = QPushButton("Go To Selected")
        self.play_btn = QPushButton("Play")
        self.close_btn = QPushButton("Close")
        button_row.addWidget(self.goto_btn)
        button_row.addWidget(self.play_btn)
        button_row.addWidget(self.close_btn)
        root.addLayout(button_row)

        self.query_edit.textChanged.connect(lambda _text: self.run_search())
        self.query_edit.installEventFilter(self)
        self.results_list.installEventFilter(self)
        self.goto_btn.clicked.connect(self.go_to_selected)
        self.play_btn.clicked.connect(self.play_selected)
        self.results_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.close_btn.clicked.connect(self.close)
        localize_widget_tree(self, language)

    def set_handlers(
        self,
        search_handler: Callable[[str], List[dict]],
        goto_handler: Callable[[dict], None],
        play_handler: Callable[[dict], None],
    ) -> None:
        self._search_handler = search_handler
        self._goto_handler = goto_handler
        self._play_handler = play_handler

    def focus_query(self) -> None:
        self.query_edit.setFocus()
        self.query_edit.selectAll()

    def set_double_click_action(self, action: str) -> None:
        if action in {"find_highlight", "play_highlight"}:
            self._double_click_action = action
        else:
            self._double_click_action = "find_highlight"

    def run_search(self) -> None:
        if self._search_handler is None:
            return
        query = self.query_edit.text().strip()
        self.results_list.clear()
        if not query:
            self.status_label.setText("Enter at least one keyword.")
            return
        matches = self._search_handler(query)
        for match in matches:
            page_label = "Cue" if match["group"] == "Q" else f"{match['group']}:{match['page'] + 1}"
            title = match["title"] or os.path.splitext(os.path.basename(match["file_path"]))[0]
            display = f"[{page_label} #{match['slot'] + 1}] {title}\n{match['file_path']}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, match)
            self.results_list.addItem(item)
        if matches:
            self.results_list.setCurrentRow(0)
        self.status_label.setText(f"{len(matches)} match(es).")

    def go_to_selected(self) -> bool:
        if self._goto_handler is None:
            return False
        match = self._selected_match()
        if match is None:
            return False
        self._goto_handler(match)
        self._return_to_main_window()
        return True

    def play_selected(self) -> bool:
        if self._play_handler is None:
            return False
        match = self._selected_match()
        if match is None:
            return False
        self._play_handler(match)
        self._return_to_main_window()
        return True

    def activate_selected_by_setting(self) -> bool:
        if self._double_click_action == "play_highlight":
            return self.play_selected()
        return self.go_to_selected()

    def select_result_delta(self, delta: int) -> bool:
        count = int(self.results_list.count())
        if count <= 0:
            return False
        current = int(self.results_list.currentRow())
        if current < 0:
            next_row = 0 if int(delta) >= 0 else (count - 1)
        else:
            next_row = (current + int(delta)) % count
        self.results_list.setCurrentRow(next_row)
        return True

    def _on_item_double_clicked(self, _item) -> None:
        self.activate_selected_by_setting()

    def _selected_match(self) -> Optional[dict]:
        item = self.results_list.currentItem()
        if item is None:
            return None
        match = item.data(Qt.UserRole)
        if not isinstance(match, dict):
            return None
        return match

    def _return_to_main_window(self) -> None:
        self.hide()
        parent = self.parentWidget()
        if parent is not None:
            parent.raise_()
            parent.activateWindow()
            parent.setFocus()

    def eventFilter(self, obj, event) -> bool:
        if event.type() != QEvent.KeyPress:
            return super().eventFilter(obj, event)
        key = int(event.key())
        mods = event.modifiers()
        if QKeySequence(int(mods) | key).matches(QKeySequence.Find):
            self.focus_query()
            return True
        if key in {Qt.Key_Return, Qt.Key_Enter} and mods == Qt.NoModifier:
            self.activate_selected_by_setting()
            return True
        if obj is self.query_edit and key in {Qt.Key_Up, Qt.Key_Down}:
            self.select_result_delta(-1 if key == Qt.Key_Up else 1)
            return True
        return super().eventFilter(obj, event)
