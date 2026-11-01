import xml.etree.ElementTree as ET
from concurrent.futures import Executor, Future
from datetime import datetime

import pytest
from PIL import Image

from autodrive_editor.game import editor_link
from autodrive_editor.terrain import game_picture
from autodrive_editor.terrain.game_picture import GamePicture, PictureGrid
from autodrive_editor.terrain.picture_capture import PictureCapture, estimate, whole_map_tiles

MAP = "FS25_Thueringen_2_0_16x.SampleModMap"
NOW = datetime(2026, 11, 1, 14, 3, 22)
RED, BLUE = (255, 0, 0), (0, 0, 255)


class Immediate(Executor):
    def submit(self, function, *args):
        future = Future()
        future.set_result(function(*args))
        return future


@pytest.fixture
def link(tmp_path, monkeypatch):
    """The mod's folder with a fresh status; tiles of 10 px on a 25 m map at 1 m/px (3 × 3)."""

    monkeypatch.setattr(game_picture, "TILE_PX", 10)
    folder = tmp_path / "link"
    folder.mkdir()
    (folder / "status.xml").write_text(
        f'<status format="1" map="{MAP}" savegame="1" time="{NOW.isoformat()}"/>', encoding="utf-8"
    )
    return folder


@pytest.fixture
def picture(tmp_path, link):
    return GamePicture.create(tmp_path / "picture", PictureGrid(25, 1.0))


def start(link, picture, tiles=None):
    tiles = whole_map_tiles(picture.grid) if tiles is None else tiles
    return PictureCapture.start(link, picture, tiles, Immediate(), MAP, "1", 400)


def mod_tile(capture, col, row, color=RED):
    folder = editor_link.pictures_directory(capture.link, capture.request_id)
    folder.mkdir(exist_ok=True)
    Image.new("RGB", (10, 10), color).save(folder / f"tile_{col}_{row}.dds", "DDS")
    (folder / f"tile_{col}_{row}.done").write_bytes(b"")


def mod_result(capture, status="done"):
    name = f"result_{capture.request_id}"
    (capture.link / f"{name}.xml").write_text(
        f'<result format="1" status="{status}" message=""/>', encoding="utf-8"
    )
    (capture.link / f"{name}.done").write_bytes(b"")


def poll(capture, now=NOW):
    """Until nothing more happens: each poll collects the work the one before started."""

    written = capture.poll(now)
    while capture.futures:
        written += capture.poll(now)
    return written


def color(picture, level, col, row):
    with Image.open(picture.tile_path(level, col, row)) as image:
        return image.convert("RGB").getpixel((0, 0))


def near(color, expected, tolerance=12):
    return all(abs(a - b) <= tolerance for a, b in zip(color, expected, strict=True))


def test_tiles_of_the_whole_map_row_by_row():
    assert whole_map_tiles(PictureGrid(8192, 0.5))[:10] == [(c, 0) for c in range(9)] + [(0, 1)]


def test_estimate_of_a_16x_map():
    seconds, megabytes = estimate(289, 500)

    assert round(seconds) == 176
    assert round(megabytes) == 101


def test_start_writes_the_request(link, picture):
    (link / "result_16.xml").write_bytes(b"")
    capture = start(link, picture)
    root = ET.parse(link / "request.xml").getroot()

    assert root.get("id") == str(capture.request_id)
    assert not (link / "result_16.xml").exists()
    assert root.find("pictures").get("res") == "10"
    assert root.find("pictures").get("waitMs") == "400"
    assert len(root.find("pictures")) == 9
    assert root.find("pictures")[1].attrib == {"col": "1", "row": "0", "x": "2.5", "z": "-7.5"}


def test_finished_tiles_are_converted_and_levels_built_once_complete(link, picture):
    capture = start(link, picture)

    for col, row in [(0, 0), (1, 0), (2, 0), (0, 1)]:
        mod_tile(capture, col, row)

    assert sorted(poll(capture)) == [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 2, 0)]
    assert capture.converted == 4
    assert set(picture.captured) == {(0, 0), (1, 0), (2, 0), (0, 1)}
    assert not list(editor_link.pictures_directory(link, capture.request_id).iterdir())
    assert not picture.tile_path(1, 0, 0).exists()

    mod_tile(capture, 1, 1, BLUE)
    assert (1, 0, 0) in poll(capture)
    assert not picture.tile_path(2, 0, 0).exists()
    assert not capture.finished


def test_the_result_finishes_the_capture_and_cleans_up(link, picture):
    capture = start(link, picture)

    for col, row in whole_map_tiles(picture.grid):
        mod_tile(capture, col, row)
    mod_result(capture)

    poll(capture)

    assert capture.finished and capture.result.status == "done"
    assert capture.converted == 9
    assert near(color(picture, 2, 0, 0), RED)
    assert [path.name for path in link.iterdir()] == ["status.xml"]


def test_cancelled_capture_keeps_old_tiles_and_rebuilds_above_the_new(link, picture):
    for col, row in whole_map_tiles(picture.grid):
        picture.add_tile(col, row, Image.new("RGB", (10, 10), BLUE))
    picture.build_levels(set(picture.captured))

    capture = start(link, picture)
    mod_tile(capture, 0, 0)
    mod_result(capture, "cancelled")

    poll(capture)

    assert capture.finished and capture.result.status == "cancelled"
    assert capture.converted == 1
    assert near(color(picture, 0, 0, 0), RED)
    assert near(color(picture, 0, 1, 0), BLUE)
    assert near(color(picture, 1, 0, 0), RED)
    assert near(color(picture, 2, 0, 0), RED, tolerance=30)


def test_a_game_that_stops_answering_ends_the_capture(link, picture):
    capture = start(link, picture)
    mod_tile(capture, 0, 0)

    poll(capture, datetime(2026, 11, 1, 14, 4))

    assert capture.finished and capture.result.status == "error"
    assert capture.converted == 1


def test_stop_cancels_and_finishes_without_waiting_for_the_mod(link, picture):
    capture = start(link, picture)
    mod_tile(capture, 0, 0)
    capture.poll(NOW)

    capture.stop()

    assert (link / f"cancel_{capture.request_id}").is_file()
    assert capture.finished and capture.result.status == "cancelled"
    assert capture.converted == 1
    assert near(color(picture, 2, 0, 0), RED)
