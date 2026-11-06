from pathlib import Path

from road_lane_helpers import junction, lane

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.operations.road_network import (
    RoadLanes,
    RoadNetworkOperation,
    RoadSettings,
)
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    write_connection_state,
)

SAVEGAME = Path("savegame1")
ROAD = [lane((0, 2), (100, 2)), lane((100, -2), (0, -2))]


def run_now(title, work):
    return work(lambda done, total, text: None, lambda: False)


def operation(data, lanes=ROAD, savegame=SAVEGAME, edits=None):
    reads = []

    def read(folder):
        reads.append(folder)
        return lanes

    result = RoadNetworkOperation(
        EditContext(edits or EditHistory(), lambda: data),
        savegame_provider=lambda: savegame,
        read_lanes=read,
        costmap_provider=lambda: None,
        gap_provider=lambda: 5.5,
        run=run_now,
    )
    result.reads = reads
    return result


def test_reads_the_lanes_once_per_savegame():
    roads = operation(AutoDriveData())
    shown = []
    roads.lanes_changed.connect(shown.append)

    assert roads.prepare() and roads.prepare()
    assert roads.reads == [SAVEGAME]
    assert shown == [ROAD]


def test_needs_a_savegame_with_traffic_lanes():
    statuses = []
    without_savegame = operation(AutoDriveData(), savegame=None)
    without_savegame.status_changed.connect(statuses.append)
    without_lanes = operation(AutoDriveData(), lanes=[])

    assert not without_savegame.prepare()
    assert "open a savegame" in statuses[0]
    assert not without_lanes.prepare()
    assert not without_lanes.create()


def test_creates_the_whole_map_in_one_undo_step():
    data = AutoDriveData()
    edits = EditHistory()
    roads = operation(data, junction([0, 90, 180]), edits=edits)
    places = []
    roads.places_found.connect(places.append)

    assert roads.prepare() and roads.create()
    assert len(data.nodes) > 20
    assert edits.undo_stack.count() == 1
    assert len(places) == 1


def two_way_network():
    data = AutoDriveData()
    for node_id in (1, 2, 3):
        data.add_node(NodeData(node_id, 500 + 10 * node_id, 0, 500))
    write_connection_state(data, 1, 2, CONNECTION_STATES[ConnectionType.DUAL])
    write_connection_state(data, 2, 3, CONNECTION_STATES[ConnectionType.DUAL])
    return data


def new_lane_sides(data, settings):
    roads = operation(data)
    roads.settings = settings
    roads.prepare()
    roads.create()
    return {round(node.z, 2) for node_id, node in data.nodes.items() if node_id > 3}


def test_auto_lanes_follow_the_existing_network():
    # One two-way lane on the centre line, as the existing network is two-way.
    assert new_lane_sides(two_way_network(), RoadSettings()) == {0.0}
    # Two one-way lanes when chosen.
    assert new_lane_sides(two_way_network(), RoadSettings(lanes=RoadLanes.PAIRS)) == {-2.75, 2.75}
