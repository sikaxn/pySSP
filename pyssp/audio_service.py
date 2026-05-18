from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
import itertools
import queue
from typing import Any, Dict, Optional, Tuple

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage

from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.dsp import DSPConfig
from pyssp.engine import EngineDiagnosticsSnapshot, MediaRuntime, RuntimeSessionSnapshot, TransportSnapshot, VideoDestinationSnapshot
from pyssp.ndi_support import NDICapabilityStatus


@dataclass(frozen=True)
class AudioPlayerStateSnapshot:
    player_id: str
    state: int = ExternalMediaPlayer.StoppedState
    position_ms: int = 0
    duration_ms: int = 0
    volume: int = 100


class AudioStateCache:
    def __init__(self) -> None:
        self._states: Dict[str, AudioPlayerStateSnapshot] = {}

    def ensure(self, player_id: str) -> AudioPlayerStateSnapshot:
        key = str(player_id)
        snapshot = self._states.get(key)
        if snapshot is None:
            snapshot = AudioPlayerStateSnapshot(player_id=key)
            self._states[key] = snapshot
        return snapshot

    def remove(self, player_id: str) -> None:
        self._states.pop(str(player_id), None)

    def snapshot(self, player_id: str) -> AudioPlayerStateSnapshot:
        return self.ensure(player_id)

    def update_state(self, player_id: str, state: int) -> AudioPlayerStateSnapshot:
        snapshot = self.ensure(player_id)
        updated = AudioPlayerStateSnapshot(
            player_id=snapshot.player_id,
            state=int(state),
            position_ms=snapshot.position_ms,
            duration_ms=snapshot.duration_ms,
            volume=snapshot.volume,
        )
        self._states[snapshot.player_id] = updated
        return updated

    def update_position(self, player_id: str, position_ms: int) -> AudioPlayerStateSnapshot:
        snapshot = self.ensure(player_id)
        updated = AudioPlayerStateSnapshot(
            player_id=snapshot.player_id,
            state=snapshot.state,
            position_ms=max(0, int(position_ms)),
            duration_ms=snapshot.duration_ms,
            volume=snapshot.volume,
        )
        self._states[snapshot.player_id] = updated
        return updated

    def update_duration(self, player_id: str, duration_ms: int) -> AudioPlayerStateSnapshot:
        snapshot = self.ensure(player_id)
        updated = AudioPlayerStateSnapshot(
            player_id=snapshot.player_id,
            state=snapshot.state,
            position_ms=snapshot.position_ms,
            duration_ms=max(0, int(duration_ms)),
            volume=snapshot.volume,
        )
        self._states[snapshot.player_id] = updated
        return updated

    def update_volume(self, player_id: str, volume: int) -> AudioPlayerStateSnapshot:
        snapshot = self.ensure(player_id)
        updated = AudioPlayerStateSnapshot(
            player_id=snapshot.player_id,
            state=snapshot.state,
            position_ms=snapshot.position_ms,
            duration_ms=snapshot.duration_ms,
            volume=max(0, min(100, int(volume))),
        )
        self._states[snapshot.player_id] = updated
        return updated

    def active_playing_ids(self) -> set[str]:
        return {
            player_id
            for player_id, snapshot in self._states.items()
            if snapshot.state == ExternalMediaPlayer.PlayingState
        }


