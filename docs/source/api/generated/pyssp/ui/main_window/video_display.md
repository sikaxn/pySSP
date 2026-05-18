# `pyssp/ui/main_window/video_display.py`

- Source: `pyssp/ui/main_window/video_display.py`
- Module path: `pyssp.ui.main_window.video_display`
- API entries: `4`

## Module Docstring

No module docstring.

## Functions

### Internal

- `_video_subprocess_platform_kwargs() -> dict` [function] (pyssp/ui/main_window/video_display.py:296)

## Classes

### `_VideoDecodeRequest`

- Defined at `pyssp/ui/main_window/video_display.py:19`

### `_VideoFrameDecodeDispatcher`

- Defined at `pyssp/ui/main_window/video_display.py:29`
- Bases: QObject

#### Public Members

- `request_stream(self, tag: int, path: str, start_ms: int, width: int, height: int, interval_ms: int) -> None` [method] (pyssp/ui/main_window/video_display.py:44)
- `request_frame(self, tag: int, path: str, position_ms: int, width: int, height: int) -> None` [method] (pyssp/ui/main_window/video_display.py:60)
- `clear(self) -> None` [method] (pyssp/ui/main_window/video_display.py:76)
- `take_latest_frame(self) -> Optional[tuple[int, str, int, int, int, bytes]]` [method] (pyssp/ui/main_window/video_display.py:79)
- `stop(self, timeout_sec: float = 1.5) -> None` [method] (pyssp/ui/main_window/video_display.py:95)

#### Internal Members

- `__init__(self, parent: Optional[QObject] = None) -> None` [constructor] (pyssp/ui/main_window/video_display.py:32)
- `_set_request(self, request: Optional[_VideoDecodeRequest]) -> None` [method] (pyssp/ui/main_window/video_display.py:86)
- `_run(self) -> None` [method] (pyssp/ui/main_window/video_display.py:107)
- `_run_single_frame(self, request: _VideoDecodeRequest, generation: int) -> None` [method] (pyssp/ui/main_window/video_display.py:124)
- `_run_stream(self, request: _VideoDecodeRequest, generation: int) -> None` [method] (pyssp/ui/main_window/video_display.py:130)
- `_is_stale(self, generation: int) -> bool` [method] (pyssp/ui/main_window/video_display.py:153)
- `_start_stream_process(self, request: _VideoDecodeRequest) -> Optional[subprocess.Popen]` [method] (pyssp/ui/main_window/video_display.py:157)
- `_decode_frame_bytes(request: _VideoDecodeRequest) -> bytes` [staticmethod] (pyssp/ui/main_window/video_display.py:202)
- `_read_exact(stream, byte_count: int) -> bytes` [staticmethod] (pyssp/ui/main_window/video_display.py:244)
- `_terminate_process_locked(self) -> None` [method] (pyssp/ui/main_window/video_display.py:257)
- `_publish_frame(self, tag: int, path: str, pts_ms: int, width: int, height: int, payload: bytes) -> None` [method] (pyssp/ui/main_window/video_display.py:278)

### `VideoDisplayMixin`

- Defined at `pyssp/ui/main_window/video_display.py:310`

#### Internal Members

