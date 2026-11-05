import copy
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPoint, QPointF

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.parallel_lane import ParallelLaneOperation
from autodrive_editor.editing.parallel_lane import ParallelLaneOptions
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    get_connection_type,
    write_connection_state,
)
from autodrive_editor.selection.node_selection import NodeSelection


class Fixture:
    """Two one-way roads along x: 1 -> 2 -> 3 at z = 0 driving east, 4 -> 5 -> 6 at z = 50
    driving west. A view position is ten times the map position."""

    def __init__(self):
        self.data = AutoDriveData()

        for node_id, x, z in [
            (1, 0, 0),
            (2, 10, 0),
            (3, 20, 0),
            (4, 20, 50),
            (5, 10, 50),
            (6, 0, 50),
        ]:
            self.data.add_node(NodeData(node_id, x, 3, z))

        for source, target in [(1, 2), (2, 3), (4, 5), (5, 6)]:
            write_connection_state(
                self.data, source, target, CONNECTION_STATES[ConnectionType.REGULAR]
            )

        self.history = EditHistory()
        self.selection = NodeSelection()
        self.messages = []
        context = EditContext(
            edit_history=self.history,
            autodrive_data_provider=lambda: self.data,
            view=SimpleNamespace(mapToScene=lambda p: QPointF(p) / 10),
            node_selection=self.selection,
        )
        self.operation = ParallelLaneOperation(context)
        self.operation.status_changed.connect(self.messages.append)

    @property
    def new_nodes(self):
        return [node for node_id, node in sorted(self.data.nodes.items()) if node_id > 6]


@pytest.fixture
def lane():
    return Fixture()


def test_pointer_sets_side_and_rounded_distance(lane):
    lane.selection.replace([1, 2, 3])
    distances = []
    lane.operation.distance_changed.connect(distances.append)

    lane.operation.pointer_moved(QPoint(50, -42))  # 4.2 m to the left

    assert lane.operation.offset == -4.0
    assert distances == [4.0]
    assert lane.operation.preview_lanes()[0][0] == pytest.approx((0, -4))


def test_every_chain_gets_the_same_side_of_its_own_direction(lane):
    lane.selection.replace(range(1, 7))
    lane.operation.pointer_moved(QPoint(100, 59))  # right of the east road (+z)

    lanes = lane.operation.preview_lanes()

    # The west road's right side is -z.
    assert {round(z, 6) for _, z in lanes[0]} == {6.0}
    assert {round(z, 6) for _, z in lanes[1]} == {44.0}


def test_apply_creates_connected_lanes_in_one_undo_step(lane):
    lane.selection.replace([1, 2, 3])
    lane.operation.set_options(
        ParallelLaneOptions(5.5, opposite=True, spacing=5, flag=SUBPRIO_FLAG)
    )
    before = copy.deepcopy(lane.data.nodes)

    assert lane.operation.apply()

    nodes = lane.new_nodes
    assert [node.x for node in nodes] == pytest.approx([20, 15, 10, 5, 0])
    assert {(node.z, node.y, node.flag) for node in nodes} == {(5.5, 3, SUBPRIO_FLAG)}
    for a, b in zip(nodes, nodes[1:], strict=False):
        assert get_connection_type(a, b) == ConnectionType.REGULAR
    # The ends stay open and the selection does not change.
    assert not nodes[0].incoming and not nodes[-1].outgoing
    assert lane.selection.selected_node_ids == {1, 2, 3}

    lane.history.undo()
    assert lane.data.nodes == before


def test_refused_lane_shows_the_reason(lane):
    write_connection_state(lane.data, 2, 5, CONNECTION_STATES[ConnectionType.REGULAR])
    lane.selection.replace([1, 2, 3, 5])

    assert not lane.operation.apply()
    assert "junction" in lane.messages[-1]
    assert lane.operation.preview_lanes() == []


def test_nothing_selected_asks_for_a_selection(lane):
    assert not lane.operation.apply()
    assert lane.messages
