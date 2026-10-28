import pytest
from PySide6.QtCore import QPoint

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.parking_spots import ParkingSpotOperation
from autodrive_editor.editing.parking_layout import ParkingSettings
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.autodrive_data import AutoDriveData, MarkerGroup, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type
from autodrive_editor.selection.node_selection import NodeSelection

SHED = IndoorArea("shed.xml", "1", ((-15, -7.5), (15, -7.5), (15, 7.5), (-15, 7.5)), 90.0)
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
        EditContext(edits, lambda: data, node_selection=selection),
        shed_at=lambda view_position: SHED if view_position == QPoint(1, 1) else None,
        ask_settings=ask,
    )
    return data, selection, edits, operation, asked


def test_creates_the_network_in_one_undo_step(setup):
    data, selection, edits, operation, asked = setup

    assert operation.create_at(QPoint(1, 1))
    assert asked == [SHED]

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

    # The four open line ends are selected.
    assert len(selection.selected_node_ids) == 4
    assert all(
        len(data.nodes[i].incoming | data.nodes[i].outgoing) == 1
        for i in selection.selected_node_ids
    )

    edits.undo()

    assert list(data.nodes) == [5]
    assert not data.markers
    assert [group.name for group in data.marker_groups] == ["All"]


def test_click_beside_a_shed_does_nothing(setup):
    data, selection, edits, operation, asked = setup

    assert not operation.create_at(QPoint(50, 50))
    assert not asked
    assert list(data.nodes) == [5]


def test_cancelled_dialog_creates_nothing(setup):
    data, selection, edits, operation, asked = setup
    operation.ask_settings = lambda area, autodrive_data: None

    assert not operation.create_at(QPoint(1, 1))
    assert list(data.nodes) == [5]
