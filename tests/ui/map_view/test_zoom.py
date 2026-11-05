"""Zooming the map with the mouse wheel."""

import pytest
from mouse_helpers import view_pos
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
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


@pytest.mark.parametrize(("key", "zoom_in"), [(Qt.Key_Plus, True), (Qt.Key_Minus, False)])
def test_plus_and_minus_zoom_around_the_middle_of_the_map(zoomable, key, zoom_in):
    view = zoomable.view
    before = view.zoom_level
    middle = view.mapToScene(view.viewport().rect().center())

    QTest.keyClick(view.viewport(), key)

    assert (view.zoom_level > before) == zoom_in
    after = view.mapToScene(view.viewport().rect().center())
    assert (after.x(), after.y()) == pytest.approx((middle.x(), middle.y()), abs=1)


def test_zoom_to_selection_fits_the_nodes_and_keeps_the_rotation(zoomable):
    view = zoomable.view
    view.set_rotation_angle(30.0)
    view.set_zoom_level(0.1)
    zoomable.node_selection.replace({1, 3})

    QTest.keyClick(view.viewport(), Qt.Key_F)

    assert view.rotation_angle == pytest.approx(30.0)
    # The 20 m between the nodes fill the map but for the margin.
    width = view.viewport().width() - 2 * view.FIT_MARGIN
    assert view.zoom_level == pytest.approx(min(2.0, width / (20 * 0.866)), rel=0.01)
    viewport = view.viewport().rect()
    assert all(viewport.contains(view_pos(zoomable, x, 0)) for x in (0, 20))


def test_zoom_to_one_node_zooms_in_like_a_marker_click(zoomable):
    zoomable.view.set_zoom_level(0.1)
    zoomable.node_selection.replace({2})

    zoomable.actions.zoom_to_selection_action.trigger()

    assert zoomable.view.zoom_level == pytest.approx(zoomable.FOCUS_MARKER_ZOOM)
    middle = zoomable.view.mapToScene(zoomable.view.viewport().rect().center())
    assert (middle.x(), middle.y()) == pytest.approx((10, 0), abs=1)


def test_zoom_to_selection_without_a_selection_leaves_the_view(zoomable):
    before = zoomable.view.zoom_level
    zoomable.node_selection.clear()

    zoomable.actions.zoom_to_selection_action.trigger()

    assert zoomable.view.zoom_level == pytest.approx(before)
