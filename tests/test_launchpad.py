from __future__ import annotations

import pytest

from pyssp.launchpad import (
    LAUNCHPAD_CONTROL_PAD_COUNT,
    LAUNCHPAD_LAYOUT_BOTTOM_SIX,
    LAUNCHPAD_LAYOUT_TOP_SIX,
    is_launchpad_name,
    launchpad_control_bindings,
    launchpad_control_note,
    launchpad_find_matching_output,
    launchpad_page_bindings,
    launchpad_page_slot_binding,
    launchpad_page_slot_note,
    launchpad_programmer_toggle_sysex,
    launchpad_programmer_note,
)


def test_launchpad_programmer_note_uses_documented_programmer_grid_coordinates() -> None:
    assert launchpad_programmer_note(7, 0) == 11
    assert launchpad_programmer_note(7, 7) == 18
    assert launchpad_programmer_note(0, 0) == 81
    assert launchpad_programmer_note(0, 7) == 88


def test_launchpad_page_slot_note_bottom_six_maps_page_to_lower_six_rows() -> None:
    assert launchpad_page_slot_note(0, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 61
    assert launchpad_page_slot_note(7, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 68
    assert launchpad_page_slot_note(40, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 11
    assert launchpad_page_slot_note(47, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 18


def test_launchpad_page_slot_note_top_six_maps_page_to_upper_six_rows() -> None:
    assert launchpad_page_slot_note(0, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 81
    assert launchpad_page_slot_note(7, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 88
    assert launchpad_page_slot_note(40, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 31
    assert launchpad_page_slot_note(47, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 38


def test_launchpad_control_note_bottom_six_maps_controls_to_top_two_rows() -> None:
    assert launchpad_control_note(0, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 81
    assert launchpad_control_note(7, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 88
    assert launchpad_control_note(8, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 71
    assert launchpad_control_note(15, layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX) == 78


def test_launchpad_control_note_top_six_maps_controls_to_bottom_two_rows() -> None:
    assert launchpad_control_note(0, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 21
    assert launchpad_control_note(7, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 28
    assert launchpad_control_note(8, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 11
    assert launchpad_control_note(15, layout=LAUNCHPAD_LAYOUT_TOP_SIX) == 18


def test_launchpad_page_slot_binding_can_be_device_specific() -> None:
    assert launchpad_page_slot_binding(0, selector="name::Launchpad Mini") == "name::Launchpad Mini|90:3D"


def test_launchpad_page_bindings_returns_all_48_page_bindings() -> None:
    bindings = launchpad_page_bindings(layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX)
    assert len(bindings) == 48
    assert bindings[0] == "90:3D"
    assert bindings[-1] == "90:12"


def test_launchpad_control_bindings_returns_all_16_control_bindings() -> None:
    bindings = launchpad_control_bindings(layout=LAUNCHPAD_LAYOUT_BOTTOM_SIX)
    assert len(bindings) == LAUNCHPAD_CONTROL_PAD_COUNT
    assert bindings[0] == "90:51"
    assert bindings[-1] == "90:4E"


def test_launchpad_name_detection_and_output_matching() -> None:
    assert is_launchpad_name("Launchpad Mini MK3")
    assert is_launchpad_name("LPX MIDI")
    assert not is_launchpad_name("MPK Mini")
    assert launchpad_find_matching_output(
        "Launchpad Mini MK3 MIDI",
        [("1", "Other Device"), ("2", "Launchpad Mini MK3"), ("3", "Launchpad Mini MK3 DAW")],
    ) == ("2", "Launchpad Mini MK3")


def test_launchpad_programmer_toggle_sysex_for_supported_devices() -> None:
    assert launchpad_programmer_toggle_sysex("Launchpad X") == bytes([0xF0, 0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x01, 0xF7])
    assert launchpad_programmer_toggle_sysex("LPX MIDI") == bytes([0xF0, 0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x01, 0xF7])
    assert launchpad_programmer_toggle_sysex("Launchpad Mini MK3", enabled=False) == bytes(
        [0xF0, 0x00, 0x20, 0x29, 0x02, 0x0D, 0x0E, 0x00, 0xF7]
    )


@pytest.mark.parametrize("row,col", [(-1, 0), (8, 0), (0, -1), (0, 8)])
def test_launchpad_programmer_note_rejects_out_of_range_coordinates(row: int, col: int) -> None:
    with pytest.raises(ValueError):
        launchpad_programmer_note(row, col)


@pytest.mark.parametrize("slot_index", [-1, 48])
def test_launchpad_page_slot_note_rejects_out_of_range_slot(slot_index: int) -> None:
    with pytest.raises(ValueError):
        launchpad_page_slot_note(slot_index)


@pytest.mark.parametrize("control_index", [-1, 16])
def test_launchpad_control_note_rejects_out_of_range_control(control_index: int) -> None:
    with pytest.raises(ValueError):
        launchpad_control_note(control_index)
