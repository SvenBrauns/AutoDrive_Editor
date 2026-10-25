from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from autodrive_editor.file_io.background_image import load_dds_as_pixmap
from autodrive_editor.rendering.items.map_grid_item import MapGridItem
from autodrive_editor.terrain.background_transform import BackgroundTransform


class BackgroundMap:
    """The map image (overview.dds) under the network, scaled to the map size, plus the grid."""

    def __init__(self, scene: QGraphicsScene, map_scale: int = 1):
        self.scene = scene
        self.map_scale = map_scale

        self.file_path = None
        self.background_item = None
        self.grid_item = None

        self.grid_visible = True
        self.grid_spacing = 10.0
        self.grid_rotation = 0.0

    def load(self, file_path):
        pixmap = load_dds_as_pixmap(file_path)

        if pixmap.isNull():
            raise ValueError("Die DDS-Datei enthält kein lesbares Bild.")

        self.file_path = file_path

        self._replace_background(pixmap)

    def restore(self):
        """
        Fügt den Hintergrund nach scene.clear() erneut ein.

        Der gespeicherte Dateipfad bleibt erhalten.
        """
        if not self.file_path:
            return False

        pixmap = load_dds_as_pixmap(self.file_path)

        if pixmap.isNull():
            raise ValueError("Die DDS-Datei konnte nicht erneut geladen werden.")

        self._replace_background(pixmap)

        return True

    def set_map_scale(self, map_scale):
        map_scale = int(map_scale)

        if map_scale <= 0:
            raise ValueError("Der Kartenmaßstab muss größer als 0 sein.")

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

        if not preserve_file_path:
            self.file_path = None

    def has_background(self):
        return self.background_item is not None

    def has_file(self):
        return self.file_path is not None

    def _replace_background(self, pixmap):
        self.remove_from_scene(preserve_file_path=True)

        self.background_item = QGraphicsPixmapItem(pixmap)

        self.background_item.setZValue(-1000)

        self.scene.addItem(self.background_item)

        self._apply_transform()
        self._create_grid_item()

    def _apply_transform(self):
        if self.background_item is None:
            return

        pixmap = self.background_item.pixmap()

        if pixmap.isNull():
            return

        background_scale = BackgroundTransform.calculate_background_scale(self.map_scale)

        position_x, position_z = BackgroundTransform.calculate_background_position(
            pixmap.width(), pixmap.height(), self.map_scale
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
            raise ValueError("Der Rasterabstand muss größer als 0 sein.")

        self.grid_spacing = spacing

        if self.grid_item is not None:
            self.grid_item.set_spacing(spacing)

    def set_grid_rotation(self, rotation_angle: float):
        self.grid_rotation = float(rotation_angle) % 360.0

        if self.grid_item is not None:
            self.grid_item.set_rotation_angle(self.grid_rotation)

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
