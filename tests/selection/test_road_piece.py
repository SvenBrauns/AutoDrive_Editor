from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import CONNECTION_STATES, ConnectionType
from autodrive_editor.model.connections import write_connection_state as write
from autodrive_editor.selection.road_piece import connection_piece, road_piece

REGULAR = CONNECTION_STATES[ConnectionType.REGULAR]
DUAL = CONNECTION_STATES[ConnectionType.DUAL]
REVERSE = CONNECTION_STATES[ConnectionType.REVERSE]


def network(count, connections, flags=None):
    data = AutoDriveData()

    for node_id in range(1, count + 1):
        data.add_node(NodeData(node_id, node_id * 10, 0, 0, (flags or {}).get(node_id, 0)))

    for source, target, state in connections:
        write(data, source, target, state)

    return data


def test_piece_runs_from_junction_to_road_end_with_both_ends():
    # 1 -> 2 -> 3 -> 4, and 5 -> 2: node 2 is a junction.
    data = network(5, [(1, 2, REGULAR), (2, 3, REGULAR), (3, 4, REGULAR), (5, 2, REGULAR)])

    assert road_piece(data, {3}) == {2, 3, 4}
    assert connection_piece(data, 3, 4) == {2, 3, 4}


def test_double_click_on_a_junction_takes_every_piece_that_meets_there():
    data = network(5, [(1, 2, REGULAR), (2, 3, REGULAR), (3, 4, REGULAR), (5, 2, REGULAR)])

    assert road_piece(data, {2}) == {1, 2, 3, 4, 5}


def test_piece_ends_where_connection_type_or_direction_changes():
    # 1 -> 2 <-> 3 <-> 4, then 5 -> 4 against the walk.
    data = network(5, [(1, 2, REGULAR), (2, 3, DUAL), (3, 4, DUAL), (5, 4, REGULAR)])

    assert road_piece(data, {3}) == {2, 3, 4}


def test_reverse_connections_count_as_neighbours():
    # Reverse connections are stored only in the source node.
    data = network(3, [(1, 2, REVERSE), (2, 3, REVERSE)])

    assert road_piece(data, {3}) == {1, 2, 3}


def test_piece_ends_before_a_node_of_the_other_type():
    data = network(4, [(1, 2, REGULAR), (2, 3, REGULAR), (3, 4, REGULAR)], {3: SUBPRIO_FLAG})

    assert road_piece(data, {1}) == {1, 2}


def test_closed_ring_is_taken_once():
    data = network(3, [(1, 2, REGULAR), (2, 3, REGULAR), (3, 1, REGULAR)])

    assert road_piece(data, {1}) == {1, 2, 3}