class AudioService(QObject):
    positionChanged = pyqtSignal(str, int)
    durationChanged = pyqtSignal(str, int)
    stateChanged = pyqtSignal(str, int)
    mediaLoadFinished = pyqtSignal(str, int, bool, str)
    commandResultReady = pyqtSignal(int, bool, object)

    @pyqtSlot(str, str, object, object)
    def handle_command(self, player_id: str, command: str, payload: object, result_queue: object) -> None:
        result_token: Optional[int] = None
        if isinstance(result_queue, int):
            result_token = int(result_queue)
            result_queue = None
        result = None
        error = None
        try:
            result = self._dispatch(str(player_id), str(command), payload if isinstance(payload, dict) else {})
        except Exception as exc:
            error = exc
        if result_token is not None:
            self.commandResultReady.emit(result_token, error is None, result if error is None else error)
            return
        if result_queue is not None:
            try:
                result_queue.put((error is None, result if error is None else error), block=False)
            except Exception:
                pass

    def __init__(self, runtime: Optional[MediaRuntime] = None) -> None:
        super().__init__()
        self._runtime = runtime or MediaRuntime()

    def _player(self, player_id: str) -> ExternalMediaPlayer:
        return self._runtime.player_for_session(str(player_id))

    def _dispatch(self, player_id: str, command: str, payload: dict):
        if command == "transportSnapshot":
            return self._runtime.transport_snapshot()
        if command == "engineDiagnostics":
            return self._runtime.diagnostics_snapshot()
        if command == "runtimeSessionSnapshots":
            return self._runtime.session_snapshots()
        if command == "videoDestinationSnapshots":
            return self._runtime.video_destination_snapshots()
        if command == "setMultiPlayEnabled":
            self._runtime.set_multi_play_enabled(bool(payload.get("enabled", False)))
            return True
        if command == "setSessionSlotKey":
            raw = payload.get("slot_key")
            slot_key = tuple(raw) if isinstance(raw, (list, tuple)) and len(raw) == 3 else None
            return self._runtime.set_session_slot_key(player_id, slot_key)
        if command == "configureVideoDestination":
            ndi_status = _payload_ndi_status(payload.get("ndi_status"))
            return self._runtime.configure_video_destination(
                str(payload.get("destination_id", "ndi_program")),
                enabled=bool(payload.get("enabled", False)),
                route_mode=str(payload.get("route_mode", "blank") or "blank"),
                width=max(2, int(payload.get("width", 1920) or 1920)),
                height=max(2, int(payload.get("height", 1080) or 1080)),
                fps=max(1.0, float(payload.get("fps", 30.0) or 30.0)),
                source_name=str(payload.get("source_name", "pyssp-video") or "pyssp-video"),
                audio_enabled=bool(payload.get("audio_enabled", False)),
                audio_tap_mode=str(payload.get("audio_tap_mode", "post_fader") or "post_fader"),
                ndi_status=ndi_status,
            )
        if command == "submitVideoDestinationFrame":
            image = payload.get("image")
            if not isinstance(image, QImage):
                return False
            route_mode = str(payload.get("route_mode", "") or "").strip()
            return self._runtime.submit_video_destination_frame(
                str(payload.get("destination_id", "ndi_program")),
                image,
                route_mode=route_mode if route_mode else None,
                pts_ms=max(0, int(payload.get("pts_ms", 0) or 0)),
                source_path=str(payload.get("source_path", "") or ""),
            )
        if command == "clearVideoDestinationFrame":
            return self._runtime.clear_video_destination_frame(str(payload.get("destination_id", "ndi_program")))
        if command == "create":
            if not self._runtime.has_session(player_id):
                player = self._runtime.create_legacy_session(player_id)
                player.positionChanged.connect(lambda value, pid=player_id: self.positionChanged.emit(pid, int(value)))
                player.durationChanged.connect(lambda value, pid=player_id: self.durationChanged.emit(pid, int(value)))
                player.stateChanged.connect(lambda value, pid=player_id: self.stateChanged.emit(pid, int(value)))
                player.mediaLoadFinished.connect(
                    lambda request_id, ok, error, pid=player_id: self.mediaLoadFinished.emit(
                        pid, int(request_id), bool(ok), str(error)
                    )
                )
            return True
        if command == "delete":
            self._runtime.delete_session(player_id)
            return True
        if command == "shutdown":
            self._runtime.shutdown()
            return True

        player = self._player(player_id)
        if command == "setNotifyInterval":
            player.setNotifyInterval(int(payload.get("interval_ms", 90)))
            return True
        if command == "setMedia":
            source = _payload_source(payload)
            player.setMedia(source, dsp_config=payload.get("dsp_config"))
            return True
        if command == "setMediaAsync":
            source = _payload_source(payload)
            return int(player.setMediaAsync(source, dsp_config=payload.get("dsp_config")))
        if command == "setMediaAsyncRequest":
            player.setMediaAsync(
                _payload_source(payload),
                dsp_config=payload.get("dsp_config"),
                request_id=int(payload.get("request_id", 0)),
            )
            return True
        if command == "setDSPConfig":
            player.setDSPConfig(payload.get("dsp_config", DSPConfig()))
            return True
        if command == "play":
            player.play()
            return True
        if command == "pause":
            player.pause()
            return True
        if command == "stop":
            player.stop()
            return True
        if command == "state":
            return int(player.state())
        if command == "setPosition":
            player.setPosition(int(payload.get("position_ms", 0)))
            return True
        if command == "position":
            return int(player.position())
        if command == "enginePositionMs":
            return int(player.enginePositionMs())
        if command == "duration":
            return int(player.duration())
        if command == "setVolume":
            player.setVolume(int(payload.get("volume", 100)))
            return True
        if command == "volume":
            return int(player.volume())
        if command == "setMasterVolume":
            setter = getattr(player, "setMasterVolume", None)
            if callable(setter):
                setter(int(payload.get("volume", 100)))
            return True
        if command == "masterVolume":
            getter = getattr(player, "masterVolume", None)
            if callable(getter):
                return int(getter())
            return 100
        if command == "meterLevels":
            left, right = player.meterLevels()
            return float(left), float(right)
        if command == "sampleRate":
            return int(player.sampleRate())
        if command == "outputBlockSize":
            return int(getattr(player, "outputBlockSize", lambda: 0)())
        if command == "takeOutputFrames":
            frames = player.takeOutputFrames(
                max_frames=int(payload.get("max_frames", 0)),
                mode=str(payload.get("mode", "post_fader") or "post_fader"),
            )
            return frames
        if command == "outputTapFrameCounts":
            return dict(player.outputTapFrameCounts())
        if command == "waveformPeaks":
            return player.waveformPeaks(int(payload.get("sample_count", 1024)))
        if command == "waveformPeaksAsync":
            return player.waveformPeaksAsync(int(payload.get("sample_count", 1024)))
        raise RuntimeError(f"Unsupported audio command: {command}")


