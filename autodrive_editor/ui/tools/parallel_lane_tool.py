from collections.abc import Callable

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from autodrive_editor.editing.operations.parallel_lane import ParallelLaneOperation
from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.map_tool import is_alive_in_scene
from autodrive_editor.ui.tools.select_tool import SelectTool


class ParallelLaneTool(SelectTool):
    """Shows the lanes beside the selected roads as a dashed preview that follows the pointer.
    A click or Enter creates them; left dragging pans. The roads are selected as with the Select
    tool: right-drag box, Shift+right-drag lasso, Ctrl+click toggles a node; a right-click
    without dragging clears the selection."""

    def __init__(
        self,
        view,
        selection_coordinator,
        operation: ParallelLaneOperation,
        color_provider: Callable[[], tuple[int, int, int]],
        node_diameter: float,
        z_value: float,
    ):
        super().__init__(view, selection_coordinator)

        self.operation = operation
        self._color_provider = color_provider
        self._node_diameter = node_diameter
        self._z_value = z_value
        self._active = False
        self._item: QGraphicsPathItem | None = None

        operation.preview_changed.connect(self._update_preview)

    def activate(self):
        self._active = True
        self._update_preview()

    def deactivate(self):
        super().deactivate()

        self._active = False
        self._update_preview()

    def mouse_move(self, event: QMouseEvent) -> bool:
        if not super().mouse_move(event):
            self.operation.pointer_moved(event.position().toPoint())

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.RightButton:
            area_dragged = self._area_selection.drag_active
            super().mouse_release(event)

            if not area_dragged:
                self.selection_coordinator.node_selection.clear()

            return True

        if event.button() != Qt.LeftButton:
            return False

        if self._end_pan():
            return True

        position = event.position().toPoint()

        if event.modifiers() & Qt.ControlModifier:
            self.selection_coordinator.handle_click(position, event.modifiers())
        else:
            self.operation.pointer_moved(position)
            self.operation.apply()

        return True

    def confirm(self) -> bool:
        return self.operation.apply()

    def status_hint(self) -> str | None:
        return tr(
            "Right-drag or Ctrl+click selects the road, then point beside it. "
            "A click or Enter creates the lane"
        )

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        return Qt.CrossCursor

    @property
    def preview_path(self) -> QPainterPath | None:
        """The dashed preview in scene coordinates, if it is shown."""

        item = self._item if is_alive_in_scene(self._item, self.view.scene()) else None

        return item.path() if item is not None and item.isVisible() else None

    def _update_preview(self):
        if not is_alive_in_scene(self._item, self.view.scene()):
            self._item = QGraphicsPathItem()
            self._item.setZValue(self._z_value)
            self._item.setAcceptedMouseButtons(Qt.NoButton)
            self.view.scene().addItem(self._item)

        lanes = self.operation.preview_lanes() if self._active else []
        path = QPainterPath()
        radius = self._node_diameter / 2

        for lane in lanes:
            path.moveTo(QPointF(*lane[0]))

            for point in lane[1:]:
                path.lineTo(QPointF(*point))

            for x, z in lane:
                path.addEllipse(QPointF(x, z), radius, radius)

        pen = QPen(QColor(*self._color_provider()), 2.0, Qt.DashLine)
        pen.setCosmetic(True)
        self._item.setPen(pen)
        self._item.setPath(path)
        self._item.setVisible(bool(lanes))
