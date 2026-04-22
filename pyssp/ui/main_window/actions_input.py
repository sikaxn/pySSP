from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class ActionsInputMixin:
    def _next_slot_for_next_action(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        blocked = blocked or set()
        if playlist_enabled:
            return self._next_playlist_slot(for_auto_advance=False, blocked=blocked)
        if self.next_play_mode == "any_available":
            return self._next_available_slot_on_current_page(blocked=blocked)
        return self._next_unplayed_slot_on_current_page(blocked=blocked)

    def _next_stage_from_hover(self) -> Optional[str]:
        slot_index = self._hover_slot_index
        if slot_index is None:
            return None
        if slot_index < 0 or slot_index >= SLOTS_PER_PAGE:
            return None
        group = self._view_group_key()
        key = (group, self.current_page, slot_index)
        slot = self._slot_for_key(key)
        if slot is None:
            return None
        return self._build_stage_slot_text(slot) or "-"

    def _view_group_key(self) -> str:
        return "Q" if self.cue_mode else self.current_group

    def _toggle_pause(self) -> None:
        if self._pending_deferred_audio_request is not None and (not self._all_active_players()):
            self._clear_pending_deferred_audio_start()
            self.current_playing = None
            self.current_duration_ms = 0
            self._last_ui_position_ms = -1
            self.total_time.setText("00:00:00")
            self.elapsed_time.setText("00:00:00")
            self.remaining_time.setText("00:00:00")
            self._set_progress_display(0)
            self.seek_slider.setValue(0)
            self._update_now_playing_label("")
            self._refresh_sound_grid()
            self._update_pause_button_label()
            return
        if self._is_multi_play_enabled():
            players = self._all_active_players()
            any_playing = any(p.state() == ExternalMediaPlayer.PlayingState for p in players)
            any_paused = any(p.state() == ExternalMediaPlayer.PausedState for p in players)
            if any_playing:
                playing_players = [p for p in players if p.state() == ExternalMediaPlayer.PlayingState]
                self._pause_players(playing_players)
                self._timecode_on_playback_pause()
            elif any_paused:
                paused_players = [p for p in players if p.state() == ExternalMediaPlayer.PausedState]
                self._resume_players(paused_players)
                self._timecode_on_playback_resume()
        else:
            if self.player.state() == ExternalMediaPlayer.PlayingState:
                self._pause_players([self.player])
                self._timecode_on_playback_pause()
            elif self.player.state() == ExternalMediaPlayer.PausedState:
                self._resume_players([self.player])
                self._timecode_on_playback_resume()
        self._update_pause_button_label()

    def _pause_players(self, players: List[ExternalMediaPlayer]) -> None:
        playing = [p for p in players if p.state() == ExternalMediaPlayer.PlayingState]
        if not playing:
            return
        if self.fade_on_pause and self._is_fade_out_enabled() and self.fade_out_sec > 0:
            for player in playing:
                resume_target = self._effective_slot_target_volume(self._slot_pct_for_player(player))
                self._start_fade(
                    player,
                    0,
                    self.fade_out_sec,
                    stop_on_complete=False,
                    pause_on_complete=True,
                    pause_resume_volume=resume_target,
                )
            return
        for player in playing:
            player.pause()
            self._sync_shadow_transport_from_primary(player)

    def _resume_players(self, players: List[ExternalMediaPlayer]) -> None:
        paused = [p for p in players if p.state() == ExternalMediaPlayer.PausedState]
        if not paused:
            return
        if self.fade_on_resume and self._is_fade_in_enabled() and self.fade_in_sec > 0:
            for player in paused:
                target = self._effective_slot_target_volume(self._slot_pct_for_player(player))
                self._set_player_volume(player, 0)
                player.play()
                self._sync_shadow_transport_from_primary(player)
                self._start_fade(player, target, self.fade_in_sec, stop_on_complete=False)
            return
        for player in paused:
            player.play()
            self._sync_shadow_transport_from_primary(player)

    def _toggle_talk(self, checked: bool) -> None:
        self.talk_active = checked
        self._apply_talk_state_volume(fade=True)
        self._update_talk_button_visual()

    def _toggle_cue_mode(self, checked: bool) -> None:
        self.cue_mode = checked
        self._hotkey_selected_slot_key = None
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(checked)
        self.current_page = 0
        self.current_playlist_start = None
        self._sync_playlist_shuffle_buttons()
        self._refresh_group_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()

    def _show_cue_button_menu(self, pos) -> None:
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn is None:
            return
        menu = QMenu(self)
        clear_action = menu.addAction("Clear Cue")
        self._apply_strike_to_disabled_menu_actions(menu)
        selected = menu.exec_(cue_btn.mapToGlobal(pos))
        if selected == clear_action:
            self._clear_cue_page()

    def _apply_strike_to_disabled_menu_actions(self, menu: QMenu) -> None:
        for action in menu.actions():
            if action.isSeparator():
                continue
            font = action.font()
            font.setStrikeOut(not action.isEnabled())
            action.setFont(font)
            submenu = action.menu()
            if submenu is not None:
                self._apply_strike_to_disabled_menu_actions(submenu)

    def _toggle_playlist_mode(self, checked: bool) -> None:
        if self.cue_mode:
            checked = False
            play_btn = self.control_buttons.get("Play List")
            if play_btn:
                play_btn.setChecked(False)
            return
        self.page_playlist_enabled[self.current_group][self.current_page] = checked
        if not checked:
            self.page_shuffle_enabled[self.current_group][self.current_page] = False
        self.current_playlist_start = None
        self._set_dirty(True)
        self._sync_playlist_shuffle_buttons()

    def _toggle_shuffle_mode(self, checked: bool) -> None:
        if self.cue_mode:
            checked = False
        if not self.page_playlist_enabled[self.current_group][self.current_page]:
            checked = False
        self.page_shuffle_enabled[self.current_group][self.current_page] = checked
        shuf_btn = self.control_buttons.get("Shuffle")
        if shuf_btn:
            shuf_btn.setChecked(checked)
        self._set_dirty(True)

    def _open_find_dialog(self) -> None:
        if self._search_window is None:
            self._search_window = SearchWindow(self, language=self.ui_language)
            self._search_window.set_handlers(
                search_handler=self._find_sound_matches,
                goto_handler=self._go_to_found_match,
                play_handler=self._play_found_match,
            )
            self._search_window.set_double_click_action(self.search_double_click_action)
            self._search_window.destroyed.connect(lambda _=None: self._clear_search_window_ref())
        self._search_window.show()
        self._search_window.raise_()
        self._search_window.activateWindow()
        self._search_window.focus_query()

    def _clear_search_window_ref(self) -> None:
        self._search_window = None

    def _open_dsp_window(self) -> None:
        if self._dsp_window is None:
            self._dsp_window = DSPWindow(self, language=self.ui_language)
            self._dsp_window.set_config(self._dsp_config)
            self._dsp_window.configChanged.connect(self._on_dsp_config_changed)
            self._dsp_window.destroyed.connect(lambda _=None: self._clear_dsp_window_ref())
        self._dsp_window.show()
        self._dsp_window.raise_()
        self._dsp_window.activateWindow()

    def _clear_dsp_window_ref(self) -> None:
        self._dsp_window = None

    def _on_dsp_config_changed(self, config: object) -> None:
        if isinstance(config, DSPConfig):
            self._dsp_config = normalize_config(config)
            self.player.setDSPConfig(self._dsp_config)
            self.player_b.setDSPConfig(self._dsp_config)
            for shadow in self._vocal_shadow_players.values():
                shadow.setDSPConfig(self._dsp_config)

    def _go_to_found_match(self, match: dict) -> None:
        self._focus_found_slot(match, play=False, flash=True)

    def _play_found_match(self, match: dict) -> None:
        self._focus_found_slot(match, play=True, flash=True)

    def _go_to_current_playing_page(self) -> None:
        if self.current_playing is None:
            self._show_info_notice_banner("No sound is currently playing.")
            return
        group_key, page_index, _slot_index = self.current_playing
        if group_key == "Q":
            self._toggle_cue_mode(True)
            return
        if group_key not in GROUPS:
            return
        if self.cue_mode:
            self._toggle_cue_mode(False)
        self._select_group(group_key)
        self._select_page(max(0, min(PAGE_COUNT - 1, int(page_index))))

    def _toggle_global_vocal_removed_mode(self, checked: bool) -> None:
        was_vocal_removed_active = bool(self.play_vocal_removed_tracks)
        self.play_vocal_removed_tracks = bool(checked)
        btn = self.control_buttons.get("Vocal Removed")
        if btn is not None and btn.isChecked() != bool(checked):
            btn.setChecked(bool(checked))
        for player in [self.player, self.player_b, *self._multi_players]:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                self._apply_vocal_removed_toggle_for_player(
                    player,
                    current_vocal_removed_active=was_vocal_removed_active,
                )
        self._refresh_sound_grid()

    def _find_sound_matches(self, query: str) -> List[dict]:
        terms = [part.casefold() for part in query.split() if part.strip()]
        if not terms:
            return []
        matches: List[dict] = []

        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                page = self.data[group][page_index]
                for slot_index, slot in enumerate(page):
                    if not slot.assigned:
                        continue
                    haystack = f"{slot.title} {slot.file_path} {os.path.basename(slot.file_path)}".casefold()
                    if all(term in haystack for term in terms):
                        matches.append(
                            {
                                "group": group,
                                "page": page_index,
                                "slot": slot_index,
                                "title": slot.title,
                                "file_path": slot.file_path,
                            }
                        )

        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned:
                continue
            haystack = f"{slot.title} {slot.file_path} {os.path.basename(slot.file_path)}".casefold()
            if all(term in haystack for term in terms):
                matches.append(
                    {
                        "group": "Q",
                        "page": 0,
                        "slot": slot_index,
                        "title": slot.title,
                        "file_path": slot.file_path,
                    }
                )

        return matches

    def _focus_found_slot(self, match: dict, play: bool = False, flash: bool = False) -> None:
        group = str(match.get("group", ""))
        page = int(match.get("page", 0))
        slot = int(match.get("slot", -1))
        if slot < 0 or slot >= SLOTS_PER_PAGE:
            return
        if group == "Q":
            self._toggle_cue_mode(True)
        elif group in GROUPS:
            if self.cue_mode:
                self._toggle_cue_mode(False)
            self._select_group(group)
            self._select_page(max(0, min(PAGE_COUNT - 1, page)))
        else:
            return
        self.sound_buttons[slot].setFocus()
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot)
        if flash:
            self._flash_slot_key = (self._view_group_key(), self.current_page, slot)
            self._flash_slot_until = time.monotonic() + 1.0
            self._refresh_sound_grid()
        if play:
            self._play_slot(slot)

    def _toggle_cross_auto_mode(self, checked: bool) -> None:
        if checked and self._is_multi_play_enabled():
            checked = False
        x_btn = self.control_buttons.get("X")
        if x_btn:
            x_btn.setChecked(checked)
        if checked:
            fade_in_btn = self.control_buttons.get("Fade In")
            fade_out_btn = self.control_buttons.get("Fade Out")
            if fade_in_btn:
                fade_in_btn.setChecked(False)
            if fade_out_btn:
                fade_out_btn.setChecked(False)

    def _toggle_multi_play_mode(self, checked: bool) -> None:
        multi_btn = self.control_buttons.get("Multi-Play")
        if multi_btn:
            multi_btn.setChecked(checked)
        self._update_timecode_multiplay_warning_banner()
        if checked:
            self.page_playlist_enabled[self.current_group][self.current_page] = False
            self.page_shuffle_enabled[self.current_group][self.current_page] = False
            play_btn = self.control_buttons.get("Play List")
            if play_btn:
                play_btn.setChecked(False)
            shuf_btn = self.control_buttons.get("Shuffle")
            if shuf_btn:
                shuf_btn.setChecked(False)
                shuf_btn.setEnabled(False)
            self.current_playlist_start = None
            self._set_dirty(True)
            x_btn = self.control_buttons.get("X")
            if x_btn:
                x_btn.setChecked(False)
            self._sync_playlist_shuffle_buttons()

    def _player_for_slot_key(self, slot_key: Tuple[str, int, int]) -> Optional[ExternalMediaPlayer]:
        for player in [self.player, self.player_b, *self._multi_players]:
            if self._player_slot_key_map.get(id(player)) == slot_key:
                return player
        return None

    def _stop_track_by_slot_key(self, slot_key: Tuple[str, int, int]) -> bool:
        player = self._player_for_slot_key(slot_key)
        if player is None:
            return False
        if self.fade_on_stop and self._is_fade_out_enabled() and player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            self._start_fade(player, 0, self.fade_out_sec, stop_on_complete=True)
        else:
            self._stop_single_player(player)
        if self.current_playing == slot_key:
            self._refresh_current_playing_from_active_players()
        self._refresh_sound_grid()
        return True

    def _toggle_fade_in_mode(self, checked: bool) -> None:
        fade_in_btn = self.control_buttons.get("Fade In")
        if fade_in_btn:
            fade_in_btn.setChecked(checked)
        if checked:
            x_btn = self.control_buttons.get("X")
            if x_btn:
                x_btn.setChecked(False)

    def _toggle_fade_out_mode(self, checked: bool) -> None:
        fade_out_btn = self.control_buttons.get("Fade Out")
        if fade_out_btn:
            fade_out_btn.setChecked(checked)
        if checked:
            x_btn = self.control_buttons.get("X")
            if x_btn:
                x_btn.setChecked(False)

    def _apply_talk_state_volume(self, fade: bool) -> None:
        fade_seconds = self.talk_fade_sec if fade else 0.0
        for player in [self.player, self.player_b, *self._multi_players]:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                target = self._effective_slot_target_volume(self._slot_pct_for_player(player))
                self._start_fade(player, target, fade_seconds, stop_on_complete=False)

    def _switch_audio_device(self, device_name: str) -> bool:
        self._hard_stop_all()
        old_player = self.player
        old_player_b = self.player_b
        old_multi_players = list(self._multi_players)
        self._clear_all_vocal_shadow_players()
        if not set_output_device(device_name):
            QMessageBox.warning(self, "Audio Device", "Could not switch to selected audio device.")
            return False
        self._multi_players = []
        try:
            old_player.deleteLater()
            old_player_b.deleteLater()
            for extra in old_multi_players:
                extra.deleteLater()
        except Exception:
            pass
        try:
            self._init_audio_players()
        except Exception as exc:
            self._dispose_audio_players()
            set_output_device("")
            self.audio_output_device = ""
            try:
                self._init_audio_players()
                QMessageBox.warning(
                    self,
                    "Audio Device",
                    f"Could not switch to selected audio device.\nFell back to system default.\n\nDetails:\n{exc}",
                )
            except Exception as exc2:
                self._init_silent_audio_players()
                QMessageBox.warning(
                    self,
                    "Audio Device",
                    "Audio output failed. Running in no-audio mode.\n\n"
                    f"Primary error:\n{exc}\n\nFallback error:\n{exc2}",
                )
        self._set_player_volume(self.player, self._effective_slot_target_volume(self._player_slot_volume_pct))
        self._set_player_volume(self.player_b, self._effective_slot_target_volume(self._player_b_slot_volume_pct))
        self.current_playing = None
        self.current_duration_ms = 0
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setValue(0)
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self._update_now_playing_label("")
        self._refresh_sound_grid()
        return True

    def _tick_talk_blink(self) -> None:
        if not self.talk_active:
            return
        self._update_talk_button_visual(toggle=True)

    def _update_talk_button_visual(self, toggle: bool = False) -> None:
        talk_button = self.control_buttons.get("Talk")
        if not talk_button:
            return
        if not self.talk_active:
            talk_button.setChecked(False)
            talk_button.setStyleSheet("")
            talk_button.setText(tr("Talk"))
            self._sync_control_button_instances("Talk")
            return
        talk_button.setChecked(True)
        if self.talk_blink_button:
            blink_on = talk_button.property("_blink_on")
            if blink_on is None:
                blink_on = False
            if toggle:
                blink_on = not bool(blink_on)
            else:
                blink_on = True
            talk_button.setProperty("_blink_on", blink_on)
            if blink_on:
                talk_button.setStyleSheet("background:#F2D74A; font-weight:bold;")
            else:
                talk_button.setStyleSheet("")
        else:
            talk_button.setProperty("_blink_on", True)
            talk_button.setStyleSheet("background:#F2D74A; font-weight:bold;")
        talk_button.setText(tr("Talk*"))
        self._sync_control_button_instances("Talk")

    def _stop_playback(self) -> None:
        self._manual_stop_requested = True
        self._pending_start_request = None
        self._pending_start_token += 1
        self._vocal_toggle_fade_jobs.clear()
        self._clear_pending_deferred_audio_start()
        self._auto_transition_done = True
        self._auto_end_fade_track = None
        self._auto_end_fade_done = False
        # Stop timecode immediately on user intent, regardless of audio fade-out.
        self._timecode_on_playback_stop()
        active_players = self._all_active_players()
        if self._stop_fade_armed:
            self._stop_fade_armed = False
            self._hard_stop_all()
            self._player_slot_volume_pct = 75
            self._player_b_slot_volume_pct = 75
            self.current_playing = None
            self.current_playlist_start = None
            self.current_duration_ms = 0
            self._last_ui_position_ms = -1
            self.total_time.setText("00:00:00")
            self.elapsed_time.setText("00:00:00")
            self.remaining_time.setText("00:00:00")
            self._set_progress_display(0)
            self.seek_slider.setValue(0)
            self._vu_levels = [0.0, 0.0]
            self._refresh_sound_grid()
            self._update_now_playing_label("")
            return
        if self.fade_on_stop and self._is_fade_out_enabled() and active_players:
            self._stop_fade_armed = True
            self.statusBar().showMessage(
                tr("Stop fade in progress. Click Stop again to force stop (skip fade)."),
                3000,
            )
            for player in active_players:
                self._start_fade(player, 0, self.fade_out_sec, stop_on_complete=True)
            return
        self._stop_fade_armed = False
        self.player.stop()
        self.player_b.stop()
        self._clear_all_vocal_shadow_players()
        self._timecode_on_playback_stop()
        self._clear_all_player_slot_keys()
        for extra in list(self._multi_players):
            self._stop_single_player(extra)
        self._prune_multi_players()
        self._player_started_map.clear()
        self._player_slot_pct_map.clear()
        self._player_mix_volume_map.clear()
        self._player_slot_volume_pct = 75
        self._player_b_slot_volume_pct = 75
        self.current_playing = None
        self.current_playlist_start = None
        self.current_duration_ms = 0
        self._last_ui_position_ms = -1
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self.seek_slider.setValue(0)
        self._vu_levels = [0.0, 0.0]
        self._refresh_sound_grid()
        self._update_now_playing_label("")

    def _hard_stop_all(self) -> None:
        self._fade_jobs.clear()
        self._vocal_toggle_fade_jobs.clear()
        self._update_fade_button_flash(False)
        self._pending_start_request = None
        self._pending_start_token += 1
        self._clear_pending_deferred_audio_start()
        self._auto_transition_done = True
        self._auto_end_fade_track = None
        self._auto_end_fade_done = False
        self._cancel_all_pending_player_media_loads()
        self.player.stop()
        self.player_b.stop()
        self._clear_all_vocal_shadow_players()
        self._timecode_on_playback_stop()
        self._clear_all_player_slot_keys()
        for extra in list(self._multi_players):
            self._stop_single_player(extra)
        self._prune_multi_players()
        self._player_started_map.clear()
        self._player_slot_pct_map.clear()
        self._player_mix_volume_map.clear()
        self._player_slot_volume_pct = 75
        self._player_b_slot_volume_pct = 75

    def _play_next(self) -> None:
        blocked: set[int] = set()
        while True:
            next_slot = self._next_slot_for_next_action(blocked=blocked)
            if next_slot is None:
                self._update_next_button_enabled()
                return
            if self._play_slot(next_slot):
                return
            blocked.add(next_slot)
            if self.candidate_error_action == "stop_playback":
                self._stop_playback()
                return

    def _has_next_playlist_slot(self, for_auto_advance: bool = False) -> bool:
        page = self._current_page_slots()
        if not page:
            return False
        valid_slots = [
            idx
            for idx, slot in enumerate(page)
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing
        ]
        if not valid_slots:
            return False
        current_idx: Optional[int] = None
        if self.current_playing and self.current_playing[0] == self._view_group_key():
            current_idx = self.current_playing[2]
        if (
            for_auto_advance
            and self.loop_enabled
            and self.playlist_loop_mode == "loop_single"
            and current_idx is not None
            and current_idx in valid_slots
        ):
            return True
        if self.playlist_play_mode == "any_available":
            if self.page_shuffle_enabled[self.current_group][self.current_page]:
                if current_idx is not None and len(valid_slots) > 1:
                    return any(idx != current_idx for idx in valid_slots)
                return bool(valid_slots)
            start = 0
            if self.current_playlist_start is not None:
                start = self.current_playlist_start
            if current_idx is not None:
                start = current_idx + 1
            for idx in range(start, SLOTS_PER_PAGE):
                if idx in valid_slots:
                    return True
            return self.loop_enabled and self.playlist_loop_mode == "loop_list" and bool(valid_slots)
        unplayed_slots = [idx for idx in valid_slots if not page[idx].played]
        if self.page_shuffle_enabled[self.current_group][self.current_page]:
            if unplayed_slots:
                return True
            return self.loop_enabled and self.playlist_loop_mode == "loop_list" and bool(valid_slots)
        start = 0
        if self.current_playlist_start is not None:
            start = self.current_playlist_start
        if current_idx is not None:
            start = current_idx + 1
        for idx in range(start, SLOTS_PER_PAGE):
            if idx in unplayed_slots:
                return True
        return self.loop_enabled and self.playlist_loop_mode == "loop_list" and bool(valid_slots)

    def _next_unplayed_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        blocked = blocked or set()
        start_slot = -1
        current_key = self._view_group_key()
        if self.current_playing and self.current_playing[0] == current_key and self.current_playing[1] == self.current_page:
            start_slot = self.current_playing[2]
        for idx in range(start_slot + 1, SLOTS_PER_PAGE):
            slot = page[idx]
            if idx in blocked:
                continue
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and not slot.played:
                return idx
        return None

    def _next_available_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        blocked = blocked or set()
        start_slot = -1
        current_key = self._view_group_key()
        if self.current_playing and self.current_playing[0] == current_key and self.current_playing[1] == self.current_page:
            start_slot = self.current_playing[2]
        for idx in range(start_slot + 1, SLOTS_PER_PAGE):
            slot = page[idx]
            if idx in blocked:
                continue
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing:
                return idx
        return None

    def _next_slot_index(self) -> Optional[int]:
        page = self._current_page_slots()
        start_slot = -1
        if self.current_playing and self.current_playing[0] == self._view_group_key() and self.current_playing[1] == self.current_page:
            start_slot = self.current_playing[2]
        for step in range(1, SLOTS_PER_PAGE + 1):
            idx = (start_slot + step) % SLOTS_PER_PAGE
            slot = page[idx]
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing:
                return idx
        return None

    def _next_playlist_slot(self, for_auto_advance: bool = False, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        if not page:
            return None
        blocked = blocked or set()
        valid_slots = [
            idx
            for idx, slot in enumerate(page)
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and idx not in blocked
        ]
        if not valid_slots:
            return None
        current_idx: Optional[int] = None
        if self.current_playing and self.current_playing[0] == self._view_group_key():
            current_idx = self.current_playing[2]
        if (
            for_auto_advance
            and self.loop_enabled
            and self.playlist_loop_mode == "loop_single"
            and current_idx is not None
            and current_idx in valid_slots
        ):
            return current_idx
        any_available = self.playlist_play_mode == "any_available"
        if self.page_shuffle_enabled[self.current_group][self.current_page]:
            if any_available:
                candidates = list(valid_slots)
            else:
                candidates = [idx for idx in valid_slots if not page[idx].played]
            if not candidates:
                if self.loop_enabled and self.playlist_loop_mode == "loop_list":
                    for slot in page:
                        slot.played = False
                        if slot.assigned:
                            slot.activity_code = "8"
                    self._set_dirty(True)
                    candidates = list(valid_slots)
                else:
                    return None
            if current_idx is not None and len(candidates) > 1 and current_idx in candidates:
                candidates = [idx for idx in candidates if idx != current_idx]
            if not candidates:
                return None
            return random.choice(candidates)

        start = 0
        if self.current_playlist_start is not None:
            start = self.current_playlist_start
        if current_idx is not None:
            start = current_idx + 1

        for idx in range(start, SLOTS_PER_PAGE):
            slot = page[idx]
            if slot.assigned and not slot.marker and not slot.locked and not slot.missing and (any_available or (not slot.played)):
                return idx
        if self.loop_enabled and self.playlist_loop_mode == "loop_list":
            if not any_available:
                for slot in page:
                    slot.played = False
                    if slot.assigned:
                        slot.activity_code = "8"
                self._set_dirty(True)
            for idx in range(0, SLOTS_PER_PAGE):
                slot = page[idx]
                if slot.assigned and not slot.marker and not slot.locked and not slot.missing:
                    return idx
        return None

    def _random_unplayed_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        blocked = blocked or set()
        candidates = [
            idx
            for idx, slot in enumerate(page)
            if idx not in blocked and slot.assigned and not slot.marker and not slot.locked and not slot.missing and not slot.played
        ]
        if not candidates:
            return None
        return random.choice(candidates)

    def _random_available_slot_on_current_page(self, blocked: Optional[set[int]] = None) -> Optional[int]:
        page = self._current_page_slots()
        blocked = blocked or set()
        candidates = [
            idx
            for idx, slot in enumerate(page)
            if idx not in blocked and slot.assigned and not slot.marker and not slot.locked and not slot.missing
        ]
        if not candidates:
            return None
        return random.choice(candidates)

    def _on_rapid_fire_clicked(self, _checked: bool = False) -> None:
        blocked: set[int] = set()
        while True:
            if self.rapid_fire_play_mode == "any_available":
                slot_index = self._random_available_slot_on_current_page(blocked=blocked)
            else:
                slot_index = self._random_unplayed_slot_on_current_page(blocked=blocked)
            if slot_index is None:
                return
            if self._play_slot(slot_index):
                return
            blocked.add(slot_index)
            if self.candidate_error_action == "stop_playback":
                self._stop_playback()
                return

    def _toggle_loop(self, checked: bool) -> None:
        self.loop_enabled = checked
        loop_button = self.control_buttons.get("Loop")
        if loop_button:
            loop_button.setChecked(checked)

    def _reset_current_page_state(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset Page",
            "Reset this page's played state?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._stop_playback()
        page = self._current_page_slots()
        for slot in page:
            slot.played = False
            if slot.assigned:
                slot.activity_code = "8"
        self.current_playlist_start = None
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _update_pause_button_label(self) -> None:
        pause_button = self.control_buttons.get("Pause")
        if not pause_button:
            return
        if self._is_multi_play_enabled():
            players = self._all_active_players()
            any_playing = any(p.state() == ExternalMediaPlayer.PlayingState for p in players)
            any_paused = any(p.state() == ExternalMediaPlayer.PausedState for p in players)
            paused_mode = any_paused and not any_playing
        else:
            paused_mode = self.player.state() == ExternalMediaPlayer.PausedState
        if paused_mode:
            pause_button.setText("Resume")
            pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            pause_button.setText("Pause")
            pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self._sync_control_button_instances("Pause")

    def _on_seek_pressed(self) -> None:
        self._is_scrubbing = True

    def _on_seek_released(self) -> None:
        self._seek_transport_display_ms(self.seek_slider.value())
        self._is_scrubbing = False

    def _seek_transport_display_ms(self, display_ms: int) -> tuple[int, int]:
        total_ms = self._transport_total_ms()
        clamped_display = max(0, min(total_ms, int(display_ms)))
        absolute = max(0, int(self._transport_absolute_ms_for_display(clamped_display)))
        self.player.setPosition(absolute)
        self._sync_shadow_transport_from_primary(self.player)
        self.seek_slider.setValue(clamped_display)
        self._apply_main_jog_outside_cue_behavior(absolute)
        self._mtc_sender.request_resync()
        return clamped_display, absolute

    def _on_seek_value_changed(self, value: int) -> None:
        if self._is_scrubbing:
            self.elapsed_time.setText(format_clock_time(value))
            remaining = max(0, self._transport_total_ms() - value)
            self.remaining_time.setText(format_clock_time(remaining))
            total_ms = self._transport_total_ms()
            progress = 0 if total_ms == 0 else int((value / total_ms) * 100)
            self._refresh_main_jog_meta(value, total_ms)

    def _refresh_main_transport_display(self) -> None:
        total_ms = self._transport_total_ms()
        self.seek_slider.setRange(0, total_ms)
        self.total_time.setText(format_clock_time(total_ms))
        current_abs = 0
        if self.player is not None:
            try:
                current_abs = max(0, int(self.player.position()))
            except Exception:
                current_abs = 0
        display = self._transport_display_ms_for_absolute(current_abs)
        if not self._is_scrubbing:
            self.seek_slider.setValue(display)
        self.elapsed_time.setText(format_clock_time(display))
        remaining = max(0, total_ms - display)
        self.remaining_time.setText(format_clock_time(remaining))
        progress = 0 if total_ms == 0 else int((display / total_ms) * 100)
        self._refresh_main_jog_meta(display, total_ms)
        self._refresh_timecode_panel()
        self._refresh_stage_display()
        self._refresh_lyric_display()

    def _refresh_main_jog_meta(self, display_ms: int, total_ms: int) -> None:
        cue_in_ms, cue_out_ms = self._current_transport_cue_bounds()
        self.jog_in_label.setText(f"In {format_clock_time(cue_in_ms)}")
        self.jog_out_label.setText(f"Out {format_clock_time(cue_out_ms)}")
        clamped = max(0, min(total_ms, int(display_ms)))
        ratio = 0.0 if total_ms == 0 else (clamped / float(total_ms))
        pct = int(ratio * 100)
        self.jog_percent_label.setText(f"{pct}%")
        self._set_progress_display(ratio, cue_in_ms, cue_out_ms)

    def _current_transport_cue_bounds(self) -> tuple[int, int]:
        low, high = self._main_transport_bounds()
        cue_in_ms = low
        cue_out_ms = high
        if self.main_transport_timeline_mode == "audio_file":
            cue_in_ms = 0
            cue_out_ms = self.current_duration_ms
            if self.current_playing is not None:
                slot = self._slot_for_key(self.current_playing)
                if slot is not None:
                    cue_in_ms = self._cue_start_for_playback(slot, self.current_duration_ms)
                    cue_end = self._cue_end_for_playback(slot, self.current_duration_ms)
                    cue_out_ms = self.current_duration_ms if cue_end is None else cue_end
        return cue_in_ms, cue_out_ms

    def _build_progress_bar_stylesheet(
        self,
        progress_ratio: float,
        cue_in_ms: Optional[int] = None,
        cue_out_ms: Optional[int] = None,
    ) -> str:
        fill_stop = max(0.0, min(1.0, float(progress_ratio)))
        base_style_prefix = (
            "QLabel{"
            "font-size:12pt;font-weight:bold;color:white;"
            "border:1px solid #3C4E58;border-radius:4px;padding:2px 8px;"
        )
        audio_file_mode = self.main_transport_timeline_mode == "audio_file" and self.current_duration_ms > 0
        if audio_file_mode:
            in_ms = 0 if cue_in_ms is None else max(0, min(self.current_duration_ms, int(cue_in_ms)))
            out_ms = self.current_duration_ms if cue_out_ms is None else max(0, min(self.current_duration_ms, int(cue_out_ms)))
            if out_ms < in_ms:
                out_ms = in_ms
            in_ratio = in_ms / float(self.current_duration_ms)
            out_ratio = out_ms / float(self.current_duration_ms)
            eps = 0.001
            played = max(0.0, min(1.0, fill_stop))
            if played <= in_ratio:
                grad = (
                    "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    f"stop:0 #747474, stop:{in_ratio:.4f} #747474, "
                    f"stop:{min(1.0, in_ratio + eps):.4f} #111111, stop:{out_ratio:.4f} #111111, "
                    f"stop:{min(1.0, out_ratio + eps):.4f} #747474, stop:1 #747474);"
                )
            elif played >= out_ratio:
                grad = (
                    "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    f"stop:0 #747474, stop:{in_ratio:.4f} #747474, "
                    f"stop:{min(1.0, in_ratio + eps):.4f} #2ECC40, stop:{out_ratio:.4f} #2ECC40, "
                    f"stop:{min(1.0, out_ratio + eps):.4f} #747474, stop:1 #747474);"
                )
            else:
                grad = (
                    "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    f"stop:0 #747474, stop:{in_ratio:.4f} #747474, "
                    f"stop:{min(1.0, in_ratio + eps):.4f} #2ECC40, stop:{played:.4f} #2ECC40, "
                    f"stop:{min(1.0, played + eps):.4f} #111111, stop:{out_ratio:.4f} #111111, "
                    f"stop:{min(1.0, out_ratio + eps):.4f} #747474, stop:1 #747474);"
                )
            return base_style_prefix + grad + "}"
        boundary = min(1.0, fill_stop + 0.002)
        return (
            base_style_prefix
            + (
                "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 #2ECC40, stop:{fill_stop:.4f} #2ECC40, "
                f"stop:{boundary:.4f} #111111, stop:1 #111111);"
            )
            + "}"
        )

    def _set_progress_display(
        self,
        progress_ratio: float,
        cue_in_ms: Optional[int] = None,
        cue_out_ms: Optional[int] = None,
    ) -> None:
        fill_stop = max(0.0, min(1.0, float(progress_ratio)))
        pct = int(fill_stop * 100)
        in_ratio = 0.0
        out_ratio = 1.0
        in_ms = 0 if cue_in_ms is None else max(0, int(cue_in_ms))
        out_ms = self.current_duration_ms if cue_out_ms is None else max(0, int(cue_out_ms))
        audio_file_mode = self.main_transport_timeline_mode == "audio_file" and self.current_duration_ms > 0
        if self.current_duration_ms > 0:
            in_ms = max(0, min(self.current_duration_ms, in_ms))
            out_ms = max(0, min(self.current_duration_ms, out_ms))
            if out_ms < in_ms:
                out_ms = in_ms
            in_ratio = in_ms / float(self.current_duration_ms)
            out_ratio = out_ms / float(self.current_duration_ms)

        self.progress_label.set_transport_state(fill_stop, in_ratio, out_ratio, audio_file_mode)
        self.progress_label.set_waveform(self._main_progress_waveform)

        if self.main_progress_show_text:
            if self.main_transport_timeline_mode == "audio_file":
                self.progress_label.setText(f"{pct}%   In {format_clock_time(in_ms)}   Out {format_clock_time(out_ms)}")
            else:
                self.progress_label.setText(f"{pct}%")
        else:
            self.progress_label.setText("")

        if self.main_progress_display_mode == "waveform":
            self.progress_label.setStyleSheet(
                "font-size:12pt;font-weight:bold;color:white;"
                "border:1px solid #3C4E58;border-radius:4px;padding:2px 8px;"
            )
            return

        self.progress_label.setStyleSheet(self._build_progress_bar_stylesheet(fill_stop, cue_in_ms, cue_out_ms))

    def _on_volume_changed(self, value: int) -> None:
        self._set_player_volume(self.player, self._effective_slot_target_volume(self._player_slot_volume_pct))
        self._set_player_volume(self.player_b, self._effective_slot_target_volume(self._player_b_slot_volume_pct))
        for player in self._multi_players:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                self._set_player_volume(player, self._effective_slot_target_volume(self._slot_pct_for_player(player)))
        self.settings.volume = value

    def _reset_set_data(self) -> None:
        self.data = {
            group: [[SoundButtonData() for _ in range(SLOTS_PER_PAGE)] for _ in range(PAGE_COUNT)]
            for group in GROUPS
        }
        self.page_names = {group: ["" for _ in range(PAGE_COUNT)] for group in GROUPS}
        self.page_colors = {group: [None for _ in range(PAGE_COUNT)] for group in GROUPS}
        self.page_playlist_enabled = {group: [False for _ in range(PAGE_COUNT)] for group in GROUPS}
        self.page_shuffle_enabled = {group: [False for _ in range(PAGE_COUNT)] for group in GROUPS}

    def _open_set_dialog(self) -> None:
        start_dir = self.settings.last_open_dir
        if not start_dir and self.current_set_path:
            start_dir = os.path.dirname(self.current_set_path)
        if not start_dir:
            start_dir = os.path.expanduser("~")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SSP Set File",
            start_dir,
            "Sports Sounds Pro Set (*.set);;All Files (*.*)",
        )
        if not file_path:
            return
        self.settings.last_open_dir = os.path.dirname(file_path)
        self._save_settings()
        self._load_set(file_path, show_message=True, restore_last_position=False)

    def _new_set(self) -> None:
        self._hard_stop_all()
        self._drag_source_key = None
        self.current_set_path = ""
        self.settings.last_set_path = ""
        self._reset_set_data()
        self.cue_page = [SoundButtonData() for _ in range(SLOTS_PER_PAGE)]
        self.cue_mode = False
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(False)
        self.current_group = "A"
        self.current_page = 0
        self.current_playing = None
        self.current_playlist_start = None
        self.current_duration_ms = 0
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._update_now_playing_label("")
        self._set_dirty(False)
        self.seek_slider.setValue(0)
        self.seek_slider.setRange(0, 0)
        self._vu_levels = [0.0, 0.0]
        self._refresh_lyric_display(force=True)
        self._save_settings()

    def _save_set(self) -> None:
        if not self.current_set_path:
            self._save_set_at()
            return
        self._write_set_file(self.current_set_path)

    def _save_set_at(self) -> None:
        start_dir = self.settings.last_save_dir
        if not start_dir and self.current_set_path:
            start_dir = os.path.dirname(self.current_set_path)
        if not start_dir:
            start_dir = os.path.expanduser("~")
        default_name = os.path.basename(self.current_set_path) if self.current_set_path else "newfile.set"
        initial_path = os.path.join(start_dir, default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save SSP Set File",
            initial_path,
            "Sports Sounds Pro Set (*.set);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".set"):
            file_path = f"{file_path}.set"
        self.settings.last_save_dir = os.path.dirname(file_path)
        self._save_settings()
        self._write_set_file(file_path)

    def _write_set_file(self, file_path: str) -> None:
        has_custom_cues = self._has_any_custom_cues()
        try:
            lines = self._build_set_file_lines()
            self._write_set_payload(file_path, lines)
        except Exception as exc:
            QMessageBox.critical(self, "Save Set Failed", f"Could not save set file:\n{exc}")
            return

        self.current_set_path = file_path
        self._set_dirty(False)
        self.settings.last_set_path = file_path
        self.settings.last_save_dir = os.path.dirname(file_path)
        self.settings.last_open_dir = os.path.dirname(file_path)
        self._save_settings()
        self._show_save_notice_banner(f"Set Saved: {file_path}")
        if has_custom_cues:
            self._show_save_notice_banner(
                "Reminder: Custom cue points saved by pySSP are not supported by original Sports Sounds Pro.",
                timeout_ms=9000,
            )

    def _build_set_file_lines(
        self,
        selected_pages: Optional[set[Tuple[str, int]]] = None,
        slot_path_overrides: Optional[Dict[Tuple[str, int, int], str]] = None,
        lyric_path_overrides: Optional[Dict[Tuple[str, int, int], str]] = None,
        skipped_slots: Optional[set[Tuple[str, int, int]]] = None,
    ) -> List[str]:
        overrides = slot_path_overrides or {}
        lyric_overrides = lyric_path_overrides or {}
        skipped = skipped_slots or set()
        lines: List[str] = [
            "[Main]",
            "CreatedBy=SportsSounds",
            f"Personalization=pySSP {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                include_page = selected_pages is None or (group, page_index) in selected_pages
                section_name = f"Page{page_index + 1}" if group == "A" else f"Page{group}{page_index + 1}"
                lines.append(f"[{section_name}]")
                page_name = clean_set_value(self.page_names[group][page_index]) if include_page else ""
                lines.append(f"PageName={page_name or ' '}")
                lines.append(f"PagePlay={'T' if include_page and self.page_playlist_enabled[group][page_index] else 'F'}")
                lines.append("RapidFire=F")
                lines.append(f"PageShuffle={'T' if include_page and self.page_shuffle_enabled[group][page_index] else 'F'}")
                lines.append(
                    f"PageColor={to_set_color_value(self.page_colors[group][page_index]) if include_page else 'clBtnFace'}"
                )

                if include_page:
                    for slot_index, slot in enumerate(self.data[group][page_index], start=1):
                        slot_key = (group, page_index, slot_index - 1)
                        if slot_key in skipped:
                            continue
                        if not slot.assigned and not slot.title:
                            continue
                        if slot.marker:
                            marker_title = clean_set_value(slot.title)
                            lines.append(f"c{slot_index}={(marker_title + '%%') if marker_title else '%%'}")
                            lines.append(f"t{slot_index}= ")
                            lines.append(f"activity{slot_index}=7")
                            lines.append(f"co{slot_index}=clBtnFace")
                            continue
                        effective_file_path = overrides.get(slot_key, slot.file_path)
                        title = clean_set_value(slot.title or os.path.splitext(os.path.basename(slot.file_path))[0])
                        notes = clean_set_value(slot.notes or title)
                        lines.append(f"c{slot_index}={notes}")
                        lines.append(f"s{slot_index}={clean_set_value(effective_file_path)}")
                        vocal_removed_file = clean_set_value(slot.vocal_removed_file)
                        if vocal_removed_file:
                            lines.append(f"pysspvocalremoval{slot_index}={vocal_removed_file}")
                        lines.append(f"t{slot_index}={format_set_time(slot.duration_ms)}")
                        lines.append(f"n{slot_index}={title}")
                        if slot.volume_override_pct is not None:
                            lines.append(f"v{slot_index}={max(0, min(100, int(slot.volume_override_pct)))}")
                        lines.append(f"activity{slot_index}={'2' if slot.played else '8'}")
                        lines.append(f"co{slot_index}={to_set_color_value(slot.custom_color)}")
                        if slot.copied_to_cue:
                            lines.append(f"ci{slot_index}=Y")
                        hotkey_code = self._encode_sound_hotkey(slot.sound_hotkey)
                        if hotkey_code:
                            lines.append(f"h{slot_index}={hotkey_code}")
                        midi_hotkey_code = self._encode_sound_midi_hotkey(slot.sound_midi_hotkey)
                        if midi_hotkey_code:
                            lines.append(f"pysspmidi{slot_index}={midi_hotkey_code}")
                        lyric_file = clean_set_value(lyric_overrides.get(slot_key, slot.lyric_file))
                        if lyric_file:
                            lines.append(f"pyssplyric{slot_index}={lyric_file}")
                        cue_start, cue_end = self._cue_time_fields_for_set(slot)
                        if cue_start is not None:
                            lines.append(f"pysspcuestart{slot_index}={cue_start}")
                        if cue_end is not None:
                            lines.append(f"pysspcueend{slot_index}={cue_end}")
                        timecode_offset = format_timecode_offset_hhmmss(
                            slot.timecode_offset_ms,
                            nominal_fps(self.timecode_fps),
                        )
                        if timecode_offset is not None:
                            lines.append(f"pyssptimecodeoffset{slot_index}={timecode_offset}")
                        timecode_timeline = normalize_slot_timecode_timeline_mode(slot.timecode_timeline_mode)
                        if timecode_timeline != "global":
                            lines.append(f"pyssptimecodedisplaytimeline{slot_index}={timecode_timeline}")
                lines.append("")

        lines.extend(
            [
                "[PageQ19]",
                "PageName=Cue",
                "PagePlay=F",
                "RapidFire=F",
                "PageShuffle=F",
                "PageColor=clBlack",
                "",
            ]
        )
        return lines

    def _write_set_payload(self, file_path: str, lines: List[str]) -> None:
        payload = "\r\n".join(lines)
        encoding = "utf-8-sig" if self.set_file_encoding == "utf8" else "gbk"
        with open(file_path, "w", encoding=encoding, newline="") as fh:
            fh.write(payload)

    def _load_set(self, file_path: str, show_message: bool = True, restore_last_position: bool = False) -> None:
        try:
            result = load_set_file(file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Open Set Failed", f"Could not load set file:\n{exc}")
            return

        self._hard_stop_all()
        self._drag_source_key = None
        self._reset_set_data()
        self.cue_mode = False
        cue_btn = self.control_buttons.get("Cue")
        if cue_btn:
            cue_btn.setChecked(False)
        self.current_playlist_start = None
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                self.page_names[group][page_index] = result.page_names[group][page_index]
                self.page_colors[group][page_index] = result.page_colors[group][page_index]
                self.page_playlist_enabled[group][page_index] = result.page_playlist_enabled[group][page_index]
                self.page_shuffle_enabled[group][page_index] = result.page_shuffle_enabled[group][page_index]
                for slot_index in range(SLOTS_PER_PAGE):
                    src = result.pages[group][page_index][slot_index]
                    self.data[group][page_index][slot_index] = SoundButtonData(
                        file_path=src.file_path,
                        vocal_removed_file=src.vocal_removed_file,
                        title=src.title,
                        notes=src.notes,
                        lyric_file=src.lyric_file,
                        duration_ms=src.duration_ms,
                        custom_color=src.custom_color,
                        played=src.played,
                        activity_code=src.activity_code,
                        marker=src.marker,
                        copied_to_cue=src.copied_to_cue,
                        volume_override_pct=src.volume_override_pct,
                        cue_start_ms=src.cue_start_ms,
                        cue_end_ms=src.cue_end_ms,
                        timecode_offset_ms=src.timecode_offset_ms,
                        timecode_timeline_mode=src.timecode_timeline_mode,
                        sound_hotkey=src.sound_hotkey,
                        sound_midi_hotkey=src.sound_midi_hotkey,
                    )

        self.current_set_path = file_path
        if restore_last_position and self.settings.last_group in GROUPS:
            self.current_group = self.settings.last_group
            self.current_page = max(0, min(PAGE_COUNT - 1, self.settings.last_page))
        else:
            self.current_group = "A"
            self.current_page = 0
        self.current_playing = None
        self.current_duration_ms = 0
        self.total_time.setText("00:00:00")
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self.seek_slider.setValue(0)
        self.seek_slider.setRange(0, 0)
        self._vu_levels = [0.0, 0.0]

        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._update_now_playing_label("")
        self._set_dirty(bool(result.migrated_legacy_cues))
        self._refresh_lyric_display(force=True)
        self.settings.last_set_path = file_path
        self.settings.last_open_dir = os.path.dirname(file_path)
        self.settings.last_group = self.current_group
        self.settings.last_page = self.current_page
        self._save_settings()

        if show_message:
            print(
                f"[pySSP] Set loaded: {file_path} | slots={result.loaded_slots} | encoding={result.encoding}",
                flush=True,
            )

    def _open_timecode_settings(self) -> None:
        self._open_options_dialog(initial_page="Audio Device & Timecode")

    def _open_options_dialog(self, initial_page: Optional[str] = None) -> None:
        available_devices = sorted(list_output_devices(), key=lambda v: v.lower())
        available_midi_output_devices = list_midi_output_devices()
        total_ram_mb, _reserved_ram_mb, preload_cap_mb = get_preload_memory_limits_mb()
        dialog = OptionsDialog(
            active_group_color=self.active_group_color,
            inactive_group_color=self.inactive_group_color,
            title_char_limit=self.title_char_limit,
            show_file_notifications=self.show_file_notifications,
            now_playing_display_mode=self.now_playing_display_mode,
            main_ui_lyric_display_mode=self.main_ui_lyric_display_mode,
            search_lyric_on_add_sound_button=self.search_lyric_on_add_sound_button,
            new_lyric_file_format=self.new_lyric_file_format,
            supported_audio_format_extensions=self.supported_audio_format_extensions,
            verify_sound_file_on_add=self.verify_sound_file_on_add,
            allow_other_unsupported_audio_files=self.allow_other_unsupported_audio_files,
            disable_path_safety=self.disable_path_safety,
            lock_allow_quit=self.lock_allow_quit,
            lock_allow_system_hotkeys=self.lock_allow_system_hotkeys,
            lock_allow_quick_action_hotkeys=self.lock_allow_quick_action_hotkeys,
            lock_allow_sound_button_hotkeys=self.lock_allow_sound_button_hotkeys,
            lock_allow_midi_control=self.lock_allow_midi_control,
            lock_auto_allow_quit=self.lock_auto_allow_quit,
            lock_auto_allow_midi_control=self.lock_auto_allow_midi_control,
            fade_in_sec=self.fade_in_sec,
            cross_fade_sec=self.cross_fade_sec,
            fade_out_sec=self.fade_out_sec,
            fade_on_quick_action_hotkey=self.fade_on_quick_action_hotkey,
            fade_on_sound_button_hotkey=self.fade_on_sound_button_hotkey,
            fade_on_pause=self.fade_on_pause,
            fade_on_resume=self.fade_on_resume,
            fade_on_stop=self.fade_on_stop,
            fade_out_when_done_playing=self.fade_out_when_done_playing,
            fade_out_end_lead_sec=self.fade_out_end_lead_sec,
            vocal_removed_toggle_fade_mode=self.vocal_removed_toggle_fade_mode,
            vocal_removed_toggle_custom_sec=self.vocal_removed_toggle_custom_sec,
            vocal_removed_toggle_always_sec=self.vocal_removed_toggle_always_sec,
            talk_volume_level=self.talk_volume_level,
            talk_fade_sec=self.talk_fade_sec,
            talk_volume_mode=self.talk_volume_mode,
            talk_blink_button=self.talk_blink_button,
            log_file_enabled=self.log_file_enabled,
            reset_all_on_startup=self.reset_all_on_startup,
            click_playing_action=self.click_playing_action,
            search_double_click_action=self.search_double_click_action,
            set_file_encoding=self.set_file_encoding,
            main_progress_display_mode=self.main_progress_display_mode,
            main_progress_show_text=self.main_progress_show_text,
            audio_output_device=self.audio_output_device,
            available_audio_devices=available_devices,
            available_midi_devices=available_midi_output_devices,
            preload_audio_enabled=self.preload_audio_enabled,
            preload_current_page_audio=self.preload_current_page_audio,
            preload_audio_memory_limit_mb=self.preload_audio_memory_limit_mb,
            preload_memory_pressure_enabled=self.preload_memory_pressure_enabled,
            preload_pause_on_playback=self.preload_pause_on_playback,
            preload_use_ffmpeg=self.preload_use_ffmpeg,
            waveform_cache_limit_mb=self.waveform_cache_limit_mb,
            waveform_cache_clear_on_launch=self.waveform_cache_clear_on_launch,
            preload_total_ram_mb=total_ram_mb,
            preload_ram_cap_mb=preload_cap_mb,
            timecode_audio_output_device=self.timecode_audio_output_device,
            timecode_midi_output_device=self.timecode_midi_output_device,
            timecode_mode=self.timecode_mode,
            timecode_fps=self.timecode_fps,
            timecode_mtc_fps=self.timecode_mtc_fps,
            timecode_mtc_idle_behavior=self.timecode_mtc_idle_behavior,
            timecode_sample_rate=self.timecode_sample_rate,
            timecode_bit_depth=self.timecode_bit_depth,
            timecode_timeline_mode=self.timecode_timeline_mode,
            soundbutton_timecode_offset_enabled=self.soundbutton_timecode_offset_enabled,
            respect_soundbutton_timecode_timeline_setting=self.respect_soundbutton_timecode_timeline_setting,
            max_multi_play_songs=self.max_multi_play_songs,
            multi_play_limit_action=self.multi_play_limit_action,
            playlist_play_mode=self.playlist_play_mode,
            rapid_fire_play_mode=self.rapid_fire_play_mode,
            next_play_mode=self.next_play_mode,
            playlist_loop_mode=self.playlist_loop_mode,
            candidate_error_action=self.candidate_error_action,
            web_remote_enabled=self.web_remote_enabled,
            web_remote_port=self.web_remote_port,
            web_remote_url=self._web_remote_open_url(),
            main_transport_timeline_mode=self.main_transport_timeline_mode,
            main_jog_outside_cue_action=self.main_jog_outside_cue_action,
            state_colors={
                "playing": self.state_colors["playing"],
                "played": self.state_colors["played"],
                "unplayed": self.state_colors["assigned"],
                "highlight": self.state_colors["highlighted"],
                "lock": self.state_colors["locked"],
                "error": self.state_colors["missing"],
                "place_marker": self.state_colors["marker"],
                "empty": self.state_colors["empty"],
                "copied_to_cue": self.state_colors["copied"],
                "cue_indicator": self.state_colors["cue_indicator"],
                "volume_indicator": self.state_colors["volume_indicator"],
                "midi_indicator": self.state_colors["midi_indicator"],
                "lyric_indicator": self.state_colors["lyric_indicator"],
            },
            sound_button_text_color=self.sound_button_text_color,
            hotkeys=self.hotkeys,
            quick_action_enabled=self.quick_action_enabled,
            quick_action_keys=self.quick_action_keys,
            sound_button_hotkey_enabled=self.sound_button_hotkey_enabled,
            sound_button_hotkey_priority=self.sound_button_hotkey_priority,
            sound_button_hotkey_go_to_playing=self.sound_button_hotkey_go_to_playing,
            midi_input_device_ids=self.midi_input_device_ids,
            midi_hotkeys=self.midi_hotkeys,
            midi_quick_action_enabled=self.midi_quick_action_enabled,
            midi_quick_action_bindings=self.midi_quick_action_bindings,
            midi_sound_button_hotkey_enabled=self.midi_sound_button_hotkey_enabled,
            midi_sound_button_hotkey_priority=self.midi_sound_button_hotkey_priority,
            midi_sound_button_hotkey_go_to_playing=self.midi_sound_button_hotkey_go_to_playing,
            midi_rotary_enabled=self.midi_rotary_enabled,
            midi_rotary_group_binding=self.midi_rotary_group_binding,
            midi_rotary_page_binding=self.midi_rotary_page_binding,
            midi_rotary_sound_button_binding=self.midi_rotary_sound_button_binding,
            midi_rotary_jog_binding=self.midi_rotary_jog_binding,
            midi_rotary_volume_binding=self.midi_rotary_volume_binding,
            midi_rotary_group_invert=self.midi_rotary_group_invert,
            midi_rotary_page_invert=self.midi_rotary_page_invert,
            midi_rotary_sound_button_invert=self.midi_rotary_sound_button_invert,
            midi_rotary_jog_invert=self.midi_rotary_jog_invert,
            midi_rotary_volume_invert=self.midi_rotary_volume_invert,
            midi_rotary_group_sensitivity=self.midi_rotary_group_sensitivity,
            midi_rotary_page_sensitivity=self.midi_rotary_page_sensitivity,
            midi_rotary_sound_button_sensitivity=self.midi_rotary_sound_button_sensitivity,
            midi_rotary_group_relative_mode=self.midi_rotary_group_relative_mode,
            midi_rotary_page_relative_mode=self.midi_rotary_page_relative_mode,
            midi_rotary_sound_button_relative_mode=self.midi_rotary_sound_button_relative_mode,
            midi_rotary_jog_relative_mode=self.midi_rotary_jog_relative_mode,
            midi_rotary_volume_relative_mode=self.midi_rotary_volume_relative_mode,
            midi_rotary_volume_mode=self.midi_rotary_volume_mode,
            midi_rotary_volume_step=self.midi_rotary_volume_step,
            midi_rotary_jog_step_ms=self.midi_rotary_jog_step_ms,
            stage_display_layout=self.stage_display_layout,
            stage_display_visibility=self.stage_display_visibility,
            stage_display_text_source=self.stage_display_text_source,
            window_layout=self.window_layout,
            lock_unlock_method=self.lock_unlock_method,
            lock_require_password=self.lock_require_password,
            lock_password=self.lock_password,
            lock_restart_state=self.lock_restart_state,
            is_playback_or_loading_active=lambda: bool(
                self._is_playback_in_progress() or self._pending_deferred_audio_request is not None
            ),
            stage_display_gadgets=self.stage_display_gadgets,
            ui_language=self.ui_language,
            initial_page=initial_page,
            parent=self,
        )
        self._midi_context_handler = dialog
        self._midi_context_block_actions = True
        if dialog.exec_() != QDialog.Accepted:
            self._midi_context_handler = None
            self._midi_context_block_actions = False
            return
        self._midi_context_handler = None
        self._midi_context_block_actions = False
        self.active_group_color = dialog.active_group_color
        self.inactive_group_color = dialog.inactive_group_color
        self.title_char_limit = dialog.title_limit_spin.value()
        self.lock_allow_quit = dialog.selected_lock_allow_quit()
        self.lock_allow_system_hotkeys = dialog.selected_lock_allow_system_hotkeys()
        self.lock_allow_quick_action_hotkeys = dialog.selected_lock_allow_quick_action_hotkeys()
        self.lock_allow_sound_button_hotkeys = dialog.selected_lock_allow_sound_button_hotkeys()
        self.lock_allow_midi_control = dialog.selected_lock_allow_midi_control()
        self.lock_auto_allow_quit = dialog.selected_lock_auto_allow_quit()
        self.lock_auto_allow_midi_control = dialog.selected_lock_auto_allow_midi_control()
        self.lock_unlock_method = dialog.selected_lock_unlock_method()
        self.lock_require_password = dialog.selected_lock_require_password()
        self.lock_password = dialog.selected_lock_password()
        self.lock_restart_state = dialog.selected_lock_restart_state()
        self.fade_in_sec = dialog.fade_in_spin.value()
        self.cross_fade_sec = dialog.cross_fade_spin.value()
        self.fade_out_sec = dialog.fade_out_spin.value()
        self.fade_on_quick_action_hotkey = dialog.fade_on_quick_action_checkbox.isChecked()
        self.fade_on_sound_button_hotkey = dialog.fade_on_sound_hotkey_checkbox.isChecked()
        self.fade_on_pause = dialog.fade_on_pause_checkbox.isChecked()
        self.fade_on_resume = dialog.fade_on_resume_checkbox.isChecked()
        self.fade_on_stop = dialog.fade_on_stop_checkbox.isChecked()
        self.fade_out_when_done_playing = dialog.fade_out_when_done_checkbox.isChecked()
        self.fade_out_end_lead_sec = dialog.fade_out_end_lead_spin.value()
        self.vocal_removed_toggle_fade_mode = dialog.selected_vocal_removed_toggle_fade_mode()
        self.vocal_removed_toggle_custom_sec = dialog.vocal_removed_toggle_custom_spin.value()
        self.vocal_removed_toggle_always_sec = dialog.vocal_removed_toggle_always_spin.value()
        self.talk_volume_level = dialog.talk_volume_spin.value()
        self.talk_fade_sec = dialog.talk_fade_spin.value()
        self.talk_volume_mode = dialog.selected_talk_volume_mode()
        self.talk_blink_button = dialog.talk_blink_checkbox.isChecked()
        self.log_file_enabled = dialog.log_file_checkbox.isChecked()
        self.reset_all_on_startup = dialog.reset_on_startup_checkbox.isChecked()
        self.click_playing_action = dialog.selected_click_playing_action()
        self.search_double_click_action = dialog.selected_search_double_click_action()
        self.now_playing_display_mode = dialog.selected_now_playing_display_mode()
        self.main_ui_lyric_display_mode = dialog.selected_main_ui_lyric_display_mode()
        self.search_lyric_on_add_sound_button = dialog.selected_search_lyric_on_add_sound_button()
        self.new_lyric_file_format = dialog.selected_new_lyric_file_format()
        self.supported_audio_format_extensions = dialog.selected_supported_audio_format_extensions()
        self.verify_sound_file_on_add = dialog.selected_verify_sound_file_on_add()
        self.allow_other_unsupported_audio_files = dialog.selected_allow_other_unsupported_audio_files()
        self.disable_path_safety = dialog.selected_disable_path_safety()
        self._refresh_lyric_display(force=True)
        selected_set_file_encoding = dialog.selected_set_file_encoding()
        if selected_set_file_encoding != self.set_file_encoding:
            self.set_file_encoding = selected_set_file_encoding
            self._set_dirty(True)
        else:
            self.set_file_encoding = selected_set_file_encoding
        self.max_multi_play_songs = dialog.selected_max_multi_play_songs()
        self.multi_play_limit_action = dialog.selected_multi_play_limit_action()
        self.playlist_play_mode = dialog.selected_playlist_play_mode()
        self.rapid_fire_play_mode = dialog.selected_rapid_fire_play_mode()
        self.next_play_mode = dialog.selected_next_play_mode()
        self.playlist_loop_mode = dialog.selected_playlist_loop_mode()
        self.candidate_error_action = dialog.selected_candidate_error_action()
        self.main_transport_timeline_mode = dialog.selected_main_transport_timeline_mode()
        self.main_progress_display_mode = dialog.selected_main_progress_display_mode()
        self.main_progress_show_text = dialog.selected_main_progress_show_text()
        self.progress_label.set_display_mode(self.main_progress_display_mode)
        if self.main_progress_display_mode == "waveform":
            self._schedule_main_waveform_refresh(0)
        self.main_jog_outside_cue_action = dialog.selected_main_jog_outside_cue_action()
        self._refresh_main_jog_meta(self.seek_slider.value(), self._transport_total_ms())
        self.timecode_timeline_mode = dialog.selected_timecode_timeline_mode()
        self.soundbutton_timecode_offset_enabled = dialog.selected_soundbutton_timecode_offset_enabled()
        self.respect_soundbutton_timecode_timeline_setting = (
            dialog.selected_respect_soundbutton_timecode_timeline_setting()
        )
        self.timecode_audio_output_device = dialog.selected_timecode_audio_output_device()
        self.timecode_midi_output_device = dialog.selected_timecode_midi_output_device()
        selected_timecode_mode = dialog.selected_timecode_mode()
        if (
            selected_timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE
            and self.timecode_mode != TIMECODE_MODE_FOLLOW_FREEZE
        ):
            self._timecode_follow_frozen_ms = self._timecode_current_follow_ms()
        self.timecode_mode = selected_timecode_mode
        self.timecode_fps = dialog.selected_timecode_fps()
        self.timecode_mtc_fps = dialog.selected_timecode_mtc_fps()
        self.timecode_mtc_idle_behavior = dialog.selected_timecode_mtc_idle_behavior()
        self.timecode_sample_rate = dialog.selected_timecode_sample_rate()
        self.timecode_bit_depth = dialog.selected_timecode_bit_depth()
        selected_colors = dialog.selected_state_colors()
        self.state_colors["playing"] = selected_colors.get("playing", self.state_colors["playing"])
        self.state_colors["played"] = selected_colors.get("played", self.state_colors["played"])
        self.state_colors["assigned"] = selected_colors.get("unplayed", self.state_colors["assigned"])
        self.state_colors["highlighted"] = selected_colors.get("highlight", self.state_colors["highlighted"])
        self.state_colors["locked"] = selected_colors.get("lock", self.state_colors["locked"])
        self.state_colors["missing"] = selected_colors.get("error", self.state_colors["missing"])
        self.state_colors["marker"] = selected_colors.get("place_marker", self.state_colors["marker"])
        self.state_colors["empty"] = selected_colors.get("empty", self.state_colors["empty"])
        self.state_colors["copied"] = selected_colors.get("copied_to_cue", self.state_colors["copied"])
        self.state_colors["cue_indicator"] = selected_colors.get("cue_indicator", self.state_colors["cue_indicator"])
        self.state_colors["volume_indicator"] = selected_colors.get(
            "volume_indicator",
            self.state_colors["volume_indicator"],
        )
        self.state_colors["midi_indicator"] = selected_colors.get("midi_indicator", self.state_colors["midi_indicator"])
        self.state_colors["lyric_indicator"] = selected_colors.get(
            "lyric_indicator",
            self.state_colors["lyric_indicator"],
        )
        self.sound_button_text_color = dialog.selected_sound_button_text_color()
        self.hotkeys = dialog.selected_hotkeys()
        self.quick_action_enabled = dialog.selected_quick_action_enabled()
        self.quick_action_keys = dialog.selected_quick_action_keys()[:48]
        if len(self.quick_action_keys) < 48:
            self.quick_action_keys.extend(["" for _ in range(48 - len(self.quick_action_keys))])
        self.sound_button_hotkey_enabled = dialog.selected_sound_button_hotkey_enabled()
        self.sound_button_hotkey_priority = dialog.selected_sound_button_hotkey_priority()
        self.sound_button_hotkey_go_to_playing = dialog.selected_sound_button_hotkey_go_to_playing()
        self.midi_input_device_ids = dialog.selected_midi_input_devices()
        self.midi_hotkeys = dialog.selected_midi_hotkeys()
        self.midi_quick_action_enabled = dialog.selected_midi_quick_action_enabled()
        self.midi_quick_action_bindings = dialog.selected_midi_quick_action_bindings()[:48]
        if len(self.midi_quick_action_bindings) < 48:
            self.midi_quick_action_bindings.extend(["" for _ in range(48 - len(self.midi_quick_action_bindings))])
        self.midi_sound_button_hotkey_enabled = dialog.selected_midi_sound_button_hotkey_enabled()
        self.midi_sound_button_hotkey_priority = dialog.selected_midi_sound_button_hotkey_priority()
        self.midi_sound_button_hotkey_go_to_playing = dialog.selected_midi_sound_button_hotkey_go_to_playing()
        self.midi_rotary_enabled = dialog.selected_midi_rotary_enabled()
        self.midi_rotary_group_binding = normalize_midi_binding(dialog.selected_midi_rotary_group_binding())
        self.midi_rotary_page_binding = normalize_midi_binding(dialog.selected_midi_rotary_page_binding())
        self.midi_rotary_sound_button_binding = normalize_midi_binding(dialog.selected_midi_rotary_sound_button_binding())
        self.midi_rotary_jog_binding = normalize_midi_binding(dialog.selected_midi_rotary_jog_binding())
        self.midi_rotary_volume_binding = normalize_midi_binding(dialog.selected_midi_rotary_volume_binding())
        self.midi_rotary_group_invert = bool(dialog.selected_midi_rotary_group_invert())
        self.midi_rotary_page_invert = bool(dialog.selected_midi_rotary_page_invert())
        self.midi_rotary_sound_button_invert = bool(dialog.selected_midi_rotary_sound_button_invert())
        self.midi_rotary_jog_invert = bool(dialog.selected_midi_rotary_jog_invert())
        self.midi_rotary_volume_invert = bool(dialog.selected_midi_rotary_volume_invert())
        self.midi_rotary_group_sensitivity = max(1, min(20, int(dialog.selected_midi_rotary_group_sensitivity())))
        self.midi_rotary_page_sensitivity = max(1, min(20, int(dialog.selected_midi_rotary_page_sensitivity())))
        self.midi_rotary_sound_button_sensitivity = max(
            1, min(20, int(dialog.selected_midi_rotary_sound_button_sensitivity()))
        )
        self.midi_rotary_group_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_group_relative_mode()
        )
        self.midi_rotary_page_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_page_relative_mode()
        )
        self.midi_rotary_sound_button_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_sound_button_relative_mode()
        )
        self.midi_rotary_jog_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_jog_relative_mode()
        )
        self.midi_rotary_volume_relative_mode = self._normalize_midi_relative_mode(
            dialog.selected_midi_rotary_volume_relative_mode()
        )
        mode = str(dialog.selected_midi_rotary_volume_mode()).strip().lower()
        self.midi_rotary_volume_mode = mode if mode in {"absolute", "relative"} else "relative"
        self.midi_rotary_volume_step = max(1, min(20, int(dialog.selected_midi_rotary_volume_step())))
        self.midi_rotary_jog_step_ms = max(10, min(5000, int(dialog.selected_midi_rotary_jog_step_ms())))
        self.stage_display_gadgets = normalize_stage_display_gadgets(dialog.selected_stage_display_gadgets())
        self.stage_display_layout, self.stage_display_visibility = gadgets_to_legacy_layout_visibility(
            self.stage_display_gadgets
        )
        self.stage_display_text_source = dialog.selected_stage_display_text_source()
        self.window_layout = normalize_window_layout(dialog.selected_window_layout())
        self._apply_top_control_layout()
        if self._stage_display_window is not None:
            self._stage_display_window.configure_gadgets(self.stage_display_gadgets)
            self._refresh_stage_display()
        selected_ui_language = dialog.selected_ui_language()
        if selected_ui_language != self.ui_language:
            self.ui_language = selected_ui_language
            self._apply_language()
        self._apply_hotkeys()
        self.web_remote_enabled = dialog.web_remote_enabled_checkbox.isChecked()
        self.web_remote_port = max(1, min(65534, int(dialog.web_remote_port_spin.value())))
        self.web_remote_ws_port = int(self.web_remote_port) + 1
        if self._search_window is not None:
            self._search_window.set_double_click_action(self.search_double_click_action)
        selected_device = dialog.selected_audio_output_device()
        self.preload_audio_enabled = dialog.selected_preload_audio_enabled()
        self.preload_current_page_audio = dialog.selected_preload_current_page_audio()
        self.preload_audio_memory_limit_mb = dialog.selected_preload_audio_memory_limit_mb()
        self.preload_memory_pressure_enabled = dialog.selected_preload_memory_pressure_enabled()
        self.preload_pause_on_playback = dialog.selected_preload_pause_on_playback()
        self.preload_use_ffmpeg = dialog.selected_preload_use_ffmpeg()
        self.waveform_cache_limit_mb = dialog.selected_waveform_cache_limit_mb()
        self.waveform_cache_clear_on_launch = dialog.selected_waveform_cache_clear_on_launch()
        self._apply_audio_preload_cache_settings()
        configure_waveform_disk_cache(self.waveform_cache_limit_mb)
        if selected_device != self.audio_output_device:
            if self._switch_audio_device(selected_device):
                self.audio_output_device = selected_device
        self._apply_talk_state_volume(fade=True)
        self._update_talk_button_visual()
        self._sync_playlist_shuffle_buttons()
        self._refresh_main_transport_display()
        self._refresh_timecode_panel()
        self._update_timecode_multiplay_warning_banner()
        self._refresh_group_buttons()
        self._refresh_sound_grid()
        if self.current_playing is None:
            self._update_now_playing_label("")
        else:
            slot = self._slot_for_key(self.current_playing)
            self._update_now_playing_label(self._build_now_playing_text(slot) if slot is not None else "")
        self._apply_web_remote_state()
        self._sync_lock_ui_state()
        self._save_settings()

    def _handle_space_bar_action(self) -> None:
        if self._search_window is not None and self._search_window.isVisible():
            active = QApplication.activeWindow()
            if active is self._search_window:
                if self._search_window.activate_selected_by_setting():
                    return
        self._stop_playback()
        return

    def keyPressEvent(self, event) -> None:
        if self._ui_locked and not self._is_locked_input_allowed("system"):
            event.accept()
            return
        if event.isAutoRepeat():
            QMainWindow.keyPressEvent(self, event)
            return
        key = int(event.key())
        handlers = self._modifier_hotkey_handlers.get(key)
        if handlers:
            if key not in self._modifier_hotkey_down:
                self._modifier_hotkey_down.add(key)
                for handler in handlers:
                    handler()
            return
        QMainWindow.keyPressEvent(self, event)

    def _click_control_button(self, key: str) -> None:
        button = self.control_buttons.get(key)
        if button is None or (not button.isEnabled()):
            return
        button.click()

    def _toggle_control_button(self, key: str) -> None:
        button = self.control_buttons.get(key)
        if button is None or (not button.isEnabled()) or (not button.isCheckable()):
            return
        button.click()

    def _hotkey_toggle_talk(self) -> None:
        self._toggle_control_button("Talk")

    def _hotkey_toggle_lyric_navigator(self) -> None:
        if self._lyric_navigator_window is not None and self._lyric_navigator_window.isVisible():
            self._lyric_navigator_window.hide()
            return
        self._open_lyric_navigator()

    def _hotkey_select_group_delta(self, delta: int) -> None:
        if self.cue_mode:
            self._toggle_cue_mode(False)
        try:
            idx = GROUPS.index(self.current_group)
        except ValueError:
            idx = 0
        next_idx = (idx + delta) % len(GROUPS)
        self._select_group(GROUPS[next_idx])

    def _hotkey_select_page_delta(self, delta: int) -> None:
        if self.cue_mode:
            self._toggle_cue_mode(False)
        next_page = (self.current_page + delta) % PAGE_COUNT
        self._select_page(next_page)

    def _hotkey_select_sound_button_delta(self, delta: int) -> None:
        if self._search_window is not None and self._search_window.isVisible():
            if self._search_window.select_result_delta(delta):
                return
        page = self._current_page_slots()
        candidates = [i for i, slot in enumerate(page) if slot.assigned and not slot.marker]
        if not candidates:
            return
        current_index = -1
        key = self._hotkey_selected_slot_key
        if key is not None and key[0] == self._view_group_key() and key[1] == self.current_page:
            current_index = key[2]
        elif self.current_playing is not None and self.current_playing[0] == self._view_group_key() and self.current_playing[1] == self.current_page:
            current_index = self.current_playing[2]

        if current_index in candidates:
            pos = candidates.index(current_index)
            next_slot = candidates[(pos + delta) % len(candidates)]
        else:
            next_slot = candidates[0] if delta >= 0 else candidates[-1]

        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, next_slot)
        self.sound_buttons[next_slot].setFocus()
        self._on_sound_button_hover(next_slot)
        self._refresh_sound_grid()

    def _hotkey_play_selected(self) -> None:
        if self._search_window is not None and self._search_window.isVisible():
            if self._search_window.activate_selected_by_setting():
                return
        slot_index: Optional[int] = None
        key = self._hotkey_selected_slot_key
        if key is not None and key[0] == self._view_group_key() and key[1] == self.current_page:
            slot_index = key[2]
        else:
            for i, btn in enumerate(self.sound_buttons):
                if btn.hasFocus():
                    slot_index = i
                    break
        if slot_index is None:
            return
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        self._play_slot(slot_index)

    def _hotkey_play_selected_pause(self) -> None:
        if self._search_window is not None and self._search_window.isVisible():
            if self._search_window.activate_selected_by_setting():
                return
        slot_index: Optional[int] = None
        key = self._hotkey_selected_slot_key
        if key is not None and key[0] == self._view_group_key() and key[1] == self.current_page:
            slot_index = key[2]
        else:
            for i, btn in enumerate(self.sound_buttons):
                if btn.hasFocus():
                    slot_index = i
                    break
        if slot_index is None:
            return
        selected_key = (self._view_group_key(), self.current_page, slot_index)
        self._hotkey_selected_slot_key = selected_key

        selected_playing: List[ExternalMediaPlayer] = []
        selected_paused: List[ExternalMediaPlayer] = []
        for player in [self.player, self.player_b, *self._multi_players]:
            if self._player_slot_key_map.get(id(player)) != selected_key:
                continue
            state = player.state()
            if state == ExternalMediaPlayer.PlayingState:
                selected_playing.append(player)
            elif state == ExternalMediaPlayer.PausedState:
                selected_paused.append(player)

        if selected_playing:
            self._pause_players(selected_playing)
            self._timecode_on_playback_pause()
            self._update_pause_button_label()
            return
        if selected_paused:
            self._resume_players(selected_paused)
            self._update_pause_button_label()
            return
        self._play_slot(slot_index)

    def _quick_action_trigger(self, slot_index: int) -> None:
        if slot_index < 0 or slot_index >= SLOTS_PER_PAGE:
            return
        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        self._play_slot(slot_index, allow_fade=self.fade_on_quick_action_hotkey)

    def _registered_system_and_quick_tokens(self) -> set[str]:
        tokens: set[str] = set()
        for key in SYSTEM_HOTKEY_ORDER_DEFAULT:
            h1, h2 = self._normalized_hotkey_pair(key)
            for seq_text in [h1, h2]:
                key_token = self._normalize_hotkey_text(seq_text)
                if not key_token:
                    continue
                modifier_key = self._modifier_key_from_hotkey_text(seq_text)
                if modifier_key is not None:
                    tokens.add(key_token)
                    continue
                seq = self._key_sequence_from_hotkey_text(seq_text)
                if seq is not None:
                    tokens.add(key_token)
        if self.quick_action_enabled:
            for raw in self.quick_action_keys[:48]:
                key_token = self._normalize_hotkey_text(raw)
                if not key_token:
                    continue
                seq = self._key_sequence_from_hotkey_text(raw)
                if seq is not None:
                    tokens.add(key_token)
        return tokens

    def _active_button_trigger_badges(
        self,
        slot_index: int,
        slot: SoundButtonData,
        sound_bindings: Dict[str, Tuple[str, int, int]],
        blocked_sound_tokens: set[str],
    ) -> List[str]:
        if not slot.assigned or slot.marker:
            return []
        badges: List[str] = []
        seen: set[str] = set()
        slot_key = (self._view_group_key(), self.current_page, slot_index)
        if self.sound_button_hotkey_enabled:
            sound_token = self._normalize_hotkey_text(self._parse_sound_hotkey(slot.sound_hotkey))
            if sound_token and sound_bindings.get(sound_token) == slot_key:
                if sound_token not in blocked_sound_tokens:
                    badge = f"[{sound_token.lower()}]"
                    badges.append(badge)
                    seen.add(badge)

        if self.quick_action_enabled and slot_index < len(self.quick_action_keys):
            quick_token = self._normalize_hotkey_text(self.quick_action_keys[slot_index])
            if quick_token and self._key_sequence_from_hotkey_text(quick_token) is not None:
                quick_blocked = (
                    self.sound_button_hotkey_enabled
                    and self.sound_button_hotkey_priority == "sound_button_first"
                    and quick_token in sound_bindings
                )
                if not quick_blocked:
                    badge = f"[{quick_token.lower()}]"
                    if badge not in seen:
                        badges.append(badge)
        return badges

    def _collect_sound_button_hotkey_bindings(self) -> Dict[str, Tuple[str, int, int]]:
        bindings: Dict[str, Tuple[str, int, int]] = {}
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    token = self._normalize_hotkey_text(self._parse_sound_hotkey(slot.sound_hotkey))
                    if not token or token in bindings:
                        continue
                    bindings[token] = (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned or slot.marker:
                continue
            token = self._normalize_hotkey_text(self._parse_sound_hotkey(slot.sound_hotkey))
            if not token or token in bindings:
                continue
            bindings[token] = ("Q", 0, slot_index)
        return bindings

    def _collect_sound_button_midi_bindings(self) -> Dict[str, Tuple[str, int, int]]:
        bindings: Dict[str, Tuple[str, int, int]] = {}
        for group in GROUPS:
            for page_index in range(PAGE_COUNT):
                for slot_index, slot in enumerate(self.data[group][page_index]):
                    if not slot.assigned or slot.marker:
                        continue
                    token = normalize_midi_binding(slot.sound_midi_hotkey)
                    if not token or token in bindings:
                        continue
                    bindings[token] = (group, page_index, slot_index)
        for slot_index, slot in enumerate(self.cue_page):
            if not slot.assigned or slot.marker:
                continue
            token = normalize_midi_binding(slot.sound_midi_hotkey)
            if not token or token in bindings:
                continue
            bindings[token] = ("Q", 0, slot_index)
        return bindings

    def _sound_button_hotkey_trigger(self, slot_key: Tuple[str, int, int]) -> None:
        if self._is_button_drag_enabled():
            return
        old_cue_mode = self.cue_mode
        old_group = self.current_group
        old_page = self.current_page

        group, page_index, slot_index = slot_key
        if group == "Q":
            self._toggle_cue_mode(True)
        else:
            if self.cue_mode:
                self._toggle_cue_mode(False)
            if group in GROUPS:
                self._select_group(group)
                self._select_page(max(0, min(PAGE_COUNT - 1, int(page_index))))

        self._hotkey_selected_slot_key = (self._view_group_key(), self.current_page, slot_index)
        self._play_slot(slot_index, allow_fade=self.fade_on_sound_button_hotkey)

        if self.sound_button_hotkey_go_to_playing:
            self._go_to_current_playing_page()
            return

        if old_cue_mode:
            self._toggle_cue_mode(True)
        else:
            if self.cue_mode:
                self._toggle_cue_mode(False)
            self._select_group(old_group)
            self._select_page(old_page)

    def _sound_button_midi_hotkey_trigger(self, slot_key: Tuple[str, int, int]) -> None:
        self._sound_button_hotkey_trigger(slot_key)
        if self.midi_sound_button_hotkey_go_to_playing:
            self._go_to_current_playing_page()

    def _poll_midi_inputs(self) -> None:
        try:
            self._midi_router.poll()
        except Exception:
            pass
        now = time.perf_counter()
        if (now - self._midi_last_status_scan_t) < 0.9:
            return
        self._midi_last_status_scan_t = now
        try:
            self._midi_router.set_devices(self.midi_input_device_ids)
        except Exception:
            pass
        try:
            self._refresh_midi_connection_warning(force_refresh=False)
        except Exception:
            pass
        if self.midi_input_device_ids and (now - self._midi_last_periodic_force_rebind_t) >= 5.0:
            self._midi_last_periodic_force_rebind_t = now
            try:
                self._midi_router.set_devices(self.midi_input_device_ids, force_refresh=True)
            except Exception:
                pass
            try:
                self._refresh_midi_connection_warning(force_refresh=True)
            except Exception:
                pass
        if self._midi_missing_selectors and (now - self._midi_last_force_rescan_t) >= 2.5:
            self._midi_last_force_rescan_t = now
            # When some selected devices are missing, force backend re-enumeration
            # so reconnect works even if other MIDI devices remain active.
            try:
                self._midi_router.set_devices(self.midi_input_device_ids, force_refresh=True)
            except Exception:
                pass
            try:
                self._refresh_midi_connection_warning(force_refresh=True)
            except Exception:
                pass

    def _cc_binding_matches(self, configured: str, source_selector: str, cc_token: str) -> bool:
        selector, token = split_midi_binding(configured)
        if not token or token != cc_token:
            return False
        if not selector:
            return True
        return selector == source_selector

    @staticmethod
    def _normalize_midi_relative_mode(mode: str) -> str:
        token = str(mode or "").strip().lower()
        if token in {"auto", "twos_complement", "sign_magnitude", "binary_offset"}:
            return token
        return "auto"

    @staticmethod
    def _midi_cc_relative_delta(value: int, mode: str = "auto") -> int:
        v = int(value) & 0x7F
        if v == 64:
            return 0
        mode_name = MainWindow._normalize_midi_relative_mode(mode)
        if mode_name == "binary_offset":
            return v - 64
        if mode_name == "sign_magnitude":
            if 1 <= v <= 63:
                return v
            if 65 <= v <= 127:
                return -(v - 64)
            return 0
        # twos_complement and auto fallback
        if 1 <= v <= 63:
            return v
        if 65 <= v <= 127:
            return v - 128
        return 0

    @staticmethod
    def _midi_pitch_relative_delta(data1: int, data2: int) -> int:
        # Many controllers encode relative pitch as 7-bit value in data2.
        if int(data1) == 0:
            return MainWindow._midi_cc_relative_delta(data2)
        # Fallback to signed delta around center for full 14-bit pitch bend.
        value14 = (int(data1) & 0x7F) | ((int(data2) & 0x7F) << 7)
        if value14 == 8192:
            return 0
        return 1 if value14 > 8192 else -1

    def _apply_midi_rotary(self, source_selector: str, status: int, data1: int, data2: int) -> bool:
        if not self.midi_rotary_enabled:
            return False
        status = int(status) & 0xFF
        data1 = int(data1) & 0xFF
        data2 = int(data2) & 0xFF
        high = status & 0xF0
        if high not in {0xB0, 0xE0}:
            return False
        source_token = ""
        if high == 0xB0:
            source_token = normalize_midi_binding(f"{status:02X}:{data1:02X}")
        elif high == 0xE0:
            source_token = normalize_midi_binding(f"{status:02X}")
        if not source_token:
            return False
        if self._cc_binding_matches(self.midi_rotary_group_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_group_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                nav_delta = raw_delta
                if self.midi_rotary_group_invert:
                    nav_delta = -nav_delta
                effective_delta = self._midi_rotary_apply_sensitivity("group", nav_delta, self.midi_rotary_group_sensitivity)
                if effective_delta == 0:
                    return True
                self._hotkey_select_group_delta(effective_delta)
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_page_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_page_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                nav_delta = raw_delta
                if self.midi_rotary_page_invert:
                    nav_delta = -nav_delta
                effective_delta = self._midi_rotary_apply_sensitivity("page", nav_delta, self.midi_rotary_page_sensitivity)
                if effective_delta == 0:
                    return True
                self._hotkey_select_page_delta(effective_delta)
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_sound_button_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_sound_button_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                nav_delta = raw_delta
                if self.midi_rotary_sound_button_invert:
                    nav_delta = -nav_delta
                effective_delta = self._midi_rotary_apply_sensitivity(
                    "sound_button",
                    nav_delta,
                    self.midi_rotary_sound_button_sensitivity,
                )
                if effective_delta == 0:
                    return True
                self._hotkey_select_sound_button_delta(effective_delta)
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_volume_binding, source_selector, source_token):
            if self.midi_rotary_volume_mode == "absolute":
                if high == 0xB0:
                    level = int(round((max(0, min(127, int(data2))) / 127.0) * 100.0))
                else:
                    value14 = (int(data1) & 0x7F) | ((int(data2) & 0x7F) << 7)
                    level = int(round((max(0, min(16383, value14)) / 16383.0) * 100.0))
                if self.midi_rotary_volume_invert:
                    level = 100 - level
                self.volume_slider.setValue(max(0, min(100, level)))
                return True
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_volume_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                if self.midi_rotary_volume_invert:
                    raw_delta = -raw_delta
                current = int(self.volume_slider.value())
                next_level = current + (int(self.midi_rotary_volume_step) * raw_delta)
                self.volume_slider.setValue(max(0, min(100, next_level)))
                return True
            return False
        if self._cc_binding_matches(self.midi_rotary_jog_binding, source_selector, source_token):
            raw_delta = (
                self._midi_cc_relative_delta(data2, self.midi_rotary_jog_relative_mode)
                if high == 0xB0
                else self._midi_pitch_relative_delta(data1, data2)
            )
            if raw_delta != 0:
                if self.midi_rotary_jog_invert:
                    raw_delta = -raw_delta
                current = int(self.seek_slider.value())
                total_ms = self._transport_total_ms()
                next_display = max(0, min(total_ms, current + (int(self.midi_rotary_jog_step_ms) * raw_delta)))
                absolute = self._transport_absolute_ms_for_display(next_display)
                self.player.setPosition(max(0, int(absolute)))
                self.seek_slider.setValue(next_display)
                return True
            return False
        return False

    def _midi_rotary_apply_sensitivity(self, key: str, raw_delta: int, sensitivity: int) -> int:
        delta = int(raw_delta)
        sens = max(1, int(sensitivity))
        if sens <= 1:
            return delta
        if not hasattr(self, "_midi_rotary_nav_accum"):
            self._midi_rotary_nav_accum = {}
        accum = int(self._midi_rotary_nav_accum.get(key, 0)) + delta
        out = 0
        while accum >= sens:
            out += 1
            accum -= sens
        while accum <= -sens:
            out -= 1
            accum += sens
        self._midi_rotary_nav_accum[key] = accum
        return out

    def _on_midi_binding_triggered(
        self,
        token: str,
        source_selector: str = "",
        status: int = 0,
        data1: int = 0,
        data2: int = 0,
    ) -> None:
        context_handler = self._midi_context_handler
        if context_handler is not None:
            try:
                if bool(context_handler.handle_midi_message(token, source_selector, status, data1, data2)):
                    return
            except Exception:
                pass
        if self._midi_context_block_actions:
            return
        if self._is_locked_input_allowed("midi") and self._apply_midi_rotary(source_selector, status, data1, data2):
            return
        _selector, normalized_token = split_midi_binding(token)
        if not normalized_token:
            return
        key_from_source = (
            normalize_midi_binding(f"{source_selector}|{normalized_token}")
            if source_selector
            else normalized_token
        )
        # Prefer device-specific bindings, then fall back to generic bindings.
        handler = self._midi_action_handlers.get(key_from_source) or self._midi_action_handlers.get(normalized_token)
        if handler is None:
            return
        now = time.perf_counter()
        dedupe_key = key_from_source if key_from_source in self._midi_action_handlers else normalized_token
        last = self._midi_last_trigger_t.get(dedupe_key, 0.0)
        if (now - last) < 0.06:
            return
        self._midi_last_trigger_t[dedupe_key] = now
        handler()

    def _toggle_mute_hotkey(self) -> None:
        current = int(self.volume_slider.value())
        if current > 0:
            self._pre_mute_volume = current
            self.volume_slider.setValue(0)
            return
        restore = self._pre_mute_volume if self._pre_mute_volume is not None else 90
        self.volume_slider.setValue(max(0, min(100, int(restore))))

    def _adjust_volume_hotkey(self, delta: int) -> None:
        current = int(self.volume_slider.value())
        self.volume_slider.setValue(max(0, min(100, current + int(delta))))

    def _volume_up_hotkey(self) -> None:
        self._adjust_volume_hotkey(5)

    def _volume_down_hotkey(self) -> None:
        self._adjust_volume_hotkey(-5)

    def keyReleaseEvent(self, event) -> None:
        key = int(event.key())
        if key in self._modifier_hotkey_down:
            self._modifier_hotkey_down.discard(key)
            return
        QMainWindow.keyReleaseEvent(self, event)

    def closeEvent(self, event) -> None:
        lock_allows_quit = self.lock_auto_allow_quit if self._automation_locked else self.lock_allow_quit
        if self._ui_locked and not lock_allows_quit:
            self.statusBar().showMessage(tr("Unlock the screen before closing pySSP."), 3000)
            event.ignore()
            return
        if self._is_playback_in_progress():
            answer = QMessageBox.warning(
                self,
                "Playback In Progress",
                "Playback is in progress. Quit anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Unsaved Changes",
                "This set has unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save:
                self._save_set()
                if self._dirty:
                    event.ignore()
                    return
        self._hard_stop_all()
        try:
            self._ltc_sender.shutdown()
        except Exception:
            pass
        try:
            self._mtc_sender.shutdown()
        except Exception:
            pass
        try:
            shutdown_audio_preload()
        except Exception:
            pass
        try:
            self._midi_poll_timer.stop()
        except Exception:
            pass
        try:
            self._midi_router.close()
        except Exception:
            pass
        try:
            if self._stage_display_window is not None:
                self._stage_display_window.close()
        except Exception:
            pass
        try:
            if self._lyric_display_window is not None:
                self._lyric_display_window.close()
        except Exception:
            pass
        try:
            if self._lyric_navigator_window is not None:
                self._lyric_navigator_window.close()
        except Exception:
            pass
        self._stop_web_remote_service()
        if not self._skip_save_on_close:
            self._save_settings()
        QMainWindow.closeEvent(self, event)

