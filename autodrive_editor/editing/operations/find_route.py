import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path

from PySide6.QtCore import Signal

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
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
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Waypoint:
    """A point the route passes: an existing node or a free map position."""

    x: float
    z: float
    node_id: int | None = None


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
        self.edit_history.planning_changed.connect(lambda _planning: self._search())

    @property
    def is_searching(self) -> bool:
        return self._running is not None

    def add_waypoint(self, x: float, z: float, node_id: int | None = None):
        if node_id is not None:
            node = self.autodrive_data_provider().nodes[node_id]
            x, z = node.x, node.z

        if self.waypoints and (self.waypoints[-1].x, self.waypoints[-1].z) == (x, z):
            return

        self.waypoints.append(Waypoint(x, z, node_id))
        self._search()

    def remove_waypoint(self, index: int):
        del self.waypoints[index]
        self._search()

    def move_waypoint(self, index: int, x: float, z: float):
        """Moves a free waypoint."""

        self.waypoints[index] = replace(self.waypoints[index], x=x, z=z)
        self._search()

    def clear(self) -> bool:
        """Removes all waypoints. Returns whether there were any."""

        had_waypoints = bool(self.waypoints)
        self.waypoints = []
        self._search()

        return had_waypoints

    def apply(self) -> bool:
        """Adds the route to the plan. The last waypoint, now a node, starts the next route."""

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

        command, last_id = self._route_command(autodrive_data, self.route)
        last = self.waypoints[-1]
        # Set first, so the edit does not start a search for the old waypoints.
        self.waypoints = [Waypoint(last.x, last.z, last_id)]
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
            return tr("Find route needs the drivability map of a savegame. Link a savegame first")

        return tr(
            "The savegame has no drivability map yet. Save the game in Farming Simulator first "
            "(again after placing buildings)"
        )

    def _search(self):
        """Starts a search for the current waypoints. While one runs, the next starts after it,
        so dragging gives a new route as soon as the last one is done."""

        self.route = None

        if self._running is not None:
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
            self._search_done.emit(number, finder.find(request, cancelled.is_set))

        threading.Thread(target=search, daemon=True).start()

        self.searching_changed.emit(True)
        self.preview_changed.emit()

    def _request(self) -> RouteRequest | None:
        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or len(self.waypoints) < 2 or self.costmap_provider() is None:
            return None

        lanes = planned_lanes(autodrive_data, self.plan_node_ids_provider())
        first, last = self.waypoints[0], self.waypoints[-1]

        return RouteRequest(
            tuple((waypoint.x, waypoint.z) for waypoint in self.waypoints),
            node_headings(autodrive_data, first.node_id) if first.node_id is not None else None,
            node_headings(autodrive_data, last.node_id) if last.node_id is not None else None,
            tuple((lane.source, lane.target) for lane in lanes),
        )

    def _finish(self, number: int, route):
        if self._running is None or number != self._running["number"]:
            return

        self._running = None

        if self._search_again:
            self._search_again = False
            self.shown_route = route
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
            self.status_changed.emit(tr("Route found. Enter adds it to the plan"))

        self.preview_changed.emit()

    def _handle_data_changed(self, _data_change):
        """Waypoints on nodes follow them; waypoints of deleted nodes become free ones. The
        route is searched again, as moved nodes or the plan may change it."""

        autodrive_data = self.autodrive_data_provider()

        if not self.waypoints or autodrive_data is None:
            return

        for index, waypoint in enumerate(self.waypoints):
            if waypoint.node_id is None:
                continue

            node = autodrive_data.nodes.get(waypoint.node_id)
            self.waypoints[index] = (
                Waypoint(waypoint.x, waypoint.z)
                if node is None
                else Waypoint(node.x, node.z, node.node_id)
            )

        self._search()

    def _route_command(
        self, autodrive_data: AutoDriveData, route: Route
    ) -> tuple[AddRouteCommand, int]:
        """The edit that adds the route, and the ID of its last node."""

        lanes = planned_lanes(autodrive_data, self.plan_node_ids_provider())
        positions = {
            node_id: (node.x, node.z)
            for node_id in {lane.source_id for lane in lanes} | {lane.target_id for lane in lanes}
            if (node := autodrive_data.nodes.get(node_id)) is not None
        }
        next_id = max(autodrive_data.nodes, default=0) + 1
        new_nodes = []
        waypoint_ids = []

        # Free waypoints become new nodes.
        for waypoint in self.waypoints:
            if waypoint.node_id is None:
                y = self.height_for_new_node(autodrive_data, waypoint.x, waypoint.z)
                new_nodes.append(NodeData(next_id, waypoint.x, y, waypoint.z))
                waypoint_ids.append(next_id)
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

        connections = chain_connections(autodrive_data, node_ids)
        dual = CONNECTION_STATES[ConnectionType.DUAL]
        logger.debug(
            "Route of %d points: %d new nodes, existing nodes used %s, made dual %s",
            len(route.points),
            len(new_nodes),
            [item for item in chain if isinstance(item, int) and item in autodrive_data.nodes],
            [(source, target) for source, target, state in connections if state == dual],
        )

        command = AddRouteCommand(tr("Find route"), autodrive_data, new_nodes, connections)

        return command, waypoint_ids[-1]
