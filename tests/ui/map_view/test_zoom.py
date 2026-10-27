"""Zooming the map with the mouse wheel."""

import pytest
from mouse_helpers import view_pos
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication


def scroll_wheel(window, pos, delta):
    viewport = window.view.viewport()
    event = QWheelEvent(
        QPointF(pos),
        QPointF(viewport.mapToGlobal(pos)),
        QPoint(),
        QPoint(0, delta),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(viewport, event)


@pytest.fixture
def zoomable(zoomed_window):
    # Room to scroll, so the view can keep the point under the cursor.
    zoomed_window.view.setSceneRect(-1000, -1000, 2000, 2000)
    return zoomed_window


@pytest.mark.parametrize("delta", [120, -120])
def test_wheel_zooms_around_the_point_under_the_cursor(zoomable, delta):
    before = zoomable.view.zoom_level
    cursor = view_pos(zoomable, 20, 0)

    scroll_wheel(zoomable, cursor, delta)

    assert (zoomable.view.zoom_level > before) == (delta > 0)
    under_cursor = zoomable.view.mapToScene(cursor)
    assert (under_cursor.x(), under_cursor.y()) == pytest.approx((20, 0), abs=1)
