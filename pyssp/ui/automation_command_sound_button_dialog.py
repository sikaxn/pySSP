from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIntValidator
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyssp.automation_command import (
    AutomationCommandSpec,
    automation_display_name,
    normalize_automation_spec,
)
from pyssp.companion_available_commands import (
    is_black_empty_command,
    is_navigation_command,
    list_companion_available_commands,
)
from pyssp.i18n import localize_widget_tree, tr
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
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Automation Command Sound Button"))
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

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.caption_edit = QLineEdit(caption)
        form.addRow(tr("Caption"), self.caption_edit)

        self.notes_edit = QLineEdit(notes)
        form.addRow(tr("Notes"), self.notes_edit)

        self.location_value_label = QLabel(self._spec.location or "-")
        form.addRow(tr("Selected Command"), self.location_value_label)

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
        form.addRow(tr("Location Mode"), mode_row)

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
        form.addRow(tr("Manual Location"), manual_row)

        self.hold_to_release_checkbox = QCheckBox(tr("Respect press-down / release-up input"))
        self.hold_to_release_checkbox.setChecked(bool(self._spec.hold_to_release))
        form.addRow("", self.hold_to_release_checkbox)

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

        root.addLayout(form)

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
        root.addLayout(filters_row)

        self.help_label = QLabel(
            tr("Pick a Companion Available Command below. If your command is missing, open Available Commands or Virtual Satellite first so pySSP can learn it.")
        )
        self.help_label.setWordWrap(True)
        root.addWidget(self.help_label, 0)

        self.table = QTableWidget(self)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([tr("Location"), tr("Type"), tr("Button")])
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        self.command_text_label = QLabel("")
        self.command_text_label.setWordWrap(True)
        root.addWidget(self.command_text_label, 0)

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
        if self._spec.location and self._find_location_row(self._spec.location) < 0:
            self.manual_location_radio.setChecked(True)
        elif self.table.rowCount() > 0:
            self.pick_from_list_radio.setChecked(True)
        else:
            self.manual_location_radio.setChecked(True)
        self._on_location_mode_changed()
        self._sync_selected_command()
        localize_widget_tree(self, language)

    def values(self) -> tuple[str, str, AutomationCommandSpec, Optional[str], str, str]:
        spec = normalize_automation_spec(
            {
                "location": self.selected_location(),
                "button_text": self.selected_button_text(),
                "hold_to_release": bool(self.hold_to_release_checkbox.isChecked()),
            }
        )
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
        location = self.selected_location()
        button_text = self.selected_button_text()
        self.location_value_label.setText(location or "-")
        self.command_text_label.setText(button_text or (tr("Manual location entry") if self.manual_location_radio.isChecked() else ""))
        auto_caption = button_text or location
        self._update_caption_auto_value(auto_caption)
        self._spec = normalize_automation_spec(
            {
                "location": location,
                "button_text": button_text,
                "hold_to_release": bool(self.hold_to_release_checkbox.isChecked()),
            }
        )

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
