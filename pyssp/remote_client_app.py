from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtGui import QColor, QIcon, QPalette
from PyQt5.QtWidgets import QApplication

from pyssp.i18n import apply_application_font, install_auto_localization, set_current_language
from pyssp.remote_client_settings import load_remote_client_settings
from pyssp.ui.remote_display_client import RemoteDisplayClientWindow


def _force_light_qt_theme(app: QApplication) -> None:
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
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)


def main(argv: list[str] | None = None) -> int:
    app = QApplication(list(sys.argv if argv is None else argv))
    _force_light_qt_theme(app)
    install_auto_localization(app)
    load_remote_client_settings()
    set_current_language("en")
    apply_application_font(app, "en")
    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.ico"
    icon = QIcon(str(icon_path))
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = RemoteDisplayClientWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    return app.exec_()
