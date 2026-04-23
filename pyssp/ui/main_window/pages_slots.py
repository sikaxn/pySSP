from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class PagesSlotsMixin:
    def _select_group(self, group: str) -> None:
        self.cue_mode = False
        self._hotkey_selected_slot_key = None
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(False)
        self.current_group = group
        self.current_page = 0
        self.current_playlist_start = None
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()

    def _select_page(self, index: int) -> None:
        if index < 0:
            return
        if self.cue_mode:
            self.current_page = 0
            self._hotkey_selected_slot_key = None
            self._update_page_status()
            self._queue_current_page_audio_preload()
            return
        self.current_page = index
        self._hotkey_selected_slot_key = None
        self.current_playlist_start = None
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_page_status()
        self._queue_current_page_audio_preload()

    def _refresh_group_buttons(self) -> None:
        for group, button in self.group_buttons.items():
            if group == self.current_group:
                button.setStyleSheet(
                    f"background: {self.active_group_color}; font-size: 18pt; font-weight: bold; border: 1px solid #7C7C7C;"
                )
            else:
                button.setStyleSheet(
                    f"background: {self.inactive_group_color}; font-size: 18pt; font-weight: bold; border: 1px solid #8A8A8A;"
                )

    def _refresh_page_list(self) -> None:
        self.page_list.blockSignals(True)
        self.page_list.clear()
        if self.cue_mode:
            cue_item = QListWidgetItem(tr("Cue Page"))
            cue_item.setTextAlignment(Qt.AlignCenter)
            self.page_list.addItem(cue_item)
            self.page_list.setCurrentRow(0)
            self._update_page_list_item_heights()
            self.page_list.blockSignals(False)
            return
        pages = self.data[self.current_group]
        for i, page in enumerate(pages):
            has_sound = any(slot.assigned for slot in page)
            page_name = self.page_names[self.current_group][i].strip()
            if page_name:
                text = page_name
            elif has_sound:
                text = f"{tr('Page ')}{self.current_group.lower()} {i + 1}"
            else:
                text = tr("(Blank Page)")
            item = QListWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            page_color = self.page_colors[self.current_group][i]
            if page_color:
                item.setBackground(QColor(page_color))
                item.setForeground(QColor("#000000" if self._is_light_color(page_color) else "#FFFFFF"))
            self.page_list.addItem(item)
        self.page_list.setCurrentRow(self.current_page)
        self._update_page_list_item_heights()
        self.page_list.blockSignals(False)

    def _update_page_list_item_heights(self) -> None:
        count = self.page_list.count()
        if count <= 0:
            return
        available = max(1, self.page_list.viewport().height())
        item_h = max(24, int(available / count))
        for i in range(count):
            item = self.page_list.item(i)
            item.setSizeHint(QSize(10, item_h))
        self.page_list.doItemsLayout()

    def _is_light_color(self, color_hex: str) -> bool:
        color = color_hex.strip()
        if len(color) != 7 or not color.startswith("#"):
            return True
        try:
            red = int(color[1:3], 16)
            green = int(color[3:5], 16)
            blue = int(color[5:7], 16)
        except ValueError:
            return True
        luminance = (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)
        return luminance >= 150.0

    def _show_page_menu(self, pos) -> None:
        if self.cue_mode:
            return
        item = self.page_list.itemAt(pos)
        row = item and self.page_list.row(item)
        if row is None or row < 0 or row >= PAGE_COUNT:
            row = self.current_page
        if row < 0 or row >= PAGE_COUNT:
            return

        page_created = self._is_page_created(self.current_group, row)
        menu = QMenu(self)

        add_action = menu.addAction("Add Page")
        add_action.setEnabled(not page_created)

        rename_action = menu.addAction("Rename Page")
        rename_action.setEnabled(page_created)

        delete_action = menu.addAction("Delete Page")
        delete_action.setEnabled(page_created)

        menu.addSeparator()
        copy_action = menu.addAction("Copy Page")
        paste_action = menu.addAction("Paste Page")
        paste_action.setEnabled(self._copied_page_buffer is not None)
        menu.addSeparator()
        import_action = menu.addAction("Import Page...")
        export_action = menu.addAction("Export Page...")
        export_action.setEnabled(page_created)
        menu.addSeparator()
        change_color_action = menu.addAction("Change Page Color...")
        clear_color_action = menu.addAction("Clear Page Color")
        clear_color_action.setEnabled(bool(self.page_colors[self.current_group][row]))

        self._apply_strike_to_disabled_menu_actions(menu)
        selected = menu.exec_(self.page_list.mapToGlobal(pos))
        if selected == add_action:
            self._add_page(row)
        elif selected == rename_action:
            self._rename_page(row)
        elif selected == delete_action:
            self._delete_page(row)
        elif selected == copy_action:
            self._copy_page(row)
        elif selected == paste_action:
            self._paste_page(row)
        elif selected == import_action:
            self._import_page(row)
        elif selected == export_action:
            self._export_page(row)
        elif selected == change_color_action:
            self._change_page_color(row)
        elif selected == clear_color_action:
            self._clear_page_color(row)

    def _change_page_color(self, page_index: int) -> None:
        current = self.page_colors[self.current_group][page_index] or "#C0C0C0"
        color = QColorDialog.getColor(QColor(current), self, "Page Button Color")
        if not color.isValid():
            return
        self.page_colors[self.current_group][page_index] = color.name().upper()
        self._set_dirty(True)
        self._refresh_page_list()

    def _clear_page_color(self, page_index: int) -> None:
        if not self.page_colors[self.current_group][page_index]:
            return
        self.page_colors[self.current_group][page_index] = None
        self._set_dirty(True)
        self._refresh_page_list()

    def _is_page_blank(self, page: List[SoundButtonData]) -> bool:
        return not any(slot.assigned or slot.title for slot in page)

    def _add_page(self, page_index: int) -> None:
        name, ok = QInputDialog.getText(self, "Page Name", "Enter page name:")
        if not ok:
            return
        page_name = name.strip()
        if not page_name:
            self._show_info_notice_banner("Page name is required.")
            return
        self.page_names[self.current_group][page_index] = page_name
        self.current_page = page_index
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_page_status()
        self._set_dirty(True)

    def _rename_page(self, page_index: int) -> None:
        current_name = self.page_names[self.current_group][page_index].strip()
        if not current_name:
            current_name = f"Page {self.current_group.lower()} {page_index + 1}"
        name, ok = QInputDialog.getText(self, "Rename Page", "Page name:", text=current_name)
        if not ok:
            return
        self.page_names[self.current_group][page_index] = name.strip()
        self._set_dirty(True)
        self._refresh_page_list()
        if self.current_page == page_index:
            self._update_page_status()

    def _delete_page(self, page_index: int) -> None:
        answer = QMessageBox.question(
            self,
            "Delete Page",
            "Delete this page and clear all its sound buttons?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self.data[self.current_group][page_index] = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self.page_names[self.current_group][page_index] = ""
        self.page_colors[self.current_group][page_index] = None
        self.page_playlist_enabled[self.current_group][page_index] = False
        self.page_shuffle_enabled[self.current_group][page_index] = False
        if self.current_page == page_index:
            self.current_playlist_start = None
            self._sync_playlist_shuffle_buttons()
            self._refresh_sound_grid()
            self._update_page_status()
        self._set_dirty(True)
        self._refresh_page_list()

    def _copy_page(self, page_index: int) -> None:
        source_page = self.data[self.current_group][page_index]
        self._copied_page_buffer = {
            "slots": [
                SoundButtonData(
                    file_path=slot.file_path,
                    vocal_removed_file=slot.vocal_removed_file,
                    title=slot.title,
                    notes=slot.notes,
                    lyric_file=slot.lyric_file,
                    duration_ms=slot.duration_ms,
                    custom_color=slot.custom_color,
                    highlighted=slot.highlighted,
                    played=slot.played,
                    activity_code=slot.activity_code,
                    locked=slot.locked,
                    marker=slot.marker,
                    copied_to_cue=slot.copied_to_cue,
                    load_failed=slot.load_failed,
                    volume_override_pct=slot.volume_override_pct,
                    cue_start_ms=slot.cue_start_ms,
                    cue_end_ms=slot.cue_end_ms,
                    timecode_offset_ms=slot.timecode_offset_ms,
                    timecode_timeline_mode=slot.timecode_timeline_mode,
                    sound_hotkey=slot.sound_hotkey,
                    sound_midi_hotkey=slot.sound_midi_hotkey,
                )
                for slot in source_page
            ],
            "page_name": self.page_names[self.current_group][page_index],
            "page_color": self.page_colors[self.current_group][page_index],
            "playlist": self.page_playlist_enabled[self.current_group][page_index],
            "shuffle": self.page_shuffle_enabled[self.current_group][page_index],
        }

    def _paste_page(self, page_index: int) -> None:
        if not self._copied_page_buffer:
            return
        self.data[self.current_group][page_index] = [
            SoundButtonData(
                file_path=slot.file_path,
                vocal_removed_file=slot.vocal_removed_file,
                title=slot.title,
                notes=slot.notes,
                lyric_file=slot.lyric_file,
                duration_ms=slot.duration_ms,
                custom_color=slot.custom_color,
                highlighted=slot.highlighted,
                played=slot.played,
                activity_code=slot.activity_code,
                locked=slot.locked,
                marker=slot.marker,
                copied_to_cue=slot.copied_to_cue,
                load_failed=slot.load_failed,
                volume_override_pct=slot.volume_override_pct,
                cue_start_ms=slot.cue_start_ms,
                cue_end_ms=slot.cue_end_ms,
                timecode_offset_ms=slot.timecode_offset_ms,
                timecode_timeline_mode=slot.timecode_timeline_mode,
                sound_hotkey=slot.sound_hotkey,
                sound_midi_hotkey=slot.sound_midi_hotkey,
            )
            for slot in self._copied_page_buffer["slots"]
        ]
        self.page_names[self.current_group][page_index] = str(self._copied_page_buffer["page_name"])
        self.page_colors[self.current_group][page_index] = self._copied_page_buffer.get("page_color")
        self.page_playlist_enabled[self.current_group][page_index] = bool(self._copied_page_buffer["playlist"])
        self.page_shuffle_enabled[self.current_group][page_index] = bool(self._copied_page_buffer["shuffle"])
        if self.current_page == page_index:
            self.current_playlist_start = None
            self._sync_playlist_shuffle_buttons()
            self._refresh_sound_grid()
            self._update_page_status()
        self._set_dirty(True)
        self._refresh_page_list()

    def _export_page(self, page_index: int) -> None:
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or os.path.expanduser("~")
        default_name = f"{self.current_group}{page_index + 1}.lib"
        initial_path = os.path.join(start_dir, default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Page Library",
            initial_path,
            "Sports Sounds Pro Page Library (*.lib);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".lib"):
            file_path = f"{file_path}.lib"
        try:
            self._write_page_library_file(file_path, self.current_group, page_index)
        except Exception as exc:
            QMessageBox.critical(self, "Export Page Failed", f"Could not export page:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        self._show_save_notice_banner(f"Page Exported: {file_path}")

    def _import_page(self, page_index: int) -> None:
        start_dir = self.settings.last_open_dir or self.settings.last_save_dir or os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Page Library",
            start_dir,
            "Sports Sounds Pro Page Library (*.lib);;All Files (*.*)",
        )
        if not file_path:
            return
        if self._is_page_created(self.current_group, page_index):
            answer = QMessageBox.question(
                self,
                "Import Page",
                "This page already has content. Replace it with imported page?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        try:
            imported = self._read_page_library_file(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Import Page Failed", f"Could not import page:\n{exc}")
            return

        self.page_names[self.current_group][page_index] = imported["page_name"]
        self.page_colors[self.current_group][page_index] = imported.get("page_color")
        self.page_playlist_enabled[self.current_group][page_index] = imported["page_playlist_enabled"]
        self.page_shuffle_enabled[self.current_group][page_index] = imported["page_shuffle_enabled"]
        self.data[self.current_group][page_index] = imported["slots"]
        self.current_page = page_index
        self.current_playlist_start = None
        self.settings.last_open_dir = os.path.dirname(file_path)
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_page_status()
        self._set_dirty(True)
        self._save_settings()

    def _write_page_library_file(self, file_path: str, group: str, page_index: int) -> None:
        lines: List[str] = [
            "[Main]",
            "CreatedBy=SportsSoundsPro Page Library",
            "",
            "[Page]",
        ]
        page_name = clean_set_value(self.page_names[group][page_index]) or " "
        lines.append(f"PageName={page_name}")
        lines.append(f"PagePlay={'T' if self.page_playlist_enabled[group][page_index] else 'F'}")
        lines.append(f"PageShuffle={'T' if self.page_shuffle_enabled[group][page_index] else 'F'}")
        lines.append(f"PageColor={to_set_color_value(self.page_colors[group][page_index])}")
        page = self.data[group][page_index]
        for slot_index, slot in enumerate(page, start=1):
            if not slot.assigned and not slot.title:
                continue
            if slot.marker:
                marker_title = clean_set_value(slot.title)
                lines.append(f"c{slot_index}={(marker_title + '%%') if marker_title else '%%'}")
                lines.append(f"t{slot_index}= ")
                lines.append(f"activity{slot_index}=7")
                lines.append(f"co{slot_index}=clBtnFace")
                continue
            title = clean_set_value(slot.title or os.path.splitext(os.path.basename(slot.file_path))[0])
            notes = clean_set_value(slot.notes or title)
            lines.append(f"c{slot_index}={notes}")
            lines.append(f"s{slot_index}={clean_set_value(slot.file_path)}")
            vocal_removed_file = clean_set_value(slot.vocal_removed_file)
            if vocal_removed_file:
                lines.append(f"pysspvocalremoval{slot_index}={vocal_removed_file}")
            lines.append(f"t{slot_index}={format_set_time(slot.duration_ms)}")
            lines.append(f"n{slot_index}={title}")
            if slot.volume_override_pct is not None:
                lines.append(f"v{slot_index}={max(0, min(100, int(slot.volume_override_pct)))}")
            hotkey_code = self._encode_sound_hotkey(slot.sound_hotkey)
            if hotkey_code:
                lines.append(f"h{slot_index}={hotkey_code}")
            midi_hotkey_code = self._encode_sound_midi_hotkey(slot.sound_midi_hotkey)
            if midi_hotkey_code:
                lines.append(f"pysspmidi{slot_index}={midi_hotkey_code}")
            lyric_file = clean_set_value(slot.lyric_file)
            if lyric_file:
                lines.append(f"pyssplyric{slot_index}={lyric_file}")
            lines.append(f"activity{slot_index}={'2' if slot.played else '8'}")
            lines.append(f"co{slot_index}={to_set_color_value(slot.custom_color)}")
            if slot.copied_to_cue:
                lines.append(f"ci{slot_index}=Y")
            cue_start, cue_end = self._cue_time_fields_for_set(slot)
            if cue_start is not None:
                lines.append(f"pysspcuestart{slot_index}={cue_start}")
            if cue_end is not None:
                lines.append(f"pysspcueend{slot_index}={cue_end}")
            timecode_offset = format_timecode_offset_hhmmss(slot.timecode_offset_ms, nominal_fps(self.timecode_fps))
            if timecode_offset is not None:
                lines.append(f"pyssptimecodeoffset{slot_index}={timecode_offset}")
            timecode_timeline = normalize_slot_timecode_timeline_mode(slot.timecode_timeline_mode)
            if timecode_timeline != "global":
                lines.append(f"pyssptimecodedisplaytimeline{slot_index}={timecode_timeline}")
        lines.append("")
        payload = "\r\n".join(lines)
        with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(payload)

    def _read_page_library_file(self, file_path: str) -> dict:
        raw = open(file_path, "rb").read()
        text = None
        for encoding in ("utf-8-sig", "utf-16", "gbk", "cp1252", "latin1"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            text = raw.decode("latin1", errors="replace")

        parser = configparser.RawConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read_string(text)
        section_name = "Page"
        if not parser.has_section(section_name):
            raise ValueError("Page section not found in .lib file.")
        section = parser[section_name]

        page_name = section.get("PageName", "").strip()
        page_color = parse_delphi_color(section.get("PageColor", "").strip())
        page_playlist_enabled = section.get("PagePlay", "F").strip().upper() == "T"
        page_shuffle_enabled = section.get("PageShuffle", "F").strip().upper() == "T"
        slots = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        for i in range(1, SLOTS_PER_PAGE + 1):
            path = section.get(f"s{i}", "").strip()
            caption = section.get(f"c{i}", "").strip()
            name = section.get(f"n{i}", "").strip()
            title = (name or caption)
            notes = caption
            activity_code = section.get(f"activity{i}", "").strip()
            marker = False
            if caption.endswith("%%"):
                marker = True
                if not name:
                    title = caption[:-2].strip()
                notes = caption[:-2].strip()
            if activity_code == "7":
                marker = True
            if not path and not title and not marker:
                continue
            if not title and path:
                title = os.path.splitext(os.path.basename(path))[0]
            duration = parse_time_string_to_ms(section.get(f"t{i}", "").strip())
            color = parse_delphi_color(section.get(f"co{i}", "").strip())
            volume_override_pct = self._parse_volume_override_pct(section.get(f"v{i}", "").strip())
            sound_hotkey = self._parse_sound_hotkey(section.get(f"h{i}", "").strip())
            cue_start_raw = section.get(f"pysspcuestart{i}", "").strip()
            cue_end_raw = section.get(f"pysspcueend{i}", "").strip()
            timecode_offset_ms = parse_timecode_offset_ms(
                section.get(f"pyssptimecodeoffset{i}", "").strip()
            )
            timecode_timeline_mode = normalize_slot_timecode_timeline_mode(
                section.get(f"pyssptimecodedisplaytimeline{i}", "").strip()
            )
            if cue_start_raw or cue_end_raw:
                cue_start_ms = self._parse_cue_time_string_to_ms(cue_start_raw)
                cue_end_ms = self._parse_cue_time_string_to_ms(cue_end_raw)
                cue_start_ms, cue_end_ms = self._normalize_cue_points(cue_start_ms, cue_end_ms, duration)
            else:
                cue_start_ms, cue_end_ms = self._parse_cue_points(
                    section.get(f"cs{i}", "").strip(),
                    section.get(f"ce{i}", "").strip(),
                    duration,
                )
            played = activity_code == "2"
            copied = section.get(f"ci{i}", "").strip().upper() == "Y"
            vocal_removed_file = section.get(f"pysspvocalremoval{i}", "").strip()
            slots[i - 1] = SoundButtonData(
                file_path=path,
                vocal_removed_file=vocal_removed_file,
                title=title,
                notes=notes,
                lyric_file=section.get(f"pyssplyric{i}", "").strip(),
                duration_ms=duration,
                custom_color=color,
                played=played,
                activity_code=activity_code or ("2" if played else "8"),
                marker=marker,
                copied_to_cue=copied,
                volume_override_pct=volume_override_pct,
                cue_start_ms=cue_start_ms,
                cue_end_ms=cue_end_ms,
                timecode_offset_ms=timecode_offset_ms,
                timecode_timeline_mode=timecode_timeline_mode,
                sound_hotkey=sound_hotkey,
                sound_midi_hotkey=self._parse_sound_midi_hotkey(section.get(f"pysspmidi{i}", "").strip()),
            )
        return {
            "page_name": page_name,
            "page_color": page_color,
            "page_playlist_enabled": page_playlist_enabled,
            "page_shuffle_enabled": page_shuffle_enabled,
            "slots": slots,
        }

    def _refresh_sound_grid(self) -> None:
        page = self._current_page_slots()
        ram_indicator_enabled = not self._is_button_drag_enabled()
        sound_bindings = self._collect_sound_button_hotkey_bindings() if self.sound_button_hotkey_enabled else {}
        blocked_sound_tokens = (
            self._registered_system_and_quick_tokens()
            if self.sound_button_hotkey_enabled and self.sound_button_hotkey_priority == "system_first"
            else set()
        )
        for i, button in enumerate(self.sound_buttons):
            slot = page[i]
            button.set_ram_loaded(False)
            button.set_indicator_colors(None, [])
            if slot.marker:
                marker_lines = wrap_text_lines(slot.title, self.title_char_limit, 3)
                button.setText("\n".join(line for line in marker_lines if line))
                button.setToolTip("")
            elif not slot.assigned:
                button.setText("")
                button.setToolTip("")
            else:
                button.set_ram_loaded(ram_indicator_enabled and is_audio_preloaded(self._effective_slot_file_path(slot)))
                has_cue = self._slot_has_custom_cue(slot)
                parts: List[str] = []
                if slot.volume_override_pct is not None:
                    parts.append("V")
                if has_cue:
                    parts.append("C")
                if self._slot_has_custom_timecode(slot):
                    parts.append("T")
                for badge in self._active_button_trigger_badges(i, slot, sound_bindings, blocked_sound_tokens):
                    parts.append(badge)
                suffix = " ".join(parts)
                button.setText(format_sound_button_label(slot.title, slot.duration_ms, suffix, self.title_char_limit))
                button.setToolTip(slot.notes.strip())
            color = self._slot_color(slot, i)
            text_color = self.sound_button_text_color
            has_volume_override = (slot.volume_override_pct is not None) and slot.assigned and (not slot.marker)
            has_cue = self._slot_has_custom_cue(slot) and slot.assigned and (not slot.marker)
            has_vocal_removed_track = bool(str(slot.vocal_removed_file or "").strip()) and slot.assigned and (not slot.marker)
            has_midi_hotkey = bool(normalize_midi_binding(slot.sound_midi_hotkey)) and slot.assigned and (not slot.marker)
            has_custom_timecode = self._slot_has_custom_timecode(slot) and slot.assigned and (not slot.marker)
            has_linked_lyric = bool(str(slot.lyric_file or "").strip()) and slot.assigned and (not slot.marker)
            indicator_colors: List[str] = []
            if has_cue:
                indicator_colors.append(self.state_colors["cue_indicator"])
            if has_volume_override:
                indicator_colors.append(self.state_colors["volume_indicator"])
            if has_vocal_removed_track:
                indicator_colors.append(self.state_colors["vocal_removed_indicator"])
            if has_linked_lyric:
                indicator_colors.append(self.state_colors["lyric_indicator"])
            if has_custom_timecode:
                indicator_colors.append(TIMECODE_SLOT_INDICATOR_COLOR)
            button.set_indicator_colors(
                self.state_colors["midi_indicator"] if has_midi_hotkey else None,
                indicator_colors,
            )
            slot_key = (self.current_group, self.current_page, i)
            if self._drag_target_slot_key == slot_key:
                border = "3px solid #2FCBFF"
            elif self._hotkey_selected_slot_key == (self._view_group_key(), self.current_page, i):
                border = "3px solid #FFE04A"
            else:
                border = "1px solid #94B8BA"
            button.setStyleSheet(
                "QPushButton{"
                f"background:{color};"
                f"color:{text_color};"
                f"font-size:10pt;font-weight:bold;border:{border};"
                "padding:4px;"
                "}"
            )
        self._refresh_vocal_removed_warning_banner()
        self._update_status_totals()
        try:
            self._refresh_launchpad_feedback(force=False)
        except Exception:
            pass

    def _refresh_vocal_removed_warning_banner(self) -> None:
        message = ""
        if self.play_vocal_removed_tracks and self.current_playing is not None:
            slot = self._slot_for_key(self.current_playing)
            if (
                slot is not None
                and slot.assigned
                and (not slot.marker)
                and (not str(slot.vocal_removed_file or "").strip())
            ):
                message = f"{tr('VOCAL REMOVED ENABLED:')} {tr('The currently playing song has no vocal removed track.')}"
        if self.play_vocal_removed_tracks and not message:
            slots = self.cue_page if self.cue_mode else self.data.get(self.current_group, [[]])[self.current_page]
            missing_count = sum(
                1
                for slot in slots
                if slot.assigned and (not slot.marker) and (not str(slot.vocal_removed_file or "").strip())
            )
            if missing_count:
                noun = tr("sound button") if missing_count == 1 else tr("sound buttons")
                message = (
                    f"{tr('VOCAL REMOVED ENABLED:')} "
                    f"{missing_count} {noun} {tr('on this page have no vocal removed track.')}"
                )
        self.vocal_removed_warning_banner.setText(message)
        self.vocal_removed_warning_banner.setVisible(bool(message))

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

    def _log_file_path(self) -> str:
        appdata = os.getenv("APPDATA")
        base = appdata if appdata else os.path.expanduser("~")
        log_dir = os.path.join(base, "pySSP")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "SportsSoundsProLog.txt")

    def _append_play_log(self, file_path: str) -> None:
        if not self.log_file_enabled or not file_path:
            return
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{stamp}\t{file_path}\n"
        try:
            with open(self._log_file_path(), "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass

    def _view_log_file(self) -> None:
        path = self._log_file_path()
        if not os.path.exists(path):
            QMessageBox.information(self, "View Log", f"No log file yet.\n{path}")
            return
        self._open_local_path(path, "View Log", "Could not open log file:")

    def _reset_all_played_state(self) -> None:
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot in self.data[group][page_index]:
                    slot.played = False
                    if slot.assigned:
                        slot.activity_code = "8"

    def _slot_color(self, slot: SoundButtonData, index: int) -> str:
        playing_key = (self._view_group_key(), self.current_page, index)
        if self._flash_slot_key == playing_key and time.monotonic() < self._flash_slot_until:
            return "#FFF36A"
        if slot.marker:
            if slot.custom_color:
                return slot.custom_color
            return self.state_colors["marker"]
        if slot.locked:
            return self.state_colors["locked"]
        if slot.missing or slot.load_failed:
            return self.state_colors["missing"]
        if playing_key in self._active_playing_keys:
            return self.state_colors["playing"]
        if slot.played:
            return self.state_colors["played"]
        if slot.highlighted:
            return self.state_colors["highlighted"]
        if slot.copied_to_cue:
            return self.state_colors["copied"]
        if slot.assigned:
            if slot.custom_color:
                return slot.custom_color
            return self.state_colors["assigned"]
        return self.state_colors["empty"]

    def _show_slot_menu(self, slot_index: int, pos) -> None:
        button = self.sound_buttons[slot_index]
        page = self._current_page_slots()
        slot = page[slot_index]
        page_created = self._is_page_created(self.current_group, self.current_page)
        if (self._view_group_key(), self.current_page, slot_index) in self._active_playing_keys:
            # Keep direct right-click -> popup behavior, but defer by one event
            # turn so the context-menu/mouse sequence can fully unwind.
            button.setDown(False)
            QTimer.singleShot(0, lambda s=slot: self._open_playback_volume_dialog(s))
            return

        menu = QMenu(self)
        is_unused = (not slot.assigned) and (not slot.marker) and (not slot.title.strip()) and (not slot.notes.strip())

        if not page_created:
            blank_action = menu.addAction(tr("This page has not been created yet."))
            blank_action.setEnabled(False)
            guidance_action = menu.addAction(tr("Please add a page first."))
            guidance_action.setEnabled(False)
            detail_action = menu.addAction(tr("Then you can add sound buttons."))
            detail_action.setEnabled(False)
            menu.exec_(button.mapToGlobal(pos))
            return

        if is_unused:
            add_action = menu.addAction(tr("Add Sound Button"))
            add_action.setEnabled(page_created)
            edit_action = menu.addAction(tr("Edit Sound Button"))
            edit_action.setEnabled(page_created)
            marker_action = menu.addAction(tr("Insert Place Marker"))
            marker_action.setEnabled(page_created)
            paste_action = menu.addAction(tr("Paste Sound Button"))
            paste_action.setEnabled(self._copied_slot_buffer is not None and page_created and not slot.locked)
            self._apply_strike_to_disabled_menu_actions(menu)
            selected = menu.exec_(button.mapToGlobal(pos))
            if selected == add_action:
                self._pick_sound(slot_index)
            elif selected == edit_action:
                self._edit_sound_button(slot_index)
            elif selected == marker_action:
                self._insert_place_marker(slot_index)
            elif selected == paste_action:
                if self._copied_slot_buffer is not None:
                    page[slot_index] = self._clone_slot(self._copied_slot_buffer)
                    self._set_dirty(True)
            self._refresh_page_list()
            self._refresh_sound_grid()
            return

        if slot.marker:
            edit_marker_action = menu.addAction(tr("Edit Place Marker"))
            copy_action = menu.addAction(tr("Copy Sound Button"))
            copy_action.setEnabled(True)
            paste_action = menu.addAction(tr("Paste Sound Button"))
            paste_action.setEnabled(self._copied_slot_buffer is not None and page_created and not slot.locked)
            change_color_action = menu.addAction(tr("Change Colour"))
            remove_color_action = menu.addAction(tr("Remove Colour"))
            remove_color_action.setEnabled(bool(slot.custom_color))
            delete_action = menu.addAction(tr("Delete"))
            self._apply_strike_to_disabled_menu_actions(menu)
            selected = menu.exec_(button.mapToGlobal(pos))
            if selected == edit_marker_action:
                self._edit_place_marker(slot_index)
            elif selected == copy_action:
                self._copied_slot_buffer = self._clone_slot(slot)
            elif selected == paste_action:
                if self._copied_slot_buffer is not None:
                    page[slot_index] = self._clone_slot(self._copied_slot_buffer)
                    self._set_dirty(True)
            elif selected == change_color_action:
                current = slot.custom_color or "#C0C0C0"
                color = QColorDialog.getColor(QColor(current), self, "Button Colour")
                if color.isValid():
                    slot.custom_color = color.name().upper()
                    self._set_dirty(True)
            elif selected == remove_color_action:
                slot.custom_color = None
                self._set_dirty(True)
            elif selected == delete_action:
                if self._confirm_delete_button():
                    page[slot_index] = SoundButtonData()
                    self._set_dirty(True)
            self._refresh_page_list()
            self._refresh_sound_grid()
            return

        cue_it_action = menu.addAction(tr("Cue It"))
        cue_it_action.setEnabled(slot.assigned and not self.cue_mode)
        edit_action = menu.addAction(tr("Edit Sound Button"))
        edit_action.setEnabled(page_created)
        cue_points_action = menu.addAction(tr("Set Cue Points..."))
        cue_points_action.setEnabled(slot.assigned)
        lyric_editor_action = menu.addAction(tr("Lyric Editor..."))
        lyric_editor_action.setEnabled(slot.assigned)
        reveal_sound_file_action = None
        reveal_lyric_file_action = None
        lyric_linked = bool(str(slot.lyric_file or "").strip())
        if lyric_linked:
            reveal_menu = menu.addMenu(tr("Reveal File in File Browser"))
            reveal_sound_file_action = reveal_menu.addAction(tr("Sound"))
            reveal_lyric_file_action = reveal_menu.addAction(tr("Lyric"))
            reveal_sound_file_action.setEnabled(bool(str(slot.file_path or "").strip()))
            reveal_lyric_file_action.setEnabled(bool(str(slot.lyric_file or "").strip()))
        else:
            reveal_sound_file_action = menu.addAction(tr("Reveal Sound File in File Browser"))
            reveal_sound_file_action.setEnabled(bool(str(slot.file_path or "").strip()))
        timecode_setup_action = menu.addAction(tr("Timecode Setup..."))
        timecode_setup_action.setEnabled(slot.assigned)
        copy_action = menu.addAction(tr("Copy Sound Button"))
        copy_action.setEnabled(slot.assigned or bool(slot.title.strip()) or bool(slot.notes.strip()))
        paste_action = menu.addAction(tr("Paste Sound Button"))
        paste_action.setEnabled(self._copied_slot_buffer is not None and page_created and not slot.locked)
        menu.addSeparator()
        highlight_action = menu.addAction(tr("Highlight Off") if slot.highlighted else tr("Highlight On"))
        lock_action = menu.addAction(tr("Lock Off") if slot.locked else tr("Lock On"))
        played_action = menu.addAction(
            tr("Mark as Played (Red) Off") if slot.played else tr("Mark as Played (Red) On")
        )
        color_action = menu.addAction(tr("Change Button Colour"))
        clear_color_action = menu.addAction(tr("Clear Button Colour"))
        clear_color_action.setEnabled(bool(slot.custom_color))
        delete_action = menu.addAction(tr("Delete Button"))
        delete_action.setEnabled(slot.assigned or bool(slot.title.strip()) or bool(slot.notes.strip()))

        self._apply_strike_to_disabled_menu_actions(menu)
        selected = menu.exec_(button.mapToGlobal(pos))
        if selected == cue_it_action:
            self._cue_slot(slot)
        elif selected == edit_action:
            self._edit_sound_button(slot_index)
        elif selected == cue_points_action:
            self._edit_slot_cue_points(slot_index)
        elif selected == lyric_editor_action:
            self._edit_slot_lyric(slot_index)
        elif selected == reveal_sound_file_action:
            self._reveal_sound_file_in_browser(slot.file_path)
        elif selected == reveal_lyric_file_action:
            self._reveal_sound_file_in_browser(slot.lyric_file)
        elif selected == timecode_setup_action:
            self._edit_slot_timecode_setup(slot_index)
        elif selected == copy_action:
            self._copied_slot_buffer = self._clone_slot(slot)
        elif selected == paste_action:
            if self._copied_slot_buffer is not None:
                page[slot_index] = self._clone_slot(self._copied_slot_buffer)
                self._set_dirty(True)
        elif selected == highlight_action:
            slot.highlighted = not slot.highlighted
            self._set_dirty(True)
        elif selected == lock_action:
            slot.locked = not slot.locked
            self._set_dirty(True)
        elif selected == played_action:
            slot.played = not slot.played
            slot.activity_code = "2" if slot.played else "8"
            self._set_dirty(True)
        elif selected == color_action:
            current = slot.custom_color or "#C0C0C0"
            color = QColorDialog.getColor(QColor(current), self, "Button Colour")
            if color.isValid():
                slot.custom_color = color.name().upper()
                self._set_dirty(True)
        elif selected == clear_color_action:
            slot.custom_color = None
            self._set_dirty(True)
        elif selected == delete_action:
            if self._confirm_delete_button():
                page[slot_index] = SoundButtonData()
                self._set_dirty(True)

        self._refresh_page_list()
        self._refresh_sound_grid()

    def _is_button_drag_enabled(self) -> bool:
        btn = self.control_buttons.get("Button Drag")
        return bool(btn and btn.isChecked())

    def _toggle_button_drag_mode(self, checked: bool) -> None:
        btn = self.control_buttons.get("Button Drag")
        if btn:
            btn.setChecked(checked)
        if checked and self._is_playback_in_progress():
            if btn:
                btn.setChecked(False)
            self._update_button_drag_visual_state()
            return
        if not checked:
            self._drag_source_key = None
            self._clear_sound_button_drop_target()
            self._page_drag_source_key = None
            self._page_drag_start_pos = None
        self._sync_preload_pause_state(self._is_playback_in_progress())
        self._update_button_drag_visual_state()

    def _on_sound_button_clicked(self, slot_index: int) -> None:
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        if not self._is_button_drag_enabled():
            self._play_slot(slot_index)
            return
        # In drag mode, click does not play; dragging handles move operations.
        return

    def _can_accept_sound_button_drop(self, mime_data: QMimeData) -> bool:
        return self._is_button_drag_enabled() and mime_data.hasFormat("application/x-pyssp-slot")

    def _can_accept_page_button_drop(self, mime_data: QMimeData) -> bool:
        return self._is_button_drag_enabled() and mime_data.hasFormat("application/x-pyssp-page")

    def _build_drag_mime(self, slot_key: Tuple[str, int, int]) -> QMimeData:
        mime = QMimeData()
        mime.setData(
            "application/x-pyssp-slot",
            f"{slot_key[0]}|{slot_key[1]}|{slot_key[2]}".encode("utf-8"),
        )
        return mime

    def _build_page_drag_mime(self, page_key: Tuple[str, int]) -> QMimeData:
        mime = QMimeData()
        mime.setData(
            "application/x-pyssp-page",
            f"{page_key[0]}|{page_key[1]}".encode("utf-8"),
        )
        return mime

    def _parse_drag_mime(self, mime_data: QMimeData) -> Optional[Tuple[str, int, int]]:
        if not mime_data.hasFormat("application/x-pyssp-slot"):
            return None
        raw = bytes(mime_data.data("application/x-pyssp-slot")).decode("utf-8", errors="ignore")
        parts = raw.split("|")
        if len(parts) != 3:
            return None
        group = parts[0].strip().upper()
        if group not in GROUPS:
            return None
        try:
            page = int(parts[1])
            slot = int(parts[2])
        except ValueError:
            return None
        if page < 0 or page >= PAGE_COUNT or slot < 0 or slot >= SLOTS_PER_PAGE:
            return None
        return (group, page, slot)

    def _parse_page_drag_mime(self, mime_data: QMimeData) -> Optional[Tuple[str, int]]:
        if not mime_data.hasFormat("application/x-pyssp-page"):
            return None
        raw = bytes(mime_data.data("application/x-pyssp-page")).decode("utf-8", errors="ignore")
        parts = raw.split("|")
        if len(parts) != 2:
            return None
        group = parts[0].strip().upper()
        if group not in GROUPS:
            return None
        try:
            page = int(parts[1])
        except ValueError:
            return None
        if page < 0 or page >= PAGE_COUNT:
            return None
        return (group, page)

    def _start_sound_button_drag(self, slot_index: int) -> None:
        if not self._is_button_drag_enabled() or self.cue_mode:
            return
        source_key = (self.current_group, self.current_page, slot_index)
        if not self._is_page_created(source_key[0], source_key[1]):
            return
        source_slot = self.data[source_key[0]][source_key[1]][source_key[2]]
        if source_key in self._active_playing_keys:
            self._show_info_notice_banner("Cannot drag a currently playing button.")
            return
        if source_slot.locked or source_slot.marker or (not source_slot.assigned and not source_slot.title):
            return
        drag = QDrag(self.sound_buttons[slot_index])
        drag.setMimeData(self._build_drag_mime(source_key))
        drag.setPixmap(self.sound_buttons[slot_index].grab())
        drag.setHotSpot(self.sound_buttons[slot_index].rect().center())
        drag.exec_(Qt.MoveAction)
        self._clear_sound_button_drop_target()

    def _set_sound_button_drop_target(self, slot_index: Optional[int]) -> None:
        if (
            slot_index is None
            or (not self._is_button_drag_enabled())
            or self.cue_mode
            or slot_index < 0
            or slot_index >= SLOTS_PER_PAGE
        ):
            target = None
        else:
            target = (self.current_group, self.current_page, int(slot_index))
        if target == self._drag_target_slot_key:
            return
        self._drag_target_slot_key = target
        self._refresh_sound_grid()

    def _clear_sound_button_drop_target(self) -> None:
        if self._drag_target_slot_key is None:
            return
        self._drag_target_slot_key = None
        self._refresh_sound_grid()

    def _start_page_button_drag(self, source_page_index: int) -> None:
        if not self._is_button_drag_enabled() or self.cue_mode:
            return
        if source_page_index < 0 or source_page_index >= PAGE_COUNT:
            return
        source_key = (self.current_group, source_page_index)
        self._page_drag_source_key = source_key
        if not self._is_page_created(source_key[0], source_key[1]):
            return
        if self._page_has_active_playing_slot(source_key[0], source_key[1]):
            self._show_info_notice_banner("Cannot drag currently playing pages.")
            return
        drag = QDrag(self.page_list.viewport())
        drag.setMimeData(self._build_page_drag_mime(source_key))
        source_item = self.page_list.item(source_page_index)
        if source_item is not None:
            source_rect = self.page_list.visualItemRect(source_item)
            if source_rect.isValid() and (not source_rect.isEmpty()):
                drag.setPixmap(self.page_list.viewport().grab(source_rect))
                drag.setHotSpot(source_rect.center() - source_rect.topLeft())
        drag.exec_(Qt.MoveAction)

    def _handle_drag_over_group(self, group: str) -> None:
        if not self._is_button_drag_enabled() or self.cue_mode:
            return
        if group not in GROUPS:
            return
        if group == self.current_group:
            return
        self._select_group(group)

    def _handle_drag_over_page(self, page_index: int, require_created: bool = True) -> bool:
        if not self._is_button_drag_enabled() or self.cue_mode:
            return False
        if page_index < 0 or page_index >= PAGE_COUNT:
            return False
        if require_created and (not self._is_page_created(self.current_group, page_index)):
            return False
        if page_index == self.current_page:
            return True
        self._select_page(page_index)
        return True

    def _handle_sound_button_drop(self, dest_slot_index: int, mime_data: QMimeData) -> bool:
        source_key = self._parse_drag_mime(mime_data)
        if source_key is None:
            return False
        if self.cue_mode:
            return False
        dest_key = (self.current_group, self.current_page, dest_slot_index)
        if dest_key == source_key:
            return False
        if not self._is_page_created(dest_key[0], dest_key[1]):
            self._show_info_notice_banner("Cannot drag into a blank page.")
            return False
        if source_key in self._active_playing_keys or dest_key in self._active_playing_keys:
            self._show_info_notice_banner("Cannot drag currently playing buttons.")
            return False

        source_slot = self.data[source_key[0]][source_key[1]][source_key[2]]
        dest_slot = self.data[dest_key[0]][dest_key[1]][dest_key[2]]
        if source_slot.locked or source_slot.marker or (not source_slot.assigned and not source_slot.title):
            return False
        if dest_slot.locked:
            self._show_info_notice_banner("Destination button is locked.")
            return False

        source_clone = self._clone_slot(source_slot)
        dest_has_content = bool(dest_slot.assigned or dest_slot.title)
        if not dest_has_content:
            self.data[dest_key[0]][dest_key[1]][dest_key[2]] = source_clone
            self.data[source_key[0]][source_key[1]][source_key[2]] = SoundButtonData()
        else:
            box = QMessageBox(self)
            box.setWindowTitle("Button Drag")
            box.setText("Destination has content.")
            replace_btn = box.addButton("Replace", QMessageBox.AcceptRole)
            swap_btn = box.addButton("Swap", QMessageBox.ActionRole)
            cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
            box.exec_()
            clicked = box.clickedButton()
            if clicked == cancel_btn or clicked is None:
                return False
            if clicked == replace_btn:
                self.data[dest_key[0]][dest_key[1]][dest_key[2]] = source_clone
                self.data[source_key[0]][source_key[1]][source_key[2]] = SoundButtonData()
            elif clicked == swap_btn:
                dest_clone = self._clone_slot(dest_slot)
                self.data[dest_key[0]][dest_key[1]][dest_key[2]] = source_clone
                self.data[source_key[0]][source_key[1]][source_key[2]] = dest_clone
            else:
                return False

        self._set_dirty(True)
        self._refresh_page_list()
        self._refresh_sound_grid()
        return True

    def _page_has_active_playing_slot(self, group: str, page_index: int) -> bool:
        for key in self._active_playing_keys:
            if key[0] == group and key[1] == page_index:
                return True
        return False

    def _capture_page_payload(self, group: str, page_index: int) -> dict:
        return {
            "slots": [self._clone_slot(slot) for slot in self.data[group][page_index]],
            "page_name": self.page_names[group][page_index],
            "page_color": self.page_colors[group][page_index],
            "playlist_enabled": bool(self.page_playlist_enabled[group][page_index]),
            "shuffle_enabled": bool(self.page_shuffle_enabled[group][page_index]),
        }

    def _apply_page_payload(self, group: str, page_index: int, payload: dict) -> None:
        self.data[group][page_index] = [self._clone_slot(slot) for slot in payload.get("slots", [])]
        if len(self.data[group][page_index]) < SLOTS_PER_PAGE:
            self.data[group][page_index].extend(SoundButtonData() for _ in range(SLOTS_PER_PAGE - len(self.data[group][page_index])))
        self.page_names[group][page_index] = str(payload.get("page_name", ""))
        self.page_colors[group][page_index] = payload.get("page_color")
        self.page_playlist_enabled[group][page_index] = bool(payload.get("playlist_enabled", False))
        self.page_shuffle_enabled[group][page_index] = bool(payload.get("shuffle_enabled", False))

    def _clear_page_payload(self, group: str, page_index: int) -> None:
        self.data[group][page_index] = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self.page_names[group][page_index] = ""
        self.page_colors[group][page_index] = None
        self.page_playlist_enabled[group][page_index] = False
        self.page_shuffle_enabled[group][page_index] = False

    def _handle_page_button_drop(self, dest_page_index: int, mime_data: QMimeData) -> bool:
        source_key = self._parse_page_drag_mime(mime_data)
        if source_key is None:
            return False
        if self.cue_mode:
            return False
        if dest_page_index < 0 or dest_page_index >= PAGE_COUNT:
            return False
        dest_key = (self.current_group, dest_page_index)
        if source_key == dest_key:
            return False
        if not self._is_page_created(source_key[0], source_key[1]):
            return False
        if self._page_has_active_playing_slot(source_key[0], source_key[1]) or self._page_has_active_playing_slot(
            dest_key[0], dest_key[1]
        ):
            self._show_info_notice_banner("Cannot drag currently playing pages.")
            return False

        source_payload = self._capture_page_payload(source_key[0], source_key[1])
        dest_has_content = self._is_page_created(dest_key[0], dest_key[1])
        if not dest_has_content:
            self._apply_page_payload(dest_key[0], dest_key[1], source_payload)
            self._clear_page_payload(source_key[0], source_key[1])
        else:
            box = QMessageBox(self)
            box.setWindowTitle("Page Drag")
            box.setText("Destination has content.")
            replace_btn = box.addButton("Replace", QMessageBox.AcceptRole)
            swap_btn = box.addButton("Swap", QMessageBox.ActionRole)
            cancel_btn = box.addButton("Cancel", QMessageBox.RejectRole)
            box.exec_()
            clicked = box.clickedButton()
            if clicked == cancel_btn or clicked is None:
                return False
            if clicked == replace_btn:
                self._apply_page_payload(dest_key[0], dest_key[1], source_payload)
                self._clear_page_payload(source_key[0], source_key[1])
            elif clicked == swap_btn:
                dest_payload = self._capture_page_payload(dest_key[0], dest_key[1])
                self._apply_page_payload(dest_key[0], dest_key[1], source_payload)
                self._apply_page_payload(source_key[0], source_key[1], dest_payload)
            else:
                return False

        self.current_group = dest_key[0]
        self.current_page = dest_key[1]
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self.current_playlist_start = None
        self._set_dirty(True)
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        return True

    def _insert_place_marker(self, slot_index: int) -> None:
        page = self._current_page_slots()
        note_text, ok = QInputDialog.getText(self, "Insert Place Marker", "Enter page note text:")
        if not ok:
            return
        note = note_text.strip()
        if not note:
            self._show_info_notice_banner("Page note text is required.")
            return
        page[slot_index] = SoundButtonData(
            title=note,
            marker=True,
            activity_code="7",
        )
        self._set_dirty(True)

    def _edit_place_marker(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        note_text, ok = QInputDialog.getText(self, "Edit Place Marker", "Page note text:", text=slot.title)
        if not ok:
            return
        note = note_text.strip()
        if not note:
            self._show_info_notice_banner("Page note text is required.")
            return
        slot.title = note
        slot.activity_code = "7"
        slot.marker = True
        self._set_dirty(True)

    def _confirm_delete_button(self) -> bool:
        answer = QMessageBox.question(
            self,
            "Delete Button",
            "Delete this button?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def _clone_slot(self, slot: SoundButtonData) -> SoundButtonData:
        return SoundButtonData(
            file_path=slot.file_path,
            vocal_removed_file=slot.vocal_removed_file,
            title=slot.title,
            notes=slot.notes,
            lyric_file=slot.lyric_file,
            duration_ms=slot.duration_ms,
            custom_color=slot.custom_color,
            highlighted=slot.highlighted,
            played=slot.played,
            activity_code=slot.activity_code,
            locked=slot.locked,
            marker=slot.marker,
            copied_to_cue=slot.copied_to_cue,
            load_failed=slot.load_failed,
            volume_override_pct=slot.volume_override_pct,
            cue_start_ms=slot.cue_start_ms,
            cue_end_ms=slot.cue_end_ms,
            timecode_offset_ms=slot.timecode_offset_ms,
            timecode_timeline_mode=slot.timecode_timeline_mode,
            sound_hotkey=slot.sound_hotkey,
            sound_midi_hotkey=slot.sound_midi_hotkey,
        )

    def _edit_sound_button(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            self._show_info_notice_banner("This sound button is locked.")
            return
        slot_key = (self._view_group_key(), self.current_page, slot_index)
        start_dir = self.settings.last_sound_dir or self.settings.last_open_dir or ""
        file_path = slot.file_path
        caption = slot.title
        notes = slot.notes
        vocal_removed_file = slot.vocal_removed_file
        lyric_file = slot.lyric_file
        volume_override_pct = slot.volume_override_pct
        sound_hotkey = slot.sound_hotkey
        sound_midi_hotkey = slot.sound_midi_hotkey
        while True:
            dialog = EditSoundButtonDialog(
                file_path=file_path,
                caption=caption,
                notes=notes,
                vocal_removed_file=vocal_removed_file,
                lyric_file=lyric_file,
                volume_override_pct=volume_override_pct,
                sound_hotkey=sound_hotkey,
                sound_midi_hotkey=sound_midi_hotkey,
                available_midi_input_devices=list_midi_input_devices(),
                selected_midi_input_device_ids=self.midi_input_device_ids,
                start_dir=start_dir,
                language=self.ui_language,
                parent=self,
            )
            self._midi_context_handler = dialog
            self._midi_context_block_actions = True
            result_code = dialog.exec_()
            self._midi_context_handler = None
            self._midi_context_block_actions = False
            (
                file_path,
                caption,
                notes,
                vocal_removed_file,
                lyric_file,
                volume_override_pct,
                sound_hotkey,
                sound_midi_hotkey,
            ) = dialog.values()
            if result_code == EditSoundButtonDialog.REGENERATE_RESULT:
                generated_path = self._generate_vocal_removed_file_for_slot(file_path, vocal_removed_file)
                if generated_path:
                    vocal_removed_file = generated_path
                continue
            if result_code != QDialog.Accepted:
                return
            break
        if not file_path:
            self._show_info_notice_banner("File is required.")
            return
        file_path_reason = self._path_safety_reason(file_path)
        if file_path_reason:
            QMessageBox.warning(self, "Invalid File Path", f"Sound file path rejected.\n\n{file_path_reason}")
            return
        lyric_path_reason = self._path_safety_reason(lyric_file) if lyric_file else None
        if lyric_path_reason:
            QMessageBox.warning(self, "Invalid File Path", f"Lyric file path rejected.\n\n{lyric_path_reason}")
            return
        vocal_removed_path_reason = self._path_safety_reason(vocal_removed_file) if vocal_removed_file else None
        if vocal_removed_path_reason:
            QMessageBox.warning(self, "Invalid File Path", f"Vocal removed file path rejected.\n\n{vocal_removed_path_reason}")
            return
        conflict = self._find_sound_hotkey_conflict(sound_hotkey, (self._view_group_key(), self.current_page, slot_index))
        if conflict is not None:
            QMessageBox.warning(
                self,
                "Sound Button Hot Key",
                f"Hot key {sound_hotkey} is already assigned to {self._format_button_key(conflict)}.",
            )
            return
        midi_conflict = self._find_sound_midi_hotkey_conflict(
            sound_midi_hotkey,
            (self._view_group_key(), self.current_page, slot_index),
        )
        if midi_conflict is not None:
            QMessageBox.warning(
                self,
                "Sound Button MIDI Hot Key",
                f"MIDI key {sound_midi_hotkey} is already assigned to {self._format_button_key(midi_conflict)}.",
            )
            return
        previous_file_path = slot.file_path
        self.settings.last_sound_dir = os.path.dirname(file_path)
        self._save_settings()
        slot.file_path = file_path
        slot.title = caption or os.path.splitext(os.path.basename(file_path))[0]
        slot.notes = notes
        slot.vocal_removed_file = vocal_removed_file
        slot.lyric_file = lyric_file
        slot.marker = False
        slot.played = False
        slot.activity_code = "8"
        slot.load_failed = False
        slot.volume_override_pct = volume_override_pct
        slot.sound_hotkey = self._parse_sound_hotkey(sound_hotkey)
        slot.sound_midi_hotkey = self._parse_sound_midi_hotkey(sound_midi_hotkey)
        if previous_file_path != file_path:
            slot.cue_start_ms = None
            slot.cue_end_ms = None
            slot.timecode_offset_ms = None
            slot.timecode_timeline_mode = "global"
        self._set_dirty(True)
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._apply_hotkeys()
        self._refresh_playing_slot_after_audio_path_change(slot_key)

    def _generate_vocal_removed_file_for_slot(self, file_path: str, current_output_path: str = "") -> str:
        source_path = str(file_path or "").strip()
        if not source_path:
            QMessageBox.warning(self, tr("Vocal Removal"), tr("Select a source audio file first."))
            return ""
        source_reason = self._path_safety_reason(source_path)
        if source_reason:
            QMessageBox.warning(self, tr("Invalid File Path"), f"Sound file path rejected.\n\n{source_reason}")
            return ""
        if not os.path.exists(source_path):
            QMessageBox.warning(self, tr("Missing File"), f"{tr('File not found:')}\n{source_path}")
            return ""
        cli_executable = str(find_bundled_spleeter_cli_executable() or "").strip()
        if not cli_executable or not os.path.exists(cli_executable):
            QMessageBox.warning(
                self,
                tr("Vocal Removal"),
                tr("spleeter-cli was not found. Build it first before generating a vocal removed track."),
            )
            return ""
        suggested_output = str(current_output_path or "").strip() or suggested_vocal_removed_output_path(source_path)
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Save Vocal Removed File"),
            suggested_output,
            tr("Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)"),
        )
        output_path = str(output_path or "").strip()
        if not output_path:
            return ""
        output_reason = self._path_safety_reason(output_path)
        if output_reason:
            QMessageBox.warning(self, tr("Invalid File Path"), f"Vocal removed file path rejected.\n\n{output_reason}")
            return ""
        if os.path.exists(output_path):
            overwrite = QMessageBox.question(
                self,
                tr("Overwrite File"),
                f"{tr('Overwrite existing file?')}\n{output_path}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if overwrite != QMessageBox.Yes:
                return ""
        try:
            generated_path = self._run_vocal_removed_cli(source_path, output_path, cli_executable)
        except Exception as exc:
            QMessageBox.warning(self, tr("Vocal Removal"), f"{tr('Could not generate vocal removal track.')}\n\n{exc}")
            return ""
        self.settings.last_sound_dir = os.path.dirname(source_path) or self.settings.last_sound_dir
        self._save_settings()
        if os.path.normcase(os.path.abspath(generated_path)) != os.path.normcase(os.path.abspath(output_path)):
            self._show_info_notice_banner(f"{tr('Vocal removed track generated:')} {generated_path}")
        else:
            self._show_info_notice_banner(tr("Vocal removed track generated."))
        return generated_path

    def _run_vocal_removed_cli(self, source_path: str, output_path: str, cli_executable: str) -> str:
        source_ext = os.path.splitext(source_path)[1].lower()
        output_ext = os.path.splitext(output_path)[1].lower()
        progress = QProgressDialog(tr("Generating vocal removed track..."), tr("Cancel"), 0, 0, self)
        progress.setWindowTitle(tr("Vocal Removal"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        process: Optional[subprocess.Popen[str]] = None
        stdout_text = ""
        stderr_text = ""
        try:
            with tempfile.TemporaryDirectory(prefix="pyssp_vocal_removal_") as temp_dir:
                temp_input_wav = source_path if source_ext == ".wav" else os.path.join(temp_dir, "input.wav")
                temp_output_wav = output_path if output_ext == ".wav" else os.path.join(temp_dir, "output.wav")
                if source_ext != ".wav":
                    self._ffmpeg_transcode_to_wav(source_path, temp_input_wav)
                stdout_log_path = os.path.join(temp_dir, "spleeter-cli-stdout.log")
                stderr_log_path = os.path.join(temp_dir, "spleeter-cli-stderr.log")
                command = [
                    cli_executable,
                    "--input",
                    temp_input_wav,
                    "--output",
                    temp_output_wav,
                ]
                popen_kwargs: dict = {
                    "stdout": None,
                    "stderr": None,
                    "stdin": subprocess.DEVNULL,
                }
                if os.name == "nt":
                    popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    try:
                        startup = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
                        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
                        startup.wShowWindow = 0
                        popen_kwargs["startupinfo"] = startup
                    except Exception:
                        pass
                with open(stdout_log_path, "w", encoding="utf-8", errors="replace") as stdout_fh, open(
                    stderr_log_path, "w", encoding="utf-8", errors="replace"
                ) as stderr_fh:
                    popen_kwargs["stdout"] = stdout_fh
                    popen_kwargs["stderr"] = stderr_fh
                    process = subprocess.Popen(command, **popen_kwargs)
                    while process.poll() is None:
                        QApplication.processEvents()
                        if progress.wasCanceled():
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except Exception:
                                process.kill()
                            raise RuntimeError("Cancelled.")
                        time.sleep(0.05)
                try:
                    with open(stdout_log_path, "r", encoding="utf-8", errors="replace") as fh:
                        stdout_text = fh.read()
                except Exception:
                    stdout_text = ""
                try:
                    with open(stderr_log_path, "r", encoding="utf-8", errors="replace") as fh:
                        stderr_text = fh.read()
                except Exception:
                    stderr_text = ""
                if process.returncode != 0:
                    detail = (stderr_text or stdout_text or f"spleeter-cli exited with code {process.returncode}").strip()
                    raise RuntimeError(detail)
                if not os.path.exists(temp_output_wav):
                    raise RuntimeError("spleeter-cli completed but no output file was produced.")
                if output_ext == ".wav":
                    if os.path.normcase(os.path.abspath(temp_output_wav)) != os.path.normcase(os.path.abspath(output_path)):
                        shutil.copyfile(temp_output_wav, output_path)
                    return output_path
                self._ffmpeg_transcode_from_wav(temp_output_wav, output_path)
                if not os.path.exists(output_path):
                    raise RuntimeError("ffmpeg completed but the requested output file was not produced.")
                return output_path
        finally:
            progress.close()
        if process is None:
            raise RuntimeError("Failed to start spleeter-cli.")
        detail = (stderr_text or stdout_text or "spleeter-cli did not complete successfully.").strip()
        raise RuntimeError(detail)

    def _ffmpeg_transcode_to_wav(self, source_path: str, output_wav_path: str) -> None:
        ffmpeg_path = str(get_ffmpeg_executable() or "").strip()
        if not ffmpeg_path:
            raise RuntimeError("ffmpeg is required to decode this source file to WAV.")
        self._run_ffmpeg_audio_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                source_path,
                "-vn",
                "-sn",
                "-dn",
                "-ac",
                "2",
                "-ar",
                "44100",
                "-c:a",
                "pcm_s16le",
                output_wav_path,
            ]
        )

    def _ffmpeg_transcode_from_wav(self, source_wav_path: str, output_path: str) -> None:
        ffmpeg_path = str(get_ffmpeg_executable() or "").strip()
        if not ffmpeg_path:
            raise RuntimeError("ffmpeg is required to encode the generated WAV to the requested output format.")
        ext = os.path.splitext(output_path)[1].lower()
        codec_flags = list(FFMPEG_AUDIO_CODEC_FLAGS.get(ext, []))
        if ext in LOSSY_AUDIO_EXTENSIONS and not codec_flags:
            codec_flags = ["-c:a", "libmp3lame", "-q:a", "2"]
        if not codec_flags:
            raise RuntimeError(f"Unsupported vocal removed output format: {ext or '(no extension)'}")
        self._run_ffmpeg_audio_command(
            [
                ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                source_wav_path,
                *codec_flags,
                output_path,
            ]
        )

    def _run_ffmpeg_audio_command(self, command: List[str]) -> None:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode == 0:
            return
        detail = (completed.stderr or completed.stdout or "ffmpeg command failed").strip()
        raise RuntimeError(detail)

    def _refresh_playing_slot_after_audio_path_change(self, slot_key: Tuple[str, int, int]) -> None:
        player = self._player_for_slot_key(slot_key)
        if player is None:
            return
        slot = self._slot_for_key(slot_key)
        if slot is None:
            return
        target_path = str(self._effective_slot_file_path(slot) or "").strip()
        current_path = str(getattr(player, "_media_path", "") or "").strip()
        if not target_path or os.path.normcase(os.path.abspath(target_path)) == os.path.normcase(os.path.abspath(current_path)):
            return
        state = player.state()
        position_ms = max(0, int(player.position()))
        load_result = self._try_load_media(player, slot)
        if load_result is None:
            return
        if not load_result:
            return
        player.setPosition(position_ms)
        if state == ExternalMediaPlayer.PlayingState:
            player.play()
        elif state == ExternalMediaPlayer.PausedState:
            player.play()
            player.pause()

    def _find_sound_hotkey_conflict(
        self, sound_hotkey: str, ignore_slot_key: Optional[Tuple[str, int, int]] = None
    ) -> Optional[Tuple[str, int, int]]:
        token = self._parse_sound_hotkey(sound_hotkey)
        if not token:
            return None
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if ignore_slot_key == (group, page_index, slot_index):
                        continue
                    if not slot.assigned or slot.marker:
                        continue
                    if self._parse_sound_hotkey(slot.sound_hotkey) == token:
                        return (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            key = ("Q", 0, slot_index)
            if ignore_slot_key == key:
                continue
            if not slot.assigned or slot.marker:
                continue
            if self._parse_sound_hotkey(slot.sound_hotkey) == token:
                return key
        return None

    def _find_sound_midi_hotkey_conflict(
        self, sound_hotkey: str, ignore_slot_key: Optional[Tuple[str, int, int]] = None
    ) -> Optional[Tuple[str, int, int]]:
        token = self._parse_sound_midi_hotkey(sound_hotkey)
        if not token:
            return None
        selector, message = split_midi_binding(token)

        def _matches(existing: str) -> bool:
            existing_selector, existing_message = split_midi_binding(existing)
            if not existing_message or existing_message != message:
                return False
            return (not existing_selector) or (not selector) or (existing_selector == selector)

        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if ignore_slot_key == (group, page_index, slot_index):
                        continue
                    if not slot.assigned or slot.marker:
                        continue
                    if _matches(self._parse_sound_midi_hotkey(slot.sound_midi_hotkey)):
                        return (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            key = ("Q", 0, slot_index)
            if ignore_slot_key == key:
                continue
            if not slot.assigned or slot.marker:
                continue
            if _matches(self._parse_sound_midi_hotkey(slot.sound_midi_hotkey)):
                return key
        return None

    def _edit_slot_cue_points(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            self._show_info_notice_banner("This sound button is locked.")
            return
        if not slot.assigned or slot.marker:
            return
        if self._is_playback_in_progress():
            self._show_info_notice_banner(tr("Stop playback before opening Set Cue Points."))
            return
        # Guard against transient stop/start events while the cue dialog initializes.
        self._timecode_event_guard_until = time.perf_counter() + 0.40
        dialog = CuePointDialog(
            file_path=slot.file_path,
            title=slot.title,
            cue_start_ms=slot.cue_start_ms,
            cue_end_ms=slot.cue_end_ms,
            stop_host_playback=self._hard_stop_all,
            language=self.ui_language,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        cue_start_ms, cue_end_ms = dialog.values()
        slot.cue_start_ms = cue_start_ms
        slot.cue_end_ms = cue_end_ms
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _edit_slot_lyric(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            self._show_info_notice_banner("This sound button is locked.")
            return
        if not slot.assigned or slot.marker:
            return
        if self._is_playback_in_progress():
            self._show_info_notice_banner(tr("Stop playback before opening Lyric Editor."))
            return

        lyric_path = str(slot.lyric_file or "").strip()
        skipped_linking_found_lyric = False
        if not lyric_path:
            candidates, cancelled = self._scan_lyric_candidates_with_progress(
                [slot.file_path],
                title="Lyric Link Scan",
                label_prefix="Scanning",
            )
            found_candidate = bool(candidates and str(candidates[0] or "").strip())
            if cancelled:
                linked = None
            else:
                linked = self._prompt_lyric_link_selection([slot.file_path], precomputed_candidates=candidates)
            if linked is None:
                linked_path = ""
                skipped_linking_found_lyric = found_candidate
            else:
                linked_path = str(linked[0] if linked else "").strip()
            if linked_path:
                slot.lyric_file = linked_path
                lyric_path = linked_path
                self._set_dirty(True)
                self._refresh_sound_grid()
                self._refresh_lyric_display(force=True)
            else:
                lyric_path = ""
                skipped_linking_found_lyric = found_candidate
        if not lyric_path:
            question_text = (
                tr("You did not link a lyric. Create a lyric file now?")
                if skipped_linking_found_lyric
                else tr("This sound has no lyric linked. Create a lyric file now?")
            )
            answer = QMessageBox.question(
                self,
                tr("Lyric Editor"),
                question_text,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return
            default_ext = ".lrc" if self.new_lyric_file_format == "lrc" else ".srt"
            audio_dir = os.path.dirname(str(slot.file_path or "").strip()) or (self.settings.last_sound_dir or "")
            base_name = os.path.splitext(os.path.basename(str(slot.file_path or "").strip()))[0].strip() or "new_lyric"
            suggestion = os.path.join(audio_dir, f"{base_name}{default_ext}")
            if self.new_lyric_file_format == "lrc":
                lyric_filter = "LRC Files (*.lrc);;SRT Files (*.srt);;All Files (*.*)"
            else:
                lyric_filter = "SRT Files (*.srt);;LRC Files (*.lrc);;All Files (*.*)"
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                tr("Create Lyric File"),
                suggestion,
                lyric_filter,
            )
            save_path = str(save_path or "").strip()
            if not save_path:
                return
            ext = os.path.splitext(save_path)[1].lower()
            if ext not in {".srt", ".lrc"}:
                save_path = f"{save_path}{default_ext}"
            try:
                os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
                if not os.path.exists(save_path):
                    with open(save_path, "w", encoding="utf-8-sig", newline="") as fh:
                        fh.write("")
            except OSError as exc:
                QMessageBox.warning(self, tr("Lyric Editor"), f"{tr('Failed to create lyric file:')}\n{exc}")
                return
            slot.lyric_file = save_path
            lyric_path = save_path
            self._set_dirty(True)
            self._refresh_sound_grid()
        elif not os.path.exists(lyric_path):
            answer = QMessageBox.question(
                self,
                tr("Lyric Editor"),
                tr("Linked lyric file does not exist:\n{path}\n\nCreate this file now?").format(path=lyric_path),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return
            try:
                os.makedirs(os.path.dirname(lyric_path) or ".", exist_ok=True)
                with open(lyric_path, "w", encoding="utf-8-sig", newline="") as fh:
                    fh.write("")
            except OSError as exc:
                QMessageBox.warning(self, tr("Lyric Editor"), f"{tr('Failed to create lyric file:')}\n{exc}")
                return

        preferred_mode = "lrc" if os.path.splitext(lyric_path)[1].lower() == ".lrc" else "srt"
        dialog = LyricEditorDialog(
            lyric_path=lyric_path,
            audio_path=slot.file_path,
            title=slot.title,
            language=self.ui_language,
            preferred_mode=preferred_mode,
            cue_start_ms=slot.cue_start_ms,
            cue_end_ms=slot.cue_end_ms,
            stop_host_playback=self._hard_stop_all,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        self._refresh_lyric_display(force=True)
        self._refresh_stage_display()

    def _edit_slot_timecode_setup(self, slot_index: int) -> None:
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            self._show_info_notice_banner("This sound button is locked.")
            return
        if not slot.assigned or slot.marker:
            return
        dialog = TimecodeSetupDialog(
            offset_ms=slot.timecode_offset_ms,
            timeline_mode=slot.timecode_timeline_mode,
            fps=nominal_fps(self.timecode_fps),
            language=self.ui_language,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        timecode_offset_ms, timecode_timeline_mode = dialog.values()
        slot.timecode_offset_ms = timecode_offset_ms
        slot.timecode_timeline_mode = normalize_slot_timecode_timeline_mode(timecode_timeline_mode)
        self._set_dirty(True)
        self._refresh_sound_grid()
        self._refresh_timecode_panel()

    def _is_page_created(self, group: str, page_index: int) -> bool:
        if self.cue_mode:
            return True
        page_name = self.page_names[group][page_index].strip()
        if page_name:
            return True
        page = self.data[group][page_index]
        return any(slot.assigned or slot.title for slot in page)

    @staticmethod
    def _slot_is_available_for_add(slot: SoundButtonData) -> bool:
        return (
            (not slot.assigned)
            and (not slot.marker)
            and (not slot.locked)
            and (not slot.title.strip())
            and (not slot.notes.strip())
        )

    def _available_add_slot_indices(self, page: List[SoundButtonData], start_index: int) -> List[int]:
        return [index for index in range(start_index, SLOTS_PER_PAGE) if self._slot_is_available_for_add(page[index])]

    def _pick_sound(self, slot_index: int) -> None:
        if not self.cue_mode and not self._is_page_created(self.current_group, self.current_page):
            self._show_info_notice_banner("Create the page first before adding sound buttons.")
            return
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            self._show_info_notice_banner("This sound button is locked.")
            return

        start_dir = self.settings.last_sound_dir or self.settings.last_open_dir or ""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("Select Sound Files"),
            start_dir,
            self._audio_file_dialog_filter(),
        )
        if not file_paths:
            return
        available_slots = self._available_add_slot_indices(page, slot_index)
        available_count = len(available_slots)
        if available_count <= 0:
            self._show_info_notice_banner("No available sound button slots from this position.")
            return
        if len(file_paths) > available_count:
            file_paths = file_paths[:available_count]
            self._show_info_notice_banner(
                f"Only {available_count} available sound button slot(s). Extra selected files were skipped."
            )
        safe_paths: List[str] = []
        rejected_paths: List[str] = []
        for candidate in file_paths:
            reason = self._path_safety_reason(candidate)
            if reason:
                rejected_paths.append(f"{candidate} ({reason})")
                continue
            safe_paths.append(candidate)
        if rejected_paths:
            preview = "\n".join(rejected_paths[:4])
            suffix = "\n..." if len(rejected_paths) > 4 else ""
            QMessageBox.warning(
                self,
                "Invalid File Path",
                f"Skipped {len(rejected_paths)} file(s) with unsafe path values.\n\n{preview}{suffix}",
            )
        if not safe_paths:
            return
        file_paths = safe_paths
        if self.verify_sound_file_on_add:
            matches = self._verify_audio_files_before_add(file_paths)
            if matches:
                self._show_audio_add_verification_results(matches)
        if self.search_lyric_on_add_sound_button:
            lyric_links = self._prompt_lyric_link_selection(file_paths)
            if lyric_links is None:
                return
        else:
            lyric_links = ["" for _ in file_paths]
        lyric_links = [lyric_links[index] if index < len(lyric_links) else "" for index in range(len(file_paths))]
        self.settings.last_sound_dir = os.path.dirname(file_paths[0])
        self._save_settings()

        changed = False
        for file_idx, target_index in enumerate(available_slots):
            if file_idx >= len(file_paths):
                break
            target = page[target_index]
            file_path = file_paths[file_idx]
            target.file_path = file_path
            target.title = os.path.splitext(os.path.basename(file_path))[0]
            target.notes = ""
            target.lyric_file = lyric_links[file_idx] if file_idx < len(lyric_links) else ""
            target.duration_ms = 0
            target.custom_color = None
            target.marker = False
            target.played = False
            target.activity_code = "8"
            target.load_failed = False
            target.cue_start_ms = None
            target.cue_end_ms = None
            changed = True

        if changed:
            self._set_dirty(True)
            self._refresh_page_list()
            self._refresh_sound_grid()

    def _scan_lyric_candidates_with_progress(
        self,
        audio_files: List[str],
        *,
        title: str,
        label_prefix: str,
    ) -> Tuple[List[str], bool]:
        if not audio_files:
            return [], False
        progress = QProgressDialog("Scanning lyric files...", "Skip", 0, max(1, len(audio_files)), self)
        progress.setWindowTitle(title)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        candidates: List[str] = []
        cancelled = False
        for index, path in enumerate(audio_files):
            if progress.wasCanceled():
                cancelled = True
                break
            progress.setLabelText(f"{label_prefix} {os.path.basename(path)}...")
            candidates.append(self._find_matching_lyric_file(path))
            progress.setValue(index + 1)
            QApplication.processEvents()
        progress.close()
        return candidates, cancelled

    def _prompt_lyric_link_selection(
        self,
        audio_files: List[str],
        *,
        precomputed_candidates: Optional[List[str]] = None,
    ) -> Optional[List[str]]:
        if precomputed_candidates is None:
            candidates, cancelled = self._scan_lyric_candidates_with_progress(
                audio_files,
                title="Lyric Link Scan",
                label_prefix="Scanning",
            )
            if cancelled:
                candidates = [candidates[idx] if idx < len(candidates) else "" for idx in range(len(audio_files))]
                self._show_info_notice_banner("Lyric scan skipped. Showing partial scan results.")
        else:
            candidates = [precomputed_candidates[idx] if idx < len(precomputed_candidates) else "" for idx in range(len(audio_files))]
        if not any(candidates):
            return ["" for _ in audio_files]
        rows = list(zip(audio_files, candidates))
        dialog = LinkLyricDialog(rows, self)
        if dialog.exec_() != QDialog.Accepted:
            return None
        flags = dialog.link_flags()
        linked: List[str] = []
        for idx, candidate in enumerate(candidates):
            should_link = idx < len(flags) and bool(flags[idx])
            linked.append(candidate if (should_link and candidate) else "")
        return linked

    def _find_matching_lyric_file(self, audio_path: str) -> str:
        path = str(audio_path or "").strip()
        if not path:
            return ""
        directory = os.path.dirname(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        if not directory or not stem:
            return ""
        matches: List[str] = []
        try:
            for name in os.listdir(directory):
                base, ext = os.path.splitext(name)
                if base.casefold() != stem.casefold():
                    continue
                if ext.lower() not in {".lrc", ".srt"}:
                    continue
                full = os.path.join(directory, name)
                if os.path.isfile(full):
                    matches.append(full)
        except OSError:
            return ""
        if not matches:
            return ""
        matches.sort(key=lambda value: (0 if os.path.splitext(value)[1].lower() == ".lrc" else 1, value.casefold()))
        return matches[0]

    def _diagnose_slot_lyric_issue(self, slot: SoundButtonData) -> Optional[str]:
        linked_path = str(slot.lyric_file or "").strip()
        if not linked_path:
            return None
        if os.path.exists(linked_path):
            return None
        return "Linked lyric file path is missing."

    def _verify_slot(self, slot: SoundButtonData) -> None:
        if slot.missing:
            QMessageBox.warning(self, "Missing File", f"File not found:\n{slot.file_path}")
        else:
            self._show_info_notice_banner("Sound file exists.")

    def _slot_volume_pct(self, slot: SoundButtonData) -> int:
        if slot.volume_override_pct is None:
            return 75
        return max(0, min(100, int(slot.volume_override_pct)))

    def _parse_volume_override_pct(self, value: str) -> Optional[int]:
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError:
            return None
        return max(0, min(100, parsed))

    def _parse_sound_hotkey(self, value: str) -> str:
        raw = str(value or "").strip().upper()
        if not raw:
            return ""
        if raw.startswith("0"):
            raw = raw[1:]
        if re.fullmatch(r"F([1-9]|1[1-2])", raw):
            if raw == "F10":
                return ""
            return raw
        if re.fullmatch(r"[0-9]", raw):
            return raw
        if re.fullmatch(r"[A-OQ-Z]", raw):
            return raw
        return ""

    def _encode_sound_hotkey(self, value: str) -> str:
        token = self._parse_sound_hotkey(value)
        if not token:
            return ""
        return f"0{token}"

    def _parse_sound_midi_hotkey(self, value: str) -> str:
        return normalize_midi_binding(value)

    def _encode_sound_midi_hotkey(self, value: str) -> str:
        return self._parse_sound_midi_hotkey(value)

    def _parse_cue_points(self, start_value: str, end_value: str, duration_ms: int) -> tuple[Optional[int], Optional[int]]:
        fallback_units_per_ms = 176.4
        start_raw = self._parse_non_negative_int(start_value)
        end_raw = self._parse_non_negative_int(end_value)
        if start_raw is None and end_raw is None:
            return None, None

        start_ms = start_raw
        end_ms = end_raw
        if duration_ms > 0 and end_raw is not None and end_raw > max(duration_ms * 2, 600000):
            scale = duration_ms / float(end_raw)
            if start_raw is not None:
                start_ms = int(round(start_raw * scale))
            end_ms = duration_ms
        elif duration_ms > 0 and end_raw is None and start_raw is not None and start_raw > duration_ms:
            # Handle cs-only files where cue values are stored in SSP units.
            inferred_start_ms = int(round(start_raw / fallback_units_per_ms))
            if 0 <= inferred_start_ms <= duration_ms:
                start_ms = inferred_start_ms

        if start_ms is not None:
            start_ms = max(0, start_ms)
        if end_ms is not None:
            end_ms = max(0, end_ms)

        if duration_ms > 0:
            if start_ms is not None:
                start_ms = min(duration_ms, start_ms)
            if end_ms is not None:
                end_ms = min(duration_ms, end_ms)
        if start_ms is not None and end_ms is not None and end_ms < start_ms:
            end_ms = start_ms
        return start_ms, end_ms

    def _parse_non_negative_int(self, value: str) -> Optional[int]:
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError:
            return None
        if parsed < 0:
            return None
        return parsed

    def _normalized_slot_cues(self, slot: SoundButtonData, duration_ms: int) -> tuple[Optional[int], Optional[int]]:
        start_ms = slot.cue_start_ms
        end_ms = slot.cue_end_ms
        if start_ms is not None:
            start_ms = max(0, int(start_ms))
        if end_ms is not None:
            end_ms = max(0, int(end_ms))
        if duration_ms > 0:
            if start_ms is not None:
                start_ms = min(duration_ms, start_ms)
            if end_ms is not None:
                end_ms = min(duration_ms, end_ms)
        if start_ms is not None and end_ms is not None and end_ms < start_ms:
            end_ms = start_ms
        if start_ms == 0 and end_ms is None:
            start_ms = None
        return start_ms, end_ms

    def _slot_has_custom_cue(self, slot: SoundButtonData) -> bool:
        start_ms, end_ms = self._normalized_slot_cues(slot, max(0, int(slot.duration_ms)))
        return (end_ms is not None) or (start_ms is not None and start_ms > 0)

    def _slot_has_custom_timecode(self, slot: SoundButtonData) -> bool:
        mode = normalize_slot_timecode_timeline_mode(slot.timecode_timeline_mode)
        has_mode_override = mode in {"audio_file", "cue_region"}
        offset_ms = slot.timecode_offset_ms
        has_offset = offset_ms is not None and int(offset_ms) > 0
        return has_mode_override or has_offset

    def _build_slot_background_gradient(
        self,
        base_color: str,
        has_midi_hotkey: bool,
        indicator_colors: List[str],
    ) -> str:
        if not has_midi_hotkey and not indicator_colors:
            return base_color
        edge_eps = 0.0010
        top_height = 0.11 if has_midi_hotkey else 0.0
        bottom_count = len(indicator_colors)
        bottom_height = 0.17 if bottom_count == 1 else 0.12
        if (top_height + (bottom_height * bottom_count)) > 0.96 and bottom_count > 0:
            bottom_height = max(0.06, (0.96 - top_height) / float(bottom_count))
        main_start = top_height if has_midi_hotkey else 0.0
        main_end = 1.0 - (bottom_height * bottom_count)
        if main_end < main_start:
            main_end = main_start

        stops: List[Tuple[float, str]] = []
        if has_midi_hotkey:
            midi_color = self.state_colors["midi_indicator"]
            stops.append((0.0, midi_color))
            stops.append((top_height, midi_color))
            if top_height > 0.0:
                stops.append((max(0.0, top_height - edge_eps), midi_color))
            stops.append((top_height, base_color))
        stops.append((main_start, base_color))
        stops.append((main_end, base_color))

        cursor = main_end
        prev_color = base_color
        for color in indicator_colors:
            start = cursor
            end = min(1.0, start + bottom_height)
            if start > 0.0:
                stops.append((max(0.0, start - edge_eps), prev_color))
            stops.append((start, color))
            stops.append((end, color))
            prev_color = color
            cursor = end
        if cursor < 1.0:
            stops.append((max(0.0, 1.0 - edge_eps), prev_color))
            stops.append((1.0, prev_color))
        gradient_stops = ", ".join(
            f"stop:{max(0.0, min(1.0, pos)):.4f} {color}" for pos, color in stops
        )
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, {gradient_stops})"

    def _slot_ssp_unit_scale(self, slot: SoundButtonData) -> Optional[Tuple[int, int]]:
        file_path = (slot.file_path or "").strip()
        if not file_path:
            return None
        cached = self._ssp_unit_cache.get(file_path)
        if cached is not None:
            return cached
        try:
            duration_ms, total_units = get_media_ssp_units(file_path)
        except Exception:
            return None
        if duration_ms <= 0 or total_units <= 0:
            return None
        self._ssp_unit_cache[file_path] = (duration_ms, total_units)
        return self._ssp_unit_cache[file_path]

    def _normalize_cue_points(
        self, start_ms: Optional[int], end_ms: Optional[int], duration_ms: int
    ) -> tuple[Optional[int], Optional[int]]:
        if start_ms is not None:
            start_ms = max(0, int(start_ms))
        if end_ms is not None:
            end_ms = max(0, int(end_ms))
        if duration_ms > 0:
            if start_ms is not None:
                start_ms = min(duration_ms, start_ms)
            if end_ms is not None:
                end_ms = min(duration_ms, end_ms)
        if start_ms is not None and end_ms is not None and end_ms < start_ms:
            end_ms = start_ms
        return start_ms, end_ms

    def _parse_cue_time_string_to_ms(self, value: str) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        parts = text.split(":")
        if len(parts) == 2:
            mm, ss = parts
            if mm.isdigit() and ss.isdigit():
                return (int(mm) * 60 + int(ss)) * 1000
            return None
        if len(parts) == 3:
            first, second, third = parts
            if not (first.isdigit() and second.isdigit() and third.isdigit()):
                return None
            minutes = int(first)
            seconds = int(second)
            frames_or_seconds = int(third)
            if frames_or_seconds < 30:
                return ((minutes * 60) + seconds) * 1000 + int((frames_or_seconds / 30.0) * 1000)
            return (minutes * 3600 + seconds * 60 + frames_or_seconds) * 1000
        return None

    def _format_cue_time_string(self, ms: int) -> str:
        return format_clock_time(max(0, int(ms)))

    def _cue_time_fields_for_set(self, slot: SoundButtonData) -> tuple[Optional[str], Optional[str]]:
        start_ms, end_ms = self._normalized_slot_cues(slot, max(0, int(slot.duration_ms)))
        if start_ms is None and end_ms is None:
            return None, None
        cue_start = None if start_ms is None else self._format_cue_time_string(start_ms)
        cue_end = None if end_ms is None else self._format_cue_time_string(end_ms)
        return cue_start, cue_end

    def _cue_start_for_playback(self, slot: SoundButtonData, duration_ms: int) -> int:
        start_ms, _ = self._normalized_slot_cues(slot, duration_ms)
        return 0 if start_ms is None else max(0, int(start_ms))

    def _cue_end_for_playback(self, slot: SoundButtonData, duration_ms: int) -> Optional[int]:
        _, end_ms = self._normalized_slot_cues(slot, duration_ms)
        return None if end_ms is None else max(0, int(end_ms))

    def _main_transport_bounds(self, duration_ms: Optional[int] = None) -> tuple[int, int]:
        dur = self.current_duration_ms if duration_ms is None else max(0, int(duration_ms))
        if self.main_transport_timeline_mode == "audio_file":
            return 0, dur
        if self.current_playing is None:
            return 0, dur
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return 0, dur
        low = self._cue_start_for_playback(slot, dur)
        end = self._cue_end_for_playback(slot, dur)
        high = dur if end is None else end
        low = max(0, min(dur, low))
        high = max(0, min(dur, high))
        if high < low:
            high = low
        return low, high

    def _transport_total_ms(self) -> int:
        low, high = self._main_transport_bounds()
        return max(0, high - low)

    def _transport_display_ms_for_absolute(self, absolute_ms: int) -> int:
        low, high = self._main_transport_bounds()
        clamped = max(low, min(high, int(absolute_ms)))
        return max(0, clamped - low)

    def _transport_absolute_ms_for_display(self, display_ms: int) -> int:
        low, high = self._main_transport_bounds()
        total = max(0, high - low)
        rel = max(0, min(total, int(display_ms)))
        return low + rel

    def _clear_player_cue_behavior_override(self, player: ExternalMediaPlayer) -> None:
        pid = id(player)
        self._player_end_override_ms.pop(pid, None)
        self._player_ignore_cue_end.discard(pid)

    def _seek_player_to_slot_start_cue(self, player: ExternalMediaPlayer, slot: SoundButtonData) -> None:
        start_ms = self._cue_start_for_playback(slot, max(0, int(player.duration())))
        if start_ms > 0:
            player.setPosition(start_ms)

    def _apply_main_jog_outside_cue_behavior(self, absolute_pos_ms: int) -> None:
        self._clear_player_cue_behavior_override(self.player)
        if self.main_transport_timeline_mode != "audio_file":
            return
        if self.current_playing is None:
            return
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return
        duration_ms = max(0, int(self.player.duration()))
        cue_start = self._cue_start_for_playback(slot, duration_ms)
        cue_end = self._cue_end_for_playback(slot, duration_ms)
        if cue_end is None and cue_start <= 0:
            return
        pos = max(0, int(absolute_pos_ms))
        before_start = pos < cue_start
        after_stop = (cue_end is not None) and (pos > cue_end)
        if not (before_start or after_stop):
            return

        action = self.main_jog_outside_cue_action
        if action == "stop_immediately":
            self._stop_playback()
            return
        if action == "ignore_cue":
            self._player_ignore_cue_end.add(id(self.player))
            return
        if action == "next_cue_or_stop":
            if before_start:
                self._player_end_override_ms[id(self.player)] = cue_start
            else:
                self._player_ignore_cue_end.add(id(self.player))
            return
        if action == "stop_cue_or_end":
            if before_start:
                if cue_end is None:
                    self._player_ignore_cue_end.add(id(self.player))
                else:
                    self._player_end_override_ms[id(self.player)] = cue_end
            else:
                self._player_ignore_cue_end.add(id(self.player))
            return

    def _enforce_cue_end_limits(self) -> None:
        for player in [self.player, self.player_b, *list(self._multi_players)]:
            if player.state() != ExternalMediaPlayer.PlayingState:
                continue
            slot_key = self._player_slot_key_map.get(id(player))
            if slot_key is None:
                continue
            slot = self._slot_for_key(slot_key)
            if slot is None:
                continue
            pid = id(player)
            if pid in self._player_ignore_cue_end:
                continue
            end_ms = self._player_end_override_ms.get(pid)
            if end_ms is None:
                end_ms = self._cue_end_for_playback(slot, max(0, int(player.duration())))
            if end_ms is None:
                continue
            if player.position() < end_ms:
                continue
            if player is self.player:
                player.stop()
            else:
                self._stop_single_player(player)

    def _open_playback_volume_dialog(self, slot: SoundButtonData) -> None:
        if not slot.assigned or slot.marker:
            return
        original_override = slot.volume_override_pct
        original_slot_pct = self._slot_volume_pct(slot)
        is_current_slot = False
        if self.current_playing is not None:
            current_group, current_page, current_slot = self.current_playing
            if current_group == self._view_group_key() and current_page == self.current_page:
                current_slots = self._current_page_slots()
                if 0 <= current_slot < len(current_slots) and current_slots[current_slot] is slot:
                    is_current_slot = True

        dialog = QDialog(self)
        dialog.setWindowTitle("Adjust Volume Level")
        dialog.setModal(True)
        dialog.resize(420, 150)

        root = QVBoxLayout(dialog)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        value_label = QLabel("")
        root.addWidget(value_label)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(original_slot_pct)
        root.addWidget(slider)

        def _sync_label(value: int) -> None:
            value_label.setText(f"Playback Volume: {value}%")
            if is_current_slot:
                self._player_slot_volume_pct = max(0, min(100, int(value)))
                self._set_player_volume(self.player, self._effective_slot_target_volume(self._player_slot_volume_pct))

        _sync_label(slider.value())
        slider.valueChanged.connect(_sync_label)

        button_row = QHBoxLayout()
        remove_btn = QPushButton("Remove Volume Level")
        save_btn = QPushButton("Save Volume")
        cancel_btn = QPushButton("Cancel")
        button_row.addStretch(1)
        button_row.addWidget(remove_btn)
        button_row.addWidget(save_btn)
        button_row.addWidget(cancel_btn)
        root.addLayout(button_row)
        committed = {"value": False}

        def _remove() -> None:
            slot.volume_override_pct = None
            if is_current_slot:
                self._player_slot_volume_pct = 75
                self._set_player_volume(self.player, self._effective_slot_target_volume(self._player_slot_volume_pct))
            self._set_dirty(True)
            self._refresh_sound_grid()
            committed["value"] = True
            dialog.accept()

        def _save() -> None:
            value = max(0, min(100, slider.value()))
            slot.volume_override_pct = value
            if is_current_slot:
                self._player_slot_volume_pct = value
                self._set_player_volume(self.player, self._effective_slot_target_volume(self._player_slot_volume_pct))
            self._set_dirty(True)
            self._refresh_sound_grid()
            committed["value"] = True
            dialog.accept()

        def _on_finished(_result: int) -> None:
            if not committed["value"]:
                slot.volume_override_pct = original_override
                if is_current_slot:
                    self._player_slot_volume_pct = original_slot_pct
                    self._set_player_volume(self.player, self._effective_slot_target_volume(self._player_slot_volume_pct))
            self._recover_from_stuck_mouse_state()
            dialog.deleteLater()
            if getattr(self, "_active_playback_volume_dialog", None) is dialog:
                self._active_playback_volume_dialog = None

        remove_btn.clicked.connect(_remove)
        save_btn.clicked.connect(_save)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.finished.connect(_on_finished)
        existing = getattr(self, "_active_playback_volume_dialog", None)
        if existing is not None and existing is not dialog:
            try:
                existing.close()
            except Exception:
                pass
        self._active_playback_volume_dialog = dialog
        dialog.open()

    def _current_page_slots(self) -> List[SoundButtonData]:
        if self.cue_mode:
            return self.cue_page
        return self.data[self.current_group][self.current_page]

