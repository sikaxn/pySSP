from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import urlparse

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QLineEdit,
    QScrollArea,
    QSlider,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyssp.settings_store import default_quick_action_keys
from pyssp.i18n import localize_widget_tree, normalize_language, tr
from pyssp.timecode import (
    MIDI_OUTPUT_DEVICE_NONE,
    MTC_IDLE_KEEP_STREAM,
    TIMECODE_MODE_FOLLOW,
    TIMECODE_MODE_FOLLOW_FREEZE,
    TIMECODE_MODE_SYSTEM,
    TIMECODE_MODE_ZERO,
    TIME_CODE_BIT_DEPTHS,
    TIME_CODE_FPS_CHOICES,
    TIME_CODE_MTC_FPS_CHOICES,
    TIME_CODE_SAMPLE_RATES,
)


class HotkeyCaptureEdit(QLineEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Press key")
        self.setReadOnly(True)

    def hotkey(self) -> str:
        return self.text().strip()

    def setHotkey(self, value: str) -> None:
        text = str(value or "").strip()
        self.setText(self._normalize_text(text))

    def keyPressEvent(self, event) -> None:
        key = int(event.key())
        if key in {Qt.Key_Tab, Qt.Key_Backtab}:
            super().keyPressEvent(event)
            return
        if key in {Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Escape}:
            self.clear()
            return

        modifiers = event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier)
        text = self._build_hotkey_text(key, modifiers)
        if text:
            self.setText(text)

    def _build_hotkey_text(self, key: int, modifiers: Qt.KeyboardModifiers) -> str:
        if key == Qt.Key_Shift and modifiers == Qt.ShiftModifier:
            return "Shift"
        if key == Qt.Key_Control and modifiers == Qt.ControlModifier:
            return "Ctrl"
        if key == Qt.Key_Alt and modifiers == Qt.AltModifier:
            return "Alt"
        if key == Qt.Key_Meta and modifiers == Qt.MetaModifier:
            return "Meta"
        seq = QKeySequence(int(key) | int(modifiers)).toString().strip()
        return self._normalize_text(seq)

    def _normalize_text(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        aliases = {
            "control": "Ctrl",
            "ctrl": "Ctrl",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Meta",
            "win": "Meta",
            "super": "Meta",
        }
        lower = raw.lower()
        if lower in aliases:
            return aliases[lower]
        normalized = QKeySequence(raw).toString().strip()
        return normalized or raw


class OptionsDialog(QDialog):
    _HOTKEY_ROWS = [
        ("new_set", "New Set"),
        ("open_set", "Open Set"),
        ("save_set", "Save Set"),
        ("save_set_as", "Save Set As"),
        ("search", "Search"),
        ("options", "Options"),
        ("play_selected", "Play Selected"),
        ("pause_toggle", "Pause/Resume"),
        ("stop_playback", "Stop Playback"),
        ("talk", "Talk"),
        ("next_group", "Next Group"),
        ("prev_group", "Previous Group"),
        ("next_page", "Next Page"),
        ("prev_page", "Previous Page"),
        ("next_sound_button", "Next Sound Button"),
        ("prev_sound_button", "Previous Sound Button"),
        ("multi_play", "Multi-Play"),
        ("go_to_playing", "Go To Playing"),
        ("loop", "Loop"),
        ("next", "Next"),
        ("rapid_fire", "Rapid Fire"),
        ("shuffle", "Shuffle"),
        ("reset_page", "Reset Page"),
        ("play_list", "Play List"),
        ("fade_in", "Fade In"),
        ("cross_fade", "X (Cross Fade)"),
        ("fade_out", "Fade Out"),
        ("mute", "Mute"),
        ("volume_up", "Volume Up"),
        ("volume_down", "Volume Down"),
    ]

    _DEFAULTS = {
        "active_group_color": "#EDE8C8",
        "inactive_group_color": "#ECECEC",
        "title_char_limit": 26,
        "show_file_notifications": True,
        "log_file_enabled": False,
        "reset_all_on_startup": False,
        "click_playing_action": "play_it_again",
        "search_double_click_action": "find_highlight",
        "set_file_encoding": "utf8",
        "ui_language": "en",
        "preload_audio_enabled": False,
        "preload_current_page_audio": True,
        "preload_audio_memory_limit_mb": 512,
        "preload_memory_pressure_enabled": True,
        "preload_pause_on_playback": False,
        "fade_in_sec": 1.0,
        "cross_fade_sec": 1.0,
        "fade_out_sec": 1.0,
        "fade_on_quick_action_hotkey": True,
        "fade_on_sound_button_hotkey": True,
        "fade_on_pause": False,
        "fade_on_resume": False,
        "fade_on_stop": True,
        "fade_out_when_done_playing": False,
        "fade_out_end_lead_sec": 2.0,
        "max_multi_play_songs": 5,
        "multi_play_limit_action": "stop_oldest",
        "playlist_play_mode": "unplayed_only",
        "rapid_fire_play_mode": "unplayed_only",
        "next_play_mode": "unplayed_only",
        "playlist_loop_mode": "loop_list",
        "candidate_error_action": "stop_playback",
        "main_transport_timeline_mode": "cue_region",
        "main_jog_outside_cue_action": "stop_immediately",
        "talk_volume_level": 30,
        "talk_fade_sec": 0.5,
        "talk_volume_mode": "percent_of_master",
        "talk_blink_button": False,
        "web_remote_enabled": False,
        "web_remote_port": 5050,
        "timecode_audio_output_device": "none",
        "timecode_midi_output_device": MIDI_OUTPUT_DEVICE_NONE,
        "timecode_mode": TIMECODE_MODE_FOLLOW,
        "timecode_fps": 30.0,
        "timecode_mtc_fps": 30.0,
        "timecode_mtc_idle_behavior": MTC_IDLE_KEEP_STREAM,
        "timecode_sample_rate": 48000,
        "timecode_bit_depth": 16,
        "timecode_timeline_mode": "cue_region",
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
        "hotkeys": {
            "new_set": ("Ctrl+N", ""),
            "open_set": ("Ctrl+O", ""),
            "save_set": ("Ctrl+S", ""),
            "save_set_as": ("Ctrl+Shift+S", ""),
            "search": ("Ctrl+F", ""),
            "options": ("", ""),
            "play_selected": ("", ""),
            "pause_toggle": ("P", ""),
            "stop_playback": ("Space", "Return"),
            "talk": ("Shift", ""),
            "next_group": ("", ""),
            "prev_group": ("", ""),
            "next_page": ("", ""),
            "prev_page": ("", ""),
            "next_sound_button": ("", ""),
            "prev_sound_button": ("", ""),
            "multi_play": ("", ""),
            "go_to_playing": ("", ""),
            "loop": ("", ""),
            "next": ("", ""),
            "rapid_fire": ("", ""),
            "shuffle": ("", ""),
            "reset_page": ("", ""),
            "play_list": ("", ""),
            "fade_in": ("", ""),
            "cross_fade": ("", ""),
            "fade_out": ("", ""),
            "mute": ("", ""),
            "volume_up": ("", ""),
            "volume_down": ("", ""),
        },
        "sound_button_hotkey_enabled": False,
        "sound_button_hotkey_priority": "system_first",
        "sound_button_hotkey_go_to_playing": False,
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
        fade_on_quick_action_hotkey: bool,
        fade_on_sound_button_hotkey: bool,
        fade_on_pause: bool,
        fade_on_resume: bool,
        fade_on_stop: bool,
        fade_out_when_done_playing: bool,
        fade_out_end_lead_sec: float,
        talk_volume_level: int,
        talk_fade_sec: float,
        talk_volume_mode: str,
        talk_blink_button: bool,
        log_file_enabled: bool,
        reset_all_on_startup: bool,
        click_playing_action: str,
        search_double_click_action: str,
        set_file_encoding: str,
        audio_output_device: str,
        available_audio_devices: List[str],
        available_midi_devices: List[tuple[str, str]],
        preload_audio_enabled: bool,
        preload_current_page_audio: bool,
        preload_audio_memory_limit_mb: int,
        preload_memory_pressure_enabled: bool,
        preload_pause_on_playback: bool,
        preload_total_ram_mb: int,
        preload_ram_cap_mb: int,
        timecode_audio_output_device: str,
        timecode_midi_output_device: str,
        timecode_mode: str,
        timecode_fps: float,
        timecode_mtc_fps: float,
        timecode_mtc_idle_behavior: str,
        timecode_sample_rate: int,
        timecode_bit_depth: int,
        timecode_timeline_mode: str,
        max_multi_play_songs: int,
        multi_play_limit_action: str,
        playlist_play_mode: str,
        rapid_fire_play_mode: str,
        next_play_mode: str,
        playlist_loop_mode: str,
        candidate_error_action: str,
        web_remote_enabled: bool,
        web_remote_port: int,
        web_remote_url: str,
        main_transport_timeline_mode: str,
        main_jog_outside_cue_action: str,
        state_colors: Dict[str, str],
        sound_button_text_color: str,
        hotkeys: Dict[str, tuple[str, str]],
        quick_action_enabled: bool,
        quick_action_keys: List[str],
        sound_button_hotkey_enabled: bool,
        sound_button_hotkey_priority: str,
        sound_button_hotkey_go_to_playing: bool,
        ui_language: str,
        initial_page: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.setModal(True)
        self.resize(760, 520)

        self.active_group_color = active_group_color
        self.inactive_group_color = inactive_group_color
        self.sound_button_text_color = sound_button_text_color
        self._hotkeys = dict(hotkeys)
        self._hotkey_edits: Dict[str, tuple[HotkeyCaptureEdit, HotkeyCaptureEdit]] = {}
        self._quick_action_enabled = bool(quick_action_enabled)
        self._quick_action_edits: List[HotkeyCaptureEdit] = []
        qa_defaults = default_quick_action_keys()
        self._quick_action_keys = list(quick_action_keys)[:48]
        if len(self._quick_action_keys) < 48:
            self._quick_action_keys.extend(qa_defaults[len(self._quick_action_keys):48])
        self._sound_button_hotkey_enabled = bool(sound_button_hotkey_enabled)
        self._sound_button_hotkey_priority = (
            sound_button_hotkey_priority if sound_button_hotkey_priority in {"system_first", "sound_button_first"} else "system_first"
        )
        self._sound_button_hotkey_go_to_playing = bool(sound_button_hotkey_go_to_playing)
        self._ui_language = normalize_language(ui_language)
        self._hotkey_labels: Dict[str, str] = {key: label for key, label in self._HOTKEY_ROWS}
        self.hotkey_warning_label: Optional[QLabel] = None
        self.state_colors = dict(state_colors)
        self._state_color_buttons: Dict[str, QPushButton] = {}
        self._available_audio_devices = list(available_audio_devices)
        self._available_midi_devices = list(available_midi_devices)

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
            self._mono_icon("info"),
            self._build_general_page(
                title_char_limit=title_char_limit,
                show_file_notifications=show_file_notifications,
                log_file_enabled=log_file_enabled,
                reset_all_on_startup=reset_all_on_startup,
                click_playing_action=click_playing_action,
                search_double_click_action=search_double_click_action,
                set_file_encoding=set_file_encoding,
            ),
        )
        self._add_page(
            "Language",
            self._mono_icon("earth"),
            self._build_language_page(self._ui_language),
        )
        self._add_page(
            "Hotkey",
            self._mono_icon("keyboard"),
            self._build_hotkey_page(),
        )
        self._add_page(
            "Colour",
            self._mono_icon("display"),
            self._build_color_page(),
        )
        self._add_page(
            "Fade",
            self._mono_icon("clock"),
            self._build_delay_page(
                fade_in_sec=fade_in_sec,
                cross_fade_sec=cross_fade_sec,
                fade_out_sec=fade_out_sec,
                fade_on_quick_action_hotkey=fade_on_quick_action_hotkey,
                fade_on_sound_button_hotkey=fade_on_sound_button_hotkey,
                fade_on_pause=fade_on_pause,
                fade_on_resume=fade_on_resume,
                fade_on_stop=fade_on_stop,
                fade_out_when_done_playing=fade_out_when_done_playing,
                fade_out_end_lead_sec=fade_out_end_lead_sec,
            ),
        )
        self._add_page(
            "Playback",
            self._mono_icon("play"),
            self._build_playback_page(
                max_multi_play_songs=max_multi_play_songs,
                multi_play_limit_action=multi_play_limit_action,
                playlist_play_mode=playlist_play_mode,
                rapid_fire_play_mode=rapid_fire_play_mode,
                next_play_mode=next_play_mode,
                playlist_loop_mode=playlist_loop_mode,
                candidate_error_action=candidate_error_action,
                main_transport_timeline_mode=main_transport_timeline_mode,
                main_jog_outside_cue_action=main_jog_outside_cue_action,
            ),
        )
        self._add_page(
            "Audio Device / Timecode",
            self._mono_icon("speaker"),
            self._build_audio_device_page(
                audio_output_device=audio_output_device,
                available_audio_devices=available_audio_devices,
                available_midi_devices=available_midi_devices,
                timecode_audio_output_device=timecode_audio_output_device,
                timecode_midi_output_device=timecode_midi_output_device,
                timecode_mode=timecode_mode,
                timecode_fps=timecode_fps,
                timecode_mtc_fps=timecode_mtc_fps,
                timecode_mtc_idle_behavior=timecode_mtc_idle_behavior,
                timecode_sample_rate=timecode_sample_rate,
                timecode_bit_depth=timecode_bit_depth,
                timecode_timeline_mode=timecode_timeline_mode,
            ),
        )
        self._add_page(
            "Audio Preload",
            self._mono_icon("ram"),
            self._build_audio_preload_page(
                preload_audio_enabled=preload_audio_enabled,
                preload_current_page_audio=preload_current_page_audio,
                preload_audio_memory_limit_mb=preload_audio_memory_limit_mb,
                preload_memory_pressure_enabled=preload_memory_pressure_enabled,
                preload_pause_on_playback=preload_pause_on_playback,
                preload_total_ram_mb=preload_total_ram_mb,
                preload_ram_cap_mb=preload_ram_cap_mb,
            ),
        )
        self._add_page(
            "Talk",
            self._mono_icon("mic"),
            self._build_talk_page(
                talk_volume_level=talk_volume_level,
                talk_fade_sec=talk_fade_sec,
                talk_volume_mode=talk_volume_mode,
                talk_blink_button=talk_blink_button,
            ),
        )
        self._add_page(
            "Web Remote",
            self._mono_icon("wireless"),
            self._build_web_remote_page(
                web_remote_enabled=web_remote_enabled,
                web_remote_port=web_remote_port,
                web_remote_url=web_remote_url,
            ),
        )
        self.page_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        if not self.select_page(initial_page):
            self.page_list.setCurrentRow(0)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.restore_defaults_btn = buttons.addButton("Restore Defaults (This Page)", QDialogButtonBox.ResetRole)
        self.restore_defaults_btn.clicked.connect(self._restore_defaults_current_page)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)
        self._validate_hotkey_conflicts()
        localize_widget_tree(self, self._ui_language)

    def _add_page(self, title: str, icon, page: QWidget) -> None:
        self.stack.addWidget(page)
        item = QListWidgetItem(icon, title)
        self.page_list.addItem(item)

    def select_page(self, title: Optional[str]) -> bool:
        needle = str(title or "").strip().lower()
        if not needle:
            return False
        for index in range(self.page_list.count()):
            item = self.page_list.item(index)
            if item is None:
                continue
            if item.text().strip().lower() == needle:
                self.page_list.setCurrentRow(index)
                return True
        return False

    def _mono_icon(self, kind: str) -> QIcon:
        size = 22
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor("#000000"))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        if kind == "info":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.setBrush(QColor("#000000"))
            p.drawEllipse(QRectF(10, 6, 2, 2))
            p.drawRoundedRect(QRectF(10, 9, 2, 7), 1, 1)
        elif kind == "keyboard":
            p.drawRoundedRect(QRectF(2.5, 5, 17, 12), 2, 2)
            for y in [8, 11, 14]:
                p.drawLine(5, y, 17, y)
            p.drawLine(8, 8, 8, 14)
            p.drawLine(12, 8, 12, 14)
            p.drawLine(16, 8, 16, 14)
        elif kind == "display":
            p.drawRoundedRect(QRectF(3, 3, 16, 12), 1.5, 1.5)
            p.drawLine(8, 18, 14, 18)
            p.drawLine(11, 15, 11, 18)
        elif kind == "clock":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.drawLine(11, 11, 11, 6)
            p.drawLine(11, 11, 15, 13)
        elif kind == "play":
            tri = QPolygonF([QPointF(7, 5), QPointF(17, 11), QPointF(7, 17)])
            p.drawPolygon(tri)
        elif kind == "speaker":
            body = QPolygonF([QPointF(4, 9), QPointF(8, 9), QPointF(12, 6), QPointF(12, 16), QPointF(8, 13), QPointF(4, 13)])
            p.drawPolygon(body)
            p.drawArc(QRectF(12, 7, 5, 8), -40 * 16, 80 * 16)
            p.drawArc(QRectF(12, 5, 8, 12), -40 * 16, 80 * 16)
        elif kind == "mic":
            p.drawRoundedRect(QRectF(8, 4, 6, 10), 3, 3)
            p.drawLine(11, 14, 11, 18)
            p.drawLine(8, 18, 14, 18)
            p.drawArc(QRectF(6, 10, 10, 8), 200 * 16, 140 * 16)
        elif kind == "wireless":
            p.drawEllipse(QRectF(10, 14, 2, 2))
            p.drawArc(QRectF(7, 11, 8, 8), 35 * 16, 110 * 16)
            p.drawArc(QRectF(5, 9, 12, 12), 35 * 16, 110 * 16)
            p.drawArc(QRectF(3, 7, 16, 16), 35 * 16, 110 * 16)
        elif kind == "ram":
            p.drawRoundedRect(QRectF(4, 6, 14, 10), 1.5, 1.5)
            p.drawLine(6, 9, 16, 9)
            p.drawLine(6, 12, 16, 12)
            for x in [5, 8, 11, 14, 17]:
                p.drawLine(x, 4, x, 6)
                p.drawLine(x, 16, x, 18)
        elif kind == "earth":
            p.drawEllipse(QRectF(3, 3, 16, 16))
            p.drawArc(QRectF(5, 3, 12, 16), 90 * 16, 180 * 16)
            p.drawArc(QRectF(5, 3, 12, 16), 270 * 16, 180 * 16)
            p.drawLine(3, 11, 19, 11)
            p.drawArc(QRectF(3, 6, 16, 10), 0, 180 * 16)
            p.drawArc(QRectF(3, 6, 16, 10), 180 * 16, 180 * 16)

        p.end()
        return QIcon(pix)

    def _build_general_page(
        self,
        title_char_limit: int,
        show_file_notifications: bool,
        log_file_enabled: bool,
        reset_all_on_startup: bool,
        click_playing_action: str,
        search_double_click_action: str,
        set_file_encoding: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        form = QFormLayout()
        self.title_limit_spin = QSpinBox()
        self.title_limit_spin.setRange(8, 80)
        self.title_limit_spin.setValue(title_char_limit)
        form.addRow("Button Title Max Chars:", self.title_limit_spin)

        self.log_file_checkbox = QCheckBox("Enable playback log file (SportsSoundsProLog.txt)")
        self.log_file_checkbox.setChecked(log_file_enabled)
        form.addRow("Log File:", self.log_file_checkbox)

        self.reset_on_startup_checkbox = QCheckBox("Reset ALL on Start-up")
        self.reset_on_startup_checkbox.setChecked(reset_all_on_startup)
        form.addRow("Startup:", self.reset_on_startup_checkbox)

        encoding_group = QGroupBox(".set Save Encoding")
        encoding_layout = QVBoxLayout(encoding_group)
        self.set_file_encoding_utf8_radio = QRadioButton("UTF-8")
        self.set_file_encoding_gbk_radio = QRadioButton("GBK (Chinese)")
        if str(set_file_encoding).strip().lower() == "gbk":
            self.set_file_encoding_gbk_radio.setChecked(True)
        else:
            self.set_file_encoding_utf8_radio.setChecked(True)
        encoding_layout.addWidget(self.set_file_encoding_utf8_radio)
        encoding_layout.addWidget(self.set_file_encoding_gbk_radio)
        encoding_note = QLabel(
            "GBK note: if song title, notes, file path, etc include Chinese characters, "
            "GBK has better compatibility with original SSP."
        )
        encoding_note.setWordWrap(True)
        encoding_layout.addWidget(encoding_note)
        layout.addWidget(encoding_group)
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

    def _build_language_page(self, ui_language: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.ui_language_combo = QComboBox()
        self.ui_language_combo.addItem("English", "en")
        self.ui_language_combo.addItem("Chinese (Simplified)", "zh_cn")
        index = self.ui_language_combo.findData(normalize_language(ui_language))
        self.ui_language_combo.setCurrentIndex(index if index >= 0 else 0)
        form.addRow("UI Language", self.ui_language_combo)
        layout.addLayout(form)
        note = QLabel("App language (requires reopen dialogs/windows to fully refresh).")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return page

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
            form.addRow(f"Button {i + 1}:", row)
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
        form.addRow(f"{label}:", row)

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

    def _build_delay_page(
        self,
        fade_in_sec: float,
        cross_fade_sec: float,
        fade_out_sec: float,
        fade_on_quick_action_hotkey: bool,
        fade_on_sound_button_hotkey: bool,
        fade_on_pause: bool,
        fade_on_resume: bool,
        fade_on_stop: bool,
        fade_out_when_done_playing: bool,
        fade_out_end_lead_sec: float,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        trigger_group = QGroupBox("Fader Trigger")
        trigger_layout = QVBoxLayout(trigger_group)

        self.fade_on_quick_action_checkbox = QCheckBox("Allow fader on Quick Action key active")
        self.fade_on_quick_action_checkbox.setChecked(bool(fade_on_quick_action_hotkey))
        trigger_layout.addWidget(self.fade_on_quick_action_checkbox)

        self.fade_on_sound_hotkey_checkbox = QCheckBox("Allow fader on Sound Button hot key active")
        self.fade_on_sound_hotkey_checkbox.setChecked(bool(fade_on_sound_button_hotkey))
        trigger_layout.addWidget(self.fade_on_sound_hotkey_checkbox)

        self.fade_on_pause_checkbox = QCheckBox("Fade on Pause")
        self.fade_on_pause_checkbox.setChecked(bool(fade_on_pause))
        trigger_layout.addWidget(self.fade_on_pause_checkbox)

        self.fade_on_resume_checkbox = QCheckBox("Fade on Resume (when paused)")
        self.fade_on_resume_checkbox.setChecked(bool(fade_on_resume))
        trigger_layout.addWidget(self.fade_on_resume_checkbox)

        self.fade_on_stop_checkbox = QCheckBox("Fade on Stop")
        self.fade_on_stop_checkbox.setChecked(bool(fade_on_stop))
        trigger_layout.addWidget(self.fade_on_stop_checkbox)

        self.fade_on_stop_note = QLabel("During fade, click Stop again to force stop (skip fade).")
        self.fade_on_stop_note.setWordWrap(True)
        self.fade_on_stop_note.setStyleSheet("color:#666666;")
        trigger_layout.addWidget(self.fade_on_stop_note)
        self.fade_dependency_note = QLabel("Note: These options work only when the matching Fade In/Fade Out control is active.")
        self.fade_dependency_note.setWordWrap(True)
        self.fade_dependency_note.setStyleSheet("color:#666666;")
        trigger_layout.addWidget(self.fade_dependency_note)
        layout.addWidget(trigger_group)

        timing_group = QGroupBox("Fade Timing")
        timing_form = QFormLayout(timing_group)

        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0.0, 20.0)
        self.fade_in_spin.setSingleStep(0.1)
        self.fade_in_spin.setDecimals(1)
        self.fade_in_spin.setValue(fade_in_sec)
        timing_form.addRow("Fade In Seconds:", self.fade_in_spin)

        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0.0, 20.0)
        self.fade_out_spin.setSingleStep(0.1)
        self.fade_out_spin.setDecimals(1)
        self.fade_out_spin.setValue(fade_out_sec)
        timing_form.addRow("Fade Out Seconds:", self.fade_out_spin)

        self.fade_out_when_done_checkbox = QCheckBox("Fade out when done playing")
        self.fade_out_when_done_checkbox.setChecked(bool(fade_out_when_done_playing))
        timing_form.addRow("", self.fade_out_when_done_checkbox)

        self.fade_out_end_lead_spin = QDoubleSpinBox()
        self.fade_out_end_lead_spin.setRange(0.0, 30.0)
        self.fade_out_end_lead_spin.setSingleStep(0.1)
        self.fade_out_end_lead_spin.setDecimals(1)
        self.fade_out_end_lead_spin.setValue(float(fade_out_end_lead_sec))
        timing_form.addRow("Length from end to start Fade Out:", self.fade_out_end_lead_spin)

        self.cross_fade_spin = QDoubleSpinBox()
        self.cross_fade_spin.setRange(0.0, 20.0)
        self.cross_fade_spin.setSingleStep(0.1)
        self.cross_fade_spin.setDecimals(1)
        self.cross_fade_spin.setValue(cross_fade_sec)
        timing_form.addRow("Cross Fade Seconds:", self.cross_fade_spin)
        layout.addWidget(timing_group)
        layout.addStretch(1)

        self.fade_out_when_done_checkbox.toggled.connect(self._sync_fade_out_end_lead_enabled)
        self._sync_fade_out_end_lead_enabled()
        return page

    def _sync_fade_out_end_lead_enabled(self) -> None:
        self.fade_out_end_lead_spin.setEnabled(self.fade_out_when_done_checkbox.isChecked())

    def _build_playback_page(
        self,
        max_multi_play_songs: int,
        multi_play_limit_action: str,
        playlist_play_mode: str,
        rapid_fire_play_mode: str,
        next_play_mode: str,
        playlist_loop_mode: str,
        candidate_error_action: str,
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

        mode_matrix_group = QGroupBox("Playback Candidate Rules:")
        mode_matrix_layout = QGridLayout(mode_matrix_group)
        mode_matrix_layout.addWidget(QLabel("Control"), 0, 0)
        mode_matrix_layout.addWidget(QLabel("Play unplayed only"), 0, 1)
        mode_matrix_layout.addWidget(QLabel("Play any (ignore red) available"), 0, 2)

        self.playlist_mode_unplayed_radio = QRadioButton("")
        self.playlist_mode_any_radio = QRadioButton("")
        self.playlist_mode_group = QButtonGroup(self)
        self.playlist_mode_group.addButton(self.playlist_mode_unplayed_radio)
        self.playlist_mode_group.addButton(self.playlist_mode_any_radio)
        if playlist_play_mode == "any_available":
            self.playlist_mode_any_radio.setChecked(True)
        else:
            self.playlist_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.playlist_mode_unplayed_radio, 1, 1)
        mode_matrix_layout.addWidget(self.playlist_mode_any_radio, 1, 2)

        self.rapid_fire_mode_unplayed_radio = QRadioButton("")
        self.rapid_fire_mode_any_radio = QRadioButton("")
        self.rapid_fire_mode_group = QButtonGroup(self)
        self.rapid_fire_mode_group.addButton(self.rapid_fire_mode_unplayed_radio)
        self.rapid_fire_mode_group.addButton(self.rapid_fire_mode_any_radio)
        if rapid_fire_play_mode == "any_available":
            self.rapid_fire_mode_any_radio.setChecked(True)
        else:
            self.rapid_fire_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.rapid_fire_mode_unplayed_radio, 2, 1)
        mode_matrix_layout.addWidget(self.rapid_fire_mode_any_radio, 2, 2)

        self.next_mode_unplayed_radio = QRadioButton("")
        self.next_mode_any_radio = QRadioButton("")
        self.next_mode_group = QButtonGroup(self)
        self.next_mode_group.addButton(self.next_mode_unplayed_radio)
        self.next_mode_group.addButton(self.next_mode_any_radio)
        if next_play_mode == "any_available":
            self.next_mode_any_radio.setChecked(True)
        else:
            self.next_mode_unplayed_radio.setChecked(True)
        mode_matrix_layout.addWidget(self.next_mode_unplayed_radio, 3, 1)
        mode_matrix_layout.addWidget(self.next_mode_any_radio, 3, 2)

        mode_matrix_layout.addWidget(QLabel("Play List"), 1, 0)
        mode_matrix_layout.addWidget(QLabel("Rapid Fire"), 2, 0)
        mode_matrix_layout.addWidget(QLabel("Next"), 3, 0)
        layout.addWidget(mode_matrix_group)

        playlist_loop_group = QGroupBox("When Loop is enabled in Play List:")
        playlist_loop_layout = QVBoxLayout(playlist_loop_group)
        self.playlist_loop_list_radio = QRadioButton("Loop List")
        self.playlist_loop_single_radio = QRadioButton("Loop Single")
        if playlist_loop_mode == "loop_single":
            self.playlist_loop_single_radio.setChecked(True)
        else:
            self.playlist_loop_list_radio.setChecked(True)
        playlist_loop_layout.addWidget(self.playlist_loop_list_radio)
        playlist_loop_layout.addWidget(self.playlist_loop_single_radio)
        layout.addWidget(playlist_loop_group)

        candidate_error_group = QGroupBox("When Play List/Next/Rapid Fire hits audio load error (purple):")
        candidate_error_layout = QVBoxLayout(candidate_error_group)
        self.candidate_error_stop_radio = QRadioButton("Stop playback")
        self.candidate_error_keep_radio = QRadioButton("Keep playing")
        if candidate_error_action == "keep_playing":
            self.candidate_error_keep_radio.setChecked(True)
        else:
            self.candidate_error_stop_radio.setChecked(True)
        candidate_error_layout.addWidget(self.candidate_error_stop_radio)
        candidate_error_layout.addWidget(self.candidate_error_keep_radio)
        layout.addWidget(candidate_error_group)

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

    def _build_audio_device_page(
        self,
        audio_output_device: str,
        available_audio_devices: List[str],
        available_midi_devices: List[tuple[str, str]],
        timecode_audio_output_device: str,
        timecode_midi_output_device: str,
        timecode_mode: str,
        timecode_fps: float,
        timecode_mtc_fps: float,
        timecode_mtc_idle_behavior: str,
        timecode_sample_rate: int,
        timecode_bit_depth: int,
        timecode_timeline_mode: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        playback_group = QGroupBox("Audio Playback")
        playback_layout = QVBoxLayout(playback_group)
        row = QHBoxLayout()
        row.addWidget(QLabel("Playback Device:"))
        self.audio_device_combo = QComboBox()
        row.addWidget(self.audio_device_combo, 1)
        self.audio_refresh_button = QPushButton("Refresh")
        self.audio_refresh_button.clicked.connect(self._refresh_audio_devices)
        row.addWidget(self.audio_refresh_button)
        playback_layout.addLayout(row)

        self.audio_device_hint = QLabel("")
        playback_layout.addWidget(self.audio_device_hint)
        layout.addWidget(playback_group)

        self._populate_audio_devices(available_audio_devices, audio_output_device)

        mode_group = QGroupBox("Timecode Mode")
        mode_form = QFormLayout(mode_group)
        self.timecode_mode_combo = QComboBox()
        self.timecode_mode_combo.addItem("All Zero", TIMECODE_MODE_ZERO)
        self.timecode_mode_combo.addItem("Follow Media/Audio Player", TIMECODE_MODE_FOLLOW)
        self.timecode_mode_combo.addItem("System Time", TIMECODE_MODE_SYSTEM)
        self.timecode_mode_combo.addItem("Pause Sync (Freeze While Playback Continues)", TIMECODE_MODE_FOLLOW_FREEZE)
        mode_form.addRow("Mode:", self.timecode_mode_combo)
        layout.addWidget(mode_group)

        timeline_group = QGroupBox("Timecode Display Timeline")
        timeline_layout = QVBoxLayout(timeline_group)
        self.timecode_timeline_cue_region_radio = QRadioButton("Relative to Cue Set Points")
        self.timecode_timeline_audio_file_radio = QRadioButton("Relative to Actual Audio File")
        if timecode_timeline_mode == "audio_file":
            self.timecode_timeline_audio_file_radio.setChecked(True)
        else:
            self.timecode_timeline_cue_region_radio.setChecked(True)
        timeline_layout.addWidget(self.timecode_timeline_cue_region_radio)
        timeline_layout.addWidget(self.timecode_timeline_audio_file_radio)
        layout.addWidget(timeline_group)

        ltc_group = QGroupBox("SMPTE Timecode (LTC)")
        ltc_form = QFormLayout(ltc_group)
        self.timecode_output_combo = QComboBox()
        self.timecode_output_combo.addItem("Follow playback device setting", "follow_playback")
        self.timecode_output_combo.addItem("Use system default", "default")
        self.timecode_output_combo.addItem("None (mute output)", "none")
        for name in available_audio_devices:
            self.timecode_output_combo.addItem(name, name)
        ltc_form.addRow("Output Device:", self.timecode_output_combo)

        self.timecode_fps_combo = QComboBox()
        for fps in TIME_CODE_FPS_CHOICES:
            self.timecode_fps_combo.addItem(f"{fps:g} fps", float(fps))
        ltc_form.addRow("Frame Rate:", self.timecode_fps_combo)

        self.timecode_sample_rate_combo = QComboBox()
        for sample_rate in TIME_CODE_SAMPLE_RATES:
            self.timecode_sample_rate_combo.addItem(f"{sample_rate} Hz", int(sample_rate))
        ltc_form.addRow("Sample Rate:", self.timecode_sample_rate_combo)

        self.timecode_bit_depth_combo = QComboBox()
        for bit_depth in TIME_CODE_BIT_DEPTHS:
            self.timecode_bit_depth_combo.addItem(f"{bit_depth}-bit", int(bit_depth))
        ltc_form.addRow("Bit Depth:", self.timecode_bit_depth_combo)
        layout.addWidget(ltc_group)

        mtc_group = QGroupBox("MIDI Timecode (MTC)")
        mtc_form = QFormLayout(mtc_group)
        self.timecode_midi_output_combo = QComboBox()
        self.timecode_midi_output_combo.addItem("None (disabled)", MIDI_OUTPUT_DEVICE_NONE)
        for device_id, device_name in available_midi_devices:
            self.timecode_midi_output_combo.addItem(device_name, device_id)
        mtc_form.addRow("MIDI Output Device:", self.timecode_midi_output_combo)

        self.timecode_mtc_fps_combo = QComboBox()
        for fps in TIME_CODE_MTC_FPS_CHOICES:
            self.timecode_mtc_fps_combo.addItem(f"{fps:g} fps", float(fps))
        mtc_form.addRow("Frame Rate:", self.timecode_mtc_fps_combo)

        self.timecode_mtc_idle_behavior_combo = QComboBox()
        self.timecode_mtc_idle_behavior_combo.addItem("Keep stream alive (no dark)", "keep_stream")
        self.timecode_mtc_idle_behavior_combo.addItem("Allow dark when idle", "allow_dark")
        mtc_form.addRow("Idle Behavior:", self.timecode_mtc_idle_behavior_combo)
        layout.addWidget(mtc_group)

        self._set_combo_data_or_default(self.timecode_output_combo, timecode_audio_output_device, "none")
        self._set_combo_data_or_default(self.timecode_mode_combo, timecode_mode, TIMECODE_MODE_FOLLOW)
        self._set_combo_float_or_default(self.timecode_fps_combo, float(timecode_fps), 30.0)
        self._set_combo_float_or_default(self.timecode_mtc_fps_combo, float(timecode_mtc_fps), 30.0)
        self._set_combo_data_or_default(self.timecode_mtc_idle_behavior_combo, timecode_mtc_idle_behavior, "keep_stream")
        self._set_combo_data_or_default(self.timecode_sample_rate_combo, int(timecode_sample_rate), 48000)
        self._set_combo_data_or_default(self.timecode_bit_depth_combo, int(timecode_bit_depth), 16)
        self._set_combo_data_or_default(self.timecode_midi_output_combo, timecode_midi_output_device, MIDI_OUTPUT_DEVICE_NONE)

        layout.addStretch(1)
        return page

    def _build_audio_preload_page(
        self,
        preload_audio_enabled: bool,
        preload_current_page_audio: bool,
        preload_audio_memory_limit_mb: int,
        preload_memory_pressure_enabled: bool,
        preload_pause_on_playback: bool,
        preload_total_ram_mb: int,
        preload_ram_cap_mb: int,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._preload_slider_step_mb = 128
        total_mb = max(512, int(preload_total_ram_mb))
        cap_mb = max(128, min(int(preload_ram_cap_mb), total_mb))
        cap_steps = max(1, cap_mb // self._preload_slider_step_mb)
        cap_mb = cap_steps * self._preload_slider_step_mb
        selected_mb = max(128, min(int(preload_audio_memory_limit_mb), cap_mb))
        selected_steps = max(1, selected_mb // self._preload_slider_step_mb)
        selected_mb = selected_steps * self._preload_slider_step_mb
        reserve_mb = max(128, int(total_mb - cap_mb))
        self._preload_ram_cap_mb = cap_mb

        options_group = QGroupBox("Behavior")
        options_form = QFormLayout(options_group)
        self.preload_audio_enabled_checkbox = QCheckBox("Enable audio preload cache")
        self.preload_audio_enabled_checkbox.setChecked(bool(preload_audio_enabled))
        options_form.addRow(self.preload_audio_enabled_checkbox)

        self.preload_current_page_checkbox = QCheckBox("Preload current page first")
        self.preload_current_page_checkbox.setChecked(bool(preload_current_page_audio))
        options_form.addRow(self.preload_current_page_checkbox)

        self.preload_memory_pressure_checkbox = QCheckBox("Auto-free cache when other apps use RAM (FIFO)")
        self.preload_memory_pressure_checkbox.setChecked(bool(preload_memory_pressure_enabled))
        options_form.addRow(self.preload_memory_pressure_checkbox)
        self.preload_pause_on_playback_checkbox = QCheckBox("Pause audio preload during playback")
        self.preload_pause_on_playback_checkbox.setChecked(bool(preload_pause_on_playback))
        options_form.addRow(self.preload_pause_on_playback_checkbox)
        layout.addWidget(options_group)

        ram_group = QGroupBox("RAM Limit")
        ram_layout = QVBoxLayout(ram_group)
        self.preload_ram_info_label = QLabel(
            f"System RAM: {total_mb} MB | Reserved: {reserve_mb} MB | Max Cache Limit: {cap_mb} MB"
        )
        self.preload_ram_info_label.setWordWrap(True)
        ram_layout.addWidget(self.preload_ram_info_label)

        self.preload_memory_slider = QSlider(Qt.Horizontal)
        self.preload_memory_slider.setRange(1, cap_steps)
        self.preload_memory_slider.setSingleStep(1)
        self.preload_memory_slider.setPageStep(1)
        self.preload_memory_slider.setValue(selected_steps)
        self.preload_memory_slider.valueChanged.connect(self._update_preload_slider_label)
        ram_layout.addWidget(self.preload_memory_slider)

        self.preload_memory_value_label = QLabel("")
        ram_layout.addWidget(self.preload_memory_value_label)
        self._update_preload_slider_label()
        layout.addWidget(ram_group)

        layout.addStretch(1)
        return page

    def _update_preload_slider_label(self) -> None:
        value = int(self.preload_memory_slider.value())
        selected_mb = value * int(self._preload_slider_step_mb)
        self.preload_memory_value_label.setText(f"Selected Cache Limit: {selected_mb} MB")

    def _build_talk_page(
        self,
        talk_volume_level: int,
        talk_fade_sec: float,
        talk_volume_mode: str,
        talk_blink_button: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()

        self.talk_volume_spin = QSpinBox()
        self.talk_volume_spin.setRange(0, 100)
        self.talk_volume_spin.setValue(talk_volume_level)
        form.addRow("Talk Volume Level:", self.talk_volume_spin)

        self.talk_fade_spin = QDoubleSpinBox()
        self.talk_fade_spin.setRange(0.0, 20.0)
        self.talk_fade_spin.setSingleStep(0.1)
        self.talk_fade_spin.setDecimals(1)
        self.talk_fade_spin.setValue(talk_fade_sec)
        form.addRow("Talk Fade Seconds:", self.talk_fade_spin)

        self.talk_blink_checkbox = QCheckBox("Blink Talk Button")
        self.talk_blink_checkbox.setChecked(talk_blink_button)
        form.addRow("Talk Button:", self.talk_blink_checkbox)
        self.talk_mode_percent_radio = QRadioButton("Use Talk level as % of current volume")
        self.talk_mode_lower_only_radio = QRadioButton("Lower to Talk level only")
        self.talk_mode_force_radio = QRadioButton("Set exactly to Talk level")
        if talk_volume_mode == "set_exact":
            self.talk_mode_force_radio.setChecked(True)
        elif talk_volume_mode == "lower_only":
            self.talk_mode_lower_only_radio.setChecked(True)
        else:
            self.talk_mode_percent_radio.setChecked(True)

        mode_group = QGroupBox("Talk Volume Behavior")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setContentsMargins(8, 8, 8, 8)
        mode_layout.setSpacing(6)
        mode_layout.addWidget(self.talk_mode_percent_radio)
        mode_layout.addWidget(self.talk_mode_lower_only_radio)
        mode_layout.addWidget(self.talk_mode_force_radio)
        layout.addLayout(form)
        layout.addWidget(mode_group)
        layout.addStretch(1)

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

    def selected_set_file_encoding(self) -> str:
        if self.set_file_encoding_gbk_radio.isChecked():
            return "gbk"
        return "utf8"

    def selected_ui_language(self) -> str:
        return normalize_language(str(self.ui_language_combo.currentData() or "en"))

    def selected_audio_output_device(self) -> str:
        return str(self.audio_device_combo.currentData() or "")

    def selected_timecode_audio_output_device(self) -> str:
        return str(self.timecode_output_combo.currentData() or "none")

    def selected_preload_audio_enabled(self) -> bool:
        return bool(self.preload_audio_enabled_checkbox.isChecked())

    def selected_preload_current_page_audio(self) -> bool:
        return bool(self.preload_current_page_checkbox.isChecked())

    def selected_preload_audio_memory_limit_mb(self) -> int:
        step_mb = int(self._preload_slider_step_mb)
        selected_mb = max(step_mb, int(self.preload_memory_slider.value()) * step_mb)
        return max(128, min(int(self._preload_ram_cap_mb), selected_mb))

    def selected_preload_memory_pressure_enabled(self) -> bool:
        return bool(self.preload_memory_pressure_checkbox.isChecked())

    def selected_preload_pause_on_playback(self) -> bool:
        return bool(self.preload_pause_on_playback_checkbox.isChecked())

    def selected_timecode_midi_output_device(self) -> str:
        return str(self.timecode_midi_output_combo.currentData() or MIDI_OUTPUT_DEVICE_NONE)

    def selected_timecode_mode(self) -> str:
        value = str(self.timecode_mode_combo.currentData() or TIMECODE_MODE_FOLLOW)
        if value not in {TIMECODE_MODE_ZERO, TIMECODE_MODE_FOLLOW, TIMECODE_MODE_SYSTEM, TIMECODE_MODE_FOLLOW_FREEZE}:
            return TIMECODE_MODE_FOLLOW
        return value

    def selected_timecode_fps(self) -> float:
        try:
            return float(self.timecode_fps_combo.currentData())
        except (TypeError, ValueError):
            return 30.0

    def selected_timecode_mtc_fps(self) -> float:
        try:
            return float(self.timecode_mtc_fps_combo.currentData())
        except (TypeError, ValueError):
            return 30.0

    def selected_timecode_mtc_idle_behavior(self) -> str:
        value = str(self.timecode_mtc_idle_behavior_combo.currentData() or "keep_stream")
        return value if value in {"keep_stream", "allow_dark"} else "keep_stream"

    def selected_timecode_sample_rate(self) -> int:
        try:
            return int(self.timecode_sample_rate_combo.currentData())
        except (TypeError, ValueError):
            return 48000

    def selected_timecode_bit_depth(self) -> int:
        try:
            return int(self.timecode_bit_depth_combo.currentData())
        except (TypeError, ValueError):
            return 16

    def selected_timecode_timeline_mode(self) -> str:
        if self.timecode_timeline_audio_file_radio.isChecked():
            return "audio_file"
        return "cue_region"

    def selected_max_multi_play_songs(self) -> int:
        return max(1, min(32, int(self.max_multi_play_spin.value())))

    def selected_multi_play_limit_action(self) -> str:
        if self.multi_play_disallow_radio.isChecked():
            return "disallow_more_play"
        return "stop_oldest"

    def selected_playlist_play_mode(self) -> str:
        if self.playlist_mode_any_radio.isChecked():
            return "any_available"
        return "unplayed_only"

    def selected_rapid_fire_play_mode(self) -> str:
        if self.rapid_fire_mode_any_radio.isChecked():
            return "any_available"
        return "unplayed_only"

    def selected_next_play_mode(self) -> str:
        if self.next_mode_any_radio.isChecked():
            return "any_available"
        return "unplayed_only"

    def selected_playlist_loop_mode(self) -> str:
        if self.playlist_loop_single_radio.isChecked():
            return "loop_single"
        return "loop_list"

    def selected_candidate_error_action(self) -> str:
        if self.candidate_error_keep_radio.isChecked():
            return "keep_playing"
        return "stop_playback"

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

    def selected_talk_volume_mode(self) -> str:
        if self.talk_mode_force_radio.isChecked():
            return "set_exact"
        if self.talk_mode_lower_only_radio.isChecked():
            return "lower_only"
        return "percent_of_master"

    def selected_hotkeys(self) -> Dict[str, tuple[str, str]]:
        result: Dict[str, tuple[str, str]] = {}
        for key, (edit1, edit2) in self._hotkey_edits.items():
            s1 = edit1.hotkey()
            s2 = edit2.hotkey()
            result[key] = (s1, s2)
        return result

    def selected_quick_action_enabled(self) -> bool:
        return bool(self.quick_action_enabled_checkbox.isChecked())

    def selected_quick_action_keys(self) -> List[str]:
        return [edit.hotkey() for edit in self._quick_action_edits]

    def selected_sound_button_hotkey_enabled(self) -> bool:
        return bool(self.sound_button_hotkey_enabled_checkbox.isChecked())

    def selected_sound_button_hotkey_priority(self) -> str:
        if self.sound_hotkey_priority_sound_first_radio.isChecked():
            return "sound_button_first"
        return "system_first"

    def selected_sound_button_hotkey_go_to_playing(self) -> bool:
        return bool(self.sound_button_go_to_playing_checkbox.isChecked())

    def _sync_jog_outside_group_enabled(self) -> None:
        enabled = self.cue_timeline_audio_file_radio.isChecked()
        self.jog_outside_group.setEnabled(enabled)

    def _set_combo_data_or_default(self, combo: QComboBox, selected_data, default_data) -> None:
        index = combo.findData(selected_data)
        if index < 0:
            index = combo.findData(default_data)
        if index < 0:
            index = 0
        combo.setCurrentIndex(index)

    def _set_combo_float_or_default(self, combo: QComboBox, selected_value: float, default_value: float) -> None:
        index = -1
        for i in range(combo.count()):
            data = combo.itemData(i)
            try:
                if abs(float(data) - float(selected_value)) <= 0.002:
                    index = i
                    break
            except (TypeError, ValueError):
                continue
        if index < 0:
            for i in range(combo.count()):
                data = combo.itemData(i)
                try:
                    if abs(float(data) - float(default_value)) <= 0.002:
                        index = i
                        break
                except (TypeError, ValueError):
                    continue
        if index < 0:
            index = 0
        combo.setCurrentIndex(index)

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
            self.audio_device_hint.setText(f"{tr('Detected ')}{len(devices)}{tr(' output device(s).')}")
        else:
            self.audio_device_hint.setText(tr("No explicit device list detected. System Default will be used."))

    def _refresh_audio_devices(self) -> None:
        selected = self.selected_audio_output_device()
        selected_timecode = self.selected_timecode_audio_output_device()
        try:
            from pyssp.audio_engine import list_output_devices

            devices = list_output_devices()
        except Exception:
            devices = []
        self._available_audio_devices = list(devices)
        self._populate_audio_devices(self._available_audio_devices, selected)
        self.timecode_output_combo.clear()
        self.timecode_output_combo.addItem("Follow playback device setting", "follow_playback")
        self.timecode_output_combo.addItem("Use system default", "default")
        self.timecode_output_combo.addItem("None (mute output)", "none")
        for name in self._available_audio_devices:
            self.timecode_output_combo.addItem(name, name)
        self._set_combo_data_or_default(self.timecode_output_combo, selected_timecode, "none")
        localize_widget_tree(self, self._ui_language)

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
        selected = QColorDialog.getColor(QColor(self.active_group_color), self, tr("Active Button Color"))
        if selected.isValid():
            self.active_group_color = selected.name().upper()
            self._refresh_color_button(self.active_color_btn, self.active_group_color)

    def _pick_inactive_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.inactive_group_color), self, tr("Inactive Button Color"))
        if selected.isValid():
            self.inactive_group_color = selected.name().upper()
            self._refresh_color_button(self.inactive_color_btn, self.inactive_group_color)

    def _pick_state_color(self, key: str, button: QPushButton, label: str) -> None:
        current = self.state_colors.get(key, "#FFFFFF")
        selected = QColorDialog.getColor(QColor(current), self, f"{tr(label)} {tr('Color')}")
        if selected.isValid():
            value = selected.name().upper()
            self.state_colors[key] = value
            self._refresh_color_button(button, value)

    def _pick_sound_text_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.sound_button_text_color), self, tr("Sound Button Text Color"))
        if selected.isValid():
            self.sound_button_text_color = selected.name().upper()
            self._refresh_color_button(self.sound_text_color_btn, self.sound_button_text_color)

    def _restore_defaults_current_page(self) -> None:
        idx = self.page_list.currentRow()
        if idx == 0:
            self._restore_general_defaults()
            return
        if idx == 1:
            self._restore_language_defaults()
            return
        if idx == 2:
            self._restore_hotkey_defaults()
            return
        if idx == 3:
            self._restore_color_defaults()
            return
        if idx == 4:
            self._restore_delay_defaults()
            return
        if idx == 5:
            self._restore_playback_defaults()
            return
        if idx == 6:
            self._restore_audio_device_defaults()
            return
        if idx == 7:
            self._restore_preload_defaults()
            return
        if idx == 8:
            self._restore_talk_defaults()
            return
        if idx == 9:
            self._restore_web_remote_defaults()
            return

    def _restore_language_defaults(self) -> None:
        d = self._DEFAULTS
        target = normalize_language(str(d.get("ui_language", "en")))
        index = self.ui_language_combo.findData(target)
        self.ui_language_combo.setCurrentIndex(index if index >= 0 else 0)

    def _restore_general_defaults(self) -> None:
        d = self._DEFAULTS
        self.title_limit_spin.setValue(int(d["title_char_limit"]))
        self.log_file_checkbox.setChecked(bool(d["log_file_enabled"]))
        self.reset_on_startup_checkbox.setChecked(bool(d["reset_all_on_startup"]))
        if str(d["set_file_encoding"]).strip().lower() == "gbk":
            self.set_file_encoding_gbk_radio.setChecked(True)
        else:
            self.set_file_encoding_utf8_radio.setChecked(True)
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

    def _restore_hotkey_defaults(self) -> None:
        d = self._DEFAULTS
        defaults = dict(d["hotkeys"])
        for key, (edit1, edit2) in self._hotkey_edits.items():
            val1, val2 = defaults.get(key, ("", ""))
            edit1.setHotkey(val1)
            edit2.setHotkey(val2)
        self.quick_action_enabled_checkbox.setChecked(False)
        qa_defaults = default_quick_action_keys()
        for i, edit in enumerate(self._quick_action_edits):
            edit.setHotkey(qa_defaults[i] if i < len(qa_defaults) else "")
        self.sound_button_hotkey_enabled_checkbox.setChecked(bool(d["sound_button_hotkey_enabled"]))
        if str(d["sound_button_hotkey_priority"]) == "sound_button_first":
            self.sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.sound_hotkey_priority_system_first_radio.setChecked(True)
        self.sound_button_go_to_playing_checkbox.setChecked(bool(d["sound_button_hotkey_go_to_playing"]))
        self._validate_hotkey_conflicts()

    def _normalize_hotkey_for_conflict(self, raw: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return ""
        aliases = {
            "control": "Ctrl",
            "ctrl": "Ctrl",
            "shift": "Shift",
            "alt": "Alt",
            "meta": "Meta",
            "win": "Meta",
            "super": "Meta",
        }
        lower = text.lower()
        if lower in aliases:
            return aliases[lower]
        canonical = QKeySequence(text).toString().strip()
        return canonical or text

    def _validate_hotkey_conflicts(self) -> None:
        seen: Dict[str, tuple[str, int]] = {}
        conflicts: List[str] = []
        conflict_cells: set[tuple[str, int]] = set()
        for key, (edit1, edit2) in self._hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                token = self._normalize_hotkey_for_conflict(edit.hotkey())
                if not token:
                    continue
                if token in seen:
                    prev_key, prev_slot_index = seen[token]
                    conflict_cells.add((prev_key, prev_slot_index))
                    conflict_cells.add((key, slot_index))
                    left = f"{tr(self._hotkey_labels.get(prev_key, prev_key))} ({prev_slot_index})"
                    right = f"{tr(self._hotkey_labels.get(key, key))} ({slot_index})"
                    conflicts.append(f"{token}: {left} {tr('and')} {right}")
                else:
                    seen[token] = (key, slot_index)

        quick_enabled = bool(self.quick_action_enabled_checkbox.isChecked())
        quick_conflict_rows: set[int] = set()
        if quick_enabled:
            for idx, edit in enumerate(self._quick_action_edits):
                token = self._normalize_hotkey_for_conflict(edit.hotkey())
                if not token:
                    continue
                mark = ("quick_action", idx + 1)
                if token in seen:
                    prev_key, prev_slot_index = seen[token]
                    conflict_cells.add((prev_key, prev_slot_index))
                    conflicts.append(
                        f"{token}: {self._describe_conflict_target(prev_key, prev_slot_index)} {tr('and')} {tr('Quick Action')} ({idx + 1})"
                    )
                    quick_conflict_rows.add(idx)
                    if prev_key == "quick_action":
                        quick_conflict_rows.add(max(0, prev_slot_index - 1))
                else:
                    seen[token] = mark

        for idx, edit in enumerate(self._quick_action_edits):
            if quick_enabled and idx in quick_conflict_rows:
                edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
            else:
                edit.setStyleSheet("")

        for key, (edit1, edit2) in self._hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                if (key, slot_index) in conflict_cells:
                    edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
                else:
                    edit.setStyleSheet("")

        has_conflict = bool(conflicts)
        if self.ok_button is not None:
            self.ok_button.setEnabled(not has_conflict)
        if self.hotkey_warning_label is None:
            return
        if not has_conflict:
            self.hotkey_warning_label.setVisible(False)
            self.hotkey_warning_label.setText("")
            return
        display = "; ".join(conflicts[:4])
        if len(conflicts) > 4:
            display += f"; +{len(conflicts) - 4} {tr('more')}"
        self.hotkey_warning_label.setText(f"{tr('Hotkey conflict detected. Fix duplicates before saving.')} {display}")
        self.hotkey_warning_label.setVisible(True)

    def _describe_conflict_target(self, key: str, slot_index: int) -> str:
        if key == "quick_action":
            return f"{tr('Quick Action')} ({slot_index})"
        return f"{tr(self._hotkey_labels.get(key, key))} ({slot_index})"

    def _restore_delay_defaults(self) -> None:
        d = self._DEFAULTS
        self.fade_on_quick_action_checkbox.setChecked(bool(d["fade_on_quick_action_hotkey"]))
        self.fade_on_sound_hotkey_checkbox.setChecked(bool(d["fade_on_sound_button_hotkey"]))
        self.fade_on_pause_checkbox.setChecked(bool(d["fade_on_pause"]))
        self.fade_on_resume_checkbox.setChecked(bool(d["fade_on_resume"]))
        self.fade_on_stop_checkbox.setChecked(bool(d["fade_on_stop"]))
        self.fade_in_spin.setValue(float(d["fade_in_sec"]))
        self.fade_out_spin.setValue(float(d["fade_out_sec"]))
        self.fade_out_when_done_checkbox.setChecked(bool(d["fade_out_when_done_playing"]))
        self.fade_out_end_lead_spin.setValue(float(d["fade_out_end_lead_sec"]))
        self.cross_fade_spin.setValue(float(d["cross_fade_sec"]))
        self._sync_fade_out_end_lead_enabled()

    def _restore_playback_defaults(self) -> None:
        d = self._DEFAULTS
        self.max_multi_play_spin.setValue(int(d["max_multi_play_songs"]))
        if d["multi_play_limit_action"] == "disallow_more_play":
            self.multi_play_disallow_radio.setChecked(True)
        else:
            self.multi_play_stop_oldest_radio.setChecked(True)
        if str(d["playlist_play_mode"]) == "any_available":
            self.playlist_mode_any_radio.setChecked(True)
        else:
            self.playlist_mode_unplayed_radio.setChecked(True)
        if str(d["rapid_fire_play_mode"]) == "any_available":
            self.rapid_fire_mode_any_radio.setChecked(True)
        else:
            self.rapid_fire_mode_unplayed_radio.setChecked(True)
        if str(d["next_play_mode"]) == "any_available":
            self.next_mode_any_radio.setChecked(True)
        else:
            self.next_mode_unplayed_radio.setChecked(True)
        if str(d["playlist_loop_mode"]) == "loop_single":
            self.playlist_loop_single_radio.setChecked(True)
        else:
            self.playlist_loop_list_radio.setChecked(True)
        if str(d["candidate_error_action"]) == "keep_playing":
            self.candidate_error_keep_radio.setChecked(True)
        else:
            self.candidate_error_stop_radio.setChecked(True)
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
        d = self._DEFAULTS
        self._set_combo_data_or_default(self.audio_device_combo, "", "")
        self._set_combo_data_or_default(
            self.timecode_output_combo,
            str(d["timecode_audio_output_device"]),
            "none",
        )
        self._set_combo_data_or_default(
            self.timecode_mode_combo,
            str(d["timecode_mode"]),
            TIMECODE_MODE_FOLLOW,
        )
        self._set_combo_float_or_default(
            self.timecode_fps_combo,
            float(d["timecode_fps"]),
            30.0,
        )
        self._set_combo_float_or_default(
            self.timecode_mtc_fps_combo,
            float(d["timecode_mtc_fps"]),
            30.0,
        )
        self._set_combo_data_or_default(
            self.timecode_mtc_idle_behavior_combo,
            str(d["timecode_mtc_idle_behavior"]),
            "keep_stream",
        )
        self._set_combo_data_or_default(
            self.timecode_midi_output_combo,
            str(d["timecode_midi_output_device"]),
            MIDI_OUTPUT_DEVICE_NONE,
        )
        self._set_combo_data_or_default(
            self.timecode_sample_rate_combo,
            int(d["timecode_sample_rate"]),
            48000,
        )
        self._set_combo_data_or_default(
            self.timecode_bit_depth_combo,
            int(d["timecode_bit_depth"]),
            16,
        )
        if str(d["timecode_timeline_mode"]) == "audio_file":
            self.timecode_timeline_audio_file_radio.setChecked(True)
        else:
            self.timecode_timeline_cue_region_radio.setChecked(True)

    def _restore_preload_defaults(self) -> None:
        d = self._DEFAULTS
        self.preload_audio_enabled_checkbox.setChecked(bool(d["preload_audio_enabled"]))
        self.preload_current_page_checkbox.setChecked(bool(d["preload_current_page_audio"]))
        self.preload_memory_pressure_checkbox.setChecked(bool(d["preload_memory_pressure_enabled"]))
        self.preload_pause_on_playback_checkbox.setChecked(bool(d["preload_pause_on_playback"]))
        step_mb = int(self._preload_slider_step_mb)
        target_mb = max(step_mb, min(int(self._preload_ram_cap_mb), int(d["preload_audio_memory_limit_mb"])))
        self.preload_memory_slider.setValue(max(1, target_mb // step_mb))
        self._update_preload_slider_label()

    def _restore_talk_defaults(self) -> None:
        d = self._DEFAULTS
        self.talk_volume_spin.setValue(int(d["talk_volume_level"]))
        self.talk_fade_spin.setValue(float(d["talk_fade_sec"]))
        self.talk_blink_checkbox.setChecked(bool(d["talk_blink_button"]))
        mode = str(d["talk_volume_mode"])
        if mode == "set_exact":
            self.talk_mode_force_radio.setChecked(True)
        elif mode == "lower_only":
            self.talk_mode_lower_only_radio.setChecked(True)
        else:
            self.talk_mode_percent_radio.setChecked(True)

    def _restore_web_remote_defaults(self) -> None:
        d = self._DEFAULTS
        self.web_remote_enabled_checkbox.setChecked(bool(d["web_remote_enabled"]))
        self.web_remote_port_spin.setValue(int(d["web_remote_port"]))
