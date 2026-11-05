from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG, SUBPRIO_FLAG


class ConnectOptionsWidget(QWidget):
    """Type of the nodes the Connect tool adds on free ground or in a connection."""

    def __init__(self, set_flag, parent=None):
        super().__init__(parent)

        self.flag_box = QComboBox(self)
        self.flag_box.setToolTip(tr("Type of the new nodes"))
        self.flag_box.addItem("Regular", REGULAR_FLAG)
        self.flag_box.addItem("Subprio", SUBPRIO_FLAG)
        self.flag_box.currentIndexChanged.connect(lambda: set_flag(self.flag_box.currentData()))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(tr("Node type"), self))
        layout.addWidget(self.flag_box)
        layout.addStretch(1)
