from __future__ import annotations

from ..shared import *
from ..widgets import *


class LyricsPageMixin:
    def _build_lyric_page(
        self,
        main_ui_lyric_display_mode: str,
        search_lyric_on_add_sound_button: bool,
        new_lyric_file_format: str,
        lyric_display_font_family: str,
        lyric_display_font_size: int,
        lyric_display_previous_line_count: int,
        lyric_display_next_line_count: int,
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

        display_font_group = QGroupBox("Lyric Display Window")
        display_font_layout = QFormLayout(display_font_group)
        self.lyric_display_font_family_combo = QFontComboBox()
        self._populate_display_font_combo(self.lyric_display_font_family_combo, lyric_display_font_family)
        self.lyric_display_font_size_spin = QSpinBox()
        self.lyric_display_font_size_spin.setRange(10, 240)
        self.lyric_display_font_size_spin.setValue(max(10, int(lyric_display_font_size)))
        self.lyric_display_previous_line_count_spin = QSpinBox()
        self.lyric_display_previous_line_count_spin.setRange(0, 20)
        self.lyric_display_previous_line_count_spin.setValue(max(0, int(lyric_display_previous_line_count)))
        self.lyric_display_next_line_count_spin = QSpinBox()
        self.lyric_display_next_line_count_spin.setRange(0, 20)
        self.lyric_display_next_line_count_spin.setValue(max(0, int(lyric_display_next_line_count)))
        self.lyric_display_played_text_size_spin = QSpinBox()
        self.lyric_display_played_text_size_spin.setRange(8, 240)
        self.lyric_display_played_text_size_spin.setValue(int(self._lyric_display_role_sizes.get("played", 24)))
        self.lyric_display_current_text_size_spin = QSpinBox()
        self.lyric_display_current_text_size_spin.setRange(8, 240)
        self.lyric_display_current_text_size_spin.setValue(int(self._lyric_display_role_sizes.get("current", 40)))
        self.lyric_display_next_text_size_spin = QSpinBox()
        self.lyric_display_next_text_size_spin.setRange(8, 240)
        self.lyric_display_next_text_size_spin.setValue(int(self._lyric_display_role_sizes.get("next", 32)))
        self.lyric_display_auto_adjust_role_sizes_checkbox = QCheckBox("Auto adjust role sizes from base text size")
        self.lyric_display_auto_adjust_role_sizes_checkbox.setChecked(bool(self._lyric_display_auto_adjust_role_sizes))
        self.lyric_display_played_scale_percent_spin = QSpinBox()
        self.lyric_display_played_scale_percent_spin.setRange(25, 300)
        self.lyric_display_played_scale_percent_spin.setSuffix("%")
        self.lyric_display_played_scale_percent_spin.setValue(int(self._lyric_display_role_scale_percents.get("played", 70)))
        self.lyric_display_current_scale_percent_spin = QSpinBox()
        self.lyric_display_current_scale_percent_spin.setRange(25, 300)
        self.lyric_display_current_scale_percent_spin.setSuffix("%")
        self.lyric_display_current_scale_percent_spin.setValue(int(self._lyric_display_role_scale_percents.get("current", 115)))
        self.lyric_display_next_scale_percent_spin = QSpinBox()
        self.lyric_display_next_scale_percent_spin.setRange(25, 300)
        self.lyric_display_next_scale_percent_spin.setSuffix("%")
        self.lyric_display_next_scale_percent_spin.setValue(int(self._lyric_display_role_scale_percents.get("next", 90)))
        self.lyric_display_played_bold_checkbox = QCheckBox("Bold")
        self.lyric_display_played_bold_checkbox.setChecked(bool(self._lyric_display_role_bold.get("played", True)))
        self.lyric_display_current_bold_checkbox = QCheckBox("Bold")
        self.lyric_display_current_bold_checkbox.setChecked(bool(self._lyric_display_role_bold.get("current", True)))
        self.lyric_display_next_bold_checkbox = QCheckBox("Bold")
        self.lyric_display_next_bold_checkbox.setChecked(bool(self._lyric_display_role_bold.get("next", True)))
        self.lyric_display_played_italic_checkbox = QCheckBox("Italic")
        self.lyric_display_played_italic_checkbox.setChecked(bool(self._lyric_display_role_italic.get("played", False)))
        self.lyric_display_current_italic_checkbox = QCheckBox("Italic")
        self.lyric_display_current_italic_checkbox.setChecked(bool(self._lyric_display_role_italic.get("current", False)))
        self.lyric_display_next_italic_checkbox = QCheckBox("Italic")
        self.lyric_display_next_italic_checkbox.setChecked(bool(self._lyric_display_role_italic.get("next", False)))
        self.lyric_display_played_color_btn = QPushButton()
        self.lyric_display_current_color_btn = QPushButton()
        self.lyric_display_next_color_btn = QPushButton()
        self._refresh_color_button(
            self.lyric_display_played_color_btn,
            str(self._lyric_display_role_colors.get("played", "#A0A0A0")),
        )
        self._refresh_color_button(
            self.lyric_display_current_color_btn,
            str(self._lyric_display_role_colors.get("current", "#FFD400")),
        )
        self._refresh_color_button(
            self.lyric_display_next_color_btn,
            str(self._lyric_display_role_colors.get("next", "#FFFFFF")),
        )
        self.lyric_display_played_color_btn.clicked.connect(lambda: self._pick_lyric_role_color("lyric_display", "played"))
        self.lyric_display_current_color_btn.clicked.connect(lambda: self._pick_lyric_role_color("lyric_display", "current"))
        self.lyric_display_next_color_btn.clicked.connect(lambda: self._pick_lyric_role_color("lyric_display", "next"))
        display_font_layout.addRow("Font:", self.lyric_display_font_family_combo)
        display_font_layout.addRow("Text Size:", self.lyric_display_font_size_spin)
        display_font_layout.addRow("Played Lyric Lines:", self.lyric_display_previous_line_count_spin)
        display_font_layout.addRow("Next Lyric Lines:", self.lyric_display_next_line_count_spin)
        display_font_layout.addRow(self.lyric_display_auto_adjust_role_sizes_checkbox)
        display_font_layout.addRow("Played Scale:", self.lyric_display_played_scale_percent_spin)
        display_font_layout.addRow("Current Scale:", self.lyric_display_current_scale_percent_spin)
        display_font_layout.addRow("Next Scale:", self.lyric_display_next_scale_percent_spin)
        display_font_layout.addRow("Played Text Size:", self.lyric_display_played_text_size_spin)
        display_font_layout.addRow("Current Text Size:", self.lyric_display_current_text_size_spin)
        display_font_layout.addRow("Next Text Size:", self.lyric_display_next_text_size_spin)
        display_font_layout.addRow("Played Style:", self._build_role_style_row(self.lyric_display_played_bold_checkbox, self.lyric_display_played_italic_checkbox))
        display_font_layout.addRow("Current Style:", self._build_role_style_row(self.lyric_display_current_bold_checkbox, self.lyric_display_current_italic_checkbox))
        display_font_layout.addRow("Next Style:", self._build_role_style_row(self.lyric_display_next_bold_checkbox, self.lyric_display_next_italic_checkbox))
        display_font_layout.addRow("Played Color:", self.lyric_display_played_color_btn)
        display_font_layout.addRow("Current Color:", self.lyric_display_current_color_btn)
        display_font_layout.addRow("Next Color:", self.lyric_display_next_color_btn)
        self.lyric_display_auto_adjust_role_sizes_checkbox.toggled.connect(self._sync_lyric_role_size_mode)
        layout.addWidget(display_font_group)
        self._sync_lyric_role_size_mode()

        layout.addStretch(1)
        return page

    def _populate_display_font_combo(self, combo: QComboBox, selected_family: str) -> None:
        selected = str(selected_family or "").strip()
        if isinstance(combo, QFontComboBox):
            fallback = selected or bundled_display_font_family() or QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()
            combo.setCurrentFont(QFont(fallback))
            return
        combo.clear()
        bundled = bundled_display_font_family()
        families = available_display_font_families()
        for family in families:
            label = family
            if bundled and family == bundled:
                label = f"{family} (Bundled)"
            combo.addItem(label, family)
        if combo.count() == 0:
            fallback = selected or QFontDatabase.systemFont(QFontDatabase.GeneralFont).family()
            combo.addItem(fallback, fallback)
        self._set_combo_data_or_default(combo, selected, str(combo.itemData(0) or ""))

    def _build_role_style_row(self, *widgets: QWidget) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        for widget in widgets:
            row_layout.addWidget(widget)
        row_layout.addStretch(1)
        return row

    def _sync_lyric_role_size_mode(self) -> None:
        auto_mode = bool(self.lyric_display_auto_adjust_role_sizes_checkbox.isChecked())
        for widget in [
            self.lyric_display_played_scale_percent_spin,
            self.lyric_display_current_scale_percent_spin,
            self.lyric_display_next_scale_percent_spin,
        ]:
            widget.setEnabled(auto_mode)
        for widget in [
            self.lyric_display_played_text_size_spin,
            self.lyric_display_current_text_size_spin,
            self.lyric_display_next_text_size_spin,
        ]:
            widget.setEnabled(not auto_mode)

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
