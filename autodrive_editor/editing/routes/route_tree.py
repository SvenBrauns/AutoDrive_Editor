"""Several routes built as a tree, e.g. from every start to every end of Find route.

The routes are searched one after another; each one has the routes searched before as planned
lanes, so it merges into them where that is cheap. When one route changes, only that one is
searched again, with all others as lanes. Its nodes are shared the same way: a route uses the
nodes of the routes before it where it runs along them, also right at a start, goal or waypoint
they have in common, so routes with the same start run together and branch off later.
"""

import math
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from itertools import pairwise

from autodrive_editor.editing.routes.route_finder import (
    Point,
    Route,
    RouteFinder,
    RouteRequest,
    _distance_to_segment,
)
from autodrive_editor.editing.routes.route_nodes import (
    SNAP_ALIGNMENT,
    SNAP_DISTANCE,
    PlannedLane,
    chain_connections,
    route_nodes,
)
from autodrive_editor.editing.routes.route_pipeline import bisector
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionState, ConnectionType

# A route that runs this close beside a changed one, roughly parallel, over at least NEAR_LENGTH
# without sharing it is searched again, so it may join the changed one.
NEAR_DISTANCE = 7.0
NEAR_LENGTH = 20.0


@dataclass(frozen=True)
class TreeRoute:
    """A route of the tree: the keys of its waypoints from start to goal and the route found."""

    keys: tuple[int, ...]
    route: Route


@dataclass(frozen=True)
class TreeNodes:
    """Where the routes' waypoints and the planned lanes are, for turning routes into nodes."""

    # The node ID of each waypoint key; new nodes for free waypoints get IDs from the caller.
    node_ids: dict[int, int]
    # The position of each of those nodes and of the lane ends.
    positions: dict[int, Point]
    lanes: tuple[PlannedLane, ...]
    spacing: float
    lane_width: float
    # The first ID for new nodes along the routes.
    next_id: int


@dataclass
class TreeChains:
    # Per route the node IDs in driving order.
    chains: list[list[int]]
    # Positions of the new nodes along the routes.
    new_positions: dict[int, Point]
    # The connections between the chains' nodes, as planned lanes.
    lanes: list[PlannedLane]


def tree_chains(routes: list[TreeRoute], nodes: TreeNodes) -> TreeChains:
    """The routes as node chains, built in order: each route shares the nodes of the routes
    before it where it runs along them (see route_nodes)."""

    positions = dict(nodes.positions)
    next_id = nodes.next_id
    result = TreeChains([], {}, [])
    # The lanes of the legs built so far, each with its leg's start and goal key.
    leg_lanes: list[tuple[int, int, PlannedLane]] = []
    # The node IDs of each leg built so far, by its start and goal key.
    built_legs: dict[tuple[int, int], list[int]] = {}

    for tree_route in routes:
        keys, route = tree_route.keys, tree_route.route
        indices = route.waypoint_indices
        chain = [nodes.node_ids[keys[0]]]

        for leg, (start_key, goal_key) in enumerate(pairwise(keys)):
            # A leg between the same waypoints as one built before takes its nodes, even if
            # the search ran a little differently.
            if (start_key, goal_key) in built_legs:
                chain += built_legs[(start_key, goal_key)][1:]
                continue

            shared_ends = frozenset(
                (lane.source_id, lane.target_id)
                for start, goal, lane in leg_lanes
                if start == start_key or goal == goal_key
            )
            leg_chain = route_nodes(
                route.points[indices[leg] : indices[leg + 1] + 1],
                nodes.node_ids[start_key],
                nodes.node_ids[goal_key],
                positions,
                [*nodes.lanes, *(lane for _, _, lane in leg_lanes)],
                nodes.spacing,
                nodes.lane_width,
                shared_ends,
            )
            ids = []

            for item in leg_chain:
                if isinstance(item, int):
                    ids.append(item)
                    continue

                positions[next_id] = result.new_positions[next_id] = item
                ids.append(next_id)
                next_id += 1

            for source, target in pairwise(ids):
                lane = PlannedLane(source, target, positions[source], positions[target])
                leg_lanes.append((start_key, goal_key, lane))

            built_legs[(start_key, goal_key)] = ids
            chain += ids[1:]

        result.chains.append(chain)

    result.lanes = [lane for _, _, lane in leg_lanes]

    return result


