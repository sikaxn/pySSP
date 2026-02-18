from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import urlparse

from PyQt5.QtCore import QSize, Qt
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
    _DEFAULTS = {
        "active_group_color": "#EDE8C8",
        "inactive_group_color": "#ECECEC",
        "title_char_limit": 26,
        "show_file_notifications": True,
        "enter_key_mirrors_space": False,
        "log_file_enabled": False,
        "reset_all_on_startup": False,
        "click_playing_action": "play_it_again",
        "search_double_click_action": "find_highlight",
        "fade_in_sec": 1.0,
        "cross_fade_sec": 1.0,
        "fade_out_sec": 1.0,
        "max_multi_play_songs": 5,
        "multi_play_limit_action": "stop_oldest",
        "main_transport_timeline_mode": "cue_region",
        "main_jog_outside_cue_action": "stop_immediately",
        "talk_volume_level": 30,
        "talk_fade_sec": 0.5,
        "talk_blink_button": False,
        "talk_shift_accelerator": True,
        "hotkeys_ignore_talk_level": False,
        "web_remote_enabled": False,
        "web_remote_port": 5050,
        "state_colors": {
            "playing": "#66FF33",
            "played": "#FF3B30",
            "unplayed": "#B0B0B0",
            "highlight": "#A6D8FF",
            "lock": "#F2D74A",
            "error": "#7B3FB3",
            "place_marker": "#111111",
            "empty": "#0B868A",
            "copied_to_cue": "#2E65FF",
            "cue_indicator": "#61D6FF",
            "volume_indicator": "#FFD45A",
        },
        "sound_button_text_color": "#000000",
    }

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
        max_multi_play_songs: int,
        multi_play_limit_action: str,
        web_remote_enabled: bool,
        web_remote_port: int,
        web_remote_url: str,
        main_transport_timeline_mode: str,
        main_jog_outside_cue_action: str,
        state_colors: Dict[str, str],
        sound_button_text_color: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setModal(True)
        self.resize(760, 520)

        self.active_group_color = active_group_color
        self.inactive_group_color = inactive_group_color
        self.sound_button_text_color = sound_button_text_color
        self.state_colors = dict(state_colors)
        self._state_color_buttons: Dict[str, QPushButton] = {}
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
            "Playback",
            self.style().standardIcon(QStyle.SP_MediaPlay),
            self._build_playback_page(
                max_multi_play_songs=max_multi_play_songs,
                multi_play_limit_action=multi_play_limit_action,
                main_transport_timeline_mode=main_transport_timeline_mode,
                main_jog_outside_cue_action=main_jog_outside_cue_action,
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
        self._add_page(
            "Web Remote",
            self.style().standardIcon(QStyle.SP_BrowserReload),
            self._build_web_remote_page(
                web_remote_enabled=web_remote_enabled,
                web_remote_port=web_remote_port,
                web_remote_url=web_remote_url,
            ),
        )
        self.page_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.page_list.setCurrentRow(0)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.restore_defaults_btn = buttons.addButton("Restore Defaults (This Page)", QDialogButtonBox.ResetRole)
        self.restore_defaults_btn.clicked.connect(self._restore_defaults_current_page)
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
        layout = QVBoxLayout(page)

        sound_group = QGroupBox("Sound Button States")
        sound_form = QFormLayout(sound_group)
        self._add_state_color_row(sound_form, "playing", "Playing")
        self._add_state_color_row(sound_form, "played", "Played")
        self._add_state_color_row(sound_form, "unplayed", "Unplayed")
        self._add_state_color_row(sound_form, "highlight", "Highlight")
        self._add_state_color_row(sound_form, "lock", "Lock")
        self._add_state_color_row(sound_form, "error", "Error")
        self._add_state_color_row(sound_form, "place_marker", "Place Marker")
        self._add_state_color_row(sound_form, "empty", "Empty")
        self._add_state_color_row(sound_form, "copied_to_cue", "Copied To Cue")
        layout.addWidget(sound_group)

        indicator_group = QGroupBox("Indicators")
        indicator_form = QFormLayout(indicator_group)
        self._add_state_color_row(indicator_form, "cue_indicator", "Cue Indicator")
        self._add_state_color_row(indicator_form, "volume_indicator", "Volume Indicator")
        self.sound_text_color_btn = QPushButton()
        self.sound_text_color_btn.clicked.connect(self._pick_sound_text_color)
        self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)
        indicator_form.addRow("Sound Button Text:", self.sound_text_color_btn)
        layout.addWidget(indicator_group)

        group_group = QGroupBox("Group Buttons")
        group_form = QFormLayout(group_group)
        self.active_color_btn = QPushButton()
        self.active_color_btn.clicked.connect(self._pick_active_color)
        self._refresh_color_button(self.active_color_btn, self.active_group_color)
        group_form.addRow("Active Group:", self.active_color_btn)
        self.inactive_color_btn = QPushButton()
        self.inactive_color_btn.clicked.connect(self._pick_inactive_color)
        self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)
        group_form.addRow("Inactive Group:", self.inactive_color_btn)
        layout.addWidget(group_group)

        layout.addStretch(1)
        return page

    def _add_state_color_row(self, form: QFormLayout, key: str, label: str) -> None:
        value = self.state_colors.get(key, "#FFFFFF")
        btn = QPushButton()
        self._refresh_color_button(btn, value)
        btn.clicked.connect(lambda _=None, k=key, b=btn, t=label: self._pick_state_color(k, b, t))
        self._state_color_buttons[key] = btn
        form.addRow(f"{label}:", btn)

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

    def _build_playback_page(
        self,
        max_multi_play_songs: int,
        multi_play_limit_action: str,
        main_transport_timeline_mode: str,
        main_jog_outside_cue_action: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.max_multi_play_spin = QSpinBox()
        self.max_multi_play_spin.setRange(1, 32)
        self.max_multi_play_spin.setValue(max(1, min(32, int(max_multi_play_songs))))
        form.addRow("Max Multi-Play Songs:", self.max_multi_play_spin)
        layout.addLayout(form)

        limit_group = QGroupBox("When max songs is reached during Multi-Play:")
        limit_layout = QVBoxLayout(limit_group)
        self.multi_play_disallow_radio = QRadioButton("Disallow more play")
        self.multi_play_stop_oldest_radio = QRadioButton("Stop the oldest")
        if multi_play_limit_action == "disallow_more_play":
            self.multi_play_disallow_radio.setChecked(True)
        else:
            self.multi_play_stop_oldest_radio.setChecked(True)
        limit_layout.addWidget(self.multi_play_disallow_radio)
        limit_layout.addWidget(self.multi_play_stop_oldest_radio)
        layout.addWidget(limit_group)

        cue_group = QGroupBox("Main Player Timeline / Jog Display:")
        cue_layout = QVBoxLayout(cue_group)
        self.cue_timeline_cue_region_radio = QRadioButton("Relative to Cue Set Points")
        self.cue_timeline_audio_file_radio = QRadioButton("Relative to Actual Audio File")
        if main_transport_timeline_mode == "audio_file":
            self.cue_timeline_audio_file_radio.setChecked(True)
        else:
            self.cue_timeline_cue_region_radio.setChecked(True)
        cue_layout.addWidget(self.cue_timeline_cue_region_radio)
        cue_layout.addWidget(self.cue_timeline_audio_file_radio)
        layout.addWidget(cue_group)

        self.jog_outside_group = QGroupBox("When jog is outside cue area (Audio File mode):")
        jog_outside_layout = QVBoxLayout(self.jog_outside_group)
        self.jog_outside_stop_immediately_radio = QRadioButton("Stop immediately")
        self.jog_outside_ignore_cue_radio = QRadioButton("Ignore cue and play until end or stopped")
        self.jog_outside_next_cue_or_stop_radio = QRadioButton(
            "Play to next cue or stop (before start: stop at start; after stop: play to end)"
        )
        self.jog_outside_stop_cue_or_end_radio = QRadioButton(
            "Play to stop cue (before start: stop at stop cue; after stop: play to end)"
        )
        if main_jog_outside_cue_action == "ignore_cue":
            self.jog_outside_ignore_cue_radio.setChecked(True)
        elif main_jog_outside_cue_action == "next_cue_or_stop":
            self.jog_outside_next_cue_or_stop_radio.setChecked(True)
        elif main_jog_outside_cue_action == "stop_cue_or_end":
            self.jog_outside_stop_cue_or_end_radio.setChecked(True)
        else:
            self.jog_outside_stop_immediately_radio.setChecked(True)
        jog_outside_layout.addWidget(self.jog_outside_stop_immediately_radio)
        jog_outside_layout.addWidget(self.jog_outside_ignore_cue_radio)
        jog_outside_layout.addWidget(self.jog_outside_next_cue_or_stop_radio)
        jog_outside_layout.addWidget(self.jog_outside_stop_cue_or_end_radio)
        layout.addWidget(self.jog_outside_group)
        self.cue_timeline_cue_region_radio.toggled.connect(self._sync_jog_outside_group_enabled)
        self.cue_timeline_audio_file_radio.toggled.connect(self._sync_jog_outside_group_enabled)
        self._sync_jog_outside_group_enabled()

        layout.addStretch(1)
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

    def _build_web_remote_page(self, web_remote_enabled: bool, web_remote_port: int, web_remote_url: str) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.web_remote_enabled_checkbox = QCheckBox("Enable Web Remote (Flask API)")
        self.web_remote_enabled_checkbox.setChecked(web_remote_enabled)
        form.addRow("Web Remote:", self.web_remote_enabled_checkbox)
        self.web_remote_port_spin = QSpinBox()
        self.web_remote_port_spin.setRange(1, 65535)
        self.web_remote_port_spin.setValue(max(1, min(65535, int(web_remote_port))))
        form.addRow("Port:", self.web_remote_port_spin)
        parsed = urlparse(web_remote_url.strip() or "http://127.0.0.1:5050/")
        self._web_remote_url_scheme = parsed.scheme or "http"
        self._web_remote_url_host = parsed.hostname or "127.0.0.1"
        self.web_remote_url_value = QLabel("")
        self.web_remote_url_value.setOpenExternalLinks(True)
        self.web_remote_url_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.web_remote_url_value.setWordWrap(True)
        form.addRow("Open URL:", self.web_remote_url_value)
        self._set_web_remote_url_label(self._build_web_remote_url_text(self.web_remote_port_spin.value()))
        self.web_remote_port_spin.valueChanged.connect(
            lambda value: self._set_web_remote_url_label(self._build_web_remote_url_text(int(value)))
        )
        return page

    def _build_web_remote_url_text(self, port: int) -> str:
        return f"{self._web_remote_url_scheme}://{self._web_remote_url_host}:{port}/"

    def _set_web_remote_url_label(self, url: str) -> None:
        self.web_remote_url_value.setText(f'<a href="{url}">{url}</a>')

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

    def selected_max_multi_play_songs(self) -> int:
        return max(1, min(32, int(self.max_multi_play_spin.value())))

    def selected_multi_play_limit_action(self) -> str:
        if self.multi_play_disallow_radio.isChecked():
            return "disallow_more_play"
        return "stop_oldest"

    def selected_main_transport_timeline_mode(self) -> str:
        if self.cue_timeline_audio_file_radio.isChecked():
            return "audio_file"
        return "cue_region"

    def selected_main_jog_outside_cue_action(self) -> str:
        if self.jog_outside_ignore_cue_radio.isChecked():
            return "ignore_cue"
        if self.jog_outside_next_cue_or_stop_radio.isChecked():
            return "next_cue_or_stop"
        if self.jog_outside_stop_cue_or_end_radio.isChecked():
            return "stop_cue_or_end"
        return "stop_immediately"

    def selected_state_colors(self) -> Dict[str, str]:
        return dict(self.state_colors)

    def selected_sound_button_text_color(self) -> str:
        return self.sound_button_text_color

    def _sync_jog_outside_group_enabled(self) -> None:
        enabled = self.cue_timeline_audio_file_radio.isChecked()
        self.jog_outside_group.setEnabled(enabled)

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

    def _pick_state_color(self, key: str, button: QPushButton, label: str) -> None:
        current = self.state_colors.get(key, "#FFFFFF")
        selected = QColorDialog.getColor(QColor(current), self, f"{label} Color")
        if selected.isValid():
            value = selected.name().upper()
            self.state_colors[key] = value
            self._refresh_color_button(button, value)

    def _pick_sound_text_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.sound_button_text_color), self, "Sound Button Text Color")
        if selected.isValid():
            self.sound_button_text_color = selected.name().upper()
            self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)

    def _restore_defaults_current_page(self) -> None:
        idx = self.page_list.currentRow()
        if idx == 0:
            self._restore_general_defaults()
            return
        if idx == 1:
            self._restore_color_defaults()
            return
        if idx == 2:
            self._restore_delay_defaults()
            return
        if idx == 3:
            self._restore_playback_defaults()
            return
        if idx == 4:
            self._restore_audio_device_defaults()
            return
        if idx == 5:
            self._restore_talk_defaults()
            return
        if idx == 6:
            self._restore_web_remote_defaults()
            return

    def _restore_general_defaults(self) -> None:
        d = self._DEFAULTS
        self.title_limit_spin.setValue(int(d["title_char_limit"]))
        self.notifications_checkbox.setChecked(bool(d["show_file_notifications"]))
        self.enter_mirror_checkbox.setChecked(bool(d["enter_key_mirrors_space"]))
        self.log_file_checkbox.setChecked(bool(d["log_file_enabled"]))
        self.reset_on_startup_checkbox.setChecked(bool(d["reset_all_on_startup"]))
        if d["click_playing_action"] == "stop_it":
            self.playing_click_stop_radio.setChecked(True)
        else:
            self.playing_click_play_again_radio.setChecked(True)
        if d["search_double_click_action"] == "play_highlight":
            self.search_dbl_play_radio.setChecked(True)
        else:
            self.search_dbl_find_radio.setChecked(True)

    def _restore_color_defaults(self) -> None:
        d = self._DEFAULTS
        self.active_group_color = str(d["active_group_color"])
        self.inactive_group_color = str(d["inactive_group_color"])
        self._refresh_color_button(self.active_color_btn, self.active_group_color)
        self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)
        for key, value in dict(d["state_colors"]).items():
            self.state_colors[key] = value
            btn = self._state_color_buttons.get(key)
            if btn is not None:
                self._refresh_color_button(btn, value)
        self.sound_button_text_color = str(d["sound_button_text_color"])
        self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)

    def _restore_delay_defaults(self) -> None:
        d = self._DEFAULTS
        self.fade_in_spin.setValue(float(d["fade_in_sec"]))
        self.cross_fade_spin.setValue(float(d["cross_fade_sec"]))
        self.fade_out_spin.setValue(float(d["fade_out_sec"]))

    def _restore_playback_defaults(self) -> None:
        d = self._DEFAULTS
        self.max_multi_play_spin.setValue(int(d["max_multi_play_songs"]))
        if d["multi_play_limit_action"] == "disallow_more_play":
            self.multi_play_disallow_radio.setChecked(True)
        else:
            self.multi_play_stop_oldest_radio.setChecked(True)
        if d["main_transport_timeline_mode"] == "audio_file":
            self.cue_timeline_audio_file_radio.setChecked(True)
        else:
            self.cue_timeline_cue_region_radio.setChecked(True)
        action = str(d["main_jog_outside_cue_action"])
        if action == "ignore_cue":
            self.jog_outside_ignore_cue_radio.setChecked(True)
        elif action == "next_cue_or_stop":
            self.jog_outside_next_cue_or_stop_radio.setChecked(True)
        elif action == "stop_cue_or_end":
            self.jog_outside_stop_cue_or_end_radio.setChecked(True)
        else:
            self.jog_outside_stop_immediately_radio.setChecked(True)
        self._sync_jog_outside_group_enabled()

    def _restore_audio_device_defaults(self) -> None:
        for i in range(self.audio_device_combo.count()):
            if str(self.audio_device_combo.itemData(i) or "") == "":
                self.audio_device_combo.setCurrentIndex(i)
                break

    def _restore_talk_defaults(self) -> None:
        d = self._DEFAULTS
        self.talk_volume_spin.setValue(int(d["talk_volume_level"]))
        self.talk_fade_spin.setValue(float(d["talk_fade_sec"]))
        self.talk_blink_checkbox.setChecked(bool(d["talk_blink_button"]))
        self.shift_accel_checkbox.setChecked(bool(d["talk_shift_accelerator"]))
        self.hotkeys_ignore_checkbox.setChecked(bool(d["hotkeys_ignore_talk_level"]))

    def _restore_web_remote_defaults(self) -> None:
        d = self._DEFAULTS
        self.web_remote_enabled_checkbox.setChecked(bool(d["web_remote_enabled"]))
        self.web_remote_port_spin.setValue(int(d["web_remote_port"]))
