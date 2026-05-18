# `pyssp/audio_engine.py`

- Source: `pyssp/audio_engine.py`
- Module path: `pyssp.audio_engine`
- API entries: `78`

## Module Docstring

No module docstring.

## Functions

### Public

- `shutdown_audio_preload() -> None` [function] (pyssp/audio_engine.py:198)
- `get_engine_output_meter_levels(mode: str = 'post_fader') -> Tuple[float, float]` [function] (pyssp/audio_engine.py:217)
- `clear_output_monitor_frames(player_id: str = '') -> None` [function] (pyssp/audio_engine.py:229)
- `append_output_monitor_frames(player_id: str, frames_block: np.ndarray, *, mode: str) -> None` [function] (pyssp/audio_engine.py:233)
- `take_output_monitor_frames(player_id: str, max_frames: int = 0, mode: str = 'post_fader') -> np.ndarray` [function] (pyssp/audio_engine.py:237)
- `output_monitor_frame_counts(player_id: str) -> Dict[str, int]` [function] (pyssp/audio_engine.py:241)
- `list_output_monitor_players(mode: str = 'post_fader') -> List[str]` [function] (pyssp/audio_engine.py:245)
- `mix_output_monitor_chunk(player_ids: List[str], *, target_frames: int, mode: str = 'post_fader') -> tuple[np.ndarray, Dict[str, int]] | None` [function] (pyssp/audio_engine.py:249)
- `consume_output_monitor_chunk(consume_map: Dict[str, int], mode: str = 'post_fader') -> None` [function] (pyssp/audio_engine.py:258)
- `get_waveform_cache_limit_bounds_mb() -> Tuple[int, int]` [function] (pyssp/audio_engine.py:339)
- `get_waveform_cache_limit_mb() -> int` [function] (pyssp/audio_engine.py:343)
- `get_waveform_cache_dir() -> str` [function] (pyssp/audio_engine.py:348)
- `prepare_waveform_disk_cache(cache_dir: str = '', clear_existing: bool = False, limit_mb: Optional[int] = None) -> str` [function] (pyssp/audio_engine.py:353)
- `configure_waveform_disk_cache(limit_mb: int, cache_dir: str = '') -> str` [function] (pyssp/audio_engine.py:375)
- `clear_waveform_disk_cache() -> bool` [function] (pyssp/audio_engine.py:379)
- `get_waveform_cache_usage_bytes() -> int` [function] (pyssp/audio_engine.py:396)
- `ensure_audio_decoder_ready() -> None` [function] (pyssp/audio_engine.py:575)
- `list_output_devices() -> List[str]` [function] (pyssp/audio_engine.py:586)
- `set_output_device(device_name: str) -> bool` [function] (pyssp/audio_engine.py:603)
- `get_media_ssp_units(file_path: str) -> Tuple[int, int]` [function] (pyssp/audio_engine.py:656)
- `configure_audio_preload_cache(enabled: bool, memory_limit_mb: int) -> None` [function] (pyssp/audio_engine.py:664)
- `configure_audio_preload_cache_policy(enabled: bool, memory_limit_mb: int, pressure_enabled: bool, preload_use_ffmpeg: bool = True) -> None` [function] (pyssp/audio_engine.py:673)
- `enforce_audio_preload_limits() -> None` [function] (pyssp/audio_engine.py:703)
- `get_preload_memory_limits_mb() -> Tuple[int, int, int]` [function] (pyssp/audio_engine.py:710)
- `get_audio_preload_runtime_status() -> Tuple[bool, int]` [function] (pyssp/audio_engine.py:722)
- `get_audio_preload_capacity_bytes() -> Tuple[int, int, int]` [function] (pyssp/audio_engine.py:734)
- `is_audio_preloaded(file_path: str) -> bool` [function] (pyssp/audio_engine.py:742)
- `can_stream_without_preload(file_path: str) -> bool` [function] (pyssp/audio_engine.py:750)
- `can_decode_with_ffmpeg(file_path: str, timeout_ms: int = 180) -> bool` [function] (pyssp/audio_engine.py:755)
- `request_audio_preload(file_paths: List[str], prioritize: bool = False, force: bool = False) -> None` [function] (pyssp/audio_engine.py:786)
- `set_audio_preload_paused(paused: bool) -> None` [function] (pyssp/audio_engine.py:846)

### Internal

