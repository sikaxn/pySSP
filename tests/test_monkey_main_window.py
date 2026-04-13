from __future__ import annotations

import os
import random
import wave
from itertools import combinations
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.settings_store import AppSettings
from pyssp.ui import main_window as mw


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
        window.hide()
        window.deleteLater()
        qapp.processEvents()


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
        window.hide()
        window.deleteLater()
        qapp.processEvents()


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
        window.hide()
        window.deleteLater()
        qapp.processEvents()


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
        window.hide()
        window.deleteLater()
        qapp.processEvents()
