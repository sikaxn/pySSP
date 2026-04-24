from __future__ import annotations

from ..shared import *
from ..widgets import *


class LyricsPageMixin:
    def _build_lyric_page(
        self,
        main_ui_lyric_display_mode: str,
        search_lyric_on_add_sound_button: bool,
        new_lyric_file_format: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        display_group = QGroupBox("Main UI Lyric Display")
        display_layout = QVBoxLayout(display_group)
        token = str(main_ui_lyric_display_mode or "").strip().lower()
        if token not in {"always", "when_available", "never"}:
            token = "always"
        self.main_ui_lyric_display_always_radio = QRadioButton("Always")
        self.main_ui_lyric_display_when_available_radio = QRadioButton("When Lyric Available")
        self.main_ui_lyric_display_never_radio = QRadioButton("Never")
        if token == "when_available":
            self.main_ui_lyric_display_when_available_radio.setChecked(True)
        elif token == "never":
            self.main_ui_lyric_display_never_radio.setChecked(True)
        else:
            self.main_ui_lyric_display_always_radio.setChecked(True)
        display_layout.addWidget(self.main_ui_lyric_display_always_radio)
        display_layout.addWidget(self.main_ui_lyric_display_when_available_radio)
        display_layout.addWidget(self.main_ui_lyric_display_never_radio)
        layout.addWidget(display_group)

        link_group = QGroupBox("Lyric Link")
        link_layout = QFormLayout(link_group)
        self.search_lyric_on_add_sound_button_checkbox = QCheckBox("Search lyric file when adding sound button")
        self.search_lyric_on_add_sound_button_checkbox.setChecked(bool(search_lyric_on_add_sound_button))
        link_layout.addRow(self.search_lyric_on_add_sound_button_checkbox)
        self.new_lyric_file_format_combo = QComboBox()
        self.new_lyric_file_format_combo.addItem("SRT", "srt")
        self.new_lyric_file_format_combo.addItem("LRC", "lrc")
        token = str(new_lyric_file_format or "").strip().lower()
        if token not in {"srt", "lrc"}:
            token = "srt"
        self._set_combo_data_or_default(self.new_lyric_file_format_combo, token, "srt")
        link_layout.addRow("Default format for new lyric file:", self.new_lyric_file_format_combo)
        layout.addWidget(link_group)

        layout.addStretch(1)
        return page

    def _rescan_supported_audio_formats(self) -> None:
        if callable(self._is_playback_or_loading_active):
            try:
                if bool(self._is_playback_or_loading_active()):
                    QMessageBox.warning(
                        self,
                        tr("Audio Format Detection"),
                        tr("Stop playback before rescanning supported audio formats."),
                    )
                    return
            except Exception:
                pass
        detected = detect_supported_audio_format_extensions(timeout_sec=10.0)
        supported = [str(token).strip().lower() for token in detected if str(token).strip()]
        self.supported_audio_format_extensions_value.setText(", ".join(supported) if supported else tr("(none detected)"))
