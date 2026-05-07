from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIntValidator
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.automation_command import (
    AUTOMATION_COMMAND_SOURCE_COMPANION,
    AUTOMATION_COMMAND_SOURCE_INTERNAL,
    AutomationCommandSpec,
    automation_display_name,
    automation_spec_detail_text,
    automation_spec_is_valid,
    normalize_automation_spec,
)
from pyssp.companion_available_commands import (
    is_black_empty_command,
    is_navigation_command,
    list_companion_available_commands,
)
from pyssp.i18n import localize_widget_tree, tr
from pyssp.internal_automation import (
    internal_automation_command_summary,
    list_internal_automation_commands,
    normalize_internal_automation_command_id,
    normalize_internal_automation_params,
)
from pyssp.midi_control import (
    midi_binding_to_display,
    midi_input_name_selector,
    normalize_midi_binding,
    split_midi_binding,
)
from pyssp.ui.edit_sound_button_dialog import SoundHotkeyEdit


class AutomationCommandSoundButtonDialog(QDialog):
    def __init__(
        self,
        *,
        caption: str,
        notes: str,
        automation_spec: Optional[AutomationCommandSpec] = None,
        custom_color: Optional[str] = None,
        sound_hotkey: str = "",
        sound_midi_hotkey: str = "",
        available_midi_input_devices: Optional[list[tuple[str, str]]] = None,
        selected_midi_input_device_ids: Optional[list[str]] = None,
        companion_payload: Optional[dict] = None,
        hide_black_empty: bool = True,
        language: str = "en",
        selection_only: bool = False,
        window_title: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._selection_only = bool(selection_only)
        self.setWindowTitle(window_title or tr("Automation Command Sound Button"))
        self.resize(820, 620)
        self._payload = dict(companion_payload or {"pages": {}, "updated_at": ""})
        self._custom_color = str(custom_color or "").strip().upper()
        self._spec = normalize_automation_spec(automation_spec or AutomationCommandSpec())
        self._caption_auto_value = automation_display_name(self._spec)
        normalized_caption = str(caption or "").strip()
        self._caption_user_edited = bool(
            normalized_caption
            and normalized_caption not in {"", self._caption_auto_value, self._spec.button_text, self._spec.location}
        )
        self._form = None
        self._selection_only_row_fields: list[QWidget] = []

        root = QVBoxLayout(self)
        form = QFormLayout()
        self._form = form

        self.caption_edit = QLineEdit(caption)
        form.addRow(tr("Caption"), self.caption_edit)
        self._selection_only_row_fields.append(self.caption_edit)

        self.notes_edit = QLineEdit(notes)
        form.addRow(tr("Notes"), self.notes_edit)
        self._selection_only_row_fields.append(self.notes_edit)

        self.location_value_label = QLabel(automation_display_name(self._spec) or "-")
        form.addRow(tr("Selected Command"), self.location_value_label)

        self.hold_to_release_checkbox = QCheckBox(tr("Respect press-down / release-up input"))
        self.hold_to_release_checkbox.setChecked(bool(self._spec.hold_to_release))
        form.addRow("", self.hold_to_release_checkbox)
        self._selection_only_row_fields.append(self.hold_to_release_checkbox)

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_color_button = QPushButton()
        self.custom_color_button.clicked.connect(self._pick_custom_color)
        clear_color_button = QPushButton(tr("Clear"))
        clear_color_button.clicked.connect(self._clear_custom_color)
        color_layout.addWidget(self.custom_color_button, 1)
        color_layout.addWidget(clear_color_button)
        form.addRow(tr("Button Colour"), color_row)
        self._selection_only_row_fields.append(color_row)
        self._refresh_custom_color_button()

        hk_row = QWidget()
        hk_layout = QHBoxLayout(hk_row)
        hk_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_hotkey_edit = SoundHotkeyEdit()
        self.sound_hotkey_edit.setHotkey(sound_hotkey)
        clear_hk_btn = QPushButton(tr("Clear"))
        clear_hk_btn.clicked.connect(lambda _=False: self.sound_hotkey_edit.setHotkey(""))
        hk_layout.addWidget(self.sound_hotkey_edit, 1)
        hk_layout.addWidget(clear_hk_btn)
        form.addRow(tr("Sound Button Hot Key"), hk_row)
        self._selection_only_row_fields.append(hk_row)

        midi_hk_row = QWidget()
        midi_hk_layout = QHBoxLayout(midi_hk_row)
        midi_hk_layout.setContentsMargins(0, 0, 0, 0)
        self.sound_midi_hotkey_edit = QLineEdit()
        self.sound_midi_hotkey_edit.setReadOnly(True)
        self._set_midi_binding(sound_midi_hotkey)
        learn_midi_btn = QPushButton(tr("Learn"))
        clear_midi_btn = QPushButton(tr("Clear"))
        learn_midi_btn.clicked.connect(self._start_midi_learn)
        clear_midi_btn.clicked.connect(lambda _=False: self._set_midi_binding(""))
        midi_hk_layout.addWidget(self.sound_midi_hotkey_edit, 1)
        midi_hk_layout.addWidget(learn_midi_btn)
        midi_hk_layout.addWidget(clear_midi_btn)
        form.addRow(tr("Sound Button MIDI Hot Key"), midi_hk_row)
        self._selection_only_row_fields.append(midi_hk_row)

        root.addLayout(form)

        self.source_tabs = QTabWidget(self)
        root.addWidget(self.source_tabs, 1)

        companion_page = QWidget(self)
        companion_root = QVBoxLayout(companion_page)
        companion_root.setContentsMargins(0, 0, 0, 0)
        companion_root.setSpacing(8)

        mode_row = QWidget()
        mode_layout = QHBoxLayout(mode_row)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        self.pick_from_list_radio = QRadioButton(tr("Pick from Available Commands"))
        self.manual_location_radio = QRadioButton(tr("Enter Location Manually"))
        self.location_mode_group = QButtonGroup(self)
        self.location_mode_group.addButton(self.pick_from_list_radio)
        self.location_mode_group.addButton(self.manual_location_radio)
        mode_layout.addWidget(self.pick_from_list_radio)
        mode_layout.addWidget(self.manual_location_radio)
        companion_root.addWidget(QLabel(tr("Location Mode")))
        companion_root.addWidget(mode_row)

        manual_row = QWidget()
        manual_layout = QHBoxLayout(manual_row)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        self.manual_page_edit = QLineEdit()
        self.manual_page_edit.setPlaceholderText(tr("Page"))
        self.manual_row_edit = QLineEdit()
        self.manual_row_edit.setPlaceholderText(tr("Row"))
        self.manual_column_edit = QLineEdit()
        self.manual_column_edit.setPlaceholderText(tr("Column"))
        numeric_validator = QIntValidator(0, 9999, self)
        for edit in (self.manual_page_edit, self.manual_row_edit, self.manual_column_edit):
            edit.setValidator(numeric_validator)
            edit.setMaxLength(4)
            manual_layout.addWidget(edit)
        companion_root.addWidget(QLabel(tr("Manual Location")))
        companion_root.addWidget(manual_row)

        filters_row = QGridLayout()
        self.hide_black_empty_checkbox = QCheckBox(tr("Hide Black Empty Buttons"))
        self.hide_black_empty_checkbox.setChecked(bool(hide_black_empty))
        self.hide_navigation_checkbox = QCheckBox(tr("Hide Page Buttons"))
        self.search_edit = QLineEdit(self)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText(tr("Search by location or button text"))
        filters_row.addWidget(self.hide_black_empty_checkbox, 0, 0)
        filters_row.addWidget(self.hide_navigation_checkbox, 0, 1)
        filters_row.addWidget(QLabel(tr("Search:")), 1, 0)
        filters_row.addWidget(self.search_edit, 1, 1)
        companion_root.addLayout(filters_row)

        self.help_label = QLabel(
            tr("Pick a Companion Available Command below. If your command is missing, open Available Commands or Virtual Satellite first so pySSP can learn it.")
        )
        self.help_label.setWordWrap(True)
        companion_root.addWidget(self.help_label, 0)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr("Location"), tr("Type"), tr("Button")])
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        companion_root.addWidget(self.table, 1)

        self.command_text_label = QLabel("")
        self.command_text_label.setWordWrap(True)
        companion_root.addWidget(self.command_text_label, 0)
        self.source_tabs.addTab(companion_page, tr("Companion"))

        internal_page = QWidget(self)
        internal_root = QHBoxLayout(internal_page)
        internal_root.setContentsMargins(0, 0, 0, 0)
        internal_root.setSpacing(8)

        self.internal_command_list = QListWidget(self)
        self.internal_command_list.setSelectionMode(QAbstractItemView.SingleSelection)
        internal_root.addWidget(self.internal_command_list, 1)

        internal_form_panel = QWidget(self)
        internal_form_layout = QVBoxLayout(internal_form_panel)
        internal_form_layout.setContentsMargins(0, 0, 0, 0)
        internal_form_layout.setSpacing(6)
        self.internal_help_label = QLabel(tr("Pick one pySSP internal command, then adjust its parameters on the right."))
        self.internal_help_label.setWordWrap(True)
        internal_form_layout.addWidget(self.internal_help_label)
        self.internal_summary_label = QLabel("-")
        self.internal_summary_label.setWordWrap(True)
        internal_form_layout.addWidget(self.internal_summary_label)
        self.internal_form = QFormLayout()
        internal_form_layout.addLayout(self.internal_form)

        self.internal_mode_combo = QComboBox(self)
        self.internal_mode_combo.addItem(tr("Show"), "show")
        self.internal_mode_combo.addItem(tr("Blank"), "blank")
        self.internal_mode_combo.addItem(tr("Toggle"), "toggle")
        self.internal_toggle_mode_combo = QComboBox(self)
        self.internal_toggle_mode_combo.addItem(tr("Enable"), "enable")
        self.internal_toggle_mode_combo.addItem(tr("Disable"), "disable")
        self.internal_toggle_mode_combo.addItem(tr("Toggle"), "toggle")
        self.internal_fade_kind_combo = QComboBox(self)
        self.internal_fade_kind_combo.addItem(tr("Fade In"), "fadein")
        self.internal_fade_kind_combo.addItem(tr("Fade Out"), "fadeout")
        self.internal_fade_kind_combo.addItem(tr("Crossfade"), "crossfade")
        self.internal_reset_scope_combo = QComboBox(self)
        self.internal_reset_scope_combo.addItem(tr("Current"), "current")
        self.internal_reset_scope_combo.addItem(tr("All"), "all")
        self.internal_nav_target_combo = QComboBox(self)
        self.internal_nav_target_combo.addItem(tr("Group"), "group")
        self.internal_nav_target_combo.addItem(tr("Page"), "page")
        self.internal_nav_target_combo.addItem(tr("Sound Button"), "sound_button")
        self.internal_nav_direction_combo = QComboBox(self)
        self.internal_nav_direction_combo.addItem(tr("Next"), "next")
        self.internal_nav_direction_combo.addItem(tr("Previous"), "prev")
        self.internal_target_edit = QLineEdit(self)
        self.internal_target_edit.setPlaceholderText("A-1-1")
        self.internal_volume_spin = QSpinBox(self)
        self.internal_volume_spin.setRange(0, 100)
        self.internal_volume_spin.setSuffix("%")
        self.internal_seek_mode_combo = QComboBox(self)
        self.internal_seek_mode_combo.addItem(tr("Percent"), "percent")
        self.internal_seek_mode_combo.addItem(tr("Time"), "time")
        self.internal_seek_percent_spin = QDoubleSpinBox(self)
        self.internal_seek_percent_spin.setRange(0.0, 100.0)
        self.internal_seek_percent_spin.setDecimals(1)
        self.internal_seek_percent_spin.setSuffix("%")
        self.internal_seek_time_edit = QLineEdit(self)
        self.internal_seek_time_edit.setPlaceholderText("01:23")
        self.internal_alert_mode_combo = QComboBox(self)
        self.internal_alert_mode_combo.addItem(tr("Show Alert"), "show")
        self.internal_alert_mode_combo.addItem(tr("Clear Alert"), "clear")
        self.internal_alert_text_edit = QPlainTextEdit(self)
        self.internal_alert_text_edit.setMaximumHeight(84)
        self.internal_alert_keep_checkbox = QCheckBox(tr("Keep on screen until cleared"), self)
        self.internal_alert_keep_checkbox.setChecked(True)
        self.internal_alert_seconds_spin = QSpinBox(self)
        self.internal_alert_seconds_spin.setRange(1, 600)
        self.internal_alert_seconds_spin.setValue(10)

        self.internal_form.addRow(tr("Mode"), self.internal_mode_combo)
        self.internal_form.addRow(tr("Toggle Mode"), self.internal_toggle_mode_combo)
        self.internal_form.addRow(tr("Fade Type"), self.internal_fade_kind_combo)
        self.internal_form.addRow(tr("Scope"), self.internal_reset_scope_combo)
        self.internal_form.addRow(tr("Target"), self.internal_nav_target_combo)
        self.internal_form.addRow(tr("Direction"), self.internal_nav_direction_combo)
        self.internal_form.addRow(tr("Button / Page"), self.internal_target_edit)
        self.internal_form.addRow(tr("Volume"), self.internal_volume_spin)
        self.internal_form.addRow(tr("Seek Mode"), self.internal_seek_mode_combo)
        self.internal_form.addRow(tr("Seek Percent"), self.internal_seek_percent_spin)
        self.internal_form.addRow(tr("Seek Time"), self.internal_seek_time_edit)
        self.internal_form.addRow(tr("Alert Action"), self.internal_alert_mode_combo)
        self.internal_form.addRow(tr("Alert Text"), self.internal_alert_text_edit)
        self.internal_form.addRow("", self.internal_alert_keep_checkbox)
        self.internal_form.addRow(tr("Seconds"), self.internal_alert_seconds_spin)
        internal_form_layout.addStretch(1)
        internal_root.addWidget(internal_form_panel, 1)
        self.source_tabs.addTab(internal_page, tr("Internal"))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.table.itemSelectionChanged.connect(self._sync_selected_command)
        self.table.itemDoubleClicked.connect(lambda _item: self.accept())
        self.hide_black_empty_checkbox.toggled.connect(self._apply_filters)
        self.hide_navigation_checkbox.toggled.connect(self._apply_filters)
        self.search_edit.textChanged.connect(self._apply_filters)
        self.pick_from_list_radio.toggled.connect(self._on_location_mode_changed)
        self.caption_edit.textEdited.connect(self._on_caption_text_edited)
        self.manual_page_edit.textChanged.connect(self._sync_selected_command)
        self.manual_row_edit.textChanged.connect(self._sync_selected_command)
        self.manual_column_edit.textChanged.connect(self._sync_selected_command)
        self.source_tabs.currentChanged.connect(self._sync_selected_command)
        self.internal_command_list.currentRowChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_toggle_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_fade_kind_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_reset_scope_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_nav_target_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_nav_direction_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_target_edit.textChanged.connect(self._sync_selected_command)
        self.internal_volume_spin.valueChanged.connect(lambda _value: self._sync_selected_command())
        self.internal_seek_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_seek_percent_spin.valueChanged.connect(lambda _value: self._sync_selected_command())
        self.internal_seek_time_edit.textChanged.connect(self._sync_selected_command)
        self.internal_alert_mode_combo.currentIndexChanged.connect(lambda _row: self._sync_selected_command())
        self.internal_alert_text_edit.textChanged.connect(self._sync_selected_command)
        self.internal_alert_keep_checkbox.toggled.connect(self._sync_selected_command)
        self.internal_alert_seconds_spin.valueChanged.connect(lambda _value: self._sync_selected_command())

        self._midi_binding = normalize_midi_binding(sound_midi_hotkey)
        self._midi_learning = False
        selected_ids = [str(v).strip() for v in (selected_midi_input_device_ids or []) if str(v).strip()]
        available_by_id = {
            str(device_id).strip(): str(device_name).strip()
            for device_id, device_name in (available_midi_input_devices or [])
        }
        allowed: set[str] = set()
        for value in selected_ids:
            if value.startswith("name::"):
                allowed.add(value)
            elif value in available_by_id:
                allowed.add(midi_input_name_selector(available_by_id[value]))
        self._allowed_midi_selectors = allowed

        manual_parts = [part.strip() for part in self._spec.location.split("/", 2)]
        if len(manual_parts) == 3:
            self.manual_page_edit.setText(manual_parts[0])
            self.manual_row_edit.setText(manual_parts[1])
            self.manual_column_edit.setText(manual_parts[2])

        self._apply_filters()
        self._populate_internal_command_list()
        if self._spec.location and self._find_location_row(self._spec.location) < 0:
            self.manual_location_radio.setChecked(True)
        elif self.table.rowCount() > 0:
            self.pick_from_list_radio.setChecked(True)
        else:
            self.manual_location_radio.setChecked(True)
        if self._spec.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
            self._apply_internal_spec(self._spec)
            self.source_tabs.setCurrentIndex(1)
        else:
            self.source_tabs.setCurrentIndex(0)
        self._on_location_mode_changed()
        self._sync_selected_command()
        self._apply_selection_only_mode()
        localize_widget_tree(self, language)

    def values(self) -> tuple[str, str, AutomationCommandSpec, Optional[str], str, str]:
        spec = self._selected_spec_from_ui()
        caption = self.caption_edit.text().strip() or automation_display_name(spec)
        return (
            caption,
            self.notes_edit.text().strip(),
            spec,
            self._custom_color or None,
            self.sound_hotkey_edit.hotkey(),
            self._midi_binding,
        )

    def selected_location(self) -> str:
        if self.source_tabs.currentIndex() == 1:
            return ""
        if self.manual_location_radio.isChecked():
            parts = [
                str(self.manual_page_edit.text() or "").strip(),
                str(self.manual_row_edit.text() or "").strip(),
                str(self.manual_column_edit.text() or "").strip(),
            ]
            if not all(parts):
                return self._spec.location
            return "/".join(parts)
        row = int(self.table.currentRow())
        if row < 0:
            return self._spec.location
        item = self.table.item(row, 0)
        if item is None:
            return self._spec.location
        return str(item.data(Qt.UserRole) or item.text() or "").strip()

    def selected_button_text(self) -> str:
        if self.source_tabs.currentIndex() == 1:
            return ""
        if self.manual_location_radio.isChecked():
            return ""
        row = int(self.table.currentRow())
        if row < 0:
            return self._spec.button_text
        item = self.table.item(row, 2)
        if item is None:
            return self._spec.button_text
        return str(item.data(Qt.UserRole) or item.text() or "").strip()

    def handle_midi_message(
        self,
        token: str,
        source_selector: str = "",
        status: int = 0,
        data1: int = 0,
        data2: int = 0,
    ) -> bool:
        if not self._midi_learning:
            return False
        if self._allowed_midi_selectors:
            if not source_selector or source_selector not in self._allowed_midi_selectors:
                return False
        self._on_midi_binding(token, source_selector)
        return True

    def _apply_filters(self) -> None:
        rows = list_companion_available_commands(self._payload)
        if self.hide_black_empty_checkbox.isChecked():
            rows = [entry for entry in rows if not is_black_empty_command(entry)]
        if self.hide_navigation_checkbox.isChecked():
            rows = [entry for entry in rows if not is_navigation_command(entry)]
        query = str(self.search_edit.text() or "").strip().lower()
        if query:
            rows = [
                entry
                for entry in rows
                if query in f"{entry.get('page', '')}/{entry.get('row', '')}/{entry.get('column', '')}".lower()
                or query in str(entry.get("text", "") or "").lower()
            ]
        previous_location = self.selected_location()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        selected_row = -1
        for row_index, entry in enumerate(rows):
            location_value = f"{entry.get('page', '')}/{entry.get('row', '')}/{entry.get('column', '')}"
            location_item = QTableWidgetItem(location_value)
            location_item.setTextAlignment(Qt.AlignCenter)
            location_item.setData(Qt.UserRole, location_value)
            self.table.setItem(row_index, 0, location_item)

            type_item = QTableWidgetItem(str(entry.get("type", "") or ""))
            type_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_index, 1, type_item)

            text_value = str(entry.get("text", "") or "")
            button_item = QTableWidgetItem(text_value)
            button_item.setData(Qt.UserRole, text_value)
            color = QColor(str(entry.get("color", "") or ""))
            if color.isValid():
                button_item.setBackground(color)
                button_item.setForeground(QColor(255 - color.red(), 255 - color.green(), 255 - color.blue()))
            self.table.setItem(row_index, 2, button_item)
            if location_value == previous_location:
                selected_row = row_index
        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif self.table.rowCount() > 0:
            fallback_row = self._find_location_row(self._spec.location)
            self.table.selectRow(fallback_row if fallback_row >= 0 else 0)
        self._sync_selected_command()

    def _find_location_row(self, location: str) -> int:
        target = str(location or "").strip()
        if not target:
            return -1
        for row_index in range(self.table.rowCount()):
            item = self.table.item(row_index, 0)
            if item is not None and str(item.data(Qt.UserRole) or item.text() or "").strip() == target:
                return row_index
        return -1

    def _sync_selected_command(self) -> None:
        self._refresh_internal_form_visibility()
        spec = self._selected_spec_from_ui()
        self.location_value_label.setText(automation_display_name(spec) or "-")
        if spec.source == AUTOMATION_COMMAND_SOURCE_INTERNAL:
            self.command_text_label.setText(automation_spec_detail_text(spec))
            self.internal_summary_label.setText(automation_display_name(spec) or "-")
        else:
            button_text = self.selected_button_text()
            self.command_text_label.setText(
                button_text or (tr("Manual location entry") if self.manual_location_radio.isChecked() else "")
            )
        self._update_caption_auto_value(automation_display_name(spec))
        self._spec = spec

    def _update_caption_auto_value(self, value: str) -> None:
        new_auto_value = str(value or "").strip()
        current_caption = self.caption_edit.text().strip()
        should_update = (not self._caption_user_edited) or (current_caption == self._caption_auto_value)
        self._caption_auto_value = new_auto_value
        if should_update:
            self.caption_edit.setText(new_auto_value)
            self._caption_user_edited = False

    def _on_caption_text_edited(self, _text: str) -> None:
        self._caption_user_edited = True

    def _on_location_mode_changed(self) -> None:
        use_picker = self.pick_from_list_radio.isChecked()
        self.hide_black_empty_checkbox.setEnabled(use_picker)
        self.hide_navigation_checkbox.setEnabled(use_picker)
        self.search_edit.setEnabled(use_picker)
        self.table.setEnabled(use_picker)
        self.manual_page_edit.setEnabled(not use_picker)
        self.manual_row_edit.setEnabled(not use_picker)
        self.manual_column_edit.setEnabled(not use_picker)
        self._sync_selected_command()

    def _populate_internal_command_list(self) -> None:
        self.internal_command_list.clear()
        for entry in list_internal_automation_commands():
            label = f"{entry.get('category', '')}: {entry.get('label', '')}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(entry.get("id", "") or "").strip())
            self.internal_command_list.addItem(item)
        if self.internal_command_list.count() > 0 and self.internal_command_list.currentRow() < 0:
            self.internal_command_list.setCurrentRow(0)

    def _selected_internal_command_id(self) -> str:
        item = self.internal_command_list.currentItem()
        if item is None:
            return ""
        return normalize_internal_automation_command_id(item.data(Qt.UserRole))

    def _selected_spec_from_ui(self) -> AutomationCommandSpec:
        if self.source_tabs.currentIndex() == 1:
            command_id = self._selected_internal_command_id()
            params = self._selected_internal_params(command_id)
            return normalize_automation_spec(
                {
                    "source": AUTOMATION_COMMAND_SOURCE_INTERNAL,
                    "internal_command": command_id,
                    "internal_params": params,
                }
            )
        return normalize_automation_spec(
            {
                "source": AUTOMATION_COMMAND_SOURCE_COMPANION,
                "location": self.selected_location(),
                "button_text": self.selected_button_text(),
                "hold_to_release": bool(self.hold_to_release_checkbox.isChecked()),
            }
        )

    def _selected_internal_params(self, command_id: str) -> dict:
        params: dict[str, object] = {}
        if command_id == "lyric_display":
            params["mode"] = self.internal_mode_combo.currentData()
        elif command_id in {"vocal_removed", "talk", "playlist", "playlist_shuffle", "multiplay"}:
            params["mode"] = self.internal_toggle_mode_combo.currentData()
        elif command_id == "fade":
            params["kind"] = self.internal_fade_kind_combo.currentData()
            params["mode"] = self.internal_toggle_mode_combo.currentData()
        elif command_id == "resetpage":
            params["scope"] = self.internal_reset_scope_combo.currentData()
        elif command_id == "navigate":
            params["target"] = self.internal_nav_target_combo.currentData()
            params["direction"] = self.internal_nav_direction_combo.currentData()
        elif command_id == "play":
            params["button_id"] = self.internal_target_edit.text().strip()
        elif command_id == "goto":
            params["target"] = self.internal_target_edit.text().strip()
        elif command_id == "volume_set":
            params["level"] = int(self.internal_volume_spin.value())
        elif command_id == "seek":
            params["seek_mode"] = self.internal_seek_mode_combo.currentData()
            if params["seek_mode"] == "time":
                params["time"] = self.internal_seek_time_edit.text().strip()
            else:
                params["percent"] = float(self.internal_seek_percent_spin.value())
        elif command_id == "alert":
            params["alert_mode"] = self.internal_alert_mode_combo.currentData()
            params["text"] = self.internal_alert_text_edit.toPlainText().strip()
            params["keep"] = bool(self.internal_alert_keep_checkbox.isChecked())
            params["seconds"] = int(self.internal_alert_seconds_spin.value())
        return normalize_internal_automation_params(command_id, params)

    def _refresh_internal_form_visibility(self) -> None:
        command_id = self._selected_internal_command_id()
        is_internal = self.source_tabs.currentIndex() == 1
        widgets = [
            self.internal_mode_combo,
            self.internal_toggle_mode_combo,
            self.internal_fade_kind_combo,
            self.internal_reset_scope_combo,
            self.internal_nav_target_combo,
            self.internal_nav_direction_combo,
            self.internal_target_edit,
            self.internal_volume_spin,
            self.internal_seek_mode_combo,
            self.internal_seek_percent_spin,
            self.internal_seek_time_edit,
            self.internal_alert_mode_combo,
            self.internal_alert_text_edit,
            self.internal_alert_keep_checkbox,
            self.internal_alert_seconds_spin,
        ]
        for widget in widgets:
            label = self.internal_form.labelForField(widget)
            if label is not None:
                label.setVisible(False)
            widget.setVisible(False)
        if not is_internal:
            return
        def _show(widget):
            label = self.internal_form.labelForField(widget)
            if label is not None:
                label.setVisible(True)
            widget.setVisible(True)
        if command_id == "lyric_display":
            _show(self.internal_mode_combo)
        elif command_id in {"vocal_removed", "talk", "playlist", "playlist_shuffle", "multiplay"}:
            _show(self.internal_toggle_mode_combo)
        elif command_id == "fade":
            _show(self.internal_fade_kind_combo)
            _show(self.internal_toggle_mode_combo)
        elif command_id == "resetpage":
            _show(self.internal_reset_scope_combo)
        elif command_id == "navigate":
            _show(self.internal_nav_target_combo)
            _show(self.internal_nav_direction_combo)
        elif command_id in {"play", "goto"}:
            _show(self.internal_target_edit)
        elif command_id == "volume_set":
            _show(self.internal_volume_spin)
        elif command_id == "seek":
            _show(self.internal_seek_mode_combo)
            if self.internal_seek_mode_combo.currentData() == "time":
                _show(self.internal_seek_time_edit)
            else:
                _show(self.internal_seek_percent_spin)
        elif command_id == "alert":
            _show(self.internal_alert_mode_combo)
            if self.internal_alert_mode_combo.currentData() == "show":
                _show(self.internal_alert_text_edit)
                _show(self.internal_alert_keep_checkbox)
                if not self.internal_alert_keep_checkbox.isChecked():
                    _show(self.internal_alert_seconds_spin)

    def _apply_internal_spec(self, spec: AutomationCommandSpec) -> None:
        normalized = normalize_automation_spec(spec)
        if normalized.source != AUTOMATION_COMMAND_SOURCE_INTERNAL:
            return
        for row in range(self.internal_command_list.count()):
            item = self.internal_command_list.item(row)
            if item is not None and str(item.data(Qt.UserRole) or "").strip() == normalized.internal_command:
                self.internal_command_list.setCurrentRow(row)
                break
        params = normalize_internal_automation_params(normalized.internal_command, normalized.internal_params or {})
        self.internal_mode_combo.setCurrentIndex(max(0, self.internal_mode_combo.findData(params.get("mode", "show"))))
        self.internal_toggle_mode_combo.setCurrentIndex(max(0, self.internal_toggle_mode_combo.findData(params.get("mode", "toggle"))))
        self.internal_fade_kind_combo.setCurrentIndex(max(0, self.internal_fade_kind_combo.findData(params.get("kind", "fadein"))))
        self.internal_reset_scope_combo.setCurrentIndex(max(0, self.internal_reset_scope_combo.findData(params.get("scope", "current"))))
        self.internal_nav_target_combo.setCurrentIndex(max(0, self.internal_nav_target_combo.findData(params.get("target", "page"))))
        self.internal_nav_direction_combo.setCurrentIndex(max(0, self.internal_nav_direction_combo.findData(params.get("direction", "next"))))
        self.internal_target_edit.setText(str(params.get("button_id", params.get("target", "")) or ""))
        self.internal_volume_spin.setValue(int(params.get("level", 0) or 0))
        self.internal_seek_mode_combo.setCurrentIndex(max(0, self.internal_seek_mode_combo.findData(params.get("seek_mode", "percent"))))
        self.internal_seek_percent_spin.setValue(float(params.get("percent", 0.0) or 0.0))
        self.internal_seek_time_edit.setText(str(params.get("time", "") or ""))
        self.internal_alert_mode_combo.setCurrentIndex(max(0, self.internal_alert_mode_combo.findData(params.get("alert_mode", "show"))))
        self.internal_alert_text_edit.setPlainText(str(params.get("text", "") or ""))
        self.internal_alert_keep_checkbox.setChecked(bool(params.get("keep", True)))
        self.internal_alert_seconds_spin.setValue(int(params.get("seconds", 10) or 10))

    def _refresh_custom_color_button(self) -> None:
        if self._custom_color:
            self.custom_color_button.setText(self._custom_color)
            self.custom_color_button.setStyleSheet(
                "QPushButton{"
                f"background:{self._custom_color};"
                "border:1px solid #6C6C6C;"
                "min-height:26px;"
                "}"
            )
            return
        self.custom_color_button.setText(tr("(Default Colour)"))
        self.custom_color_button.setStyleSheet("")

    def _pick_custom_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self._custom_color or "#C0C0C0"), self, tr("Button Colour"))
        if not selected.isValid():
            return
        self._custom_color = selected.name().upper()
        self._refresh_custom_color_button()

    def _clear_custom_color(self) -> None:
        self._custom_color = ""
        self._refresh_custom_color_button()

    def _set_midi_binding(self, token: str) -> None:
        normalized = normalize_midi_binding(token)
        self._midi_binding = normalized
        self.sound_midi_hotkey_edit.setText(midi_binding_to_display(normalized) if normalized else "")

    def _start_midi_learn(self) -> None:
        self._midi_learning = True
        self.sound_midi_hotkey_edit.setStyleSheet("QLineEdit{border:2px solid #2E65FF;}")

    def _on_midi_binding(self, token: str, source_selector: str = "") -> None:
        if not self._midi_learning:
            return
        _prev_selector, normalized_token = split_midi_binding(token)
        if source_selector:
            self._set_midi_binding(f"{source_selector}|{normalized_token}")
        else:
            self._set_midi_binding(normalized_token)
        self._midi_learning = False
        self.sound_midi_hotkey_edit.setStyleSheet("")

    def _apply_selection_only_mode(self) -> None:
        if not self._selection_only:
            return
        if self._form is not None:
            for widget in self._selection_only_row_fields:
                label = self._form.labelForField(widget)
                if label is not None:
                    label.setVisible(False)
                widget.setVisible(False)
        self.help_label.setText(
            tr("Pick one Companion command to add to this sound button automation list.")
        )
