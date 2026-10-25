from PySide6.QtCore import QObject

from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.ui.map_view.map_view import MapView
from autodrive_editor.ui.panels.debug_dock import DebugDock


class DebugDockCoordinator(QObject):
    """Refreshes the debug dock while it is visible."""

    def __init__(
        self, debug_dock: DebugDock, view: MapView, scene_renderer: SceneRenderer, parent=None
    ):
        super().__init__(parent)

        self.debug_dock = debug_dock
        self.view = view
        self.scene_renderer = scene_renderer

        self.view.zoom_changed.connect(self.refresh)

        self.view.rotation_changed.connect(self.refresh)

        self.view.visible_scene_rect_changed.connect(self.refresh)

        self.view.interaction_mode_changed.connect(self.refresh)

        self.debug_dock.visibilityChanged.connect(self._handle_visibility_changed)

    def refresh(self, *args):
        if not self.debug_dock.isVisible():
            return

        self.debug_dock.set_interaction_mode(self.view.interaction_mode)

        self.debug_dock.set_view_state(
            zoom_level=self.view.zoom_level,
            rotation_angle=self.view.rotation_angle,
            visible_rect=self.scene_renderer.current_visible_rect,
        )

        self.debug_dock.set_renderer_state(self.scene_renderer.get_debug_state())

    def _handle_visibility_changed(self, visible: bool):
        if visible:
            self.refresh()
