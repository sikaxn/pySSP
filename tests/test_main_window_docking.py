from __future__ import annotations

import copy
import gc
import os

import pytest
from PyQt5.QtCore import QEvent, QPoint, Qt
from PyQt5.QtGui import QContextMenuEvent, QMouseEvent
from PyQt5.QtWidgets import QApplication, QDockWidget

from pyssp.audio_beat_map import AudioBeatMap
from pyssp.settings_store import AppSettings
from pyssp.ui import main_window as mw


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _cleanup_main_window(window, qapp: QApplication) -> None:
    try:
        window._suspend_settings_save = True
        window._dock_layout_save_pending = False
    except Exception:
        pass
    shutdown_runtime_threads = getattr(window, "_shutdown_runtime_threads", None)
    if callable(shutdown_runtime_threads):
        try:
            shutdown_runtime_threads()
        except Exception:
            pass
    stop_companion_client = getattr(window, "_stop_companion_satellite_client", None)
    if callable(stop_companion_client):
        try:
            stop_companion_client()
        except Exception:
            pass
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
    QApplication.sendPostedEvents(None, 0)
    for widget in list(qapp.topLevelWidgets()):
        try:
            if widget is window:
                continue
            widget.close()
        except Exception:
            try:
                widget.hide()
            except Exception:
                pass
    for _ in range(3):
        qapp.processEvents()
        QApplication.sendPostedEvents(None, 0)
    gc.collect()


def _patch_main_window_startup(monkeypatch, *, patch_close_event: bool = True) -> None:
    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False

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
    monkeypatch.setattr(mw, "load_settings", lambda: settings)
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
    if patch_close_event:
        monkeypatch.setattr(mw.MainWindow, "closeEvent", lambda self, event: event.accept())


def _window_menu(window):
    return next(
        action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Window"
    )


def _navigation_menu(window):
    return next(
        action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Navigation"
    )


def _submenu(menu, title: str):
    return next(action.menu() for action in menu.actions() if action.text().replace("&", "") == title)


