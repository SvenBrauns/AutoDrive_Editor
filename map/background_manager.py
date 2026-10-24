from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene
)

from map.background_loader import load_dds_as_pixmap
from map.background_transform import MapTransform


class BackgroundManager:

    def __init__(
        self,
        scene: QGraphicsScene,
        map_scale: int = 1
    ):
        self.scene = scene
        self.map_scale = map_scale

        self.file_path = None
        self.background_item = None

    def load(self, file_path):
        pixmap = load_dds_as_pixmap(
            file_path
        )

        if pixmap.isNull():
            raise ValueError(
                "Die DDS-Datei enthält kein lesbares Bild."
            )

        self.file_path = file_path

        self._replace_background(
            pixmap
        )

    def restore(self):
        """
        Fügt den Hintergrund nach scene.clear() erneut ein.

        Der gespeicherte Dateipfad bleibt erhalten.
        """
        if not self.file_path:
            return False

        pixmap = load_dds_as_pixmap(
            self.file_path
        )

        if pixmap.isNull():
            raise ValueError(
                "Die DDS-Datei konnte nicht erneut geladen werden."
            )

        self._replace_background(
            pixmap
        )

        return True

    def set_map_scale(self, map_scale):
        map_scale = int(map_scale)

        if map_scale <= 0:
            raise ValueError(
                "Der Kartenmaßstab muss größer als 0 sein."
            )

        self.map_scale = map_scale

        self._apply_transform()

    def remove_from_scene(
        self,
        preserve_file_path=True
    ):
        """
        Entfernt das GraphicsItem aus der Scene.

        Bei preserve_file_path=True kann die Karte danach mit
        restore() erneut geladen werden.
        """
        if self.background_item is not None:
            if self.background_item.scene() is self.scene:
                self.scene.removeItem(
                    self.background_item
                )

            self.background_item = None

        if not preserve_file_path:
            self.file_path = None

    def has_background(self):
        return self.background_item is not None

    def has_file(self):
        return self.file_path is not None

    def _replace_background(self, pixmap):
        self.remove_from_scene(
            preserve_file_path=True
        )

        self.background_item = QGraphicsPixmapItem(
            pixmap
        )

        self.background_item.setZValue(
            -1000
        )

        self.scene.addItem(
            self.background_item
        )

        self._apply_transform()

    def _apply_transform(self):
        if self.background_item is None:
            return

        pixmap = self.background_item.pixmap()

        if pixmap.isNull():
            return

        background_scale = (
            MapTransform.calculate_background_scale(
                self.map_scale
            )
        )

        position_x, position_z = (
            MapTransform.calculate_background_position(
                pixmap.width(),
                pixmap.height(),
                self.map_scale
            )
        )

        self.background_item.setScale(
            background_scale
        )

        self.background_item.setPos(
            position_x,
            position_z
        )