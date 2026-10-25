"""Starts the editor."""

import sys

from PySide6.QtWidgets import QApplication

from autodrive_editor.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    return app.exec()
