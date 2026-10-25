import math

from PySide6.QtCore import (
    QPoint,
    QPointF,
    QRectF,
    Qt
)
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPen
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsLineItem
)

from editing.selection_rotate_coordinator import (
    SelectionRotateCoordinator
)
from ui.map_tools.map_tool import (
    DragGesture,
    MapTool,
    is_alive_in_scene
)


class RotateSelectionTool(MapTool):
    """Shows a ring around the average center of the selection (at
    least two nodes). Dragging the ring rotates the selection, Shift
    snaps to 15° steps and Esc cancels. Dragging elsewhere pans."""

    RING_COLOR = QColor(255, 190, 0)

    # In screen pixels, so the ring is easy to grab at any zoom.
    RING_PADDING_PX = 24.0
    MIN_RING_RADIUS_PX = 40.0
    RING_GRAB_TOLERANCE_PX = 8.0
    CENTER_MARK_SIZE_PX = 6.0

    def __init__(
        self,
        view,
        selection_rotate_coordinator: SelectionRotateCoordinator,
        z_value: float
    ):
        super().__init__(
            view
        )

        self.coordinator = selection_rotate_coordinator

        self._z_value = z_value
        self._rotation_drag = DragGesture()
        self._overlay: QGraphicsItemGroup | None = None
        self._is_active = False

        # Center and radius of the ring in scene coordinates.
        self._ring: tuple[QPointF, float] | None = None

        self.coordinator.target_changed.connect(
            self._refresh_ring
        )

        self.view.zoom_changed.connect(
            lambda zoom_level: self._refresh_ring()
        )

    @property
    def ring(self) -> tuple[QPointF, float] | None:
        """Center and radius of the shown ring, or None."""

        return self._ring

    def activate(self):
        self._is_active = True
        self._refresh_ring()

    def status_hint(self) -> str | None:
        if self._ring is None:
            return "Zum Rotieren mindestens zwei Nodes auswählen"

        return (
            "Ring ziehen zum Drehen, Umschalt rastet in "
            "15°-Schritten ein. Esc bricht ab"
        )

    def deactivate(self):
        super().deactivate()

        self._is_active = False
        self._refresh_ring()

    def mouse_press(
        self,
        event: QMouseEvent
    ) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        position = event.position().toPoint()

        if (
            self.is_on_ring(position)
            and self.coordinator.begin_rotation(
                self.view.mapToScene(position)
            )
        ):
            self._rotation_drag.press(
                Qt.LeftButton,
                position
            )

            return True

        return super().mouse_press(
            event
        )

    def mouse_move(
        self,
        event: QMouseEvent
    ) -> bool:
        if not self._rotation_drag.is_pressed:
            return super().mouse_move(
                event
            )

        position = event.position().toPoint()

        if self._rotation_drag.move(position) is not None:
            self.coordinator.update_rotation(
                self.view.mapToScene(position),
                snap=bool(
                    event.modifiers() & Qt.ShiftModifier
                )
            )

        return True

    def mouse_release(
        self,
        event: QMouseEvent
    ) -> bool:
        if (
            event.button() == Qt.LeftButton
            and self._rotation_drag.is_pressed
        ):
            self._rotation_drag.reset()

            self.coordinator.finish_rotation()

            return True

        return super().mouse_release(
            event
        )

    def cancel(self) -> bool:
        if not self._rotation_drag.is_pressed:
            return False

        self._rotation_drag.reset()

        self.coordinator.cancel_rotation()

        return True

    def cursor_at(
        self,
        view_position: QPoint
    ) -> Qt.CursorShape:
        if self._rotation_drag.is_dragging:
            return Qt.ClosedHandCursor

        if self._pan.is_dragging:
            return Qt.ClosedHandCursor

        if self.is_on_ring(view_position):
            return Qt.PointingHandCursor

        return Qt.OpenHandCursor

    def is_on_ring(
        self,
        view_position: QPoint
    ) -> bool:
        if self._ring is None:
            return False

        center, radius = self._ring

        scene_position = self.view.mapToScene(
            view_position
        )

        distance = math.hypot(
            scene_position.x() - center.x(),
            scene_position.y() - center.y()
        )

        return (
            abs(distance - radius)
            * self.view.zoom_level
            <= self.RING_GRAB_TOLERANCE_PX
        )

    def _refresh_ring(self):
        target = (
            self.coordinator.rotation_target()
            if self._is_active
            else None
        )

        if target is None:
            self._ring = None
            self._hide_overlay()
            return

        center, node_radius = target

        zoom_level = max(
            self.view.zoom_level,
            1e-6
        )

        radius = max(
            node_radius
            + self.RING_PADDING_PX / zoom_level,
            self.MIN_RING_RADIUS_PX / zoom_level
        )

        self._ring = (
            QPointF(center),
            radius
        )

        self._draw_overlay(
            center,
            radius,
            self.CENTER_MARK_SIZE_PX / zoom_level
        )

    def _draw_overlay(
        self,
        center: QPointF,
        radius: float,
        mark_size: float
    ):
        if not is_alive_in_scene(
            self._overlay,
            self.view.scene()
        ):
            self._create_overlay()

        ring, horizontal, vertical = self._overlay.childItems()

        ring.setRect(
            QRectF(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2
            )
        )

        horizontal.setLine(
            center.x() - mark_size,
            center.y(),
            center.x() + mark_size,
            center.y()
        )

        vertical.setLine(
            center.x(),
            center.y() - mark_size,
            center.x(),
            center.y() + mark_size
        )

        self._overlay.setVisible(
            True
        )

    def _create_overlay(self):
        pen = QPen(
            self.RING_COLOR
        )

        pen.setCosmetic(
            True
        )

        pen.setWidthF(
            2.0
        )

        self._overlay = QGraphicsItemGroup()
        self._overlay.setZValue(self._z_value)
        self._overlay.setAcceptedMouseButtons(Qt.NoButton)

        for item in (
            QGraphicsEllipseItem(),
            QGraphicsLineItem(),
            QGraphicsLineItem()
        ):
            item.setPen(pen)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self._overlay.addToGroup(item)

        self.view.scene().addItem(
            self._overlay
        )

    def _hide_overlay(self):
        if is_alive_in_scene(
            self._overlay,
            self.view.scene()
        ):
            self._overlay.setVisible(
                False
            )
