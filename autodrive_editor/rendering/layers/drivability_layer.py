import math

from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QImage, QPainter, qRgba

from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, ROAD_VALUE, NavigationCostmap
from autodrive_editor.rendering.display_style import DisplayStyle
from autodrive_editor.rendering.layers.map_layer_item import MapLayerItem
from autodrive_editor.rendering.screen_size import view_scale

# Cells per image pixel by the least screen pixels per metre it is drawn at. Zoomed out,
# smaller images keep the copied part about as large as the screen.
LEVELS = ((2.0, 1), (0.5, 4), (0.0, 16))
# Width of a cost band: roads start at 51, the next band at 85, and so on.
BAND_WIDTH = 34
# Colour per band, from the cheapest after roads to the most expensive.
BAND_COLORS = ((60, 200, 60), (230, 220, 40), (240, 150, 30), (230, 80, 30), (200, 40, 40))


def cell_color(value: int) -> int:
    """ARGB colour of a cell value. Roads are left clear, blocked cells are strong."""

    if value == 255:
        return qRgba(220, 0, 0, 170)

    if value >= BLOCKED_VALUE:
        return qRgba(60, 60, 230, 170)

    if value >= 250:
        return qRgba(200, 0, 200, 150)

    band = (value - ROAD_VALUE) // BAND_WIDTH

    if band <= 0:
        return qRgba(0, 0, 0, 0)

    red, green, blue = BAND_COLORS[min(band, len(BAND_COLORS)) - 1]
    # Steeper ground within a band is drawn a little stronger.
    slope = (value - ROAD_VALUE) % BAND_WIDTH / BAND_WIDTH

    return qRgba(red, green, blue, int(70 + 70 * slope))


COLOR_TABLE = [cell_color(value) for value in range(256)]


def _indexed_image(cells: bytes, width: int, height: int) -> QImage:
    image = QImage(cells, width, height, width, QImage.Format_Indexed8)
    image.setColorTable(COLOR_TABLE)

    return image


class DrivabilityLayerItem(MapLayerItem):
    """The game's drivability map of the savegame, drawn over the background map, below the
    network. Only the visible part is copied to an image when painting."""

    def __init__(self, display_style: DisplayStyle):
        super().__init__(display_style, display_style.drivability_z)

        self.costmap: NavigationCostmap | None = None
        # Image and its cells (the image does not keep them alive) by cells per pixel.
        self._images: dict[int, tuple[QImage, bytes]] = {}

    def set_costmap(self, costmap: NavigationCostmap | None):
        self.prepareGeometryChange()

        self.costmap = costmap
        self._images = {}
        self.bounds = QRectF()

        if costmap is not None:
            width, height = costmap.width, costmap.height
            self.bounds = QRectF(-width / 2, -height / 2, width, height)

            for _, step in LEVELS:
                cells = costmap.cells

                if step > 1:
                    cells = b"".join(
                        cells[row * width : (row + 1) * width : step]
                        for row in range(0, height, step)
                    )

                image = _indexed_image(cells, math.ceil(width / step), math.ceil(height / step))
                self._images[step] = (image, cells)

        self.update()

    def set_network_bounds(self, network_bounds: QRectF):
        """The layer covers the whole map, which may be larger than the network."""

    def paint(self, painter: QPainter, option, widget=None):
        scale = view_scale(painter)

        if self.costmap is None or not self.visibility.drivability or scale <= 0:
            return

        exposed = option.exposedRect.intersected(self.bounds)

        if exposed.isEmpty():
            return

        step = next(step for minimum, step in LEVELS if scale >= minimum)
        image = self._images[step][0]
        left = self.bounds.left()
        top = self.bounds.top()

        # The part of the image under the exposed area, in whole pixels.
        first_column = max(0, math.floor((exposed.left() - left) / step))
        first_row = max(0, math.floor((exposed.top() - top) / step))
        end_column = min(image.width(), math.ceil((exposed.right() - left) / step))
        end_row = min(image.height(), math.ceil((exposed.bottom() - top) / step))

        if end_column <= first_column or end_row <= first_row:
            return

        source = QRect(first_column, first_row, end_column - first_column, end_row - first_row)
        target = QRectF(
            left + first_column * step,
            top + first_row * step,
            source.width() * step,
            source.height() * step,
        )

        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.drawImage(target, image.copy(source))
