from __future__ import annotations

from ..shared import *
from ..widgets import *


class AudioLoadingFormatPageMixin:
    def _build_audio_preload_page(
        self,
        preload_audio_enabled: bool,
        preload_current_page_audio: bool,
        preload_audio_memory_limit_mb: int,
        preload_memory_pressure_enabled: bool,
        preload_pause_on_playback: bool,
        preload_use_ffmpeg: bool,
        waveform_cache_limit_mb: int,
        waveform_cache_clear_on_launch: bool,
        preload_total_ram_mb: int,
        preload_ram_cap_mb: int,
        supported_audio_format_extensions: List[str],
        verify_sound_file_on_add: bool,
        allow_other_unsupported_audio_files: bool,
        disable_path_safety: bool,
    ) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        self._preload_slider_step_mb = 128
        total_mb = max(512, int(preload_total_ram_mb))
        cap_mb = max(128, min(int(preload_ram_cap_mb), total_mb))
        cap_steps = max(1, cap_mb // self._preload_slider_step_mb)
        cap_mb = cap_steps * self._preload_slider_step_mb
        selected_mb = max(128, min(int(preload_audio_memory_limit_mb), cap_mb))
        selected_steps = max(1, selected_mb // self._preload_slider_step_mb)
        selected_mb = selected_steps * self._preload_slider_step_mb
        reserve_mb = max(128, int(total_mb - cap_mb))
        self._preload_ram_cap_mb = cap_mb

        options_group = QGroupBox("Behavior")
        options_form = QFormLayout(options_group)
        self.preload_audio_enabled_checkbox = QCheckBox("Enable audio preload cache")
        self.preload_audio_enabled_checkbox.setChecked(bool(preload_audio_enabled))
        options_form.addRow(self.preload_audio_enabled_checkbox)

        self.preload_current_page_checkbox = QCheckBox("Preload current page first")
        self.preload_current_page_checkbox.setChecked(bool(preload_current_page_audio))
        options_form.addRow(self.preload_current_page_checkbox)

        self.preload_memory_pressure_checkbox = QCheckBox("Auto-free cache when other apps use RAM (FIFO)")
        self.preload_memory_pressure_checkbox.setChecked(bool(preload_memory_pressure_enabled))
        options_form.addRow(self.preload_memory_pressure_checkbox)
        self.preload_pause_on_playback_checkbox = QCheckBox("Pause audio preload during playback")
        self.preload_pause_on_playback_checkbox.setChecked(bool(preload_pause_on_playback))
        options_form.addRow(self.preload_pause_on_playback_checkbox)
        self.preload_use_ffmpeg_checkbox = QCheckBox("Use FFmpeg for RAM preload decoding")
        self.preload_use_ffmpeg_checkbox.setChecked(bool(preload_use_ffmpeg))
        options_form.addRow(self.preload_use_ffmpeg_checkbox)
        ffmpeg_note = QLabel("Warning: Enabling this may increase CPU usage during preload.")
        ffmpeg_note.setWordWrap(True)
        options_form.addRow(ffmpeg_note)
        layout.addWidget(options_group)

        ram_group = QGroupBox("RAM Limit")
        ram_layout = QVBoxLayout(ram_group)
        self.preload_ram_info_label = QLabel(
            f"System RAM: {total_mb} MB | Reserved: {reserve_mb} MB | Max Cache Limit: {cap_mb} MB"
        )
        self.preload_ram_info_label.setWordWrap(True)
        ram_layout.addWidget(self.preload_ram_info_label)

        self.preload_memory_slider = QSlider(Qt.Horizontal)
        self.preload_memory_slider.setRange(1, cap_steps)
        self.preload_memory_slider.setSingleStep(1)
        self.preload_memory_slider.setPageStep(1)
        self.preload_memory_slider.setValue(selected_steps)
        self.preload_memory_slider.valueChanged.connect(self._update_preload_slider_label)
        ram_layout.addWidget(self.preload_memory_slider)

        self.preload_memory_value_label = QLabel("")
        ram_layout.addWidget(self.preload_memory_value_label)
        self._update_preload_slider_label()
        layout.addWidget(ram_group)

        waveform_group = QGroupBox("Waveform Cache")
        waveform_layout = QVBoxLayout(waveform_group)
        self._waveform_cache_slider_step_mb = 128
        wf_min_mb, wf_max_mb = get_waveform_cache_limit_bounds_mb()
        self._waveform_cache_min_mb = int(wf_min_mb)
        self._waveform_cache_max_mb = int(wf_max_mb)
        wf_selected_mb = max(self._waveform_cache_min_mb, min(int(waveform_cache_limit_mb), self._waveform_cache_max_mb))
        wf_selected_mb = max(
            self._waveform_cache_min_mb,
            (wf_selected_mb // self._waveform_cache_slider_step_mb) * self._waveform_cache_slider_step_mb,
        )
        if wf_selected_mb <= 0:
            wf_selected_mb = self._waveform_cache_min_mb
        self._waveform_cache_syncing = False

        self.waveform_cache_size_input = QSpinBox()
        self.waveform_cache_size_input.setRange(self._waveform_cache_min_mb, self._waveform_cache_max_mb)
        self.waveform_cache_size_input.setSingleStep(self._waveform_cache_slider_step_mb)
        self.waveform_cache_size_input.setValue(wf_selected_mb)
        waveform_layout.addWidget(self.waveform_cache_size_input)

        self.waveform_cache_size_slider = QSlider(Qt.Horizontal)
        self.waveform_cache_size_slider.setRange(
            self._waveform_cache_min_mb // self._waveform_cache_slider_step_mb,
            self._waveform_cache_max_mb // self._waveform_cache_slider_step_mb,
        )
        self.waveform_cache_size_slider.setSingleStep(1)
        self.waveform_cache_size_slider.setPageStep(1)
        self.waveform_cache_size_slider.setValue(wf_selected_mb // self._waveform_cache_slider_step_mb)
        waveform_layout.addWidget(self.waveform_cache_size_slider)

        self.waveform_cache_size_value_label = QLabel("")
        waveform_layout.addWidget(self.waveform_cache_size_value_label)

        self.waveform_cache_clear_on_launch_checkbox = QCheckBox("Clear waveform cache on every launch")
        self.waveform_cache_clear_on_launch_checkbox.setChecked(bool(waveform_cache_clear_on_launch))
        waveform_layout.addWidget(self.waveform_cache_clear_on_launch_checkbox)

        cache_usage_mb = max(0.0, float(get_waveform_cache_usage_bytes()) / (1024.0 * 1024.0))
        self.waveform_cache_usage_label = QLabel(f"{tr('Current Cache Usage:')} {cache_usage_mb:.1f} MB")
        waveform_layout.addWidget(self.waveform_cache_usage_label)

        self.waveform_cache_clear_button = QPushButton("Clear Waveform Cache")
        self.waveform_cache_clear_button.clicked.connect(self._clear_waveform_cache_now)
        waveform_layout.addWidget(self.waveform_cache_clear_button, 0, Qt.AlignLeft)

        self.waveform_cache_size_input.valueChanged.connect(self._on_waveform_cache_size_input_changed)
        self.waveform_cache_size_slider.valueChanged.connect(self._on_waveform_cache_size_slider_changed)
        self._update_waveform_cache_size_label(wf_selected_mb)
        layout.addWidget(waveform_group)

        detected_group = QGroupBox("Detected Supported Audio Format Extensions")
        detected_layout = QVBoxLayout(detected_group)
        supported = [str(token).strip().lower() for token in supported_audio_format_extensions if str(token).strip()]
        self.supported_audio_format_extensions_value = QLabel(", ".join(supported) if supported else "(none detected)")
        self.supported_audio_format_extensions_value.setWordWrap(True)
        self.supported_audio_format_extensions_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        detected_layout.addWidget(self.supported_audio_format_extensions_value)
        self.rescan_supported_audio_format_button = QPushButton("Rescan Supported Audio Format")
        self.rescan_supported_audio_format_button.clicked.connect(self._rescan_supported_audio_formats)
        detected_layout.addWidget(self.rescan_supported_audio_format_button, 0, Qt.AlignLeft)
        layout.addWidget(detected_group)

        behavior_group = QGroupBox("Add Sound Button Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        self.verify_sound_file_on_add_checkbox = QCheckBox("Verify sound file upon adding sound button")
        self.verify_sound_file_on_add_checkbox.setChecked(bool(verify_sound_file_on_add))
        behavior_layout.addWidget(self.verify_sound_file_on_add_checkbox)
        self.allow_other_unsupported_audio_files_checkbox = QCheckBox(
            "Allow other unsupported file"
        )
        self.allow_other_unsupported_audio_files_checkbox.setChecked(bool(allow_other_unsupported_audio_files))
        behavior_layout.addWidget(self.allow_other_unsupported_audio_files_checkbox)
        self.disable_path_safety_checkbox = QCheckBox("Disable path safety")
        self.disable_path_safety_checkbox.setChecked(bool(disable_path_safety))
        self.disable_path_safety_checkbox.toggled.connect(self._update_disable_path_safety_warning)
        behavior_layout.addWidget(self.disable_path_safety_checkbox)
        self.disable_path_safety_warning_label = QLabel(
            "Warning: Disabling path safety can allow malformed file paths and is not recommended."
        )
        self.disable_path_safety_warning_label.setStyleSheet("color:#C62828; font-weight:600;")
        self.disable_path_safety_warning_label.setWordWrap(True)
        behavior_layout.addWidget(self.disable_path_safety_warning_label)
        self._update_disable_path_safety_warning()
        note = QLabel(
            "When disabled, Add Sound Button file selection is limited to the detected supported audio extensions."
        )
        note.setWordWrap(True)
        behavior_layout.addWidget(note)
        layout.addWidget(behavior_group)

        layout.addStretch(1)
        return page

    def _update_disable_path_safety_warning(self) -> None:
        if not hasattr(self, "disable_path_safety_warning_label"):
            return
        enabled = bool(self.disable_path_safety_checkbox.isChecked())
        self.disable_path_safety_warning_label.setVisible(enabled)

    def _update_preload_slider_label(self) -> None:
        value = int(self.preload_memory_slider.value())
        selected_mb = value * int(self._preload_slider_step_mb)
        self.preload_memory_value_label.setText(f"Selected Cache Limit: {selected_mb} MB")

    def _update_waveform_cache_size_label(self, selected_mb: int) -> None:
        selected = max(self._waveform_cache_min_mb, min(int(selected_mb), self._waveform_cache_max_mb))
        self.waveform_cache_size_value_label.setText(f"{tr('Selected Waveform Cache Limit:')} {selected} MB")

    def _on_waveform_cache_size_input_changed(self, value: int) -> None:
        if self._waveform_cache_syncing:
            return
        selected_mb = max(
            self._waveform_cache_min_mb,
            min(int(value), self._waveform_cache_max_mb),
        )
        selected_mb = (selected_mb // self._waveform_cache_slider_step_mb) * self._waveform_cache_slider_step_mb
        selected_mb = max(self._waveform_cache_min_mb, selected_mb)
        self._waveform_cache_syncing = True
        self.waveform_cache_size_input.setValue(selected_mb)
        self.waveform_cache_size_slider.setValue(selected_mb // self._waveform_cache_slider_step_mb)
        self._waveform_cache_syncing = False
        self._update_waveform_cache_size_label(selected_mb)

    def _on_waveform_cache_size_slider_changed(self, value: int) -> None:
        if self._waveform_cache_syncing:
            return
        selected_mb = int(value) * self._waveform_cache_slider_step_mb
        selected_mb = max(self._waveform_cache_min_mb, min(selected_mb, self._waveform_cache_max_mb))
        self._waveform_cache_syncing = True
        self.waveform_cache_size_input.setValue(selected_mb)
        self._waveform_cache_syncing = False
        self._update_waveform_cache_size_label(selected_mb)

    def _clear_waveform_cache_now(self) -> None:
        ok = bool(clear_waveform_disk_cache())
        cache_usage_mb = max(0.0, float(get_waveform_cache_usage_bytes()) / (1024.0 * 1024.0))
        self.waveform_cache_usage_label.setText(f"{tr('Current Cache Usage:')} {cache_usage_mb:.1f} MB")
        if ok:
            QMessageBox.information(self, tr("Waveform Cache"), tr("Waveform cache cleared."))
        else:
            QMessageBox.warning(self, tr("Waveform Cache"), tr("Failed to clear waveform cache."))

