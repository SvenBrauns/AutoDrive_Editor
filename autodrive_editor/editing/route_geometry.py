"""Routes as straight pieces and circular arcs, the way hand-made courses are drawn: a line through
corner points, each corner rounded by an arc of one radius that touches both sides.

Points are map positions (x, z); headings in radians, a left turn raises the heading (see dubins).
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from autodrive_editor.editing.dubins import Pose, advance

Point = tuple[float, float]

# Corners turning less than this are left out; lengths below this count as zero.
STRAIGHT_TURN = 1e-6
TOLERANCE = 1e-6


@dataclass(frozen=True)
class Piece:
    start: Pose
    length: float
    # 1 / radius, + = left; 0 on a straight piece.
    curvature: float = 0.0

    @property
    def end(self) -> Pose:
        return advance(self.start, self.curvature, self.length)


def fillet(corners: list[Point], radius: float) -> list[Piece] | None:
    """Straight pieces through the corners, each inner corner rounded by an arc of the radius
    touching both sides, so the route starts and ends exactly at the first and last corner along
    the first and last side. Two neighbouring corners too close for their arcs are merged into
    one where their outer sides meet, if they turn the same way. None where the arcs still do not
    fit or a corner turns back."""

    corners = _without_straight_corners(corners)

    if corners is None:
        return None

    while (merged := _merge_first_overlap(corners, radius)) is not corners:
        if merged is None:
            return None

        corners = merged

    if len(corners) < 2:
        return []

    pieces = []
    position = corners[0]

    for index in range(1, len(corners) - 1):
        before, corner, after = corners[index - 1 : index + 2]
        heading = _heading(before, corner)
        turn = _turn(before, corner, after)
        tangent = _tangent(turn, radius)
        arc_start = _towards(corner, before, tangent)
        _add_straight(pieces, position, arc_start, heading)
        pieces.append(
            Piece((*arc_start, heading), abs(turn) * radius, math.copysign(1, turn) / radius)
        )
        position = _towards(corner, after, tangent)

    _add_straight(pieces, position, corners[-1], _heading(corners[-2], corners[-1]))

    return pieces


def sample(pieces: list[Piece], step: float) -> list[Point]:
    """Points along the pieces at most `step` apart, from the start to the exact end."""

    if not pieces:
        return []

    points = [pieces[0].start[:2]]

    for piece in pieces:
        count = max(1, math.ceil(piece.length / step))
        points += [
            advance(piece.start, piece.curvature, piece.length * k / count)[:2]
            for k in range(1, count + 1)
        ]

    return points


def _without_straight_corners(corners: list[Point]) -> list[Point] | None:
    """The corners without repeated points and without corners that do not turn; None if one
    turns back."""

    result: list[Point] = []

    for corner in corners:
        if result and math.dist(result[-1], corner) < TOLERANCE:
            continue

        if len(result) >= 2:
            turn = _turn(result[-2], result[-1], corner)

            if abs(turn) < STRAIGHT_TURN:
                result.pop()
            elif abs(turn) > math.pi - STRAIGHT_TURN:
                return None

        result.append(corner)

    return result


def _merge_first_overlap(corners: list[Point], radius: float) -> list[Point] | None:
    """The corners with the first two whose arcs overlap merged (see fillet); the same list if
    no arcs overlap, None if two overlap and cannot be merged."""

    tangents = [0.0] * len(corners)

    for index in range(1, len(corners) - 1):
        tangents[index] = _tangent(_turn(*corners[index - 1 : index + 2]), radius)

    for index, (a, b) in enumerate(pairwise(corners)):
        if tangents[index] + tangents[index + 1] <= math.dist(a, b) + TOLERANCE:
            continue

        if index == 0 or index + 2 >= len(corners):
            return None

        before, first, second, after = corners[index - 1 : index + 3]
        first_turn = _turn(before, first, second)
        second_turn = _turn(first, second, after)

        if first_turn * second_turn <= 0 or abs(first_turn + second_turn) >= math.pi:
            return None

        meeting = _meeting_point(before, first, second, after)

        if meeting is None:
            return None

        return _without_straight_corners([*corners[:index], meeting, *corners[index + 2 :]])

    return corners


def _meeting_point(before: Point, first: Point, second: Point, after: Point) -> Point | None:
    """Where the line from `before` through `first` meets the line from `after` back through
    `second`, if it lies ahead on both."""

    (ax, az), (bx, bz) = before, after
    dx1, dz1 = first[0] - ax, first[1] - az
    dx2, dz2 = second[0] - bx, second[1] - bz
    cross = dx1 * dz2 - dz1 * dx2

    if abs(cross) < TOLERANCE:
        return None

    along_first = ((bx - ax) * dz2 - (bz - az) * dx2) / cross
    along_second = ((bx - ax) * dz1 - (bz - az) * dx1) / cross

    if along_first <= 0 or along_second <= 0:
        return None

    return ax + along_first * dx1, az + along_first * dz1


def _add_straight(pieces: list[Piece], start: Point, end: Point, heading: float):
    length = math.dist(start, end)

    if length > TOLERANCE:
        pieces.append(Piece((*start, heading), length))


def _tangent(turn: float, radius: float) -> float:
    """Distance from a corner to where the arc touches its sides."""

    return radius * math.tan(abs(turn) / 2)


def _turn(before: Point, corner: Point, after: Point) -> float:
    return math.remainder(_heading(corner, after) - _heading(before, corner), math.tau)


def _heading(a: Point, b: Point) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def _towards(a: Point, b: Point, distance: float) -> Point:
    length = math.dist(a, b)

    return a[0] + (b[0] - a[0]) * distance / length, a[1] + (b[1] - a[1]) * distance / length
