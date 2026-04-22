from __future__ import annotations

from ..shared import *
from ..widgets import *


class DisplayPageMixin:
    @classmethod
    def _normalize_stage_display_layout(cls, values: List[str]) -> List[str]:
        gadgets = normalize_stage_display_gadgets({}, legacy_layout=values)
        order, _visibility = gadgets_to_legacy_layout_visibility(gadgets)
        return order

    @classmethod
    def _normalize_stage_display_visibility(cls, values: Dict[str, bool]) -> Dict[str, bool]:
        gadgets = normalize_stage_display_gadgets({}, legacy_visibility=values)
        _order, visibility = gadgets_to_legacy_layout_visibility(gadgets)
        return visibility

    def _build_display_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        source_form = QFormLayout()
        self.display_text_source_combo = QComboBox()
        self.display_text_source_combo.addItem("Caption", "caption")
        self.display_text_source_combo.addItem("Filename", "filename")
        self.display_text_source_combo.addItem("Note", "note")
        self._set_combo_data_or_default(self.display_text_source_combo, self._stage_display_text_source, "caption")
        source_form.addRow("Now/Next Text Source:", self.display_text_source_combo)
        layout.addLayout(source_form)

        tip = QLabel("Drag and resize gadgets in the preview. Toggle visibility, then save to apply to Stage Display.")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        body = QHBoxLayout()
        toggles = QGroupBox("Gadgets")
        toggles_layout = QGridLayout(toggles)
        toggles_layout.setContentsMargins(6, 6, 6, 6)
        toggles_layout.setHorizontalSpacing(6)
        toggles_layout.setVerticalSpacing(4)
        self._display_gadget_table_layout = toggles_layout
        self._display_gadget_checks: Dict[str, QCheckBox] = {}
        self._display_alert_edit_visibility_button: Optional[QPushButton] = None
        self._display_gadget_hide_text_checks: Dict[str, QCheckBox] = {}
        self._display_gadget_hide_border_checks: Dict[str, QCheckBox] = {}
        self._display_gadget_orientation_combos: Dict[str, QComboBox] = {}
        self._display_gadget_name_labels: Dict[str, QLabel] = {}
        self._display_gadget_visibility_widgets: Dict[str, QWidget] = {}
        self._display_gadget_layer_cells: Dict[str, QWidget] = {}
        self._display_gadget_layer_labels: Dict[str, QLabel] = {}
        self._display_gadget_layer_up_buttons: Dict[str, QPushButton] = {}
        self._display_gadget_layer_down_buttons: Dict[str, QPushButton] = {}
        labels = dict(self._DISPLAY_OPTION_SPECS)
        header_style = "font-weight:bold; color:#666666;"
        for col, text in enumerate(["Gadget", "Visible / Edit", "Hide Text", "Hide Border", "Orientation", "Layer"]):
            header = QLabel(text)
            header.setStyleSheet(header_style)
            header.setMaximumHeight(18)
            toggles_layout.addWidget(header, 0, col)
        for row, (key, _label) in enumerate(self._DISPLAY_OPTION_SPECS, start=1):
            name_label = QLabel(labels.get(key, key))
            toggles_layout.addWidget(name_label, row, 0)
            self._display_gadget_name_labels[key] = name_label
            if key == "alert":
                edit_button = QPushButton("")
                edit_button.clicked.connect(lambda _=False: self._toggle_alert_edit_visibility())
                toggles_layout.addWidget(edit_button, row, 1)
                self._display_alert_edit_visibility_button = edit_button
                self._display_gadget_visibility_widgets[key] = edit_button
            else:
                checkbox = QCheckBox(labels.get(key, key))
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("visible", True)))
                checkbox.toggled.connect(
                    lambda checked, token=key: self.display_layout_editor.set_gadget_visible(token, bool(checked))
                )
                checkbox.setText("")
                toggles_layout.addWidget(checkbox, row, 1)
                self._display_gadget_checks[key] = checkbox
                self._display_gadget_visibility_widgets[key] = checkbox

            hide_text_checkbox = QCheckBox("")
            hide_text_checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_text", False)))
            hide_text_checkbox.toggled.connect(
                lambda checked, token=key: self.display_layout_editor.set_gadget_hide_text(token, bool(checked))
            )
            toggles_layout.addWidget(hide_text_checkbox, row, 2)
            self._display_gadget_hide_text_checks[key] = hide_text_checkbox

            hide_border_checkbox = QCheckBox("")
            hide_border_checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_border", False)))
            hide_border_checkbox.toggled.connect(
                lambda checked, token=key: self.display_layout_editor.set_gadget_hide_border(token, bool(checked))
            )
            toggles_layout.addWidget(hide_border_checkbox, row, 3)
            self._display_gadget_hide_border_checks[key] = hide_border_checkbox

            orientation_combo = QComboBox()
            orientation_combo.addItem("Horizontal", "horizontal")
            orientation_combo.addItem("Vertical", "vertical")
            token = str(self._stage_display_gadgets.get(key, {}).get("orientation", "vertical")).strip().lower()
            if token not in {"horizontal", "vertical"}:
                token = "vertical"
            orientation_combo.setCurrentIndex(max(0, orientation_combo.findData(token)))
            orientation_combo.currentIndexChanged.connect(
                lambda _idx, combo=orientation_combo, gadget_key=key: self.display_layout_editor.set_gadget_orientation(
                    gadget_key,
                    str(combo.currentData() or "vertical"),
                )
            )
            toggles_layout.addWidget(orientation_combo, row, 4)
            self._display_gadget_orientation_combos[key] = orientation_combo

            layer_cell = QWidget()
            layer_cell_layout = QHBoxLayout(layer_cell)
            layer_cell_layout.setContentsMargins(0, 0, 0, 0)
            layer_cell_layout.setSpacing(4)
            up_btn = QPushButton("Up")
            down_btn = QPushButton("Down")
            layer_label = QLabel("")
            layer_label.setAlignment(Qt.AlignCenter)
            up_btn.clicked.connect(lambda _=False, token=key: self._move_display_layer(token, -1))
            down_btn.clicked.connect(lambda _=False, token=key: self._move_display_layer(token, 1))
            layer_cell_layout.addWidget(up_btn)
            layer_cell_layout.addWidget(down_btn)
            layer_cell_layout.addWidget(layer_label)
            toggles_layout.addWidget(layer_cell, row, 5)
            self._display_gadget_layer_cells[key] = layer_cell
            self._display_gadget_layer_labels[key] = layer_label
            self._display_gadget_layer_up_buttons[key] = up_btn
            self._display_gadget_layer_down_buttons[key] = down_btn

        self._sync_alert_edit_button_text()
        self._refresh_display_layer_table()
        body.addWidget(toggles, 0)

        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.display_layout_editor = StageDisplayLayoutEditor()
        self.display_layout_editor.set_gadgets(self._stage_display_gadgets)
        self._refresh_display_layer_table()
        preview_layout.addWidget(self.display_layout_editor, 1)
        body.addWidget(preview_group, 1)
        layout.addLayout(body, 1)

        note = QLabel("Next Song is shown when playlist mode is enabled on the active page.")
        note.setWordWrap(True)
        layout.addWidget(note)
        alert_note = QLabel("Alert gadget is always hidden on live Stage Display until an alert is sent.")
        alert_note.setWordWrap(True)
        alert_note.setStyleSheet("color:#888888;")
        layout.addWidget(alert_note)
        return page

    def _refresh_display_layer_table(self) -> None:
        if not hasattr(self, "display_layout_editor"):
            return
        base_order = self.display_layout_editor.layer_order()
        ordered = list(reversed(base_order))
        total = len(ordered)
        for idx, key in enumerate(ordered):
            row = idx + 1
            name_label = self._display_gadget_name_labels.get(key)
            vis_widget = self._display_gadget_visibility_widgets.get(key)
            hide_text_widget = self._display_gadget_hide_text_checks.get(key)
            hide_border_widget = self._display_gadget_hide_border_checks.get(key)
            orient_widget = self._display_gadget_orientation_combos.get(key)
            layer_cell = self._display_gadget_layer_cells.get(key)
            layer_label = self._display_gadget_layer_labels.get(key)
            up_btn = self._display_gadget_layer_up_buttons.get(key)
            down_btn = self._display_gadget_layer_down_buttons.get(key)
            if name_label is not None:
                self._display_gadget_table_layout.addWidget(name_label, row, 0)
            if vis_widget is not None:
                self._display_gadget_table_layout.addWidget(vis_widget, row, 1)
            if hide_text_widget is not None:
                self._display_gadget_table_layout.addWidget(hide_text_widget, row, 2)
            if hide_border_widget is not None:
                self._display_gadget_table_layout.addWidget(hide_border_widget, row, 3)
            if orient_widget is not None:
                self._display_gadget_table_layout.addWidget(orient_widget, row, 4)
            if layer_cell is not None:
                self._display_gadget_table_layout.addWidget(layer_cell, row, 5)
            if up_btn is None or down_btn is None or layer_label is None:
                continue
            layer_label.setText(f"{idx + 1}/{total}")
            up_btn.setEnabled(idx > 0)
            down_btn.setEnabled(idx < (total - 1))

    def _move_display_layer(self, key: str, delta: int) -> None:
        if not hasattr(self, "display_layout_editor"):
            return
        ordered = list(reversed(self.display_layout_editor.layer_order()))
        if key not in ordered:
            return
        idx = ordered.index(key)
        target = idx + int(delta)
        if target < 0 or target >= len(ordered):
            return
        ordered[idx], ordered[target] = ordered[target], ordered[idx]
        self.display_layout_editor.set_layer_order(list(reversed(ordered)))
        self._stage_display_gadgets = self.display_layout_editor.gadgets()
        self._refresh_display_layer_table()

    def _toggle_alert_edit_visibility(self) -> None:
        current = bool(self.display_layout_editor.gadgets().get("alert", {}).get("visible", False))
        next_value = not current
        self._stage_display_gadgets["alert"]["visible"] = next_value
        self.display_layout_editor.set_gadget_visible("alert", next_value)
        self._sync_alert_edit_button_text()

    def _sync_alert_edit_button_text(self) -> None:
        if self._display_alert_edit_visibility_button is None:
            return
        if hasattr(self, "display_layout_editor"):
            visible = bool(self.display_layout_editor.gadgets().get("alert", {}).get("visible", False))
        else:
            visible = bool(self._stage_display_gadgets.get("alert", {}).get("visible", False))
        self._display_alert_edit_visibility_button.setText("Hide for Edit" if visible else "Show for Edit")