def test_main_window_exposes_dockable_ui_panels(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        assert window.notice_dock is None
        assert window.group_dock is not None
        assert window.page_dock is not None
        assert window.sound_buttons_dock is not None
        assert window.status_display_dock is not None
        assert window.main_button_dock is not None
        assert window.fade_button_dock is not None
        assert window.meter_volume_dock is not None
        assert window.time_transport_dock is not None
        assert window.lyric_navigator_dock is not None
        assert window.automation_script_navigator_dock is not None
        assert window.available_commands_dock is not None
        assert window.video_control_dock is not None
        assert window.video_preview_widget is not None
        assert window.video_control_dock.widget().isAncestorOf(window.video_preview_widget)
        assert window.centralWidget() is window._dock_canvas
        assert window.sound_buttons_dock.widget().isAncestorOf(window.button_legend_label)
        assert window.status_display_dock.widget().isAncestorOf(window.info_notice_banner)
        assert window.status_display_dock.widget().isAncestorOf(window.drag_mode_banner)

        for dock in [
            window.group_dock,
            window.page_dock,
            window.sound_buttons_dock,
            window.status_display_dock,
            window.main_button_dock,
            window.fade_button_dock,
            window.meter_volume_dock,
            window.time_transport_dock,
        ]:
            assert dock.features() & QDockWidget.DockWidgetFloatable
            assert dock.features() & QDockWidget.DockWidgetMovable
            assert dock.features() & QDockWidget.DockWidgetClosable

        for dock in [
            window.lyric_navigator_dock,
            window.automation_script_navigator_dock,
            window.available_commands_dock,
            window.video_control_dock,
        ]:
            assert dock.features() & QDockWidget.DockWidgetFloatable
            assert dock.features() & QDockWidget.DockWidgetClosable

        window_menu = _window_menu(window)
        menu_items = {action.text().replace("&", "") for action in window_menu.actions()}
        display_menu = next(
            action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Display"
        )
        display_items = {action.text().replace("&", "") for action in display_menu.actions()}
        logs_menu = next(
            action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Logs"
        )
        logs_items = {action.text().replace("&", "") for action in logs_menu.actions()}
        navigation_menu = _navigation_menu(window)
        navigation_items = {action.text().replace("&", "") for action in navigation_menu.actions()}
        top_level_menus = [action.text().replace("&", "") for action in window.menuBar().actions()]
        assert top_level_menus == [
            "File",
            "Setup",
            "Display",
            "Navigation",
            "Timecode",
            "Tools",
            "Automation",
            "Logs",
            "Window",
            "Help",
        ]
        assert "Restore Default Layout" in menu_items
        assert "Sound Buttons Grid View" in menu_items
        assert "Sound Buttons List View" in menu_items
        assert "Remove Blank Space" in menu_items
        assert "Add Horizontal Divider" in menu_items
        assert "Add Vertical Divider" in menu_items
        assert "Clear All Standalone Mode" in menu_items
        assert "Open Video Display" in display_items
        assert "Video Display Setting" in display_items
        assert "View Log" in logs_items
        assert "Open Runtime Log Folder" in logs_items
        assert "Previous Group" in navigation_items
        assert "Next Group" in navigation_items
        assert "Previous Page" in navigation_items
        assert "Next Page" in navigation_items
        assert "Home Page" in navigation_items
        assert "Groups" in navigation_items
        assert "Pages" in navigation_items
        assert "Group" in menu_items
        assert "Pages" in menu_items
        assert "Sound Buttons" in menu_items
        assert "Status Display" in menu_items
        assert "Main Buttons" in menu_items
        assert "Fade Buttons" in menu_items
        assert "VU Meter and Volume" in menu_items
        assert "Time and Transport" in menu_items
        assert "Lyric Navigator" in menu_items
        assert "Automation Script Navigator" in menu_items
        assert "Available Commands" in menu_items
        assert any(action.text().replace("&", "") == "Lock Window Layout" for action in window_menu.actions())
        assert not window._dock_canvas.isVisible()
        assert window.centralWidget() is window._dock_canvas
        assert not any(action.menu() is not None for action in window_menu.actions() if action.text().replace("&", "") == "Group")
        assert window.main_button_dock.y() <= window.status_display_dock.y()
        assert window.main_button_dock.y() <= window.sound_buttons_dock.y()
        assert window.sound_buttons_dock.y() >= window.status_display_dock.y()
        assert window.page_dock.height() > window.group_dock.height()
        assert window.sound_buttons_dock.height() > window.main_button_dock.height()

        window._select_group("C")
        window._select_page(2)
        qapp.processEvents()
        assert [action.text().replace("&", "") for action in window.menuBar().actions()] == top_level_menus

        before_dividers = len(window.dock_dividers)
        window._create_global_divider(Qt.Vertical)
        assert len(window.dock_dividers) == before_dividers + 1

        grid_action = next(
            action for action in window_menu.actions() if action.text().replace("&", "") == "Sound Buttons Grid View"
        )
        list_action = next(
            action for action in window_menu.actions() if action.text().replace("&", "") == "Sound Buttons List View"
        )
        assert grid_action.isChecked() is True
        assert list_action.isChecked() is False
        list_action.trigger()
        qapp.processEvents()
        assert window.sound_button_view_mode == "list"
        assert list_action.isChecked() is True
        assert grid_action.isChecked() is False
        grid_action.trigger()
        qapp.processEvents()
        assert window.sound_button_view_mode == "grid"

        window.fade_button_dock.setFloating(True)
        qapp.processEvents()
        assert "fade_button_widget_dock" in window.standalone_docks
        assert window.fade_button_dock.allowedAreas() == Qt.NoDockWidgetArea
        assert window.fade_button_dock.features() & QDockWidget.DockWidgetFloatable
        assert not (window.fade_button_dock.features() & QDockWidget.DockWidgetMovable)
        window._clear_all_standalone_modes()
        assert not window.standalone_docks
        assert window.fade_button_dock.allowedAreas() == Qt.AllDockWidgetAreas
        assert window.fade_button_dock.features() & QDockWidget.DockWidgetMovable

        window._toggle_window_layout_lock(True)
        assert window._dock_canvas.contextMenuPolicy() == Qt.NoContextMenu
        assert not window._remove_blank_space_action.isEnabled()
        assert not window._add_horizontal_divider_action.isEnabled()
        assert not window._add_vertical_divider_action.isEnabled()
        assert not window._clear_all_standalone_action.isEnabled()
        separator_x = (window.group_dock.geometry().right() + window.main_button_dock.geometry().left()) // 2
        separator_y = window.group_dock.geometry().center().y()
        separator_event = QMouseEvent(
            QEvent.MouseButtonPress,
            QPoint(separator_x, separator_y),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        assert window.eventFilter(window, separator_event) is True
        for dock in [
            window.group_dock,
            window.page_dock,
            window.sound_buttons_dock,
            window.status_display_dock,
        ]:
            assert dock.features() == QDockWidget.NoDockWidgetFeatures
        locked_dividers = len(window.dock_dividers)
        window._create_global_divider(Qt.Horizontal)
        assert len(window.dock_dividers) == locked_dividers
    finally:
        _cleanup_main_window(window, qapp)


def test_video_control_uses_follow_checkbox_and_shared_route_combo(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        assert window.video_follow_sound_button_focus_checkbox is not None
        assert window.video_route_combo is not None
        assert window.video_follow_sound_button_focus_checkbox.isChecked() is True
        assert window.video_route_combo.currentData() == "blank"

        window.video_follow_sound_button_focus_checkbox.setChecked(False)
        route_index = window.video_route_combo.findData("stage_display")
        window.video_route_combo.setCurrentIndex(route_index)
        qapp.processEvents()

        assert window.video_display_mode_playing == "stage_display"
        assert window.video_display_mode_idle == "stage_display"

        window.video_follow_sound_button_focus_checkbox.setChecked(True)
        route_index = window.video_route_combo.findData("backdrop")
        window.video_route_combo.setCurrentIndex(route_index)
        qapp.processEvents()

        assert window.video_display_mode_playing == "follow_sound_button"
        assert window.video_display_mode_idle == "backdrop"
    finally:
        _cleanup_main_window(window, qapp)


def test_navigation_menu_controls_groups_and_pages(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        navigation_menu = _navigation_menu(window)
        groups_menu = _submenu(navigation_menu, "Groups")
        pages_menu = _submenu(navigation_menu, "Pages")

        group_h_action = next(action for action in groups_menu.actions() if action.text().replace("&", "") == "H")
        group_h_action.trigger()
        qapp.processEvents()
        assert window.current_group == "H"
        assert window.current_page == 0

        page_five_action = next(action for action in pages_menu.actions() if action.text().startswith("5. "))
        page_five_action.trigger()
        qapp.processEvents()
        assert window.current_group == "H"
        assert window.current_page == 4
        assert page_five_action.isChecked()

        home_action = next(action for action in navigation_menu.actions() if action.text().replace("&", "") == "Home Page")
        home_action.trigger()
        qapp.processEvents()
        assert window.current_page == 0

        next_group_action = next(
            action for action in navigation_menu.actions() if action.text().replace("&", "") == "Next Group"
        )
        next_group_action.trigger()
        qapp.processEvents()
        assert window.current_group == "I"

        first_page_label = pages_menu.actions()[0].text()
        assert first_page_label.startswith("1. I1")
    finally:
        _cleanup_main_window(window, qapp)


def test_restore_default_layout_is_stable_after_scrambling(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        window.fade_button_dock.setFloating(True)
        window.time_transport_dock.setFloating(True)
        window._create_global_divider(Qt.Vertical)
        qapp.processEvents()

        def snapshot():
            names = [
                "group_dock",
                "page_dock",
                "main_button_dock",
                "status_display_dock",
                "fade_button_dock",
                "meter_volume_dock",
                "time_transport_dock",
                "sound_buttons_dock",
            ]
            return {name: getattr(window, name).geometry().getRect() for name in names}

        window._restore_default_dock_layout()
        qapp.processEvents()
        first = snapshot()

        window._restore_default_dock_layout()
        qapp.processEvents()
        second = snapshot()

        assert first == second
    finally:
        _cleanup_main_window(window, qapp)


def test_restore_default_layout_clears_standalone_core_docks(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        window.fade_button_dock.setFloating(True)
        qapp.processEvents()
        assert "fade_button_widget_dock" in window.standalone_docks

        window._restore_default_dock_layout()
        qapp.processEvents()

        assert "fade_button_widget_dock" not in window.standalone_docks
        assert not window.fade_button_dock.isFloating()
        assert window.fade_button_dock.allowedAreas() == Qt.AllDockWidgetAreas
        assert window.fade_button_dock.features() & QDockWidget.DockWidgetMovable
    finally:
        _cleanup_main_window(window, qapp)


def test_remove_blank_space_refreshes_live_layout_state(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        window._dock_canvas.show()
        window.dock_layout_state = ""
        divider_names_before = list(window.dock_dividers)
        window.fade_button_dock.setFloating(True)
        window._remove_blank_dock_space()
        qapp.processEvents()

        assert window.dock_layout_state
        assert not window._dock_canvas.isVisible()
        assert not window.group_dock.isFloating()
        assert not window.main_button_dock.isFloating()
        assert window.fade_button_dock.isFloating()
        assert window.dock_dividers == divider_names_before

        first_layout_state = window.dock_layout_state
        window._remove_blank_dock_space()
        qapp.processEvents()
        assert window.dock_layout_state == first_layout_state
    finally:
        _cleanup_main_window(window, qapp)


def test_close_saves_current_dock_layout_before_shutdown(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch, patch_close_event=False)
    saved_settings: list[AppSettings] = []

    def _capture_save(settings: AppSettings) -> None:
        saved_settings.append(copy.deepcopy(settings))

    monkeypatch.setattr(mw, "save_settings", _capture_save)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        window._create_global_divider(Qt.Vertical)
        window.fade_button_dock.setFloating(True)
        expected_layout_state = window._capture_dock_layout_state()
        expected_dividers = list(window.dock_dividers)

        window.close()
        qapp.processEvents()

        assert saved_settings
        latest = saved_settings[-1]
        assert latest.dock_layout_state == expected_layout_state
        assert latest.dock_dividers == expected_dividers
    finally:
        _cleanup_main_window(window, qapp)


def test_global_divider_actions_shift_workspace(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.resize(1280, 720)
    window.show()
    qapp.processEvents()

    try:
        before_count = len(window.dock_dividers)
        before_sound_bottom = window.sound_buttons_dock.geometry().bottom()
        before_group_left = window.group_dock.geometry().left()

        window._create_global_divider(Qt.Vertical)
        qapp.processEvents()
        assert len(window.dock_dividers) == before_count + 1
        row_divider = window._divider_docks[window.dock_dividers[-1]]
        assert not row_divider.isFloating()
        assert row_divider.geometry().height() < window.height()
        assert window.sound_buttons_dock.geometry().bottom() < before_sound_bottom

        window._restore_default_dock_layout()
        qapp.processEvents()
        before_sound_right = window.sound_buttons_dock.geometry().right()
        window._create_global_divider(Qt.Horizontal)
        qapp.processEvents()
        assert len(window.dock_dividers) == 1
        right_divider = window._divider_docks[window.dock_dividers[-1]]
        assert not right_divider.isFloating()
        assert right_divider.geometry().width() < window.width()
        assert right_divider.geometry().left() >= window.group_dock.geometry().right()
        assert window.sound_buttons_dock.geometry().right() < before_sound_right
    finally:
        _cleanup_main_window(window, qapp)


def test_invalid_saved_layout_falls_back_to_hidden_canvas_default(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)

    settings = AppSettings()
    settings.tips_open_on_startup = False
    settings.reset_all_on_startup = False
    settings.last_group = "A"
    settings.last_page = 0
    settings.web_remote_enabled = False
    settings.dock_layout_state = "not-valid-base64"
    monkeypatch.setattr(mw, "load_settings", lambda: settings)

    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        assert not window._dock_canvas.isVisible()
        assert not window.group_dock.isFloating()
        assert not window.main_button_dock.isFloating()
    finally:
        _cleanup_main_window(window, qapp)


def test_sound_buttons_reflow_on_resize_without_horizontal_scroll(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        window.resize(640, 700)
        qapp.processEvents()

        grid_viewport_width = window.sound_button_grid_scroll.viewport().width()
        assert window.sound_button_grid_widget.width() <= grid_viewport_width

        window._set_sound_button_view_mode("list", persist=False)
        qapp.processEvents()

        list_viewport_width = window.sound_button_list_scroll.viewport().width()
        assert window.sound_button_list_widget.width() <= list_viewport_width
    finally:
        _cleanup_main_window(window, qapp)


def test_sound_button_grid_uses_multiple_columns_on_startup(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.resize(1200, 760)
    window.show()
    for _ in range(8):
        qapp.processEvents()

    try:
        grid_layout = window.sound_button_grid_layout
        assert grid_layout is not None
        rendered_columns = max(
            (
                int(grid_layout.getItemPosition(index)[1]) + int(grid_layout.getItemPosition(index)[3])
                for index in range(grid_layout.count())
            ),
            default=0,
        )
        assert rendered_columns > 1
    finally:
        _cleanup_main_window(window, qapp)


def test_build_set_file_lines_persists_disable_video_loading_flag(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        slot = window.data["A"][0][0]
        slot.file_path = r"C:\Media\clip.mp4"
        slot.disable_video_loading = True
        slot.title = "Clip"
        slot.notes = "Clip"
        slot.duration_ms = 1000
        slot.activity_code = "8"

        lines = window._build_set_file_lines()

        assert "pysspdisablevideo1=1" in lines
    finally:
        _cleanup_main_window(window, qapp)


def test_build_set_file_lines_persists_display_focus_fields(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        slot = window.data["A"][0][0]
        slot.file_path = r"C:\Media\theme.mp3"
        slot.title = "Theme"
        slot.notes = "Theme"
        slot.duration_ms = 1000
        slot.activity_code = "8"
        slot.display_focus = "image"
        slot.display_image_path = r"C:\Media\theme.png"

        lines = window._build_set_file_lines()

        assert "pysspdisplayfocus1=image" in lines
        assert "pysspdisplayimage1=C:\\Media\\theme.png" in lines
    finally:
        _cleanup_main_window(window, qapp)


def test_build_set_file_lines_persists_audio_beat_map(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        slot = window.data["A"][0][0]
        slot.file_path = r"C:\Media\theme.mp3"
        slot.title = "Theme"
        slot.notes = "Theme"
        slot.duration_ms = 1000
        slot.activity_code = "8"
        slot.audio_beat_map = AudioBeatMap(
            bpm=128.5,
            time_signature_num=3,
            time_signature_den=4,
            first_downbeat_ms=250,
            beat_times_ms=[250, 719],
            beat_numbers=[1, 2],
            source="librosa",
            confidence=0.75,
        )

        lines = window._build_set_file_lines()

        assert any(line.startswith("pysspbeatmap1=") for line in lines)
    finally:
        _cleanup_main_window(window, qapp)


def test_tools_clear_display_focus_clears_assigned_button_overrides(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        tools_menu = next(
            action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Tools"
        )
        tool_items = {action.text().replace("&", "") for action in tools_menu.actions()}
        assert "Clear Display Focus" in tool_items

        main_slot = window.data["A"][0][0]
        main_slot.file_path = r"C:\Media\theme.mp3"
        main_slot.title = "Theme"
        main_slot.duration_ms = 1000
        main_slot.activity_code = "8"
        main_slot.display_focus = "image"

        cue_slot = window.cue_page[0]
        cue_slot.file_path = r"C:\Media\cue.mp3"
        cue_slot.title = "Cue"
        cue_slot.duration_ms = 1000
        cue_slot.activity_code = "8"
        cue_slot.display_focus = "lyric_display"

        untouched_slot = window.data["A"][0][1]
        untouched_slot.file_path = r"C:\Media\plain.mp3"
        untouched_slot.title = "Plain"
        untouched_slot.duration_ms = 1000
        untouched_slot.activity_code = "8"
        untouched_slot.display_focus = ""

        monkeypatch.setattr(mw.QMessageBox, "question", lambda *args, **kwargs: mw.QMessageBox.Yes)

        window._clear_all_display_focus()

        assert main_slot.display_focus == ""
        assert cue_slot.display_focus == ""
        assert untouched_slot.display_focus == ""
        assert window._dirty is True
    finally:
        _cleanup_main_window(window, qapp)


def test_tools_menu_includes_bpm_actions_and_window_menu_includes_metronome_display(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        tools_menu = next(
            action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Tools"
        )
        tool_items = {action.text().replace("&", "") for action in tools_menu.actions()}
        assert "Analyze BPM In Set" in tool_items
        assert "Clear All BPM" in tool_items

        window_menu = next(
            action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Window"
        )
        window_items = {action.text().replace("&", "") for action in window_menu.actions()}
        assert "Metronome Display" in window_items
    finally:
        _cleanup_main_window(window, qapp)


def test_tools_clear_all_bpm_removes_audio_beat_maps(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        slot = window.data["A"][0][0]
        slot.file_path = r"C:\Media\theme.mp3"
        slot.title = "Theme"
        slot.duration_ms = 1000
        slot.activity_code = "8"
        slot.audio_beat_map = AudioBeatMap(bpm=128.0)

        monkeypatch.setattr(mw.QMessageBox, "question", lambda *args, **kwargs: mw.QMessageBox.Yes)

        window._clear_all_bpm_analysis()

        assert slot.audio_beat_map is None
        assert window._dirty is True
    finally:
        _cleanup_main_window(window, qapp)


def test_tools_analyze_bpm_in_set_analyzes_selected_files_with_progress(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        primary_path = r"C:\Media\theme.mp3"
        secondary_path = r"C:\Media\walkin.mp3"

        slot_a = window.data["A"][0][0]
        slot_a.file_path = primary_path
        slot_a.title = "Theme A"
        slot_a.duration_ms = 1000
        slot_a.activity_code = "8"

        slot_b = window.data["A"][0][1]
        slot_b.file_path = primary_path
        slot_b.title = "Theme B"
        slot_b.duration_ms = 1000
        slot_b.activity_code = "8"

        slot_c = window.data["A"][0][2]
        slot_c.file_path = secondary_path
        slot_c.title = "Walk-In"
        slot_c.duration_ms = 1000
        slot_c.activity_code = "8"

        def _select_only_primary(candidates):
            return [candidate for candidate in candidates if candidate.get("file_path") == primary_path]

        batch_calls: list[list[str]] = []

        def _fake_run_bpm_analysis_batch(candidates):
            batch_calls.append([candidate.get("file_path") for candidate in candidates])
            analyzed = AudioBeatMap(bpm=111.0)
            updated_buttons = 0
            for candidate in candidates:
                for ref in list(candidate.get("refs", []) or []):
                    slot = ref.get("slot_ref")
                    if slot is None:
                        continue
                    slot.audio_beat_map = analyzed
                    updated_buttons += 1
            return {
                "analyzed_files": len(candidates),
                "updated_buttons": updated_buttons,
                "skipped_files": 0,
                "failures": [],
                "canceled": False,
            }

        monkeypatch.setattr(window, "_select_bpm_analysis_file_candidates", _select_only_primary)
        monkeypatch.setattr(window, "_run_bpm_analysis_batch", _fake_run_bpm_analysis_batch)

        window._analyze_bpm_in_set()

        assert batch_calls == [[primary_path]]
        assert slot_a.audio_beat_map is not None and slot_a.audio_beat_map.bpm == 111.0
        assert slot_b.audio_beat_map is not None and slot_b.audio_beat_map.bpm == 111.0
        assert slot_c.audio_beat_map is None
        assert window._dirty is True
    finally:
        _cleanup_main_window(window, qapp)


def test_tools_set_changes_reports_dirty_set_lines(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        tools_menu = next(
            action.menu() for action in window.menuBar().actions() if action.text().replace("&", "") == "Tools"
        )
        tool_items = {action.text().replace("&", "") for action in tools_menu.actions()}
        assert "Set Changes" in tool_items

        window._capture_clean_set_snapshot()
        slot = window.data["A"][0][0]
        slot.file_path = r"C:\Media\theme.mp3"
        slot.title = "Theme"
        slot.duration_ms = 1000
        slot.activity_code = "8"
        window._set_dirty(True)

        report, dirty = window._current_set_change_report()

        assert dirty is True
        assert "Dirty: Yes" in report
        assert "Unified Diff:" in report
        assert "+s1=C:\\Media\\theme.mp3" in report
    finally:
        _cleanup_main_window(window, qapp)


def test_discard_current_set_changes_reloads_current_set(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        calls: list[tuple[str, object]] = []
        window.current_set_path = r"C:\Sets\service.set"
        window._set_dirty(True)

        monkeypatch.setattr(mw.QMessageBox, "question", lambda *args, **kwargs: mw.QMessageBox.Yes)
        monkeypatch.setattr(
            window,
            "_load_set",
            lambda path, show_message=False, restore_last_position=False: calls.append(
                ("load", path, show_message, restore_last_position)
            ),
        )

        window._discard_current_set_changes()

        assert calls == [("load", r"C:\Sets\service.set", False, False)]
    finally:
        _cleanup_main_window(window, qapp)


def test_discard_current_set_changes_resets_unsaved_new_set(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        calls: list[str] = []
        window.current_set_path = ""
        window._set_dirty(True)

        monkeypatch.setattr(mw.QMessageBox, "question", lambda *args, **kwargs: mw.QMessageBox.Yes)
        monkeypatch.setattr(window, "_new_set", lambda: calls.append("new"))

        window._discard_current_set_changes()

        assert calls == ["new"]
    finally:
        _cleanup_main_window(window, qapp)


def test_playing_sound_button_is_revealed_after_page_switch_and_in_list_view(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        target_slot = 35
        playing_key = ("A", 0, target_slot)
        window.resize(640, 420)
        window.current_playing = playing_key
        window._active_playing_keys = {playing_key}
        window._refresh_sound_grid()
        qapp.processEvents()

        window._select_page(1)
        qapp.processEvents()
        window._select_page(0)
        qapp.processEvents()

        grid_button = window.sound_buttons[target_slot]
        grid_viewport = window.sound_button_grid_scroll.viewport()
        grid_rect = grid_button.geometry()
        grid_rect.moveTopLeft(grid_button.mapTo(grid_viewport, QPoint(0, 0)))
        assert window.sound_button_grid_scroll.verticalScrollBar().value() > 0
        assert grid_viewport.rect().intersects(grid_rect)

        window._set_sound_button_view_mode("list", persist=False)
        qapp.processEvents()
        list_row = window.sound_button_list_rows[target_slot]
        list_viewport = window.sound_button_list_scroll.viewport()
        list_rect = list_row.geometry()
        list_rect.moveTopLeft(list_row.mapTo(list_viewport, QPoint(0, 0)))
        assert window.sound_button_list_scroll.verticalScrollBar().value() > 0
        assert list_viewport.rect().intersects(list_rect)
    finally:
        _cleanup_main_window(window, qapp)


def test_list_view_context_menu_uses_mouse_global_position(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.show()
    qapp.processEvents()

    try:
        window._set_sound_button_view_mode("list", persist=False)
        qapp.processEvents()
        captured: dict[str, object] = {}

        def _capture(slot_index, pos, *, global_pos=False):
            captured["slot_index"] = slot_index
            captured["pos"] = pos
            captured["global_pos"] = global_pos

        monkeypatch.setattr(window, "_show_slot_menu", _capture)
        row = window.sound_button_list_rows[0]
        local_pos = QPoint(17, 19)
        global_pos = row.mapToGlobal(local_pos)
        event = QContextMenuEvent(QContextMenuEvent.Mouse, local_pos, global_pos)
        row.contextMenuEvent(event)

        assert captured["slot_index"] == 0
        assert captured["global_pos"] is True
        assert captured["pos"] == global_pos
    finally:
        _cleanup_main_window(window, qapp)


def test_list_view_header_stays_visible_and_columns_follow_settings(qapp, monkeypatch):
    _patch_main_window_startup(monkeypatch)
    window = mw.MainWindow()
    window.resize(900, 520)
    window.show()
    qapp.processEvents()

    try:
        window._set_sound_button_view_mode("list", persist=False)
        qapp.processEvents()

        assert window.sound_button_stack.currentWidget() is window.sound_button_list_container
        assert window.sound_button_list_scroll.widget() is window.sound_button_list_widget
        assert not window.sound_button_list_widget.isAncestorOf(window.sound_button_list_header)

        header_y_before = window.sound_button_list_header.mapTo(window.sound_button_list_container, QPoint(0, 0)).y()
        window.sound_button_list_scroll.verticalScrollBar().setValue(
            window.sound_button_list_scroll.verticalScrollBar().maximum()
        )
        qapp.processEvents()
        header_y_after = window.sound_button_list_header.mapTo(window.sound_button_list_container, QPoint(0, 0)).y()
        assert header_y_after == header_y_before
        assert window.sound_button_list_header.isVisible()

        window._set_sound_button_list_hidden_columns(["ram", "notes"], persist=False)
        window._set_sound_button_list_column_width_for_key("ram", 18, persist=False)
        qapp.processEvents()

        header = window.sound_button_list_header
        first_row = window.sound_button_list_rows[0]
        assert header.column_labels["ram"].isHidden()
        assert header.column_labels["notes"].isHidden()
        assert first_row.column_widgets["ram"].isHidden()
        assert first_row.column_widgets["notes"].isHidden()

        window._set_sound_button_list_hidden_columns([], persist=False)
        qapp.processEvents()
        assert header.column_labels["ram"].isVisible()
        assert first_row.column_widgets["ram"].isVisible()
        assert header.column_labels["ram"].width() == 18
        assert first_row.column_widgets["ram"].width() == 18
    finally:
        _cleanup_main_window(window, qapp)
