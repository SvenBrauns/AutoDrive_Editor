"""The road layout of a map from its traffic lanes (file_io.traffic_splines): the lanes joined
into stretches, the junctions between them and the moves the traffic may make through each one.

Points are world positions (x, height, z); distances on the map use x and z.
"""

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations, pairwise

from autodrive_editor.file_io.traffic_splines import TrafficLane

Point3 = tuple[float, float, float]

JOIN_DISTANCE = 0.3  # from a lane's end to the start of the lane it goes on into
JUNCTION_RADIUS = 30.0  # forks, merges and crossings this close form one junction
SAME_LEVEL = 3.0  # lanes further apart in height pass over each other (bridges)
MAX_INNER_LENGTH = 150.0  # longer stretches from a junction back to it are roads
JUNCTION_SPAN = 120.0  # turn lanes join forks and merges into one junction up to this size
OPPOSITE_ANGLE = 165.0  # headings at least this far apart (degrees) are opposite lanes
PAIR_DISTANCE = 12.0  # opposite lanes at most this far apart are one road
SAMPLE_SPACING = 5.0  # along a lane, where the opposite lane is looked for


@dataclass(frozen=True)
class Stretch:
    """Lanes joined end to start, from a junction or road end to the next, in driving order."""

    points: tuple[Point3, ...]
    start: int | None  # junction at the start, None at a road end
    end: int | None


@dataclass(frozen=True)
class Junction:
    points: tuple[Point3, ...]  # the forks, merges and crossings it is made of
    inner: frozenset[int]  # stretches inside it: turn lanes, the ring of a roundabout
    moves: frozenset[tuple[int, int]]  # (stretch in, stretch out) the traffic may take
    crossing: bool  # found only where lanes cross: the traffic data has no turns here
    roundabout: bool

    @property
    def centre(self) -> Point3:
        n = len(self.points)
        return tuple(sum(p[k] for p in self.points) / n for k in range(3))


@dataclass(frozen=True)
class RoadGraph:
    stretches: tuple[Stretch, ...]
    junctions: tuple[Junction, ...]

    @property
    def has_crossings(self) -> bool:
        """Some junctions were found only where lanes cross (maps whose lanes run in loops)."""
        return any(j.crossing for j in self.junctions)


class Grid:
    """Items by position on the map; near() finds all items within `size` of a point."""

    def __init__(self, size: float):
        self.size = size
        self.cells = defaultdict(list)

    def _cell(self, x: float, z: float) -> tuple[int, int]:
        return math.floor(x / self.size), math.floor(z / self.size)

    def add(self, x: float, z: float, item) -> None:
        self.cells[self._cell(x, z)].append(item)

    def add_segment(self, a: Point3, b: Point3, item) -> None:
        """Adds the item to every cell the bounding box of segment a-b touches."""
        x0, z0 = self._cell(min(a[0], b[0]), min(a[2], b[2]))
        x1, z1 = self._cell(max(a[0], b[0]), max(a[2], b[2]))
        for i in range(x0, x1 + 1):
            for k in range(z0, z1 + 1):
                self.cells[i, k].append(item)

    def near(self, x: float, z: float):
        """Items in the cell of (x, z) and the eight around it; segments may come more than once."""
        cx, cz = self._cell(x, z)
        for i in (cx - 1, cx, cx + 1):
            for k in (cz - 1, cz, cz + 1):
                yield from self.cells.get((i, k), ())

    def box(self, x0: float, z0: float, x1: float, z1: float):
        """Items in the cells the rectangle touches."""
        cx0, cz0 = self._cell(x0, z0)
        cx1, cz1 = self._cell(x1, z1)
        for i in range(cx0, cx1 + 1):
            for k in range(cz0, cz1 + 1):
                yield from self.cells.get((i, k), ())


def flat_distance(a: Point3, b: Point3) -> float:
    return math.hypot(a[0] - b[0], a[2] - b[2])


def lerp(a: Point3, b: Point3, t: float) -> Point3:
    return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))


def length(points) -> float:
    return sum(flat_distance(a, b) for a, b in pairwise(points))


@dataclass(frozen=True)
class Partner:
    line: int
    point: Point3  # the nearest point on it
    heading: tuple[float, float]  # its heading there


