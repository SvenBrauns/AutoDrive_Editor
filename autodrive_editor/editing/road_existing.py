"""The planned road network (road_network) fitted to the existing AutoDrive network.

Skip and connect: planned connections that run along existing regular ones in the same direction
are left out, and so are planned junctions with existing nodes inside (the existing junction is
kept); the cut ends join the existing lanes by the join rules, and where no node fits an existing
connection is split. Replace: the existing regular nodes on connections the plan runs along and
those inside planned junctions are removed; their markers move to the new lanes and the branches
that led to them join the new lanes.

Both networks are taken as directed connections, a two-way connection as one each way: a planned
two-way lane next to an existing one-way lane keeps the other direction. Subprio nodes are never
covered or removed.
"""

import copy
import math
from collections import defaultdict

from autodrive_editor.editing.join_rules import join_problem
from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.editing.road_graph import SAME_LEVEL, Grid, Point3, flat_distance, lerp
from autodrive_editor.editing.road_network import RoadNetwork
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import ConnectionType

ALONG_ANGLE = 20.0  # a connection runs along another if their headings differ by less (degrees)
ALONG_EXTRA = 2.0  # ... and both its ends are within half the lane gap plus this (metres)
AREA_MARGIN = 2.0  # nodes this close outside a junction outline count as inside it
SHORT_BIT = 20.0  # shorter planned bits between left-out parts are left out too
JOIN_REACH = 12.0  # a cut end joins the other network this close to the node it lost
JOIN_ANGLE = 45.0  # ... where that network heads at most this far off the way it went on
MERGE_REACH = 1.0  # a cut end this close to an existing node becomes that node
SPLIT_KEEP = 1.0  # a connection is split at least this far from its ends

Edge = tuple[int, int]


class _Net:
    """Positions and directed connections of the planned or the existing network."""

    def __init__(self, points: dict[int, Point3], edges: set[Edge]):
        self.points, self.edges = points, edges
        self.after, self.before = defaultdict(set), defaultdict(set)
        for a, b in edges:
            self.after[a].add(b)
            self.before[b].add(a)

    def heading(self, a: int, b: int) -> float:
        p, q = self.points[a], self.points[b]
        return math.atan2(q[2] - p[2], q[0] - p[0])

    def onward(self, node: int, out: bool) -> list[float]:
        """Headings of the connections that leave the node (out) or lead into it."""
        if out:
            return [self.heading(node, n) for n in self.after[node]]
        return [self.heading(n, node) for n in self.before[node]]


def fit_to_existing(
    network: RoadNetwork, autodrive_data: AutoDriveData, replace: bool, gap: float
) -> RoadNetwork:
    """The plan for *skip and connect* (replace False) or *replace*; gap is the lane gap."""
    nodes = autodrive_data.nodes
    points = {i: (n.x, n.y, n.z) for i, n in nodes.items()}
    edges = {(i, t) for i, n in nodes.items() for t in n.outgoing if i in nodes[t].incoming}
    regular = {i for i, n in nodes.items() if n.is_regular}
    existing = _Net(points, edges)
    road = _Net(points, {e for e in edges if e[0] in regular and e[1] in regular})
    planned = _planned_net(network.piece)
    reach = gap / 2 + ALONG_EXTRA
    if replace:
        return _replace(network, autodrive_data, planned, existing, road, regular, reach)
    return _skip(network, autodrive_data, planned, road, regular, reach)


