from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter

from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.marker_layer import grid_cells
from autodrive_editor.rendering.layers.node_layer import node_diameter_px, node_opacity
from autodrive_editor.rendering.screen_size import view_scale
from autodrive_editor.rendering.spatial.node_index import NodeSpatialIndex

LABEL_PADDING_X = 2.0
LABEL_GAP = 2.0
LABEL_TEXT_COLOR = QColor(255, 255, 255)
LABEL_BACKGROUND_COLOR = QColor(0, 0, 0, 160)


class NodeLabelLayerItem(MapLayerItem):
    """The node IDs as small labels right of their nodes, when switched on and zoomed in to
    node_id_min_zoom. Labels that would overlap one of a lower node ID are left out."""

    def __init__(self, node_index: NodeSpatialIndex, display_style: DisplayStyle):
        super().__init__(display_style, display_style.node_z + 1)

        self.node_index = node_index

        self.font = QFont()
        self.font.setPointSizeF(7.5)
        self._font_metrics = QFontMetricsF(self.font)

        # IDs drawn in the last paint.
        self.shown_ids: list[int] = []

    def paint(self, painter: QPainter, option, widget=None):
        self.shown_ids = []

        style = self.display_style
        scale = view_scale(painter)

        if (
            not (self.visibility.nodes and self.visibility.node_ids)
            or scale < style.node_id_min_zoom
            or node_opacity(style, scale) <= 0
        ):
            return

        transform = painter.worldTransform()
        # The labels are laid out for the whole view, so partial repaints show the same ones.
        if widget is not None:
            area = transform.inverted()[0].mapRect(QRectF(widget.rect()))
        else:
            area = option.exposedRect

        device_rect = transform.mapRect(option.exposedRect)
        offset = node_diameter_px(style, scale) / 2 + LABEL_GAP
        height = self._font_metrics.height()

        labels = []
        placed_by_cell: dict[tuple[int, int], list[QRectF]] = {}

        for node in sorted(self.node_index.get_nodes_in_rect(area), key=lambda n: n.node_id):
            text = str(node.node_id)
            point = transform.map(QPointF(node.x, node.z))
            width = self._font_metrics.horizontalAdvance(text) + 2 * LABEL_PADDING_X
            rect = QRectF(point.x() + offset, point.y() - height / 2, width, height)
            cells = grid_cells(rect)

            if any(
                rect.intersects(other) for cell in cells for other in placed_by_cell.get(cell, ())
            ):
                continue

            for cell in cells:
                placed_by_cell.setdefault(cell, []).append(rect)

            if rect.intersects(device_rect):
                labels.append((node.node_id, text, rect))

        painter.save()
        painter.resetTransform()
        painter.setFont(self.font)

        for node_id, text, rect in labels:
            painter.fillRect(rect, LABEL_BACKGROUND_COLOR)
            painter.setPen(LABEL_TEXT_COLOR)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            self.shown_ids.append(node_id)

        painter.restore()
