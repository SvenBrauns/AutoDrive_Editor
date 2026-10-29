"""Small drivability maps for tests (see navigation_costmap)."""

import struct
import zlib

from autodrive_editor.file_io.navigation_costmap import NavigationCostmap

ROAD = 51
GRASS = 119
BLOCKED = 255


def make_costmap(size=200, value=ROAD, blocked=()) -> NavigationCostmap:
    """A square map of one value; `blocked` holds (x1, z1, x2, z2) world rectangles."""

    cells = bytearray([value]) * (size * size)

    for x1, z1, x2, z2 in blocked:
        for z in range(z1, z2):
            for x in range(x1, x2):
                cells[(z + size // 2) * size + x + size // 2] = BLOCKED

    return NavigationCostmap(size, size, bytes(cells))


def costmap_file_bytes(costmap: NavigationCostmap) -> bytes:
    content = struct.pack("<4H", costmap.width, costmap.height, 32, 32) + bytes(16)
    header = b"VNCM" + struct.pack("<I", 1) + bytes(4)

    return header + zlib.compress(content + costmap.cells)