- `_utility_duration_frames(spec: UtilitySoundSpec, sample_rate: int) -> int` [function] (pyssp/audio_engine.py:71)
- `_hash_noise_values(values: np.ndarray, seed: int) -> np.ndarray` [function] (pyssp/audio_engine.py:75)
- `_generate_utility_samples(spec: UtilitySoundSpec, sample_positions: np.ndarray, sample_rate: int, channels: int) -> np.ndarray` [function] (pyssp/audio_engine.py:86)
- `_compute_waveform_peaks_from_utility(spec: UtilitySoundSpec, sample_count: int = 1024, sample_rate: int = 44100, channels: int = 2) -> List[float]` [function] (pyssp/audio_engine.py:136)
- `_shutdown_preload_executor() -> None` [function] (pyssp/audio_engine.py:153)
- `_shutdown_waveform_executor() -> None` [function] (pyssp/audio_engine.py:160)
- `_shutdown_media_load_executor() -> None` [function] (pyssp/audio_engine.py:167)
- `_shutdown_coreaudio_keepalive() -> None` [function] (pyssp/audio_engine.py:174)
- `_update_engine_output_meter(stream_id: int, left: float, right: float, *, mode: str = 'post_fader') -> None` [function] (pyssp/audio_engine.py:221)
- `_clear_engine_output_meter(stream_id: int) -> None` [function] (pyssp/audio_engine.py:225)
- `_coreaudio_keepalive_callback(outdata, frames, _time_info, _status) -> None` [function] (pyssp/audio_engine.py:262)
- `_coreaudio_keepalive_stream_kwargs(sample_rate: int, channels: int) -> dict` [function] (pyssp/audio_engine.py:266)
- `_retain_coreaudio_keepalive(sample_rate: int, channels: int) -> None` [function] (pyssp/audio_engine.py:285)
- `_release_coreaudio_keepalive() -> None` [function] (pyssp/audio_engine.py:300)
- `_default_waveform_cache_dir() -> str` [function] (pyssp/audio_engine.py:322)
- `_normalize_waveform_cache_limit_mb(limit_mb: int) -> int` [function] (pyssp/audio_engine.py:334)
- `_waveform_cache_usage_bytes_locked() -> int` [function] (pyssp/audio_engine.py:401)
- `_enforce_waveform_cache_limit_locked() -> None` [function] (pyssp/audio_engine.py:419)
- `_waveform_cache_path(file_path: str, sample_count: int) -> str` [function] (pyssp/audio_engine.py:452)
- `_load_waveform_peaks_from_disk(file_path: str, sample_count: int) -> Optional[List[float]]` [function] (pyssp/audio_engine.py:471)
- `_save_waveform_peaks_to_disk(file_path: str, sample_count: int, peaks: List[float]) -> None` [function] (pyssp/audio_engine.py:488)
- `_prime_waveform_disk_cache_from_frames(file_path: str, frames: np.ndarray) -> None` [function] (pyssp/audio_engine.py:515)
- `_ensure_decoder() -> None` [function] (pyssp/audio_engine.py:538)
- `_allocate_stream_id() -> int` [function] (pyssp/audio_engine.py:579)
- `_find_output_device_index(device_name: str) -> Optional[int]` [function] (pyssp/audio_engine.py:617)
- `_normalize_device_names(raw_names) -> List[str]` [function] (pyssp/audio_engine.py:631)
- `_dedupe(values: List[str]) -> List[str]` [function] (pyssp/audio_engine.py:644)
- `_preload_path_worker(file_path: str, force: bool = False) -> None` [function] (pyssp/audio_engine.py:833)
- `_store_preload_entry(file_path: str, frames: np.ndarray, duration_ms: int, force: bool = False) -> None` [function] (pyssp/audio_engine.py:858)
- `_evict_preload_cache_locked() -> None` [function] (pyssp/audio_engine.py:879)
- `_effective_limit_bytes_locked() -> int` [function] (pyssp/audio_engine.py:887)
- `_memory_reserve_bytes(total_bytes: int) -> int` [function] (pyssp/audio_engine.py:900)
- `_system_memory_bytes() -> Tuple[int, int]` [function] (pyssp/audio_engine.py:906)
- `_normalize_cache_key(file_path: str) -> str` [function] (pyssp/audio_engine.py:937)
- `_bytes_to_frames(raw: bytes, sample_size: int, channels: int) -> Optional[np.ndarray]` [function] (pyssp/audio_engine.py:943)
- `_decode_media_frames(file_path: str, prefer_ffmpeg: bool = False) -> Tuple[np.ndarray, int]` [function] (pyssp/audio_engine.py:963)
- `_decode_media_frames_with_ffmpeg(file_path: str, sample_rate: int, channels: int) -> Tuple[np.ndarray, int]` [function] (pyssp/audio_engine.py:983)
- `_prepare_media_source(file_path: str, sample_rate: int, channels: int, dsp_config: Optional[DSPConfig] = None) -> Tuple[Optional[np.ndarray], int, bool, Optional[FFmpegPCMStream]]` [function] (pyssp/audio_engine.py:1011)
- `_prepare_audio_source(source: object, sample_rate: int, channels: int, dsp_config: Optional[DSPConfig] = None) -> Tuple[Optional[np.ndarray], int, bool, Optional[FFmpegPCMStream], str, Optional[UtilitySoundSpec]]` [function] (pyssp/audio_engine.py:1036)
- `_load_sound_with_fallback(file_path: str)` [function] (pyssp/audio_engine.py:1055)
- `_find_mp3_frame_sync_offset(raw: bytes) -> int` [function] (pyssp/audio_engine.py:1075)
- `_peek_cached_media_frames(file_path: str) -> Optional[Tuple[np.ndarray, int]]` [function] (pyssp/audio_engine.py:1098)
- `_load_media_frames(file_path: str, prefer_ffmpeg: bool = False) -> Tuple[np.ndarray, int]` [function] (pyssp/audio_engine.py:1112)
- `_compute_waveform_peaks_from_frames(frames: Optional[np.ndarray], sample_count: int = 1024) -> List[float]` [function] (pyssp/audio_engine.py:1128)
- `_compute_waveform_peaks_from_path(file_path: str, sample_count: int = 1024) -> List[float]` [function] (pyssp/audio_engine.py:1161)

