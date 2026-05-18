# `pyssp/ui/main_window/remote_api.py`

- Source: `pyssp/ui/main_window/remote_api.py`
- Module path: `pyssp.ui.main_window.remote_api`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `RemoteApiMixin`

- Defined at `pyssp/ui/main_window/remote_api.py:16`

#### Internal Members

- `_execute_internal_automation_spec(self, spec: Optional[AutomationCommandSpec]) -> bool` [method] (pyssp/ui/main_window/remote_api.py:17)
- `_api_success(self, result: Optional[dict] = None, status: int = 200) -> dict` [method] (pyssp/ui/main_window/remote_api.py:38)
- `_api_error(self, code: str, message: str, status: int = 400) -> dict` [method] (pyssp/ui/main_window/remote_api.py:41)
- `_parse_api_mode(self, raw: str) -> Optional[str]` [method] (pyssp/ui/main_window/remote_api.py:44)
- `_parse_lyric_display_mode(self, raw: str) -> Optional[str]` [method] (pyssp/ui/main_window/remote_api.py:54)
- `_parse_api_bool(raw: object) -> Optional[bool]` [staticmethod] (pyssp/ui/main_window/remote_api.py:65)
- `_parse_button_id(self, raw: str, require_slot: bool) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[dict]]` [method] (pyssp/ui/main_window/remote_api.py:75)
- `_slot_for_location(self, group: str, page_index: int, slot_index: int) -> SoundButtonData` [method] (pyssp/ui/main_window/remote_api.py:120)
- `_api_slot_state(self, group: str, page_index: int, slot_index: int) -> dict` [method] (pyssp/ui/main_window/remote_api.py:125)
- `_api_page_state(self, group: str, page_index: int) -> dict` [method] (pyssp/ui/main_window/remote_api.py:149)
- `_api_page_buttons(self, group: str, page_index: int) -> List[dict]` [method] (pyssp/ui/main_window/remote_api.py:179)
- `_slot_for_key(self, slot_key: Tuple[str, int, int]) -> Optional[SoundButtonData]` [method] (pyssp/ui/main_window/remote_api.py:216)
- `_api_player_state_name(self, player: ExternalMediaPlayer) -> str` [method] (pyssp/ui/main_window/remote_api.py:232)
- `_api_playing_tracks(self) -> List[dict]` [method] (pyssp/ui/main_window/remote_api.py:240)
- `_api_state(self) -> dict` [method] (pyssp/ui/main_window/remote_api.py:280)
- `_api_primary_playing_key(self) -> Optional[Tuple[str, int, int]]` [method] (pyssp/ui/main_window/remote_api.py:313)
- `_api_lyric_openlp(self) -> dict` [method] (pyssp/ui/main_window/remote_api.py:318)
- `_resolve_local_ip(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:435)
- `_web_remote_http_open_url(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:496)
- `_web_remote_https_open_url(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:500)
- `_web_remote_open_url(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:504)
- `_preferred_web_remote_ws_port(self) -> int` [method] (pyssp/ui/main_window/remote_api.py:509)
- `_api_select_location(self, group: str, page_index: Optional[int]) -> None` [method] (pyssp/ui/main_window/remote_api.py:514)
- `_reset_current_page_state_no_prompt(self) -> None` [method] (pyssp/ui/main_window/remote_api.py:531)
- `_force_stop_playback(self) -> None` [method] (pyssp/ui/main_window/remote_api.py:541)
- `_apply_web_remote_state(self) -> None` [method] (pyssp/ui/main_window/remote_api.py:559)
- `_start_web_remote_service(self) -> None` [method] (pyssp/ui/main_window/remote_api.py:574)
- `_is_web_remote_port_conflict(exc: Exception) -> bool` [staticmethod] (pyssp/ui/main_window/remote_api.py:623)
- `_is_port_listening_by_other_process(port: int) -> bool` [staticmethod] (pyssp/ui/main_window/remote_api.py:637)
- `_update_web_remote_status_label(self) -> None` [method] (pyssp/ui/main_window/remote_api.py:666)
- `_stop_web_remote_service(self) -> None` [method] (pyssp/ui/main_window/remote_api.py:670)
- `_set_web_remote_warning_banner(self, text: str) -> None` [method] (pyssp/ui/main_window/remote_api.py:682)
- `_show_midi_connection_warning_banner(self, text: str, timeout_ms: int = 0) -> None` [method] (pyssp/ui/main_window/remote_api.py:687)
- `_debug_midi_connection(self, text: str) -> None` [method] (pyssp/ui/main_window/remote_api.py:696)
- `_hide_midi_connection_warning_banner(self, token: Optional[int] = None) -> None` [method] (pyssp/ui/main_window/remote_api.py:699)
- `_refresh_midi_connection_warning(self, force_refresh: bool = False) -> None` [method] (pyssp/ui/main_window/remote_api.py:705)
- `_web_remote_port_conflict_text(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:784)
- `_web_remote_ws_port_conflict_text(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:791)
- `_web_remote_https_port_conflict_text(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:798)
- `_web_remote_wss_port_conflict_text(self) -> str` [method] (pyssp/ui/main_window/remote_api.py:805)
- `_dispatch_web_remote_command_threadsafe(self, command: str, params: dict) -> dict` [method] (pyssp/ui/main_window/remote_api.py:812)
- `_handle_web_remote_command(self, command: str, params: dict) -> dict` [method] (pyssp/ui/main_window/remote_api.py:820)
