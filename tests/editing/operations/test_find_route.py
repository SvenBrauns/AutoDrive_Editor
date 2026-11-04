import math
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand
from autodrive_editor.editing.commands.move_nodes import MoveNodesCommand
from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.find_route import FindRouteOperation, Waypoint
from autodrive_editor.editing.plan_changes import PlanChanges
from autodrive_editor.editing.route_finder import Vehicle
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    get_connection_type,
    write_connection_state,
)

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
        self.costmap = costmap
        self.plan = None
        self.messages = []
        context = EditContext(
            edit_history=self.history,
            autodrive_data_provider=lambda: self.data,
            node_selection=SimpleNamespace(selected_node_ids=set(), primary_node_id=None),
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

    def wait(self):
        deadline = time.monotonic() + 60

        while self.operation.is_searching and time.monotonic() < deadline:
            self.qapp.processEvents()
            time.sleep(0.01)

    def find(self, *waypoints):
        """Sets the waypoints (node IDs or (x, z)) and waits for the route."""

        self.operation.clear()

        for waypoint in waypoints:
            if isinstance(waypoint, int):
                self.operation.add_waypoint(0, 0, waypoint)
            else:
                self.operation.add_waypoint(*waypoint)

        self.wait()

        return self.operation.route

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


def test_preview_is_found_outside_planning_but_only_added_in_planning_mode(route):
    assert route.find(1, 2).is_clear

    assert not route.operation.apply()
    assert route.messages[-1] == "Find route adds routes in planning mode"


def test_without_drivability_map_explains_how_to_get_one(route):
    route.costmap = None

    assert route.find(1, 2) is None
    assert "Save the game" in route.operation.missing_costmap_message()


def test_route_through_the_corridor_is_one_undo_step_in_the_plan(route):
    route.start_plan()
    route.find(1, 2)

    assert route.operation.apply()

    path = route.path_from(1, 2)
    assert path is not None and len(path) > 20
    assert all(abs(route.data.nodes[n].z) < 2.5 for n in path if abs(route.data.nodes[n].x) < 40)
    assert {route.data.nodes[n].y for n in path[1:-1]} == {3.0}
    assert route.history.undo_stack.count() == 0
    assert route.history.can_undo

    route.history.undo()
    assert set(route.data.nodes) == {1, 2}


def test_free_waypoints_become_nodes_and_the_tool_starts_empty(route):
    route.start_plan()
    route.find((-60, 20), 1, (60, -20))

    assert route.operation.apply()

    first = next(n for n in route.data.nodes.values() if (n.x, n.z) == (-60, 20))
    last = next(n for n in route.data.nodes.values() if (n.x, n.z) == (60, -20))
    path = route.path_from(first.node_id, last.node_id)
    assert path is not None and 1 in path
    assert route.operation.waypoints == []
    assert not route.operation.can_undo_waypoints


def test_way_back_through_the_narrow_corridor_shares_the_lane_as_dual(route):
    route.start_plan()
    route.find(1, 2)
    route.operation.apply()
    corridor = [n for n in route.path_from(1, 2) if abs(route.data.nodes[n].x) < 30]

    route.find(2, 1)
    assert route.operation.apply()

    assert route.path_from(2, 1) is not None
    for source, target in zip(corridor, corridor[1:], strict=False):
        nodes = route.data.nodes
        assert get_connection_type(nodes[source], nodes[target]) == ConnectionType.DUAL


def test_route_through_a_wall_is_marked_and_not_added(qapp):
    route = Fixture(qapp, make_costmap(blocked=[(-10, -100, 10, 100)]))
    route.start_plan()

    assert not route.find(1, 2).is_clear
    assert "crosses obstacles" in route.messages[-1]
    assert not route.operation.apply()
    assert set(route.data.nodes) == {1, 2}


def test_a_route_with_a_gap_names_the_waypoint_and_is_not_added(qapp, monkeypatch):
    # No built leg, and too few search steps to get through the corridor.
    monkeypatch.setattr("autodrive_editor.editing.route_pipeline.LegBuilder.build", lambda *a: None)
    monkeypatch.setattr("autodrive_editor.editing.route_finder.MAX_EXPANSIONS", 5)
    route = Fixture(qapp)
    route.start_plan()

    assert not route.find(1, 2).is_complete
    message = "No drivable way found to waypoint 2 (red dashed). Move or add waypoints there"
    assert route.messages[-1] == message
    assert not route.operation.apply()
    assert route.messages[-1] == message
    assert set(route.data.nodes) == {1, 2}


def test_waypoints_too_close_for_the_radius_are_named(route):
    # One-way lanes east: the start node 11 and, 5 m behind it, the goal node 12.
    for node_id, x, z in ((10, -20, 0), (11, 0, 0), (12, -5, 1), (13, 15, 1)):
        route.data.add_node(NodeData(node_id, x, 0, z))
    for source, target in ((10, 11), (12, 13)):
        write_connection_state(
            route.data, source, target, CONNECTION_STATES[ConnectionType.REGULAR]
        )

    assert route.find(11, 12).too_close
    assert route.messages[-1] == (
        "Waypoints 1 and 2 are too close for the curve radius of 6 m (red dashed). Move them apart"
    )


def test_a_failing_search_ends_with_an_error_message(route, monkeypatch):
    def broken(*args):
        raise RuntimeError("broken")

    monkeypatch.setattr("autodrive_editor.editing.route_finder.RouteFinder.find", broken)

    assert route.find(1, 2) is None
    assert not route.operation.is_searching
    assert route.messages[-1] == "The route search failed. Details are in the log file"


def test_waypoints_follow_moved_nodes_and_the_route_is_searched_again(route):
    route.find(1, 2)

    route.history.push(
        MoveNodesCommand(route.data, {2: (60, 0, 0)}, {2: (70, 0, 0)}, merge_key=None)
    )
    assert route.operation.route is None
    route.wait()

    assert route.operation.waypoints[1] == Waypoint(70, 0, 2)
    assert route.operation.route.points[-1] == pytest.approx((70, 0))


def test_moving_a_free_waypoint_searches_again(route):
    route.find(1, (60, 0))

    route.operation.move_waypoint(1, 60, 2)
    route.wait()

    assert route.operation.route.points[-1] == pytest.approx((60, 2))


def test_removing_waypoints(route):
    route.find(1, (0, 0), 2)

    route.operation.remove_waypoint(1)
    route.wait()

    assert [waypoint.node_id for waypoint in route.operation.waypoints] == [1, 2]
    assert route.operation.clear()
    assert route.operation.route is None
    assert not route.operation.clear()


def test_ctrl_z_takes_back_waypoint_changes_one_by_one(route):
    route.find(1, (0, 0))
    route.operation.remember_waypoints()
    route.operation.move_waypoint(1, 5, 5)
    route.operation.remove_last()
    route.operation.clear()

    positions = []
    while route.operation.undo_waypoints():
        positions.append([(w.x, w.z) for w in route.operation.waypoints])

    start = route.data.nodes[1]
    first = (start.x, start.z)
    # Before: clear, remove last, move, add (0, 0), add node 1.
    assert positions == [[first], [first, (5, 5)], [first, (0, 0)], [first], []]
    assert route.operation.waypoints == []


def test_reset_drops_waypoints_and_their_undo(route):
    route.find(1, (0, 0))

    route.operation.reset()

    assert route.operation.waypoints == []
    assert not route.operation.undo_waypoints()


def test_leg_at_a_point_of_the_route_and_inserting_a_waypoint_there(route):
    route.find(1, (0, 0), 2)

    assert route.operation.legs_at(-30, 0, 1.0) == {0: 0}
    assert route.operation.legs_at(30, 0, 1.0) == {0: 1}
    assert route.operation.legs_at(30, 20, 1.0) == {}

    route.operation.insert_waypoint(30, 1, {0: 1})

    assert route.operation.waypoints[2] == Waypoint(30, 1)
    assert route.operation.legs_at(30, 0, 1.0) == {}


def test_a_newer_change_cancels_the_running_search_and_the_last_route_stays_shown(route):
    route.find(1, (60, 0))
    shown = route.operation.shown_route

    route.operation.move_waypoint(1, 60, 1)
    route.operation.move_waypoint(1, 60, 2)

    assert route.operation.shown_route is shown
    route.wait()
    assert route.operation.route.points[-1] == pytest.approx((60, 2))


def add_road(route, *nodes):
    """Adds the nodes (ID, x, z) as a one-way road in their order."""

    for node_id, x, z in nodes:
        route.data.add_node(NodeData(node_id, x, 0, z))

    for (source, *_), (target, *_) in zip(nodes, nodes[1:], strict=False):
        write_connection_state(route.data, source, target, CONNECTION_STATES["regular"])


def test_waypoint_on_a_connection_splits_it_when_the_route_is_added(route):
    add_road(route, (10, -90, -20), (11, -50, -20))
    route.start_plan()
    route.operation.add_waypoint_on_connection(10, 11, -70, -18)
    route.operation.add_waypoint(0, 0, 2)
    route.wait()

    assert route.operation.waypoints[0] == Waypoint(-70, -20, connection=(10, 11), fraction=0.5)
    assert route.operation.apply()

    split = next(n for n in route.data.nodes.values() if (n.x, n.z) == (-70, -20))
    assert 11 not in route.data.nodes[10].outgoing
    assert route.path_from(10, 11) == [10, split.node_id, 11]
    assert route.path_from(10, 2) is not None

    route.history.undo()
    assert route.data.nodes[10].outgoing == {11}


def test_waypoint_on_a_connection_follows_its_nodes_and_is_freed_with_the_connection(route):
    add_road(route, (10, -90, -20), (11, -50, -20))
    route.operation.add_waypoint_on_connection(10, 11, -70, -20)

    route.history.push(
        MoveNodesCommand(route.data, {11: (-50, 0, -20)}, {11: (-50, 0, -40)}, merge_key=None)
    )
    assert route.operation.waypoints[0] == Waypoint(-70, -30, connection=(10, 11), fraction=0.5)

    route.history.push(DeleteNodesCommand(route.data, [11]))
    assert route.operation.waypoints[0] == Waypoint(-70, -30)


def test_route_found_message_warns_about_poor_join_nodes(route):
    route.data.add_marker(MarkerData(2, "Silo"))
    route.find(1, 2)

    assert route.messages[-1] == (
        "Route found. Enter adds it to the plan. "
        "Nothing drives to node 1, so the route cannot be reached. "
        "Node 2 is a marker: other routes would lead through it"
    )


def test_stop_search_waits_until_the_running_search_has_ended(qapp, monkeypatch):
    ended = []

    def find(self, request, cancelled):
        while not cancelled():
            time.sleep(0.01)

        ended.append(1)

    monkeypatch.setattr("autodrive_editor.editing.route_finder.RouteFinder.find", find)
    route = Fixture(qapp)
    route.operation.add_waypoint(0, 0, 1)
    route.operation.add_waypoint(0, 0, 2)

    route.operation.stop_search()

    assert ended == [1]


def find_tree(route, starts, ends):
    """Sets starts and ends (node IDs) and waits for the routes."""

    route.operation.clear()

    for node_id in starts:
        route.operation.add_start(node_id)

    for node_id in ends:
        route.operation.add_end(node_id)

    route.wait()

    return route.operation.current_routes


def corridor_nodes(route, path):
    return [n for n in path if abs(route.data.nodes[n].x) < 30]


def test_routes_from_two_starts_merge_in_the_corridor_as_one_undo_step(route):
    route.data.add_node(NodeData(3, -60, 0, 30))
    route.start_plan()

    routes = find_tree(route, [1, 3], [2])

    assert len(routes) == 2 and all(r.is_clear for r in routes)
    assert route.messages[-1].startswith("Routes found. Enter adds them to the plan")
    assert route.operation.apply()
    assert route.messages[-1].startswith("2 routes with")
    first, second = route.path_from(1, 2), route.path_from(3, 2)
    assert first and second
    assert corridor_nodes(route, first) == corridor_nodes(route, second) != []

    route.history.undo()
    assert set(route.data.nodes) == {1, 2, 3}


def test_routes_to_two_ends_share_the_way_from_their_start(route):
    route.data.add_node(NodeData(5, 60, 0, 30))
    route.start_plan()

    find_tree(route, [1], [2, 5])
    assert route.operation.apply()

    first, second = route.path_from(1, 2), route.path_from(1, 5)
    assert first[:5] == second[:5]
    assert corridor_nodes(route, first) == corridor_nodes(route, second)


def test_several_starts_or_ends_must_be_nodes(route):
    route.operation.add_waypoint(-60, 20)
    route.operation.add_waypoint(0, 0, 2)

    route.operation.add_start(1)

    assert route.operation.starts == [0]
    assert route.messages[-1] == "With several starts or ends, all starts and ends are nodes"


def test_a_click_with_several_ends_adds_a_waypoint_all_routes_share(route):
    route.data.add_node(NodeData(5, 60, 0, 30))
    find_tree(route, [1], [2, 5])

    route.operation.add_waypoint(50, 10)

    key = max(route.operation.points)
    assert all(keys[1:-1] == (key,) for keys in route.operation.routes)
    # A new end gets the waypoints all routes share.
    route.data.add_node(NodeData(6, 60, 0, -30))
    route.operation.add_end(6)
    assert route.operation.routes[-1][1:-1] == (key,)


def test_routes_through_a_shared_waypoint_run_as_one_up_to_it(route):
    route.data.add_node(NodeData(5, 60, 0, 30))
    find_tree(route, [1], [2, 5])

    route.operation.add_waypoint(45, 0)
    route.wait()

    first, second = route.operation.current_routes
    assert first.points[: first.waypoint_indices[1] + 1] == pytest.approx(
        second.points[: second.waypoint_indices[1] + 1]
    )


def test_a_waypoint_on_one_route_searches_only_that_route_again(route):
    route.data.add_node(NodeData(5, 60, 0, 30))
    find_tree(route, [1], [2, 5])
    kept, edited = route.operation.current_routes

    point = next(point for point in edited.points if point[0] > 45)
    legs = route.operation.legs_at(*point, 1.0)
    route.operation.insert_waypoint(*point, {1: legs[1]})
    route.wait()

    first, second = route.operation.current_routes
    assert first is kept
    assert second is not edited and second.is_clear


def test_pressing_just_past_where_routes_split_inserts_into_all_of_them(route):
    route.data.add_node(NodeData(5, 60, 0, 30))
    find_tree(route, [1], [2, 5])
    first, second = route.operation.current_routes

    split = next(
        i for i, p in enumerate(second.points) if min(math.dist(p, q) for q in first.points) > 1.5
    )

    assert route.operation.legs_at(*second.points[split + 4], 1.0) == {0: 0, 1: 0}
    assert route.operation.legs_at(*second.points[-5], 1.0) == {1: 0}


def test_a_route_that_is_not_clear_is_named_and_nothing_is_added(route):
    # Node 5 lies in the blocked area north of the corridor.
    route.data.add_node(NodeData(5, 0, 0, 50))
    route.start_plan()

    find_tree(route, [1], [2, 5])

    assert route.messages[-1] == "Not clear yet (red): 1 → 5. Move or add waypoints there"
    assert not route.operation.apply()
    assert set(route.data.nodes) == {1, 2, 5}


def test_removing_a_start_takes_its_routes_and_backspace_the_last_added(route):
    route.data.add_node(NodeData(3, -60, 0, 30))
    find_tree(route, [1, 3], [2])

    route.operation.remove_waypoint(route.operation.starts[0])
    assert [keys for keys in route.operation.routes] == [(1, 2)]

    route.operation.remove_last()
    assert route.operation.ends == [] and route.operation.starts == [1]
