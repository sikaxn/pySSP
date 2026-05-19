from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from PyQt5.QtGui import QImage

from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.audio_engine import consume_output_monitor_chunk, list_output_monitor_players, mix_output_monitor_chunk
from pyssp.engine.ffmpeg import FFmpegEngineServices
from pyssp.engine.types import (
    AudioBusId,
    EngineDiagnosticsSnapshot,
    MediaProbeResult,
    PlaybackSessionId,
    RuntimeSessionSnapshot,
    TransportSnapshot,
    VideoDestinationId,
    VideoDestinationSnapshot,
)
from pyssp.ndi_output import NDIOutputConfig, NDIOutputDispatcher
from pyssp.ndi_support import NDICapabilityStatus

_DEFAULT_AUDIO_BUS_IDS: tuple[AudioBusId, ...] = (
    "voice_pre",
    "voice_post",
    "program_pre",
    "program_post",
    "main_lr",
    "aux_ndi",
    "aux_monitor",
)
_DEFAULT_VIDEO_DESTINATION_IDS: tuple[VideoDestinationId, ...] = (
    "local_program",
    "ndi_program",
    "monitor_program",
)


@dataclass
class _SessionRecord:
    session_id: PlaybackSessionId
    player: ExternalMediaPlayer
    started_order: int = -1
    started_at: float = 0.0
    state: int = ExternalMediaPlayer.StoppedState
    position_ms: int = 0
    duration_ms: int = 0
    slot_key: Optional[tuple[str, int, int]] = None


@dataclass
class _DestinationRecord:
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


@dataclass
class _RuntimeOutputStreamProxy:
    callback: Callable
    sample_rate: int
    channels: int
    stream_blocksize: int = 1024

    def _audio_callback(self, outdata, frames, time_info, status) -> None:
        self.callback(outdata, frames, time_info, status)

    @property
    def _sample_rate(self) -> int:
        return int(self.sample_rate)

    @property
    def _channels(self) -> int:
        return int(self.channels)

    @property
    def _stream_blocksize(self) -> int:
        return int(self.stream_blocksize)

    @_stream_blocksize.setter
    def _stream_blocksize(self, value: int) -> None:
        self.stream_blocksize = max(1, int(value))


