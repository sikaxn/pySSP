from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class SettingsArchiveMixin:
    def _project_root_path(self) -> str:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _asset_file_path(self, *parts: str) -> str:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
            bundled = os.path.join(base_dir, "pyssp", "assets", *parts)
            if os.path.exists(bundled):
                return bundled
            meipass_dir = getattr(sys, "_MEIPASS", "")
            if meipass_dir:
                candidate = os.path.join(meipass_dir, "pyssp", "assets", *parts)
                if os.path.exists(candidate):
                    return candidate
            return bundled
        return os.path.join(self._project_root_path(), "pyssp", "assets", *parts)

    def _help_index_path(self) -> str:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
            bundled = os.path.join(base_dir, "docs", "build", "html", "index.html")
            if os.path.exists(bundled):
                return bundled
            meipass_dir = getattr(sys, "_MEIPASS", "")
            if meipass_dir:
                candidate = os.path.join(meipass_dir, "docs", "build", "html", "index.html")
                if os.path.exists(candidate):
                    return candidate
            return bundled
        return os.path.join(self._project_root_path(), "docs", "build", "html", "index.html")

    def _default_backup_dir(self) -> str:
        return self.settings.last_save_dir or self.settings.last_open_dir or os.path.expanduser("~")

    @staticmethod
    def _coerce_bool(value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            token = value.strip().lower()
            if token in {"1", "true", "yes", "on"}:
                return True
            if token in {"0", "false", "no", "off"}:
                return False
        return bool(value) if value is not None else bool(default)

    @staticmethod
    def _coerce_int(value, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except Exception:
            parsed = int(default)
        return max(int(minimum), min(int(maximum), int(parsed)))

    @staticmethod
    def _normalize_stage_display_layout(values: List[str]) -> List[str]:
        valid = [
            "current_time",
            "alert",
            "total_time",
            "elapsed",
            "remaining",
            "progress_bar",
            "song_name",
            "lyric",
            "next_song",
        ]
        output: List[str] = []
        for raw in list(values or []):
            key = str(raw or "").strip().lower()
            if key in valid and key not in output:
                output.append(key)
        for key in valid:
            if key not in output:
                output.append(key)
        return output

    @staticmethod
    def _normalize_stage_display_visibility(values: Dict[str, bool]) -> Dict[str, bool]:
        valid = [
            "current_time",
            "alert",
            "total_time",
            "elapsed",
            "remaining",
            "progress_bar",
            "song_name",
            "lyric",
            "next_song",
        ]
        output: Dict[str, bool] = {}
        for key in valid:
            output[key] = bool(values.get(key, True))
        return output

    def _backup_pyssp_settings(self) -> None:
        self._save_settings()
        source = get_settings_path()
        if not source.exists():
            try:
                save_settings(self.settings)
            except Exception as exc:
                QMessageBox.critical(self, "Backup pySSP Settings", f"Could not create settings file:\n{exc}")
                return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_path = os.path.join(self._default_backup_dir(), f"pyssp_settings_backup_{stamp}.ini")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup pySSP Settings",
            initial_path,
            "INI Files (*.ini);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".ini"):
            file_path = f"{file_path}.ini"
        try:
            shutil.copy2(str(source), file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Backup pySSP Settings", f"Could not backup settings:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Backup pySSP Settings", f"Backup saved:\n{file_path}")

    def _restore_pyssp_settings(self) -> None:
        start_dir = self._default_backup_dir()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore pySSP Settings",
            start_dir,
            "INI Files (*.ini);;All Files (*.*)",
        )
        if not file_path:
            return
        target = get_settings_path()
        try:
            shutil.copy2(file_path, str(target))
        except Exception as exc:
            QMessageBox.critical(self, "Restore pySSP Settings", f"Could not restore settings:\n{exc}")
            return
        answer = QMessageBox.question(
            self,
            "Restore pySSP Settings",
            "Settings restored.\npySSP needs restart to apply them correctly.\n\nRestart now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._skip_save_on_close = True
            self.close()
            return
        QMessageBox.information(
            self,
            "Restore pySSP Settings",
            "Settings restored to disk. Restart pySSP before making more changes.",
        )

    def _pack_audio_library(self) -> None:
        dialog = PackAudioLibraryDialog(self._build_pack_page_selection_items(), parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return

        selected_pages: set[Tuple[str, int]] = set()
        for key in dialog.selected_keys():
            decoded = self._decode_pack_page_key(key)
            if decoded is not None:
                selected_pages.add(decoded)
        if not selected_pages:
            QMessageBox.information(self, tr("Pack Audio Library"), tr("Select at least one page to pack."))
            return

        start_dir = self.settings.last_save_dir or self.settings.last_open_dir or os.path.expanduser("~")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_path = os.path.join(start_dir, f"pyssp_audio_library_{stamp}.pyssppak")
        package_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Pack Audio Library"),
            initial_path,
            tr("pySSP Audio Library (*.pyssppak);;All Files (*.*)"),
        )
        if not package_path:
            return
        if not package_path.lower().endswith(".pyssppak"):
            package_path = f"{package_path}.pyssppak"

        include_settings = bool(dialog.include_settings_checkbox.isChecked())
        include_lyrics = bool(dialog.pack_lyrics_checkbox.isChecked())
        maintain_structure = bool(dialog.maintain_structure_checkbox.isChecked())
        settings_source = None
        if include_settings:
            self._save_settings()
            settings_path = get_settings_path()
            if settings_path.exists():
                settings_source = str(settings_path)

        path_usage = self._collect_pack_path_usage(selected_pages)
        ordered_paths = [item["source_path"] for item in path_usage.values()]
        planned_audio_entries = build_archive_audio_entries(ordered_paths, maintain_structure)
        entry_by_path = {
            os.path.normcase(os.path.abspath(entry.source_path)): entry for entry in planned_audio_entries
        }
        lyric_path_usage = self._collect_pack_lyric_path_usage(selected_pages) if include_lyrics else {}
        lyric_ordered_paths = [item["source_path"] for item in lyric_path_usage.values()]
        planned_lyric_entries = build_archive_lyric_entries(lyric_ordered_paths, maintain_structure) if include_lyrics else []
        lyric_entry_by_path = {
            os.path.normcase(os.path.abspath(entry.source_path)): entry for entry in planned_lyric_entries
        }
        total_steps = len(planned_audio_entries) + len(planned_lyric_entries) + 2 + (1 if settings_source else 0)
        progress = QProgressDialog(tr("Packing audio library..."), tr("Cancel"), 0, max(1, total_steps), self)
        progress.setWindowTitle(tr("Pack Audio Library"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        set_member_name = f"{os.path.splitext(os.path.basename(package_path))[0]}.set"
        packed_audio_entries: List[object] = []
        packed_lyric_entries: List[object] = []
        slot_path_overrides: Dict[Tuple[str, int, int], str] = {}
        lyric_path_overrides: Dict[Tuple[str, int, int], str] = {}
        skipped_slots: set[Tuple[str, int, int]] = set()
        report_rows: List[PackReportRow] = []
        try:
            with tempfile.TemporaryDirectory(prefix="pyssp_pack_") as temp_dir:
                with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    step = 0
                    for normalized_path, path_info in path_usage.items():
                        if progress.wasCanceled():
                            raise ArchiveOperationCancelled()
                        source_path = str(path_info["source_path"])
                        progress.setLabelText(f"{tr('Verifying and packing')} {os.path.basename(source_path)}...")
                        cause = self._diagnose_sound_button_issue(source_path)
                        if cause:
                            for slot_info in path_info["slots"]:
                                skipped_slots.add((slot_info["group"], slot_info["page"], slot_info["slot"]))
                                report_rows.append(
                                    PackReportRow(
                                        location=str(slot_info["location"]),
                                        slot=int(slot_info["slot"]) + 1,
                                        title=str(slot_info["title"]),
                                        file_path=source_path,
                                        status=tr("Skipped"),
                                        cause=cause,
                                    )
                                )
                        else:
                            entry = entry_by_path.get(normalized_path)
                            if entry is None:
                                raise RuntimeError(f"Missing archive entry for {source_path}")
                            archive.write(source_path, arcname=entry.archive_member)
                            packed_audio_entries.append(entry)
                            for slot_info in path_info["slots"]:
                                slot_key = (slot_info["group"], slot_info["page"], slot_info["slot"])
                                slot_path_overrides[slot_key] = entry.set_path
                                report_rows.append(
                                    PackReportRow(
                                        location=str(slot_info["location"]),
                                        slot=int(slot_info["slot"]) + 1,
                                        title=str(slot_info["title"]),
                                        file_path=source_path,
                                        status=tr("Packed"),
                                        cause="",
                                    )
                                )
                            step += 1
                            self._update_archive_progress(
                                progress,
                                step,
                                total_steps,
                                f"{tr('Processed')} {os.path.basename(source_path)}",
                            )

                    for normalized_path, path_info in lyric_path_usage.items():
                        if progress.wasCanceled():
                            raise ArchiveOperationCancelled()
                        source_path = str(path_info["source_path"])
                        if not os.path.exists(source_path):
                            continue
                        progress.setLabelText(f"{tr('Verifying and packing')} {os.path.basename(source_path)}...")
                        entry = lyric_entry_by_path.get(normalized_path)
                        if entry is None:
                            raise RuntimeError(f"Missing lyric archive entry for {source_path}")
                        archive.write(source_path, arcname=entry.archive_member)
                        packed_lyric_entries.append(entry)
                        for slot_info in path_info["slots"]:
                            slot_key = (slot_info["group"], slot_info["page"], slot_info["slot"])
                            lyric_path_overrides[slot_key] = entry.set_path
                        step += 1
                        self._update_archive_progress(
                            progress,
                            step,
                            total_steps,
                            f"{tr('Processed')} {os.path.basename(source_path)}",
                        )

                    temp_set_path = os.path.join(temp_dir, set_member_name)
                    pack_lines = self._build_set_file_lines(
                        selected_pages=selected_pages,
                        slot_path_overrides=slot_path_overrides,
                        lyric_path_overrides=lyric_path_overrides,
                        skipped_slots=skipped_slots,
                    )
                    self._write_set_payload(temp_set_path, pack_lines)
                    archive.write(temp_set_path, arcname=set_member_name)
                    step += 1
                    self._update_archive_progress(progress, step, total_steps, f"{tr('Packing')} {set_member_name}...")

                    if settings_source:
                        if progress.wasCanceled():
                            raise ArchiveOperationCancelled()
                        archive.write(settings_source, arcname="settings.ini")
                        step += 1
                        self._update_archive_progress(progress, step, total_steps, tr("Packing settings.ini..."))

                    manifest = build_manifest(
                        set_member_name,
                        packed_audio_entries,
                        bool(settings_source),
                        lyric_entries=packed_lyric_entries,
                    )
                    write_manifest(archive, manifest)
                    step += 1
                    self._update_archive_progress(progress, step, total_steps, tr("Writing package manifest..."))
        except ArchiveOperationCancelled:
            progress.close()
            if os.path.exists(package_path):
                try:
                    os.remove(package_path)
                except OSError:
                    pass
            QMessageBox.information(self, tr("Pack Audio Library"), tr("Pack operation cancelled."))
            return
        except Exception as exc:
            progress.close()
            QMessageBox.critical(self, tr("Pack Audio Library"), f"{tr('Could not pack audio library:')}\n{exc}")
            return

        progress.close()
        self.settings.last_save_dir = os.path.dirname(package_path)
        self._save_settings()
        report_dialog = PackReportDialog(report_rows, os.path.dirname(package_path), parent=self)
        report_dialog.exec_()

    def _unpack_audio_library(self) -> None:
        dialog = UnpackLibraryDialog("", "", parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.values()
        package_path = values.package_path
        destination_dir = values.destination_dir or default_unpack_directory(package_path)
        if not package_path or not os.path.exists(package_path):
            QMessageBox.warning(self, tr("Unpack Audio Library"), tr("Select a valid pyssppak file."))
            return
        if not destination_dir:
            QMessageBox.warning(self, tr("Unpack Audio Library"), tr("Select an unpack directory."))
            return

        progress = QProgressDialog(tr("Unpacking audio library..."), tr("Cancel"), 0, 1, self)
        progress.setWindowTitle(tr("Unpack Audio Library"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        try:
            result = unpack_pyssppak(
                package_path=package_path,
                destination_dir=destination_dir,
                maintain_directory_structure=values.maintain_directory_structure,
                unpack_lyrics=values.unpack_lyrics,
                progress_callback=lambda current, total, label: self._update_archive_progress(
                    progress, current, total, label
                ),
                is_cancelled=progress.wasCanceled,
            )
            if result.audio_path_map or result.lyric_path_map or (bool(result.manifest.get("lyric_entries")) and (not values.unpack_lyrics)):
                rewrite_packed_set_paths(
                    result.extracted_set_path,
                    result.audio_path_map,
                    lyric_replacements=result.lyric_path_map,
                    clear_missing_lyrics=(
                        bool(result.manifest.get("lyric_entries")) and (not values.unpack_lyrics)
                    ),
                )
        except ArchiveOperationCancelled:
            progress.close()
            QMessageBox.information(self, tr("Unpack Audio Library"), tr("Unpack operation cancelled."))
            return
        except Exception as exc:
            progress.close()
            QMessageBox.critical(self, tr("Unpack Audio Library"), f"{tr('Could not unpack library:')}\n{exc}")
            return

        progress.close()
        self.settings.last_open_dir = os.path.dirname(package_path)
        self.settings.last_save_dir = destination_dir
        self._save_settings()

        if values.open_set_after_unpack:
            self._load_set(result.extracted_set_path, show_message=True, restore_last_position=False)

        if values.restore_settings and result.extracted_settings_path:
            self._restore_packed_pyssp_settings(
                result.extracted_settings_path,
                open_set_path=result.extracted_set_path if values.open_set_after_unpack else "",
            )
            return

        QMessageBox.information(
            self,
            tr("Unpack Audio Library"),
            f"{tr('Library unpacked.')}\n\n{tr('Set file:')}\n{result.extracted_set_path}\n\n{tr('Audio folder:')}\n{destination_dir}",
        )

    def _restore_packed_pyssp_settings(self, source_path: str, open_set_path: str = "") -> None:
        target = get_settings_path()
        try:
            shutil.copy2(source_path, str(target))
            restored_settings = load_settings()
            if open_set_path:
                restored_settings.last_set_path = open_set_path
                restored_settings.last_open_dir = os.path.dirname(open_set_path)
                restored_settings.last_save_dir = os.path.dirname(open_set_path)
                restored_settings.last_group = "A"
                restored_settings.last_page = 0
                save_settings(restored_settings)
        except Exception as exc:
            QMessageBox.critical(self, tr("Restore pySSP Settings"), f"{tr('Could not restore settings:')}\n{exc}")
            return

        answer = QMessageBox.question(
            self,
            tr("Restore pySSP Settings"),
            tr("Settings restored.\npySSP needs restart to apply them correctly.\n\nRestart now?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            self._skip_save_on_close = True
            self.close()
            return
        QMessageBox.information(
            self,
            tr("Restore pySSP Settings"),
            tr("Settings restored to disk. Restart pySSP before making more changes."),
        )

    def _build_pack_page_selection_items(self) -> List[PageSelectionItem]:
        items: List[PageSelectionItem] = []
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                label = self._page_display_name(group, page_index)
                page_created = self._is_page_created(group, page_index)
                items.append(
                    PageSelectionItem(
                        key=self._encode_pack_page_key(group, page_index),
                        label=label,
                        checked=page_created,
                        enabled=page_created,
                    )
                )
        return items

    def _collect_pack_path_usage(self, selected_pages: set[Tuple[str, int]]) -> Dict[str, dict]:
        usage: Dict[str, dict] = {}
        for group, page_index in sorted(selected_pages):
            location = self._page_display_name(group, page_index)
            for slot_index, slot in enumerate(self.data[group][page_index]):
                if not slot.assigned or slot.marker:
                    continue
                path = str(slot.file_path or "").strip()
                normalized = os.path.normcase(os.path.abspath(path))
                if normalized not in usage:
                    usage[normalized] = {"source_path": path, "slots": []}
                usage[normalized]["slots"].append(
                    {
                        "group": group,
                        "page": page_index,
                        "slot": slot_index,
                        "location": location,
                        "title": slot.title.strip() or os.path.splitext(os.path.basename(path))[0],
                    }
                )
        return usage

    def _collect_pack_lyric_path_usage(self, selected_pages: set[Tuple[str, int]]) -> Dict[str, dict]:
        usage: Dict[str, dict] = {}
        for group, page_index in sorted(selected_pages):
            location = self._page_display_name(group, page_index)
            for slot_index, slot in enumerate(self.data[group][page_index]):
                lyric_path = str(slot.lyric_file or "").strip()
                if not lyric_path:
                    continue
                normalized = os.path.normcase(os.path.abspath(lyric_path))
                if normalized not in usage:
                    usage[normalized] = {"source_path": lyric_path, "slots": []}
                usage[normalized]["slots"].append(
                    {
                        "group": group,
                        "page": page_index,
                        "slot": slot_index,
                        "location": location,
                        "title": slot.title.strip() or "",
                    }
                )
        return usage

    def _update_archive_progress(self, progress: QProgressDialog, current: int, total: int, label: str) -> None:
        progress.setMaximum(max(1, total))
        progress.setValue(max(0, min(current, max(1, total))))
        progress.setLabelText(label)
        QApplication.processEvents()

    @staticmethod
    def _encode_pack_page_key(group: str, page_index: int) -> str:
        return f"{group}:{page_index}"

    @staticmethod
    def _decode_pack_page_key(value: str) -> Optional[Tuple[str, int]]:
        raw = str(value or "").strip()
        if ":" not in raw:
            return None
        group, page_value = raw.split(":", 1)
        group = group.strip().upper()
        if group not in GROUPS:
            return None
        try:
            page_index = int(page_value)
        except ValueError:
            return None
        if page_index < 0 or page_index >= PAGE_COUNT:
            return None
        return group, page_index

    def _backup_keyboard_hotkey_bindings(self) -> None:
        payload = {
            "type": "pyssp_keyboard_hotkey_bindings",
            "version": 1,
            "hotkeys": {k: [v[0], v[1]] for k, v in self.hotkeys.items()},
            "quick_action_enabled": bool(self.quick_action_enabled),
            "quick_action_keys": list(self.quick_action_keys[:48]),
            "sound_button_hotkey_enabled": bool(self.sound_button_hotkey_enabled),
            "sound_button_hotkey_priority": str(self.sound_button_hotkey_priority),
            "sound_button_hotkey_go_to_playing": bool(self.sound_button_hotkey_go_to_playing),
        }
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_path = os.path.join(self._default_backup_dir(), f"keyboard_hotkeys_backup_{stamp}.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Keyboard Hotkey Bindings",
            initial_path,
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path = f"{file_path}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.critical(self, "Backup Keyboard Hotkey Bindings", f"Could not write backup file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Backup Keyboard Hotkey Bindings", f"Backup saved:\n{file_path}")

    def _restore_keyboard_hotkey_bindings(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Keyboard Hotkey Bindings",
            self._default_backup_dir(),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            QMessageBox.critical(self, "Restore Keyboard Hotkey Bindings", f"Could not read backup file:\n{exc}")
            return
        if not isinstance(payload, dict):
            QMessageBox.critical(self, "Restore Keyboard Hotkey Bindings", "Invalid backup format.")
            return

        raw_hotkeys = payload.get("hotkeys", {})
        next_hotkeys: Dict[str, tuple[str, str]] = {}
        for key in HOTKEY_DEFAULTS.keys():
            default_pair = HOTKEY_DEFAULTS.get(key, ("", ""))
            raw_pair = raw_hotkeys.get(key, default_pair) if isinstance(raw_hotkeys, dict) else default_pair
            v1 = str(raw_pair[0]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 1 else str(default_pair[0])
            v2 = str(raw_pair[1]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 2 else str(default_pair[1])
            next_hotkeys[key] = (v1, v2)

        raw_quick = payload.get("quick_action_keys", [])
        next_quick: List[str] = []
        if isinstance(raw_quick, list):
            next_quick = [str(v).strip() for v in raw_quick[:48]]
        if len(next_quick) < 48:
            next_quick.extend(["" for _ in range(48 - len(next_quick))])

        self.hotkeys = next_hotkeys
        self.quick_action_enabled = self._coerce_bool(payload.get("quick_action_enabled", self.quick_action_enabled))
        self.quick_action_keys = next_quick
        self.sound_button_hotkey_enabled = self._coerce_bool(
            payload.get("sound_button_hotkey_enabled", self.sound_button_hotkey_enabled)
        )
        priority = str(payload.get("sound_button_hotkey_priority", self.sound_button_hotkey_priority)).strip()
        self.sound_button_hotkey_priority = (
            priority if priority in {"system_first", "sound_button_first"} else "system_first"
        )
        self.sound_button_hotkey_go_to_playing = self._coerce_bool(
            payload.get("sound_button_hotkey_go_to_playing", self.sound_button_hotkey_go_to_playing)
        )
        self._apply_hotkeys()
        self._save_settings()
        QMessageBox.information(self, "Restore Keyboard Hotkey Bindings", "Keyboard hotkey bindings restored.")

    def _backup_midi_bindings(self) -> None:
        payload = {
            "type": "pyssp_midi_bindings",
            "version": 1,
            "midi_input_device_ids": list(self.midi_input_device_ids),
            "midi_hotkeys": {k: [v[0], v[1]] for k, v in self.midi_hotkeys.items()},
            "midi_quick_action_enabled": bool(self.midi_quick_action_enabled),
            "midi_quick_action_bindings": list(self.midi_quick_action_bindings[:48]),
            "midi_sound_button_hotkey_enabled": bool(self.midi_sound_button_hotkey_enabled),
            "midi_sound_button_hotkey_priority": str(self.midi_sound_button_hotkey_priority),
            "midi_sound_button_hotkey_go_to_playing": bool(self.midi_sound_button_hotkey_go_to_playing),
            "midi_rotary_enabled": bool(self.midi_rotary_enabled),
            "midi_rotary_group_binding": self.midi_rotary_group_binding,
            "midi_rotary_page_binding": self.midi_rotary_page_binding,
            "midi_rotary_sound_button_binding": self.midi_rotary_sound_button_binding,
            "midi_rotary_jog_binding": self.midi_rotary_jog_binding,
            "midi_rotary_volume_binding": self.midi_rotary_volume_binding,
            "midi_rotary_group_invert": bool(self.midi_rotary_group_invert),
            "midi_rotary_page_invert": bool(self.midi_rotary_page_invert),
            "midi_rotary_sound_button_invert": bool(self.midi_rotary_sound_button_invert),
            "midi_rotary_jog_invert": bool(self.midi_rotary_jog_invert),
            "midi_rotary_volume_invert": bool(self.midi_rotary_volume_invert),
            "midi_rotary_group_sensitivity": int(self.midi_rotary_group_sensitivity),
            "midi_rotary_page_sensitivity": int(self.midi_rotary_page_sensitivity),
            "midi_rotary_sound_button_sensitivity": int(self.midi_rotary_sound_button_sensitivity),
            "midi_rotary_group_relative_mode": self.midi_rotary_group_relative_mode,
            "midi_rotary_page_relative_mode": self.midi_rotary_page_relative_mode,
            "midi_rotary_sound_button_relative_mode": self.midi_rotary_sound_button_relative_mode,
            "midi_rotary_jog_relative_mode": self.midi_rotary_jog_relative_mode,
            "midi_rotary_volume_relative_mode": self.midi_rotary_volume_relative_mode,
            "midi_rotary_volume_mode": self.midi_rotary_volume_mode,
            "midi_rotary_volume_step": int(self.midi_rotary_volume_step),
            "midi_rotary_jog_step_ms": int(self.midi_rotary_jog_step_ms),
        }
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        initial_path = os.path.join(self._default_backup_dir(), f"midi_bindings_backup_{stamp}.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup MIDI Bindings",
            initial_path,
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path = f"{file_path}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception as exc:
            QMessageBox.critical(self, "Backup MIDI Bindings", f"Could not write backup file:\n{exc}")
            return
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        QMessageBox.information(self, "Backup MIDI Bindings", f"Backup saved:\n{file_path}")

    def _restore_midi_bindings(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore MIDI Bindings",
            self._default_backup_dir(),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            QMessageBox.critical(self, "Restore MIDI Bindings", f"Could not read backup file:\n{exc}")
            return
        if not isinstance(payload, dict):
            QMessageBox.critical(self, "Restore MIDI Bindings", "Invalid backup format.")
            return

        raw_hotkeys = payload.get("midi_hotkeys", {})
        next_midi_hotkeys: Dict[str, tuple[str, str]] = {}
        for key in MIDI_HOTKEY_DEFAULTS.keys():
            raw_pair = raw_hotkeys.get(key, ("", "")) if isinstance(raw_hotkeys, dict) else ("", "")
            v1 = str(raw_pair[0]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 1 else ""
            v2 = str(raw_pair[1]).strip() if isinstance(raw_pair, (list, tuple)) and len(raw_pair) >= 2 else ""
            next_midi_hotkeys[key] = (normalize_midi_binding(v1), normalize_midi_binding(v2))

        raw_midi_quick = payload.get("midi_quick_action_bindings", [])
        next_midi_quick: List[str] = []
        if isinstance(raw_midi_quick, list):
            next_midi_quick = [normalize_midi_binding(str(v).strip()) for v in raw_midi_quick[:48]]
        if len(next_midi_quick) < 48:
            next_midi_quick.extend(["" for _ in range(48 - len(next_midi_quick))])

        raw_inputs = payload.get("midi_input_device_ids", [])
        midi_inputs = [str(v).strip() for v in raw_inputs] if isinstance(raw_inputs, list) else []
        self.midi_input_device_ids = self._normalize_midi_input_selectors([v for v in midi_inputs if v])
        self.midi_hotkeys = next_midi_hotkeys
        self.midi_quick_action_enabled = self._coerce_bool(
            payload.get("midi_quick_action_enabled", self.midi_quick_action_enabled)
        )
        self.midi_quick_action_bindings = next_midi_quick
        self.midi_sound_button_hotkey_enabled = self._coerce_bool(
            payload.get("midi_sound_button_hotkey_enabled", self.midi_sound_button_hotkey_enabled)
        )
        midi_prio = str(payload.get("midi_sound_button_hotkey_priority", self.midi_sound_button_hotkey_priority)).strip()
        self.midi_sound_button_hotkey_priority = (
            midi_prio if midi_prio in {"system_first", "sound_button_first"} else "system_first"
        )
        self.midi_sound_button_hotkey_go_to_playing = self._coerce_bool(
            payload.get("midi_sound_button_hotkey_go_to_playing", self.midi_sound_button_hotkey_go_to_playing)
        )
        self.midi_rotary_enabled = self._coerce_bool(payload.get("midi_rotary_enabled", self.midi_rotary_enabled))
        self.midi_rotary_group_binding = normalize_midi_binding(str(payload.get("midi_rotary_group_binding", "")))
        self.midi_rotary_page_binding = normalize_midi_binding(str(payload.get("midi_rotary_page_binding", "")))
        self.midi_rotary_sound_button_binding = normalize_midi_binding(str(payload.get("midi_rotary_sound_button_binding", "")))
        self.midi_rotary_jog_binding = normalize_midi_binding(str(payload.get("midi_rotary_jog_binding", "")))
        self.midi_rotary_volume_binding = normalize_midi_binding(str(payload.get("midi_rotary_volume_binding", "")))
        self.midi_rotary_group_invert = self._coerce_bool(payload.get("midi_rotary_group_invert", self.midi_rotary_group_invert))
        self.midi_rotary_page_invert = self._coerce_bool(payload.get("midi_rotary_page_invert", self.midi_rotary_page_invert))
        self.midi_rotary_sound_button_invert = self._coerce_bool(payload.get("midi_rotary_sound_button_invert", self.midi_rotary_sound_button_invert))
        self.midi_rotary_jog_invert = self._coerce_bool(payload.get("midi_rotary_jog_invert", self.midi_rotary_jog_invert))
        self.midi_rotary_volume_invert = self._coerce_bool(payload.get("midi_rotary_volume_invert", self.midi_rotary_volume_invert))
        self.midi_rotary_group_sensitivity = self._coerce_int(
            payload.get("midi_rotary_group_sensitivity", self.midi_rotary_group_sensitivity),
            self.midi_rotary_group_sensitivity,
            1,
            20,
        )
        self.midi_rotary_page_sensitivity = self._coerce_int(
            payload.get("midi_rotary_page_sensitivity", self.midi_rotary_page_sensitivity),
            self.midi_rotary_page_sensitivity,
            1,
            20,
        )
        self.midi_rotary_sound_button_sensitivity = self._coerce_int(
            payload.get("midi_rotary_sound_button_sensitivity", self.midi_rotary_sound_button_sensitivity),
            self.midi_rotary_sound_button_sensitivity,
            1,
            20,
        )
        self.midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_group_relative_mode", self.midi_rotary_group_relative_mode))
        )
        self.midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_page_relative_mode", self.midi_rotary_page_relative_mode))
        )
        self.midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_sound_button_relative_mode", self.midi_rotary_sound_button_relative_mode))
        )
        self.midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_jog_relative_mode", self.midi_rotary_jog_relative_mode))
        )
        self.midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            str(payload.get("midi_rotary_volume_relative_mode", self.midi_rotary_volume_relative_mode))
        )
        mode = str(payload.get("midi_rotary_volume_mode", self.midi_rotary_volume_mode)).strip().lower()
        self.midi_rotary_volume_mode = mode if mode in {"absolute", "relative"} else "relative"
        self.midi_rotary_volume_step = self._coerce_int(
            payload.get("midi_rotary_volume_step", self.midi_rotary_volume_step),
            self.midi_rotary_volume_step,
            1,
            20,
        )
        self.midi_rotary_jog_step_ms = self._coerce_int(
            payload.get("midi_rotary_jog_step_ms", self.midi_rotary_jog_step_ms),
            self.midi_rotary_jog_step_ms,
            10,
            5000,
        )
        self._apply_hotkeys()
        self._save_settings()
        QMessageBox.information(self, "Restore MIDI Bindings", "MIDI bindings restored.")

    def _normalized_hotkey_pair(self, action_key: str) -> tuple[str, str]:
        raw1, raw2 = self.hotkeys.get(action_key, HOTKEY_DEFAULTS.get(action_key, ("", "")))
        seq1 = self._normalize_hotkey_text(raw1)
        seq2 = self._normalize_hotkey_text(raw2)
        if seq2 == seq1:
            seq2 = ""
        return seq1, seq2

    def _normalize_hotkey_text(self, value: str) -> str:
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

    def _key_sequence_from_hotkey_text(self, value: str) -> Optional[QKeySequence]:
        text = self._normalize_hotkey_text(value)
        if not text:
            return None
        if text == "Shift":
            return QKeySequence(int(Qt.SHIFT))
        if text == "Ctrl":
            return QKeySequence(int(Qt.CTRL))
        if text == "Alt":
            return QKeySequence(int(Qt.ALT))
        if text == "Meta":
            return QKeySequence(int(Qt.META))
        return QKeySequence(text)

    def _modifier_key_from_hotkey_text(self, value: str) -> Optional[int]:
        text = self._normalize_hotkey_text(value)
        if text == "Shift":
            return int(Qt.Key_Shift)
        if text == "Ctrl":
            return int(Qt.Key_Control)
        if text == "Alt":
            return int(Qt.Key_Alt)
        if text == "Meta":
            return int(Qt.Key_Meta)
        return None

    def _apply_hotkeys(self) -> None:
        for key in ["new_set", "open_set", "save_set", "save_set_as", "search", "options"]:
            action = self._menu_actions.get(key)
            if action is None:
                continue
            h1, h2 = self._normalized_hotkey_pair(key)
            sequences: List[QKeySequence] = []
            for text in [h1, h2]:
                seq = self._key_sequence_from_hotkey_text(text)
                if seq is not None:
                    sequences.append(seq)
            action.setShortcuts(sequences)

        for sc in self._runtime_hotkey_shortcuts:
            try:
                sc.activated.disconnect()
            except Exception:
                pass
            sc.setParent(None)
            sc.deleteLater()
        self._runtime_hotkey_shortcuts = []
        self._modifier_hotkey_handlers = {}
        self._modifier_hotkey_down.clear()

        runtime_handlers = self._runtime_action_handlers()
        ordered_system_keys: List[str] = [k for k in SYSTEM_HOTKEY_ORDER_DEFAULT if k in runtime_handlers]

        sound_bindings = self._collect_sound_button_hotkey_bindings() if self.sound_button_hotkey_enabled else {}
        registered_keys: set[str] = set()

        for key in ordered_system_keys:
            handler = runtime_handlers[key]
            source_name = "lock_toggle" if key == "lock_toggle" else "system"
            wrapped_handler = (lambda fn=handler, source=source_name: self._run_locked_input(source, fn))
            h1, h2 = self._normalized_hotkey_pair(key)
            for seq_text in [h1, h2]:
                key_token = self._normalize_hotkey_text(seq_text)
                if self.sound_button_hotkey_enabled and self.sound_button_hotkey_priority == "sound_button_first":
                    if key_token and key_token in sound_bindings:
                        continue
                modifier_key = self._modifier_key_from_hotkey_text(seq_text)
                if modifier_key is not None:
                    handlers = self._modifier_hotkey_handlers.setdefault(modifier_key, [])
                    if wrapped_handler not in handlers:
                        handlers.append(wrapped_handler)
                        key_name = self._normalize_hotkey_text(seq_text)
                        if key_name:
                            registered_keys.add(key_name)
                    continue
                seq = self._key_sequence_from_hotkey_text(seq_text)
                if seq is None:
                    continue
                shortcut = QShortcut(seq, self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.activated.connect(wrapped_handler)
                self._runtime_hotkey_shortcuts.append(shortcut)
                if key_token:
                    registered_keys.add(key_token)

        if self.quick_action_enabled:
            for idx, raw in enumerate(self.quick_action_keys[:48]):
                key_token = self._normalize_hotkey_text(raw)
                if self.sound_button_hotkey_enabled and self.sound_button_hotkey_priority == "sound_button_first":
                    if key_token and key_token in sound_bindings:
                        continue
                seq = self._key_sequence_from_hotkey_text(raw)
                if seq is None:
                    continue
                shortcut = QShortcut(seq, self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.activated.connect(
                    lambda slot=idx: self._run_locked_input("quick_action", lambda: self._quick_action_trigger(slot))
                )
                self._runtime_hotkey_shortcuts.append(shortcut)
                if key_token:
                    registered_keys.add(key_token)

        if self.sound_button_hotkey_enabled:
            for key_token, slot_key in sound_bindings.items():
                if self.sound_button_hotkey_priority == "system_first" and key_token in registered_keys:
                    continue
                seq = self._key_sequence_from_hotkey_text(key_token)
                if seq is None:
                    continue
                shortcut = QShortcut(seq, self)
                shortcut.setContext(Qt.ApplicationShortcut)
                shortcut.activated.connect(
                    lambda sk=slot_key: self._run_locked_input("sound_button", lambda: self._sound_button_hotkey_trigger(sk))
                )
                self._runtime_hotkey_shortcuts.append(shortcut)
        self._apply_midi_bindings()
        self._sync_lock_ui_state()

    def _runtime_action_handlers(self) -> Dict[str, Callable[[], None]]:
        return {
            "play_selected_pause": self._hotkey_play_selected_pause,
            "play_selected": self._hotkey_play_selected,
            "pause_toggle": self._toggle_pause,
            "stop_playback": self._handle_space_bar_action,
            "talk": self._hotkey_toggle_talk,
            "next_group": lambda: self._hotkey_select_group_delta(1),
            "prev_group": lambda: self._hotkey_select_group_delta(-1),
            "next_page": lambda: self._hotkey_select_page_delta(1),
            "prev_page": lambda: self._hotkey_select_page_delta(-1),
            "next_sound_button": lambda: self._hotkey_select_sound_button_delta(1),
            "prev_sound_button": lambda: self._hotkey_select_sound_button_delta(-1),
            "multi_play": lambda: self._toggle_control_button("Multi-Play"),
            "go_to_playing": self._go_to_current_playing_page,
            "loop": lambda: self._toggle_control_button("Loop"),
            "next": self._play_next,
            "rapid_fire": self._on_rapid_fire_clicked,
            "shuffle": lambda: self._toggle_control_button("Shuffle"),
            "reset_page": self._reset_current_page_state,
            "play_list": lambda: self._toggle_control_button("Play List"),
            "fade_in": lambda: self._toggle_control_button("Fade In"),
            "cross_fade": lambda: self._toggle_control_button("X"),
            "fade_out": lambda: self._toggle_control_button("Fade Out"),
            "mute": self._toggle_mute_hotkey,
            "volume_up": self._volume_up_hotkey,
            "volume_down": self._volume_down_hotkey,
            "lock_toggle": self._hotkey_lock_toggle,
            "open_hide_lyric_navigator": self._hotkey_toggle_lyric_navigator,
        }

    def _normalized_midi_pair(self, action_key: str) -> tuple[str, str]:
        raw1, raw2 = self.midi_hotkeys.get(action_key, MIDI_HOTKEY_DEFAULTS.get(action_key, ("", "")))
        return normalize_midi_binding(raw1), normalize_midi_binding(raw2)

    def _normalize_midi_input_selectors(self, selectors: List[str]) -> List[str]:
        wanted: List[str] = []
        seen: set[str] = set()
        known_names_by_id = {str(device_id): str(device_name) for device_id, device_name in list_midi_input_devices()}
        for raw in selectors:
            token = str(raw or "").strip()
            if not token:
                continue
            if token.isdigit() and token in known_names_by_id:
                token = midi_input_name_selector(known_names_by_id[token])
            if token in seen:
                continue
            seen.add(token)
            wanted.append(token)
        return wanted

    def _apply_midi_bindings(self) -> None:
        self._midi_action_handlers = {}
        self._midi_last_trigger_t = {}
        self._midi_router.set_devices(self.midi_input_device_ids)
        self._refresh_midi_connection_warning(force_refresh=False)
        runtime_handlers = self._runtime_action_handlers()
        ordered_system_keys: List[str] = [k for k in SYSTEM_HOTKEY_ORDER_DEFAULT if k in runtime_handlers]
        sound_bindings = self._collect_sound_button_midi_bindings() if self.midi_sound_button_hotkey_enabled else {}
        registered_tokens: set[str] = set()

        for key in ordered_system_keys:
            handler = runtime_handlers[key]
            source_name = "lock_toggle" if key == "lock_toggle" else "midi"
            m1, m2 = self._normalized_midi_pair(key)
            for token in [m1, m2]:
                if not token:
                    continue
                if self.midi_sound_button_hotkey_enabled and self.midi_sound_button_hotkey_priority == "sound_button_first":
                    if token in sound_bindings:
                        continue
                self._midi_action_handlers[token] = (lambda fn=handler, source=source_name: self._run_locked_input(source, fn))
                registered_tokens.add(token)

        if self.midi_quick_action_enabled:
            for idx, raw in enumerate(self.midi_quick_action_bindings[:48]):
                token = normalize_midi_binding(raw)
                if not token:
                    continue
                if self.midi_sound_button_hotkey_enabled and self.midi_sound_button_hotkey_priority == "sound_button_first":
                    if token in sound_bindings:
                        continue
                self._midi_action_handlers[token] = (lambda slot=idx: self._quick_action_trigger(slot))
                registered_tokens.add(token)

        if self.midi_sound_button_hotkey_enabled:
            for token, slot_key in sound_bindings.items():
                if self.midi_sound_button_hotkey_priority == "system_first" and token in registered_tokens:
                    continue
                self._midi_action_handlers[token] = (lambda sk=slot_key: self._sound_button_midi_hotkey_trigger(sk))

    def _restore_last_set_on_startup(self) -> None:
        last_set_path = self.settings.last_set_path.strip()
        if not last_set_path:
            return
        if not os.path.exists(last_set_path):
            self.settings.last_set_path = ""
            self._save_settings()
            return
        self._load_set(last_set_path, show_message=False, restore_last_position=True)
        self._queue_current_page_audio_preload()

    def _has_any_custom_cues(self) -> bool:
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot in self.data[group][page_index]:
                    if self._slot_has_custom_cue(slot):
                        return True
        return False

    def _save_settings(self) -> None:
        self.settings.active_group_color = self.active_group_color
        self.settings.inactive_group_color = self.inactive_group_color
        self.settings.title_char_limit = self.title_char_limit
        self.settings.show_file_notifications = self.show_file_notifications
        self.settings.lock_allow_quit = bool(self.lock_allow_quit)
        self.settings.lock_allow_system_hotkeys = bool(self.lock_allow_system_hotkeys)
        self.settings.lock_allow_quick_action_hotkeys = bool(self.lock_allow_quick_action_hotkeys)
        self.settings.lock_allow_sound_button_hotkeys = bool(self.lock_allow_sound_button_hotkeys)
        self.settings.lock_allow_midi_control = bool(self.lock_allow_midi_control)
        self.settings.lock_auto_allow_quit = bool(self.lock_auto_allow_quit)
        self.settings.lock_auto_allow_midi_control = bool(self.lock_auto_allow_midi_control)
        self.settings.lock_unlock_method = self.lock_unlock_method
        self.settings.lock_require_password = bool(self.lock_require_password)
        self.settings.lock_password = self.lock_password
        self.settings.lock_restart_state = self.lock_restart_state
        self.settings.lock_was_locked_on_exit = bool(self._ui_locked)
        self.settings.volume = (
            self.volume_slider.value() if self.volume_slider is not None else self._logical_player_volume(self.player)
        )
        self.settings.last_set_path = self.current_set_path
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self.settings.fade_in_sec = self.fade_in_sec
        self.settings.cross_fade_sec = self.cross_fade_sec
        self.settings.fade_out_sec = self.fade_out_sec
        self.settings.fade_on_quick_action_hotkey = bool(self.fade_on_quick_action_hotkey)
        self.settings.fade_on_sound_button_hotkey = bool(self.fade_on_sound_button_hotkey)
        self.settings.fade_on_pause = bool(self.fade_on_pause)
        self.settings.fade_on_resume = bool(self.fade_on_resume)
        self.settings.fade_on_stop = bool(self.fade_on_stop)
        self.settings.fade_out_when_done_playing = bool(self.fade_out_when_done_playing)
        self.settings.fade_out_end_lead_sec = float(self.fade_out_end_lead_sec)
        self.settings.vocal_removed_toggle_fade_mode = str(self.vocal_removed_toggle_fade_mode)
        self.settings.vocal_removed_toggle_custom_sec = float(self.vocal_removed_toggle_custom_sec)
        self.settings.vocal_removed_toggle_always_sec = float(self.vocal_removed_toggle_always_sec)
        self.settings.talk_volume_level = self.talk_volume_level
        self.settings.talk_fade_sec = self.talk_fade_sec
        self.settings.talk_volume_mode = self.talk_volume_mode
        self.settings.talk_blink_button = self.talk_blink_button
        self.settings.log_file_enabled = self.log_file_enabled
        self.settings.reset_all_on_startup = self.reset_all_on_startup
        self.settings.click_playing_action = self.click_playing_action
        self.settings.search_double_click_action = self.search_double_click_action
        self.settings.set_file_encoding = self.set_file_encoding
        self.settings.ui_language = self.ui_language
        self.settings.app_version = str(self.app_version_text or "")
        self.settings.app_build_id = str(self.app_build_text or "")
        self.settings.tips_open_on_startup = bool(self.tips_open_on_startup)
        self.settings.audio_output_device = self.audio_output_device
        self.settings.preload_audio_enabled = bool(self.preload_audio_enabled)
        self.settings.preload_current_page_audio = bool(self.preload_current_page_audio)
        self.settings.preload_audio_memory_limit_mb = int(self.preload_audio_memory_limit_mb)
        self.settings.preload_memory_pressure_enabled = bool(self.preload_memory_pressure_enabled)
        self.settings.preload_pause_on_playback = bool(self.preload_pause_on_playback)
        self.settings.preload_use_ffmpeg = bool(self.preload_use_ffmpeg)
        self.settings.waveform_cache_limit_mb = int(self.waveform_cache_limit_mb)
        self.settings.waveform_cache_clear_on_launch = bool(self.waveform_cache_clear_on_launch)
        self.settings.max_multi_play_songs = self.max_multi_play_songs
        self.settings.multi_play_limit_action = self.multi_play_limit_action
        self.settings.playlist_play_mode = self.playlist_play_mode
        self.settings.rapid_fire_play_mode = self.rapid_fire_play_mode
        self.settings.next_play_mode = self.next_play_mode
        self.settings.playlist_loop_mode = self.playlist_loop_mode
        self.settings.candidate_error_action = self.candidate_error_action
        self.settings.web_remote_enabled = self.web_remote_enabled
        self.settings.web_remote_port = self.web_remote_port
        self.settings.web_remote_ws_port = self.web_remote_ws_port
        self.settings.timecode_audio_output_device = self.timecode_audio_output_device
        self.settings.timecode_midi_output_device = self.timecode_midi_output_device
        self.settings.timecode_mode = self.timecode_mode
        self.settings.timecode_fps = self.timecode_fps
        self.settings.timecode_mtc_fps = self.timecode_mtc_fps
        self.settings.timecode_mtc_idle_behavior = self.timecode_mtc_idle_behavior
        self.settings.timecode_sample_rate = self.timecode_sample_rate
        self.settings.timecode_bit_depth = self.timecode_bit_depth
        self.settings.show_timecode_panel = bool(self.show_timecode_panel)
        self.settings.timecode_timeline_mode = self.timecode_timeline_mode
        self.settings.soundbutton_timecode_offset_enabled = bool(self.soundbutton_timecode_offset_enabled)
        self.settings.respect_soundbutton_timecode_timeline_setting = bool(
            self.respect_soundbutton_timecode_timeline_setting
        )
        self.settings.main_transport_timeline_mode = self.main_transport_timeline_mode
        self.settings.main_progress_display_mode = self.main_progress_display_mode
        self.settings.main_progress_show_text = bool(self.main_progress_show_text)
        self.settings.main_jog_outside_cue_action = self.main_jog_outside_cue_action
        self.settings.color_empty = self.state_colors["empty"]
        self.settings.color_unplayed = self.state_colors["assigned"]
        self.settings.color_highlight = self.state_colors["highlighted"]
        self.settings.color_playing = self.state_colors["playing"]
        self.settings.color_played = self.state_colors["played"]
        self.settings.color_error = self.state_colors["missing"]
        self.settings.color_lock = self.state_colors["locked"]
        self.settings.color_place_marker = self.state_colors["marker"]
        self.settings.color_copied_to_cue = self.state_colors["copied"]
        self.settings.color_cue_indicator = self.state_colors["cue_indicator"]
        self.settings.color_volume_indicator = self.state_colors["volume_indicator"]
        self.settings.color_midi_indicator = self.state_colors["midi_indicator"]
        self.settings.color_lyric_indicator = self.state_colors["lyric_indicator"]
        self.settings.sound_button_text_color = self.sound_button_text_color
        self.settings.hotkey_new_set_1 = self.hotkeys.get("new_set", ("Ctrl+N", ""))[0]
        self.settings.hotkey_new_set_2 = self.hotkeys.get("new_set", ("Ctrl+N", ""))[1]
        self.settings.hotkey_open_set_1 = self.hotkeys.get("open_set", ("Ctrl+O", ""))[0]
        self.settings.hotkey_open_set_2 = self.hotkeys.get("open_set", ("Ctrl+O", ""))[1]
        self.settings.hotkey_save_set_1 = self.hotkeys.get("save_set", ("Ctrl+S", ""))[0]
        self.settings.hotkey_save_set_2 = self.hotkeys.get("save_set", ("Ctrl+S", ""))[1]
        self.settings.hotkey_save_set_as_1 = self.hotkeys.get("save_set_as", ("Ctrl+Shift+S", ""))[0]
        self.settings.hotkey_save_set_as_2 = self.hotkeys.get("save_set_as", ("Ctrl+Shift+S", ""))[1]
        self.settings.hotkey_search_1 = self.hotkeys.get("search", ("Ctrl+F", ""))[0]
        self.settings.hotkey_search_2 = self.hotkeys.get("search", ("Ctrl+F", ""))[1]
        self.settings.hotkey_options_1 = self.hotkeys.get("options", ("", ""))[0]
        self.settings.hotkey_options_2 = self.hotkeys.get("options", ("", ""))[1]
        self.settings.hotkey_play_selected_pause_1 = self.hotkeys.get("play_selected_pause", ("", ""))[0]
        self.settings.hotkey_play_selected_pause_2 = self.hotkeys.get("play_selected_pause", ("", ""))[1]
        self.settings.hotkey_play_selected_1 = self.hotkeys.get("play_selected", ("", ""))[0]
        self.settings.hotkey_play_selected_2 = self.hotkeys.get("play_selected", ("", ""))[1]
        self.settings.hotkey_pause_toggle_1 = self.hotkeys.get("pause_toggle", ("P", ""))[0]
        self.settings.hotkey_pause_toggle_2 = self.hotkeys.get("pause_toggle", ("P", ""))[1]
        self.settings.hotkey_stop_playback_1 = self.hotkeys.get("stop_playback", ("Space", "Return"))[0]
        self.settings.hotkey_stop_playback_2 = self.hotkeys.get("stop_playback", ("Space", "Return"))[1]
        self.settings.hotkey_talk_1 = self.hotkeys.get("talk", ("", ""))[0]
        self.settings.hotkey_talk_2 = self.hotkeys.get("talk", ("", ""))[1]
        self.settings.hotkey_next_group_1 = self.hotkeys.get("next_group", ("", ""))[0]
        self.settings.hotkey_next_group_2 = self.hotkeys.get("next_group", ("", ""))[1]
        self.settings.hotkey_prev_group_1 = self.hotkeys.get("prev_group", ("", ""))[0]
        self.settings.hotkey_prev_group_2 = self.hotkeys.get("prev_group", ("", ""))[1]
        self.settings.hotkey_next_page_1 = self.hotkeys.get("next_page", ("", ""))[0]
        self.settings.hotkey_next_page_2 = self.hotkeys.get("next_page", ("", ""))[1]
        self.settings.hotkey_prev_page_1 = self.hotkeys.get("prev_page", ("", ""))[0]
        self.settings.hotkey_prev_page_2 = self.hotkeys.get("prev_page", ("", ""))[1]
        self.settings.hotkey_next_sound_button_1 = self.hotkeys.get("next_sound_button", ("", ""))[0]
        self.settings.hotkey_next_sound_button_2 = self.hotkeys.get("next_sound_button", ("", ""))[1]
        self.settings.hotkey_prev_sound_button_1 = self.hotkeys.get("prev_sound_button", ("", ""))[0]
        self.settings.hotkey_prev_sound_button_2 = self.hotkeys.get("prev_sound_button", ("", ""))[1]
        self.settings.hotkey_multi_play_1 = self.hotkeys.get("multi_play", ("", ""))[0]
        self.settings.hotkey_multi_play_2 = self.hotkeys.get("multi_play", ("", ""))[1]
        self.settings.hotkey_go_to_playing_1 = self.hotkeys.get("go_to_playing", ("", ""))[0]
        self.settings.hotkey_go_to_playing_2 = self.hotkeys.get("go_to_playing", ("", ""))[1]
        self.settings.hotkey_loop_1 = self.hotkeys.get("loop", ("", ""))[0]
        self.settings.hotkey_loop_2 = self.hotkeys.get("loop", ("", ""))[1]
        self.settings.hotkey_next_1 = self.hotkeys.get("next", ("", ""))[0]
        self.settings.hotkey_next_2 = self.hotkeys.get("next", ("", ""))[1]
        self.settings.hotkey_rapid_fire_1 = self.hotkeys.get("rapid_fire", ("", ""))[0]
        self.settings.hotkey_rapid_fire_2 = self.hotkeys.get("rapid_fire", ("", ""))[1]
        self.settings.hotkey_shuffle_1 = self.hotkeys.get("shuffle", ("", ""))[0]
        self.settings.hotkey_shuffle_2 = self.hotkeys.get("shuffle", ("", ""))[1]
        self.settings.hotkey_reset_page_1 = self.hotkeys.get("reset_page", ("", ""))[0]
        self.settings.hotkey_reset_page_2 = self.hotkeys.get("reset_page", ("", ""))[1]
        self.settings.hotkey_play_list_1 = self.hotkeys.get("play_list", ("", ""))[0]
        self.settings.hotkey_play_list_2 = self.hotkeys.get("play_list", ("", ""))[1]
        self.settings.hotkey_fade_in_1 = self.hotkeys.get("fade_in", ("", ""))[0]
        self.settings.hotkey_fade_in_2 = self.hotkeys.get("fade_in", ("", ""))[1]
        self.settings.hotkey_cross_fade_1 = self.hotkeys.get("cross_fade", ("", ""))[0]
        self.settings.hotkey_cross_fade_2 = self.hotkeys.get("cross_fade", ("", ""))[1]
        self.settings.hotkey_fade_out_1 = self.hotkeys.get("fade_out", ("", ""))[0]
        self.settings.hotkey_fade_out_2 = self.hotkeys.get("fade_out", ("", ""))[1]
        self.settings.hotkey_mute_1 = self.hotkeys.get("mute", ("", ""))[0]
        self.settings.hotkey_mute_2 = self.hotkeys.get("mute", ("", ""))[1]
        self.settings.hotkey_volume_up_1 = self.hotkeys.get("volume_up", ("", ""))[0]
        self.settings.hotkey_volume_up_2 = self.hotkeys.get("volume_up", ("", ""))[1]
        self.settings.hotkey_volume_down_1 = self.hotkeys.get("volume_down", ("", ""))[0]
        self.settings.hotkey_volume_down_2 = self.hotkeys.get("volume_down", ("", ""))[1]
        self.settings.hotkey_lock_toggle_1 = self.hotkeys.get("lock_toggle", ("", ""))[0]
        self.settings.hotkey_lock_toggle_2 = self.hotkeys.get("lock_toggle", ("", ""))[1]
        self.settings.hotkey_open_hide_lyric_navigator_1 = self.hotkeys.get("open_hide_lyric_navigator", ("", ""))[0]
        self.settings.hotkey_open_hide_lyric_navigator_2 = self.hotkeys.get("open_hide_lyric_navigator", ("", ""))[1]
        self.settings.quick_action_enabled = bool(self.quick_action_enabled)
        self.settings.quick_action_keys = list(self.quick_action_keys[:48])
        self.settings.sound_button_hotkey_enabled = bool(self.sound_button_hotkey_enabled)
        self.settings.sound_button_hotkey_priority = self.sound_button_hotkey_priority
        self.settings.sound_button_hotkey_go_to_playing = bool(self.sound_button_hotkey_go_to_playing)
        self.settings.midi_input_device_ids = list(self.midi_input_device_ids)
        self.settings.midi_hotkey_new_set_1 = self.midi_hotkeys.get("new_set", ("", ""))[0]
        self.settings.midi_hotkey_new_set_2 = self.midi_hotkeys.get("new_set", ("", ""))[1]
        self.settings.midi_hotkey_open_set_1 = self.midi_hotkeys.get("open_set", ("", ""))[0]
        self.settings.midi_hotkey_open_set_2 = self.midi_hotkeys.get("open_set", ("", ""))[1]
        self.settings.midi_hotkey_save_set_1 = self.midi_hotkeys.get("save_set", ("", ""))[0]
        self.settings.midi_hotkey_save_set_2 = self.midi_hotkeys.get("save_set", ("", ""))[1]
        self.settings.midi_hotkey_save_set_as_1 = self.midi_hotkeys.get("save_set_as", ("", ""))[0]
        self.settings.midi_hotkey_save_set_as_2 = self.midi_hotkeys.get("save_set_as", ("", ""))[1]
        self.settings.midi_hotkey_search_1 = self.midi_hotkeys.get("search", ("", ""))[0]
        self.settings.midi_hotkey_search_2 = self.midi_hotkeys.get("search", ("", ""))[1]
        self.settings.midi_hotkey_options_1 = self.midi_hotkeys.get("options", ("", ""))[0]
        self.settings.midi_hotkey_options_2 = self.midi_hotkeys.get("options", ("", ""))[1]
        self.settings.midi_hotkey_play_selected_pause_1 = self.midi_hotkeys.get("play_selected_pause", ("", ""))[0]
        self.settings.midi_hotkey_play_selected_pause_2 = self.midi_hotkeys.get("play_selected_pause", ("", ""))[1]
        self.settings.midi_hotkey_play_selected_1 = self.midi_hotkeys.get("play_selected", ("", ""))[0]
        self.settings.midi_hotkey_play_selected_2 = self.midi_hotkeys.get("play_selected", ("", ""))[1]
        self.settings.midi_hotkey_pause_toggle_1 = self.midi_hotkeys.get("pause_toggle", ("", ""))[0]
        self.settings.midi_hotkey_pause_toggle_2 = self.midi_hotkeys.get("pause_toggle", ("", ""))[1]
        self.settings.midi_hotkey_stop_playback_1 = self.midi_hotkeys.get("stop_playback", ("", ""))[0]
        self.settings.midi_hotkey_stop_playback_2 = self.midi_hotkeys.get("stop_playback", ("", ""))[1]
        self.settings.midi_hotkey_talk_1 = self.midi_hotkeys.get("talk", ("", ""))[0]
        self.settings.midi_hotkey_talk_2 = self.midi_hotkeys.get("talk", ("", ""))[1]
        self.settings.midi_hotkey_next_group_1 = self.midi_hotkeys.get("next_group", ("", ""))[0]
        self.settings.midi_hotkey_next_group_2 = self.midi_hotkeys.get("next_group", ("", ""))[1]
        self.settings.midi_hotkey_prev_group_1 = self.midi_hotkeys.get("prev_group", ("", ""))[0]
        self.settings.midi_hotkey_prev_group_2 = self.midi_hotkeys.get("prev_group", ("", ""))[1]
        self.settings.midi_hotkey_next_page_1 = self.midi_hotkeys.get("next_page", ("", ""))[0]
        self.settings.midi_hotkey_next_page_2 = self.midi_hotkeys.get("next_page", ("", ""))[1]
        self.settings.midi_hotkey_prev_page_1 = self.midi_hotkeys.get("prev_page", ("", ""))[0]
        self.settings.midi_hotkey_prev_page_2 = self.midi_hotkeys.get("prev_page", ("", ""))[1]
        self.settings.midi_hotkey_next_sound_button_1 = self.midi_hotkeys.get("next_sound_button", ("", ""))[0]
        self.settings.midi_hotkey_next_sound_button_2 = self.midi_hotkeys.get("next_sound_button", ("", ""))[1]
        self.settings.midi_hotkey_prev_sound_button_1 = self.midi_hotkeys.get("prev_sound_button", ("", ""))[0]
        self.settings.midi_hotkey_prev_sound_button_2 = self.midi_hotkeys.get("prev_sound_button", ("", ""))[1]
        self.settings.midi_hotkey_multi_play_1 = self.midi_hotkeys.get("multi_play", ("", ""))[0]
        self.settings.midi_hotkey_multi_play_2 = self.midi_hotkeys.get("multi_play", ("", ""))[1]
        self.settings.midi_hotkey_go_to_playing_1 = self.midi_hotkeys.get("go_to_playing", ("", ""))[0]
        self.settings.midi_hotkey_go_to_playing_2 = self.midi_hotkeys.get("go_to_playing", ("", ""))[1]
        self.settings.midi_hotkey_loop_1 = self.midi_hotkeys.get("loop", ("", ""))[0]
        self.settings.midi_hotkey_loop_2 = self.midi_hotkeys.get("loop", ("", ""))[1]
        self.settings.midi_hotkey_next_1 = self.midi_hotkeys.get("next", ("", ""))[0]
        self.settings.midi_hotkey_next_2 = self.midi_hotkeys.get("next", ("", ""))[1]
        self.settings.midi_hotkey_rapid_fire_1 = self.midi_hotkeys.get("rapid_fire", ("", ""))[0]
        self.settings.midi_hotkey_rapid_fire_2 = self.midi_hotkeys.get("rapid_fire", ("", ""))[1]
        self.settings.midi_hotkey_shuffle_1 = self.midi_hotkeys.get("shuffle", ("", ""))[0]
        self.settings.midi_hotkey_shuffle_2 = self.midi_hotkeys.get("shuffle", ("", ""))[1]
        self.settings.midi_hotkey_reset_page_1 = self.midi_hotkeys.get("reset_page", ("", ""))[0]
        self.settings.midi_hotkey_reset_page_2 = self.midi_hotkeys.get("reset_page", ("", ""))[1]
        self.settings.midi_hotkey_play_list_1 = self.midi_hotkeys.get("play_list", ("", ""))[0]
        self.settings.midi_hotkey_play_list_2 = self.midi_hotkeys.get("play_list", ("", ""))[1]
        self.settings.midi_hotkey_fade_in_1 = self.midi_hotkeys.get("fade_in", ("", ""))[0]
        self.settings.midi_hotkey_fade_in_2 = self.midi_hotkeys.get("fade_in", ("", ""))[1]
        self.settings.midi_hotkey_cross_fade_1 = self.midi_hotkeys.get("cross_fade", ("", ""))[0]
        self.settings.midi_hotkey_cross_fade_2 = self.midi_hotkeys.get("cross_fade", ("", ""))[1]
        self.settings.midi_hotkey_fade_out_1 = self.midi_hotkeys.get("fade_out", ("", ""))[0]
        self.settings.midi_hotkey_fade_out_2 = self.midi_hotkeys.get("fade_out", ("", ""))[1]
        self.settings.midi_hotkey_mute_1 = self.midi_hotkeys.get("mute", ("", ""))[0]
        self.settings.midi_hotkey_mute_2 = self.midi_hotkeys.get("mute", ("", ""))[1]
        self.settings.midi_hotkey_volume_up_1 = self.midi_hotkeys.get("volume_up", ("", ""))[0]
        self.settings.midi_hotkey_volume_up_2 = self.midi_hotkeys.get("volume_up", ("", ""))[1]
        self.settings.midi_hotkey_volume_down_1 = self.midi_hotkeys.get("volume_down", ("", ""))[0]
        self.settings.midi_hotkey_volume_down_2 = self.midi_hotkeys.get("volume_down", ("", ""))[1]
        self.settings.midi_hotkey_lock_toggle_1 = self.midi_hotkeys.get("lock_toggle", ("", ""))[0]
        self.settings.midi_hotkey_lock_toggle_2 = self.midi_hotkeys.get("lock_toggle", ("", ""))[1]
        self.settings.midi_hotkey_open_hide_lyric_navigator_1 = self.midi_hotkeys.get("open_hide_lyric_navigator", ("", ""))[0]
        self.settings.midi_hotkey_open_hide_lyric_navigator_2 = self.midi_hotkeys.get("open_hide_lyric_navigator", ("", ""))[1]
        self.settings.midi_quick_action_enabled = bool(self.midi_quick_action_enabled)
        self.settings.midi_quick_action_bindings = list(self.midi_quick_action_bindings[:48])
        self.settings.midi_sound_button_hotkey_enabled = bool(self.midi_sound_button_hotkey_enabled)
        self.settings.midi_sound_button_hotkey_priority = self.midi_sound_button_hotkey_priority
        self.settings.midi_sound_button_hotkey_go_to_playing = bool(self.midi_sound_button_hotkey_go_to_playing)
        self.settings.midi_rotary_enabled = bool(self.midi_rotary_enabled)
        self.settings.midi_rotary_group_binding = self.midi_rotary_group_binding
        self.settings.midi_rotary_page_binding = self.midi_rotary_page_binding
        self.settings.midi_rotary_sound_button_binding = self.midi_rotary_sound_button_binding
        self.settings.midi_rotary_jog_binding = self.midi_rotary_jog_binding
        self.settings.midi_rotary_volume_binding = self.midi_rotary_volume_binding
        self.settings.midi_rotary_group_invert = bool(self.midi_rotary_group_invert)
        self.settings.midi_rotary_page_invert = bool(self.midi_rotary_page_invert)
        self.settings.midi_rotary_sound_button_invert = bool(self.midi_rotary_sound_button_invert)
        self.settings.midi_rotary_jog_invert = bool(self.midi_rotary_jog_invert)
        self.settings.midi_rotary_volume_invert = bool(self.midi_rotary_volume_invert)
        self.settings.midi_rotary_group_sensitivity = int(self.midi_rotary_group_sensitivity)
        self.settings.midi_rotary_page_sensitivity = int(self.midi_rotary_page_sensitivity)
        self.settings.midi_rotary_sound_button_sensitivity = int(self.midi_rotary_sound_button_sensitivity)
        self.settings.midi_rotary_group_relative_mode = self.midi_rotary_group_relative_mode
        self.settings.midi_rotary_page_relative_mode = self.midi_rotary_page_relative_mode
        self.settings.midi_rotary_sound_button_relative_mode = self.midi_rotary_sound_button_relative_mode
        self.settings.midi_rotary_jog_relative_mode = self.midi_rotary_jog_relative_mode
        self.settings.midi_rotary_volume_relative_mode = self.midi_rotary_volume_relative_mode
        self.settings.midi_rotary_volume_mode = self.midi_rotary_volume_mode
        self.settings.midi_rotary_volume_step = int(self.midi_rotary_volume_step)
        self.settings.midi_rotary_jog_step_ms = int(self.midi_rotary_jog_step_ms)
        self.settings.stage_display_layout = list(self.stage_display_layout)
        self.settings.stage_display_show_current_time = bool(self.stage_display_visibility.get("current_time", True))
        self.settings.stage_display_show_alert = bool(self.stage_display_visibility.get("alert", False))
        self.settings.stage_display_show_total_time = bool(self.stage_display_visibility.get("total_time", True))
        self.settings.stage_display_show_elapsed = bool(self.stage_display_visibility.get("elapsed", True))
        self.settings.stage_display_show_remaining = bool(self.stage_display_visibility.get("remaining", True))
        self.settings.stage_display_show_progress_bar = bool(self.stage_display_visibility.get("progress_bar", True))
        self.settings.stage_display_show_song_name = bool(self.stage_display_visibility.get("song_name", True))
        self.settings.stage_display_show_lyric = bool(self.stage_display_visibility.get("lyric", True))
        self.settings.stage_display_show_next_song = bool(self.stage_display_visibility.get("next_song", True))
        self.settings.stage_display_gadgets = normalize_stage_display_gadgets(self.stage_display_gadgets)
        self.settings.stage_display_text_source = self.stage_display_text_source
        self.settings.now_playing_display_mode = self.now_playing_display_mode
        self.settings.main_ui_lyric_display_mode = self.main_ui_lyric_display_mode
        self.settings.search_lyric_on_add_sound_button = bool(self.search_lyric_on_add_sound_button)
        self.settings.new_lyric_file_format = self.new_lyric_file_format
        self.settings.supported_audio_format_extensions = list(self.supported_audio_format_extensions)
        self.settings.verify_sound_file_on_add = bool(self.verify_sound_file_on_add)
        self.settings.allow_other_unsupported_audio_files = bool(self.allow_other_unsupported_audio_files)
        self.settings.disable_path_safety = bool(self.disable_path_safety)
        self.settings.window_layout = normalize_window_layout(self.window_layout)
        save_settings(self.settings)

