from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem

from autodrive_editor.terrain.game_picture import PictureGrid


class PictureGridItem(QGraphicsItem):
    """The tiles of the game picture while the refresh tool is on: grid lines and the marked
    tiles filled."""

    # Above the map grid (-900), below the network.
    Z_VALUE = -890.0

    LINE_COLOR = QColor(255, 200, 0, 200)
    FILL_COLOR = QColor(255, 200, 0, 90)

    def __init__(self, grid: PictureGrid):
        super().__init__()

        self.setZValue(self.Z_VALUE)
        self.setAcceptedMouseButtons(Qt.NoButton)

        self.grid = grid
        self.marked: set[tuple[int, int]] = set()
        half = grid.map_size / 2
        self.bounds = QRectF(-half, -half, 2 * half, 2 * half)
        self.pen = QPen(self.LINE_COLOR)
        self.pen.setCosmetic(True)
        self.pen.setWidthF(1.5)

    def boundingRect(self) -> QRectF:
        return self.bounds

    def set_marked(self, marked: set[tuple[int, int]]):
        self.marked = set(marked)
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        for col, row in self.marked:
            painter.fillRect(QRectF(*self.grid.tile_rect(0, col, row)), self.FILL_COLOR)

        start, side = self.bounds.left(), self.grid.tiles_per_side()
        steps = [start + i * self.grid.edge for i in range(side)] + [self.bounds.right()]
        top, bottom = self.bounds.top(), self.bounds.bottom()

        painter.setPen(self.pen)
        painter.drawLines([QLineF(x, top, x, bottom) for x in steps])
        painter.drawLines([QLineF(start, z, self.bounds.right(), z) for z in steps])
