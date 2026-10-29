"""Parking spots in a shed: the bays and the AutoDrive network that leads into them.

Positions are worked out in the shed's own frame (a, d): a runs along the open side from its left
end, seen from outside, and d runs into the shed (0 on the open side, the depth on the opposite
wall, negative outside). ShedFrame turns them into map positions.

The back in layout is copied from marker G1 of the example route (xml/g8Cq02ZGwaIPuGPr.xml).
"""

import math
from dataclasses import dataclass, field, replace
from enum import Enum

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.connections import ConnectionType


class ParkingMode(Enum):
    BACK_IN = "back_in"
    DRIVE_THROUGH = "drive_through"


# Sides of an indoor area relative to the building, by their corners (start, width end, opposite,
# height end). The front is the side at the end of the height (the building's +Z).
SIDE_CORNERS = {"front": (3, 2), "back": (0, 1), "left": (0, 3), "right": (1, 2)}
OPPOSITE_SIDE = {"front": "back", "back": "front", "left": "right", "right": "left"}

MIN_BAY_WIDTH = 3.0

# Back in, distances outside the open side: the entry line, then the nodes of the bay line from
# where the entry branch joins it. The exit branch starts at the second-to-last node.
ENTRY_LINE_OUTSIDE = 1.0
# The entry line runs this far inside the node the entry branch joins, and at least
# ENTRY_LINE_OUTSIDE outside the shed.
ENTRY_LINE_INSIDE = 1.3
OUTSIDE_NODES = (2.3, 3.3, 4.8, 6.3, 7.8, 11.2, 14.8, 19.7)
FIRST_STEP = 0.5
STEP = 1.5
# The entry branch starts this far before the bay line, against the travel direction.
ENTRY_BRANCH_BACK = 1.2
# The exit line runs this far beyond the exit node; its branch ends this far along the line.
EXIT_LINE_OUTSIDE = 1.6
EXIT_BRANCH_ALONG = 1.7
# Forward steps of the turn after the end of the bay line; the last node reverses to the end.
TURN_STEPS = (3.2, 1.2)

# Drive through: distance of the lines from the shed and the node spacing of the bay lines.
DRIVE_THROUGH_LINE_OUTSIDE = 10.0

# The entry and exit lines reach this far beyond the outer bays.
LINE_EXTENSION = 5.0


@dataclass(frozen=True)
class BayLine:
    """The back in bay line of every bay: segment lengths of the dual line from the marker
    outward, the forward steps of the turn after its end, and the dual line nodes where the entry
    branch joins and the exit branch starts."""

    segments: tuple[float, ...]
    turn: tuple[float, ...]
    entry_node: int
    exit_node: int

    @property
    def distances(self) -> list[float]:
        """Distance of each dual line node from the marker."""

        distances = [0.0]

        for segment in self.segments:
            distances.append(distances[-1] + segment)

        return distances

    def with_segment(self, index: int, length: float) -> "BayLine":
        segments = list(self.segments)
        segments[index] = length

        return replace(self, segments=tuple(segments))

    def with_turn_step(self, index: int, length: float) -> "BayLine":
        turn = list(self.turn)
        turn[index] = length

        return replace(self, turn=tuple(turn))

    def split(self, index: int) -> "BayLine":
        """Inserts a node in the middle of a segment."""

        half = self.segments[index] / 2
        segments = self.segments[:index] + (half, half) + self.segments[index + 1 :]

        def shifted(node):
            return node + 1 if node > index else node

        return BayLine(segments, self.turn, shifted(self.entry_node), shifted(self.exit_node))

    def can_remove(self, node: int) -> bool:
        return 0 < node < len(self.segments) and node not in (self.entry_node, self.exit_node)

    def remove(self, node: int) -> "BayLine":
        """Removes a node, joining its two segments."""

        if not self.can_remove(node):
            raise ValueError("This node can't be removed.")

        joined = self.segments[node - 1] + self.segments[node]
        segments = self.segments[: node - 1] + (joined,) + self.segments[node + 1 :]

        def shifted(index):
            return index - 1 if index > node else index

        return BayLine(segments, self.turn, shifted(self.entry_node), shifted(self.exit_node))

    def entry_nodes(self, marker_d: float) -> list[int]:
        """Nodes the entry branch can join: far enough outside for the entry line, and before
        the exit branch."""

        return [
            node
            for node in range(1, self.exit_node)
            if self._entry_line_depth(marker_d, node) <= -ENTRY_LINE_OUTSIDE
        ]

    def entry_line_depth(self, marker_d: float) -> float:
        return self._entry_line_depth(marker_d, self.entry_node)

    def _entry_line_depth(self, marker_d: float, node: int) -> float:
        return round(marker_d - self.distances[node] + ENTRY_LINE_INSIDE, 6)

    def exit_nodes(self) -> list[int]:
        """Nodes the exit branch can start from: after the entry branch."""

        return list(range(self.entry_node + 1, len(self.segments) + 1))

    def fits(self, marker_d: float) -> bool:
        return self.entry_node in self.entry_nodes(marker_d)


