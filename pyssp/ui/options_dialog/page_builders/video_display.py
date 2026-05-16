from __future__ import annotations

from ..shared import *
from ..widgets import *


class VideoDisplayPageMixin:
    def _build_video_display_page(
        self,
        *,
        mode_playing: str,
        mode_idle: str,
        show_lyric_overlay: bool,
        show_stage_alert: bool,
        lyric_overlay_rect: Dict[str, int],
        lyric_font_family: str,
        lyric_font_size: int,
        lyric_previous_line_count: int,
        lyric_next_line_count: int,
        lyric_role_colors: Dict[str, str],
        lyric_auto_adjust_role_sizes: bool,
        lyric_role_scale_percents: Dict[str, int],
        lyric_role_sizes: Dict[str, int],
        lyric_role_bold: Dict[str, bool],
        lyric_role_italic: Dict[str, bool],
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        routing_group = QGroupBox("Routing Defaults")
        routing_form = QFormLayout(routing_group)
        self.video_display_mode_playing_combo = QComboBox()
        for label, value in [
            ("Video", "video"),
            ("Lyric Display", "lyric_display"),
            ("Stage Display", "stage_display"),
            ("Blank", "blank"),
            ("White Screen", "white_screen"),
            ("Colour Bars", "colour_bars"),
        ]:
            self.video_display_mode_playing_combo.addItem(label, value)
        self._set_combo_data_or_default(self.video_display_mode_playing_combo, mode_playing, "video")
        routing_form.addRow("When video is playing:", self.video_display_mode_playing_combo)
        self.video_display_mode_idle_combo = QComboBox()
        for label, value in [
            ("Lyric Display", "lyric_display"),
            ("Stage Display", "stage_display"),
            ("Blank", "blank"),
            ("White Screen", "white_screen"),
            ("Colour Bars", "colour_bars"),
        ]:
            self.video_display_mode_idle_combo.addItem(label, value)
        self._set_combo_data_or_default(self.video_display_mode_idle_combo, mode_idle, "blank")
        routing_form.addRow("When video is not playing:", self.video_display_mode_idle_combo)
        layout.addWidget(routing_group)

        overlay_group = QGroupBox("Overlay")
        overlay_form = QFormLayout(overlay_group)
        self.video_display_show_lyric_overlay_checkbox = QCheckBox("Show lyric on video")
        self.video_display_show_lyric_overlay_checkbox.setChecked(bool(show_lyric_overlay))
        overlay_form.addRow(self.video_display_show_lyric_overlay_checkbox)
        self.video_display_show_stage_alert_checkbox = QCheckBox("Show stage alert on video display")
        self.video_display_show_stage_alert_checkbox.setChecked(bool(show_stage_alert))
        overlay_form.addRow(self.video_display_show_stage_alert_checkbox)
        layout.addWidget(overlay_group)

        preview_group = QGroupBox("Lyric Overlay Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.video_display_overlay_editor = StageDisplayLayoutEditor()
        overlay_gadgets = normalize_stage_display_gadgets({})
        rect = dict(lyric_overlay_rect or {})
        for key, spec in overlay_gadgets.items():
            spec["visible"] = key == "lyric"
            spec["hide_text"] = key == "lyric"
            spec["hide_border"] = key != "lyric"
            spec["orientation"] = "vertical"
            if key == "lyric":
                spec["x"] = int(rect.get("x", 800))
                spec["y"] = int(rect.get("y", 6800))
                spec["w"] = int(rect.get("w", 8400))
                spec["h"] = int(rect.get("h", 2400))
                spec["z"] = 99
            else:
                spec["z"] = 0
        self.video_display_overlay_editor.set_gadgets(overlay_gadgets)
        self.video_display_overlay_editor.set_font_settings(
            default_font_family=lyric_font_family,
            default_value_font_size=lyric_font_size,
            lyric_font_family=lyric_font_family,
            lyric_value_font_size=lyric_font_size,
        )
        preview_layout.addWidget(self.video_display_overlay_editor, 1)
        preview_note = QLabel("Drag and resize the lyric gadget to place the video lyric overlay.")
        preview_note.setWordWrap(True)
        preview_layout.addWidget(preview_note)
        layout.addWidget(preview_group, 1)

        font_group = QGroupBox("Lyric Overlay Style")
        font_form = QFormLayout(font_group)
        self.video_display_lyric_font_family_combo = QFontComboBox()
        self._populate_display_font_combo(self.video_display_lyric_font_family_combo, lyric_font_family)
        self.video_display_lyric_font_size_spin = QSpinBox()
        self.video_display_lyric_font_size_spin.setRange(10, 240)
        self.video_display_lyric_font_size_spin.setValue(max(10, int(lyric_font_size)))
        self.video_display_lyric_previous_line_count_spin = QSpinBox()
        self.video_display_lyric_previous_line_count_spin.setRange(0, 20)
        self.video_display_lyric_previous_line_count_spin.setValue(max(0, int(lyric_previous_line_count)))
        self.video_display_lyric_next_line_count_spin = QSpinBox()
        self.video_display_lyric_next_line_count_spin.setRange(0, 20)
        self.video_display_lyric_next_line_count_spin.setValue(max(0, int(lyric_next_line_count)))
        self.video_display_lyric_auto_adjust_role_sizes_checkbox = QCheckBox("Auto adjust role sizes from lyric text size")
        self.video_display_lyric_auto_adjust_role_sizes_checkbox.setChecked(bool(lyric_auto_adjust_role_sizes))
        self.video_display_lyric_played_scale_percent_spin = QSpinBox()
        self.video_display_lyric_played_scale_percent_spin.setRange(25, 300)
        self.video_display_lyric_played_scale_percent_spin.setSuffix("%")
        self.video_display_lyric_played_scale_percent_spin.setValue(int(lyric_role_scale_percents.get("played", 70)))
        self.video_display_lyric_current_scale_percent_spin = QSpinBox()
        self.video_display_lyric_current_scale_percent_spin.setRange(25, 300)
        self.video_display_lyric_current_scale_percent_spin.setSuffix("%")
        self.video_display_lyric_current_scale_percent_spin.setValue(int(lyric_role_scale_percents.get("current", 115)))
        self.video_display_lyric_next_scale_percent_spin = QSpinBox()
        self.video_display_lyric_next_scale_percent_spin.setRange(25, 300)
        self.video_display_lyric_next_scale_percent_spin.setSuffix("%")
        self.video_display_lyric_next_scale_percent_spin.setValue(int(lyric_role_scale_percents.get("next", 90)))
        self.video_display_lyric_played_text_size_spin = QSpinBox()
        self.video_display_lyric_played_text_size_spin.setRange(8, 240)
        self.video_display_lyric_played_text_size_spin.setValue(int(lyric_role_sizes.get("played", 24)))
        self.video_display_lyric_current_text_size_spin = QSpinBox()
        self.video_display_lyric_current_text_size_spin.setRange(8, 240)
        self.video_display_lyric_current_text_size_spin.setValue(int(lyric_role_sizes.get("current", 40)))
        self.video_display_lyric_next_text_size_spin = QSpinBox()
        self.video_display_lyric_next_text_size_spin.setRange(8, 240)
        self.video_display_lyric_next_text_size_spin.setValue(int(lyric_role_sizes.get("next", 32)))
        self.video_display_lyric_played_bold_checkbox = QCheckBox("Bold")
        self.video_display_lyric_played_bold_checkbox.setChecked(bool(lyric_role_bold.get("played", True)))
        self.video_display_lyric_current_bold_checkbox = QCheckBox("Bold")
        self.video_display_lyric_current_bold_checkbox.setChecked(bool(lyric_role_bold.get("current", True)))
        self.video_display_lyric_next_bold_checkbox = QCheckBox("Bold")
        self.video_display_lyric_next_bold_checkbox.setChecked(bool(lyric_role_bold.get("next", True)))
        self.video_display_lyric_played_italic_checkbox = QCheckBox("Italic")
        self.video_display_lyric_played_italic_checkbox.setChecked(bool(lyric_role_italic.get("played", False)))
        self.video_display_lyric_current_italic_checkbox = QCheckBox("Italic")
        self.video_display_lyric_current_italic_checkbox.setChecked(bool(lyric_role_italic.get("current", False)))
        self.video_display_lyric_next_italic_checkbox = QCheckBox("Italic")
        self.video_display_lyric_next_italic_checkbox.setChecked(bool(lyric_role_italic.get("next", False)))
        self._video_display_lyric_role_colors = {
            "played": str(lyric_role_colors.get("played", "#A0A0A0")),
            "current": str(lyric_role_colors.get("current", "#FFD400")),
            "next": str(lyric_role_colors.get("next", "#FFFFFF")),
        }
        self.video_display_lyric_played_color_btn = QPushButton()
        self.video_display_lyric_current_color_btn = QPushButton()
        self.video_display_lyric_next_color_btn = QPushButton()
        self._refresh_color_button(self.video_display_lyric_played_color_btn, self._video_display_lyric_role_colors["played"])
        self._refresh_color_button(self.video_display_lyric_current_color_btn, self._video_display_lyric_role_colors["current"])
        self._refresh_color_button(self.video_display_lyric_next_color_btn, self._video_display_lyric_role_colors["next"])
        self.video_display_lyric_played_color_btn.clicked.connect(lambda: self._pick_lyric_role_color("video_display", "played"))
        self.video_display_lyric_current_color_btn.clicked.connect(lambda: self._pick_lyric_role_color("video_display", "current"))
        self.video_display_lyric_next_color_btn.clicked.connect(lambda: self._pick_lyric_role_color("video_display", "next"))
        self.video_display_lyric_auto_adjust_role_sizes_checkbox.toggled.connect(self._sync_video_display_lyric_role_size_mode)

        font_form.addRow("Font:", self.video_display_lyric_font_family_combo)
        font_form.addRow("Text Size:", self.video_display_lyric_font_size_spin)
        font_form.addRow("Played Lyric Lines:", self.video_display_lyric_previous_line_count_spin)
        font_form.addRow("Next Lyric Lines:", self.video_display_lyric_next_line_count_spin)
        font_form.addRow(self.video_display_lyric_auto_adjust_role_sizes_checkbox)
        font_form.addRow("Played Scale:", self.video_display_lyric_played_scale_percent_spin)
        font_form.addRow("Current Scale:", self.video_display_lyric_current_scale_percent_spin)
        font_form.addRow("Next Scale:", self.video_display_lyric_next_scale_percent_spin)
        font_form.addRow("Played Text Size:", self.video_display_lyric_played_text_size_spin)
        font_form.addRow("Current Text Size:", self.video_display_lyric_current_text_size_spin)
        font_form.addRow("Next Text Size:", self.video_display_lyric_next_text_size_spin)
        font_form.addRow(
            "Played Style:",
            self._build_role_style_row(
                self.video_display_lyric_played_bold_checkbox,
                self.video_display_lyric_played_italic_checkbox,
            ),
        )
        font_form.addRow(
            "Current Style:",
            self._build_role_style_row(
                self.video_display_lyric_current_bold_checkbox,
                self.video_display_lyric_current_italic_checkbox,
            ),
        )
        font_form.addRow(
            "Next Style:",
            self._build_role_style_row(
                self.video_display_lyric_next_bold_checkbox,
                self.video_display_lyric_next_italic_checkbox,
            ),
        )
        font_form.addRow("Played Color:", self.video_display_lyric_played_color_btn)
        font_form.addRow("Current Color:", self.video_display_lyric_current_color_btn)
        font_form.addRow("Next Color:", self.video_display_lyric_next_color_btn)
        layout.addWidget(font_group)
        self._sync_video_display_lyric_role_size_mode()
        layout.addStretch(1)
        return page

    def _sync_video_display_lyric_role_size_mode(self) -> None:
        enabled = not bool(self.video_display_lyric_auto_adjust_role_sizes_checkbox.isChecked())
        for spin in [
            self.video_display_lyric_played_text_size_spin,
            self.video_display_lyric_current_text_size_spin,
            self.video_display_lyric_next_text_size_spin,
        ]:
            spin.setEnabled(enabled)
