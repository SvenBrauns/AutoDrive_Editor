"""The road network generator: the roads of a road graph (road_centre) built as AutoDrive lanes in
the network's style.

Pair style: a two-way road becomes two one-way lanes `gap` apart, each on the side where the map
drives it; two-way style: one two-way lane on the centre line. One-way roads, the lanes inside
junctions (turn lanes, roundabout rings) and the bits of map lane that no road piece follows are
the map's own lanes. Generated lane ends snap to the
map lane ends next to them, so every move the map allows stays possible. Nodes are spaced as
AutoDrive records a drive; heights come from the map's lanes.

Points are world positions (x, height, z).
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import pairwise

from autodrive_editor.editing.junction import LANE_GAP
from autodrive_editor.editing.parallel_lane import ParallelLaneError, offset_polyline
from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.editing.road_centre import RoadPiece, road_pieces
from autodrive_editor.editing.road_graph import (
    SAME_LEVEL,
    Grid,
    Point3,
    RoadGraph,
    _between,
    flat_distance,
    length,
    lerp,
)
from autodrive_editor.editing.yard_road import road_points
from autodrive_editor.i18n import tr
from autodrive_editor.model.connections import ConnectionType

SNAP_REACH = 8.0  # a generated lane end joins a lane end this close (metres) ...
SNAP_ANGLE = 45.0  # ... whose heading differs by at most this (degrees)
NODE_SNAP = 0.5  # lane ends this close share a node
MIN_REST = 1.0  # shorter bits of map lane outside the road pieces are left out
MIN_STEP = 1.0  # centre line points closer than this are left out before the lanes are offset
SPACING = 12.0  # longest node gap on straight roads (AutoDrive's recording)


@dataclass(frozen=True)
class RoadOptions:
    gap: float = LANE_GAP  # between the two lanes of a two-way road
    two_way: bool = False  # one two-way lane instead of two one-way lanes
    spacing: float = SPACING


@dataclass
class RoadNetwork:
    piece: PlannedPiece  # points as map positions (x, y, z)
    listed: list[tuple[Point3, str]] = field(default_factory=list)  # places to look at


Ends = tuple[Point3 | None, Point3 | None]  # where a lane's start and end belong


@dataclass
class _Lane:
    points: list[Point3]  # in driving order (for a two-way lane: along the road piece)
    fixed: bool  # the map's own points: other lanes snap to its ends, never the other way
    two_way: bool = False
    # Where the ends of a generated lane belong if they are close: the ends of its map lane
    # driven along its points, and for a two-way lane of the one driven back.
    along: Ends | None = None
    back: Ends | None = None


def build_road_network(graph: RoadGraph, options: RoadOptions | None = None) -> RoadNetwork:
    options = options or RoadOptions()
    network = RoadNetwork(PlannedPiece())
    pieces = road_pieces(graph)
    inner = set().union(*(j.inner for j in graph.junctions))
    rests = _uncovered(graph, pieces, inner)
    lanes = [_Lane(list(graph.stretches[i].points), fixed=True) for i in sorted(inner)]
    lanes += [_Lane(list(part), fixed=True) for parts in rests.values() for _, _, part in parts]
    for piece in pieces:
        lanes += _piece_lanes(piece, graph, rests, options, network.listed)
    joins = _snap_ends(lanes)
    _add_lanes(network.piece, lanes, joins, options.spacing)
    return network


Rests = dict[int, list[tuple[float, float, tuple[Point3, ...]]]]  # stretch -> (from, to, points)


def _uncovered(graph: RoadGraph, pieces: list[RoadPiece], inner: set[int]) -> Rests:
    """The parts of the map lanes outside junctions that no road piece follows: road_pieces
    leaves out bits near a junction, e.g. where a road stops being two-way shortly before it.
    Positions along the lane as in _position."""
    covered = defaultdict(list)
    for piece in pieces:
        for s in (piece.forward, piece.backward):
            if s is not None:
                points = graph.stretches[s].points
                ends = (_position(points, piece.points[0]), _position(points, piece.points[-1]))
                covered[s].append((min(ends), max(ends)))
    rests = defaultdict(list)
    for s, stretch in enumerate(graph.stretches):
        if s in inner:
            continue
        points, reached = stretch.points, 0.0
        for a, b in [*sorted(covered[s]), (len(points) - 1.0, len(points) - 1.0)]:
            if a > reached:
                part = _between(points, reached, a)
                if length(part) >= MIN_REST:
                    rests[s].append((reached, a, part))
            reached = max(reached, b)
    return rests


def _piece_lanes(
    piece: RoadPiece, graph: RoadGraph, rests: Rests, options: RoadOptions, listed
) -> list[_Lane]:
    points = list(piece.points)
    if not piece.two_way:
        return [_Lane(points, fixed=True)]

    def target(s: int, point: Point3, after: bool, junction: int | None) -> Point3 | None:
        """Where a lane end beside the point belongs: the map lane's part left out next to it,
        else at a junction the map lane's end there; None at a road end."""
        lane = graph.stretches[s].points
        position = _position(lane, point)
        for a, b, part in rests.get(s, ()):
            if abs((a if after else b) - position) < 1e-9:
                return part[0 if after else -1]
        return None if junction is None else lane[-1 if after else 0]

    along = (
        target(piece.forward, points[0], False, piece.start),
        target(piece.forward, points[-1], True, piece.end),
    )
    back = (
        target(piece.backward, points[-1], False, piece.end),
        target(piece.backward, points[0], True, piece.start),
    )
    if not options.two_way:
        side = _side(points, graph.stretches[piece.forward].points)
        try:
            return [
                _Lane(_offset(points, side * options.gap / 2), False, along=along),
                _Lane(_offset(points, -side * options.gap / 2)[::-1], False, along=back),
            ]
        except ParallelLaneError:
            listed.append((points[len(points) // 2], tr("Curve too tight for two lanes")))
    return [_Lane(points, False, two_way=True, along=along, back=back)]


def _position(points, point: Point3) -> float:
    """Where the point lies along the lane: segment index plus the share along it."""
    best = None
    for j, (a, b) in enumerate(pairwise(points)):
        t = min(1.0, max(0.0, _along(a, b, point[0], point[2])))
        q = lerp(a, b, t)
        d = flat_distance(q, point) + (0 if abs(q[1] - point[1]) <= SAME_LEVEL else math.inf)
        if best is None or d < best[0]:
            best = (d, j + t)
    return best[1]


def _side(centre: list[Point3], lane: tuple[Point3, ...]) -> float:
    """+1 if the lane runs on the right of the centre line, -1 if on its left."""
    middle = centre[len(centre) // 2]
    near = min(lane, key=lambda p: flat_distance(p, middle))
    a, b = centre[max(0, len(centre) // 2 - 1)], centre[min(len(centre) - 1, len(centre) // 2 + 1)]
    cross = (b[0] - a[0]) * (near[2] - a[2]) - (b[2] - a[2]) * (near[0] - a[0])
    return 1.0 if cross >= 0 else -1.0


def _offset(points: list[Point3], distance: float) -> list[Point3]:
    # Points closer than MIN_STEP make the offset turn back on noise in the centre line.
    kept = [points[0]]
    for p in points[1:]:
        if flat_distance(p, kept[-1]) >= MIN_STEP:
            kept.append(p)
    kept[-1] = points[-1]
    points = kept if len(kept) >= 2 else [points[0], points[-1]]
    flat = offset_polyline([(p[0], p[2]) for p in points], distance)
    return [(x, p[1], z) for (x, z), p in zip(flat, points, strict=True)]


def _heading(a: Point3, b: Point3) -> float:
    return math.atan2(b[2] - a[2], b[0] - a[0])


def _end_heading(points: list[Point3], at_end: bool) -> float:
    return _heading(points[-2], points[-1]) if at_end else _heading(points[0], points[1])


def _snap_ends(lanes: list[_Lane]) -> list[tuple[int, bool, Point3, bool]]:
    """Joins the ends of generated lanes to the lanes next to them. An end close to the end of
    its own map lane moves there (where the map's turn lanes start or end); any other end moves
    onto the nearest lane end it can drive on to (a lane's end onto a start, its start onto an
    end, heading within SNAP_ANGLE): first the map's lanes, then other generated ones (where the
    road changes). A two-way lane can't be in two places: its ends get joins instead (lane, at
    its end, map point, driven from the lane to the point)."""

    fixed_ends = Grid(SNAP_REACH)
    for i, lane in enumerate(lanes):
        if lane.fixed:
            fixed_ends.add(lane.points[0][0], lane.points[0][2], (i, False))
            fixed_ends.add(lane.points[-1][0], lane.points[-1][2], (i, True))

    def close(p: Point3, q: Point3 | None) -> bool:
        return (
            q is not None and flat_distance(p, q) <= SNAP_REACH and abs(p[1] - q[1]) <= SAME_LEVEL
        )

    def best(point, heading, wanted_end, exclude, grid, lanes_ok):
        found = []
        for k, at_end in grid.near(point[0], point[2]):
            other = lanes[k]
            if k == exclude or at_end != wanted_end or not lanes_ok(other):
                continue
            q = other.points[-1 if at_end else 0]
            turn = abs(math.remainder(_end_heading(other.points, at_end) - heading, math.tau))
            if close(point, q) and turn <= math.radians(SNAP_ANGLE):
                found.append((flat_distance(point, q), k, at_end))
        return min(found) if found else None

    joins = []
    loose = Grid(SNAP_REACH)  # generated lane ends not joined to the map
    loose_ends = []
    for i, lane in enumerate(lanes):
        if lane.fixed:
            continue
        for at_end in (False, True):
            index = -1 if at_end else 0
            point = lane.points[index]
            if lane.two_way:
                # At its end the lane is driven on into its map lane's end and comes from the
                # start of the one driven back; at its start the other way round. Without those
                # close by, the nearest map lanes that fit.
                leaving = _end_heading(lane.points, at_end) + (0 if at_end else math.pi)
                out_to, in_from = (
                    (lane.along[1], lane.back[0]) if at_end else (lane.back[1], lane.along[0])
                )
                if not close(point, out_to):
                    hit = best(point, leaving, False, i, fixed_ends, lambda _: True)
                    out_to = hit and lanes[hit[1]].points[0]
                if not close(point, in_from):
                    hit = best(point, leaving + math.pi, True, i, fixed_ends, lambda _: True)
                    in_from = hit and lanes[hit[1]].points[-1]
                found = [(q, out) for q, out in ((out_to, True), (in_from, False)) if q]
                joins += [(i, at_end, q, out) for q, out in found]
                if found:
                    continue
            elif close(point, lane.along[1 if at_end else 0]):
                lane.points[index] = lane.along[1 if at_end else 0]
                continue
            else:
                hit = best(
                    point,
                    _end_heading(lane.points, at_end),
                    not at_end,
                    i,
                    fixed_ends,
                    lambda _: True,
                )
                if hit:
                    lane.points[index] = lanes[hit[1]].points[-1 if hit[2] else 0]
                    continue
            loose.add(point[0], point[2], (i, at_end))
            loose_ends.append((i, at_end))

    # Generated lanes that meet each other where the road changes (no map lane between them).
    for i, at_end in loose_ends:
        lane = lanes[i]
        if not (at_end or lane.two_way):
            continue
        point = lane.points[-1 if at_end else 0]
        arriving = _end_heading(lane.points, at_end) + (0 if at_end else math.pi)
        hit = best(point, arriving, False, i, loose, lambda o, t=lane.two_way: o.two_way == t)
        if lane.two_way and hit is None:
            hit = best(point, arriving + math.pi, True, i, loose, lambda o: o.two_way)
        if hit:
            lane.points[-1 if at_end else 0] = lanes[hit[1]].points[-1 if hit[2] else 0]
    return joins


def _add_lanes(piece: PlannedPiece, lanes: list[_Lane], joins, spacing: float) -> None:
    nodes = Grid(NODE_SNAP)

    def node(point: Point3) -> int:
        for index in nodes.near(point[0], point[2]):
            q = piece.points[index]
            if flat_distance(point, q) <= NODE_SNAP and abs(point[1] - q[1]) <= SAME_LEVEL:
                return index
        index = piece.add(*point)
        nodes.add(point[0], point[2], index)
        return index

    ends = {}
    for i, lane in enumerate(lanes):
        spaced = _with_heights(
            road_points([(p[0], p[2]) for p in lane.points], spacing), lane, spacing
        )
        indices = [node(spaced[0]), *(piece.add(*p) for p in spaced[1:-1]), node(spaced[-1])]
        kind = ConnectionType.DUAL if lane.two_way else ConnectionType.REGULAR
        piece.chain(indices, kind)
        ends[i, False], ends[i, True] = indices[0], indices[-1]

    for i, at_end, point, out in joins:
        a, b = ends[i, at_end], node(point)
        piece.connect(*((a, b) if out else (b, a)))


def _with_heights(flat: list[tuple[float, float]], lane: _Lane, spacing: float) -> list[Point3]:
    """The node positions with the height of the lane under them. The nodes run along the lane,
    so each one is looked for on the lane segments up to a few node gaps after the last one."""
    points, k, result = lane.points, 0, []
    walked = [0.0]
    for a, b in pairwise(points):
        walked.append(walked[-1] + flat_distance(a, b))
    for x, z in flat:
        best = None
        for j in range(k, len(points) - 1):
            if j > k and walked[j] - walked[k] > 3 * spacing:
                break
            a, b = points[j], points[j + 1]
            t = min(1.0, max(0.0, _along(a, b, x, z)))
            d = math.hypot(a[0] + t * (b[0] - a[0]) - x, a[2] + t * (b[2] - a[2]) - z)
            if best is None or d < best[0]:
                best = (d, j, a[1] + t * (b[1] - a[1]))
        k = best[1]
        result.append((x, best[2], z))
    return result


def _along(a: Point3, b: Point3, x: float, z: float) -> float:
    dx, dz = b[0] - a[0], b[2] - a[2]
    squared = dx * dx + dz * dz
    return ((x - a[0]) * dx + (z - a[2]) * dz) / squared if squared else 1.0
