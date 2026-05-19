from __future__ import annotations

import os
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pytest
from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication

import pyssp.audio_engine as audio_engine
from pyssp.settings_store import AppSettings
from pyssp.ui import main_window as mw
from pyssp.utility_audio import UtilitySoundSpec


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _write_dummy_wav(path: Path, duration_sec: float = 0.20, sample_rate: int = 22050) -> None:
    frame_count = max(1, int(duration_sec * sample_rate))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


class _DummyLtcSender:
    def set_output(self, *_args, **_kwargs):
        return None

    def update(self, *_args, **_kwargs):
        return None

    def request_resync(self):
        return None

    def shutdown(self):
        return None


class _DummyMtcSender:
    def __init__(self, *_args, **_kwargs):
        pass

    def set_device(self, *_args, **_kwargs):
        return None

    def update(self, *_args, **_kwargs):
        return None

    def request_resync(self):
        return None

    def shutdown(self):
        return None


class _ControllableDummyStream:
    def __init__(self, player, registry: "_DummyStreamRegistry") -> None:
        self._player = player
        self._registry = registry
        self._running = False
        self._closed = False
        registry.register(self)

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def close(self) -> None:
        self._closed = True
        self._running = False

    def pump(self, frames: int = 1024, count: int = 1) -> None:
        if self._closed:
            return
        channels = max(1, int(getattr(self._player, "_channels", 2)))
        for _ in range(max(0, int(count))):
            if (not self._running) or self._closed:
                return
            outdata = np.zeros((frames, channels), dtype=np.float32)
            self._player._audio_callback(outdata, frames, None, None)


class _DummyStreamRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._streams: list[_ControllableDummyStream] = []

    def build_stream(self, player) -> _ControllableDummyStream:
        return _ControllableDummyStream(player, self)

    def register(self, stream: _ControllableDummyStream) -> None:
        with self._lock:
            self._streams.append(stream)

    def snapshot(self) -> list[_ControllableDummyStream]:
        with self._lock:
            return list(self._streams)

    def pump_all(self, frames: int = 1024, count: int = 1) -> None:
        for stream in self.snapshot():
            stream.pump(frames=frames, count=count)


def _process_events(qapp: QApplication, delay_ms: int = 15) -> None:
    qapp.processEvents()
    loop = QEventLoop()
    QTimer.singleShot(max(0, int(delay_ms)), loop.quit)
    loop.exec_()
    qapp.processEvents()


def _wait_until(
    qapp: QApplication,
    registry: _DummyStreamRegistry,
    predicate,
    *,
    timeout_ms: int = 4000,
    pump_count: int = 2,
    delay_ms: int = 15,
) -> None:
    deadline = time.monotonic() + (max(1, int(timeout_ms)) / 1000.0)
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
            last_error = None
        except Exception as exc:  # pragma: no cover - defensive during polling
            last_error = exc
        registry.pump_all(count=pump_count)
        _process_events(qapp, delay_ms=delay_ms)
    if last_error is not None:
        raise last_error
    raise AssertionError("Timed out waiting for playback condition")


def _cleanup_main_window(window, qapp: QApplication) -> None:
    for timer_name in [
        "meter_timer",
        "timecode_mtc_timer",
        "fade_timer",
        "_preload_trim_timer",
        "_preload_status_timer",
        "talk_blink_timer",
        "_midi_poll_timer",
    ]:
        timer = getattr(window, timer_name, None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
    try:
        window._hard_stop_all()
    except Exception:
        pass
    try:
        window._audio_service.shutdown()
    except Exception:
        pass
    try:
        window.close()
    except Exception:
        window.hide()
    window.deleteLater()
    qapp.processEvents()


def _configure_common_window_monkeypatches(monkeypatch, registry: _DummyStreamRegistry, settings: AppSettings) -> None:
    monkeypatch.setattr(audio_engine.ExternalMediaPlayer, "_create_stream", lambda self: registry.build_stream(self))
    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)


