import pytest

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.stations import StationOperation
from autodrive_editor.editing.station_layout import StationSettings, StopChoice
from autodrive_editor.editing.station_yard import plan_yard
from autodrive_editor.editing.yard_road import yard_road
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type
from autodrive_editor.selection.node_selection import NodeSelection

STOP = Stop("store.xml", "7", "Store", StopKind.SELL, ("WHEAT",), (100, 5, 200), 90.0, True)
SETTINGS = StationSettings(5, 5, 5, 0)


@pytest.fixture
def setup():
    data = AutoDriveData()
    data.add_node(NodeData(5, 0, 0, 0))
    selection = NodeSelection()
    edits = EditHistory()
    asked = []

    def ask(stops, autodrive_data):
        asked.append(stops)
        return [
            StopChoice(stop, "Store (Selling point)", "Selling points", 90) for stop in stops
        ], SETTINGS

    operation = StationOperation(EditContext(edits, lambda: data, node_selection=selection), ask)
    return data, selection, edits, operation, asked


def test_creates_lanes_and_markers_in_one_undo_step(setup):
    data, selection, edits, operation, asked = setup

    assert operation.create_for([STOP])
    assert asked == [[STOP]]

    assert sorted(data.nodes) == [5, 6, 7, 8]
    assert all(data.nodes[i].is_subprio for i in (6, 7, 8))
    assert get_connection_type(data.nodes[6], data.nodes[7]) == ConnectionType.REGULAR
    assert data.nodes[7].outgoing == {8} and data.nodes[7].incoming == {6}
    assert [(m.node_id, m.name, m.group) for m in data.markers.values()] == [
        (7, "Store (Selling point)", "Selling points")
    ]
    assert selection.selected_node_ids == set()

    edits.undo()

    assert list(data.nodes) == [5]
    assert not data.markers


def test_cancelled_dialog_or_no_stops_create_nothing(setup):
    data, selection, edits, operation, asked = setup

    assert not operation.create_for([])
    assert not asked

    operation.ask_choices = lambda stops, autodrive_data: None
    assert not operation.create_for([STOP])

    operation.ask_choices = lambda stops, autodrive_data: ([], SETTINGS)
    assert not operation.create_for([STOP])
    assert list(data.nodes) == [5]


def test_a_drawn_yard_road_is_created_with_the_lanes_in_one_undo_step(setup):
    data, selection, edits, operation, asked = setup
    plan = plan_yard(yard_road([(0, 10), (100, 10)], 6.0), [], SETTINGS, 6.0)
    lane = StopChoice(STOP, "Store", "Selling points", 90)
    operation.height_for_new_node = lambda *_: 3.0
    operation.ask_choices = lambda stops, autodrive_data: ([lane], SETTINGS, (plan, (5, None)))

    assert operation.create_for([STOP])

    road = [n for n in data.nodes.values() if n.z == 10]
    assert len(data.nodes) == 3 + len(plan.piece.points) and all(n.y == 3.0 for n in road)
    assert data.nodes[5].outgoing and len(data.markers) == 1

    edits.undo()
    assert list(data.nodes) == [5]
