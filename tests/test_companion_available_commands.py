from __future__ import annotations

from pathlib import Path

import pytest
from PyQt5.QtWidgets import QApplication

from pyssp.companion_available_commands import (
    clear_companion_available_commands,
    format_companion_available_commands,
    get_companion_available_commands_path,
    is_black_empty_command,
    is_navigation_command,
    load_companion_available_commands,
    record_companion_available_command,
)
from pyssp.ui.companion_available_commands_dialog import CompanionAvailableCommandsDialog


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_companion_available_commands_round_trip(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)
    monkeypatch.setattr("pyssp.companion_available_commands.get_settings_path", lambda: settings_path)

    payload = record_companion_available_command(
        location="2/1/3",
        text="Play Song",
        key_type="BUTTON",
        color="#112233",
        pressed=False,
    )
    assert payload is not None
    saved_path = get_companion_available_commands_path()
    assert saved_path == tmp_path / "companion_available_commands.json"
    loaded = load_companion_available_commands()
    assert loaded["pages"]["2"]["1/3"]["page"] == 2
    assert loaded["pages"]["2"]["1/3"]["row"] == 1
    assert loaded["pages"]["2"]["1/3"]["column"] == 3
    assert loaded["pages"]["2"]["1/3"]["text"] == "Play Song"
    assert loaded["pages"]["2"]["1/3"]["type"] == "BUTTON"
    assert loaded["pages"]["2"]["1/3"]["color"] == "#112233"


def test_companion_available_commands_replaces_newlines_in_text(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)
    monkeypatch.setattr("pyssp.companion_available_commands.get_settings_path", lambda: settings_path)

    record_companion_available_command(
        location="3/2/1",
        text="Line 1\nLine 2\r\nLine 3",
        key_type="BUTTON",
        color="#445566",
        pressed=False,
    )
    loaded = load_companion_available_commands()
    assert loaded["pages"]["3"]["2/1"]["text"] == "Line 1 Line 2 Line 3"


def test_companion_available_commands_replaces_literal_backslash_new_sequences(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)
    monkeypatch.setattr("pyssp.companion_available_commands.get_settings_path", lambda: settings_path)

    record_companion_available_command(
        location="4/1/2",
        text=r"Power\nON",
        key_type="BUTTON",
        color="#778899",
        pressed=False,
    )
    loaded = load_companion_available_commands()
    assert loaded["pages"]["4"]["1/2"]["text"] == "Power ON"


