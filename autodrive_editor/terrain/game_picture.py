"""The game picture: the map as the game renders it from above, captured by the companion mod
in square tiles and kept in the map cache, one picture per savegame.

    <map folder>\\game_picture\\<savegame>\\
        meta.json        map size, metres per pixel, capture date of each tile
        0\\<col>_<row>.webp   tiles as captured, cut at the map border
        1\\…                  2×2 tiles of the level below shrunk into one, up to one tile

The grid starts at the map's north-west corner; a tile holds TILE_PX pixels per side.
"""

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

PICTURE_FOLDER = "game_picture"
META_FILE = "meta.json"
TILE_PX = 2000
WEBP_QUALITY = 85
# Encoder effort 0–6: 2 is four times faster than the default 4, files 2 % bigger.
WEBP_METHOD = 2


@dataclass(frozen=True)
class PictureGrid:
    map_size: float
    m_per_px: float

    @property
    def map_px(self) -> int:
        return round(self.map_size / self.m_per_px)

    @property
    def edge(self) -> float:
        """Edge of a level 0 tile in metres."""

        return TILE_PX * self.m_per_px

    def level_px(self, level: int) -> int:
        """Pixels across the whole map at this level."""

        return math.ceil(self.map_px / 2**level)

    def tiles_per_side(self, level: int = 0) -> int:
        return math.ceil(self.level_px(level) / TILE_PX)

    @property
    def top_level(self) -> int:
        """The level where one tile holds the whole map."""

        level = 0

        while self.tiles_per_side(level) > 1:
            level += 1

        return level

    def tile_center(self, col: int, row: int) -> tuple[float, float]:
        """World x, z of a level 0 tile's centre, where the game camera looks."""

        start = -self.map_size / 2
        return start + (col + 0.5) * self.edge, start + (row + 0.5) * self.edge

    def tile_size(self, level: int, col: int, row: int) -> tuple[int, int]:
        """Pixel size of a tile, smaller at the map's east and south border."""

        px = self.level_px(level)
        return min(TILE_PX, px - col * TILE_PX), min(TILE_PX, px - row * TILE_PX)

    def tile_rect(self, level: int, col: int, row: int) -> tuple[float, float, float, float]:
        """Left, top, width and height of a tile in world metres."""

        m_per_px = self.m_per_px * 2**level
        width, height = self.tile_size(level, col, row)
        start = -self.map_size / 2

        return (
            start + col * TILE_PX * m_per_px,
            start + row * TILE_PX * m_per_px,
            width * m_per_px,
            height * m_per_px,
        )

    def level_for(self, m_per_screen_px: float) -> int:
        """The coarsest level whose pixels are still no bigger than a screen pixel."""

        if m_per_screen_px <= self.m_per_px:
            return 0

        return min(self.top_level, int(math.log2(m_per_screen_px / self.m_per_px)))

    def tiles_in(self, level: int, left: float, top: float, right: float, bottom: float):
        """Columns and rows of the tiles of a level that touch the world rectangle."""

        tile_m = TILE_PX * self.m_per_px * 2**level
        last = self.tiles_per_side(level) - 1
        start = -self.map_size / 2

        def span(low, high):
            first = max(0, math.floor((low - start) / tile_m))
            return range(first, min(last, math.floor((high - start) / tile_m)) + 1)

        return [(col, row) for row in span(top, bottom) for col in span(left, right)]


