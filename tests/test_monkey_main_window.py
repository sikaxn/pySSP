from __future__ import annotations

import os
import random
import wave
from itertools import combinations
from pathlib import Path

import pytest
from PyQt5.QtCore import QMimeData, QUrl
from PyQt5.QtWidgets import QApplication, QLabel

from pyssp.automation_command import (
    AUTOMATION_DEFAULT_BUTTON_COLOR,
    AUTOMATION_SOURCE_TYPE,
    AutomationCommandSpec,
    SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
    SoundButtonAutomationConfig,
)
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
        window.close()
    except Exception:
        window.hide()
    window.deleteLater()
    qapp.processEvents()


def _pair_keys(case: dict[str, object], names: list[str]) -> set[tuple[str, object, str, object]]:
    out: set[tuple[str, object, str, object]] = set()
    for i, j in combinations(range(len(names)), 2):
        a = names[i]
        b = names[j]
        out.add((a, case[a], b, case[b]))
    return out


def _build_pairwise_cases(values: dict[str, list[object]], seed: int = 20260413) -> list[dict[str, object]]:
    rng = random.Random(seed)
    names = list(values.keys())
    uncovered: set[tuple[str, object, str, object]] = set()
    for i, j in combinations(range(len(names)), 2):
        a = names[i]
        b = names[j]
        for va in values[a]:
            for vb in values[b]:
                uncovered.add((a, va, b, vb))
    cases: list[dict[str, object]] = []
    while uncovered:
        best_case: dict[str, object] | None = None
        best_cover: set[tuple[str, object, str, object]] = set()
        for _ in range(160):
            candidate = {name: rng.choice(values[name]) for name in names}
            cover = _pair_keys(candidate, names) & uncovered
            if len(cover) > len(best_cover):
                best_case = candidate
                best_cover = cover
        if best_case is None:
            break
        cases.append(best_case)
        uncovered -= best_cover
    return cases


def _settings_for_combo(combo: dict[str, object]) -> AppSettings:
    s = AppSettings()
    s.tips_open_on_startup = False
    s.reset_all_on_startup = False
    s.last_group = "A"
    s.last_page = 0
    s.web_remote_enabled = False
    s.search_lyric_on_add_sound_button = bool(combo["search_lyric_on_add_sound_button"])
    s.verify_sound_file_on_add = bool(combo["verify_sound_file_on_add"])
    s.allow_other_unsupported_audio_files = bool(combo["allow_other_unsupported_audio_files"])
    s.candidate_error_action = str(combo["candidate_error_action"])
    s.main_transport_timeline_mode = str(combo["main_transport_timeline_mode"])
    s.rapid_fire_play_mode = str(combo["rapid_fire_play_mode"])
    s.supported_audio_format_extensions = [".wav", "mp3"]
    return s


