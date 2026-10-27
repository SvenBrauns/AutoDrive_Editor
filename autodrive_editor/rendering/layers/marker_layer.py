from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.layers.node_layer import node_diameter_px, node_opacity
from autodrive_editor.rendering.screen_size import fade_in, screen_size, view_scale

LABEL_PADDING_X = 4.0
LABEL_PADDING_Y = 1.0
LABEL_GAP = 2.0
LABEL_TEXT_COLOR = QColor(15, 45, 82)
LABEL_BACKGROUND_COLOR = QColor(255, 255, 255, 215)
LABEL_BORDER_COLOR = QColor(15, 45, 82, 140)
LABEL_GRID_PX = 128
# Names start to fade in at this share of marker_name_min_zoom.
NAME_FADE_START = 0.7
PARKING_SIGN_COLOR = QColor(30, 90, 200)
# Size of the parking sign as share of the icon height.
PARKING_SIGN_SHARE = 0.5


class MarkerLayerItem(MapLayerItem):
    """Marker icons above their nodes, with their names. Icons and names have a size on screen
    and stay upright when the map is rotated. Markers are drawn at every zoom level; names that
    would overlap an earlier marker's name are left out."""

    def __init__(self, autodrive_data: AutoDriveData, icon_path: str, display_style: DisplayStyle):
        super().__init__(display_style, display_style.marker_z)

        self.autodrive_data = autodrive_data
        self.icon_renderer = QSvgRenderer(str(icon_path))
        self.names_visible = True

        self.font = QFont()
        self.font.setPointSizeF(8.5)
        self._font_metrics = QFontMetricsF(self.font)

        self._icons: dict[tuple[int, float], QPixmap] = {}
        self._label_widths: dict[str, float] = {}
        # Node ids whose names are shown, for one zoom and rotation. Moving the view does
        # not change which names overlap.
        self._label_layout_key = None
        self._labeled_node_ids: set[int] = set()

        # Markers vehicles park at, by object id; the list keeps the objects (and their ids) alive.
        self._parking_markers: list[MarkerData] = []
        self._parking_ids: set[int] = set()

        self.drawn_markers = 0
        self.drawn_parking = 0
        # Names drawn in the last paint, by node id.
        self.shown_names: dict[int, str] = {}

    def set_names_visible(self, visible: bool):
        self.names_visible = bool(visible)
        self.update()

    def set_parking_markers(self, markers):
        """Markers that get a parking sign. Markers are recognised by object, so the sign
        follows a marker that is moved to another node."""

        self._parking_markers = list(markers)
        self._parking_ids = {id(marker) for marker in self._parking_markers}
        self.update()

    def invalidate(self):
        """Call after markers or their nodes changed."""

        self._label_layout_key = None
        self.update()

    def set_display_style(self, display_style: DisplayStyle):
        self._icons.clear()
        super().set_display_style(display_style)
        self.invalidate()

    def paint(self, painter: QPainter, option, widget=None):
        scale = view_scale(painter)

        if scale <= 0 or not self.autodrive_data.markers or not self.visibility.markers:
            self.drawn_markers = self.drawn_parking = 0
            self.shown_names = {}
            return

        style = self.display_style
        transform = painter.worldTransform()
        device_rect = transform.mapRect(option.exposedRect)

        icon_height = round(
            screen_size(style.marker_size, scale, style.marker_min_px, style.marker_max_px)
        )
        icon_width = icon_height * self._icon_aspect_ratio()
        # The icon's tip touches the top of the node while nodes are drawn.
        node_gap = (
            node_diameter_px(style, scale) / 2 * node_opacity(style, scale)
            if self.visibility.nodes
            else 0.0
        )

        markers = []

        for marker in self.autodrive_data.markers.values():
            node = self.autodrive_data.get_node(marker.node_id)

            if node is not None:
                tip = transform.map(QPointF(node.x, node.z))
                icon_rect = QRectF(
                    tip.x() - icon_width / 2,
                    tip.y() - node_gap - icon_height,
                    icon_width,
                    icon_height,
                )
                markers.append((marker, icon_rect))

        name_opacity = fade_in(
            scale, style.marker_name_min_zoom * NAME_FADE_START, style.marker_name_min_zoom
        )
        names_shown = self.names_visible and name_opacity > 0
        labeled = self._get_labeled_node_ids(transform, markers) if names_shown else set()
        self.shown_names = {
            marker.node_id: marker.name for marker, _ in markers if marker.node_id in labeled
        }

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        icon = self._get_icon(icon_height, painter.device().devicePixelRatioF())
        drawn = drawn_parking = 0

        for marker, icon_rect in markers:
            if icon_rect.intersects(device_rect):
                painter.drawPixmap(icon_rect.topLeft(), icon)
                drawn += 1

                if self.visibility.parking and id(marker) in self._parking_ids:
                    _draw_parking_sign(painter, icon_rect)
                    drawn_parking += 1

        painter.setFont(self.font)
        painter.setOpacity(painter.opacity() * name_opacity)

        for marker, icon_rect in markers:
            if marker.node_id in labeled:
                label_rect = self._label_rect(marker.name, icon_rect)

                if label_rect.intersects(device_rect):
                    self._draw_label(painter, marker.name, label_rect)

        painter.restore()

        self.drawn_markers = drawn
        self.drawn_parking = drawn_parking

    def _get_labeled_node_ids(self, transform, markers) -> set[int]:
        key = (transform.m11(), transform.m12(), transform.m21(), transform.m22())

        if key == self._label_layout_key:
            return self._labeled_node_ids

        labeled = set()
        placed_by_cell: dict[tuple[int, int], list[QRectF]] = {}

        # Earlier markers win, so the shown names stay the same while panning.
        for marker, icon_rect in markers:
            if not marker.name:
                continue

            label_rect = self._label_rect(marker.name, icon_rect)
            cells = grid_cells(label_rect)

            if any(
                label_rect.intersects(other)
                for cell in cells
                for other in placed_by_cell.get(cell, ())
            ):
                continue

            for cell in cells:
                placed_by_cell.setdefault(cell, []).append(label_rect)

            labeled.add(marker.node_id)

        self._label_layout_key = key
        self._labeled_node_ids = labeled

        return labeled

    def _label_rect(self, name: str, icon_rect: QRectF) -> QRectF:
        width = self._label_widths.get(name)

        if width is None:
            width = self._font_metrics.horizontalAdvance(name) + 2 * LABEL_PADDING_X
            self._label_widths[name] = width

        height = self._font_metrics.height() + 2 * LABEL_PADDING_Y

        # Right of the icon's upper part.
        return QRectF(
            icon_rect.right() + LABEL_GAP, icon_rect.top() + icon_rect.height() * 0.1, width, height
        )

    def _draw_label(self, painter: QPainter, name: str, rect: QRectF):
        painter.setPen(LABEL_BORDER_COLOR)
        painter.setBrush(LABEL_BACKGROUND_COLOR)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 3, 3)

        painter.setPen(LABEL_TEXT_COLOR)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, name)

    def _icon_aspect_ratio(self) -> float:
        size = self.icon_renderer.defaultSize()

        return size.width() / size.height() if size.height() > 0 else 1.0

    def _get_icon(self, height: int, device_pixel_ratio: float) -> QPixmap:
        key = (height, device_pixel_ratio)
        icon = self._icons.get(key)

        if icon is None:
            width = height * self._icon_aspect_ratio()
            icon = QPixmap(
                max(1, round(width * device_pixel_ratio)),
                max(1, round(height * device_pixel_ratio)),
            )
            icon.setDevicePixelRatio(device_pixel_ratio)
            icon.fill(Qt.transparent)

            icon_painter = QPainter(icon)
            icon_painter.setRenderHint(QPainter.Antialiasing, True)
            self.icon_renderer.render(icon_painter, QRectF(0, 0, width, height))
            icon_painter.end()

            self._icons[key] = icon

        return icon


def _draw_parking_sign(painter: QPainter, icon_rect: QRectF):
    """A small "P" sign left of the marker icon's upper part."""

    size = icon_rect.height() * PARKING_SIGN_SHARE
    rect = QRectF(icon_rect.left() - size + 1, icon_rect.top(), size, size)

    painter.setPen(Qt.NoPen)
    painter.setBrush(PARKING_SIGN_COLOR)
    painter.drawRoundedRect(rect, size * 0.2, size * 0.2)

    font = QFont()
    font.setBold(True)
    font.setPixelSize(max(1, round(size * 0.75)))
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "P")


def grid_cells(rect: QRectF):
    """The LABEL_GRID_PX cells a rectangle on screen touches, to find overlapping labels."""

    return [
        (cell_x, cell_y)
        for cell_x in range(
            int(rect.left() // LABEL_GRID_PX), int(rect.right() // LABEL_GRID_PX) + 1
        )
        for cell_y in range(
            int(rect.top() // LABEL_GRID_PX), int(rect.bottom() // LABEL_GRID_PX) + 1
        )
    ]