def default_bay_line(marker_d: float) -> BayLine:
    """G1's bay line, fitted to the distance of the marker from the open side: 0.5 m, then
    1.5 m steps up to 1 m before the entry branch, then G1's nodes outside the shed."""

    join = marker_d + OUTSIDE_NODES[0]
    distances = [0.0, FIRST_STEP]
    step = STEP

    while step < join - 1.0:
        distances.append(step)
        step += STEP

    distances += [marker_d + outside for outside in OUTSIDE_NODES]
    segments = tuple(round(b - a, 3) for a, b in zip(distances, distances[1:], strict=False))
    last = len(segments)

    return BayLine(segments, TURN_STEPS, last - len(OUTSIDE_NODES) + 1, last - 1)


@dataclass(frozen=True)
class ParkingSettings:
    mode: ParkingMode = ParkingMode.BACK_IN
    # Open side (back in) or entry side (drive through).
    open_side: str = "front"
    bays: int = 1
    left_offset: float = 0.5
    right_offset: float = 0.5
    # Back wall (back in) or exit side (drive through) to the marker.
    back_offset: float = 2.0
    # Gaps between the bays, from the left; one fewer than bays.
    gaps: tuple[float, ...] = ()
    # Travel direction of the lines, as seen from outside the open side.
    entry_left_to_right: bool = True
    exit_left_to_right: bool = True
    # Back in only; None fits the default bay line to the shed depth.
    bay_line: BayLine | None = None
    marker_name: str = ""
    start_number: int = 1
    group: str = ""


@dataclass
class ParkingNetwork:
    """Nodes as (a, d) points, connections between their indices, markers as (index, name), and
    the open ends of the entry and exit lines."""

    points: list[tuple[float, float]] = field(default_factory=list)
    connections: list[tuple[int, int, ConnectionType]] = field(default_factory=list)
    markers: list[tuple[int, str]] = field(default_factory=list)
    open_ends: list[int] = field(default_factory=list)

    def add(self, a: float, d: float) -> int:
        self.points.append((a, d))

        return len(self.points) - 1

    def connect(self, source: int, target: int, connection_type=ConnectionType.REGULAR):
        self.connections.append((source, target, connection_type))

    def chain(self, indices: list[int], connection_type=ConnectionType.REGULAR):
        for source, target in zip(indices, indices[1:], strict=False):
            self.connect(source, target, connection_type)


@dataclass(frozen=True)
class ShedFrame:
    """The frame of a shed seen from outside its open side."""

    origin: tuple[float, float]
    along: tuple[float, float]
    inward: tuple[float, float]
    length: float
    depth: float

    @classmethod
    def from_area(cls, area: IndoorArea, side: str) -> "ShedFrame":
        corners = area.corners
        start, end = (corners[index] for index in SIDE_CORNERS[side])
        center = tuple(sum(corner[i] for corner in corners) / len(corners) for i in range(2))

        length = math.dist(start, end)
        along = ((end[0] - start[0]) / length, (end[1] - start[1]) / length)
        inward = (-along[1], along[0])
        depth = 2 * _dot((center[0] - start[0], center[1] - start[1]), inward)

        if depth < 0:
            inward, depth = (-inward[0], -inward[1]), -depth

        # The map's z axis points down on screen, so (-inward z, inward x) is the right hand of
        # someone outside looking in.
        if _dot(along, (-inward[1], inward[0])) < 0:
            start, along = end, (-along[0], -along[1])

        return cls(start, along, inward, length, depth)

    def to_map(self, a: float, d: float) -> tuple[float, float]:
        return tuple(self.origin[i] + a * self.along[i] + d * self.inward[i] for i in range(2))

    def map_direction(self, x: float, z: float) -> tuple[float, float]:
        """A map direction in the frame, as (a, d)."""

        return _dot((x, z), self.along), _dot((x, z), self.inward)


def default_open_side(area: IndoorArea) -> str:
    """The front if it is a long side, otherwise the left."""

    start, width_end, _, height_end = area.corners

    return "front" if math.dist(start, width_end) >= math.dist(start, height_end) else "left"


def side_angle(area: IndoorArea, side: str) -> float:
    """Map angle the side faces outward: 0° up, 90° right."""

    frame = ShedFrame.from_area(area, side)

    return math.degrees(math.atan2(-frame.inward[0], frame.inward[1])) % 360


def bay_width(frame: ShedFrame, settings: ParkingSettings) -> float:
    free = frame.length - settings.left_offset - settings.right_offset - sum(settings.gaps)

    return free / settings.bays


def bay_centers(frame: ShedFrame, settings: ParkingSettings) -> list[float]:
    width = bay_width(frame, settings)
    centers = []
    a = settings.left_offset

    for index in range(settings.bays):
        centers.append(a + width / 2)
        a += width + (settings.gaps[index] if index < len(settings.gaps) else 0.0)

    return centers


