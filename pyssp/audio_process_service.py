"""Playback service in a separate interpreter from the Qt user interface.

PortAudio calls Python for every output buffer. A Qt widget operation can hold
the UI interpreter's GIL longer than one audio buffer, even when the players
live on a QThread. The worker owns the streams and its own GIL; UI events are
delivered through queues and may arrive late without delaying audio output.
"""

from __future__ import annotations

from concurrent.futures import Future
from collections import deque
import itertools
import math
import multiprocessing
from queue import Empty
import time
from typing import Optional

from PyQt5.QtCore import QCoreApplication, QObject, QTimer, pyqtSignal

from pyssp.audio_service import AudioPlayerProxy, AudioService, AudioStateCache
from pyssp.audio_engine import ExternalMediaPlayer
from pyssp.timecode import MIDI_OUTPUT_DEVICE_NONE


def _audio_worker(commands, events, output_device: str, preload_policy, waveform_limit: int) -> None:
    # This entry point is importable by multiprocessing's spawn method. In
    # particular, no QWidget or QApplication from the parent enters the worker.
    from pyssp import audio_engine
    from pyssp.timecode import (
        LtcAudioOutput, MtcMidiOutput, MTC_IDLE_KEEP_STREAM, MIDI_OUTPUT_DEVICE_NONE,
        TIMECODE_MODE_FOLLOW, TIMECODE_MODE_FOLLOW_FREEZE, TIMECODE_MODE_SYSTEM,
    )
    from datetime import datetime

    app = QCoreApplication([])
    audio_engine.set_output_device(output_device)
    if preload_policy is not None:
        audio_engine.configure_audio_preload_cache_policy(*preload_policy)
    audio_engine.configure_waveform_disk_cache(waveform_limit)
    service = AudioService()
    ltc = None
    mtc = None
    mtc_idle_behavior = MTC_IDLE_KEEP_STREAM
    timecode_config = None
    timecode_frame = 0
    timecode_running = False
    volume_ramps: dict[str, tuple[float, float, float, float, str, bool]] = {}

    service.positionChanged.connect(
        lambda pid, value: events.put(("position", pid, int(value), time.perf_counter()))
    )
    service.durationChanged.connect(lambda pid, value: events.put(("duration", pid, int(value))))
    service.stateChanged.connect(lambda pid, value: events.put(("state", pid, int(value))))
    service.mediaLoadFinished.connect(
        lambda pid, request_id, ok, error: events.put(
            ("media", pid, int(request_id), bool(ok), str(error))
        )
    )

    def dispatch(player_id: str, command: str, payload: dict, token: int) -> bool:
        nonlocal ltc, mtc, mtc_idle_behavior, timecode_config
        try:
            if player_id == "__runtime__":
                if command == "shutdown":
                    service._dispatch("__all__", "shutdown", {})
                    if ltc is not None:
                        ltc.shutdown()
                    if mtc is not None:
                        mtc.shutdown()
                    app.quit()
                    return False
                if command == "output_device":
                    result = audio_engine.set_output_device(str(payload.get("device", "")))
                elif command == "preload_policy":
                    audio_engine.configure_audio_preload_cache_policy(*payload["policy"])
                    result = True
                elif command == "preload":
                    audio_engine.request_audio_preload(
                        list(payload.get("paths", [])),
                        prioritize=bool(payload.get("prioritize", False)),
                        force=bool(payload.get("force", False)),
                    )
                    result = True
                elif command == "preload_paused":
                    audio_engine.set_audio_preload_paused(bool(payload.get("paused", False)))
                    result = True
                elif command == "preload_trim":
                    audio_engine.enforce_audio_preload_limits()
                    result = True
                elif command == "waveform_cache":
                    audio_engine.configure_waveform_disk_cache(int(payload["limit_mb"]))
                    result = True
                elif command == "timecode_config":
                    timecode_config = dict(payload)
                    mtc_idle_behavior = str(payload.get("idle_behavior", MTC_IDLE_KEEP_STREAM))
                    ltc_device = payload.get("ltc_device")
                    if ltc is None and ltc_device is not None:
                        ltc = LtcAudioOutput()
                    if ltc is not None:
                        ltc.set_output(
                            ltc_device, int(payload["sample_rate"]),
                            int(payload["bit_depth"]), float(payload["fps"]),
                        )
                    mtc_device = str(payload.get("mtc_device", MIDI_OUTPUT_DEVICE_NONE))
                    if mtc is None and mtc_device != MIDI_OUTPUT_DEVICE_NONE:
                        mtc = MtcMidiOutput(lambda: mtc_idle_behavior)
                    if mtc is not None:
                        mtc.set_device(mtc_device)
                    result = True
                elif command == "timecode_snapshot":
                    result = (timecode_frame, timecode_running)
                elif command == "ltc_set_output":
                    device = payload.get("device")
                    if ltc is None and device is not None:
                        ltc = LtcAudioOutput()
                    if ltc is not None:
                        ltc.set_output(device, int(payload["sample_rate"]), int(payload["bit_depth"]), float(payload["fps"]))
                    result = True
                elif command == "ltc_update":
                    if ltc is not None:
                        ltc.update(int(payload["current_frame"]), float(payload["fps"]), running=bool(payload["running"]))
                    result = True
                elif command == "ltc_resync":
                    if ltc is not None:
                        ltc.request_resync()
                    result = True
                elif command == "ltc_shutdown":
                    if ltc is not None:
                        ltc.shutdown()
                        ltc = None
                    result = True
                elif command == "mtc_set_device":
                    device = str(payload["device"])
                    if mtc is None and device != MIDI_OUTPUT_DEVICE_NONE:
                        mtc = MtcMidiOutput(lambda: mtc_idle_behavior)
                    if mtc is not None:
                        mtc.set_device(device)
                    result = True
                elif command == "mtc_update":
                    mtc_idle_behavior = str(payload.get("idle_behavior", MTC_IDLE_KEEP_STREAM))
                    if mtc is not None:
                        mtc.update(
                            int(payload["current_frame"]),
                            float(payload["source_fps"]),
                            float(payload["mtc_fps"]),
                            running=bool(payload["running"]),
                        )
                    result = True
                elif command == "mtc_resync":
                    if mtc is not None:
                        mtc.request_resync()
                    result = True
                elif command == "mtc_shutdown":
                    if mtc is not None:
                        mtc.shutdown()
                        mtc = None
                    result = True
                else:
                    raise RuntimeError(f"Unsupported runtime command: {command}")
            else:
                if command == "rampVolume":
                    player = service._player(player_id)
                    start = float(player.volume())
                    end = max(0.0, min(100.0, float(payload["target"])))
                    duration = max(0.0, float(payload["seconds"]))
                    if duration <= 0:
                        player.setVolume(int(round(end)))
                    else:
                        volume_ramps[player_id] = (
                            start, end, time.perf_counter(), duration,
                            str(payload.get("curve", "linear")),
                            bool(payload.get("pause_on_complete", False)),
                        )
                    result = True
                else:
                    if command in {"setVolume", "stop", "pause", "delete", "setMedia", "setMediaAsync", "setMediaAsyncRequest"}:
                        volume_ramps.pop(player_id, None)
                    result = service._dispatch(player_id, command, payload)
                if command == "waveformPeaksAsync" and isinstance(result, Future):
                    if token:
                        def finish(future):
                            try:
                                events.put(("result", token, True, future.result()))
                            except Exception as exc:
                                events.put(("result", token, False, str(exc)))
                        result.add_done_callback(finish)
                    return True
            if token:
                events.put(("result", token, True, result))
        except Exception as exc:
            if token:
                events.put(("result", token, False, str(exc)))
        return True

    def poll_commands() -> None:
        for _ in range(128):
            try:
                player_id, command, payload, token = commands.get_nowait()
            except Empty:
                break
            if not dispatch(player_id, command, payload, token):
                return

    def poll_meter() -> None:
        levels = audio_engine.get_engine_output_meter_levels()
        events.put(("meter", float(levels[0]), float(levels[1]), time.monotonic()))
        for player_id, player in service._players.items():
            left, right = player._meter_levels
            events.put(("player_meter", player_id, float(left), float(right)))

    def poll_ramps() -> None:
        now = time.perf_counter()
        for player_id, (start, end, began, duration, curve, pause_on_complete) in list(volume_ramps.items()):
            player = service._players.get(player_id)
            if player is None:
                volume_ramps.pop(player_id, None)
                continue
            ratio = min(1.0, max(0.0, (now - began) / duration))
            if curve == "equal_power":
                if end >= start:
                    volume = start + (end - start) * math.sin(ratio * math.pi / 2.0)
                else:
                    volume = end + (start - end) * math.cos(ratio * math.pi / 2.0)
            else:
                volume = start + (end - start) * ratio
            # An integer assignment is atomic under this interpreter's GIL.
            # Taking the player's lock here could make a PortAudio callback
            # emit a silent buffer when the 10 ms ramp timer overlaps it.
            player._volume = int(round(volume))
            if ratio >= 1.0:
                volume_ramps.pop(player_id, None)
                if pause_on_complete:
                    player.pause()

    def poll_preload() -> None:
        enabled, active, capacity, paths = audio_engine.get_audio_preload_snapshot()
        events.put(("preload_status", enabled, active, capacity, paths))

    def poll_timecode() -> None:
        nonlocal timecode_frame, timecode_running
        config = timecode_config
        if config is None:
            return
        mode = str(config.get("mode", ""))
        running = False
        if mode == TIMECODE_MODE_SYSTEM:
            now = datetime.now()
            output_ms = ((now.hour * 3600 + now.minute * 60 + now.second) * 1000) + now.microsecond // 1000
            running = True
        elif mode == TIMECODE_MODE_FOLLOW_FREEZE:
            output_ms = max(0, int(config.get("frozen_ms", 0)))
        elif mode == TIMECODE_MODE_FOLLOW:
            player = service._players.get(str(config.get("reference_player_id", "")))
            state, absolute_ms = player.realtimeStatePositionMs() if player is not None else (ExternalMediaPlayer.StoppedState, 0)
            stop_at = float(config.get("stop_at", 0.0))
            if stop_at > 0 and time.monotonic() >= stop_at:
                output_ms = 0
            elif player is not None and state in {player.PlayingState, player.PausedState}:
                output_ms = max(0, absolute_ms - max(0, int(config.get("cue_start_ms", 0))))
                output_ms += max(0, int(config.get("offset_ms", 0)))
                running = state == player.PlayingState
            else:
                output_ms = 0
        else:
            output_ms = 0
        fps = max(1.0, float(config["fps"]))
        frame = int((output_ms / 1000.0) * fps)
        timecode_frame = frame
        timecode_running = running
        if ltc is not None:
            ltc.update(frame, fps, running=running)
        if mtc is not None:
            mtc.update(frame, fps, max(1.0, float(config["mtc_fps"])), running=running)

    command_timer = QTimer()
    command_timer.timeout.connect(poll_commands)
    command_timer.start(3)
    meter_timer = QTimer()
    meter_timer.timeout.connect(poll_meter)
    meter_timer.start(60)
    ramp_timer = QTimer()
    ramp_timer.timeout.connect(poll_ramps)
    ramp_timer.start(10)
    preload_timer = QTimer()
    preload_timer.timeout.connect(poll_preload)
    preload_timer.start(250)
    timecode_timer = QTimer()
    timecode_timer.timeout.connect(poll_timecode)
    timecode_timer.start(10)
    events.put(("ready",))
    app.exec_()


