from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from PyQt5.QtGui import QImage

PlaybackSessionId = str
AudioBusId = Literal[
    "voice_pre",
    "voice_post",
    "program_pre",
    "program_post",
    "main_lr",
    "aux_ndi",
    "aux_monitor",
]
VideoDestinationId = Literal["local_program", "ndi_program", "monitor_program"]


@dataclass(frozen=True)
class RuntimeCommand:
    name: str
    session_id: Optional[PlaybackSessionId] = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.perf_counter)


@dataclass(frozen=True)
class RuntimeEvent:
    kind: str
    session_id: Optional[PlaybackSessionId] = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.perf_counter)


@dataclass(frozen=True)
class DestinationSceneConfig:
    destination_id: VideoDestinationId
    route_mode: str = "video"
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    overlays: tuple[str, ...] = ()
    transition_mode: str = "cut"


@dataclass(frozen=True)
class MediaProbeResult:
    source_path: str = ""
    duration_ms: int = 0
    has_audio: bool = False
    has_video: bool = False
    width: int = 0
    height: int = 0
    fps: float = 0.0
    rotation_deg: int = 0


@dataclass(frozen=True)
class FFmpegDecodeRequest:
    path: str
    kind: Literal["audio", "video"] = "audio"
    position_ms: int = 0
    frame_count: int = 0
    sample_rate: int = 48000
    channels: int = 2
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class TransportSnapshot:
    generated_at: float
    reference_session_id: Optional[PlaybackSessionId]
    active_session_ids: tuple[PlaybackSessionId, ...]
    playing_session_ids: tuple[PlaybackSessionId, ...]
    multi_play_enabled: bool
    position_ms: int = 0
    duration_ms: int = 0
    state: int = 0


@dataclass(frozen=True)
class EngineDiagnosticsSnapshot:
    generated_at: float
    session_count: int
    active_session_ids: tuple[PlaybackSessionId, ...]
    playing_session_ids: tuple[PlaybackSessionId, ...]
    reference_session_id: Optional[PlaybackSessionId]
    ffmpeg_available: bool
    ffmpeg_source: str
    ffmpeg_version: str
    audio_bus_ids: tuple[AudioBusId, ...]
    video_destination_ids: tuple[VideoDestinationId, ...]
    render_core: str = "legacy_player"
    audio_output_stream_active: bool = False
    audio_output_sample_rate: int = 0
    audio_output_channels: int = 0
    audio_output_blocksize: int = 0
    local_video_runtime_enabled: bool = False
    video_destinations: tuple["VideoDestinationSnapshot", ...] = ()


@dataclass(frozen=True)
class RuntimeSessionSnapshot:
    session_id: PlaybackSessionId
    runtime_id: int
    started_at: float
    state: int
    position_ms: int
    duration_ms: int
    slot_key: Optional[tuple[str, int, int]] = None


@dataclass(frozen=True)
class VideoDestinationSnapshot:
    destination_id: VideoDestinationId
    enabled: bool
    route_mode: str
    source_name: str
    width: int
    height: int
    fps: float
    audio_enabled: bool
    audio_tap_mode: str
    groups: str
    discovery_servers: str
    allowed_adapters: tuple[str, ...]
    multicast_enabled: bool
    multicast_ttl: int
    multicast_netmask: str
    multicast_netprefix: str
    sender_ready: bool
    connection_count: int
    has_current_frame: bool
    current_frame_width: int
    current_frame_height: int
    last_video_pts_ms: int
    last_video_source_path: str
    frame_submit_count: int
    video_send_count: int
    audio_send_count: int
    audio_drop_count: int
    audio_recovery_count: int
    last_audio_sample_rate: int
    last_audio_channel_count: int
    last_audio_mode: str = ""
    last_audio_error: str = ""
    last_network_config_error: str = ""
    last_network_config_path: str = ""


@dataclass(frozen=True)
class VideoSessionSnapshot:
    session_id: PlaybackSessionId
    source_path: str = ""
    configured: bool = False
    primed: bool = False
    state: int = 0
    position_ms: int = 0
    duration_ms: int = 0
    frame_pts_ms: int = 0
    frame_width: int = 0
    frame_height: int = 0
    backend_name: str = ""
    error: str = ""


@dataclass(frozen=True)
class VideoFrameSnapshot:
    session_id: PlaybackSessionId
    source_path: str = ""
    pts_ms: int = 0
    ready: bool = False
    image: QImage = field(default_factory=QImage)
