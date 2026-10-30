from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.planned_piece import PlannedPiece, push_piece
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG, AutoDriveData, NodeData
from autodrive_editor.model.connections import ConnectionType, get_connection_type


def test_add_connect_and_chain():
    piece = PlannedPiece()
    a, b = piece.add(1, 2), piece.add(3, 4, flag=SUBPRIO_FLAG)
    c = piece.add(5, 6)
    piece.chain([a, b, c], ConnectionType.DUAL)
    piece.connect(c, a, ConnectionType.REVERSE)

    assert piece.points == [(1, 2), (3, 4), (5, 6)]
    assert piece.flags == [0, SUBPRIO_FLAG, 0]
    assert piece.connections == [
        (0, 1, ConnectionType.DUAL),
        (1, 2, ConnectionType.DUAL),
        (2, 0, ConnectionType.REVERSE),
    ]


def test_moved_turns_points_into_map_positions():
    piece = PlannedPiece()
    piece.chain([piece.add(1, 2), piece.add(3, 4)])
    piece.markers.append((1, "M", "G"))
    piece.open_ends.append(0)

    moved = piece.moved(lambda a, d: (a + 10, 7, d * 2))

    assert moved.points == [(11, 7, 4), (13, 7, 8)]
    assert moved.connections == piece.connections
    assert moved.markers == [(1, "M", "G")] and moved.open_ends == [0]
    assert piece.points == [(1, 2), (3, 4)]


def test_push_piece_adds_nodes_connections_and_markers_in_one_undo_step():
    data = AutoDriveData()
    data.add_node(NodeData(5, 0, 0, 0))
    edits = EditHistory()
    piece = PlannedPiece()
    a, b, c = piece.add(0, 1, 0), piece.add(10, 1, 0, flag=SUBPRIO_FLAG), piece.add(20, 1, 0)
    piece.connect(a, b)
    piece.connect(b, c, ConnectionType.DUAL)
    piece.markers.append((b, "Stop", "Group"))

    assert push_piece(edits, data, piece, "Create") == [6, 7, 8]

    assert (data.nodes[7].x, data.nodes[7].y, data.nodes[7].z) == (10, 1, 0)
    assert data.nodes[7].is_subprio and not data.nodes[6].is_subprio
    assert get_connection_type(data.nodes[6], data.nodes[7]) == ConnectionType.REGULAR
    assert get_connection_type(data.nodes[7], data.nodes[8]) == ConnectionType.DUAL
    assert [(m.node_id, m.name, m.group) for m in data.markers.values()] == [(7, "Stop", "Group")]

    edits.undo()

    assert list(data.nodes) == [5] and not data.markers
