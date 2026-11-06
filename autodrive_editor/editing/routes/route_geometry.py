"""Routes as straight pieces and circular arcs, the way hand-made courses are drawn: a line through
corner points, each corner rounded by an arc of one radius that touches both sides.

Points are map positions (x, z); headings in radians, a left turn raises the heading (see dubins).
"""

import math
from dataclasses import dataclass
from itertools import pairwise

from autodrive_editor.editing.routes.dubins import WORDS, Pose, advance

Point = tuple[float, float]

# Corners turning less than this are left out; lengths below this count as zero.
STRAIGHT_TURN = 1e-6
TOLERANCE = 1e-6
# Arcs turning this close to half a circle are left out; corners cannot round them.
MAX_ARC = math.pi - 0.01


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
    one where their outer sides meet, if they turn the same way; otherwise they are replaced by
    the shortest turn, straight, turn between where the arcs before and after them end. None
    where the arcs still do not fit or a corner turns back."""

    corners = _without_straight_corners(corners)

    for _ in range(2 * len(corners or ()) + 10):
        if corners is None:
            return None

        repaired = _repair_first_overlap(corners, radius)

        if repaired is corners:
            break

        corners = repaired
    else:
        return None

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


def corners_of(pieces: list[Piece]) -> list[Point]:
    """The corner points the pieces were rounded from (see fillet)."""

    corners = [pieces[0].start[:2]]

    for piece in pieces:
        if piece.curvature:
            radius = 1 / abs(piece.curvature)
            corners.append(_ahead(piece.start, _tangent(piece.curvature * piece.length, radius)))

    return [*corners, pieces[-1].end[:2]]


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


def _repair_first_overlap(corners: list[Point], radius: float) -> list[Point] | None:
    """The corners with the first two whose arcs overlap merged or replaced (see fillet); the
    same list if no arcs overlap, None if two overlap and cannot be repaired."""

    tangents = [0.0] * len(corners)

    for index in range(1, len(corners) - 1):
        tangents[index] = _tangent(_turn(*corners[index - 1 : index + 2]), radius)

    for index, (a, b) in enumerate(pairwise(corners)):
        if tangents[index] + tangents[index + 1] <= math.dist(a, b) + TOLERANCE:
            continue

        if 0 < index and index + 2 < len(corners):
            merged = _merged(corners, index)

            if merged is not None:
                return merged

        first, last = max(index, 1), min(index + 1, len(corners) - 2)

        return _replaced(corners, first, last, tangents, radius)

    return corners


def _replaced(
    corners: list[Point], first: int, last: int, tangents: list[float], radius: float
) -> list[Point] | None:
    """The corners with corners `first` to `last` replaced by the shortest turn, straight, turn
    that turns no more than they do, from a point on the side before them to one on the side
    after them. The points start one radius away and move out until the way fits, at most to the
    ends of the arcs before and after. None if it never fits."""

    before, after = corners[first - 1], corners[last + 1]
    turns = sum(abs(_turn(*corners[index - 1 : index + 2])) for index in range(first, last + 1))
    start_heading = _heading(before, corners[first])
    goal_heading = _heading(corners[last], after)
    room_before = math.dist(before, corners[first]) - tangents[first - 1]
    room_after = math.dist(corners[last], after) - tangents[last + 1]
    reach = radius

    while True:
        start = _towards(corners[first], before, min(reach, room_before))
        goal = _towards(corners[last], after, min(reach, room_after))
        ways = turn_straight_turn((*start, start_heading), (*goal, goal_heading), radius, turns)

        if ways:
            middle = [start, *ways[0], goal]
            return _without_straight_corners([*corners[:first], *middle, *corners[last + 1 :]])

        if reach >= max(room_before, room_after):
            return None

        reach *= 2


def _merged(corners: list[Point], index: int) -> list[Point] | None:
    """The corners with corner `index` and the next merged where the sides before and after
    them meet, if they turn the same way by less than half a circle; else None."""

    before, first, second, after = corners[index - 1 : index + 3]
    first_turn = _turn(before, first, second)
    second_turn = _turn(first, second, after)

    if first_turn * second_turn <= 0 or abs(first_turn + second_turn) >= math.pi:
        return None

    meeting = _meeting_point(before, first, second, after)

    if meeting is None:
        return None

    return _without_straight_corners([*corners[:index], meeting, *corners[index + 2 :]])


def turn_straight_turn(
    start: Pose, goal: Pose, radius: float, max_turn: float = math.inf
) -> list[tuple[Point, Point]]:
    """The two corners of each way from start to goal that turns at the radius, runs straight
    and turns again, each turn less than half a circle and both together at most `max_turn`
    (the Dubins paths without a middle arc), shortest first."""

    dx, dz = goal[0] - start[0], goal[1] - start[1]
    d = math.hypot(dx, dz) / radius
    angle = math.atan2(dz, dx)
    a = (start[2] - angle) % math.tau
    b = (goal[2] - angle) % math.tau
    ways = []

    for word in ("LSL", "RSR", "LSR", "RSL"):
        parts = WORDS[word](a, b, d)

        if parts is None or max(parts[0], parts[2]) >= MAX_ARC:
            continue

        if parts[0] + parts[2] > max_turn + STRAIGHT_TURN:
            continue

        first = _ahead(start, radius * math.tan(parts[0] / 2))
        second = _ahead(goal, -radius * math.tan(parts[2] / 2))
        ways.append((sum(parts), first, second))

    return [(first, second) for _, first, second in sorted(ways)]


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


def _ahead(pose: Pose, distance: float) -> Point:
    return pose[0] + distance * math.cos(pose[2]), pose[1] + distance * math.sin(pose[2])


def _heading(a: Point, b: Point) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def _towards(a: Point, b: Point, distance: float) -> Point:
    length = math.dist(a, b)

    return a[0] + (b[0] - a[0]) * distance / length, a[1] + (b[1] - a[1]) * distance / length
