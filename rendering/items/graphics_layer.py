from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QGraphicsItem


class GraphicsLayerItem(QGraphicsItem):

    def __init__(self):
        super().__init__()

        self.setFlag(
            QGraphicsItem.ItemHasNoContents,
            True
        )

        self.setAcceptedMouseButtons(
            Qt.NoButton
        )

    def boundingRect(self):
        return QRectF()

    def paint(
        self,
        painter,
        option,
        widget=None
    ):
        pass