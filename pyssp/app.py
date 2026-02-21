from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QLockFile
from PyQt5.QtGui import QColor, QIcon, QPalette
from PyQt5.QtWidgets import QApplication, QMessageBox

from pyssp.i18n import apply_application_font, install_auto_localization, normalize_language, set_current_language, tr
from pyssp.settings_store import get_settings_path, load_settings, save_settings
from pyssp.ui.main_window import MainWindow

_INSTANCE_LOCK: Optional[QLockFile] = None
_STDOUT_FALLBACK = None
_STDERR_FALLBACK = None
_STDIN_FALLBACK = None


def _force_light_qt_theme(app: QApplication) -> None:
    # Use Fusion + explicit light palette to avoid inheriting OS dark appearance.
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(0, 102, 204))
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def _parse_startup_args(argv: list[str]) -> tuple[list[str], bool, bool]:
    clean_tokens = {"--cleanstart", "/cleanstart"}
    debug_tokens = {"-debug", "--debug", "/debug"}
    cleanstart = False
    debug = False
    filtered = [argv[0]] if argv else [""]
    for arg in argv[1:]:
        token = str(arg or "").strip().lower()
        if token in clean_tokens:
            cleanstart = True
            continue
        if token in debug_tokens:
            debug = True
            continue
        filtered.append(arg)
    return filtered, cleanstart, debug


def _enable_debug_console(enabled: bool) -> None:
    if not enabled or os.name != "nt":
        return
    kernel32 = ctypes.windll.kernel32
    attached = bool(kernel32.AttachConsole(ctypes.c_uint(-1).value))
    if not attached:
        kernel32.AllocConsole()
    try:
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
    except Exception:
        pass
    try:
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
    except Exception:
        pass
    try:
        sys.stdin = open("CONIN$", "r", encoding="utf-8")
    except Exception:
        pass


def _ensure_standard_streams(debug_enabled: bool) -> None:
    global _STDOUT_FALLBACK, _STDERR_FALLBACK, _STDIN_FALLBACK
    if debug_enabled:
        return
    try:
        if sys.stdout is None:
            _STDOUT_FALLBACK = open(os.devnull, "w", encoding="utf-8", buffering=1)
            sys.stdout = _STDOUT_FALLBACK
    except Exception:
        pass
    try:
        if sys.stderr is None:
            _STDERR_FALLBACK = open(os.devnull, "w", encoding="utf-8", buffering=1)
            sys.stderr = _STDERR_FALLBACK
    except Exception:
        pass
    try:
        if sys.stdin is None:
            _STDIN_FALLBACK = open(os.devnull, "r", encoding="utf-8")
            sys.stdin = _STDIN_FALLBACK
    except Exception:
        pass


def _apply_cleanstart() -> bool:
    settings_path = get_settings_path()
    if not settings_path.exists():
        return True
    try:
        os.remove(settings_path)
        return True
    except Exception as exc:
        QMessageBox.critical(
            None,
            tr("Cleanstart Failed"),
            f"{tr('Could not remove settings.ini for cleanstart.')}\n\n"
            f"{exc}",
        )
        return False


def _acquire_single_instance_lock() -> bool:
    global _INSTANCE_LOCK
    lock_path = str(Path(tempfile.gettempdir()) / "pyssp.instance.lock")
    lock = QLockFile(lock_path)
    lock.setStaleLockTime(30_000)
    if lock.tryLock(0):
        _INSTANCE_LOCK = lock
        return True
    QMessageBox.critical(
        None,
        tr("pySSP Already Running"),
        f"{tr('Another instance of pySSP is already running.')}\n\n"
        f"{tr('Close the existing instance, then launch pySSP again.')}",
    )
    return False


def _is_process_running(image_name: str) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except Exception:
        return False
    output = (result.stdout or "").strip().lower()
    return bool(output) and "no tasks are running" not in output and image_name.lower() in output


def _confirm_sports_sounds_pro_warning() -> bool:
    if not _is_process_running("SportsSoundsPro.exe"):
        return True
    box = QMessageBox()
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(tr("SportsSoundsPro Detected"))
    box.setText(
        f"{tr('pySSP and SportsSoundsPro are both working on .set files, which might cause issues.')}\n\n"
        f"{tr('Choose Quit to close pySSP now, or Continue to run both.')}"
    )
    quit_button = box.addButton(tr("Quit"), QMessageBox.RejectRole)
    box.addButton(tr("Continue"), QMessageBox.AcceptRole)
    box.setDefaultButton(quit_button)
    box.exec_()
    return box.clickedButton() is not quit_button


def _prompt_first_run_language() -> str:
    box = QMessageBox()
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle("Select Language / 选择语言")
    box.setText("Choose your UI language.\n请选择界面语言。")
    english_button = box.addButton("English", QMessageBox.AcceptRole)
    chinese_button = box.addButton("简体中文", QMessageBox.AcceptRole)
    box.setDefaultButton(english_button)
    box.exec_()
    if box.clickedButton() is chinese_button:
        return "zh_cn"
    return "en"


def _confirm_cleanstart_warning() -> bool:
    answer = QMessageBox.warning(
        None,
        tr("Cleanstart Warning"),
        tr("Cleanstart will reset all settings to defaults. Continue?"),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return answer == QMessageBox.Yes


def _resolve_startup_language(preferred_if_missing: Optional[str] = None) -> str:
    settings_path = get_settings_path()
    if not settings_path.exists():
        selected_language = normalize_language(preferred_if_missing or _prompt_first_run_language())
        settings = load_settings()
        settings.ui_language = selected_language
        save_settings(settings)
        return selected_language
    settings = load_settings()
    return normalize_language(getattr(settings, "ui_language", "en"))


def main() -> int:
    qt_argv, cleanstart_requested, debug_requested = _parse_startup_args(list(sys.argv))
    _enable_debug_console(debug_requested)
    _ensure_standard_streams(debug_requested)
    app = QApplication(qt_argv)
    _force_light_qt_theme(app)
    install_auto_localization(app)
    preferred_language: Optional[str] = None
    if cleanstart_requested:
        preferred_language = normalize_language(_prompt_first_run_language())
        set_current_language(preferred_language)
        apply_application_font(app, preferred_language)
        if not _confirm_cleanstart_warning():
            return 0
        if not _apply_cleanstart():
            return 1
    try:
        startup_language = _resolve_startup_language(preferred_if_missing=preferred_language)
    except Exception:
        startup_language = "en"
    set_current_language(startup_language)
    apply_application_font(app, startup_language)
    if not _acquire_single_instance_lock():
        return 1
    if not _confirm_sports_sounds_pro_warning():
        return 0
    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow()
    if icon_path.exists():
        win.setWindowIcon(QIcon(str(icon_path)))
    win.show()
    return app.exec_()
