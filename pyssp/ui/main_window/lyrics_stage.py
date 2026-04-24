from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class LyricsStageMixin:
    def _update_now_playing_label(self, text: str) -> None:
        if text:
            self.now_playing_label.set_now_playing_text(tr("NOW PLAYING:"), text)
        else:
            self.now_playing_label.set_now_playing_text(tr("NOW PLAYING:"), "")
        self._refresh_lyric_display()
        self._refresh_stage_display()

    def _update_main_lyric_label(self, text: str) -> None:
        value = str(text or "")
        self.main_lyric_label.set_now_playing_text(tr("LYRIC:"), value)
        mode = str(getattr(self, "main_ui_lyric_display_mode", "always")).strip().lower()
        if mode == "never":
            visible = False
        elif mode == "when_available":
            visible = bool(value.strip())
        else:
            visible = True
        self.main_lyric_label.setVisible(visible)
        if hasattr(self, "lyric_navigator_button") and self.lyric_navigator_button is not None:
            self.lyric_navigator_button.setVisible(visible)
        if hasattr(self, "lyric_blank_toggle_button") and self.lyric_blank_toggle_button is not None:
            self.lyric_blank_toggle_button.setVisible(visible)

    def _toggle_lyric_force_blank(self, checked: bool = False) -> None:
        self._set_lyric_force_blank(bool(checked))

    def _set_lyric_force_blank(self, blank: bool) -> None:
        new_value = bool(blank)
        if new_value == bool(self._lyric_force_blank):
            self._sync_lyric_display_controls()
            return
        self._lyric_force_blank = new_value
        self._sync_lyric_display_controls()
        self._refresh_lyric_display(force=True)

    def _sync_lyric_display_controls(self) -> None:
        blank = bool(self._lyric_force_blank)
        if hasattr(self, "lyric_blank_toggle_button") and self.lyric_blank_toggle_button is not None:
            self.lyric_blank_toggle_button.blockSignals(True)
            self.lyric_blank_toggle_button.setChecked(blank)
            self.lyric_blank_toggle_button.setText(tr("Show Lyric") if blank else tr("Blank Lyric"))
            self.lyric_blank_toggle_button.blockSignals(False)
        if self._lyric_blank_toggle_action is not None:
            self._lyric_blank_toggle_action.blockSignals(True)
            self._lyric_blank_toggle_action.setChecked(blank)
            self._lyric_blank_toggle_action.blockSignals(False)

    def _main_ui_current_lyric_text(self) -> str:
        if self.current_playing is None:
            return ""
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return ""
        lyric_path = str(slot.lyric_file or "").strip()
        if not lyric_path:
            return "This audio has no lyric linked."
        lines, error = self._load_stage_lyric_lines(lyric_path)
        if error:
            return "Lyric file is unavailable."
        if not lines:
            return "No lyrics were found in this file."
        position_ms = self._lyric_position_ms_for_key(self.current_playing)
        text = line_for_position(lines, position_ms)
        return text.strip() if text and text.strip() else ""

    def _lyric_position_ms_for_key(self, slot_key: Optional[Tuple[str, int, int]]) -> int:
        if slot_key is None:
            return 0
        player = self._player_for_slot_key(slot_key)
        if player is None:
            return 0
        try:
            state = player.state()
        except Exception:
            return 0
        if state not in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
            return 0
        try:
            return max(0, int(player.position()))
        except Exception:
            return 0

    def _build_now_playing_text(self, slot: SoundButtonData) -> str:
        mode = str(self.now_playing_display_mode or "caption").strip().lower()
        caption = str(slot.title or "").strip()
        notes = str(slot.notes or "").strip()
        path = str(slot.file_path or "").strip()
        base_name = os.path.basename(path) if path else ""
        stem = os.path.splitext(base_name)[0] if base_name else ""
        if mode == "filepath":
            return path or caption or notes or stem
        if mode == "filename":
            return stem or base_name or caption or notes
        if mode == "note":
            return notes or caption or stem
        if mode == "caption_note":
            if caption and notes and notes.casefold() != caption.casefold():
                return f"{caption} - {notes}"
            return caption or notes or stem
        return caption or stem or notes

    def _show_stage_display(self) -> None:
        if self._stage_display_window is None:
            self._stage_display_window = GadgetStageDisplayWindow(self)
            self._stage_display_window.destroyed.connect(self._on_stage_display_destroyed)
        self._stage_display_window.retranslate_ui()
        self._stage_display_window.configure_gadgets(self.stage_display_gadgets)
        self._refresh_stage_display()
        self._stage_display_window.show()
        self._stage_display_window.raise_()
        self._stage_display_window.activateWindow()

    def _open_lyric_display(self) -> None:
        if self._lyric_display_window is None:
            self._lyric_display_window = LyricDisplayWindow(self)
            self._lyric_display_window.destroyed.connect(self._on_lyric_display_destroyed)
        self._lyric_display_window.retranslate_ui()
        self._lyric_display_window.show()
        self._lyric_display_window.raise_()
        self._lyric_display_window.activateWindow()
        self._refresh_lyric_display(force=True)

    def _on_lyric_display_destroyed(self, _obj=None) -> None:
        self._lyric_display_window = None

    def _open_lyric_navigator(self) -> None:
        if self._lyric_navigator_window is None:
            self._lyric_navigator_window = LyricNavigatorWindow(
                on_seek_to_ms=self._seek_to_lyric_timestamp,
                language=self.ui_language,
                parent=self,
            )
            self._lyric_navigator_window.destroyed.connect(self._on_lyric_navigator_destroyed)
        self._lyric_navigator_window.retranslate_ui(self.ui_language)
        self._lyric_navigator_window.show()
        self._lyric_navigator_window.raise_()
        self._lyric_navigator_window.activateWindow()
        self._refresh_lyric_display(force=True)

    def _on_lyric_navigator_destroyed(self, _obj=None) -> None:
        self._lyric_navigator_window = None

    def _seek_to_lyric_timestamp(self, position_ms: int) -> None:
        if self.current_playing is None:
            return
        self._seek_transport_display_ms(max(0, int(position_ms)))
        self._refresh_lyric_display(force=True)

    def _refresh_lyric_display(self, force: bool = False) -> None:
        self._update_main_lyric_label(self._main_ui_current_lyric_text())
        has_active_track = False
        lyric_path = ""
        position_ms = 0
        if self.current_playing is not None:
            slot = self._slot_for_key(self.current_playing)
            if slot is not None:
                has_active_track = True
                lyric_path = str(slot.lyric_file or "").strip()
                position_ms = self._lyric_position_ms_for_key(self.current_playing)
        if self._lyric_display_window is not None and (self._lyric_display_window.isVisible() or force):
            self._lyric_display_window.update_playback_state(
                has_active_track=has_active_track,
                lyric_path=lyric_path,
                position_ms=position_ms,
                force_blank=bool(self._lyric_force_blank),
                force=force,
            )
        if self._lyric_navigator_window is not None and (self._lyric_navigator_window.isVisible() or force):
            self._lyric_navigator_window.update_playback_state(
                has_active_track=has_active_track,
                lyric_path=lyric_path,
                position_ms=position_ms,
                force=force,
            )

    def _open_stage_alert_panel(self) -> None:
        if self._stage_alert_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Send Alert")
            dialog.setModal(False)
            dialog.resize(480, 320)
            root = QVBoxLayout(dialog)
            root.setContentsMargins(10, 10, 10, 10)
            root.setSpacing(8)
            root.addWidget(QLabel("Alert Message"))
            self._stage_alert_text_edit = QPlainTextEdit(dialog)
            self._stage_alert_text_edit.setPlaceholderText("Type alert text to show on Stage Display")
            root.addWidget(self._stage_alert_text_edit, 1)
            row = QHBoxLayout()
            self._stage_alert_keep_checkbox = QCheckBox("Keep on screen until cleared", dialog)
            self._stage_alert_keep_checkbox.setChecked(True)
            self._stage_alert_duration_spin = QSpinBox(dialog)
            self._stage_alert_duration_spin.setRange(1, 600)
            self._stage_alert_duration_spin.setValue(10)
            self._stage_alert_duration_spin.setEnabled(False)
            self._stage_alert_keep_checkbox.toggled.connect(
                lambda keep: self._stage_alert_duration_spin.setEnabled(not bool(keep))
            )
            row.addWidget(self._stage_alert_keep_checkbox)
            row.addStretch(1)
            row.addWidget(QLabel("Seconds"))
            row.addWidget(self._stage_alert_duration_spin)
            root.addLayout(row)
            buttons = QHBoxLayout()
            buttons.addStretch(1)
            send_btn = QPushButton("Send", dialog)
            clear_btn = QPushButton("Clear Alert", dialog)
            close_btn = QPushButton("Close", dialog)
            send_btn.clicked.connect(self._send_stage_alert_from_panel)
            clear_btn.clicked.connect(self._clear_stage_alert)
            close_btn.clicked.connect(dialog.close)
            buttons.addWidget(send_btn)
            buttons.addWidget(clear_btn)
            buttons.addWidget(close_btn)
            root.addLayout(buttons)
            dialog.destroyed.connect(self._on_stage_alert_dialog_destroyed)
            self._stage_alert_dialog = dialog
        if self._stage_alert_text_edit is not None and not self._stage_alert_text_edit.toPlainText().strip():
            self._stage_alert_text_edit.setPlainText(self._stage_alert_message)
        self._stage_alert_dialog.show()
        self._stage_alert_dialog.raise_()
        self._stage_alert_dialog.activateWindow()

    def _on_stage_alert_dialog_destroyed(self, _obj=None) -> None:
        self._stage_alert_dialog = None
        self._stage_alert_text_edit = None
        self._stage_alert_duration_spin = None
        self._stage_alert_keep_checkbox = None

    def _send_stage_alert_from_panel(self) -> None:
        if self._stage_alert_text_edit is None:
            return
        text = self._stage_alert_text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Send Alert", "Please enter alert text.")
            return
        keep = bool(self._stage_alert_keep_checkbox.isChecked()) if self._stage_alert_keep_checkbox is not None else True
        seconds = int(self._stage_alert_duration_spin.value()) if self._stage_alert_duration_spin is not None else 10
        self._set_stage_alert(text, keep=keep, seconds=seconds)

    def _set_stage_alert(self, text: str, keep: bool = True, seconds: int = 10) -> None:
        self._stage_alert_message = str(text or "").strip()
        self._stage_alert_sticky = bool(keep)
        if self._stage_alert_sticky:
            self._stage_alert_until_monotonic = 0.0
        else:
            self._stage_alert_until_monotonic = time.monotonic() + max(1, int(seconds))
        self._refresh_stage_display()

    def _clear_stage_alert(self) -> None:
        self._set_stage_alert("", keep=True, seconds=1)

    def _stage_alert_active(self) -> bool:
        if not self._stage_alert_message:
            return False
        if self._stage_alert_sticky:
            return True
        if self._stage_alert_until_monotonic > 0.0 and time.monotonic() < self._stage_alert_until_monotonic:
            return True
        if self._stage_alert_until_monotonic > 0.0:
            self._stage_alert_message = ""
            self._stage_alert_until_monotonic = 0.0
            self._stage_alert_sticky = False
        return False

    def _on_stage_display_destroyed(self, _obj=None) -> None:
        self._stage_display_window = None

    def _refresh_stage_display(self) -> None:
        if self._stage_display_window is None:
            return
        if not self._stage_display_window.isVisible():
            return
        total_ms = max(0, self._transport_total_ms())
        elapsed_text = self.elapsed_time.text().strip() or "00:00:00"
        remaining_text = self.remaining_time.text().strip() or "00:00:00"
        total_text = self.total_time.text().strip() or "00:00:00"
        display_pos = 0
        try:
            display_pos = max(0, int(self.seek_slider.value()))
        except Exception:
            display_pos = 0
        progress = 0 if total_ms <= 0 else int((display_pos / float(total_ms)) * 100)
        progress_ratio = 0.0 if total_ms <= 0 else max(0.0, min(1.0, display_pos / float(total_ms)))
        cue_in_ms, cue_out_ms = self._current_transport_cue_bounds()
        song_name = "-"
        if self.current_playing is not None:
            slot = self._slot_for_key(self.current_playing)
            if slot is not None:
                song_name = self._build_stage_slot_text(slot) or "-"
        lyric = self._stage_display_current_lyric()
        next_song = self._next_stage_song_name()
        self._stage_display_window.update_values(
            total_time=total_text,
            elapsed=elapsed_text,
            remaining=remaining_text,
            progress_percent=progress,
            song_name=song_name,
            lyric=lyric,
            next_song=next_song,
            progress_text=self.progress_label.text().strip(),
            progress_style=self._build_progress_bar_stylesheet(progress_ratio, cue_in_ms, cue_out_ms),
        )
        self._stage_display_window.set_alert(self._stage_alert_message, self._stage_alert_active())
        self._stage_display_window.set_playback_status(self._stage_playback_status())

    def _stage_playback_status(self) -> str:
        states = [
            self.player.state(),
            self.player_b.state(),
        ]
        for extra in self._multi_players:
            try:
                states.append(extra.state())
            except Exception:
                pass
        if any(state == ExternalMediaPlayer.PlayingState for state in states):
            return "playing"
        if any(state == ExternalMediaPlayer.PausedState for state in states):
            return "paused"
        return "not_playing"

    def _build_stage_slot_text(self, slot: SoundButtonData) -> str:
        source = str(self.stage_display_text_source or "caption").strip().lower()
        if source == "filename":
            base_name = os.path.basename(slot.file_path or "")
            if base_name:
                return base_name
        elif source == "note":
            note = str(slot.notes or "").strip()
            if note:
                return note
        title = str(slot.title or "").strip()
        if title:
            return title
        base_name = os.path.basename(slot.file_path or "")
        if base_name:
            return os.path.splitext(base_name)[0]
        return "-"

    def _next_stage_song_name(self) -> str:
        if self.cue_mode:
            return "-"
        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if not playlist_enabled:
            if self._hover_slot_index is not None and 0 <= self._hover_slot_index < SLOTS_PER_PAGE:
                next_slot = self._hover_slot_index
            else:
                next_slot = self._next_slot_for_next_action(blocked=None)
        else:
            next_slot = self._next_slot_for_next_action(blocked=None)
        if next_slot is None:
            return "-"
        slots = self.data[self.current_group][self.current_page]
        if next_slot < 0 or next_slot >= len(slots):
            return "-"
        slot = slots[next_slot]
        if not slot.assigned or slot.marker:
            return "-"
        return self._build_stage_slot_text(slot) or "-"

    def _stage_display_current_lyric(self) -> str:
        if self.current_playing is None:
            return "-"
        slot = self._slot_for_key(self.current_playing)
        if slot is None:
            return "-"
        lyric_path = str(slot.lyric_file or "").strip()
        if not lyric_path:
            return "-"
        lines, error = self._load_stage_lyric_lines(lyric_path)
        if error or not lines:
            return "-"
        position_ms = self._lyric_position_ms_for_key(self.current_playing)
        text = line_for_position(lines, position_ms)
        return text.strip() if text and text.strip() else ""

    def _load_stage_lyric_lines(self, lyric_path: str) -> tuple[List[LyricLine], str]:
        mtime = -1.0
        try:
            mtime = os.path.getmtime(lyric_path)
        except OSError:
            return [], f"Lyric file not found:\n{lyric_path}"
        if lyric_path == self._stage_lyric_cache_path and abs(mtime - self._stage_lyric_cache_mtime) < 0.0001:
            return self._stage_lyric_cache_lines, self._stage_lyric_cache_error
        try:
            lines = parse_lyric_file(lyric_path)
            error = ""
        except Exception as exc:
            lines = []
            error = f"Failed to read lyric file:\n{exc}"
        self._stage_lyric_cache_path = lyric_path
        self._stage_lyric_cache_mtime = mtime
        self._stage_lyric_cache_lines = lines
        self._stage_lyric_cache_error = error
        return lines, error