class OppositeLanes:
    """Finds the nearest of the given lines that runs the other way beside a point."""

    def __init__(self, lines: dict[int, Sequence[Point3]]):
        self.lines = lines
        self.segments = Grid(PAIR_DISTANCE)
        for i, points in lines.items():
            for k, (a, b) in enumerate(pairwise(points)):
                if flat_distance(a, b) > 0:
                    self.segments.add_segment(a, b, (i, k))
        self.limit = math.cos(math.radians(OPPOSITE_ANGLE))

    def find(self, p: Point3, heading: tuple[float, float], exclude: int) -> Partner | None:
        best, best_distance = None, PAIR_DISTANCE
        for i, k in set(self.segments.near(p[0], p[2])):
            if i == exclude:
                continue
            a, b = self.lines[i][k], self.lines[i][k + 1]
            h = direction(a, b)
            if h[0] * heading[0] + h[1] * heading[1] > self.limit:
                continue
            q = lerp(a, b, _projection(p, a, b))
            d = flat_distance(p, q)
            if d <= best_distance and abs(q[1] - p[1]) <= SAME_LEVEL:
                best, best_distance = Partner(i, q, h), d
        return best


def direction(a: Point3, b: Point3) -> tuple[float, float]:
    d = flat_distance(a, b)
    return (b[0] - a[0]) / d, (b[2] - a[2]) / d


