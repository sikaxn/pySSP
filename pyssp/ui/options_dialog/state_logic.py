from __future__ import annotations

from .shared import *
from .widgets import *


class StateLogicMixin:
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
            self._restore_lock_defaults()
            return
        if idx == 3:
            self._restore_hotkey_defaults()
            return
        if idx == 4:
            self._restore_midi_defaults()
            return
        if idx == 5:
            self._restore_color_defaults()
            return
        if idx == 6:
            self._restore_display_defaults()
            return
        if idx == 7:
            self._restore_lyric_defaults()
            return
        if idx == 8:
            self._restore_window_layout_defaults()
            return
        if idx == 9:
            self._restore_delay_defaults()
            return
        if idx == 10:
            self._restore_playback_defaults()
            return
        if idx == 11:
            self._restore_audio_device_defaults()
            return
        if idx == 12:
            self._restore_preload_defaults()
            return
        if idx == 13:
            self._restore_talk_defaults()
            return
        if idx == 14:
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
        token = str(d.get("now_playing_display_mode", "caption")).strip().lower()
        if token == "filename":
            self.now_playing_filename_radio.setChecked(True)
        elif token == "filepath":
            self.now_playing_filepath_radio.setChecked(True)
        elif token == "note":
            self.now_playing_note_radio.setChecked(True)
        elif token == "caption_note":
            self.now_playing_caption_note_radio.setChecked(True)
        else:
            self.now_playing_caption_radio.setChecked(True)
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
        mode_token = str(d.get("main_progress_display_mode", "progress_bar")).strip().lower()
        if mode_token == "waveform":
            self.main_progress_display_waveform_radio.setChecked(True)
        else:
            self.main_progress_display_progress_bar_radio.setChecked(True)
        self.main_progress_show_text_checkbox.setChecked(bool(d.get("main_progress_show_text", True)))

    def _restore_lock_defaults(self) -> None:
        d = self._DEFAULTS
        self.lock_allow_quit_checkbox.setChecked(bool(d.get("lock_allow_quit", False)))
        self.lock_allow_system_hotkeys_checkbox.setChecked(bool(d.get("lock_allow_system_hotkeys", False)))
        self.lock_allow_quick_action_hotkeys_checkbox.setChecked(bool(d.get("lock_allow_quick_action_hotkeys", False)))
        self.lock_allow_sound_button_hotkeys_checkbox.setChecked(bool(d.get("lock_allow_sound_button_hotkeys", False)))
        self.lock_allow_midi_control_checkbox.setChecked(bool(d.get("lock_allow_midi_control", False)))
        self.lock_auto_allow_quit_checkbox.setChecked(bool(d.get("lock_auto_allow_quit", False)))
        self.lock_auto_allow_midi_control_checkbox.setChecked(bool(d.get("lock_auto_allow_midi_control", False)))
        method = str(d.get("lock_unlock_method", "click_3_random_points")).strip().lower()
        if method == "click_one_button":
            self.lock_method_fixed_button_radio.setChecked(True)
        elif method == "slide_to_unlock":
            self.lock_method_slide_radio.setChecked(True)
        else:
            self.lock_method_random_points_radio.setChecked(True)
        self.lock_require_password_checkbox.setChecked(bool(d.get("lock_require_password", False)))
        password = str(d.get("lock_password", ""))
        self._lock_existing_password = password
        self.lock_password_edit.clear()
        self.lock_password_verify_edit.clear()
        restart_state = str(d.get("lock_restart_state", "unlock_on_restart")).strip().lower()
        if restart_state == "lock_on_restart":
            self.lock_restart_lock_radio.setChecked(True)
        else:
            self.lock_restart_unlock_radio.setChecked(True)
        self._validate_lock_page()

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

    def _restore_display_defaults(self) -> None:
        d = self._DEFAULTS
        self._stage_display_layout = self._normalize_stage_display_layout(list(d.get("stage_display_layout", [])))
        self._stage_display_visibility = self._normalize_stage_display_visibility(dict(d.get("stage_display_visibility", {})))
        self._stage_display_gadgets = normalize_stage_display_gadgets(
            d.get("stage_display_gadgets"),
            legacy_layout=self._stage_display_layout,
            legacy_visibility=self._stage_display_visibility,
        )
        self._set_combo_data_or_default(
            self.display_text_source_combo,
            str(d.get("stage_display_text_source", "caption")),
            "caption",
        )
        if hasattr(self, "display_layout_editor"):
            self.display_layout_editor.set_gadgets(self._stage_display_gadgets)
        if hasattr(self, "_display_gadget_checks"):
            for key, checkbox in self._display_gadget_checks.items():
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("visible", True)))
        if hasattr(self, "_display_gadget_hide_text_checks"):
            for key, checkbox in self._display_gadget_hide_text_checks.items():
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_text", False)))
        if hasattr(self, "_display_gadget_hide_border_checks"):
            for key, checkbox in self._display_gadget_hide_border_checks.items():
                checkbox.setChecked(bool(self._stage_display_gadgets.get(key, {}).get("hide_border", False)))
        if hasattr(self, "_display_gadget_orientation_combos"):
            for key, combo in self._display_gadget_orientation_combos.items():
                token = str(self._stage_display_gadgets.get(key, {}).get("orientation", "vertical")).strip().lower()
                if token not in {"horizontal", "vertical"}:
                    token = "vertical"
                combo.setCurrentIndex(max(0, combo.findData(token)))
        self._refresh_display_layer_table()
        self._sync_alert_edit_button_text()

    def _restore_window_layout_defaults(self) -> None:
        d = self._DEFAULTS
        self._window_layout = normalize_window_layout(d.get("window_layout"))
        if hasattr(self, "window_layout_main_editor"):
            self.window_layout_main_editor.set_items(list(self._window_layout.get("main", [])))
        if hasattr(self, "window_layout_fade_editor"):
            self.window_layout_fade_editor.set_items(list(self._window_layout.get("fade", [])))
        if hasattr(self, "window_layout_show_all_checkbox"):
            self.window_layout_show_all_checkbox.setChecked(bool(self._window_layout.get("show_all_available", False)))
        self._refresh_window_layout_available_list()

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

    def _restore_midi_defaults(self) -> None:
        d = self._DEFAULTS
        self._midi_input_device_ids = list(d.get("midi_input_device_ids", []))
        self._launchpad_enabled = bool(d.get("launchpad_enabled", False))
        self._launchpad_device_selector = str(d.get("launchpad_device_selector", "")).strip()
        self._launchpad_output_device_id = str(d.get("launchpad_output_device_id", "")).strip()
        self._launchpad_layout = normalize_launchpad_layout(str(d.get("launchpad_layout", "bottom_six")))
        self._launchpad_control_bindings = [
            str(value or "").strip() for value in d.get("launchpad_control_bindings", [""] * 16)[:16]
        ]
        if len(self._launchpad_control_bindings) < 16:
            self._launchpad_control_bindings.extend(["" for _ in range(16 - len(self._launchpad_control_bindings))])
        self._refresh_midi_input_devices()
        self._set_combo_data_or_default(self.launchpad_layout_combo, self._launchpad_layout, "bottom_six")
        self._set_combo_data_or_default(self.launchpad_device_combo, self._launchpad_device_selector, "")
        self._set_combo_data_or_default(self.launchpad_output_combo, self._launchpad_output_device_id, "")
        for index, combo in enumerate(self._launchpad_control_combos):
            self._set_combo_data_or_default(combo, self._launchpad_control_bindings[index], LAUNCHPAD_ACTION_NONE)
        self._sync_launchpad_controls()
        defaults = dict(d.get("midi_hotkeys", {}))
        for key, (edit1, edit2) in self._midi_hotkey_edits.items():
            v1, v2 = defaults.get(key, ("", ""))
            edit1.setBinding(v1)
            edit2.setBinding(v2)
        self.midi_quick_action_enabled_checkbox.setChecked(bool(d.get("midi_quick_action_enabled", False)))
        midi_quick_defaults = list(d.get("midi_quick_action_bindings", [""] * 48))
        for i, edit in enumerate(self._midi_quick_action_edits):
            edit.setBinding(midi_quick_defaults[i] if i < len(midi_quick_defaults) else "")
        self.midi_sound_button_hotkey_enabled_checkbox.setChecked(bool(d.get("midi_sound_button_hotkey_enabled", False)))
        if str(d.get("midi_sound_button_hotkey_priority", "system_first")) == "sound_button_first":
            self.midi_sound_hotkey_priority_sound_first_radio.setChecked(True)
        else:
            self.midi_sound_hotkey_priority_system_first_radio.setChecked(True)
        self.midi_sound_button_go_to_playing_checkbox.setChecked(bool(d.get("midi_sound_button_hotkey_go_to_playing", False)))
        self.midi_rotary_enabled_checkbox.setChecked(bool(d.get("midi_rotary_enabled", False)))
        self.midi_rotary_group_edit.setBinding(str(d.get("midi_rotary_group_binding", "")))
        self.midi_rotary_page_edit.setBinding(str(d.get("midi_rotary_page_binding", "")))
        self.midi_rotary_sound_button_edit.setBinding(str(d.get("midi_rotary_sound_button_binding", "")))
        self.midi_rotary_jog_edit.setBinding(str(d.get("midi_rotary_jog_binding", "")))
        self.midi_rotary_volume_edit.setBinding(str(d.get("midi_rotary_volume_binding", "")))
        self.midi_rotary_group_invert_checkbox.setChecked(bool(d.get("midi_rotary_group_invert", False)))
        self.midi_rotary_page_invert_checkbox.setChecked(bool(d.get("midi_rotary_page_invert", False)))
        self.midi_rotary_sound_button_invert_checkbox.setChecked(bool(d.get("midi_rotary_sound_button_invert", False)))
        self.midi_rotary_jog_invert_checkbox.setChecked(bool(d.get("midi_rotary_jog_invert", False)))
        self.midi_rotary_volume_invert_checkbox.setChecked(bool(d.get("midi_rotary_volume_invert", False)))
        self.midi_rotary_group_sensitivity_spin.setValue(int(d.get("midi_rotary_group_sensitivity", 1)))
        self.midi_rotary_page_sensitivity_spin.setValue(int(d.get("midi_rotary_page_sensitivity", 1)))
        self.midi_rotary_sound_button_sensitivity_spin.setValue(int(d.get("midi_rotary_sound_button_sensitivity", 1)))
        self._midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_group_relative_mode", "auto"))
        )
        self._midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_page_relative_mode", "auto"))
        )
        self._midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_sound_button_relative_mode", "auto"))
        )
        self._midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_jog_relative_mode", "auto"))
        )
        self._midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            str(d.get("midi_rotary_volume_relative_mode", "auto"))
        )
        self._set_combo_data_or_default(self.midi_rotary_volume_mode_combo, str(d.get("midi_rotary_volume_mode", "relative")), "relative")
        self.midi_rotary_volume_step_spin.setValue(int(d.get("midi_rotary_volume_step", 2)))
        self.midi_rotary_jog_step_spin.setValue(int(d.get("midi_rotary_jog_step_ms", 250)))
        self._validate_midi_conflicts()

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

    def _validate_lock_page(self) -> None:
        require_password = bool(self.lock_require_password_checkbox.isChecked())
        password = str(self.lock_password_edit.text())
        verify = str(self.lock_password_verify_edit.text())
        has_saved_password = bool(self._lock_existing_password)
        changing_password = bool(password or verify)
        message = ""
        if require_password and changing_password:
            if not password:
                message = "Password is required when changing the password."
            elif password != verify:
                message = "Password and Verify Password must match."
        if message:
            self.lock_password_status_label.setText(message)
            self.lock_password_status_label.setVisible(True)
        else:
            self.lock_password_status_label.setVisible(False)
            self.lock_password_status_label.setText("")
        if require_password:
            if has_saved_password:
                self.lock_password_info_label.setText("Password has been set. Start typing in Password to change it.")
            elif changing_password:
                self.lock_password_info_label.setText("Type a new password and verify it to save the change.")
            else:
                self.lock_password_info_label.setText("Password fields are ignored until you start typing.")
        else:
            self.lock_password_info_label.setText("Password unlock is disabled.")
        self._sync_ok_button_state()

    def _sync_ok_button_state(self) -> None:
        if self.ok_button is None:
            return
        keyboard_conflict = bool(self.hotkey_warning_label is not None and self.hotkey_warning_label.text().strip())
        midi_conflict = bool(self._midi_has_conflict)
        lock_invalid = bool(
            hasattr(self, "lock_password_status_label")
            and self.lock_password_status_label.text().strip()
        )
        self.ok_button.setEnabled((not keyboard_conflict) and (not midi_conflict) and (not lock_invalid))

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
        if self.hotkey_warning_label is None:
            self._sync_ok_button_state()
            return
        if not has_conflict:
            self.hotkey_warning_label.setVisible(False)
            self.hotkey_warning_label.setText("")
            self._sync_ok_button_state()
            return
        display = "; ".join(conflicts[:4])
        if len(conflicts) > 4:
            display += f"; +{len(conflicts) - 4} {tr('more')}"
        self.hotkey_warning_label.setText(f"{tr('Hotkey conflict detected. Fix duplicates before saving.')} {display}")
        self.hotkey_warning_label.setVisible(True)
        self._sync_ok_button_state()

    def _validate_midi_conflicts(self) -> None:
        seen: Dict[str, List[tuple[str, int, str]]] = {}
        conflicts: List[str] = []
        conflict_cells: set[tuple[str, int]] = set()
        for key, (edit1, edit2) in self._midi_hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                token = normalize_midi_binding(edit.binding())
                if not token:
                    continue
                selector, msg = split_midi_binding(token)
                entries = seen.setdefault(msg, [])
                for prev_key, prev_slot_index, prev_selector in entries:
                    if (
                        (not prev_selector)
                        or (not selector)
                        or (prev_selector == selector)
                    ):
                        conflict_cells.add((prev_key, prev_slot_index))
                        conflict_cells.add((key, slot_index))
                        left = f"{tr(self._hotkey_labels.get(prev_key, prev_key))} ({prev_slot_index})"
                        right = f"{tr(self._hotkey_labels.get(key, key))} ({slot_index})"
                        conflicts.append(f"{token}: {left} {tr('and')} {right}")
                entries.append((key, slot_index, selector))

        quick_enabled = bool(self.midi_quick_action_enabled_checkbox.isChecked())
        quick_conflict_rows: set[int] = set()
        if quick_enabled:
            for idx, edit in enumerate(self._midi_quick_action_edits):
                token = normalize_midi_binding(edit.binding())
                if not token:
                    continue
                selector, msg = split_midi_binding(token)
                entries = seen.setdefault(msg, [])
                row_has_conflict = False
                for prev_key, prev_slot_index, prev_selector in entries:
                    if (
                        (not prev_selector)
                        or (not selector)
                        or (prev_selector == selector)
                    ):
                        conflict_cells.add((prev_key, prev_slot_index))
                        conflicts.append(
                            f"{token}: {self._describe_conflict_target(prev_key, prev_slot_index)} {tr('and')} {tr('Quick Action')} ({idx + 1})"
                        )
                        row_has_conflict = True
                        if prev_key == "midi_quick_action":
                            quick_conflict_rows.add(max(0, prev_slot_index - 1))
                if row_has_conflict:
                    quick_conflict_rows.add(idx)
                entries.append(("midi_quick_action", idx + 1, selector))

        for idx, edit in enumerate(self._midi_quick_action_edits):
            if quick_enabled and idx in quick_conflict_rows:
                edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
            elif self._learning_midi_target is not edit:
                edit.setStyleSheet("")
        for key, (edit1, edit2) in self._midi_hotkey_edits.items():
            for slot_index, edit in enumerate((edit1, edit2), start=1):
                if (key, slot_index) in conflict_cells:
                    edit.setStyleSheet("QLineEdit{border:2px solid #B00020;}")
                elif self._learning_midi_target is not edit:
                    edit.setStyleSheet("")

        has_conflict = bool(conflicts)
        self._midi_has_conflict = has_conflict
        if self._midi_warning_label is not None:
            if has_conflict:
                display = "; ".join(conflicts[:4])
                if len(conflicts) > 4:
                    display += f"; +{len(conflicts) - 4} {tr('more')}"
                self._midi_warning_label.setStyleSheet("color:#B00020; font-weight:bold;")
                self._midi_warning_label.setText(f"MIDI conflict detected. Fix duplicates before saving. {display}")
                self._midi_warning_label.setVisible(True)
            else:
                if self._learning_midi_rotary_target is None:
                    self._midi_warning_label.setVisible(False)
                    self._midi_warning_label.setText("")
        self._sync_ok_button_state()

    def _describe_conflict_target(self, key: str, slot_index: int) -> str:
        if key in {"quick_action", "midi_quick_action"}:
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
        mode = str(d["vocal_removed_toggle_fade_mode"])
        if mode == "follow_cross_fade_custom":
            self.vocal_removed_follow_cross_fade_custom_radio.setChecked(True)
        elif mode == "never":
            self.vocal_removed_never_fade_radio.setChecked(True)
        elif mode == "always":
            self.vocal_removed_always_fade_radio.setChecked(True)
        else:
            self.vocal_removed_follow_cross_fade_radio.setChecked(True)
        self.vocal_removed_toggle_custom_spin.setValue(float(d["vocal_removed_toggle_custom_sec"]))
        self.vocal_removed_toggle_always_spin.setValue(float(d["vocal_removed_toggle_always_sec"]))
        self._sync_fade_out_end_lead_enabled()
        self._sync_vocal_removed_toggle_fade_enabled()

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
        self._refresh_midi_input_devices(force_refresh=False)
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
        self.soundbutton_timecode_offset_enabled_checkbox.setChecked(
            bool(d.get("soundbutton_timecode_offset_enabled", True))
        )
        self.respect_soundbutton_timecode_timeline_setting_checkbox.setChecked(
            bool(d.get("respect_soundbutton_timecode_timeline_setting", True))
        )

    def _restore_preload_defaults(self) -> None:
        d = self._DEFAULTS
        self.preload_audio_enabled_checkbox.setChecked(bool(d["preload_audio_enabled"]))
        self.preload_current_page_checkbox.setChecked(bool(d["preload_current_page_audio"]))
        self.preload_memory_pressure_checkbox.setChecked(bool(d["preload_memory_pressure_enabled"]))
        self.preload_pause_on_playback_checkbox.setChecked(bool(d["preload_pause_on_playback"]))
        self.preload_use_ffmpeg_checkbox.setChecked(bool(d["preload_use_ffmpeg"]))
        step_mb = int(self._preload_slider_step_mb)
        target_mb = max(step_mb, min(int(self._preload_ram_cap_mb), int(d["preload_audio_memory_limit_mb"])))
        self.preload_memory_slider.setValue(max(1, target_mb // step_mb))
        self._update_preload_slider_label()
        target_wave_mb = max(self._waveform_cache_min_mb, min(self._waveform_cache_max_mb, int(d["waveform_cache_limit_mb"])))
        target_wave_mb = (target_wave_mb // self._waveform_cache_slider_step_mb) * self._waveform_cache_slider_step_mb
        target_wave_mb = max(self._waveform_cache_min_mb, target_wave_mb)
        self.waveform_cache_size_input.setValue(target_wave_mb)
        self.waveform_cache_size_slider.setValue(target_wave_mb // self._waveform_cache_slider_step_mb)
        self.waveform_cache_clear_on_launch_checkbox.setChecked(bool(d["waveform_cache_clear_on_launch"]))
        self._update_waveform_cache_size_label(target_wave_mb)
        self._restore_audio_format_defaults()

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
        self._update_web_remote_page_labels(int(self.web_remote_port_spin.value()))

    def _restore_lyric_defaults(self) -> None:
        d = self._DEFAULTS
        token = str(d.get("main_ui_lyric_display_mode", "always")).strip().lower()
        if token == "when_available":
            self.main_ui_lyric_display_when_available_radio.setChecked(True)
        elif token == "never":
            self.main_ui_lyric_display_never_radio.setChecked(True)
        else:
            self.main_ui_lyric_display_always_radio.setChecked(True)
        self.search_lyric_on_add_sound_button_checkbox.setChecked(
            bool(d.get("search_lyric_on_add_sound_button", True))
        )
        self._set_combo_data_or_default(
            self.new_lyric_file_format_combo,
            str(d.get("new_lyric_file_format", "srt")),
            "srt",
        )

    def _restore_audio_format_defaults(self) -> None:
        d = self._DEFAULTS
        supported = [str(token).strip().lower() for token in d.get("supported_audio_format_extensions", []) if str(token).strip()]
        self.supported_audio_format_extensions_value.setText(", ".join(supported) if supported else tr("(none detected)"))
        self.verify_sound_file_on_add_checkbox.setChecked(bool(d.get("verify_sound_file_on_add", True)))
        self.allow_other_unsupported_audio_files_checkbox.setChecked(
            bool(d.get("allow_other_unsupported_audio_files", False))
        )
        self.disable_path_safety_checkbox.setChecked(bool(d.get("disable_path_safety", False)))
        self._update_disable_path_safety_warning()
