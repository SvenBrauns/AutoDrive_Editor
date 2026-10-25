from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QGraphicsSvgItem


class MarkerItem(QGraphicsSvgItem):
    def __init__(self, svg_path):
        super().__init__(svg_path)

        self.setAcceptedMouseButtons(Qt.NoButton)
