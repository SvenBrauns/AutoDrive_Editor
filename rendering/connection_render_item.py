import math

from PySide6.QtCore import (
    QPointF,
    QRectF,
    Qt
)

from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QPolygonF
)

from PySide6.QtWidgets import (
    QGraphicsItem
)

from rendering.connection_spatial_index import (
    ConnectionSpatialIndex
)

from rendering.display_style import DisplayStyle


class ConnectionRenderItem(QGraphicsItem):

    CONNECTION_REGULAR = "regular"
    CONNECTION_DUAL = "dual"
    CONNECTION_REVERSE = "reverse"

    def __init__(
        self,
        spatial_index: ConnectionSpatialIndex,
        scene_rect: QRectF,
        display_style: DisplayStyle
    ):
        super().__init__()

        self.setFlag(
            QGraphicsItem.ItemUsesExtendedStyleOption,
            True
        )

        self.spatial_index = spatial_index
        self.scene_rect = QRectF(
            scene_rect
        )

        self.display_style = display_style

        self.connection_pens = {
            self.CONNECTION_REGULAR: self._create_pen(
                QColor(0, 255, 0)
            ),
            self.CONNECTION_DUAL: self._create_pen(
                QColor(0, 0, 255)
            ),
            self.CONNECTION_REVERSE: self._create_pen(
                QColor(100, 220, 255)
            )
        }

        self.connection_brushes = {
            connection_type: QBrush(
                connection_pen.color()
            )
            for (
                connection_type,
                connection_pen
            ) in self.connection_pens.items()
        }

        self.setAcceptedMouseButtons(
            Qt.NoButton
        )

        self.setFlag(
            QGraphicsItem.ItemIsSelectable,
            False
        )

    def boundingRect(self) -> QRectF:
        margin = max(
            self.display_style.arrow_length,
            self.display_style.arrow_width,
            self.display_style.node_diameter
        )

        return self.scene_rect.adjusted(
            -margin,
            -margin,
            margin,
            margin
        )

    def paint(
        self,
        painter: QPainter,
        option,
        widget=None
    ):
        paint_margin = max(
            self.display_style.arrow_length,
            self.display_style.arrow_width,
            self.display_style.detailed_connection_width
        )

        visible_rect = QRectF(
            option.exposedRect
        ).adjusted(
            -paint_margin,
            -paint_margin,
            paint_margin,
            paint_margin
        )

        painter.setClipRect(
            visible_rect
        )

        visible_connections = (
            self.spatial_index.get_connections_in_rect(
                visible_rect
            )
        )

        if not visible_connections:
            return

        connections_by_type = {
            self.CONNECTION_REGULAR: [],
            self.CONNECTION_DUAL: [],
            self.CONNECTION_REVERSE: []
        }

        for connection in visible_connections:
            type_connections = (
                connections_by_type.get(
                    connection.connection_type
                )
            )

            if type_connections is None:
                continue

            type_connections.append(
                connection
            )

        painter.save()

        painter.setRenderHint(
            QPainter.Antialiasing,
            False
        )

        for (
            connection_type,
            type_connections
        ) in connections_by_type.items():
            if not type_connections:
                continue

            painter.setPen(
                self.connection_pens[
                    connection_type
                ]
            )

            painter.setBrush(
                self.connection_brushes[
                    connection_type
                ]
            )

            for connection in type_connections:
                self._draw_connection(
                    painter,
                    connection
                )

        painter.restore()

    def _draw_connection(
        self,
        painter,
        connection
    ):
        delta_x = (
            connection.target_x
            - connection.source_x
        )

        delta_z = (
            connection.target_z
            - connection.source_z
        )

        distance = math.hypot(
            delta_x,
            delta_z
        )

        if distance <= 0.000001:
            return

        direction_x = delta_x / distance
        direction_z = delta_z / distance

        node_radius = (
            self.display_style.node_diameter
            / 2
        )

        maximum_offset = max(
            0.0,
            distance / 2 - 0.0001
        )

        endpoint_offset = min(
            node_radius,
            maximum_offset
        )

        source_tip = QPointF(
            connection.source_x
            + direction_x * endpoint_offset,
            connection.source_z
            + direction_z * endpoint_offset
        )

        target_tip = QPointF(
            connection.target_x
            - direction_x * endpoint_offset,
            connection.target_z
            - direction_z * endpoint_offset
        )

        visible_length = max(
            0.0,
            distance
            - 2 * endpoint_offset
        )

        if visible_length <= 0.0001:
            return

        arrow_length = min(
            self.display_style.arrow_length,
            visible_length * 0.4
        )

        if arrow_length <= 0.0001:
            return

        arrow_width = min(
            self.display_style.arrow_width,
            arrow_length
        )

        target_arrow_base = QPointF(
            target_tip.x()
            - direction_x * arrow_length,
            target_tip.y()
            - direction_z * arrow_length
        )

        line_start = source_tip
        line_end = target_arrow_base

        if (
            connection.connection_type
            == self.CONNECTION_DUAL
        ):
            source_arrow_base = QPointF(
                source_tip.x()
                + direction_x * arrow_length,
                source_tip.y()
                + direction_z * arrow_length
            )

            line_start = source_arrow_base

            source_arrow = (
                self._create_arrow_polygon(
                    tip=source_tip,
                    direction_x=-direction_x,
                    direction_z=-direction_z,
                    arrow_length=arrow_length,
                    arrow_width=arrow_width
                )
            )

            painter.drawPolygon(
                source_arrow
            )

        painter.drawLine(
            line_start,
            line_end
        )

        target_arrow = (
            self._create_arrow_polygon(
                tip=target_tip,
                direction_x=direction_x,
                direction_z=direction_z,
                arrow_length=arrow_length,
                arrow_width=arrow_width
            )
        )

        painter.drawPolygon(
            target_arrow
        )

    @staticmethod
    def _create_arrow_polygon(
        tip,
        direction_x,
        direction_z,
        arrow_length,
        arrow_width
    ):
        base_x = (
            tip.x()
            - direction_x * arrow_length
        )

        base_z = (
            tip.y()
            - direction_z * arrow_length
        )

        perpendicular_x = -direction_z
        perpendicular_z = direction_x

        half_width = arrow_width / 2

        left_point = QPointF(
            base_x
            + perpendicular_x * half_width,
            base_z
            + perpendicular_z * half_width
        )

        right_point = QPointF(
            base_x
            - perpendicular_x * half_width,
            base_z
            - perpendicular_z * half_width
        )

        return QPolygonF(
            [
                tip,
                left_point,
                right_point
            ]
        )

    def _create_pen(
        self,
        color
    ):
        connection_pen = QPen(
            color
        )

        connection_pen.setWidthF(
            self.display_style.detailed_connection_width
        )

        connection_pen.setCapStyle(
            Qt.FlatCap
        )

        connection_pen.setJoinStyle(
            Qt.BevelJoin
        )

        return connection_pen