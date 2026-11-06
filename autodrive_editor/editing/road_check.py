"""Checks of the planned road network (road_network, fitted by road_existing) on the network it
leaves behind: the existing nodes with the plan applied.

- Every move the map's traffic lanes allow through a junction can be driven: a path from
  APPROACH before the junction on the road in to APPROACH after it on the road out, at most
  DETOUR_FACTOR times the map's own way plus DETOUR_EXTRA.
- New nodes and the existing nodes joined to them lead on and are reached, except near the end
  of a map lane (map edge).
- New connections stay off blocked cells of the drivability map.

Failures are added to the network's list of places to look at.
"""

import heapq
import math
from dataclasses import replace
from itertools import pairwise

from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.editing.road_graph import (
    JOIN_DISTANCE,
    MAX_INNER_LENGTH,
    SAME_LEVEL,
    Grid,
    Point3,
    RoadGraph,
    Stretch,
    flat_distance,
    length,
    lerp,
)
from autodrive_editor.editing.road_network import SPAWN_LENGTH, RoadNetwork, _middle
from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, NavigationCostmap
from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData
from autodrive_editor.model.connections import ConnectionType

APPROACH = 30.0  # a move is checked from this far before the junction to this far after it
APPROACH_STEPS = (APPROACH, 45.0, 60.0)  # ... or further where no node fits there
DETOUR_FACTOR = 1.5  # the path may be this much longer than the map's own way ...
DETOUR_EXTRA = 30.0  # ... plus this (metres)
FIND_REACH = 8.0  # the nodes a move starts and ends at lie this close to the map lane ...
FIND_ANGLE = 45.0  # ... and head along it within this (degrees)
END_REACH = 15.0  # lane ends this close to the end of a map lane are no dead ends
SAMPLE_STEP = 1.0  # connections are checked on the drivability map every metre
REPORT_SPACING = 20.0  # blocked points this close to a listed one are not listed again


def check_road_network(
    network: RoadNetwork,
    graph: RoadGraph,
    autodrive_data: AutoDriveData,
    costmap: NavigationCostmap | None,
) -> RoadNetwork:
    """The network with the failures of all checks added to its list; no costmap, no check of
    blocked cells."""
    result = _Result(network.piece, autodrive_data)
    listed = list(network.listed)
    listed += _missing_moves(graph, network.groups, result)
    listed += _dead_ends(graph, network.piece, result)
    if costmap is not None:
        listed += _blocked(network.piece, autodrive_data, costmap)
    return replace(network, listed=listed)


def _new(index: int) -> int:
    """The key of a planned node in the result (existing nodes keep their IDs, which are > 0)."""
    return -1 - index


class _Result:
    """Positions and directed connections of the network after the plan is applied."""

    def __init__(self, piece: PlannedPiece, autodrive_data: AutoDriveData):
        nodes = autodrive_data.nodes
        self.points = {i: (n.x, n.y, n.z) for i, n in nodes.items() if i not in piece.removed}
        edges = {
            (i, t)
            for i, n in nodes.items()
            for t in n.outgoing
            if i in nodes[t].incoming and i in self.points and t in self.points
        } - set(piece.cut)
        for i, p in enumerate(piece.points):
            self.points[_new(i)] = tuple(p)
        for a, b, kind in piece.connections:
            edges.add((_new(a), _new(b)))
            if kind == ConnectionType.DUAL:
                edges.add((_new(b), _new(a)))
        for i, n, out in piece.joins:
            edges.add((_new(i), n) if out else (n, _new(i)))
        self.after, self.before = {n: set() for n in self.points}, {n: set() for n in self.points}
        for a, b in edges:
            self.after[a].add(b)
            self.before[b].add(a)
        self.grid = Grid(FIND_REACH)
        for n, p in self.points.items():
            self.grid.add(p[0], p[2], n)

    def fitting(self, point: Point3, heading: float, out: bool) -> list[int]:
        """Nodes near the point whose connections leave them (out) or lead in along the heading."""
        found = []
        for n in self.grid.near(point[0], point[2]):
            p = self.points[n]
            if flat_distance(p, point) > FIND_REACH or abs(p[1] - point[1]) > SAME_LEVEL:
                continue
            pairs = [(n, m) for m in self.after[n]] if out else [(m, n) for m in self.before[n]]
            if any(_fits(self._heading(*pair), heading) for pair in pairs):
                found.append(n)
        return found

    def reaches(self, starts: list[int], goals: list[int], limit: float) -> bool:
        """Whether a path no longer than the limit leads from a start to a goal."""
        goals = set(goals)
        best = dict.fromkeys(starts, 0.0)
        todo = [(0.0, n) for n in starts]
        while todo:
            d, n = heapq.heappop(todo)
            if n in goals:
                return True
            if d > best[n]:
                continue
            for m in self.after[n]:
                e = d + flat_distance(self.points[n], self.points[m])
                if e <= limit and e < best.get(m, math.inf):
                    best[m] = e
                    heapq.heappush(todo, (e, m))
        return False

    def _heading(self, a: int, b: int) -> float:
        p, q = self.points[a], self.points[b]
        return math.atan2(q[2] - p[2], q[0] - p[0])