class AudioServiceController(QObject):
    commandRequested = pyqtSignal(str, str, object, object)
    positionChanged = pyqtSignal(str, int)
    durationChanged = pyqtSignal(str, int)
    stateChanged = pyqtSignal(str, int)
    mediaLoadFinished = pyqtSignal(str, int, bool, str)

    def __init__(self, parent: Optional[QObject] = None, runtime: Optional[MediaRuntime] = None) -> None:
        super().__init__(parent)
        self._thread = QThread(self)
        self._service = AudioService(runtime=runtime)
        self._service.moveToThread(self._thread)
        self.commandRequested.connect(self._service.handle_command, type=Qt.QueuedConnection)
        self.state_cache = AudioStateCache()
        self._service.positionChanged.connect(self._on_service_position_changed)
        self._service.durationChanged.connect(self._on_service_duration_changed)
        self._service.stateChanged.connect(self._on_service_state_changed)
        self._service.mediaLoadFinished.connect(self.mediaLoadFinished)
        self._service.commandResultReady.connect(self._on_command_result_ready)
        self._counter = itertools.count(1)
        self._request_counter = itertools.count(1)
        self._pending_results: Dict[int, Future] = {}
        self._thread.start()

    def create_player(self, parent: Optional[QObject] = None) -> "AudioPlayerProxy":
        player_id = f"player-{next(self._counter)}"
        self.state_cache.ensure(player_id)
        proxy = AudioPlayerProxy(self, player_id, parent)
        self.post(player_id, "create", {})
        return proxy

    def call(self, player_id: str, command: str, payload: Optional[dict] = None, timeout: float = 2.0):
        result_queue: "queue.Queue[Tuple[bool, object]]" = queue.Queue(maxsize=1)
        self.commandRequested.emit(str(player_id), str(command), dict(payload or {}), result_queue)
        ok, value = result_queue.get(timeout=max(0.1, float(timeout)))
        if ok:
            return value
        if isinstance(value, Exception):
            raise value
        raise RuntimeError(str(value))

    def post(self, player_id: str, command: str, payload: Optional[dict] = None) -> None:
        self.commandRequested.emit(str(player_id), str(command), dict(payload or {}), None)

    def request_async(self, player_id: str, command: str, payload: Optional[dict] = None) -> Future:
        token = int(next(self._request_counter))
        future: Future = Future()
        self._pending_results[token] = future
        self.commandRequested.emit(str(player_id), str(command), dict(payload or {}), token)
        return future

    def shutdown(self) -> None:
        try:
            for player_id in ["__all__"]:
                self.call(player_id, "shutdown", {}, timeout=2.0)
        except Exception:
            pass
        self._thread.quit()
        self._thread.wait(1500)

    def transport_snapshot(self) -> TransportSnapshot:
        result = self.call("__runtime__", "transportSnapshot", {}, timeout=0.5)
        if isinstance(result, TransportSnapshot):
            return result
        return TransportSnapshot(
            generated_at=0.0,
            reference_session_id=None,
            active_session_ids=(),
            playing_session_ids=(),
            multi_play_enabled=False,
        )

    def engine_diagnostics_snapshot(self) -> EngineDiagnosticsSnapshot:
        result = self.call("__runtime__", "engineDiagnostics", {}, timeout=0.5)
        if isinstance(result, EngineDiagnosticsSnapshot):
            return result
        return EngineDiagnosticsSnapshot(
            generated_at=0.0,
            session_count=0,
            active_session_ids=(),
            playing_session_ids=(),
            reference_session_id=None,
            ffmpeg_available=False,
            ffmpeg_source="none",
            ffmpeg_version="",
            audio_bus_ids=(),
            video_destination_ids=(),
        )

    def set_multi_play_enabled(self, enabled: bool) -> None:
        self.post("__runtime__", "setMultiPlayEnabled", {"enabled": bool(enabled)})

    def runtime_session_snapshots(self) -> tuple[RuntimeSessionSnapshot, ...]:
        result = self.call("__runtime__", "runtimeSessionSnapshots", {}, timeout=0.5)
        if isinstance(result, tuple) and all(isinstance(item, RuntimeSessionSnapshot) for item in result):
            return result
        if isinstance(result, list) and all(isinstance(item, RuntimeSessionSnapshot) for item in result):
            return tuple(result)
        return ()

    def video_destination_snapshots(self) -> tuple[VideoDestinationSnapshot, ...]:
        result = self.call("__runtime__", "videoDestinationSnapshots", {}, timeout=0.5)
        if isinstance(result, tuple) and all(isinstance(item, VideoDestinationSnapshot) for item in result):
            return result
        if isinstance(result, list) and all(isinstance(item, VideoDestinationSnapshot) for item in result):
            return tuple(result)
        return ()

    def set_session_slot_key(self, player_id: str, slot_key: Optional[tuple[str, int, int]]) -> None:
        payload = {"slot_key": list(slot_key) if slot_key is not None else None}
        self.post(str(player_id), "setSessionSlotKey", payload)

    def configure_video_destination(
        self,
        destination_id: str,
        *,
        enabled: bool,
        route_mode: str,
        width: int,
        height: int,
        fps: float,
        source_name: str,
        audio_enabled: bool,
        audio_tap_mode: str,
        ndi_status: Optional[NDICapabilityStatus],
    ) -> None:
        self.post(
            "__runtime__",
            "configureVideoDestination",
            {
                "destination_id": str(destination_id),
                "enabled": bool(enabled),
                "route_mode": str(route_mode or "blank"),
                "width": int(width),
                "height": int(height),
                "fps": float(fps),
                "source_name": str(source_name or "pyssp-video"),
                "audio_enabled": bool(audio_enabled),
                "audio_tap_mode": str(audio_tap_mode or "post_fader"),
                "ndi_status": _serialize_ndi_status(ndi_status),
            },
        )

    def submit_video_destination_frame(
        self,
        destination_id: str,
        image: QImage,
        *,
        route_mode: str,
        pts_ms: int,
        source_path: str,
    ) -> None:
        self.post(
            "__runtime__",
            "submitVideoDestinationFrame",
            {
                "destination_id": str(destination_id),
                "image": image,
                "route_mode": str(route_mode or ""),
                "pts_ms": int(pts_ms),
                "source_path": str(source_path or ""),
            },
        )

    def clear_video_destination_frame(self, destination_id: str) -> None:
        self.post("__runtime__", "clearVideoDestinationFrame", {"destination_id": str(destination_id)})

    def _on_service_position_changed(self, player_id: str, value: int) -> None:
        self.state_cache.update_position(player_id, value)
        self.positionChanged.emit(str(player_id), int(value))

    def _on_service_duration_changed(self, player_id: str, value: int) -> None:
        self.state_cache.update_duration(player_id, value)
        self.durationChanged.emit(str(player_id), int(value))

    def _on_service_state_changed(self, player_id: str, value: int) -> None:
        self.state_cache.update_state(player_id, value)
        self.stateChanged.emit(str(player_id), int(value))

    def _on_command_result_ready(self, token: int, ok: bool, value: object) -> None:
        future = self._pending_results.pop(int(token), None)
        if future is None or future.done():
            return
        if ok:
            future.set_result(value)
        elif isinstance(value, Exception):
            future.set_exception(value)
        else:
            future.set_exception(RuntimeError(str(value)))


