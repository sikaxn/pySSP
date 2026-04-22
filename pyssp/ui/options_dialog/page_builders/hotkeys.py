from __future__ import annotations

from ..shared import *
from ..widgets import *


class HotkeysPageMixin:
    def _build_hotkey_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        tabs = QTabWidget()
        tabs.addTab(self._build_system_hotkey_tab(), "System Hotkey")
        tabs.addTab(self._build_quick_action_tab(), "Quick Action Key")
        tabs.addTab(self._build_sound_button_hotkey_tab(), "Sound Button Hot Key")
        layout.addWidget(tabs, 1)
        self.hotkey_warning_label = QLabel("")
        self.hotkey_warning_label.setWordWrap(True)
        self.hotkey_warning_label.setStyleSheet("color:#B00020; font-weight:bold;")
        self.hotkey_warning_label.setVisible(False)
        layout.addWidget(self.hotkey_warning_label)
        note = QLabel("Each operation supports two hotkeys. You can clear either key.")
        note.setWordWrap(True)
        layout.addWidget(note)
        return page

    def _build_midi_control_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        tabs = QTabWidget()
        tabs.addTab(self._build_midi_settings_tab(), "Midi Setting")
        tabs.addTab(self._build_midi_system_hotkey_tab(), "System Hotkey")
        tabs.addTab(self._build_midi_system_rotary_tab(), "System Rotary")
        tabs.addTab(self._build_midi_quick_action_tab(), "Quick Action Key")
        tabs.addTab(self._build_midi_sound_button_hotkey_tab(), "Sound Button Hot Key")
        layout.addWidget(tabs, 1)
        self._midi_warning_label = QLabel("")
        self._midi_warning_label.setWordWrap(True)
        self._midi_warning_label.setStyleSheet("color:#B00020; font-weight:bold;")
        self._midi_warning_label.setVisible(False)
        layout.addWidget(self._midi_warning_label)
        return page

    def _build_midi_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        hint = QLabel("Select one or more MIDI input devices. pySSP will listen on all selected devices.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.midi_input_status_label = QLabel("")
        self.midi_input_status_label.setWordWrap(True)
        self.midi_input_status_label.setStyleSheet("color:#B00020; font-weight:bold;")
        self.midi_input_status_label.setVisible(False)
        layout.addWidget(self.midi_input_status_label)
        self.midi_input_list = QListWidget()
        self.midi_input_list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.midi_input_list, 1)
        button_row = QHBoxLayout()
        self.midi_refresh_btn = QPushButton("Refresh")
        self.midi_refresh_btn.clicked.connect(lambda: self._refresh_midi_input_devices(force_refresh=True))
        button_row.addWidget(self.midi_refresh_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        mtc_group = QGroupBox("MIDI Timecode (MTC)")
        mtc_group.setEnabled(False)
        mtc_layout = QVBoxLayout(mtc_group)
        mtc_note = QLabel("Configure MTC output in Audio Device & Timecode.")
        mtc_note.setWordWrap(True)
        mtc_layout.addWidget(mtc_note)
        layout.addWidget(mtc_group)
        self._refresh_midi_input_devices()
        return page

    def _build_midi_system_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for key, label in self._HOTKEY_ROWS:
            self._add_midi_row(form, key, label)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_midi_system_rotary_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.midi_rotary_enabled_checkbox = QCheckBox("Enable System Rotary MIDI Control")
        self.midi_rotary_enabled_checkbox.setChecked(self._midi_rotary_enabled)
        layout.addWidget(self.midi_rotary_enabled_checkbox)

        form = QFormLayout()
        self.midi_rotary_group_edit = MidiCaptureEdit()
        self.midi_rotary_group_edit.setBinding(self._midi_rotary_group_binding)
        form.addRow("Group Rotary:", self._build_midi_learn_row(self.midi_rotary_group_edit, rotary=True))
        self.midi_rotary_group_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_group_invert_checkbox.setChecked(self._midi_rotary_group_invert)
        self.midi_rotary_group_sensitivity_spin = QSpinBox()
        self.midi_rotary_group_sensitivity_spin.setRange(1, 20)
        self.midi_rotary_group_sensitivity_spin.setValue(self._midi_rotary_group_sensitivity)
        form.addRow(
            "Group Options:",
            self._build_rotary_option_row(self.midi_rotary_group_invert_checkbox, self.midi_rotary_group_sensitivity_spin),
        )

        self.midi_rotary_page_edit = MidiCaptureEdit()
        self.midi_rotary_page_edit.setBinding(self._midi_rotary_page_binding)
        form.addRow("Page Rotary:", self._build_midi_learn_row(self.midi_rotary_page_edit, rotary=True))
        self.midi_rotary_page_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_page_invert_checkbox.setChecked(self._midi_rotary_page_invert)
        self.midi_rotary_page_sensitivity_spin = QSpinBox()
        self.midi_rotary_page_sensitivity_spin.setRange(1, 20)
        self.midi_rotary_page_sensitivity_spin.setValue(self._midi_rotary_page_sensitivity)
        form.addRow(
            "Page Options:",
            self._build_rotary_option_row(self.midi_rotary_page_invert_checkbox, self.midi_rotary_page_sensitivity_spin),
        )

        self.midi_rotary_sound_button_edit = MidiCaptureEdit()
        self.midi_rotary_sound_button_edit.setBinding(self._midi_rotary_sound_button_binding)
        form.addRow("Sound Button Rotary:", self._build_midi_learn_row(self.midi_rotary_sound_button_edit, rotary=True))
        self.midi_rotary_sound_button_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_sound_button_invert_checkbox.setChecked(self._midi_rotary_sound_button_invert)
        self.midi_rotary_sound_button_sensitivity_spin = QSpinBox()
        self.midi_rotary_sound_button_sensitivity_spin.setRange(1, 20)
        self.midi_rotary_sound_button_sensitivity_spin.setValue(self._midi_rotary_sound_button_sensitivity)
        form.addRow(
            "Sound Button Options:",
            self._build_rotary_option_row(
                self.midi_rotary_sound_button_invert_checkbox,
                self.midi_rotary_sound_button_sensitivity_spin,
            ),
        )

        self.midi_rotary_volume_edit = MidiCaptureEdit()
        self.midi_rotary_volume_edit.setBinding(self._midi_rotary_volume_binding)
        form.addRow("Volume Control:", self._build_midi_learn_row(self.midi_rotary_volume_edit, rotary=True))
        self.midi_rotary_volume_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_volume_invert_checkbox.setChecked(self._midi_rotary_volume_invert)
        form.addRow("Volume Options:", self._build_rotary_invert_row(self.midi_rotary_volume_invert_checkbox))

        self.midi_rotary_jog_edit = MidiCaptureEdit()
        self.midi_rotary_jog_edit.setBinding(self._midi_rotary_jog_binding)
        form.addRow("Jog Control:", self._build_midi_learn_row(self.midi_rotary_jog_edit, rotary=True))
        self.midi_rotary_jog_invert_checkbox = QCheckBox("Invert")
        self.midi_rotary_jog_invert_checkbox.setChecked(self._midi_rotary_jog_invert)
        form.addRow("Jog Options:", self._build_rotary_invert_row(self.midi_rotary_jog_invert_checkbox))

        self.midi_rotary_volume_mode_combo = QComboBox()
        self.midi_rotary_volume_mode_combo.addItem("Relative (rotary encoder)", "relative")
        self.midi_rotary_volume_mode_combo.addItem("Absolute (slider/fader)", "absolute")
        self._set_combo_data_or_default(self.midi_rotary_volume_mode_combo, self._midi_rotary_volume_mode, "relative")
        form.addRow("Volume Mode:", self.midi_rotary_volume_mode_combo)

        self.midi_rotary_volume_step_spin = QSpinBox()
        self.midi_rotary_volume_step_spin.setRange(1, 20)
        self.midi_rotary_volume_step_spin.setValue(self._midi_rotary_volume_step)
        form.addRow("Volume Relative Step:", self.midi_rotary_volume_step_spin)

        self.midi_rotary_jog_step_spin = QSpinBox()
        self.midi_rotary_jog_step_spin.setRange(10, 5000)
        self.midi_rotary_jog_step_spin.setSuffix(" ms")
        self.midi_rotary_jog_step_spin.setValue(self._midi_rotary_jog_step_ms)
        form.addRow("Jog Relative Step:", self.midi_rotary_jog_step_spin)

        layout.addLayout(form)
        note = QLabel("Rotary learns Control Change (CC) by control number. For direction, pySSP uses CC value.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _build_rotary_invert_row(self, invert_checkbox: QCheckBox) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(invert_checkbox)
        row_layout.addStretch(1)
        return row

    def _build_rotary_option_row(self, invert_checkbox: QCheckBox, sensitivity_spin: QSpinBox) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(invert_checkbox)
        row_layout.addSpacing(8)
        row_layout.addWidget(QLabel("Sensitivity:"))
        row_layout.addWidget(sensitivity_spin)
        row_layout.addStretch(1)
        return row

    def _build_midi_learn_row(self, edit: MidiCaptureEdit, rotary: bool = False) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        learn_btn = QPushButton("Learn")
        clear_btn = QPushButton("Clear")
        learn_btn.setFixedWidth(62)
        clear_btn.setFixedWidth(56)
        if rotary:
            learn_btn.clicked.connect(lambda _=False, e=edit: self._start_midi_rotary_learning(e))
        else:
            learn_btn.clicked.connect(lambda _=False, e=edit: self._start_midi_learning(e))
        clear_btn.clicked.connect(lambda _=False, e=edit: e.setBinding(""))
        row_layout.addWidget(edit, 1)
        row_layout.addWidget(learn_btn)
        row_layout.addWidget(clear_btn)
        return row

    def _build_midi_quick_action_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.midi_quick_action_enabled_checkbox = QCheckBox("Enable MIDI Quick Action")
        self.midi_quick_action_enabled_checkbox.setChecked(self._midi_quick_action_enabled)
        self.midi_quick_action_enabled_checkbox.toggled.connect(self._validate_midi_conflicts)
        layout.addWidget(self.midi_quick_action_enabled_checkbox)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for i in range(48):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            edit = MidiCaptureEdit()
            edit.setBinding(self._midi_quick_action_bindings[i])
            edit.textChanged.connect(self._validate_midi_conflicts)
            learn_btn = QPushButton("Learn")
            clear_btn = QPushButton("Clear")
            learn_btn.setFixedWidth(62)
            clear_btn.setFixedWidth(56)
            learn_btn.clicked.connect(lambda _=False, e=edit: self._start_midi_learning(e))
            clear_btn.clicked.connect(lambda _=False, e=edit: e.setBinding(""))
            row_layout.addWidget(edit, 1)
            row_layout.addWidget(learn_btn)
            row_layout.addWidget(clear_btn)
            self._midi_quick_action_edits.append(edit)
            form.addRow(f"{tr('Button ')}{i + 1}:", row)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_midi_sound_button_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.midi_sound_button_hotkey_enabled_checkbox = QCheckBox("Enable Sound Button MIDI Hot Key")
        self.midi_sound_button_hotkey_enabled_checkbox.setChecked(self._midi_sound_button_hotkey_enabled)
        layout.addWidget(self.midi_sound_button_hotkey_enabled_checkbox)

        prio_group = QGroupBox("Priority")
        prio_layout = QVBoxLayout(prio_group)
        self.midi_sound_hotkey_priority_sound_first_radio = QRadioButton("Sound Button MIDI Hot Key has highest priority")
        self.midi_sound_hotkey_priority_system_first_radio = QRadioButton(
            "System MIDI Hotkey and Quick Action have highest priority"
        )
        if self._midi_sound_button_hotkey_priority == "sound_button_first":
            self.midi_sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.midi_sound_hotkey_priority_system_first_radio.setChecked(True)
        prio_layout.addWidget(self.midi_sound_hotkey_priority_sound_first_radio)
        prio_layout.addWidget(self.midi_sound_hotkey_priority_system_first_radio)
        layout.addWidget(prio_group)

        self.midi_sound_button_go_to_playing_checkbox = QCheckBox("Go To Playing after trigger")
        self.midi_sound_button_go_to_playing_checkbox.setChecked(self._midi_sound_button_hotkey_go_to_playing)
        layout.addWidget(self.midi_sound_button_go_to_playing_checkbox)
        note = QLabel("Assign per-button MIDI hotkeys in Edit Sound Button.")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

    def _add_midi_row(self, form: QFormLayout, key: str, label: str) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        edit1 = MidiCaptureEdit()
        edit2 = MidiCaptureEdit()
        v1, v2 = self._midi_hotkeys.get(key, ("", ""))
        edit1.setBinding(v1)
        edit2.setBinding(v2)
        learn1 = QPushButton("Learn")
        clear1 = QPushButton("Clear")
        learn2 = QPushButton("Learn")
        clear2 = QPushButton("Clear")
        for btn in (learn1, clear1, learn2, clear2):
            btn.setFixedWidth(56 if btn.text() == "Clear" else 62)
        learn1.clicked.connect(lambda _=False, e=edit1: self._start_midi_learning(e))
        clear1.clicked.connect(lambda _=False, e=edit1: e.setBinding(""))
        learn2.clicked.connect(lambda _=False, e=edit2: self._start_midi_learning(e))
        clear2.clicked.connect(lambda _=False, e=edit2: e.setBinding(""))
        edit1.textChanged.connect(self._validate_midi_conflicts)
        edit2.textChanged.connect(self._validate_midi_conflicts)
        row_layout.addWidget(edit1, 1)
        row_layout.addWidget(learn1)
        row_layout.addWidget(clear1)
        row_layout.addWidget(edit2, 1)
        row_layout.addWidget(learn2)
        row_layout.addWidget(clear2)
        self._midi_hotkey_edits[key] = (edit1, edit2)
        form.addRow(f"{tr(label)}:", row)

    def _build_system_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for key, label in self._HOTKEY_ROWS:
            self._add_hotkey_row(form, key, label)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_quick_action_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.quick_action_enabled_checkbox = QCheckBox("Enable Quick Action Key (assign broadcast short key)")
        self.quick_action_enabled_checkbox.setChecked(self._quick_action_enabled)
        self.quick_action_enabled_checkbox.toggled.connect(self._validate_hotkey_conflicts)
        layout.addWidget(self.quick_action_enabled_checkbox)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form = QFormLayout(container)
        for i in range(48):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            edit = HotkeyCaptureEdit()
            edit.setHotkey(self._quick_action_keys[i])
            edit.textChanged.connect(self._validate_hotkey_conflicts)
            clear_btn = QPushButton("Clear")
            clear_btn.setFixedWidth(56)
            clear_btn.clicked.connect(lambda _=False, e=edit: e.setHotkey(""))
            row_layout.addWidget(edit)
            row_layout.addWidget(clear_btn)
            self._quick_action_edits.append(edit)
            form.addRow(f"{tr('Button ')}{i + 1}:", row)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def _build_sound_button_hotkey_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.sound_button_hotkey_enabled_checkbox = QCheckBox("Enable Sound Button Hot Key")
        self.sound_button_hotkey_enabled_checkbox.setChecked(self._sound_button_hotkey_enabled)
        self.sound_button_hotkey_enabled_checkbox.toggled.connect(self._validate_hotkey_conflicts)
        layout.addWidget(self.sound_button_hotkey_enabled_checkbox)

        prio_group = QGroupBox("Priority")
        prio_layout = QVBoxLayout(prio_group)
        self.sound_hotkey_priority_sound_first_radio = QRadioButton("Sound Button Hot Key has highest priority")
        self.sound_hotkey_priority_system_first_radio = QRadioButton(
            "System Hotkey and Quick Action Key have highest priority"
        )
        if self._sound_button_hotkey_priority == "sound_button_first":
            self.sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.sound_hotkey_priority_system_first_radio.setChecked(True)
        prio_layout.addWidget(self.sound_hotkey_priority_sound_first_radio)
        prio_layout.addWidget(self.sound_hotkey_priority_system_first_radio)
        layout.addWidget(prio_group)

        self.sound_button_go_to_playing_checkbox = QCheckBox("Go To Playing after trigger")
        self.sound_button_go_to_playing_checkbox.setChecked(self._sound_button_hotkey_go_to_playing)
        layout.addWidget(self.sound_button_go_to_playing_checkbox)
        layout.addStretch(1)
        return page

    def _add_hotkey_row(self, form: QFormLayout, key: str, label: str) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        edit1 = HotkeyCaptureEdit()
        edit2 = HotkeyCaptureEdit()
        clear1 = QPushButton("Clear")
        clear2 = QPushButton("Clear")
        clear1.setFixedWidth(56)
        clear2.setFixedWidth(56)
        v1, v2 = self._hotkeys.get(key, ("", ""))
        edit1.setHotkey(v1)
        edit2.setHotkey(v2)
        clear1.clicked.connect(lambda _=False, e=edit1: e.setHotkey(""))
        clear2.clicked.connect(lambda _=False, e=edit2: e.setHotkey(""))
        edit1.textChanged.connect(self._validate_hotkey_conflicts)
        edit2.textChanged.connect(self._validate_hotkey_conflicts)
        row_layout.addWidget(edit1)
        row_layout.addWidget(clear1)
        row_layout.addWidget(edit2)
        row_layout.addWidget(clear2)
        self._hotkey_edits[key] = (edit1, edit2)
        form.addRow(f"{tr(label)}:", row)