def _projection(p: Point3, a: Point3, b: Point3) -> float:
    """Where p lies along a-b on the map, from 0 at a to 1 at b."""
    dx, dz = b[0] - a[0], b[2] - a[2]
    t = ((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / (dx * dx + dz * dz)
    return min(1.0, max(0.0, t))


def samples(points) -> list[tuple[Point3, tuple[float, float]]]:
    """Points along the line at most SAMPLE_SPACING apart, the line's own included, each with the
    heading of its segment."""
    found = []
    for a, b in pairwise(points):
        d = flat_distance(a, b)
        if d == 0:
            continue
        heading = direction(a, b)
        count = math.ceil(d / SAMPLE_SPACING)
        found.extend((lerp(a, b, i / count), heading) for i in range(count))
    if found:
        found.append((points[-1], found[-1][1]))
    return found


def build_road_graph(lanes: Iterable[TrafficLane]) -> RoadGraph:
    lanes = [lane.points for lane in lanes if len(lane.points) >= 2]
    succ, pred = _joins(lanes)
    chains = _chains(succ, pred)
    first_of = {chain[0]: c for c, chain in enumerate(chains)}
    points, closed, chain_succ = [], [], []
    for chain in chains:
        pts = list(lanes[chain[0]])
        for lane in chain[1:]:
            pts.extend(lanes[lane][1:])
        is_closed = succ[chain[-1]] == [chain[0]] and len(pred[chain[0]]) == 1
        points.append(pts)
        closed.append(is_closed)
        chain_succ.append([] if is_closed else [first_of[j] for j in succ[chain[-1]]])

    # Forks and merges: every chain end that goes on and every chain start that is reached.
    marks = []  # (point, chain, at its end)
    for c, chain in enumerate(chains):
        if not closed[c]:
            if chain_succ[c]:
                marks.append((points[c][-1], c, True))
            if pred[chain[0]]:
                marks.append((points[c][0], c, False))
    clusters = _clusters([m[0] for m in marks])
    starts, ends = [None] * len(chains), [None] * len(chains)
    for (_, c, at_end), j in zip(marks, clusters, strict=True):
        (ends if at_end else starts)[c] = j
    clusters, starts, ends = _join_parts(
        [m[0] for m in marks], clusters, starts, ends, points, chain_succ
    )
    count = max(clusters, default=-1) + 1

    # Crossings of lanes that are not joined, away from the forks and merges.
    near_marks = Grid(JUNCTION_RADIUS)
    for point, _, _ in marks:
        near_marks.add(point[0], point[2], point)

    def inside(c):  # the chain is a lane inside a junction
        return (
            starts[c] is not None and starts[c] == ends[c] and length(points[c]) <= MAX_INNER_LENGTH
        )

    crossings = [
        x
        for x in _crossings(points, closed)
        if not any(_close(x[0], p) for p in near_marks.near(x[0][0], x[0][2]))
        and not all(inside(c) for c, _ in x[1])
    ]
    crossing_clusters = [count + j for j in _clusters([x[0] for x in crossings])]
    junction_points = defaultdict(list)
    for (point, _, _), j in zip(marks, clusters, strict=True):
        junction_points[j].append(point)
    cuts = defaultdict(list)  # chain -> (position along it, junction)
    for (point, cuts_here), j in zip(crossings, crossing_clusters, strict=True):
        junction_points[j].append(point)
        for c, position in cuts_here:
            cuts[c].append((position, j))

    # Stretches: the chains cut at the crossings.
    stretches, successors = [], []
    first_piece, last_piece = [], []
    for c in range(len(chains)):
        pieces = _cut(points[c], closed[c], sorted(cuts[c]), starts[c], ends[c])
        first_piece.append(len(stretches))
        for i in range(len(pieces)):
            successors.append(
                [len(stretches) + (i + 1) % len(pieces)] if closed[c] or i < len(pieces) - 1 else []
            )
        stretches.extend(pieces)
        last_piece.append(len(stretches) - 1)
    for c in range(len(chains)):
        successors[last_piece[c]].extend(first_piece[s] for s in chain_succ[c])

    inner = defaultdict(set)
    for i, s in enumerate(stretches):
        if s.start is not None and s.start == s.end and length(s.points) <= MAX_INNER_LENGTH:
            inner[s.start].add(i)
    moves = defaultdict(set)
    for i, s in enumerate(stretches):
        if s.end is not None and i not in inner[s.end]:
            moves[s.end].update((i, t) for t in _reached(i, successors, inner[s.end]))
    junctions = tuple(
        Junction(
            points=tuple(junction_points[j]),
            inner=frozenset(inner[j]),
            moves=frozenset(moves[j]),
            crossing=j >= count,
            roundabout=_has_cycle(inner[j], successors),
        )
        for j in range(count + len(set(crossing_clusters)))
    )
    return RoadGraph(tuple(stretches), junctions)


def _joins(lanes) -> tuple[list[list[int]], list[list[int]]]:
    """Per lane, the lanes it goes on into and the lanes that lead into it."""
    starts = Grid(1.0)
    for i, pts in enumerate(lanes):
        starts.add(pts[0][0], pts[0][2], i)
    succ, pred = [[] for _ in lanes], [[] for _ in lanes]
    for i, pts in enumerate(lanes):
        for j in starts.near(pts[-1][0], pts[-1][2]):
            if math.dist(pts[-1], lanes[j][0]) <= JOIN_DISTANCE:
                succ[i].append(j)
                pred[j].append(i)
    return succ, pred


def _chains(succ, pred) -> list[list[int]]:
    """Lanes joined while each goes on into exactly one lane that only it leads into."""

    def continues(i):
        return len(succ[i]) == 1 and len(pred[succ[i][0]]) == 1

    seen = set()

    def follow(i):
        chain = [i]
        seen.add(i)
        while continues(chain[-1]) and succ[chain[-1]][0] not in seen:
            chain.append(succ[chain[-1]][0])
            seen.add(chain[-1])
        return chain

    chains = [
        follow(i) for i in range(len(succ)) if not (len(pred[i]) == 1 and continues(pred[i][0]))
    ]
    chains.extend(follow(i) for i in range(len(succ)) if i not in seen)  # closed loops
    return chains


def _close(a: Point3, b: Point3) -> bool:
    return flat_distance(a, b) <= JUNCTION_RADIUS and abs(a[1] - b[1]) <= SAME_LEVEL


def _clusters(points: list[Point3]) -> list[int]:
    """A cluster number per point; points within reach of each other share one."""
    parent = list(range(len(points)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    grid = Grid(JUNCTION_RADIUS)
    for i, p in enumerate(points):
        for k in grid.near(p[0], p[2]):
            if _close(p, points[k]):
                parent[root(i)] = root(k)
        grid.add(p[0], p[2], i)
    numbers = {}
    return [numbers.setdefault(root(i), len(numbers)) for i in range(len(points))]


def _join_parts(cluster_points, clusters, starts, ends, points, chain_succ):
    """Joins clusters of forks and merges that are parts of one junction: clusters linked by a turn
    lane, a short lane straight off a long one or straight into one, as where turn lanes fork off
    well before a side road. A short road between two junctions only links turn lanes. Returns the
    new clusters, starts, ends."""
    long = [length(p) > MAX_INNER_LENGTH for p in points]
    chain_pred = defaultdict(list)
    for c, following in enumerate(chain_succ):
        for d in following:
            chain_pred[d].append(c)

    links = sorted(
        (length(points[c]), starts[c], ends[c])
        for c in range(len(points))
        if starts[c] is not None
        and ends[c] is not None
        and starts[c] != ends[c]
        and not long[c]
        and any(long[d] for d in chain_pred[c] + chain_succ[c])
    )
    joined = _join_clusters(cluster_points, clusters, links)
    clusters = [joined[j] for j in clusters]
    starts = [None if j is None else joined[j] for j in starts]
    ends = [None if j is None else joined[j] for j in ends]
    return clusters, starts, ends


def _join_clusters(points: list[Point3], clusters: list[int], links) -> dict[int, int]:
    """New cluster numbers, where linked clusters become one while it stays within JUNCTION_SPAN.
    Links: (length, cluster, cluster), shortest first."""
    groups = defaultdict(list)
    for p, j in zip(points, clusters, strict=True):
        groups[j].append(p)
    parent = {j: j for j in groups}

    def root(j):
        while parent[j] != j:
            j = parent[j]
        return j

    for _, f, g in links:
        a, b = root(f), root(g)
        if a != b and all(
            flat_distance(p, q) <= JUNCTION_SPAN for p in groups[a] for q in groups[b]
        ):
            parent[b] = a
            groups[a].extend(groups.pop(b))
    numbers = {}
    return {j: numbers.setdefault(root(j), len(numbers)) for j in sorted(parent)}


def _crossings(points, closed):
    """Where chains cross at the same level: (point, ((chain, position along it), ...))."""
    grid = Grid(JUNCTION_RADIUS)
    for c, pts in enumerate(points):
        for k, (a, b) in enumerate(pairwise(pts)):
            grid.add_segment(a, b, (c, k))
    found = {}
    for cell in grid.cells.values():
        for (c1, k1), (c2, k2) in combinations(cell, 2):
            key = ((c1, k1), (c2, k2)) if (c1, k1) < (c2, k2) else ((c2, k2), (c1, k1))
            if key in found or _neighbours(c1, k1, c2, k2, points, closed):
                continue
            a, b, p, q = points[c1][k1], points[c1][k1 + 1], points[c2][k2], points[c2][k2 + 1]
            hit = _intersection(a, b, p, q)
            found[key] = None
            if hit is not None:
                t, u = hit
                x, y = lerp(a, b, t), lerp(p, q, u)
                if abs(x[1] - y[1]) <= SAME_LEVEL:
                    found[key] = (lerp(x, y, 0.5), ((c1, k1 + t), (c2, k2 + u)))
    return [x for x in found.values() if x is not None]


def _neighbours(c1, k1, c2, k2, points, closed) -> bool:
    """Two segments of one chain that share a point."""
    if c1 != c2:
        return False
    last = len(points[c1]) - 2
    return abs(k1 - k2) <= 1 or (closed[c1] and {k1, k2} == {0, last})


def _intersection(a, b, p, q) -> tuple[float, float] | None:
    """Positions t on a-b and u on p-q where the two segments cross on the map, each in [0, 1)."""
    rx, rz = b[0] - a[0], b[2] - a[2]
    sx, sz = q[0] - p[0], q[2] - p[2]
    denominator = rx * sz - rz * sx
    if abs(denominator) < 1e-9:
        return None
    dx, dz = p[0] - a[0], p[2] - a[2]
    t = (dx * sz - dz * sx) / denominator
    u = (dx * rz - dz * rx) / denominator
    return (t, u) if 0 <= t < 1 and 0 <= u < 1 else None


def _cut(points, closed, cuts, start, end) -> list[Stretch]:
    """The chain's stretches between its cuts (position along the chain, junction)."""
    if not cuts:
        return [Stretch(tuple(points), start, end)]
    if closed:
        span = len(points) - 1
        points = points + points[1:]
        bounds = cuts + [(cuts[0][0] + span, cuts[0][1])]
    else:
        bounds = [(0.0, start), *cuts, (len(points) - 1.0, end)]
    return [Stretch(_between(points, a, b), ja, jb) for (a, ja), (b, jb) in pairwise(bounds)]


def _between(points, a: float, b: float) -> tuple[Point3, ...]:
    """The chain from position a to position b (segment index plus the share along it)."""

    def at(position):
        k = min(int(position), len(points) - 2)
        return lerp(points[k], points[k + 1], position - k)

    return (at(a), *points[math.floor(a) + 1 : math.ceil(b)], at(b))


def _reached(start: int, successors, inner: set[int]) -> set[int]:
    """The stretches past the junction that traffic from `start` reaches through its inner ones."""
    reached, seen, stack = set(), set(), list(successors[start])
    while stack:
        s = stack.pop()
        if s in seen:
            continue
        seen.add(s)
        if s in inner:
            stack.extend(successors[s])
        else:
            reached.add(s)
    return reached


def _has_cycle(inner: set[int], successors) -> bool:
    state = {}

    def visit(s):
        state[s] = 1
        for t in successors[s]:
            if t in inner and (state.get(t) == 1 or (t not in state and visit(t))):
                return True
        state[s] = 2
        return False

    return any(s not in state and visit(s) for s in inner)