class MediaRuntime:
    """Own the current media runtime while legacy players remain the execution node.

    This is the first compatibility-first cut of the rewrite plan: the runtime now
    owns session lifecycle, FFmpeg services, transport snapshots, and diagnostics,
    while existing `ExternalMediaPlayer` instances remain the v1 playback worker.
    """

    def __init__(
        self,
        *,
        player_factory: Optional[Callable[[], ExternalMediaPlayer]] = None,
        ffmpeg_services: Optional[FFmpegEngineServices] = None,
        audio_bus_ids: tuple[AudioBusId, ...] = _DEFAULT_AUDIO_BUS_IDS,
        video_destination_ids: tuple[VideoDestinationId, ...] = _DEFAULT_VIDEO_DESTINATION_IDS,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._player_factory = player_factory or ExternalMediaPlayer
        self._ffmpeg = ffmpeg_services or FFmpegEngineServices()
        self._audio_bus_ids = tuple(audio_bus_ids)
        self._video_destination_ids = tuple(video_destination_ids)
        self._clock = clock or time.perf_counter
        self._lock = threading.RLock()
        self._sessions: dict[PlaybackSessionId, _SessionRecord] = {}
        self._video_destinations: dict[VideoDestinationId, _DestinationRecord] = {
            destination_id: _DestinationRecord(destination_id=destination_id)
            for destination_id in self._video_destination_ids
        }
        self._audio_stream = None
        self._audio_stream_blocksize = 1024
        self._audio_sample_rate = 48000
        self._audio_channels = 2
        self._ndi_idle_phase = 0.0
        self._start_counter = 0
        self._multi_play_enabled = False
        self._ndi_dispatcher: Optional[NDIOutputDispatcher] = None
        self._ndi_status_signature: tuple[bool, str, str, str] = (False, "", "", "")
        self._destinations_wake = threading.Event()
        self._stop_destinations = threading.Event()
        self._destinations_thread = threading.Thread(
            target=self._destination_loop,
            name="pyssp-media-destinations",
            daemon=True,
        )
        self._destinations_thread.start()
        self._shutdown_complete = False

    @property
    def ffmpeg(self) -> FFmpegEngineServices:
        return self._ffmpeg

    def has_session(self, session_id: PlaybackSessionId) -> bool:
        with self._lock:
            return str(session_id) in self._sessions

    def create_legacy_session(self, session_id: PlaybackSessionId) -> ExternalMediaPlayer:
        token = str(session_id)
        with self._lock:
            existing = self._sessions.get(token)
            if existing is not None:
                return existing.player
            player = self._player_factory()
            record = _SessionRecord(session_id=token, player=player)
            self._sessions[token] = record
        try:
            player.setOutputMonitorId(token)
        except Exception:
            pass
        self._ensure_audio_output_stream_for_player(player)
        player.positionChanged.connect(lambda value, sid=token: self._on_position_changed(sid, value))
        player.durationChanged.connect(lambda value, sid=token: self._on_duration_changed(sid, value))
        player.stateChanged.connect(lambda value, sid=token: self._on_state_changed(sid, value))
        return player

    def player_for_session(self, session_id: PlaybackSessionId) -> ExternalMediaPlayer:
        with self._lock:
            record = self._sessions.get(str(session_id))
            if record is None:
                raise RuntimeError(f"Media session not found: {session_id}")
            return record.player

    def delete_session(self, session_id: PlaybackSessionId) -> bool:
        record: Optional[_SessionRecord]
        with self._lock:
            record = self._sessions.pop(str(session_id), None)
        if record is None:
            return False
        try:
            record.player.stop()
        except Exception:
            pass
        try:
            record.player.deleteLater()
        except Exception:
            pass
        return True

    def set_session_slot_key(self, session_id: PlaybackSessionId, slot_key: Optional[tuple[str, int, int]]) -> bool:
        with self._lock:
            record = self._sessions.get(str(session_id))
            if record is None:
                return False
            record.slot_key = tuple(slot_key) if slot_key is not None else None
            return True

    def session_snapshots(self) -> tuple[RuntimeSessionSnapshot, ...]:
        with self._lock:
            records = sorted(self._sessions.values(), key=lambda item: (item.started_order, item.session_id))
            return tuple(
                RuntimeSessionSnapshot(
                    session_id=record.session_id,
                    runtime_id=max(-1, int(record.started_order)),
                    started_at=float(record.started_at),
                    state=int(record.state),
                    position_ms=max(0, int(record.position_ms)),
                    duration_ms=max(0, int(record.duration_ms)),
                    slot_key=tuple(record.slot_key) if record.slot_key is not None else None,
                )
                for record in records
            )

    def video_destination_snapshots(self) -> tuple[VideoDestinationSnapshot, ...]:
        with self._lock:
            snapshots: list[VideoDestinationSnapshot] = []
            dispatcher = self._ndi_dispatcher
            for destination_id in self._video_destination_ids:
                record = self._video_destinations.get(destination_id, _DestinationRecord(destination_id=destination_id))
                frame = QImage(record.frame_image) if record.frame_image is not None else QImage()
                last_audio_mode = ""
                last_audio_error = ""
                audio_drop_count = 0
                audio_recovery_count = 0
                sender_ready = False
                if destination_id == "ndi_program" and dispatcher is not None:
                    sender_ready = bool(getattr(dispatcher, "available", False))
                    last_audio_mode = str(getattr(dispatcher, "_last_audio_mode", "") or "")
                    last_audio_error = str(getattr(dispatcher, "_last_audio_error", "") or "")
                    audio_drop_count = max(0, int(getattr(dispatcher, "_audio_drop_count", 0) or 0))
                    audio_recovery_count = max(0, int(getattr(dispatcher, "_audio_recovery_count", 0) or 0))
                    last_network_config_error = str(getattr(dispatcher, "_last_network_config_error", "") or "")
                    last_network_config_path = str(getattr(dispatcher, "_last_network_config_path", "") or "")
                else:
                    last_network_config_error = ""
                    last_network_config_path = ""
                snapshots.append(
                    VideoDestinationSnapshot(
                        destination_id=destination_id,
                        enabled=bool(record.enabled),
                        route_mode=str(record.route_mode or "blank"),
                        source_name=str(record.source_name or ""),
                        width=max(0, int(record.width)),
                        height=max(0, int(record.height)),
                        fps=max(0.0, float(record.fps)),
                        audio_enabled=bool(record.audio_enabled),
                        audio_tap_mode=str(record.audio_tap_mode or "post_fader"),
                        groups=str(record.groups or "Public"),
                        discovery_servers=str(record.discovery_servers or ""),
                        allowed_adapters=tuple(record.allowed_adapters),
                        multicast_enabled=bool(record.multicast_enabled),
                        multicast_ttl=max(1, int(record.multicast_ttl)),
                        multicast_netmask=str(record.multicast_netmask or "255.255.0.0"),
                        multicast_netprefix=str(record.multicast_netprefix or "239.255.0.0"),
                        sender_ready=sender_ready,
                        connection_count=max(0, int(record.connection_count)),
                        has_current_frame=not frame.isNull(),
                        current_frame_width=max(0, int(frame.width())),
                        current_frame_height=max(0, int(frame.height())),
                        last_video_pts_ms=max(0, int(record.last_video_pts_ms)),
                        last_video_source_path=str(record.last_video_source_path or ""),
                        frame_submit_count=max(0, int(record.frame_submit_count)),
                        video_send_count=max(0, int(record.video_send_count)),
                        audio_send_count=max(0, int(record.audio_send_count)),
                        audio_drop_count=audio_drop_count,
                        audio_recovery_count=audio_recovery_count,
                        last_audio_sample_rate=max(1, int(record.last_audio_sample_rate)),
                        last_audio_channel_count=max(1, int(record.last_audio_channel_count)),
                        last_audio_mode=last_audio_mode,
                        last_audio_error=last_audio_error,
                        last_network_config_error=last_network_config_error,
                        last_network_config_path=last_network_config_path,
                    )
                )
            return tuple(snapshots)

    def shutdown(self) -> None:
        with self._lock:
            if self._shutdown_complete:
                return
            self._shutdown_complete = True
        self._stop_destinations.set()
        self._destinations_wake.set()
        try:
            self._destinations_thread.join(timeout=1.5)
        except Exception:
            pass
        self._shutdown_audio_output_stream()
        dispatcher: Optional[NDIOutputDispatcher]
        with self._lock:
            dispatcher = self._ndi_dispatcher
            self._ndi_dispatcher = None
        if dispatcher is not None:
            try:
                dispatcher.shutdown()
            except Exception:
                pass
        with self._lock:
            session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            self.delete_session(session_id)
        self._ffmpeg.shutdown()

    def set_multi_play_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._multi_play_enabled = bool(enabled)

    def transport_snapshot(self) -> TransportSnapshot:
        with self._lock:
            return self._transport_snapshot_locked()

    def diagnostics_snapshot(self) -> EngineDiagnosticsSnapshot:
        with self._lock:
            snapshot = self._transport_snapshot_locked()
        return EngineDiagnosticsSnapshot(
            generated_at=self._clock(),
            session_count=len(self._sessions),
            active_session_ids=snapshot.active_session_ids,
            playing_session_ids=snapshot.playing_session_ids,
            reference_session_id=snapshot.reference_session_id,
            ffmpeg_available=self._ffmpeg.available(),
            ffmpeg_source=self._ffmpeg.source(),
            ffmpeg_version=self._ffmpeg.version_text(),
            audio_bus_ids=self._audio_bus_ids,
            video_destination_ids=self._video_destination_ids,
            render_core="runtime_shared_mix_graph_v1",
            audio_output_stream_active=self._audio_stream is not None,
            audio_output_sample_rate=max(0, int(self._audio_sample_rate)),
            audio_output_channels=max(0, int(self._audio_channels)),
            audio_output_blocksize=max(0, int(self._audio_stream_blocksize)),
            local_video_runtime_enabled=True,
            video_destinations=self.video_destination_snapshots(),
        )

    def probe_media(self, path: str) -> MediaProbeResult:
        return self._ffmpeg.probe_media_info(path)

    def _ensure_audio_output_stream_for_player(self, player: ExternalMediaPlayer) -> None:
        with self._lock:
            if self._audio_stream is not None:
                return
            try:
                self._audio_sample_rate = max(1, int(player.sampleRate()))
            except Exception:
                self._audio_sample_rate = 48000
            self._audio_channels = max(1, int(getattr(player, "_channels", self._audio_channels) or self._audio_channels))
            proxy = _RuntimeOutputStreamProxy(
                callback=self._audio_output_callback,
                sample_rate=self._audio_sample_rate,
                channels=self._audio_channels,
                stream_blocksize=1024,
            )
            stream = ExternalMediaPlayer._create_stream(proxy)
            self._audio_stream = stream
            self._audio_stream_blocksize = max(1, int(proxy._stream_blocksize))
        try:
            self._audio_stream.start()
        except Exception:
            pass

    def _shutdown_audio_output_stream(self) -> None:
        stream = None
        with self._lock:
            stream = self._audio_stream
            self._audio_stream = None
        if stream is None:
            return
        try:
            stream.stop()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass

    def _audio_output_callback(self, outdata, frames, _time_info, _status) -> None:
        frame_count = max(0, int(frames))
        if frame_count <= 0:
            return
        outdata.fill(0.0)
        if not self._lock.acquire(blocking=False):
            return
        try:
            active_players: list[ExternalMediaPlayer] = []
            for record in self._sessions.values():
                try:
                    if record.player.wantsAudioRender():
                        active_players.append(record.player)
                except Exception:
                    continue
        finally:
            self._lock.release()
        if not active_players:
            self._service_ndi_audio_from_render(frame_count)
            return
        mixed = np.zeros((frame_count, self._audio_channels), dtype=np.float32)
        for player in active_players:
            try:
                block = np.asarray(player.renderAudioBlock(frame_count), dtype=np.float32)
            except Exception:
                continue
            if block.ndim != 2 or len(block) <= 0:
                continue
            channels = min(int(block.shape[1]), int(mixed.shape[1]))
            take = min(int(len(block)), frame_count)
            if take <= 0 or channels <= 0:
                continue
            mixed[:take, :channels] += block[:take, :channels]
        np.clip(mixed, -1.0, 1.0, out=mixed)
        outdata[:frame_count, : mixed.shape[1]] = mixed
        self._service_ndi_audio_from_render(frame_count, mixed_post_fader=mixed)

    def _configure_ndi_destination_locked(
        self,
        record: _DestinationRecord,
        ndi_status: Optional[NDICapabilityStatus],
    ) -> None:
        if record.destination_id != "ndi_program":
            return
        enabled = bool(record.enabled and ndi_status is not None and ndi_status.ready and ndi_status.runtime_library_path)
        signature = (
            bool(getattr(ndi_status, "ready", False)),
            str(getattr(ndi_status, "runtime_library_path", "") or ""),
            str(getattr(ndi_status, "ndi_runtime_version", "") or ""),
            str(getattr(ndi_status, "ndi_backend_name", "") or ""),
        )
        if not enabled:
            dispatcher = self._ndi_dispatcher
            self._ndi_dispatcher = None
            self._ndi_status_signature = (False, "", "", "")
            record.connection_count = 0
            if dispatcher is not None:
                try:
                    dispatcher.stop()
                except Exception:
                    pass
            return
        if self._ndi_dispatcher is None or self._ndi_status_signature != signature:
            old_dispatcher = self._ndi_dispatcher
            self._ndi_dispatcher = NDIOutputDispatcher(ndi_status)
            self._ndi_status_signature = signature
            if old_dispatcher is not None:
                try:
                    old_dispatcher.shutdown()
                except Exception:
                    pass
        dispatcher = self._ndi_dispatcher
        if dispatcher is None:
            return
        config = NDIOutputConfig(
            source_name=record.source_name,
            width=record.width,
            height=record.height,
            fps=record.fps,
            audio_enabled=bool(record.audio_enabled),
            groups=str(record.groups or "Public"),
            discovery_servers=str(record.discovery_servers or ""),
            allowed_adapters=tuple(record.allowed_adapters),
            multicast_enabled=bool(record.multicast_enabled),
            multicast_ttl=max(1, int(record.multicast_ttl)),
            multicast_netmask=str(record.multicast_netmask or "255.255.0.0"),
            multicast_netprefix=str(record.multicast_netprefix or "239.255.0.0"),
        )
        dispatcher.configure(config)

    def _destination_loop(self) -> None:
        last_connection_poll = 0.0
        while not self._stop_destinations.is_set():
            self._destinations_wake.wait(timeout=0.01)
            self._destinations_wake.clear()
            now = self._clock()
            dispatcher: Optional[NDIOutputDispatcher]
            with self._lock:
                record = self._video_destinations.get("ndi_program")
                dispatcher = self._ndi_dispatcher
                if record is None or dispatcher is None or (not record.enabled):
                    continue
                frame_interval_sec = max(1.0 / max(1.0, float(record.fps)), 0.005)
                should_send_video = (
                    record.frame_image is not None
                    and (now - float(record.last_video_sent_at)) >= frame_interval_sec
                )
                frame = QImage(record.frame_image) if should_send_video and record.frame_image is not None else QImage()
                last_video_pts_ms = int(record.last_video_pts_ms)
            if should_send_video and not frame.isNull():
                try:
                    sent = bool(dispatcher.send_video_frame(frame))
                except Exception:
                    sent = False
                if sent:
                    with self._lock:
                        record = self._video_destinations.get("ndi_program")
                        if record is not None:
                            record.video_send_count += 1
                            record.last_video_sent_at = now
                            record.last_video_pts_ms = last_video_pts_ms
            if (now - last_connection_poll) >= 0.25:
                last_connection_poll = now
                try:
                    connection_count = max(0, int(dispatcher.get_num_connections(0.0)))
                except Exception:
                    connection_count = 0
                with self._lock:
                    record = self._video_destinations.get("ndi_program")
                    if record is not None:
                            record.connection_count = connection_count

    def _ordered_output_monitor_players_locked(self, mode: str) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        transport = self._transport_snapshot_locked()
        for session_id in transport.playing_session_ids:
            if session_id in seen:
                continue
            seen.add(session_id)
            ordered.append(session_id)
        for player_id in list_output_monitor_players(mode):
            token = str(player_id or "").strip()
            if not token or token in seen:
                continue
            seen.add(token)
            ordered.append(token)
        return ordered

    def _service_ndi_audio_from_render(self, frames: int, mixed_post_fader: Optional[np.ndarray] = None) -> None:
        frame_count = max(0, int(frames))
        if frame_count <= 0:
            return
        with self._lock:
            record = self._video_destinations.get("ndi_program")
            dispatcher = self._ndi_dispatcher
            if record is None or dispatcher is None or (not record.enabled) or (not record.audio_enabled):
                return
            mode = str(record.audio_tap_mode or "post_fader")
            sample_rate = max(1, int(getattr(self, "_audio_sample_rate", record.last_audio_sample_rate or 48000) or 48000))
            channel_count = max(
                1,
                int(getattr(self, "_audio_channels", record.last_audio_channel_count or 2) or 2),
            )
        chunk = None
        consume_map: dict[str, int] = {}
        if mode == "post_fader" and mixed_post_fader is not None:
            direct = np.asarray(mixed_post_fader, dtype=np.float32)
            if direct.ndim == 2 and len(direct) > 0 and direct.shape[1] > 0:
                chunk = np.ascontiguousarray(direct[:frame_count, :], dtype=np.float32)
                channel_count = int(chunk.shape[1])
        else:
            ordered_player_ids = self._ordered_output_monitor_players_locked(mode)
            if ordered_player_ids:
                mixed = mix_output_monitor_chunk(ordered_player_ids, target_frames=frame_count, mode=mode)
                if mixed is not None:
                    mixed_chunk, mixed_consume_map = mixed
                    if mixed_chunk.ndim == 2 and len(mixed_chunk) > 0 and mixed_chunk.shape[1] > 0:
                        chunk = np.ascontiguousarray(mixed_chunk, dtype=np.float32)
                        channel_count = int(chunk.shape[1])
                        consume_map = dict(mixed_consume_map)
        if chunk is None:
            chunk = self._ndi_idle_audio_block(frame_count, channel_count, sample_rate)
        elif not np.any(np.abs(chunk) > 1.0e-7):
            chunk = self._ndi_idle_audio_block(frame_count, channel_count, sample_rate)
        sent = False
        if chunk.ndim == 2 and len(chunk) > 0 and chunk.shape[1] > 0:
            try:
                sent = bool(dispatcher.send_audio_frames(chunk, sample_rate))
            except Exception:
                sent = False
        if sent and consume_map:
            consume_output_monitor_chunk(consume_map, mode=mode)
        now = self._clock()
        with self._lock:
            record = self._video_destinations.get("ndi_program")
            if record is None:
                return
            record.last_audio_sent_at = now
            record.last_audio_sample_rate = sample_rate
            record.last_audio_channel_count = channel_count
            if sent:
                record.audio_send_count += 1

    def _ndi_idle_audio_block(self, frames: int, channel_count: int, sample_rate: int) -> np.ndarray:
        frame_count = max(1, int(frames))
        channels = max(1, int(channel_count))
        sr = max(1, int(sample_rate))
        amplitude = 5.0e-4
        frequency_hz = 997.0
        phase_step = (2.0 * np.pi * frequency_hz) / float(sr)
        phase = float(self._ndi_idle_phase)
        angles = phase + (np.arange(frame_count, dtype=np.float32) * phase_step)
        tone = (np.sin(angles) * amplitude).astype(np.float32, copy=False)
        self._ndi_idle_phase = float((phase + (frame_count * phase_step)) % (2.0 * np.pi))
        return np.repeat(tone[:, np.newaxis], channels, axis=1)

    def configure_video_destination(
        self,
        destination_id: VideoDestinationId,
        *,
        enabled: bool,
        route_mode: str,
        width: int,
        height: int,
        fps: float,
        source_name: str = "",
        audio_enabled: bool = False,
        audio_tap_mode: str = "post_fader",
        groups: str = "Public",
        discovery_servers: str = "",
        allowed_adapters: tuple[str, ...] = (),
        multicast_enabled: bool = False,
        multicast_ttl: int = 1,
        multicast_netmask: str = "255.255.0.0",
        multicast_netprefix: str = "239.255.0.0",
        ndi_status: Optional[NDICapabilityStatus] = None,
    ) -> bool:
        destination_token = str(destination_id)
        if destination_token not in self._video_destinations:
            return False
        with self._lock:
            record = self._video_destinations[destination_token]
            record.enabled = bool(enabled)
            record.route_mode = str(route_mode or "blank")
            record.source_name = str(source_name or "pyssp-video").strip() or "pyssp-video"
            record.width = max(2, int(width))
            record.height = max(2, int(height))
            record.fps = max(1.0, float(fps))
            record.audio_enabled = bool(audio_enabled)
            record.audio_tap_mode = str(audio_tap_mode or "post_fader").strip().lower() or "post_fader"
            record.groups = str(groups or "Public").strip() or "Public"
            record.discovery_servers = str(discovery_servers or "").strip()
            record.allowed_adapters = tuple(str(item or "").strip() for item in allowed_adapters if str(item or "").strip())
            record.multicast_enabled = bool(multicast_enabled)
            record.multicast_ttl = max(1, min(255, int(multicast_ttl)))
            record.multicast_netmask = str(multicast_netmask or "255.255.0.0").strip() or "255.255.0.0"
            record.multicast_netprefix = str(multicast_netprefix or "239.255.0.0").strip() or "239.255.0.0"
            self._configure_ndi_destination_locked(record, ndi_status)
        self._destinations_wake.set()
        return True

    def submit_video_destination_frame(
        self,
        destination_id: VideoDestinationId,
        image: QImage,
        *,
        route_mode: Optional[str] = None,
        pts_ms: int = 0,
        source_path: str = "",
    ) -> bool:
        destination_token = str(destination_id)
        if destination_token not in self._video_destinations or image.isNull():
            return False
        with self._lock:
            record = self._video_destinations[destination_token]
            if route_mode is not None:
                record.route_mode = str(route_mode or record.route_mode or "blank")
            record.frame_image = image.copy()
            record.last_video_pts_ms = max(0, int(pts_ms))
            record.last_video_source_path = str(source_path or "").strip()
            record.frame_submit_count += 1
        self._destinations_wake.set()
        return True

    def clear_video_destination_frame(self, destination_id: VideoDestinationId) -> bool:
        destination_token = str(destination_id)
        if destination_token not in self._video_destinations:
            return False
        with self._lock:
            record = self._video_destinations[destination_token]
            record.frame_image = None
            record.last_video_pts_ms = 0
            record.last_video_source_path = ""
        return True

    def video_destination_frame(self, destination_id: VideoDestinationId) -> QImage:
        destination_token = str(destination_id)
        with self._lock:
            record = self._video_destinations.get(destination_token)
            if record is None or record.frame_image is None:
                return QImage()
            return QImage(record.frame_image)

    def _on_position_changed(self, session_id: PlaybackSessionId, value: int) -> None:
        with self._lock:
            record = self._sessions.get(str(session_id))
            if record is None:
                return
            record.position_ms = max(0, int(value))

    def _on_duration_changed(self, session_id: PlaybackSessionId, value: int) -> None:
        with self._lock:
            record = self._sessions.get(str(session_id))
            if record is None:
                return
            record.duration_ms = max(0, int(value))

    def _on_state_changed(self, session_id: PlaybackSessionId, value: int) -> None:
        with self._lock:
            record = self._sessions.get(str(session_id))
            if record is None:
                return
            next_state = int(value)
            if next_state == ExternalMediaPlayer.PlayingState and record.state != ExternalMediaPlayer.PlayingState:
                record.started_order = self._start_counter
                record.started_at = self._clock()
                self._start_counter += 1
            record.state = next_state
            if next_state == ExternalMediaPlayer.StoppedState:
                record.position_ms = 0

    def _transport_snapshot_locked(self) -> TransportSnapshot:
        active_ids: list[PlaybackSessionId] = []
        playing_records: list[_SessionRecord] = []
        for session_id, record in self._sessions.items():
            if self._record_is_active(record):
                active_ids.append(session_id)
            if record.state == ExternalMediaPlayer.PlayingState:
                playing_records.append(record)
        reference: Optional[_SessionRecord] = None
        if playing_records:
            if self._multi_play_enabled:
                reference = min(playing_records, key=lambda item: (item.started_order, item.started_at, item.session_id))
            else:
                reference = max(playing_records, key=lambda item: (item.started_order, item.started_at, item.session_id))
        return TransportSnapshot(
            generated_at=self._clock(),
            reference_session_id=reference.session_id if reference is not None else None,
            active_session_ids=tuple(sorted(active_ids)),
            playing_session_ids=tuple(sorted(item.session_id for item in playing_records)),
            multi_play_enabled=bool(self._multi_play_enabled),
            position_ms=max(0, int(reference.position_ms)) if reference is not None else 0,
            duration_ms=max(0, int(reference.duration_ms)) if reference is not None else 0,
            state=int(reference.state) if reference is not None else ExternalMediaPlayer.StoppedState,
        )

    @staticmethod
    def _record_is_active(record: _SessionRecord) -> bool:
        return (
            record.state in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}
            or record.position_ms > 0
            or record.duration_ms > 0
        )
