import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import Signal

from autodrive_editor.editing.commands.add_route import AddRouteCommand
from autodrive_editor.editing.edit_context import EditContext, EditOperation
from autodrive_editor.editing.operations.background_search import BackgroundSearch
from autodrive_editor.editing.routes.join_rules import join_problem
from autodrive_editor.editing.routes.route_finder import (
    CURVE_RADIUS,
    Route,
    RouteFinder,
    RouteRequest,
    Vehicle,
)
from autodrive_editor.editing.routes.route_nodes import SNAP_DISTANCE, node_headings, planned_lanes
from autodrive_editor.editing.routes.route_tree import (
    TreeNodes,
    TreeRoute,
    TreeSearch,
    shared_headings,
    tree_chains,
    tree_connections,
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

# A waypoint inserted this close to where routes split or merge goes into all of them.
SPLIT_DISTANCE = 5.0


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


@dataclass
class _Found:
    """The route last found for a start and end, and what it was searched with (see
    _searched_with); None once the network changed."""

    route: Route | None
    searched: tuple | None


class FindRouteOperation(EditOperation):
    """Find route: drivable routes from each start to each end through waypoints, which are
    existing nodes or free map positions. Usually there is one start and one end; with several,
    all starts and ends are existing nodes and a route from every start to every end forms a
    tree. Waypoints are kept by key; each route has its own list of them, and a waypoint can be
    in several routes. After each change the routes whose waypoints changed are searched again
    in a background thread (see route_tree) and shown as a preview; parts that cross obstacles
    are marked. apply() adds clear routes to the plan as one undo step."""

    # The waypoints or the previewed routes changed.
    preview_changed = Signal()
    # A search started or ended.
    searching_changed = Signal(bool)

    def __init__(
        self,
        context: EditContext,
        costmap_provider: Callable[[], NavigationCostmap | None],
        savegame_provider: Callable[[], Path | None],
        vehicle_provider: Callable[[], Vehicle],
        spacing_provider: Callable[[], float],
        plan_node_ids_provider: Callable[[], set[int]],
        height_for_new_node: Callable[[AutoDriveData, float, float], float],
        curve_radius_provider: Callable[[], float] = lambda: CURVE_RADIUS,
        parent=None,
    ):
        super().__init__(context, parent)

        self.costmap_provider = costmap_provider
        self.curve_radius_provider = curve_radius_provider
        self.savegame_provider = savegame_provider
        self.vehicle_provider = vehicle_provider
        self.spacing_provider = spacing_provider
        self.plan_node_ids_provider = plan_node_ids_provider
        self.height_for_new_node = height_for_new_node

        # The waypoints by key; keys grow in the order the waypoints were added.
        self.points: dict[int, Waypoint] = {}
        self.starts: list[int] = []
        self.ends: list[int] = []
        # The inner waypoints of the route from each start to each end.
        self._vias: dict[tuple[int, int], list[int]] = {}
        # Earlier states of the waypoints, for Ctrl+Z inside the tool.
        self._undo_waypoints: list[tuple] = []
        self._found: dict[tuple[int, int], _Found] = {}

        # Number of the latest search; results of older ones are dropped.
        self._search_number = 0
        self._running: dict | None = None
        self._search_again = False
        self._background = BackgroundSearch(self)
        self.edit_history.data_changed.connect(self._handle_data_changed)
        # Only an ended plan changes the planned lanes; a new plan is empty.
        self.edit_history.planning_changed.connect(lambda planning: planning or self._outdate())
        # A discarded plan is a complete reset, so its waypoints go too.
        self.edit_history.plan_discarded.connect(self.reset)

    @property
    def is_searching(self) -> bool:
        return self._running is not None

    @property
    def can_undo_waypoints(self) -> bool:
        return bool(self._undo_waypoints)

    @property
    def pairs(self) -> list[tuple[int, int]]:
        """The start and end key of each route."""

        return [(start, end) for start in self.starts for end in self.ends]

    @property
    def routes(self) -> list[tuple[int, ...]]:
        """The waypoint keys of each route, from start to end."""

        return [(start, *self._vias.get((start, end), ()), end) for start, end in self.pairs]

    @property
    def waypoints(self) -> list[Waypoint]:
        """The waypoints of the first route in order; without a route the starts and ends."""

        routes = self.routes
        keys = routes[0] if routes else [*self.starts, *self.ends]

        return [self.points[key] for key in keys]

    @property
    def is_tree(self) -> bool:
        return len(self.starts) > 1 or len(self.ends) > 1

    @property
    def current_routes(self) -> list[Route | None]:
        """Per route the route found for its current waypoints, None while there is none."""

        return [
            found.route if (found := self._found.get(pair)) and self._is_current(pair) else None
            for pair in self.pairs
        ]

    @property
    def shown_routes(self) -> list[Route | None]:
        """Per route the route last found, shown until the next one is found."""

        return [found.route if (found := self._found.get(pair)) else None for pair in self.pairs]

    @property
    def route(self) -> Route | None:
        """The route of a single start and end through the current waypoints, None while there
        is none or it is outdated."""

        routes = self.current_routes

        return routes[0] if len(routes) == 1 else None

    @property
    def shown_route(self) -> Route | None:
        routes = self.shown_routes

        return routes[0] if len(routes) == 1 else None

    def undo_waypoints(self) -> bool:
        """Takes back the last change of the waypoints (add, move, remove). Returns False if
        there is none, so Ctrl+Z goes on to the plan's undo."""

        if not self._undo_waypoints:
            return False

        points, self.starts, self.ends, vias = self._undo_waypoints.pop()
        self.points = points
        self._vias = vias
        self._search()

        return True

    def remember_waypoints(self):
        """Keeps the waypoints before a change, e.g. before a waypoint is dragged."""

        vias = {pair: list(keys) for pair, keys in self._vias.items()}
        self._undo_waypoints.append((dict(self.points), list(self.starts), list(self.ends), vias))

    def add_waypoint(self, x: float, z: float, node_id: int | None = None):
        """Adds a waypoint: the start, then the end; with one start and one end the end becomes
        an inner waypoint and this one the end. With several starts or ends it is an inner
        waypoint of all routes, before their ends."""

        if node_id is not None:
            node = self.autodrive_data_provider().nodes[node_id]
            x, z = node.x, node.z

        waypoints = self.waypoints

        if waypoints and (waypoints[-1].x, waypoints[-1].z) == (x, z):
            return

        self._add(Waypoint(x, z, node_id))

    def add_waypoint_on_connection(self, source_id: int, target_id: int, x: float, z: float):
        """Adds a waypoint on the connection, at the point closest to (x, z)."""

        nodes = self.autodrive_data_provider().nodes
        source, target = nodes[source_id], nodes[target_id]
        dx, dz = target.x - source.x, target.z - source.z
        length_squared = dx * dx + dz * dz or 1.0
        fraction = ((x - source.x) * dx + (z - source.z) * dz) / length_squared
        fraction = min(max(fraction, 0.01), 0.99)

        self._add(
            Waypoint(
                source.x + fraction * dx,
                source.z + fraction * dz,
                connection=(source_id, target_id),
                fraction=fraction,
            )
        )

    def add_start(self, node_id: int):
        """Adds another start at the node (Shift+click)."""

        self._add_end_node(node_id, self.starts)

    def add_end(self, node_id: int):
        """Adds another end at the node (Ctrl+click)."""

        self._add_end_node(node_id, self.ends)

    def _add(self, waypoint: Waypoint):
        if not self.starts or not self.ends:
            ends = self.ends if self.starts else self.starts
            others = self.starts if self.starts else self.ends

            if len(others) > 1 and waypoint.node_id is None:
                self.status_changed.emit(self._nodes_only_message())
                return

            self.remember_waypoints()
            ends.append(self._new_key(waypoint))
        elif not self.is_tree:
            self.remember_waypoints()
            (start,), (end,) = self.starts, self.ends
            vias = self._vias.pop((start, end), [])
            self.ends = [self._new_key(waypoint)]
            self._vias[(start, self.ends[0])] = [*vias, end]
        else:
            self.remember_waypoints()
            key = self._new_key(waypoint)

            for pair in self.pairs:
                self._vias.setdefault(pair, []).append(key)

        self._search()

    def _add_end_node(self, node_id: int, ends: list[int]):
        node = self.autodrive_data_provider().nodes[node_id]

        if any(self.points[key].node_id == node_id for key in (*self.starts, *self.ends)):
            return

        if any(self.points[key].node_id is None for key in (*self.starts, *self.ends)):
            self.status_changed.emit(self._nodes_only_message())
            return

        # A new route gets the waypoints all routes share.
        routes = self.routes
        shared = [key for key in routes[0][1:-1] if all(key in r for r in routes)] if routes else []

        self.remember_waypoints()
        ends.append(self._new_key(Waypoint(node.x, node.z, node_id)))

        for pair in self.pairs:
            self._vias.setdefault(pair, list(shared))

        self._search()

    @staticmethod
    def _nodes_only_message() -> str:
        return tr("With several starts or ends, all starts and ends are nodes")

    def _new_key(self, waypoint: Waypoint) -> int:
        key = max(self.points, default=-1) + 1
        self.points[key] = waypoint

        return key

    def join_warnings(self) -> list[str]:
        """Why existing nodes among the waypoints are poor places to join the routes."""

        autodrive_data = self.autodrive_data_provider()
        used = {key for keys in self.routes for key in keys}

        return [
            problem
            for key, waypoint in self.points.items()
            if waypoint.node_id is not None
            and key in used
            and (
                problem := join_problem(
                    autodrive_data, waypoint.node_id, key in self.starts, key in self.ends
                )
            )
        ]

    def legs_at(self, x: float, z: float, tolerance: float) -> dict[int, int]:
        """Per route whose shown route passes within `tolerance` of the point, the leg there:
        leg k runs from the route's waypoint k to k + 1. Routes that run together with one of
        these within SPLIT_DISTANCE of the point, as just past where they split, are included
        too. Outdated routes are left out."""

        shown = [
            (index, route)
            for index, (keys, route) in enumerate(zip(self.routes, self.shown_routes, strict=True))
            if route is not None and route.points and len(route.waypoint_indices) == len(keys)
        ]
        legs, nearests, close = {}, {}, []

        for index, route in shown:
            nearest = min(
                range(len(route.points)), key=lambda i: math.dist(route.points[i], (x, z))
            )
            nearests[index] = nearest

            if math.dist(route.points[nearest], (x, z)) <= tolerance:
                legs[index] = nearest
                close += [p for p in route.points if math.dist(p, (x, z)) <= SPLIT_DISTANCE]

        for index, route in shown:
            if index not in legs and any(
                math.dist(p, q) <= SNAP_DISTANCE for p in route.points for q in close
            ):
                legs[index] = nearests[index]

        return {
            index: max(
                leg for leg, start in enumerate(route.waypoint_indices[:-1]) if start <= legs[index]
            )
            for index, route in shown
            if index in legs
        }

    def insert_waypoint(self, x: float, z: float, legs: dict[int, int]) -> int:
        """Adds a free waypoint to each route of `legs` (see legs_at), in its leg there.
        Returns its key."""

        self.remember_waypoints()
        key = self._new_key(Waypoint(x, z))
        pairs = self.pairs

        for index, leg in legs.items():
            self._vias.setdefault(pairs[index], []).insert(leg, key)

        self._search()

        return key

    def remove_waypoint(self, key: int):
        """Removes the waypoint from all routes. A removed start or end takes its routes along;
        with one start and one end the next inner waypoint takes its place."""

        self.remember_waypoints()

        if key in self.starts or key in self.ends:
            single = not self.is_tree and self.pairs
            vias = self._vias.pop(self.pairs[0], []) if single else []

            for pair in self.pairs:
                if key in pair:
                    self._vias.pop(pair, None)

            if key in self.starts:
                self.starts.remove(key)

                if single and vias:
                    self.starts = [vias.pop(0)]
            else:
                self.ends.remove(key)

                if single and vias:
                    self.ends = [vias.pop()]

            if single and vias:
                self._vias[self.pairs[0]] = vias
        else:
            for vias in self._vias.values():
                if key in vias:
                    vias.remove(key)

        del self.points[key]
        self._search()

    def remove_last(self) -> bool:
        """Removes the waypoint added last. Returns whether there was one."""

        if not self.points:
            return False

        self.remove_waypoint(max(self.points))

        return True

    def move_waypoint(self, key: int, x: float, z: float):
        """Moves a free waypoint. A drag calls remember_waypoints() once before."""

        self.points[key] = replace(self.points[key], x=x, z=z)
        self._search()

    def clear(self) -> bool:
        """Removes all waypoints. Returns whether there were any."""

        had_waypoints = bool(self.points)

        if had_waypoints:
            self.remember_waypoints()

        self._set_empty()

        return had_waypoints

    def reset(self):
        """Starts empty, without waypoint undo, e.g. when the tool is left."""

        self._undo_waypoints = []
        self._set_empty()

    def _set_empty(self):
        self.points, self.starts, self.ends, self._vias = {}, [], [], {}
        self._search()

    def apply(self) -> bool:
        """Adds the routes to the plan. The tool starts empty; the next click picks a new
        start."""

        autodrive_data = self.autodrive_data_provider()

        if autodrive_data is None or not self.pairs or self.edit_history.history_locked:
            return False

        if not self.edit_history.is_planning:
            self.status_changed.emit(tr("Find route adds routes in planning mode"))
            return False

        routes = self.current_routes

        if self.is_searching or None in routes:
            self.status_changed.emit(
                tr("The routes are still being searched")
                if self.is_tree
                else tr("The route is still being searched")
            )
            return False

        if self.is_tree and not all(route.is_clear for route in routes):
            self.status_changed.emit(self._unclear_message(routes))
            return False

        if not routes[0].is_complete:
            self.status_changed.emit(self._gap_message(routes[0]))
            return False

        if not routes[0].is_clear:
            self.status_changed.emit(
                tr("The route crosses obstacles (red). Move or add waypoints first")
            )
            return False

        command = self._route_command(autodrive_data, routes)
        # Emptied first, so the edit does not start a search for the old waypoints.
        self.points, self.starts, self.ends, self._vias = {}, [], [], {}
        self._undo_waypoints = []
        self.edit_history.push(command)
        self.status_changed.emit(
            tr(
                "{routes} routes with {count} new nodes added",
                routes=len(routes),
                count=len(command.new_nodes),
            )
            if len(routes) > 1
            else tr("Route with {count} new nodes added", count=len(command.new_nodes))
        )

        return True

    def stop_search(self):
        """Cancels a running search and waits until it has ended. For closing the window."""

        self._background.stop()

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

    def _route_waypoints(self, keys: tuple[int, ...]) -> tuple[Waypoint, ...]:
        return tuple(self.points[key] for key in keys)

    def _shared_headings(self) -> dict[int, float]:
        points = {key: (waypoint.x, waypoint.z) for key, waypoint in self.points.items()}

        return shared_headings(self.routes, points)

    def _searched_with(self, keys: tuple[int, ...], shared: dict[int, float]) -> tuple:
        """What a route is searched with: its waypoints and their fixed headings."""

        return self._route_waypoints(keys), tuple(shared.get(key) for key in keys)

    def _is_current(self, pair: tuple[int, int]) -> bool:
        found = self._found.get(pair)
        keys = (pair[0], *self._vias.get(pair, ()), pair[1])

        return found is not None and found.searched == self._searched_with(
            keys, self._shared_headings()
        )

    def _outdate(self):
        """Marks all routes for a new search, e.g. after the network changed, and starts it."""

        for found in self._found.values():
            found.searched = None

        self._search()

    def _search(self):
        """Starts a search for the routes whose waypoints changed. A running search is outdated
        then: it is cancelled, and the new one starts once it has stopped. The last routes stay
        shown."""

        if self._running is not None:
            self._running["cancelled"].set()
            self._search_again = True
            self.preview_changed.emit()
            return

        pairs = self.pairs
        self._found = {pair: found for pair, found in self._found.items() if pair in pairs}
        autodrive_data = self.autodrive_data_provider()
        stale = [pair for pair in pairs if not self._is_current(pair)]

        if autodrive_data is None or not stale or self.costmap_provider() is None:
            if autodrive_data is None or self.costmap_provider() is None:
                self._found = {}

            self.preview_changed.emit()
            return

        search = self._tree_search(autodrive_data)
        shared = self._shared_headings()
        searched = {
            pair: self._searched_with(keys, shared)
            for pair, keys in zip(pairs, self.routes, strict=True)
        }
        self._search_number += 1
        finder = RouteFinder(self.costmap_provider(), self.vehicle_provider())
        number = self._search_number
        cancelled = self._background.start(
            lambda cancelled: search.run(finder, cancelled),
            lambda routes: self._finish(number, pairs, searched, routes),
            lambda: self._finish(number, stale, searched, None, failed=True),
        )
        self._running = {"number": number, "cancelled": cancelled}

        self.searching_changed.emit(True)
        self.preview_changed.emit()

    def _tree_nodes(self, autodrive_data: AutoDriveData) -> TreeNodes:
        """The nodes for the routes; waypoints that are no node get new IDs."""

        lanes = self._lanes(autodrive_data)
        positions = {
            node_id: (node.x, node.z)
            for node_id in {lane.source_id for lane in lanes} | {lane.target_id for lane in lanes}
            if (node := autodrive_data.nodes.get(node_id)) is not None
        }
        next_id = max(autodrive_data.nodes, default=0) + 1
        node_ids = {}

        for key, waypoint in self.points.items():
            if waypoint.node_id is None:
                node_ids[key] = next_id
                next_id += 1
            else:
                node_ids[key] = waypoint.node_id

            positions[node_ids[key]] = (waypoint.x, waypoint.z)

        vehicle = self.vehicle_provider()
        width = vehicle.width + vehicle.margin

        return TreeNodes(node_ids, positions, tuple(lanes), self.spacing_provider(), width, next_id)

    def _tree_search(self, autodrive_data: AutoDriveData) -> TreeSearch:
        lanes = tuple((lane.source, lane.target) for lane in self._lanes(autodrive_data))
        shared = self._shared_headings()
        requests = [
            RouteRequest(
                tuple((waypoint.x, waypoint.z) for waypoint in self._route_waypoints(keys)),
                self._headings(autodrive_data, self.points[keys[0]]),
                self._headings(autodrive_data, self.points[keys[-1]]),
                lanes,
                turning_radius=self.curve_radius_provider(),
                waypoint_headings=tuple(shared.get(key) for key in keys),
            )
            for keys in self.routes
        ]
        routes = [
            self._found[pair].route if self._is_current(pair) else None for pair in self.pairs
        ]

        return TreeSearch(self.routes, requests, routes, self._tree_nodes(autodrive_data))

    def _lanes(self, autodrive_data: AutoDriveData):
        """The planned lanes routes can share, without the connections that get split."""

        split = {waypoint.connection for waypoint in self.points.values() if waypoint.connection}
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

    def _finish(self, number: int, pairs, searched, routes, failed: bool = False):
        if self._running is None or number != self._running["number"]:
            return

        self._running = None

        if self._search_again:
            self._search_again = False
            self._search()
            return

        self.searching_changed.emit(False)

        for index, pair in enumerate(pairs):
            route = None if failed or routes is None else routes[index]
            self._found[pair] = _Found(route, searched[pair])

        routes = self.current_routes

        if failed:
            self.status_changed.emit(tr("The route search failed. Details are in the log file"))
        elif self.is_tree:
            if all(route is not None and route.is_clear for route in routes):
                message = tr("Routes found. Enter adds them to the plan")
                self.status_changed.emit(". ".join([message, *self.join_warnings()]))
            else:
                self.status_changed.emit(self._unclear_message(routes))
        elif routes[0] is None:
            self.status_changed.emit(tr("No route found through the waypoints"))
        elif not routes[0].is_complete:
            self.status_changed.emit(self._gap_message(routes[0]))
        elif not routes[0].is_clear:
            self.status_changed.emit(
                tr("The route crosses obstacles (red). Move nodes or waypoints until it is clear")
            )
        else:
            message = tr("Route found. Enter adds it to the plan")
            self.status_changed.emit(". ".join([message, *self.join_warnings()]))

        self.preview_changed.emit()

    def _unclear_message(self, routes: list[Route | None]) -> str:
        """Names the routes that are not clear, by their start and end node."""

        names = [
            f"{self.points[start].node_id} → {self.points[end].node_id}"
            for (start, end), route in zip(self.pairs, routes, strict=True)
            if route is None or not route.is_clear
        ]

        return tr(
            "Not clear yet (red): {routes}. Move or add waypoints there", routes=", ".join(names)
        )

    def _gap_message(self, route: Route) -> str:
        if route.too_close:
            return tr(
                "Waypoints {first} and {second} are too close for the curve radius of {radius} m "
                "(red dashed). Move them apart",
                first=route.gap_to,
                second=route.gap_to + 1,
                radius=f"{self.curve_radius_provider():g}",
            )

        return tr(
            "No drivable way found to waypoint {number} (red dashed). Move or add waypoints there",
            number=route.gap_to + 1,
        )

    def _handle_data_changed(self, _data_change):
        """Waypoints on nodes or connections follow them; waypoints of deleted nodes or
        connections become free ones. The routes are searched again, as moved nodes or the plan
        may change them."""

        autodrive_data = self.autodrive_data_provider()

        if not self.points or autodrive_data is None:
            return

        for key, waypoint in self.points.items():
            if waypoint.connection is not None:
                self.points[key] = self._on_connection(autodrive_data, waypoint)
                continue

            if waypoint.node_id is None:
                continue

            node = autodrive_data.nodes.get(waypoint.node_id)
            self.points[key] = (
                Waypoint(waypoint.x, waypoint.z)
                if node is None
                else Waypoint(node.x, node.z, node.node_id)
            )

        self._outdate()

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

    def _route_command(self, autodrive_data: AutoDriveData, routes: list[Route]) -> AddRouteCommand:
        """The edit that adds the routes."""

        nodes = self._tree_nodes(autodrive_data)
        new_nodes = []
        split_connections = []

        # Free waypoints become new nodes; a waypoint on a connection splits it with a new node.
        for key, waypoint in self.points.items():
            if waypoint.node_id is not None:
                continue

            node_id = nodes.node_ids[key]
            y = self.height_for_new_node(autodrive_data, waypoint.x, waypoint.z)
            new_nodes.append(NodeData(node_id, waypoint.x, y, waypoint.z))

            if waypoint.connection is not None:
                source_id, target_id = waypoint.connection
                state = read_connection_state(autodrive_data, source_id, target_id)
                split_connections += [
                    (source_id, target_id, NO_CONNECTION),
                    (source_id, node_id, state),
                    (node_id, target_id, state),
                ]

        tree = tree_chains(
            [TreeRoute(keys, route) for keys, route in zip(self.routes, routes, strict=True)],
            nodes,
        )

        for node_id, (x, z) in tree.new_positions.items():
            new_nodes.append(
                NodeData(node_id, x, self.height_for_new_node(autodrive_data, x, z), z)
            )

        connections = split_connections + tree_connections(autodrive_data, tree.chains)
        dual = CONNECTION_STATES[ConnectionType.DUAL]
        logger.debug(
            "%d routes: %d new nodes, existing nodes used %s, made dual %s",
            len(routes),
            len(new_nodes),
            sorted({n for chain in tree.chains for n in chain if n in autodrive_data.nodes}),
            [(source, target) for source, target, state in connections if state == dual],
        )

        return AddRouteCommand(tr("Find route"), autodrive_data, new_nodes, connections)
