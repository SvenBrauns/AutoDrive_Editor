"""Shapes of the line and curve tools and how nodes are spread along them.

Points are map positions (x, z). Each shape is described by a dense polyline;
spaced_points() then places nodes along it at equal distances.
"""

import math
from dataclasses import dataclass
from enum import Enum
from itertools import pairwise

from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import REGULAR_FLAG
from autodrive_editor.model.connections import ConnectionType

Point = tuple[float, float]

# Polyline points per curve. Enough for an error of about 1 cm on an arc with
# a radius of 500 m.
CURVE_SAMPLES = 512


class PathShape(Enum):
    LINE = "line"
    BEZIER = "bezier"
    ARC = "arc"


@dataclass(frozen=True)
class PathOptions:
    """Settings of the line and curve tools."""

    spacing: float = 5.0
    connection_type: ConnectionType = ConnectionType.REGULAR
    flag: int = REGULAR_FLAG
    # Control points of the Bézier curve: 1 (quadratic) or 2 (cubic).
    control_points: int = 2

    def __post_init__(self):
        if self.control_points not in (1, 2):
            raise ValueError(f"control_points must be 1 or 2, not {self.control_points}")


def default_handles(
    shape: PathShape, start: Point, end: Point, control_points: int = 2
) -> list[Point]:
    """Starting positions of the draggable handles: Bézier control points
    at a third and two thirds of the way (one control point: in the middle),
    the arc point beside the middle so the arc is visible at once."""

    (x0, z0), (x1, z1) = start, end

    if shape == PathShape.BEZIER:
        if control_points == 1:
            return [_lerp(start, end, 0.5)]

        return [_lerp(start, end, 1 / 3), _lerp(start, end, 2 / 3)]

    if shape == PathShape.ARC:
        middle_x, middle_z = _lerp(start, end, 0.5)
        return [(middle_x - (z1 - z0) / 4, middle_z + (x1 - x0) / 4)]

    return []


def shape_polyline(shape: PathShape, start: Point, end: Point, handles: list[Point]) -> list[Point]:
    if shape == PathShape.BEZIER:
        return bezier_polyline(start, *handles, end)

    if shape == PathShape.ARC:
        return arc_polyline(start, handles[0], end)

    return [start, end]


def bezier_polyline(*controls: Point) -> list[Point]:
    """Bézier curve from the first to the last point: quadratic with three
    points (one control point), cubic with four."""

    degree = len(controls) - 1
    points = []

    for index in range(CURVE_SAMPLES + 1):
        t = index / CURVE_SAMPLES
        weights = [math.comb(degree, i) * (1 - t) ** (degree - i) * t**i for i in range(degree + 1)]

        x = sum(weight * point[0] for weight, point in zip(weights, controls, strict=True))
        z = sum(weight * point[1] for weight, point in zip(weights, controls, strict=True))

        points.append((x, z))

    return points


def arc_polyline(start: Point, through: Point, end: Point) -> list[Point]:
    """Circular arc from start through the second point to end. Three points
    on one line give a straight line."""

    (ax, az), (bx, bz), (cx, cz) = start, through, end

    determinant = 2 * (ax * (bz - cz) + bx * (cz - az) + cx * (az - bz))

    if abs(determinant) < 1e-9 * max(1.0, math.dist(start, end) ** 2):
        return [start, end]

    a_square, b_square, c_square = ax * ax + az * az, bx * bx + bz * bz, cx * cx + cz * cz

    center_x = (a_square * (bz - cz) + b_square * (cz - az) + c_square * (az - bz)) / determinant
    center_z = (a_square * (cx - bx) + b_square * (ax - cx) + c_square * (bx - ax)) / determinant
    radius = math.dist(start, (center_x, center_z))

    def angle(point: Point) -> float:
        return math.atan2(point[1] - center_z, point[0] - center_x)

    start_angle = angle(start)
    sweep = (angle(end) - start_angle) % math.tau

    # Go the other way round if the through point is not on this side.
    if (angle(through) - start_angle) % math.tau > sweep:
        sweep -= math.tau

    points = []

    for index in range(CURVE_SAMPLES + 1):
        point_angle = start_angle + sweep * index / CURVE_SAMPLES
        points.append(
            (center_x + radius * math.cos(point_angle), center_z + radius * math.sin(point_angle))
        )

    # Exact end points, without rounding errors from the angles.
    points[0], points[-1] = start, end

    return points


def spaced_points(polyline: list[Point], spacing: float) -> list[Point]:
    """Points along the polyline at equal distances, including both ends.
    The distance is the one closest to `spacing` that divides the length
    evenly."""

    if spacing <= 0:
        raise ValueError(tr("The node spacing must be greater than 0."))

    segment_lengths = [math.dist(a, b) for a, b in pairwise(polyline)]
    total_length = sum(segment_lengths)

    segment_count = max(1, round(total_length / spacing))
    step = total_length / segment_count

    points = [polyline[0]]
    walked = 0.0
    segment_index = 0

    for index in range(1, segment_count):
        target = index * step

        while walked + segment_lengths[segment_index] <= target:
            walked += segment_lengths[segment_index]
            segment_index += 1

        fraction = (target - walked) / segment_lengths[segment_index]

        points.append(_lerp(polyline[segment_index], polyline[segment_index + 1], fraction))

    points.append(polyline[-1])

    return points


def _lerp(a: Point, b: Point, fraction: float) -> Point:
    return a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction
