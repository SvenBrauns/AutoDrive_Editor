import math
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject

from autodrive_editor.terrain.game_picture import GamePicture

# 2000² tiles take 16 MB each as a pixmap.
CACHED_TILES = 24


class GamePictureItem(QGraphicsObject):
    """The game picture over the map image. Draws only the visible tiles of the level that fits
    the zoom, loads them in the background and shows a coarser level until they arrive; where
    nothing was captured the map image below shows through."""

    # Above the map image (-1000), below the field outlines (-950).
    Z_VALUE = -975.0

    _loaded = Signal(object, QImage)

    def __init__(self, picture: GamePicture):
        super().__init__()

        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setZValue(self.Z_VALUE)

        self.picture = picture
        self.pixmaps: OrderedDict[tuple[int, int, int], QPixmap] = OrderedDict()
        self.loading: set[tuple[int, int, int]] = set()
        self.loader = ThreadPoolExecutor(max_workers=2)
        self._loaded.connect(self._store)

        half = picture.grid.map_size / 2
        self.bounds = QRectF(-half, -half, 2 * half, 2 * half)

    def boundingRect(self) -> QRectF:
        return self.bounds

    def paint(self, painter: QPainter, option, widget=None):
        transform = painter.worldTransform()
        screen_px_per_m = math.hypot(transform.m11(), transform.m12())
        screen_px_per_m *= painter.device().devicePixelRatioF()

        if screen_px_per_m <= 0:
            return

        grid = self.picture.grid
        level = grid.level_for(1 / screen_px_per_m)
        exposed = option.exposedRect
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        for col, row in grid.tiles_in(
            level, exposed.left(), exposed.top(), exposed.right(), exposed.bottom()
        ):
            if self.picture.has_tile(level, col, row):
                self._draw_tile(painter, level, col, row)

    def _draw_tile(self, painter: QPainter, level: int, col: int, row: int):
        """The tile, or the part of the nearest coarser tile already loaded."""

        target = QRectF(*self.picture.grid.tile_rect(level, col, row))
        pixmap = self._pixmap((level, col, row))

        if pixmap is not None:
            painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
            return

        for coarser in range(level + 1, self.picture.grid.top_level + 1):
            shift = coarser - level
            key = (coarser, col >> shift, row >> shift)

            if (pixmap := self.pixmaps.get(key)) is not None:
                left, top, _, _ = self.picture.grid.tile_rect(*key)
                px_per_m = 1 / (self.picture.grid.m_per_px * 2**coarser)
                source = QRectF(
                    (target.left() - left) * px_per_m,
                    (target.top() - top) * px_per_m,
                    target.width() * px_per_m,
                    target.height() * px_per_m,
                )
                painter.drawPixmap(target, pixmap, source)
                return

    def _pixmap(self, key) -> QPixmap | None:
        """The cached pixmap of a tile; starts loading it if it is not cached."""

        if (pixmap := self.pixmaps.get(key)) is not None:
            self.pixmaps.move_to_end(key)
            return pixmap

        if key not in self.loading:
            self.loading.add(key)
            self.loader.submit(self._load, key, str(self.picture.tile_path(*key)))

        return None

    def _load(self, key, path: str):
        image = QImage(path)

        try:
            self._loaded.emit(key, image)
        except RuntimeError:
            # The item was deleted while loading.
            pass

    def _store(self, key, image: QImage):
        # A tile that cannot be read stays in loading, so it is not tried again on every paint.
        if image.isNull():
            return

        self.loading.discard(key)

        self.pixmaps[key] = QPixmap.fromImage(image)

        while len(self.pixmaps) > CACHED_TILES:
            self.pixmaps.popitem(last=False)

        self.update(QRectF(*self.picture.grid.tile_rect(*key)))

    def close(self):
        """Stops loading; call before the item is dropped."""

        self.loader.shutdown(wait=False, cancel_futures=True)
