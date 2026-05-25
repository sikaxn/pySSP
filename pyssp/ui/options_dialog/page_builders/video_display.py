from __future__ import annotations

from ..shared import *
from ..widgets import *

_MERGED_VIDEO_ROUTE_OPTIONS = [
    (DISPLAY_ROUTE_SOURCE_LABELS["video"], "video"),
    (DISPLAY_ROUTE_SOURCE_LABELS["image"], "image"),
    ("Lyric Display", "lyric_display"),
    ("Stage Display", "stage_display"),
    (DISPLAY_ROUTE_SOURCE_LABELS["metronome_display"], "metronome_display"),
    ("Backdrop", "backdrop"),
    (DISPLAY_ROUTE_SOURCE_LABELS[DISPLAY_ROUTE_SOURCE_BLANK], DISPLAY_ROUTE_SOURCE_BLANK),
    ("White Screen", "white_screen"),
    ("Colour Bars", "colour_bars"),
]


def _merged_manual_route_value(mode_playing: str, mode_idle: str, *, default: str = "blank") -> str:
    playing = normalize_display_focus_override(str(mode_playing or ""), default=DISPLAY_FOCUS_FOLLOW)
    idle = normalize_display_route_source(str(mode_idle or default), default=default)
    valid = {value for _label, value in _MERGED_VIDEO_ROUTE_OPTIONS}
    if playing in valid:
        return playing
    if playing == "none":
        return DISPLAY_ROUTE_SOURCE_BLANK
    if idle in valid:
        return idle
    return default


