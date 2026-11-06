"""Made-up traffic lanes for the road graph tests: two-way roads are two lanes 4 m apart."""

import math

from autodrive_editor.file_io.traffic_splines import TrafficLane

HALF_GAP = 2.0


def lane(*points, height=0.0) -> TrafficLane:
    """A lane through map points (x, z) or world points (x, y, z)."""
    return TrafficLane(tuple(p if len(p) == 3 else (p[0], height, p[1]) for p in points), None)


def _along(
    angle: float, distance: float, side: float = 0.0, centre=(0.0, 0.0)
) -> tuple[float, float]:
    """The point `distance` along the direction `angle` (degrees) from the centre, `side` metres to
    its left."""
    dx, dz = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return centre[0] + dx * distance - dz * side, centre[1] + dz * distance + dx * side


def junction(angles, inner_radius=10.0, arm_length=100.0, centre=(0.0, 0.0)) -> list[TrafficLane]:
    """Two-way arms from the centre in the given directions, the lanes ending inner_radius from
    it, and a turn lane from every arm into every other one. arm_length: one for all arms or a
    length per angle."""
    lengths = arm_length if isinstance(arm_length, dict) else dict.fromkeys(angles, arm_length)
    lanes = []
    for a in angles:
        far, near = lengths[a], inner_radius
        lanes.append(lane(_along(a, far, HALF_GAP, centre), _along(a, near, HALF_GAP, centre)))
        lanes.append(lane(_along(a, near, -HALF_GAP, centre), _along(a, far, -HALF_GAP, centre)))
    for a in angles:
        for b in angles:
            if a != b:
                lanes.append(
                    lane(
                        _along(a, inner_radius, HALF_GAP, centre),
                        _along(b, inner_radius, -HALF_GAP, centre),
                    )
                )
    return lanes


def _arc(radius, start, end, step=3.0):
    count = max(1, math.ceil(abs(end - start) / step))
    return [_along(start + (end - start) * i / count, radius) for i in range(count + 1)]


def roundabout(angles, radius=20.0, arm_length=100.0, spread=12.0) -> list[TrafficLane]:
    """A one-way ring, driven counterclockwise (growing angles), with two-way arms; each arm
    enters the ring `spread` degrees before its direction and leaves it `spread` after."""
    angles = sorted(angles)
    lanes = []
    for i, a in enumerate(angles):
        b = angles[(i + 1) % len(angles)] + (360 if i == len(angles) - 1 else 0)
        lanes.append(lane(_along(a, arm_length, -HALF_GAP), _along(a - spread, radius)))
        lanes.append(lane(_along(a + spread, radius), _along(a, arm_length, HALF_GAP)))
        lanes.append(lane(*_arc(radius, a - spread, a + spread)))
        lanes.append(lane(*_arc(radius, a + spread, b - spread)))
    return lanes


def circle(centre, radius, counterclockwise=True, step=5.0) -> TrafficLane:
    """A closed one-way lane."""
    sign = 1 if counterclockwise else -1
    count = round(360 / step)
    return lane(*(_along(sign * 360 * i / count, radius, centre=centre) for i in range(count + 1)))


def two_way_circle(centre, radius) -> list[TrafficLane]:
    return [
        circle(centre, radius - HALF_GAP),
        circle(centre, radius + HALF_GAP, counterclockwise=False),
    ]
