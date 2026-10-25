"""The "Rotieren" tool, driven by real mouse and key input."""

import pytest

from PySide6.QtCore import QEvent, QPoint, QRectF, Qt
from PySide6.QtGui import QPainterPath

from mouse_helpers import click, cursor_shape, drag, hover, press_escape, send_mouse, view_pos
from ui.interaction_mode import InteractionMode

# Test network from conftest: nodes 1, 2, 3 on z=0 at x = 0, 10, 20.
# Selecting all three gives the center (10, 0). At zoom 4 the ring
# radius is 10 + 24 px / 4 = 16.

CENTER = (10, 0)
RADIUS = 16


def select(window, rect):
    path = QPainterPath()
    path.addRect(rect)
    window.selection_coordinator.handle_area(path, Qt.NoModifier)


def select_all(window):
    select(window, QRectF(-5, -5, 30, 10))


def tool(window):
    return window.view._tools[InteractionMode.ROTATE_SELECTION]


def xz(window, node_id):
    node = window.project_coordinator.autodrive_data.get_node(node_id)
    return (node.x, node.z)


def on_ring(window, dx, dz):
    """View position on the ring in the direction (dx, dz) from the center."""
    return view_pos(window, CENTER[0] + dx * RADIUS, CENTER[1] + dz * RADIUS)


@pytest.fixture
def rotating(zoomed_window):
    select_all(zoomed_window)
    zoomed_window.set_interaction_mode(InteractionMode.ROTATE_SELECTION)
    return zoomed_window


def test_ring_surrounds_the_selection(rotating):
    center, radius = tool(rotating).ring

    assert center.toTuple() == CENTER
    assert radius == pytest.approx(RADIUS)


def test_dragging_the_ring_rotates_the_selection(rotating):
    drag(rotating, on_ring(rotating, 1, 0), on_ring(rotating, 0, 1), steps=8)

    assert xz(rotating, 1) == pytest.approx((10, -10), abs=0.2)
    assert xz(rotating, 2) == pytest.approx((10, 0), abs=0.2)
    assert xz(rotating, 3) == pytest.approx((10, 10), abs=0.2)
    assert rotating.edit_coordinator.undo_stack.count() == 1
    assert rotating.actions.undo_action.text() == "Rückgängig: 3 Nodes rotieren"
    assert rotating.status.text().startswith("3 Nodes um 90")


def test_shift_snaps_while_dragging(rotating):
    drag(
        rotating,
        on_ring(rotating, 1, 0),
        on_ring(rotating, 0.64, 0.77),
        steps=4,
        modifiers=Qt.ShiftModifier,
    )  # ~50°

    assert rotating.status.text() == "3 Nodes um 45.0° rotiert"


def test_dragging_off_the_ring_pans(rotating):
    before = rotating.view.horizontalScrollBar().value()
    rotating.view.setSceneRect(-1000, -1000, 2000, 2000)
    start = view_pos(rotating, 10, 0)  # the center, inside the ring

    drag(rotating, start, start + QPoint(60, 0))

    assert xz(rotating, 1) == (0, 0)
    assert rotating.edit_coordinator.undo_stack.count() == 0


def test_escape_cancels_rotation(rotating):
    drag(rotating, on_ring(rotating, 1, 0), on_ring(rotating, 0, 1), release=False)

    press_escape(rotating)
    send_mouse(
        rotating, QEvent.MouseButtonRelease, on_ring(rotating, 0, 1), Qt.LeftButton, Qt.NoButton
    )

    assert xz(rotating, 1) == pytest.approx((0, 0))
    assert rotating.edit_coordinator.undo_stack.count() == 0


def test_undo_restores_positions_and_ring(rotating):
    drag(rotating, on_ring(rotating, 1, 0), on_ring(rotating, 0, 1), steps=8)

    rotating.actions.undo_action.trigger()

    assert xz(rotating, 1) == (0, 0)
    center, _ = tool(rotating).ring
    assert center.toTuple() == pytest.approx(CENTER)


def test_cursor_points_at_the_ring(rotating):
    hover(rotating, on_ring(rotating, 0, -1))
    assert cursor_shape(rotating) == Qt.PointingHandCursor

    hover(rotating, view_pos(rotating, *CENTER))
    assert cursor_shape(rotating) == Qt.OpenHandCursor


def test_no_ring_with_fewer_than_two_nodes(zoomed_window):
    select(zoomed_window, QRectF(-5, -5, 10, 10))  # node 1 only

    zoomed_window.set_interaction_mode(InteractionMode.ROTATE_SELECTION)

    assert tool(zoomed_window).ring is None
    assert zoomed_window.status.text() == (
        "Modus: Auswahl rotieren – Zum Rotieren mindestens zwei Nodes auswählen"
    )


def test_ring_follows_selection_changes(rotating):
    select(rotating, QRectF(5, -5, 20, 10))  # nodes 2 and 3
    center, _ = tool(rotating).ring
    assert center.toTuple() == (15, 0)

    rotating.selection_coordinator.clear()
    assert tool(rotating).ring is None


def test_ring_disappears_when_switching_tools(rotating):
    rotating.set_interaction_mode(InteractionMode.SELECT)

    assert tool(rotating).ring is None
    assert not tool(rotating)._overlay.isVisible()


def test_loading_data_while_active_does_not_crash(rotating, write_xml):
    rotating.project_coordinator.load_xml_file(write_xml())

    assert tool(rotating).ring is None
    select_all(rotating)
    assert tool(rotating).ring is not None