def _missing_moves(graph: RoadGraph, groups, result: _Result) -> list[tuple[Point3, str]]:
    """One entry per junction where moves the map allows cannot be driven."""
    stretches, successors = graph.stretches, _successors(graph.stretches)
    listed = []
    for group in groups:
        internal = {
            i
            for i, s in enumerate(stretches)
            if s.start in group and s.end in group and length(s.points) <= MAX_INNER_LENGTH
        }
        moves = missing = 0
        for i, s in enumerate(stretches):
            if s.end not in group or i in internal or _spawn(s, s.start):
                continue
            back, starts = _approach(result, s.points[::-1], True)
            for t, through in _reached(i, successors, internal, stretches).items():
                out = stretches[t]
                if _spawn(out, out.end):
                    continue
                ahead, goals = _approach(result, out.points, False)
                moves += 1
                limit = DETOUR_FACTOR * (back + through + ahead) + DETOUR_EXTRA
                missing += not result.reaches(starts, goals, limit)
        if missing:
            text = tr("{missing} of {moves} turns missing", missing=missing, moves=moves)
            listed.append((_middle(graph, group), text))
    return listed


def _approach(result: _Result, points, start: bool) -> tuple[float, list[int]]:
    """How far from the junction a move is checked and the nodes there: APPROACH along the map
    lane (points from the junction outwards), further if no node fits there (box lanes run
    straight where the map lane bends). start: the move starts there (points reversed)."""
    size = length(points)
    for distance in APPROACH_STEPS:
        distance = min(distance, size)
        point, heading = _at(points, distance)
        nodes = result.fitting(point, heading + math.pi if start else heading, start)
        if nodes:
            break
    return distance, nodes


def _spawn(stretch: Stretch, far_end: int | None) -> bool:
    """A short lane from a road end: left out of the plan (spawn lane)."""
    return far_end is None and length(stretch.points) < SPAWN_LENGTH


def _successors(stretches) -> list[list[int]]:
    """Per stretch, the stretches that start where it ends."""
    starts = Grid(1.0)
    for i, s in enumerate(stretches):
        starts.add(s.points[0][0], s.points[0][2], i)
    return [
        [j for j in starts.near(s.points[-1][0], s.points[-1][2])
         if math.dist(s.points[-1], stretches[j].points[0]) <= JOIN_DISTANCE]
        for s in stretches
    ]  # fmt: skip


def _reached(start: int, successors, internal: set[int], stretches) -> dict[int, float]:
    """The stretches out of the junction reached from `start` through internal ones, with the
    shortest way through them (metres)."""
    best, reached = {}, {}
    todo = [(0.0, j) for j in successors[start]]
    while todo:
        d, s = heapq.heappop(todo)
        if s not in internal:
            reached.setdefault(s, d)
            continue
        if s in best:
            continue
        best[s] = d
        e = d + length(stretches[s].points)
        for j in successors[s]:
            heapq.heappush(todo, (e, j))
    return reached


def _at(points, distance: float) -> tuple[Point3, float]:
    """The point that far along the line and the heading there."""
    heading = 0.0
    for a, b in pairwise(points):
        size = flat_distance(a, b)
        if size == 0:
            continue
        heading = math.atan2(b[2] - a[2], b[0] - a[0])
        if distance <= size:
            return lerp(a, b, distance / size), heading
        distance -= size
    return points[-1], heading


def _fits(heading: float, other: float) -> bool:
    return abs(math.remainder(heading - other, math.tau)) <= math.radians(FIND_ANGLE)


def _dead_ends(graph: RoadGraph, piece: PlannedPiece, result: _Result) -> list:
    """New nodes and existing nodes joined to them that lead nowhere or are never reached, away
    from the map lanes' ends. Open ends are already listed."""
    map_ends = Grid(END_REACH)
    for s in graph.stretches:
        for end, p in ((s.start, s.points[0]), (s.end, s.points[-1])):
            if end is None:
                map_ends.add(p[0], p[2], p)
    checked = {_new(i) for i in range(len(piece.points))} - {_new(i) for i in piece.open_ends}
    checked |= {n for _, n, _ in piece.joins}
    listed = []
    for n in sorted(checked):
        p = result.points[n]
        if any(flat_distance(p, q) <= END_REACH for q in map_ends.near(p[0], p[2])):
            continue
        if not result.after[n]:
            listed.append((p, tr("Dead end")))
        elif not result.before[n]:
            listed.append((p, tr("Lane never reached")))
    return listed


def _blocked(piece: PlannedPiece, autodrive_data: AutoDriveData, costmap) -> list:
    """Places where new connections run over blocked cells, one entry per REPORT_SPACING."""
    nodes = autodrive_data.nodes
    segments = [(piece.points[a], piece.points[b]) for a, b, _ in piece.connections]
    segments += [(piece.points[i], (nodes[n].x, nodes[n].y, nodes[n].z)) for i, n, _ in piece.joins]
    seen, listed = Grid(REPORT_SPACING), []
    for a, b in segments:
        steps = max(1, math.ceil(flat_distance(a, b) / SAMPLE_STEP))
        for k in range(steps + 1):
            p = lerp(a, b, k / steps)
            if costmap.value_at(p[0], p[2]) < BLOCKED_VALUE:
                continue
            if not any(flat_distance(p, q) <= REPORT_SPACING for q in seen.near(p[0], p[2])):
                seen.add(p[0], p[2], p)
                listed.append((p, tr("Road over blocked ground")))
    return listed