@pytest.mark.monkey
def test_monkey_main_window_pairwise_settings_combo(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "dummy.wav"
    lyric_path = tmp_path / "dummy.lrc"
    _write_dummy_wav(audio_path)
    lyric_path.write_text("[00:01.00]dummy line\n", encoding="utf-8")

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

    # Keep startup deterministic and avoid external side effects.
    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())
    monkeypatch.setattr(mw.QFileDialog, "getOpenFileNames", lambda *args, **kwargs: ([str(audio_path)], ""))

    dimensions: dict[str, list[object]] = {
        "search_lyric_on_add_sound_button": [False, True],
        "verify_sound_file_on_add": [False, True],
        "allow_other_unsupported_audio_files": [False, True],
        "candidate_error_action": ["stop_playback", "keep_playing"],
        "main_transport_timeline_mode": ["cue_region", "audio_file"],
        "rapid_fire_play_mode": ["unplayed_only", "any_available"],
    }
    cases = _build_pairwise_cases(dimensions)
    assert len(cases) >= 6

    initial = _settings_for_combo(cases[0])
    monkeypatch.setattr(mw, "load_settings", lambda s=initial: s)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        for combo in cases:
            calls = {"verify": 0, "lyric_prompt": 0, "play_slot": 0, "stop_playback": 0}

            window._reset_set_data()
            window.current_group = "A"
            window.current_page = 0
            window.page_names["A"][0] = "Monkey Page A1"
            window.settings.last_sound_dir = str(tmp_path)
            window.search_lyric_on_add_sound_button = bool(combo["search_lyric_on_add_sound_button"])
            window.verify_sound_file_on_add = bool(combo["verify_sound_file_on_add"])
            window.allow_other_unsupported_audio_files = bool(combo["allow_other_unsupported_audio_files"])
            window.candidate_error_action = str(combo["candidate_error_action"])
            window.main_transport_timeline_mode = str(combo["main_transport_timeline_mode"])
            window.rapid_fire_play_mode = str(combo["rapid_fire_play_mode"])
            window.supported_audio_format_extensions = [".wav", ".mp3"]

            def _verify(paths):
                calls["verify"] += 1
                return []

            def _prompt(paths):
                calls["lyric_prompt"] += 1
                return [str(lyric_path) for _ in paths]

            window._verify_audio_files_before_add = _verify  # type: ignore[method-assign]
            window._prompt_lyric_link_selection = _prompt  # type: ignore[method-assign]

            # User flow: add sound to current page.
            window._pick_sound(0)
            slot = window.data["A"][0][0]
            assert slot.assigned is True
            assert Path(slot.file_path) == audio_path
            assert calls["verify"] == (1 if combo["verify_sound_file_on_add"] else 0)
            assert calls["lyric_prompt"] == (1 if combo["search_lyric_on_add_sound_button"] else 0)
            if combo["search_lyric_on_add_sound_button"]:
                assert Path(slot.lyric_file) == lyric_path
            else:
                assert slot.lyric_file == ""

            # User flow: switch groups/pages and toggle controls.
            window._select_group("B")
            window.page_names["B"][0] = "Monkey Page B1"
            window._select_page(0)
            window._toggle_playlist_mode(True)
            window._toggle_shuffle_mode(True)
            assert window.page_playlist_enabled["B"][0] is True
            assert window.page_shuffle_enabled["B"][0] is True
            window._toggle_loop(True)
            assert window.loop_enabled is True
            window._toggle_talk(True)
            assert window.talk_active is True
            window._toggle_talk(False)
            assert window.talk_active is False
            window._toggle_cue_mode(True)
            assert window.cue_mode is True
            window._toggle_cue_mode(False)
            assert window.cue_mode is False
            window._select_group("A")
            window._select_page(0)

            # Settings-driven behavior: file dialog filter text.
            filter_text = window._audio_file_dialog_filter()
            if combo["allow_other_unsupported_audio_files"]:
                assert "All Files (*.*)" in filter_text
            else:
                assert "All Files (*.*)" not in filter_text

            # Settings-driven behavior: transport bounds.
            window.current_playing = ("A", 0, 0)
            window.current_duration_ms = 3000
            slot.cue_start_ms = 500
            slot.cue_end_ms = 1200
            low, high = window._main_transport_bounds()
            if combo["main_transport_timeline_mode"] == "audio_file":
                assert (low, high) == (0, 3000)
            else:
                assert (low, high) == (500, 1200)

            # Settings-driven behavior: rapid-fire + candidate error handling.
            rapid_slot = window.data["A"][0][0]
            rapid_slot.played = True

            def _fake_play_slot(_slot_index, allow_fade=True):
                calls["play_slot"] += 1
                return False

            def _fake_stop_playback():
                calls["stop_playback"] += 1

            window._play_slot = _fake_play_slot  # type: ignore[method-assign]
            window._stop_playback = _fake_stop_playback  # type: ignore[method-assign]

            window._on_rapid_fire_clicked()
            if combo["rapid_fire_play_mode"] == "unplayed_only":
                assert calls["play_slot"] == 0
            else:
                assert calls["play_slot"] >= 1

            calls["play_slot"] = 0
            calls["stop_playback"] = 0
            rapid_slot.played = False
            window._on_rapid_fire_clicked()
            assert calls["play_slot"] >= 1
            if combo["candidate_error_action"] == "stop_playback":
                assert calls["stop_playback"] == 1
            else:
                assert calls["stop_playback"] == 0
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_pick_sound_limits_verify_and_lyric_scan_to_available_slots(qapp, monkeypatch, tmp_path):
    audio_paths = [tmp_path / "a.wav", tmp_path / "b.wav", tmp_path / "c.wav"]
    for path in audio_paths:
        _write_dummy_wav(path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.search_lyric_on_add_sound_button = True
    settings.verify_sound_file_on_add = True
    settings.supported_audio_format_extensions = [".wav"]
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)
    monkeypatch.setattr(
        mw.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: ([str(path) for path in audio_paths], ""),
    )

    calls = {"verify_paths": 0, "lyric_paths": 0}
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_names["A"][0] = "Capacity Page"
        window.verify_sound_file_on_add = True
        window.search_lyric_on_add_sound_button = True
        for idx in range(1, mw.SLOTS_PER_PAGE):
            slot = window.data["A"][0][idx]
            slot.file_path = str(audio_paths[0])
            slot.title = f"Filled {idx + 1}"

        def _verify(paths):
            calls["verify_paths"] = len(paths)
            return []

        def _prompt(paths):
            calls["lyric_paths"] = len(paths)
            return ["" for _ in paths]

        window._verify_audio_files_before_add = _verify  # type: ignore[method-assign]
        window._prompt_lyric_link_selection = _prompt  # type: ignore[method-assign]

        window._pick_sound(0)

        assert calls["verify_paths"] == 1
        assert calls["lyric_paths"] == 1
        assert window.data["A"][0][0].assigned is True
        assert window.data["A"][0][0].file_path == str(audio_paths[0])
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_next_playlist_slot_ignores_current_track_from_different_page(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "playlist_same_group.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw.MainWindow, "_clear_main_waveform_display", lambda self: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        page = window.data["A"][0]
        page[0].file_path = str(audio_path)
        page[0].title = "First"
        page[1].file_path = str(audio_path)
        page[1].title = "Second"
        other_page_slot = window.data["A"][1][10]
        other_page_slot.file_path = str(audio_path)
        other_page_slot.title = "Elsewhere"
        window.page_playlist_enabled["A"][0] = True
        window.current_playing = ("A", 1, 10)

        assert window._has_next_playlist_slot() is True
        assert window._next_playlist_slot(for_auto_advance=False) == 0
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_sound_button_simple_automation_start_and_stop_events(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "automation_events.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    captured: list[list[str]] = []
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_names["A"][0] = "Automation Events"
        slot = window.data["A"][0][0]
        slot.file_path = str(audio_path)
        slot.title = "Automation Event Song"
        slot.sound_button_automation = SoundButtonAutomationConfig(
            mode=SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
            on_become_playing=[
                AutomationCommandSpec(location="5/1/2", button_text="Start One"),
                AutomationCommandSpec(location="5/1/3", button_text="Start Two"),
            ],
            on_leave_playing=[
                AutomationCommandSpec(location="5/1/4", button_text="Stop One"),
            ],
        )

        window._send_companion_command_specs_async = (  # type: ignore[method-assign]
            lambda specs: captured.append([spec.location for spec in specs]) or True
        )

        assert window._play_slot(0) is True
        assert captured[0] == ["5/1/2", "5/1/3"]

        window._stop_playback()
        assert captured[1] == ["5/1/4"]
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_next_button_enabled_while_idle_when_next_candidate_exists(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "next_idle.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        slot = window.data["A"][0][0]
        slot.file_path = str(audio_path)
        slot.title = "Idle next"

        window.current_playing = None
        window._update_next_button_enabled()

        next_btn = window.control_buttons.get("Next")
        assert next_btn is not None
        assert next_btn.isEnabled() is True

        slot.file_path = ""
        slot.title = ""
        window._update_next_button_enabled()
        assert next_btn.isEnabled() is False
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_utility_sound_buttons_follow_playback_controls_by_default_for_next(qapp, monkeypatch):
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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        slot = window.data["A"][0][0]
        slot.source_type = "utility"
        slot.utility_spec = UtilitySoundSpec(mode="blank", duration_ms=1000)
        slot.title = "Utility"

        assert window.utility_sound_buttons_follow_playback_controls is True
        assert window._next_available_slot_on_current_page() == 0
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_automation_sound_buttons_use_distinct_default_color_and_are_excluded_from_next_by_default(
    qapp, monkeypatch
):
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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        slot = window.data["A"][0][0]
        slot.source_type = AUTOMATION_SOURCE_TYPE
        slot.automation_spec = AutomationCommandSpec(location="5/1/2", button_text="Automation")
        slot.title = "Automation"

        assert window.automation_command_buttons_follow_playback_controls is False
        assert window._slot_color(slot, 0) == AUTOMATION_DEFAULT_BUTTON_COLOR
        assert window._next_available_slot_on_current_page() is None

        window._update_next_button_enabled()
        next_btn = window.control_buttons.get("Next")
        assert next_btn is not None
        assert next_btn.isEnabled() is False
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_automation_sound_buttons_can_join_next_when_enabled_without_interrupting_audio(qapp, monkeypatch):
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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.automation_command_buttons_follow_playback_controls = True
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        slot = window.data["A"][0][0]
        slot.source_type = AUTOMATION_SOURCE_TYPE
        slot.automation_spec = AutomationCommandSpec(location="5/1/2", button_text="Automation")
        slot.title = "Automation"
        window.current_playing = ("B", 0, 7)

        sent_calls: list[tuple[str, str]] = []
        stop_calls: list[bool] = []
        window._send_companion_location_command_async = (  # type: ignore[method-assign]
            lambda location, action: sent_calls.append((location, action)) or True
        )
        window._stop_playback = lambda: stop_calls.append(True)  # type: ignore[method-assign]

        assert window._next_available_slot_on_current_page() == 0
        assert window._play_slot(0) is True
        assert sent_calls == [("5/1/2", "press")]
        assert stop_calls == []
        assert window.current_playing == ("B", 0, 7)
        assert slot.played is True
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_playlist_clicking_automation_button_continues_to_next_sound(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "automation_playlist_next.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.automation_command_buttons_follow_playback_controls = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_playlist_enabled["A"][0] = True

        automation_slot = window.data["A"][0][0]
        automation_slot.source_type = AUTOMATION_SOURCE_TYPE
        automation_slot.automation_spec = AutomationCommandSpec(location="5/1/2", button_text="Automation")
        automation_slot.title = "Automation"

        regular_slot = window.data["A"][0][1]
        regular_slot.file_path = str(audio_path)
        regular_slot.title = "Next Song"

        sent_calls: list[tuple[str, str]] = []
        next_started: list[int] = []
        window._send_companion_location_command_async = (  # type: ignore[method-assign]
            lambda location, action: sent_calls.append((location, action)) or True
        )
        window._play_slot_via_control_flow = lambda slot_index, allow_fade=True: next_started.append(int(slot_index)) or True  # type: ignore[method-assign]

        assert window._play_slot(0) is True
        assert sent_calls == [("5/1/2", "press")]
        assert next_started == [1]
        assert window.current_playlist_start == 0
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_playlist_auto_advance_runs_automation_buttons_in_order_between_sounds(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "automation_playlist_chain.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.automation_command_buttons_follow_playback_controls = True
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_playlist_enabled["A"][0] = True
        window.current_playlist_start = 0

        page = window.data["A"][0]
        page[0].file_path = str(audio_path)
        page[0].title = "Sound 0"
        page[1].source_type = AUTOMATION_SOURCE_TYPE
        page[1].automation_spec = AutomationCommandSpec(location="5/1/2", button_text="Auto 1")
        page[1].title = "Auto 1"
        page[2].file_path = str(audio_path)
        page[2].title = "Sound 1"
        page[3].source_type = AUTOMATION_SOURCE_TYPE
        page[3].automation_spec = AutomationCommandSpec(location="6/1/2", button_text="Auto 2")
        page[3].title = "Auto 2"

        sent_calls: list[tuple[str, str]] = []
        started_audio: list[int] = []
        window._send_companion_location_command_async = (  # type: ignore[method-assign]
            lambda location, action: sent_calls.append((location, action)) or True
        )

        def _fake_play_slot(
            slot_index,
            allow_fade=True,
            prefer_immediate_load=False,
            continue_playlist_after_automation=True,
        ):
            _ = allow_fade, prefer_immediate_load
            slot = window.data["A"][0][int(slot_index)]
            if slot.source_type == AUTOMATION_SOURCE_TYPE:
                return mw.MainWindow._trigger_automation_slot_non_audio(
                    window,
                    int(slot_index),
                    auto_release=True,
                    continue_playlist_after_automation=continue_playlist_after_automation,
                )
            started_audio.append(int(slot_index))
            return True

        window._play_slot = _fake_play_slot  # type: ignore[method-assign]

        window.current_playing = ("A", 0, 0)
        window._player_slot_key_map[id(window.player)] = ("A", 0, 0)
        transition0 = window._capture_track_end_transition_state()
        assert window._handle_track_end_transition(transition0) is True
        assert sent_calls == [("5/1/2", "press")]
        assert started_audio == [2]

        window.current_playing = ("A", 0, 2)
        window._player_slot_key_map[id(window.player)] = ("A", 0, 2)
        transition1 = window._capture_track_end_transition_state()
        assert window._handle_track_end_transition(transition1) is True
        assert sent_calls == [("5/1/2", "press"), ("6/1/2", "press")]
        assert started_audio == [2]
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_next_command_runs_automation_button_when_setting_enabled(qapp, monkeypatch):
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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.automation_command_buttons_follow_playback_controls = True
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        slot = window.data["A"][0][0]
        slot.source_type = AUTOMATION_SOURCE_TYPE
        slot.automation_spec = AutomationCommandSpec(location="5/1/2", button_text="Auto")
        slot.title = "Auto"
        window.current_group = "A"
        window.current_page = 0
        window.current_playing = ("B", 0, 10)

        sent_calls: list[tuple[str, str]] = []
        window._send_companion_location_command_async = (  # type: ignore[method-assign]
            lambda location, action: sent_calls.append((location, action)) or True
        )

        window._play_next()

        assert sent_calls == [("5/1/2", "press")]
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_next_button_enabled_for_utility_only_page_when_playlist_enabled(qapp, monkeypatch):
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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_playlist_enabled["A"][0] = True
        slot = window.data["A"][0][0]
        slot.source_type = "utility"
        slot.utility_spec = UtilitySoundSpec(mode="blank", duration_ms=1000)
        slot.title = "Utility only"

        window._update_next_button_enabled()

        next_btn = window.control_buttons.get("Next")
        assert next_btn is not None
        assert next_btn.isEnabled() is True
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_playlist_auto_advance_from_utility_to_normal(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "utility_to_normal.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw.MainWindow, "_clear_main_waveform_display", lambda self: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        page = window.data["A"][0]
        page[0].source_type = "utility"
        page[0].utility_spec = UtilitySoundSpec(mode="blank", duration_ms=1000)
        page[0].title = "Utility first"
        page[0].played = True
        page[0].activity_code = "2"
        page[1].file_path = str(audio_path)
        page[1].title = "Normal second"
        window.page_playlist_enabled["A"][0] = True
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        window.current_playing = ("A", 0, 0)
        window.current_playlist_start = 0
        window._player_slot_key_map[id(window.player)] = ("A", 0, 0)
        window._active_playing_keys.add(("A", 0, 0))

        started: list[int] = []

        def _fake_play_slot(slot_index, allow_fade=True):
            _ = allow_fade
            started.append(int(slot_index))
            return True

        window._play_slot = _fake_play_slot  # type: ignore[method-assign]
        window._on_state_changed(window.player.state())

        assert started == [1]
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
@pytest.mark.parametrize(
    ("controls_enabled", "expected_restarts"),
    [
        (True, 1),
        (False, 0),
    ],
)
def test_utility_sound_buttons_loop_respects_playback_control_setting(qapp, monkeypatch, controls_enabled, expected_restarts):
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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw.MainWindow, "_clear_main_waveform_display", lambda self: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.utility_sound_buttons_follow_playback_controls = bool(controls_enabled)
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        slot = window.data["A"][0][0]
        slot.source_type = "utility"
        slot.utility_spec = UtilitySoundSpec(mode="blank", duration_ms=1000)
        slot.title = "Looper"
        window.current_group = "A"
        window.current_page = 0
        window.cue_mode = False
        window.loop_enabled = True
        window.current_playing = ("A", 0, 0)
        window._player_slot_key_map[id(window.player)] = ("A", 0, 0)
        window._active_playing_keys.add(("A", 0, 0))

        restarted: list[int] = []

        def _fake_play_slot(slot_index, allow_fade=True):
            _ = allow_fade
            restarted.append(int(slot_index))
            return True

        window._play_slot = _fake_play_slot  # type: ignore[method-assign]
        window._on_state_changed(window.player.state())

        assert restarted == ([0] if expected_restarts else [])
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_playlist_auto_advance_uses_playing_page_not_visible_page(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "playlist_auto_advance.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw.MainWindow, "_clear_main_waveform_display", lambda self: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        playlist_page = window.data["A"][0]
        playlist_page[0].file_path = str(audio_path)
        playlist_page[0].title = "Track 1"
        playlist_page[0].played = True
        playlist_page[0].activity_code = "2"
        playlist_page[1].file_path = str(audio_path)
        playlist_page[1].title = "Track 2"
        window.page_playlist_enabled["A"][0] = True

        window.current_playing = ("A", 0, 0)
        window.current_playlist_start = 0
        window.current_group = "B"
        window.current_page = 0
        window.cue_mode = False
        window._manual_stop_requested = False
        window._player_slot_key_map[id(window.player)] = ("A", 0, 0)
        window._active_playing_keys.add(("A", 0, 0))

        started: list[tuple[str, int, int]] = []

        def _fake_play_slot(slot_index, allow_fade=True):
            _ = allow_fade
            started.append((window.current_group, window.current_page, int(slot_index)))
            return True

        window._play_slot = _fake_play_slot  # type: ignore[method-assign]

        window._on_state_changed(window.player.state())

        assert started == [("A", 0, 1)]
        assert window.current_group == "A"
        assert window.current_page == 0
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_drop_audio_files_on_sound_button_uses_add_sound_flow(qapp, monkeypatch, tmp_path):
    audio_a = tmp_path / "drop_a.wav"
    audio_b = tmp_path / "drop_b.wav"
    lyric_a = tmp_path / "drop_a.lrc"
    _write_dummy_wav(audio_a)
    _write_dummy_wav(audio_b)
    lyric_a.write_text("", encoding="utf-8")

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.search_lyric_on_add_sound_button = True
    settings.verify_sound_file_on_add = True
    settings.supported_audio_format_extensions = [".wav"]
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    calls = {"verify": 0, "lyric": 0}
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_names["A"][0] = "Drop Page"
        window.verify_sound_file_on_add = True
        window.search_lyric_on_add_sound_button = True
        window.allow_other_unsupported_audio_files = False
        window.supported_audio_format_extensions = [".wav"]

        def _verify(paths):
            calls["verify"] += 1
            assert [Path(path) for path in paths] == [audio_a, audio_b]
            return []

        def _prompt(paths):
            calls["lyric"] += 1
            assert [Path(path) for path in paths] == [audio_a, audio_b]
            return [str(lyric_a), ""]

        window._verify_audio_files_before_add = _verify  # type: ignore[method-assign]
        window._prompt_lyric_link_selection = _prompt  # type: ignore[method-assign]

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(audio_a)), QUrl.fromLocalFile(str(audio_b))])

        assert window._is_button_drag_enabled() is False
        assert window._can_accept_sound_file_drop(mime) is True
        assert window._handle_sound_button_drop(0, mime) is True

        first = window.data["A"][0][0]
        second = window.data["A"][0][1]
        assert Path(first.file_path) == audio_a
        assert Path(second.file_path) == audio_b
        assert Path(first.lyric_file) == lyric_a
        assert second.lyric_file == ""
        assert calls["verify"] == 1
        assert calls["lyric"] == 1
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_vocal_removed_indicator_uses_stripe_without_page_missing_track_warning(qapp, monkeypatch, tmp_path):
    audio_with_backtrack = tmp_path / "with_backtrack.wav"
    audio_without_backtrack = tmp_path / "without_backtrack.wav"
    backtrack_path = tmp_path / "with_backtrack_no_vocals.wav"
    _write_dummy_wav(audio_with_backtrack)
    _write_dummy_wav(audio_without_backtrack)
    _write_dummy_wav(backtrack_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        slot0 = window.data["A"][0][0]
        slot0.file_path = str(audio_with_backtrack)
        slot0.vocal_removed_file = str(backtrack_path)
        slot0.title = "Track With Backtrack"
        slot0.duration_ms = 2500

        slot1 = window.data["A"][0][1]
        slot1.file_path = str(audio_without_backtrack)
        slot1.title = "Track Without Backtrack"
        slot1.duration_ms = 1800

        window._refresh_sound_grid()

        assert "VR" not in window.sound_buttons[0].text()
        assert window.sound_buttons[0]._bottom_indicator_colors == [window.state_colors["vocal_removed_indicator"]]
        assert window.sound_buttons[1]._bottom_indicator_colors == []
        assert window.vocal_removed_warning_banner.isVisible() is False

        window._toggle_global_vocal_removed_mode(True)

        assert window.vocal_removed_warning_banner.isVisible() is False
        assert window.vocal_removed_warning_banner.text() == ""
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_sound_button_automation_uses_stripe_and_legend_entry(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "automation_stripe.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        slot = window.data["A"][0][0]
        slot.file_path = str(audio_path)
        slot.title = "Automation Track"
        slot.duration_ms = 1200
        slot.sound_button_automation = SoundButtonAutomationConfig(
            mode=SOUND_BUTTON_AUTOMATION_MODE_SIMPLE,
            on_become_playing=[AutomationCommandSpec(location="7/1/2", button_text="Start Macro")],
        )

        window._refresh_sound_grid()

        assert window.sound_buttons[0]._bottom_indicator_colors == [window.state_colors["automation_indicator"]]
        legend_labels = [
            child.text()
            for child in window.button_legend_label.findChildren(QLabel)
            if child.text()
        ]
        assert "Automation Stripe" in legend_labels
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_sound_button_text_wrap_and_status_legend(qapp, monkeypatch, tmp_path):
    audio_path = tmp_path / "very_long_demo_filename_for_wrapped_button_text.wav"
    _write_dummy_wav(audio_path)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.title_char_limit = 12
        slot = window.data["A"][0][0]
        slot.file_path = str(audio_path)
        slot.title = "very_long_demo_filename_for_wrapped_button_text"
        slot.duration_ms = 4321

        window._refresh_sound_grid()

        rendered = window.sound_buttons[0].text().splitlines()
        assert len(rendered) == 3
        assert rendered[-1].startswith("00:04")
        assert window.button_legend_label.isVisible() is True
        legend_labels = [
            child.text()
            for child in window.button_legend_label.findChildren(QLabel)
            if child.text()
        ]
        assert "Button Legend:" in legend_labels
        assert "Vocal Removed Stripe" in legend_labels
        assert "Automation Stripe" in legend_labels
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_colour_legend_toggle_action_updates_visibility_and_setting(qapp, monkeypatch):
    import pyssp.ui.main_window as mw

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.show_colour_legend = True
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        action = window._menu_actions["show_colour_legend"]
        assert action.isChecked() is True
        assert window.button_legend_label.isVisible() is True

        action.trigger()
        qapp.processEvents()

        assert window.show_colour_legend is False
        assert action.isChecked() is False
        assert window.button_legend_label.isVisible() is False
        assert window.settings.show_colour_legend is False

        action.trigger()
        qapp.processEvents()

        assert window.show_colour_legend is True
        assert action.isChecked() is True
        assert window.button_legend_label.isVisible() is True
        assert window.settings.show_colour_legend is True
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_pick_sound_skip_lyric_scan_keeps_add_and_uses_partial_results(qapp, monkeypatch, tmp_path):
    audio_a = tmp_path / "a.wav"
    audio_b = tmp_path / "b.wav"
    lyric_a = tmp_path / "a.lrc"
    _write_dummy_wav(audio_a)
    _write_dummy_wav(audio_b)
    lyric_a.write_text("[00:01.00]line\n", encoding="utf-8")

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

    class _DummyLinkLyricDialog:
        def __init__(self, rows, parent=None):
            self._rows = rows

        def exec_(self):
            return mw.QDialog.Accepted

        def link_flags(self):
            return [True for _ in self._rows]

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())
    monkeypatch.setattr(
        mw.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: ([str(audio_a), str(audio_b)], ""),
    )
    monkeypatch.setattr(mw, "LinkLyricDialog", _DummyLinkLyricDialog)

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.search_lyric_on_add_sound_button = True
    settings.verify_sound_file_on_add = False
    settings.supported_audio_format_extensions = [".wav"]
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    notices: list[str] = []
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_names["A"][0] = "Skip Scan Partial"
        window.verify_sound_file_on_add = False
        window.search_lyric_on_add_sound_button = True
        window._show_info_notice_banner = lambda text: notices.append(str(text))  # type: ignore[method-assign]
        window._scan_lyric_candidates_with_progress = (  # type: ignore[method-assign]
            lambda files, **kwargs: ([str(lyric_a)], True)
        )

        window._pick_sound(0)

        first = window.data["A"][0][0]
        second = window.data["A"][0][1]
        assert first.assigned is True
        assert second.assigned is True
        assert first.file_path == str(audio_a)
        assert second.file_path == str(audio_b)
        assert first.lyric_file == str(lyric_a)
        assert second.lyric_file == ""
        assert any("partial scan results" in msg.lower() for msg in notices)
    finally:
        _cleanup_main_window(window, qapp)


@pytest.mark.monkey
def test_preload_queue_respects_path_safety_toggle(qapp, monkeypatch, tmp_path):
    safe_audio = tmp_path / "safe.wav"
    unsafe_audio = tmp_path / "unsafe;name.wav"
    _write_dummy_wav(safe_audio)
    _write_dummy_wav(unsafe_audio)

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

    monkeypatch.setattr(mw, "LtcAudioOutput", _DummyLtcSender)
    monkeypatch.setattr(mw, "MtcMidiOutput", _DummyMtcSender)
    monkeypatch.setattr(mw.MainWindow, "_init_audio_players", mw.MainWindow._init_silent_audio_players)
    monkeypatch.setattr(mw.MainWindow, "_apply_web_remote_state", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_restore_last_set_on_startup", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_poll_midi_inputs", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_timecode_mtc", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_meter", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_fades", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_preload_status_icon", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_tick_talk_blink", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_open_tips_window", lambda self, startup=False: None)
    monkeypatch.setattr(mw, "set_output_device", lambda _name: True)
    monkeypatch.setattr(mw, "configure_audio_preload_cache_policy", lambda *args, **kwargs: None)
    monkeypatch.setattr(mw, "configure_waveform_disk_cache", lambda *args, **kwargs: "")
    monkeypatch.setattr(mw, "shutdown_audio_preload", lambda: None)
    monkeypatch.setattr(mw, "save_settings", lambda _settings: None)
    monkeypatch.setattr(mw.MainWindow, "_hard_stop_all", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "_stop_web_remote_service", lambda self: None)
    monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())
    monkeypatch.setattr(mw, "is_audio_preloaded", lambda _path: False)
    monkeypatch.setattr(mw, "get_audio_preload_capacity_bytes", lambda: (10**9, 10**9, 0))

    captured: list[list[str]] = []
    monkeypatch.setattr(mw, "request_audio_preload", lambda paths, prioritize=True: captured.append(list(paths)))

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    monkeypatch.setattr(mw, "load_settings", lambda s=settings: s)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()
    try:
        window._reset_set_data()
        window.current_group = "A"
        window.current_page = 0
        window.page_names["A"][0] = "Preload Path Safety"
        window.preload_audio_enabled = True
        window.preload_current_page_audio = True

        s0 = window.data["A"][0][0]
        s0.file_path = str(safe_audio)
        s0.title = "Safe"
        s1 = window.data["A"][0][1]
        s1.file_path = str(unsafe_audio)
        s1.title = "Unsafe"

        window.disable_path_safety = False
        window._queue_current_page_audio_preload()
        assert captured
        assert str(safe_audio) in captured[-1]
        assert str(unsafe_audio) not in captured[-1]

        window.disable_path_safety = True
        window._queue_current_page_audio_preload()
        assert str(unsafe_audio) in captured[-1]
    finally:
        _cleanup_main_window(window, qapp)
