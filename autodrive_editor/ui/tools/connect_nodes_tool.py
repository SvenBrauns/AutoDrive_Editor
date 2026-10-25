from collections.abc import Callable

from PySide6.QtCore import QLineF, QPoint, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsLineItem

from autodrive_editor.editing.operations.connect_nodes import NodeConnectCoordinator
from autodrive_editor.rendering.connections.connection_data import ConnectionType
from autodrive_editor.ui.tools.map_tool import MapTool, is_alive_in_scene


class ConnectNodesTool(MapTool):
    """Click nodes one after another to connect them with one
    connection type. A dashed line shows the next connection. Left
    dragging pans; a click on empty map or Esc ends the chain."""

    def __init__(
        self,
        view,
        node_connect_coordinator: NodeConnectCoordinator,
        connection_type: ConnectionType,
        color_provider: Callable[[], tuple[int, int, int]],
        z_value: float,
    ):
        super().__init__(view)

        self.node_connect_coordinator = node_connect_coordinator
        self.connection_type = connection_type

        # Read on every update, so display option changes apply.
        self._color_provider = color_provider

        self._preview_pen = QPen()

        self._preview_pen.setCosmetic(True)

        self._preview_pen.setWidthF(2.0)

        self._preview_pen.setStyle(Qt.DashLine)

        self._preview_z_value = z_value
        self._preview_item: QGraphicsLineItem | None = None

    def deactivate(self):
        super().deactivate()

        self.node_connect_coordinator.end_chain()
        self._hide_preview()

    def mouse_move(self, event: QMouseEvent) -> bool:
        if not self._continue_pan(event):
            self._update_preview(event.position().toPoint())

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        # Only a click connects. Releasing after a pan does nothing.
        if not self._end_pan():
            self.node_connect_coordinator.click(position, self.connection_type)

        self._update_preview(position)

        return True

    def cancel(self) -> bool:
        cancelled = self.node_connect_coordinator.end_chain()

        self._hide_preview()

        return cancelled

    def status_hint(self) -> str | None:
        return (
            "Start-Node, dann weitere Nodes anklicken. Gleicher Typ "
            "entfernt eine Connection. Esc beendet"
        )

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.view.has_selectable_item_at(view_position):
            return Qt.PointingHandCursor

        if self.node_connect_coordinator.start_node is not None:
            return Qt.CrossCursor

        return Qt.OpenHandCursor

    @property
    def preview_line(self) -> QLineF | None:
        """The preview line in scene coordinates, if it is shown."""

        item = self._valid_preview_item()

        if item is None or not item.isVisible():
            return None

        return item.line()

    def _update_preview(self, view_position: QPoint):
        start_node = self.node_connect_coordinator.start_node

        if start_node is None:
            self._hide_preview()
            return

        item = self._valid_preview_item()

        self._preview_pen.setColor(QColor(*self._color_provider()))

        if item is None:
            item = QGraphicsLineItem()
            item.setZValue(self._preview_z_value)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self.view.scene().addItem(item)
            self._preview_item = item

        mouse_scene_position = self.view.mapToScene(view_position)

        item.setLine(start_node.x, start_node.z, mouse_scene_position.x(), mouse_scene_position.y())

        item.setPen(self._preview_pen)

        item.setVisible(True)

    def _hide_preview(self):
        item = self._valid_preview_item()

        if item is not None:
            item.setVisible(False)

    def _valid_preview_item(self) -> QGraphicsLineItem | None:
        if not is_alive_in_scene(self._preview_item, self.view.scene()):
            self._preview_item = None

        return self._preview_item
