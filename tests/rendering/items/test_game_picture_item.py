import time

import pytest
from drawing_helpers import paint_scene
from PIL import Image
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.rendering.items import game_picture_item
from autodrive_editor.rendering.items.game_picture_item import GamePictureItem
from autodrive_editor.terrain import game_picture
from autodrive_editor.terrain.game_picture import GamePicture, PictureGrid

RED, BLUE, WHITE = "#ff0000", "#0000ff", "#ffffff"


@pytest.fixture
def scene(qapp, monkeypatch, tmp_path):
    """A 25 m map at 1 m/px in 10 px tiles: red in the north-west tile, blue in the middle one,
    nothing captured elsewhere."""

    monkeypatch.setattr(game_picture, "TILE_PX", 10)
    picture = GamePicture.create(tmp_path, PictureGrid(25, 1.0))
    picture.add_tile(0, 0, Image.new("RGB", (10, 10), (255, 0, 0)))
    picture.add_tile(1, 1, Image.new("RGB", (10, 10), (0, 0, 255)))
    picture.build_levels(set(picture.captured))

    scene = QGraphicsScene()
    scene.item = GamePictureItem(picture)
    scene.addItem(scene.item)
    yield scene
    scene.item.close()


def wait_loaded(qapp, item):
    deadline = time.monotonic() + 5

    while item.loading and time.monotonic() < deadline:
        qapp.processEvents()


def near(color, expected, tolerance=20):
    return all(
        abs(int(color[i : i + 2], 16) - int(expected[i : i + 2], 16)) < tolerance for i in (1, 3, 5)
    )


def test_tiles_are_drawn_once_loaded(qapp, scene):
    assert paint_scene(scene, (0, 0), scale=4).color_at(-7.5, -7.5) == WHITE

    wait_loaded(qapp, scene.item)
    painted = paint_scene(scene, (0, 0), scale=4)

    assert near(painted.color_at(-7.5, -7.5), RED)
    assert near(painted.color_at(2.5, 2.5), BLUE)
    assert painted.color_at(2.5, -7.5) == WHITE
    assert {level for level, _, _ in scene.item.pixmaps} == {0}


def test_only_tiles_in_view_are_loaded(qapp, scene):
    paint_scene(scene, (-7.5, -7.5), scale=10, size=40)
    wait_loaded(qapp, scene.item)

    assert set(scene.item.pixmaps) == {(0, 0, 0)}


def test_zoomed_out_uses_a_coarser_level(qapp, scene):
    paint_scene(scene, (0, 0), scale=0.25)
    wait_loaded(qapp, scene.item)

    assert set(scene.item.pixmaps) == {(2, 0, 0)}


def test_coarser_level_shows_while_the_tile_loads(qapp, scene):
    paint_scene(scene, (0, 0), scale=0.25)
    wait_loaded(qapp, scene.item)

    painted = paint_scene(scene, (0, 0), scale=4)

    assert (0, 0, 0) in scene.item.loading
    # The coarse tile is only 7 px; smoothing blends it a little.
    assert near(painted.color_at(-7.5, -7.5), RED, tolerance=40)


def test_only_some_tiles_stay_cached(qapp, scene, monkeypatch):
    monkeypatch.setattr(game_picture_item, "CACHED_TILES", 1)

    paint_scene(scene, (0, 0), scale=4)
    wait_loaded(qapp, scene.item)

    assert len(scene.item.pixmaps) == 1
