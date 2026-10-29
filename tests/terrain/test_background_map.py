import pytest
from drawing_helpers import paint_scene
from PIL import Image
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.file_io.ground_map import Field
from autodrive_editor.rendering.items.field_outline_item import FieldOutlineItem
from autodrive_editor.terrain.background_map import BackgroundMap

FIELDS = [Field(1, [(-500, -500), (500, -500), (500, 500)])]


@pytest.fixture
def background(qapp, tmp_path):
    Image.new("RGB", (64, 64), (0, 0, 255)).save(tmp_path / "overview.png")
    Image.new("RGB", (128, 128), (0, 255, 0)).save(tmp_path / "ground.png")

    background = BackgroundMap(QGraphicsScene(), map_scale=2)
    background.load(str(tmp_path / "overview.png"))
    return background


def shown_color(background, x=0, z=0):
    pixmap = background.background_item.pixmap()
    point = background.background_item.mapFromScene(x, z)
    return QColor(pixmap.toImage().pixel(int(point.x()), int(point.y()))).getRgb()[:3]


def field_items(background):
    return [item for item in background.scene.items() if isinstance(item, FieldOutlineItem)]


def test_ground_map_is_shown_with_its_fields_only_when_switched_on(background, tmp_path):
    background.set_ground(tmp_path / "ground.png", FIELDS)
    assert shown_color(background) == (0, 0, 255)
    assert field_items(background) == []

    background.set_ground_visible(True)
    assert shown_color(background) == (0, 255, 0)
    assert len(field_items(background)) == 1

    background.set_ground_visible(False)
    assert shown_color(background) == (0, 0, 255)
    assert field_items(background) == []


def test_both_images_cover_the_whole_map(background, tmp_path):
    overview_rect = background.background_item.sceneBoundingRect()

    background.set_ground_visible(True)
    background.set_ground(tmp_path / "ground.png", FIELDS)

    assert background.background_item.sceneBoundingRect() == overview_rect
    assert overview_rect.width() == 4096 and overview_rect.left() == -2048


def test_a_new_background_drops_the_ground_map(background, tmp_path):
    background.set_ground_visible(True)
    background.set_ground(tmp_path / "ground.png", FIELDS)

    background.load(str(tmp_path / "overview.png"))

    assert not background.showing_ground()
    assert shown_color(background) == (0, 0, 255)
    assert field_items(background) == []


def test_restore_after_clearing_the_scene_keeps_the_ground_map(background, tmp_path):
    background.set_ground_visible(True)
    background.set_ground(tmp_path / "ground.png", FIELDS)

    background.remove_from_scene()
    background.scene.clear()
    background.restore()

    assert shown_color(background) == (0, 255, 0)
    assert len(field_items(background)) == 1


def test_field_outline_is_drawn(qapp):
    scene = QGraphicsScene()
    scene.addItem(FieldOutlineItem([Field(7, [(0, 0), (100, 0), (100, 100), (0, 100)])]))

    painted = paint_scene(scene, center=(50, 50), scale=1)

    # Antialiasing blends the thin line with the white image.
    assert QColor(painted.color_at(100, 70)).blue() < 200
    assert painted.color_at(50, 70) == "#ffffff"
