from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from pyssp.i18n import install_auto_localization
from pyssp.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    install_auto_localization(app)
    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow()
    if icon_path.exists():
        win.setWindowIcon(QIcon(str(icon_path)))
    win.show()
    return app.exec_()
