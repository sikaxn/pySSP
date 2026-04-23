from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class RemoteApiMixin:
    def _api_success(self, result: Optional[dict] = None, status: int = 200) -> dict:
        return {"ok": True, "status": status, "result": result or {}}

    def _api_error(self, code: str, message: str, status: int = 400) -> dict:
        return {"ok": False, "status": status, "error": {"code": code, "message": message}}

    def _parse_api_mode(self, raw: str) -> Optional[str]:
        value = str(raw or "").strip().lower()
        if value in {"enable", "on", "true", "1"}:
            return "enable"
        if value in {"disable", "off", "false", "0"}:
            return "disable"
        if value in {"toggle", "flip"}:
            return "toggle"
        return None

    def _parse_lyric_display_mode(self, raw: str) -> Optional[str]:
        value = str(raw or "").strip().lower()
        if value in {"show", "enable", "on", "true", "1"}:
            return "show"
        if value in {"blank", "hide", "disable", "off", "false", "0"}:
            return "blank"
        if value in {"toggle", "flip"}:
            return "toggle"
        return None

    @staticmethod
    def _parse_api_bool(raw: object) -> Optional[bool]:
        if isinstance(raw, bool):
            return raw
        value = str(raw or "").strip().lower()
        if value in {"1", "true", "on", "yes"}:
            return True
        if value in {"0", "false", "off", "no"}:
            return False
        return None

    def _parse_button_id(self, raw: str, require_slot: bool) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[dict]]:
        parts = [segment for segment in str(raw or "").strip().split("-") if segment]
        if not parts:
            return None, None, None, self._api_error("invalid_id", "Missing target id.")
        if len(parts) > 3:
            return None, None, None, self._api_error("invalid_id", "Target id can be group, group-page, or group-page-button.")

        group = parts[0].upper()
        if group not in GROUPS and group != "Q":
            return None, None, None, self._api_error("invalid_group", f"Unknown group '{parts[0]}'.")

        page_index: Optional[int] = None
        slot_index: Optional[int] = None
        if len(parts) >= 2:
            try:
                page_number = int(parts[1])
            except ValueError:
                return None, None, None, self._api_error("invalid_page", f"Invalid page value '{parts[1]}'.")
            if group == "Q":
                if page_number != 1:
                    return None, None, None, self._api_error("invalid_page", "Cue group only supports page 1.")
                page_index = 0
            else:
                if page_number < 1 or page_number > PAGE_COUNT:
                    return None, None, None, self._api_error("invalid_page", f"Page must be 1..{PAGE_COUNT}.")
                page_index = page_number - 1
        elif group == "Q":
            page_index = 0

        if len(parts) == 3:
            try:
                slot_number = int(parts[2])
            except ValueError:
                return None, None, None, self._api_error("invalid_button", f"Invalid button value '{parts[2]}'.")
            if slot_number < 1 or slot_number > SLOTS_PER_PAGE:
                return None, None, None, self._api_error("invalid_button", f"Button must be 1..{SLOTS_PER_PAGE}.")
            slot_index = slot_number - 1

        if require_slot and (page_index is None or slot_index is None):
            return None, None, None, self._api_error(
                "invalid_id",
                "This endpoint requires group-page-button format, e.g. a-1-1.",
            )
        return group, page_index, slot_index, None

    def _slot_for_location(self, group: str, page_index: int, slot_index: int) -> SoundButtonData:
        if group == "Q":
            return self.cue_page[slot_index]
        return self.data[group][page_index][slot_index]

    def _api_slot_state(self, group: str, page_index: int, slot_index: int) -> dict:
        slot = self._slot_for_location(group, page_index, slot_index)
        key = (group, page_index, slot_index)
        return {
            "button_id": self._format_button_key(key).lower(),
            "group": group,
            "page": page_index + 1,
            "button": slot_index + 1,
            "title": slot.title,
            "file_path": slot.file_path,
            "assigned": slot.assigned,
            "locked": slot.locked,
            "marker": slot.marker,
            "missing": slot.missing,
            "played": slot.played,
            "highlighted": slot.highlighted,
            "is_playing": key in self._active_playing_keys,
        }

    def _api_page_state(self, group: str, page_index: int) -> dict:
        page = self.cue_page if group == "Q" else self.data[group][page_index]
        assigned = sum(1 for slot in page if slot.assigned and not slot.marker)
        played = sum(1 for slot in page if slot.assigned and not slot.marker and slot.played)
        playable = sum(1 for slot in page if slot.assigned and not slot.marker and not slot.locked and not slot.missing)
        if group == "Q":
            page_name = "Cue Page"
            page_color = None
        else:
            page_name = self.page_names[group][page_index].strip()
            page_color = self.page_colors[group][page_index]
        if group == "Q":
            playlist_enabled = False
            shuffle_enabled = False
        else:
            playlist_enabled = self.page_playlist_enabled[group][page_index]
            shuffle_enabled = self.page_shuffle_enabled[group][page_index]
        return {
            "group": group,
            "page": page_index + 1,
            "page_name": page_name,
            "page_color": page_color,
            "assigned_count": assigned,
            "played_count": played,
            "playable_count": playable,
            "playlist_enabled": playlist_enabled,
            "shuffle_enabled": shuffle_enabled,
            "is_current": (self._view_group_key() == group and self.current_page == page_index),
        }

    def _api_page_buttons(self, group: str, page_index: int) -> List[dict]:
        page = self.cue_page if group == "Q" else self.data[group][page_index]
        output: List[dict] = []
        for idx, slot in enumerate(page):
            key = (group, page_index, idx)
            marker_text = slot.title.strip() if slot.marker else ""
            if slot.marker:
                display_title = marker_text
            elif slot.assigned:
                display_title = self._build_now_playing_text(slot)
            else:
                display_title = ""
            output.append(
                {
                    "button_id": self._format_button_key(key).lower(),
                    "button": idx + 1,
                    "row": (idx // GRID_COLS) + 1,
                    "col": (idx % GRID_COLS) + 1,
                    "title": display_title,
                    "marker_text": marker_text,
                    "assigned": slot.assigned,
                    "locked": slot.locked,
                    "marker": slot.marker,
                    "missing": slot.missing,
                    "played": slot.played,
                    "is_playing": key in self._active_playing_keys,
                }
            )
        return output

    def _slot_for_key(self, slot_key: Tuple[str, int, int]) -> Optional[SoundButtonData]:
        group, page_index, slot_index = slot_key
        if slot_index < 0 or slot_index >= SLOTS_PER_PAGE:
            return None
        if group == "Q":
            return self.cue_page[slot_index]
        if group not in self.data:
            return None
        if page_index < 0 or page_index >= PAGE_COUNT:
            return None
        return self.data[group][page_index][slot_index]

    def _api_player_state_name(self, player: ExternalMediaPlayer) -> str:
        state = player.state()
        if state == ExternalMediaPlayer.PlayingState:
            return "playing"
        if state == ExternalMediaPlayer.PausedState:
            return "paused"
        return "stopped"

    def _api_playing_tracks(self) -> List[dict]:
        tracks: List[dict] = []
        for player in [self.player, self.player_b, *self._multi_players]:
            player_state = player.state()
            if player_state not in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                continue
            slot_key = self._player_slot_key_map.get(id(player))
            if slot_key is None:
                continue
            slot = self._slot_for_key(slot_key)
            if slot is None:
                continue
            duration_ms = max(0, int(player.duration()))
            position_ms = max(0, int(player.position()))
            remaining_ms = max(0, duration_ms - position_ms)
            tracks.append(
                {
                    "button_id": self._format_button_key(slot_key).lower(),
                    "title": self._build_now_playing_text(slot),
                    "file_path": slot.file_path,
                    "group": slot_key[0],
                    "page": slot_key[1] + 1,
                    "button": slot_key[2] + 1,
                    "state": self._api_player_state_name(player),
                    "position_ms": position_ms,
                    "duration_ms": duration_ms,
                    "remaining_ms": remaining_ms,
                    "position": format_clock_time(position_ms),
                    "duration": format_clock_time(duration_ms),
                    "remaining": format_clock_time(remaining_ms),
                }
            )
        tracks.sort(key=lambda item: item["button_id"])
        return tracks

    def _api_state(self) -> dict:
        current_group = self._view_group_key()
        current_page = self.current_page
        playing_tracks = self._api_playing_tracks()
        return {
            "current_group": current_group,
            "current_page": current_page + 1,
            "cue_mode": self.cue_mode,
            "talk_active": self.talk_active,
            "vocal_removed_active": bool(self.play_vocal_removed_tracks),
            "multi_play_enabled": self._is_multi_play_enabled(),
            "fade_in_enabled": self._is_fade_in_enabled(),
            "fade_out_enabled": self._is_fade_out_enabled(),
            "crossfade_enabled": self._is_cross_fade_enabled(),
            "playlist_enabled": False if self.cue_mode else self.page_playlist_enabled[self.current_group][self.current_page],
            "shuffle_enabled": False if self.cue_mode else self.page_shuffle_enabled[self.current_group][self.current_page],
            "is_playing": bool(self._all_active_players()),
            "screen_locked": bool(self._ui_locked),
            "automation_locked": bool(self._automation_locked),
            "playing_buttons": [self._format_button_key(k).lower() for k in sorted(self._active_playing_keys)],
            "current_playing": self._format_button_key(self.current_playing).lower() if self.current_playing else None,
            "playing_tracks": playing_tracks,
            "web_remote_url": self._web_remote_open_url(),
            "lyric_display": "blank" if self._lyric_force_blank else "show",
        }

    def _api_primary_playing_key(self) -> Optional[Tuple[str, int, int]]:
        if self.current_playing is not None:
            return self.current_playing
        return self._newest_active_playing_key()

    def _api_lyric_openlp(self) -> dict:
        slot_key = self._api_primary_playing_key()
        slides: List[dict] = []
        current_slide_index = 0
        item_id = ""
        service_id = ""
        current_title = ""
        current_notes = ""

        if slot_key is not None:
            slot = self._slot_for_key(slot_key)
            if slot is not None:
                item_id = self._format_button_key(slot_key).lower()
                current_title = self._build_now_playing_text(slot)
                current_notes = str(slot.notes or "")
                lyric_path = str(slot.lyric_file or "").strip()
                if lyric_path:
                    lines, error = self._load_stage_lyric_lines(lyric_path)
                    if not error and lines:
                        position_ms = self._lyric_position_ms_for_key(slot_key)
                        first_line_start_ms = max(0, int(lines[0].start_ms))
                        if first_line_start_ms > 0:
                            slides.append(
                                {
                                    "title": current_title,
                                    "text": "\u200b",
                                    "html": "&#8203;",
                                    "img": "",
                                    "tag": "L0",
                                    "selected": False,
                                }
                            )
                        for idx, line in enumerate(lines):
                            if line.start_ms <= position_ms:
                                current_slide_index = len(slides)
                            text_value = str(line.text or "")
                            html_value = "<br />".join(html.escape(part) for part in text_value.splitlines())
                            slides.append(
                                {
                                    "title": current_title,
                                    "text": text_value,
                                    "html": html_value,
                                    "img": "",
                                    "tag": f"L{idx + 1}",
                                    "selected": False,
                                }
                            )
                        if slides:
                            current_slide_index = max(0, min(current_slide_index, len(slides) - 1))
                            slides[current_slide_index]["selected"] = True
                if not slides:
                    slides.append(
                        {
                            "title": current_title,
                            "text": "\u200b",
                            "html": "&#8203;",
                            "img": "",
                            "tag": "L0",
                            "selected": True,
                        }
                    )
                    current_slide_index = 0
        else:
            current_title = tr("no song is playing")
            slides.append(
                {
                    "title": current_title,
                    "text": "\u200b",
                    "html": "&#8203;",
                    "img": "",
                    "tag": "L0",
                    "selected": True,
                }
            )
            current_slide_index = 0
        if not slides:
            slides.append(
                {
                    "title": current_title,
                    "text": "\u200b",
                    "html": "&#8203;",
                    "img": "",
                    "tag": "L0",
                    "selected": True,
                }
            )
            current_slide_index = 0

        next_song = self._next_stage_song_name()
        next_title = "" if next_song == "-" else str(next_song or "").strip()
        service_items: List[dict] = []
        if current_title:
            service_items.append({"title": current_title, "notes": current_notes, "selected": True})
        if next_title:
            service_items.append({"title": next_title, "notes": "", "selected": False})
        service_id = "|".join([item_id, current_title, next_title])

        blank = bool(self._lyric_force_blank)
        display = "blank" if blank else "show"

        return {
            "ws": {
                "item": item_id,
                "service": service_id,
                "slide": int(current_slide_index),
                "twelve": False,
                "display": display,
                "blank": bool(blank),
                "theme": False,
            },
            "live_items": {
                "item": item_id,
                "slides": slides,
            },
            "service_items": service_items,
        }

    def _resolve_local_ip(self) -> str:
        now = time.perf_counter()
        if (now - float(self._local_ip_cache_at)) < 10.0 and self._local_ip_cache:
            return self._local_ip_cache

        candidates: List[str] = []

        # Fast path: no external process; UDP connect does not send packets.
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(("8.8.8.8", 80))
                value = sock.getsockname()[0]
                if value:
                    candidates.append(value)
            finally:
                sock.close()
        except Exception:
            pass

        # Fallback: local resolver, still offline-safe.
        try:
            infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
            for info in infos:
                value = info[4][0]
                if value:
                    candidates.append(value)
        except Exception:
            pass

        resolved = "127.0.0.1"
        seen = set()
        filtered: List[str] = []
        for value in candidates:
            if value in seen:
                continue
            seen.add(value)
            try:
                ip = ipaddress.ip_address(value)
                if not isinstance(ip, ipaddress.IPv4Address):
                    continue
                if ip.is_loopback or ip.is_link_local:
                    continue
                filtered.append(value)
            except ValueError:
                continue

        for value in filtered:
            try:
                if ipaddress.ip_address(value).is_private:
                    resolved = value
                    break
            except ValueError:
                continue
        if resolved == "127.0.0.1" and filtered:
            resolved = filtered[0]

        self._local_ip_cache = resolved
        self._local_ip_cache_at = now
        return resolved

    def _web_remote_open_url(self) -> str:
        host = self._resolve_local_ip()
        return f"http://{host}:{self.web_remote_port}/"

    def _api_select_location(self, group: str, page_index: Optional[int]) -> None:
        if group == "Q":
            if not self.cue_mode:
                self._toggle_cue_mode(True)
            self.current_page = 0
            self._refresh_page_list()
            self._refresh_sound_grid()
            self._update_group_status()
            self._update_page_status()
            return
        if self.cue_mode:
            self._toggle_cue_mode(False)
        if self.current_group != group:
            self._select_group(group)
        if page_index is not None and self.current_page != page_index:
            self._select_page(page_index)

    def _reset_current_page_state_no_prompt(self) -> None:
        page = self._current_page_slots()
        for slot in page:
            slot.played = False
            if slot.assigned:
                slot.activity_code = "8"
        self.current_playlist_start = None
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _force_stop_playback(self) -> None:
        self._manual_stop_requested = True
        self._stop_fade_armed = False
        self._hard_stop_all()
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
        self._update_pause_button_label()

    def _apply_web_remote_state(self) -> None:
        self.web_remote_ws_port = int(self.web_remote_port) + 1
        if not self.web_remote_enabled:
            self._stop_web_remote_service()
            self._update_web_remote_status_label()
            return
        if self._web_remote_server is not None and self._web_remote_server.is_running:
            same_host = self._web_remote_server.host == self.web_remote_host
            same_port = int(self._web_remote_server.port) == int(self.web_remote_port)
            same_ws_port = int(self._web_remote_server.ws_port) == int(self.web_remote_ws_port)
            if same_host and same_port and same_ws_port:
                self._update_web_remote_status_label()
                return
            self._stop_web_remote_service()
        self._start_web_remote_service()
        self._update_web_remote_status_label()

    def _start_web_remote_service(self) -> None:
        if self._web_remote_server is not None and self._web_remote_server.is_running:
            self._set_web_remote_warning_banner("")
            return
        if self._is_port_listening_by_other_process(self.web_remote_port):
            self._set_web_remote_warning_banner(self._web_remote_port_conflict_text())
            return
        self.web_remote_ws_port = int(self.web_remote_port) + 1
        if self._is_port_listening_by_other_process(self.web_remote_ws_port):
            self._set_web_remote_warning_banner(self._web_remote_ws_port_conflict_text())
            return
        try:
            self._web_remote_server = WebRemoteServer(
                dispatch=self._dispatch_web_remote_command_threadsafe,
                host=self.web_remote_host,
                port=self.web_remote_port,
                ws_port=self.web_remote_ws_port,
            )
            self._web_remote_server.start()
            self._set_web_remote_warning_banner("")
            self._update_web_remote_status_label()
        except Exception as exc:
            self._stop_web_remote_service()
            self._web_remote_server = None
            self._update_web_remote_status_label()
            if self._is_web_remote_port_conflict(exc):
                self._set_web_remote_warning_banner(self._web_remote_port_conflict_text())
                return
            self._set_web_remote_warning_banner(
                f"{tr('WEB REMOTE ERROR: Could not start Web Remote service.')} {exc}"
            )

    @staticmethod
    def _is_web_remote_port_conflict(exc: Exception) -> bool:
        if isinstance(exc, OSError):
            if getattr(exc, "errno", None) in {48, 98, 10048}:
                return True
            if getattr(exc, "winerror", None) == 10048:
                return True
        message = str(exc).lower()
        return (
            "address already in use" in message
            or "only one usage of each socket address" in message
            or "winerror 10048" in message
        )

    @staticmethod
    def _is_port_listening_by_other_process(port: int) -> bool:
        try:
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        except Exception:
            return False
        pid_self = str(os.getpid())
        port_token = f":{int(port)}"
        for line in (result.stdout or "").splitlines():
            row = line.strip()
            if not row:
                continue
            parts = re.split(r"\s+", row)
            if len(parts) < 5:
                continue
            proto, local_addr, _foreign, state, pid = parts[0], parts[1], parts[2], parts[3], parts[4]
            if proto.upper() != "TCP" or state.upper() != "LISTENING":
                continue
            if not local_addr.endswith(port_token):
                continue
            if pid != pid_self:
                return True
        return False

    def _update_web_remote_status_label(self) -> None:
        state = "Enabled" if self.web_remote_enabled else "Disabled"
        self.web_remote_status_label.setText(f"{tr('Web Remote is ')}{tr(state)}")

    def _stop_web_remote_service(self) -> None:
        server = self._web_remote_server
        self._web_remote_server = None
        if not self.web_remote_enabled:
            self._set_web_remote_warning_banner("")
        if server is None:
            return
        try:
            server.stop()
        except Exception:
            pass

    def _set_web_remote_warning_banner(self, text: str) -> None:
        message = str(text or "").strip()
        self.web_remote_warning_banner.setText(message)
        self.web_remote_warning_banner.setVisible(bool(message))

    def _show_midi_connection_warning_banner(self, text: str, timeout_ms: int = 0) -> None:
        message = str(text or "").strip()
        self._midi_connection_warning_token += 1
        token = self._midi_connection_warning_token
        self.midi_connection_warning_banner.setText(message)
        self.midi_connection_warning_banner.setVisible(bool(message))
        if message and timeout_ms > 0:
            QTimer.singleShot(timeout_ms, lambda t=token: self._hide_midi_connection_warning_banner(t))

    def _debug_midi_connection(self, text: str) -> None:
        print(f"[MIDI-CONNECTION] {str(text or '').strip()}", flush=True)

    def _hide_midi_connection_warning_banner(self, token: Optional[int] = None) -> None:
        if token is not None and token != self._midi_connection_warning_token:
            return
        self.midi_connection_warning_banner.setVisible(False)
        self.midi_connection_warning_banner.setText("")

    def _refresh_midi_connection_warning(self, force_refresh: bool = False) -> None:
        previous_missing = set(self._midi_missing_selectors)
        previous_launchpad_missing = set(getattr(self, "_launchpad_missing_selectors", set()))
        previous_launchpad_output_missing = bool(getattr(self, "_launchpad_output_missing", False))
        selected = [str(v).strip() for v in self.midi_input_device_ids if str(v).strip()]
        missing_selectors = set(self._midi_missing_selectors) if selected else set()
        self._midi_missing_selectors = missing_selectors

        launchpad_selector = str(getattr(self, "launchpad_device_selector", "") or "").strip()
        if bool(getattr(self, "launchpad_enabled", False)) and launchpad_selector:
            launchpad_missing = set(self._launchpad_missing_selectors)
        else:
            launchpad_missing = set()
        self._launchpad_missing_selectors = launchpad_missing

        launchpad_output_missing = False
        launchpad_output_id = str(getattr(self, "launchpad_output_device_id", "") or "").strip()
        if bool(getattr(self, "launchpad_enabled", False)) and launchpad_output_id:
            launchpad_output_missing = True
            for device_id, _device_name in list_midi_output_devices():
                if str(device_id).strip() == launchpad_output_id:
                    launchpad_output_missing = False
                    break
        self._launchpad_output_missing = launchpad_output_missing

        if not missing_selectors and not launchpad_missing and not launchpad_output_missing:
            recovered_parts = []
            if previous_missing:
                recovered_labels = [midi_input_selector_name(v) or str(v) for v in sorted(previous_missing) if str(v).strip()]
                display = ", ".join(recovered_labels[:3])
                if len(recovered_labels) > 3:
                    display += f" (+{len(recovered_labels) - 3} more)"
                recovered_parts.append(f"{tr('MIDI input reconnected:')} {display}")
            if previous_launchpad_missing:
                recovered_labels = [midi_input_selector_name(v) or str(v) for v in sorted(previous_launchpad_missing) if str(v).strip()]
                display = ", ".join(recovered_labels[:3])
                if len(recovered_labels) > 3:
                    display += f" (+{len(recovered_labels) - 3} more)"
                recovered_parts.append(f"{tr('Launchpad input reconnected:')} {display}")
            if previous_launchpad_output_missing and launchpad_output_id:
                recovered_parts.append(f"{tr('Launchpad output reconnected:')} {launchpad_output_id}")
            if recovered_parts:
                message = ". ".join(part for part in recovered_parts if part)
                self._debug_midi_connection(f"reconnected={message or '<none>'}")
                self._show_midi_connection_warning_banner(
                    f"{message}. {tr('MIDI control restored.')}",
                    timeout_ms=4500,
                )
            else:
                self._hide_midi_connection_warning_banner()
            return

        problem_parts = []
        if missing_selectors:
            current_labels = [midi_input_selector_name(v) or str(v) for v in sorted(missing_selectors)]
            display = ", ".join(current_labels[:3])
            if len(current_labels) > 3:
                display += f" (+{len(current_labels) - 3} more)"
            problem_parts.append(f"{tr('MIDI input disconnected:')} {display}")
        if launchpad_missing:
            current_labels = [midi_input_selector_name(v) or str(v) for v in sorted(launchpad_missing)]
            display = ", ".join(current_labels[:3])
            if len(current_labels) > 3:
                display += f" (+{len(current_labels) - 3} more)"
            problem_parts.append(f"{tr('Launchpad input disconnected:')} {display}")
        if launchpad_output_missing and launchpad_output_id:
            problem_parts.append(f"{tr('Launchpad output disconnected:')} {launchpad_output_id}")
        message = ". ".join(problem_parts)
        if (
            missing_selectors != previous_missing
            or launchpad_missing != previous_launchpad_missing
            or launchpad_output_missing != previous_launchpad_output_missing
        ):
            self._debug_midi_connection(f"disconnected={message or '<none>'}")
        self._show_midi_connection_warning_banner(
            f"{message}. {tr('MIDI control will resume automatically when reconnected.')}",
            timeout_ms=0,
        )

    def _web_remote_port_conflict_text(self) -> str:
        return (
            f"{tr('WEB REMOTE PORT CONFLICT:')} {tr('Port')} {self.web_remote_port} {tr('is already in use.')}\n"
            f"{tr('Change port, disable Web Remote, or close the program using this port.')}\n"
            f"{tr('Restart pySSP to resolve the issue.')}"
        )

    def _web_remote_ws_port_conflict_text(self) -> str:
        return (
            f"{tr('WEB REMOTE WS PORT CONFLICT:')} {tr('Port')} {self.web_remote_ws_port} {tr('is already in use.')}\n"
            f"{tr('Change WS Port, disable Web Remote, or close the program using this port.')}\n"
            f"{tr('Restart pySSP to resolve the issue.')}"
        )

    def _dispatch_web_remote_command_threadsafe(self, command: str, params: dict) -> dict:
        try:
            return self._main_thread_executor.call(lambda: self._handle_web_remote_command(command, params))
        except queue.Empty:
            return self._api_error("timeout", "Timed out waiting for UI thread.", status=504)
        except Exception as exc:
            return self._api_error("internal_error", str(exc), status=500)

    def _handle_web_remote_command(self, command: str, params: dict) -> dict:
        cmd = str(command or "").strip().lower()
        if cmd == "health":
            return self._api_success({"service": "web-remote", "state": self._api_state()})
        if cmd == "query_all":
            return self._api_success(self._api_state())
        if cmd == "query_button":
            group, page_index, slot_index, error = self._parse_button_id(params.get("button_id", ""), require_slot=True)
            if error:
                return error
            return self._api_success(self._api_slot_state(group, page_index, slot_index))
        if cmd == "query_pagegroup":
            group = str(params.get("group_id", "")).strip().upper()
            if group not in GROUPS and group != "Q":
                return self._api_error("invalid_group", f"Unknown group '{group}'.")
            if group == "Q":
                return self._api_success({"group": "Q", "pages": [self._api_page_state("Q", 0)]})
            pages = [self._api_page_state(group, idx) for idx in range(PAGE_COUNT)]
            return self._api_success({"group": group, "pages": pages})
        if cmd == "query_page":
            group, page_index, _slot_index, error = self._parse_button_id(params.get("page_id", ""), require_slot=False)
            if error:
                return error
            if page_index is None:
                return self._api_error("invalid_page", "Page query requires group-page format, e.g. a-1.")
            page = self._api_page_state(group, page_index)
            page["buttons"] = self._api_page_buttons(group, page_index)
            return self._api_success(page)
        if cmd == "query_lyric_openlp":
            return self._api_success(self._api_lyric_openlp())
        if cmd == "lyric_display":
            mode = self._parse_lyric_display_mode(params.get("mode", ""))
            if mode is None:
                return self._api_error("invalid_mode", "Mode must be show, blank, or toggle.")
            if mode == "toggle":
                self._set_lyric_force_blank(not self._lyric_force_blank)
            else:
                self._set_lyric_force_blank(mode == "blank")
            return self._api_success(
                {
                    "lyric_display": "blank" if self._lyric_force_blank else "show",
                    "state": self._api_state(),
                }
            )
        if cmd == "vocal_removed":
            mode = self._parse_api_mode(params.get("mode", ""))
            if mode is None:
                return self._api_error("invalid_mode", "Mode must be enable, disable, or toggle.")
            current = bool(self.play_vocal_removed_tracks)
            new_value = (not current) if mode == "toggle" else (mode == "enable")
            self._toggle_global_vocal_removed_mode(new_value)
            return self._api_success(
                {
                    "vocal_removed_active": bool(self.play_vocal_removed_tracks),
                    "state": self._api_state(),
                }
            )
        if cmd == "lock":
            self._engage_lock_screen()
            return self._api_success({"screen_locked": True, "automation_locked": False, "state": self._api_state()})
        if cmd == "automation_lock":
            self._engage_lock_screen(automation=True)
            return self._api_success({"screen_locked": True, "automation_locked": True, "state": self._api_state()})
        if cmd == "unlock":
            self._release_lock_screen(force=True)
            return self._api_success({"screen_locked": False, "automation_locked": False, "state": self._api_state()})

        if cmd == "goto":
            group, page_index, slot_index, error = self._parse_button_id(params.get("target", ""), require_slot=False)
            if error:
                return error
            self._api_select_location(group, page_index)
            if slot_index is not None:
                self.sound_buttons[slot_index].setFocus()
                self._on_sound_button_hover(slot_index)
            return self._api_success({"state": self._api_state()})

        if cmd == "play":
            group, page_index, slot_index, error = self._parse_button_id(params.get("button_id", ""), require_slot=True)
            if error:
                return error
            self._api_select_location(group, page_index)
            slot = self._slot_for_location(group, page_index, slot_index)
            if slot.locked:
                return self._api_error("locked", "Button is locked.", status=409)
            if slot.marker:
                return self._api_error("marker", "Button is a marker and cannot be played.", status=409)
            if not slot.assigned:
                return self._api_error("empty", "Button has no assigned sound.", status=409)
            if slot.missing:
                return self._api_error("missing", "Sound file is missing.", status=409)
            self._play_slot(slot_index)
            pending = self._pending_start_request == (group, page_index, slot_index)
            return self._api_success(
                {
                    "button": self._api_slot_state(group, page_index, slot_index),
                    "pending_start": pending,
                    "state": self._api_state(),
                }
            )

        if cmd == "pause":
            players = self._all_active_players()
            if (not players) and self._pending_deferred_audio_request is not None:
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
                return self._api_success({"deferred_load_canceled": True, "state": self._api_state()})
            if not players:
                return self._api_error("not_playing", "No active playback to pause.", status=409)
            changed = False
            for player in players:
                if player.state() == ExternalMediaPlayer.PlayingState:
                    player.pause()
                    changed = True
            if not changed:
                return self._api_error("already_paused", "Playback is already paused.", status=409)
            self._update_pause_button_label()
            return self._api_success({"state": self._api_state()})

        if cmd == "resume":
            players = self._all_active_players()
            if not players:
                return self._api_error("not_paused", "No paused playback to resume.", status=409)
            changed = False
            for player in players:
                if player.state() == ExternalMediaPlayer.PausedState:
                    player.play()
                    changed = True
            if not changed:
                return self._api_error("already_playing", "Playback is already playing.", status=409)
            self._update_pause_button_label()
            return self._api_success({"state": self._api_state()})

        if cmd == "stop":
            self._stop_playback()
            return self._api_success({"state": self._api_state()})

        if cmd == "forcestop":
            self._force_stop_playback()
            return self._api_success({"state": self._api_state()})

        if cmd == "rapidfire":
            blocked: set[int] = set()
            while True:
                if self.rapid_fire_play_mode == "any_available":
                    slot_index = self._random_available_slot_on_current_page(blocked=blocked)
                else:
                    slot_index = self._random_unplayed_slot_on_current_page(blocked=blocked)
                if slot_index is None:
                    return self._api_error("no_candidate", "No playable button is available on the current page.", status=409)
                if self._play_slot(slot_index):
                    key = (self._view_group_key(), self.current_page, slot_index)
                    return self._api_success({"button": self._api_slot_state(*key), "state": self._api_state()})
                blocked.add(slot_index)
                if self.candidate_error_action == "stop_playback":
                    self._stop_playback()
                    return self._api_error("audio_load_failed", "Playback stopped due to audio load error.", status=409)

        if cmd == "playnext":
            if not self._all_active_players():
                return self._api_error("not_playing", "Cannot play next when nothing is currently playing.", status=409)
            playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
            blocked: set[int] = set()
            while True:
                if playlist_enabled:
                    next_slot = self._next_playlist_slot(for_auto_advance=False, blocked=blocked)
                else:
                    if self.next_play_mode == "any_available":
                        next_slot = self._next_available_slot_on_current_page(blocked=blocked)
                    else:
                        next_slot = self._next_unplayed_slot_on_current_page(blocked=blocked)
                if next_slot is None:
                    return self._api_error("no_next", "No next track is available.", status=409)
                if self._play_slot(next_slot):
                    return self._api_success({"state": self._api_state()})
                blocked.add(next_slot)
                if self.candidate_error_action == "stop_playback":
                    self._stop_playback()
                    return self._api_error("audio_load_failed", "Playback stopped due to audio load error.", status=409)

        if cmd in {"talk", "playlist", "playlist_shuffle", "multiplay"}:
            mode = self._parse_api_mode(params.get("mode", ""))
            if mode is None:
                return self._api_error("invalid_mode", "Mode must be enable, disable, or toggle.")
            if cmd == "talk":
                new_value = (not self.talk_active) if mode == "toggle" else (mode == "enable")
                self._toggle_talk(new_value)
                return self._api_success({"talk_active": self.talk_active, "state": self._api_state()})
            if cmd == "playlist":
                if self.cue_mode and mode == "enable":
                    return self._api_error("invalid_state", "Playlist cannot be enabled in Cue mode.", status=409)
                current = self.page_playlist_enabled[self.current_group][self.current_page]
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_playlist_mode(new_value)
                actual = self.page_playlist_enabled[self.current_group][self.current_page] if not self.cue_mode else False
                return self._api_success({"playlist_enabled": actual, "state": self._api_state()})
            if cmd == "playlist_shuffle":
                if not self.page_playlist_enabled[self.current_group][self.current_page]:
                    return self._api_error("playlist_required", "Enable playlist mode before shuffle.", status=409)
                current = self.page_shuffle_enabled[self.current_group][self.current_page]
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_shuffle_mode(new_value)
                return self._api_success(
                    {"shuffle_enabled": self.page_shuffle_enabled[self.current_group][self.current_page], "state": self._api_state()}
                )
            if cmd == "multiplay":
                current = self._is_multi_play_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_multi_play_mode(new_value)
                return self._api_success({"multi_play_enabled": self._is_multi_play_enabled(), "state": self._api_state()})

        if cmd == "fade":
            kind = str(params.get("kind", "")).strip().lower()
            mode = self._parse_api_mode(params.get("mode", ""))
            if mode is None:
                return self._api_error("invalid_mode", "Mode must be enable, disable, or toggle.")
            if kind == "fadein":
                current = self._is_fade_in_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_fade_in_mode(new_value)
            elif kind == "fadeout":
                current = self._is_fade_out_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_fade_out_mode(new_value)
            elif kind == "crossfade":
                current = self._is_cross_fade_enabled()
                new_value = (not current) if mode == "toggle" else (mode == "enable")
                self._toggle_cross_auto_mode(new_value)
            else:
                return self._api_error("invalid_fade", "Fade type must be fadein, fadeout, or crossfade.")
            return self._api_success({"state": self._api_state()})

        if cmd == "resetpage":
            scope = str(params.get("scope", "")).strip().lower()
            if scope == "current":
                self._stop_playback()
                self._reset_current_page_state_no_prompt()
                return self._api_success({"state": self._api_state()})
            if scope == "all":
                self._stop_playback()
                self._reset_all_played_state()
                self.current_playlist_start = None
                self._set_dirty(True)
                self._refresh_sound_grid()
                return self._api_success({"state": self._api_state()})
            return self._api_error("invalid_scope", "Scope must be current or all.")

        if cmd == "volume_set":
            try:
                level = int(params.get("level", 0))
            except (TypeError, ValueError):
                return self._api_error("invalid_volume", "Volume level must be an integer.")
            if level < 0 or level > 100:
                return self._api_error("invalid_volume", "Volume level must be in range 0..100.")
            self.volume_slider.setValue(level)
            return self._api_success({"volume": int(self.volume_slider.value()), "state": self._api_state()})

        if cmd == "mute":
            self._toggle_mute_hotkey()
            return self._api_success({"volume": int(self.volume_slider.value()), "state": self._api_state()})

        if cmd == "navigate":
            target = str(params.get("target", "")).strip().lower()
            direction = str(params.get("direction", "")).strip().lower()
            if direction not in {"next", "prev"}:
                return self._api_error("invalid_direction", "Direction must be next or prev.")
            delta = 1 if direction == "next" else -1
            if target == "group":
                self._hotkey_select_group_delta(delta)
                return self._api_success({"state": self._api_state()})
            if target == "page":
                self._hotkey_select_page_delta(delta)
                return self._api_success({"state": self._api_state()})
            if target == "sound_button":
                self._hotkey_select_sound_button_delta(delta)
                return self._api_success({"state": self._api_state()})
            return self._api_error("invalid_target", "Navigation target must be group, page, or sound_button.")

        if cmd in {"playselected", "playselectedpause"}:
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
                return self._api_error("no_selected_button", "No selected sound button on current page.", status=409)
            if cmd == "playselected":
                self._hotkey_play_selected()
            else:
                self._hotkey_play_selected_pause()
            return self._api_success({"selected_button": slot_index + 1, "state": self._api_state()})

        if cmd == "seek":
            total_ms = self._transport_total_ms()
            if total_ms <= 0:
                return self._api_error("not_seekable", "No active seek range is available.", status=409)
            percent_raw = params.get("percent")
            time_raw = params.get("time")
            target_display: Optional[int] = None
            if percent_raw is not None and str(percent_raw).strip() != "":
                try:
                    percent = float(str(percent_raw).strip())
                except (TypeError, ValueError):
                    return self._api_error("invalid_percent", "percent must be a number in range 0..100.")
                if percent < 0.0 or percent > 100.0:
                    return self._api_error("invalid_percent", "percent must be in range 0..100.")
                target_display = int(round((percent / 100.0) * total_ms))
            elif time_raw is not None and str(time_raw).strip() != "":
                parsed_ms = self._parse_cue_time_string_to_ms(str(time_raw).strip())
                if parsed_ms is None:
                    return self._api_error("invalid_time", "time must be mm:ss, mm:ss:ff, or hh:mm:ss.")
                target_display = parsed_ms
            else:
                return self._api_error("invalid_seek", "Provide either percent or time.")
            display_ms, absolute_ms = self._seek_transport_display_ms(target_display)
            return self._api_success(
                {
                    "display_ms": display_ms,
                    "display_time": format_clock_time(display_ms),
                    "absolute_ms": absolute_ms,
                    "absolute_time": format_clock_time(absolute_ms),
                    "state": self._api_state(),
                }
            )

        if cmd == "alert":
            clear_mode = self._parse_api_mode(params.get("mode", ""))
            clear_flag = self._parse_api_bool(params.get("clear"))
            if clear_mode == "disable" or clear_flag is True:
                self._clear_stage_alert()
                return self._api_success({"alert_active": False, "alert_message": "", "state": self._api_state()})

            text = str(params.get("text", "")).strip()
            if not text:
                return self._api_error("invalid_alert", "Alert text is required.")

            keep = self._parse_api_bool(params.get("keep"))
            keep_value = True if keep is None else bool(keep)
            try:
                seconds = int(params.get("seconds", 10))
            except (TypeError, ValueError):
                return self._api_error("invalid_seconds", "seconds must be an integer.")
            if seconds < 1 or seconds > 600:
                return self._api_error("invalid_seconds", "seconds must be in range 1..600.")

            self._set_stage_alert(text, keep=keep_value, seconds=seconds)
            return self._api_success(
                {
                    "alert_active": self._stage_alert_active(),
                    "alert_message": self._stage_alert_message,
                    "alert_keep": self._stage_alert_sticky,
                    "state": self._api_state(),
                }
            )

        return self._api_error("unknown_command", f"Unknown command '{command}'.", status=404)

