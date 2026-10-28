import pytest

from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.visibility import Visibility


def test_everything_is_shown_by_default_except_node_ids():
    visibility = Visibility()

    assert not visibility.node_ids
    assert not visibility.hidden_selectable
    assert visibility.nodes and visibility.markers and visibility.parking
    assert all(visibility.shows_connection(kind) for kind in ConnectionType)


@pytest.mark.parametrize("kind", list(ConnectionType))
def test_each_connection_type_has_its_own_switch(kind):
    visibility = Visibility(**{f"{kind.value}_connections": False})

    assert [k for k in ConnectionType if not visibility.shows_connection(k)] == [kind]


def test_hidden_items_are_selectable_only_when_asked_for():
    hidden = Visibility(nodes=False, dual_connections=False)

    assert not hidden.nodes_selectable
    assert not hidden.connection_selectable(ConnectionType.DUAL)
    assert hidden.connection_selectable(ConnectionType.REGULAR)

    selectable = Visibility(nodes=False, dual_connections=False, hidden_selectable=True)

    assert selectable.nodes_selectable
    assert selectable.connection_selectable(ConnectionType.DUAL)
