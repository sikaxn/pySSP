from __future__ import annotations

from dataclasses import dataclass

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *
from pyssp.automation_command import (
    AUTOMATION_SOURCE_TYPE,
    normalize_automation_spec,
    normalize_sound_button_automation_config,
)
from pyssp.utility_audio import FILE_SOURCE_TYPE, normalize_utility_spec, utility_is_infinite


@dataclass
class _TrackEndTransitionState:
    source_key: Optional[Tuple[str, int, int]]
    source_slot: Optional[SoundButtonData]
    controls_follow_source: bool
    playlist_enabled: bool
    should_loop: bool
    manual_stop: bool
    pending_target_key: Optional[Tuple[str, int, int]] = None


class PlaybackMixin:
    def _current_transport_is_infinite_utility(self) -> bool:
        slot_key = self.current_playing
        if slot_key is None:
            return False
        slot = self._slot_for_key(slot_key)
        if slot is None or slot.source_type != "utility":
            return False
        return utility_is_infinite(slot.utility_spec)

    def _transport_total_label_text(self, total_ms: int) -> str:
        if self._current_transport_is_infinite_utility():
            return "inf"
        return format_clock_time(total_ms)

    def _transport_remaining_label_text(self, remaining_ms: int) -> str:
        if self._current_transport_is_infinite_utility():
            return "inf"
        return format_clock_time(remaining_ms)

    @staticmethod
    def _is_audio_player(player) -> bool:
        return isinstance(player, (ExternalMediaPlayer, AudioPlayerProxy))

    def _play_slot_via_control_flow(
        self,
        slot_index: int,
        allow_fade: bool = True,
        *,
        continue_playlist_after_automation: bool = True,
    ) -> bool:
        try:
            return self._play_slot(
                slot_index,
                allow_fade=allow_fade,
                prefer_immediate_load=True,
                continue_playlist_after_automation=continue_playlist_after_automation,
                trigger_source="playback_control",
            )
        except TypeError as exc:
            message = str(exc)
            if "trigger_source" not in message:
                if (
                    "prefer_immediate_load" not in message
                    and "continue_playlist_after_automation" not in message
                ):
                    raise
            try:
                return self._play_slot(
                    slot_index,
                    allow_fade=allow_fade,
                    prefer_immediate_load=True,
                    continue_playlist_after_automation=continue_playlist_after_automation,
                )
            except TypeError as inner_exc:
                inner_message = str(inner_exc)
                if (
                    "prefer_immediate_load" not in inner_message
                    and "continue_playlist_after_automation" not in inner_message
                ):
                    raise
                try:
                    return self._play_slot(
                        slot_index,
                        allow_fade=allow_fade,
                        continue_playlist_after_automation=continue_playlist_after_automation,
                    )
                except TypeError as final_exc:
                    if "continue_playlist_after_automation" not in str(final_exc):
                        raise
                    return self._play_slot(slot_index, allow_fade=allow_fade)

    def _clear_track_end_transition_state(self) -> None:
        self._track_end_transition_state = None

    def _finalize_primary_stop_after_transition(self) -> None:
        self._clear_track_end_transition_state()
        self.current_playing = None
        self._last_ui_position_ms = -1
        self.elapsed_time.setText("00:00:00")
        self.remaining_time.setText("00:00:00")
        self._set_progress_display(0)
        self.seek_slider.setValue(0)
        self._update_now_playing_label("")
        self._refresh_sound_grid()

    def _track_end_transition_target_key(self) -> Optional[Tuple[str, int, int]]:
        transition = getattr(self, "_track_end_transition_state", None)
        if transition is None:
            return None
        return transition.pending_target_key

    def _emit_interruption_events_for_active_players(self, trigger_source: str) -> None:
        event_token = (
            "playback_control"
            if str(trigger_source or "").strip().lower() == "playback_control"
            else "sound_button"
        )
        for player in self._all_active_players():
            slot_key = self._player_slot_key_map.get(id(player))
            if slot_key is None:
                continue
            if event_token == "playback_control":
                self._trigger_sound_button_interrupted_by_playback_control_event(slot_key)
            else:
                self._trigger_sound_button_interrupted_by_sound_button_event(slot_key)

    def _capture_track_end_transition_state(self) -> _TrackEndTransitionState:
        stopped_key = self._player_slot_key_map.get(id(self.player))
        source_key = stopped_key if stopped_key is not None else self.current_playing
        source_slot = self._slot_for_key(source_key) if source_key is not None else None
        controls_follow_source = self._slot_follows_regular_playback_controls(source_slot)
        playlist_enabled = False
        if source_key is not None and controls_follow_source:
            source_group, source_page, _source_slot = source_key
            if source_group != "Q" and 0 <= int(source_page) < PAGE_COUNT:
                playlist_enabled = bool(self.page_playlist_enabled[source_group][int(source_page)])
        manual_stop = bool(self._manual_stop_requested)
        should_loop = bool(
            self.loop_enabled
            and source_key is not None
            and controls_follow_source
            and (not manual_stop)
            and (not playlist_enabled)
        )
        return _TrackEndTransitionState(
            source_key=source_key,
            source_slot=source_slot,
            controls_follow_source=controls_follow_source,
            playlist_enabled=playlist_enabled,
            should_loop=should_loop,
            manual_stop=manual_stop,
        )

    def _apply_track_end_source_view(self, transition: _TrackEndTransitionState) -> bool:
        source_key = transition.source_key
        if source_key is None:
            return False
        source_group, source_page, _source_slot = source_key
        if source_group == "Q":
            self.cue_mode = True
        else:
            self.cue_mode = False
            self.current_group = source_group
        self.current_page = int(source_page)
        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._refresh_page_list()
        return True

    def _track_end_transition_started(
        self,
        transition: _TrackEndTransitionState,
        slot_index: int,
    ) -> Optional[bool]:
        source_key = transition.source_key
        if source_key is None:
            return False
        target_key = (source_key[0], int(source_key[1]), int(slot_index))
        target_slot = self._slot_for_key(target_key)
        continue_playlist_after_automation = not (
            target_slot is not None and target_slot.source_type == AUTOMATION_SOURCE_TYPE
        )
        try:
            started_ok = self._play_slot_via_control_flow(
                slot_index,
                continue_playlist_after_automation=continue_playlist_after_automation,
            )
        except TypeError as exc:
            if "continue_playlist_after_automation" not in str(exc):
                raise
            started_ok = self._play_slot_via_control_flow(slot_index)
        if not started_ok:
            self._clear_track_end_transition_state()
            return False
        if target_slot is not None and target_slot.source_type == AUTOMATION_SOURCE_TYPE:
            transition.source_key = target_key
            transition.source_slot = target_slot
            transition.controls_follow_source = self._slot_follows_regular_playback_controls(target_slot)
            transition.pending_target_key = None
            self._track_end_transition_state = transition
            return None
        has_pending_transition = bool(self._pending_player_media_loads) or self._pending_deferred_audio_request is not None
        if self.current_playing is None and has_pending_transition:
            transition.pending_target_key = target_key
            self._track_end_transition_state = transition
        else:
            self._clear_track_end_transition_state()
        return True

    def _handle_track_end_transition(self, transition: _TrackEndTransitionState) -> bool:
        self._track_end_transition_state = transition
        if transition.should_loop:
            if self._apply_track_end_source_view(transition) and transition.source_key is not None:
                if self._track_end_transition_started(transition, int(transition.source_key[2])):
                    return True
            self._clear_track_end_transition_state()
            return False
        if self._pending_start_request is not None:
            self._clear_track_end_transition_state()
            self.current_playing = None
            self._last_ui_position_ms = -1
            self.elapsed_time.setText("00:00:00")
            self.remaining_time.setText("00:00:00")
            self._set_progress_display(0)
            self.seek_slider.setValue(0)
            self._update_now_playing_label("")
            self._refresh_sound_grid()
            return True
        if transition.playlist_enabled and transition.source_key is not None:
            if transition.manual_stop:
                self._finalize_primary_stop_after_transition()
                return True
            source_group, source_page, _source_slot = transition.source_key
            self._apply_track_end_source_view(transition)
            blocked: set[int] = set()
            executed_automation = False
            while True:
                next_slot = self._next_playlist_slot(
                    for_auto_advance=True,
                    blocked=blocked,
                    group_key=source_group,
                    page_index=int(source_page),
                    current_track=transition.source_key,
                )
                if next_slot is None:
                    break
                started = self._track_end_transition_started(transition, next_slot)
                if started is True:
                    return True
                if started is None:
                    executed_automation = True
                    continue
                blocked.add(next_slot)
                if self.candidate_error_action == "stop_playback":
                    self._clear_track_end_transition_state()
                    self._stop_playback()
                    return True
            if executed_automation:
                self._finalize_primary_stop_after_transition()
                return True
        self._clear_track_end_transition_state()
        return False

    def _continue_playlist_after_automation_trigger(self, source_key: Optional[Tuple[str, int, int]]) -> bool:
        if source_key is None:
            return False
        source_group, source_page, _source_slot = source_key
        if source_group == "Q":
            return False
        if not (0 <= int(source_page) < PAGE_COUNT):
            return False
        if not bool(self.page_playlist_enabled[source_group][int(source_page)]):
            return False
        # Manual automation clicks must not interrupt an already-running audio path.
        if self._all_active_players() or self._pending_deferred_audio_request is not None or self._pending_player_media_loads:
            return False
        blocked: set[int] = set()
        while True:
            next_slot = self._next_playlist_slot(
                for_auto_advance=True,
                blocked=blocked,
                group_key=source_group,
                page_index=int(source_page),
                current_track=source_key,
            )
            if next_slot is None:
                return False
            if self._play_slot_via_control_flow(next_slot):
                return True
            blocked.add(next_slot)
            if self.candidate_error_action == "stop_playback":
                return False

    def _init_audio_players(self) -> None:
        self.player = self._audio_service.create_player(self)
        self.player_b = self._audio_service.create_player(self)
        self._audio_service.set_multi_play_enabled(False)
        self.player.setNotifyInterval(90)
        self.player_b.setNotifyInterval(90)
        self._player_mix_volume_map[id(self.player)] = self.player.volume()
        self._player_mix_volume_map[id(self.player_b)] = self.player_b.volume()
        self._main_waveform_poll_timer = QTimer(self)
        self._main_waveform_poll_timer.setInterval(50)
        self._main_waveform_poll_timer.timeout.connect(self._poll_main_waveform_refresh)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)
        self.player.mediaLoadFinished.connect(self._on_player_media_load_finished)
        self.player_b.positionChanged.connect(self._on_secondary_position_changed)
        self.player_b.mediaLoadFinished.connect(self._on_player_media_load_finished)

    def _dispose_audio_players(self) -> None:
        self._cancel_all_pending_player_media_loads()
        self._clear_all_vocal_shadow_players()
        for name in ["player", "player_b"]:
            player = getattr(self, name, None)
            if player is None:
                continue
            try:
                player.stop()
            except Exception:
                pass
            try:
                player.deleteLater()
            except Exception:
                pass
            setattr(self, name, None)

    def _init_silent_audio_players(self) -> None:
        self.player = NoAudioPlayer(self)
        self.player_b = NoAudioPlayer(self)
        self._player_mix_volume_map[id(self.player)] = 100
        self._player_mix_volume_map[id(self.player_b)] = 100
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)

    def _disconnect_audio_players_for_shutdown(self) -> None:
        for signal, handler in [
            (getattr(getattr(self, "player", None), "positionChanged", None), self._on_position_changed),
            (getattr(getattr(self, "player", None), "durationChanged", None), self._on_duration_changed),
            (getattr(getattr(self, "player", None), "stateChanged", None), self._on_state_changed),
            (getattr(getattr(self, "player", None), "mediaLoadFinished", None), self._on_player_media_load_finished),
            (getattr(getattr(self, "player_b", None), "positionChanged", None), self._on_secondary_position_changed),
            (getattr(getattr(self, "player_b", None), "durationChanged", None), self._on_duration_changed),
            (getattr(getattr(self, "player_b", None), "stateChanged", None), self._on_state_changed),
            (getattr(getattr(self, "player_b", None), "mediaLoadFinished", None), self._on_player_media_load_finished),
        ]:
            if signal is None:
                continue
            try:
                signal.disconnect(handler)
            except Exception:
                pass
        for player in [getattr(self, "player", None), getattr(self, "player_b", None), *list(getattr(self, "_multi_players", []))]:
            if player is None:
                continue
            try:
                player.blockSignals(True)
            except Exception:
                pass
        for shadow in list(getattr(self, "_vocal_shadow_players", {}).values()):
            try:
                shadow.mediaLoadFinished.disconnect(self._on_vocal_shadow_media_load_finished)
            except Exception:
                pass
            try:
                shadow.blockSignals(True)
            except Exception:
                pass

    def _recover_from_stuck_mouse_state(self) -> None:
        # Defensive UI recovery for platform-specific pointer grab issues after
        # closing context-launched modal dialogs.
        try:
            grabber = QWidget.mouseGrabber()
            if grabber is not None:
                grabber.releaseMouse()
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            try:
                popup = app.activePopupWidget()
                if popup is not None:
                    popup.close()
            except Exception:
                pass
        for btn in self.control_buttons.values():
            btn.setDown(False)
        for btn in self.group_buttons.values():
            btn.setDown(False)
        for btn in self.sound_buttons:
            btn.setDown(False)

    def _play_slot(
        self,
        slot_index: int,
        allow_fade: bool = True,
        prefer_immediate_load: bool = False,
        continue_playlist_after_automation: bool = True,
        trigger_source: str = "sound_button",
    ) -> bool:
        click_t = time.perf_counter()
        if self._is_button_drag_enabled():
            self.statusBar().showMessage(tr("Playback is not allowed while Button Drag is enabled."), 2500)
            return False
        page = self._current_page_slots()
        slot = page[slot_index]
        if slot.locked:
            return False
        if slot.marker:
            return False
        if not slot.assigned:
            return False
        if slot.source_type == AUTOMATION_SOURCE_TYPE:
            return self._trigger_automation_slot_non_audio(
                slot_index,
                auto_release=(self._automation_button_auto_release_mode() == "immediate"),
                continue_playlist_after_automation=continue_playlist_after_automation,
            )
        if slot.missing:
            self._refresh_sound_grid()
            return False

        group_key = self._view_group_key()
        playing_key = (group_key, self.current_page, slot_index)
        self._trigger_sound_button_trigger_event(playing_key)
        print(
            f"[TCDBG] {click_t:.6f} play_click key={playing_key} title={(slot.title or '<untitled>')} "
            f"mode={self._current_fade_mode()} multi={self._is_multi_play_enabled()}"
        )
        self._prune_multi_players()
        force_single_play = False
        if (not self._is_multi_play_enabled()) and self._multi_players:
            # Multi-Play was previously active; a normal click should collapse playback
            # to the selected track only.
            force_single_play = True
            for extra in list(self._multi_players):
                self._stop_single_player(extra)
            self._prune_multi_players()
        if self._is_multi_play_enabled() and playing_key in self._active_playing_keys:
            self._stop_track_by_slot_key(playing_key)
            return False
        playlist_enabled_here = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if self._is_multi_play_enabled() and (not playlist_enabled_here) and self._all_active_players():
            return self._play_slot_multi(slot, playing_key)
        if self.current_playing == playing_key and self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            if self.click_playing_action == "stop_it" and not force_single_play:
                self._stop_playback()
                return False
        # Invalidate any previously scheduled delayed start to avoid stale restarts.
        self._pending_start_request = None
        self._pending_start_token += 1
        self._clear_pending_deferred_audio_start()
        self._clear_pending_video_synced_start()
        old_player, new_player = self._select_transition_players()
        any_playing = old_player is not None
        mode = self._current_fade_mode()
        if not allow_fade:
            mode = "none"
        if self._is_multi_play_enabled():
            if mode == "cross_fade":
                mode = "none"
            elif mode == "fade_out_then_fade_in":
                mode = "fade_in_only"
        fade_in_on = mode in {"fade_in_only", "fade_out_then_fade_in"}
        fade_out_on = mode in {"fade_out_only", "fade_out_then_fade_in"}
        cross_mode = mode == "cross_fade"
        if any_playing:
            self._emit_interruption_events_for_active_players(trigger_source)
        start_video_switch_blank = getattr(self, "_start_video_switch_blank", None)
        clear_video_switch_blank = getattr(self, "_clear_video_switch_blank", None)
        current_slot = self._slot_for_key(self.current_playing) if self.current_playing is not None else None
        slot_has_video = bool(getattr(self, "_slot_has_video_media", lambda _slot: False)(slot))
        current_has_video = bool(getattr(self, "_slot_has_video_media", lambda _slot: False)(current_slot))
        if callable(start_video_switch_blank) and any_playing and slot_has_video and current_has_video and self.current_playing != playing_key:
            try:
                start_video_switch_blank(str(slot.file_path or "").strip())
            except Exception:
                pass
        elif callable(clear_video_switch_blank):
            try:
                clear_video_switch_blank()
            except Exception:
                pass
        if (
            any_playing
            and fade_out_on
            and not cross_mode
        ):
            print(f"[TCDBG] {time.perf_counter():.6f} delayed_start_due_to_fadeout key={playing_key}")
            self._schedule_start_after_fadeout(group_key, self.current_page, slot_index)
            return True

        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if playlist_enabled and self.current_playlist_start is None and self._slot_follows_regular_playback_controls(slot):
            self.current_playlist_start = slot_index
        slot.played = True
        slot.activity_code = "2"
        self._set_dirty(True)

        self.current_playing = playing_key
        self._cancel_main_waveform_refresh()
        self._main_progress_waveform = []
        self.progress_label.set_waveform([])
        self._manual_stop_requested = False
        self._cancel_fade_for_player(self.player)
        self._cancel_fade_for_player(self.player_b)
        slot_pct = self._slot_volume_pct(slot)

        started_playback = False
        if cross_mode:
            self._stop_player_internal(new_player)
            load_t = time.perf_counter()
            load_result = self._try_load_media(
                new_player,
                slot,
                playing_key=playing_key,
                allow_deferred=(not prefer_immediate_load),
                on_success=lambda old=old_player, new=new_player, s=slot, key=playing_key, pct=slot_pct: self._finish_cross_loaded_playback(
                    old, new, s, key, pct
                ),
            )
            if load_result is None:
                self._refresh_sound_grid()
                return True
            if not load_result:
                print(
                    f"[TCDBG] {time.perf_counter():.6f} media_load_failed cross "
                    f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
                )
                if callable(clear_video_switch_blank):
                    try:
                        clear_video_switch_blank()
                    except Exception:
                        pass
                self.current_playing = None
                self._refresh_sound_grid()
                self._update_now_playing_label("")
                return False
            print(
                f"[TCDBG] {time.perf_counter():.6f} media_load_ok cross "
                f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
            )
            self._finish_cross_loaded_playback(old_player, new_player, slot, playing_key, slot_pct)
            return True
        else:
            self._clear_all_player_slot_keys()
            self._stop_player_internal(self.player_b)
            self._stop_player_internal(self.player)
            load_t = time.perf_counter()
            load_result = self._try_load_media(
                self.player,
                slot,
                playing_key=playing_key,
                allow_deferred=(not prefer_immediate_load),
                on_success=lambda p=self.player, s=slot, key=playing_key, pct=slot_pct, fade=fade_in_on: self._finish_primary_loaded_playback(
                    p, s, key, pct, fade
                ),
            )
            if load_result is None:
                self._refresh_sound_grid()
                return True
            if not load_result:
                print(
                    f"[TCDBG] {time.perf_counter():.6f} media_load_failed primary "
                    f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
                )
                if callable(clear_video_switch_blank):
                    try:
                        clear_video_switch_blank()
                    except Exception:
                        pass
                self.current_playing = None
                self._refresh_sound_grid()
                self._update_now_playing_label("")
                return False
            print(
                f"[TCDBG] {time.perf_counter():.6f} media_load_ok primary "
                f"dt_ms={(time.perf_counter() - load_t) * 1000.0:.1f} key={playing_key}"
            )
            self._finish_primary_loaded_playback(self.player, slot, playing_key, slot_pct, fade_in_on)
            return True

        if started_playback:
            self._trigger_sound_button_started_event(playing_key, include_advanced=True)
            self._timecode_on_playback_start(slot)
            self._prepare_transport_for_new_playback()

        self._refresh_sound_grid()
        self._update_now_playing_label(self._build_now_playing_text(slot))
        self._append_play_log(slot.file_path)
        return True

    def _prepare_transport_for_new_playback(self) -> None:
        invalidate_video = getattr(self, "_invalidate_video_playback_sync", None)
        if callable(invalidate_video):
            invalidate_video(refresh=False)
        self._auto_transition_track = self.current_playing
        self._auto_transition_done = False
        self._auto_end_fade_track = self.current_playing
        self._auto_end_fade_done = False
        self._track_started_at = time.monotonic()
        # Clear stale UI timing without wiping duration loaded by setMedia().
        self._last_ui_position_ms = -1
        display_pos = self._transport_display_ms_for_absolute(0)
        total_ms = self._transport_total_ms()
        self.seek_slider.setValue(display_pos)
        self.total_time.setText(self._transport_total_label_text(total_ms))
        self.elapsed_time.setText(format_clock_time(display_pos))
        self.remaining_time.setText(self._transport_remaining_label_text(max(0, total_ms - display_pos)))
        self._refresh_main_jog_meta(display_pos, total_ms)
        if self.main_progress_display_mode == "waveform":
            self._schedule_main_waveform_refresh(0)

    def _play_slot_multi(self, slot: SoundButtonData, playing_key: Tuple[str, int, int]) -> bool:
        if not self._enforce_multi_play_limit():
            return False
        extra_player = self._audio_service.create_player(self)
        extra_player.setNotifyInterval(90)
        extra_player.setDSPConfig(self._dsp_config)
        extra_player.positionChanged.connect(lambda _pos, p=extra_player: self._process_automation_script_player(p))
        extra_player.mediaLoadFinished.connect(self._on_player_media_load_finished)
        slot_pct = self._slot_volume_pct(slot)
        finish_multi = lambda p=extra_player, s=slot, key=playing_key, pct=slot_pct: self._finish_multi_loaded_playback(
            p, s, key, pct
        )
        try:
            load_result = self._try_load_media(
                extra_player,
                slot,
                playing_key=playing_key,
                allow_deferred=False,
                on_success=finish_multi,
            )
            if load_result is None:
                return True
            if not load_result:
                extra_player.deleteLater()
                return False
            finish_multi()
        except Exception:
            try:
                extra_player.deleteLater()
            except Exception:
                pass
            return False
        return True

    def _try_load_media(
        self,
        player: ExternalMediaPlayer,
        slot: SoundButtonData,
        *,
        playing_key: Optional[Tuple[str, int, int]] = None,
        allow_deferred: bool = False,
        on_success: Optional[Callable[[], None]] = None,
    ) -> Optional[bool]:
        self._cancel_pending_player_media_load(player)
        source_payload = self._slot_audio_source_payload(slot)
        target_file_path = self._effective_slot_file_path(slot)
        reason = self._path_safety_reason(target_file_path) if target_file_path else None
        if reason and slot.source_type == FILE_SOURCE_TYPE:
            slot.load_failed = True
            self._stop_player_internal(player)
            title = slot.title.strip() or os.path.basename(target_file_path) or "(unknown)"
            self._show_playback_warning_banner(f"{tr('Audio Load Failed:')} Could not play '{title}'. Reason: {reason}")
            print(f"[pySSP] Unsafe audio path rejected: {target_file_path} | {reason}", flush=True)
            return False
        normalized_path = str(target_file_path or "").strip()
        can_stream_now = can_stream_without_preload(normalized_path)
        if (
            slot.source_type == FILE_SOURCE_TYPE
            and allow_deferred
            and normalized_path
            and (not is_audio_preloaded(normalized_path))
            and (not can_stream_now)
        ):
            try:
                request_audio_preload([normalized_path], prioritize=True, force=True)
            except Exception:
                pass
            if not is_audio_preloaded(normalized_path):
                slot.load_failed = False
                self._hide_playback_warning_banner()
                if playing_key is not None:
                    self._schedule_deferred_audio_start(playing_key, slot)
                return None
        try:
            if player is self.player:
                self._cancel_main_waveform_refresh()
                self._main_progress_waveform = []
                self.progress_label.set_waveform([])
            if isinstance(player, AudioPlayerProxy) or sys.platform == "darwin":
                request_id = player.setMediaAsync(source_payload, dsp_config=self._dsp_config)
                self._pending_player_media_loads[id(player)] = {
                    "request_id": int(request_id),
                    "player": player,
                    "slot": slot,
                    "playing_key": playing_key,
                    "on_success": on_success,
                }
                self._schedule_player_media_load_status(player, slot)
                return None
            player.setMedia(source_payload, dsp_config=self._dsp_config)
            slot.load_failed = False
            self._hide_playback_warning_banner()
            return True
        except Exception as exc:
            slot.load_failed = True
            self._stop_player_internal(player)
            title = slot.title.strip() or os.path.basename(target_file_path) or "(unknown)"
            self._show_playback_warning_banner(f"{tr('Audio Load Failed:')} Could not play '{title}'. Reason: {exc}")
            print(f"[pySSP] Audio load failed: {target_file_path} | {exc}", flush=True)
            return False

    def _schedule_player_media_load_status(self, player: ExternalMediaPlayer, slot: SoundButtonData) -> None:
        path = self._effective_slot_file_path(slot)
        name = self._slot_display_name(slot) or os.path.basename(path) or "(unknown)"
        self.statusBar().showMessage(f"{tr('Reading audio file...')} {name}")
        if player is self.player:
            self._set_now_playing_loading(name, 0)
            self._refresh_stage_display()

    def _cancel_pending_player_media_load(self, player: Optional[ExternalMediaPlayer]) -> None:
        if player is None:
            return
        pending = self._pending_player_media_loads.pop(id(player), None)
        if pending is None:
            return
        if player is self.player:
            self.statusBar().clearMessage()

    def _cancel_all_pending_player_media_loads(self) -> None:
        pending_players = [item.get("player") for item in self._pending_player_media_loads.values()]
        self._pending_player_media_loads.clear()
        self.statusBar().clearMessage()
        for player in pending_players:
            if not self._is_audio_player(player):
                continue
            try:
                player.stop()
            except Exception:
                pass
            if player not in {self.player, self.player_b}:
                try:
                    player.deleteLater()
                except Exception:
                    pass

    def _clear_pending_video_synced_start(self) -> None:
        self._pending_video_synced_start_token += 1
        self._pending_video_synced_start = None
        clear_hold = getattr(self, "_clear_video_prestart_hold", None)
        if callable(clear_hold):
            try:
                clear_hold()
            except Exception:
                pass

    def _arm_video_synced_start(
        self,
        slot: SoundButtonData,
        playing_key: Tuple[str, int, int],
        start_callback: Callable[[], None],
    ) -> bool:
        has_video = bool(getattr(self, "_slot_has_video_media", lambda _slot: False)(slot))
        if not has_video:
            return False
        path = str(slot.file_path or "").strip()
        if not path:
            return False
        begin_hold = getattr(self, "_begin_video_prestart_hold", None)
        if not callable(begin_hold):
            return False
        self._pending_video_synced_start_token += 1
        token = int(self._pending_video_synced_start_token)
        normalized_path = str(getattr(self, "_normalized_media_probe_key", lambda value: value)(path) or "").strip()
        self.current_playing = playing_key
        self._pending_video_synced_start = {
            "token": token,
            "path_key": normalized_path,
            "callback": start_callback,
            "playing_key": playing_key,
            "armed_at": time.monotonic(),
        }
        try:
            begin_hold(path)
        except Exception:
            self._pending_video_synced_start = None
            return False
        QTimer.singleShot(500, lambda t=token: self._force_pending_video_synced_start(t))
        return True

    def _complete_pending_video_synced_start(self, path_key: str) -> None:
        pending = getattr(self, "_pending_video_synced_start", None)
        if not isinstance(pending, dict):
            return
        expected_path = str(pending.get("path_key", "") or "").strip()
        if expected_path and str(path_key or "").strip() != expected_path:
            return
        callback = pending.get("callback")
        token = int(pending.get("token", 0) or 0)
        if token != int(getattr(self, "_pending_video_synced_start_token", 0) or 0):
            return
        self._pending_video_synced_start = None
        if callable(callback):
            callback()
        clear_hold = getattr(self, "_clear_video_prestart_hold", None)
        if callable(clear_hold):
            try:
                clear_hold()
            except Exception:
                pass

    def _force_pending_video_synced_start(self, token: int) -> None:
        pending = getattr(self, "_pending_video_synced_start", None)
        if not isinstance(pending, dict):
            return
        if int(pending.get("token", 0) or 0) != int(token):
            return
        path_key = str(pending.get("path_key", "") or "").strip()
        self._complete_pending_video_synced_start(path_key)

    def _start_primary_loaded_playback(
        self,
        player: ExternalMediaPlayer,
        slot: SoundButtonData,
        playing_key: Tuple[str, int, int],
        target_volume: int,
        fade_in_on: bool,
    ) -> None:
        if fade_in_on:
            self._set_player_volume(player, 0)
            player.play()
            self._sync_shadow_transport_from_primary(player)
            self._set_player_slot_key(player, playing_key)
            self._mark_player_started(player)
            self._start_fade(
                player,
                target_volume,
                self.fade_in_sec,
                stop_on_complete=False,
                automation_slot_key=playing_key,
                automation_start_events=("on_fade_in_start",),
                automation_end_events=("on_fade_in_end",),
            )
        else:
            self._set_player_volume(player, target_volume)
            player.play()
            self._sync_shadow_transport_from_primary(player)
            self._set_player_slot_key(player, playing_key)
            self._mark_player_started(player)
        self.current_playing = playing_key
        self._timecode_on_playback_start(slot)
        self._trigger_sound_button_started_event(playing_key, include_advanced=True)
        self._prepare_transport_for_new_playback()
        self._refresh_sound_grid()
        self._update_now_playing_label(self._build_now_playing_text(slot))
        self._append_play_log(slot.file_path)

    def _start_cross_loaded_playback(
        self,
        old_player: Optional[ExternalMediaPlayer],
        new_player: ExternalMediaPlayer,
        slot: SoundButtonData,
        playing_key: Tuple[str, int, int],
        target_volume: int,
    ) -> None:
        self._set_player_volume(new_player, 0)
        new_player.play()
        self._sync_shadow_transport_from_primary(new_player)
        self._set_player_slot_key(new_player, playing_key)
        self._mark_player_started(new_player)
        fade_seconds = self.cross_fade_sec
        self._start_fade(
            new_player,
            target_volume,
            fade_seconds,
            stop_on_complete=False,
            automation_slot_key=playing_key,
            automation_start_events=("on_fade_in_start",),
            automation_end_events=("on_fade_in_end",),
        )
        if old_player is not None:
            self._start_fade(old_player, 0, fade_seconds, stop_on_complete=True)
        if self.player is not new_player:
            self._swap_primary_secondary_players()
        self.current_playing = playing_key
        self._timecode_on_playback_start(slot)
        self._trigger_sound_button_started_event(playing_key, include_advanced=True)
        self._prepare_transport_for_new_playback()
        self._refresh_sound_grid()
        self._update_now_playing_label(self._build_now_playing_text(slot))
        self._append_play_log(slot.file_path)

    def _start_multi_loaded_playback(
        self,
        player: ExternalMediaPlayer,
        slot: SoundButtonData,
        playing_key: Tuple[str, int, int],
        target_volume: int,
        fade_in_on: bool,
    ) -> None:
        if fade_in_on and self.fade_in_sec > 0:
            self._set_player_volume(player, 0)
        else:
            self._set_player_volume(player, target_volume)
        player.play()
        self._sync_shadow_transport_from_primary(player)
        if fade_in_on and self.fade_in_sec > 0:
            self._start_fade(
                player,
                target_volume,
                self.fade_in_sec,
                stop_on_complete=False,
                automation_slot_key=playing_key,
                automation_start_events=("on_fade_in_start",),
                automation_end_events=("on_fade_in_end",),
            )
        if player not in self._multi_players:
            self._multi_players.append(player)
        self._set_player_slot_key(player, playing_key)
        self._mark_player_started(player)
        slot.played = True
        slot.activity_code = "2"
        self._set_dirty(True)
        self.current_playing = playing_key
        self._trigger_sound_button_started_event(playing_key, include_advanced=True)
        self._prepare_transport_for_new_playback()
        self._refresh_sound_grid()
        self._update_now_playing_label(self._build_now_playing_text(slot))
        self._append_play_log(slot.file_path)

    def _finish_primary_loaded_playback(
        self,
        player: ExternalMediaPlayer,
        slot: SoundButtonData,
        playing_key: Tuple[str, int, int],
        slot_pct: int,
        fade_in_on: bool,
    ) -> None:
        self.current_playing = playing_key
        self._clear_track_end_transition_state()
        self._player_slot_volume_pct = slot_pct
        resolved_duration = max(0, int(player.duration()))
        if resolved_duration > 0:
            self.current_duration_ms = resolved_duration
            slot.duration_ms = resolved_duration
        target_volume = self._effective_slot_target_volume(slot_pct)
        self._seek_player_to_slot_start_cue(player, slot)
        self._prepare_vocal_shadow_player(player, slot, start_playing=False)
        start_callback = lambda p=player, s=slot, key=playing_key, target=target_volume, fade=fade_in_on: self._start_primary_loaded_playback(
            p, s, key, target, fade
        )
        if self._arm_video_synced_start(slot, playing_key, start_callback):
            self._refresh_sound_grid()
            self._update_now_playing_label(self._build_now_playing_text(slot))
            return
        start_callback()

    def _finish_cross_loaded_playback(
        self,
        old_player: Optional[ExternalMediaPlayer],
        new_player: ExternalMediaPlayer,
        slot: SoundButtonData,
        playing_key: Tuple[str, int, int],
        slot_pct: int,
    ) -> None:
        self.current_playing = playing_key
        self._clear_track_end_transition_state()
        if new_player is self.player:
            self._player_slot_volume_pct = slot_pct
        else:
            self._player_b_slot_volume_pct = slot_pct
        resolved_duration = max(0, int(new_player.duration()))
        if resolved_duration > 0:
            self.current_duration_ms = resolved_duration
            slot.duration_ms = resolved_duration
        target_volume = self._effective_slot_target_volume(slot_pct)
        self._seek_player_to_slot_start_cue(new_player, slot)
        self._prepare_vocal_shadow_player(new_player, slot, start_playing=False)
        start_callback = lambda old=old_player, new=new_player, s=slot, key=playing_key, target=target_volume: self._start_cross_loaded_playback(
            old, new, s, key, target
        )
        if self._arm_video_synced_start(slot, playing_key, start_callback):
            self._refresh_sound_grid()
            self._update_now_playing_label(self._build_now_playing_text(slot))
            return
        start_callback()

    def _finish_multi_loaded_playback(
        self,
        player: ExternalMediaPlayer,
        slot: SoundButtonData,
        playing_key: Tuple[str, int, int],
        slot_pct: int,
    ) -> None:
        self._set_player_slot_pct(player, slot_pct)
        self._clear_track_end_transition_state()
        resolved_duration = max(0, int(player.duration()))
        if resolved_duration > 0:
            self.current_duration_ms = resolved_duration
            slot.duration_ms = resolved_duration
        target_volume = self._effective_slot_target_volume(slot_pct)
        self._seek_player_to_slot_start_cue(player, slot)
        self._prepare_vocal_shadow_player(player, slot, start_playing=False)
        fade_in_on = self._is_fade_in_enabled()
        start_callback = lambda p=player, s=slot, key=playing_key, target=target_volume, fade=fade_in_on: self._start_multi_loaded_playback(
            p, s, key, target, fade
        )
        if self._arm_video_synced_start(slot, playing_key, start_callback):
            self._refresh_sound_grid()
            self._update_now_playing_label(self._build_now_playing_text(slot))
            return
        start_callback()

    def _on_player_media_load_finished(self, request_id: int, ok: bool, error: str) -> None:
        if bool(getattr(self, "_shutdown_in_progress", False)):
            return
        player = self.sender()
        if not self._is_audio_player(player):
            return
        pending = self._pending_player_media_loads.get(id(player))
        if pending is None or int(pending.get("request_id", -1)) != int(request_id):
            return
        self._pending_player_media_loads.pop(id(player), None)
        slot = pending.get("slot")
        if not isinstance(slot, SoundButtonData):
            return
        if player is self.player:
            self.statusBar().clearMessage()
        if not ok:
            self._clear_track_end_transition_state()
            slot.load_failed = True
            self._stop_player_internal(player)
            title = self._slot_display_name(slot) or "(unknown)"
            self._show_playback_warning_banner(f"{tr('Audio Load Failed:')} Could not play '{title}'. Reason: {error}")
            print(f"[pySSP] Audio load failed: {self._effective_slot_file_path(slot)} | {error}", flush=True)
            if player is self.player:
                self.current_playing = None
                self._update_now_playing_label("")
            elif player is not self.player_b:
                try:
                    player.deleteLater()
                except Exception:
                    pass
            self._refresh_sound_grid()
            return
        slot.load_failed = False
        self._hide_playback_warning_banner()
        on_success = pending.get("on_success")
        if callable(on_success):
            try:
                on_success()
            except Exception as exc:
                slot.load_failed = True
                self._stop_player_internal(player)
                title = self._slot_display_name(slot) or "(unknown)"
                self._show_playback_warning_banner(f"{tr('Audio Load Failed:')} Could not play '{title}'. Reason: {exc}")
                print(f"[pySSP] Audio start failed after async load: {self._effective_slot_file_path(slot)} | {exc}", flush=True)
                if player is not self.player and player is not self.player_b:
                    try:
                        player.deleteLater()
                    except Exception:
                        pass
                self._refresh_sound_grid()

    def _select_transition_players(self) -> Tuple[Optional[ExternalMediaPlayer], ExternalMediaPlayer]:
        def is_active(player: ExternalMediaPlayer) -> bool:
            return player.state() in {
                ExternalMediaPlayer.PlayingState,
                ExternalMediaPlayer.PausedState,
            }

        def score(player: ExternalMediaPlayer) -> Tuple[int, int]:
            # Prefer actively playing channel, then louder channel.
            is_playing = 1 if player.state() == ExternalMediaPlayer.PlayingState else 0
            return (is_playing, self._logical_player_volume(player))

        a_active = is_active(self.player)
        b_active = is_active(self.player_b)

        if a_active and b_active:
            # Fade out the dominant (audible) player; reuse the other as fade-in target.
            if score(self.player) >= score(self.player_b):
                return self.player, self.player_b
            return self.player_b, self.player
        if a_active:
            return self.player, self.player_b
        if b_active:
            return self.player_b, self.player
        return None, self.player

    def _schedule_start_after_fadeout(self, group_key: str, page_index: int, slot_index: int) -> None:
        self._pending_start_request = (group_key, page_index, slot_index)
        self._pending_start_token += 1
        token = self._pending_start_token
        fade_ms = max(1, int(self.fade_out_sec * 1000))
        self._start_fade(self.player, 0, self.fade_out_sec, stop_on_complete=True)
        if self.player_b.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
            self._start_fade(self.player_b, 0, self.fade_out_sec, stop_on_complete=True)
        QTimer.singleShot(fade_ms + 30, lambda t=token: self._run_pending_start(t))

    def _run_pending_start(self, token: int) -> None:
        if token != self._pending_start_token:
            return
        request = self._pending_start_request
        if request is None:
            return
        self._pending_start_request = None
        group_key, page_index, slot_index = request
        if group_key == "Q":
            self.cue_mode = True
        else:
            self.cue_mode = False
            self.current_group = group_key
        self.current_page = max(0, min(PAGE_COUNT - 1, page_index))
        self._refresh_group_buttons()
        self._sync_playlist_shuffle_buttons()
        self._apply_hotkeys()
        self._refresh_page_list()
        self._refresh_sound_grid()
        self._update_group_status()
        self._update_page_status()
        self._queue_current_page_audio_preload()
        self._play_slot(slot_index)

    def _clear_pending_deferred_audio_start(self) -> None:
        had_pending = self._pending_deferred_audio_request is not None
        self._pending_deferred_audio_token += 1
        self._pending_deferred_audio_request = None
        if had_pending:
            self.statusBar().clearMessage()

    def _schedule_deferred_audio_start(self, playing_key: Tuple[str, int, int], slot: SoundButtonData) -> None:
        path = str(slot.file_path or "").strip()
        if not path:
            return
        self._pending_deferred_audio_token += 1
        self._pending_deferred_audio_request = (
            playing_key[0],
            int(playing_key[1]),
            int(playing_key[2]),
            path,
            time.monotonic(),
        )
        name = slot.title.strip() or os.path.basename(path) or "(unknown)"
        self.statusBar().showMessage(f"{tr('Reading audio file...')} {name}")
        self._set_now_playing_loading(name, 0)
        self._refresh_stage_display()

    def _tick_deferred_audio_start(self) -> None:
        request = self._pending_deferred_audio_request
        if request is None:
            return
        group_key, page_index, slot_index, path, started_at = request
        slot = self._slot_for_key((group_key, page_index, slot_index))
        loading_name = (
            slot.title.strip()
            if (slot is not None and str(getattr(slot, "title", "")).strip())
            else (os.path.basename(path) or "(unknown)")
        )
        elapsed = max(0.0, time.monotonic() - started_at)
        dot_count = int(elapsed * 3.0) % 4
        self._set_now_playing_loading(loading_name, dot_count)
        self.statusBar().showMessage(f"{tr('Reading audio file...')} {loading_name}" + ("." * dot_count))
        if is_audio_preloaded(path):
            self._pending_deferred_audio_request = None
            self.statusBar().clearMessage()
            if group_key == "Q":
                self.cue_mode = True
            else:
                self.cue_mode = False
                self.current_group = group_key
            self.current_page = max(0, min(PAGE_COUNT - 1, page_index))
            self._refresh_group_buttons()
            self._sync_playlist_shuffle_buttons()
            self._apply_hotkeys()
            self._refresh_page_list()
            self._refresh_sound_grid()
            self._update_group_status()
            self._update_page_status()
            self._queue_current_page_audio_preload()
            self._play_slot(slot_index)
            return
        if elapsed >= 120.0:
            self._clear_track_end_transition_state()
            self._clear_pending_deferred_audio_start()
            self._show_playback_warning_banner(f"{tr('Audio Load Failed:')} {tr('Reading audio file timed out.')}")
            self._update_now_playing_label("")
            self._refresh_sound_grid()

    def _set_now_playing_loading(self, title: str, dot_count: int) -> None:
        dots = "." * max(0, int(dot_count))
        base = tr("Reading audio file...")
        loading_line = f"{base}{dots}"
        title_html = NowPlayingLabel._to_wrapped_html(str(title or "").strip() or "(unknown)")
        loading_html = NowPlayingLabel._to_wrapped_html(loading_line)
        value_html = f"<span style=\"color:#C62828; font-weight:700;\">{loading_html}</span><br/>{title_html}"
        self.now_playing_label.set_now_playing_html(tr("NOW PLAYING:"), value_html)

    def _on_position_changed(self, pos: int) -> None:
        if bool(getattr(self, "_shutdown_in_progress", False)):
            return
        self._process_automation_script_player(self.player)
        display_pos = self._transport_display_ms_for_absolute(pos)
        if not self._is_scrubbing:
            self.seek_slider.setValue(display_pos)
        # Keep transport updates smooth without redrawing excessively.
        if self._last_ui_position_ms >= 0 and abs(pos - self._last_ui_position_ms) < 25:
            return
        self._last_ui_position_ms = pos
        self.elapsed_time.setText(format_clock_time(display_pos))
        total_ms = self._transport_total_ms()
        remaining = max(0, total_ms - display_pos)
        self.remaining_time.setText(self._transport_remaining_label_text(remaining))
        progress = 0 if total_ms == 0 else int((display_pos / total_ms) * 100)
        self._refresh_main_jog_meta(display_pos, total_ms)
        self._refresh_timecode_panel()
        self._refresh_stage_display()
        refresh_video = getattr(self, "_refresh_video_display", None)
        if callable(refresh_video):
            refresh_video()

    def _on_secondary_position_changed(self, _pos: int) -> None:
        if bool(getattr(self, "_shutdown_in_progress", False)):
            return
        self._process_automation_script_player(self.player_b)

    def _on_duration_changed(self, duration: int) -> None:
        if bool(getattr(self, "_shutdown_in_progress", False)):
            return
        self.current_duration_ms = duration
        if self.main_progress_display_mode == "waveform":
            self._schedule_main_waveform_refresh(120)
        else:
            self._cancel_main_waveform_refresh()
            self._main_progress_waveform = []
            self.progress_label.set_waveform([])
        self._last_ui_position_ms = -1
        total_ms = self._transport_total_ms()
        self.seek_slider.setRange(0, total_ms)
        self.total_time.setText(self._transport_total_label_text(total_ms))
        target_key = self.current_playing if self.current_playing is not None else self._track_end_transition_target_key()
        if target_key:
            group, page_index, slot_index = target_key
            if group == "Q":
                if 0 <= slot_index < len(self.cue_page):
                    self.cue_page[slot_index].duration_ms = duration
            elif group in self.data and 0 <= page_index < PAGE_COUNT and 0 <= slot_index < len(self.data[group][page_index]):
                self.data[group][page_index][slot_index].duration_ms = duration
            self._refresh_sound_grid()
        self._refresh_timecode_panel()
        self._refresh_stage_display()
        refresh_video = getattr(self, "_refresh_video_display", None)
        if callable(refresh_video):
            refresh_video(force=True)

    def _schedule_main_waveform_refresh(self, delay_ms: int = 0) -> None:
        if self.current_playing is None:
            return
        token = self._main_waveform_request_token + 1
        self._main_waveform_request_token = token
        expected_key = self.current_playing
        QTimer.singleShot(max(0, int(delay_ms)), lambda t=token, k=expected_key: self._start_main_waveform_refresh_if_current(t, k))

    def _cancel_main_waveform_refresh(self) -> None:
        self._main_waveform_request_token += 1
        self._main_waveform_future = None
        self._main_waveform_future_token = 0
        self._main_waveform_future_key = None
        timer = getattr(self, "_main_waveform_poll_timer", None)
        if timer is not None and timer.isActive():
            timer.stop()

    def _clear_main_waveform_display(self) -> None:
        self._cancel_main_waveform_refresh()
        self._main_progress_waveform = []
        self.progress_label.set_waveform([])

    def _start_main_waveform_refresh_if_current(self, token: int, expected_key: Optional[Tuple[str, int, int]]) -> None:
        if token != self._main_waveform_request_token:
            return
        if expected_key is None or self.current_playing != expected_key:
            return
        player = self._player_for_slot_key(expected_key)
        if player is None:
            return
        try:
            self._main_waveform_future = player.waveformPeaksAsync(1800)
            self._main_waveform_future_token = token
            self._main_waveform_future_key = expected_key
        except Exception:
            self._main_waveform_future = None
            self._main_waveform_future_token = 0
            self._main_waveform_future_key = None
            self._main_progress_waveform = []
            self.progress_label.set_waveform([])
            return
        self._main_waveform_poll_timer.start()

    def _poll_main_waveform_refresh(self) -> None:
        future = self._main_waveform_future
        if future is None:
            timer = getattr(self, "_main_waveform_poll_timer", None)
            if timer is not None:
                timer.stop()
            return
        if not future.done():
            return
        token = int(self._main_waveform_future_token)
        expected_key = self._main_waveform_future_key
        self._main_waveform_future = None
        self._main_waveform_future_token = 0
        self._main_waveform_future_key = None
        if token != self._main_waveform_request_token:
            return
        if expected_key is None or self.current_playing != expected_key:
            timer = getattr(self, "_main_waveform_poll_timer", None)
            if timer is not None:
                timer.stop()
            return
        try:
            peaks = list(future.result())
        except Exception:
            peaks = []
        self._main_progress_waveform = list(peaks)
        self.progress_label.set_waveform(self._main_progress_waveform)
        if self.main_progress_display_mode != "waveform":
            timer = getattr(self, "_main_waveform_poll_timer", None)
            if timer is not None:
                timer.stop()
            return
        if self.current_playing != expected_key:
            timer = getattr(self, "_main_waveform_poll_timer", None)
            if timer is not None:
                timer.stop()
            return
        timer = getattr(self, "_main_waveform_poll_timer", None)
        if timer is not None:
            timer.stop()

    def _on_state_changed(self, _state: int) -> None:
        if bool(getattr(self, "_shutdown_in_progress", False)):
            return
        print(
            f"[TCDBG] {time.perf_counter():.6f} state_changed "
            f"primary={self.player.state()} secondary={self.player_b.state()}"
        )
        self._update_pause_button_label()
        refresh_video = getattr(self, "_refresh_video_display", None)
        if self._ignore_state_changes > 0:
            if callable(refresh_video):
                refresh_video(force=True)
            return
        if self.player.state() == ExternalMediaPlayer.StoppedState:
            transition = self._capture_track_end_transition_state()
            self._timecode_on_playback_stop()
            self._clear_vocal_shadow_player(self.player)
            self._player_mix_volume_map.pop(id(self.player), None)
            if id(self.player) in self._sound_button_automation_handled_stop_player_ids:
                self._sound_button_automation_handled_stop_player_ids.discard(id(self.player))
            elif transition.source_key is not None and not transition.manual_stop:
                self._trigger_sound_button_stopped_event(transition.source_key, natural=True)
            self._clear_player_slot_key(self.player)
            self._clear_main_waveform_display()
            self._manual_stop_requested = False
            if self._handle_track_end_transition(transition):
                return
            self._clear_track_end_transition_state()
            self.current_playing = None
            self._auto_transition_track = None
            self._auto_transition_done = False
            self._last_ui_position_ms = -1
            self.elapsed_time.setText("00:00:00")
            self.remaining_time.setText("00:00:00")
            self._set_progress_display(0)
            self._refresh_sound_grid()
            self.seek_slider.setValue(0)
            self._update_now_playing_label("")
        self._refresh_timecode_panel()
        self._refresh_stage_display()
        self._refresh_lyric_display()
        if callable(refresh_video):
            refresh_video(force=True)

    def _stop_player_internal(self, player: ExternalMediaPlayer) -> None:
        self._clear_pending_video_synced_start()
        self._cancel_pending_player_media_load(player)
        self._ignore_state_changes += 1
        try:
            player.stop()
            shadow = self._shadow_player_for(player)
            if shadow is not None:
                shadow.stop()
        finally:
            self._ignore_state_changes = max(0, self._ignore_state_changes - 1)

    def _tick_preload_status_icon(self) -> None:
        enabled, active_jobs = get_audio_preload_runtime_status()
        self._refresh_current_page_ram_loaded_indicators()
        if (not enabled) or active_jobs <= 0:
            self._preload_icon_blink_on = False
            self.preload_status_icon.setStyleSheet(
                "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#C8CDD4;border:1px solid #8C939D;border-radius:8px;}"
            )
            self.preload_status_icon.setToolTip("RAM preload idle")
            return
        self._preload_icon_blink_on = not self._preload_icon_blink_on
        if self._preload_icon_blink_on:
            self.preload_status_icon.setStyleSheet(
                "QLabel{font-size:9pt;font-weight:bold;color:#0B4A1F;background:#5FE088;border:1px solid #219653;border-radius:8px;}"
            )
        else:
            self.preload_status_icon.setStyleSheet(
                "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#C8CDD4;border:1px solid #8C939D;border-radius:8px;}"
            )
        self.preload_status_icon.setToolTip(f"RAM preload active ({active_jobs})")

    def _tick_meter(self) -> None:
        self._tick_deferred_audio_start()
        self._prune_multi_players()
        self._maintain_vocal_shadow_sync()
        self._enforce_cue_end_limits()
        if self.player_b.state() == ExternalMediaPlayer.StoppedState:
            had_player_b_key = id(self.player_b) in self._player_slot_key_map
            if had_player_b_key:
                if id(self.player_b) in self._sound_button_automation_handled_stop_player_ids:
                    self._sound_button_automation_handled_stop_player_ids.discard(id(self.player_b))
                else:
                    self._trigger_sound_button_stopped_event(
                        self._player_slot_key_map.get(id(self.player_b)),
                        natural=True,
                    )
            self._clear_vocal_shadow_player(self.player_b)
            self._player_mix_volume_map.pop(id(self.player_b), None)
            self._clear_player_slot_key(self.player_b)
            if had_player_b_key:
                self._refresh_sound_grid()
        self._try_auto_fade_transition()
        self._update_next_button_enabled()
        if self._flash_slot_key and time.monotonic() >= self._flash_slot_until:
            self._flash_slot_key = None
            self._flash_slot_until = 0.0
            self._refresh_sound_grid()
        any_playing = (
            self.player.state() == ExternalMediaPlayer.PlayingState
            or self.player_b.state() == ExternalMediaPlayer.PlayingState
        )
        for extra in self._multi_players:
            if extra.state() == ExternalMediaPlayer.PlayingState:
                any_playing = True
        target_left, target_right = get_engine_output_meter_levels(getattr(self, "meter_output_tap_mode", "post_fader"))
        target_left = min(1.0, max(0.0, float(target_left)))
        target_right = min(1.0, max(0.0, float(target_right)))
        attack = 0.92
        release = 0.68 if any_playing else 0.45
        if target_left >= self._vu_levels[0]:
            self._vu_levels[0] += (target_left - self._vu_levels[0]) * attack
        else:
            self._vu_levels[0] += (target_left - self._vu_levels[0]) * release
        if target_right >= self._vu_levels[1]:
            self._vu_levels[1] += (target_right - self._vu_levels[1]) * attack
        else:
            self._vu_levels[1] += (target_right - self._vu_levels[1]) * release
        self._sync_preload_pause_state(any_playing)
        self.left_meter.setLevel(self._vu_levels[0])
        self.right_meter.setLevel(self._vu_levels[1])
        now = time.monotonic()
        if (now - self._last_meter_aux_refresh_t) >= 0.18:
            self._last_meter_aux_refresh_t = now
            self._refresh_timecode_panel()
            self._refresh_stage_display()
            self._refresh_lyric_display()

    def _update_group_status(self) -> None:
        self.group_status.setText("")
        self._update_page_status()

    def _update_page_status(self) -> None:
        if self.cue_mode:
            self.page_status.setText("Current Page: Cue")
            return
        group = str(self.current_group or "").strip().upper()
        index = self.current_page + 1
        page_name = self.page_names[self.current_group][self.current_page].strip()
        if page_name:
            self.page_status.setText(f"Current Page: {group} - [{index}]{page_name}")
        else:
            self.page_status.setText(f"Current Page: {group} - [{index}]")

    def _actual_slot_file_path(self, slot: SoundButtonData) -> str:
        return str(slot.file_path or "").strip()

    def _vocal_removed_slot_file_path(self, slot: SoundButtonData) -> str:
        path = str(slot.vocal_removed_file or "").strip()
        if path and os.path.exists(path):
            return path
        return ""

    def _effective_slot_file_path(self, slot: SoundButtonData) -> str:
        return self._actual_slot_file_path(slot)

    def _logical_player_volume(self, player: ExternalMediaPlayer) -> int:
        return max(0, min(100, int(self._player_mix_volume_map.get(id(player), player.volume()))))

    def _shadow_player_for(self, player: Optional[ExternalMediaPlayer]) -> Optional[ExternalMediaPlayer]:
        if player is None:
            return None
        return self._vocal_shadow_players.get(id(player))

    def _create_vocal_shadow_player(self) -> ExternalMediaPlayer:
        shadow = self._audio_service.create_player(self)
        shadow.setNotifyInterval(90)
        shadow.setDSPConfig(self._dsp_config)
        shadow.setVolume(0)
        self._set_player_master_volume(shadow, self._effective_master_volume())
        shadow.mediaLoadFinished.connect(self._on_vocal_shadow_media_load_finished)
        return shadow

    def _clear_vocal_shadow_player(self, player: Optional[ExternalMediaPlayer]) -> None:
        if player is None:
            return
        self._cancel_vocal_toggle_fade_for_player(player)
        shadow = self._vocal_shadow_players.pop(id(player), None)
        if shadow is None:
            return
        self._vocal_shadow_pending_loads.pop(id(shadow), None)
        try:
            shadow.stop()
        except Exception:
            pass
        self._player_mix_volume_map.pop(id(shadow), None)
        try:
            shadow.deleteLater()
        except Exception:
            pass

    def _clear_all_vocal_shadow_players(self) -> None:
        for player_id in list(self._vocal_shadow_players.keys()):
            shadow = self._vocal_shadow_players.pop(player_id, None)
            if shadow is None:
                continue
            self._vocal_shadow_pending_loads.pop(id(shadow), None)
            try:
                shadow.stop()
            except Exception:
                pass
            self._player_mix_volume_map.pop(id(shadow), None)
            try:
                shadow.deleteLater()
            except Exception:
                pass
        self._vocal_shadow_pending_loads.clear()

    def _apply_player_mix_volumes(self, player: Optional[ExternalMediaPlayer], logical_volume: Optional[int] = None) -> None:
        if player is None:
            return
        if id(player) in self._vocal_toggle_fade_jobs and logical_volume is None:
            return
        if logical_volume is None:
            logical = self._logical_player_volume(player)
        else:
            logical = max(0, min(100, int(logical_volume)))
            self._player_mix_volume_map[id(player)] = logical
        shadow = self._shadow_player_for(player)
        primary_volume = logical
        shadow_volume = 0
        shadow_ready = shadow is not None and id(shadow) not in self._vocal_shadow_pending_loads
        if self.play_vocal_removed_tracks and shadow_ready:
            primary_volume = 0
            shadow_volume = logical
        player.setVolume(primary_volume)
        self._set_player_master_volume(player, self._effective_master_volume())
        if shadow is not None:
            shadow.setVolume(shadow_volume)
            self._set_player_master_volume(shadow, self._effective_master_volume())

    def _cancel_vocal_toggle_fade_for_player(self, player: Optional[ExternalMediaPlayer]) -> None:
        if player is None:
            return
        self._vocal_toggle_fade_jobs.pop(id(player), None)

    def _start_vocal_toggle_fade(
        self,
        player: ExternalMediaPlayer,
        shadow: ExternalMediaPlayer,
        *,
        target_primary: int,
        target_shadow: int,
        seconds: float,
    ) -> None:
        self._cancel_vocal_toggle_fade_for_player(player)
        if seconds <= 0:
            player.setVolume(max(0, min(100, int(target_primary))))
            shadow.setVolume(max(0, min(100, int(target_shadow))))
            return
        self._vocal_toggle_fade_jobs[id(player)] = {
            "player": player,
            "shadow": shadow,
            "start_primary": max(0, min(100, int(player.volume()))),
            "start_shadow": max(0, min(100, int(shadow.volume()))),
            "end_primary": max(0, min(100, int(target_primary))),
            "end_shadow": max(0, min(100, int(target_shadow))),
            "started": time.monotonic(),
            "duration": max(0.01, float(seconds)),
        }

    def _vocal_removed_toggle_fade_seconds(self) -> float:
        mode = str(self.vocal_removed_toggle_fade_mode or "follow_cross_fade").strip().lower()
        if mode == "never":
            return 0.0
        if mode == "always":
            return max(0.0, float(self.vocal_removed_toggle_always_sec))
        if not self._is_cross_fade_enabled():
            return 0.0
        if mode == "follow_cross_fade_custom":
            return max(0.0, float(self.vocal_removed_toggle_custom_sec))
        return max(0.0, float(self.cross_fade_sec))

    def _apply_vocal_removed_toggle_for_player(
        self,
        player: Optional[ExternalMediaPlayer],
        *,
        current_vocal_removed_active: Optional[bool] = None,
    ) -> None:
        if player is None:
            return
        shadow = self._shadow_player_for(player)
        if shadow is None:
            self._cancel_vocal_toggle_fade_for_player(player)
            self._apply_player_mix_volumes(player)
            return
        if current_vocal_removed_active is None:
            current_vocal_removed_active = bool(self.play_vocal_removed_tracks)
        self._sync_vocal_pair_transport(
            player,
            audible_is_shadow=bool(current_vocal_removed_active),
            force_seek=True,
        )
        logical_volume = self._logical_player_volume(player)
        fade_seconds = self._vocal_removed_toggle_fade_seconds()
        if player.state() != ExternalMediaPlayer.PlayingState or fade_seconds <= 0:
            self._cancel_fade_for_player(player)
            self._cancel_fade_for_player(shadow)
            self._cancel_vocal_toggle_fade_for_player(player)
            self._apply_player_mix_volumes(player, logical_volume)
            return
        self._cancel_fade_for_player(player)
        self._cancel_fade_for_player(shadow)
        if self.play_vocal_removed_tracks:
            self._start_vocal_toggle_fade(
                player,
                shadow,
                target_primary=0,
                target_shadow=logical_volume,
                seconds=fade_seconds,
            )
            return
        self._start_vocal_toggle_fade(
            player,
            shadow,
            target_primary=logical_volume,
            target_shadow=0,
            seconds=fade_seconds,
        )

    def _player_transport_sync_ms(self, player: ExternalMediaPlayer) -> int:
        try:
            if player.state() == ExternalMediaPlayer.PlayingState:
                return max(0, int(player.enginePositionMs()))
        except Exception:
            pass
        try:
            return max(0, int(player.position()))
        except Exception:
            return 0

    def _should_sync_vocal_shadow(self, player: ExternalMediaPlayer) -> bool:
        shadow = self._shadow_player_for(player)
        if shadow is None:
            return False
        if id(player) in self._vocal_toggle_fade_jobs:
            return False
        if player.state() != ExternalMediaPlayer.PlayingState:
            return False
        if shadow.state() != ExternalMediaPlayer.PlayingState:
            return True
        player_volume = max(0, min(100, int(player.volume())))
        shadow_volume = max(0, min(100, int(shadow.volume())))
        return player_volume == 0 or shadow_volume == 0

    def _sync_vocal_pair_transport(
        self,
        player: ExternalMediaPlayer,
        *,
        audible_is_shadow: bool,
        force_seek: bool = False,
        max_drift_ms: int = 12,
    ) -> None:
        shadow = self._shadow_player_for(player)
        if shadow is None:
            return
        source = shadow if audible_is_shadow else player
        target = player if audible_is_shadow else shadow
        target_ms = self._player_transport_sync_ms(source)
        try:
            target_pos = self._player_transport_sync_ms(target)
        except Exception:
            target_pos = 0
        should_seek = force_seek or target.state() == ExternalMediaPlayer.StoppedState
        if not should_seek:
            should_seek = abs(target_ms - target_pos) > max(0, int(max_drift_ms))
        if should_seek:
            try:
                target.setPosition(target_ms)
            except Exception:
                pass
        try:
            if source.state() == ExternalMediaPlayer.PlayingState:
                target.play()
            elif source.state() == ExternalMediaPlayer.PausedState:
                target.pause()
            else:
                target.stop()
        except Exception:
            pass

    def _maintain_vocal_shadow_sync(self) -> None:
        for player in [self.player, self.player_b, *self._multi_players]:
            if not self._should_sync_vocal_shadow(player):
                continue
            self._sync_vocal_pair_transport(
                player,
                audible_is_shadow=bool(self.play_vocal_removed_tracks),
                force_seek=False,
                max_drift_ms=12,
            )

    def _sync_shadow_transport_from_primary(
        self,
        player: Optional[ExternalMediaPlayer],
        *,
        force_seek: bool = True,
        max_drift_ms: int = 45,
    ) -> None:
        if player is None:
            return
        shadow = self._shadow_player_for(player)
        if shadow is None:
            return
        target_ms = self._player_transport_sync_ms(player)
        try:
            shadow_pos = self._player_transport_sync_ms(shadow)
        except Exception:
            shadow_pos = 0
        should_seek = force_seek or shadow.state() == ExternalMediaPlayer.StoppedState
        if not should_seek:
            should_seek = abs(target_ms - shadow_pos) > max(0, int(max_drift_ms))
        if should_seek:
            try:
                shadow.setPosition(target_ms)
            except Exception:
                pass
        state = player.state()
        try:
            if state == ExternalMediaPlayer.PlayingState:
                shadow.play()
            elif state == ExternalMediaPlayer.PausedState:
                shadow.pause()
            else:
                shadow.stop()
        except Exception:
            pass
        if id(player) not in self._vocal_toggle_fade_jobs:
            self._apply_player_mix_volumes(player)

    def _prepare_vocal_shadow_player(
        self,
        player: Optional[ExternalMediaPlayer],
        slot: SoundButtonData,
        *,
        start_playing: bool,
    ) -> None:
        if player is None or not self._is_audio_player(player):
            return
        vocal_path = self._vocal_removed_slot_file_path(slot)
        actual_path = self._actual_slot_file_path(slot)
        if (not vocal_path) or vocal_path == actual_path:
            self._clear_vocal_shadow_player(player)
            return
        shadow = self._shadow_player_for(player)
        if shadow is None:
            shadow = self._create_vocal_shadow_player()
            self._vocal_shadow_players[id(player)] = shadow
        try:
            self._vocal_shadow_pending_loads.pop(id(shadow), None)
            request_id = shadow.setMediaAsync(vocal_path, dsp_config=self._dsp_config)
            self._vocal_shadow_pending_loads[id(shadow)] = {
                "request_id": int(request_id),
                "primary": player,
                "slot": slot,
                "vocal_path": vocal_path,
                "start_playing": bool(start_playing),
                "started_at": time.perf_counter(),
            }
            self._player_mix_volume_map[id(shadow)] = 0
            self._apply_player_mix_volumes(player)
        except Exception:
            self._clear_vocal_shadow_player(player)

    def _on_vocal_shadow_media_load_finished(self, request_id: int, ok: bool, error: str) -> None:
        if bool(getattr(self, "_shutdown_in_progress", False)):
            return
        shadow = self.sender()
        if not self._is_audio_player(shadow):
            return
        pending = self._vocal_shadow_pending_loads.get(id(shadow))
        if pending is None or int(pending.get("request_id", -1)) != int(request_id):
            return
        self._vocal_shadow_pending_loads.pop(id(shadow), None)
        primary = pending.get("primary")
        if not self._is_audio_player(primary):
            try:
                shadow.deleteLater()
            except Exception:
                pass
            return
        if self._shadow_player_for(primary) is not shadow:
            try:
                shadow.deleteLater()
            except Exception:
                pass
            return
        if not ok:
            print(f"[pySSP] Vocal-removed shadow load failed: {pending.get('vocal_path')} | {error}", flush=True)
            self._clear_vocal_shadow_player(primary)
            return
        slot = pending.get("slot")
        if isinstance(slot, SoundButtonData):
            self._seek_player_to_slot_start_cue(shadow, slot)
        self._player_mix_volume_map[id(shadow)] = 0
        if bool(pending.get("start_playing", False)):
            shadow.play()
        else:
            shadow.pause()
        self._sync_shadow_transport_from_primary(primary)
        self._apply_player_mix_volumes(primary)

    def _apply_audio_preload_cache_settings(self) -> None:
        configure_audio_preload_cache_policy(
            self.preload_audio_enabled,
            self.preload_audio_memory_limit_mb,
            self.preload_memory_pressure_enabled,
            self.preload_use_ffmpeg,
        )
        self._sync_preload_pause_state(self._is_playback_in_progress())
        self._queue_current_page_audio_preload()

    def _clear_waveform_cache_now(self) -> None:
        if clear_waveform_disk_cache():
            QMessageBox.information(self, tr("Waveform Cache"), tr("Waveform cache cleared."))
            return
        QMessageBox.warning(self, tr("Waveform Cache"), tr("Failed to clear waveform cache."))

    def _queue_current_page_audio_preload(self) -> None:
        if not self.preload_audio_enabled or not self.preload_current_page_audio or self._is_button_drag_enabled():
            return
        # Cache stores float32 stereo PCM (~352.8 bytes/ms @ 44.1kHz), use this as a practical estimate.
        bytes_per_ms = 352.8
        fallback_bytes = 5 * 1024 * 1024
        candidates: List[Tuple[str, int]] = []
        for slot in self._current_page_slots():
            if not slot.assigned or slot.marker:
                continue
            path = str(slot.file_path or "").strip()
            if slot.source_type != FILE_SOURCE_TYPE:
                continue
            if not path or not os.path.exists(path):
                continue
            if self._path_safety_reason(path):
                continue
            if is_audio_preloaded(path):
                continue
            duration_ms = max(0, int(slot.duration_ms))
            estimated = int(duration_ms * bytes_per_ms) if duration_ms > 0 else fallback_bytes
            candidates.append((path, max(1, estimated)))
        if not candidates:
            return
        remaining_bytes, _effective_limit, _used_bytes = get_audio_preload_capacity_bytes()
        total_estimated = sum(size for _path, size in candidates)
        if remaining_bytes < total_estimated:
            # Constrained RAM: prioritize first couple tracks on the page.
            paths = [path for path, _size in candidates[:2]]
        else:
            paths = [path for path, _size in candidates]
        if paths:
            request_audio_preload(paths, prioritize=True)

    def _refresh_current_page_ram_loaded_indicators(self) -> None:
        if self._is_button_drag_enabled():
            for button in self.sound_buttons:
                button.set_ram_loaded(False)
            return
        page = self._current_page_slots()
        for i, button in enumerate(self.sound_buttons):
            if i >= len(page):
                button.set_ram_loaded(False)
                continue
            slot = page[i]
            if slot.assigned and not slot.marker and slot.source_type == FILE_SOURCE_TYPE:
                button.set_ram_loaded(is_audio_preloaded(slot.file_path))
            else:
                button.set_ram_loaded(False)

    def _sync_preload_pause_state(self, playback_active: bool) -> None:
        should_pause = bool((self.preload_pause_on_playback and playback_active) or self._is_button_drag_enabled())
        if should_pause == self._preload_runtime_paused:
            return
        self._preload_runtime_paused = should_pause
        set_audio_preload_paused(should_pause)
        if not should_pause:
            self._queue_current_page_audio_preload()

    def _sync_playlist_shuffle_buttons(self) -> None:
        if self.cue_mode:
            playlist_enabled = False
            shuffle_enabled = False
        else:
            playlist_enabled = self.page_playlist_enabled[self.current_group][self.current_page]
            shuffle_enabled = self.page_shuffle_enabled[self.current_group][self.current_page]
        play_btn = self.control_buttons.get("Play List")
        shuf_btn = self.control_buttons.get("Shuffle")
        loop_btn = self.control_buttons.get("Loop")
        if play_btn:
            play_btn.setChecked(playlist_enabled)
            self._sync_control_button_instances("Play List")
        if shuf_btn:
            shuf_btn.setEnabled(playlist_enabled)
            shuf_btn.setChecked(shuffle_enabled)
            self._sync_control_button_instances("Shuffle")
        if loop_btn:
            if playlist_enabled:
                loop_btn.setText(tr("Loop Single") if self.playlist_loop_mode == "loop_single" else tr("Loop List"))
            else:
                loop_btn.setText(tr("Loop"))
            self._sync_control_button_instances("Loop")
        self._update_next_button_enabled()
        self._refresh_stage_display()

    def _update_next_button_enabled(self) -> None:
        next_btn = self.control_buttons.get("Next")
        if not next_btn:
            return
        has_next = self._next_slot_for_next_action(blocked=None) is not None
        next_btn.setEnabled(has_next)
        self._sync_control_button_instances("Next")
        self._update_button_drag_control_state()

    def _update_button_drag_control_state(self) -> None:
        drag_btn = self.control_buttons.get("Button Drag")
        if not drag_btn:
            return
        playback_active = self._is_playback_in_progress()
        if playback_active and drag_btn.isChecked():
            drag_btn.setChecked(False)
        drag_btn.setEnabled(not playback_active)
        self._sync_control_button_instances("Button Drag")
        self._update_button_drag_visual_state()

    def _update_button_drag_visual_state(self) -> None:
        enabled = self._is_button_drag_enabled()
        if enabled:
            self.drag_mode_banner.setText(
                tr("BUTTON DRAG MODE ENABLED: Playback is not allowed. ")
                + tr("Drag a sound button with the mouse, drag over Group/Page targets, then drop on a destination button.")
            )
            self.drag_mode_banner.setVisible(True)
            if self.centralWidget() is not None:
                self.centralWidget().setStyleSheet("background:#FFF9E8;")
        else:
            self.drag_mode_banner.setVisible(False)
            if self.centralWidget() is not None:
                self.centralWidget().setStyleSheet("")

    def _cue_slot(self, slot: SoundButtonData) -> None:
        for i, cue_slot in enumerate(self.cue_page):
            if not cue_slot.assigned:
                self.cue_page[i] = SoundButtonData(
                    source_type=slot.source_type,
                    file_path=slot.file_path,
                    disable_video_loading=bool(slot.disable_video_loading),
                    vocal_removed_file=slot.vocal_removed_file,
                    title=slot.title,
                    notes=slot.notes,
                    lyric_file=slot.lyric_file,
                    automation_script_path=slot.automation_script_path,
                    duration_ms=slot.duration_ms,
                    automation_spec=None if slot.automation_spec is None else normalize_automation_spec(slot.automation_spec),
                    sound_button_automation=normalize_sound_button_automation_config(slot.sound_button_automation),
                    automation_script_bypassed=bool(slot.automation_script_bypassed),
                    utility_spec=None if slot.utility_spec is None else normalize_utility_spec(slot.utility_spec),
                    custom_color=slot.custom_color,
                    played=slot.played,
                    activity_code=slot.activity_code,
                    copied_to_cue=True,
                    volume_override_pct=slot.volume_override_pct,
                    cue_start_ms=slot.cue_start_ms,
                    cue_end_ms=slot.cue_end_ms,
                    timecode_offset_ms=slot.timecode_offset_ms,
                    timecode_timeline_mode=slot.timecode_timeline_mode,
                    sound_hotkey=slot.sound_hotkey,
                    sound_midi_hotkey=slot.sound_midi_hotkey,
                )
                slot.copied_to_cue = True
                self._set_dirty(True)
                break
        self._refresh_sound_grid()

    def _clear_cue_page(self) -> None:
        self.cue_page = [SoundButtonData() for _ in range(self._runtime_sound_button_slot_cap())]
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _is_fade_in_enabled(self) -> bool:
        btn = self.control_buttons.get("Fade In")
        return bool(btn and btn.isChecked())

    def _is_cross_fade_enabled(self) -> bool:
        btn = self.control_buttons.get("X")
        return bool(btn and btn.isChecked())

    def _is_cross_mode_enabled(self) -> bool:
        return self._is_cross_fade_enabled()

    def _current_fade_mode(self) -> str:
        # Mode priority:
        # 1) Cross fade when X is enabled.
        # 2) Fade out then fade in when both fade buttons are enabled.
        # 3) Fade out only.
        # 4) Fade in only.
        # 5) No fade mode.
        if self._is_cross_fade_enabled():
            return "cross_fade"
        fade_in_on = self._is_fade_in_enabled()
        fade_out_on = self._is_fade_out_enabled()
        if fade_in_on and fade_out_on:
            return "fade_out_then_fade_in"
        if fade_out_on:
            return "fade_out_only"
        if fade_in_on:
            return "fade_in_only"
        return "none"

    def _is_fade_out_enabled(self) -> bool:
        btn = self.control_buttons.get("Fade Out")
        return bool(btn and btn.isChecked())

    def _effective_master_volume(self) -> int:
        base = self.volume_slider.value()
        return max(0, min(100, base))

    def _effective_output_base_volume(self) -> int:
        base = self._effective_master_volume()
        if self.talk_active:
            talk_level = max(0, min(100, int(self.talk_volume_level)))
            if self.talk_volume_mode == "set_exact":
                base = talk_level
            elif self.talk_volume_mode == "lower_only":
                base = min(base, talk_level)
            else:
                base = int(base * (talk_level / 100.0))
        return max(0, min(100, base))

    def _effective_slot_target_volume(self, slot_volume_pct: int) -> int:
        slot = max(0, min(100, int(slot_volume_pct)))
        master = self._effective_master_volume()
        output_base = self._effective_output_base_volume()
        if master <= 0:
            unity_base = 100
            if self.talk_active:
                talk_level = max(0, min(100, int(self.talk_volume_level)))
                if self.talk_volume_mode == "set_exact":
                    unity_base = talk_level
                elif self.talk_volume_mode == "lower_only":
                    unity_base = min(100, talk_level)
                else:
                    unity_base = int(100 * (talk_level / 100.0))
            return max(0, min(100, int(round(slot * (unity_base / 100.0)))))
        output_target = output_base * (slot / 100.0)
        return max(0, min(100, int(round(output_target * (100.0 / master)))))

    def _slot_pct_for_player(self, player: ExternalMediaPlayer) -> int:
        if player is self.player:
            return self._player_slot_volume_pct
        if player is self.player_b:
            return self._player_b_slot_volume_pct
        return max(0, min(100, int(self._player_slot_pct_map.get(id(player), 75))))

    def _set_player_slot_pct(self, player: ExternalMediaPlayer, slot_pct: int) -> None:
        slot_pct = max(0, min(100, int(slot_pct)))
        if player is self.player:
            self._player_slot_volume_pct = slot_pct
            return
        if player is self.player_b:
            self._player_b_slot_volume_pct = slot_pct
            return
        self._player_slot_pct_map[id(player)] = slot_pct

    def _mark_player_started(self, player: ExternalMediaPlayer) -> None:
        slot_key = self._player_slot_key_map.get(id(player))
        self._player_started_map[id(player)] = time.monotonic()
        self._player_runtime_local_id_map[id(player)] = int(self._player_runtime_local_id_next)
        self._player_runtime_local_id_next += 1
        if slot_key is not None:
            self._prime_automation_script_player(player, slot_key)
            slot = self._slot_for_key(slot_key)
            if slot is not None:
                self._warn_dual_automation_sources_if_needed(slot)

    def _set_player_slot_key(self, player: ExternalMediaPlayer, slot_key: Tuple[str, int, int]) -> None:
        pid = id(player)
        old_key = self._player_slot_key_map.get(pid)
        if old_key is not None:
            self._active_playing_keys.discard(old_key)
        self._clear_player_cue_behavior_override(player)
        self._player_slot_key_map[pid] = slot_key
        player_id = str(getattr(player, "player_id", "") or "").strip()
        if player_id:
            try:
                self._audio_service.set_session_slot_key(player_id, slot_key)
            except Exception:
                pass
        self._active_playing_keys.add(slot_key)
        self._update_status_now_playing()
        self._refresh_vocal_removed_warning_banner()

    def _clear_player_slot_key(self, player: ExternalMediaPlayer) -> None:
        pid = id(player)
        key = self._player_slot_key_map.pop(pid, None)
        player_id = str(getattr(player, "player_id", "") or "").strip()
        if player_id:
            try:
                self._audio_service.set_session_slot_key(player_id, None)
            except Exception:
                pass
        self._automation_script_runtime.pop(pid, None)
        if key is not None:
            self._active_playing_keys.discard(key)
        self._clear_player_cue_behavior_override(player)
        self._player_runtime_local_id_map.pop(pid, None)
        if self.current_playing == key:
            self._refresh_current_playing_from_active_players()
        self._update_status_now_playing()
        self._refresh_vocal_removed_warning_banner()

    def _clear_all_player_slot_keys(self) -> None:
        self._player_slot_key_map.clear()
        self._automation_script_runtime.clear()
        self._active_playing_keys.clear()
        self._player_runtime_local_id_map.clear()
        self._player_end_override_ms.clear()
        self._player_ignore_cue_end.clear()
        self.current_playing = None
        self._update_status_now_playing()
        self._refresh_vocal_removed_warning_banner()

    def _is_multi_play_enabled(self) -> bool:
        btn = self.control_buttons.get("Multi-Play")
        return bool(btn and btn.isChecked())

    def _all_active_players(self) -> List[ExternalMediaPlayer]:
        active: List[ExternalMediaPlayer] = []
        for player in [self.player, self.player_b, *self._multi_players]:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                active.append(player)
        return active

    def _prune_multi_players(self) -> None:
        remaining: List[ExternalMediaPlayer] = []
        current_changed = False
        for player in self._multi_players:
            if player.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                remaining.append(player)
                continue
            handled_stop = id(player) in self._sound_button_automation_handled_stop_player_ids
            if handled_stop:
                self._sound_button_automation_handled_stop_player_ids.discard(id(player))
            else:
                self._trigger_sound_button_stopped_event(self._player_slot_key_map.get(id(player)), natural=True)
            if self.current_playing == self._player_slot_key_map.get(id(player)):
                current_changed = True
            self._clear_vocal_shadow_player(player)
            self._clear_player_slot_key(player)
            self._player_slot_pct_map.pop(id(player), None)
            self._player_started_map.pop(id(player), None)
            self._player_mix_volume_map.pop(id(player), None)
            try:
                player.deleteLater()
            except Exception:
                pass
        self._multi_players = remaining
        if current_changed:
            self._refresh_current_playing_from_active_players()

    def _enforce_multi_play_limit(self) -> bool:
        max_allowed = max(1, int(self.max_multi_play_songs))
        active_players = self._all_active_players()
        if len(active_players) < max_allowed:
            return True
        if self.multi_play_limit_action == "disallow_more_play":
            self._show_info_notice_banner(f"Maximum Multi-Play songs reached ({max_allowed}).")
            return False
        runtime_by_player_id = {
            str(session.session_id): session
            for session in self._audio_service.runtime_session_snapshots()
        }
        oldest = None
        ranked_players: list[tuple[int, float, str, ExternalMediaPlayer]] = []
        for player in active_players:
            player_id = str(getattr(player, "player_id", "") or "").strip()
            session = runtime_by_player_id.get(player_id)
            if session is None:
                continue
            ranked_players.append((int(session.runtime_id), float(session.started_at), player_id, player))
        if ranked_players:
            oldest = min(ranked_players, key=lambda item: (item[0], item[1], item[2]))[-1]
        if oldest is None:
            oldest = min(active_players, key=lambda p: self._player_started_map.get(id(p), 0.0))
        self._stop_single_player(oldest)
        self._prune_multi_players()
        return True

    def _stop_single_player(self, player: ExternalMediaPlayer, emit_stop_events: bool = True) -> None:
        stopped_key = self._player_slot_key_map.get(id(player))
        if emit_stop_events and stopped_key is not None:
            self._trigger_sound_button_stopped_event(stopped_key, natural=False)
            self._sound_button_automation_handled_stop_player_ids.add(id(player))
        self._cancel_fade_for_player(player)
        self._stop_player_internal(player)
        self._clear_vocal_shadow_player(player)
        self._clear_player_slot_key(player)
        self._player_slot_pct_map.pop(id(player), None)
        self._player_started_map.pop(id(player), None)
        self._player_mix_volume_map.pop(id(player), None)
        if player is self.player:
            self._player_slot_volume_pct = 75
        elif player is self.player_b:
            self._player_b_slot_volume_pct = 75
        if self.current_playing == stopped_key or self.current_playing is None:
            self._refresh_current_playing_from_active_players()

    def _set_player_volume(self, player: ExternalMediaPlayer, volume: int) -> None:
        self._apply_player_mix_volumes(player, volume)

    @staticmethod
    def _set_player_master_volume(player: object, volume: int) -> None:
        setter = getattr(player, "setMasterVolume", None)
        if not callable(setter):
            return
        try:
            setter(max(0, min(100, int(volume))))
        except Exception:
            pass

    def _cancel_fade_for_player(self, player: ExternalMediaPlayer) -> None:
        self._fade_jobs = [job for job in self._fade_jobs if job["player"] is not player]
        self._cancel_vocal_toggle_fade_for_player(player)

    def _start_fade(
        self,
        player: ExternalMediaPlayer,
        target_volume: int,
        seconds: float,
        stop_on_complete: bool = False,
        pause_on_complete: bool = False,
        pause_resume_volume: Optional[int] = None,
        automation_slot_key: Optional[Tuple[str, int, int]] = None,
        automation_start_events: tuple[str, ...] = (),
        automation_end_events: tuple[str, ...] = (),
    ) -> None:
        start_volume = self._logical_player_volume(player)
        target = max(0, min(100, int(target_volume)))
        self._cancel_fade_for_player(player)
        if target == start_volume:
            if stop_on_complete and target == 0:
                if player is not self.player or self._manual_stop_requested:
                    slot_key = self._player_slot_key_map.get(id(player))
                    if slot_key is not None:
                        self._trigger_sound_button_stopped_event(slot_key, natural=False)
                        self._sound_button_automation_handled_stop_player_ids.add(id(player))
                player.stop()
            return
        if seconds <= 0:
            self._set_player_volume(player, target)
            if stop_on_complete:
                if player is not self.player or self._manual_stop_requested:
                    slot_key = self._player_slot_key_map.get(id(player))
                    if slot_key is not None:
                        self._trigger_sound_button_stopped_event(slot_key, natural=False)
                        self._sound_button_automation_handled_stop_player_ids.add(id(player))
                player.stop()
            return
        direction = "none"
        if target > start_volume:
            direction = "in"
        elif target < start_volume:
            direction = "out"
        if automation_slot_key is not None and automation_start_events:
            self._trigger_sound_button_fade_events(automation_slot_key, *automation_start_events)
        self._fade_jobs.append(
            {
                "player": player,
                "start": start_volume,
                "end": target,
                "dir": direction,
                "started": time.monotonic(),
                "duration": max(0.01, float(seconds)),
                "stop": stop_on_complete,
                "pause": pause_on_complete,
                "pause_resume_volume": pause_resume_volume,
                "automation_slot_key": automation_slot_key,
                "automation_end_events": tuple(automation_end_events or ()),
            }
        )

    def _tick_fades(self) -> None:
        if not self._fade_jobs and not self._vocal_toggle_fade_jobs:
            if self._stop_fade_armed:
                self._stop_fade_armed = False
            self._update_fade_button_flash(False)
            return
        now = time.monotonic()
        remaining: List[dict] = []
        any_stopped = False
        remaining_vocal_jobs: Dict[int, dict] = {}
        for player_id, job in self._vocal_toggle_fade_jobs.items():
            player = job.get("player")
            shadow = job.get("shadow")
            if not self._is_audio_player(player) or not self._is_audio_player(shadow):
                continue
            if player.state() not in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                continue
            if shadow.state() not in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                continue
            elapsed = now - job["started"]
            ratio = max(0.0, min(1.0, elapsed / job["duration"]))
            primary_volume = _equal_power_crossfade_volume(
                job["start_primary"],
                job["end_primary"],
                ratio,
            )
            shadow_volume = _equal_power_crossfade_volume(
                job["start_shadow"],
                job["end_shadow"],
                ratio,
            )
            player.setVolume(max(0, min(100, primary_volume)))
            shadow.setVolume(max(0, min(100, shadow_volume)))
            if ratio < 1.0:
                remaining_vocal_jobs[player_id] = job
        self._vocal_toggle_fade_jobs = remaining_vocal_jobs
        for job in self._fade_jobs:
            elapsed = now - job["started"]
            ratio = max(0.0, min(1.0, elapsed / job["duration"]))
            volume = int(job["start"] + (job["end"] - job["start"]) * ratio)
            self._set_player_volume(job["player"], volume)
            if ratio >= 1.0:
                slot_key = job.get("automation_slot_key")
                end_events = tuple(job.get("automation_end_events") or ())
                if slot_key is not None and end_events:
                    self._trigger_sound_button_fade_events(slot_key, *end_events)
                if job["stop"]:
                    if job["player"] is not self.player or self._manual_stop_requested:
                        stop_slot_key = self._player_slot_key_map.get(id(job["player"]))
                        if stop_slot_key is not None:
                            self._trigger_sound_button_stopped_event(stop_slot_key, natural=False)
                            self._sound_button_automation_handled_stop_player_ids.add(id(job["player"]))
                    self._stop_player_internal(job["player"])
                    any_stopped = True
                elif job.get("pause"):
                    job["player"].pause()
                    self._sync_shadow_transport_from_primary(job["player"])
                    self._trigger_sound_button_paused_event(self._player_slot_key_map.get(id(job["player"])))
                    resume_volume = job.get("pause_resume_volume")
                    if resume_volume is not None:
                        self._set_player_volume(job["player"], int(resume_volume))
            else:
                remaining.append(job)
        self._fade_jobs = remaining
        self._update_fade_button_flash(True)
        if any_stopped:
            self._refresh_sound_grid()

    def _update_fade_button_flash(self, any_fade: bool) -> None:
        now = time.monotonic()
        if now - self._last_fade_flash_toggle >= 0.22:
            self._fade_flash_on = not self._fade_flash_on
            self._last_fade_flash_toggle = now
        flash_on = any_fade and self._fade_flash_on
        self._set_button_flash_style("Fade In", flash_on)
        self._set_button_flash_style("Fade Out", flash_on)
        self._set_button_flash_style("X", flash_on)

    def _set_button_flash_style(self, key: str, flash_on: bool) -> None:
        btn = self.control_buttons.get(key)
        if not btn:
            return
        if flash_on:
            btn.setStyleSheet("background:#FFE680; font-weight:bold;")
        else:
            btn.setStyleSheet("")
        self._sync_control_button_instances(key)

    def _try_auto_fade_transition(self) -> None:
        if (
            self.fade_out_when_done_playing
            and self.current_playing is not None
            and self.player.state() == ExternalMediaPlayer.PlayingState
            and self.current_duration_ms > 0
            and self.fade_out_sec > 0
            and self._is_fade_out_enabled()
            and (not self._is_cross_fade_enabled())
        ):
            track_key = self.current_playing
            if self._auto_end_fade_track != track_key:
                self._auto_end_fade_track = track_key
                self._auto_end_fade_done = False
            if not self._auto_end_fade_done:
                remaining_ms = max(0, self.current_duration_ms - self.player.position())
                lead_ms = max(0, int(self.fade_out_end_lead_sec * 1000))
                if remaining_ms <= lead_ms:
                    self._auto_end_fade_done = True
                    self._start_fade(
                        self.player,
                        0,
                        self.fade_out_sec,
                        stop_on_complete=True,
                        automation_slot_key=track_key,
                        automation_start_events=("on_end_fade_out_start",),
                        automation_end_events=("on_end_fade_out_end",),
                    )

        if not self._is_cross_fade_enabled():
            return
        if self.cue_mode:
            return
        if not self.current_playing:
            return
        track_key = self.current_playing
        track_slot = self._slot_for_key(track_key)
        if not self._slot_follows_regular_playback_controls(track_slot):
            return
        track_group, track_page, _track_slot_index = track_key
        if track_group == "Q":
            return
        if not self.page_playlist_enabled[track_group][int(track_page)]:
            return
        if self.player.state() != ExternalMediaPlayer.PlayingState:
            return
        if self.current_duration_ms <= 0:
            return
        if (time.monotonic() - self._track_started_at) < 0.35:
            return

        if self._auto_transition_track != track_key:
            self._auto_transition_track = track_key
            self._auto_transition_done = False
        if self._auto_transition_done:
            return

        remaining_ms = max(0, self.current_duration_ms - self.player.position())
        if self._is_cross_fade_enabled() and self.cross_fade_sec > 0:
            if remaining_ms <= int(self.cross_fade_sec * 1000):
                blocked: set[int] = set()
                while True:
                    next_slot = self._next_playlist_slot(
                        for_auto_advance=True,
                        blocked=blocked,
                        group_key=track_group,
                        page_index=int(track_page),
                        current_track=track_key,
                    )
                    if next_slot is None:
                        break
                    next_key = (track_group, int(track_page), int(next_slot))
                    next_slot_data = self._slot_for_key(next_key)
                    if next_slot_data is not None and next_slot_data.source_type == AUTOMATION_SOURCE_TYPE:
                        blocked.add(next_slot)
                        continue
                    self.current_group = track_group
                    self.current_page = int(track_page)
                    self.cue_mode = False
                    self._refresh_group_buttons()
                    self._sync_playlist_shuffle_buttons()
                    self._refresh_page_list()
                    if self._play_slot_via_control_flow(next_slot):
                        self._auto_transition_done = True
                        break
                    blocked.add(next_slot)
                    if self.candidate_error_action == "stop_playback":
                        self._stop_playback()
                        break
            return

    def _swap_primary_secondary_players(self) -> None:
        try:
            self.player.positionChanged.disconnect(self._on_position_changed)
            self.player.durationChanged.disconnect(self._on_duration_changed)
            self.player.stateChanged.disconnect(self._on_state_changed)
        except TypeError:
            pass
        try:
            self.player_b.positionChanged.disconnect(self._on_secondary_position_changed)
        except TypeError:
            pass
        self.player, self.player_b = self.player_b, self.player
        self._player_slot_volume_pct, self._player_b_slot_volume_pct = (
            self._player_b_slot_volume_pct,
            self._player_slot_volume_pct,
        )
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.stateChanged.connect(self._on_state_changed)
        self.player_b.positionChanged.connect(self._on_secondary_position_changed)
