from typing import Any

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from autodrive_editor.i18n import tr
from autodrive_editor.ui.panels.open_screen import OpenLists, OpenScreen


class OpenDialog(QDialog):
    """File → Open… while a file is open: the Open screen with a Cancel button. "Open other
    file…" ends the dialog with BROWSE."""

    BROWSE = 2

    def __init__(self, lists: OpenLists, parent=None):
        super().__init__(parent)

        self.setWindowTitle(tr("Open"))
        self.resize(760, 520)

        self.open_screen = OpenScreen(self)
        self.open_screen.set_lists(lists)
        self.open_screen.chosen.connect(lambda value: self.accept())
        self.open_screen.browse_requested.connect(lambda: self.done(self.BROWSE))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.open_screen, 1)
        layout.addWidget(buttons)

    @property
    def chosen_value(self) -> Any:
        return self.open_screen.chosen_value
