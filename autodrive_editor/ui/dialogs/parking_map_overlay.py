from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QGraphicsItem

from autodrive_editor.editing.parking_layout import ParkingNetwork, ShedFrame
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.ui.dialogs.parking_painting import MARKER_COLOR, paint_connection
from autodrive_editor.ui.dialogs.parking_preview import ParkingPreview


class ParkingMapOverlay(QGraphicsItem):
    """The planned parking spots on the map while the dialog is open, drawn translucent and in
    screen pixels like the dialog's top view."""

    Z_VALUE = 1000.0
    OPACITY = 0.75
    # Room around the nodes for the node dots and arrows, in metres.
    MARGIN = 3.0

    def __init__(self, display_style: DisplayStyle, parent=None):
        super().__init__(parent)

        self.display_style = display_style
        self.network: ParkingNetwork | None = None
        self.points: list[QPointF] = []

        self.setZValue(self.Z_VALUE)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def set_plan(self, frame: ShedFrame, network: ParkingNetwork | None):
        """Shows the network in the frame's shed; None hides it."""

        self.prepareGeometryChange()
        self.network = network
        self.points = (
            [] if network is None else [QPointF(*frame.to_map(*p)) for p in network.points]
        )
        self.update()

    def boundingRect(self) -> QRectF:
        if not self.points:
            return QRectF()

        bounds = QPolygonF(self.points).boundingRect()

        return bounds.adjusted(-self.MARGIN, -self.MARGIN, self.MARGIN, self.MARGIN)

    def paint(self, painter: QPainter, option, widget=None):
        if self.network is None:
            return

        to_screen = painter.worldTransform()
        points = [to_screen.map(point) for point in self.points]

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setOpacity(self.OPACITY)

        for source, target, connection_type in self.network.connections:
            paint_connection(
                painter, points[source], points[target], connection_type, self.display_style
            )

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*self.display_style.subprio_node_color))

        for point in points:
            painter.drawEllipse(point, ParkingPreview.NODE_PX / 2, ParkingPreview.NODE_PX / 2)

        painter.setBrush(MARKER_COLOR)

        for index, _ in self.network.markers:
            size = ParkingPreview.MARKER_PX / 2
            painter.drawEllipse(points[index], size, size)

        painter.restore()
