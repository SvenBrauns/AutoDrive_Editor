"""The game's drivability map, `vehicleNavigationCostmap.dat` in the savegame.

File: `VNCM`, uint32 version, 4 unknown bytes, then a zlib stream. Decompressed: uint16 width,
height, tile width, tile height, a block of unknown bytes, then width × height cells, one byte
per square metre, row by row: column = x + width / 2, row = z + height / 2.

Cell values come in bands 34 apart that start at 51 (roads), 85, 119, 153, 187 and so on; the
steeper the ground, the higher the value within its band. 254 and 255 are blocked (buildings,
water, trees, fences).
"""

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

COSTMAP_FILE_NAME = "vehicleNavigationCostmap.dat"
MAGIC = b"VNCM"
HEADER_SIZE = 12
# Cells with this value or higher cannot be driven on.
BLOCKED_VALUE = 254
# The cheapest value, on roads.
ROAD_VALUE = 51


class CostmapError(Exception):
    """The file is not a drivability map this reader understands."""


@dataclass(frozen=True)
class NavigationCostmap:
    width: int
    height: int
    cells: bytes

    def cell_of(self, x: float, z: float) -> tuple[int, int]:
        """Column and row of the cell at the world position."""

        return int(x + self.width / 2), int(z + self.height / 2)

    def value_at(self, x: float, z: float) -> int:
        """The cell value at the world position; outside the map counts as blocked."""

        column, row = self.cell_of(x, z)

        if not (0 <= column < self.width and 0 <= row < self.height):
            return 255

        return self.cells[row * self.width + column]

    def row(self, row: int, first_column: int, end_column: int) -> bytes:
        """The cells of one row from first_column to end_column (exclusive). Parts outside the
        map are blocked."""

        before = max(0, -first_column)
        after = max(0, end_column - self.width)

        if not 0 <= row < self.height:
            return b"\xff" * (end_column - first_column)

        start = row * self.width + max(0, first_column)
        end = row * self.width + min(self.width, end_column)

        return b"\xff" * before + self.cells[start:end] + b"\xff" * after


def costmap_path(savegame_directory: Path) -> Path:
    return Path(savegame_directory) / COSTMAP_FILE_NAME


def read_costmap(path: Path) -> NavigationCostmap:
    data = Path(path).read_bytes()

    if data[:4] != MAGIC:
        raise CostmapError(f"{path} is not a navigation costmap.")

    try:
        content = zlib.decompress(data[HEADER_SIZE:])
    except zlib.error as error:
        raise CostmapError(f"{path} could not be unpacked: {error}") from error

    if len(content) < 8:
        raise CostmapError(f"{path} is too short.")

    width, height = struct.unpack_from("<2H", content)

    if width == 0 or height == 0 or len(content) < 8 + width * height:
        raise CostmapError(f"{path} has no cells for {width} × {height}.")

    return NavigationCostmap(width, height, content[-width * height :])
