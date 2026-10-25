from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem

from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.connections.connection_data import ConnectionData
from autodrive_editor.rendering.connections.connection_geometry import (
    MINIMUM_VISIBLE_LENGTH,
    calculate_connection_geometry,
    create_arrow_polygon,
)
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.spatial.connection_index import ConnectionSpatialIndex


class ConnectionRenderItem(QGraphicsItem):
    def __init__(
        self, spatial_index: ConnectionSpatialIndex, scene_rect: QRectF, display_style: DisplayStyle
    ):
        super().__init__()

        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)

        self.spatial_index = spatial_index
        self.scene_rect = QRectF(scene_rect)

        self.display_style = display_style

        self.connection_pens = {
            ConnectionType.REGULAR: self._create_pen(self.display_style.regular_connection_color),
            ConnectionType.DUAL: self._create_pen(self.display_style.dual_connection_color),
            ConnectionType.REVERSE: self._create_pen(self.display_style.reverse_connection_color),
        }

        self.connection_brushes = {
            connection_type: QBrush(connection_pen.color())
            for (connection_type, connection_pen) in self.connection_pens.items()
        }

        self.setAcceptedMouseButtons(Qt.NoButton)

        self.setFlag(QGraphicsItem.ItemIsSelectable, False)

    def boundingRect(self) -> QRectF:
        margin = max(
            self.display_style.arrow_length,
            self.display_style.arrow_width,
            self.display_style.node_diameter,
        )

        return self.scene_rect.adjusted(-margin, -margin, margin, margin)

    def set_scene_rect(self, scene_rect: QRectF):
        scene_rect = QRectF(scene_rect)

        if scene_rect == self.scene_rect:
            return

        self.prepareGeometryChange()

        self.scene_rect = scene_rect

        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        if self.scene_rect.isEmpty():
            return

        paint_margin = max(
            self.display_style.arrow_length,
            self.display_style.arrow_width,
            self.display_style.detailed_connection_width,
        )

        visible_rect = QRectF(option.exposedRect).adjusted(
            -paint_margin, -paint_margin, paint_margin, paint_margin
        )

        visible_rect = visible_rect.intersected(self.boundingRect())

        if visible_rect.isEmpty():
            return

        visible_connections = self.spatial_index.get_connections_in_rect(visible_rect)

        if not visible_connections:
            return

        connections_by_type = {
            ConnectionType.REGULAR: [],
            ConnectionType.DUAL: [],
            ConnectionType.REVERSE: [],
        }

        for connection in visible_connections:
            type_connections = connections_by_type.get(connection.connection_type)

            if type_connections is None:
                continue

            type_connections.append(connection)

        painter.save()

        painter.setClipRect(visible_rect)

        painter.setRenderHint(QPainter.Antialiasing, False)

        for connection_type, type_connections in connections_by_type.items():
            if not type_connections:
                continue

            painter.setPen(self.connection_pens[connection_type])

            painter.setBrush(self.connection_brushes[connection_type])

            for connection in type_connections:
                self._draw_connection(painter, connection)

        painter.restore()

    def _draw_connection(self, painter: QPainter, connection: ConnectionData):
        geometry = calculate_connection_geometry(
            source_x=connection.source_x,
            source_z=connection.source_z,
            target_x=connection.target_x,
            target_z=connection.target_z,
            node_diameter=(self.display_style.node_diameter),
        )

        if geometry is None:
            return

        visible_length = max(0.0, geometry.distance - 2 * geometry.endpoint_offset)

        if visible_length <= MINIMUM_VISIBLE_LENGTH:
            return

        arrow_length = min(self.display_style.arrow_length, visible_length * 0.4)

        if arrow_length <= MINIMUM_VISIBLE_LENGTH:
            return

        arrow_width = min(self.display_style.arrow_width, arrow_length)

        target_arrow_base = QPointF(
            geometry.target_tip.x() - geometry.direction_x * arrow_length,
            geometry.target_tip.y() - geometry.direction_z * arrow_length,
        )

        line_start = geometry.source_tip
        line_end = target_arrow_base

        if connection.connection_type == ConnectionType.DUAL:
            source_arrow_base = QPointF(
                geometry.source_tip.x() + geometry.direction_x * arrow_length,
                geometry.source_tip.y() + geometry.direction_z * arrow_length,
            )

            line_start = source_arrow_base

            source_arrow = create_arrow_polygon(
                tip=geometry.source_tip,
                direction_x=-geometry.direction_x,
                direction_z=-geometry.direction_z,
                arrow_length=arrow_length,
                arrow_width=arrow_width,
            )

            painter.drawPolygon(source_arrow)

        painter.drawLine(line_start, line_end)

        target_arrow = create_arrow_polygon(
            tip=geometry.target_tip,
            direction_x=geometry.direction_x,
            direction_z=geometry.direction_z,
            arrow_length=arrow_length,
            arrow_width=arrow_width,
        )

        painter.drawPolygon(target_arrow)

    def _create_pen(self, color: tuple[int, int, int]) -> QPen:
        connection_pen = QPen(QColor(color[0], color[1], color[2]))

        connection_pen.setWidthF(self.display_style.detailed_connection_width)

        connection_pen.setCapStyle(Qt.FlatCap)

        connection_pen.setJoinStyle(Qt.BevelJoin)

        return connection_pen
