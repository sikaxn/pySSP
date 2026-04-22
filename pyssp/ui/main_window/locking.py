from __future__ import annotations

from .shared import *
from .constants import *
from .helpers import *
from .widgets import *


class LockingMixin:
    def _is_playback_in_progress(self) -> bool:
        if self.player.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            return True
        if self.player_b.state() in {
            ExternalMediaPlayer.PlayingState,
            ExternalMediaPlayer.PausedState,
        }:
            return True
        for extra in self._multi_players:
            if extra.state() in {ExternalMediaPlayer.PlayingState, ExternalMediaPlayer.PausedState}:
                return True
        return False

    def _is_locked_input_allowed(self, source: str) -> bool:
        if not self._ui_locked:
            return True
        token = str(source or "").strip().lower()
        if token == "lock_toggle":
            return True
        if self._automation_locked:
            if token == "midi":
                return bool(self.lock_auto_allow_midi_control)
            return False
        if token == "system":
            return bool(self.lock_allow_system_hotkeys)
        if token == "quick_action":
            return bool(self.lock_allow_quick_action_hotkeys and self.quick_action_enabled)
        if token == "sound_button":
            return bool(self.lock_allow_sound_button_hotkeys and self.sound_button_hotkey_enabled)
        if token == "midi":
            return bool(self.lock_allow_midi_control)
        return False

    def _run_locked_input(self, source: str, handler: Callable[[], None]) -> None:
        if not self._is_locked_input_allowed(source):
            return
        handler()

    def _handle_lock_overlay_key_press(self, event) -> None:
        if event.isAutoRepeat():
            return
        if not self._is_locked_input_allowed("system"):
            return
        key = int(event.key())
        handlers = self._modifier_hotkey_handlers.get(key)
        if handlers and key not in self._modifier_hotkey_down:
            self._modifier_hotkey_down.add(key)
            for handler in handlers:
                handler()

    def _handle_lock_overlay_key_release(self, event) -> None:
        key = int(event.key())
        if key in self._modifier_hotkey_down:
            self._modifier_hotkey_down.discard(key)

    def _hotkey_lock_toggle(self) -> None:
        if self._ui_locked:
            self._attempt_unlock_from_hotkey()
            return
        self._engage_lock_screen()

    def _toggle_lock_screen(self) -> None:
        if self._ui_locked:
            return
        self._engage_lock_screen()

    def _engage_lock_screen(self, automation: bool = False) -> None:
        if self._ui_locked and self._automation_locked == bool(automation):
            return
        self._ui_locked = True
        self._automation_locked = bool(automation)
        self._modifier_hotkey_down.clear()
        if self._lock_screen_overlay is not None:
            self._lock_screen_overlay.activate_lock()
        self._sync_lock_ui_state()
        status = tr("Automation lock is active.") if self._automation_locked else tr("Lock screen is active.")
        self.statusBar().showMessage(status, 2500)

    def _attempt_unlock_from_overlay(self) -> None:
        if self._automation_locked:
            if not self._prompt_unlock_phrase(
                phrase="sure to unlock",
                message=tr("Type sure to unlock and press Enter to unlock remote automation control."),
                error_text=tr("Type sure to unlock to continue."),
                require_password=bool(self.lock_require_password and self.lock_password),
            ):
                if self._lock_screen_overlay is not None:
                    self._lock_screen_overlay.reset_unlock_progress()
                return
            self._release_lock_screen()
            return
        if self.lock_require_password:
            if not self._prompt_unlock_credentials(require_keyword=False):
                if self._lock_screen_overlay is not None:
                    self._lock_screen_overlay.reset_unlock_progress()
                return
        self._release_lock_screen()

    def _attempt_unlock_from_hotkey(self) -> None:
        if self._automation_locked:
            if not self._prompt_unlock_phrase(
                phrase="sure to unlock",
                message=tr("Type sure to unlock and press Enter to unlock remote automation control."),
                error_text=tr("Type sure to unlock to continue."),
                require_password=bool(self.lock_require_password and self.lock_password),
            ):
                return
            self._release_lock_screen()
            return
        require_keyword = not bool(self.lock_require_password and self.lock_password)
        if not self._prompt_unlock_credentials(require_keyword=require_keyword):
            return
        self._release_lock_screen()

    def _prompt_unlock_credentials(self, require_keyword: bool) -> bool:
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Unlock pySSP"))
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        if require_keyword:
            message = tr("Type unlock and press Enter to unlock.")
        elif self.lock_require_password:
            message = tr("Enter password and press Enter to unlock.")
        else:
            message = tr("Press Enter to unlock.")
        if self.lock_require_password and require_keyword:
            message += "\n" + tr("Password is also required.")
        note = QLabel(message, dialog)
        note.setWordWrap(True)
        layout.addWidget(note)
        keyword_edit: Optional[QLineEdit] = None
        if require_keyword:
            keyword_edit = QLineEdit(dialog)
            keyword_edit.setPlaceholderText("unlock")
            layout.addWidget(keyword_edit)
        password_edit: Optional[QLineEdit] = None
        if self.lock_require_password:
            password_edit = QLineEdit(dialog)
            password_edit.setEchoMode(QLineEdit.Password)
            password_edit.setPlaceholderText(tr("Password"))
            layout.addWidget(password_edit)
        warning = QLabel("", dialog)
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#B00020; font-weight:bold;")
        warning.setVisible(False)
        layout.addWidget(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        layout.addWidget(buttons)

        def submit() -> None:
            if require_keyword and keyword_edit is not None and keyword_edit.text().strip().lower() != "unlock":
                warning.setText(tr("Type unlock to continue."))
                warning.setVisible(True)
                return
            if self.lock_require_password and password_edit is not None and password_edit.text() != self.lock_password:
                warning.setText(tr("Password is incorrect."))
                warning.setVisible(True)
                return
            dialog.accept()

        buttons.accepted.connect(submit)
        buttons.rejected.connect(dialog.reject)
        if keyword_edit is not None:
            keyword_edit.returnPressed.connect(submit)
            keyword_edit.setFocus()
        elif password_edit is not None:
            password_edit.returnPressed.connect(submit)
            password_edit.setFocus()
        if password_edit is not None and keyword_edit is not None:
            password_edit.returnPressed.connect(submit)
        return dialog.exec_() == QDialog.Accepted

    def _prompt_unlock_phrase(self, phrase: str, message: str, error_text: str, require_password: bool = False) -> bool:
        target = str(phrase or "").strip().lower()
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Unlock pySSP"))
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        prompt_message = str(message or "")
        if require_password:
            prompt_message += "\n" + tr("Password is also required.")
        note = QLabel(prompt_message, dialog)
        note.setWordWrap(True)
        layout.addWidget(note)
        text_edit = QLineEdit(dialog)
        text_edit.setPlaceholderText(target)
        layout.addWidget(text_edit)
        password_edit: Optional[QLineEdit] = None
        if require_password:
            password_edit = QLineEdit(dialog)
            password_edit.setEchoMode(QLineEdit.Password)
            password_edit.setPlaceholderText(tr("Password"))
            layout.addWidget(password_edit)
        warning = QLabel("", dialog)
        warning.setWordWrap(True)
        warning.setStyleSheet("color:#B00020; font-weight:bold;")
        warning.setVisible(False)
        layout.addWidget(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        layout.addWidget(buttons)

        def submit() -> None:
            if text_edit.text().strip().lower() != target:
                warning.setText(error_text)
                warning.setVisible(True)
                return
            if require_password and password_edit is not None and password_edit.text() != self.lock_password:
                warning.setText(tr("Password is incorrect."))
                warning.setVisible(True)
                return
            dialog.accept()

        buttons.accepted.connect(submit)
        buttons.rejected.connect(dialog.reject)
        text_edit.returnPressed.connect(submit)
        if password_edit is not None:
            password_edit.returnPressed.connect(submit)
        text_edit.setFocus()
        return dialog.exec_() == QDialog.Accepted

    def _release_lock_screen(self, force: bool = False) -> None:
        if not self._ui_locked:
            return
        was_automation_locked = self._automation_locked
        self._ui_locked = False
        self._automation_locked = False
        self._modifier_hotkey_down.clear()
        if self._lock_screen_overlay is not None:
            self._lock_screen_overlay.deactivate_lock()
        self._sync_lock_ui_state()
        status = tr("Automation lock released.") if was_automation_locked else tr("Lock screen released.")
        if force and was_automation_locked:
            status = tr("Automation lock released by Web Remote.")
        self.statusBar().showMessage(status, 2500)

    def _sync_lock_ui_state(self) -> None:
        if self.lock_screen_button is not None:
            self.lock_screen_button.setChecked(self._ui_locked)
            self.lock_screen_button.setToolTip(
                tr("Lock Screen") if not self._ui_locked else tr("Click the 3 targets to unlock.")
            )
        system_actions_enabled = (not self._ui_locked) or bool(self.lock_allow_system_hotkeys)
        for key in ["new_set", "open_set", "save_set", "save_set_as", "search", "options"]:
            action = self._menu_actions.get(key)
            if action is not None:
                action.setEnabled(system_actions_enabled)
