"""The road network generator: the roads of a road graph (road_centre) built as AutoDrive lanes in
the network's style.

Pair style: a two-way road becomes two one-way lanes `gap` apart, each on the side where the map
drives it; two-way style: one two-way lane on the centre line. One-way roads, the lanes inside
junctions (turn lanes, roundabout rings) and the bits of map lane that no road piece follows are
the map's own lanes. Generated lane ends snap to the
map lane ends next to them, so every move the map allows stays possible. Nodes are spaced as
AutoDrive records a drive; heights come from the map's lanes.

Junctions close together form one (junction_groups). Where three or four two-way roads meet, the
roads end at a box in the NF Marsch style (see junction_box.py) in the pair style, or at one
shared node in the two-way style; every other junction keeps the map's lanes and is listed.

Points are world positions (x, height, z).
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field, replace
from itertools import combinations, pairwise

from autodrive_editor.editing.dubins import shortest_path
from autodrive_editor.editing.junction import (
    LANE_GAP,
    MIN_RADIUS,
    RADIUS_STEP,
    SAMPLE,
    _turns_little,
)
from autodrive_editor.editing.junction_box import BOX_MARGIN
from autodrive_editor.editing.parallel_lane import ParallelLaneError, offset_polyline
from autodrive_editor.editing.planned_piece import PlannedPiece
from autodrive_editor.editing.road_centre import RoadPiece, road_pieces
from autodrive_editor.editing.road_graph import (
    JUNCTION_SPAN,
    PAIR_DISTANCE,
    SAME_LEVEL,
    Grid,
    Point3,
    RoadGraph,
    _between,
    _intersection,
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
MERGE_ONE_WAY = 60.0  # junctions linked by a one-way piece this short are one ...
MERGE_ANY = 30.0  # ... and by any piece this short
SPAWN_LENGTH = 20.0  # shorter pieces from a junction to a road end are left out (spawn lanes)
MIN_ARM_ANGLE = 30.0  # roads into a box are at least this far apart (degrees)
ARM_HEADING = 20.0  # a road's direction at a junction: over this much of it (metres)
MIN_ARM = 5.0  # a road keeps at least this much outside the box (metres)
LONG = 200.0  # half length of the lines through a box centre the crossings are found on


@dataclass(frozen=True)
class RoadOptions:
    gap: float = LANE_GAP  # between the two lanes of a two-way road
    two_way: bool = False  # one two-way lane instead of two one-way lanes
    spacing: float = SPACING


@dataclass
class RoadNetwork:
    piece: PlannedPiece  # points as map positions (x, y, z)
    listed: list[tuple[Point3, str]] = field(default_factory=list)  # places to look at
    areas: list[list[tuple[float, float]]] = field(default_factory=list)  # outline (x, z) per group
    groups: list[frozenset[int]] = field(default_factory=list)  # junctions built as one


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
    placed: tuple[bool, bool] = (False, False)  # start, end already where they belong (boxes)


@dataclass
class JunctionGroups:
    """Junctions that become one junction, and the road pieces left out."""

    groups: list[frozenset[int]]
    links: set[int]  # short pieces between junctions of one group
    spawns: set[int]  # short pieces from a junction to a road end (spawn lanes)


def junction_groups(graph: RoadGraph, pieces: list[RoadPiece]) -> JunctionGroups:
    """Junctions linked by a one-way piece up to MERGE_ONE_WAY or any piece under MERGE_ANY are
    one (the map's turn lanes split some junctions into a main-road and a side-road part)."""
    parent = list(range(len(graph.junctions)))

    def root(j: int) -> int:
        while parent[j] != j:
            j = parent[j]
        return j

    links = set()
    for i, piece in enumerate(pieces):
        if piece.start is None or piece.end is None or piece.start == piece.end:
            continue
        size = length(piece.points)
        if size < MERGE_ANY or (not piece.two_way and size <= MERGE_ONE_WAY):
            links.add(i)
            parent[root(piece.start)] = root(piece.end)
    members = defaultdict(set)
    for j in range(len(graph.junctions)):
        members[root(j)].add(j)

    def free(piece: RoadPiece, at_end: bool) -> bool:
        stretch, k = graph.stretches[piece.forward], -1 if at_end else 0
        road_end = (stretch.end if at_end else stretch.start) is None
        return road_end and flat_distance(piece.points[k], stretch.points[k]) <= PAIR_DISTANCE

    spawns = {
        i
        for i, p in enumerate(pieces)
        if length(p.points) < SPAWN_LENGTH
        and ((p.start is not None and free(p, True)) or (p.end is not None and free(p, False)))
    }
    return JunctionGroups([frozenset(m) for m in members.values()], links, spawns)


def build_road_network(graph: RoadGraph, options: RoadOptions | None = None) -> RoadNetwork:
    options = options or RoadOptions()
    network = RoadNetwork(PlannedPiece())
    pieces = road_pieces(graph)
    grouped = junction_groups(graph, pieces)
    network.groups = grouped.groups
    dropped = grouped.links | grouped.spawns
    boxes, kept_inner, area_of = [], set(), {}
    for group in grouped.groups:
        box = _plan_box(group, graph, pieces, dropped, options)
        if box is not None:
            boxes.append(box)
            continue
        group_inner = set().union(*(graph.junctions[j].inner for j in group))
        kept_inner |= group_inner
        area_of[group] = _outline(
            [p for j in group for p in graph.junctions[j].points]
            + [p for s in group_inner for p in graph.stretches[s].points]
        )
        network.listed.append((_middle(graph, group), tr("No junction box")))
    boxed = set().union(*(box.group for box in boxes))
    inner = set().union(*(j.inner for j in graph.junctions))
    spawn_stretches = {s for i in grouped.spawns for s in (pieces[i].forward, pieces[i].backward)}
    kept = [p for i, p in enumerate(pieces) if i not in dropped]
    rests = _uncovered(graph, kept, inner | spawn_stretches)
    for s, parts in rests.items():  # bits of map lane into a box are left out
        stretch, last = graph.stretches[s], len(graph.stretches[s].points) - 1
        parts[:] = [
            (a, b, part)
            for a, b, part in parts
            if not (a == 0 and stretch.start in boxed or b == last and stretch.end in boxed)
        ]

    lanes = [_Lane(list(graph.stretches[i].points), fixed=True) for i in sorted(kept_inner)]
    lanes += [_Lane(list(part), fixed=True) for parts in rests.values() for _, _, part in parts]
    cuts = {(arm.piece, arm.at_end): (box, arm) for box in boxes for arm in box.arms}
    piece_lanes = {}
    for i, piece in enumerate(pieces):
        if i in dropped:
            continue
        placed = ((i, False) in cuts, (i, True) in cuts)
        points = list(piece.points)
        for at_end in (False, True):
            if placed[at_end]:
                points = _cut(points, at_end, *cuts[i, at_end], options.two_way)
        piece = replace(piece, points=tuple(points))
        piece_lanes[i] = _piece_lanes(piece, graph, rests, options, network.listed, placed)
        lanes += piece_lanes[i]
    for box in boxes:
        if options.two_way:  # the arms meet at the centre: the outline of a box that size
            reach = options.gap / 2 + BOX_MARGIN
            corners = [_from_centre(box, arm.heading, reach) for arm in box.arms]
            area_of[box.group] = _outline([box.centre, *corners])
            continue
        box_lanes = _box_lanes(box, [_arm_ends(arm, piece_lanes[arm.piece]) for arm in box.arms])
        area_of[box.group] = _outline([p for lane in box_lanes for p in lane.points])
        lanes += box_lanes
    network.areas = [area_of[group] for group in network.groups]
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
    piece: RoadPiece,
    graph: RoadGraph,
    rests: Rests,
    options: RoadOptions,
    listed,
    placed: tuple[bool, bool] = (False, False),
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
            forward = _offset(points, side * options.gap / 2)
            backward = _offset(points, -side * options.gap / 2)[::-1]
            return [
                _Lane(forward, False, along=along, placed=placed),
                _Lane(backward, False, along=back, placed=placed[::-1]),
            ]
        except ParallelLaneError:
            listed.append((points[len(points) // 2], tr("Curve too tight for two lanes")))
    return [_Lane(points, False, two_way=True, along=along, back=back, placed=placed)]


def _middle(graph: RoadGraph, group) -> Point3:
    points = [p for j in group for p in graph.junctions[j].points]
    return tuple(sum(p[k] for p in points) / len(points) for k in range(3))


@dataclass
class _Arm:
    piece: int
    at_end: bool  # the piece's end lies at the junction, else its start
    heading: float = 0.0  # from the box centre out along the road
    reach: float = 0.0  # from the centre to the box edge along the heading (pair style)


@dataclass
class _Box:
    group: frozenset[int]
    centre: Point3
    arms: list[_Arm]
    roads: list[tuple[int, ...]]  # the arms of each road through the box: two, or one (a stem)
    lines: list[list[Point3]] = field(default_factory=list)  # two lanes per road, along it
    crossings: list[tuple[int, int, Point3]] = field(default_factory=list)  # line, line, point


def _plan_box(
    group: frozenset[int], graph: RoadGraph, pieces: list[RoadPiece], dropped, options
) -> _Box | None:
    """The box where 3 or 4 two-way roads at least MIN_ARM_ANGLE apart meet: the two most
    opposite roads run through it, a third one runs into it (stem), a fourth one through as well.
    None for any other junction."""
    if any(graph.junctions[j].crossing or graph.junctions[j].roundabout for j in group):
        return None
    arms = [
        _Arm(i, at_end)
        for i, p in enumerate(pieces)
        if i not in dropped
        for at_end in (False, True)
        if (p.end if at_end else p.start) in group
    ]
    if not 3 <= len(arms) <= 4 or not all(pieces[arm.piece].two_way for arm in arms):
        return None
    outward = [_outward(pieces[arm.piece].points, arm.at_end) for arm in arms]
    headings = [_heading(line[0], _point_at(line, ARM_HEADING)) for line in outward]
    centre = _meeting_point([line[0] for line in outward], headings)
    if centre is None or flat_distance(centre, _middle(graph, group)) > JUNCTION_SPAN:
        return None
    for arm, line in zip(arms, outward, strict=True):
        # The direction to the arm's end; the arm's own one if the end lies at the centre.
        far = line[0] if flat_distance(centre, line[0]) >= 1.0 else line[-1]
        arm.heading = _heading(centre, far)
    order = sorted(arm.heading % math.tau for arm in arms)
    turns = [(b - a) % math.tau for a, b in zip(order, order[1:] + order[:1], strict=True)]
    if min(turns) < math.radians(MIN_ARM_ANGLE):
        return None
    a, b = max(
        combinations(range(len(arms)), 2),
        key=lambda ab: abs(math.remainder(arms[ab[0]].heading - arms[ab[1]].heading, math.tau)),
    )
    box = _Box(group, centre, arms, [(a, b), tuple(k for k in range(len(arms)) if k not in (a, b))])
    if not options.two_way and not _place_crossings(box, options.gap):
        return None
    if any(
        flat_distance(centre, line[-1]) < arm.reach + MIN_ARM
        for arm, line in zip(arms, outward, strict=True)
    ):
        return None
    return box


def _outline(points) -> list[tuple[float, float]]:
    """The convex hull (x, z) of the points, counterclockwise."""
    flat = sorted({(p[0], p[2]) for p in points})
    if len(flat) < 3:
        return flat

    def half(ordered):
        hull = []
        for p in ordered:
            while len(hull) >= 2 and _cross(hull[-2], hull[-1], p) <= 0:
                hull.pop()
            hull.append(p)
        return hull[:-1]

    return half(flat) + half(flat[::-1])


def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _outward(points, at_end: bool) -> list[Point3]:
    """The piece's points from its end at the junction outward."""
    return list(points[::-1] if at_end else points)


def _point_at(points: list[Point3], distance: float) -> Point3:
    walked = 0.0
    for a, b in pairwise(points):
        step = flat_distance(a, b)
        if step > 0 and walked + step >= distance:
            return lerp(a, b, (distance - walked) / step)
        walked += step
    return points[-1]


def _meeting_point(points: list[Point3], headings: list[float]) -> Point3 | None:
    """The point closest to all lines through the points along the headings (least squares)."""
    a11 = a12 = a22 = b1 = b2 = 0.0
    for p, heading in zip(points, headings, strict=True):
        dx, dz = math.cos(heading), math.sin(heading)
        m11, m12, m22 = 1 - dx * dx, -dx * dz, 1 - dz * dz
        a11, a12, a22 = a11 + m11, a12 + m12, a22 + m22
        b1 += m11 * p[0] + m12 * p[2]
        b2 += m12 * p[0] + m22 * p[2]
    determinant = a11 * a22 - a12 * a12
    if abs(determinant) < 1e-3:
        return None
    x, z = (b1 * a22 - b2 * a12) / determinant, (a11 * b2 - a12 * b1) / determinant
    return x, sum(p[1] for p in points) / len(points), z


def _from_centre(box: _Box, heading: float, distance: float) -> Point3:
    c = box.centre
    return c[0] + distance * math.cos(heading), c[1], c[2] + distance * math.sin(heading)


def _place_crossings(box: _Box, gap: float) -> bool:
    """The box lanes: each road's centre line through the box centre (kinked there between the
    two arms of a through road, straight on across for a stem) with a lane gap/2 to each side;
    where the lanes of the two roads cross; each arm's box edge BOX_MARGIN past the crossings.
    False if the lanes don't cross four times."""
    for road in box.roads:
        first = box.arms[road[0]].heading
        last = box.arms[road[1]].heading if len(road) == 2 else first + math.pi
        line = [_from_centre(box, first, LONG), box.centre, _from_centre(box, last, LONG)]
        try:
            box.lines += [_offset(line, gap / 2), _offset(line, -gap / 2)]
        except ParallelLaneError:
            return False
    for p in (0, 1):
        for q in (2, 3):
            found = []
            for a, b in pairwise(box.lines[p]):
                for c, d in pairwise(box.lines[q]):
                    hit = _intersection(a, b, c, d)
                    if hit is not None:
                        point = lerp(a, b, hit[0])
                        found.append((flat_distance(point, box.centre), point))
            if not found:
                return False
            box.crossings.append((p, q, min(found)[1]))
    for arm in box.arms:
        dx, dz = math.cos(arm.heading), math.sin(arm.heading)
        arm.reach = BOX_MARGIN + max(
            (x[0] - box.centre[0]) * dx + (x[2] - box.centre[2]) * dz for _, _, x in box.crossings
        )
    return True


def _cut(points: list[Point3], at_end: bool, box: _Box, arm: _Arm, two_way: bool) -> list[Point3]:
    """The road's centre line cut back to the box edge (pair style) or run on to the box centre
    (two-way style), straight from its last point outside."""
    line = _outward(points, at_end)
    if two_way:
        target, keep_out = box.centre, 0.0
    else:
        edge = _from_centre(box, arm.heading, arm.reach)
        target, keep_out = (edge[0], line[0][1], edge[2]), arm.reach
    while len(line) > 1 and flat_distance(line[0], box.centre) < keep_out + MIN_STEP:
        line.pop(0)
    return _outward([target, *line], at_end)


def _arm_ends(arm: _Arm, lanes: list[_Lane]) -> tuple[Point3, Point3]:
    """Where the road's lane into the box ends and its lane out of it starts."""
    if len(lanes) == 1:
        end = lanes[0].points[-1 if arm.at_end else 0]
        return end, end
    into, out = lanes if arm.at_end else lanes[::-1]
    return into.points[-1], out.points[0]


def _box_lanes(box: _Box, ends: list[tuple[Point3, Point3]]) -> list[_Lane]:
    """The box from the arms' lane ends (in, out): lanes from edge to crossing two-way, between
    crossings one-way; a centre node with two-way lanes to the crossings (left turns, U-turns);
    the short turns between neighbouring arms of different roads as arcs."""
    lanes = []
    for r, road in enumerate(box.roads):
        first_in = ends[road[0]][0]
        nearer = min((2 * r, 2 * r + 1), key=lambda k: _distance_to(box.lines[k], first_in))
        for k in (2 * r, 2 * r + 1):
            stops = [x for p, q, x in box.crossings if k in (p, q)]
            stops.sort(key=lambda x, line=box.lines[k]: _position(line, x))
            # The lane nearer to the first arm's lane into the box is driven along the road.
            along = k == nearer
            chain = stops if along else stops[::-1]
            if along or len(road) == 2:
                chain = [ends[road[0] if along else road[-1]][0], *chain]
            if not along or len(road) == 2:
                chain = [*chain, ends[road[-1] if along else road[0]][1]]
            for a, b in pairwise(chain):
                between = a in stops and b in stops
                lanes.append(_Lane([a, b], fixed=True, two_way=not between))
    middle = tuple(sum(x[k] for _, _, x in box.crossings) / 4 for k in range(3))
    lanes += [_Lane([middle, x], fixed=True, two_way=True) for _, _, x in box.crossings]

    road_of = {k: r for r, road in enumerate(box.roads) for k in road}
    order = sorted(range(len(box.arms)), key=lambda k: box.arms[k].heading % math.tau)
    for k, m in zip(order, order[1:] + order[:1], strict=True):
        if road_of[k] == road_of[m]:
            continue
        # Of the two turns between the arms, the short one: lane ends on the side facing.
        a, b = min((k, m), (m, k), key=lambda ab: flat_distance(ends[ab[0]][0], ends[ab[1]][1]))
        arc = _corner(ends[a][0], box.arms[a].heading + math.pi, ends[b][1], box.arms[b].heading)
        if arc is not None:
            lanes.append(_Lane(arc, fixed=True))
    return lanes


def _distance_to(points: list[Point3], point: Point3) -> float:
    """Flat distance from the point to the line."""
    return min(
        flat_distance(point, lerp(a, b, min(1.0, max(0.0, _along(a, b, point[0], point[2])))))
        for a, b in pairwise(points)
    )


def _corner(start: Point3, start_heading: float, goal: Point3, goal_heading: float):
    """An arc from the lane end into the box to the lane start out of it, at BOX_MARGIN or
    tighter down to MIN_RADIUS; None if none fits."""
    radius = BOX_MARGIN
    while radius >= MIN_RADIUS - 1e-9:
        path = shortest_path(
            (start[0], start[2], start_heading), (goal[0], goal[2], goal_heading), radius
        )
        if path is not None and _turns_little(path, start_heading, goal_heading, radius):
            poses = path.sample(SAMPLE)
            count = len(poses) - 1
            points = [
                (x, start[1] + (goal[1] - start[1]) * n / count, z)
                for n, (x, z, _) in enumerate(poses)
            ]
            points[0], points[-1] = start, goal
            return points
        radius -= RADIUS_STEP
    return None


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
            if lane.placed[at_end]:
                continue
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
    so each one is looked for on the lane up to a few node gaps after the last one."""
    points, k, reached, result = lane.points, 0, 0.0, []
    walked = [0.0]
    for a, b in pairwise(points):
        walked.append(walked[-1] + flat_distance(a, b))
    for x, z in flat:
        best = None
        for j in range(k, len(points) - 1):
            if j > k and walked[j] - reached > 3 * spacing:
                break
            a, b = points[j], points[j + 1]
            t = min(1.0, max(0.0, _along(a, b, x, z)))
            d = math.hypot(a[0] + t * (b[0] - a[0]) - x, a[2] + t * (b[2] - a[2]) - z)
            if best is None or d < best[0]:
                best = (d, j, t, a[1] + t * (b[1] - a[1]))
        _, k, t, height = best
        reached = walked[k] + t * (walked[k + 1] - walked[k])
        result.append((x, height, z))
    return result


def _along(a: Point3, b: Point3, x: float, z: float) -> float:
    dx, dz = b[0] - a[0], b[2] - a[2]
    squared = dx * dx + dz * dz
    return ((x - a[0]) * dx + (z - a[2]) * dz) / squared if squared else 1.0
