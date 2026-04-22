from __future__ import annotations

from typing import Callable, Dict, List

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AudioEngineInsightDialog(QDialog):
    def __init__(self, snapshot_provider: Callable[[], dict], parent=None) -> None:
        super().__init__(parent)
        self._snapshot_provider = snapshot_provider
        self._current_snapshot: dict = {}
        self._legacy_players: Dict[str, dict] = {}
        self.setWindowTitle("Audio Engine Insight")
        self.resize(980, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("Live audio engine player list and runtime details")
        title.setStyleSheet("QLabel{font-size:13pt;font-weight:bold;}")
        root.addWidget(title)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("QLabel{color:#50565D;}")
        self._keep_legacy_checkbox = QCheckBox("Keep Legacy", self)
        self._keep_legacy_checkbox.toggled.connect(self._on_keep_legacy_toggled)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        controls.addWidget(self._status_label, 1)
        controls.addWidget(self._keep_legacy_checkbox)
        controls.addWidget(refresh_button)
        root.addLayout(controls)

        splitter = QSplitter(self)
        splitter.setChildrenCollapsible(False)

        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(QLabel("Players"))
        self._player_list = QListWidget(self)
        self._player_list.currentRowChanged.connect(self._on_player_changed)
        left_layout.addWidget(self._player_list, 1)
        splitter.addWidget(left_panel)

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        self._detail_table = QTableWidget(0, 2, self)
        self._detail_table.setHorizontalHeaderLabels(["Field", "Value"])
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._detail_table.setSelectionMode(QTableWidget.NoSelection)
        self._detail_table.horizontalHeader().setStretchLastSection(True)
        self._detail_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        right_layout.addWidget(self._detail_table, 1)
        splitter.addWidget(right_panel)
        splitter.setSizes([280, 640])

        root.addWidget(splitter, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def refresh(self) -> None:
        current_row = self._player_list.currentRow()
        try:
            snapshot = self._snapshot_provider() or {}
        except Exception as exc:
            snapshot = {
                "summary": [("error", f"Audio engine insight failed: {exc}")],
                "players": [],
            }
        self._current_snapshot = self._merge_legacy_players(snapshot)
        self._rebuild_player_list()
        player_count = len(list(self._current_snapshot.get("players", [])))
        legacy_count = sum(1 for player in self._current_snapshot.get("players", []) if player.get("is_legacy"))
        self._status_label.setText(f"Auto refresh: 500 ms | Players: {player_count} | Legacy: {legacy_count}")
        if self._player_list.count() <= 0:
            self._populate_detail_table(list(self._current_snapshot.get("summary", [])))
            return
        if current_row < 0 or current_row >= self._player_list.count():
            current_row = 0
        self._player_list.setCurrentRow(current_row)
        self._show_player_details(current_row)

    def _on_keep_legacy_toggled(self, checked: bool) -> None:
        if not checked:
            self._legacy_players.clear()
        self.refresh()

    def _player_identity(self, player: dict) -> str:
        runtime_id = player.get("runtime_id")
        if runtime_id not in {None, "", "inactive"}:
            return f"runtime:{runtime_id}"
        return f"object:{player.get('object_id', '')}"

    def _merge_legacy_players(self, snapshot: dict) -> dict:
        current_players = list(snapshot.get("players", []))
        merged_players: List[dict] = []
        seen: set[str] = set()

        for player in current_players:
            item = dict(player)
            item["is_legacy"] = False
            identity = self._player_identity(item)
            item["_identity"] = identity
            self._legacy_players[identity] = dict(item)
            seen.add(identity)
            merged_players.append(item)

        if self._keep_legacy_checkbox.isChecked():
            for identity, player in list(self._legacy_players.items()):
                if identity in seen:
                    continue
                legacy = dict(player)
                legacy["is_legacy"] = True
                legacy["state"] = "closed"
                details = list(legacy.get("details", []))
                details.insert(0, ("legacy_status", "closed / retained in insight"))
                legacy["details"] = details
                merged_players.append(legacy)
        else:
            self._legacy_players = {identity: self._legacy_players[identity] for identity in seen if identity in self._legacy_players}

        merged = dict(snapshot)
        merged["players"] = merged_players
        return merged

    def _rebuild_player_list(self) -> None:
        players = list(self._current_snapshot.get("players", []))
        self._player_list.blockSignals(True)
        self._player_list.clear()
        for player in players:
            title = str(player.get("title") or "").strip()
            state = str(player.get("state") or "unknown").strip()
            label = str(player.get("label") or "player").strip()
            runtime_id = player.get("runtime_id")
            suffix = f" | {title}" if title else ""
            runtime_text = "inactive" if runtime_id in {None, ""} else str(runtime_id)
            legacy = bool(player.get("is_legacy"))
            item = QListWidgetItem(f"{label} [{state}] #{runtime_text}{suffix}")
            if legacy:
                item.setForeground(QColor("#8A4F00"))
                item.setBackground(QColor("#FFF1D6"))
            self._player_list.addItem(item)
        self._player_list.blockSignals(False)

    def _on_player_changed(self, row: int) -> None:
        self._show_player_details(row)

    def _show_player_details(self, row: int) -> None:
        players = list(self._current_snapshot.get("players", []))
        if row < 0 or row >= len(players):
            self._populate_detail_table(list(self._current_snapshot.get("summary", [])))
            return
        player = players[row]
        rows = [("selected_player", player.get("label", "player"))]
        rows.append(("selected_state", player.get("state", "unknown")))
        rows.append(("legacy_row", bool(player.get("is_legacy"))))
        rows.extend(list(self._current_snapshot.get("summary", [])))
        rows.extend(list(player.get("details", [])))
        self._populate_detail_table(rows)

    def _populate_detail_table(self, rows: List[tuple]) -> None:
        self._detail_table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            if len(entry) >= 2:
                key, value = entry[0], entry[1]
            else:
                key, value = "", ""
            key_item = QTableWidgetItem(str(key))
            value_item = QTableWidgetItem(str(value))
            self._detail_table.setItem(row_index, 0, key_item)
            self._detail_table.setItem(row_index, 1, value_item)
        self._detail_table.resizeColumnToContents(0)
