import pytest

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.stations import StationOperation
from autodrive_editor.editing.station_layout import StationSettings, StopChoice
from autodrive_editor.file_io.savegame_stations import Stop, StopKind
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type
from autodrive_editor.selection.node_selection import NodeSelection

STOP = Stop("store.xml", "7", "Store", StopKind.SELL, ("WHEAT",), (100, 5, 200), 90.0, True)
SETTINGS = StationSettings(5, 5, 5)


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
            StopChoice(stop, "Store (Selling point)", "Selling points") for stop in stops
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
    assert selection.selected_node_ids == {6, 8}

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
