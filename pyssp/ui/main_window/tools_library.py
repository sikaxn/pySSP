from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *
from pyssp.launchpad import (
    LAUNCHPAD_LAYOUT_BOTTOM_SIX,
    launchpad_layout_options,
    launchpad_page_bindings,
    launchpad_profile_label,
)


class ToolsLibraryMixin:
    def _apply_launchpad_mapping_to_current_page(self) -> None:
        slots = self._current_page_slots()
        assigned_slots = [slot for slot in slots if slot.assigned and (not slot.marker)]
        if not assigned_slots:
            self._show_info_notice_banner("No assigned sound buttons on the current page.")
            return

        layout_options = launchpad_layout_options()
        labels = [item.label for item in layout_options]
        default_index = 0
        selected_label, ok = QInputDialog.getItem(
            self,
            "Apply Launchpad MIDI Mapping",
            "Launchpad layout:",
            labels,
            default_index,
            False,
        )
        if not ok:
            return

        selected_layout = LAUNCHPAD_LAYOUT_BOTTOM_SIX
        for item in layout_options:
            if item.label == selected_label:
                selected_layout = item.key
                break

        page_label = "Cue Page" if self.cue_mode else self._page_display_name(self.current_group, self.current_page)
        answer = QMessageBox.question(
            self,
            "Apply Launchpad MIDI Mapping",
            f"Apply {launchpad_profile_label('programmer')} mapping to {page_label}?\n\n"
            "This replaces Sound Button MIDI Hot Key values on the current page.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        selected_inputs = [str(value).strip() for value in list(self.midi_input_device_ids or []) if str(value).strip()]
        selector = selected_inputs[0] if len(selected_inputs) == 1 else ""
        bindings = launchpad_page_bindings(layout=selected_layout, selector=selector)
        mapped_count = 0
        cleared_count = 0
        for index, slot in enumerate(slots[:48]):
            if slot.assigned and (not slot.marker):
                slot.sound_midi_hotkey = bindings[index]
                mapped_count += 1
            else:
                if str(slot.sound_midi_hotkey or "").strip():
                    cleared_count += 1
                slot.sound_midi_hotkey = ""

        self._set_dirty(True)
        self._refresh_sound_grid()
        self._show_save_notice_banner(
            f"Launchpad MIDI mapping applied to {page_label}: {mapped_count} button(s) mapped"
            f"{', ' + str(cleared_count) + ' cleared' if cleared_count else ''}."
        )

    def _sports_sounds_pro_folder(self) -> str:
        default_path = r"C:\SportsSoundsPro"
        if os.path.isdir(default_path):
            return default_path
        if self.current_set_path:
            return os.path.dirname(self.current_set_path)
        return os.path.join(os.path.expanduser("~"), "SportsSoundsPro")

    def _page_library_folder_path(self) -> str:
        return os.path.join(self._sports_sounds_pro_folder(), "PageLib")

    def _page_display_name(self, group: str, page_index: int) -> str:
        page_name = self.page_names[group][page_index].strip()
        if page_name:
            return f"{group}{page_index + 1} ({page_name})"
        return f"{group}{page_index + 1}"

    def _iter_all_sound_button_entries(self, include_cue: bool = True) -> List[dict]:
        entries: List[dict] = []
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    title = slot.title.strip() or os.path.splitext(os.path.basename(slot.file_path))[0]
                    entries.append(
                        {
                            "group": group,
                            "page": page_index,
                            "slot": slot_index,
                            "title": title,
                            "file_path": slot.file_path,
                            "location": self._page_display_name(group, page_index),
                        }
                    )
        if include_cue:
            for slot_index, slot in enumerate(self.cue_page):
                if not slot.assigned or slot.marker:
                    continue
                title = slot.title.strip() or os.path.splitext(os.path.basename(slot.file_path))[0]
                entries.append(
                    {
                        "group": "Q",
                        "page": 0,
                        "slot": slot_index,
                        "title": title,
                        "file_path": slot.file_path,
                        "location": "Cue Page",
                    }
                )
        return entries

    def _print_lines(self, title: str, lines: List[str]) -> None:
        text = "\n".join(lines).strip() or "(no items)"
        printer = QPrinter(QPrinter.HighResolution)
        printer.setDocName(title)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle(f"Print - {title}")
        if dialog.exec_() != QDialog.Accepted:
            return
        doc = QTextDocument()
        doc.setPlainText(text)
        doc.print_(printer)

    def _open_tool_window(
        self,
        key: str,
        title: str,
        double_click_action: str,
        show_play_button: bool,
    ) -> ToolListWindow:
        window = self._tool_windows.get(key)
        if window is not None:
            window.show()
            window.raise_()
            window.activateWindow()
            return window
        window = ToolListWindow(
            title=title,
            parent=self,
            double_click_action=double_click_action,
            show_play_button=show_play_button,
        )
        window.destroyed.connect(
            lambda _=None, k=key: (self._tool_windows.pop(k, None), self._tool_window_matches.pop(k, None))
        )
        self._tool_windows[key] = window
        return window

    def _tool_match_to_line(self, match: dict) -> str:
        line = (
            f"{match['location']} - Button {int(match['slot']) + 1}: "
            f"{match['title']} | {match['file_path']}"
        )
        cause = str(match.get("cause", "")).strip()
        if cause:
            return f"{line} | Cause: {cause}"
        return line

    def _tool_hotkey_match_to_line(self, match: dict) -> str:
        return (
            f"{match['location']} - Button {int(match['slot']) + 1}: "
            f"{match['sound_hotkey']} | {match['title']} | {match['file_path']}"
        )

    def _tool_midi_match_to_line(self, match: dict) -> str:
        return (
            f"{match['location']} - Button {int(match['slot']) + 1}: "
            f"{match['sound_midi_hotkey']} | {match['title']} | {match['file_path']}"
        )

    def _tool_export_matches(self, key: str, export_format: str, base_name: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        if not matches:
            QMessageBox.information(self, "Export", "No rows to export.")
            return
        export_format = "excel" if export_format == "excel" else "csv"
        ext = ".xls" if export_format == "excel" else ".csv"
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or self._sports_sounds_pro_folder()
        initial_path = os.path.join(start_dir, f"{base_name}{ext}")
        file_filter = "Excel (*.xls)" if export_format == "excel" else "CSV (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", initial_path, f"{file_filter};;All Files (*.*)")
        if not file_path:
            return
        if not file_path.lower().endswith(ext):
            file_path = f"{file_path}{ext}"
        header = "Page,Button Number,Sound Button Name,File Path"
        if key == "verify_sound_buttons":
            header = "Page,Button Number,Sound Button Name,File Path,Cause"
        try:
            self._write_csv_rows(file_path, header, matches)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Export Complete", f"Exported:\n{file_path}")

    def _print_tool_window(self, key: str, title: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        lines = [self._tool_match_to_line(match) for match in matches]
        if not lines:
            lines = ["(no items)"]
        self._print_lines(title, lines)

    def _print_hotkey_tool_window(self, key: str, title: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        lines = [self._tool_hotkey_match_to_line(match) for match in matches]
        if not lines:
            lines = ["(no items)"]
        self._print_lines(title, lines)

    def _print_midi_tool_window(self, key: str, title: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        lines = [self._tool_midi_match_to_line(match) for match in matches]
        if not lines:
            lines = ["(no items)"]
        self._print_lines(title, lines)

    def _write_csv_rows(self, file_path: str, header: str, matches: List[dict]) -> None:
        def _csv_cell(value: str) -> str:
            cell = (value or "").replace("\r", " ").replace("\n", " ")
            cell = cell.replace('"', '""')
            return f'"{cell}"'

        include_cause = "Cause" in header
        lines = [header]
        for match in matches:
            row = [
                _csv_cell(str(match["location"])),
                _csv_cell(str(int(match["slot"]) + 1)),
                _csv_cell(str(match["title"])),
                _csv_cell(str(match["file_path"])),
            ]
            if include_cause:
                row.append(_csv_cell(str(match.get("cause", ""))))
            lines.append(",".join(row))
        with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("\r\n".join(lines))

    def _tool_export_sound_hotkey_matches(self, key: str, export_format: str, base_name: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        if not matches:
            QMessageBox.information(self, "Export", "No rows to export.")
            return
        export_format = "excel" if export_format == "excel" else "csv"
        ext = ".xls" if export_format == "excel" else ".csv"
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or self._sports_sounds_pro_folder()
        initial_path = os.path.join(start_dir, f"{base_name}{ext}")
        file_filter = "Excel (*.xls)" if export_format == "excel" else "CSV (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", initial_path, f"{file_filter};;All Files (*.*)")
        if not file_path:
            return
        if not file_path.lower().endswith(ext):
            file_path = f"{file_path}{ext}"

        def _csv_cell(value: str) -> str:
            cell = (value or "").replace("\r", " ").replace("\n", " ")
            cell = cell.replace('"', '""')
            return f'"{cell}"'

        lines = ["Page,Button Number,Sound Hotkey,Sound Button Name,File Path"]
        for match in matches:
            lines.append(
                ",".join(
                    [
                        _csv_cell(str(match["location"])),
                        _csv_cell(str(int(match["slot"]) + 1)),
                        _csv_cell(str(match["sound_hotkey"])),
                        _csv_cell(str(match["title"])),
                        _csv_cell(str(match["file_path"])),
                    ]
                )
            )
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
                fh.write("\r\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Export Complete", f"Exported:\n{file_path}")

    def _tool_export_sound_midi_matches(self, key: str, export_format: str, base_name: str) -> None:
        matches = self._tool_window_matches.get(key, [])
        if not matches:
            QMessageBox.information(self, "Export", "No rows to export.")
            return
        export_format = "excel" if export_format == "excel" else "csv"
        ext = ".xls" if export_format == "excel" else ".csv"
        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or self._sports_sounds_pro_folder()
        initial_path = os.path.join(start_dir, f"{base_name}{ext}")
        file_filter = "Excel (*.xls)" if export_format == "excel" else "CSV (*.csv)"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export", initial_path, f"{file_filter};;All Files (*.*)")
        if not file_path:
            return
        if not file_path.lower().endswith(ext):
            file_path = f"{file_path}{ext}"

        def _csv_cell(value: str) -> str:
            cell = (value or "").replace("\r", " ").replace("\n", " ")
            cell = cell.replace('"', '""')
            return f'"{cell}"'

        lines = ["Page,Button Number,Sound MIDI Mapping,Sound Button Name,File Path"]
        for match in matches:
            lines.append(
                ",".join(
                    [
                        _csv_cell(str(match["location"])),
                        _csv_cell(str(int(match["slot"]) + 1)),
                        _csv_cell(str(match["sound_midi_hotkey"])),
                        _csv_cell(str(match["title"])),
                        _csv_cell(str(match["file_path"])),
                    ]
                )
            )
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as fh:
                fh.write("\r\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Export Complete", f"Exported:\n{file_path}")

    def _run_duplicate_check(self) -> None:
        entries = self._iter_all_sound_button_entries(include_cue=True)
        by_path: Dict[str, List[dict]] = {}
        for entry in entries:
            file_path = str(entry["file_path"]).strip()
            if not file_path:
                continue
            key = os.path.normcase(os.path.abspath(file_path))
            by_path.setdefault(key, []).append(entry)

        duplicate_groups = [group for group in by_path.values() if len(group) > 1]
        duplicate_groups.sort(key=lambda group: str(group[0]["file_path"]).casefold())
        matches: List[dict] = []
        for group in duplicate_groups:
            duplicate_count = len(group)
            for entry in group:
                item = dict(entry)
                item["title"] = f"{entry['title']} (duplicate x{duplicate_count})"
                matches.append(item)

        window = self._open_tool_window(
            key="duplicate_check",
            title="Duplicate Check",
            double_click_action="goto",
            show_play_button=False,
        )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=None,
            export_handler=lambda fmt: self._tool_export_matches("duplicate_check", fmt, "DuplicateCheck"),
            print_handler=lambda: self._print_tool_window("duplicate_check", "Duplicate Check"),
        )
        lines = [self._tool_match_to_line(match) for match in matches]
        status = f"{len(matches)} duplicate button(s) found."
        if not lines:
            status = "No duplicate sound buttons found."
        self._tool_window_matches["duplicate_check"] = matches
        window.set_items(lines, matches=matches, status=status)
        window.show()
        window.raise_()
        window.activateWindow()

    def _run_verify_sound_buttons(self) -> None:
        matches: List[dict] = []
        diagnostics_cache: Dict[str, Optional[str]] = {}
        entries: List[Tuple[str, int, int, SoundButtonData, str]] = []

        def slot_cause(slot: SoundButtonData) -> Optional[str]:
            path = str(slot.file_path or "").strip()
            if not path:
                return "No file path assigned."
            cached = diagnostics_cache.get(path)
            if cached is not None or path in diagnostics_cache:
                return cached
            cause = self._diagnose_sound_button_issue(path)
            diagnostics_cache[path] = cause
            return cause

        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                location = self._page_display_name(group, page_index)
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    entries.append((group, page_index, slot_index, slot, location))
        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned or slot.marker:
                continue
            entries.append(("Q", 0, slot_index, slot, "Cue Page"))

        cancelled = False
        total = len(entries)
        progress = QProgressDialog("Verifying sound buttons...", "Cancel", 0, max(1, total), self)
        progress.setWindowTitle("Verify Sound Buttons")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        processed = 0
        for group, page_index, slot_index, slot, location in entries:
            if progress.wasCanceled():
                cancelled = True
                break
            progress.setLabelText(f"Checking {location} - Button {slot_index + 1}...")
            causes: List[str] = []
            audio_cause = slot_cause(slot)
            if audio_cause:
                causes.append(audio_cause)
            lyric_cause = self._diagnose_slot_lyric_issue(slot)
            if lyric_cause:
                causes.append(lyric_cause)
            if causes:
                title = slot.title.strip() or os.path.splitext(os.path.basename(slot.file_path))[0]
                matches.append(
                    {
                        "group": group,
                        "page": page_index,
                        "slot": slot_index,
                        "title": title,
                        "file_path": slot.file_path,
                        "location": location,
                        "cause": "; ".join(causes),
                    }
                )
            processed += 1
            progress.setValue(processed)
            QApplication.processEvents()
        progress.close()

        self._refresh_sound_grid()
        window = self._open_tool_window(
            key="verify_sound_buttons",
            title="Verify Sound Buttons",
            double_click_action="goto",
            show_play_button=False,
        )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=None,
            export_handler=lambda fmt: self._tool_export_matches("verify_sound_buttons", fmt, "VerifySoundButtons"),
            print_handler=lambda: self._print_tool_window("verify_sound_buttons", "Verify Sound Buttons"),
        )
        lines = [self._tool_match_to_line(match) for match in matches]
        if cancelled:
            status = f"Cancelled after {processed}/{total} button(s). {len(matches)} invalid button(s) found."
        else:
            status = f"{len(matches)} invalid button(s) found."
        if not lines and not cancelled:
            status = "No invalid sound button paths found."
        self._tool_window_matches["verify_sound_buttons"] = matches
        window.set_items(lines, matches=matches, status=status)
        window.show()
        window.raise_()
        window.activateWindow()

    def _scan_sound_button_lyrics(self) -> None:
        entries: List[Tuple[str, int, int, SoundButtonData, str]] = []
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                location = self._page_display_name(group, page_index)
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    entries.append((group, page_index, slot_index, slot, location))
        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned or slot.marker:
                continue
            entries.append(("Q", 0, slot_index, slot, "Cue Page"))

        total = len(entries)
        if total <= 0:
            self._show_info_notice_banner("No sound buttons assigned.")
            return

        progress = QProgressDialog("Scanning lyric files...", "Skip", 0, max(1, total), self)
        progress.setWindowTitle("Scan Sound Buttons Lyrics")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        QApplication.processEvents()

        processed = 0
        cancelled = False
        rows: List[Tuple[str, str]] = []
        refs: List[SoundButtonData] = []
        for _group, _page, slot_index, slot, location in entries:
            if progress.wasCanceled():
                cancelled = True
                break
            progress.setLabelText(f"Scanning {location} - Button {slot_index + 1}...")
            if str(slot.lyric_file or "").strip():
                processed += 1
                progress.setValue(processed)
                QApplication.processEvents()
                continue
            candidate = self._find_matching_lyric_file(slot.file_path)
            if candidate:
                rows.append((slot.file_path, candidate))
                refs.append(slot)
            processed += 1
            progress.setValue(processed)
            QApplication.processEvents()
        progress.close()

        if cancelled and rows:
            self._show_info_notice_banner(f"Lyric scan skipped ({processed}/{total}). Showing partial scan results.")
        elif cancelled:
            self._show_info_notice_banner(f"Lyric scan cancelled ({processed}/{total}).")
            return
        if not rows:
            self._show_info_notice_banner("No matching lyric files found.")
            return

        dialog = LinkLyricDialog(rows, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        flags = dialog.link_flags()
        changed = False
        linked = 0
        unlinked = 0
        for idx, slot in enumerate(refs):
            candidate = rows[idx][1]
            should_link = idx < len(flags) and bool(flags[idx])
            next_value = candidate if should_link else ""
            if str(slot.lyric_file or "").strip() != next_value:
                slot.lyric_file = next_value
                changed = True
                if should_link:
                    linked += 1
                else:
                    unlinked += 1

        if changed:
            self._set_dirty(True)
            self._refresh_sound_grid()
            self._show_save_notice_banner(f"Lyrics scan complete. Linked: {linked}, Unlinked: {unlinked}.")
            return
        self._show_info_notice_banner("Lyrics scan complete. No changes.")

    def _remove_all_linked_lyric_files(self) -> None:
        linked_count = 0
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot in self.data[group][page_index]:
                    if not slot.assigned or slot.marker:
                        continue
                    if str(slot.lyric_file or "").strip():
                        linked_count += 1
        for slot in self.cue_page:
            if not slot.assigned or slot.marker:
                continue
            if str(slot.lyric_file or "").strip():
                linked_count += 1

        if linked_count <= 0:
            self._show_info_notice_banner("No linked lyric files to remove.")
            return

        answer = QMessageBox.question(
            self,
            "Remove All Linked Lyric File",
            f"Remove linked lyric files from {linked_count} sound button(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        changed = 0
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot in self.data[group][page_index]:
                    if not slot.assigned or slot.marker:
                        continue
                    if str(slot.lyric_file or "").strip():
                        slot.lyric_file = ""
                        changed += 1
        for slot in self.cue_page:
            if not slot.assigned or slot.marker:
                continue
            if str(slot.lyric_file or "").strip():
                slot.lyric_file = ""
                changed += 1

        if changed <= 0:
            self._show_info_notice_banner("No linked lyric files were removed.")
            return

        self._set_dirty(True)
        self._refresh_sound_grid()
        self._refresh_stage_display()
        self._refresh_lyric_display(force=True)
        self._show_save_notice_banner(f"Removed linked lyric files from {changed} sound button(s).")

    def _diagnose_sound_button_issue(self, file_path: str) -> Optional[str]:
        path = str(file_path or "").strip()
        if not path:
            return "No file path assigned."
        reason = self._path_safety_reason(path)
        if reason:
            return f"Invalid file path: {reason}"
        if not os.path.exists(path):
            base_name = os.path.basename(path)
            if ("?" in base_name) or ("\uFFFD" in base_name):
                return "Missing file. Filename appears encoding-corrupted ('?' or replacement character)."
            return "Missing file path."
        try:
            get_media_ssp_units(path)
            return None
        except Exception as exc:
            try:
                if can_decode_with_ffmpeg(path):
                    return None
            except Exception:
                pass
            return self._classify_audio_decode_issue(path, exc)

    def _path_safety_reason(self, file_path: str) -> Optional[str]:
        if self.disable_path_safety:
            return None
        return unsafe_path_reason(file_path)

    def _classify_audio_decode_issue(self, file_path: str, exc: Exception) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        reason = str(exc).strip() or exc.__class__.__name__
        video_extensions = {
            ".mp4",
            ".m4v",
            ".mov",
            ".mkv",
            ".avi",
            ".wmv",
            ".webm",
            ".flv",
            ".mpg",
            ".mpeg",
            ".ts",
            ".m2ts",
            ".3gp",
            ".ogv",
        }
        if ext in video_extensions:
            has_audio = media_has_audio_stream(file_path)
            if has_audio is False:
                return "Audio decode failed: video file has no audio stream."
            if has_audio is True:
                return "Audio decode failed: video audio stream is unsupported or corrupted."
        try:
            with open(file_path, "rb") as fh:
                head = fh.read(64)
        except OSError:
            return f"Audio decode failed: {reason}"

        asf_header = bytes.fromhex("30 26 B2 75 8E 66 CF 11 A6 D9 00 AA 00 62 CE 6C")
        if len(head) >= 16 and head[:16] == asf_header:
            return "Audio decode failed: file is ASF/WMA content mislabeled as .mp3."
        if ext == ".mp3" and len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
            return "Audio decode failed: MPEG bitstream appears malformed or unsupported by decoder."
        if ext == ".mp3":
            return "Audio decode failed: data does not appear to be valid MP3."
        return f"Audio decode failed: {reason}"

    def _audio_file_dialog_filter(self) -> str:
        return build_audio_file_dialog_filter(
            self.supported_audio_format_extensions,
            self.allow_other_unsupported_audio_files,
        )

    def _verify_audio_files_before_add(self, file_paths: List[str]) -> List[dict]:
        matches: List[dict] = []
        progress = QProgressDialog("Verifying audio files...", "Skip", 0, max(1, len(file_paths)), self)
        progress.setWindowTitle("Verify Added Sound Files")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        for index, file_path in enumerate(file_paths):
            if progress.wasCanceled():
                break
            progress.setLabelText(f"Checking {os.path.basename(file_path)}...")
            cause = self._diagnose_sound_button_issue(file_path)
            if cause:
                matches.append(
                    {
                        "group": self.current_group,
                        "page": self.current_page,
                        "slot": index,
                        "title": os.path.splitext(os.path.basename(file_path))[0],
                        "file_path": file_path,
                        "location": "Add Sound Button",
                        "cause": cause,
                    }
                )
            progress.setValue(index + 1)
            QApplication.processEvents()
        progress.close()
        return matches

    def _show_audio_add_verification_results(self, matches: List[dict]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Verify Added Sound Files")
        dialog.resize(820, 420)
        root = QVBoxLayout(dialog)
        note = QLabel(
            "Some files could not be verified. They will still be added. Close this window to continue lyric scanning.",
            dialog,
        )
        note.setWordWrap(True)
        root.addWidget(note)
        text = QPlainTextEdit(dialog)
        text.setReadOnly(True)
        lines: List[str] = []
        for match in matches:
            lines.append(str(match.get("title", "")).strip())
            lines.append(f"  Path: {match.get('file_path', '')}")
            lines.append(f"  Reason: {match.get('cause', '')}")
            lines.append("")
        text.setPlainText("\n".join(lines).strip())
        root.addWidget(text, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.clicked.connect(dialog.accept)
        root.addWidget(buttons)
        dialog.exec_()

    def _disable_playlist_on_all_pages(self) -> None:
        changed = False
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                if self.page_playlist_enabled[group][page_index] or self.page_shuffle_enabled[group][page_index]:
                    changed = True
                self.page_playlist_enabled[group][page_index] = False
                self.page_shuffle_enabled[group][page_index] = False
        if not changed:
            self._show_info_notice_banner("Play List is already disabled on all pages.")
            return
        self.current_playlist_start = None
        self._set_dirty(True)
        self._sync_playlist_shuffle_buttons()
        self._show_save_notice_banner("Play List has been disabled on all pages.")

    def _reset_all_pages_state(self) -> None:
        answer = QMessageBox.question(
            self,
            tr("Reset All Pages"),
            tr("Reset all pages' played state?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._stop_playback()
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot in self.data[group][page_index]:
                    slot.played = False
                    if slot.assigned:
                        slot.activity_code = "8"
        self.current_playlist_start = None
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _show_page_library_folder_path(self) -> None:
        path = self._page_library_folder_path()
        box = QMessageBox(self)
        box.setWindowTitle("Page Library Folder Path")
        box.setText(f"Sports Sounds Pro Page Library folder:\n{path}")
        open_btn = box.addButton("Open Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        box.exec_()
        if box.clickedButton() == open_btn:
            self._open_directory(path)

    def _show_set_file_and_path(self) -> None:
        if self.current_set_path:
            path = os.path.dirname(self.current_set_path)
            text = f"Current .set file:\n{self.current_set_path}"
        else:
            path = self.settings.last_open_dir or self._sports_sounds_pro_folder()
            text = "No .set file is currently loaded."
        box = QMessageBox(self)
        box.setWindowTitle("Display .set File and Path")
        box.setText(text)
        open_btn = box.addButton("Open Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        box.exec_()
        if box.clickedButton() == open_btn:
            self._open_directory(path)

    def _export_page_and_sound_buttons_to_excel(self) -> None:
        if self._export_buttons_window is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Export Page and Sound Buttons")
            dialog.resize(700, 190)
            dialog.setModal(False)
            dialog.setWindowModality(Qt.NonModal)
            root = QVBoxLayout(dialog)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(8)

            dir_row = QHBoxLayout()
            dir_row.addWidget(QLabel("Directory"))
            self._export_dir_edit = QLineEdit(self._sports_sounds_pro_folder())
            dir_row.addWidget(self._export_dir_edit, 1)
            browse_btn = QPushButton("Browse")
            dir_row.addWidget(browse_btn)
            root.addLayout(dir_row)

            format_row = QHBoxLayout()
            format_row.addWidget(QLabel("Format"))
            self._export_format_combo = QComboBox()
            self._export_format_combo.addItems(["Excel (.xls)", "CSV (.csv)"])
            format_row.addWidget(self._export_format_combo)
            format_row.addStretch(1)
            root.addLayout(format_row)

            button_row = QHBoxLayout()
            button_row.addStretch(1)
            export_btn = QPushButton("Export")
            close_btn = QPushButton("Close")
            button_row.addWidget(export_btn)
            button_row.addWidget(close_btn)
            root.addLayout(button_row)

            browse_btn.clicked.connect(self._browse_export_directory)
            export_btn.clicked.connect(self._run_export_buttons_from_window)
            close_btn.clicked.connect(dialog.close)
            dialog.destroyed.connect(lambda _=None: self._clear_export_window_ref())
            self._export_buttons_window = dialog
        self._export_buttons_window.show()
        self._export_buttons_window.raise_()
        self._export_buttons_window.activateWindow()

    def _list_sound_buttons(self) -> None:
        window = self._open_tool_window(
            key="list_sound_buttons",
            title="List Sound Buttons",
            double_click_action="play",
            show_play_button=True,
        )
        window.set_note("")
        if not window.order_combo.isVisible():
            window.enable_order_controls(
                options=["Group/Page sequence", "Sound Button sequence"],
                refresh_handler=self._refresh_list_sound_buttons_window,
            )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=self._play_found_match,
            export_handler=lambda fmt: self._tool_export_matches("list_sound_buttons", fmt, "ListSoundButtons"),
            print_handler=lambda: self._print_tool_window("list_sound_buttons", "List Sound Buttons"),
        )
        if not window.current_order():
            window.order_combo.setCurrentIndex(0)
        self._refresh_list_sound_buttons_window(window.current_order())
        window.show()
        window.raise_()
        window.activateWindow()

    def _list_sound_button_hotkeys(self) -> None:
        window = self._open_tool_window(
            key="list_sound_button_hotkeys",
            title="List Sound Button Hot Key",
            double_click_action="play",
            show_play_button=True,
        )
        window.set_note(
            "Note: Sound Button Hot Key only works when enabled in Options > Hotkey. "
            f"Current priority: {'Sound Button Hot Key first' if self.sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        if not window.order_combo.isVisible():
            window.enable_order_controls(
                options=["Group/Page sequence", "Hotkey sequence"],
                refresh_handler=self._refresh_list_sound_button_hotkeys_window,
            )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=self._play_found_match,
            export_handler=lambda fmt: self._tool_export_sound_hotkey_matches(
                "list_sound_button_hotkeys",
                fmt,
                "ListSoundButtonHotKeys",
            ),
            print_handler=lambda: self._print_hotkey_tool_window("list_sound_button_hotkeys", "List Sound Button Hot Key"),
        )
        if not window.current_order():
            window.order_combo.setCurrentIndex(0)
        self._refresh_list_sound_button_hotkeys_window(window.current_order())
        window.show()
        window.raise_()
        window.activateWindow()

    def _list_sound_device_midi_mappings(self) -> None:
        window = self._open_tool_window(
            key="list_sound_device_midi_mappings",
            title="List Sound Device MIDI Mapping",
            double_click_action="play",
            show_play_button=True,
        )
        window.set_note(
            "Note: Sound Button MIDI Hot Key only works when enabled in Options > Midi Control > Sound Button Hot Key. "
            f"Current priority: {'Sound Button MIDI Hot Key first' if self.midi_sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        if not window.order_combo.isVisible():
            window.enable_order_controls(
                options=["Group/Page sequence", "MIDI mapping sequence"],
                refresh_handler=self._refresh_list_sound_device_midi_mappings_window,
            )
        window.set_handlers(
            goto_handler=self._go_to_found_match,
            play_handler=self._play_found_match,
            export_handler=lambda fmt: self._tool_export_sound_midi_matches(
                "list_sound_device_midi_mappings",
                fmt,
                "ListSoundDeviceMidiMappings",
            ),
            print_handler=lambda: self._print_midi_tool_window(
                "list_sound_device_midi_mappings",
                "List Sound Device MIDI Mapping",
            ),
        )
        if not window.current_order():
            window.order_combo.setCurrentIndex(0)
        self._refresh_list_sound_device_midi_mappings_window(window.current_order())
        window.show()
        window.raise_()
        window.activateWindow()

    def _refresh_list_sound_buttons_window(self, selected_order: str) -> None:
        matches: List[dict] = self._iter_all_sound_button_entries(include_cue=True)
        if selected_order == "Sound Button sequence":
            matches.sort(
                key=lambda entry: (
                    str(entry["title"]).casefold(),
                    str(entry["file_path"]).casefold(),
                    str(entry["location"]).casefold(),
                    int(entry["slot"]),
                )
            )
        window = self._tool_windows.get("list_sound_buttons")
        if window is None:
            return
        self._tool_window_matches["list_sound_buttons"] = matches
        lines = [self._tool_match_to_line(entry) for entry in matches]
        status = f"{len(matches)} sound button(s)."
        if not lines:
            status = "No sound buttons assigned."
        window.set_items(lines, matches=matches, status=status)

    def _refresh_list_sound_button_hotkeys_window(self, selected_order: str) -> None:
        matches: List[dict] = []
        for entry in self._iter_all_sound_button_entries(include_cue=True):
            slot = self._slot_for_location(str(entry["group"]), int(entry["page"]), int(entry["slot"]))
            token = self._parse_sound_hotkey(slot.sound_hotkey)
            if not token:
                continue
            item = dict(entry)
            item["sound_hotkey"] = token
            matches.append(item)
        if selected_order == "Hotkey sequence":
            matches.sort(
                key=lambda entry: (
                    str(entry["sound_hotkey"]).casefold(),
                    str(entry["location"]).casefold(),
                    int(entry["slot"]),
                )
            )
        window = self._tool_windows.get("list_sound_button_hotkeys")
        if window is None:
            return
        window.set_note(
            "Note: Sound Button Hot Key only works when enabled in Options > Hotkey. "
            f"Current priority: {'Sound Button Hot Key first' if self.sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        self._tool_window_matches["list_sound_button_hotkeys"] = matches
        lines = [self._tool_hotkey_match_to_line(entry) for entry in matches]
        status = f"{len(matches)} sound button hot key assignment(s)."
        if not lines:
            status = "No sound button hot keys assigned."
        window.set_items(lines, matches=matches, status=status)

    def _refresh_list_sound_device_midi_mappings_window(self, selected_order: str) -> None:
        matches: List[dict] = []
        for entry in self._iter_all_sound_button_entries(include_cue=True):
            slot = self._slot_for_location(str(entry["group"]), int(entry["page"]), int(entry["slot"]))
            token = normalize_midi_binding(slot.sound_midi_hotkey)
            if not token:
                continue
            item = dict(entry)
            item["sound_midi_hotkey"] = token
            matches.append(item)
        if selected_order == "MIDI mapping sequence":
            matches.sort(
                key=lambda entry: (
                    str(entry["sound_midi_hotkey"]).casefold(),
                    str(entry["location"]).casefold(),
                    int(entry["slot"]),
                )
            )
        window = self._tool_windows.get("list_sound_device_midi_mappings")
        if window is None:
            return
        window.set_note(
            "Note: Sound Button MIDI Hot Key only works when enabled in Options > Midi Control > Sound Button Hot Key. "
            f"Current priority: {'Sound Button MIDI Hot Key first' if self.midi_sound_button_hotkey_priority == 'sound_button_first' else 'System/Quick Action first'}."
        )
        self._tool_window_matches["list_sound_device_midi_mappings"] = matches
        lines = [self._tool_midi_match_to_line(entry) for entry in matches]
        status = f"{len(matches)} sound button MIDI mapping assignment(s)."
        if not lines:
            status = "No sound button MIDI mappings assigned."
        window.set_items(lines, matches=matches, status=status)

    def _browse_export_directory(self) -> None:
        if self._export_dir_edit is None:
            return
        start_dir = self._export_dir_edit.text().strip() or self._sports_sounds_pro_folder()
        directory = QFileDialog.getExistingDirectory(self, "Select Export Directory", start_dir)
        if not directory:
            return
        self._export_dir_edit.setText(directory)

    def _run_export_buttons_from_window(self) -> None:
        if self._export_dir_edit is None or self._export_format_combo is None:
            return
        export_dir = self._export_dir_edit.text().strip() or self._sports_sounds_pro_folder()
        os.makedirs(export_dir, exist_ok=True)
        selected = self._export_format_combo.currentText().strip().lower()
        extension = ".xls" if selected.startswith("excel") else ".csv"
        export_path = os.path.join(export_dir, f"SSPExportToExcel{extension}")
        matches = self._iter_all_sound_button_entries(include_cue=True)
        try:
            self._write_csv_rows(export_path, "Page,Button Number,Sound Button Name,File Path", matches)
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", f"Could not export file:\n{exc}")
            return
        self.settings.last_save_dir = export_dir
        self._save_settings()
        box = QMessageBox(self)
        box.setWindowTitle("Export Complete")
        box.setText(f"Exported:\n{export_path}")
        open_btn = box.addButton("Open Folder", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        box.exec_()
        if box.clickedButton() == open_btn:
            self._open_directory(export_dir)

    def _clear_export_window_ref(self) -> None:
        self._export_buttons_window = None
        self._export_dir_edit = None
        self._export_format_combo = None

    def _open_local_path(self, path: str, title: str, error_prefix: str) -> bool:
        target = str(path or "").strip()
        if not target:
            return False
        normalized = os.path.abspath(target)
        try:
            if QDesktopServices.openUrl(QUrl.fromLocalFile(normalized)):
                return True
        except Exception:
            pass
        try:
            if sys.platform == "darwin":
                subprocess.Popen(
                    ["open", normalized],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            if os.name == "nt":
                os.startfile(normalized)  # type: ignore[attr-defined]
                return True
            subprocess.Popen(
                ["xdg-open", normalized],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as exc:
            QMessageBox.warning(self, title, f"{error_prefix}\n{exc}")
            return False

    def _open_directory(self, path: str) -> None:
        if not path:
            return
        os.makedirs(path, exist_ok=True)
        self._open_local_path(path, "Open Folder", "Could not open folder:")

    def _open_settings_folder(self) -> None:
        self._open_directory(str(get_settings_path().parent))

    def _reveal_sound_file_in_browser(self, file_path: str) -> None:
        path = str(file_path or "").strip()
        if not path:
            return
        normalized = os.path.abspath(path)
        if not os.path.exists(normalized):
            QMessageBox.warning(
                self,
                tr("Reveal Sound File"),
                tr("Sound file does not exist:\n{path}").format(path=normalized),
            )
            return
        try:
            if os.name == "nt":
                subprocess.Popen(
                    ["explorer", "/select,", normalized],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            if sys.platform == "darwin":
                subprocess.Popen(
                    ["open", "-R", normalized],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
        except Exception:
            pass
        self._open_directory(os.path.dirname(normalized) or ".")