class ProcessAudioServiceController(QObject):
    """Nonblocking UI proxy for the audio and timecode process."""

    positionChanged = pyqtSignal(str, int)
    positionSampled = pyqtSignal(str, int, float)
    durationChanged = pyqtSignal(str, int)
    stateChanged = pyqtSignal(str, int)
    mediaLoadFinished = pyqtSignal(str, int, bool, str)
    serviceFailed = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.state_cache = AudioStateCache()
        self._counter = itertools.count(1)
        self._request_counter = itertools.count(1)
        self._pending_results: dict[int, Future] = {}
        self._output_device = ""
        self._preload_policy = None
        self._waveform_limit = 1024
        self._meter_levels = (0.0, 0.0)
        self._worker_meter_times = deque(maxlen=256)
        self._player_meters: dict[str, tuple[float, float]] = {}
        self._preload_enabled = False
        self._preload_active = 0
        self._preload_capacity = (0, 0, 0)
        self._preloaded_paths: set[str] = set()
        self._timecode_config = None
        self._shutdown = False
        self._failure_reported = False
        self._ready = False
        self._context = multiprocessing.get_context("spawn")
        self._commands = None
        self._events = None
        self._process = None
        self._event_timer = QTimer(self)
        self._event_timer.timeout.connect(self._drain_events)

    def _start(self) -> None:
        if self._process is not None:
            return
        self._commands = self._context.Queue()
        self._events = self._context.Queue()
        self._process = self._context.Process(
            target=_audio_worker,
            args=(self._commands, self._events, self._output_device, self._preload_policy, self._waveform_limit),
            name="pySSP Audio and Timecode",
            daemon=True,
        )
        self._process.start()
        self._event_timer.start(15)

    def ensure_ready(self, timeout: float = 10.0) -> None:
        if self._shutdown:
            raise RuntimeError("Audio service has shut down")
        if self._failure_reported:
            raise RuntimeError("Audio process stopped")
        self._start()
        deadline = time.monotonic() + max(0.1, float(timeout))
        while not self._ready:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Audio process did not become ready")
            try:
                event = self._events.get(timeout=min(0.05, remaining))
            except Empty:
                if not self._process.is_alive():
                    raise RuntimeError("Audio process stopped during startup")
                continue
            except (EOFError, OSError) as exc:
                raise RuntimeError("Audio process stopped during startup") from exc
            self._handle_event(event)

    def create_player(self, parent: Optional[QObject] = None) -> AudioPlayerProxy:
        player_id = f"player-{next(self._counter)}"
        self.state_cache.ensure(player_id)
        proxy = AudioPlayerProxy(self, player_id, parent)
        self.post(player_id, "create")
        return proxy

    def post(self, player_id: str, command: str, payload: Optional[dict] = None) -> None:
        if self._shutdown or self._failure_reported:
            return
        self._start()
        self._commands.put_nowait((str(player_id), str(command), dict(payload or {}), 0))

    def post_runtime(self, command: str, payload: Optional[dict] = None) -> None:
        self.post("__runtime__", command, payload)

    def request_async(self, player_id: str, command: str, payload: Optional[dict] = None) -> Future:
        future: Future = Future()
        if self._shutdown or self._failure_reported:
            future.set_exception(RuntimeError(
                "Audio service has shut down" if self._shutdown else "Audio process stopped"
            ))
            return future
        self._start()
        token = next(self._request_counter)
        self._pending_results[token] = future
        self._commands.put_nowait((str(player_id), str(command), dict(payload or {}), token))
        return future

    def call(self, player_id: str, command: str, payload: Optional[dict] = None, timeout: float = 2.0):
        future = self.request_async(player_id, command, payload)
        deadline = time.monotonic() + max(0.1, float(timeout))
        while not future.done():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Audio command timed out: {command}")
            try:
                event = self._events.get(timeout=min(0.05, remaining))
            except Empty:
                if self._process is not None and not self._process.is_alive():
                    self._mark_failed()
                    break
                continue
            except (EOFError, OSError):
                self._mark_failed()
                break
            self._handle_event(event)
        return future.result()

    def set_output_device(self, device: str) -> None:
        self._output_device = str(device or "")
        if self._process is not None:
            self.post_runtime("output_device", {"device": self._output_device})

    def set_preload_policy(self, enabled: bool, limit_mb: int, pressure: bool, use_ffmpeg: bool) -> None:
        self._preload_policy = (bool(enabled), int(limit_mb), bool(pressure), bool(use_ffmpeg))
        self._preload_enabled = bool(enabled)
        if not enabled:
            self._preloaded_paths.clear()
        limit_bytes = max(0, int(limit_mb)) * 1024 * 1024
        self._preload_capacity = (limit_bytes, limit_bytes, 0)
        if self._process is not None:
            self.post_runtime("preload_policy", {"policy": self._preload_policy})

    def set_waveform_limit(self, limit_mb: int) -> None:
        self._waveform_limit = int(limit_mb)
        if self._process is not None:
            self.post_runtime("waveform_cache", {"limit_mb": self._waveform_limit})

    def set_timecode_config(self, config: dict) -> None:
        configuration = dict(config)
        if configuration == self._timecode_config:
            return
        self._timecode_config = configuration
        self.post_runtime("timecode_config", configuration)

    def meterLevels(self) -> tuple[float, float]:
        return self._meter_levels

    def playerMeterLevels(self, player_id: str) -> tuple[float, float]:
        return self._player_meters.get(str(player_id), (0.0, 0.0))

    def is_audio_preloaded(self, file_path: str) -> bool:
        if not file_path:
            return False
        import os
        return os.path.normcase(os.path.abspath(str(file_path))) in self._preloaded_paths

    def preload_runtime_status(self) -> tuple[bool, int]:
        return self._preload_enabled, self._preload_active

    def preload_capacity_bytes(self) -> tuple[int, int, int]:
        return self._preload_capacity

    def _drain_events(self) -> None:
        if self._events is None:
            return
        for _ in range(256):
            try:
                event = self._events.get_nowait()
            except Empty:
                break
            except (EOFError, OSError):
                self._mark_failed()
                break
            self._handle_event(event)
        if not self._shutdown and self._process is not None and not self._process.is_alive():
            self._mark_failed()

    def _mark_failed(self) -> None:
        if self._failure_reported or self._shutdown:
            return
        self._failure_reported = True
        error = RuntimeError("Audio process stopped unexpectedly")
        for future in self._pending_results.values():
            if not future.done():
                future.set_exception(error)
        self._pending_results.clear()
        self.serviceFailed.emit(str(error))

    def _handle_event(self, event) -> None:
        kind = event[0]
        if kind == "ready":
            self._ready = True
        elif kind == "position":
            _, player_id, value, sampled_at = event
            self.state_cache.update_position(player_id, value)
            self.positionSampled.emit(player_id, value, sampled_at)
            self.positionChanged.emit(player_id, value)
        elif kind == "duration":
            _, player_id, value = event
            self.state_cache.update_duration(player_id, value)
            self.durationChanged.emit(player_id, value)
        elif kind == "state":
            _, player_id, value = event
            self.state_cache.update_state(player_id, value)
            self.stateChanged.emit(player_id, value)
        elif kind == "media":
            _, player_id, request_id, ok, error = event
            self.mediaLoadFinished.emit(player_id, request_id, ok, error)
        elif kind == "result":
            _, token, ok, value = event
            future = self._pending_results.pop(token, None)
            if future is not None and not future.done():
                if ok:
                    future.set_result(value)
                else:
                    future.set_exception(RuntimeError(str(value)))
        elif kind == "meter":
            self._meter_levels = (event[1], event[2])
            self._worker_meter_times.append(float(event[3]))
        elif kind == "player_meter":
            self._player_meters[event[1]] = (event[2], event[3])
        elif kind == "preload_status":
            _, enabled, active, capacity, paths = event
            self._preload_enabled = bool(enabled)
            self._preload_active = int(active)
            self._preload_capacity = tuple(capacity)
            self._preloaded_paths = set(paths)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._event_timer.stop()
        if self._process is not None:
            if self._process.is_alive():
                self._commands.put_nowait(("__runtime__", "shutdown", {}, 0))
                self._process.join(timeout=2.0)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1.0)
            self._process.close()
            self._process = None
            self._commands.close()
            self._events.close()
        for future in self._pending_results.values():
            if not future.done():
                future.set_exception(RuntimeError("Audio service has shut down"))
        self._pending_results.clear()


