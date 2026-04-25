from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class UiBuildMixin:
    def _build_ui(self) -> None:
        self._build_menu_bar()

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        self.drag_mode_banner.setVisible(False)
        self.drag_mode_banner.setWordWrap(True)
        self.drag_mode_banner.setStyleSheet(
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.drag_mode_banner)
        self.timecode_multiplay_banner.setVisible(False)
        self.timecode_multiplay_banner.setWordWrap(True)
        self.timecode_multiplay_banner.setStyleSheet(
            "QLabel{background:#FDE7E9; color:#7A0010; border:1px solid #B00020; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.timecode_multiplay_banner)
        self.web_remote_warning_banner.setVisible(False)
        self.web_remote_warning_banner.setWordWrap(True)
        self.web_remote_warning_banner.setStyleSheet(
            "QLabel{background:#FDE7E9; color:#7A0010; border:1px solid #B00020; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.web_remote_warning_banner)
        self.midi_connection_warning_banner.setVisible(False)
        self.midi_connection_warning_banner.setWordWrap(True)
        self.midi_connection_warning_banner.setStyleSheet(
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.midi_connection_warning_banner)
        self.vocal_removed_warning_banner.setVisible(False)
        self.vocal_removed_warning_banner.setWordWrap(True)
        self.vocal_removed_warning_banner.setStyleSheet(
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.vocal_removed_warning_banner)
        self.playback_warning_banner.setVisible(False)
        self.playback_warning_banner.setWordWrap(True)
        self.playback_warning_banner.setStyleSheet(
            "QLabel{background:#EFE3FA; color:#3F205E; border:1px solid #7B3FB3; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.playback_warning_banner)
        self.save_notice_banner.setVisible(False)
        self.save_notice_banner.setWordWrap(True)
        self.save_notice_banner.setStyleSheet(
            "QLabel{background:#E4F7E7; color:#165A20; border:1px solid #2E9B47; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.save_notice_banner)
        self.info_notice_banner.setVisible(False)
        self.info_notice_banner.setWordWrap(True)
        self.info_notice_banner.setStyleSheet(
            "QLabel{background:#FFF0A6; color:#3A2A00; border:1px solid #CFAE2A; "
            "padding:6px; font-weight:bold;}"
        )
        root_layout.addWidget(self.info_notice_banner)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        root_layout.addLayout(body_layout, 1)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        body_layout.addWidget(left_panel, 1)
        body_layout.addWidget(right_panel, 5)

        self.button_legend_label = QWidget()
        self.button_legend_label.setContentsMargins(0, 0, 0, 0)
        self.button_legend_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._button_legend_layout = QHBoxLayout(self.button_legend_label)
        self._button_legend_layout.setContentsMargins(2, 0, 2, 0)
        self._button_legend_layout.setSpacing(12)
        self._refresh_button_legend_label()
        self.button_legend_label.setVisible(bool(self.show_colour_legend))
        root_layout.addWidget(self.button_legend_label)

        self._build_timecode_dock()

    def _apply_language(self) -> None:
        set_current_language(self.ui_language)
        apply_application_font(QApplication.instance(), self.ui_language)
        localize_widget_tree(self, self.ui_language)
        if self._search_window is not None:
            localize_widget_tree(self._search_window, self.ui_language)
        if self._dsp_window is not None:
            localize_widget_tree(self._dsp_window, self.ui_language)
        for window in self._tool_windows.values():
            localize_widget_tree(window, self.ui_language)
        if self._about_window is not None:
            localize_widget_tree(self._about_window, self.ui_language)
        if self._getting_started_window is not None:
            self._getting_started_window.set_language(self.ui_language)
        if self._tips_window is not None:
            self._tips_window.set_language(self.ui_language)
        if self._stage_display_window is not None:
            self._stage_display_window.retranslate_ui()
        self._refresh_button_legend_label()

    def _refresh_button_legend_label(self) -> None:
        while self._button_legend_layout.count():
            item = self._button_legend_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        title = QLabel(tr("Button Legend:"))
        title.setStyleSheet("color:#666666; font-size:9pt; font-weight:600;")
        self._button_legend_layout.addWidget(title)

        items = [
            (self.state_colors["playing"], tr("Now Playing")),
            (self.state_colors["played"], tr("Played")),
            (self.state_colors["assigned"], tr("Unplayed")),
            (self.state_colors["cue_indicator"], tr("Cue Stripe")),
            (self.state_colors["volume_indicator"], tr("Volume Stripe")),
            (self.state_colors["vocal_removed_indicator"], tr("Vocal Removed Stripe")),
            (self.state_colors["lyric_indicator"], tr("Lyric Stripe")),
            (TIMECODE_SLOT_INDICATOR_COLOR, tr("Timecode Stripe")),
            (self.state_colors["midi_indicator"], tr("MIDI Top Stripe")),
        ]
        for color, label_text in items:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)

            dot = QLabel("")
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(
                "QLabel{"
                f"background:{str(color or '#000000')};"
                "border:1px solid #666666;"
                "border-radius:5px;"
                "}"
            )
            text = QLabel(label_text)
            text.setStyleSheet("color:#666666; font-size:9pt;")

            item_layout.addWidget(dot)
            item_layout.addWidget(text)
            self._button_legend_layout.addWidget(item_widget)

        self._button_legend_layout.addStretch(1)

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        new_set_action = QAction("New Set", self)
        new_set_action.triggered.connect(self._new_set)
        file_menu.addAction(new_set_action)
        self._menu_actions["new_set"] = new_set_action

        open_set_action = QAction("Open Set", self)
        open_set_action.triggered.connect(self._open_set_dialog)
        file_menu.addAction(open_set_action)
        self._menu_actions["open_set"] = open_set_action

        save_set_action = QAction("Save Set", self)
        save_set_action.triggered.connect(self._save_set)
        file_menu.addAction(save_set_action)
        self._menu_actions["save_set"] = save_set_action

        save_set_at_action = QAction("Save Set At", self)
        save_set_at_action.triggered.connect(self._save_set_at)
        file_menu.addAction(save_set_at_action)
        self._menu_actions["save_set_as"] = save_set_at_action

        file_menu.addSeparator()

        pack_audio_library_action = QAction(tr("Pack Audio Library"), self)
        pack_audio_library_action.triggered.connect(self._pack_audio_library)
        file_menu.addAction(pack_audio_library_action)

        unpack_audio_library_action = QAction(tr("Unpack Audio Library"), self)
        unpack_audio_library_action.triggered.connect(self._unpack_audio_library)
        file_menu.addAction(unpack_audio_library_action)

        file_menu.addSeparator()

        backup_settings_action = QAction("Backup pySSP Settings", self)
        backup_settings_action.triggered.connect(self._backup_pyssp_settings)
        file_menu.addAction(backup_settings_action)

        restore_settings_action = QAction("Restore pySSP Settings", self)
        restore_settings_action.triggered.connect(self._restore_pyssp_settings)
        file_menu.addAction(restore_settings_action)

        file_menu.addSeparator()

        backup_keyboard_hotkeys_action = QAction("Backup Keyboard Hotkey Bindings", self)
        backup_keyboard_hotkeys_action.triggered.connect(self._backup_keyboard_hotkey_bindings)
        file_menu.addAction(backup_keyboard_hotkeys_action)

        restore_keyboard_hotkeys_action = QAction("Restore Keyboard Hotkey Bindings", self)
        restore_keyboard_hotkeys_action.triggered.connect(self._restore_keyboard_hotkey_bindings)
        file_menu.addAction(restore_keyboard_hotkeys_action)

        file_menu.addSeparator()

        backup_midi_bindings_action = QAction("Backup MIDI Bindings", self)
        backup_midi_bindings_action.triggered.connect(self._backup_midi_bindings)
        file_menu.addAction(backup_midi_bindings_action)

        restore_midi_bindings_action = QAction("Restore MIDI Bindings", self)
        restore_midi_bindings_action.triggered.connect(self._restore_midi_bindings)
        file_menu.addAction(restore_midi_bindings_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        setup_menu = self.menuBar().addMenu("Setup")
        options_action = QAction("Options", self)
        options_action.triggered.connect(self._open_options_dialog)
        preferences_action: Optional[QAction] = None
        if sys.platform == "darwin":
            preferences_action = QAction("Preferences", self)
            preferences_action.triggered.connect(self._open_options_dialog)
            setup_menu.addAction(preferences_action)
        setup_menu.addAction(options_action)
        configure_preferences_menu_actions(
            options_action,
            preferences_action,
            platform_name=sys.platform,
        )
        self._menu_actions["options"] = options_action
        open_web_remote_action = QAction("Open Web Remote", self)
        open_web_remote_action.triggered.connect(self._open_web_remote)
        setup_menu.addAction(open_web_remote_action)

        display_menu = self.menuBar().addMenu("Display")
        show_display_action = QAction("Show Stage Display", self)
        show_display_action.triggered.connect(self._show_stage_display)
        display_menu.addAction(show_display_action)
        send_alert_action = QAction("Send Alert", self)
        send_alert_action.triggered.connect(self._open_stage_alert_panel)
        display_menu.addAction(send_alert_action)
        lyric_display_action = QAction("Open Lyric Display", self)
        lyric_display_action.triggered.connect(self._open_lyric_display)
        display_menu.addAction(lyric_display_action)
        web_lyric_display_menu = display_menu.addMenu("Web Lyric Display")
        web_lyric_caption_action = QAction("Caption", self)
        web_lyric_caption_action.triggered.connect(lambda: self._open_web_lyric_display("caption"))
        web_lyric_display_menu.addAction(web_lyric_caption_action)
        web_lyric_overhead_action = QAction("Overhead", self)
        web_lyric_overhead_action.triggered.connect(lambda: self._open_web_lyric_display("overhead"))
        web_lyric_display_menu.addAction(web_lyric_overhead_action)
        web_lyric_banner_action = QAction("Banner", self)
        web_lyric_banner_action.triggered.connect(lambda: self._open_web_lyric_display("banner"))
        web_lyric_display_menu.addAction(web_lyric_banner_action)
        web_lyric_vmix_action = QAction("vMix Overlay", self)
        web_lyric_vmix_action.triggered.connect(lambda: self._open_web_lyric_display("vmixoverlay"))
        web_lyric_display_menu.addAction(web_lyric_vmix_action)
        self._lyric_blank_toggle_action = QAction("Blank Lyric", self)
        self._lyric_blank_toggle_action.setCheckable(True)
        self._lyric_blank_toggle_action.triggered.connect(lambda checked=False: self._set_lyric_force_blank(bool(checked)))
        display_menu.addAction(self._lyric_blank_toggle_action)
        stage_display_setting_action = QAction("Stage Display Setting", self)
        stage_display_setting_action.triggered.connect(lambda: self._open_options_dialog(initial_page="Stage Display"))
        display_menu.addAction(stage_display_setting_action)
        self._sync_lyric_display_controls()

        search_action = QAction("Search", self)
        search_action.triggered.connect(self._open_find_dialog)
        self.addAction(search_action)
        self._menu_actions["search"] = search_action

        timecode_menu = self.menuBar().addMenu("Timecode")
        timecode_settings_action = QAction("Timecode Settings", self)
        timecode_settings_action.triggered.connect(self._open_timecode_settings)
        timecode_menu.addAction(timecode_settings_action)
        self._menu_actions["timecode_settings"] = timecode_settings_action
        timecode_panel_action = QAction("Timecode Panel", self)
        timecode_panel_action.setCheckable(True)
        timecode_panel_action.setChecked(bool(self.show_timecode_panel))
        timecode_panel_action.triggered.connect(self._toggle_timecode_panel)
        timecode_menu.addAction(timecode_panel_action)
        self._menu_actions["timecode_panel"] = timecode_panel_action

        tools_menu = self.menuBar().addMenu("Tools")
        show_colour_legend_action = QAction("Show Colour Legend", self)
        show_colour_legend_action.setCheckable(True)
        show_colour_legend_action.setChecked(bool(self.show_colour_legend))
        show_colour_legend_action.triggered.connect(self._toggle_colour_legend)
        tools_menu.addAction(show_colour_legend_action)
        self._menu_actions["show_colour_legend"] = show_colour_legend_action

        tools_menu.addSeparator()

        duplicate_check_action = QAction("Duplicate Check", self)
        duplicate_check_action.triggered.connect(self._run_duplicate_check)
        tools_menu.addAction(duplicate_check_action)

        verify_sound_buttons_action = QAction("Verify Sound Buttons", self)
        verify_sound_buttons_action.triggered.connect(self._run_verify_sound_buttons)
        tools_menu.addAction(verify_sound_buttons_action)

        scan_sound_button_lyrics_action = QAction("Scan Sound Buttons Lyrics", self)
        scan_sound_button_lyrics_action.triggered.connect(self._scan_sound_button_lyrics)
        tools_menu.addAction(scan_sound_button_lyrics_action)

        lyric_navigator_action = QAction("Lyric Navigator", self)
        lyric_navigator_action.triggered.connect(self._open_lyric_navigator)
        tools_menu.addAction(lyric_navigator_action)

        remove_linked_lyrics_action = QAction("Remove All Linked Lyric File", self)
        remove_linked_lyrics_action.triggered.connect(self._remove_all_linked_lyric_files)
        tools_menu.addAction(remove_linked_lyrics_action)

        bulk_generate_vocal_removed_action = QAction("Bulk Generate Vocal Removed Track", self)
        bulk_generate_vocal_removed_action.triggered.connect(self._bulk_generate_vocal_removed_tracks)
        tools_menu.addAction(bulk_generate_vocal_removed_action)

        link_unlinked_vocal_removed_action = QAction("Link Unlinked Vocal Removed Track", self)
        link_unlinked_vocal_removed_action.triggered.connect(self._link_unlinked_vocal_removed_tracks)
        tools_menu.addAction(link_unlinked_vocal_removed_action)

        remove_linked_vocal_removed_action = QAction("Unlink All Vocal Removed Track", self)
        remove_linked_vocal_removed_action.triggered.connect(self._remove_all_linked_vocal_removed_files)
        tools_menu.addAction(remove_linked_vocal_removed_action)

        disable_playlist_all_pages_action = QAction("Disable Play List on All Pages", self)
        disable_playlist_all_pages_action.triggered.connect(self._disable_playlist_on_all_pages)
        tools_menu.addAction(disable_playlist_all_pages_action)
        reset_all_pages_action = QAction("Reset All Pages", self)
        reset_all_pages_action.triggered.connect(self._reset_all_pages_state)
        tools_menu.addAction(reset_all_pages_action)

        tools_menu.addSeparator()

        clear_waveform_cache_action = QAction("Clear Waveform Cache", self)
        clear_waveform_cache_action.triggered.connect(self._clear_waveform_cache_now)
        tools_menu.addAction(clear_waveform_cache_action)

        open_settings_folder_action = QAction("Open Settings Folder", self)
        open_settings_folder_action.triggered.connect(self._open_settings_folder)
        tools_menu.addAction(open_settings_folder_action)

        set_file_path_action = QAction("Display .set File and Path", self)
        set_file_path_action.triggered.connect(self._show_set_file_and_path)
        tools_menu.addAction(set_file_path_action)

        tools_menu.addSeparator()

        export_excel_action = QAction("Export Page and Sound Buttons to Excel", self)
        export_excel_action.triggered.connect(self._export_page_and_sound_buttons_to_excel)
        tools_menu.addAction(export_excel_action)

        list_sound_buttons_action = QAction("List Sound Buttons", self)
        list_sound_buttons_action.triggered.connect(self._list_sound_buttons)
        tools_menu.addAction(list_sound_buttons_action)

        list_sound_button_hotkey_action = QAction("List Sound Button Hot Key", self)
        list_sound_button_hotkey_action.triggered.connect(self._list_sound_button_hotkeys)
        tools_menu.addAction(list_sound_button_hotkey_action)

        list_sound_device_midi_mapping_action = QAction("List Sound Device MIDI Mapping", self)
        list_sound_device_midi_mapping_action.triggered.connect(self._list_sound_device_midi_mappings)
        tools_menu.addAction(list_sound_device_midi_mapping_action)

        launchpad_cheatsheet_action = QAction("Launchpad Cheat Sheet", self)
        launchpad_cheatsheet_action.triggered.connect(self._show_launchpad_cheatsheet)
        tools_menu.addAction(launchpad_cheatsheet_action)

        log_menu = self.menuBar().addMenu("Logs")
        view_log_action = QAction("View Log", self)
        view_log_action.triggered.connect(self._view_log_file)
        log_menu.addAction(view_log_action)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._open_about_window)
        application_about_action: Optional[QAction] = None
        if sys.platform == "darwin":
            application_about_action = QAction("About", self)
            application_about_action.triggered.connect(self._open_about_window)
            help_menu.addAction(application_about_action)
        help_menu.addAction(about_action)
        configure_about_menu_actions(
            about_action,
            application_about_action,
            platform_name=sys.platform,
        )
        system_info_action = QAction("System Information", self)
        system_info_action.triggered.connect(self._open_system_information_window)
        help_menu.addAction(system_info_action)
        audio_engine_insight_action = QAction("Audio Engine Insight", self)
        audio_engine_insight_action.triggered.connect(self._open_audio_engine_insight_window)
        help_menu.addAction(audio_engine_insight_action)

        help_action = QAction("Help", self)
        help_action.triggered.connect(self._open_help_window)
        help_menu.addAction(help_action)

        getting_started_action = QAction("Getting Started", self)
        getting_started_action.triggered.connect(lambda _=False: self._open_getting_started_window(startup=False))
        help_menu.addAction(getting_started_action)

        latest_version_action = QAction("Get the Latest Version", self)
        latest_version_action.triggered.connect(self._open_latest_version_page)
        help_menu.addAction(latest_version_action)
        website_action = QAction("Website", self)
        website_action.triggered.connect(self._open_website_page)
        help_menu.addAction(website_action)

        tips_action = QAction("Tips", self)
        tips_action.triggered.connect(lambda _=False: self._open_tips_window(startup=False))
        help_menu.addAction(tips_action)

        register_action = QAction("Register", self)
        register_action.triggered.connect(self._show_register_message)
        help_menu.addAction(register_action)

        if not getattr(sys, "frozen", False):
            debug_crash_action = QAction("Crash for Debug", self)
            debug_crash_action.triggered.connect(self._trigger_debug_crash)
            help_menu.addAction(debug_crash_action)
        if sys.platform != "darwin":
            self.lock_screen_button = self._create_lock_screen_button(self.menuBar(), auto_raise=True)
            self.menuBar().setCornerWidget(self.lock_screen_button, Qt.TopRightCorner)
        self._apply_hotkeys()

    def _create_lock_screen_button(self, parent: QWidget, *, auto_raise: bool) -> QToolButton:
        button = QToolButton(parent)
        button.setCheckable(True)
        button.setAutoRaise(bool(auto_raise))
        button.setIcon(QIcon(build_lock_icon()))
        button.setIconSize(QSize(18, 18))
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.clicked.connect(self._on_lock_screen_button_clicked)
        return button

    def _on_lock_screen_button_clicked(self) -> None:
        if sys.platform == "darwin":
            QTimer.singleShot(0, self._toggle_lock_screen)
            return
        self._toggle_lock_screen()

    def _show_register_message(self) -> None:
        QMessageBox.information(
            self,
            "Register",
            "pySSP is free software. No registration is required.",
        )

    def _load_asset_text_file(self, *parts: str) -> str:
        file_path = self._asset_file_path(*parts)
        if not os.path.exists(file_path):
            return f"{os.path.join(*parts)} not found at:\n{file_path}"
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                return fh.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin1", errors="replace") as fh:
                return fh.read()
        except Exception as exc:
            return f"Could not read {os.path.join(*parts)}:\n{exc}"

    def _open_about_window(self) -> None:
        if self._about_window is None:
            self._about_window = AboutWindowDialog(
                title="About",
                logo_path=self._asset_file_path("logo2.png"),
                version_text=self.app_version_text,
                website_url=self._website_url(),
                parent=self,
            )
            self._about_window.destroyed.connect(lambda _=None: self._clear_about_window_ref())

        about_text = self._load_asset_text_file("about", "about.md").replace("{{VERSION}}", self.app_version_text)
        credits_text = self._load_asset_text_file("about", "credits.md")
        license_text = self._load_asset_text_file("about", "license.md")
        self._about_window.set_version_and_website(
            self.app_version_text,
            self._website_url(),
            self.app_build_text,
        )
        self._about_window.set_content(about_text=about_text, credits_text=credits_text, license_text=license_text)
        self._about_window.show()
        self._about_window.raise_()
        self._about_window.activateWindow()

    def _open_system_information_window(self) -> None:
        if self._is_playback_in_progress():
            answer = QMessageBox.question(
                self,
                tr("System Information"),
                tr("Opening System Information during playback may interrupt playback. Do you want to continue?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        if self._system_info_window is None:
            self._system_info_window = SystemInformationDialog(
                app_version_text=self.app_version_text,
                app_build_text=self.app_build_text,
                parent=self,
            )
            self._system_info_window.destroyed.connect(lambda _=None: self._clear_system_info_window_ref())
        self._system_info_window.set_app_version_text(self.app_version_text)
        self._system_info_window.set_app_build_text(self.app_build_text)
        self._system_info_window.refresh()
        self._system_info_window.show()
        self._system_info_window.raise_()
        self._system_info_window.activateWindow()

    def _open_audio_engine_insight_window(self) -> None:
        if self._audio_engine_insight_window is None:
            self._audio_engine_insight_window = AudioEngineInsightDialog(
                snapshot_provider=self._audio_engine_insight_snapshot_data,
                parent=self,
            )
            self._audio_engine_insight_window.destroyed.connect(
                lambda _=None: self._clear_audio_engine_insight_window_ref()
            )
        self._audio_engine_insight_window.refresh()
        self._audio_engine_insight_window.show()
        self._audio_engine_insight_window.raise_()
        self._audio_engine_insight_window.activateWindow()

    def _audio_engine_insight_snapshot_data(self) -> dict:
        ref_player, ref_key = self._timecode_reference_context()
        engine_left, engine_right = get_engine_output_meter_levels()
        summary = [
            ("audio_output_device", self.audio_output_device or "default"),
            ("timecode_audio_output_device", self.timecode_audio_output_device or "none"),
            ("timecode_mode", self.timecode_mode),
            ("multi_play_enabled", self._is_multi_play_enabled()),
            ("active_playing_keys", len(self._active_playing_keys)),
            ("current_playing", self.current_playing),
            ("fade_jobs", len(self._fade_jobs)),
            ("global_volume", self.volume_slider.value() if self.volume_slider is not None else 100),
            ("dsp_config", self._describe_dsp_config(self._dsp_config)),
            ("engine_output_meter", f"({engine_left:.4f}, {engine_right:.4f})"),
            ("timecode_reference", "none" if ref_player is None else f"{self._audio_player_label(ref_player)} slot={ref_key}"),
        ]
        player_records: List[dict] = []
        runtime_players = self._insight_runtime_players()
        for index, player in enumerate(runtime_players):
            player_records.append(self._audio_player_insight_record(player, index))
        return {"summary": summary, "players": player_records}

    def _insight_runtime_players(self) -> List[ExternalMediaPlayer]:
        players: List[ExternalMediaPlayer] = [self.player, self.player_b, *self._multi_players]
        for primary in [self.player, self.player_b, *self._multi_players]:
            shadow = self._shadow_player_for(primary)
            if shadow is not None:
                players.append(shadow)
        return players

    def _audio_player_label(self, player: object) -> str:
        if player is self.player:
            return "primary"
        if player is self.player_b:
            return "secondary"
        if player in self._multi_players:
            try:
                return f"multi[{self._multi_players.index(player)}]"
            except Exception:
                return "multi"
        for primary in [self.player, self.player_b, *self._multi_players]:
            shadow = self._shadow_player_for(primary)
            if shadow is player:
                return f"{self._audio_player_label(primary)}_shadow"
        return "player"

    def _describe_dsp_config(self, config: Optional[DSPConfig]) -> str:
        cfg = normalize_config(config)
        return (
            f"eq_enabled={cfg.eq_enabled}, "
            f"eq_bands={cfg.eq_bands}, "
            f"reverb_sec={cfg.reverb_sec}, "
            f"tempo_pct={cfg.tempo_pct}, "
            f"pitch_pct={cfg.pitch_pct}, "
            f"plugin_paths={cfg.plugin_paths}"
        )

    def _audio_player_insight_record(self, player: object, index: int) -> dict:
        label = self._audio_player_label(player)
        pid = id(player)
        slot_key = self._player_slot_key_map.get(pid)
        if slot_key is None:
            for primary in [self.player, self.player_b, *self._multi_players]:
                shadow = self._shadow_player_for(primary)
                if shadow is player:
                    slot_key = self._player_slot_key_map.get(id(primary))
                    break
        slot = self._slot_for_key(slot_key) if slot_key is not None else None
        runtime_id = self._playback_runtime.runtime_id_for(player)
        meter = getattr(player, "meterLevels", lambda: (0.0, 0.0))()
        try:
            state_name = self._api_player_state_name(player)  # type: ignore[arg-type]
        except Exception:
            state_name = "unknown"
        try:
            engine_pos = int(getattr(player, "enginePositionMs", lambda: 0)())
        except Exception:
            engine_pos = 0
        try:
            position_ms = int(getattr(player, "position", lambda: 0)())
        except Exception:
            position_ms = 0
        try:
            duration_ms = int(getattr(player, "duration", lambda: 0)())
        except Exception:
            duration_ms = 0
        try:
            volume = int(getattr(player, "volume", lambda: 0)())
        except Exception:
            volume = 0
        title = "" if slot is None else self._build_now_playing_text(slot)
        details = [
            ("index", index),
            ("label", label),
            ("object_id", pid),
            ("runtime_id", runtime_id if runtime_id is not None else "inactive"),
            ("state", state_name),
            ("slot_key", slot_key),
            ("title", title),
            ("file_path", "" if slot is None else slot.file_path),
            ("volume", volume),
            ("slot_volume_pct", self._slot_pct_for_player(player)),
            ("duration_ms", duration_ms),
            ("position_ms", position_ms),
            ("engine_position_ms", engine_pos),
            ("remaining_ms", max(0, duration_ms - position_ms)),
            ("streaming_mode", bool(getattr(player, "_streaming_mode", False))),
            ("media_path", getattr(player, "_media_path", "")),
            ("cue_end_override_ms", self._player_end_override_ms.get(pid)),
            ("ignore_cue_end", pid in self._player_ignore_cue_end),
            ("started_at_monotonic", self._player_started_map.get(pid)),
            ("meter_levels", meter),
            ("dsp_config", self._describe_dsp_config(getattr(player, "_dsp_config", None))),
        ]
        return {
            "index": index,
            "label": label,
            "runtime_id": runtime_id if runtime_id is not None else "inactive",
            "state": state_name,
            "title": title,
            "details": details,
        }

    def _open_help_window(self) -> None:
        help_index = self._help_index_path()
        if not os.path.exists(help_index):
            QMessageBox.warning(
                self,
                "Help Not Found",
                "Built help index not found.\n\n"
                "Build docs first by running:\n"
                "docs\\build.bat\n\n"
                f"Expected path:\n{help_index}",
            )
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(help_index)):
            QMessageBox.warning(
                self,
                "Help Open Failed",
                f"Could not open help index with the default browser.\n\nPath:\n{help_index}",
            )

    def _open_getting_started_docs_page(self) -> None:
        target = self._help_doc_path("startup.html")
        if os.path.exists(target):
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(target)):
                QMessageBox.warning(
                    self,
                    "Help Open Failed",
                    f"Could not open help page with the default browser.\n\nPath:\n{target}",
                )
            return
        self._open_help_window()

    def _open_latest_version_page(self) -> None:
        releases_url = QUrl("https://github.com/sikaxn/pySSP/releases")
        if not QDesktopServices.openUrl(releases_url):
            QMessageBox.warning(
                self,
                "Help Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{releases_url.toString()}",
            )

    def _trigger_debug_crash(self) -> None:
        nonsense = None
        nonsense.setWindowTitle("This should crash")

    def _website_url(self) -> str:
        return "https://pyssp.studenttechsupport.com/"

    def _open_website_page(self) -> None:
        website_url = QUrl(self._website_url())
        if not QDesktopServices.openUrl(website_url):
            QMessageBox.warning(
                self,
                "Help Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{website_url.toString()}",
            )

    def _clear_getting_started_window_ref(self) -> None:
        self._getting_started_window = None

    def _open_audio_device_options(self) -> None:
        self._open_options_dialog(initial_page="Audio Device & Timecode")

    def _getting_started_image_path(self, *parts: str) -> str:
        docs_source = os.path.join(self._project_root_path(), "docs", "source", "images", *parts)
        if os.path.exists(docs_source):
            return docs_source
        docs_built = os.path.join(os.path.dirname(self._help_index_path()), "_images", *parts)
        if os.path.exists(docs_built):
            return docs_built
        basename = os.path.basename(os.path.join(*parts))
        docs_built_flat = os.path.join(os.path.dirname(self._help_index_path()), "_images", basename)
        if os.path.exists(docs_built_flat):
            return docs_built_flat
        return docs_source

    def _open_getting_started_window(self, startup: bool = False) -> None:
        if self._getting_started_window is None:
            self._getting_started_window = GettingStartedDialog(
                language=self.ui_language,
                version_text=self.app_version_text,
                build_text=self.app_build_text,
                beta_build=is_beta_version(self.app_version_text),
                splash_image_path=self._asset_file_path("logo2.png"),
                add_page_image_path=self._getting_started_image_path("getting_started", "add_page.png"),
                drag_file_image_path=self._getting_started_image_path("getting_started", "drag_file_to_sound_button.png"),
                open_audio_device_options=self._open_audio_device_options,
                open_latest_version_page=self._open_latest_version_page,
                open_docs_page=self._open_getting_started_docs_page,
                open_options_page=self._open_options_dialog,
                open_about_window=self._open_about_window,
                parent=self,
            )
            self._getting_started_window.destroyed.connect(lambda _=None: self._clear_getting_started_window_ref())
        if not startup:
            self._getting_started_window.reset_to_first_page()
        self._getting_started_window.show()
        if startup:
            self._getting_started_window.raise_()
            self._getting_started_window.activateWindow()
        else:
            self._getting_started_window.raise_()
            self._getting_started_window.activateWindow()

    def _open_web_lyric_display(self, view_name: str) -> None:
        target = str(view_name or "").strip().lower()
        if target not in {"caption", "overhead", "banner", "vmixoverlay"}:
            return
        if not self._require_web_remote_enabled(tr("Web Lyric Display")):
            return
        base = self._web_remote_open_url().rstrip("/")
        url = QUrl(f"{base}/lyric/{target}/?ws_port={int(self.web_remote_ws_port)}&ws_path=/ws")
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(
                self,
                "Web Lyric Display Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{url.toString()}",
            )

    def _open_web_remote(self) -> None:
        if not self._require_web_remote_enabled(tr("Open Web Remote")):
            return
        url = QUrl(self._web_remote_open_url())
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(
                self,
                "Web Remote Open Failed",
                f"Could not open URL with the default browser.\n\nURL:\n{url.toString()}",
            )

    def _require_web_remote_enabled(self, feature_name: str) -> bool:
        if self.web_remote_enabled:
            return True
        template = tr("Web Remote is not enabled. Please enable Web Remote for {feature} to work.")
        feature = str(feature_name or "").strip() or tr("Web Remote")
        self._show_playback_warning_banner(template.format(feature=feature))
        return False

    def _open_tips_window(self, startup: bool = False) -> None:
        was_visible = self._tips_window is not None and self._tips_window.isVisible()
        if self._tips_window is None:
            self._tips_window = TipsWindow(
                language=self.ui_language,
                open_on_startup=self.tips_open_on_startup,
                parent=self,
            )
            self._tips_window.openOnStartupChanged.connect(self._on_tips_open_on_startup_changed)
            self._tips_window.destroyed.connect(lambda _=None: self._clear_tips_window_ref())
        else:
            self._tips_window.set_language(self.ui_language)
            self._tips_window.set_open_on_startup(self.tips_open_on_startup)
        if not was_visible:
            self._tips_window.pick_random_tip()
        self._tips_window.show()
        if startup:
            self._position_tips_window_for_startup()
        self._tips_window.raise_()
        self._tips_window.activateWindow()

    def _on_tips_open_on_startup_changed(self, enabled: bool) -> None:
        self.tips_open_on_startup = bool(enabled)
        if not self._suspend_settings_save:
            self._save_settings()

    def _clear_about_window_ref(self) -> None:
        self._about_window = None

    def _clear_audio_engine_insight_window_ref(self) -> None:
        self._audio_engine_insight_window = None

    def _clear_system_info_window_ref(self) -> None:
        self._system_info_window = None

    def _clear_tips_window_ref(self) -> None:
        self._tips_window = None

    def _position_tips_window_for_startup(self) -> None:
        if self._tips_window is None:
            return
        tips = self._tips_window
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        main_rect = self.frameGeometry()
        width = tips.width()
        height = tips.height()
        margin = 16

        x = main_rect.right() + margin
        y = main_rect.top() + margin
        if (x + width) > (avail.x() + avail.width() - margin):
            x = main_rect.left() - width - margin
        if x < (avail.x() + margin):
            x = avail.x() + avail.width() - width - margin

        max_x = avail.x() + avail.width() - width - margin
        max_y = avail.y() + avail.height() - height - margin
        x = max(avail.x() + margin, min(x, max_x))
        y = max(avail.y() + margin, min(y, max_y))

        candidate = QRect(x, y, width, height)
        if candidate.intersects(main_rect):
            y2 = main_rect.bottom() + margin
            y = max(avail.y() + margin, min(y2, max_y))
        tips.move(x, y)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        group_grid = QGridLayout()
        group_grid.setContentsMargins(0, 0, 0, 0)
        group_grid.setHorizontalSpacing(2)
        group_grid.setVerticalSpacing(2)

        for i, group in enumerate(GROUPS):
            button = GroupButton(group, self)
            button.setMinimumSize(40, 40)
            button.setStyleSheet("font-size: 18pt; font-weight: bold;")
            button.clicked.connect(lambda _=False, g=group: self._select_group(g))
            row = 0 if i < 5 else 1
            col = i % 5
            group_grid.addWidget(button, row, col)
            self.group_buttons[group] = button

        layout.addLayout(group_grid)

        self.page_list.setAlternatingRowColors(True)
        self.page_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.page_list.setSpacing(0)
        self.page_list.currentRowChanged.connect(self._select_page)
        self.page_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.page_list.customContextMenuRequested.connect(self._show_page_menu)
        self.page_list.setAcceptDrops(True)
        self.page_list.viewport().setAcceptDrops(True)
        self.page_list.viewport().installEventFilter(self)
        layout.addWidget(self.page_list, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top = self._build_top_controls()
        layout.addWidget(top, 1)

        grid_container = QFrame()
        grid_container.setFrameShape(QFrame.StyledPanel)
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(1)

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                idx = row * GRID_COLS + col
                button = SoundButton(idx, self)
                button.clicked.connect(lambda _=False, slot=idx: self._on_sound_button_clicked(slot))
                self.sound_buttons.append(button)
                grid_layout.addWidget(button, row, col)
        for row in range(GRID_ROWS):
            grid_layout.setRowStretch(row, 1)
        for col in range(GRID_COLS):
            grid_layout.setColumnStretch(col, 1)

        layout.addWidget(grid_container, 3)
        return panel

    def _build_top_controls(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._main_control_grid_layout = QGridLayout()
        self._main_control_grid_layout.setContentsMargins(0, 0, 0, 0)
        self._main_control_grid_layout.setSpacing(2)
        self._main_control_buttons_ui: Dict[str, QPushButton] = {}
        self._control_button_instances: Dict[str, List[QPushButton]] = {}
        self._control_button_clones: List[QPushButton] = []
        for text in WINDOW_LAYOUT_MAIN_ORDER:
            btn = QPushButton(text)
            btn.setMinimumHeight(42)
            if text == "Pause":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                btn.clicked.connect(self._toggle_pause)
            elif text == "STOP":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
                btn.clicked.connect(self._stop_playback)
            elif text == "Next":
                btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                btn.clicked.connect(self._play_next)
                btn.setEnabled(False)
            elif text == "Cue":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_cue_mode)
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(self._show_cue_button_menu)
            elif text == "Loop":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_loop)
            elif text == "Multi-Play":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_multi_play_mode)
            elif text == "Button Drag":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_button_drag_mode)
            elif text == "Rapid Fire":
                btn.clicked.connect(self._on_rapid_fire_clicked)
            elif text == "Reset Page":
                btn.clicked.connect(self._reset_current_page_state)
            elif text == "Talk":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_talk)
            elif text == "Play List":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_playlist_mode)
            elif text == "Shuffle":
                btn.setCheckable(True)
                btn.clicked.connect(self._toggle_shuffle_mode)
                btn.setEnabled(False)
            elif text == "Search":
                btn.clicked.connect(self._open_find_dialog)
            elif text == "DSP":
                btn.clicked.connect(self._open_dsp_window)
            elif text == "Go To Playing":
                btn.clicked.connect(self._go_to_current_playing_page)
            elif text == "Vocal Removed":
                btn.setCheckable(True)
                btn.setToolTip("")
                btn.clicked.connect(self._toggle_global_vocal_removed_mode)
            if text in {"Pause", "STOP", "Next", "Loop", "Reset Page", "Talk", "Cue", "Play List", "Shuffle", "Rapid Fire", "Multi-Play", "Button Drag", "Vocal Removed"}:
                self.control_buttons[text] = btn
            self._main_control_buttons_ui[text] = btn
            btn.toggled.connect(lambda _checked=False, key=text: self._sync_control_button_instances(key))
            btn.clicked.connect(lambda _checked=False, key=text: self._sync_control_button_instances(key))
        left_layout.addLayout(self._main_control_grid_layout)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(6)
        self.page_status.setStyleSheet("font-size: 13pt; color: #0A29E0; font-weight: bold;")
        self.page_status.setWordWrap(False)
        page_status_scroll = QScrollArea()
        page_status_scroll.setWidgetResizable(True)
        page_status_scroll.setFrameShape(QFrame.NoFrame)
        page_status_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        page_status_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page_status_scroll.setWidget(self.page_status)
        page_status_scroll.setMinimumHeight(30)
        page_status_scroll.setMaximumHeight(34)
        status_row.addWidget(page_status_scroll, 1)
        left_layout.addLayout(status_row)
        self.now_playing_label.set_now_playing_text("NOW PLAYING:", "")
        self.now_playing_label.setVisible(True)
        self.now_playing_label.setFixedHeight(40)
        left_layout.addWidget(self.now_playing_label)
        self.main_lyric_label.set_now_playing_text("LYRIC:", "")
        self.main_lyric_label.setVisible(True)
        self.main_lyric_label.setFixedHeight(42)
        self.main_lyric_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lyric_row = QHBoxLayout()
        lyric_row.setContentsMargins(0, 0, 0, 0)
        lyric_row.setSpacing(6)
        lyric_row.addWidget(self.main_lyric_label, 1)
        self.lyric_navigator_button = QPushButton("Lyric Navigator")
        self.lyric_navigator_button.setMinimumHeight(36)
        self.lyric_navigator_button.clicked.connect(self._open_lyric_navigator)
        lyric_row.addWidget(self.lyric_navigator_button, 0)
        self.lyric_blank_toggle_button = QPushButton("Blank Lyric")
        self.lyric_blank_toggle_button.setMinimumHeight(36)
        self.lyric_blank_toggle_button.setCheckable(True)
        self.lyric_blank_toggle_button.clicked.connect(self._toggle_lyric_force_blank)
        lyric_row.addWidget(self.lyric_blank_toggle_button, 0)
        self._sync_lyric_display_controls()
        left_layout.addLayout(lyric_row)
        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self._fade_control_grid_layout = QGridLayout()
        self._fade_control_grid_layout.setContentsMargins(0, 0, 0, 0)
        self._fade_control_grid_layout.setSpacing(2)
        self._fade_control_buttons_ui: Dict[str, QPushButton] = {}
        fade_specs = [
            ("Fade In", self._toggle_fade_in_mode, "Fade in on start"),
            ("X", self._toggle_cross_auto_mode, "Cross fade (fade out + fade in)"),
            ("Fade Out", self._toggle_fade_out_mode, "Fade out on stop/switch"),
        ]
        for label, handler, tooltip in fade_specs:
            b = QPushButton(label)
            b.setMinimumHeight(38)
            b.setCheckable(True)
            b.setToolTip(tooltip)
            b.clicked.connect(handler)
            self.control_buttons[label] = b
            self._fade_control_buttons_ui[label] = b
            b.toggled.connect(lambda _checked=False, key=label: self._sync_control_button_instances(key))
            b.clicked.connect(lambda _checked=False, key=label: self._sync_control_button_instances(key))
        right_layout.addLayout(self._fade_control_grid_layout)
        self._apply_top_control_layout()

        meter_row = QHBoxLayout()
        meter_labels = QVBoxLayout()
        meter_labels.addWidget(QLabel("dBFS"))
        meter_labels.addWidget(QLabel("Left"))
        meter_labels.addWidget(QLabel("Right"))
        meter_row.addLayout(meter_labels)

        meters = QVBoxLayout()
        meters.setSpacing(3)
        meters.addWidget(self.meter_scale)
        meters.addWidget(self.left_meter)
        meters.addWidget(self.right_meter)
        meter_row.addLayout(meters, 1)
        right_layout.addLayout(meter_row)

        volume_row = QHBoxLayout()
        volume_row.addWidget(QLabel("Volume"))
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(90)
        self.volume_slider.setFixedWidth(140)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_row.addWidget(self.volume_slider)
        volume_row.addStretch(1)
        right_layout.addLayout(volume_row)

        times = QHBoxLayout()
        for title, value in [
            ("Total Time", self.total_time),
            ("Elapsed", self.elapsed_time),
            ("Remaining", self.remaining_time),
        ]:
            box = QFrame()
            box.setFrameShape(QFrame.StyledPanel)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(8, 2, 8, 2)
            label = QLabel(title)
            label.setStyleSheet("font-size: 16pt; font-weight: bold;")
            value.setStyleSheet("font-size: 30pt; font-weight: bold;")
            value.setAlignment(Qt.AlignCenter)
            box_layout.addWidget(label)
            box_layout.addWidget(value)
            times.addWidget(box, 1)
        right_layout.addLayout(times)

        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: white;")
        self.progress_label.setMinimumHeight(28)
        self.progress_label.set_display_mode(self.main_progress_display_mode)
        self.progress_label.setVisible(True)
        right_layout.addWidget(self.progress_label)

        transport_row = QHBoxLayout()
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.valueChanged.connect(self._on_seek_value_changed)
        transport_row.addWidget(self.seek_slider, 1)
        right_layout.addLayout(transport_row)

        jog_meta_row = QHBoxLayout()
        self.jog_percent_label.setAlignment(Qt.AlignCenter)
        self.jog_out_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        jog_meta_row.addWidget(self.jog_in_label)
        jog_meta_row.addStretch(1)
        jog_meta_row.addWidget(self.jog_percent_label)
        jog_meta_row.addStretch(1)
        jog_meta_row.addWidget(self.jog_out_label)
        right_layout.addLayout(jog_meta_row)

        layout.addWidget(left, 2)
        layout.addWidget(right, 3)
        return panel

    @staticmethod
    def _clear_layout_only(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue

    def _make_control_button_clone(self, key: str) -> QPushButton:
        primary = self.control_buttons.get(key)
        if primary is None:
            primary = self._main_control_buttons_ui.get(key)
        if primary is None:
            primary = self._fade_control_buttons_ui.get(key)
        btn = QPushButton(key)
        if primary is None:
            return btn
        btn.setCheckable(primary.isCheckable())
        btn.setToolTip(primary.toolTip())
        if primary.icon().isNull() is False:
            btn.setIcon(primary.icon())
        btn.clicked.connect(lambda _checked=False, token=key: self._click_named_button(token))
        return btn

    def _click_named_button(self, key: str) -> None:
        primary = self.control_buttons.get(key)
        if primary is None:
            primary = self._main_control_buttons_ui.get(key)
        if primary is None:
            primary = self._fade_control_buttons_ui.get(key)
        if primary is None or (not primary.isEnabled()):
            return
        primary.click()

    def _sync_control_button_instances(self, key: Optional[str] = None) -> None:
        keys = [key] if key else list(self._control_button_instances.keys())
        for token in keys:
            if not token:
                continue
            primary = self.control_buttons.get(token)
            if primary is None:
                primary = self._main_control_buttons_ui.get(token)
            if primary is None:
                primary = self._fade_control_buttons_ui.get(token)
            if primary is None:
                continue
            for inst in self._control_button_instances.get(token, []):
                if inst is primary:
                    continue
                inst.blockSignals(True)
                inst.setCheckable(primary.isCheckable())
                if primary.isCheckable():
                    inst.setChecked(primary.isChecked())
                inst.setEnabled(primary.isEnabled())
                inst.setText(primary.text())
                inst.setToolTip(primary.toolTip())
                inst.setStyleSheet(primary.styleSheet())
                inst.setIcon(primary.icon())
                inst.blockSignals(False)
        try:
            self._refresh_launchpad_feedback(force=False)
        except Exception:
            pass

    def _apply_top_control_layout(self) -> None:
        if not hasattr(self, "_main_control_grid_layout") or not hasattr(self, "_fade_control_grid_layout"):
            return
        normalized = normalize_window_layout(self.window_layout)
        self.window_layout = normalized
        self._clear_layout_only(self._main_control_grid_layout)
        self._clear_layout_only(self._fade_control_grid_layout)
        self._control_button_instances = {key: [] for key in [*WINDOW_LAYOUT_MAIN_ORDER, *WINDOW_LAYOUT_FADE_ORDER]}
        for clone in list(self._control_button_clones):
            clone.setParent(None)
            clone.deleteLater()
        self._control_button_clones = []

        for key, btn in self._main_control_buttons_ui.items():
            btn.hide()
            self._control_button_instances.setdefault(key, []).append(btn)
        for key, btn in self._fade_control_buttons_ui.items():
            btn.hide()
            self._control_button_instances.setdefault(key, []).append(btn)

        all_keys = [*WINDOW_LAYOUT_MAIN_ORDER, *WINDOW_LAYOUT_FADE_ORDER]
        used_main: Dict[str, int] = {}
        for item in list(normalized.get("main", [])):
            if not isinstance(item, dict):
                continue
            key = str(item.get("button", "")).strip()
            if key not in all_keys:
                continue
            use_count = used_main.get(key, 0)
            used_main[key] = use_count + 1
            if use_count == 0:
                btn = self._main_control_buttons_ui.get(key)
                if btn is None:
                    btn = self._fade_control_buttons_ui.get(key)
            else:
                btn = self._make_control_button_clone(key)
                self._control_button_clones.append(btn)
                self._control_button_instances.setdefault(key, []).append(btn)
            if btn is None:
                continue
            btn.setMinimumHeight(42 * max(1, int(item.get("h", 1))))
            self._main_control_grid_layout.addWidget(
                btn,
                int(item.get("y", 0)),
                int(item.get("x", 0)),
                int(item.get("h", 1)),
                int(item.get("w", 1)),
            )
            btn.show()

        used_fade: Dict[str, int] = {}
        for item in list(normalized.get("fade", [])):
            if not isinstance(item, dict):
                continue
            key = str(item.get("button", "")).strip()
            if key not in all_keys:
                continue
            use_count = used_fade.get(key, 0)
            used_fade[key] = use_count + 1
            if use_count == 0:
                btn = self._fade_control_buttons_ui.get(key)
                if btn is None:
                    btn = self._main_control_buttons_ui.get(key)
            else:
                btn = self._make_control_button_clone(key)
                self._control_button_clones.append(btn)
                self._control_button_instances.setdefault(key, []).append(btn)
            if btn is None:
                continue
            btn.setMinimumHeight(38 * max(1, int(item.get("h", 1))))
            self._fade_control_grid_layout.addWidget(
                btn,
                int(item.get("y", 0)),
                int(item.get("x", 0)),
                int(item.get("h", 1)),
                int(item.get("w", 1)),
            )
            btn.show()
        self._sync_control_button_instances()

    def _set_dirty(self, dirty: bool = True) -> None:
        if self._dirty == dirty:
            return
        self._dirty = dirty
        self._refresh_window_title()

    def _refresh_window_title(self) -> None:
        base = self.app_title_base
        title = f"{base}    {self.current_set_path}" if self.current_set_path else base
        if self._dirty:
            title = f"{title} *"
        self.setWindowTitle(title)

    def _update_status_totals(self) -> None:
        total_buttons = 0
        total_ms = 0
        for slot in self._current_page_slots():
            if slot.assigned and not slot.marker:
                total_buttons += 1
                total_ms += max(0, int(slot.duration_ms))
        self.status_totals_label.setText(f"{total_buttons} {tr('button')} ({format_set_time(total_ms)})")

    def _on_sound_button_hover(self, slot_index: Optional[int]) -> None:
        self._hover_slot_index = None
        if slot_index is not None and 0 <= slot_index < SLOTS_PER_PAGE:
            self._hover_slot_index = slot_index
        self._refresh_status_hover_label()
        self._refresh_stage_display()
        if self._stage_display_window is not None and self._stage_display_window.isVisible():
            self._stage_display_window.repaint()

    def _refresh_status_hover_label(self) -> None:
        slot_index: Optional[int] = None
        if self._hover_slot_index is not None and 0 <= self._hover_slot_index < SLOTS_PER_PAGE:
            slot_index = self._hover_slot_index
        elif (not self.cue_mode) and (not self.page_playlist_enabled[self.current_group][self.current_page]):
            slot_index = self._next_slot_for_next_action(blocked=None)
        if slot_index is None:
            self.status_hover_label.setText(tr("Button: -"))
            return
        group = self._view_group_key()
        group_text = group if group == "Q" else group.upper()
        self.status_hover_label.setText(f"{tr('Button: ')}{group_text}-{self.current_page + 1}-{slot_index + 1}")

    def _format_button_key(self, slot_key: Tuple[str, int, int]) -> str:
        group, page_index, slot_index = slot_key
        group_text = group if group == "Q" else group.upper()
        return f"{group_text}-{page_index + 1}-{slot_index + 1}"

    def _update_status_now_playing(self) -> None:
        if not self._active_playing_keys:
            self.status_now_playing_label.setText(tr("Now Playing: -"))
            return
        ordered = sorted(self._active_playing_keys, key=lambda item: (item[0], item[1], item[2]))
        values = ", ".join(self._format_button_key(key) for key in ordered)
        self.status_now_playing_label.setText(f"{tr('Now Playing: ')}{values}")

    def resizeEvent(self, event) -> None:
        QMainWindow.resizeEvent(self, event)
        self._update_page_list_item_heights()
        if self._lock_screen_overlay is not None:
            self._lock_screen_overlay.sync_geometry(rebuild_targets=self._ui_locked)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.page_list.viewport():
            if event.type() == QEvent.Resize:
                self._update_page_list_item_heights()
            elif event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if 0 <= row < PAGE_COUNT:
                        self._page_drag_source_key = (self.current_group, row)
                        self._page_drag_start_pos = event.pos()
                    else:
                        self._page_drag_source_key = None
                        self._page_drag_start_pos = None
            elif event.type() == QEvent.MouseMove:
                if (
                    self._page_drag_start_pos is not None
                    and (event.buttons() & Qt.LeftButton)
                    and self._is_button_drag_enabled()
                    and self._page_drag_source_key is not None
                ):
                    if (event.pos() - self._page_drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                        source_group, source_page = self._page_drag_source_key
                        if source_group == self.current_group:
                            self._start_page_button_drag(source_page)
                        self._page_drag_start_pos = None
                        self._page_drag_source_key = None
                        return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._page_drag_start_pos = None
                self._page_drag_source_key = None
            elif event.type() == QEvent.DragEnter:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
                if self._can_accept_page_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.DragMove:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if self._handle_drag_over_page(row):
                        event.acceptProposedAction()
                        return True
                if self._can_accept_page_button_drop(event.mimeData()):
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if self._handle_drag_over_page(row, require_created=False):
                        event.acceptProposedAction()
                        return True
            elif event.type() == QEvent.Drop:
                if self._can_accept_sound_button_drop(event.mimeData()):
                    event.acceptProposedAction()
                    return True
                if self._can_accept_page_button_drop(event.mimeData()):
                    item = self.page_list.itemAt(event.pos())
                    row = self.page_list.row(item) if item is not None else -1
                    if self._handle_page_button_drop(row, event.mimeData()):
                        event.acceptProposedAction()
                        return True
        return QMainWindow.eventFilter(self, obj, event)
