import os
import random
import sys
from itertools import combinations
from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_options_dialog_ui import _build_dialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _pick_existing_page(rng: random.Random):
    # These are end-user visible pages in Options used by existing tests.
    candidates = ["General", "Playback", "Web Remote", "Lock Screen", "Display", "Window Layout", "Hotkeys"]
    rng.shuffle(candidates)
    return candidates[0]


def _action_switch_page(dialog, rng: random.Random) -> None:
    page = _pick_existing_page(rng)
    try:
        dialog.select_page(page)
    except Exception:
        # Some builds/localizations may rename pages; this action is best-effort.
        pass


def _action_web_remote(dialog, rng: random.Random) -> None:
    if hasattr(dialog, "web_remote_enabled_checkbox"):
        dialog.web_remote_enabled_checkbox.setChecked(rng.choice([True, False]))
    if hasattr(dialog, "web_remote_port_spin"):
        dialog.web_remote_port_spin.setValue(rng.randint(1024, 65000))


def _action_playback(dialog, rng: random.Random) -> None:
    if hasattr(dialog, "cue_timeline_audio_file_radio"):
        dialog.cue_timeline_audio_file_radio.setChecked(rng.choice([True, False]))
    if hasattr(dialog, "jog_outside_next_cue_or_stop_radio"):
        dialog.jog_outside_next_cue_or_stop_radio.setChecked(True)
    if hasattr(dialog, "candidate_error_keep_radio"):
        dialog.candidate_error_keep_radio.setChecked(rng.choice([True, False]))
    if hasattr(dialog, "_sync_jog_outside_group_enabled"):
        dialog._sync_jog_outside_group_enabled()


def _action_lock_screen(dialog, rng: random.Random) -> None:
    for key in [
        "lock_allow_quit_checkbox",
        "lock_allow_system_hotkeys_checkbox",
        "lock_allow_quick_action_hotkeys_checkbox",
        "lock_allow_sound_button_hotkeys_checkbox",
        "lock_allow_midi_control_checkbox",
    ]:
        checkbox = getattr(dialog, key, None)
        if checkbox is not None:
            checkbox.setChecked(rng.choice([True, False]))
    if hasattr(dialog, "lock_password_edit") and hasattr(dialog, "lock_password_verify_edit"):
        if rng.choice([True, False]):
            dialog.lock_password_edit.setText("secret123")
            dialog.lock_password_verify_edit.setText("secret123")
        else:
            dialog.lock_password_edit.clear()
            dialog.lock_password_verify_edit.clear()


def _action_hotkeys(dialog, rng: random.Random) -> None:
    hotkey_edits = getattr(dialog, "_hotkey_edits", {})
    if "new_set" in hotkey_edits and "open_set" in hotkey_edits:
        # Simulate both conflict and recovery like real user corrections.
        if rng.choice([True, False]):
            hotkey_edits["new_set"][0].setText("Ctrl+N")
            hotkey_edits["open_set"][0].setText("Ctrl+N")
        else:
            hotkey_edits["new_set"][0].setText("Ctrl+N")
            hotkey_edits["open_set"][0].setText("Ctrl+O")
        if hasattr(dialog, "_validate_hotkey_conflicts"):
            dialog._validate_hotkey_conflicts()


def _action_window_layout(dialog, rng: random.Random) -> None:
    if not hasattr(dialog, "_handle_window_layout_drop"):
        return
    if not hasattr(dialog, "window_layout_main_editor"):
        return
    src = dialog.window_layout_main_editor
    items = src.export_items()
    if not items:
        return
    payload = items[rng.randrange(len(items))].copy()
    payload["source_zone"] = "main"
    import json

    dialog._handle_window_layout_drop("fade", json.dumps(payload), rng.randint(10, 80), rng.randint(10, 80))


def _pair_keys(case: dict[str, object], names: list[str]) -> set[tuple[str, object, str, object]]:
    pairs: set[tuple[str, object, str, object]] = set()
    for i, j in combinations(range(len(names)), 2):
        a = names[i]
        b = names[j]
        pairs.add((a, case[a], b, case[b]))
    return pairs


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
        for _ in range(220):
            candidate = {name: rng.choice(values[name]) for name in names}
            cover = _pair_keys(candidate, names) & uncovered
            if len(cover) > len(best_cover):
                best_case = candidate
                best_cover = cover
                if len(best_cover) >= len(uncovered):
                    break
        if best_case is None:
            break
        cases.append(best_case)
        uncovered -= best_cover
    return cases


