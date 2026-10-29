import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.find_route import FindRouteOperation
from autodrive_editor.editing.plan_changes import PlanChanges
from autodrive_editor.editing.route_finder import Vehicle
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type

# Blocked except a corridor 8 m wide between two open yards, where vehicles can turn.
CORRIDOR_MAP = make_costmap(
    blocked=[(-40, -100, 40, -4), (-40, 4, 40, 100)],
)


class Fixture:
    def __init__(self, qapp, costmap=CORRIDOR_MAP):
        self.qapp = qapp
        self.data = AutoDriveData()
        self.data.add_node(NodeData(1, -60, 0, 0))
        self.data.add_node(NodeData(2, 60, 0, 0))
        self.history = EditHistory()
        self.selection = SimpleNamespace(selected_node_ids=set(), primary_node_id=None)
        self.costmap = costmap
        self.plan = None
        self.messages = []
        context = EditContext(
            edit_history=self.history,
            autodrive_data_provider=lambda: self.data,
            node_selection=self.selection,
        )
        self.operation = FindRouteOperation(
            context,
            costmap_provider=lambda: self.costmap,
            savegame_provider=lambda: Path("savegame1"),
            vehicle_provider=lambda: Vehicle(8, 3, 0.5),
            spacing_provider=lambda: 5.0,
            plan_node_ids_provider=lambda: self.plan.changed_node_ids if self.plan else set(),
            height_for_new_node=lambda data, x, z: 3.0,
        )
        self.operation.status_changed.connect(self.messages.append)
        self.history.data_changed.connect(lambda change: self.plan and self.plan.update(change))

    def start_plan(self):
        self.plan = PlanChanges(self.data)
        self.history.start_plan()

    def find(self, start_id, goal_id):
        self.selection.selected_node_ids = {start_id, goal_id}
        self.selection.primary_node_id = goal_id
        started = self.operation.find_route()
        deadline = time.monotonic() + 60

        while self.operation.is_searching and time.monotonic() < deadline:
            self.qapp.processEvents()
            time.sleep(0.01)

        return started

    def path_from(self, start_id, goal_id):
        """Node IDs of a shortest way from start to goal over outgoing connections, or None."""

        previous, queue = {start_id: None}, [start_id]

        for node_id in queue:
            for other in sorted(self.data.nodes[node_id].outgoing):
                if other not in previous:
                    previous[other] = node_id
                    queue.append(other)

        if goal_id not in previous:
            return None

        path = [goal_id]

        while path[-1] != start_id:
            path.append(previous[path[-1]])

        return path[::-1]


@pytest.fixture
def route(qapp):
    return Fixture(qapp)


def test_needs_planning_mode(route):
    assert not route.find(1, 2)
    assert route.messages[-1] == "Find route works in planning mode"


def test_without_drivability_map_explains_how_to_get_one(route):
    route.start_plan()
    route.costmap = None

    assert not route.find(1, 2)
    assert "Save the game" in route.messages[-1]


def test_needs_two_selected_nodes(route):
    route.start_plan()
    route.selection.selected_node_ids = {1}

    assert not route.operation.find_route()
    assert route.messages[-1] == "Select the two nodes the route should connect"


def test_route_through_the_corridor_is_one_undo_step_in_the_plan(route):
    route.start_plan()

    assert route.find(1, 2)

    path = route.path_from(1, 2)
    assert path is not None and len(path) > 20
    assert all(abs(route.data.nodes[n].z) < 2.5 for n in path if abs(route.data.nodes[n].x) < 40)
    assert {route.data.nodes[n].y for n in path[1:-1]} == {3.0}
    assert route.history.undo_stack.count() == 0
    assert route.history.can_undo

    route.history.undo()
    assert set(route.data.nodes) == {1, 2}


def test_way_back_through_the_narrow_corridor_shares_the_lane_as_dual(route):
    route.start_plan()
    route.find(1, 2)
    corridor = [n for n in route.path_from(1, 2) if abs(route.data.nodes[n].x) < 30]

    assert route.find(2, 1)

    assert route.path_from(2, 1) is not None
    for source, target in zip(corridor, corridor[1:], strict=False):
        nodes = route.data.nodes
        assert get_connection_type(nodes[source], nodes[target]) == ConnectionType.DUAL


def test_no_route_reports_it(qapp):
    route = Fixture(qapp, make_costmap(blocked=[(-10, -100, 10, 100)]))
    route.start_plan()

    route.find(1, 2)

    assert route.messages[-1] == "No drivable route found from node 1 to node 2"


def test_result_is_dropped_when_the_plan_ends_during_the_search(route):
    route.start_plan()
    route.selection.selected_node_ids = {1, 2}
    route.selection.primary_node_id = 2
    route.operation.find_route()
    route.history.discard_plan()

    while route.operation.is_searching:
        route.qapp.processEvents()
        time.sleep(0.01)

    assert set(route.data.nodes) == {1, 2}
