from __future__ import annotations

from ..shared import *
from ..widgets import *


class LockScreenPageMixin:
    def _build_lock_screen_page(
        self,
        lock_allow_quit: bool,
        lock_allow_system_hotkeys: bool,
        lock_allow_quick_action_hotkeys: bool,
        lock_allow_sound_button_hotkeys: bool,
        lock_allow_midi_control: bool,
        lock_auto_allow_quit: bool,
        lock_auto_allow_midi_control: bool,
        lock_unlock_method: str,
        lock_require_password: bool,
        lock_password: str,
        lock_restart_state: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        method_group = QGroupBox("Method of Unlock")
        method_layout = QVBoxLayout(method_group)
        self.lock_method_random_points_radio = QRadioButton("Click 3 random points")
        self.lock_method_fixed_button_radio = QRadioButton("Click one button in a fixed position")
        self.lock_method_slide_radio = QRadioButton("Slide to unlock")
        method_token = str(lock_unlock_method or "").strip().lower()
        if method_token == "click_one_button":
            self.lock_method_fixed_button_radio.setChecked(True)
        elif method_token == "slide_to_unlock":
            self.lock_method_slide_radio.setChecked(True)
        else:
            self.lock_method_random_points_radio.setChecked(True)
        method_layout.addWidget(self.lock_method_random_points_radio)
        method_layout.addWidget(self.lock_method_fixed_button_radio)
        method_layout.addWidget(self.lock_method_slide_radio)
        method_note = QLabel("Web Remote always keeps working while the lock screen is active.")
        method_note.setWordWrap(True)
        method_layout.addWidget(method_note)
        layout.addWidget(method_group)

        access_group = QGroupBox("Allow While Locked")
        access_layout = QVBoxLayout(access_group)
        self.lock_allow_quit_checkbox = QCheckBox("Allow closing pySSP while locked")
        self.lock_allow_quit_checkbox.setChecked(lock_allow_quit)
        access_layout.addWidget(self.lock_allow_quit_checkbox)
        self.lock_allow_system_hotkeys_checkbox = QCheckBox("Allow standard hotkeys while locked")
        self.lock_allow_system_hotkeys_checkbox.setChecked(lock_allow_system_hotkeys)
        access_layout.addWidget(self.lock_allow_system_hotkeys_checkbox)
        self.lock_allow_quick_action_hotkeys_checkbox = QCheckBox("Allow Quick Action keys while locked")
        self.lock_allow_quick_action_hotkeys_checkbox.setChecked(lock_allow_quick_action_hotkeys)
        access_layout.addWidget(self.lock_allow_quick_action_hotkeys_checkbox)
        self.lock_allow_sound_button_hotkeys_checkbox = QCheckBox("Allow Sound Button hotkeys while locked")
        self.lock_allow_sound_button_hotkeys_checkbox.setChecked(lock_allow_sound_button_hotkeys)
        access_layout.addWidget(self.lock_allow_sound_button_hotkeys_checkbox)
        self.lock_allow_midi_control_checkbox = QCheckBox("Allow MIDI control while locked")
        self.lock_allow_midi_control_checkbox.setChecked(lock_allow_midi_control)
        access_layout.addWidget(self.lock_allow_midi_control_checkbox)
        locked_note = QLabel("These settings apply to the regular lock screen.")
        locked_note.setWordWrap(True)
        access_layout.addWidget(locked_note)
        layout.addWidget(access_group)

        auto_access_group = QGroupBox("Allow While Auto Locked")
        auto_access_layout = QVBoxLayout(auto_access_group)
        self.lock_auto_allow_quit_checkbox = QCheckBox("Allow closing pySSP while auto locked")
        self.lock_auto_allow_quit_checkbox.setChecked(lock_auto_allow_quit)
        auto_access_layout.addWidget(self.lock_auto_allow_quit_checkbox)
        self.lock_auto_allow_midi_control_checkbox = QCheckBox("Allow MIDI control while auto locked")
        self.lock_auto_allow_midi_control_checkbox.setChecked(lock_auto_allow_midi_control)
        auto_access_layout.addWidget(self.lock_auto_allow_midi_control_checkbox)
        auto_note = QLabel("Keyboard shortcuts except Unlock are all disabled while automation lock is active.")
        auto_note.setWordWrap(True)
        auto_access_layout.addWidget(auto_note)
        layout.addWidget(auto_access_group)

        password_group = QGroupBox("Password")
        password_layout = QFormLayout(password_group)
        self.lock_require_password_checkbox = QCheckBox("Require password for unlock")
        self.lock_require_password_checkbox.setChecked(lock_require_password)
        password_layout.addRow(self.lock_require_password_checkbox)
        self.lock_password_info_label = QLabel("")
        self.lock_password_info_label.setWordWrap(True)
        password_layout.addRow(self.lock_password_info_label)
        self.lock_password_edit = QLineEdit()
        self.lock_password_edit.setEchoMode(QLineEdit.Password)
        self.lock_password_edit.setPlaceholderText("Password has been set. Start typing to change it.")
        password_layout.addRow("Password:", self.lock_password_edit)
        self.lock_password_verify_edit = QLineEdit()
        self.lock_password_verify_edit.setEchoMode(QLineEdit.Password)
        self.lock_password_verify_edit.setPlaceholderText("Re-enter new password to change it.")
        password_layout.addRow("Verify Password:", self.lock_password_verify_edit)
        self.lock_password_warning_label = QLabel(
            "Warning: this password is stored as plain text in the settings file."
        )
        self.lock_password_warning_label.setWordWrap(True)
        self.lock_password_warning_label.setStyleSheet("color:#B00020; font-weight:bold;")
        password_layout.addRow(self.lock_password_warning_label)
        self.lock_password_status_label = QLabel("")
        self.lock_password_status_label.setWordWrap(True)
        self.lock_password_status_label.setStyleSheet("color:#B00020; font-weight:bold;")
        self.lock_password_status_label.setVisible(False)
        password_layout.addRow(self.lock_password_status_label)
        layout.addWidget(password_group)

        restart_group = QGroupBox("After Restart")
        restart_layout = QVBoxLayout(restart_group)
        self.lock_restart_unlock_radio = QRadioButton("Start unlocked")
        self.lock_restart_lock_radio = QRadioButton("Start locked again if pySSP closed while locked")
        if str(lock_restart_state or "").strip().lower() == "lock_on_restart":
            self.lock_restart_lock_radio.setChecked(True)
        else:
            self.lock_restart_unlock_radio.setChecked(True)
        restart_layout.addWidget(self.lock_restart_unlock_radio)
        restart_layout.addWidget(self.lock_restart_lock_radio)
        layout.addWidget(restart_group)

        self.lock_require_password_checkbox.toggled.connect(self._validate_lock_page)
        self.lock_password_edit.textChanged.connect(self._validate_lock_page)
        self.lock_password_verify_edit.textChanged.connect(self._validate_lock_page)
        self._validate_lock_page()
        layout.addStretch(1)
        return page

