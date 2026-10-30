import math
from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem

from autodrive_editor.editing.operations.junction import JunctionOperation
from autodrive_editor.i18n import tr
from autodrive_editor.rendering.connections.connection_data import ConnectionData
from autodrive_editor.ui.tools.map_tool import MapTool, is_alive_in_scene


class JunctionTool(MapTool):
    """Pressing on a road connection and dragging away from the road previews a junction there;
    release adds it to the plan. Dragging elsewhere pans, Esc cancels."""

    def __init__(
        self,
        view,
        operation: JunctionOperation,
        connection_at: Callable[[QPoint], ConnectionData | None],
        color_provider: Callable[[], tuple[int, int, int]],
        missing_costmap_message: Callable[[], str | None],
        z_value: float,
    ):
        super().__init__(view)

        self.operation = operation
        self._connection_at = connection_at
        self._color_provider = color_provider
        self._missing_costmap_message = missing_costmap_message
        self._z_value = z_value
        self._dragging = False
        self._item: QGraphicsPathItem | None = None

        operation.preview_changed.connect(self._update_preview)

    def deactivate(self):
        super().deactivate()
        self._dragging = False

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()
        connection = self._connection_at(position)

        if connection is not None:
            scene_position = self.view.mapToScene(position)
            self._dragging = self.operation.start(
                connection.source_id, connection.target_id, scene_position.x(), scene_position.y()
            )

            if self._dragging:
                return True

        self._begin_pan(event)

        return True

    def mouse_move(self, event: QMouseEvent) -> bool:
        if self._dragging and event.buttons() & Qt.LeftButton:
            scene_position = self.view.mapToScene(event.position().toPoint())
            self.operation.drag_to(scene_position.x(), scene_position.y())
            return True

        return self._continue_pan(event)

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        if self._dragging:
            self._dragging = False
            self.operation.finish()
            return True

        self._end_pan()

        return True

    def cancel(self) -> bool:
        self._dragging = False

        return self.operation.cancel()

    def status_hint(self) -> str | None:
        return self._missing_costmap_message() or tr(
            "Press on a road and drag towards the yard to add a junction; release adds it, Esc "
            "cancels"
        )

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self._dragging or self._connection_at(view_position) is not None:
            return Qt.CrossCursor

        return Qt.OpenHandCursor

    def _update_preview(self):
        preview = self.operation.preview
        path = QPainterPath()

        if preview is not None:
            for curve in preview.plan.curves:
                path.moveTo(*curve.points[0])

                for point in curve.points[1:]:
                    path.lineTo(*point)

            x, z, heading = preview.junction
            path.moveTo(x, z)
            path.lineTo(
                x + preview.stem_length * math.cos(heading),
                z + preview.stem_length * math.sin(heading),
            )

        item = self._item if is_alive_in_scene(self._item, self.view.scene()) else None

        if item is None:
            item = QGraphicsPathItem()
            item.setZValue(self._z_value)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self.view.scene().addItem(item)
            self._item = item

        pen = QPen(QColor(*self._color_provider()), 2.5)
        pen.setCosmetic(True)
        item.setPen(pen)
        item.setPath(path)
        item.setVisible(preview is not None)