class VideoDisplayPageMixin:
    def _build_video_display_page(
        self,
        *,
        mode_playing: str,
        mode_idle: str,
        display_focus_default_video: str,
        display_focus_default_audio: str,
        display_focus_default_audio_with_lyric: str,
        display_focus_default_utility_blank: str,
        display_focus_default_utility_noise: str,
        display_focus_default_utility_tone: str,
        display_focus_default_utility_metronome: str,
        display_focus_default_automation: str,
        use_default_backdrop: bool,
        backdrop_path: str,
        show_backdrop_message: bool,
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
        ndi_status_text: str,
        ndi_download_url: str,
        ndi_ready: bool,
        ndi_output_enabled: bool,
        ndi_output_name: str,
        ndi_output_mode_playing: str,
        ndi_output_mode_idle: str,
        ndi_output_resolution_mode: str,
        ndi_output_width: int,
        ndi_output_height: int,
        ndi_output_fps: int,
        ndi_output_audio_enabled: bool,
        ndi_output_audio_tap_mode: str,
        ndi_debug_print_enabled: bool,
        ndi_debug_idle_audio_pacing_enabled: bool,
        ndi_output_group: str,
        ndi_output_discovery_servers: str,
        ndi_output_allowed_adapters: str,
        ndi_output_multicast_enabled: bool,
        ndi_output_multicast_ttl: int,
        ndi_output_multicast_netmask: str,
        ndi_output_multicast_netprefix: str,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self._video_display_mode_playing_value = normalize_display_focus_override(
            mode_playing,
            default=DISPLAY_FOCUS_FOLLOW,
        )
        self._ndi_output_mode_playing_value = normalize_display_focus_override(
            ndi_output_mode_playing,
            default=DISPLAY_FOCUS_FOLLOW,
        )

        routing_group = QGroupBox("Routing Defaults")
        routing_form = QFormLayout(routing_group)
        self.video_display_mode_playing_combo = QComboBox()
        self._add_display_focus_items(self.video_display_mode_playing_combo)
        self._set_combo_data_or_default(self.video_display_mode_playing_combo, display_focus_default_video, "video")
        routing_form.addRow("Video sound buttons:", self.video_display_mode_playing_combo)
        self.display_focus_default_audio_combo = QComboBox()
        self._add_display_focus_items(self.display_focus_default_audio_combo)
        self._set_combo_data_or_default(self.display_focus_default_audio_combo, display_focus_default_audio, "none")
        routing_form.addRow("Audio sound buttons:", self.display_focus_default_audio_combo)
        self.display_focus_default_audio_with_lyric_combo = QComboBox()
        self._add_display_focus_items(self.display_focus_default_audio_with_lyric_combo)
        self._set_combo_data_or_default(
            self.display_focus_default_audio_with_lyric_combo,
            display_focus_default_audio_with_lyric,
            "lyric_display",
        )
        routing_form.addRow("Audio With Lyric:", self.display_focus_default_audio_with_lyric_combo)
        self.display_focus_default_utility_blank_combo = QComboBox()
        self._add_display_focus_items(self.display_focus_default_utility_blank_combo)
        self._set_combo_data_or_default(self.display_focus_default_utility_blank_combo, display_focus_default_utility_blank, "none")
        routing_form.addRow("Utility Blank:", self.display_focus_default_utility_blank_combo)
        self.display_focus_default_utility_noise_combo = QComboBox()
        self._add_display_focus_items(self.display_focus_default_utility_noise_combo)
        self._set_combo_data_or_default(self.display_focus_default_utility_noise_combo, display_focus_default_utility_noise, "colour_bars")
        routing_form.addRow("Utility Noise:", self.display_focus_default_utility_noise_combo)
        self.display_focus_default_utility_tone_combo = QComboBox()
        self._add_display_focus_items(self.display_focus_default_utility_tone_combo)
        self._set_combo_data_or_default(self.display_focus_default_utility_tone_combo, display_focus_default_utility_tone, "colour_bars")
        routing_form.addRow("Utility Tone:", self.display_focus_default_utility_tone_combo)
        self.display_focus_default_utility_metronome_combo = QComboBox()
        self._add_display_focus_items(self.display_focus_default_utility_metronome_combo)
        self._set_combo_data_or_default(
            self.display_focus_default_utility_metronome_combo,
            display_focus_default_utility_metronome,
            "metronome_display",
        )
        routing_form.addRow("Utility Metronome:", self.display_focus_default_utility_metronome_combo)
        self.display_focus_default_automation_combo = QComboBox()
        self._add_display_focus_items(self.display_focus_default_automation_combo)
        self._set_combo_data_or_default(self.display_focus_default_automation_combo, display_focus_default_automation, "none")
        routing_form.addRow("Automation Buttons:", self.display_focus_default_automation_combo)
        self.video_display_follow_sound_button_focus_checkbox = QCheckBox("Follow sound button display focus")
        self.video_display_follow_sound_button_focus_checkbox.setChecked(
            normalize_display_focus_override(mode_playing, default=DISPLAY_FOCUS_FOLLOW) == DISPLAY_FOCUS_FOLLOW
        )
        routing_form.addRow(self.video_display_follow_sound_button_focus_checkbox)
        self.video_display_route_combo = QComboBox()
        for label, value in _MERGED_VIDEO_ROUTE_OPTIONS:
            self.video_display_route_combo.addItem(label, value)
        self._set_combo_data_or_default(
            self.video_display_route_combo,
            _merged_manual_route_value(mode_playing, mode_idle),
            "blank",
        )
        routing_form.addRow("Otherwise:", self.video_display_route_combo)
        layout.addWidget(routing_group)

        backdrop_group = QGroupBox("Backdrop")
        backdrop_form = QFormLayout(backdrop_group)
        self.video_display_use_default_backdrop_checkbox = QCheckBox("Use default backdrop")
        self.video_display_use_default_backdrop_checkbox.setChecked(bool(use_default_backdrop))
        backdrop_form.addRow(self.video_display_use_default_backdrop_checkbox)
        backdrop_path_row = QWidget()
        backdrop_path_layout = QHBoxLayout(backdrop_path_row)
        backdrop_path_layout.setContentsMargins(0, 0, 0, 0)
        backdrop_path_layout.setSpacing(6)
        self.video_display_backdrop_path_edit = QLineEdit(str(backdrop_path or ""))
        self.video_display_backdrop_path_browse_button = QPushButton("Browse...")
        self.video_display_backdrop_path_browse_button.clicked.connect(self._browse_video_display_backdrop_path)
        backdrop_path_layout.addWidget(self.video_display_backdrop_path_edit, 1)
        backdrop_path_layout.addWidget(self.video_display_backdrop_path_browse_button)
        backdrop_form.addRow("Backdrop Image:", backdrop_path_row)
        self.video_display_show_backdrop_message_checkbox = QCheckBox("Show message on backdrop")
        self.video_display_show_backdrop_message_checkbox.setChecked(bool(show_backdrop_message))
        backdrop_form.addRow(self.video_display_show_backdrop_message_checkbox)
        backdrop_note = QLabel("Backdrop message text: No video is playing")
        backdrop_note.setWordWrap(True)
        backdrop_form.addRow(backdrop_note)
        self.video_display_use_default_backdrop_checkbox.toggled.connect(self._sync_video_display_backdrop_controls)
        layout.addWidget(backdrop_group)

        ndi_group = QGroupBox("NDI Output")
        ndi_form = QFormLayout(ndi_group)
        self.ndi_output_status_label = QLabel(str(ndi_status_text or ""))
        self.ndi_output_status_label.setWordWrap(True)
        ndi_form.addRow("Status:", self.ndi_output_status_label)
        self.ndi_output_download_label = QLabel(
            f'<a href="{str(ndi_download_url or "").strip()}">{tr("Download NDI SDK / Runtime")}</a>'
        )
        self.ndi_output_download_label.setOpenExternalLinks(True)
        ndi_form.addRow("Install:", self.ndi_output_download_label)
        self.ndi_output_enabled_checkbox = QCheckBox("Enable NDI output")
        self.ndi_output_enabled_checkbox.setChecked(bool(ndi_output_enabled))
        ndi_form.addRow(self.ndi_output_enabled_checkbox)
        self.ndi_output_name_edit = QLineEdit(str(ndi_output_name or ""))
        ndi_form.addRow("Source Name:", self.ndi_output_name_edit)
        self.ndi_output_route_note_label = QLabel("Source routing mirrors the Video Display route controls.")
        self.ndi_output_route_note_label.setWordWrap(True)
        ndi_form.addRow("Source:", self.ndi_output_route_note_label)
        self.ndi_output_follow_sound_button_focus_checkbox = QCheckBox("Follow sound button display focus")
        self.ndi_output_follow_sound_button_focus_checkbox.setEnabled(False)
        self.ndi_output_follow_sound_button_focus_checkbox.setChecked(
            normalize_display_focus_override(ndi_output_mode_playing, default=DISPLAY_FOCUS_FOLLOW) == DISPLAY_FOCUS_FOLLOW
        )
        ndi_form.addRow(self.ndi_output_follow_sound_button_focus_checkbox)
        self.ndi_output_route_combo = QComboBox()
        for label, value in _MERGED_VIDEO_ROUTE_OPTIONS:
            self.ndi_output_route_combo.addItem(label, value)
        self._set_combo_data_or_default(
            self.ndi_output_route_combo,
            _merged_manual_route_value(ndi_output_mode_playing, ndi_output_mode_idle, default="backdrop"),
            "backdrop",
        )
        ndi_form.addRow("Otherwise:", self.ndi_output_route_combo)
        self.ndi_output_resolution_mode_combo = QComboBox()
        for label, value in [
            ("Source / Native", "source"),
            ("1280 x 720", "720p"),
            ("1920 x 1080", "1080p"),
            ("Custom", "custom"),
        ]:
            self.ndi_output_resolution_mode_combo.addItem(label, value)
        self._set_combo_data_or_default(self.ndi_output_resolution_mode_combo, ndi_output_resolution_mode, "source")
        ndi_form.addRow("Resolution:", self.ndi_output_resolution_mode_combo)
        ndi_size_row = QWidget()
        ndi_size_layout = QHBoxLayout(ndi_size_row)
        ndi_size_layout.setContentsMargins(0, 0, 0, 0)
        ndi_size_layout.setSpacing(6)
        self.ndi_output_width_spin = QSpinBox()
        self.ndi_output_width_spin.setRange(2, 8192)
        self.ndi_output_width_spin.setValue(max(2, int(ndi_output_width)))
        self.ndi_output_height_spin = QSpinBox()
        self.ndi_output_height_spin.setRange(2, 8192)
        self.ndi_output_height_spin.setValue(max(2, int(ndi_output_height)))
        ndi_size_layout.addWidget(self.ndi_output_width_spin, 1)
        ndi_size_layout.addWidget(QLabel("x"))
        ndi_size_layout.addWidget(self.ndi_output_height_spin, 1)
        ndi_form.addRow("Custom Size:", ndi_size_row)
        self.ndi_output_fps_combo = QComboBox()
        fps_value = max(1, int(ndi_output_fps))
        fps_presets = [24, 25, 30, 50, 60]
        for preset in fps_presets:
            self.ndi_output_fps_combo.addItem(f"{preset} fps", preset)
        if fps_value not in fps_presets:
            self.ndi_output_fps_combo.addItem(f"{fps_value} fps", fps_value)
        self._set_combo_data_or_default(self.ndi_output_fps_combo, fps_value, 30)
        ndi_form.addRow("Frame Rate:", self.ndi_output_fps_combo)
        self.ndi_output_audio_enabled_checkbox = QCheckBox("Send audio")
        self.ndi_output_audio_enabled_checkbox.setChecked(bool(ndi_output_audio_enabled))
        ndi_form.addRow(self.ndi_output_audio_enabled_checkbox)
        self.ndi_output_audio_tap_mode_combo = QComboBox()
        self.ndi_output_audio_tap_mode_combo.addItem("Post volume fader", "post_fader")
        self.ndi_output_audio_tap_mode_combo.addItem("Pre volume fader", "pre_fader")
        self._set_combo_data_or_default(self.ndi_output_audio_tap_mode_combo, ndi_output_audio_tap_mode, "post_fader")
        ndi_form.addRow("Audio Tap:", self.ndi_output_audio_tap_mode_combo)
        self.ndi_debug_print_enabled_checkbox = QCheckBox("Enable NDI debug print")
        self.ndi_debug_print_enabled_checkbox.setChecked(bool(ndi_debug_print_enabled))
        ndi_form.addRow(self.ndi_debug_print_enabled_checkbox)
        self.ndi_debug_idle_audio_pacing_enabled_checkbox = QCheckBox("Pace idle NDI audio sends (debug)")
        self.ndi_debug_idle_audio_pacing_enabled_checkbox.setChecked(bool(ndi_debug_idle_audio_pacing_enabled))
        ndi_form.addRow(self.ndi_debug_idle_audio_pacing_enabled_checkbox)
        self.ndi_output_group_edit = QLineEdit(str(ndi_output_group or "Public"))
        self.ndi_output_group_edit.setPlaceholderText("Public")
        ndi_form.addRow("Group(s):", self.ndi_output_group_edit)
        self.ndi_output_discovery_servers_edit = QLineEdit(str(ndi_output_discovery_servers or ""))
        self.ndi_output_discovery_servers_edit.setPlaceholderText("discovery server host or IP, comma separated")
        ndi_form.addRow("Discovery Server(s):", self.ndi_output_discovery_servers_edit)
        self.ndi_output_allowed_adapters_edit = QLineEdit(str(ndi_output_allowed_adapters or ""))
        self.ndi_output_allowed_adapters_edit.setPlaceholderText("adapter IPs, comma separated")
        ndi_form.addRow("Allowed Adapters:", self.ndi_output_allowed_adapters_edit)
        self.ndi_output_multicast_enabled_checkbox = QCheckBox("Enable multicast send")
        self.ndi_output_multicast_enabled_checkbox.setChecked(bool(ndi_output_multicast_enabled))
        ndi_form.addRow(self.ndi_output_multicast_enabled_checkbox)
        self.ndi_output_multicast_ttl_spin = QSpinBox()
        self.ndi_output_multicast_ttl_spin.setRange(1, 255)
        self.ndi_output_multicast_ttl_spin.setValue(max(1, min(255, int(ndi_output_multicast_ttl))))
        ndi_form.addRow("Multicast TTL:", self.ndi_output_multicast_ttl_spin)
        self.ndi_output_multicast_netmask_edit = QLineEdit(str(ndi_output_multicast_netmask or "255.255.0.0"))
        ndi_form.addRow("Multicast Netmask:", self.ndi_output_multicast_netmask_edit)
        self.ndi_output_multicast_netprefix_edit = QLineEdit(str(ndi_output_multicast_netprefix or "239.255.0.0"))
        ndi_form.addRow("Multicast Netprefix:", self.ndi_output_multicast_netprefix_edit)
        self._ndi_capability_ready = bool(ndi_ready)
        self.ndi_output_enabled_checkbox.toggled.connect(self._sync_ndi_controls)
        self.ndi_output_audio_enabled_checkbox.toggled.connect(self._sync_ndi_controls)
        self.ndi_output_multicast_enabled_checkbox.toggled.connect(self._sync_ndi_controls)
        self.ndi_output_resolution_mode_combo.currentIndexChanged.connect(self._sync_ndi_controls)
        self.video_display_follow_sound_button_focus_checkbox.toggled.connect(self._sync_ndi_route_controls)
        self.video_display_route_combo.currentIndexChanged.connect(self._sync_ndi_route_controls)
        self._sync_ndi_route_controls()
        layout.addWidget(ndi_group)

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
        self._sync_video_display_backdrop_controls()
        self._sync_video_display_lyric_role_size_mode()
        self._sync_ndi_controls()
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

    def _sync_video_display_backdrop_controls(self) -> None:
        enabled = not bool(self.video_display_use_default_backdrop_checkbox.isChecked())
        self.video_display_backdrop_path_edit.setEnabled(enabled)
        self.video_display_backdrop_path_browse_button.setEnabled(enabled)

    def _add_display_focus_items(self, combo: QComboBox) -> None:
        for value in [
            "none",
            "video",
            "image",
            "lyric_display",
            "stage_display",
            "backdrop",
            "white_screen",
            "colour_bars",
            "metronome_display",
        ]:
            combo.addItem(DISPLAY_FOCUS_LABELS.get(value, value), value)

    def _sync_ndi_controls(self) -> None:
        ready = bool(getattr(self, "_ndi_capability_ready", False))
        enabled = ready and bool(self.ndi_output_enabled_checkbox.isChecked())
        for widget in [
            self.ndi_output_name_edit,
            self.ndi_output_resolution_mode_combo,
            self.ndi_output_fps_combo,
            self.ndi_output_audio_enabled_checkbox,
            self.ndi_debug_print_enabled_checkbox,
            self.ndi_debug_idle_audio_pacing_enabled_checkbox,
            self.ndi_output_group_edit,
            self.ndi_output_discovery_servers_edit,
            self.ndi_output_allowed_adapters_edit,
            self.ndi_output_multicast_enabled_checkbox,
        ]:
            widget.setEnabled(ready)
        self.ndi_output_follow_sound_button_focus_checkbox.setEnabled(False)
        self.ndi_output_route_combo.setEnabled(False)
        custom_enabled = (
            ready
            and enabled
            and str(self.ndi_output_resolution_mode_combo.currentData() or "source") == "custom"
        )
        self.ndi_output_width_spin.setEnabled(custom_enabled)
        self.ndi_output_height_spin.setEnabled(custom_enabled)
        self.ndi_output_audio_tap_mode_combo.setEnabled(
            ready and enabled and self.ndi_output_audio_enabled_checkbox.isChecked()
        )
        multicast_enabled = ready and enabled and self.ndi_output_multicast_enabled_checkbox.isChecked()
        self.ndi_output_multicast_ttl_spin.setEnabled(multicast_enabled)
        self.ndi_output_multicast_netmask_edit.setEnabled(multicast_enabled)
        self.ndi_output_multicast_netprefix_edit.setEnabled(multicast_enabled)

    def _sync_ndi_route_controls(self) -> None:
        self.ndi_output_follow_sound_button_focus_checkbox.setChecked(
            bool(self.video_display_follow_sound_button_focus_checkbox.isChecked())
        )
        self._set_combo_data_or_default(
            self.ndi_output_route_combo,
            str(self.video_display_route_combo.currentData() or "blank"),
            "backdrop",
        )

    def _browse_video_display_backdrop_path(self) -> None:
        start_dir = str(self.video_display_backdrop_path_edit.text() or "").strip()
        selected, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Select Backdrop Image",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*.*)",
        )
        if selected:
            self.video_display_backdrop_path_edit.setText(selected)
