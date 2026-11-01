import os
from pathlib import Path

import pytest
from PIL import Image

from autodrive_editor.terrain import game_picture
from autodrive_editor.terrain.game_picture import (
    GamePicture,
    PictureGrid,
    find_picture,
    savegame_key,
)

RED, BLUE = (255, 0, 0), (0, 0, 255)


@pytest.fixture
def small_tiles(monkeypatch):
    """Tiles of 10 px on a 25 m map at 1 m/px: 3 × 3 tiles, the last column and row 5 px."""

    monkeypatch.setattr(game_picture, "TILE_PX", 10)
    return PictureGrid(25, 1.0)


def near(color, expected, tolerance=12):
    return all(abs(a - b) <= tolerance for a, b in zip(color, expected, strict=True))


def test_grid_of_a_16x_map():
    fine, coarse = PictureGrid(8192, 0.25), PictureGrid(8192, 0.5)

    assert (fine.edge, fine.tiles_per_side(), fine.top_level) == (500, 17, 5)
    assert [fine.tiles_per_side(level) for level in range(6)] == [17, 9, 5, 3, 2, 1]
    assert (coarse.edge, coarse.tiles_per_side(), coarse.top_level) == (1000, 9, 4)
    assert fine.tile_center(0, 0) == (-3846, -3846)
    assert coarse.tile_center(8, 0) == (4404, -3596)


def test_edge_tiles_are_cut_at_the_map_border():
    grid = PictureGrid(8192, 0.5)

    assert grid.tile_size(0, 8, 3) == (384, 2000)
    assert grid.tile_rect(0, 8, 8) == (3904, 3904, 192, 192)
    assert grid.tile_rect(1, 0, 0) == (-4096, -4096, 2000, 2000)


def test_level_follows_the_size_of_a_screen_pixel():
    grid = PictureGrid(8192, 0.25)

    assert grid.level_for(0.1) == 0
    assert grid.level_for(0.49) == 0
    assert grid.level_for(0.5) == 1
    assert grid.level_for(3.0) == 3
    assert grid.level_for(1000) == 5


def test_tiles_in_a_rectangle():
    grid = PictureGrid(8192, 0.5)

    assert grid.tiles_in(0, -4096, -4096, -3500, -3500) == [(0, 0)]
    assert grid.tiles_in(0, -3200, -4096, -2900, -3000) == [(0, 0), (1, 0), (0, 1), (1, 1)]
    assert grid.tiles_in(0, -9000, -9000, 9000, -4000) == [(col, 0) for col in range(9)]
    assert grid.tiles_in(4, -100, -100, 100, 100) == [(0, 0)]


def test_tile_at_a_world_point():
    grid = PictureGrid(8192, 0.5)

    assert grid.tile_at(-4096, -4096) == (0, 0)
    assert grid.tile_at(-3097, -3095) == (0, 1)
    assert grid.tile_at(4095, 4095) == (8, 8)
    assert grid.tile_at(4096, 0) is None
    assert grid.tile_at(0, -4097) is None


def test_added_tile_is_stored_cut_and_listed(small_tiles, tmp_path):
    picture = GamePicture.create(tmp_path / "1", small_tiles)
    picture.add_tile(2, 0, Image.new("RGBA", (10, 10), RED + (255,)), "2026-11-01T12:00:00")

    with Image.open(picture.tile_path(0, 2, 0)) as stored:
        assert (stored.size, stored.mode) == ((5, 10), "RGB")
        assert near(stored.getpixel((2, 2)), RED)

    opened = GamePicture.open(tmp_path / "1")
    assert opened.grid == small_tiles
    assert opened.captured == {(2, 0): "2026-11-01T12:00:00"}
    assert opened.has_tile(0, 2, 0) and opened.has_tile(1, 1, 0) and opened.has_tile(2, 0, 0)
    assert not opened.has_tile(0, 1, 0) and not opened.has_tile(1, 0, 0)


def test_levels_shrink_the_tiles_below(small_tiles, tmp_path):
    picture = GamePicture.create(tmp_path / "1", small_tiles)

    for col in range(3):
        for row in range(3):
            picture.add_tile(col, row, Image.new("RGB", (10, 10), RED if col < 2 else BLUE))

    picture.build_levels(set(picture.captured))

    with Image.open(picture.tile_path(1, 0, 0)) as tile:
        assert (tile.size, tile.mode) == ((10, 10), "RGB")
        assert near(tile.getpixel((5, 5)), RED)

    with Image.open(picture.tile_path(1, 1, 0)) as tile:
        assert tile.size == (3, 10)
        assert near(tile.getpixel((1, 1)), BLUE)

    with Image.open(picture.tile_path(2, 0, 0)) as tile:
        assert tile.size == (7, 7)
        assert near(tile.getpixel((1, 1)), RED) and near(tile.getpixel((6, 1)), BLUE, 60)


def test_levels_are_transparent_where_nothing_was_captured(small_tiles, tmp_path):
    picture = GamePicture.create(tmp_path / "1", small_tiles)
    picture.add_tile(0, 0, Image.new("RGB", (10, 10), RED))
    picture.build_levels({(0, 0)})

    with Image.open(picture.tile_path(1, 0, 0)) as tile:
        assert tile.mode == "RGBA"
        assert near(tile.getpixel((2, 2)), RED + (255,))
        assert tile.getpixel((8, 8))[3] == 0


def test_only_the_parents_of_changed_tiles_are_rebuilt(small_tiles, tmp_path):
    picture = GamePicture.create(tmp_path / "1", small_tiles)

    for col, row in [(0, 0), (2, 2)]:
        picture.add_tile(col, row, Image.new("RGB", (10, 10), RED))

    picture.build_levels({(0, 0), (2, 2)})
    untouched = picture.tile_path(1, 1, 1).stat().st_mtime_ns
    os.utime(picture.tile_path(1, 0, 0), ns=(0, 0))

    picture.add_tile(0, 0, Image.new("RGB", (10, 10), BLUE))
    picture.build_levels({(0, 0)})

    assert picture.tile_path(1, 1, 1).stat().st_mtime_ns == untouched
    with Image.open(picture.tile_path(1, 0, 0)) as tile:
        assert near(tile.getpixel((2, 2)), BLUE + (255,))


def test_create_replaces_the_old_picture(small_tiles, tmp_path):
    old = GamePicture.create(tmp_path / "1", PictureGrid(25, 0.5))
    old.add_tile(0, 0, Image.new("RGB", (10, 10), RED))

    new = GamePicture.create(tmp_path / "1", small_tiles)

    assert not old.tile_path(0, 0, 0).exists()
    assert GamePicture.open(tmp_path / "1").captured == {}
    assert new.grid.m_per_px == 1.0


def test_open_without_meta_finds_nothing(tmp_path):
    assert GamePicture.open(tmp_path / "1") is None


def test_picture_of_the_savegame_else_the_newest(tmp_path):
    root = tmp_path / game_picture.PICTURE_FOLDER

    for savegame, mtime in [("1", 100), ("2", 300), ("3", 200)]:
        GamePicture.create(root / savegame, PictureGrid(8192, 0.25))
        os.utime(root / savegame / game_picture.META_FILE, (mtime, mtime))

    assert find_picture(tmp_path, "3").directory.name == "3"
    assert find_picture(tmp_path, "7").directory.name == "2"
    assert find_picture(tmp_path, None).directory.name == "2"
    assert find_picture(tmp_path / "other", "1") is None


def test_savegame_key():
    assert savegame_key(Path("C:/games/savegame12")) == "12"
    assert savegame_key(Path("C:/games/backup")) is None
    assert savegame_key(None) is None
