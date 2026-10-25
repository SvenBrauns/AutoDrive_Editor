from PySide6.QtCore import QObject, Signal

from autodrive_editor.terrain.background_map import BackgroundMap
from autodrive_editor.ui.controls.grid_controls import GridControls


class GridCoordinator(QObject):
    """Applies the grid controls to the background map's grid."""

    status_changed = Signal(str)

    def __init__(self, background_map: BackgroundMap, grid_controls: GridControls, parent=None):
        super().__init__(parent)

        self.background_map = background_map
        self.grid_controls = grid_controls

        self.grid_controls.visibility_requested.connect(self.set_grid_visible)

        self.grid_controls.spacing_requested.connect(self.set_grid_spacing)

        self.grid_controls.rotation_requested.connect(self.set_grid_rotation)

        self.grid_controls.reset_requested.connect(self.reset_grid)

    def set_grid_visible(self, visible: bool):
        self.background_map.set_grid_visible(visible)

        self.grid_controls.set_grid_visible(self.background_map.grid_visible)

        if self.background_map.grid_visible:
            status_text = "Raster eingeblendet"

        else:
            status_text = "Raster ausgeblendet"

        self.status_changed.emit(status_text)

    def set_grid_spacing(self, spacing: float):
        try:
            self.background_map.set_grid_spacing(spacing)

        except Exception as ex:
            self.status_changed.emit(f"Rasterabstand konnte nicht geändert werden: {ex}")
            return

        self.grid_controls.set_grid_spacing(self.background_map.grid_spacing)

        self.status_changed.emit(f"Rasterabstand: {self.background_map.grid_spacing:.2f} m")

    def set_grid_rotation(self, rotation_angle: float):
        self.background_map.set_grid_rotation(rotation_angle)

        self.grid_controls.set_grid_rotation(self.background_map.grid_rotation)

        self.status_changed.emit(f"Rasterrotation: {self.background_map.grid_rotation:.2f}°")

    def set_grid_snap_enabled(self, enabled: bool):
        self.background_map.set_grid_snap_enabled(enabled)

        self.grid_controls.set_grid_snap(self.background_map.grid_snap_enabled)

        self.status_changed.emit(
            "Einrasten am Raster an" if self.background_map.grid_snap_enabled else "Einrasten aus"
        )

    def reset_grid(self):
        self.background_map.reset_grid()

        self.grid_controls.set_grid_visible(self.background_map.grid_visible)

        self.grid_controls.set_grid_spacing(self.background_map.grid_spacing)

        self.grid_controls.set_grid_rotation(self.background_map.grid_rotation)

        self.status_changed.emit("Raster zurückgesetzt")