def _build_settings(*, utility_controls: bool = True) -> AppSettings:
    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.utility_sound_buttons_follow_playback_controls = bool(utility_controls)
    return settings


def _build_window(qapp: QApplication, monkeypatch, *, utility_controls: bool = True):
    registry = _DummyStreamRegistry()
    _configure_common_window_monkeypatches(monkeypatch, registry, _build_settings(utility_controls=utility_controls))
    window = mw.MainWindow()
    window.show()
    _wait_until(qapp, registry, lambda: len(registry.snapshot()) >= 1, timeout_ms=2500, pump_count=0)
    window.player.setNotifyInterval(20)
    window.player_b.setNotifyInterval(20)
    _process_events(qapp, delay_ms=40)
    return window, registry


def _assign_file_slot(slot, audio_path: Path, title: str) -> None:
    slot.source_type = "file"
    slot.file_path = str(audio_path)
    slot.utility_spec = None
    slot.title = title
    slot.marker = False
    slot.locked = False
    slot.load_failed = False
    slot.played = False
    slot.activity_code = "7"


def _assign_utility_slot(slot, title: str, duration_ms: int = 200) -> None:
    slot.source_type = "utility"
    slot.file_path = ""
    slot.utility_spec = UtilitySoundSpec(mode="blank", duration_ms=int(duration_ms))
    slot.title = title
    slot.marker = False
    slot.locked = False
    slot.load_failed = False
    slot.played = False
    slot.activity_code = "7"


def _start_slot_and_wait(window, registry: _DummyStreamRegistry, qapp: QApplication, slot_index: int) -> None:
    assert window._play_slot(slot_index) is True
    expected_key = (window._view_group_key(), window.current_page, int(slot_index))
    _wait_until(
        qapp,
        registry,
        lambda: window.current_playing == expected_key and window.player.state() == window.player.PlayingState,
    )