## Classes

### `_NullOutputStream`

- Defined at `pyssp/audio_engine.py:527`

#### Public Members

- `start(self) -> None` [method] (pyssp/audio_engine.py:528)
- `stop(self) -> None` [method] (pyssp/audio_engine.py:531)
- `close(self) -> None` [method] (pyssp/audio_engine.py:534)

### `ExternalMediaPlayer`

- Defined at `pyssp/audio_engine.py:1183`
- Bases: QObject

#### Public Members

- `setNotifyInterval(self, interval_ms: int) -> None` [method] (pyssp/audio_engine.py:1256)
- `setMedia(self, source: object, dsp_config: Optional[DSPConfig] = None) -> None` [method] (pyssp/audio_engine.py:1259)
- `setMediaAsync(self, source: object, dsp_config: Optional[DSPConfig] = None, request_id: Optional[int] = None) -> int` [method] (pyssp/audio_engine.py:1280)
- `setDSPConfig(self, dsp_config: DSPConfig) -> None` [method] (pyssp/audio_engine.py:1329)
- `play(self) -> None` [method] (pyssp/audio_engine.py:1333)
- `pause(self) -> None` [method] (pyssp/audio_engine.py:1359)
- `stop(self) -> None` [method] (pyssp/audio_engine.py:1380)
- `state(self) -> int` [method] (pyssp/audio_engine.py:1412)
- `setPosition(self, position_ms: int) -> None` [method] (pyssp/audio_engine.py:1416)
- `position(self) -> int` [method] (pyssp/audio_engine.py:1471)
- `enginePositionMs(self) -> int` [method] (pyssp/audio_engine.py:1475)
- `duration(self) -> int` [method] (pyssp/audio_engine.py:1492)
- `setVolume(self, volume: int) -> None` [method] (pyssp/audio_engine.py:1496)
- `volume(self) -> int` [method] (pyssp/audio_engine.py:1500)
- `setMasterVolume(self, volume: int) -> None` [method] (pyssp/audio_engine.py:1504)
- `masterVolume(self) -> int` [method] (pyssp/audio_engine.py:1508)
- `meterLevels(self) -> Tuple[float, float]` [method] (pyssp/audio_engine.py:1512)
- `sampleRate(self) -> int` [method] (pyssp/audio_engine.py:1516)
- `setOutputMonitorId(self, player_id: str) -> None` [method] (pyssp/audio_engine.py:1520)
- `outputMonitorId(self) -> str` [method] (pyssp/audio_engine.py:1528)
- `outputBlockSize(self) -> int` [method] (pyssp/audio_engine.py:1532)
- `takeOutputFrames(self, max_frames: int = 0, mode: str = 'post_fader') -> np.ndarray` [method] (pyssp/audio_engine.py:1536)
- `outputTapFrameCounts(self) -> Dict[str, int]` [method] (pyssp/audio_engine.py:1548)
- `waveformPeaks(self, sample_count: int = 1024) -> List[float]` [method] (pyssp/audio_engine.py:1557)
- `waveformPeaksAsync(self, sample_count: int = 1024) -> Future` [method] (pyssp/audio_engine.py:1576)

