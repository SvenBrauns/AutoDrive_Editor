from dataclasses import dataclass, field

from PySide6.QtCore import (
    QPoint,
    QRectF,
    Qt,
    Signal
)
from PySide6.QtGui import (
    QCursor,
    QMouseEvent,
    QResizeEvent,
    QWheelEvent,
    QKeyEvent
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsView
)

from ui.interaction_mode import InteractionMode
from ui.view_rotation_controller import (
    ViewRotationController
)
from ui.view_zoom_controller import (
    ViewZoomController
)
from ui.view_selection_controller import (
    ViewSelectionController
)


@dataclass
class PointerDragState:

    pressed_button: Qt.MouseButton = Qt.NoButton
    drag_active: bool = False

    press_position: QPoint = field(
        default_factory=QPoint
    )

    last_position: QPoint = field(
        default_factory=QPoint
    )

    def begin(
        self,
        button: Qt.MouseButton,
        position: QPoint
    ):
        self.pressed_button = button
        self.drag_active = False

        self.press_position = QPoint(
            position
        )

        self.last_position = QPoint(
            position
        )

    def reset(self):
        self.pressed_button = Qt.NoButton
        self.drag_active = False

        self.press_position = QPoint()
        self.last_position = QPoint()


class MapView(QGraphicsView):

    zoom_changed = Signal(
        float
    )

    rotation_changed = Signal(
        float
    )

    rotation_step_changed = Signal(
        float
    )

    visible_scene_rect_changed = Signal(
        QRectF
    )

    interaction_mode_changed = Signal(
        object
    )

    selection_click_requested = Signal(
        QPoint,
        object
    )

    selection_area_requested = Signal(
        object,
        object
    )

    selection_area_preview_requested = Signal(
        object,
        object
    )

    selection_area_preview_cleared = Signal()

    measurement_press_requested = Signal(
        QPoint,
        object
    )

    measurement_move_requested = Signal(
        QPoint,
        object
    )

    measurement_release_requested = Signal(
        QPoint,
        object
    )

    measurement_cancel_requested = Signal()

    def __init__(self):
        super().__init__()

        self._interaction_mode = (
            InteractionMode.NAVIGATE
        )

        self._measurement_active = False
        self._measurement_point_drag_active = False

        self._pointer_state = (
            PointerDragState()
        )

        self._configure_view()

        self._selection_controller = (
            ViewSelectionController(
                view=self,
                parent=self
            )
        )

        self._selection_controller.area_requested.connect(
            self.selection_area_requested.emit
        )

        self._selection_controller.area_preview_requested.connect(
            self.selection_area_preview_requested.emit
        )

        self._selection_controller.area_preview_cleared.connect(
            self.selection_area_preview_cleared.emit
        )

        self._zoom_controller = (
            ViewZoomController(
                view=self,
                parent=self
            )
        )

        self._zoom_controller.zoom_changed.connect(
            self.zoom_changed.emit
        )

        self._zoom_controller.visible_scene_rect_changed.connect(
            self.visible_scene_rect_changed.emit
        )

        self._rotation_controller = (
            ViewRotationController(
                view=self,
                viewport_update_callback=(
                    self._zoom_controller
                    .schedule_viewport_update
                ),
                parent=self
            )
        )

        self._rotation_controller.rotation_changed.connect(
            self.rotation_changed.emit
        )

        self._rotation_controller.rotation_step_changed.connect(
            self.rotation_step_changed.emit
        )

        self._apply_interaction_mode()

    @property
    def zoom_level(self) -> float:
        return (
            self._zoom_controller
            .zoom_level
        )

    @property
    def rotation_angle(self) -> float:
        return (
            self._rotation_controller
            .rotation_angle
        )

    @property
    def rotation_step(self) -> float:
        return (
            self._rotation_controller
            .rotation_step
        )

    @property
    def interaction_mode(
        self
    ) -> InteractionMode:
        return self._interaction_mode

    @property
    def measurement_active(self) -> bool:
        return self._measurement_active

    def set_zoom_level(
        self,
        zoom_level
    ):
        self._zoom_controller.set_zoom_level(
            zoom_level
        )

    def set_rotation_angle(
        self,
        rotation_angle: float
    ):
        self._rotation_controller.set_rotation_angle(
            rotation_angle
        )

    def set_exact_rotation_angle(
        self,
        rotation_angle: float
    ):
        self._rotation_controller.set_exact_rotation_angle(
            rotation_angle
        )

    def set_rotation_step(
        self,
        rotation_step: float
    ):
        self._rotation_controller.set_rotation_step(
            rotation_step
        )

    def reset_view_rotation(self):
        self._rotation_controller.reset_rotation()

    def set_interaction_mode(
        self,
        interaction_mode: InteractionMode
    ):
        if not isinstance(
            interaction_mode,
            InteractionMode
        ):
            raise TypeError(
                "Der Interaktionsmodus ist ungültig."
            )

        if (
            interaction_mode
            == self._interaction_mode
        ):
            return

        if (
            interaction_mode
            != InteractionMode.SELECT
        ):
            self._selection_controller.cancel()

        self._interaction_mode = (
            interaction_mode
        )

        self._apply_interaction_mode()

        self.interaction_mode_changed.emit(
            interaction_mode
        )

    def set_measurement_active(
        self,
        active: bool
    ):
        active = bool(
            active
        )

        if active == self._measurement_active:
            return

        self._measurement_active = active
        self._measurement_point_drag_active = False

        self._selection_controller.cancel()

        self._pointer_state.reset()

        self._restore_interaction_cursor()

    def set_measurement_point_drag_active(
        self,
        active: bool
    ):
        self._measurement_point_drag_active = bool(
            active
        )

    def get_visible_scene_rect(
        self
    ) -> QRectF:
        return (
            self._zoom_controller
            .get_visible_scene_rect()
        )

    def fitInView(
        self,
        *args
    ):
        super().fitInView(
            *args
        )

        self._zoom_controller.notify_transform_changed()

    def wheelEvent(
        self,
        event: QWheelEvent
    ):
        zoom_handled = (
            self._zoom_controller
            .zoom_by_wheel_delta(
                wheel_delta=(
                    event.angleDelta().y()
                ),
                view_position=(
                    event.position().toPoint()
                )
            )
        )

        if zoom_handled:
            event.accept()

        else:
            event.ignore()

    def resizeEvent(
        self,
        event: QResizeEvent
    ):
        super().resizeEvent(
            event
        )

        self._zoom_controller.schedule_viewport_update()

    def mousePressEvent(
        self,
        event: QMouseEvent
    ):
        pressed_button = event.button()

        mouse_position = (
            event.position().toPoint()
        )

        if (
            self._measurement_active
            and pressed_button == Qt.LeftButton
        ):
            self._handle_measurement_press(
                mouse_position,
                event.modifiers()
            )

            event.accept()
            return

        supported_button = (
            pressed_button
            in (
                Qt.LeftButton,
                Qt.MiddleButton
            )
        )

        right_selection_button = (
            pressed_button == Qt.RightButton
            and self._interaction_mode
            == InteractionMode.SELECT
            and not self._measurement_active
        )

        if (
            not supported_button
            and not right_selection_button
        ):
            super().mousePressEvent(
                event
            )
            return

        self._pointer_state.begin(
            button=pressed_button,
            position=mouse_position
        )

        if right_selection_button:
            self._selection_controller.begin(
                mouse_position
            )

        if pressed_button == Qt.MiddleButton:
            self.viewport().setCursor(
                Qt.SizeAllCursor
            )

        event.accept()

    def mouseMoveEvent(
        self,
        event: QMouseEvent
    ):
        mouse_position = (
            event.position().toPoint()
        )

        if self._is_button_drag(
            event,
            Qt.MiddleButton
        ):
            self._handle_rotation_drag(
                mouse_position
            )

            event.accept()
            return

        if self._measurement_active:
            self._handle_measurement_move(
                event,
                mouse_position
            )

            event.accept()
            return

        if self._is_button_drag(
            event,
            Qt.RightButton
        ):
            selection_drag_active = (
                self._selection_controller
                .handle_drag(
                    current_position=mouse_position,
                    modifiers=event.modifiers()
                )
            )

            self._pointer_state.drag_active = (
                selection_drag_active
            )

            if selection_drag_active:
                self.viewport().setCursor(
                    Qt.CrossCursor
                )

            event.accept()
            return

        if self._is_button_drag(
            event,
            Qt.LeftButton
        ):
            self._handle_pan_drag(
                mouse_position
            )

            event.accept()
            return

        self._update_hover_cursor(
            mouse_position
        )

        super().mouseMoveEvent(
            event
        )

    def mouseReleaseEvent(
        self,
        event: QMouseEvent
    ):
        mouse_position = (
            event.position().toPoint()
        )

        if (
            self._measurement_active
            and event.button() == Qt.LeftButton
            and self._pointer_state.pressed_button
            == Qt.LeftButton
        ):
            self._handle_measurement_release(
                mouse_position,
                event.modifiers()
            )

            event.accept()
            return

        if (
            event.button()
            != self._pointer_state.pressed_button
        ):
            super().mouseReleaseEvent(
                event
            )
            return

        released_button = (
            self._pointer_state.pressed_button
        )

        was_dragging = (
            self._pointer_state.drag_active
        )

        if released_button == Qt.RightButton:
            if was_dragging:
                self._selection_controller.finish(
                    event.modifiers()
                )

            else:
                self._selection_controller.cancel()

        self._pointer_state.reset()

        self._restore_interaction_cursor(
            mouse_position
        )

        if (
            released_button == Qt.LeftButton
            and not was_dragging
            and self._interaction_mode
            == InteractionMode.SELECT
        ):
            self.selection_click_requested.emit(
                mouse_position,
                event.modifiers()
            )

        event.accept()

    def keyPressEvent(
        self,
        event: QKeyEvent
    ):
        if (
            self._measurement_active
            and event.key() == Qt.Key_Escape
        ):
            self.measurement_cancel_requested.emit()

            event.accept()
            return

        super().keyPressEvent(
            event
        )

    def _configure_view(self):
        self.setMouseTracking(
            True
        )

        self.viewport().setMouseTracking(
            True
        )

        self.setInteractive(
            False
        )

        self.setDragMode(
            QGraphicsView.NoDrag
        )

        self.setTransformationAnchor(
            QGraphicsView.NoAnchor
        )

        self.setResizeAnchor(
            QGraphicsView.AnchorViewCenter
        )

    def _apply_interaction_mode(self):
        self._restore_interaction_cursor()

    def _handle_measurement_press(
        self,
        mouse_position: QPoint,
        modifiers
    ):
        self._pointer_state.begin(
            button=Qt.LeftButton,
            position=mouse_position
        )

        # The coordinator re-enables this while handling the press
        # if the press hit a draggable measurement point.
        self._measurement_point_drag_active = False

        self.measurement_press_requested.emit(
            mouse_position,
            modifiers
        )

    def _handle_measurement_move(
        self,
        event: QMouseEvent,
        mouse_position: QPoint
    ):
        if not self._is_button_drag(
            event,
            Qt.LeftButton
        ):
            self._emit_measurement_move(
                mouse_position,
                event.modifiers()
            )
            return

        # Left drag on free space pans the map.
        if not self._measurement_point_drag_active:
            self._handle_pan_drag(
                mouse_position
            )
            return

        if (
            not self._pointer_state.drag_active
            and not self._drag_threshold_reached(
                mouse_position
            )
        ):
            return

        self._pointer_state.drag_active = True

        self._emit_measurement_move(
            mouse_position,
            event.modifiers()
        )

    def _emit_measurement_move(
        self,
        mouse_position: QPoint,
        modifiers
    ):
        self.measurement_move_requested.emit(
            mouse_position,
            modifiers
        )

        self._update_hover_cursor(
            mouse_position
        )

    def _handle_measurement_release(
        self,
        mouse_position: QPoint,
        modifiers
    ):
        # Releasing after panning the map is not a measurement click.
        panned_map = (
            self._pointer_state.drag_active
            and not self._measurement_point_drag_active
        )

        if not panned_map:
            self.measurement_release_requested.emit(
                mouse_position,
                modifiers
            )

        self._measurement_point_drag_active = False

        self._pointer_state.reset()

        self._restore_interaction_cursor(
            mouse_position
        )

    def _is_button_drag(
        self,
        event: QMouseEvent,
        button: Qt.MouseButton
    ) -> bool:
        return (
            self._pointer_state.pressed_button
            == button
            and bool(
                event.buttons()
                & button
            )
        )

    def _drag_threshold_reached(
        self,
        mouse_position: QPoint
    ) -> bool:
        drag_distance = (
            mouse_position
            - self._pointer_state.press_position
        ).manhattanLength()

        return (
            drag_distance
            >= QApplication.startDragDistance()
        )

    def _handle_pan_drag(
        self,
        mouse_position: QPoint
    ):
        if not self._pointer_state.drag_active:
            if not self._drag_threshold_reached(
                mouse_position
            ):
                return

            self._begin_panning(
                mouse_position
            )
            return

        self._pan_to(
            mouse_position
        )

    def _handle_rotation_drag(
        self,
        mouse_position: QPoint
    ):
        if not self._pointer_state.drag_active:
            if not self._drag_threshold_reached(
                mouse_position
            ):
                return

            self._pointer_state.drag_active = True

            self._pointer_state.last_position = QPoint(
                mouse_position
            )

            self.viewport().setCursor(
                Qt.SizeAllCursor
            )

            return

        movement = (
            mouse_position
            - self._pointer_state.last_position
        )

        self._pointer_state.last_position = QPoint(
            mouse_position
        )

        self._rotation_controller.rotate_by_horizontal_pixels(
            movement.x()
        )

    def _begin_panning(
        self,
        mouse_position: QPoint
    ):
        self._pointer_state.drag_active = True

        self._pointer_state.last_position = QPoint(
            mouse_position
        )

        self.viewport().setCursor(
            Qt.ClosedHandCursor
        )

    def _pan_to(
        self,
        mouse_position: QPoint
    ):
        movement = (
            mouse_position
            - self._pointer_state.last_position
        )

        self.horizontalScrollBar().setValue(
            self.horizontalScrollBar().value()
            - movement.x()
        )

        self.verticalScrollBar().setValue(
            self.verticalScrollBar().value()
            - movement.y()
        )

        self._pointer_state.last_position = QPoint(
            mouse_position
        )

    def _restore_interaction_cursor(
        self,
        view_position=None
    ):
        if view_position is None:
            view_position = (
                self.viewport()
                .mapFromGlobal(
                    QCursor.pos()
                )
            )

        self._update_hover_cursor(
            view_position
        )

    def _update_hover_cursor(
        self,
        view_position: QPoint
    ):
        if self._pointer_state.drag_active:
            if (
                self._pointer_state.pressed_button
                == Qt.MiddleButton
            ):
                self.viewport().setCursor(
                    Qt.SizeAllCursor
                )

            elif (
                self._pointer_state.pressed_button
                == Qt.RightButton
            ):
                self.viewport().setCursor(
                    Qt.CrossCursor
                )

            elif (
                self._measurement_active
                and self._measurement_point_drag_active
            ):
                self.viewport().setCursor(
                    Qt.SizeAllCursor
                )

            else:
                self.viewport().setCursor(
                    Qt.ClosedHandCursor
                )

            return

        if self._measurement_active:
            self.viewport().setCursor(
                Qt.CrossCursor
            )

            return

        if (
            self._interaction_mode
            == InteractionMode.NAVIGATE
        ):
            self.viewport().setCursor(
                Qt.OpenHandCursor
            )

            return

        if self._has_selectable_item_at(
            view_position
        ):
            self.viewport().setCursor(
                Qt.ArrowCursor
            )

        else:
            self.viewport().setCursor(
                Qt.OpenHandCursor
            )

    def _has_selectable_item_at(
        self,
        view_position: QPoint
    ) -> bool:
        for item in self.items(
            view_position
        ):
            if (
                item.flags()
                & QGraphicsItem.ItemIsSelectable
            ):
                return True

        return False