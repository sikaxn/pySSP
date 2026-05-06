from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.automation_command import (
    AutomationCommandSpec,
    SOUND_BUTTON_AUTOMATION_EVENTS,
    SOUND_BUTTON_AUTOMATION_SIMPLE_EVENTS,
    SOUND_BUTTON_AUTOMATION_MODE_ADVANCED,
    SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
    SoundButtonAutomationConfig,
    automation_display_name,
    normalize_automation_spec,
    normalize_sound_button_automation_config,
    sound_button_automation_event_label,
)
from pyssp.i18n import localize_widget_tree, tr
from pyssp.ui.automation_command_sound_button_dialog import AutomationCommandSoundButtonDialog


class _CommandListEditor(QGroupBox):
    def __init__(
        self,
        title: str,
        *,
        commands: Optional[list[AutomationCommandSpec]] = None,
        open_picker,
        on_changed=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)
        self._open_picker = open_picker
        self._on_changed = on_changed
        self._commands: list[AutomationCommandSpec] = [
            normalize_automation_spec(item) for item in list(commands or []) if normalize_automation_spec(item).location
        ]

        root = QVBoxLayout(self)
        self.list_widget = QListWidget(self)
        root.addWidget(self.list_widget, 1)

        button_row = QHBoxLayout()
        self.add_button = QPushButton(tr("Add"))
        self.edit_button = QPushButton(tr("Edit"))
        self.remove_button = QPushButton(tr("Remove"))
        self.up_button = QPushButton(tr("Move Up"))
        self.down_button = QPushButton(tr("Move Down"))
        self.clear_button = QPushButton(tr("Clear"))
        for button in (
            self.add_button,
            self.edit_button,
            self.remove_button,
            self.up_button,
            self.down_button,
            self.clear_button,
        ):
            button_row.addWidget(button)
        root.addLayout(button_row)

        self.add_button.clicked.connect(self._add_command)
        self.edit_button.clicked.connect(self._edit_selected_command)
        self.remove_button.clicked.connect(self._remove_selected_command)
        self.up_button.clicked.connect(lambda: self._move_selected(-1))
        self.down_button.clicked.connect(lambda: self._move_selected(1))
        self.clear_button.clicked.connect(self._clear_commands)
        self.list_widget.itemDoubleClicked.connect(lambda _item: self._edit_selected_command())
        self.list_widget.currentRowChanged.connect(lambda _row: self._refresh_button_state())

        self._refresh_list()

    def commands(self) -> list[AutomationCommandSpec]:
        return [normalize_automation_spec(item) for item in self._commands if normalize_automation_spec(item).location]

    def set_commands(self, commands: Optional[list[AutomationCommandSpec]]) -> None:
        self._commands = [
            normalize_automation_spec(item) for item in list(commands or []) if normalize_automation_spec(item).location
        ]
        self._refresh_list()

    def _refresh_list(self) -> None:
        current_row = self.list_widget.currentRow()
        self.list_widget.clear()
        for spec in self._commands:
            item = QListWidgetItem(automation_display_name(spec))
            item.setData(Qt.UserRole, normalize_automation_spec(spec))
            detail = normalize_automation_spec(spec).location
            item.setToolTip(detail)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(max(0, min(current_row, self.list_widget.count() - 1)))
        self._refresh_button_state()

    def _refresh_button_state(self) -> None:
        row = self.list_widget.currentRow()
        has_selection = row >= 0
        count = len(self._commands)
        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)
        self.up_button.setEnabled(has_selection and row > 0)
        self.down_button.setEnabled(has_selection and row >= 0 and row < (count - 1))
        self.clear_button.setEnabled(count > 0)

    def _add_command(self) -> None:
        spec = self._open_picker(None)
        if spec is None or not spec.location:
            return
        self._commands.append(normalize_automation_spec(spec))
        self._refresh_list()
        self.list_widget.setCurrentRow(len(self._commands) - 1)
        self._emit_changed()

    def _edit_selected_command(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._commands):
            return
        spec = self._open_picker(self._commands[row])
        if spec is None or not spec.location:
            return
        self._commands[row] = normalize_automation_spec(spec)
        self._refresh_list()
        self.list_widget.setCurrentRow(row)
        self._emit_changed()

    def _remove_selected_command(self) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._commands):
            return
        self._commands.pop(row)
        self._refresh_list()
        self._emit_changed()

    def _move_selected(self, delta: int) -> None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._commands):
            return
        target = row + int(delta)
        if target < 0 or target >= len(self._commands):
            return
        self._commands[row], self._commands[target] = self._commands[target], self._commands[row]
        self._refresh_list()
        self.list_widget.setCurrentRow(target)
        self._emit_changed()

    def _clear_commands(self) -> None:
        self._commands = []
        self._refresh_list()
        self._emit_changed()

    def _emit_changed(self) -> None:
        if callable(self._on_changed):
            self._on_changed()


