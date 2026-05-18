# `pyssp/ui/options_dialog/page_builders/audio_loading_format.py`

- Source: `pyssp/ui/options_dialog/page_builders/audio_loading_format.py`
- Module path: `pyssp.ui.options_dialog.page_builders.audio_loading_format`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `AudioLoadingFormatPageMixin`

- Defined at `pyssp/ui/options_dialog/page_builders/audio_loading_format.py:7`

#### Internal Members

- `_build_audio_preload_page(self, preload_audio_enabled: bool, preload_current_page_audio: bool, preload_audio_memory_limit_mb: int, preload_memory_pressure_enabled: bool, preload_pause_on_playback: bool, preload_use_ffmpeg: bool, preload_video_enabled: bool, waveform_cache_limit_mb: int, waveform_cache_clear_on_launch: bool, preload_total_ram_mb: int, preload_ram_cap_mb: int, supported_audio_format_extensions: List[str], verify_sound_file_on_add: bool, allow_other_unsupported_audio_files: bool, disable_path_safety: bool) -> QWidget` [method] (pyssp/ui/options_dialog/page_builders/audio_loading_format.py:8)
- `_update_disable_path_safety_warning(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/audio_loading_format.py:182)
- `_update_preload_slider_label(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/audio_loading_format.py:188)
- `_update_waveform_cache_size_label(self, selected_mb: int) -> None` [method] (pyssp/ui/options_dialog/page_builders/audio_loading_format.py:193)
- `_on_waveform_cache_size_input_changed(self, value: int) -> None` [method] (pyssp/ui/options_dialog/page_builders/audio_loading_format.py:197)
- `_on_waveform_cache_size_slider_changed(self, value: int) -> None` [method] (pyssp/ui/options_dialog/page_builders/audio_loading_format.py:212)
- `_clear_waveform_cache_now(self) -> None` [method] (pyssp/ui/options_dialog/page_builders/audio_loading_format.py:222)
