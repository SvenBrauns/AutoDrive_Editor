"""Dubins paths: the shortest way from one position and heading to another for a vehicle that
only drives forward and turns no tighter than a given radius. Each path is three parts, each a
left turn (L), right turn (R) or straight (S).

Headings are in radians, direction (cos, sin) in the x-z plane; a left turn raises the heading.
Formulas after A. M. Shkel and V. Lumelsky, "Classification of the Dubins set" (2001).
"""

import math
from dataclasses import dataclass

Pose = tuple[float, float, float]

# Curvature sign per part letter.
TURNS = {"L": 1, "S": 0, "R": -1}


def mod2pi(angle: float) -> float:
    return angle % math.tau


def _lsl(a, b, d):
    p2 = 2 + d * d - 2 * math.cos(a - b) + 2 * d * (math.sin(a) - math.sin(b))
    if p2 < -1e-9:
        return None
    p2 = max(p2, 0.0)
    angle = math.atan2(math.cos(b) - math.cos(a), d + math.sin(a) - math.sin(b))
    return mod2pi(angle - a), math.sqrt(p2), mod2pi(b - angle)


def _rsr(a, b, d):
    p2 = 2 + d * d - 2 * math.cos(a - b) + 2 * d * (math.sin(b) - math.sin(a))
    if p2 < -1e-9:
        return None
    p2 = max(p2, 0.0)
    angle = math.atan2(math.cos(a) - math.cos(b), d - math.sin(a) + math.sin(b))
    return mod2pi(a - angle), math.sqrt(p2), mod2pi(angle - b)


def _lsr(a, b, d):
    p2 = -2 + d * d + 2 * math.cos(a - b) + 2 * d * (math.sin(a) + math.sin(b))
    if p2 < -1e-9:
        return None
    p2 = max(p2, 0.0)
    p = math.sqrt(p2)
    angle = math.atan2(-math.cos(a) - math.cos(b), d + math.sin(a) + math.sin(b)) - math.atan2(
        -2, p
    )
    return mod2pi(angle - a), p, mod2pi(angle - b)


def _rsl(a, b, d):
    p2 = d * d - 2 + 2 * math.cos(a - b) - 2 * d * (math.sin(a) + math.sin(b))
    if p2 < -1e-9:
        return None
    p2 = max(p2, 0.0)
    p = math.sqrt(p2)
    angle = math.atan2(math.cos(a) + math.cos(b), d - math.sin(a) - math.sin(b)) - math.atan2(2, p)
    return mod2pi(a - angle), p, mod2pi(b - angle)


def _rlr(a, b, d):
    value = (6 - d * d + 2 * math.cos(a - b) + 2 * d * (math.sin(a) - math.sin(b))) / 8
    if abs(value) > 1:
        return None
    p = mod2pi(math.tau - math.acos(value))
    t = mod2pi(a - math.atan2(math.cos(a) - math.cos(b), d - math.sin(a) + math.sin(b)) + p / 2)
    return t, p, mod2pi(a - b - t + p)


def _lrl(a, b, d):
    value = (6 - d * d + 2 * math.cos(a - b) + 2 * d * (math.sin(b) - math.sin(a))) / 8
    if abs(value) > 1:
        return None
    p = mod2pi(math.tau - math.acos(value))
    t = mod2pi(-a - math.atan2(math.cos(a) - math.cos(b), d + math.sin(a) - math.sin(b)) + p / 2)
    return t, p, mod2pi(b - a - t + p)


WORDS = {"LSL": _lsl, "RSR": _rsr, "LSR": _lsr, "RSL": _rsl, "RLR": _rlr, "LRL": _lrl}


@dataclass(frozen=True)
class DubinsPath:
    start: Pose
    radius: float
    word: str
    # Length of each part in metres.
    lengths: tuple[float, float, float]

    @property
    def length(self) -> float:
        return sum(self.lengths)

    def sample(self, step: float) -> list[Pose]:
        """Poses along the path about `step` apart, from the start to the exact end."""

        poses = [self.start]
        pose = self.start

        for letter, length in zip(self.word, self.lengths, strict=True):
            curvature = TURNS[letter] / self.radius
            count = max(1, math.ceil(length / step)) if length > 1e-9 else 0

            for _ in range(count):
                pose = advance(pose, curvature, length / count)
                poses.append(pose)

        return poses


def advance(pose: Pose, curvature: float, length: float) -> Pose:
    """The pose after driving `length` metres with the curvature (1 / radius, + = left)."""

    x, z, heading = pose

    if abs(curvature) < 1e-12:
        return x + length * math.cos(heading), z + length * math.sin(heading), heading

    end_heading = heading + curvature * length

    return (
        x + (math.sin(end_heading) - math.sin(heading)) / curvature,
        z - (math.cos(end_heading) - math.cos(heading)) / curvature,
        end_heading,
    )


def shortest_path(start: Pose, goal: Pose, radius: float) -> DubinsPath | None:
    dx, dz = goal[0] - start[0], goal[1] - start[1]
    d = math.hypot(dx, dz) / radius
    angle = math.atan2(dz, dx)
    a, b = mod2pi(start[2] - angle), mod2pi(goal[2] - angle)

    best = None

    for word, solve in WORDS.items():
        parts = solve(a, b, d)

        if parts is None:
            continue

        lengths = tuple(part * radius for part in parts)

        if best is None or sum(lengths) < best.length:
            best = DubinsPath(start, radius, word, lengths)

    return best
