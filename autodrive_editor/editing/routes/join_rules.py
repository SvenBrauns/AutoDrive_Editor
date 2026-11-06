"""Rules for where new pieces meet the existing network."""

from autodrive_editor.i18n import tr
from autodrive_editor.model.autodrive_data import AutoDriveData


def join_problem(
    autodrive_data: AutoDriveData, node_id: int, starts: bool, ends: bool
) -> str | None:
    """Why the existing node is a poor place for a new piece to join, or None. A piece that
    starts at the node needs a way in, one that ends there a way out. Marker nodes never fit:
    other routes would lead through the marker."""

    node = autodrive_data.nodes[node_id]

    if node_id in autodrive_data.markers:
        return tr("Node {id} is a marker: other routes would lead through it", id=node_id)

    if starts and not node.incoming:
        return tr("Nothing drives to node {id}, so the route cannot be reached", id=node_id)

    if ends and not node.outgoing:
        return tr("Node {id} leads nowhere, so the route ends in a dead end", id=node_id)

    return None