class AudioPlayerProxy(QObject):
    StoppedState = ExternalMediaPlayer.StoppedState
    PlayingState = ExternalMediaPlayer.PlayingState
    PausedState = ExternalMediaPlayer.PausedState

    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)
    mediaLoadFinished = pyqtSignal(int, bool, str)

    def __init__(self, controller: AudioServiceController, player_id: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._player_id = str(player_id)
        self._state = self.StoppedState
        self._position_ms = 0
        self._duration_ms = 0
        self._volume = 100
        self._meter_levels: Tuple[float, float] = (0.0, 0.0)
        self._media_request_counter = itertools.count(1_000_000)
        controller.positionChanged.connect(self._on_position_changed)
        controller.durationChanged.connect(self._on_duration_changed)
        controller.stateChanged.connect(self._on_state_changed)
        controller.mediaLoadFinished.connect(self._on_media_load_finished)

    @property
    def player_id(self) -> str:
        return self._player_id

    def _call(self, command: str, payload: Optional[dict] = None, timeout: float = 2.0):
        return self._controller.call(self._player_id, command, payload, timeout=timeout)

    def _post(self, command: str, payload: Optional[dict] = None) -> None:
        self._controller.post(self._player_id, command, payload)

    def setNotifyInterval(self, interval_ms: int) -> None:
        self._post("setNotifyInterval", {"interval_ms": int(interval_ms)})

    def setMedia(self, source: Any, dsp_config: Optional[DSPConfig] = None) -> None:
        self.setMediaAsync(source, dsp_config=dsp_config)

    def setMediaAsync(self, source: Any, dsp_config: Optional[DSPConfig] = None) -> int:
        request_id = int(next(self._media_request_counter))
        self._state = self.StoppedState
        self._position_ms = 0
        self._duration_ms = 0
        self._controller.state_cache.update_state(self._player_id, self._state)
        self._controller.state_cache.update_position(self._player_id, self._position_ms)
        self._controller.state_cache.update_duration(self._player_id, self._duration_ms)
        self._post(
            "setMediaAsyncRequest",
            _build_media_payload(source, dsp_config, request_id),
        )
        return request_id

    def setDSPConfig(self, dsp_config: DSPConfig) -> None:
        self._post("setDSPConfig", {"dsp_config": dsp_config})

    def play(self) -> None:
        self._state = self.PlayingState
        self._controller.state_cache.update_state(self._player_id, self._state)
        self._post("play")

    def pause(self) -> None:
        self._state = self.PausedState
        self._controller.state_cache.update_state(self._player_id, self._state)
        self._post("pause")

    def stop(self) -> None:
        self._state = self.StoppedState
        self._position_ms = 0
        self._controller.state_cache.update_state(self._player_id, self._state)
        self._controller.state_cache.update_position(self._player_id, self._position_ms)
        self._post("stop")

    def state(self) -> int:
        return int(self._state)

    def setPosition(self, position_ms: int) -> None:
        self._position_ms = max(0, int(position_ms))
        self._controller.state_cache.update_position(self._player_id, self._position_ms)
        self._post("setPosition", {"position_ms": self._position_ms})

    def position(self) -> int:
        return int(self._position_ms)

    def enginePositionMs(self) -> int:
        return int(self._position_ms)

    def duration(self) -> int:
        return int(self._duration_ms)

    def setVolume(self, volume: int) -> None:
        self._volume = max(0, min(100, int(volume)))
        self._controller.state_cache.update_volume(self._player_id, self._volume)
        self._post("setVolume", {"volume": self._volume})

    def volume(self) -> int:
        return int(self._volume)

    def setMasterVolume(self, volume: int) -> None:
        self._post("setMasterVolume", {"volume": max(0, min(100, int(volume)))})

    def masterVolume(self) -> int:
        try:
            return int(self._call("masterVolume", timeout=0.5))
        except Exception:
            return 100

    def meterLevels(self) -> Tuple[float, float]:
        return float(self._meter_levels[0]), float(self._meter_levels[1])

    def sampleRate(self) -> int:
        try:
            return int(self._call("sampleRate", timeout=0.5))
        except Exception:
            return 48000

    def outputBlockSize(self) -> int:
        try:
            return max(0, int(self._call("outputBlockSize", timeout=0.5)))
        except Exception:
            return 0

    def takeOutputFrames(self, max_frames: int = 0, mode: str = "post_fader"):
        result = self._call(
            "takeOutputFrames",
            {
                "max_frames": max(0, int(max_frames)),
                "mode": str(mode or "post_fader"),
            },
            timeout=0.5,
        )
        return result

    def outputTapFrameCounts(self) -> Dict[str, int]:
        result = self._call("outputTapFrameCounts", timeout=0.5)
        if isinstance(result, dict):
            return {
                "pre_fader": max(0, int(result.get("pre_fader", 0) or 0)),
                "post_fader": max(0, int(result.get("post_fader", 0) or 0)),
            }
        return {"pre_fader": 0, "post_fader": 0}

    def waveformPeaks(self, sample_count: int = 1024):
        return self._call("waveformPeaks", {"sample_count": int(sample_count)}, timeout=20.0)

    def waveformPeaksAsync(self, sample_count: int = 1024):
        outer = self._controller.request_async(
            self._player_id,
            "waveformPeaksAsync",
            {"sample_count": int(sample_count)},
        )
        chained: Future = Future()

        def _finish_outer(done_future: Future) -> None:
            if chained.done():
                return
            try:
                inner = done_future.result()
            except Exception as exc:
                chained.set_exception(exc)
                return
            if not isinstance(inner, Future):
                chained.set_result(inner)
                return

            def _finish_inner(inner_future: Future) -> None:
                if chained.done():
                    return
                try:
                    chained.set_result(inner_future.result())
                except Exception as exc:
                    chained.set_exception(exc)

            inner.add_done_callback(_finish_inner)

        outer.add_done_callback(_finish_outer)
        return chained

    def deleteLater(self) -> None:
        try:
            self._post("delete")
        except Exception:
            pass
        self._controller.state_cache.remove(self._player_id)
        super().deleteLater()

    def _on_position_changed(self, player_id: str, value: int) -> None:
        if str(player_id) != self._player_id:
            return
        self._position_ms = max(0, int(value))
        self.positionChanged.emit(self._position_ms)

    def _on_duration_changed(self, player_id: str, value: int) -> None:
        if str(player_id) != self._player_id:
            return
        self._duration_ms = max(0, int(value))
        self.durationChanged.emit(self._duration_ms)

    def _on_state_changed(self, player_id: str, value: int) -> None:
        if str(player_id) != self._player_id:
            return
        self._state = int(value)
        self.stateChanged.emit(self._state)

    def _on_media_load_finished(self, player_id: str, request_id: int, ok: bool, error: str) -> None:
        if str(player_id) != self._player_id:
            return
        self.mediaLoadFinished.emit(int(request_id), bool(ok), str(error))


def _build_media_payload(source: Any, dsp_config: Optional[DSPConfig], request_id: int) -> dict:
    payload = {"dsp_config": dsp_config, "request_id": int(request_id)}
    if isinstance(source, dict):
        payload["source"] = dict(source)
        payload["file_path"] = ""
    else:
        payload["file_path"] = str(source or "")
    return payload


def _payload_source(payload: dict) -> Any:
    source = payload.get("source")
    if isinstance(source, dict):
        return dict(source)
    return str(payload.get("file_path", ""))


def _serialize_ndi_status(status: Optional[NDICapabilityStatus]) -> Optional[dict]:
    if status is None:
        return None
    return {
        "ndi_backend_name": str(getattr(status, "ndi_backend_name", "") or ""),
        "ndi_python_available": bool(getattr(status, "ndi_python_available", False)),
        "ndi_python_version": str(getattr(status, "ndi_python_version", "") or ""),
        "ndi_module_importable": bool(getattr(status, "ndi_module_importable", False)),
        "ndi_runtime_or_sdk_detected": bool(getattr(status, "ndi_runtime_or_sdk_detected", False)),
        "availability_reason": str(getattr(status, "availability_reason", "") or ""),
        "runtime_library_path": str(getattr(status, "runtime_library_path", "") or ""),
        "ndi_runtime_version": str(getattr(status, "ndi_runtime_version", "") or ""),
    }


def _payload_ndi_status(payload: object) -> Optional[NDICapabilityStatus]:
    if isinstance(payload, NDICapabilityStatus):
        return payload
    if not isinstance(payload, dict):
        return None
    return NDICapabilityStatus(
        ndi_backend_name=str(payload.get("ndi_backend_name", "") or ""),
        ndi_python_available=bool(payload.get("ndi_python_available", False)),
        ndi_python_version=str(payload.get("ndi_python_version", "") or ""),
        ndi_module_importable=bool(payload.get("ndi_module_importable", False)),
        ndi_runtime_or_sdk_detected=bool(payload.get("ndi_runtime_or_sdk_detected", False)),
        availability_reason=str(payload.get("availability_reason", "") or ""),
        runtime_library_path=str(payload.get("runtime_library_path", "") or ""),
        ndi_runtime_version=str(payload.get("ndi_runtime_version", "") or ""),
    )
