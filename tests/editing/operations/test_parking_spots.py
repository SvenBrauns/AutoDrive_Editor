import pytest

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.parking_spots import ParkingSpotOperation
from autodrive_editor.editing.parking_layout import ParkingSettings
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerGroup, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type
from autodrive_editor.selection.node_selection import NodeSelection

SHED = IndoorArea("shed.xml", "1", ((-15, -7.5), (15, -7.5), (15, 7.5), (-15, 7.5)), 90.0)
NEXT = IndoorArea("shed.xml", "2", ((16, -7.5), (46, -7.5), (46, 7.5), (16, 7.5)), 90.0)
OTHER = IndoorArea("barn.xml", "3", ((16, -7.5), (46, -7.5), (46, 7.5), (16, 7.5)), 90.0)
SETTINGS = ParkingSettings(bays=2, gaps=(0.0,), marker_name="Shed", start_number=1, group="Farm")


@pytest.fixture
def setup():
    data = AutoDriveData()
    data.add_node(NodeData(5, 100, 0, 100))
    data.marker_groups.append(MarkerGroup("All", 1))
    selection = NodeSelection()
    edits = EditHistory()
    asked = []

    def ask(area, autodrive_data):
        asked.append(area)
        return SETTINGS

    operation = ParkingSpotOperation(
        EditContext(edits, lambda: data, node_selection=selection), ask_settings=ask
    )
    return data, selection, edits, operation, asked


def test_creates_the_network_in_one_undo_step(setup):
    data, selection, edits, operation, asked = setup

    assert operation.create_for([SHED])
    assert asked == [[SHED]]

    new_nodes = [node for node_id, node in data.nodes.items() if node_id != 5]
    assert min(node.node_id for node in new_nodes) == 6
    assert all(node.is_subprio and node.y == 90.0 for node in new_nodes)
    assert [(m.name, m.group) for m in data.markers.values()] == [
        ("Shed 1", "Farm"),
        ("Shed 2", "Farm"),
    ]
    assert data.find_marker_group("Farm") is not None

    marker = data.nodes[next(iter(data.markers))]
    neighbour = data.nodes[next(iter(marker.outgoing))]
    assert get_connection_type(marker, neighbour) == ConnectionType.DUAL

    # The line ends are not selected.
    assert selection.selected_node_ids == set()

    edits.undo()

    assert list(data.nodes) == [5]
    assert not data.markers
    assert [group.name for group in data.marker_groups] == ["All"]


def test_numbers_run_on_across_sheds(setup):
    data, selection, edits, operation, asked = setup

    assert operation.create_for([SHED, NEXT])
    assert [m.name for m in data.markers.values()] == [f"Shed {n}" for n in range(1, 5)]


def test_sheds_of_different_types_are_refused(setup):
    data, selection, edits, operation, asked = setup
    messages = []
    operation.status_changed.connect(messages.append)

    assert not operation.create_for([SHED, OTHER])
    assert not asked
    assert list(data.nodes) == [5]
    assert "different types" in messages[0]


def test_cancelled_dialog_creates_nothing(setup):
    data, selection, edits, operation, asked = setup
    operation.ask_settings = lambda area, autodrive_data: None

    assert not operation.create_for([SHED])
    assert list(data.nodes) == [5]