- `_slot_allows_video_loading(slot: Optional[SoundButtonData]) -> bool` [staticmethod] (pyssp/ui/main_window/video_display.py:312)
- `_path_may_have_video(self, path: str) -> bool` [method] (pyssp/ui/main_window/video_display.py:315)
- `_build_video_control_dock(self) -> None` [method] (pyssp/ui/main_window/video_display.py:324)
- `_on_video_control_dock_visibility_changed(self, visible: bool) -> None` [method] (pyssp/ui/main_window/video_display.py:389)
- `_toggle_video_control_panel(self) -> None` [method] (pyssp/ui/main_window/video_display.py:398)
- `_on_video_display_route_changed(self, _index: int = 0) -> None` [method] (pyssp/ui/main_window/video_display.py:406)
- `_open_video_display(self) -> None` [method] (pyssp/ui/main_window/video_display.py:413)
- `_on_video_display_destroyed(self, _obj = None) -> None` [method] (pyssp/ui/main_window/video_display.py:423)
- `_normalized_media_probe_key(self, path: str) -> str` [method] (pyssp/ui/main_window/video_display.py:426)
- `_media_probe_for_path(self, path: str) -> MediaProbeInfo` [method] (pyssp/ui/main_window/video_display.py:429)
- `_slot_has_video_media(self, slot: Optional[SoundButtonData]) -> bool` [method] (pyssp/ui/main_window/video_display.py:443)
- `_current_video_slot_and_probe(self) -> tuple[Optional[SoundButtonData], MediaProbeInfo]` [method] (pyssp/ui/main_window/video_display.py:453)
- `_active_video_route_mode(self) -> str` [method] (pyssp/ui/main_window/video_display.py:466)
- `_active_ndi_route_mode(self) -> str` [method] (pyssp/ui/main_window/video_display.py:475)
- `_video_frame_interval_ms(self, info: Optional[MediaProbeInfo] = None) -> int` [method] (pyssp/ui/main_window/video_display.py:478)
- `_default_video_backdrop_path(self) -> str` [method] (pyssp/ui/main_window/video_display.py:490)
- `_resolved_video_backdrop_path(self) -> str` [method] (pyssp/ui/main_window/video_display.py:499)
- `_video_backdrop_pixmap(self) -> QPixmap` [method] (pyssp/ui/main_window/video_display.py:510)
- `_video_backdrop_message_text(self) -> str` [method] (pyssp/ui/main_window/video_display.py:524)
- `_video_output_dimensions(self, info: Optional[MediaProbeInfo]) -> tuple[int, int]` [method] (pyssp/ui/main_window/video_display.py:532)
- `_video_decode_dimensions(self, info: Optional[MediaProbeInfo]) -> tuple[int, int]` [method] (pyssp/ui/main_window/video_display.py:542)
- `_next_video_request_tag(self) -> int` [method] (pyssp/ui/main_window/video_display.py:549)
- `_video_target_surface_pixel_size(self) -> tuple[int, int]` [method] (pyssp/ui/main_window/video_display.py:553)
- `_video_snapshot_target_pixel_size(self) -> tuple[int, int]` [method] (pyssp/ui/main_window/video_display.py:577)
- `_video_target_decode_dimensions(self, info: Optional[MediaProbeInfo]) -> tuple[int, int]` [method] (pyssp/ui/main_window/video_display.py:603)
- `_on_video_surface_geometry_changed(self) -> None` [method] (pyssp/ui/main_window/video_display.py:621)
- `_invalidate_video_playback_sync(self, *, refresh: bool = False) -> None` [method] (pyssp/ui/main_window/video_display.py:630)
- `_video_frame_bucket_ms(self, position_ms: int, info: Optional[MediaProbeInfo] = None) -> int` [method] (pyssp/ui/main_window/video_display.py:636)
- `_video_display_target_visible(self) -> bool` [method] (pyssp/ui/main_window/video_display.py:640)
- `_current_video_display_position_ms(self) -> int` [method] (pyssp/ui/main_window/video_display.py:648)
- `_video_frame_pixmap(self, path: str, position_ms: int) -> QPixmap` [method] (pyssp/ui/main_window/video_display.py:669)
- `_render_widget_snapshot(self, widget: QWidget, width: int = 960, height: int = 540) -> QPixmap` [method] (pyssp/ui/main_window/video_display.py:681)
- `_render_widget_image(self, widget: QWidget, width: int, height: int) -> QImage` [method] (pyssp/ui/main_window/video_display.py:688)
- `_video_snapshot_dimensions(self) -> tuple[int, int]` [method] (pyssp/ui/main_window/video_display.py:697)
- `_render_stage_display_snapshot(self, target_width: Optional[int] = None, target_height: Optional[int] = None) -> QPixmap` [method] (pyssp/ui/main_window/video_display.py:703)
- `_render_lyric_display_snapshot(self, target_width: Optional[int] = None, target_height: Optional[int] = None) -> QPixmap` [method] (pyssp/ui/main_window/video_display.py:755)
- `_video_display_lyric_role_styles(self) -> dict[str, dict[str, object]]` [method] (pyssp/ui/main_window/video_display.py:791)
- `_current_video_lyric_html(self) -> str` [method] (pyssp/ui/main_window/video_display.py:823)
- `_sync_output_surface_widget(self, widget: Optional[VideoDisplayWidget], mode: str, *, force: bool = False) -> None` [method] (pyssp/ui/main_window/video_display.py:850)
- `_sync_video_surface_widget(self, widget: Optional[VideoDisplayWidget], *, force: bool = False) -> None` [method] (pyssp/ui/main_window/video_display.py:877)
- `_ndi_output_dimensions(self) -> tuple[int, int]` [method] (pyssp/ui/main_window/video_display.py:880)
- `_sync_ndi_timer_intervals(self) -> None` [method] (pyssp/ui/main_window/video_display.py:893)
- `_ensure_ndi_preview_widget(self) -> VideoDisplayWidget` [method] (pyssp/ui/main_window/video_display.py:923)
- `_current_ndi_video_frame_image(self) -> QImage` [method] (pyssp/ui/main_window/video_display.py:931)
- `_render_ndi_frame_image(self) -> QImage` [method] (pyssp/ui/main_window/video_display.py:940)
- `_ndi_audio_players(self) -> List[ExternalMediaPlayer]` [method] (pyssp/ui/main_window/video_display.py:960)
- `_ndi_sender_has_receivers(self) -> bool` [method] (pyssp/ui/main_window/video_display.py:997)
- `_ndi_audio_output_block_frames(self) -> int` [method] (pyssp/ui/main_window/video_display.py:1003)
- `_ndi_audio_target_frames(self, sample_rate: int) -> int` [method] (pyssp/ui/main_window/video_display.py:1021)
- `_ndi_audio_send_silence_keepalive(self, sender: object, *, sample_rate: int, channel_count: int) -> bool` [method] (pyssp/ui/main_window/video_display.py:1025)
- `_configure_ndi_sender(self) -> bool` [method] (pyssp/ui/main_window/video_display.py:1042)
- `_send_ndi_audio(self) -> None` [method] (pyssp/ui/main_window/video_display.py:1070)
- `_refresh_ndi_output(self, force: bool = False) -> None` [method] (pyssp/ui/main_window/video_display.py:1132)
- `_tick_ndi_refresh(self) -> None` [method] (pyssp/ui/main_window/video_display.py:1157)
- `_tick_ndi_audio_refresh(self) -> None` [method] (pyssp/ui/main_window/video_display.py:1160)
- `_apply_video_frame_to_targets(self) -> None` [method] (pyssp/ui/main_window/video_display.py:1165)
- `_clear_video_frame_runtime(self, preserve_current_frame: bool = False) -> None` [method] (pyssp/ui/main_window/video_display.py:1175)
- `_queue_video_frame_refresh(self, *, force: bool = False) -> None` [method] (pyssp/ui/main_window/video_display.py:1198)
- `_tick_video_refresh(self) -> None` [method] (pyssp/ui/main_window/video_display.py:1275)
- `_on_video_frame_ready(self) -> None` [method] (pyssp/ui/main_window/video_display.py:1280)
- `_on_video_frame_decoded(self, tag: int, path: str, bucket_ms: int, width: int, height: int, payload: bytes) -> None` [method] (pyssp/ui/main_window/video_display.py:1292)
- `_refresh_video_display(self, force: bool = False) -> None` [method] (pyssp/ui/main_window/video_display.py:1353)
- `_slot_or_media_has_audio(self, slot: Optional[SoundButtonData]) -> bool` [method] (pyssp/ui/main_window/video_display.py:1369)
- `_silent_video_source_payload(self, slot: SoundButtonData) -> Optional[dict]` [method] (pyssp/ui/main_window/video_display.py:1381)