def _apply_settings_combo(dialog, combo: dict[str, object]) -> None:
    if combo["main_transport_timeline_mode"] == "audio_file":
        dialog.cue_timeline_audio_file_radio.setChecked(True)
    else:
        dialog.cue_timeline_cue_region_radio.setChecked(True)

    jog_value = str(combo["main_jog_outside_cue_action"])
    if jog_value == "ignore_cue":
        dialog.jog_outside_ignore_cue_radio.setChecked(True)
    elif jog_value == "next_cue_or_stop":
        dialog.jog_outside_next_cue_or_stop_radio.setChecked(True)
    elif jog_value == "stop_cue_or_end":
        dialog.jog_outside_stop_cue_or_end_radio.setChecked(True)
    else:
        dialog.jog_outside_stop_immediately_radio.setChecked(True)

    (dialog.candidate_error_keep_radio if combo["candidate_error_action"] == "keep_playing" else dialog.candidate_error_stop_radio).setChecked(True)
    (dialog.playlist_mode_any_radio if combo["playlist_play_mode"] == "any_available" else dialog.playlist_mode_unplayed_radio).setChecked(True)
    (dialog.rapid_fire_mode_any_radio if combo["rapid_fire_play_mode"] == "any_available" else dialog.rapid_fire_mode_unplayed_radio).setChecked(True)
    (dialog.next_mode_any_radio if combo["next_play_mode"] == "any_available" else dialog.next_mode_unplayed_radio).setChecked(True)
    (dialog.playlist_loop_single_radio if combo["playlist_loop_mode"] == "loop_single" else dialog.playlist_loop_list_radio).setChecked(True)
    (dialog.multi_play_stop_oldest_radio if combo["multi_play_limit_action"] == "stop_oldest" else dialog.multi_play_disallow_radio).setChecked(True)
    (dialog.playing_click_stop_radio if combo["click_playing_action"] == "stop_it" else dialog.playing_click_play_again_radio).setChecked(True)
    (dialog.search_dbl_play_radio if combo["search_double_click_action"] == "play_highlight" else dialog.search_dbl_find_radio).setChecked(True)
    (dialog.main_progress_display_waveform_radio if combo["main_progress_display_mode"] == "waveform" else dialog.main_progress_display_progress_bar_radio).setChecked(True)
    dialog.main_progress_show_text_checkbox.setChecked(bool(combo["main_progress_show_text"]))

    lock_method = str(combo["lock_unlock_method"])
    if lock_method == "click_one_button":
        dialog.lock_method_fixed_button_radio.setChecked(True)
    elif lock_method == "slide_to_unlock":
        dialog.lock_method_slide_radio.setChecked(True)
    else:
        dialog.lock_method_random_points_radio.setChecked(True)
    dialog.lock_require_password_checkbox.setChecked(bool(combo["lock_require_password"]))
    if bool(combo["lock_require_password"]):
        dialog.lock_password_edit.setText("secret123")
        dialog.lock_password_verify_edit.setText("secret123")
    else:
        dialog.lock_password_edit.clear()
        dialog.lock_password_verify_edit.clear()
    (dialog.lock_restart_lock_radio if combo["lock_restart_state"] == "lock_on_restart" else dialog.lock_restart_unlock_radio).setChecked(True)

    dialog.web_remote_enabled_checkbox.setChecked(bool(combo["web_remote_enabled"]))
    if hasattr(dialog, "_sync_jog_outside_group_enabled"):
        dialog._sync_jog_outside_group_enabled()


