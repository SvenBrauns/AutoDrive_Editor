import pytest
from drawing_helpers import paint_scene
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.paths import MARKER_ICON_PATH
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.rendering.visibility import Visibility

# Far away from the only node.
AREA = IndoorArea("shed.xml", "a", ((500, 500), (530, 500), (530, 515), (500, 515)), 80.0)


@pytest.fixture
def renderer(qapp):
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))
    renderer = SceneRenderer(QGraphicsScene(), MARKER_ICON_PATH)
    renderer.render(data)
    renderer.set_shed_areas([AREA])
    return renderer


def test_layer_covers_the_sheds_outside_the_network(renderer):
    bounds = renderer.shed_layer.boundingRect()

    assert bounds.contains(500, 500) and bounds.contains(530, 515)


@pytest.mark.parametrize("sheds", [True, False])
def test_outline_is_drawn_unless_hidden(renderer, sheds):
    renderer.set_visibility(Visibility(sheds=sheds))

    painted = paint_scene(renderer.scene, (500, 507), scale=4.0)
    pixel = QColor(painted.color_at(500, 507))

    # The outline is magenta: less green than the white background.
    assert (pixel.green() < 150) == sheds


def test_new_route_clears_the_sheds(renderer):
    renderer.render(AutoDriveData())

    assert renderer.shed_areas == []
    assert renderer.shed_layer.polygons == []


def test_shed_is_found_inside_its_outline_while_shown(renderer):
    assert renderer.get_shed_at(510, 505) == AREA
    assert renderer.get_shed_at(540, 505) is None

    renderer.set_visibility(Visibility(sheds=False))

    assert renderer.get_shed_at(510, 505) is None