def shared_headings(routes: list[tuple[int, ...]], points: dict[int, Point]) -> dict[int, float]:
    """The heading at each inner waypoint that several routes pass: halfway between the headings
    each route alone would pass it at (see bisector). So the routes pass it alike and can run
    as one up to there."""

    headings = defaultdict(list)

    for keys in routes:
        for before, key, after in zip(keys, keys[1:], keys[2:], strict=False):
            headings[key].append(bisector(points[before], points[key], points[after]))

    return {
        key: math.atan2(sum(map(math.sin, values)), sum(map(math.cos, values)))
        for key, values in headings.items()
        if len(values) > 1
    }


def tree_connections(
    autodrive_data: AutoDriveData, chains: list[list[int]]
) -> list[tuple[int, int, ConnectionState]]:
    """The connections the chains need (see chain_connections), each pair once; a pair that
    chains drive both ways becomes dual."""

    dual = CONNECTION_STATES[ConnectionType.DUAL]
    connections: dict[tuple[int, int], ConnectionState] = {}

    for chain in chains:
        for source, target, state in chain_connections(autodrive_data, chain):
            if (target, source) in connections:
                connections[(target, source)] = dual
            elif (source, target) not in connections:
                connections[(source, target)] = state

    return [(source, target, state) for (source, target), state in connections.items()]


def runs_beside(route: Route, other: Route) -> bool:
    """Whether the route runs close beside the other one, roughly parallel, over NEAR_LENGTH
    without sharing it (closer than SNAP_DISTANCE)."""

    segments = list(pairwise(other.points))
    length = 0.0

    for a, b in pairwise(route.points):
        step = math.dist(a, b)

        if step < 1e-6:
            continue

        middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        distance, c, d = min(
            ((_distance_to_segment(middle, c, d), c, d) for c, d in segments), default=(None,) * 3
        )

        if distance is None or not SNAP_DISTANCE < distance <= NEAR_DISTANCE:
            continue

        other_step = math.dist(c, d)
        alignment = ((b[0] - a[0]) * (d[0] - c[0]) + (b[1] - a[1]) * (d[1] - c[1])) / (
            step * other_step or 1.0
        )

        if abs(alignment) >= SNAP_ALIGNMENT:
            length += step

    return length >= NEAR_LENGTH


@dataclass
class TreeSearch:
    """A search of the tree's routes, with all inputs read on the UI thread."""

    keys: list[tuple[int, ...]]
    # The request of each route, with the planned lanes but not those of the other routes.
    requests: list[RouteRequest]
    # The routes found; None for those to search.
    routes: list[Route | None]
    nodes: TreeNodes

    def run(self, finder: RouteFinder, cancelled: Callable[[], bool]) -> list[Route | None] | None:
        """Searches the missing routes one after another, each with all other routes found as
        lanes. If some routes stayed, those running close beside a searched one are searched
        again. Returns the routes, None if cancelled."""

        searched = [index for index, route in enumerate(self.routes) if route is None]
        kept = [index for index in range(len(self.routes)) if index not in searched]

        for index in searched:
            if not self._search(finder, index, cancelled):
                return None

        changed = [self.routes[index] for index in searched if self.routes[index] is not None]

        for index in kept:
            if any(runs_beside(self.routes[index], route) for route in changed):
                if not self._search(finder, index, cancelled):
                    return None

        return self.routes

    def _search(self, finder: RouteFinder, index: int, cancelled) -> bool:
        others = [
            TreeRoute(keys, route)
            for other, (keys, route) in enumerate(zip(self.keys, self.routes, strict=True))
            if other != index and route is not None and route.is_complete
        ]
        lanes = tree_chains(others, self.nodes).lanes
        request = self.requests[index]
        request = replace(
            request, lanes=request.lanes + tuple((lane.source, lane.target) for lane in lanes)
        )
        route = finder.find(request, cancelled)

        if cancelled():
            return False

        self.routes[index] = route

        return True
