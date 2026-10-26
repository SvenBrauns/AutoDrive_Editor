from PySide6.QtCore import QObject, Signal

from autodrive_editor.i18n import tr
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
            status_text = tr("Grid shown")

        else:
            status_text = tr("Grid hidden")

        self.status_changed.emit(status_text)

    def set_grid_spacing(self, spacing: float):
        try:
            self.background_map.set_grid_spacing(spacing)

        except Exception as ex:
            self.status_changed.emit(tr("The grid spacing could not be changed: {error}", error=ex))
            return

        self.grid_controls.set_grid_spacing(self.background_map.grid_spacing)

        self.status_changed.emit(
            tr("Grid spacing: {spacing:.2f} m", spacing=self.background_map.grid_spacing)
        )

    def set_grid_rotation(self, rotation_angle: float):
        self.background_map.set_grid_rotation(rotation_angle)

        self.grid_controls.set_grid_rotation(self.background_map.grid_rotation)

        self.status_changed.emit(
            tr("Grid rotation: {angle:.2f}°", angle=self.background_map.grid_rotation)
        )

    def set_grid_snap_enabled(self, enabled: bool):
        self.background_map.set_grid_snap_enabled(enabled)

        self.grid_controls.set_grid_snap(self.background_map.grid_snap_enabled)

        self.status_changed.emit(
            tr("Snap to grid on") if self.background_map.grid_snap_enabled else tr("Snap off")
        )

    def reset_grid(self):
        self.background_map.reset_grid()

        self.grid_controls.set_grid_visible(self.background_map.grid_visible)

        self.grid_controls.set_grid_spacing(self.background_map.grid_spacing)

        self.grid_controls.set_grid_rotation(self.background_map.grid_rotation)

        self.status_changed.emit(tr("Grid reset"))
