from PySide6.QtCore import QPoint, QPointF
from PySide6.QtWidgets import QWidget

# Gap between the dialog and the edge of the map, in pixels; also allows for the window frame.
MARGIN = 16


def place_beside(dialog: QWidget, view, points: list[tuple[float, float]]):
    """Moves the dialog to the side of the map farther from the map points and, if they are still
    under it, pans the map so they sit in the middle of the free part."""

    if not points:
        return

    viewport = view.viewport()
    width = viewport.width()
    placed = [view.mapFromScene(QPointF(x, z)) for x, z in points]
    center_x = sum(point.x() for point in placed) / len(placed)
    dialog_width = dialog.width() + MARGIN
    on_left = center_x > width / 2
    top_left = viewport.mapToGlobal(QPoint(0, 0))
    x = top_left.x() + (MARGIN if on_left else width - dialog_width)
    dialog.move(x, top_left.y() + MARGIN)

    free_left, free_right = (dialog_width + MARGIN, width) if on_left else (0, width - dialog_width)

    if free_right <= free_left or all(free_left <= p.x() <= free_right for p in placed):
        return

    view.pan_by(QPoint(round((free_left + free_right) / 2 - center_x), 0))