class _AdvancedAutomationRowDialog(QDialog):
    def __init__(
        self,
        *,
        row_data: Optional[tuple[str, AutomationCommandSpec]] = None,
        open_picker,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Edit Automation Row"))
        self._open_picker = open_picker
        self._selected_spec = normalize_automation_spec(
            AutomationCommandSpec() if row_data is None else row_data[1]
        )

        root = QVBoxLayout(self)

        form = QGridLayout()
        form.addWidget(QLabel(tr("Trigger")), 0, 0)
        self.trigger_combo = QComboBox(self)
        for event_name in SOUND_BUTTON_AUTOMATION_EVENTS:
            self.trigger_combo.addItem(tr(sound_button_automation_event_label(event_name)), event_name)
        form.addWidget(self.trigger_combo, 0, 1)

        form.addWidget(QLabel(tr("Command")), 1, 0)
        self.command_label = QLabel(self)
        self.command_label.setWordWrap(True)
        form.addWidget(self.command_label, 1, 1)
        root.addLayout(form)

        command_buttons = QHBoxLayout()
        self.select_button = QPushButton(tr("Select Command"))
        command_buttons.addWidget(self.select_button)
        command_buttons.addStretch(1)
        root.addLayout(command_buttons)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.select_button.clicked.connect(self._select_command)

        event_name = SOUND_BUTTON_AUTOMATION_EVENTS[0]
        if row_data is not None and str(row_data[0] or "").strip().lower() in SOUND_BUTTON_AUTOMATION_EVENTS:
            event_name = str(row_data[0]).strip().lower()
        self.trigger_combo.setCurrentIndex(max(0, SOUND_BUTTON_AUTOMATION_EVENTS.index(event_name)))
        self._refresh_command_label()

    def values(self) -> Optional[tuple[str, AutomationCommandSpec]]:
        event_name = str(self.trigger_combo.currentData() or "").strip().lower()
        spec = normalize_automation_spec(self._selected_spec)
        if event_name not in SOUND_BUTTON_AUTOMATION_EVENTS or not spec.location:
            return None
        return event_name, spec

    def _select_command(self) -> None:
        spec = self._open_picker(self._selected_spec if self._selected_spec.location else None)
        if spec is None or not spec.location:
            return
        self._selected_spec = normalize_automation_spec(spec)
        self._refresh_command_label()

    def _refresh_command_label(self) -> None:
        spec = normalize_automation_spec(self._selected_spec)
        if not spec.location:
            self.command_label.setText(tr("No command selected."))
            return
        label = automation_display_name(spec)
        self.command_label.setText(f"{label} ({spec.location})")


class _AdvancedAutomationTable(QGroupBox):
    def __init__(
        self,
        *,
        rows: Optional[list[tuple[str, AutomationCommandSpec]]] = None,
        open_picker,
        on_changed=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(tr("Advanced Automation"), parent)
        self._open_picker = open_picker
        self._on_changed = on_changed
        self._rows: list[tuple[str, AutomationCommandSpec]] = []

        root = QVBoxLayout(self)
        self.table = QTableWidget(0, 2, self)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setHorizontalHeaderLabels([tr("Trigger"), tr("Command")])
        root.addWidget(self.table, 1)

        button_row = QHBoxLayout()
        self.add_button = QPushButton(tr("Add"))
        self.edit_button = QPushButton(tr("Edit"))
        self.remove_button = QPushButton(tr("Remove"))
        self.up_button = QPushButton(tr("Move Up"))
        self.down_button = QPushButton(tr("Move Down"))
        self.clear_button = QPushButton(tr("Clear"))
        for button in (
            self.add_button,
            self.edit_button,
            self.remove_button,
            self.up_button,
            self.down_button,
            self.clear_button,
        ):
            button_row.addWidget(button)
        root.addLayout(button_row)

        self.add_button.clicked.connect(self._add_row)
        self.edit_button.clicked.connect(self._edit_selected_row)
        self.remove_button.clicked.connect(self._remove_selected_row)
        self.up_button.clicked.connect(lambda: self._move_selected(-1))
        self.down_button.clicked.connect(lambda: self._move_selected(1))
        self.clear_button.clicked.connect(self._clear_rows)
        self.table.itemDoubleClicked.connect(lambda _item: self._edit_selected_row())
        self.table.itemSelectionChanged.connect(self._refresh_button_state)

        for row_data in list(rows or []):
            self._append_row(row_data[0], row_data[1])
        self._refresh_table()

    def rows(self) -> list[tuple[str, AutomationCommandSpec]]:
        return [
            (str(event_name or "").strip().lower(), normalize_automation_spec(spec))
            for event_name, spec in self._rows
            if str(event_name or "").strip().lower() in SOUND_BUTTON_AUTOMATION_EVENTS
            and normalize_automation_spec(spec).location
        ]

    def set_rows(self, rows: Optional[list[tuple[str, AutomationCommandSpec]]]) -> None:
        self._rows = []
        for row_data in list(rows or []):
            self._append_row(row_data[0], row_data[1])
        self._refresh_table()

    def replace_event_rows(
        self,
        event_names: tuple[str, ...],
        replacement_rows: list[tuple[str, AutomationCommandSpec]],
    ) -> None:
        event_set = {str(name or "").strip().lower() for name in event_names}
        normalized_replacements: dict[str, list[tuple[str, AutomationCommandSpec]]] = {
            name: [] for name in event_set
        }
        for event_name, spec in replacement_rows:
            normalized_event = str(event_name or "").strip().lower()
            normalized_spec = normalize_automation_spec(spec)
            if normalized_event in event_set and normalized_spec.location:
                normalized_replacements.setdefault(normalized_event, []).append((normalized_event, normalized_spec))
        updated_rows: list[tuple[str, AutomationCommandSpec]] = []
        inserted_events: set[str] = set()
        for event_name, spec in self._rows:
            normalized_event = str(event_name or "").strip().lower()
            if normalized_event in event_set:
                if normalized_event not in inserted_events:
                    updated_rows.extend(normalized_replacements.get(normalized_event, []))
                    inserted_events.add(normalized_event)
                continue
            updated_rows.append((normalized_event, normalize_automation_spec(spec)))
        for event_name in event_names:
            normalized_event = str(event_name or "").strip().lower()
            if normalized_event in inserted_events:
                continue
            updated_rows.extend(normalized_replacements.get(normalized_event, []))
        self._rows = updated_rows
        self._refresh_table()

    def _append_row(self, event_name: str, spec: AutomationCommandSpec) -> None:
        normalized_event = str(event_name or "").strip().lower()
        normalized_spec = normalize_automation_spec(spec)
        if normalized_event not in SOUND_BUTTON_AUTOMATION_EVENTS or not normalized_spec.location:
            return
        self._rows.append((normalized_event, normalized_spec))

    def _refresh_table(self) -> None:
        current_row = self.table.currentRow()
        self.table.setRowCount(0)
        for event_name, spec in self._rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            trigger_item = QTableWidgetItem(tr(sound_button_automation_event_label(event_name)))
            trigger_item.setData(Qt.UserRole, event_name)
            trigger_item.setFlags(trigger_item.flags() & ~Qt.ItemIsEditable)
            command_text = automation_display_name(spec)
            command_item = QTableWidgetItem(command_text)
            command_item.setData(Qt.UserRole, normalize_automation_spec(spec))
            command_item.setToolTip(normalize_automation_spec(spec).location)
            command_item.setFlags(command_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, trigger_item)
            self.table.setItem(row, 1, command_item)
        if self.table.rowCount() > 0:
            self.table.selectRow(max(0, min(current_row, self.table.rowCount() - 1)))
        self._refresh_button_state()

    def _refresh_button_state(self) -> None:
        row = self.table.currentRow()
        has_selection = row >= 0
        count = len(self._rows)
        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)
        self.up_button.setEnabled(has_selection and row > 0)
        self.down_button.setEnabled(has_selection and row >= 0 and row < (count - 1))
        self.clear_button.setEnabled(count > 0)

    def _open_row_dialog(
        self,
        current: Optional[tuple[str, AutomationCommandSpec]],
    ) -> Optional[tuple[str, AutomationCommandSpec]]:
        dialog = _AdvancedAutomationRowDialog(
            row_data=current,
            open_picker=self._open_picker,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return None
        return dialog.values()

    def _add_row(self) -> None:
        row_data = self._open_row_dialog(None)
        if row_data is None:
            return
        self._rows.append((row_data[0], normalize_automation_spec(row_data[1])))
        self._refresh_table()
        self.table.selectRow(len(self._rows) - 1)
        self._emit_changed()

    def _edit_selected_row(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            return
        updated = self._open_row_dialog(self._rows[row])
        if updated is None:
            return
        self._rows[row] = (updated[0], normalize_automation_spec(updated[1]))
        self._refresh_table()
        self.table.selectRow(row)
        self._emit_changed()

    def _remove_selected_row(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            return
        self._rows.pop(row)
        self._refresh_table()
        self._emit_changed()

    def _move_selected(self, delta: int) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            return
        target = row + int(delta)
        if target < 0 or target >= len(self._rows):
            return
        self._rows[row], self._rows[target] = self._rows[target], self._rows[row]
        self._refresh_table()
        self.table.selectRow(target)
        self._emit_changed()

    def _clear_rows(self) -> None:
        self._rows = []
        self._refresh_table()
        self._emit_changed()

    def _emit_changed(self) -> None:
        if callable(self._on_changed):
            self._on_changed()


class SoundButtonAutomationDialog(QDialog):
    def __init__(
        self,
        *,
        config: Optional[SoundButtonAutomationConfig] = None,
        companion_payload: Optional[dict] = None,
        hide_black_empty: bool = True,
        language: str = "en",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Set Sound Button Automation"))
        self.resize(960, 760)
        self._payload = dict(companion_payload or {"pages": {}, "updated_at": ""})
        self._hide_black_empty = bool(hide_black_empty)
        self._language = language
        self._syncing_views = False
        self._config = normalize_sound_button_automation_config(config)
        if self._config is None:
            self._config = SoundButtonAutomationConfig()

        root = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel(tr("Mode")))
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItem(tr("Simple"), SOUND_BUTTON_AUTOMATION_MODE_SIMPLE)
        self.mode_combo.addItem(tr("Advanced"), SOUND_BUTTON_AUTOMATION_MODE_ADVANCED)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch(1)
        root.addLayout(mode_row)

        self.mode_note = QLabel(self)
        self.mode_note.setWordWrap(True)
        root.addWidget(self.mode_note)

        self.stack = QStackedWidget(self)
        root.addWidget(self.stack, 1)

        self.simple_page = QWidget(self)
        self.advanced_page = QWidget(self)
        self.stack.addWidget(self.simple_page)
        self.stack.addWidget(self.advanced_page)

        simple_layout = QGridLayout(self.simple_page)
        self.simple_start_editor = _CommandListEditor(
            tr("When this sound button starts playing"),
            commands=self._config.on_become_playing,
            open_picker=self._open_picker_dialog,
            on_changed=self._on_simple_lists_changed,
            parent=self.simple_page,
        )
        self.simple_stop_editor = _CommandListEditor(
            tr("When this sound button stops playing for any reason except pause"),
            commands=self._config.on_leave_playing,
            open_picker=self._open_picker_dialog,
            on_changed=self._on_simple_lists_changed,
            parent=self.simple_page,
        )
        self.simple_pause_editor = _CommandListEditor(
            tr("When this sound button pauses"),
            commands=self._config.on_pause,
            open_picker=self._open_picker_dialog,
            on_changed=self._on_simple_lists_changed,
            parent=self.simple_page,
        )
        self.simple_resume_editor = _CommandListEditor(
            tr("When this sound button resumes playing"),
            commands=self._config.on_resume_complete,
            open_picker=self._open_picker_dialog,
            on_changed=self._on_simple_lists_changed,
            parent=self.simple_page,
        )
        simple_layout.addWidget(self.simple_start_editor, 0, 0)
        simple_layout.addWidget(self.simple_stop_editor, 0, 1)
        simple_layout.addWidget(self.simple_pause_editor, 1, 0)
        simple_layout.addWidget(self.simple_resume_editor, 1, 1)

        advanced_layout = QVBoxLayout(self.advanced_page)
        self.advanced_table = _AdvancedAutomationTable(
            rows=self._config_to_advanced_rows(self._config),
            open_picker=self._open_picker_dialog,
            on_changed=self._on_advanced_rows_changed,
            parent=self.advanced_page,
        )
        advanced_layout.addWidget(self.advanced_table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        target_mode = SOUND_BUTTON_AUTOMATION_MODE_SIMPLE
        if self._config is not None:
            target_mode = self._config.mode
        self.mode_combo.currentIndexChanged.connect(self._refresh_mode_ui)
        self.mode_combo.setCurrentIndex(
            1 if target_mode == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED else 0
        )
        self._refresh_mode_ui()
        localize_widget_tree(self, language)

    def values(self) -> Optional[SoundButtonAutomationConfig]:
        mode = self.selected_mode()
        data = self._advanced_rows_to_data()
        data["mode"] = mode
        data["on_become_playing"] = self.simple_start_editor.commands()
        data["on_leave_playing"] = self.simple_stop_editor.commands()
        data["on_pause"] = self.simple_pause_editor.commands()
        data["on_resume_complete"] = self.simple_resume_editor.commands()
        return normalize_sound_button_automation_config(data)

    def _advanced_rows_to_data(self) -> dict[str, object]:
        data = {
            event_name: None for event_name in SOUND_BUTTON_AUTOMATION_EVENTS
        }
        for event_name, spec in self.advanced_table.rows():
            bucket = list(data.get(event_name) or [])
            bucket.append(spec)
            data[event_name] = bucket
        return data

    def selected_mode(self) -> str:
        token = str(self.mode_combo.currentData() or SOUND_BUTTON_AUTOMATION_MODE_SIMPLE).strip().lower()
        if token == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED:
            return SOUND_BUTTON_AUTOMATION_MODE_ADVANCED
        return SOUND_BUTTON_AUTOMATION_MODE_SIMPLE

    def _refresh_mode_ui(self) -> None:
        mode = self.selected_mode()
        self._sync_views_for_mode(mode)
        if mode == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED:
            self.stack.setCurrentWidget(self.advanced_page)
            self.mode_note.setText(
                tr("Advanced mode gives you one ordered Trigger / Command list with all available lifecycle options.")
            )
            return
        self.stack.setCurrentWidget(self.simple_page)
        self.mode_note.setText(
            tr("Simple mode gives you separate command lists for start, stop, pause, and resume. Stop excludes pause.")
        )

    def _open_picker_dialog(self, spec: Optional[AutomationCommandSpec]) -> Optional[AutomationCommandSpec]:
        dialog = AutomationCommandSoundButtonDialog(
            caption="",
            notes="",
            automation_spec=spec or AutomationCommandSpec(),
            companion_payload=self._payload,
            hide_black_empty=self._hide_black_empty,
            language=self._language,
            selection_only=True,
            window_title=tr("Select Automation Command"),
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return None
        _caption, _notes, selected_spec, _custom_color, _sound_hotkey, _sound_midi_hotkey = dialog.values()
        normalized = normalize_automation_spec(selected_spec)
        if not normalized.location:
            return None
        return normalized

    def _sync_views_for_mode(self, mode: str) -> None:
        if self._syncing_views:
            return
        self._syncing_views = True
        try:
            if mode == SOUND_BUTTON_AUTOMATION_MODE_ADVANCED:
                self.advanced_table.replace_event_rows(
                    SOUND_BUTTON_AUTOMATION_SIMPLE_EVENTS,
                    self._simple_rows(),
                )
            else:
                self._set_simple_editors_from_advanced_rows()
        finally:
            self._syncing_views = False

    def _simple_rows(self) -> list[tuple[str, AutomationCommandSpec]]:
        rows: list[tuple[str, AutomationCommandSpec]] = []
        rows.extend(
            ("on_become_playing", spec) for spec in self.simple_start_editor.commands()
        )
        rows.extend(
            ("on_leave_playing", spec) for spec in self.simple_stop_editor.commands()
        )
        rows.extend(
            ("on_pause", spec) for spec in self.simple_pause_editor.commands()
        )
        rows.extend(
            ("on_resume_complete", spec) for spec in self.simple_resume_editor.commands()
        )
        return rows

    def _set_simple_editors_from_advanced_rows(self) -> None:
        start_specs: list[AutomationCommandSpec] = []
        stop_specs: list[AutomationCommandSpec] = []
        pause_specs: list[AutomationCommandSpec] = []
        resume_specs: list[AutomationCommandSpec] = []
        for event_name, spec in self.advanced_table.rows():
            if event_name == "on_become_playing":
                start_specs.append(spec)
            elif event_name == "on_leave_playing":
                stop_specs.append(spec)
            elif event_name == "on_pause":
                pause_specs.append(spec)
            elif event_name == "on_resume_complete":
                resume_specs.append(spec)
        self.simple_start_editor.set_commands(start_specs)
        self.simple_stop_editor.set_commands(stop_specs)
        self.simple_pause_editor.set_commands(pause_specs)
        self.simple_resume_editor.set_commands(resume_specs)

    def _on_simple_lists_changed(self) -> None:
        if self._syncing_views:
            return
        self._syncing_views = True
        try:
            self.advanced_table.replace_event_rows(
                SOUND_BUTTON_AUTOMATION_SIMPLE_EVENTS,
                self._simple_rows(),
            )
        finally:
            self._syncing_views = False

    def _on_advanced_rows_changed(self) -> None:
        if self._syncing_views:
            return
        self._syncing_views = True
        try:
            self._set_simple_editors_from_advanced_rows()
        finally:
            self._syncing_views = False

    @staticmethod
    def _config_to_advanced_rows(
        config: Optional[SoundButtonAutomationConfig],
    ) -> list[tuple[str, AutomationCommandSpec]]:
        normalized = normalize_sound_button_automation_config(config)
        if normalized is None:
            return []
        rows: list[tuple[str, AutomationCommandSpec]] = []
        for event_name in SOUND_BUTTON_AUTOMATION_EVENTS:
            for spec in list(getattr(normalized, event_name, None) or []):
                normalized_spec = normalize_automation_spec(spec)
                if normalized_spec.location:
                    rows.append((event_name, normalized_spec))
        return rows
