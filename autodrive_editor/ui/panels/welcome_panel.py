from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from autodrive_editor.i18n import tr
from autodrive_editor.paths import APP_ICON_PATH
from autodrive_editor.settings.recent_items import RecentItem


class WelcomePanel(QWidget):
    """Shown on the empty map until a route is loaded. Offers the
    open actions as buttons and the recently opened files."""

    ICON_SIZE = 96

    recent_item_requested = Signal(object)

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
        # A font instead of a style sheet, so the text color follows a theme change.
        title_font = title.font()
        title_font.setPixelSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
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

        layout.addSpacing(16)

        self.recent_title = QLabel(tr("Recently opened"), self)
        self.recent_title.setAlignment(Qt.AlignCenter)
        recent_font = self.recent_title.font()
        recent_font.setBold(True)
        self.recent_title.setFont(recent_font)
        layout.addWidget(self.recent_title)

        self.recent_list = QWidget(self)
        self.recent_layout = QVBoxLayout(self.recent_list)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_layout.setSpacing(2)
        layout.addWidget(self.recent_list, alignment=Qt.AlignCenter)

        self.set_recent_items([])

    def set_recent_items(self, items: list[RecentItem]):
        while self.recent_layout.count():
            self.recent_layout.takeAt(0).widget().deleteLater()

        for item in items:
            button = QPushButton(item.label, self.recent_list)
            button.setFlat(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(item.path)
            button.clicked.connect(
                lambda checked=False, item=item: self.recent_item_requested.emit(item)
            )
            self.recent_layout.addWidget(button)

        self.recent_title.setVisible(bool(items))
        self.recent_list.setVisible(bool(items))
