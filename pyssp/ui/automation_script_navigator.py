from __future__ import annotations

import os
from typing import Callable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.automation_script import (
    AutomationScriptCue,
    automation_script_cue_command_summary,
    load_automation_script,
)
from pyssp.i18n import localize_widget_tree, tr
from pyssp.lyrics import parse_lyric_file


class AutomationScriptNavigatorWindow(QWidget):
    def __init__(
        self,
        *,
        on_seek_to_ms: Callable[[int], None],
        show_lyric_default: bool = False,
        on_show_lyric_changed: Optional[Callable[[bool], None]] = None,
        companion_bypass: bool = False,
        internal_bypass: bool = False,
        on_companion_bypass_changed: Optional[Callable[[bool], None]] = None,
        on_internal_bypass_changed: Optional[Callable[[bool], None]] = None,
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(tr("Automation Script Navigator"))
        self.resize(860, 560)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._on_seek_to_ms = on_seek_to_ms
        self._on_show_lyric_changed = on_show_lyric_changed
        self._on_companion_bypass_changed = on_companion_bypass_changed
        self._on_internal_bypass_changed = on_internal_bypass_changed
        self._cache_script_path: str = ""
        self._cache_script_mtime: float = -1.0
        self._cache_lyric_path: str = ""
        self._cache_lyric_mtime: float = -1.0
        self._cache_rows: List[dict] = []
        self._cache_error: str = ""
        self._rows: List[dict] = []
        self._current_script_path: str = ""
        self._current_lyric_path: str = ""
        self._active_row = -1
        self._track_active = False
        self._show_lyric = bool(show_lyric_default)
        self._last_position_ms = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        controls_row = QHBoxLayout()
        self._show_lyric_checkbox = QCheckBox(tr("Show lyric alongside automation cues"))
        self._show_lyric_checkbox.setChecked(self._show_lyric)
        self._show_lyric_checkbox.toggled.connect(self._on_show_lyric_toggled)
        controls_row.addWidget(self._show_lyric_checkbox)
        controls_row.addStretch(1)

        self._companion_bypass_button = QPushButton(tr("Companion Bypass"))
        self._companion_bypass_button.setCheckable(True)
        self._companion_bypass_button.toggled.connect(self._on_companion_bypass_toggled)
        controls_row.addWidget(self._companion_bypass_button)

        self._internal_bypass_button = QPushButton(tr("Internal Bypass"))
        self._internal_bypass_button.setCheckable(True)
        self._internal_bypass_button.toggled.connect(self._on_internal_bypass_toggled)
        controls_row.addWidget(self._internal_bypass_button)
        root.addLayout(controls_row)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._tree = QTreeWidget(self)
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels([tr("Timestamp"), tr("Type"), tr("Comment / Lyric"), tr("Commands")])
        self._tree.setRootIsDecorated(True)
        self._tree.setItemsExpandable(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self._tree, 1)

        self.set_companion_bypass(companion_bypass)
        self.set_internal_bypass(internal_bypass)
        localize_widget_tree(self, language)

    def retranslate_ui(self, language: str = "en") -> None:
        self.setWindowTitle(tr("Automation Script Navigator"))
        self._tree.setHeaderLabels([tr("Timestamp"), tr("Type"), tr("Comment / Lyric"), tr("Commands")])
        self._show_lyric_checkbox.setText(tr("Show lyric alongside automation cues"))
        self._companion_bypass_button.setText(tr("Companion Bypass"))
        self._internal_bypass_button.setText(tr("Internal Bypass"))
        localize_widget_tree(self, language)

    def clear(self) -> None:
        self._track_active = False
        self._rows = []
        self._current_script_path = ""
        self._current_lyric_path = ""
        self._active_row = -1
        self._status_label.setText("")
        self._tree.clear()

    def update_playback_state(
        self,
        *,
        has_active_track: bool,
        script_path: str,
        lyric_path: str = "",
        position_ms: int,
        companion_bypass: Optional[bool] = None,
        internal_bypass: Optional[bool] = None,
        force: bool = False,
    ) -> None:
        self._track_active = bool(has_active_track)
        self._last_position_ms = max(0, int(position_ms))
        if companion_bypass is not None:
            self.set_companion_bypass(companion_bypass)
        if internal_bypass is not None:
            self.set_internal_bypass(internal_bypass)
        if not has_active_track:
            self.clear()
            return

        path = str(script_path or "").strip()
        lyric_file_path = str(lyric_path or "").strip()
        self._current_script_path = path
        self._current_lyric_path = lyric_file_path
        if not path and not lyric_file_path:
            self._status_label.setText(tr("No automation script assigned for this sound."))
            self._rows = []
            self._tree.clear()
            return
        if path and not os.path.exists(path):
            self._status_label.setText(tr("Automation script not found:\n{path}").format(path=path))
            self._rows = []
            self._tree.clear()
            return
        if lyric_file_path and not os.path.exists(lyric_file_path):
            lyric_file_path = ""

        rows, error = self._load_rows(path, lyric_file_path)
        if error:
            self._status_label.setText(error)
            self._rows = []
            self._current_script_path = ""
            self._tree.clear()
            return
        visible_rows = [
            row for row in list(rows)
            if self._show_lyric or str(row.get("kind", "") or "") == "cue"
        ]
        status_lines = []
        if path:
            status_lines.append(path)
        if lyric_file_path and self._show_lyric:
            status_lines.append(lyric_file_path)
        self._status_label.setText("\n".join(status_lines))
        if force or self._rows != visible_rows or self._current_script_path != path:
            self._rows = list(visible_rows)
            self._current_script_path = path
            self._tree.clear()
            for row_idx, row in enumerate(self._rows):
                item = QTreeWidgetItem(
                    [
                        self._format_timestamp(int(row["time_ms"])),
                        tr("Cue") if row["kind"] == "cue" else tr("Lyric"),
                        str(row.get("comment", "") or ""),
                        str(row.get("commands", "") or ""),
                    ]
                )
                item.setData(0, Qt.UserRole, row_idx)
                self._tree.addTopLevelItem(item)
                for child in list(row.get("children", []) or []):
                    child_item = QTreeWidgetItem(
                        [
                            "",
                            tr("Command"),
                            str(child.get("comment", "") or ""),
                            str(child.get("commands", "") or ""),
                        ]
                    )
                    child_item.setData(0, Qt.UserRole, row_idx)
                    item.addChild(child_item)

        self._highlight_row(self._row_index_for_position(position_ms))

    def set_companion_bypass(self, bypassed: bool) -> None:
        self._companion_bypass_button.blockSignals(True)
        self._companion_bypass_button.setChecked(bool(bypassed))
        self._companion_bypass_button.blockSignals(False)
        self._refresh_toggle_button_style(
            self._companion_bypass_button,
            active_color="#D86A6A",
            inactive_color="#3E8E63",
        )

    def set_internal_bypass(self, bypassed: bool) -> None:
        self._internal_bypass_button.blockSignals(True)
        self._internal_bypass_button.setChecked(bool(bypassed))
        self._internal_bypass_button.blockSignals(False)
        self._refresh_toggle_button_style(
            self._internal_bypass_button,
            active_color="#CC8A32",
            inactive_color="#2F7DAF",
        )

    def _on_show_lyric_toggled(self, checked: bool) -> None:
        self._show_lyric = bool(checked)
        if self._on_show_lyric_changed is not None:
            self._on_show_lyric_changed(self._show_lyric)
        self._cache_lyric_path = ""
        self._cache_lyric_mtime = -1.0
        self._cache_rows = []
        self.update_playback_state(
            has_active_track=self._track_active,
            script_path=self._current_script_path,
            lyric_path=self._current_lyric_path,
            position_ms=self._last_position_ms,
            force=True,
        )

    def _on_companion_bypass_toggled(self, checked: bool) -> None:
        self._refresh_toggle_button_style(self._companion_bypass_button, "#D86A6A", "#3E8E63")
        if self._on_companion_bypass_changed is not None:
            self._on_companion_bypass_changed(bool(checked))

    def _on_internal_bypass_toggled(self, checked: bool) -> None:
        self._refresh_toggle_button_style(self._internal_bypass_button, "#CC8A32", "#2F7DAF")
        if self._on_internal_bypass_changed is not None:
            self._on_internal_bypass_changed(bool(checked))

    @staticmethod
    def _refresh_toggle_button_style(button: QPushButton, active_color: str, inactive_color: str) -> None:
        bg = active_color if button.isChecked() else inactive_color
        button.setStyleSheet(
            "QPushButton{"
            f"background:{bg};"
            "color:#FFFFFF;"
            "font-weight:bold;"
            "padding:4px 10px;"
            "border:1px solid #4A4A4A;"
            "border-radius:4px;"
            "}"
        )

    def _load_rows(self, script_path: str, lyric_path: str) -> tuple[List[dict], str]:
        try:
            script_mtime = os.path.getmtime(script_path) if script_path else -1.0
        except OSError:
            return [], tr("Automation script not found:\n{path}").format(path=script_path)
        try:
            lyric_mtime = os.path.getmtime(lyric_path) if lyric_path else -1.0
        except OSError:
            lyric_mtime = -1.0
        if (
            script_path == self._cache_script_path
            and lyric_path == self._cache_lyric_path
            and abs(script_mtime - self._cache_script_mtime) < 0.0001
            and abs(lyric_mtime - self._cache_lyric_mtime) < 0.0001
        ):
            return self._cache_rows, self._cache_error
        try:
            rows: List[dict] = []
            if script_path:
                script = load_automation_script(script_path)
                for cue in list(script.cues or []):
                    rows.append(
                        {
                            "kind": "cue",
                            "time_ms": int(cue.time_ms),
                            "comment": str(cue.comment or ""),
                            "commands": automation_script_cue_command_summary(cue),
                            "children": [
                                {
                                    "comment": "",
                                    "commands": automation_script_cue_command_summary(
                                        AutomationScriptCue(
                                            time_ms=int(cue.time_ms),
                                            comment="",
                                            actions=[action],
                                        )
                                    ),
                                }
                                for action in list(cue.actions or [])
                            ],
                        }
                    )
            if lyric_path:
                for line in list(parse_lyric_file(lyric_path) or []):
                    rows.append(
                        {
                            "kind": "lyric",
                            "time_ms": int(line.start_ms),
                            "comment": str(line.text or ""),
                            "commands": tr("Reference"),
                            "children": [],
                        }
                    )
            rows.sort(key=lambda entry: (int(entry["time_ms"]), 0 if entry["kind"] == "cue" else 1))
            error = ""
        except Exception as exc:
            rows = []
            error = f"{tr('Failed to read automation script:')}\n{exc}"
        self._cache_script_path = script_path
        self._cache_script_mtime = script_mtime
        self._cache_lyric_path = lyric_path
        self._cache_lyric_mtime = lyric_mtime
        self._cache_rows = rows
        self._cache_error = error
        return rows, error

    def _highlight_row(self, row: int) -> None:
        if row < 0 or row >= len(self._rows):
            self._active_row = -1
            self._tree.clearSelection()
            return
        if row == self._active_row:
            return
        self._active_row = row
        item = self._tree.topLevelItem(row)
        if item is not None:
            self._tree.setCurrentItem(item)
            self._tree.scrollToItem(item, QTreeWidget.PositionAtCenter)

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if not self._track_active:
            return
        row = int(item.data(0, Qt.UserRole) or -1)
        if row < 0 or row >= len(self._rows):
            return
        self._on_seek_to_ms(max(0, int(self._rows[row]["time_ms"])))

    def _row_index_for_position(self, position_ms: int) -> int:
        row = -1
        for index, item in enumerate(self._rows):
            if int(item["time_ms"]) <= max(0, int(position_ms)):
                row = index
            else:
                break
        return row

    @staticmethod
    def _format_timestamp(ms: int) -> str:
        value = max(0, int(ms))
        hours = value // 3600000
        minutes = (value // 60000) % 60
        seconds = (value // 1000) % 60
        millis = value % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
