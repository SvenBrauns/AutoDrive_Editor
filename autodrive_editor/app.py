"""Starts the editor."""

import ctypes
import sys

from PySide6.QtCore import QLibraryInfo, QTimer, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from autodrive_editor import __version__, i18n
from autodrive_editor.error_log import install_error_handler, logger, setup_logging
from autodrive_editor.paths import APP_ICON_PATH, log_directory
from autodrive_editor.settings.app_settings import AppSettings

APP_NAME = "AutoDrive FS25 Editor"

# Own identity for the Windows taskbar. Without it, the taskbar groups
# the editor under python.exe and shows the Python icon.
WINDOWS_APP_ID = "AutoDriveEditor.FS25"


def run() -> int:
    setup_logging(log_directory())
    logger.info("%s %s started", APP_NAME, __version__)

    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    install_language(app, AppSettings().language)

    # Imported only now, because some UI modules translate their texts
    # when they are imported.
    from autodrive_editor.ui.dialogs.error_dialog import show_unexpected_error
    from autodrive_editor.ui.main_window import MainWindow

    # Before the window is built, so errors while building it are logged too.
    install_error_handler(
        lambda details: show_unexpected_error(QApplication.activeWindow(), details)
    )

    window = MainWindow()
    window.show()

    # After the window is visible, so the setup dialog appears on top of it.
    QTimer.singleShot(0, window.map_import.run_first_start)
    QTimer.singleShot(0, window.files.offer_autosave_restore)

    return app.exec()


def install_language(app: QApplication, language: str):
    """Sets the language of the editor's texts and of Qt's own texts,
    such as the Yes/No/Cancel buttons of message boxes."""

    i18n.set_language(language)

    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)

    if translator.load(f"qtbase_{language}", translations):
        app.installTranslator(translator)