def test_companion_available_commands_updates_existing_slot_and_clears(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr("pyssp.settings_store.get_settings_path", lambda: settings_path)
    monkeypatch.setattr("pyssp.companion_available_commands.get_settings_path", lambda: settings_path)

    record_companion_available_command(location="1/0/0", text="First", key_type="BUTTON", color="#101010")
    record_companion_available_command(location="1/0/0", text="Second", key_type="BUTTON", color="#202020")
    rendered = format_companion_available_commands()
    assert "Second" in rendered
    assert "First" not in rendered
    assert "#202020" in rendered

    record_companion_available_command(
        location="1/0/0",
        text="Pressed Text",
        key_type="BUTTON",
        color="#FFFF00",
        pressed=True,
    )
    loaded = load_companion_available_commands()
    assert loaded["pages"]["1"]["0/0"]["text"] == "Pressed Text"
    assert loaded["pages"]["1"]["0/0"]["color"] == "#202020"

    cleared = clear_companion_available_commands()
    assert cleared["pages"] == {}
    assert load_companion_available_commands()["pages"] == {}


def test_companion_available_commands_black_empty_filter_detection():
    assert is_black_empty_command({"text": "", "color": "#000000"}) is True
    assert is_black_empty_command({"text": "Play", "color": "#000000"}) is False
    assert is_black_empty_command({"text": "", "color": "#101010"}) is False


def test_companion_available_commands_navigation_filter_detection():
    assert is_navigation_command({"type": "PAGEUP"}) is True
    assert is_navigation_command({"type": "PAGEDOWN"}) is True
    assert is_navigation_command({"type": "PAGENUM"}) is True
    assert is_navigation_command({"type": "BUTTON"}) is False


def test_companion_available_commands_dialog_hides_black_empty_rows(qapp):
    dialog = CompanionAvailableCommandsDialog()
    payload = {
        "pages": {
            "1": {
                "0/0": {"page": 1, "row": 0, "column": 0, "text": "", "type": "BUTTON", "color": "#000000"},
                "0/1": {"page": 1, "row": 0, "column": 1, "text": "Play", "type": "BUTTON", "color": "#123456"},
                "0/2": {"page": 1, "row": 0, "column": 2, "text": "Page Up", "type": "PAGEUP", "color": "#334455"},
            }
        },
        "updated_at": "",
    }

    dialog.set_payload(payload, hide_black_empty=False, hide_navigation=False)
    assert dialog.table.rowCount() == 3
    assert dialog.table.item(0, 0).text() == "1/0/0"
    assert dialog.table.item(1, 0).text() == "1/0/1"
    assert dialog.table.item(1, 2).text() == "Play"
    assert dialog.table.item(1, 2).background().color().name().lower() == "#123456"
    assert dialog.table.item(1, 2).foreground().color().name().lower() == "#edcba9"

    dialog.set_payload(payload, hide_black_empty=True, hide_navigation=False)
    assert dialog.table.rowCount() == 2
    assert dialog.table.item(0, 0).text() == "1/0/1"
    assert dialog.table.item(0, 2).text() == "Play"

    dialog.set_payload(payload, hide_black_empty=True, hide_navigation=True)
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "1/0/1"
    assert dialog.table.item(0, 2).text() == "Play"


def test_companion_available_commands_dialog_emits_press_down_up_for_selected_row(qapp):
    dialog = CompanionAvailableCommandsDialog()
    payload = {
        "pages": {
            "2": {
                "1/3": {"page": 2, "row": 1, "column": 3, "text": "Play", "type": "BUTTON", "color": "#123456"},
            }
        },
        "updated_at": "",
    }
    seen: list[tuple[str, str]] = []
    dialog.locationCommandRequested.connect(lambda location, action: seen.append((location, action)))
    dialog.set_payload(payload)
    assert dialog.down_button.text() == "Press Down"
    assert dialog.up_button.text() == "Release Up"
    dialog.table.selectRow(0)

    dialog.press_button.click()
    dialog.down_button.click()
    dialog.up_button.click()
    dialog.table.itemDoubleClicked.emit(dialog.table.item(0, 0))

    assert seen == [
        ("2/1/3", "press"),
        ("2/1/3", "down"),
        ("2/1/3", "up"),
        ("2/1/3", "press"),
    ]


def test_companion_available_commands_dialog_open_virtual_satellite_signal(qapp):
    dialog = CompanionAvailableCommandsDialog()
    seen: list[str] = []
    dialog.openVirtualSatelliteRequested.connect(lambda: seen.append("open"))

    dialog.open_virtual_satellite_button.click()

    assert seen == ["open"]


def test_companion_available_commands_dialog_bypass_signal(qapp):
    dialog = CompanionAvailableCommandsDialog()
    seen: list[bool] = []
    dialog.bypassToggled.connect(seen.append)

    dialog.bypass_checkbox.setChecked(True)
    dialog.bypass_checkbox.setChecked(False)

    assert seen == [True, False]


def test_companion_available_commands_dialog_search_filters_by_location_and_text(qapp):
    dialog = CompanionAvailableCommandsDialog()
    payload = {
        "pages": {
            "1": {
                "0/1": {"page": 1, "row": 0, "column": 1, "text": "Play Intro", "type": "BUTTON", "color": "#123456"},
                "2/3": {"page": 1, "row": 2, "column": 3, "text": "Stop", "type": "BUTTON", "color": "#654321"},
            }
        },
        "updated_at": "",
    }

    dialog.set_payload(payload)
    assert dialog.table.rowCount() == 2

    dialog.search_edit.setText("1/2/3")
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "1/2/3"
    assert dialog.table.item(0, 2).text() == "Stop"

    dialog.search_edit.setText("play")
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 0).text() == "1/0/1"
    assert dialog.table.item(0, 2).text() == "Play Intro"

    dialog.search_edit.setText("")
    assert dialog.table.rowCount() == 2
