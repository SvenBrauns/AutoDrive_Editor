import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from autodrive_editor import __version__, updates
from autodrive_editor.error_log import logger
from autodrive_editor.i18n import tr
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.messages import inform
from autodrive_editor.ui.dialogs.update_dialog import show_update


class UpdateController(QObject):
    """Checks for a newer version in the background: at startup when the
    setting is on, and from the Help menu."""

    # (release or None, error text or "", started from the menu)
    _checked = Signal(object, str, bool)

    def __init__(self, window: QWidget, settings: AppSettings):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self._checked.connect(self.show_result)

    def check_at_startup(self):
        if self.settings.check_updates:
            self._start(manual=False)

    def check_now(self):
        self._start(manual=True)

    def _start(self, manual: bool):
        # In a thread, so a slow connection does not freeze the editor.
        threading.Thread(target=self._check, args=(manual,), daemon=True).start()

    def _check(self, manual: bool):
        try:
            release = updates.newer_release(updates.fetch_latest_release(), __version__)
        except (OSError, ValueError) as error:
            logger.info("Update check failed: %s", error)
            self._checked.emit(None, str(error), manual)
        else:
            self._checked.emit(release, "", manual)

    def show_result(self, release: updates.Release | None, error: str, manual: bool):
        if release is not None:
            show_update(self.window, release)
        elif not manual:
            return
        elif error:
            inform(self.window, tr("Could not check for updates:\n{error}", error=error))
        else:
            inform(self.window, tr("You have the latest version ({version}).", version=__version__))
