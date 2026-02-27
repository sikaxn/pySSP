from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyssp.i18n import localize_widget_tree
from pyssp.vst import plugin_display_name
from pyssp.vst_host import host_unavailable_reason, is_host_available


class VSTWindow(QDialog):
    chainChanged = pyqtSignal(list)
    chainEnabledChanged = pyqtSignal(list)
    processingEnabledChanged = pyqtSignal(bool)
    pluginStateChanged = pyqtSignal(str, dict)
    pluginPanelRequested = pyqtSignal(str)
    newRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    saveAsRequested = pyqtSignal()

    def __init__(self, parent=None, language: str = "en") -> None:
        super().__init__(parent)
        self.setWindowTitle("VST Rack")
        self.resize(980, 560)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)
        self._available_plugins: List[str] = []
        self._plugin_state: Dict[str, Dict[str, object]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        title = QLabel("Plugin Rack")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        root.addWidget(title)
        rack_row = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.newRequested.emit)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.saveRequested.emit)
        save_as_btn = QPushButton("Save As")
        save_as_btn.clicked.connect(self.saveAsRequested.emit)
        self.rack_path_label = QLabel("Rack: (default)")
        self.rack_path_label.setStyleSheet("color:#555;")
        rack_row.addWidget(new_btn)
        rack_row.addWidget(save_btn)
        rack_row.addWidget(save_as_btn)
        rack_row.addSpacing(10)
        rack_row.addWidget(self.rack_path_label, 1)
        root.addLayout(rack_row)
        self.processing_enabled_checkbox = QPushButton("Plugins ON")
        self.processing_enabled_checkbox.setCheckable(True)
        self.processing_enabled_checkbox.setChecked(True)
        self.processing_enabled_checkbox.toggled.connect(self._on_processing_toggled)
        root.addWidget(self.processing_enabled_checkbox)

        row = QHBoxLayout()
        root.addLayout(row, 1)

        available_panel = QWidget()
        available_layout = QVBoxLayout(available_panel)
        available_layout.setContentsMargins(0, 0, 0, 0)
        available_layout.addWidget(QLabel("Enabled Plugins"))
        self.available_list = QListWidget()
        available_layout.addWidget(self.available_list, 1)
        row.addWidget(available_panel, 1)

        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addStretch(1)
        add_btn = QPushButton("Add ->")
        add_btn.clicked.connect(self._add_selected_plugin)
        controls_layout.addWidget(add_btn)
        remove_btn = QPushButton("<- Remove")
        remove_btn.clicked.connect(self._remove_selected_chain_item)
        controls_layout.addWidget(remove_btn)
        controls_layout.addSpacing(14)
        up_btn = QPushButton("Move Up")
        up_btn.clicked.connect(lambda: self._move_chain_item(-1))
        controls_layout.addWidget(up_btn)
        down_btn = QPushButton("Move Down")
        down_btn.clicked.connect(lambda: self._move_chain_item(1))
        controls_layout.addWidget(down_btn)
        controls_layout.addSpacing(14)
        panel_btn = QPushButton("Open Plugin Panel")
        panel_btn.clicked.connect(self._open_plugin_panel_for_selection)
        controls_layout.addWidget(panel_btn)
        controls_layout.addStretch(1)
        row.addWidget(controls_panel)

        chain_panel = QWidget()
        chain_layout = QVBoxLayout(chain_panel)
        chain_layout.setContentsMargins(0, 0, 0, 0)
        chain_layout.addWidget(QLabel("Plugin Chain"))
        self.chain_list = QListWidget()
        self.chain_list.itemChanged.connect(self._on_chain_item_changed)
        chain_layout.addWidget(self.chain_list, 1)
        row.addWidget(chain_panel, 1)

        localize_widget_tree(self, language)

    def set_available_plugins(self, plugins: List[str]) -> None:
        self._available_plugins = [str(p).strip() for p in plugins if str(p).strip()]
        self.available_list.clear()
        for plugin_path in self._available_plugins:
            item = QListWidgetItem(plugin_display_name(plugin_path))
            item.setToolTip(plugin_path)
            item.setData(Qt.UserRole, plugin_path)
            self.available_list.addItem(item)

    def set_chain(self, chain: List[str]) -> None:
        try:
            self.chain_list.itemChanged.disconnect(self._on_chain_item_changed)
        except Exception:
            pass
        self.chain_list.clear()
        for plugin_path in [str(p).strip() for p in chain if str(p).strip()]:
            self.chain_list.addItem(self._make_chain_item(plugin_path, enabled=True))
        self.chain_list.itemChanged.connect(self._on_chain_item_changed)
        self._emit_chain_changed()

    def set_plugin_state_map(self, plugin_state: Dict[str, Dict[str, object]]) -> None:
        self._plugin_state = {
            str(path).strip(): dict(state)
            for path, state in dict(plugin_state or {}).items()
            if str(path).strip() and isinstance(state, dict)
        }

    def set_chain_enabled(self, enabled_flags: List[bool]) -> None:
        flags = [bool(v) for v in list(enabled_flags)]
        try:
            self.chain_list.itemChanged.disconnect(self._on_chain_item_changed)
        except Exception:
            pass
        for index in range(self.chain_list.count()):
            item = self.chain_list.item(index)
            if item is None:
                continue
            checked = flags[index] if index < len(flags) else True
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.chain_list.itemChanged.connect(self._on_chain_item_changed)
        self.chainEnabledChanged.emit(self.chain_enabled())

    def chain_enabled(self) -> List[bool]:
        values: List[bool] = []
        for i in range(self.chain_list.count()):
            item = self.chain_list.item(i)
            if item is None:
                continue
            values.append(item.checkState() == Qt.Checked)
        return values

    def set_processing_enabled(self, enabled: bool) -> None:
        self.processing_enabled_checkbox.setChecked(bool(enabled))
        self._on_processing_toggled(bool(enabled))

    def set_rack_path(self, rack_path: str) -> None:
        token = str(rack_path or "").strip()
        self.rack_path_label.setText(f"Rack: {token if token else '(default)'}")

    def chain(self) -> List[str]:
        items: List[str] = []
        for i in range(self.chain_list.count()):
            item = self.chain_list.item(i)
            if item is None:
                continue
            plugin_path = str(item.data(Qt.UserRole) or "").strip()
            if plugin_path:
                items.append(plugin_path)
        return items

    def _add_selected_plugin(self) -> None:
        current = self.available_list.currentItem()
        if current is None:
            return
        plugin_path = str(current.data(Qt.UserRole) or "").strip()
        if not plugin_path:
            return
        item = self._make_chain_item(plugin_path, enabled=True)
        self.chain_list.addItem(item)
        self.chain_list.setCurrentItem(item)
        self._emit_chain_changed()

    def _make_chain_item(self, plugin_path: str, enabled: bool = True) -> QListWidgetItem:
        item = QListWidgetItem(plugin_display_name(plugin_path))
        item.setToolTip(plugin_path)
        item.setData(Qt.UserRole, plugin_path)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if bool(enabled) else Qt.Unchecked)
        return item

    def _remove_selected_chain_item(self) -> None:
        row = self.chain_list.currentRow()
        if row < 0:
            return
        self.chain_list.takeItem(row)
        if self.chain_list.count() > 0:
            self.chain_list.setCurrentRow(max(0, min(row, self.chain_list.count() - 1)))
        self._emit_chain_changed()

    def _move_chain_item(self, direction: int) -> None:
        row = self.chain_list.currentRow()
        if row < 0:
            return
        target = row + int(direction)
        if target < 0 or target >= self.chain_list.count():
            return
        item = self.chain_list.takeItem(row)
        self.chain_list.insertItem(target, item)
        self.chain_list.setCurrentRow(target)
        self._emit_chain_changed()

    def _emit_chain_changed(self) -> None:
        self.chainChanged.emit(self.chain())
        self.chainEnabledChanged.emit(self.chain_enabled())

    def _on_chain_item_changed(self, _item: QListWidgetItem) -> None:
        self.chainEnabledChanged.emit(self.chain_enabled())

    def _on_processing_toggled(self, enabled: bool) -> None:
        self.processing_enabled_checkbox.setText("Plugins ON" if enabled else "Plugins OFF")
        self.processingEnabledChanged.emit(bool(enabled))

    def _selected_plugin_path(self) -> str:
        chain_item = self.chain_list.currentItem()
        if chain_item is not None:
            token = str(chain_item.data(Qt.UserRole) or "").strip()
            if token:
                return token
        available_item = self.available_list.currentItem()
        if available_item is not None:
            token = str(available_item.data(Qt.UserRole) or "").strip()
            if token:
                return token
        return ""

    def _open_plugin_panel_for_selection(self) -> None:
        if not is_host_available():
            QMessageBox.warning(self, "Plugin Panel", f"VST host unavailable:\n{host_unavailable_reason()}")
            return
        plugin_path = self._selected_plugin_path()
        if not plugin_path:
            QMessageBox.information(self, "Plugin Panel", "Select a plugin from the chain or enabled plugins list.")
            return
        self.pluginPanelRequested.emit(plugin_path)
