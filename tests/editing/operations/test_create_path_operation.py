from types import SimpleNamespace

import pytest
from PySide6.QtCore import QPoint, QPointF

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.create_path import CreatePathOperation
from autodrive_editor.editing.path_shapes import PathOptions, PathShape
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type


class Fixture:
    """Operation on a fake view: view positions are map positions, and a
    click within 1 m of a node hits that node."""

    def __init__(self):
        self.data = AutoDriveData()
        self.data.add_node(NodeData(1, 0, 4, 0))
        self.data.add_node(NodeData(2, 30, 10, 0))
        self.history = EditHistory()
        self.terrain = None
        context = EditContext(
            edit_history=self.history,
            autodrive_data_provider=lambda: self.data,
            view=SimpleNamespace(mapToScene=lambda p: QPointF(p)),
            selection_coordinator=SimpleNamespace(get_node_at=self.node_at),
            terrain_height_at=lambda x, z: None if self.terrain is None else self.terrain(x, z),
        )
        self.operation = CreatePathOperation(context, height_for_new_node=lambda data, x, z: 7.0)

    def node_at(self, position):
        for node in self.data.nodes.values():
            if abs(node.x - position.x()) < 1 and abs(node.z - position.y()) < 1:
                return node

        return None

    def click(self, x, z):
        self.operation.click(QPoint(x, z))

    @property
    def new_nodes(self):
        return [node for node_id, node in sorted(self.data.nodes.items()) if node_id > 2]


@pytest.fixture
def path():
    return Fixture()


def test_line_between_free_points_is_spaced_and_connected(path):
    path.operation.set_options(PathOptions(5.0, ConnectionType.DUAL, SUBPRIO_FLAG))

    path.click(0, 20)
    path.click(10, 20)

    assert sorted(n.x for n in path.new_nodes) == pytest.approx([0, 5, 10])
    assert {n.flag for n in path.new_nodes} == {SUBPRIO_FLAG}
    assert {n.y for n in path.new_nodes} == {7.0}
    assert path.data.validate_connections() == []
    assert path.history.undo_stack.count() == 1


def test_line_connection_type_is_applied_to_each_pair(path):
    path.operation.set_options(PathOptions(5.0, ConnectionType.REVERSE))

    path.click(0, 20)
    path.click(10, 20)

    first, second, third = path.data.nodes[3], path.data.nodes[5], path.data.nodes[4]
    assert get_connection_type(first, second) == ConnectionType.REVERSE
    assert get_connection_type(second, third) == ConnectionType.REVERSE


def test_line_between_existing_nodes_adds_only_inner_nodes(path):
    path.click(0, 0)
    path.click(30, 0)

    assert len(path.new_nodes) == 5
    assert path.data.nodes[1].outgoing == {3}
    assert path.data.nodes[2].incoming == {path.new_nodes[-1].node_id}


def test_end_becomes_the_next_start(path):
    path.click(0, 0)
    path.click(30, 0)
    count = len(path.data)

    path.click(30, 20)

    assert len(path.data) > count
    assert path.operation.start.node_id is not None
    assert path.data.nodes[2].outgoing


def test_undo_removes_the_whole_path_in_one_step(path):
    path.click(0, 20)
    path.click(10, 20)

    path.history.undo()

    assert set(path.data.nodes) == {1, 2}


def test_click_on_the_start_again_does_nothing(path):
    path.click(0, 0)
    path.click(0, 0)

    assert not path.operation.is_adjusting
    assert path.history.undo_stack.count() == 0


def test_bezier_waits_for_apply(path):
    path.operation.set_shape(PathShape.BEZIER)
    path.click(0, 20)
    path.click(30, 20)

    assert path.operation.is_adjusting
    assert len(path.operation.handles) == 2
    assert len(path.data) == 2

    path.operation.move_handle(0, 10, 40)

    assert path.operation.apply()
    assert len(path.new_nodes) >= 6
    assert max(n.z for n in path.new_nodes) > 20
    assert not path.operation.is_adjusting
    assert path.operation.start.x == 30


def test_clicks_are_ignored_while_adjusting(path):
    path.operation.set_shape(PathShape.ARC)
    path.click(0, 20)
    path.click(30, 20)

    path.click(50, 50)

    assert path.operation.end.x == 30
    assert len(path.data) == 2


def test_cancel_drops_the_curve_then_the_start(path):
    path.operation.set_shape(PathShape.ARC)
    path.click(0, 20)
    path.click(30, 20)

    assert path.operation.cancel()
    assert not path.operation.is_adjusting
    assert path.operation.start is not None

    assert path.operation.cancel()
    assert path.operation.start is None
    assert not path.operation.cancel()
    assert len(path.data) == 2


def test_heights_come_from_the_terrain(path):
    path.terrain = lambda x, z: x * 2

    path.click(0, 20)
    path.click(10, 20)

    inner = [n for n in path.new_nodes if 0 < n.x < 10]
    assert inner[0].y == pytest.approx(inner[0].x * 2)


def test_heights_are_interpolated_between_existing_endpoints_without_terrain(path):
    path.click(0, 0)
    path.click(30, 0)

    heights = [n.y for n in sorted(path.new_nodes, key=lambda n: n.x)]
    assert heights == pytest.approx([5, 6, 7, 8, 9])


def test_free_endpoints_use_the_height_for_new_nodes(path):
    path.click(0, 20)
    path.click(10, 20)

    ends = [n for n in path.new_nodes if n.x in (0, 10)]
    assert [n.y for n in ends] == [7.0, 7.0]


def test_history_lock_blocks_apply(path):
    path.operation.set_shape(PathShape.BEZIER)
    path.click(0, 20)
    path.click(30, 20)
    path.history.set_history_locked(True)

    assert not path.operation.apply()
    assert len(path.data) == 2
    assert path.operation.is_adjusting


def test_snap_point_is_used_for_free_points(path):
    path.operation.snap_point = lambda x, z: (round(x / 10) * 10, round(z / 10) * 10)

    path.click(0, 19)
    path.click(11, 21)

    assert {(n.x, n.z) for n in path.new_nodes} >= {(0, 20), (10, 20)}


def test_start_node_removed_by_undo_is_forgotten(path):
    path.click(0, 20)
    path.click(10, 20)
    assert path.operation.start.node_id is not None

    path.history.undo()

    assert path.operation.start is None