#### Internal Members

- `__init__(self, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/audio_engine.py:1194)
- `_waveform_from_frames_with_cache(file_path: str, frames: np.ndarray, sample_count: int) -> List[float]` [staticmethod] (pyssp/audio_engine.py:1595)
- `_detach_stream_decoder_locked(self) -> Optional[FFmpegPCMStream]` [method] (pyssp/audio_engine.py:1607)
- `_seek_stream_decoder_to_position(self, target_ms: int) -> bool` [method] (pyssp/audio_engine.py:1613)
- `_create_stream(self)` [method] (pyssp/audio_engine.py:1648)
- `_queue_declick_tail_locked(self) -> None` [method] (pyssp/audio_engine.py:1679)
- `_discard_declick_history_locked(self) -> None` [method] (pyssp/audio_engine.py:1699)
- `_arm_declick_fade_in_locked(self, frame_count: Optional[int] = None) -> None` [method] (pyssp/audio_engine.py:1709)
- `_apply_declick_fade_in_locked(self, block: np.ndarray) -> np.ndarray` [method] (pyssp/audio_engine.py:1715)
- `_emit_declick_tail_locked(self, outdata: np.ndarray, frames: int) -> bool` [method] (pyssp/audio_engine.py:1729)
- `_peak_levels_from_block(block: np.ndarray) -> Tuple[float, float]` [staticmethod] (pyssp/audio_engine.py:1761)
- `_apply_pending_dsp_config_locked(self) -> None` [method] (pyssp/audio_engine.py:1770)
- `_append_recent_output_locked(self, frames_block: np.ndarray) -> None` [method] (pyssp/audio_engine.py:1779)
- `_append_output_tap_locked(self, frames_block: np.ndarray, *, mode: str) -> None` [method] (pyssp/audio_engine.py:1795)
- `_fresh_start_fade_frames_for_media_locked(self, file_path: str) -> int` [method] (pyssp/audio_engine.py:1811)
- `_on_apply_prepared_media(self, payload: object) -> None` [method] (pyssp/audio_engine.py:1819)
- `_install_prepared_media(self, source: object, media_path: str, frames: Optional[np.ndarray], duration_ms: int, use_streaming: bool, new_decoder: Optional[FFmpegPCMStream], utility_spec: Optional[UtilitySoundSpec], dsp_config: Optional[DSPConfig]) -> None` [method] (pyssp/audio_engine.py:1849)
- `_audio_callback(self, outdata, frames, _time_info, status) -> None` [method] (pyssp/audio_engine.py:1905)
- `_read_source_block_locked(self, frames: int) -> Optional[np.ndarray]` [method] (pyssp/audio_engine.py:2041)
- `_read_utility_block_locked(self, frames: int) -> Optional[np.ndarray]` [method] (pyssp/audio_engine.py:2086)
- `_read_stream_block_locked(self, frames: int) -> Tuple[Optional[np.ndarray], int, bool]` [method] (pyssp/audio_engine.py:2108)
- `_tempo_ratio_locked(self) -> float` [method] (pyssp/audio_engine.py:2121)
- `_apply_pitch_ratio_block(self, block: np.ndarray, ratio: float) -> np.ndarray` [method] (pyssp/audio_engine.py:2124)
- `_bytes_to_frames(self, raw: bytes, sample_size: int, channels: int) -> Optional[np.ndarray]` [method] (pyssp/audio_engine.py:2135)
- `_position_from_source_pos_locked(self) -> int` [method] (pyssp/audio_engine.py:2138)
- `_poll(self) -> None` [method] (pyssp/audio_engine.py:2144)
- `_set_state_locked(self, new_state: int) -> None` [method] (pyssp/audio_engine.py:2161)
- `__del__(self) -> None` [method] (pyssp/audio_engine.py:2166)
