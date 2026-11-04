"""Bunker silos: how vehicles use a silo, found from the drivability map, and the default layout.

The silo's inner area (see savegame_sheds) runs between its walls; its height is the driving
direction, so its ends are the back (start edge) and the front (height end), named as the shed
sides in parking_layout. Which end is closed by a wall is not in the building's XML, but the
drivability map shows it: just outside a closed end the cells are blocked, outside an open end
they are not.

The layout is the shed's (parking_layout) with the silo's distances; its bays are the lanes.
"""

import math

from autodrive_editor.editing.parking_layout import ParkingMode, ParkingSettings, ShedFrame
from autodrive_editor.file_io.navigation_costmap import BLOCKED_VALUE, NavigationCostmap
from autodrive_editor.file_io.savegame_sheds import IndoorArea

ENDS = {"back": (0, 1, 3), "front": (3, 2, 0)}
# Distances outside an end where the wall shows in the map: it lies 0–1.5 m past the inner area.
WALL_DISTANCES = (0.5, 1.0, 1.5)
# An end is closed when at least this part of it is blocked.
CLOSED_SHARE = 0.5

# One lane per this much of the inner width.
LANE_WIDTH = 5.5
# Back in: the marker's distance from the back wall. Drive through: past the silo's far end.
BACK_WALL_TO_MARKER = 3.0
MARKER_PAST_SILO = 15.0


def silo_settings(area: IndoorArea, costmap: NavigationCostmap | None) -> ParkingSettings:
    """The default layout of a silo: mode and side from the map, lanes in the centres of equal
    strips of the inner width."""

    mode, side = silo_access(area, costmap)
    lanes = max(1, round(ShedFrame.from_area(area, side).length / LANE_WIDTH))
    back_in = mode == ParkingMode.BACK_IN

    return ParkingSettings(
        mode=mode,
        open_side=side,
        bays=lanes,
        left_offset=0.0,
        right_offset=0.0,
        back_offset=BACK_WALL_TO_MARKER if back_in else -MARKER_PAST_SILO,
        gaps=(0.0,) * (lanes - 1),
        silo=True,
    )


def silo_access(area: IndoorArea, costmap: NavigationCostmap | None) -> tuple[ParkingMode, str]:
    """Mode and open side of a silo (for driving through, the side vehicles drive in). One end
    closed: back in from the other end. Both open: drive through from the front. Without a map
    or with both ends closed: back in from the front, as most silos are built."""

    if costmap is None:
        return ParkingMode.BACK_IN, "front"

    closed = {side for side in ENDS if blocked_share(area, side, costmap) >= CLOSED_SHARE}

    if not closed:
        return ParkingMode.DRIVE_THROUGH, "front"

    if closed == {"front"}:
        return ParkingMode.BACK_IN, "back"

    return ParkingMode.BACK_IN, "front"


def blocked_share(area: IndoorArea, side: str, costmap: NavigationCostmap) -> float:
    """The largest blocked part of the lines just outside one end of the silo, without the
    corners at the side walls."""

    start, end, inner = (area.corners[index] for index in ENDS[side])
    depth = math.dist(start, inner)
    outward = ((start[0] - inner[0]) / depth, (start[1] - inner[1]) / depth)
    steps = max(2, int(math.dist(start, end)))
    shares = []

    for distance in WALL_DISTANCES:
        points = [
            tuple(
                start[i] + (end[i] - start[i]) * step / steps + outward[i] * distance
                for i in range(2)
            )
            for step in range(1, steps)
        ]
        blocked = sum(costmap.value_at(*point) >= BLOCKED_VALUE for point in points)
        shares.append(blocked / len(points))

    return max(shares)
