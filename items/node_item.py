from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtCore import Qt


class NodeItem(QGraphicsEllipseItem):

    def __init__(self, index, x, y, z, flag, main_window):

        self.index = index
        self.flag = flag
        self.x_coord = x
        self.y_coord = y
        self.z_coord = z
        self.main_window = main_window

        super().__init__(-3, -3, 6, 6)

        self.setPos(x, z)

        if self.flag == 0:
            self.setBrush(QBrush(QColor("red")))
        else:
            self.setBrush(QBrush(QColor("orange")))

        self.setPen(QPen(Qt.black))

        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable)

    def mousePressEvent(self, event):

        self.main_window.show_node_info(self)

        super().mousePressEvent(event)