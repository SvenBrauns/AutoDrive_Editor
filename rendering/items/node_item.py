from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPen
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem
)

from autodrive.models import NodeData
from rendering.display_style import DisplayStyle


class NodeItem(QGraphicsEllipseItem):

    def __init__(
        self,
        node_data: NodeData,
        display_style: DisplayStyle
    ):
        self.display_style = display_style

        diameter = (
            self.display_style.node_diameter
        )

        radius = diameter / 2

        super().__init__(
            -radius,
            -radius,
            diameter,
            diameter
        )

        self.node_data = node_data

        self.setPos(
            node_data.x,
            node_data.z
        )

        if node_data.is_regular:
            node_color = QColor(
                "red"
            )

        else:
            node_color = QColor(
                "orange"
            )

        self.setBrush(
            QBrush(
                node_color
            )
        )

        node_pen = QPen(
            Qt.black
        )

        node_pen.setWidthF(
            self.display_style.node_border_width
        )

        self.setPen(
            node_pen
        )

        self.setAcceptedMouseButtons(
            Qt.LeftButton
        )

    @property
    def node_id(self) -> int:
        return self.node_data.node_id

    