class GamePicture:
    def __init__(self, directory: Path, grid: PictureGrid, captured: dict[tuple[int, int], str]):
        self.directory = Path(directory)
        self.grid = grid
        self.captured = dict(captured)

    @classmethod
    def create(cls, directory: Path, grid: PictureGrid) -> "GamePicture":
        """A new, empty picture; replaces one stored there before."""

        directory = Path(directory)

        if directory.is_dir():
            for path in directory.glob("*/*.webp"):
                path.unlink()

        directory.mkdir(parents=True, exist_ok=True)
        picture = cls(directory, grid, {})
        picture._write_meta()

        return picture

    @classmethod
    def open_or_create(cls, directory: Path, grid: PictureGrid) -> "GamePicture":
        """The picture stored there if it has this grid, otherwise a new one."""

        picture = cls.open(directory)
        return (
            picture if picture is not None and picture.grid == grid else cls.create(directory, grid)
        )

    @classmethod
    def open(cls, directory: Path) -> "GamePicture | None":
        try:
            meta = json.loads((Path(directory) / META_FILE).read_text(encoding="utf-8"))
            grid = PictureGrid(float(meta["map_size"]), float(meta["m_per_px"]))
            captured = {
                tuple(int(part) for part in key.split("_")): info["captured"]
                for key, info in meta["tiles"].items()
            }
        except (OSError, ValueError, KeyError, TypeError):
            return None

        return cls(directory, grid, captured)

    def tile_path(self, level: int, col: int, row: int) -> Path:
        return self.directory / str(level) / f"{col}_{row}.webp"

    def has_tile(self, level: int, col: int, row: int) -> bool:
        """Whether a tile of this level covers at least one captured tile."""

        span = 2**level

        return any(
            (c, r) in self.captured
            for c in range(col * span, (col + 1) * span)
            for r in range(row * span, (row + 1) * span)
        )

    def add_tile(self, col: int, row: int, image: Image.Image, captured: str | None = None):
        """Stores a captured tile, cut at the map border. The levels above are not rebuilt;
        call build_levels with all added tiles."""

        self.save_tile(col, row, image)
        self.record_tile(col, row, captured)

    def save_tile(self, col: int, row: int, image: Image.Image):
        """Writes the tile's file only; may run in a worker thread. record_tile adds it."""

        width, height = self.grid.tile_size(0, col, row)
        path = self.tile_path(0, col, row)
        path.parent.mkdir(exist_ok=True)

        image.crop((0, 0, width, height)).convert("RGB").save(
            path, quality=WEBP_QUALITY, method=WEBP_METHOD
        )

    def record_tile(self, col: int, row: int, captured: str | None = None):
        self.captured[(col, row)] = captured or datetime.now().isoformat(timespec="seconds")
        self._write_meta()

    def build_levels(self, changed: set[tuple[int, int]]):
        """Rebuilds the tiles of all levels above the changed level 0 tiles."""

        for level in range(1, self.grid.top_level + 1):
            changed = {(col // 2, row // 2) for col, row in changed}

            for col, row in changed:
                self.build_tile(level, col, row)

    def build_tile(self, level: int, col: int, row: int):
        """One tile from the 2×2 tiles below it; transparent where none was captured."""

        below = level - 1
        px = self.grid.level_px(below)
        width = min(2 * TILE_PX, px - col * 2 * TILE_PX)
        height = min(2 * TILE_PX, px - row * 2 * TILE_PX)
        children = [
            (dc * TILE_PX, dr * TILE_PX, self.tile_path(below, col * 2 + dc, row * 2 + dr))
            for dr in (0, 1)
            for dc in (0, 1)
            if dc * TILE_PX < width and dr * TILE_PX < height
        ]
        images = [(x, y, Image.open(path)) for x, y, path in children if path.is_file()]
        complete = len(images) == len(children) and all(i.mode == "RGB" for *_, i in images)
        canvas = Image.new("RGB" if complete else "RGBA", (width, height))

        for x, y, image in images:
            with image:
                canvas.paste(image.convert(canvas.mode), (x, y))

        # Halves an odd size rounded up, like level_px.
        tile = canvas.reduce(2)

        path = self.tile_path(level, col, row)
        path.parent.mkdir(exist_ok=True)
        tile.save(path, quality=WEBP_QUALITY, method=WEBP_METHOD)

    def _write_meta(self):
        meta = {
            "format": 1,
            "map_size": self.grid.map_size,
            "m_per_px": self.grid.m_per_px,
            "tiles": {f"{c}_{r}": {"captured": date} for (c, r), date in self.captured.items()},
        }
        (self.directory / META_FILE).write_text(json.dumps(meta, indent=1), encoding="utf-8")


def savegame_key(savegame_directory: Path | None) -> str | None:
    """ "1" for a folder savegame1, as the game's status file names it."""

    if savegame_directory is None:
        return None

    match = re.fullmatch(r"savegame(\d+)", Path(savegame_directory).name)
    return match.group(1) if match else None


def find_picture(map_directory: Path, savegame: str | None) -> GamePicture | None:
    """The picture of the savegame, otherwise the newest one of the map."""

    root = Path(map_directory) / PICTURE_FOLDER

    if savegame is not None and (picture := GamePicture.open(root / savegame)) is not None:
        return picture

    if not root.is_dir():
        return None

    metas = sorted(root.glob(f"*/{META_FILE}"), key=lambda path: path.stat().st_mtime)

    for meta in reversed(metas):
        if (picture := GamePicture.open(meta.parent)) is not None:
            return picture

    return None
