from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem

from autodrive_editor.model.autodrive_data import NodeData
from autodrive_editor.rendering.display_style import DisplayStyle


class NodeSelectionItem(QGraphicsEllipseItem):
    def __init__(self, node_data: NodeData, display_style: DisplayStyle):
        node_diameter = display_style.node_diameter

        node_radius = node_diameter / 2

        super().__init__(-node_radius, -node_radius, node_diameter, node_diameter)

        if node_data.is_regular:
            node_color = QColor("red")

        else:
            node_color = QColor("orange")

        self.setBrush(QBrush(node_color))

        selection_pen = QPen(Qt.white)

        selection_pen.setWidthF(display_style.selected_node_ring_width)

        self.setPen(selection_pen)

        self.setPos(node_data.x, node_data.z)

        self.setAcceptedMouseButtons(Qt.NoButton)
