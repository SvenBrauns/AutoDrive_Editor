from PySide6.QtCore import QObject, Signal

from autodrive_editor.terrain.background_map import BackgroundManager
from autodrive_editor.ui.controls.grid_controls import GridControls


class GridCoordinator(QObject):
    status_changed = Signal(str)

    def __init__(
        self, background_manager: BackgroundManager, grid_controls: GridControls, parent=None
    ):
        super().__init__(parent)

        self.background_manager = background_manager
        self.grid_controls = grid_controls

        self.grid_controls.visibility_requested.connect(self.set_grid_visible)

        self.grid_controls.spacing_requested.connect(self.set_grid_spacing)

        self.grid_controls.rotation_requested.connect(self.set_grid_rotation)

        self.grid_controls.reset_requested.connect(self.reset_grid)

    def set_grid_visible(self, visible: bool):
        self.background_manager.set_grid_visible(visible)

        self.grid_controls.set_grid_visible(self.background_manager.grid_visible)

        if self.background_manager.grid_visible:
            status_text = "Raster eingeblendet"

        else:
            status_text = "Raster ausgeblendet"

        self.status_changed.emit(status_text)

    def set_grid_spacing(self, spacing: float):
        try:
            self.background_manager.set_grid_spacing(spacing)

        except Exception as ex:
            self.status_changed.emit(f"Rasterabstand konnte nicht geändert werden: {ex}")
            return

        self.grid_controls.set_grid_spacing(self.background_manager.grid_spacing)

        self.status_changed.emit(f"Rasterabstand: {self.background_manager.grid_spacing:.2f} m")

    def set_grid_rotation(self, rotation_angle: float):
        self.background_manager.set_grid_rotation(rotation_angle)

        self.grid_controls.set_grid_rotation(self.background_manager.grid_rotation)

        self.status_changed.emit(f"Rasterrotation: {self.background_manager.grid_rotation:.2f}°")

    def reset_grid(self):
        self.background_manager.reset_grid()

        self.grid_controls.set_grid_visible(self.background_manager.grid_visible)

        self.grid_controls.set_grid_spacing(self.background_manager.grid_spacing)

        self.grid_controls.set_grid_rotation(self.background_manager.grid_rotation)

        self.status_changed.emit("Raster zurückgesetzt")
