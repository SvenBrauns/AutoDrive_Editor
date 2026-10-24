from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem

from autodrive.models import NodeData


class NodeItem(QGraphicsEllipseItem):

    def __init__(
        self,
        node_data: NodeData,
        on_selected: Callable[[NodeData], None] | None = None
    ):
        super().__init__(
            -3,
            -3,
            6,
            6
        )

        self.node_data = node_data
        self.on_selected = on_selected

        self.setPos(
            node_data.x,
            node_data.z
        )

        if node_data.is_regular:
            self.setBrush(
                QBrush(
                    QColor("red")
                )
            )
        else:
            self.setBrush(
                QBrush(
                    QColor("orange")
                )
            )

        self.setPen(
            QPen(Qt.black)
        )

        self.setFlag(
            QGraphicsEllipseItem.ItemIsSelectable
        )

    @property
    def node_id(self) -> int:
        return self.node_data.node_id

    def mousePressEvent(self, event):
        if self.on_selected is not None:
            self.on_selected(
                self.node_data
            )

        super().mousePressEvent(
            event
        )