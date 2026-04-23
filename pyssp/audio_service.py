from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
import itertools
import queue
from typing import Dict, Optional, Tuple

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, pyqtSlot

from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.dsp import DSPConfig


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

    def __init__(self) -> None:
        super().__init__()
        self._players: Dict[str, ExternalMediaPlayer] = {}

    def _player(self, player_id: str) -> ExternalMediaPlayer:
        player = self._players.get(str(player_id))
        if player is None:
            raise RuntimeError(f"Audio player not found: {player_id}")
        return player

    def _dispatch(self, player_id: str, command: str, payload: dict):
        if command == "create":
            if player_id not in self._players:
                player = ExternalMediaPlayer()
                self._players[player_id] = player
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
            player = self._players.pop(player_id, None)
            if player is not None:
                try:
                    player.stop()
                finally:
                    player.deleteLater()
            return True
        if command == "shutdown":
            for pid in list(self._players.keys()):
                self._dispatch(pid, "delete", {})
            return True

        player = self._player(player_id)
        if command == "setNotifyInterval":
            player.setNotifyInterval(int(payload.get("interval_ms", 90)))
            return True
        if command == "setMedia":
            player.setMedia(str(payload.get("file_path", "")), dsp_config=payload.get("dsp_config"))
            return True
        if command == "setMediaAsync":
            return int(player.setMediaAsync(str(payload.get("file_path", "")), dsp_config=payload.get("dsp_config")))
        if command == "setMediaAsyncRequest":
            player.setMediaAsync(
                str(payload.get("file_path", "")),
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
        if command == "meterLevels":
            left, right = player.meterLevels()
            return float(left), float(right)
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

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._thread = QThread(self)
        self._service = AudioService()
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

    def setMedia(self, file_path: str, dsp_config: Optional[DSPConfig] = None) -> None:
        self.setMediaAsync(file_path, dsp_config=dsp_config)

    def setMediaAsync(self, file_path: str, dsp_config: Optional[DSPConfig] = None) -> int:
        request_id = int(next(self._media_request_counter))
        self._state = self.StoppedState
        self._position_ms = 0
        self._duration_ms = 0
        self._controller.state_cache.update_state(self._player_id, self._state)
        self._controller.state_cache.update_position(self._player_id, self._position_ms)
        self._controller.state_cache.update_duration(self._player_id, self._duration_ms)
        self._post(
            "setMediaAsyncRequest",
            {"file_path": file_path, "dsp_config": dsp_config, "request_id": request_id},
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

    def meterLevels(self) -> Tuple[float, float]:
        return float(self._meter_levels[0]), float(self._meter_levels[1])

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
