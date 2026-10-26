from collections.abc import Callable

from PySide6.QtCore import QLineF, QPoint, QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem

from autodrive_editor.editing.operations.create_path import CreatePathOperation
from autodrive_editor.editing.path_shapes import PathShape
from autodrive_editor.i18n import tr
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.ui.tools.map_tool import MapTool, is_alive_in_scene

HINTS = {
    PathShape.LINE: tr("Click start and end (node or free ground). Esc finishes"),
    PathShape.BEZIER: tr("Click start and end, then drag the handles. Enter creates the curve"),
    PathShape.ARC: tr("Click start and end, then drag the handle. Enter creates the arc"),
}


class PathTool(MapTool):
    """Draws a line, Bézier curve or circular arc of evenly spaced nodes.
    A dashed preview shows the new nodes; curve handles are dragged with
    the left button. Left dragging elsewhere pans."""

    # Handle size and how far from its centre a press still grabs it, in pixels.
    HANDLE_RADIUS = 6.0
    HANDLE_GRAB_DISTANCE = 9.0

    def __init__(
        self,
        view,
        operation: CreatePathOperation,
        shape: PathShape,
        color_provider: Callable[[ConnectionType], tuple[int, int, int]],
        node_diameter: float,
        z_value: float,
    ):
        super().__init__(view)

        self.operation = operation
        self.shape = shape
        self._color_provider = color_provider
        self._node_diameter = node_diameter
        self._z_value = z_value

        self._active = False
        self._mouse_position: QPoint | None = None
        self._dragged_handle: int | None = None

        self._path_item: QGraphicsPathItem | None = None
        self._guide_item: QGraphicsPathItem | None = None
        self._handle_items: list[QGraphicsEllipseItem] = []

        operation.preview_changed.connect(self._update_preview)

    def activate(self):
        self._active = True
        self.operation.set_shape(self.shape)

    def deactivate(self):
        super().deactivate()

        self._active = False
        self._dragged_handle = None
        self.operation.reset()
        self._update_preview()

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        self._dragged_handle = self._handle_at(event.position().toPoint())

        if self._dragged_handle is None:
            self._begin_pan(event)

        return True

    def mouse_move(self, event: QMouseEvent) -> bool:
        position = event.position().toPoint()
        self._mouse_position = position

        if self._dragged_handle is not None and event.buttons() & Qt.LeftButton:
            scene_position = self.view.mapToScene(position)
            self.operation.move_handle(self._dragged_handle, scene_position.x(), scene_position.y())

        elif not self._continue_pan(event):
            self._update_preview()

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        if self._dragged_handle is not None:
            self._dragged_handle = None
            return True

        # Only a click sets a point. Releasing after a pan does nothing.
        if not self._end_pan():
            self.operation.click(event.position().toPoint())

        return True

    def cancel(self) -> bool:
        return self.operation.cancel()

    def confirm(self) -> bool:
        return self.operation.apply()

    def status_hint(self) -> str | None:
        return HINTS[self.shape]

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging or self._dragged_handle is not None:
            return Qt.ClosedHandCursor

        if self._handle_at(view_position) is not None:
            return Qt.OpenHandCursor

        if self.view.has_selectable_item_at(view_position):
            return Qt.PointingHandCursor

        return Qt.CrossCursor

    @property
    def preview_path(self) -> QPainterPath | None:
        """The dashed preview in scene coordinates, if it is shown."""

        item = self._valid(self._path_item)

        if item is None or not item.isVisible():
            return None

        return item.path()

    def _handle_at(self, view_position: QPoint) -> int | None:
        for index, (x, z) in enumerate(self.operation.handles):
            handle_position = self.view.mapFromScene(QPointF(x, z))

            if QLineF(handle_position, view_position).length() <= self.HANDLE_GRAB_DISTANCE:
                return index

        return None

    def _update_preview(self):
        if not self._active:
            self._hide_preview()
            return

        mouse_end = None

        if self._mouse_position is not None and not self.operation.is_adjusting:
            mouse_end = self.operation.end_at(self._mouse_position)

        points = self.operation.preview_points(mouse_end)

        if not points:
            self._hide_preview()
            return

        color = QColor(*self._color_provider(self.operation.options.connection_type))

        path = QPainterPath(QPointF(*points[0]))

        for point in points[1:]:
            path.lineTo(QPointF(*point))

        radius = self._node_diameter / 2

        for x, z in points:
            path.addEllipse(QPointF(x, z), radius, radius)

        pen = QPen(color, 2.0, Qt.DashLine)
        pen.setCosmetic(True)

        path_item = self._path_item = self._item(self._path_item)
        path_item.setPath(path)
        path_item.setPen(pen)
        path_item.setVisible(True)

        self._update_guides()

    def _update_guides(self):
        """Thin lines from the curve ends to the Bézier control points, and
        the handles themselves."""

        handles = self.operation.handles
        start, end = self.operation.start, self.operation.end

        guide = QPainterPath()

        if self.shape == PathShape.BEZIER and handles and start and end:
            guide.moveTo(start.x, start.z)
            guide.lineTo(*handles[0])
            guide.moveTo(end.x, end.z)
            guide.lineTo(*handles[1])

        pen = QPen(QColor(90, 90, 90), 1.0, Qt.DotLine)
        pen.setCosmetic(True)

        guide_item = self._guide_item = self._item(self._guide_item)
        guide_item.setPath(guide)
        guide_item.setPen(pen)
        guide_item.setVisible(True)

        self._handle_items = [item for item in self._handle_items if self._valid(item)]

        while len(self._handle_items) < len(handles):
            self._handle_items.append(self._new_handle_item())

        for index, item in enumerate(self._handle_items):
            item.setVisible(index < len(handles))

            if index < len(handles):
                item.setPos(*handles[index])

    def _new_handle_item(self) -> QGraphicsEllipseItem:
        radius = self.HANDLE_RADIUS
        item = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)

        # Same size on screen at every zoom level.
        item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        item.setBrush(QBrush(QColor(255, 255, 255)))
        item.setPen(QPen(QColor(30, 30, 30), 1.5))
        item.setZValue(self._z_value + 1)
        item.setAcceptedMouseButtons(Qt.NoButton)
        self.view.scene().addItem(item)

        return item

    def _item(self, item: QGraphicsPathItem | None) -> QGraphicsPathItem:
        """The overlay item, created again if loading data deleted it."""

        item = self._valid(item)

        if item is None:
            item = QGraphicsPathItem()
            item.setZValue(self._z_value)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self.view.scene().addItem(item)

        return item

    def _hide_preview(self):
        for item in (self._path_item, self._guide_item, *self._handle_items):
            if self._valid(item) is not None:
                item.setVisible(False)

    def _valid(self, item):
        return item if is_alive_in_scene(item, self.view.scene()) else None
