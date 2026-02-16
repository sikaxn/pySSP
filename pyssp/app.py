from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from pyssp.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()

