"""The yard road past the stops of stations, drawn by the user as corner points.

Each inner corner is rounded by an arc of the curve radius (see route_geometry.fillet). A Through
road runs one-way from the first corner to the last. A Loop closes when the last corner is put on
an earlier one: the corners up to there are a two-way stem, the rest a one-way ring that starts
and ends at that corner, in the order clicked.

Points are map positions (x, z).
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from autodrive_editor.editing.routes.route_geometry import fillet, sample
from autodrive_editor.editing.routes.route_nodes import _recorded

Point = tuple[float, float]

# The road is drawn with points this far apart (in metres) before its nodes are spaced.
LINE_STEP = 0.25
# Road nodes where branches leave and join lie at least this far apart (in metres).
MIN_GAP = 1.0


@dataclass(frozen=True)
class YardRoad:
    """The road as fine lines: the two-way stem from the first corner to the ring (empty for a
    Through road or a ring right at the first corner) and the one-way road, which for a Loop
    starts and ends at the same point."""

    stem: list[Point]
    road: list[Point]
    loop: bool


def yard_road(corners: list[Point], radius: float, closes_at: int | None = None) -> YardRoad | None:
    """The road through the corners; `closes_at` is the index of the earlier corner the last one
    was put on, which makes it a Loop. None where the arcs do not fit or there are too few
    corners."""

    if closes_at is None:
        road = _line(corners, radius)

        return YardRoad([], road, False) if road else None

    ring = [*corners[closes_at:-1], corners[closes_at]]
    stem = _line(corners[: closes_at + 1], radius) if closes_at > 0 else []
    road = _line(ring, radius) if len(ring) >= 4 else None

    if road is None or (closes_at > 0 and not stem):
        return None

    return YardRoad(stem, road, True)


def _line(corners: list[Point], radius: float) -> list[Point] | None:
    if len(corners) < 2 or any(math.dist(a, b) < 1e-6 for a, b in pairwise(corners)):
        return None

    pieces = fillet(corners, radius)

    return sample(pieces, LINE_STEP) if pieces else None


def road_points(line: list[Point], spacing: float, fixed: list[float] = ()) -> list[Point]:
    """Node positions along the line as AutoDrive records a drive, with a node exactly at each
    of the `fixed` distances from the start (where branches leave and join). Fixed distances
    closer than MIN_GAP to one before them or to an end share that node."""

    points: list[Point] = []
    kept: list[float] = []

    for distance in sorted(fixed):
        if MIN_GAP <= distance <= length(line) - MIN_GAP and (
            not kept or distance - kept[-1] >= MIN_GAP
        ):
            kept.append(distance)

    for part in _split_at(line, kept):
        spaced = _recorded(part, spacing) if len(part) > 1 else part
        points += spaced if not points else spaced[1:]

    return points


def _split_at(line: list[Point], distances: list[float]) -> list[list[Point]]:
    """The line cut into parts at the distances, each part with the point at the cut."""

    parts, part, walked = [], [line[0]], 0.0
    pending = [d for d in distances if 0 < d < length(line)]

    for a, b in pairwise(line):
        step = math.dist(a, b)

        while pending and pending[0] <= walked + step:
            fraction = (pending.pop(0) - walked) / step if step else 0.0
            cut = (a[0] + fraction * (b[0] - a[0]), a[1] + fraction * (b[1] - a[1]))

            if math.dist(cut, part[-1]) > 1e-6:
                part.append(cut)
                parts.append(part)
                part = [cut]

        walked += step

        if math.dist(b, part[-1]) > 1e-6:
            part.append(b)

    return [*parts, part]


def length(line: list[Point]) -> float:
    return sum(math.dist(a, b) for a, b in pairwise(line))
