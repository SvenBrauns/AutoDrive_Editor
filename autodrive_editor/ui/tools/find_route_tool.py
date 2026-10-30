from collections.abc import Callable
from itertools import pairwise

from PySide6.QtCore import QLineF, QPoint, QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem

from autodrive_editor.editing.operations.find_route import FindRouteOperation
from autodrive_editor.editing.operations.move_nodes import MoveNodesOperation
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import NodeData
from autodrive_editor.rendering.connections.connection_data import ConnectionData
from autodrive_editor.ui.tools.map_tool import DragGesture, MapTool, is_alive_in_scene

BLOCKED_COLOR = QColor(230, 30, 30)
GUIDE_COLOR = QColor(90, 90, 90)
# The route is drawn faded while a newer one is searched.
OUTDATED_OPACITY = 0.45


class FindRouteTool(MapTool):
    """Left click on a node or free ground adds a waypoint. Left dragging a free waypoint moves
    it, left dragging a node moves the node. Pressing on the route inserts a waypoint there,
    which a drag moves at once. Left dragging elsewhere pans. Right click on a
    waypoint removes it, Backspace the last one. Esc removes all waypoints, Enter adds the
    route to the plan."""

    RIGHT_CLICK_CANCELS = False

    HANDLE_RADIUS = 6.0
    HANDLE_GRAB_DISTANCE = 9.0

    def __init__(
        self,
        view,
        operation: FindRouteOperation,
        move_nodes_operation: MoveNodesOperation,
        node_at: Callable[[QPoint], NodeData | None],
        connection_at: Callable[[QPoint], ConnectionData | None],
        color_provider: Callable[[], tuple[int, int, int]],
        z_value: float,
    ):
        super().__init__(view)

        self.operation = operation
        self.move_nodes_operation = move_nodes_operation
        self._node_at = node_at
        self._connection_at = connection_at
        self._color_provider = color_provider
        self._z_value = z_value

        self._active = False
        self._dragged_waypoint: int | None = None
        self._node_drag = DragGesture()
        self._pressed_node_id: int | None = None

        self._route_item: QGraphicsPathItem | None = None
        self._blocked_item: QGraphicsPathItem | None = None
        self._guide_item: QGraphicsPathItem | None = None
        self._handle_items: list[QGraphicsEllipseItem] = []

        operation.preview_changed.connect(self._update_preview)

    def activate(self):
        self._active = True
        self._update_preview()

    def deactivate(self):
        super().deactivate()

        self._active = False
        self.operation.clear()

    def mouse_press(self, event: QMouseEvent) -> bool:
        position = event.position().toPoint()

        if event.button() == Qt.RightButton:
            index = self._waypoint_at(position)

            if index is not None:
                self.operation.remove_waypoint(index)
            else:
                self.cancel()

            return True

        if event.button() != Qt.LeftButton:
            return False

        self._dragged_waypoint = self._waypoint_at(position, free_only=True)

        if self._dragged_waypoint is not None:
            return True

        node = self._node_at(position)

        if node is not None and self.move_nodes_operation.begin_drag(position):
            self._pressed_node_id = node.node_id
            self._node_drag.press(Qt.LeftButton, position)
            return True

        scene_position = self.view.mapToScene(position)
        leg = self._leg_at(position)

        if leg is not None:
            self.operation.insert_waypoint(leg + 1, scene_position.x(), scene_position.y())
            self._dragged_waypoint = leg + 1
            return True

        self._begin_pan(event)

        return True

    def mouse_move(self, event: QMouseEvent) -> bool:
        position = event.position().toPoint()

        if self._dragged_waypoint is not None and event.buttons() & Qt.LeftButton:
            scene_position = self.view.mapToScene(position)
            self.operation.move_waypoint(
                self._dragged_waypoint, scene_position.x(), scene_position.y()
            )
            return True

        if self._node_drag.is_pressed:
            if self._node_drag.move(position) is not None:
                self.move_nodes_operation.update_drag(
                    position, axis_lock=bool(event.modifiers() & Qt.ShiftModifier)
                )
            return True

        return self._continue_pan(event)

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return event.button() == Qt.RightButton

        if self._dragged_waypoint is not None:
            self._dragged_waypoint = None
            return True

        if self._node_drag.is_pressed:
            dragged = self._node_drag.is_dragging
            self._node_drag.reset()

            if dragged:
                self.move_nodes_operation.finish_drag()
            else:
                self.move_nodes_operation.cancel_drag()
                self._add_waypoint(node_id=self._pressed_node_id)

            self._pressed_node_id = None
            return True

        # Only a click adds a waypoint. Releasing after a pan does nothing.
        if not self._end_pan():
            position = event.position().toPoint()
            scene_position = self.view.mapToScene(position)
            connection = self._connection_at(position)

            if connection is not None and self.operation.missing_costmap_message() is None:
                self.operation.add_waypoint_on_connection(
                    connection.source_id,
                    connection.target_id,
                    scene_position.x(),
                    scene_position.y(),
                )
            else:
                self._add_waypoint(scene_position.x(), scene_position.y())

        return True

    def cancel(self) -> bool:
        if self._node_drag.is_pressed:
            self._node_drag.reset()
            self._pressed_node_id = None
            self.move_nodes_operation.cancel_drag()
            return True

        self._dragged_waypoint = None

        return self.operation.clear()

    def confirm(self) -> bool:
        return self.operation.apply()

    def remove_last(self) -> bool:
        if not self.operation.waypoints:
            return False

        self.operation.remove_waypoint(len(self.operation.waypoints) - 1)

        return True

    def status_hint(self) -> str | None:
        return self.operation.missing_costmap_message() or tr(
            "Click nodes, connections or free ground as waypoints; drag waypoints or nodes to "
            "change the route. Right-click or Backspace removes waypoints, Enter adds the route"
        )

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self._node_drag.is_dragging or self._dragged_waypoint is not None:
            return Qt.SizeAllCursor

        if self._waypoint_at(view_position, free_only=True) is not None:
            return Qt.SizeAllCursor

        if not self.view.has_node_at(view_position) and self._leg_at(view_position) is not None:
            return Qt.SizeAllCursor

        if self.view.has_node_at(view_position) or self._connection_at(view_position) is not None:
            return Qt.PointingHandCursor

        return Qt.CrossCursor

    def _add_waypoint(self, x: float = 0.0, z: float = 0.0, node_id: int | None = None):
        message = self.operation.missing_costmap_message()

        if message is not None:
            self.operation.status_changed.emit(message)
            return

        self.operation.add_waypoint(x, z, node_id)

    def _leg_at(self, view_position: QPoint) -> int | None:
        scene_position = self.view.mapToScene(view_position)
        tolerance = self.HANDLE_GRAB_DISTANCE / max(self.view.zoom_level, 1e-6)

        return self.operation.leg_at(scene_position.x(), scene_position.y(), tolerance)

    def _waypoint_at(self, view_position: QPoint, free_only: bool = False) -> int | None:
        for index, waypoint in reversed(list(enumerate(self.operation.waypoints))):
            if free_only and not waypoint.is_free:
                continue

            handle_position = self.view.mapFromScene(QPointF(waypoint.x, waypoint.z))

            if QLineF(handle_position, view_position).length() <= self.HANDLE_GRAB_DISTANCE:
                return index

        return None

    def _update_preview(self):
        if not self._active:
            self._hide_preview()
            return

        waypoints = self.operation.waypoints
        route = self.operation.shown_route if len(waypoints) > 1 else None
        clear_path, blocked_path = QPainterPath(), QPainterPath()

        if route is not None:
            for (a, b), blocked in zip(
                pairwise(route.points), pairwise(route.blocked), strict=False
            ):
                path = blocked_path if any(blocked) else clear_path
                path.moveTo(*a)
                path.lineTo(*b)

        opacity = 1.0 if self.operation.route is not None else OUTDATED_OPACITY
        self._route_item = self._show(
            self._route_item, clear_path, QPen(QColor(*self._color_provider()), 2.5), opacity
        )
        self._blocked_item = self._show(
            self._blocked_item, blocked_path, QPen(BLOCKED_COLOR, 4.0), opacity
        )

        guide = QPainterPath()

        for index, waypoint in enumerate(waypoints):
            if index == 0:
                guide.moveTo(waypoint.x, waypoint.z)
            else:
                guide.lineTo(waypoint.x, waypoint.z)

        self._guide_item = self._show(self._guide_item, guide, QPen(GUIDE_COLOR, 1.0, Qt.DotLine))
        self._update_handles()

    def _update_handles(self):
        waypoints = self.operation.waypoints
        self._handle_items = [item for item in self._handle_items if self._valid(item)]

        while len(self._handle_items) < len(waypoints):
            self._handle_items.append(self._new_handle_item())

        for index, item in enumerate(self._handle_items):
            item.setVisible(index < len(waypoints))

            if index < len(waypoints):
                waypoint = waypoints[index]
                item.setPos(waypoint.x, waypoint.z)
                # Free waypoints are filled white, waypoints on nodes or connections only ringed.
                filled = waypoint.is_free
                item.setBrush(QBrush(QColor(255, 255, 255)) if filled else QBrush(Qt.NoBrush))

    def _new_handle_item(self) -> QGraphicsEllipseItem:
        radius = self.HANDLE_RADIUS
        item = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)

        # Same size on screen at every zoom level.
        item.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        item.setPen(QPen(QColor(30, 30, 30), 1.5))
        item.setZValue(self._z_value + 1)
        item.setAcceptedMouseButtons(Qt.NoButton)
        self.view.scene().addItem(item)

        return item

    def _show(self, item, path: QPainterPath, pen: QPen, opacity: float = 1.0):
        """Shows the path in the overlay item, created again if loading data deleted it."""

        item = self._valid(item)

        if item is None:
            item = QGraphicsPathItem()
            item.setZValue(self._z_value)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self.view.scene().addItem(item)

        pen.setCosmetic(True)
        item.setPen(pen)
        item.setPath(path)
        item.setOpacity(opacity)
        item.setVisible(True)

        return item

    def _hide_preview(self):
        for item in (self._route_item, self._blocked_item, self._guide_item, *self._handle_items):
            if self._valid(item) is not None:
                item.setVisible(False)

    def _valid(self, item):
        return item if is_alive_in_scene(item, self.view.scene()) else None
