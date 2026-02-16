from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class OptionsDialog(QDialog):
    def __init__(
        self,
        active_group_color: str,
        inactive_group_color: str,
        title_char_limit: int,
        show_file_notifications: bool,
        fade_in_sec: float,
        cross_fade_sec: float,
        fade_out_sec: float,
        talk_volume_level: int,
        talk_fade_sec: float,
        talk_blink_button: bool,
        talk_shift_accelerator: bool,
        hotkeys_ignore_talk_level: bool,
        enter_key_mirrors_space: bool,
        log_file_enabled: bool,
        reset_all_on_startup: bool,
        click_playing_action: str,
        search_double_click_action: str,
        audio_output_device: str,
        available_audio_devices: List[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setModal(True)
        self.resize(760, 520)

        self.active_group_color = active_group_color
        self.inactive_group_color = inactive_group_color
        self._available_audio_devices = list(available_audio_devices)

        root_layout = QVBoxLayout(self)
        content = QHBoxLayout()
        root_layout.addLayout(content, 1)

        self.page_list = QListWidget()
        self.page_list.setIconSize(QSize(22, 22))
        self.page_list.setMinimumWidth(210)
        self.page_list.setMaximumWidth(240)
        self.page_list.setFrameShape(QFrame.StyledPanel)
        content.addWidget(self.page_list)

        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)

        self._add_page(
            "General",
            self.style().standardIcon(QStyle.SP_DesktopIcon),
            self._build_general_page(
                title_char_limit=title_char_limit,
                show_file_notifications=show_file_notifications,
                enter_key_mirrors_space=enter_key_mirrors_space,
                log_file_enabled=log_file_enabled,
                reset_all_on_startup=reset_all_on_startup,
                click_playing_action=click_playing_action,
                search_double_click_action=search_double_click_action,
            ),
        )
        self._add_page(
            "Colour",
            self.style().standardIcon(QStyle.SP_DriveDVDIcon),
            self._build_color_page(),
        )
        self._add_page(
            "Delay",
            self.style().standardIcon(QStyle.SP_BrowserReload),
            self._build_delay_page(
                fade_in_sec=fade_in_sec,
                cross_fade_sec=cross_fade_sec,
                fade_out_sec=fade_out_sec,
            ),
        )
        self._add_page(
            "Audio Device",
            self.style().standardIcon(QStyle.SP_MediaVolume),
            self._build_audio_device_page(
                audio_output_device=audio_output_device,
                available_audio_devices=available_audio_devices,
            ),
        )
        self._add_page(
            "Talk",
            self.style().standardIcon(QStyle.SP_MessageBoxInformation),
            self._build_talk_page(
                talk_volume_level=talk_volume_level,
                talk_fade_sec=talk_fade_sec,
                talk_blink_button=talk_blink_button,
                talk_shift_accelerator=talk_shift_accelerator,
                hotkeys_ignore_talk_level=hotkeys_ignore_talk_level,
            ),
        )
        self.page_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.page_list.setCurrentRow(0)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

    def _add_page(self, title: str, icon, page: QWidget) -> None:
        self.stack.addWidget(page)
        item = QListWidgetItem(icon, title)
        self.page_list.addItem(item)

    def _build_general_page(
        self,
        title_char_limit: int,
        show_file_notifications: bool,
        enter_key_mirrors_space: bool,
        log_file_enabled: bool,
        reset_all_on_startup: bool,
        click_playing_action: str,
        search_double_click_action: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.title_limit_spin = QSpinBox()
        self.title_limit_spin.setRange(8, 80)
        self.title_limit_spin.setValue(title_char_limit)
        form.addRow("Button Title Max Chars:", self.title_limit_spin)

        self.notifications_checkbox = QCheckBox("Show set load/save popup messages")
        self.notifications_checkbox.setChecked(show_file_notifications)
        form.addRow("Notifications:", self.notifications_checkbox)

        self.enter_mirror_checkbox = QCheckBox('"Enter Key" Mirrors "Space Bar"')
        self.enter_mirror_checkbox.setChecked(enter_key_mirrors_space)
        form.addRow("Keyboard:", self.enter_mirror_checkbox)

        self.log_file_checkbox = QCheckBox("Enable playback log file (SportsSoundsProLog.txt)")
        self.log_file_checkbox.setChecked(log_file_enabled)
        form.addRow("Log File:", self.log_file_checkbox)

        self.reset_on_startup_checkbox = QCheckBox("Reset ALL on Start-up")
        self.reset_on_startup_checkbox.setChecked(reset_all_on_startup)
        form.addRow("Startup:", self.reset_on_startup_checkbox)
        layout.addLayout(form)

        click_group = QGroupBox("Clicking on a Playing Sound will:")
        click_layout = QVBoxLayout(click_group)
        self.playing_click_play_again_radio = QRadioButton("Play It Again")
        self.playing_click_stop_radio = QRadioButton("Stop It")
        if click_playing_action == "stop_it":
            self.playing_click_stop_radio.setChecked(True)
        else:
            self.playing_click_play_again_radio.setChecked(True)
        click_layout.addWidget(self.playing_click_play_again_radio)
        click_layout.addWidget(self.playing_click_stop_radio)
        layout.addWidget(click_group)

        search_group = QGroupBox("Search Double-Click will:")
        search_layout = QVBoxLayout(search_group)
        self.search_dbl_find_radio = QRadioButton("Find (Highlight)")
        self.search_dbl_play_radio = QRadioButton("Play and Highlight")
        if search_double_click_action == "play_highlight":
            self.search_dbl_play_radio.setChecked(True)
        else:
            self.search_dbl_find_radio.setChecked(True)
        search_layout.addWidget(self.search_dbl_find_radio)
        search_layout.addWidget(self.search_dbl_play_radio)
        layout.addWidget(search_group)

        layout.addStretch(1)
        return page

    def _build_color_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.active_color_btn = QPushButton()
        self.active_color_btn.clicked.connect(self._pick_active_color)
        self._refresh_color_button(self.active_color_btn, self.active_group_color)
        form.addRow("Active Button Color:", self.active_color_btn)

        self.inactive_color_btn = QPushButton()
        self.inactive_color_btn.clicked.connect(self._pick_inactive_color)
        self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)
        form.addRow("Inactive Button Color:", self.inactive_color_btn)
        return page

    def _build_delay_page(self, fade_in_sec: float, cross_fade_sec: float, fade_out_sec: float) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0.0, 20.0)
        self.fade_in_spin.setSingleStep(0.1)
        self.fade_in_spin.setDecimals(1)
        self.fade_in_spin.setValue(fade_in_sec)
        form.addRow("Fade In Seconds:", self.fade_in_spin)

        self.cross_fade_spin = QDoubleSpinBox()
        self.cross_fade_spin.setRange(0.0, 20.0)
        self.cross_fade_spin.setSingleStep(0.1)
        self.cross_fade_spin.setDecimals(1)
        self.cross_fade_spin.setValue(cross_fade_sec)
        form.addRow("Cross Fade Seconds:", self.cross_fade_spin)

        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0.0, 20.0)
        self.fade_out_spin.setSingleStep(0.1)
        self.fade_out_spin.setDecimals(1)
        self.fade_out_spin.setValue(fade_out_sec)
        form.addRow("Fade Out Seconds:", self.fade_out_spin)
        return page

    def _build_audio_device_page(self, audio_output_device: str, available_audio_devices: List[str]) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        row = QHBoxLayout()
        row.addWidget(QLabel("Output Device:"))
        self.audio_device_combo = QComboBox()
        row.addWidget(self.audio_device_combo, 1)
        self.audio_refresh_button = QPushButton("Refresh")
        self.audio_refresh_button.clicked.connect(self._refresh_audio_devices)
        row.addWidget(self.audio_refresh_button)
        layout.addLayout(row)

        self.audio_device_hint = QLabel("")
        layout.addWidget(self.audio_device_hint)

        self._populate_audio_devices(available_audio_devices, audio_output_device)
        layout.addWidget(QLabel("MIDI and timecode settings will be added to this page later."))
        layout.addStretch(1)
        return page

    def _build_talk_page(
        self,
        talk_volume_level: int,
        talk_fade_sec: float,
        talk_blink_button: bool,
        talk_shift_accelerator: bool,
        hotkeys_ignore_talk_level: bool,
    ) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self.talk_volume_spin = QSpinBox()
        self.talk_volume_spin.setRange(0, 100)
        self.talk_volume_spin.setValue(talk_volume_level)
        form.addRow("Talk Volume Level (%):", self.talk_volume_spin)

        self.talk_fade_spin = QDoubleSpinBox()
        self.talk_fade_spin.setRange(0.0, 20.0)
        self.talk_fade_spin.setSingleStep(0.1)
        self.talk_fade_spin.setDecimals(1)
        self.talk_fade_spin.setValue(talk_fade_sec)
        form.addRow("Talk Fade Seconds:", self.talk_fade_spin)

        self.talk_blink_checkbox = QCheckBox("Blink Talk Button")
        self.talk_blink_checkbox.setChecked(talk_blink_button)
        form.addRow("Talk Button:", self.talk_blink_checkbox)

        self.shift_accel_checkbox = QCheckBox("Use Shift Key to activate Talk")
        self.shift_accel_checkbox.setChecked(talk_shift_accelerator)
        form.addRow("Accelerator:", self.shift_accel_checkbox)

        self.hotkeys_ignore_checkbox = QCheckBox("Hot Keys Ignore Talk Volume Level")
        self.hotkeys_ignore_checkbox.setChecked(hotkeys_ignore_talk_level)
        form.addRow("Hot Keys:", self.hotkeys_ignore_checkbox)
        return page

    def selected_click_playing_action(self) -> str:
        if self.playing_click_stop_radio.isChecked():
            return "stop_it"
        return "play_it_again"

    def selected_search_double_click_action(self) -> str:
        if self.search_dbl_play_radio.isChecked():
            return "play_highlight"
        return "find_highlight"

    def selected_audio_output_device(self) -> str:
        return str(self.audio_device_combo.currentData() or "")

    def _populate_audio_devices(self, devices: List[str], selected_device: str) -> None:
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("System Default", "")
        for name in devices:
            self.audio_device_combo.addItem(name, name)
        selected_index = 0
        for i in range(self.audio_device_combo.count()):
            if str(self.audio_device_combo.itemData(i)) == selected_device:
                selected_index = i
                break
        self.audio_device_combo.setCurrentIndex(selected_index)
        if devices:
            self.audio_device_hint.setText(f"Detected {len(devices)} output device(s).")
        else:
            self.audio_device_hint.setText("No explicit device list detected. System Default will be used.")

    def _refresh_audio_devices(self) -> None:
        selected = self.selected_audio_output_device()
        try:
            from pyssp.audio_engine import list_output_devices

            devices = list_output_devices()
        except Exception:
            devices = []
        self._available_audio_devices = list(devices)
        self._populate_audio_devices(self._available_audio_devices, selected)

    def _refresh_color_button(self, button: QPushButton, color_hex: str) -> None:
        button.setText(color_hex)
        button.setStyleSheet(
            "QPushButton{"
            f"background:{color_hex};"
            "border:1px solid #6C6C6C;"
            "min-height:26px;"
            "}"
        )

    def _pick_active_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.active_group_color), self, "Active Button Color")
        if selected.isValid():
            self.active_group_color = selected.name().upper()
            self._refresh_color_button(self.active_color_btn, self.active_group_color)

    def _pick_inactive_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.inactive_group_color), self, "Inactive Button Color")
        if selected.isValid():
            self.inactive_group_color = selected.name().upper()
            self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)