class ProcessLtcAudioOutput:
    def __init__(self, controller: ProcessAudioServiceController) -> None:
        self._controller = controller
        self._configuration = (None, 48000, 16, 30.0)

    def set_output(self, device_name, sample_rate, bit_depth, fps) -> None:
        configuration = (device_name, int(sample_rate), int(bit_depth), float(fps))
        if configuration == self._configuration:
            return
        self._configuration = configuration
        self._controller.post_runtime("ltc_set_output", {
            "device": device_name, "sample_rate": sample_rate, "bit_depth": bit_depth, "fps": fps,
        })

    def update(self, current_frame, fps, *, running: bool = True) -> None:
        if self._configuration[0] is None:
            return
        self._controller.post_runtime("ltc_update", {
            "current_frame": current_frame, "fps": fps, "running": running,
        })

    def request_resync(self) -> None:
        self._controller.post_runtime("ltc_resync")

    def shutdown(self) -> None:
        self._controller.post_runtime("ltc_shutdown")
        self._configuration = (None, 48000, 16, 30.0)


class ProcessMtcMidiOutput:
    def __init__(self, controller: ProcessAudioServiceController, idle_behavior_provider) -> None:
        self._controller = controller
        self._idle_behavior_provider = idle_behavior_provider
        self._device = MIDI_OUTPUT_DEVICE_NONE

    def set_device(self, device_id) -> None:
        device = str(device_id or MIDI_OUTPUT_DEVICE_NONE)
        if device == self._device:
            return
        self._device = device
        self._controller.post_runtime("mtc_set_device", {"device": device_id})

    def update(self, current_frame, source_fps, mtc_fps, *, running: bool = True) -> None:
        if self._device == MIDI_OUTPUT_DEVICE_NONE:
            return
        self._controller.post_runtime("mtc_update", {
            "current_frame": current_frame, "source_fps": source_fps, "mtc_fps": mtc_fps,
            "running": running, "idle_behavior": self._idle_behavior_provider(),
        })

    def request_resync(self) -> None:
        self._controller.post_runtime("mtc_resync")

    def shutdown(self) -> None:
        self._controller.post_runtime("mtc_shutdown")
        self._device = MIDI_OUTPUT_DEVICE_NONE
