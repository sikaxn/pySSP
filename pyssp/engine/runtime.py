from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from PyQt5.QtGui import QImage

from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.audio_engine import consume_output_monitor_chunk, list_output_monitor_players, mix_output_monitor_chunk, output_monitor_frame_counts
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
                    )
                )
            return tuple(snapshots)

    def shutdown(self) -> None:
        self._stop_destinations.set()
        self._destinations_wake.set()
        try:
            self._destinations_thread.join(timeout=1.5)
        except Exception:
            pass
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
            video_destinations=self.video_destination_snapshots(),
        )

    def probe_media(self, path: str) -> MediaProbeResult:
        return self._ffmpeg.probe_media_info(path)

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
                audio_enabled = bool(record.audio_enabled)
                audio_tap_mode = str(record.audio_tap_mode or "post_fader")
                audio_interval_sec = self._destination_audio_interval_locked(record)
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
            if audio_enabled:
                with self._lock:
                    record = self._video_destinations.get("ndi_program")
                    should_send_audio = record is not None and (now - float(record.last_audio_sent_at)) >= audio_interval_sec
                if should_send_audio:
                    self._service_ndi_audio(dispatcher, audio_tap_mode, now)
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

    def _destination_audio_interval_locked(self, record: _DestinationRecord) -> float:
        sample_rate = 48000
        block_frames = 1024
        ordered_ids = self._ordered_output_monitor_players_locked(record.audio_tap_mode)
        for session_id in ordered_ids:
            player = self._sessions.get(session_id)
            if player is None:
                continue
            try:
                sample_rate = max(1, int(player.player.sampleRate()))
            except Exception:
                sample_rate = 48000
            try:
                block_value = max(0, int(getattr(player.player, "outputBlockSize", lambda: 0)()))
            except Exception:
                block_value = 0
            if block_value > 0:
                block_frames = block_value
            break
        record.last_audio_sample_rate = int(sample_rate)
        record.last_audio_channel_count = max(1, int(record.last_audio_channel_count or 2))
        return max(0.005, (float(max(1, block_frames)) / float(max(1, sample_rate))))

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

    def _service_ndi_audio(self, dispatcher: NDIOutputDispatcher, mode: str, now: float) -> None:
        with self._lock:
            record = self._video_destinations.get("ndi_program")
            if record is None:
                return
            ordered_player_ids = self._ordered_output_monitor_players_locked(mode)
            sample_rate = max(1, int(record.last_audio_sample_rate or 48000))
            target_frames = max(240, int(self._ndi_audio_output_block_frames_locked(ordered_player_ids)))
        channel_count = max(1, int(getattr(record, "last_audio_channel_count", 2) or 2))
        sent = False
        if ordered_player_ids:
            max_available = 0
            for player_id in ordered_player_ids:
                counts = output_monitor_frame_counts(player_id)
                max_available = max(max_available, max(0, int(counts.get(mode, 0) or 0)))
            target_frames = min(max_available, target_frames)
            if target_frames > 0:
                mixed = mix_output_monitor_chunk(ordered_player_ids, target_frames=target_frames, mode=mode)
                if mixed is not None:
                    chunk, consume_map = mixed
                    if chunk.ndim == 2 and len(chunk) > 0 and chunk.shape[1] > 0:
                        channel_count = int(chunk.shape[1])
                        try:
                            sent = bool(dispatcher.send_audio_frames(chunk, sample_rate))
                        except Exception:
                            sent = False
                        if sent:
                            consume_output_monitor_chunk(consume_map, mode=mode)
        if not sent:
            silence = np.zeros((max(1, target_frames), channel_count), dtype=np.float32)
            try:
                sent = bool(dispatcher.send_audio_frames(silence, sample_rate))
            except Exception:
                sent = False
        with self._lock:
            record = self._video_destinations.get("ndi_program")
            if record is None:
                return
            record.last_audio_sent_at = now
            record.last_audio_sample_rate = sample_rate
            record.last_audio_channel_count = channel_count
            if sent:
                record.audio_send_count += 1

    def _ndi_audio_output_block_frames_locked(self, ordered_player_ids: list[str]) -> int:
        for session_id in ordered_player_ids:
            player_record = self._sessions.get(session_id)
            if player_record is None:
                continue
            getter = getattr(player_record.player, "outputBlockSize", None)
            if not callable(getter):
                continue
            try:
                value = max(0, int(getter()))
            except Exception:
                value = 0
            if value > 0:
                return value
        return 1024

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
