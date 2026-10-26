from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from autodrive_editor.i18n import tr
from autodrive_editor.paths import APP_ICON_PATH


class WelcomePanel(QWidget):
    """Shown on the empty map until a route is loaded. Offers the
    open actions as buttons."""

    ICON_SIZE = 96

    def __init__(self, open_actions: list[QAction], parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        icon_label = QLabel(self)
        icon_label.setPixmap(
            QIcon(str(APP_ICON_PATH)).pixmap(QSize(self.ICON_SIZE, self.ICON_SIZE))
        )
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel("AutoDrive FS25 Editor", self)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel(tr("Open a route, a savegame or an XML file to get started."), self)
        hint.setAlignment(Qt.AlignCenter)
        hint.setEnabled(False)
        layout.addWidget(hint)

        layout.addSpacing(8)

        for action in open_actions:
            button = QPushButton(action.text(), self)
            button.setMinimumWidth(220)
            button.setMinimumHeight(34)
            button.clicked.connect(action.trigger)
            layout.addWidget(button, alignment=Qt.AlignCenter)
