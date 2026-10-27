import pytest
from PySide6.QtCore import QPointF

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.rotate_selection import RotateSelectionOperation
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.selection.node_selection import NodeSelection


@pytest.fixture
def setup():
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 5, 0))
    data.add_node(NodeData(2, 20, 7, 0))
    data.add_node(NodeData(3, 100, 0, 100))
    selection = NodeSelection()
    edits = EditHistory()
    coordinator = RotateSelectionOperation(
        EditContext(edits, lambda: data, node_selection=selection)
    )
    return data, selection, edits, coordinator


def xz(data, node_id):
    node = data.nodes[node_id]
    return (node.x, node.z)


def rotate(coordinator, angle_points, snap=False):
    """Grab at the first point, move through the others, release."""
    first, *rest = angle_points
    assert coordinator.begin_rotation(QPointF(*first))
    for point in rest:
        coordinator.update_rotation(QPointF(*point), snap=snap)
    coordinator.finish_rotation()


def test_needs_at_least_two_selected_nodes(setup):
    data, selection, edits, coordinator = setup

    selection.replace([1])

    assert coordinator.rotation_target() is None
    assert not coordinator.begin_rotation(QPointF(0, 0))


def test_target_is_average_center_and_largest_distance(setup):
    data, selection, edits, coordinator = setup

    selection.replace([1, 2])
    center, radius = coordinator.rotation_target()

    assert center.toTuple() == (10, 0)
    assert radius == pytest.approx(10)


def test_quarter_turn_around_center(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])  # center (10, 0)

    rotate(coordinator, [(30, 0), (10, 20)])  # grab right of center, drag below it

    assert xz(data, 1) == pytest.approx((10, -10))
    assert xz(data, 2) == pytest.approx((10, 10))
    assert xz(data, 3) == (100, 100)  # not selected


def test_height_is_kept(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])

    rotate(coordinator, [(30, 0), (10, 20)])

    assert (data.nodes[1].y, data.nodes[2].y) == (5, 7)


def test_center_stays_in_place(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2, 3])
    before, _ = coordinator.rotation_target()

    rotate(coordinator, [(200, 0), (150, 120)])

    after, _ = coordinator.rotation_target()
    assert after.toTuple() == pytest.approx(before.toTuple())


def test_whole_rotation_is_one_undo_step(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])

    rotate(coordinator, [(30, 0), (25, 10), (20, 15), (10, 20)])

    assert edits.undo_stack.count() == 1
    assert edits.undo_stack.undoText() == "Rotate 2 nodes"

    edits.undo()
    assert xz(data, 1) == (0, 0)
    assert xz(data, 2) == (20, 0)


def test_shift_snaps_to_15_degree_steps(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])
    assert coordinator.begin_rotation(QPointF(30, 0))

    angle = coordinator.update_rotation(QPointF(10 + 20 * 0.64, 20 * 0.77), snap=True)  # ~50°

    assert angle == 45
    coordinator.finish_rotation()


def test_snap_step_can_be_changed(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])
    coordinator.snap_angle = 35.0
    assert coordinator.begin_rotation(QPointF(30, 0))

    angle = coordinator.update_rotation(QPointF(10 + 20 * 0.64, 20 * 0.77), snap=True)  # ~50°

    assert angle == 35
    coordinator.finish_rotation()


def test_angle_is_reported_between_minus_180_and_180(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])
    assert coordinator.begin_rotation(QPointF(30, 0))

    angle = coordinator.update_rotation(QPointF(10, -20))  # quarter turn the other way

    assert angle == pytest.approx(-90)
    coordinator.cancel_rotation()


def test_cancel_restores_positions_without_undo_step(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])
    assert coordinator.begin_rotation(QPointF(30, 0))
    coordinator.update_rotation(QPointF(10, 20))

    coordinator.cancel_rotation()

    assert xz(data, 1) == pytest.approx((0, 0))
    assert edits.undo_stack.count() == 0
    assert not edits.history_locked


def test_history_is_locked_while_rotating(setup):
    data, selection, edits, coordinator = setup
    selection.replace([1, 2])
    assert coordinator.begin_rotation(QPointF(30, 0))
    coordinator.update_rotation(QPointF(10, 20))

    assert edits.history_locked

    coordinator.finish_rotation()
    assert not edits.history_locked


def test_target_changed_follows_selection_and_edits(setup):
    data, selection, edits, coordinator = setup
    events = []
    coordinator.target_changed.connect(lambda: events.append(1))

    selection.replace([1, 2])
    rotate(coordinator, [(30, 0), (10, 20)])

    assert len(events) >= 2
