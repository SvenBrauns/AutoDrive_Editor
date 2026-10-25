"""Starts the editor."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from autodrive_editor.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    # After the window is visible, so the setup dialog appears on top of it.
    QTimer.singleShot(0, window.run_first_start)

    return app.exec()
