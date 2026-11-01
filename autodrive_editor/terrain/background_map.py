from enum import StrEnum

from PySide6.QtCore import QPointF
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from autodrive_editor.file_io.background_image import load_background_pixmap
from autodrive_editor.file_io.ground_map import Field
from autodrive_editor.i18n import tr
from autodrive_editor.rendering.items.field_outline_item import FieldOutlineItem
from autodrive_editor.rendering.items.game_picture_item import GamePictureItem
from autodrive_editor.rendering.items.map_grid_item import MapGridItem
from autodrive_editor.terrain.background_transform import BackgroundTransform
from autodrive_editor.terrain.game_picture import GamePicture


class Background(StrEnum):
    OVERVIEW = "overview"
    GROUND = "ground"
    PICTURE = "picture"


class BackgroundMap:
    """The map image (overview.dds) under the network, scaled to the map size, plus the grid.
    An imported map can show its ground map with the field outlines instead, or the game picture
    over the map image."""

    def __init__(self, scene: QGraphicsScene, map_scale: int = 1):
        self.scene = scene
        self.map_scale = map_scale

        self.file_path = None
        self.background_item = None
        self.grid_item = None
        self.field_item = None
        self.picture_item = None

        self.ground_path = None
        self.fields: list[Field] = []
        self.picture: GamePicture | None = None
        self.background = Background.OVERVIEW

        self.grid_visible = True
        self.grid_spacing = 10.0
        self.grid_rotation = 0.0

        # Snapping works even while the grid is hidden.
        self.grid_snap_enabled = False

    def load(self, file_path):
        pixmap = load_background_pixmap(file_path)

        if pixmap.isNull():
            raise ValueError(tr("The image file contains no readable image."))

        self.file_path = file_path
        self.ground_path = None
        self.fields = []
        self.picture = None

        self._replace_background(pixmap)

    def set_ground(self, ground_path, fields: list[Field]):
        """The ground map of the loaded map image; None if it has none."""

        self.ground_path = ground_path
        self.fields = list(fields)

        if self.showing_ground():
            self.restore()

    def set_picture(self, picture: GamePicture | None):
        """The game picture of the loaded map; None if it has none."""

        was_showing = self.showing_picture()
        self.picture = picture

        if was_showing or self.showing_picture():
            self.restore()

    def picture_tiles_changed(self, keys):
        """Tiles (level, col, row) of the shown picture were written."""

        if self.picture_item is not None:
            self.picture_item.tiles_changed(keys)

    def set_background(self, background: Background):
        """Shows the chosen background where the map has it, otherwise the map image."""

        shown = (self.showing_ground(), self.showing_picture())
        self.background = Background(background)

        if (self.showing_ground(), self.showing_picture()) != shown:
            self.restore()

    def available(self, background: Background) -> bool:
        if background == Background.GROUND:
            return self.ground_path is not None

        if background == Background.PICTURE:
            return self.picture is not None

        return True

    def showing_ground(self) -> bool:
        return self.background == Background.GROUND and self.ground_path is not None

    def showing_picture(self) -> bool:
        return self.background == Background.PICTURE and self.picture is not None

    def restore(self):
        """
        Fügt den Hintergrund nach scene.clear() erneut ein.

        Der gespeicherte Dateipfad bleibt erhalten.
        """
        if not self.file_path:
            return False

        pixmap = load_background_pixmap(
            self.ground_path if self.showing_ground() else self.file_path
        )

        if pixmap.isNull():
            raise ValueError(tr("The image file could not be loaded again."))

        self._replace_background(pixmap)

        return True

    def set_map_scale(self, map_scale):
        map_scale = int(map_scale)

        if map_scale <= 0:
            raise ValueError(tr("The map scale must be greater than 0."))

        self.map_scale = map_scale

        self._apply_transform()
        self._update_grid_rect()

    def remove_from_scene(self, preserve_file_path=True):
        if self.grid_item is not None:
            if self.grid_item.scene() is self.scene:
                self.scene.removeItem(self.grid_item)

            self.grid_item = None

        if self.background_item is not None:
            if self.background_item.scene() is self.scene:
                self.scene.removeItem(self.background_item)

            self.background_item = None

        if self.field_item is not None:
            if self.field_item.scene() is self.scene:
                self.scene.removeItem(self.field_item)

            self.field_item = None

        if self.picture_item is not None:
            self.picture_item.close()

            if self.picture_item.scene() is self.scene:
                self.scene.removeItem(self.picture_item)

            self.picture_item = None

        if not preserve_file_path:
            self.file_path = None
            self.ground_path = None
            self.fields = []
            self.picture = None

    def has_background(self):
        return self.background_item is not None

    def has_file(self):
        return self.file_path is not None

    def _replace_background(self, pixmap):
        self.remove_from_scene(preserve_file_path=True)

        self.background_item = QGraphicsPixmapItem(pixmap)

        self.background_item.setZValue(-1000)

        self.scene.addItem(self.background_item)

        if self.showing_ground() and self.fields:
            self.field_item = FieldOutlineItem(self.fields)
            self.scene.addItem(self.field_item)

        if self.showing_picture():
            self.picture_item = GamePictureItem(self.picture)
            self.scene.addItem(self.picture_item)

        self._apply_transform()
        self._create_grid_item()

    def _apply_transform(self):
        if self.background_item is None:
            return

        pixmap = self.background_item.pixmap()

        if pixmap.isNull():
            return

        background_scale = BackgroundTransform.calculate_background_scale(
            self.map_scale, pixmap.width()
        )

        position_x, position_z = BackgroundTransform.calculate_background_position(
            pixmap.width(), pixmap.height(), background_scale
        )

        self.background_item.setScale(background_scale)

        self.background_item.setPos(position_x, position_z)

        self._update_grid_rect()

    def set_grid_visible(self, visible: bool):
        self.grid_visible = bool(visible)

        if self.grid_item is not None:
            self.grid_item.setVisible(self.grid_visible)

    def set_grid_spacing(self, spacing: float):
        spacing = float(spacing)

        if spacing <= 0.0:
            raise ValueError(tr("The grid spacing must be greater than 0."))

        self.grid_spacing = spacing

        if self.grid_item is not None:
            self.grid_item.set_spacing(spacing)

    def set_grid_rotation(self, rotation_angle: float):
        self.grid_rotation = float(rotation_angle) % 360.0

        if self.grid_item is not None:
            self.grid_item.set_rotation_angle(self.grid_rotation)

    def set_grid_snap_enabled(self, enabled: bool):
        self.grid_snap_enabled = bool(enabled)

    def snap_point(self, x: float, z: float) -> tuple[float, float]:
        """The nearest grid point while snapping is on, otherwise the
        point itself."""

        if not self.grid_snap_enabled:
            return x, z

        return snap_to_grid(x, z, self.grid_spacing, self.grid_rotation)

    def reset_grid(self):
        self.grid_visible = True
        self.grid_spacing = 10.0
        self.grid_rotation = 0.0

        if self.grid_item is None:
            self._create_grid_item()
            return

        self.grid_item.set_spacing(self.grid_spacing)

        self.grid_item.set_rotation_angle(self.grid_rotation)

        self.grid_item.setVisible(self.grid_visible)

    def _create_grid_item(self):
        if self.background_item is None:
            return

        if self.grid_item is not None:
            if self.grid_item.scene() is self.scene:
                self.scene.removeItem(self.grid_item)

            self.grid_item = None

        grid_rect = self.background_item.sceneBoundingRect()

        if grid_rect.isEmpty():
            return

        self.grid_item = MapGridItem(
            grid_rect=grid_rect, spacing=self.grid_spacing, rotation_angle=self.grid_rotation
        )

        self.grid_item.setVisible(self.grid_visible)

        self.scene.addItem(self.grid_item)

    def _update_grid_rect(self):
        if self.background_item is None or self.grid_item is None:
            return

        grid_rect = self.background_item.sceneBoundingRect()

        self.grid_item.set_grid_rect(grid_rect)


def snap_to_grid(x: float, z: float, spacing: float, rotation_angle: float) -> tuple[float, float]:
    """Nearest point of a grid with the given spacing, rotated around
    the map center like the drawn grid (MapGridItem)."""

    to_grid = QTransform().rotate(-rotation_angle)
    grid_point = to_grid.map(QPointF(x, z))

    snapped = QPointF(
        round(grid_point.x() / spacing) * spacing, round(grid_point.y() / spacing) * spacing
    )

    scene_point = QTransform().rotate(rotation_angle).map(snapped)

    return scene_point.x(), scene_point.y()


def map_scale_for_extent(xs, zs) -> int:
    """The smallest map size (1, 2, 4, 8 = 2, 4, 8, 16 km) that holds all positions; the map's
    centre is 0, 0."""

    reach = max((abs(value) for value in (*xs, *zs)), default=0.0)

    return next((scale for scale in (1, 2, 4) if reach <= scale * 1024), 8)