def plan_parking(frame: ShedFrame, settings: ParkingSettings) -> ParkingNetwork:
    """The network of all bays and their shared entry and exit lines."""

    if len(settings.gaps) != settings.bays - 1:
        raise ValueError("There must be one gap fewer than bays.")

    if bay_width(frame, settings) < MIN_BAY_WIDTH:
        raise ValueError("The bays are too narrow.")

    if not 0 <= settings.back_offset < frame.depth:
        raise ValueError("The marker must be inside the shed.")

    back_in = settings.mode == ParkingMode.BACK_IN

    if back_in and not bay_line(frame, settings).fits(marker_depth(frame, settings)):
        raise ValueError("The entry line must be outside the shed.")

    network = ParkingNetwork()
    entry_nodes, exit_nodes = [], []

    for number, a in enumerate(bay_centers(frame, settings), start=settings.start_number):
        if settings.mode == ParkingMode.BACK_IN:
            marker, entry, exit_ = _back_in_bay(network, frame, settings, a)
        else:
            marker, entry, exit_ = _drive_through_bay(network, frame, settings, a)

        network.markers.append((marker, f"{settings.marker_name} {number}"))
        entry_nodes.append(entry)
        exit_nodes.append(exit_)

    _line(network, entry_nodes, settings.entry_left_to_right)
    _line(network, exit_nodes, settings.exit_left_to_right)

    return network


def bay_line(frame: ShedFrame, settings: ParkingSettings) -> BayLine:
    """The back in bay line: the edited one, or the default fitted to the shed."""

    return settings.bay_line or default_bay_line(marker_depth(frame, settings))


def marker_depth(frame: ShedFrame, settings: ParkingSettings) -> float:
    return frame.depth - settings.back_offset


def _back_in_bay(network, frame, settings, a) -> tuple[int, int, int]:
    """Dual line from the marker out of the shed with a turn at its end. Returns the marker and
    the entry and exit line nodes."""

    marker_d = marker_depth(frame, settings)
    layout = bay_line(frame, settings)
    distances = layout.distances
    line = [network.add(a, marker_d - distance) for distance in distances]
    network.chain(line, ConnectionType.DUAL)

    turn = [line[-1]]
    distance = distances[-1]

    for turn_step in layout.turn:
        distance += turn_step
        turn.append(network.add(a, marker_d - distance))

    network.chain(turn)
    network.connect(turn[-1], line[-1], ConnectionType.REVERSE)

    entry_sign = 1 if settings.entry_left_to_right else -1
    entry_d = layout.entry_line_depth(marker_d)
    entry = network.add(a - entry_sign * ENTRY_BRANCH_BACK, entry_d)
    network.connect(entry, line[layout.entry_node])

    exit_sign = 1 if settings.exit_left_to_right else -1
    exit_d = marker_d - distances[layout.exit_node] - EXIT_LINE_OUTSIDE
    exit_ = network.add(a + exit_sign * EXIT_BRANCH_ALONG, exit_d)
    network.connect(line[layout.exit_node], exit_)

    return line[0], entry, exit_


def drive_through_line(frame: ShedFrame, settings: ParkingSettings) -> tuple[list[float], int]:
    """Depths of the nodes of a drive through bay line, and the index of the marker."""

    marker_d = marker_depth(frame, settings)
    stops = (-DRIVE_THROUGH_LINE_OUTSIDE, marker_d, frame.depth + DRIVE_THROUGH_LINE_OUTSIDE)
    depths = [stops[0]]
    marker = None

    for start, end in zip(stops, stops[1:], strict=False):
        steps = max(1, round((end - start) / STEP))

        for index in range(1, steps + 1):
            depths.append(start + (end - start) * index / steps)

        marker = len(depths) - 1 if marker is None else marker

    return depths, marker


def _drive_through_bay(network, frame, settings, a) -> tuple[int, int, int]:
    """Straight line from the entry line through the shed to the marker and on to the exit
    line."""

    depths, marker = drive_through_line(frame, settings)
    line = [network.add(a, d) for d in depths]
    network.chain(line)

    return line[marker], line[0], line[-1]


def _line(network: ParkingNetwork, nodes: list[int], left_to_right: bool):
    """Connects the bays' line nodes in travel order, with an open end beyond each outer bay."""

    sign = 1 if left_to_right else -1
    ordered = sorted(nodes, key=lambda index: sign * network.points[index][0])
    first_a, first_d = network.points[ordered[0]]
    last_a, last_d = network.points[ordered[-1]]

    start = network.add(first_a - sign * LINE_EXTENSION, first_d)
    end = network.add(last_a + sign * LINE_EXTENSION, last_d)

    network.chain([start, *ordered, end])
    network.open_ends += [start, end]


def _dot(u, v) -> float:
    return u[0] * v[0] + u[1] * v[1]
