# `pyssp/ui/main_window/companion_satellite.py`

- Source: `pyssp/ui/main_window/companion_satellite.py`
- Module path: `pyssp.ui.main_window.companion_satellite`
- API entries: `2`

## Module Docstring

No module docstring.

## Classes

### `_CompanionSatelliteBridge`

- Defined at `pyssp/ui/main_window/companion_satellite.py:29`
- Bases: QObject

### `CompanionSatelliteMixin`

- Defined at `pyssp/ui/main_window/companion_satellite.py:37`

#### Internal Members

- `_load_automation_script_cached(self, path: str) -> tuple[Optional[AutomationScript], str]` [method] (pyssp/ui/main_window/companion_satellite.py:38)
- `_build_automation_script_specs(self, actions: list[AutomationScriptAction]) -> list[AutomationCommandSpec]` [method] (pyssp/ui/main_window/companion_satellite.py:60)
- `_execute_automation_command_spec(self, spec: AutomationCommandSpec, action: str = 'press') -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:92)
- `_execute_automation_command_specs(self, specs: list[AutomationCommandSpec]) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:100)
- `_prime_automation_script_player(self, player: ExternalMediaPlayer, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:115)
- `_resync_automation_script_player_for_position(self, player: ExternalMediaPlayer, position_ms: int) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:151)
- `_process_automation_script_player(self, player: ExternalMediaPlayer) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:171)
- `_automation_script_comments_for_slot_key(self, slot_key: Optional[Tuple[str, int, int]], player: Optional[ExternalMediaPlayer] = None) -> tuple[str, str]` [method] (pyssp/ui/main_window/companion_satellite.py:205)
- `_open_companion_available_commands(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:230)
- `_refresh_companion_available_commands_dialog(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:242)
- `_clear_companion_available_commands(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:252)
- `_refresh_companion_available_commands_from_window(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:256)
- `_set_companion_available_commands_filter_black_empty(self, checked: bool) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:264)
- `_record_companion_available_command_state(self, state: dict) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:269)
- `_send_companion_location_command_async(self, location: str, action: str) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:282)
- `_send_companion_command_specs_async(self, specs: list[AutomationCommandSpec]) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:328)
- `_trigger_sound_button_automation_event(self, slot_key: Optional[Tuple[str, int, int]], event_name: str) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:379)
- `_trigger_sound_button_automation_events(self, slot_key: Optional[Tuple[str, int, int]], *event_names: str) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:401)
- `_trigger_sound_button_trigger_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:410)
- `_trigger_sound_button_started_event(self, slot_key: Optional[Tuple[str, int, int]], *, include_advanced: bool) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:413)
- `_trigger_sound_button_fade_events(self, slot_key: Optional[Tuple[str, int, int]], *event_names: str) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:424)
- `_trigger_sound_button_pause_requested_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:431)
- `_trigger_sound_button_paused_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:437)
- `_trigger_sound_button_resume_requested_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:440)
- `_trigger_sound_button_resumed_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:446)
- `_trigger_sound_button_stop_requested_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:452)
- `_trigger_sound_button_force_stop_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:458)
- `_trigger_sound_button_interrupted_by_sound_button_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:464)
- `_trigger_sound_button_interrupted_by_playback_control_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:470)
- `_trigger_sound_button_interrupted_by_app_reset_event(self, slot_key: Optional[Tuple[str, int, int]]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:476)
- `_trigger_sound_button_stopped_event(self, slot_key: Optional[Tuple[str, int, int]], *, natural: bool) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:482)
- `_automation_slot_key(self, slot_index: int) -> Tuple[str, int, int]` [method] (pyssp/ui/main_window/companion_satellite.py:494)
- `_set_automation_slot_active(self, slot_key: Tuple[str, int, int], active: bool) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:497)
- `_mark_automation_slot_played(self, slot_key: Tuple[str, int, int]) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:504)
- `_flash_automation_slot(self, slot_key: Tuple[str, int, int], duration_ms: int = 180) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:513)
- `_automation_button_auto_release_mode(self) -> str` [method] (pyssp/ui/main_window/companion_satellite.py:523)
- `_trigger_automation_slot_press(self, slot_index: int) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:527)
- `_trigger_automation_slot_release(self, slot_index: int) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:546)
- `_trigger_automation_slot_click(self, slot_index: int) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:567)
- `_trigger_automation_slot_non_audio(self, slot_index: int, auto_release: bool = True, *, continue_playlist_after_automation: bool = True) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:573)
- `_companion_satellite_event(self, event_type: str, payload: dict) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:617)
- `_companion_satellite_should_run(self) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:635)
- `_companion_satellite_client_matches_settings(self) -> bool` [method] (pyssp/ui/main_window/companion_satellite.py:638)
- `_apply_companion_satellite_state(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:652)
- `_start_companion_satellite_client(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:662)
- `_stop_companion_satellite_client(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:675)
- `_reconnect_companion_satellite_client(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:681)
- `_open_companion_satellite_options(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:687)
- `_open_virtual_satellite(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:690)
- `_ensure_companion_satellite_window(self) -> CompanionSatelliteWindow` [method] (pyssp/ui/main_window/companion_satellite.py:697)
- `_on_companion_satellite_window_closed(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:712)
- `_refresh_companion_satellite_window(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:715)
- `_on_companion_satellite_status_changed(self, state: str, message: str) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:725)
- `_update_companion_satellite_status_indicator(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:732)
- `_toggle_companion_bypass(self, checked: bool) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:768)
- `_toggle_internal_bypass(self, checked: bool) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:787)
- `_on_companion_satellite_hello_received(self, version: str) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:803)
- `_on_companion_satellite_caps_received(self, caps: dict) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:806)
- `_on_companion_satellite_key_state_received(self, key: int, state: dict) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:809)
- `_on_companion_satellite_keys_cleared(self) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:816)
- `_on_companion_satellite_button_pressed(self, key: int, pressed: bool) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:821)
- `_on_companion_satellite_navigation_requested(self, direction: str) -> None` [method] (pyssp/ui/main_window/companion_satellite.py:827)
