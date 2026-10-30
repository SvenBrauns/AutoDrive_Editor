import pytest
from costmap_helpers import make_costmap
from drawing_helpers import paint_scene
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.paths import MARKER_ICON_PATH
from autodrive_editor.rendering.layers.drivability_layer import cell_color
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.rendering.visibility import Visibility

# Blocked square around (20, 20) on a road map.
COSTMAP = make_costmap(blocked=[(15, 15, 25, 25)])


@pytest.fixture
def renderer(qapp):
    renderer = SceneRenderer(QGraphicsScene(), MARKER_ICON_PATH)
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))
    renderer.render(data)
    renderer.set_costmap(COSTMAP)
    return renderer


def is_red(renderer, x, z, scale):
    pixel = QColor(paint_scene(renderer.scene, (20, 20), scale=scale).color_at(x, z))

    return pixel.red() > 200 and pixel.green() < 150 and pixel.blue() < 150


@pytest.mark.parametrize("shown", [True, False])
def test_blocked_cells_are_drawn_when_shown(renderer, shown):
    renderer.set_visibility(Visibility(drivability=shown))

    assert is_red(renderer, 20, 20, scale=4.0) == shown
    assert not is_red(renderer, 10, 20, scale=4.0)


def test_zoomed_out_the_smaller_image_is_drawn(renderer):
    # Large enough for the image with every 16th cell.
    renderer.set_costmap(make_costmap(blocked=[(0, 0, 40, 40)]))
    renderer.set_visibility(Visibility(drivability=True))

    assert is_red(renderer, 20, 20, scale=0.3)


def test_layer_covers_the_whole_map(renderer):
    assert renderer.drivability_layer.boundingRect().width() == COSTMAP.width


def test_new_data_clears_the_map_like_the_buildings(renderer):
    renderer.render(AutoDriveData())

    assert renderer.drivability_layer.costmap is None


def test_roads_are_clear_and_blocked_cells_are_strong():
    assert QColor.fromRgba(cell_color(51)).alpha() == 0
    assert QColor.fromRgba(cell_color(255)).alpha() > 150
