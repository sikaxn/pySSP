from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class TimecodeMixin:
    def _build_timecode_dock(self) -> None:
        self.timecode_dock = QDockWidget("Timecode", self)
        self.timecode_panel = TimecodePanel(self.timecode_dock)
        self.timecode_dock.setWidget(self.timecode_panel)
        self.timecode_dock.setAllowedAreas(Qt.NoDockWidgetArea)
        self.timecode_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        self.timecode_dock.setVisible(bool(self.show_timecode_panel))
        self.addDockWidget(Qt.RightDockWidgetArea, self.timecode_dock)
        self.timecode_dock.setFloating(True)
        self.timecode_dock.visibilityChanged.connect(self._on_timecode_dock_visibility_changed)
        self.timecode_panel.mode_combo.currentIndexChanged.connect(self._on_timecode_mode_changed)
        mode_idx = self.timecode_panel.mode_combo.findData(self.timecode_mode)
        self.timecode_panel.mode_combo.blockSignals(True)
        self.timecode_panel.mode_combo.setCurrentIndex(mode_idx if mode_idx >= 0 else 0)
        self.timecode_panel.mode_combo.blockSignals(False)
        self._refresh_timecode_panel()

    def _on_timecode_mode_changed(self, _index: int) -> None:
        if self.timecode_panel is None:
            return
        mode = str(self.timecode_panel.mode_combo.currentData() or TIMECODE_MODE_ZERO)
        if mode not in {
            TIMECODE_MODE_ZERO,
            TIMECODE_MODE_FOLLOW,
            TIMECODE_MODE_SYSTEM,
            TIMECODE_MODE_FOLLOW_FREEZE,
        }:
            mode = TIMECODE_MODE_ZERO
        if mode == TIMECODE_MODE_FOLLOW_FREEZE and self.timecode_mode != TIMECODE_MODE_FOLLOW_FREEZE:
            self._timecode_follow_frozen_ms = self._timecode_current_follow_ms()
        self.timecode_mode = mode
        self._refresh_timecode_panel()
        if not self._suspend_settings_save:
            self._save_settings()

    def _on_timecode_dock_visibility_changed(self, visible: bool) -> None:
        self.show_timecode_panel = bool(visible)
        action = self._menu_actions.get("timecode_panel")
        if action is not None:
            action.setChecked(bool(visible))
        if not self._suspend_settings_save:
            self._save_settings()

    def _toggle_timecode_panel(self) -> None:
        if self.timecode_dock is None:
            return
        self.timecode_dock.setVisible(not self.timecode_dock.isVisible())

    def _is_timecode_output_enabled(self) -> bool:
        ltc_enabled = str(self.timecode_audio_output_device or "none").strip().lower() != "none"
        mtc_enabled = str(self.timecode_midi_output_device or MIDI_OUTPUT_DEVICE_NONE).strip() != MIDI_OUTPUT_DEVICE_NONE
        return ltc_enabled or mtc_enabled

    def _update_timecode_multiplay_warning_banner(self) -> None:
        show_warning = self._is_multi_play_enabled() and self._is_timecode_output_enabled()
        if show_warning:
            self.timecode_multiplay_banner.setText(
                tr("TIMECODE ENABLED: Multi-Play is not designed for timecode. Unexpected behaviour could happen.")
            )
            self.timecode_multiplay_banner.setVisible(True)
            return
        self.timecode_multiplay_banner.setVisible(False)

    def _show_playback_warning_banner(self, text: str, timeout_ms: int = 5000) -> None:
        self._playback_warning_token += 1
        token = self._playback_warning_token
        self.playback_warning_banner.setText(str(text or "").strip())
        self.playback_warning_banner.setVisible(True)
        if timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda t=token: self._hide_playback_warning_banner(t))

    def _hide_playback_warning_banner(self, token: Optional[int] = None) -> None:
        if token is not None and token != self._playback_warning_token:
            return
        self.playback_warning_banner.setVisible(False)

    def _show_save_notice_banner(self, text: str, timeout_ms: int = 5000) -> None:
        self._save_notice_token += 1
        token = self._save_notice_token
        self.save_notice_banner.setText(str(text or "").strip())
        self.save_notice_banner.setVisible(True)
        if timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda t=token: self._hide_save_notice_banner(t))

    def _hide_save_notice_banner(self, token: Optional[int] = None) -> None:
        if token is not None and token != self._save_notice_token:
            return
        self.save_notice_banner.setVisible(False)

    def _show_info_notice_banner(self, text: str, timeout_ms: int = 5000) -> None:
        self._info_notice_token += 1
        token = self._info_notice_token
        self.info_notice_banner.setText(str(text or "").strip())
        self.info_notice_banner.setVisible(True)
        if timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda t=token: self._hide_info_notice_banner(t))

    def _hide_info_notice_banner(self, token: Optional[int] = None) -> None:
        if token is not None and token != self._info_notice_token:
            return
        self.info_notice_banner.setVisible(False)

    def _timecode_current_follow_ms(self) -> int:
        reference_player, reference_key = self._timecode_reference_context()
        if reference_player is None:
            self._timecode_follow_anchor_ms = 0.0
            self._timecode_follow_anchor_t = time.perf_counter()
            self._timecode_follow_playing = False
            self._timecode_follow_intent_pending = False
            return 0
        is_playing = reference_player.state() == ExternalMediaPlayer.PlayingState
        now = time.perf_counter()
        predicted_ms = self._timecode_follow_anchor_ms + max(0.0, (now - self._timecode_follow_anchor_t) * 1000.0)
        try:
            absolute_ms = max(0, int(reference_player.enginePositionMs()))
        except Exception:
            try:
                absolute_ms = max(0, int(reference_player.position()))
            except Exception:
                absolute_ms = 0
        media_ms = float(self._timecode_display_ms_from_absolute(absolute_ms, slot_key=reference_key))
        if not is_playing:
            if self._timecode_follow_intent_pending and self._timecode_follow_playing:
                self._timecode_follow_anchor_ms = predicted_ms
                self._timecode_follow_anchor_t = now
                return int(max(0.0, predicted_ms))
            self._timecode_follow_anchor_ms = media_ms
            self._timecode_follow_anchor_t = now
            self._timecode_follow_playing = False
            return int(media_ms)

        self._timecode_follow_anchor_ms = media_ms
        self._timecode_follow_anchor_t = now
        self._timecode_follow_playing = True
        self._timecode_follow_intent_pending = False
        self._timecode_last_media_ms = media_ms
        self._timecode_last_media_t = now
        return int(max(0.0, self._timecode_follow_anchor_ms))

    def _timecode_reference_context(self) -> Tuple[Optional[ExternalMediaPlayer], Optional[Tuple[str, int, int]]]:
        active_players = self._all_active_players()
        reference_player = self._playback_runtime.timecode_player(active_players, self._is_multi_play_enabled())
        if reference_player is None:
            return None, None
        reference_key = self._player_slot_key_map.get(id(reference_player))
        return reference_player, reference_key

    def _newest_active_playing_key(self) -> Optional[Tuple[str, int, int]]:
        active_players = self._all_active_players()
        newest_player = self._playback_runtime.newest_active_player(active_players)
        if newest_player is not None:
            newest_key = self._player_slot_key_map.get(id(newest_player))
            if newest_key is not None:
                return newest_key
        if self._active_playing_keys:
            return sorted(self._active_playing_keys)[-1]
        return None

    def _refresh_current_playing_from_active_players(self) -> None:
        self.current_playing = self._newest_active_playing_key()

    def _timecode_display_ms_from_absolute(
        self,
        absolute_ms: int,
        slot_key: Optional[Tuple[str, int, int]] = None,
    ) -> int:
        absolute = max(0, int(absolute_ms))
        slot: Optional[SoundButtonData] = None
        effective_slot_key = slot_key if slot_key is not None else self.current_playing
        if effective_slot_key is not None:
            slot = self._slot_for_key(effective_slot_key)
        timeline_mode = self.timecode_timeline_mode
        if slot is not None:
            timeline_mode = self._effective_slot_timecode_timeline_mode(slot)
        if timeline_mode == "cue_region" and slot is not None:
            cue_start = 0 if slot.cue_start_ms is None else max(0, int(slot.cue_start_ms))
            absolute = max(0, absolute - cue_start)
        if slot is not None and self.soundbutton_timecode_offset_enabled:
            offset_ms = slot.timecode_offset_ms
            if offset_ms is not None and int(offset_ms) > 0:
                absolute += int(offset_ms)
        return max(0, absolute)

    def _effective_slot_timecode_timeline_mode(self, slot: SoundButtonData) -> str:
        mode = self.timecode_timeline_mode
        if not self.respect_soundbutton_timecode_timeline_setting:
            return mode
        slot_mode = normalize_slot_timecode_timeline_mode(slot.timecode_timeline_mode)
        if slot_mode in {"audio_file", "cue_region"}:
            return slot_mode
        return mode

    def _timecode_output_ms(self) -> int:
        if self.timecode_mode == TIMECODE_MODE_ZERO:
            return 0
        if self.timecode_mode == TIMECODE_MODE_SYSTEM:
            now = datetime.now()
            return (
                ((now.hour * 3600 + now.minute * 60 + now.second) * 1000)
                + int(now.microsecond / 1000)
            )
        if self.timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE:
            return max(0, int(self._timecode_follow_frozen_ms))
        # In follow mode, once playback is fully stopped/ended, reset timecode to zero
        # instead of re-deriving from residual player position without slot offset context.
        if not self._is_playback_in_progress():
            return 0
        return self._timecode_current_follow_ms()

    def _timecode_device_text(self) -> str:
        ltc_format = (
            f"LTC {self.timecode_fps:g} fps, MTC {self.timecode_mtc_fps:g} fps "
            f"({self.timecode_mtc_idle_behavior}), {self.timecode_sample_rate} Hz, {self.timecode_bit_depth}-bit"
        )
        midi_text = "MIDI: Disabled"
        if self.timecode_midi_output_device != MIDI_OUTPUT_DEVICE_NONE:
            midi_map = {device_id: name for device_id, name in list_midi_output_devices()}
            midi_name = midi_map.get(self.timecode_midi_output_device, "Unavailable")
            midi_text = f"MIDI: {midi_name}"
        if self.timecode_audio_output_device == "follow_playback":
            return f"Output Device: Follows playback device setting ({ltc_format}) | {midi_text}"
        if self.timecode_audio_output_device == "none":
            return f"Output Device: None (muted) ({ltc_format}) | {midi_text}"
        if self.timecode_audio_output_device in {"default", ""}:
            return f"Output Device: System default ({ltc_format}) | {midi_text}"
        return f"Output Device: {self.timecode_audio_output_device} ({ltc_format}) | {midi_text}"

    def _tick_timecode_mtc(self) -> None:
        ltc_device: Optional[str]
        if self.timecode_audio_output_device == "none":
            ltc_device = None
        elif self.timecode_audio_output_device == "follow_playback":
            selected = str(self.audio_output_device or "").strip()
            ltc_device = selected if selected else None
        elif self.timecode_audio_output_device in {"default", ""}:
            ltc_device = ""
        else:
            ltc_device = str(self.timecode_audio_output_device).strip()
        self._ltc_sender.set_output(
            ltc_device,
            int(self.timecode_sample_rate),
            int(self.timecode_bit_depth),
            float(self.timecode_fps),
        )
        self._mtc_sender.set_device(self.timecode_midi_output_device)
        output_ms = self._timecode_output_ms()
        current_frame = int((max(0, output_ms) / 1000.0) * max(1.0, float(self.timecode_fps)))
        self._ltc_sender.update(
            current_frame=current_frame,
            fps=max(1.0, float(self.timecode_fps)),
        )
        self._mtc_sender.update(
            current_frame=current_frame,
            source_fps=max(1.0, float(self.timecode_fps)),
            mtc_fps=max(1.0, float(self.timecode_mtc_fps)),
        )

    def _timecode_on_playback_start(self, slot: Optional[SoundButtonData] = None) -> None:
        now = time.perf_counter()
        if now < self._timecode_event_guard_until:
            return
        start_abs = 0
        if slot is not None:
            duration_guess = max(0, int(slot.duration_ms))
            start_abs = self._cue_start_for_playback(slot, duration_guess)
        start_display = float(self._timecode_display_ms_from_absolute(start_abs))
        self._timecode_follow_anchor_ms = start_display
        self._timecode_follow_anchor_t = now
        self._timecode_follow_playing = True
        self._timecode_follow_intent_pending = True
        self._timecode_last_media_ms = start_display
        self._timecode_last_media_t = now
        print(
            f"[TCDBG] {now:.6f} timecode_start anchor_ms={start_display:.1f} "
            f"slot={(slot.title if slot else '<none>')}"
        )
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _timecode_on_playback_stop(self) -> None:
        now = time.perf_counter()
        if now < self._timecode_event_guard_until:
            return
        self._timecode_follow_anchor_ms = 0.0
        self._timecode_follow_anchor_t = now
        self._timecode_follow_playing = False
        self._timecode_follow_intent_pending = False
        self._timecode_last_media_ms = 0.0
        self._timecode_last_media_t = now
        print(f"[TCDBG] {now:.6f} timecode_stop")
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _timecode_on_playback_pause(self) -> None:
        if time.perf_counter() < self._timecode_event_guard_until:
            return
        paused_ms = float(self._timecode_current_follow_ms())
        self._timecode_follow_anchor_ms = paused_ms
        self._timecode_follow_anchor_t = time.perf_counter()
        self._timecode_follow_playing = False
        self._timecode_follow_intent_pending = False
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _timecode_on_playback_resume(self) -> None:
        if time.perf_counter() < self._timecode_event_guard_until:
            return
        resume_ms = float(self._timecode_current_follow_ms())
        self._timecode_follow_anchor_ms = resume_ms
        self._timecode_follow_anchor_t = time.perf_counter()
        self._timecode_follow_playing = True
        self._timecode_follow_intent_pending = False
        self._ltc_sender.request_resync()
        self._mtc_sender.request_resync()

    def _refresh_timecode_panel(self) -> None:
        self._update_timecode_status_label()
        if self.timecode_panel is None:
            return
        mode_idx = self.timecode_panel.mode_combo.findData(self.timecode_mode)
        if mode_idx >= 0 and mode_idx != self.timecode_panel.mode_combo.currentIndex():
            self.timecode_panel.mode_combo.blockSignals(True)
            self.timecode_panel.mode_combo.setCurrentIndex(mode_idx)
            self.timecode_panel.mode_combo.blockSignals(False)
        output_ms = self._timecode_output_ms()
        self.timecode_panel.timecode_label.setText(
            ms_to_timecode_string(output_ms, nominal_fps(self.timecode_fps))
        )
        self.timecode_panel.device_label.setText(self._timecode_device_text())

    def _update_timecode_status_label(self) -> None:
        ltc_enabled = str(self.timecode_audio_output_device or "none").strip().lower() != "none"
        mtc_enabled = str(self.timecode_midi_output_device or MIDI_OUTPUT_DEVICE_NONE).strip() != MIDI_OUTPUT_DEVICE_NONE
        if self.timecode_mode == TIMECODE_MODE_ZERO:
            mode_text = "All Zero"
        elif self.timecode_mode == TIMECODE_MODE_SYSTEM:
            mode_text = "System Time"
        elif self.timecode_mode == TIMECODE_MODE_FOLLOW_FREEZE:
            if self.timecode_timeline_mode == "audio_file":
                mode_text = "Freeze Timecode (relative to actual audio file)"
            else:
                mode_text = "Freeze Timecode (relative to cue set point)"
        else:
            if self.timecode_timeline_mode == "audio_file":
                mode_text = "Follow Media/Audio Player (relative to actual audio file)"
            else:
                mode_text = "Follow Media/Audio Player (relative to cue set point)"
        self.timecode_status_label.setText(
            f"{tr('LTC: ')}{tr('Enabled') if ltc_enabled else tr('Disabled')} | "
            f"{tr('MTC: ')}{tr('Enabled') if mtc_enabled else tr('Disabled')} | "
            f"{tr('Timecode: ')}{tr(mode_text)}"
        )

