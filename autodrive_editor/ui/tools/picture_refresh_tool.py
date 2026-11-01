from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QMouseEvent, QPainterPath

from autodrive_editor.i18n import tr
from autodrive_editor.rendering.items.picture_grid_item import PictureGridItem
from autodrive_editor.terrain.game_picture import GamePicture
from autodrive_editor.terrain.picture_capture import estimate
from autodrive_editor.ui.dialogs.picture_capture_dialog import minutes
from autodrive_editor.ui.map_view.area_selection import AreaSelectionController
from autodrive_editor.ui.tools.map_tool import MapTool, is_alive_in_scene


class PictureRefreshTool(MapTool):
    """Marks tiles of the game picture to capture again. Left click toggles a tile, right
    dragging marks every tile the box touches, Ctrl + right dragging unmarks them. Left dragging
    pans. Enter sends the marked tiles, Esc clears them and then ends the tool."""

    RIGHT_CLICK_CANCELS = False

    def __init__(
        self,
        view,
        picture: GamePicture,
        wait_ms: int,
        send: Callable[[list[tuple[int, int]]], object],
        close: Callable[[], None],
        show_status: Callable[[str], None],
    ):
        super().__init__(view)

        self.picture = picture
        self.wait_ms = wait_ms
        self.send = send
        self.close = close
        self.show_status = show_status
        self.marked: set[tuple[int, int]] = set()
        self.item: PictureGridItem | None = None
        self.hovered = ""
        self._right_button_pressed = False

        self._area = AreaSelectionController(view=view, parent=view)
        self._area.area_requested.connect(self._apply_area)
        self._area.area_preview_requested.connect(
            lambda path, modifiers: self.item.set_marked(self._area_result(path, modifiers))
        )
        self._area.area_preview_cleared.connect(lambda: self.item.set_marked(self.marked))

    def activate(self):
        self.item = PictureGridItem(self.picture.grid)
        self.view.scene().addItem(self.item)
        self.show_status(self.status_hint())

    def deactivate(self):
        self._pan.reset()
        self._right_button_pressed = False
        self._area.cancel(emit_preview_cleared=False)

        if is_alive_in_scene(self.item, self.view.scene()):
            self.view.scene().removeItem(self.item)

    def mouse_press(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.RightButton:
            self._right_button_pressed = True
            self._area.begin(event.position().toPoint())
            return True

        return super().mouse_press(event)

    def mouse_move(self, event: QMouseEvent) -> bool:
        if self._right_button_pressed and event.buttons() & Qt.RightButton:
            self._area.handle_drag(event.position().toPoint(), event.modifiers())
            return True

        if not self._continue_pan(event):
            self._hover(event.position().toPoint())

        return True

    def mouse_release(self, event: QMouseEvent) -> bool:
        if event.button() == Qt.RightButton and self._right_button_pressed:
            self._right_button_pressed = False
            self._area.finish(event.modifiers())
            return True

        if event.button() != Qt.LeftButton:
            return False

        if not self._end_pan():
            tile = self._tile_at(event.position().toPoint())

            if tile is not None:
                self._set_marked(self.marked ^ {tile})

        return True

    def mouse_leave(self):
        self.hovered = ""
        self.show_status(self.status_hint())

    def cancel(self) -> bool:
        if self._right_button_pressed:
            self._right_button_pressed = False
            self._area.cancel()
        elif self.marked:
            self._set_marked(set())
        else:
            self.close()

        return True

    def confirm(self) -> bool:
        if not self.marked:
            return False

        self.send(sorted(self.marked, key=lambda tile: (tile[1], tile[0])))
        return True

    def status_hint(self) -> str | None:
        count = len(self.marked)

        if count:
            hint = tr(
                "{count} tiles marked · about {minutes} min · Enter refreshes, Esc clears",
                count=count,
                minutes=minutes(estimate(count, self.wait_ms)[0]),
            )
        else:
            hint = tr(
                "Click a tile or right-drag a box to mark tiles for a refresh, "
                "Ctrl+right-drag unmarks, Esc ends"
            )

        return f"{self.hovered} – {hint}" if self.hovered else hint

    def cursor_at(self, view_position: QPoint) -> Qt.CursorShape:
        if self._right_button_pressed:
            return Qt.CrossCursor

        return super().cursor_at(view_position)

    def _hover(self, view_position: QPoint):
        tile = self._tile_at(view_position)

        if tile is None:
            hovered = ""
        elif (captured := self.picture.captured.get(tile)) is not None:
            date = datetime.fromisoformat(captured).strftime("%Y-%m-%d %H:%M")
            hovered = tr("Tile {col}, {row} · captured {date}", col=tile[0], row=tile[1], date=date)
        else:
            hovered = tr("Tile {col}, {row} · not captured", col=tile[0], row=tile[1])

        if hovered != self.hovered:
            self.hovered = hovered
            self.show_status(self.status_hint())

    def _tile_at(self, view_position: QPoint) -> tuple[int, int] | None:
        point = self.view.mapToScene(view_position)
        return self.picture.grid.tile_at(point.x(), point.y())

    def _area_result(self, path: QPainterPath, modifiers) -> set[tuple[int, int]]:
        bounds = path.boundingRect()
        grid = self.picture.grid
        touched = {
            tile
            for tile in grid.tiles_in(
                0, bounds.left(), bounds.top(), bounds.right(), bounds.bottom()
            )
            if path.intersects(QRectF(*grid.tile_rect(0, *tile)))
        }

        if modifiers & Qt.ControlModifier:
            return self.marked - touched

        return self.marked | touched

    def _apply_area(self, path: QPainterPath, modifiers):
        self._set_marked(self._area_result(path, modifiers))

    def _set_marked(self, marked: set[tuple[int, int]]):
        self.marked = marked
        self.item.set_marked(marked)
        self.show_status(self.status_hint())
