from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt5.QtGui import QImage

from pyssp.engine.types import VideoDestinationId


@dataclass
class PlaybackV2DestinationState:
    destination_id: VideoDestinationId
    enabled: bool = False
    route_mode: str = "blank"
    source_name: str = "pyssp-video"
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    audio_enabled: bool = False
    audio_tap_mode: str = "post_fader"
    groups: str = "Public"
    discovery_servers: str = ""
    allowed_adapters: tuple[str, ...] = ()
    multicast_enabled: bool = False
    multicast_ttl: int = 1
    multicast_netmask: str = "255.255.0.0"
    multicast_netprefix: str = "239.255.0.0"
    frame_image: Optional[QImage] = None
    last_video_pts_ms: int = 0
    last_video_source_path: str = ""
    frame_submit_count: int = 0
    video_send_count: int = 0
    audio_send_count: int = 0
    last_audio_sample_rate: int = 48000
    last_audio_channel_count: int = 2
    connection_count: int = 0
    last_video_sent_at: float = 0.0
    last_audio_sent_at: float = 0.0