@pytest.mark.monkey
@pytest.mark.parametrize("seed", [11, 37, 101])
def test_monkey_options_dialog_seeded(qapp, seed):
    rng = random.Random(seed)
    dialog = _build_dialog(initial_page="General")
    if hasattr(dialog, "_confirm_layout_overlap_action"):
        dialog._confirm_layout_overlap_action = lambda: "replace"
    dialog.show()
    qapp.processEvents()

    actions = [
        _action_switch_page,
        _action_web_remote,
        _action_playback,
        _action_lock_screen,
        _action_hotkeys,
        _action_window_layout,
    ]

    for _ in range(220):
        action = rng.choice(actions)
        action(dialog, rng)

        qapp.processEvents()
        assert dialog.isVisible()
        if hasattr(dialog, "ok_button"):
            assert dialog.ok_button is not None

    # Pull selected values at end to ensure user-visible state readers stay valid.
    assert dialog.selected_main_transport_timeline_mode() in {"cue_region", "audio_file"}
    assert dialog.selected_playlist_play_mode() in {"unplayed_only", "any_available"}
    assert dialog.selected_lock_unlock_method() in {"click_3_random_points", "click_one_button", "slide_to_unlock"}

    dialog.close()
    qapp.processEvents()


@pytest.mark.monkey
def test_monkey_options_dialog_pairwise_setting_combos(qapp):
    dimensions: dict[str, list[object]] = {
        "main_transport_timeline_mode": ["cue_region", "audio_file"],
        "main_jog_outside_cue_action": ["stop_immediately", "ignore_cue", "next_cue_or_stop", "stop_cue_or_end"],
        "candidate_error_action": ["stop_playback", "keep_playing"],
        "playlist_play_mode": ["unplayed_only", "any_available"],
        "rapid_fire_play_mode": ["unplayed_only", "any_available"],
        "next_play_mode": ["unplayed_only", "any_available"],
        "playlist_loop_mode": ["loop_list", "loop_single"],
        "multi_play_limit_action": ["disallow_more_play", "stop_oldest"],
        "click_playing_action": ["play_it_again", "stop_it"],
        "search_double_click_action": ["find_highlight", "play_highlight"],
        "main_progress_display_mode": ["progress_bar", "waveform"],
        "main_progress_show_text": [True, False],
        "lock_unlock_method": ["click_3_random_points", "click_one_button", "slide_to_unlock"],
        "lock_require_password": [False, True],
        "lock_restart_state": ["unlock_on_restart", "lock_on_restart"],
        "web_remote_enabled": [False, True],
    }
    cases = _build_pairwise_cases(dimensions)
    assert len(cases) >= 10

    for combo in cases:
        dialog = _build_dialog(initial_page="General")
        if hasattr(dialog, "_confirm_layout_overlap_action"):
            dialog._confirm_layout_overlap_action = lambda: "replace"
        dialog.show()
        qapp.processEvents()
        _apply_settings_combo(dialog, combo)
        qapp.processEvents()

        assert dialog.selected_main_transport_timeline_mode() == combo["main_transport_timeline_mode"]
        if combo["main_transport_timeline_mode"] == "audio_file":
            assert dialog.selected_main_jog_outside_cue_action() == combo["main_jog_outside_cue_action"]
        assert dialog.selected_candidate_error_action() == combo["candidate_error_action"]
        assert dialog.selected_playlist_play_mode() == combo["playlist_play_mode"]
        assert dialog.selected_rapid_fire_play_mode() == combo["rapid_fire_play_mode"]
        assert dialog.selected_next_play_mode() == combo["next_play_mode"]
        assert dialog.selected_playlist_loop_mode() == combo["playlist_loop_mode"]
        assert dialog.selected_multi_play_limit_action() == combo["multi_play_limit_action"]
        assert dialog.selected_click_playing_action() == combo["click_playing_action"]
        assert dialog.selected_search_double_click_action() == combo["search_double_click_action"]
        assert dialog.selected_main_progress_display_mode() == combo["main_progress_display_mode"]
        assert dialog.selected_main_progress_show_text() is combo["main_progress_show_text"]
        assert dialog.selected_lock_unlock_method() == combo["lock_unlock_method"]
        assert dialog.selected_lock_require_password() is combo["lock_require_password"]
        assert dialog.selected_lock_restart_state() == combo["lock_restart_state"]
        assert dialog.web_remote_enabled_checkbox.isChecked() is combo["web_remote_enabled"]
        if combo["lock_require_password"]:
            assert dialog.selected_lock_password() == "secret123"

        dialog.close()
        qapp.processEvents()
