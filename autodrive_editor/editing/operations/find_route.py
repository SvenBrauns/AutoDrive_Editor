import logging
import math
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path

from PySide6.QtCore import Signal

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.join_rules import join_problem
from autodrive_editor.editing.route_finder import Route, RouteFinder, RouteRequest, Vehicle
from autodrive_editor.editing.route_nodes import (
    chain_connections,
    node_headings,
    planned_lanes,
    route_nodes,
)
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    NO_CONNECTION,
    ConnectionType,
    read_connection_state,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Waypoint:
    """A point the route passes: an existing node, a point on an existing connection (split
    there when the route is added) or a free map position."""

    x: float
    z: float
    node_id: int | None = None
    # The connection (source, target) and how far along it the point lies, from 0 to 1.
    connection: tuple[int, int] | None = None
    fraction: float = 0.0

    @property
    def is_free(self) -> bool:
        return self.node_id is None and self.connection is None


class FindRouteOperation(EditOperation):
    """Find route: a drivable route through waypoints, which are existing nodes or free map
    positions. After each change of the waypoints or the network the route is searched again in
    a background thread and shown as a preview; parts that cross obstacles are marked. apply()
    adds a clear route to the plan as one undo step."""

    # The waypoints or the previewed route changed.
    preview_changed = Signal()
    # A search started or ended.
    searching_changed = Signal(bool)
    # From the search thread: the search number and the route or None.
    _search_done = Signal(int, object)

    def __init__(
        self,
        context: EditContext,
        costmap_provider: Callable[[], NavigationCostmap | None],
        savegame_provider: Callable[[], Path | None],
        vehicle_provider: Callable[[], Vehicle],
        spacing_provider: Callable[[], float],
        plan_node_ids_provider: Callable[[], set[int]],
        height_for_new_node: Callable[[AutoDriveData, float, float], float],
        parent=None,
    ):
        super().__init__(context, parent)

        self.costmap_provider = costmap_provider
        self.savegame_provider = savegame_provider
        self.vehicle_provider = vehicle_provider
        self.spacing_provider = spacing_provider
        self.plan_node_ids_provider = plan_node_ids_provider
        self.height_for_new_node = height_for_new_node

        self.waypoints: list[Waypoint] = []
        # Earlier waypoint lists of the route being built, for Ctrl+Z inside the tool.
        self._undo_waypoints: list[list[Waypoint]] = []
        # The route through the current waypoints, None while there is none or it is outdated.
        self.route: Route | None = None
        # The route last found, shown until the next one is found.
        self.shown_route: Route | None = None

        # Number of the latest search; results of older ones are dropped.
        self._search_number = 0
        self._running: dict | None = None
        self._search_again = False
        self._search_done.connect(self._finish)
        self.edit_history.data_changed.connect(self._handle_data_changed)
        # Only an ended plan changes the planned lanes; a new plan is empty.
        self.edit_history.planning_changed.connect(lambda planning: planning or self._search())
        # A discarded plan is a complete reset, so its waypoints go too.
        self.edit_history.plan_discarded.connect(self.reset)

    @property
    def is_searching(self) -> bool:
        return self._running is not None

    @property
    def can_undo_waypoints(self) -> bool:
        return bool(self._undo_waypoints)

    def undo_waypoints(self) -> bool:
        """Takes back the last change of the waypoints (add, move, remove). Returns False if
        there is none, so Ctrl+Z goes on to the plan's undo."""

        if not self._undo_waypoints:
            return False

        self.waypoints = self._undo_waypoints.pop()
        self._search()

        return True

    def remember_waypoints(self):
        """Keeps the waypoints before a change, e.g. before a waypoint is dragged."""

        self._undo_waypoints.append(list(self.waypoints))

    def add_waypoint(self, x: float, z: float, node_id: int | None = None):
        if node_id is not None:
            node = self.autodrive_data_provider().nodes[node_id]
            x, z = node.x, node.z

        if self.waypoints and (self.waypoints[-1].x, self.waypoints[-1].z) == (x, z):
            return

        self.remember_waypoints()
        self.waypoints.append(Waypoint(x, z, node_id))
        self._search()

    def add_waypoint_on_connection(self, source_id: int, target_id: int, x: float, z: float):
        """Adds a waypoint on the connection, at the point closest to (x, z)."""

        nodes = self.autodrive_data_provider().nodes
        source, target = nodes[source_id], nodes[target_id]
        dx, dz = target.x - source.x, target.z - source.z
        length_squared = dx * dx + dz * dz or 1.0
        fraction = ((x - source.x) * dx + (z - source.z) * dz) / length_squared
        fraction = min(max(fraction, 0.01), 0.99)

        self.remember_waypoints()
        self.waypoints.append(
            Waypoint(
                source.x + fraction * dx,
                source.z + fraction * dz,
                connection=(source_id, target_id),
                fraction=fraction,
            )
        )
        self._search()

    def join_warnings(self) -> list[str]:
        """Why existing nodes among the waypoints are poor places to join the route."""

        autodrive_data = self.autodrive_data_provider()
        last = len(self.waypoints) - 1

        return [
            problem
            for index, waypoint in enumerate(self.waypoints)
            if waypoint.node_id is not None
            and (
                problem := join_problem(autodrive_data, waypoint.node_id, index == 0, index == last)
            )
        ]

    def insert_waypoint(self, index: int, x: float, z: float):
        """Adds a free waypoint before the one at the index."""

        self.remember_waypoints()
        self.waypoints.insert(index, Waypoint(x, z))
        self._search()

    def leg_at(self, x: float, z: float, tolerance: float) -> int | None:
        """The leg of the shown route that passes within `tolerance` of the point: leg k runs
        from waypoint k to k + 1. None if the route does not pass there or is outdated."""

        route = self.shown_route

        if route is None or len(route.waypoint_indices) != len(self.waypoints):
            return None

        nearest = min(
            range(len(route.points)),
            key=lambda index: math.dist(route.points[index], (x, z)),
        )

        if math.dist(route.points[nearest], (x, z)) > tolerance:
            return None

        return max(leg for leg, start in enumerate(route.waypoint_indices[:-1]) if start <= nearest)

    def remove_waypoint(self, index: int):
        self.remember_waypoints()
        del self.waypoints[index]
        self._search()

    def remove_last(self) -> bool:
        """Removes the last waypoint. Returns whether there was one."""

        if not self.waypoints:
            return False

        self.remove_waypoint(len(self.waypoints) - 1)

        return True

    def move_waypoint(self, index: int, x: float, z: float):
        """Moves a free waypoint. A drag calls remember_waypoints() once before."""

        self.waypoints[index] = replace(self.waypoints[index], x=x, z=z)
        self._search()

    def clear(self) -> bool:
        """Removes all waypoints. Returns whether there were any."""

        had_waypoints = bool(self.waypoints)

        if had_waypoints:
            self.remember_waypoints()

        self.waypoints = []
        self._search()

        return had_waypoints

    def reset(self):
        """Starts empty, without waypoint undo, e.g. when the tool is left."""

        self._undo_waypoints = []
        self.waypoints = []
        self._search()

    def apply(self) -> bool:
        """Adds the route to the plan. The tool starts empty; the next click picks a new start."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or len(self.waypoints) < 2 or self.edit_history.history_locked:
            return False

        if not self.edit_history.is_planning:
            self.status_changed.emit(tr("Find route adds routes in planning mode"))
            return False

        if self.route is None:
            self.status_changed.emit(tr("The route is still being searched"))
            return False

        if not self.route.is_clear:
            self.status_changed.emit(
                tr("The route crosses obstacles (red). Move or add waypoints first")
            )
            return False

        command = self._route_command(autodrive_data, self.route)
        # Set first, so the edit does not start a search for the old waypoints.
        self.waypoints = []
        self._undo_waypoints = []
        self.edit_history.push(command)
        self.status_changed.emit(
            tr("Route with {count} new nodes added", count=len(command.new_nodes))
        )

        return True

    def missing_costmap_message(self) -> str | None:
        """Why there is no drivability map, or None if there is one."""

        if self.costmap_provider() is not None:
            return None

        if self.savegame_provider() is None:
            return tr("Find route needs the drivability map of a savegame. Open a savegame")

        return tr(
            "The savegame has no drivability map yet. Save the game in Farming Simulator first "
            "(again after placing buildings)"
        )

    def _search(self):
        """Starts a search for the current waypoints. A running search is outdated then: it is
        cancelled, and the new one starts once it has stopped. The last route stays shown."""

        self.route = None

        if self._running is not None:
            self._running["cancelled"].set()
            self._search_again = True
            self.preview_changed.emit()
            return

        request = self._request()

        if request is None:
            self.shown_route = None
            self.preview_changed.emit()
            return

        self._search_number += 1
        cancelled = threading.Event()
        self._running = {"number": self._search_number, "cancelled": cancelled}
        finder = RouteFinder(self.costmap_provider(), self.vehicle_provider())
        number = self._search_number

        def search():
            result = finder.find(request, cancelled.is_set)

            try:
                self._search_done.emit(number, result)
            except RuntimeError:
                # The window was closed during the search.
                pass

        threading.Thread(target=search, daemon=True).start()

        self.searching_changed.emit(True)
        self.preview_changed.emit()

    def _request(self) -> RouteRequest | None:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or len(self.waypoints) < 2 or self.costmap_provider() is None:
            return None

        lanes = self._lanes(autodrive_data)

        return RouteRequest(
            tuple((waypoint.x, waypoint.z) for waypoint in self.waypoints),
            self._headings(autodrive_data, self.waypoints[0]),
            self._headings(autodrive_data, self.waypoints[-1]),
            tuple((lane.source, lane.target) for lane in lanes),
        )

    def _lanes(self, autodrive_data: AutoDriveData):
        """The planned lanes routes can share, without the connections that get split."""

        split = {waypoint.connection for waypoint in self.waypoints if waypoint.connection}
        split |= {(target, source) for source, target in split}

        return [
            lane
            for lane in planned_lanes(autodrive_data, self.plan_node_ids_provider())
            if (lane.source_id, lane.target_id) not in split
        ]

    @staticmethod
    def _headings(autodrive_data: AutoDriveData, waypoint: Waypoint) -> tuple[float, ...] | None:
        """The directions a vehicle drives through the waypoint, None for a free one."""

        if waypoint.node_id is not None:
            return node_headings(autodrive_data, waypoint.node_id)

        if waypoint.connection is None:
            return None

        source_id, target_id = waypoint.connection
        source, target = autodrive_data.nodes[source_id], autodrive_data.nodes[target_id]
        heading = math.atan2(target.z - source.z, target.x - source.x)
        headings = []

        if target_id in source.outgoing:
            headings.append(heading)

        if source_id in target.outgoing:
            headings.append(heading + math.pi if heading <= 0 else heading - math.pi)

        return tuple(headings) or None

    def _finish(self, number: int, route):
        if self._running is None or number != self._running["number"]:
            return

        self._running = None

        if self._search_again:
            self._search_again = False
            self._search()
            return

        self.searching_changed.emit(False)
        self.route = self.shown_route = route

        if route is None:
            self.status_changed.emit(tr("No route found through the waypoints"))
        elif not route.is_clear:
            self.status_changed.emit(
                tr("The route crosses obstacles (red). Move nodes or waypoints until it is clear")
            )
        else:
            message = tr("Route found. Enter adds it to the plan")
            self.status_changed.emit(". ".join([message, *self.join_warnings()]))

        self.preview_changed.emit()

    def _handle_data_changed(self, _data_change):
        """Waypoints on nodes or connections follow them; waypoints of deleted nodes or
        connections become free ones. The route is searched again, as moved nodes or the plan
        may change it."""

        autodrive_data = self.autodrive_data_provider()

        if not self.waypoints or autodrive_data is None:
            return

        for index, waypoint in enumerate(self.waypoints):
            if waypoint.connection is not None:
                self.waypoints[index] = self._on_connection(autodrive_data, waypoint)
                continue

            if waypoint.node_id is None:
                continue

            node = autodrive_data.nodes.get(waypoint.node_id)
            self.waypoints[index] = (
                Waypoint(waypoint.x, waypoint.z)
                if node is None
                else Waypoint(node.x, node.z, node.node_id)
            )

        self._search()

    @staticmethod
    def _on_connection(autodrive_data: AutoDriveData, waypoint: Waypoint) -> Waypoint:
        """The waypoint at its place on the connection, a free one if the connection is gone."""

        source_id, target_id = waypoint.connection
        source = autodrive_data.nodes.get(source_id)
        target = autodrive_data.nodes.get(target_id)

        if source is None or target is None or target_id not in source.outgoing:
            return Waypoint(waypoint.x, waypoint.z)

        fraction = waypoint.fraction

        return replace(
            waypoint,
            x=source.x + fraction * (target.x - source.x),
            z=source.z + fraction * (target.z - source.z),
        )

    def _route_command(self, autodrive_data: AutoDriveData, route: Route) -> AddRouteCommand:
        """The edit that adds the route."""

        lanes = self._lanes(autodrive_data)
        positions = {
            node_id: (node.x, node.z)
            for node_id in {lane.source_id for lane in lanes} | {lane.target_id for lane in lanes}
            if (node := autodrive_data.nodes.get(node_id)) is not None
        }
        next_id = max(autodrive_data.nodes, default=0) + 1
        new_nodes = []
        waypoint_ids = []
        split_connections = []

        # Free waypoints become new nodes; a waypoint on a connection splits it with a new node.
        for waypoint in self.waypoints:
            if waypoint.node_id is None:
                y = self.height_for_new_node(autodrive_data, waypoint.x, waypoint.z)
                new_nodes.append(NodeData(next_id, waypoint.x, y, waypoint.z))
                waypoint_ids.append(next_id)

                if waypoint.connection is not None:
                    source_id, target_id = waypoint.connection
                    state = read_connection_state(autodrive_data, source_id, target_id)
                    split_connections += [
                        (source_id, target_id, NO_CONNECTION),
                        (source_id, next_id, state),
                        (next_id, target_id, state),
                    ]

                next_id += 1
            else:
                waypoint_ids.append(waypoint.node_id)

            positions[waypoint_ids[-1]] = (waypoint.x, waypoint.z)

        vehicle = self.vehicle_provider()
        indices = route.waypoint_indices
        chain: list = [waypoint_ids[0]]

        for leg, (start_id, goal_id) in enumerate(pairwise(waypoint_ids)):
            points = route.points[indices[leg] : indices[leg + 1] + 1]
            leg_chain = route_nodes(
                points,
                start_id,
                goal_id,
                positions,
                lanes,
                self.spacing_provider(),
                vehicle.width + vehicle.margin,
            )
            chain += leg_chain[1:]

        node_ids = []

        for item in chain:
            if isinstance(item, int):
                node_ids.append(item)
                continue

            x, z = item
            y = self.height_for_new_node(autodrive_data, x, z)
            new_nodes.append(NodeData(next_id, x, y, z))
            node_ids.append(next_id)
            next_id += 1

        connections = split_connections + chain_connections(autodrive_data, node_ids)
        dual = CONNECTION_STATES[ConnectionType.DUAL]
        logger.debug(
            "Route of %d points: %d new nodes, existing nodes used %s, made dual %s",
            len(route.points),
            len(new_nodes),
            [item for item in chain if isinstance(item, int) and item in autodrive_data.nodes],
            [(source, target) for source, target, state in connections if state == dual],
        )

        return AddRouteCommand(tr("Find route"), autodrive_data, new_nodes, connections)
