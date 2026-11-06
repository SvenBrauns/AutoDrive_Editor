"""The parts of the planned road network (road_network) that the Box and Click road modes of the
Roads generator build. A box keeps the junctions whose middle lies inside it, whole, and the
roads inside it; the junctions of the others are left out. A clicked road is the road along one
map lane from junction to junction, without the junctions."""

from dataclasses import dataclass, replace

from autodrive_editor.editing.road_existing import _inside
from autodrive_editor.editing.road_graph import Point3, RoadGraph, flat_distance, lerp
from autodrive_editor.editing.road_network import RoadNetwork

ROAD_REACH = 6.0  # planned nodes this close to the clicked map lane belong to its road (metres)

Polygon = list[tuple[float, float]]  # (x, z)


@dataclass
class Part:
    network: RoadNetwork  # with only the kept junctions and the places to look at in the part
    keep: set[int]  # the planned nodes to build
    edges: list[Point3]  # kept nodes next to left-out ones, where the part was cut off


def box_part(network: RoadNetwork, graph: RoadGraph, box: Polygon) -> Part:
    def middle(group) -> Point3:
        centres = [graph.junctions[j].centre for j in group]
        return tuple(sum(c[k] for c in centres) / len(centres) for k in range(3))

    kept = [k for k, group in enumerate(network.groups) if _in_polygon(box, middle(group))]
    others = [_Area(network.areas[k]) for k in range(len(network.groups)) if k not in kept]
    whole = [_Area(network.areas[k]) for k in kept]

    def keep(p: Point3) -> bool:
        if any(area.has(p) for area in whole):
            return True
        return _in_polygon(box, p) and not any(area.has(p) for area in others)

    return _part(network, kept, keep)


def road_at(graph: RoadGraph, x: float, z: float, reach: float) -> int | None:
    """The stretch of the map lane within reach of (x, z) that a road follows, if any."""
    inner = set().union(*(j.inner for j in graph.junctions))
    point = (x, 0.0, z)
    found = [
        (_distance(point, stretch.points), s)
        for s, stretch in enumerate(graph.stretches)
        if s not in inner
    ]
    distance, s = min(found, default=(reach + 1, None))
    return s if distance <= reach else None


def road_part(network: RoadNetwork, graph: RoadGraph, s: int) -> Part:
    """The road along stretch s from junction to junction."""
    line = graph.stretches[s].points
    road = _Area([(p[0], p[2]) for p in line], ROAD_REACH)
    areas = [_Area(area) for area in network.areas]

    def keep(p: Point3) -> bool:
        return (
            road.near(p)
            and _distance(p, line) <= ROAD_REACH
            and not any(area.has(p) for area in areas)
        )

    return _part(network, [], keep)


def _part(network: RoadNetwork, kept: list[int], keep) -> Part:
    piece = network.piece
    nodes = {i for i, p in enumerate(piece.points) if keep(p)}
    edges = {
        i
        for a, b, _ in piece.connections
        if (a in nodes) != (b in nodes)
        for i in (a, b)
        if i in nodes
    }
    return Part(
        replace(
            network,
            listed=[(p, text) for p, text in network.listed if keep(p)],
            areas=[network.areas[k] for k in kept],
            groups=[network.groups[k] for k in kept],
        ),
        nodes,
        [piece.points[i] for i in sorted(edges)],
    )


class _Area:
    """An outline with its bounds (plus margin), for a quick test first."""

    def __init__(self, outline: Polygon, margin: float = 3.0):
        self.outline = outline
        xs, zs = [p[0] for p in outline], [p[1] for p in outline]
        self.bounds = min(xs) - margin, min(zs) - margin, max(xs) + margin, max(zs) + margin

    def near(self, p: Point3) -> bool:
        x0, z0, x1, z1 = self.bounds
        return x0 <= p[0] <= x1 and z0 <= p[2] <= z1

    def has(self, p: Point3) -> bool:
        return self.near(p) and _inside(self.outline, p)


def _in_polygon(polygon: Polygon, p: Point3) -> bool:
    x, z = p[0], p[2]
    inside = False
    for (ax, az), (bx, bz) in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        if (az > z) != (bz > z) and x < ax + (z - az) * (bx - ax) / (bz - az):
            inside = not inside
    return inside


def _distance(p: Point3, line) -> float:
    """From p to the nearest point of the line, on the map."""
    best = float("inf")
    for a, b in zip(line, line[1:], strict=False):
        dx, dz = b[0] - a[0], b[2] - a[2]
        size = dx * dx + dz * dz
        t = 0.0 if size == 0 else ((p[0] - a[0]) * dx + (p[2] - a[2]) * dz) / size
        best = min(best, flat_distance(p, lerp(a, b, min(1.0, max(0.0, t)))))
    return best
