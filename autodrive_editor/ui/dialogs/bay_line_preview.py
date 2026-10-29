import math
from dataclasses import replace

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget,
)

from autodrive_editor.editing.parking_layout import (
    ENTRY_BRANCH_BACK,
    ENTRY_LINE_INSIDE,
    EXIT_BRANCH_ALONG,
    EXIT_LINE_OUTSIDE,
    BayLine,
    ParkingSettings,
    ShedFrame,
    marker_depth,
)
from autodrive_editor.i18n import tr
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.ui.dialogs.parking_painting import MARKER_COLOR, paint_connection


class BayLinePreview(QWidget):
    """Side view of one bay line, outward to the right. Back in: segments can be clicked to edit
    their length, "+" splits a segment, a clicked node is deleted with Delete, and the entry and
    exit branches are dragged to another node. Drive through: shown only."""

    line_changed = Signal(object)
    # "segment" or "turn", its index, and where the click was on the screen.
    length_clicked = Signal(str, int, QPoint)

    MARGIN_PX = 24
    HEIGHT_PX = 150
    NODE_PX = 6
    MARKER_PX = 10
    ARROW_PX = 7
    PLUS_PX = 12
    # The "+" buttons sit this far above the line.
    PLUS_ABOVE_PX = 18
    HANDLE_PX = 10
    CLICK_PX = 7
    WALL_HALF_PX = 40

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(self.HEIGHT_PX)
        self.setMinimumWidth(480)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setMouseTracking(True)

        self.frame: ShedFrame | None = None
        self.settings: ParkingSettings | None = None
        self.line: BayLine | None = None
        # Drive through: the depths of the nodes and the index of the marker.
        self.depths: list[float] = []
        self.marker = 0
        self.selected: int | None = None
        # "entry" or "exit" while a branch is dragged.
        self.dragging: str | None = None

    def clear(self):
        self.frame = None
        self.update()

    def show_bay_line(self, frame: ShedFrame, settings: ParkingSettings, line: BayLine):
        self.frame, self.settings, self.line = frame, settings, line
        marker_d = marker_depth(frame, settings)
        self.depths = [marker_d - distance for distance in line.distances]
        self.marker = 0

        if self.selected is not None and self.selected > len(line.segments):
            self.selected = None

        self.update()

    def show_drive_through(self, frame, settings, depths: list[float], marker: int):
        self.frame, self.settings, self.line = frame, settings, None
        self.depths, self.marker = depths, marker
        self.selected = self.dragging = None
        self.update()

    # Layout in screen coordinates.

    def node_points(self) -> list[QPointF]:
        """Dual line nodes (back in) or line nodes (drive through)."""

        to_screen = self._transform()

        return [to_screen(d, 0) for d in self.depths]

    def turn_points(self) -> list[QPointF]:
        to_screen = self._transform()
        d = self.depths[-1]
        points = []

        for step in self.line.turn:
            d -= step
            points.append(to_screen(d, 0))

        return points

    def plus_points(self) -> list[QPointF]:
        nodes = self.node_points()

        return [
            QPointF((start.x() + end.x()) / 2, start.y() - self.PLUS_ABOVE_PX)
            for start, end in zip(nodes, nodes[1:], strict=False)
        ]

    def entry_point(self) -> QPointF:
        sign = 1 if self.settings.entry_left_to_right else -1

        return self._transform()(self._entry_d(), -sign * ENTRY_BRANCH_BACK)

    def exit_point(self) -> QPointF:
        sign = 1 if self.settings.exit_left_to_right else -1

        return self._transform()(self._exit_d(), sign * EXIT_BRANCH_ALONG)

    # Mouse and keys.

    def mousePressEvent(self, event):
        if self.line is None or event.button() != Qt.LeftButton:
            return

        position = event.position()
        hit = self._hit(position)

        if hit is None:
            self.selected = None
        elif hit[0] in ("entry", "exit"):
            self.dragging = hit[0]
        elif hit[0] == "plus":
            self.line_changed.emit(self.line.split(hit[1]))
        elif hit[0] == "node":
            self.selected = hit[1]
        else:
            self.length_clicked.emit(hit[0], hit[1], event.globalPosition().toPoint())

        self.update()

    def mouseMoveEvent(self, event):
        if self.line is None:
            return

        if self.dragging is None:
            hit = self._hit(event.position())
            self.setCursor(Qt.ArrowCursor if hit is None else Qt.PointingHandCursor)
            return

        x = event.position().x()
        to_screen = self._transform()

        # The square is on the entry or exit line, which runs a set distance from its node.
        if self.dragging == "entry":
            candidates = self.line.entry_nodes(marker_depth(self.frame, self.settings))
            shift = ENTRY_LINE_INSIDE
        else:
            candidates = self.line.exit_nodes()
            shift = -EXIT_LINE_OUTSIDE

        if not candidates:
            return

        def square_x(node):
            return to_screen(self.depths[node] + shift, 0).x()

        node = min(candidates, key=lambda index: abs(square_x(index) - x))
        field = "entry_node" if self.dragging == "entry" else "exit_node"

        if node != getattr(self.line, field):
            self.line_changed.emit(replace(self.line, **{field: node}))

    def mouseReleaseEvent(self, event):
        self.dragging = None

    def keyPressEvent(self, event):
        line, node = self.line, self.selected

        if event.key() == Qt.Key_Delete and line is not None and node is not None:
            if line.can_remove(node):
                self.selected = None
                self.line_changed.emit(line.remove(node))
        else:
            super().keyPressEvent(event)

    def _hit(self, position: QPointF):
        """What is under the mouse: ("entry"|"exit"|"plus"|"node"|"segment"|"turn", index)."""

        def distance(point):
            return math.dist((point.x(), point.y()), (position.x(), position.y()))

        def near(point, limit):
            return distance(point) <= limit

        if near(self.entry_point(), self.HANDLE_PX):
            return ("entry", 0)

        if near(self.exit_point(), self.HANDLE_PX):
            return ("exit", 0)

        for index, point in enumerate(self.plus_points()):
            if near(point, self.PLUS_PX / 2 + 2):
                return ("plus", index)

        nodes = self.node_points()

        nearest = min(range(len(nodes)), key=lambda index: distance(nodes[index]))

        if distance(nodes[nearest]) <= self.CLICK_PX:
            return ("node", nearest)

        turn = [nodes[-1], *self.turn_points()]

        for part, points in (("segment", nodes), ("turn", turn)):
            for index, (start, end) in enumerate(zip(points, points[1:], strict=False)):
                left, right = sorted((start.x(), end.x()))

                if left <= position.x() <= right and abs(position.y() - start.y()) <= 5:
                    return (part, index)

        return None

    # Painting.

    def paintEvent(self, event):
        if self.frame is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().base())

        style = DisplayStyle()
        to_screen = self._transform()
        self._paint_walls(painter, to_screen, style)

        nodes = self.node_points()
        back_in = self.line is not None
        line_type = ConnectionType.DUAL if back_in else ConnectionType.REGULAR

        for start, end in zip(nodes, nodes[1:], strict=False):
            paint_connection(painter, start, end, line_type, style, self.ARROW_PX)

        others = []

        if back_in:
            others = self._paint_back_in(painter, nodes, style)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*style.subprio_node_color))

        for point in nodes + others:
            painter.drawEllipse(point, self.NODE_PX / 2, self.NODE_PX / 2)

        painter.setBrush(MARKER_COLOR)
        painter.drawEllipse(nodes[self.marker], self.MARKER_PX / 2, self.MARKER_PX / 2)

        if self.selected is not None:
            painter.setPen(QPen(self.palette().highlight().color(), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(nodes[self.selected], self.NODE_PX + 1, self.NODE_PX + 1)

        painter.end()

    def _paint_walls(self, painter, to_screen, style):
        """Back wall and open side, or entry and exit side; and the entry and exit lines."""

        frame, back_in = self.frame, self.line is not None
        middle = to_screen(0, 0).y()
        shed_color = QColor(*style.shed_color)
        line_pen = QPen(self.palette().mid().color(), 1)

        for d, is_open in ((0, True), (frame.depth, not back_in)):
            pen = QPen(shed_color, 1.5 if is_open else 3, Qt.DashLine if is_open else Qt.SolidLine)
            painter.setPen(pen)
            x = to_screen(d, 0).x()
            painter.drawLine(
                QPointF(x, middle - self.WALL_HALF_PX), QPointF(x, middle + self.WALL_HALF_PX)
            )

        if not back_in:
            return

        painter.setPen(line_pen)

        for d, text in ((self._entry_d(), tr("Entry line")), (self._exit_d(), tr("Exit line"))):
            x = to_screen(d, 0).x()
            painter.drawLine(QPointF(x, 4), QPointF(x, self.height() - 20))
            painter.drawText(QRectF(x - 50, self.height() - 18, 100, 16), Qt.AlignCenter, text)

    def _paint_back_in(self, painter, nodes, style) -> list[QPointF]:
        """Turn, branches and "+" buttons. Returns the extra nodes."""

        line = self.line
        turn = [nodes[-1], *self.turn_points()]
        reverse_offset = QPointF(0, 5)

        for start, end in zip(turn, turn[1:], strict=False):
            paint_connection(painter, start, end, ConnectionType.REGULAR, style, self.ARROW_PX)

        paint_connection(
            painter,
            turn[-1] + reverse_offset,
            turn[0] + reverse_offset,
            ConnectionType.REVERSE,
            style,
            self.ARROW_PX,
        )

        entry, exit_ = self.entry_point(), self.exit_point()
        regular = ConnectionType.REGULAR
        paint_connection(painter, entry, nodes[line.entry_node], regular, style, self.ARROW_PX)
        paint_connection(painter, nodes[line.exit_node], exit_, regular, style, self.ARROW_PX)

        # Handles to drag the branches.
        painter.setPen(QPen(self.palette().text().color(), 1))
        painter.setBrush(self.palette().button())
        size = self.HANDLE_PX

        for point in (entry, exit_):
            painter.drawRect(QRectF(point.x() - size / 2, point.y() - size / 2, size, size))

        for point in self.plus_points():
            radius = self.PLUS_PX / 2
            painter.drawEllipse(point, radius, radius)
            painter.drawLine(point - QPointF(radius - 3, 0), point + QPointF(radius - 3, 0))
            painter.drawLine(point - QPointF(0, radius - 3), point + QPointF(0, radius - 3))

        return turn[1:]

    def _entry_d(self) -> float:
        return self.line.entry_line_depth(marker_depth(self.frame, self.settings))

    def _exit_d(self) -> float:
        return self.depths[self.line.exit_node] - EXIT_LINE_OUTSIDE

    def _transform(self):
        """Function from (d, a) to screen: outward to the right, a upward."""

        frame = self.frame
        ds = [frame.depth, 0.0, *self.depths]

        if self.line is not None:
            ds += [self.depths[-1] - sum(self.line.turn), self._entry_d(), self._exit_d()]

        min_d, max_d = min(ds), max(ds)
        margin = self.MARGIN_PX
        scale = (self.width() - 2 * margin) / max(max_d - min_d, 1.0)
        # Exaggerated across the line, so the branches can be told apart.
        a_scale = min(max(scale, 10.0), (self.height() / 2 - 30) / 2)
        middle = self.height() / 2

        def to_screen(d: float, a: float) -> QPointF:
            return QPointF(margin + (max_d - d) * scale, middle - a * a_scale)

        return to_screen
