from collections.abc import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from autodrive_editor.editing.operations.parallel_lane import ParallelLaneOperation
from autodrive_editor.i18n import tr
from autodrive_editor.ui.tools.map_tool import MapTool, is_alive_in_scene


class ParallelLaneTool(MapTool):
    """Shows the lanes beside the selected roads as a dashed preview that follows the pointer.
    A click or Enter creates them; left dragging pans."""

    def __init__(
        self,
        view,
        operation: ParallelLaneOperation,
        color_provider: Callable[[], tuple[int, int, int]],
        node_diameter: float,
        z_value: float,
    ):
        super().__init__(view)

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

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        self._begin_pan(event)

        return True

    def mouse_move(self, event: QMouseEvent) -> bool:
        if not self._continue_pan(event):
            self.operation.pointer_moved(event.position().toPoint())

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        if not self._end_pan():
            self.operation.pointer_moved(event.position().toPoint())
            self.operation.apply()

        return True

    def confirm(self) -> bool:
        return self.operation.apply()

    def status_hint(self) -> str | None:
        return tr("Select a road, then point beside it. A click or Enter creates the lane")

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
