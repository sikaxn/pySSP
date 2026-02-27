import os
import sys
from pathlib import Path

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pyssp.ui.vst_window import VSTWindow


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_added_plugin_item_is_checkable_and_enabled_by_default(qapp):
    _ = qapp
    window = VSTWindow()
    plugin_path = "/Library/Audio/Plug-Ins/VST3/Test.vst3"
    window.set_available_plugins([plugin_path])
    window.available_list.setCurrentRow(0)

    window._add_selected_plugin()

    item = window.chain_list.item(0)
    assert item is not None
    assert bool(item.flags() & Qt.ItemIsUserCheckable) is True
    assert item.checkState() == Qt.Checked
    assert window.chain_enabled() == [True]


def test_unchecked_chain_item_reports_bypass_state(qapp):
    _ = qapp
    window = VSTWindow()
    plugin_path = "/Library/Audio/Plug-Ins/VST3/Test.vst3"
    window.set_chain([plugin_path])
    window.set_chain_enabled([False])

    assert window.chain_enabled() == [False]
