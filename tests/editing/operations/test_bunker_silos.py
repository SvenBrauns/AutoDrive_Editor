from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.bunker_silos import BunkerSiloOperation
from autodrive_editor.editing.parking.bunker_silo import silo_settings
from autodrive_editor.file_io.savegame_sheds import IndoorArea
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.selection.node_selection import NodeSelection

# Two silos side by side, 11 m wide (2 lanes), open towards +z.
LEFT = IndoorArea("silo.xml", "1", ((0, 0), (11, 0), (11, 30), (0, 30)), 80.0, "Farm")
RIGHT = IndoorArea("silo.xml", "2", ((12, 0), (23, 0), (23, 30), (12, 30)), 80.0, "Farm")


def test_creates_the_lanes_of_all_picked_silos_in_one_undo_step():
    data = AutoDriveData()
    data.add_node(NodeData(1, 100, 0, 100))
    selection = NodeSelection()
    edits = EditHistory()
    asked = []

    def ask(areas, autodrive_data):
        asked.append(areas)
        return silo_settings(LEFT, None)

    operation = BunkerSiloOperation(
        EditContext(edits, lambda: data, node_selection=selection), ask_settings=ask
    )

    assert operation.create_for([LEFT, RIGHT])
    assert asked == [[LEFT, RIGHT]]
    assert sorted((m.group, m.name) for m in data.markers.values()) == [
        ("Farm-KS-A", "KS-A-1"),
        ("Farm-KS-A", "KS-A-2"),
        ("Farm-KS-B", "KS-B-1"),
        ("Farm-KS-B", "KS-B-2"),
    ]
    assert all(node.y == 80.0 for node_id, node in data.nodes.items() if node_id != 1)
    # The line ends are not selected.
    assert selection.selected_node_ids == set()

    edits.undo()

    assert list(data.nodes) == [1]


def test_nothing_happens_when_cancelled_or_nothing_is_picked():
    data = AutoDriveData()
    edits = EditHistory()
    operation = BunkerSiloOperation(EditContext(edits, lambda: data), lambda *args: None)

    assert not operation.create_for([LEFT])
    assert not operation.create_for([])
    assert data.nodes == {}
