import math
from collections.abc import Callable

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem

from autodrive_editor.editing.junction import lane_poses
from autodrive_editor.editing.operations.junction import JunctionOperation
from autodrive_editor.i18n import tr
from autodrive_editor.rendering.connections.connection_data import ConnectionData
from autodrive_editor.ui.tools.map_tool import MapTool, is_alive_in_scene


class JunctionTool(MapTool):
    """Junction task in two steps. Step 1: pressing on a road connection and dragging previews
    a junction; moving along the road moves it. Step 2, after release: a handle at the stem's
    tip bends the stem when dragged and joins a node it is dropped on. Enter or a click away
    from the handle adds the junction to the plan, Esc cancels. Dragging elsewhere in step 1
    pans."""

    # Radius of the tip handle, in pixels.
    HANDLE_RADIUS = 6

    def __init__(
        self,
        view,
        operation: JunctionOperation,
        connection_at: Callable[[QPoint], ConnectionData | None],
        node_at: Callable[[QPoint], int | None],
        color_provider: Callable[[], tuple[int, int, int]],
        missing_costmap_message: Callable[[], str | None],
        z_value: float,
    ):
        super().__init__(view)

        self.operation = operation
        self._connection_at = connection_at
        self._node_at = node_at
        self._color_provider = color_provider
        self._missing_costmap_message = missing_costmap_message
        self._z_value = z_value
        self._dragging = False
        self._dragging_tip = False
        self._item: QGraphicsPathItem | None = None
        self._handle: QGraphicsEllipseItem | None = None

        operation.preview_changed.connect(self._update_preview)

    def deactivate(self):
        super().deactivate()
        self._dragging = self._dragging_tip = False

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        if self.operation.is_bending:
            if self._is_on_handle(position):
                self._dragging_tip = True
            else:
                self.operation.finish()

            return True

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
        if not event.buttons() & Qt.LeftButton:
            return self._continue_pan(event)

        position = event.position().toPoint()
        scene_position = self.view.mapToScene(position)

        if self._dragging:
            self.operation.drag_to(scene_position.x(), scene_position.y())
            return True

        if self._dragging_tip:
            self.operation.bend_to(scene_position.x(), scene_position.y(), self._node_at(position))
            return True

        return self._continue_pan(event)

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        if self._dragging:
            self._dragging = False
            self.operation.release()
            self._update_preview()
            return True

        if self._dragging_tip:
            self._dragging_tip = False
            return True

        self._end_pan()

        return True

    def cancel(self) -> bool:
        self._dragging = self._dragging_tip = False

        return self.operation.cancel()

    def confirm(self) -> bool:
        if not self.operation.is_bending:
            return False

        self._dragging_tip = False
        self.operation.finish()

        return True

    def status_hint(self) -> str | None:
        if self.operation.is_bending:
            return tr(
                "Drag the handle to bend the stem, drop it on a node to join it; Enter or a click "
                "elsewhere adds the junction, Esc cancels"
            )

        return self._missing_costmap_message() or tr(
            "Press on a road and drag towards the yard to place a junction, Esc cancels"
        )

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.operation.is_bending:
            return Qt.SizeAllCursor if self._is_on_handle(view_position) else Qt.ArrowCursor

        if self._dragging or self._connection_at(view_position) is not None:
            return Qt.CrossCursor

        return Qt.OpenHandCursor

    def _is_on_handle(self, view_position: QPoint) -> bool:
        preview = self.operation.preview

        if preview is None:
            return False

        tip = self.view.mapFromScene(QPointF(*preview.stem[-1][:2]))

        return math.dist((tip.x(), tip.y()), (view_position.x(), view_position.y())) <= (
            self.HANDLE_RADIUS + 3
        )

    def _update_preview(self):
        preview = self.operation.preview
        path = QPainterPath()

        if preview is not None:
            for line in preview.plan.paths():
                path.moveTo(*line[0])

                for point in line[1:]:
                    path.lineTo(*point)

            for index in range(2 if preview.gap > 0 else 1):
                points = [
                    lane_poses(pose, preview.gap)[index][:2] if preview.gap > 0 else pose[:2]
                    for pose in preview.stem
                ]
                path.moveTo(*points[0])

                for point in points[1:]:
                    path.lineTo(*point)

        color = QColor(*self._color_provider())
        pen = QPen(color, 2.5)
        pen.setCosmetic(True)
        item = self._path_item()
        item.setPen(pen)
        item.setPath(path)
        item.setVisible(preview is not None)

        handle = self._handle_item()
        handle.setPen(pen)
        handle.setVisible(preview is not None and self.operation.is_bending)

        if preview is not None:
            handle.setPos(*preview.stem[-1][:2])

    def _path_item(self) -> QGraphicsPathItem:
        if not is_alive_in_scene(self._item, self.view.scene()):
            self._item = QGraphicsPathItem()
            self._item.setZValue(self._z_value)
            self._item.setAcceptedMouseButtons(Qt.NoButton)
            self.view.scene().addItem(self._item)

        return self._item

    def _handle_item(self) -> QGraphicsEllipseItem:
        if not is_alive_in_scene(self._handle, self.view.scene()):
            radius = self.HANDLE_RADIUS
            self._handle = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
            self._handle.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            self._handle.setZValue(self._z_value + 0.1)
            self._handle.setAcceptedMouseButtons(Qt.NoButton)
            self.view.scene().addItem(self._handle)

        return self._handle