def _skip(network, autodrive_data, planned, road, regular, reach) -> RoadNetwork:
    listed = list(network.listed)
    road_grid = _edge_grid(road)
    road_nodes = _node_grid(road, regular)
    planned_nodes = _node_grid(planned, planned.points)
    gone = set()
    for area in network.areas:
        inside = _in_area(road_nodes, road, area)
        if inside:
            gone |= _in_area(planned_nodes, planned, area)
            height = road.points[min(inside)][1]
            listed.append((_area_point(area, height), tr("Existing junction kept")))
    dropped = {
        e
        for e in planned.edges
        if e[0] in gone or e[1] in gone or _covered(e, planned, road_grid, road, reach)
    }
    kept = planned.edges - dropped
    gone |= set(planned.points) - {n for e in kept for n in e}
    lost = {n for e in dropped for n in e} - gone
    for part_nodes, part_edges in _parts(kept):
        pairs = {tuple(sorted(e)) for e in part_edges}
        size = sum(flat_distance(planned.points[a], planned.points[b]) for a, b in pairs)
        if len(part_nodes & lost) >= 2 and size < SHORT_BIT:
            gone |= part_nodes
    kept = {e for e in kept if e[0] not in gone}
    dropped = planned.edges - kept

    needs = _needs(dropped, gone, kept)
    # A cut end on an existing node becomes that node.
    merged = {
        k: e
        for k in sorted({k for k, _, _ in needs})
        if (e := _merge_target(planned.points[k], road_nodes, road, autodrive_data)) is not None
    }
    gone |= set(merged)

    piece, new = network.piece, PlannedPiece()
    index = {
        i: new.add(*piece.points[i], flag=piece.flags[i])
        for i in sorted(planned.points)
        if i not in gone
    }
    edges = {(index[a], index[b]) for a, b in kept if a in index and b in index}
    for a, b in sorted(kept):
        if a in merged and b in index:
            new.joins.append((index[b], merged[a], False))
        elif b in merged and a in index:
            new.joins.append((index[a], merged[b], True))
    splits = {}  # existing connection -> index of the new node splitting it
    for k, out, m in needs:
        if k in merged:
            continue
        headings = planned.onward(m, out) or [planned.heading(*((k, m) if out else (m, k)))]
        near = planned.points[m]
        targets = _targets(
            near, road_nodes, road, headings, out,
            lambda e, out=out: join_problem(autodrive_data, e, starts=not out, ends=out) is None,
        )  # fmt: skip
        new.joins += [(index[k], e, out) for e in targets]
        if targets:
            continue
        t = _split(near, headings, road, road_grid, splits, new)
        if t is None:
            new.open_ends.append(index[k])
            listed.append((planned.points[k], tr("Road end not joined to the network")))
        else:
            edges.add((index[k], t) if out else (t, index[k]))
    _connect(new, edges)
    new.markers += [(index[i], name, group) for i, name, group in piece.markers if i in index]
    new.open_ends += [index[i] for i in piece.open_ends if i in index]
    return RoadNetwork(new, listed, network.areas)


def _replace(network, autodrive_data, planned, existing, road, regular, reach) -> RoadNetwork:
    listed = list(network.listed)
    plan_grid = _edge_grid(planned)
    road_nodes = _node_grid(road, regular)
    planned_nodes = _node_grid(planned, planned.points)
    removed = set()
    for area in network.areas:
        removed |= _in_area(road_nodes, road, area)
    removed |= {n for e in road.edges if _covered(e, road, plan_grid, planned, reach) for n in e}
    dropped = {e for e in existing.edges if e[0] in removed or e[1] in removed}

    new = copy.deepcopy(network.piece)
    new.removed |= removed
    for k, out, m in _needs(dropped, removed, existing.edges - dropped):
        # The branch drives on each way the old road did from the lost node.
        headings = road.onward(m, out) or [existing.heading(*((k, m) if out else (m, k)))]
        targets = _targets(existing.points[m], planned_nodes, planned, headings, out)
        if not targets:
            listed.append((existing.points[k], tr("Branch not joined to the new road")))
        new.joins += [(p, k, not out) for p in targets]
    for m in sorted(removed & set(autodrive_data.markers)):
        marker, point = autodrive_data.markers[m], existing.points[m]
        p = _nearest_fitting(point, planned_nodes, planned, road.onward(m, True), True)
        if p is None:
            p = min(planned.points, key=lambda i: flat_distance(planned.points[i], point))
        new.markers.append((p, marker.name, marker.group))
    return RoadNetwork(new, listed, network.areas)


