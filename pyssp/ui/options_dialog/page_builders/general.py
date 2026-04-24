from __future__ import annotations

from ..shared import *
from ..widgets import *


class GeneralPageMixin:
    def _build_general_page(
        self,
        title_char_limit: int,
        show_file_notifications: bool,
        now_playing_display_mode: str,
        log_file_enabled: bool,
        reset_all_on_startup: bool,
        click_playing_action: str,
        search_double_click_action: str,
        set_file_encoding: str,
        main_progress_display_mode: str,
        main_progress_show_text: bool,
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
        mode_token = str(now_playing_display_mode or "caption").strip().lower()
        if mode_token not in {"filename", "filepath", "caption", "note", "caption_note"}:
            mode_token = "caption"
        self.now_playing_caption_radio = QRadioButton("Show Caption (Default)")
        self.now_playing_filename_radio = QRadioButton("Show File Name")
        self.now_playing_filepath_radio = QRadioButton("Show File Name with Full Path")
        self.now_playing_note_radio = QRadioButton("Show Notes")
        self.now_playing_caption_note_radio = QRadioButton("Show Caption with Notes")
        if mode_token == "filename":
            self.now_playing_filename_radio.setChecked(True)
        elif mode_token == "filepath":
            self.now_playing_filepath_radio.setChecked(True)
        elif mode_token == "note":
            self.now_playing_note_radio.setChecked(True)
        elif mode_token == "caption_note":
            self.now_playing_caption_note_radio.setChecked(True)
        else:
            self.now_playing_caption_radio.setChecked(True)
        now_playing_group = QGroupBox("Now Playing Display")
        now_playing_layout = QVBoxLayout(now_playing_group)
        now_playing_layout.addWidget(self.now_playing_caption_radio)
        now_playing_layout.addWidget(self.now_playing_filename_radio)
        now_playing_layout.addWidget(self.now_playing_filepath_radio)
        now_playing_layout.addWidget(self.now_playing_note_radio)
        now_playing_layout.addWidget(self.now_playing_caption_note_radio)

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
        layout.addWidget(now_playing_group)

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

        transport_group = QGroupBox("Main Transport Display")
        transport_layout = QVBoxLayout(transport_group)
        self.main_progress_display_progress_bar_radio = QRadioButton("Display Progress Bar")
        self.main_progress_display_waveform_radio = QRadioButton("Display Waveform")
        mode_token = str(main_progress_display_mode or "").strip().lower()
        if mode_token not in {"progress_bar", "waveform"}:
            mode_token = "progress_bar"
        if mode_token == "waveform":
            self.main_progress_display_waveform_radio.setChecked(True)
        else:
            self.main_progress_display_progress_bar_radio.setChecked(True)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.main_progress_display_progress_bar_radio)
        mode_row.addWidget(self.main_progress_display_waveform_radio)
        mode_row.addStretch(1)
        transport_layout.addLayout(mode_row)
        waveform_note = QLabel(
            "If Main Transport uses Waveform display, it is recommended to enable Audio Preload for better performance."
        )
        waveform_note.setWordWrap(True)
        transport_layout.addWidget(waveform_note)
        self.main_progress_show_text_checkbox = QCheckBox("Show transport text on progress display")
        self.main_progress_show_text_checkbox.setChecked(bool(main_progress_show_text))
        transport_layout.addWidget(self.main_progress_show_text_checkbox)
        layout.addWidget(transport_group)
        layout.addStretch(1)
        return page

