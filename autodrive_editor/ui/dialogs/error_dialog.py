from PySide6.QtWidgets import QMessageBox

from autodrive_editor.i18n import tr
from autodrive_editor.ui.dialogs.help_dialogs import open_log_folder
from autodrive_editor.ui.dialogs.messages import APP_TITLE

# Errors raised while the dialog is open are only logged, so they do not
# stack up dialogs.
_dialog_open = False


def create_error_box(parent, details: str) -> QMessageBox:
    """Short message, the traceback under "Show Details" and a button that
    opens the log folder."""

    box = QMessageBox(
        QMessageBox.Critical, APP_TITLE, tr("An unexpected error occurred."), QMessageBox.Ok, parent
    )
    box.setInformativeText(
        tr(
            "The editor keeps running. If it behaves oddly, save your work and restart it. "
            "The details are also in the log file."
        )
    )
    box.setDetailedText(details)
    box.addButton(tr("Open log folder"), QMessageBox.ActionRole).clicked.connect(open_log_folder)

    return box


def show_unexpected_error(parent, details: str):
    global _dialog_open

    if _dialog_open:
        return

    _dialog_open = True

    try:
        create_error_box(parent, details).exec()
    finally:
        _dialog_open = False
