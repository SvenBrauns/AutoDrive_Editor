"""One capture of the game picture: the editor asks the companion mod for tiles, converts each
tile the mod finishes and rebuilds the levels above as soon as all tiles below them are in."""

from concurrent.futures import Executor, Future, wait
from datetime import datetime
from pathlib import Path

from autodrive_editor.game import editor_link
from autodrive_editor.game.editor_link import CaptureResult
from autodrive_editor.i18n import tr
from autodrive_editor.terrain import game_picture
from autodrive_editor.terrain.game_picture import GamePicture, PictureGrid

# Seconds the game renders a tile, on top of the wait before it.
RENDER_SECONDS = 0.1
# Size of a 2000 px tile as WebP, all levels together.
TILE_MB = 0.35


def whole_map_tiles(grid: PictureGrid) -> list[tuple[int, int]]:
    """All level 0 tiles, row by row from the north-west corner."""

    side = grid.tiles_per_side()
    return [(col, row) for row in range(side) for col in range(side)]


def estimate(tile_count: int, wait_ms: int) -> tuple[float, float]:
    """Seconds and megabytes a capture of this many tiles takes."""

    seconds = editor_link.FIRST_WAIT_MS / 1000 + tile_count * (wait_ms / 1000 + RENDER_SECONDS)
    return seconds, tile_count * TILE_MB


class PictureCapture:
    def __init__(
        self,
        link: Path,
        picture: GamePicture,
        tiles: list[tuple[int, int]],
        executor: Executor,
        request_id: int,
    ):
        self.link = Path(link)
        self.picture = picture
        self.tiles = list(tiles)
        self.executor = executor
        self.request_id = request_id
        self.result: CaptureResult | None = None
        self.started: set[tuple[int, int]] = set()
        self.submitted: set[tuple[int, int, int]] = set()
        self.done: set[tuple[int, int, int]] = set()
        self.futures: list[Future] = []
        self.pending = self._pending_levels(set(self.tiles))

    @classmethod
    def start(cls, link, picture, tiles, executor, map_id: str, savegame: str, wait_ms: int):
        """Writes the request for the tiles and returns the running capture."""

        request_id = editor_link.new_request_id(datetime.now())
        grid = picture.grid
        editor_link.clean_up(link)
        editor_link.write_request(
            link,
            request_id,
            map_id,
            savegame,
            grid.m_per_px,
            game_picture.TILE_PX,
            wait_ms,
            [(col, row, *grid.tile_center(col, row)) for col, row in tiles],
        )
        return cls(link, picture, tiles, executor, request_id)

    @property
    def converted(self) -> int:
        return len(self._converted())

    @property
    def finished(self) -> bool:
        return self.result is not None and not self.futures

    def poll(self, now: datetime | None = None) -> list[tuple[int, int, int]]:
        """Collects finished work and starts new work. Returns the tiles (level, col, row)
        written since the last poll."""

        written = self._collect()

        if self.result is None:
            # The result first: once it exists, every tile the mod made is already listed.
            self.result = editor_link.read_result(self.link, self.request_id)

            for col, row, path, marker in editor_link.finished_tiles(self.link, self.request_id):
                if (col, row) not in self.started:
                    self.started.add((col, row))
                    self._submit(self._convert, col, row, path, marker)

            if self.result is None and not self._game_answers(now or datetime.now()):
                self.result = CaptureResult("error", tr("The game stopped answering."))

            if self.result is not None:
                self._close()

        if self.finished:
            editor_link.clean_up(self.link)

        return written

    def cancel(self):
        """Asks the mod to stop after the current tile; it answers with "cancelled"."""

        editor_link.write_cancel(self.link, self.request_id)

    def stop(self):
        """Cancels and finishes at once, without waiting for the mod: the tiles converted so far
        are kept and the levels above them rebuilt."""

        self.cancel()

        if self.result is None:
            self.result = CaptureResult("cancelled")
            self._close()

        while self.futures:
            wait(self.futures)
            self._collect()

    def _game_answers(self, now: datetime) -> bool:
        status = editor_link.read_status(self.link)
        return status is not None and status.is_fresh(now)

    def _converted(self) -> set[tuple[int, int]]:
        return {(col, row) for level, col, row in self.done if level == 0}

    def _close(self):
        """No more tiles come: the levels above wait only for the tiles already started."""

        self.pending = self._pending_levels(self.started)

        for level, col, row in sorted(self.done):
            self._start_parent(level, col, row)

    def _pending_levels(self, tiles: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
        """Per level the tiles this capture writes."""

        levels = [set(tiles)]

        for _ in range(self.picture.grid.top_level):
            levels.append({(col // 2, row // 2) for col, row in levels[-1]})

        return levels

    def _collect(self) -> list[tuple[int, int, int]]:
        written = []

        for future in [future for future in self.futures if future.done()]:
            self.futures.remove(future)
            level, col, row = future.result()

            if level == 0:
                self.picture.record_tile(col, row)

            self.done.add((level, col, row))
            written.append((level, col, row))
            self._start_parent(level, col, row)

        return written

    def _start_parent(self, level: int, col: int, row: int):
        """Builds the tile above once all its tiles of this capture are written."""

        if level >= self.picture.grid.top_level:
            return

        parent = (level + 1, col // 2, row // 2)
        children = [
            (level, c, r)
            for c in (2 * parent[1], 2 * parent[1] + 1)
            for r in (2 * parent[2], 2 * parent[2] + 1)
            if (c, r) in self.pending[level]
        ]

        if parent not in self.submitted and all(child in self.done for child in children):
            self.submitted.add(parent)
            self._submit(self._build, *parent)

    def _submit(self, function, *args):
        self.futures.append(self.executor.submit(function, *args))

    def _convert(self, col: int, row: int, path: Path, marker: Path):
        with editor_link.read_tile(path) as image:
            self.picture.save_tile(col, row, image)

        path.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
        return 0, col, row

    def _build(self, level: int, col: int, row: int):
        self.picture.build_tile(level, col, row)
        return level, col, row
