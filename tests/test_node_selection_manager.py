import pytest

from autodrive_editor.selection.node_selection import NodeSelectionManager


@pytest.fixture
def manager():
    return NodeSelectionManager()


@pytest.fixture
def emitted(manager):
    events = []
    manager.selection_changed.connect(lambda ids, primary: events.append((ids, primary)))
    return events


def test_replace_sets_selection_and_primary(manager):
    manager.replace([3, 1, 2], primary_node_id=2)

    assert manager.selected_node_ids == {1, 2, 3}
    assert manager.primary_node_id == 2


def test_replace_falls_back_to_lowest_id_as_primary(manager):
    manager.replace([5, 3], primary_node_id=99)

    assert manager.primary_node_id == 3


def test_replace_ignores_non_positive_ids(manager):
    manager.replace([0, -1, 4])

    assert manager.selected_node_ids == {4}


def test_add_extends_selection(manager):
    manager.replace([1])

    manager.add([2, 3], primary_node_id=3)

    assert manager.selected_node_ids == {1, 2, 3}
    assert manager.primary_node_id == 3


def test_toggle_adds_and_makes_primary(manager):
    manager.replace([1])

    manager.toggle(5)

    assert manager.selected_node_ids == {1, 5}
    assert manager.primary_node_id == 5


def test_toggle_off_primary_picks_lowest_remaining(manager):
    manager.replace([2, 4, 6], primary_node_id=4)

    manager.toggle(4)

    assert manager.selected_node_ids == {2, 6}
    assert manager.primary_node_id == 2


def test_toggle_off_last_node_clears_primary(manager):
    manager.replace([1])

    manager.toggle(1)

    assert manager.selected_node_ids == set()
    assert manager.primary_node_id is None


def test_toggle_many_flips_each_node(manager):
    manager.replace([1, 2, 3], primary_node_id=1)

    manager.toggle_many([2, 3, 4])

    assert manager.selected_node_ids == {1, 4}
    assert manager.primary_node_id == 1


def test_toggle_many_keeps_requested_primary_if_selected(manager):
    manager.replace([1])

    manager.toggle_many([5, 6], primary_node_id=6)

    assert manager.primary_node_id == 6


def test_toggle_many_replaces_removed_primary(manager):
    manager.replace([1, 2, 3], primary_node_id=1)

    manager.toggle_many([1])

    assert manager.primary_node_id == 2


def test_selected_node_ids_returns_a_copy(manager):
    manager.replace([1])

    manager.selected_node_ids.add(99)

    assert manager.selected_node_ids == {1}


def test_signal_emitted_only_on_change(manager, emitted):
    manager.replace([1, 2])
    manager.replace([2, 1])
    manager.clear()
    manager.clear()

    assert emitted == [({1, 2}, 1), (set(), None)]


def test_remove_deselects_and_picks_new_primary(manager):
    manager.replace([1, 2, 3], primary_node_id=2)

    manager.remove([2, 99])

    assert manager.selected_node_ids == {1, 3}
    assert manager.primary_node_id == 1


def test_remove_keeps_primary_if_still_selected(manager):
    manager.replace([1, 2, 3], primary_node_id=3)

    manager.remove([1])

    assert manager.primary_node_id == 3
