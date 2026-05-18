# `pyssp/ui/options_dialog/layout_helpers.py`

- Source: `pyssp/ui/options_dialog/layout_helpers.py`
- Module path: `pyssp.ui.options_dialog.layout_helpers`
- API entries: `1`

## Module Docstring

No module docstring.

## Classes

### `LayoutHelpersMixin`

- Defined at `pyssp/ui/options_dialog/layout_helpers.py:7`

#### Internal Members

- `_capture_window_layout_from_editor(self) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:8)
- `_handle_window_layout_drop(self, target: str, raw_payload: str, px: int, py: int) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:32)
- `_refresh_window_layout_available_list(self) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:154)
- `_on_window_layout_show_all_toggled(self, checked: bool) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:178)
- `_clear_all_window_layout_buttons(self) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:183)
- `_confirm_layout_overlap_action(self) -> str` [method] (pyssp/ui/options_dialog/layout_helpers.py:188)
- `_build_web_remote_url_text(self, port: int) -> str` [method] (pyssp/ui/options_dialog/layout_helpers.py:204)
- `_build_web_remote_ws_port_text(port: int) -> str` [staticmethod] (pyssp/ui/options_dialog/layout_helpers.py:208)
- `_build_web_remote_https_url_text(self, port: int) -> str` [method] (pyssp/ui/options_dialog/layout_helpers.py:214)
- `_build_web_remote_https_port_text(port: int) -> str` [staticmethod] (pyssp/ui/options_dialog/layout_helpers.py:218)
- `_build_web_remote_wss_port_text(port: int) -> str` [staticmethod] (pyssp/ui/options_dialog/layout_helpers.py:225)
- `_set_web_remote_url_label(self, url: str) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:231)
- `_set_web_remote_ws_port_label(self, ws_port_text: str) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:234)
- `_set_web_remote_https_url_label(self, url: str) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:237)
- `_set_web_remote_https_port_label(self, https_port_text: str) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:240)
- `_set_web_remote_wss_port_label(self, wss_port_text: str) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:243)
- `_update_web_remote_page_labels(self, port: int) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:246)
- `_set_web_remote_companion_text(self, port: int) -> None` [method] (pyssp/ui/options_dialog/layout_helpers.py:254)
