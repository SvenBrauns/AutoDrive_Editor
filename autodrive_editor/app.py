"""Starts the editor."""

import ctypes
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from autodrive_editor.paths import APP_ICON_PATH
from autodrive_editor.ui.main_window import MainWindow

APP_NAME = "AutoDrive FS25 Editor"

# Own identity for the Windows taskbar. Without it, the taskbar groups
# the editor under python.exe and shows the Python icon.
WINDOWS_APP_ID = "AutoDriveEditor.FS25"


def run() -> int:
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    window = MainWindow()
    window.show()

    # After the window is visible, so the setup dialog appears on top of it.
    QTimer.singleShot(0, window.run_first_start)
    QTimer.singleShot(0, window.offer_autosave_restore)

    return app.exec()
