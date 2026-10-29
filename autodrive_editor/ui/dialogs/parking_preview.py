from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QWidget,
)

from autodrive_editor.editing.parking_layout import (
    SIDE_CORNERS,
    ParkingMode,
    ParkingNetwork,
    ParkingSettings,
    ShedFrame,
    bay_centers,
    bay_width,
    marker_depth,
    side_angle,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.i18n import tr
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.ui.dialogs.parking_painting import MARKER_COLOR, arrow_head, paint_connection

SIDE_NAMES = {"front": tr("Front"), "back": tr("Back"), "left": tr("Left"), "right": tr("Right")}

COMPASS_NAMES = (
    tr("north"),
    tr("north-east"),
    tr("east"),
    tr("south-east"),
    tr("south"),
    tr("south-west"),
    tr("west"),
    tr("north-west"),
)


def compass_name(angle: float) -> str:
    return COMPASS_NAMES[round(angle / 45) % 8]


class ParkingPreview(QWidget):
    """Top view of the shed with the open side at the bottom, and the network to be created.
    Walls, offset strips and gaps can be clicked to edit them, side labels to open that side."""

    side_clicked = Signal(str)
    # "left", "right", "back" or the index of a gap, and where the click was on the screen.
    length_clicked = Signal(object, QPoint)

    MARGIN_PX = 16
    # Room around the shed for the side labels, and on the right for the north arrow.
    LABEL_WIDTH_PX = 80
    LABEL_HEIGHT_PX = 32
    NORTH_PX = 48
    # Walls and gaps narrower than this on screen are widened for clicking.
    CLICK_PX = 8
    NODE_PX = 4
    MARKER_PX = 8
    ARROW_PX = 7

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(480, 400)
        self.setMouseTracking(True)

        self.area: IndoorArea | None = None
        self.frame: ShedFrame | None = None
        self.settings: ParkingSettings | None = None
        self.network: ParkingNetwork | None = None

    def show_plan(self, area: IndoorArea, frame: ShedFrame, settings: ParkingSettings, network):
        self.area, self.frame, self.settings, self.network = area, frame, settings, network
        self.update()

    def side_labels(self) -> dict[str, QRectF]:
        """Where the label of each side is drawn."""

        frame, to_screen = self.frame, self._transform()
        top_left = to_screen(0, frame.depth)
        bottom_right = to_screen(frame.length, 0)
        middle = (top_left + bottom_right) / 2
        width, height = self.LABEL_WIDTH_PX, self.LABEL_HEIGHT_PX
        rectangles = {
            "bottom": QRectF(middle.x() - width, self.height() - height, 2 * width, height),
            "top": QRectF(middle.x() - width, top_left.y() - height, 2 * width, height),
            "left": QRectF(top_left.x() - width - 4, middle.y() - height / 2, width, height),
            "right": QRectF(bottom_right.x() + 4, middle.y() - height / 2, width, height),
        }

        return {side: rectangles[self._screen_side(side)] for side in SIDE_CORNERS}

    def length_areas(self) -> list[tuple[object, QRectF]]:
        """Clickable areas of the gaps and of the walls with their offset strips."""

        frame, settings, to_screen = self.frame, self.settings, self._transform()
        width = bay_width(frame, settings)
        areas = []

        def area(key, a1, d1, a2, d2, widen_a=0, widen_d=0):
            rectangle = QRectF(to_screen(a1, d1), to_screen(a2, d2)).normalized()
            extra_x = max(0.0, (self.CLICK_PX - rectangle.width()) / 2) if widen_a else 0.0
            extra_y = max(0.0, (self.CLICK_PX - rectangle.height()) / 2) if widen_d else 0.0
            areas.append((key, rectangle.adjusted(-extra_x, -extra_y, extra_x, extra_y)))

        if width > 0:
            for index, center in enumerate(bay_centers(frame, settings)[:-1]):
                start = center + width / 2
                area(index, start, 0, start + settings.gaps[index], frame.depth, widen_a=1)

        area("left", 0, 0, settings.left_offset, frame.depth, widen_a=1)
        area("right", frame.length - settings.right_offset, 0, frame.length, frame.depth, 1)
        area("back", 0, marker_depth(frame, settings), frame.length, frame.depth, widen_d=1)

        return areas

    def mousePressEvent(self, event):
        if self.frame is None or event.button() != Qt.LeftButton:
            return

        key = self._clickable(event.position())

        if key is None:
            return

        if key in SIDE_CORNERS:
            self.side_clicked.emit(key)
        else:
            self.length_clicked.emit(key[0], event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.frame is not None:
            clickable = self._clickable(event.position()) is not None
            self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    def _clickable(self, position: QPointF):
        """The side of a clicked label, or (key,) of a clicked length area."""

        for side, rectangle in self.side_labels().items():
            if side != self.settings.open_side and rectangle.contains(position):
                return side

        for key, rectangle in self.length_areas():
            if rectangle.contains(position):
                return (key,)

        return None

    def paintEvent(self, event):
        if self.frame is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())

        frame, settings = self.frame, self.settings
        style = DisplayStyle()
        to_screen = self._transform()

        # Shed and bays.
        shed_color = QColor(*style.shed_color)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*style.shed_color, style.shed_fill_alpha))
        painter.drawPolygon(self._rectangle(to_screen, 0, 0, frame.length, frame.depth))

        width = bay_width(frame, settings)

        if width > 0:
            painter.setBrush(QColor(*style.shed_color, 2 * style.shed_fill_alpha))

            for center in bay_centers(frame, settings):
                bay = self._rectangle(to_screen, center - width / 2, 0, width, frame.depth)
                painter.drawPolygon(bay)

        # Walls: the open side (and the exit side when driving through) is dashed.
        corners = [to_screen(a, d) for a, d in ((0, 0), (frame.length, 0))]
        corners += [to_screen(a, d) for a, d in ((frame.length, frame.depth), (0, frame.depth))]
        exit_open = settings.mode == ParkingMode.DRIVE_THROUGH

        for index in range(4):
            is_open = index == 0 or (index == 2 and exit_open)
            pen = QPen(shed_color, 1.5 if is_open else 3, Qt.DashLine if is_open else Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(corners[index], corners[(index + 1) % 4])

        if self.network is not None:
            self._paint_network(painter, to_screen, style)

        self._paint_side_labels(painter)
        self._paint_north(painter)

        painter.end()

    def _paint_network(self, painter, to_screen, style):
        network = self.network
        points = [to_screen(a, d) for a, d in network.points]

        for source, target, connection_type in network.connections:
            paint_connection(painter, points[source], points[target], connection_type, style)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*style.subprio_node_color))

        for point in points:
            painter.drawEllipse(point, self.NODE_PX / 2, self.NODE_PX / 2)

        painter.setBrush(MARKER_COLOR)

        for index, _ in network.markers:
            painter.drawEllipse(points[index], self.MARKER_PX / 2, self.MARKER_PX / 2)

    def _paint_side_labels(self, painter):
        font = painter.font()

        for side, rectangle in self.side_labels().items():
            is_open = side == self.settings.open_side
            font.setBold(is_open)
            painter.setFont(font)
            painter.setPen(self.palette().text().color())
            compass = compass_name(side_angle(self.area, side))
            text = f"{SIDE_NAMES[side]}\n({compass})"
            painter.drawText(rectangle, Qt.AlignCenter, text)

        font.setBold(False)
        painter.setFont(font)

    def _paint_north(self, painter):
        """Arrow pointing to the top of the map, so the sides can be found on the map."""

        a, d = self.frame.map_direction(0, -1)
        direction = QPointF(a, -d)
        center = QPointF(self.width() - 28, 28)
        tip = center + direction * 14

        painter.setPen(QPen(self.palette().text().color(), 1.5))
        painter.drawLine(center - direction * 14, tip)
        painter.setBrush(self.palette().text().color())
        painter.drawPolygon(arrow_head(center, tip, self.ARROW_PX))
        painter.drawText(QRectF(center.x() - 30, center.y() + 14, 60, 16), Qt.AlignCenter, tr("N"))

    def _screen_side(self, side: str) -> str:
        """Where a side of the building is in the view: "bottom" is the open side."""

        corners = self.area.corners
        start, end = (corners[index] for index in SIDE_CORNERS[side])
        x, z = ((start[i] + end[i]) / 2 - self.frame.origin[i] for i in range(2))
        a, d = self.frame.map_direction(x, z)

        if d < self.frame.depth / 4:
            return "bottom"

        if d > self.frame.depth * 3 / 4:
            return "top"

        return "left" if a < self.frame.length / 2 else "right"

    def _transform(self):
        """Function from (a, d) to screen, fitting the shed and the network into the widget."""

        frame = self.frame
        points = [(0.0, 0.0), (frame.length, frame.depth)]

        if self.network is not None:
            points += self.network.points

        min_a = min(a for a, _ in points)
        max_a = max(a for a, _ in points)
        min_d = min(d for _, d in points)
        max_d = max(d for _, d in points)

        side_x = self.MARGIN_PX + self.LABEL_WIDTH_PX
        side_y = self.MARGIN_PX + self.LABEL_HEIGHT_PX
        scale = min(
            (self.width() - 2 * side_x - self.NORTH_PX) / max(max_a - min_a, 1.0),
            (self.height() - 2 * side_y) / max(max_d - min_d, 1.0),
        )
        offset_x = (self.width() - self.NORTH_PX - (max_a - min_a) * scale) / 2
        offset_y = (self.height() - (max_d - min_d) * scale) / 2

        def to_screen(a: float, d: float) -> QPointF:
            return QPointF(offset_x + (a - min_a) * scale, offset_y + (max_d - d) * scale)

        return to_screen

    @staticmethod
    def _rectangle(to_screen, a, d, length, depth) -> QPolygonF:
        corners = ((a, d), (a + length, d), (a + length, d + depth), (a, d + depth))

        return QPolygonF([to_screen(*corner) for corner in corners])