def _planned_net(piece: PlannedPiece) -> _Net:
    edges = set()
    for a, b, kind in piece.connections:
        edges.add((a, b))
        if kind == ConnectionType.DUAL:
            edges.add((b, a))
    return _Net(dict(enumerate(piece.points)), edges)


def _connect(piece: PlannedPiece, edges: set[Edge]) -> None:
    """The edges as connections, both ways of a pair as one two-way connection."""
    for a, b in sorted(edges):
        if (b, a) not in edges:
            piece.connect(a, b)
        elif a < b:
            piece.connect(a, b, ConnectionType.DUAL)


def _needs(dropped: set[Edge], gone: set[int], kept: set[Edge]) -> list[tuple[int, bool, int]]:
    """(kept node, out, the node it lost) for each connection taken away from a kept node that
    traffic still wants: the node is still reached from (out) or still leads to another node than
    the lost one, or it has no connections left."""
    into, out_of = defaultdict(set), defaultdict(set)
    for a, b in kept:
        out_of[a].add(b)
        into[b].add(a)

    def wanted(k: int, others: set[int], m: int) -> bool:
        return k not in gone and (bool(others - {m}) or not (into[k] or out_of[k]))

    needs = [(a, True, b) for a, b in dropped if wanted(a, into[a], b)]
    needs += [(b, False, a) for a, b in dropped if wanted(b, out_of[b], a)]
    return sorted(needs)


def _targets(near: Point3, grid: Grid, net: _Net, headings, out: bool, allowed=None) -> list:
    """For each heading the nearest fitting node (see _nearest_fitting), each node once."""
    found = (_nearest_fitting(near, grid, net, [h], out, allowed) for h in headings)
    return sorted({n for n in found if n is not None})


def _merge_target(point: Point3, grid: Grid, road: _Net, autodrive_data) -> int | None:
    """An existing regular node without a marker within MERGE_REACH of the point."""
    for n in grid.near(point[0], point[2]):
        p = road.points[n]
        close = flat_distance(p, point) <= MERGE_REACH and abs(p[1] - point[1]) <= SAME_LEVEL
        if close and n not in autodrive_data.markers:
            return n
    return None


def _nearest_fitting(near: Point3, grid: Grid, net: _Net, headings, out: bool, allowed=None):
    """The node of the net nearest to `near` within JOIN_REACH whose connections leave it (out)
    or lead into it within JOIN_ANGLE of one of the headings, or None."""
    best = None
    for n in grid.near(near[0], near[2]):
        p = net.points[n]
        d = flat_distance(p, near)
        if d > JOIN_REACH or abs(p[1] - near[1]) > SAME_LEVEL or (best and d >= best[0]):
            continue
        if _fits(net.onward(n, out), headings, JOIN_ANGLE) and (allowed is None or allowed(n)):
            best = d, n
    return None if best is None else best[1]


def _split(near: Point3, headings, road: _Net, grid: Grid, splits: dict, piece: PlannedPiece):
    """The index of a new node on the existing connection nearest to `near` that heads along one
    of the headings, split there; None if there is none within JOIN_REACH."""
    best = None
    for c, d in set(grid.near(near[0], near[2])):
        if not _fits([road.heading(c, d)], headings, JOIN_ANGLE):
            continue
        a, b = road.points[c], road.points[d]
        size = flat_distance(a, b)
        if size < 2 * SPLIT_KEEP:
            continue
        t = min(max(_along(near, a, b), SPLIT_KEEP / size), 1 - SPLIT_KEEP / size)
        point = lerp(a, b, t)
        distance = flat_distance(point, near)
        if distance <= JOIN_REACH and abs(point[1] - near[1]) <= SAME_LEVEL:
            if best is None or distance < best[0]:
                best = distance, (c, d), point
    if best is None:
        return None
    _, (c, d), point = best
    if (c, d) in splits:
        return splits[c, d]
    t = splits[c, d] = piece.add(*point)
    piece.joins += [(t, c, False), (t, d, True)]
    piece.cut.append((c, d))
    if (d, c) in road.edges:  # two-way: split the way back as well
        splits[d, c] = t
        piece.joins += [(t, d, False), (t, c, True)]
        piece.cut.append((d, c))
    return t


