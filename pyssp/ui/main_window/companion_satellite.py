from __future__ import annotations

import threading

from .shared import *
from pyssp.automation_command import AUTOMATION_AUTO_RELEASE_IMMEDIATE, AUTOMATION_SOURCE_TYPE

from pyssp.companion_remote_control import send_companion_location_command
from pyssp.companion_satellite import CompanionSatelliteClient
from pyssp.ui.companion_satellite_window import CompanionSatelliteWindow


class _CompanionSatelliteBridge(QObject):
    statusChanged = pyqtSignal(str, str)
    helloReceived = pyqtSignal(str)
    capsReceived = pyqtSignal(dict)
    keyStateReceived = pyqtSignal(int, dict)
    keysCleared = pyqtSignal()


class CompanionSatelliteMixin:
    def _open_companion_available_commands(self) -> None:
        dialog = self._companion_available_commands_dialog
        if dialog is None:
            dialog = CompanionAvailableCommandsDialog(self)
            dialog.clear_button.clicked.connect(self._clear_companion_available_commands)
            dialog.hide_black_empty_checkbox.toggled.connect(
                self._set_companion_available_commands_filter_black_empty
            )
            dialog.hide_navigation_checkbox.toggled.connect(self._refresh_companion_available_commands_dialog)
            dialog.bypassToggled.connect(self._toggle_companion_bypass)
            dialog.locationCommandRequested.connect(self._send_companion_location_command_async)
            dialog.openVirtualSatelliteRequested.connect(self._open_virtual_satellite)
            self._companion_available_commands_dialog = dialog
        dialog.hide_black_empty_checkbox.blockSignals(True)
        dialog.hide_black_empty_checkbox.setChecked(bool(self.companion_available_commands_filter_black_empty))
        dialog.hide_black_empty_checkbox.blockSignals(False)
        dialog.set_bypass_checked(bool(self.companion_bypass))
        self._refresh_companion_available_commands_dialog()
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _refresh_companion_available_commands_dialog(self) -> None:
        dialog = self._companion_available_commands_dialog
        if dialog is None:
            return
        dialog.set_payload(
            load_companion_available_commands(),
            hide_black_empty=bool(self.companion_available_commands_filter_black_empty),
            hide_navigation=bool(dialog.hide_navigation_checkbox.isChecked()),
        )

    def _clear_companion_available_commands(self) -> None:
        clear_companion_available_commands()
        self._refresh_companion_available_commands_dialog()

    def _refresh_companion_available_commands_from_window(self) -> None:
        window = self._companion_satellite_window
        if window is None:
            return
        for state in window.current_page_button_states():
            self._record_companion_available_command_state(state)
        self._refresh_companion_available_commands_dialog()

    def _set_companion_available_commands_filter_black_empty(self, checked: bool) -> None:
        self.companion_available_commands_filter_black_empty = bool(checked)
        self._refresh_companion_available_commands_dialog()
        self._save_settings()

    def _record_companion_available_command_state(self, state: dict) -> None:
        normalized_state = dict(state or {})
        location = str(normalized_state.get("location", "") or "").strip()
        if not location:
            return
        record_companion_available_command(
            location=location,
            text=str(normalized_state.get("text", "") or ""),
            key_type=str(normalized_state.get("type", "") or ""),
            color=str(normalized_state.get("color", "") or ""),
            pressed=bool(normalized_state.get("pressed", False)),
        )

    def _send_companion_location_command_async(self, location: str, action: str) -> bool:
        if bool(getattr(self, "companion_bypass", False)):
            self._show_info_notice_banner(tr("Companion commands are bypassed. Command will not go through."))
            return False
        host = self.companion_satellite_host
        mode = self.companion_command_mode
        tcp_port = self.companion_command_tcp_port
        udp_port = self.companion_command_udp_port
        http_port = self.companion_command_http_port

        def _notify_failure(message: str) -> None:
            failure_message = str(message or location).strip() or str(location or "").strip() or "Unknown error"
            try:
                self._main_thread_executor.call(
                    lambda: self._show_info_notice_banner(
                        f"{tr('Companion command failed')}: {failure_message}"
                    )
                )
            except Exception:
                pass

        def _worker() -> None:
            try:
                ok, message = send_companion_location_command(
                    host=host,
                    mode=mode,
                    tcp_port=tcp_port,
                    udp_port=udp_port,
                    http_port=http_port,
                    location=location,
                    action=action,
                )
            except Exception as exc:
                _notify_failure(str(exc))
                return
            if ok:
                return
            _notify_failure(message)

        try:
            threading.Thread(target=_worker, name="pyssp-companion-command", daemon=True).start()
        except Exception as exc:
            _notify_failure(str(exc))
            return False
        return True

    def _automation_slot_key(self, slot_index: int) -> Tuple[str, int, int]:
        return (self._view_group_key(), self.current_page, int(slot_index))

    def _set_automation_slot_active(self, slot_key: Tuple[str, int, int], active: bool) -> None:
        if active:
            self._automation_active_keys.add(slot_key)
        else:
            self._automation_active_keys.discard(slot_key)
        self._refresh_sound_grid()

    def _mark_automation_slot_played(self, slot_key: Tuple[str, int, int]) -> None:
        slot = self._slot_for_key(slot_key)
        if slot is None:
            return
        slot.played = True
        slot.activity_code = "2"
        self._set_dirty(True)
        self._refresh_sound_grid()

    def _flash_automation_slot(self, slot_key: Tuple[str, int, int], duration_ms: int = 180) -> None:
        self._set_automation_slot_active(slot_key, True)

        def _clear_flash() -> None:
            if slot_key in self._automation_hold_active_keys:
                return
            self._set_automation_slot_active(slot_key, False)

        QTimer.singleShot(max(1, int(duration_ms)), _clear_flash)

    def _automation_button_auto_release_mode(self) -> str:
        token = str(getattr(self, "automation_command_button_auto_release_mode", AUTOMATION_AUTO_RELEASE_IMMEDIATE) or "")
        return token if token in {"immediate", "down_only"} else AUTOMATION_AUTO_RELEASE_IMMEDIATE

    def _trigger_automation_slot_press(self, slot_index: int) -> bool:
        slot_key = self._automation_slot_key(slot_index)
        slot = self._slot_for_key(slot_key)
        if slot is None or slot.source_type != AUTOMATION_SOURCE_TYPE or slot.marker or not slot.assigned or slot.locked:
            return False
        spec = slot.automation_spec
        if spec is None or (not spec.hold_to_release):
            return False
        if slot_key in self._automation_hold_active_keys:
            return True
        if not self._send_companion_location_command_async(spec.location, "down"):
            return False
        self._automation_hold_active_keys.add(slot_key)
        self._set_automation_slot_active(slot_key, True)
        return True

    def _trigger_automation_slot_release(self, slot_index: int) -> bool:
        slot_key = self._automation_slot_key(slot_index)
        slot = self._slot_for_key(slot_key)
        if slot is None or slot.source_type != AUTOMATION_SOURCE_TYPE or slot.marker or not slot.assigned:
            return False
        if slot_key not in self._automation_hold_active_keys:
            return False
        spec = slot.automation_spec
        self._automation_hold_active_keys.discard(slot_key)
        self._automation_click_suppressed_slot_key = slot_key
        QTimer.singleShot(0, lambda: setattr(self, "_automation_click_suppressed_slot_key", None))
        self._set_automation_slot_active(slot_key, False)
        if spec is None:
            return False
        if self._send_companion_location_command_async(spec.location, "up"):
            self._mark_automation_slot_played(slot_key)
            self._continue_playlist_after_automation_trigger(slot_key)
            return True
        return False

    def _trigger_automation_slot_click(self, slot_index: int) -> bool:
        slot_key = self._automation_slot_key(slot_index)
        if getattr(self, "_automation_click_suppressed_slot_key", None) == slot_key:
            return True
        return self._trigger_automation_slot_non_audio(slot_index, auto_release=True)

    def _trigger_automation_slot_non_audio(
        self,
        slot_index: int,
        auto_release: bool = True,
        *,
        continue_playlist_after_automation: bool = True,
    ) -> bool:
        slot_key = self._automation_slot_key(slot_index)
        slot = self._slot_for_key(slot_key)
        if slot is None or slot.source_type != AUTOMATION_SOURCE_TYPE or slot.marker or not slot.assigned or slot.locked:
            return False
        spec = slot.automation_spec
        if spec is None or not spec.location:
            self._show_info_notice_banner(tr("Automation command location is missing."))
            return False
        playlist_enabled = (not self.cue_mode) and self.page_playlist_enabled[self.current_group][self.current_page]
        if playlist_enabled and self.current_playlist_start is None:
            self.current_playlist_start = slot_index
        if spec.hold_to_release and (not auto_release):
            if not self._send_companion_location_command_async(spec.location, "down"):
                return False
            self._flash_automation_slot(slot_key, duration_ms=600)
            self._mark_automation_slot_played(slot_key)
            if continue_playlist_after_automation:
                self._continue_playlist_after_automation_trigger(slot_key)
            return True
        if spec.hold_to_release:
            if not self._send_companion_location_command_async(spec.location, "down"):
                return False
            self._flash_automation_slot(slot_key)
            self._mark_automation_slot_played(slot_key)
            self._send_companion_location_command_async(spec.location, "up")
            if continue_playlist_after_automation:
                self._continue_playlist_after_automation_trigger(slot_key)
            return True
        if not self._send_companion_location_command_async(spec.location, "press"):
            return False
        self._flash_automation_slot(slot_key)
        self._mark_automation_slot_played(slot_key)
        if continue_playlist_after_automation:
            self._continue_playlist_after_automation_trigger(slot_key)
        return True

    def _companion_satellite_event(self, event_type: str, payload: dict) -> None:
        if event_type == "status":
            self._companion_satellite_bridge.statusChanged.emit(
                str(payload.get("state", "") or ""),
                str(payload.get("message", "") or ""),
            )
        elif event_type == "hello":
            self._companion_satellite_bridge.helloReceived.emit(str(payload.get("api_version", "") or ""))
        elif event_type == "caps":
            self._companion_satellite_bridge.capsReceived.emit(dict(payload.get("caps", {}) or {}))
        elif event_type == "key_state":
            self._companion_satellite_bridge.keyStateReceived.emit(
                int(payload.get("key", -1)),
                dict(payload.get("state", {}) or {}),
            )
        elif event_type == "keys_clear":
            self._companion_satellite_bridge.keysCleared.emit()

    def _companion_satellite_should_run(self) -> bool:
        return bool(self.companion_satellite_enabled)

    def _companion_satellite_client_matches_settings(self) -> bool:
        client = self._companion_satellite_client
        if client is None:
            return False
        return (
            client.host == self.companion_satellite_host
            and int(client.port) == int(self.companion_satellite_port)
            and int(client.columns) == int(self.companion_satellite_columns)
            and int(client.rows) == int(self.companion_satellite_rows)
            and client.serial_suffix == CompanionSatelliteClient._normalize_serial_suffix(
                self.companion_satellite_serial_suffix
            )
        )

    def _apply_companion_satellite_state(self) -> None:
        self._refresh_companion_satellite_window()
        should_run = self._companion_satellite_should_run()
        if should_run:
            if not self._companion_satellite_client_matches_settings():
                self._stop_companion_satellite_client()
            self._start_companion_satellite_client()
        else:
            self._stop_companion_satellite_client()

    def _start_companion_satellite_client(self) -> None:
        if self._companion_satellite_client is None:
            self._companion_satellite_client = CompanionSatelliteClient(
                host=self.companion_satellite_host,
                port=self.companion_satellite_port,
                columns=self.companion_satellite_columns,
                rows=self.companion_satellite_rows,
                serial_suffix=self.companion_satellite_serial_suffix,
                on_event=self._companion_satellite_event,
            )
        if not self._companion_satellite_client.is_running:
            self._companion_satellite_client.start()

    def _stop_companion_satellite_client(self) -> None:
        client = self._companion_satellite_client
        self._companion_satellite_client = None
        if client is not None:
            client.stop()

    def _reconnect_companion_satellite_client(self) -> None:
        if self._companion_satellite_client is None:
            self._start_companion_satellite_client()
            return
        self._companion_satellite_client.reconnect()

    def _open_companion_satellite_options(self) -> None:
        self._open_options_dialog(initial_page="Companion Satellite")

    def _open_virtual_satellite(self) -> None:
        window = self._ensure_companion_satellite_window()
        window.show()
        window.raise_()
        window.activateWindow()
        self._refresh_companion_satellite_window()

    def _ensure_companion_satellite_window(self) -> CompanionSatelliteWindow:
        window = self._companion_satellite_window
        if window is not None:
            return window
        window = CompanionSatelliteWindow(self)
        window.openOptionsRequested.connect(self._open_companion_satellite_options)
        window.openAvailableCommandsRequested.connect(self._open_companion_available_commands)
        window.refreshAvailableCommandsRequested.connect(self._refresh_companion_available_commands_from_window)
        window.buttonPressed.connect(self._on_companion_satellite_button_pressed)
        window.navigationRequested.connect(self._on_companion_satellite_navigation_requested)
        window.windowClosed.connect(self._on_companion_satellite_window_closed)
        self._companion_satellite_window = window
        self._refresh_companion_satellite_window()
        return window

    def _on_companion_satellite_window_closed(self) -> None:
        return

    def _refresh_companion_satellite_window(self) -> None:
        window = self._companion_satellite_window
        if window is None:
            return
        window.set_target(self.companion_satellite_host, self.companion_satellite_port)
        window.set_grid_size(self.companion_satellite_columns, self.companion_satellite_rows)
        window.set_render_mode(self.companion_satellite_render_mode)
        state, message = self._companion_satellite_last_status
        window.set_connection_state(state, message)

    def _on_companion_satellite_status_changed(self, state: str, message: str) -> None:
        self._companion_satellite_last_status = (str(state or ""), str(message or ""))
        self._update_companion_satellite_status_indicator()
        window = self._companion_satellite_window
        if window is not None:
            window.set_connection_state(state, message)

    def _update_companion_satellite_status_indicator(self) -> None:
        label = getattr(self, "companion_satellite_status_icon", None)
        if label is None:
            return
        state = str(self._companion_satellite_last_status[0] or "").strip().lower()
        bypassed = bool(getattr(self, "companion_bypass", False))
        text = tr("SAT (Bypassed)") if bypassed else "SAT"
        if state == "connected":
            style = "QLabel{font-size:9pt;font-weight:bold;color:#165A20;background:#CFF3D6;border:1px solid #2E9B47;border-radius:8px;padding:0 6px;}"
        elif state in {"connecting", "reconnecting"}:
            style = "QLabel{font-size:9pt;font-weight:bold;color:#5F4200;background:#FFF0A6;border:1px solid #CFAE2A;border-radius:8px;padding:0 6px;}"
        else:
            style = "QLabel{font-size:9pt;font-weight:bold;color:#4A4F55;background:#D6D9DE;border:1px solid #8C939D;border-radius:8px;padding:0 6px;}"
        label.setText(text)
        label.setStyleSheet(style)
        message = str(self._companion_satellite_last_status[1] or "").strip()
        if bypassed:
            message = tr("Companion remote commands are bypassed.") + (f" {message}" if message else "")
        tooltip = message or (
            tr("Connected") if state == "connected" else tr("Connecting") if state in {"connecting", "reconnecting"} else tr("Not Connected")
        )
        label.setToolTip(tooltip)

    def _toggle_companion_bypass(self, checked: bool) -> None:
        self.companion_bypass = bool(checked)
        action = self._menu_actions.get("companion_bypass")
        if action is not None and action.isChecked() != self.companion_bypass:
            action.setChecked(self.companion_bypass)
        dialog = self._companion_available_commands_dialog
        if dialog is not None:
            dialog.set_bypass_checked(self.companion_bypass)
        btn = self.control_buttons.get("Companion Bypass")
        if btn is not None and btn.isChecked() != self.companion_bypass:
            btn.setChecked(self.companion_bypass)
        self._sync_control_button_instances("Companion Bypass")
        self._update_companion_satellite_status_indicator()
        if not self._suspend_settings_save:
            self._save_settings()

    def _on_companion_satellite_hello_received(self, version: str) -> None:
        self._companion_satellite_api_version = str(version or "").strip()

    def _on_companion_satellite_caps_received(self, caps: dict) -> None:
        self._companion_satellite_caps = dict(caps or {})

    def _on_companion_satellite_key_state_received(self, key: int, state: dict) -> None:
        window = self._ensure_companion_satellite_window()
        normalized_state = dict(state or {})
        window.update_button(int(key), normalized_state)
        self._record_companion_available_command_state(normalized_state)
        self._refresh_companion_available_commands_dialog()

    def _on_companion_satellite_keys_cleared(self) -> None:
        window = self._companion_satellite_window
        if window is not None:
            window.clear_buttons()

    def _on_companion_satellite_button_pressed(self, key: int, pressed: bool) -> None:
        client = self._companion_satellite_client
        if client is None:
            return
        client.send_key_press(int(key), bool(pressed))

    def _on_companion_satellite_navigation_requested(self, direction: str) -> None:
        client = self._companion_satellite_client
        window = self._companion_satellite_window
        if client is None or window is None:
            return
        token = str(direction or "").strip().upper()
        if token == "PAGEUP":
            client.send_change_page(True)
        elif token == "PAGEDOWN":
            client.send_change_page(False)
        elif token == "HOME":
            current_page = window.current_page()
            if current_page is None or current_page <= 1:
                return
            for _ in range(max(0, min(255, int(current_page) - 1))):
                if not client.send_change_page(False):
                    break
