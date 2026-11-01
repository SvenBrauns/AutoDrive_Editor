"""Files exchanged with the companion mod FS25_AutoDriveEditorLink (see its FORMAT.md).

    <game folder>\\modSettings\\FS25_AutoDriveEditorLink\\
        status.xml                   the mod, every second while a map is loaded
        request.xml                  the editor
        pictures_<id>\\tile_<col>_<row>.dds  + .done marker, the mod per tile
        result_<id>.xml              + result_<id>.done, the mod at the end
        cancel_<id>                  the editor
"""

import os
import re
import shutil
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

from autodrive_editor.i18n import tr

LINK_FOLDER = "FS25_AutoDriveEditorLink"
FORMAT = "1"
# The mod writes the status every second; an older one means the game is closed.
STATUS_MAX_AGE = 10
FIRST_WAIT_MS = 3000
ALTITUDE = 150
TILE_FILE = re.compile(r"tile_(\d+)_(\d+)\.done")
DDS_HEADER = 128
# Byte order of a 24-bit DDS by its red, green and blue masks.
DDS_ORDERS = {(0xFF, 0xFF00, 0xFF0000): "RGB", (0xFF0000, 0xFF00, 0xFF): "BGR"}


@dataclass(frozen=True)
class GameStatus:
    map_id: str
    savegame: str
    time: datetime

    def is_fresh(self, now: datetime) -> bool:
        return abs((now - self.time).total_seconds()) <= STATUS_MAX_AGE


@dataclass(frozen=True)
class CaptureResult:
    status: str
    message: str = ""


def link_directory(game_folder_path: Path) -> Path:
    return Path(game_folder_path) / "modSettings" / LINK_FOLDER


def read_status(directory: Path) -> GameStatus | None:
    """The game's status; None if there is none, it is half written or of another format."""

    try:
        root = ET.parse(Path(directory) / "status.xml").getroot()
        if root.get("format") != FORMAT:
            return None
        return GameStatus(
            root.get("map", ""),
            root.get("savegame", ""),
            datetime.fromisoformat(root.get("time", "")),
        )
    except (OSError, ET.ParseError, ValueError):
        return None


def new_request_id(now: datetime) -> int:
    """Month to second, e.g. 1101110720; new each second."""

    return int(now.strftime("%m%d%H%M%S"))


def write_request(
    directory: Path,
    request_id: int,
    map_id: str,
    savegame: str,
    m_per_px: float,
    tile_px: int,
    wait_ms: int,
    tiles: list[tuple[int, int, float, float]],
):
    """A picture request for the tiles (col, row, centre x, centre z), in the order given."""

    root = ET.Element(
        "request", format=FORMAT, id=str(request_id), type="pictures", map=map_id, savegame=savegame
    )
    pictures = ET.SubElement(
        root,
        "pictures",
        mPerPx=f"{m_per_px:g}",
        res=str(tile_px),
        mode="raw",
        altitude=str(ALTITUDE),
        waitMs=str(wait_ms),
        firstWaitMs=str(FIRST_WAIT_MS),
        dayTime="12",
        weather="SUN",
    )

    for col, row, x, z in tiles:
        ET.SubElement(pictures, "tile", col=str(col), row=str(row), x=f"{x:g}", z=f"{z:g}")

    _write_atomic(Path(directory) / "request.xml", ET.tostring(root, encoding="unicode"))


def pictures_directory(directory: Path, request_id: int) -> Path:
    return Path(directory) / f"pictures_{request_id}"


def finished_tiles(directory: Path, request_id: int) -> list[tuple[int, int, Path, Path]]:
    """Tiles the mod has finished: col, row, picture file and marker."""

    folder = pictures_directory(directory, request_id)

    if not folder.is_dir():
        return []

    tiles = []

    for marker in folder.glob("tile_*.done"):
        if match := TILE_FILE.fullmatch(marker.name):
            col, row = int(match.group(1)), int(match.group(2))
            tiles.append((col, row, marker.with_suffix(".dds"), marker))

    return sorted(tiles, key=lambda tile: (tile[1], tile[0]))


def read_tile(path: Path) -> Image.Image:
    """A tile picture. The mod's uncompressed 24-bit DDS is read directly: Pillow takes
    4.5 s for one of 2000², and blocks the editor meanwhile."""

    with open(path, "rb") as file:
        data = file.read()

    if data[:4] == b"DDS " and len(data) >= DDS_HEADER:
        height, width, pitch = struct.unpack_from("<3I", data, 12)
        bits, *masks = struct.unpack_from("<4I", data, 88)
        order = DDS_ORDERS.get(tuple(masks))
        pitch = pitch or width * 3

        if bits == 24 and order and len(data) >= DDS_HEADER + pitch * height:
            return Image.frombuffer(
                "RGB", (width, height), data[DDS_HEADER:], "raw", order, pitch, 1
            ).copy()

    return Image.open(path)


def read_result(directory: Path, request_id: int) -> CaptureResult | None:
    """The mod's answer once its marker is written; None before."""

    directory = Path(directory)

    if not (directory / f"result_{request_id}.done").is_file():
        return None

    try:
        root = ET.parse(directory / f"result_{request_id}.xml").getroot()
    except (OSError, ET.ParseError):
        return CaptureResult("error", tr("The game's answer could not be read."))

    if root.get("format") != FORMAT:
        return CaptureResult(
            "error", tr("The game mod has another version; please update the editor and the mod.")
        )

    return CaptureResult(root.get("status", "error"), root.get("message", ""))


def write_cancel(directory: Path, request_id: int):
    _write_atomic(Path(directory) / f"cancel_{request_id}", "")


def clean_up(directory: Path):
    """Deletes every exchanged file but the status: requests, answers, cancel files and tiles,
    also those left by earlier captures. The request goes too, or the mod would capture it
    again in the next game session once its answer is gone."""

    directory = Path(directory)

    if not directory.is_dir():
        return

    for path in directory.iterdir():
        if path.is_dir() and path.name.startswith("pictures_"):
            shutil.rmtree(path, ignore_errors=True)
        elif path.name.startswith(("request.xml", "result_", "cancel_")):
            path.unlink(missing_ok=True)


def _write_atomic(path: Path, text: str):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