@pytest.mark.monkey
def test_track_end_transition_uses_captured_page_context(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "captured_context.wav"
    _write_dummy_wav(audio_path)
    window, _registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        _assign_utility_slot(window.data["A"][0][0], "Utility first")
        _assign_file_slot(window.data["A"][0][1], audio_path, "Normal second")
        window.page_playlist_enabled["A"][0] = True
        window.current_group = "B"
        window.current_page = 1
        window.current_playing = ("A", 0, 0)
        window._player_slot_key_map[id(window.player)] = ("A", 0, 0)
        window._active_playing_keys.add(("A", 0, 0))
        transition = window._capture_track_end_transition_state()
        window.current_group = "B"
        window.current_page = 1
        window.current_playing = None
        window._player_slot_key_map.clear()
        window._active_playing_keys.clear()
        started: list[int] = []
        window._play_slot_via_control_flow = lambda slot_index, allow_fade=True: started.append(int(slot_index)) is None or True  # type: ignore[method-assign]
        assert window._handle_track_end_transition(transition) is True
        assert started == [1]
        assert window.current_group == "A"
        assert window.current_page == 0
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
@pytest.mark.parametrize(
    ("start_type", "next_type"),
    [("file", "utility"), ("utility", "file")],
)
def test_playlist_auto_advance_mixed_page_real_players(qapp, monkeypatch, tmp_path, start_type, next_type):
    audio_path = tmp_path / f"playlist_{start_type}_to_{next_type}.wav"
    _write_dummy_wav(audio_path)
    window, registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        if start_type == "file":
            _assign_file_slot(page[0], audio_path, "First")
        else:
            _assign_utility_slot(page[0], "First")
        if next_type == "file":
            _assign_file_slot(page[1], audio_path, "Second")
        else:
            _assign_utility_slot(page[1], "Second")
        page[0].played = True
        page[0].activity_code = "2"
        window.page_playlist_enabled["A"][0] = True
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 0)
        _wait_until(
            qapp,
            registry,
            lambda: window.current_playing == ("A", 0, 1) and window.player.state() == window.player.PlayingState,
            timeout_ms=4500,
        )
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_playlist_auto_advance_utility_to_regular_preserves_pending_track_end_state(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "utility_to_regular_pending.wav"
    _write_dummy_wav(audio_path)
    original_prepare = audio_engine._prepare_audio_source

    def _slow_prepare(source, *args, **kwargs):
        source_type = ""
        if isinstance(source, dict):
            source_type = str(source.get("source_type", ""))
        if source_type != "utility":
            time.sleep(0.08)
        return original_prepare(source, *args, **kwargs)

    monkeypatch.setattr(audio_engine, "_prepare_audio_source", _slow_prepare)
    window, registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        _assign_utility_slot(page[0], "Utility first")
        _assign_file_slot(page[1], audio_path, "Normal second")
        page[0].played = True
        page[0].activity_code = "2"
        window.page_playlist_enabled["A"][0] = True
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 0)
        _wait_until(
            qapp,
            registry,
            lambda: window._track_end_transition_target_key() == ("A", 0, 1),
            timeout_ms=2500,
        )
        assert window.current_playing is None
        _wait_until(
            qapp,
            registry,
            lambda: window.current_playing == ("A", 0, 1) and window.player.state() == window.player.PlayingState,
            timeout_ms=4500,
        )
        assert window._track_end_transition_target_key() is None
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_playlist_auto_advance_uses_playing_page_not_visible_page_real_players(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "playing_page_real.wav"
    _write_dummy_wav(audio_path)
    window, registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        playlist_page = window.data["A"][0]
        _assign_utility_slot(playlist_page[0], "Track 1")
        _assign_file_slot(playlist_page[1], audio_path, "Track 2")
        playlist_page[0].played = True
        playlist_page[0].activity_code = "2"
        _assign_file_slot(window.data["B"][1][0], audio_path, "Visible page file")
        window.page_playlist_enabled["A"][0] = True
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 0)
        window.current_group = "B"
        window.current_page = 1
        window._refresh_group_buttons()
        window._refresh_page_list()
        window._refresh_sound_grid()
        _wait_until(
            qapp,
            registry,
            lambda: window.current_playing == ("A", 0, 1) and window.player.state() == window.player.PlayingState,
            timeout_ms=4500,
        )
        assert window.current_group == "A"
        assert window.current_page == 0
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_next_button_enabled_for_utility_only_page_real_players(qapp, monkeypatch):
    window, registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        _assign_utility_slot(page[0], "Utility first")
        _assign_utility_slot(page[1], "Utility second")
        window.page_playlist_enabled["A"][0] = True
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        window._update_next_button_enabled()
        next_btn = window.control_buttons.get("Next")
        assert next_btn is not None
        assert next_btn.isEnabled() is True
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
@pytest.mark.parametrize(
    ("start_type", "next_type"),
    [("file", "utility"), ("utility", "file")],
)
def test_shuffle_auto_advance_real_players(qapp, monkeypatch, tmp_path, start_type, next_type):
    audio_path = tmp_path / f"shuffle_{start_type}.wav"
    _write_dummy_wav(audio_path)
    window, registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        if start_type == "file":
            _assign_file_slot(page[0], audio_path, "First")
        else:
            _assign_utility_slot(page[0], "First")
        if next_type == "file":
            _assign_file_slot(page[1], audio_path, "Second")
        else:
            _assign_utility_slot(page[1], "Second")
        page[0].played = True
        page[0].activity_code = "2"
        window.page_playlist_enabled["A"][0] = True
        window.page_shuffle_enabled["A"][0] = True
        window.playlist_play_mode = "any_available"
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 0)
        _wait_until(
            qapp,
            registry,
            lambda: window.current_playing == ("A", 0, 1) and window.player.state() == window.player.PlayingState,
            timeout_ms=4500,
        )
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
@pytest.mark.parametrize("source_type", ["file", "utility"])
def test_loop_single_restart_real_players(qapp, monkeypatch, tmp_path, source_type):
    audio_path = tmp_path / f"loop_single_{source_type}.wav"
    _write_dummy_wav(audio_path)
    window, registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        slot = window.data["A"][0][0]
        if source_type == "file":
            _assign_file_slot(slot, audio_path, "Loop me")
        else:
            _assign_utility_slot(slot, "Loop me")
        window.page_playlist_enabled["A"][0] = True
        window.loop_enabled = True
        window.playlist_loop_mode = "loop_single"
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 0)
        started_at = float(window._track_started_at)
        _wait_until(
            qapp,
            registry,
            lambda: window.current_playing == ("A", 0, 0)
            and window.player.state() == window.player.PlayingState
            and float(window._track_started_at) > started_at,
            timeout_ms=4500,
        )
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_loop_list_wrap_real_players(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "loop_list_wrap.wav"
    _write_dummy_wav(audio_path)
    window, registry = _build_window(qapp, monkeypatch)
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        _assign_file_slot(page[0], audio_path, "First")
        _assign_utility_slot(page[1], "Second")
        page[0].played = True
        page[1].played = True
        page[1].activity_code = "2"
        window.page_playlist_enabled["A"][0] = True
        window.loop_enabled = True
        window.playlist_loop_mode = "loop_list"
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 1)
        _wait_until(
            qapp,
            registry,
            lambda: window.current_playing == ("A", 0, 0) and window.player.state() == window.player.PlayingState,
            timeout_ms=4500,
        )
        assert page[0].played is True
        assert page[1].played is False
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_utility_controls_disabled_blocks_playlist_and_next_real_players(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "utility_controls_disabled.wav"
    _write_dummy_wav(audio_path)
    window, registry = _build_window(qapp, monkeypatch, utility_controls=False)
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        _assign_utility_slot(page[0], "Utility first")
        window.page_playlist_enabled["A"][0] = True
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        window._update_next_button_enabled()
        next_btn = window.control_buttons.get("Next")
        assert next_btn is not None
        assert next_btn.isEnabled() is False
        _assign_file_slot(page[1], audio_path, "Normal second")
        page[0].played = True
        page[0].activity_code = "2"
        _start_slot_and_wait(window, registry, qapp, 0)
        _wait_until(
            qapp,
            registry,
            lambda: window.player.state() == window.player.StoppedState and window.current_playing is None,
            timeout_ms=4500,
        )
        assert window._track_end_transition_target_key() is None
        assert window.current_playing is None
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_utility_controls_disabled_blocks_shuffle_and_loop_real_players(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "utility_controls_disabled_shuffle.wav"
    _write_dummy_wav(audio_path)
    window, registry = _build_window(qapp, monkeypatch, utility_controls=False)
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        _assign_file_slot(page[0], audio_path, "Normal first")
        _assign_utility_slot(page[1], "Utility second")
        page[0].played = True
        page[0].activity_code = "2"
        window.page_playlist_enabled["A"][0] = True
        window.page_shuffle_enabled["A"][0] = True
        window.playlist_play_mode = "any_available"
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 0)
        _wait_until(
            qapp,
            registry,
            lambda: window.player.state() == window.player.StoppedState and window.current_playing is None,
            timeout_ms=4500,
        )
        assert window.current_playing is None
        window._reset_set_data()
        loop_slot = window.data["A"][0][0]
        _assign_utility_slot(loop_slot, "Loop me")
        window.page_playlist_enabled["A"][0] = True
        window.loop_enabled = True
        window.playlist_loop_mode = "loop_single"
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        _start_slot_and_wait(window, registry, qapp, 0)
        _wait_until(
            qapp,
            registry,
            lambda: window.player.state() == window.player.StoppedState and window.current_playing is None,
            timeout_ms=4500,
        )
        assert window.current_playing is None
    finally:
        _cleanup_main_window(window, qapp)
