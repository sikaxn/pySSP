from __future__ import annotations

from .shared import *
from .widgets import *


class LayoutHelpersMixin:
    def _capture_window_layout_from_editor(self) -> None:
        if getattr(self, "_window_layout_drop_in_progress", False):
            self._window_layout_capture_pending = True
            return
        if not hasattr(self, "window_layout_main_editor") or not hasattr(self, "window_layout_fade_editor"):
            return
        available_buttons = (
            self.window_layout_available_list.buttons() if hasattr(self, "window_layout_available_list") else []
        )
        self._window_layout = normalize_window_layout(
            {
                "main": self.window_layout_main_editor.export_items(),
                "fade": self.window_layout_fade_editor.export_items(),
                "available": available_buttons,
                "show_all_available": bool(
                    self.window_layout_show_all_checkbox.isChecked()
                    if hasattr(self, "window_layout_show_all_checkbox")
                    else False
                ),
            }
        )
        self._refresh_window_layout_available_list()
        self._window_layout_capture_pending = False

    def _handle_window_layout_drop(self, target: str, raw_payload: str, px: int, py: int) -> None:
        try:
            payload = json.loads(str(raw_payload or ""))
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        button = str(payload.get("button", "")).strip()
        if button not in set(WINDOW_LAYOUT_MAIN_ORDER + WINDOW_LAYOUT_FADE_ORDER):
            return
        source_zone = str(payload.get("source_zone", "")).strip().lower()
        uid = str(payload.get("uid", "")).strip()
        try:
            w = max(1, int(payload.get("w", 1)))
        except Exception:
            w = 1
        try:
            h = max(1, int(payload.get("h", 1)))
        except Exception:
            h = 1

        src_canvas = None
        if source_zone == "main":
            src_canvas = self.window_layout_main_editor
        elif source_zone == "fade":
            src_canvas = self.window_layout_fade_editor

        dst_canvas = None
        if target == "main":
            dst_canvas = self.window_layout_main_editor
        elif target == "fade":
            dst_canvas = self.window_layout_fade_editor

        source_item = src_canvas.get_item(uid) if (src_canvas is not None and uid) else None
        source_uid = str(source_item.get("uid", uid)) if source_item else str(uid)
        source_button = str(source_item.get("button", button)) if source_item else button
        source_w = int(source_item.get("w", w)) if source_item else w
        source_h = int(source_item.get("h", h)) if source_item else h
        source_x = int(source_item.get("x", 0)) if source_item else 0
        source_y = int(source_item.get("y", 0)) if source_item else 0

        changed = False
        self._window_layout_drop_in_progress = True
        try:
            allow_dupes = bool(self.window_layout_show_all_checkbox.isChecked())
            if (not allow_dupes) and target in {"main", "fade"}:
                removed_main = self.window_layout_main_editor.remove_all_by_button(
                    source_button,
                    exclude_uid=(source_uid if src_canvas is self.window_layout_main_editor else ""),
                )
                removed_fade = self.window_layout_fade_editor.remove_all_by_button(
                    source_button,
                    exclude_uid=(source_uid if src_canvas is self.window_layout_fade_editor else ""),
                )
                changed = bool(removed_main or removed_fade) or changed

            if target == "available":
                if src_canvas is not None and uid:
                    changed = src_canvas.remove_uid(uid) is not None or changed
                return

            if dst_canvas is None:
                return
            gx, gy = dst_canvas.snap_to_grid(QPoint(px, py))
            if source_item is None:
                source_x, source_y = gx, gy

            occupied = dst_canvas.occupied_item_at(gx, gy, exclude_uid=(source_uid if src_canvas is dst_canvas else ""))
            if occupied is not None:
                decision = self._confirm_layout_overlap_action()
                if decision == "cancel":
                    return
                if decision == "copy":
                    if src_canvas is not None and uid and source_item is not None:
                        changed = src_canvas.remove_uid(uid) is not None or changed
                    dst_canvas.upsert_item(
                        str(occupied.get("uid", "")),
                        source_button,
                        int(occupied.get("x", gx)),
                        int(occupied.get("y", gy)),
                        int(occupied.get("w", 1)),
                        int(occupied.get("h", 1)),
                    )
                    changed = True
                    return
                # swap
                target_uid = str(occupied.get("uid", ""))
                target_button = str(occupied.get("button", ""))
                target_x = int(occupied.get("x", gx))
                target_y = int(occupied.get("y", gy))
                target_w = int(occupied.get("w", 1))
                target_h = int(occupied.get("h", 1))

                if src_canvas is not None and uid and source_item is not None:
                    changed = src_canvas.remove_uid(uid) is not None or changed
                dst_canvas.upsert_item(target_uid, source_button, target_x, target_y, target_w, target_h)
                if src_canvas is not None and source_item is not None:
                    src_canvas.add_item(target_button, source_x, source_y, source_w, source_h, uid=source_uid)
                else:
                    current = self.window_layout_available_list.buttons()
                    if target_button not in current:
                        current.append(target_button)
                        self.window_layout_available_list.set_buttons(current)
                changed = True
                return

            reuse_uid = None
            if src_canvas is not None and uid:
                removed = src_canvas.remove_uid(uid)
                if removed is not None:
                    changed = True
                    reuse_uid = str(removed.get("uid", ""))
                    source_w = int(removed.get("w", source_w))
                    source_h = int(removed.get("h", source_h))
                    source_button = str(removed.get("button", source_button))
            dst_canvas.add_item(source_button, gx, gy, source_w, source_h, uid=reuse_uid)
            changed = True
        finally:
            self._window_layout_drop_in_progress = False
        if changed or self._window_layout_capture_pending:
            self._capture_window_layout_from_editor()

    def _refresh_window_layout_available_list(self) -> None:
        if not hasattr(self, "window_layout_available_list"):
            return
        show_all = bool(self._window_layout.get("show_all_available", False))
        all_buttons = list(dict.fromkeys(WINDOW_LAYOUT_MAIN_ORDER + WINDOW_LAYOUT_FADE_ORDER))
        if show_all:
            self.window_layout_available_list.set_buttons(all_buttons)
            return
        current = list(self._window_layout.get("available", []))
        used = {
            str(item.get("button", ""))
            for item in [*self.window_layout_main_editor.export_items(), *self.window_layout_fade_editor.export_items()]
            if isinstance(item, dict)
        }
        output: List[str] = []
        for token in current:
            key = str(token).strip()
            if key in all_buttons and key not in used and key not in output:
                output.append(key)
        for key in all_buttons:
            if key not in used and key not in output:
                output.append(key)
        self.window_layout_available_list.set_buttons(output)

    def _on_window_layout_show_all_toggled(self, checked: bool) -> None:
        self._window_layout["show_all_available"] = bool(checked)
        self._refresh_window_layout_available_list()
        self._capture_window_layout_from_editor()

    def _clear_all_window_layout_buttons(self) -> None:
        self.window_layout_main_editor.set_items([])
        self.window_layout_fade_editor.set_items([])
        self._capture_window_layout_from_editor()

    def _confirm_layout_overlap_action(self) -> str:
        box = QMessageBox(self)
        box.setWindowTitle(tr("Button Overlap"))
        box.setText(tr("Destination is already occupied."))
        box.setInformativeText(tr("Choose action:"))
        swap_btn = box.addButton(tr("Swap"), QMessageBox.AcceptRole)
        copy_btn = box.addButton(tr("Copy"), QMessageBox.ActionRole)
        cancel_btn = box.addButton(tr("Cancel"), QMessageBox.RejectRole)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is swap_btn:
            return "swap"
        if clicked is copy_btn:
            return "copy"
        return "cancel"

    def _build_web_remote_url_text(self, port: int) -> str:
        return f"{self._web_remote_url_scheme}://{self._web_remote_url_host}:{port}/"

    @staticmethod
    def _build_web_remote_ws_port_text(port: int) -> str:
        token = int(port)
        if token >= 65535:
            return "Unavailable (choose Web Remote port 65534 or lower)"
        return str(token + 1)

    def _set_web_remote_url_label(self, url: str) -> None:
        self.web_remote_url_value.setText(f'<a href="{url}">{url}</a>')

    def _set_web_remote_ws_port_label(self, ws_port_text: str) -> None:
        self.web_remote_ws_port_value.setText(ws_port_text)

    def _update_web_remote_page_labels(self, port: int) -> None:
        self._set_web_remote_url_label(self._build_web_remote_url_text(port))
        self._set_web_remote_ws_port_label(self._build_web_remote_ws_port_text(port))
        self._set_web_remote_companion_text(port)

    def _set_web_remote_companion_text(self, port: int) -> None:
        host = self._web_remote_url_host
        self.web_remote_companion_setup_value.setText(
            tr("Use the Python SSP module in Companion when linking to pySSP.")
        )
        self.web_remote_companion_ip_value.setText(f"{tr('IP address: ')}{host}")
        self.web_remote_companion_port_value.setText(f"{tr('Port: ')}{port}")
        if int(port) == 5050:
            self.web_remote_companion_default_value.setText(
                tr("If Companion and pySSP are on the same computer, adding the module will usually work with the default settings.")
            )
        else:
            self.web_remote_companion_default_value.setText("")

