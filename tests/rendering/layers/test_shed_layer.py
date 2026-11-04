from dataclasses import replace

import pytest
from drawing_helpers import paint_scene
from PySide6.QtGui import QColor, QPainterPath
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.file_io.savegame_buildings import (
    BuildingGroup,
    BuildingType,
    SavegameBuildings,
)
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.paths import MARKER_ICON_PATH
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.rendering.visibility import Visibility

# Far away from the only node.
AREA = IndoorArea("shed.xml", "a", ((500, 500), (530, 500), (530, 515), (500, 515)), 80.0)
SHED = BuildingType("shed.xml", "Shed", "sheds", BuildingGroup.SHEDS, 1)


def buildings(group=BuildingGroup.SHEDS):
    return SavegameBuildings(types=[replace(SHED, group=group)], areas=[AREA])


@pytest.fixture
def renderer(qapp):
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))
    renderer = SceneRenderer(QGraphicsScene(), MARKER_ICON_PATH)
    renderer.render(data)
    renderer.set_buildings(buildings())
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

    assert renderer.buildings.areas == []
    assert renderer.shed_layer.polygons == []


def test_shed_is_found_inside_its_outline_while_shown(renderer):
    assert renderer.get_shed_at(510, 505) == AREA
    assert renderer.get_shed_at(540, 505) is None

    renderer.set_visibility(Visibility(sheds=False))

    assert renderer.get_shed_at(510, 505) is None


def test_hidden_type_is_neither_drawn_nor_found(renderer):
    renderer.set_building_types({}, {"shed.xml"})

    assert renderer.shed_layer.polygons == []
    assert renderer.get_shed_at(510, 505) is None
    # Kept, so the type can be shown again.
    assert renderer.buildings.areas == [AREA]

    renderer.set_building_types({}, set())

    assert renderer.get_shed_at(510, 505) == AREA


def test_hidden_types_stay_hidden_for_the_next_route(renderer):
    renderer.set_building_types({}, {"shed.xml"})
    renderer.render(AutoDriveData())
    renderer.set_buildings(buildings())

    assert renderer.shed_layer.polygons == []


def test_only_types_of_the_sheds_group_are_sheds(renderer):
    renderer.set_buildings(buildings(BuildingGroup.STATIONS))

    assert renderer.shed_layer.polygons == []
    assert renderer.group_of("shed.xml") == BuildingGroup.STATIONS

    renderer.set_building_types({"shed.xml": BuildingGroup.SHEDS}, set())

    assert renderer.get_shed_at(510, 505) == AREA
    assert renderer.group_of("shed.xml") == BuildingGroup.SHEDS
    assert renderer.group_of("unknown.xml") == BuildingGroup.OTHER


SILO = IndoorArea("silo.xml", "s", ((600, 500), (620, 500), (620, 530), (600, 530)), 80.0)


@pytest.fixture
def silo_renderer(renderer):
    silo_type = BuildingType("silo.xml", "Silo", "silos", BuildingGroup.BUNKER_SILOS, 1)
    renderer.set_buildings(SavegameBuildings(types=[SHED, silo_type], areas=[AREA], silos=[SILO]))
    return renderer


def test_silos_are_drawn_and_found_apart_from_the_sheds(silo_renderer):
    assert len(silo_renderer.silo_layer.polygons) == 1
    assert silo_renderer.get_silo_at(610, 515) == SILO
    assert silo_renderer.get_silo_at(510, 505) is None
    assert silo_renderer.get_shed_at(610, 515) is None

    silo_renderer.set_visibility(Visibility(silos=False))

    assert silo_renderer.get_silo_at(610, 515) is None
    assert silo_renderer.get_shed_at(510, 505) == AREA


def test_box_picks_the_silos_with_their_centre_inside(silo_renderer):
    path = QPainterPath()
    path.addRect(590, 505, 40, 20)

    assert silo_renderer.get_silos_in_path(path) == [SILO]

    path = QPainterPath()
    path.addRect(590, 490, 40, 20)

    assert silo_renderer.get_silos_in_path(path) == []


def test_picked_silos_are_filled_stronger(silo_renderer):
    def fill():
        return QColor(paint_scene(silo_renderer.scene, (610, 515), scale=4.0).color_at(610, 515))

    plain = fill()
    silo_renderer.set_picked_silos([SILO])

    assert fill().red() < plain.red() - 50