def _covered(edge: Edge, net: _Net, grid: Grid, other: _Net, reach: float) -> bool:
    """Both ends of the connection lie within reach of connections of the other net that head
    the same way (within ALONG_ANGLE)."""
    heading = net.heading(*edge)
    return all(_along_other(net.points[n], heading, grid, other, reach) for n in edge)


def _along_other(p: Point3, heading: float, grid: Grid, other: _Net, reach: float) -> bool:
    for c, d in grid.near(p[0], p[2]):
        if not _fits([other.heading(c, d)], [heading], ALONG_ANGLE):
            continue
        a, b = other.points[c], other.points[d]
        q = lerp(a, b, _along(p, a, b))
        if flat_distance(p, q) <= reach and abs(p[1] - q[1]) <= SAME_LEVEL:
            return True
    return False


def _fits(own, headings, angle: float) -> bool:
    limit = math.radians(angle)
    return any(abs(math.remainder(h - g, math.tau)) < limit for h in own for g in headings)


def _along(p: Point3, a: Point3, b: Point3) -> float:
    """Where p lies along segment a-b (0 to 1)."""
    dx, dz = b[0] - a[0], b[2] - a[2]
    size = dx * dx + dz * dz
    if size == 0:
        return 0.0
    return min(max(((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / size, 0.0), 1.0)


def _parts(edges: set[Edge]) -> list[tuple[set[int], set[Edge]]]:
    """The connected parts (nodes, edges), directions ignored."""
    neighbours = defaultdict(set)
    for a, b in edges:
        neighbours[a].add(b)
        neighbours[b].add(a)
    seen, parts = set(), []
    for start in neighbours:
        if start in seen:
            continue
        nodes, todo = {start}, [start]
        while todo:
            for n in neighbours[todo.pop()] - nodes:
                nodes.add(n)
                todo.append(n)
        seen |= nodes
        parts.append((nodes, {e for e in edges if e[0] in nodes}))
    return parts


def _edge_grid(net: _Net) -> Grid:
    grid = Grid(JOIN_REACH)
    for a, b in net.edges:
        grid.add_segment(net.points[a], net.points[b], (a, b))
    return grid


def _node_grid(net: _Net, nodes) -> Grid:
    grid = Grid(JOIN_REACH)
    for n in nodes:
        grid.add(net.points[n][0], net.points[n][2], n)
    return grid


def _in_area(grid: Grid, net: _Net, area) -> set[int]:
    """The nodes of the grid inside the outline or within AREA_MARGIN of it."""
    xs, zs = [p[0] for p in area], [p[1] for p in area]
    m = AREA_MARGIN
    found = grid.box(min(xs) - m, min(zs) - m, max(xs) + m, max(zs) + m)
    return {n for n in found if _inside(area, net.points[n])}


def _inside(area, p: Point3) -> bool:
    x, z = p[0], p[2]
    corners = list(zip(area, area[1:] + area[:1], strict=True))
    if len(area) >= 3 and all(
        (b[0] - a[0]) * (z - a[1]) - (b[1] - a[1]) * (x - a[0]) >= 0 for a, b in corners
    ):
        return True
    point = (x, 0.0, z)
    return any(
        flat_distance(point, lerp(a3, b3, _along(point, a3, b3))) <= AREA_MARGIN
        for a3, b3 in (((a[0], 0.0, a[1]), (b[0], 0.0, b[1])) for a, b in corners)
    )


def _area_point(area, height: float) -> Point3:
    return sum(p[0] for p in area) / len(area), height, sum(p[1] for p in area) / len(area)
