from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QGraphicsItem


class GraphicsLayerItem(QGraphicsItem):
    """An invisible parent item that groups items into a layer with its own z order."""

    def __init__(self):
        super().__init__()

        self.setFlag(QGraphicsItem.ItemHasNoContents, True)

        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self):
        return QRectF()

    def paint(self, painter, option, widget=None):
        pass
