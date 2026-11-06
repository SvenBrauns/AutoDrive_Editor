"""The roads of a road graph: stretches that run side by side in opposite directions are paired
into the centre line of a two-way road; the rest stay one-way lanes (one-way streets, slip roads).
"""

from dataclasses import dataclass
from itertools import groupby

from autodrive_editor.editing.roads.road_graph import (
    JUNCTION_RADIUS,
    SAME_LEVEL,
    Grid,
    OppositeLanes,
    Point3,
    RoadGraph,
    flat_distance,
    length,
    lerp,
    samples,
)

MUTUAL_DISTANCE = 2.0  # from a lane point to the point found back from its partner


@dataclass(frozen=True)
class RoadPiece:
    """A road between junctions or road ends. The points are the centre line of a two-way road or
    the lane of a one-way road, in the driving direction of `forward`."""

    points: tuple[Point3, ...]
    forward: int  # stretch driven along the points
    backward: int | None  # stretch driven the other way on a two-way road
    start: int | None  # junction at each end, None at a road end or where the road changes
    end: int | None

    @property
    def two_way(self) -> bool:
        return self.backward is not None


def road_pieces(graph: RoadGraph) -> list[RoadPiece]:
    inner = set().union(*(j.inner for j in graph.junctions))
    roads = [i for i in range(len(graph.stretches)) if i not in inner]
    beside = OppositeLanes({i: graph.stretches[i].points for i in roads})
    junction_points = Grid(JUNCTION_RADIUS)
    for j, junction in enumerate(graph.junctions):
        for p in junction.points:
            junction_points.add(p[0], p[2], (p, j))

    def junction_near(p: Point3) -> int | None:
        found = [
            (flat_distance(p, q), j)
            for q, j in junction_points.near(p[0], p[2])
            if flat_distance(p, q) <= JUNCTION_RADIUS and abs(p[1] - q[1]) <= SAME_LEVEL
        ]
        return min(found)[1] if found else None

    pieces = []
    for s in roads:
        stretch = graph.stretches[s]
        along = samples(stretch.points)
        partners = []
        for p, heading in along:
            partner = beside.find(p, heading, s)
            back = partner and beside.find(partner.point, partner.heading, partner.line)
            # Paired only both ways: from the partner the nearest point is this one again.
            mutual = back and back.line == s and flat_distance(back.point, p) <= MUTUAL_DISTANCE
            partners.append(partner if mutual else None)
        for other, run in groupby(
            range(len(along)), key=lambda n: partners[n] and partners[n].line
        ):
            run = list(run)
            if other is not None and other < s:
                continue  # made from the other stretch
            if other is None:  # the map lane, from the sample before to the one after the run
                wider = range(max(0, run[0] - 1), min(len(along), run[-1] + 2))
                line = tuple(along[n][0] for n in wider)
            else:
                line = tuple(lerp(along[n][0], partners[n].point, 0.5) for n in run)
            if len(line) < 2:
                continue
            start = stretch.start if run[0] == 0 else junction_near(along[run[0]][0])
            end = stretch.end if run[-1] == len(along) - 1 else junction_near(along[run[-1]][0])
            if start is not None and start == end and length(line) < 2 * JUNCTION_RADIUS:
                continue  # a bit of lane inside a junction
            pieces.append(RoadPiece(line, s, other, start, end))
    return pieces
