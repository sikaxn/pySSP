from __future__ import annotations

from .shared import *
from .widgets import *


class DeviceMidiMixin:
    def _refresh_midi_input_devices(self, force_refresh: bool = False) -> None:
        current_ids = set(self._checked_midi_input_device_ids() or self._midi_input_device_ids)
        current_names = set(self._checked_midi_input_device_names())
        for selector in current_ids:
            name = midi_input_selector_name(selector)
            if name:
                current_names.add(name)
        mtc_device_id = str(
            self.timecode_midi_output_combo.currentData() if hasattr(self, "timecode_midi_output_combo") else MIDI_OUTPUT_DEVICE_NONE
        ).strip()
        mtc_device_name = (
            str(self.timecode_midi_output_combo.currentText() if hasattr(self, "timecode_midi_output_combo") else "").strip()
            if mtc_device_id != MIDI_OUTPUT_DEVICE_NONE
            else ""
        )
        selected_before = set(current_ids)
        disconnected_labels: List[str] = []
        mtc_blocked_labels: List[str] = []
        listed_selectors: set[str] = set()
        try:
            self.midi_input_list.itemChanged.disconnect(self._on_midi_input_selection_changed)
        except Exception:
            pass
        self.midi_input_list.clear()
        for device_id, device_name in list_midi_input_devices(force_refresh=force_refresh):
            selector = midi_input_name_selector(device_name)
            listed_selectors.add(selector)
            item = QListWidgetItem(device_name)
            item.setData(Qt.UserRole, selector)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            checked = (selector in current_ids) or (str(device_name).strip() in current_names) or (str(device_id) in current_ids)
            blocked_for_mtc = bool(mtc_device_name) and str(device_name).strip().lower() == mtc_device_name.lower()
            if blocked_for_mtc:
                checked = False
                item.setFlags(Qt.NoItemFlags)
                font = item.font()
                font.setStrikeOut(True)
                item.setFont(font)
                item.setText(f"{device_name} (used by MTC)")
                item.setForeground(QColor("#7A7A7A"))
                mtc_blocked_labels.append(str(device_name).strip() or str(selector))
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            self.midi_input_list.addItem(item)
        for selector in list(selected_before):
            token = str(selector or "").strip()
            if (not token) or (token in listed_selectors):
                continue
            disconnected_name = midi_input_selector_name(token) or token
            item = QListWidgetItem(f"{disconnected_name} (Disconnected)")
            item.setData(Qt.UserRole, token)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setForeground(QColor("#7A7A7A"))
            self.midi_input_list.addItem(item)
            disconnected_labels.append(disconnected_name)
        self.midi_input_list.itemChanged.connect(self._on_midi_input_selection_changed)
        self._on_midi_input_selection_changed()
        notices: List[str] = []
        if disconnected_labels:
            display = ", ".join(disconnected_labels[:3])
            if len(disconnected_labels) > 3:
                display += f" (+{len(disconnected_labels) - 3} more)"
            notices.append(f"{tr('Disconnected MIDI device selected:')} {display}")
        if mtc_blocked_labels:
            display = ", ".join(mtc_blocked_labels[:3])
            if len(mtc_blocked_labels) > 3:
                display += f" (+{len(mtc_blocked_labels) - 3} more)"
            mtc_notice = tr("Device used for MTC can't be used for MIDI control:")
            notices.append(f"{mtc_notice} {display}")
        if hasattr(self, "midi_input_status_label") and self.midi_input_status_label is not None:
            self.midi_input_status_label.setText(" ".join(notices))
            self.midi_input_status_label.setVisible(bool(notices))

    def _checked_midi_input_device_ids(self) -> List[str]:
        selected: List[str] = []
        seen: set[str] = set()
        if not hasattr(self, "midi_input_list"):
            return selected
        for i in range(self.midi_input_list.count()):
            item = self.midi_input_list.item(i)
            if item is None:
                continue
            if not (item.flags() & Qt.ItemIsEnabled):
                continue
            if item.checkState() == Qt.Checked:
                device_id = str(item.data(Qt.UserRole) or "").strip()
                if device_id and device_id not in seen:
                    seen.add(device_id)
                    selected.append(device_id)
        return selected

    def _checked_midi_input_device_names(self) -> List[str]:
        selected: List[str] = []
        if not hasattr(self, "midi_input_list"):
            return selected
        for i in range(self.midi_input_list.count()):
            item = self.midi_input_list.item(i)
            if item is None:
                continue
            if item.checkState() == Qt.Checked:
                name = str(item.text() or "").strip()
                if name:
                    selected.append(name)
        return selected

    def _on_midi_input_selection_changed(self, _item=None) -> None:
        ids = self._checked_midi_input_device_ids()
        self._midi_input_device_ids = ids

    def _start_midi_learning(self, target: MidiCaptureEdit) -> None:
        self._set_midi_info("")
        if self._learning_midi_rotary_target is not None and self._learning_midi_rotary_target is not target:
            self._learning_midi_rotary_target.setStyleSheet("")
            self._learning_midi_rotary_target = None
            self._learning_midi_rotary_state = None
        if self._learning_midi_target is not None and self._learning_midi_target is not target:
            self._learning_midi_target.setStyleSheet("")
        self._learning_midi_target = target
        target.setStyleSheet("QLineEdit{border:2px solid #2E65FF;}")

    def _start_midi_rotary_learning(self, target: MidiCaptureEdit) -> None:
        if self._learning_midi_target is not None and self._learning_midi_target is not target:
            self._learning_midi_target.setStyleSheet("")
            self._learning_midi_target = None
        if self._learning_midi_rotary_target is not None and self._learning_midi_rotary_target is not target:
            self._learning_midi_rotary_target.setStyleSheet("")
        self._learning_midi_rotary_target = target
        self._learning_midi_rotary_state = {
            "selector": "",
            "status": -1,
            "data1": -1,
            "phase": "forward",
            "forward": [],
            "backward": [],
        }
        self._set_midi_info(tr("Rotary learn: turn encoder forward several ticks, then backward several ticks."))
        target.setStyleSheet("QLineEdit{border:2px solid #2E65FF;}")

    def _on_midi_binding_captured(self, token: str, source_selector: str = "") -> None:
        if self._learning_midi_target is None:
            return
        _prev_selector, normalized_token = split_midi_binding(token)
        if source_selector:
            self._learning_midi_target.setBinding(f"{source_selector}|{normalized_token}")
        else:
            self._learning_midi_target.setBinding(normalized_token)
        self._learning_midi_target.setStyleSheet("")
        self._learning_midi_target = None
        self._validate_midi_conflicts()

    def handle_midi_message(
        self,
        token: str,
        source_selector: str = "",
        status: int = 0,
        data1: int = 0,
        data2: int = 0,
    ) -> bool:
        if self._learning_midi_rotary_target is not None:
            status = int(status) & 0xFF
            data1 = int(data1) & 0xFF
            data2 = int(data2) & 0xFF
            base = ""
            high = status & 0xF0
            state = self._learning_midi_rotary_state or {
                "selector": "",
                "status": -1,
                "data1": -1,
                "phase": "forward",
                "forward": [],
                "backward": [],
            }
            if high == 0xB0:
                base = normalize_midi_binding(f"{status:02X}:{data1:02X}")
                bound_selector = str(state.get("selector", "") or "")
                bound_status = int(state.get("status", -1))
                bound_data1 = int(state.get("data1", -1))
                if bound_status < 0:
                    state["selector"] = str(source_selector or "")
                    state["status"] = status
                    state["data1"] = data1
                else:
                    if str(source_selector or "") != bound_selector:
                        return True
                    if status != bound_status or data1 != bound_data1:
                        return True
                phase = str(state.get("phase", "forward"))
                if data2 != 64:
                    if phase == "forward":
                        state["forward"].append(data2)
                        if len(state["forward"]) >= 4:
                            state["phase"] = "backward"
                            self._set_midi_info(tr("Rotary learn: now turn backward several ticks."))
                    else:
                        state["backward"].append(data2)
                self._learning_midi_rotary_state = state
                if len(state["forward"]) >= 4 and len(state["backward"]) >= 4:
                    mode = self._infer_midi_relative_mode(
                        [int(v) for v in state["forward"]],
                        [int(v) for v in state["backward"]],
                    )
                    value = f"{source_selector}|{base}" if source_selector else base
                    self._learning_midi_rotary_target.setBinding(value)
                    self._set_midi_rotary_relative_mode_for_target(self._learning_midi_rotary_target, mode)
                    self._learning_midi_rotary_target.setStyleSheet("")
                    self._learning_midi_rotary_target = None
                    self._learning_midi_rotary_state = None
                    self._set_midi_info(tr("Rotary learn complete. Relative mode: {mode}.").format(mode=mode))
                    self._validate_midi_conflicts()
                return True
            elif high == 0xE0:
                # Pitch Bend encoders/wheels: bind by status(channel).
                base = normalize_midi_binding(f"{status:02X}")
            if base:
                value = f"{source_selector}|{base}" if source_selector else base
                self._learning_midi_rotary_target.setBinding(value)
                self._set_midi_rotary_relative_mode_for_target(self._learning_midi_rotary_target, "auto")
                self._learning_midi_rotary_target.setStyleSheet("")
                self._learning_midi_rotary_target = None
                self._learning_midi_rotary_state = None
                self._set_midi_info(tr("Rotary learn complete."))
                self._validate_midi_conflicts()
                return True
            return False
        if self._learning_midi_target is None:
            return False
        selected = set(self._midi_input_device_ids)
        if selected:
            if not source_selector:
                return False
            if source_selector not in selected:
                return False
        self._on_midi_binding_captured(token, source_selector)
        return True

    def _set_midi_info(self, text: str) -> None:
        if self._midi_warning_label is None:
            return
        message = str(text or "").strip()
        if message:
            self._midi_warning_label.setStyleSheet("color:#1E4FAF; font-weight:bold;")
            self._midi_warning_label.setText(message)
            self._midi_warning_label.setVisible(True)
            return
        self._midi_warning_label.setVisible(False)
        self._midi_warning_label.setText("")

    @staticmethod
    def _normalize_midi_relative_mode(value: str) -> str:
        mode = str(value or "").strip().lower()
        if mode in {"auto", "twos_complement", "sign_magnitude", "binary_offset"}:
            return mode
        return "auto"

    @staticmethod
    def _decode_relative_delta(value: int, mode: str) -> int:
        v = int(value) & 0x7F
        if v == 64:
            return 0
        mode_name = OptionsDialog._normalize_midi_relative_mode(mode)
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

    def _infer_midi_relative_mode(self, forward_values: List[int], backward_values: List[int]) -> str:
        modes = ["twos_complement", "sign_magnitude", "binary_offset"]
        best_mode = "auto"
        best_score = None
        for mode in modes:
            f = [self._decode_relative_delta(v, mode) for v in forward_values]
            b = [self._decode_relative_delta(v, mode) for v in backward_values]
            sign_penalty = (sum(1 for d in f if d <= 0) + sum(1 for d in b if d >= 0)) * 1000
            f_abs = [abs(d) for d in f if d > 0]
            b_abs = [abs(d) for d in b if d < 0]
            if not f_abs or not b_abs:
                score = sign_penalty + 99999
            else:
                mean_f = sum(f_abs) / float(len(f_abs))
                mean_b = sum(b_abs) / float(len(b_abs))
                symmetry_penalty = abs(mean_f - mean_b) * 20.0
                size_penalty = max(0.0, mean_f - 12.0) * 8.0 + max(0.0, mean_b - 12.0) * 8.0
                score = sign_penalty + symmetry_penalty + size_penalty
            if best_score is None or score < best_score:
                best_score = score
                best_mode = mode
        return best_mode

    def _set_midi_rotary_relative_mode_for_target(self, target: MidiCaptureEdit, mode: str) -> None:
        normalized = self._normalize_midi_relative_mode(mode)
        if target is self.midi_rotary_group_edit:
            self._midi_rotary_group_relative_mode = normalized
        elif target is self.midi_rotary_page_edit:
            self._midi_rotary_page_relative_mode = normalized
        elif target is self.midi_rotary_sound_button_edit:
            self._midi_rotary_sound_button_relative_mode = normalized
        elif target is self.midi_rotary_jog_edit:
            self._midi_rotary_jog_relative_mode = normalized
        elif target is self.midi_rotary_volume_edit:
            self._midi_rotary_volume_relative_mode = normalized

    def _set_combo_data_or_default(self, combo: QComboBox, selected_data, default_data) -> None:
        index = combo.findData(selected_data)
        if index < 0:
            index = combo.findData(default_data)
        if index < 0:
            index = 0
        combo.setCurrentIndex(index)

    def _set_combo_float_or_default(self, combo: QComboBox, selected_value: float, default_value: float) -> None:
        index = -1
        for i in range(combo.count()):
            data = combo.itemData(i)
            try:
                if abs(float(data) - float(selected_value)) <= 0.002:
                    index = i
                    break
            except (TypeError, ValueError):
                continue
        if index < 0:
            for i in range(combo.count()):
                data = combo.itemData(i)
                try:
                    if abs(float(data) - float(default_value)) <= 0.002:
                        index = i
                        break
                except (TypeError, ValueError):
                    continue
        if index < 0:
            index = 0
        combo.setCurrentIndex(index)

    def _populate_audio_devices(self, devices: List[str], selected_device: str) -> None:
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("System Default", "")
        for name in devices:
            self.audio_device_combo.addItem(name, name)
        selected_index = 0
        for i in range(self.audio_device_combo.count()):
            if str(self.audio_device_combo.itemData(i)) == selected_device:
                selected_index = i
                break
        self.audio_device_combo.setCurrentIndex(selected_index)
        if devices:
            self.audio_device_hint.setText(f"{tr('Detected ')}{len(devices)}{tr(' output device(s).')}")
        else:
            self.audio_device_hint.setText(tr("No explicit device list detected. System Default will be used."))

    def _refresh_audio_devices(self) -> None:
        selected = self.selected_audio_output_device()
        selected_timecode = self.selected_timecode_audio_output_device()
        selected_timecode_midi = self.selected_timecode_midi_output_device()
        try:
            from pyssp.audio_engine import list_output_devices

            devices = list_output_devices()
        except Exception:
            devices = []
        self._available_audio_devices = list(devices)
        self._populate_audio_devices(self._available_audio_devices, selected)
        self.timecode_output_combo.clear()
        self.timecode_output_combo.addItem("Follow playback device setting", "follow_playback")
        self.timecode_output_combo.addItem("Use system default", "default")
        self.timecode_output_combo.addItem("None (mute output)", "none")
        for name in self._available_audio_devices:
            self.timecode_output_combo.addItem(name, name)
        self._set_combo_data_or_default(self.timecode_output_combo, selected_timecode, "none")
        self.timecode_midi_output_combo.clear()
        self.timecode_midi_output_combo.addItem("None (disabled)", MIDI_OUTPUT_DEVICE_NONE)
        for device_id, device_name in list_midi_output_devices():
            self.timecode_midi_output_combo.addItem(device_name, device_id)
        self._set_combo_data_or_default(
            self.timecode_midi_output_combo,
            selected_timecode_midi,
            MIDI_OUTPUT_DEVICE_NONE,
        )
        self._refresh_midi_input_devices(force_refresh=False)
        localize_widget_tree(self, self._ui_language)

