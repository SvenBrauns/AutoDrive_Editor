import pytest
from drawing_helpers import paint_scene
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene

from autodrive_editor.file_io.savegame_buildings import (
    BuildingGroup,
    BuildingType,
    SavegameBuildings,
)
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.paths import MARKER_ICON_PATH
from autodrive_editor.rendering.scene_renderer import SceneRenderer
from autodrive_editor.rendering.visibility import Visibility

# Far away from the only node, pointing right.
STOP = Stop("mill.xml", "a", "Mill", StopKind.SELL, ("WHEAT",), (500, 80, 500), 90.0, True)
MILL = BuildingType("mill.xml", "Mill", "", BuildingGroup.STATIONS, 1)


@pytest.fixture
def renderer(qapp):
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))
    renderer = SceneRenderer(QGraphicsScene(), MARKER_ICON_PATH)
    renderer.render(data)
    renderer.set_buildings(SavegameBuildings(types=[MILL], stops=[STOP]))
    return renderer


def is_yellow(renderer, x, z):
    painted = paint_scene(renderer.scene, (500, 500), scale=4.0)
    pixel = QColor(painted.color_at(x, z))

    return pixel.red() > 200 and pixel.green() > 150 and pixel.blue() < 100


def test_layer_covers_the_stops_outside_the_network(renderer):
    assert renderer.station_layer.boundingRect().contains(500, 500)


@pytest.mark.parametrize("stations", [True, False])
def test_arrow_is_drawn_unless_hidden(renderer, stations):
    renderer.set_visibility(Visibility(stations=stations))

    # Behind the tip of the arrow pointing right, inside it.
    assert is_yellow(renderer, 499, 500) == stations


def test_arrow_points_along_the_heading(renderer):
    # Beside the tip (right) the arrow is narrow, beside its back (left) it is wide.
    assert not is_yellow(renderer, 502, 501.2)
    assert is_yellow(renderer, 498, 501.2)


def test_hidden_types_and_types_of_other_groups_are_not_drawn(renderer):
    renderer.set_building_types({}, {"mill.xml"})
    assert renderer.station_layer.stops == []

    renderer.set_building_types({"mill.xml": BuildingGroup.OTHER}, set())
    assert renderer.station_layer.stops == []

    renderer.set_building_types({}, set())
    assert renderer.shown_stops == [STOP]


def test_new_route_clears_the_stops(renderer):
    renderer.render(AutoDriveData())

    assert renderer.station_layer.stops == []


def test_arrow_shows_the_default_lane_heading(renderer):
    # West of its building and heading up: circling counterclockwise turns it down the map.
    stop = Stop("mill.xml", "a", "Mill", StopKind.SELL, (), (500, 80, 500), 0.0, True, (600, 500))
    renderer.set_buildings(SavegameBuildings(types=[MILL], stops=[stop]))

    assert renderer.stop_headings[stop] == 180
    assert not is_yellow(renderer, 501.2, 502)
    assert is_yellow(renderer, 501.2, 498)
