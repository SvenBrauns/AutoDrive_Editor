from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.network_check.checks import (
    HEIGHT,
    OUTSIDE,
    OVERLAP,
    CheckResults,
    HeightProblem,
)
from autodrive_editor.network_check.ignores import (
    CheckIgnores,
    IgnoreStore,
    ignore_key,
    ignore_keys,
    split_ignored,
)

RESULTS = CheckResults([[1, 2]], [3], [HeightProblem(4, 30.0, 10.0)])


def make_data():
    data = AutoDriveData()
    data.add_node(NodeData(1, 0, 0, 0))
    data.add_node(NodeData(2, 0.004, 0, 0))
    data.add_node(NodeData(3, 1500, 0, 0))
    data.add_node(NodeData(4, 10.123, 30, 5))
    return data


def test_entries_are_remembered_by_rounded_node_positions():
    data = make_data()

    assert ignore_key(data, OVERLAP, [1, 2]) == (OVERLAP, frozenset({(0, 0, 0)}))
    assert ignore_key(data, HEIGHT, HeightProblem(4, 30, 10)) == (
        HEIGHT,
        frozenset({(10.12, 30, 5)}),
    )
    assert ignore_key(data, OUTSIDE, 99) is None


def test_ignored_entries_are_split_off():
    data = make_data()
    ignored = ignore_keys(data, CheckResults([[1, 2]], [], [HeightProblem(4, 30.0, 10.0)]))

    visible, hidden = split_ignored(data, RESULTS, ignored)

    assert visible == CheckResults([], [3], [])
    assert hidden == CheckResults([[1, 2]], [], [HeightProblem(4, 30.0, 10.0)])


def test_ignored_entry_comes_back_when_its_node_moves():
    data = make_data()
    ignored = ignore_keys(data, CheckResults([], [3], []))

    data.nodes[3].x = 1600

    visible, hidden = split_ignored(data, RESULTS, ignored)

    assert visible.outside_node_ids == [3]
    assert hidden.problem_count == 0


def test_ignored_entry_survives_renumbered_ids():
    data = make_data()
    ignored = ignore_keys(data, CheckResults([], [3], []))

    node = data.nodes.pop(3)
    node.node_id = 7
    data.add_node(node)

    visible, _ = split_ignored(data, CheckResults([], [7], None), ignored)

    assert visible == CheckResults([], [], None)  # unchecked heights stay unchecked


def test_store_keeps_ignores_per_network(tmp_path):
    store = IgnoreStore(tmp_path / "ignores.json")
    ignores = CheckIgnores({HEIGHT}, ignore_keys(make_data(), RESULTS))

    store.save(tmp_path / "route_a.xml", ignores)

    assert IgnoreStore(tmp_path / "ignores.json").load(tmp_path / "route_a.xml") == ignores
    assert store.load(tmp_path / "route_b.xml") == CheckIgnores()


def test_store_removes_networks_without_ignores(tmp_path):
    store = IgnoreStore(tmp_path / "ignores.json")
    store.save(tmp_path / "route.xml", CheckIgnores({HEIGHT}))

    store.save(tmp_path / "route.xml", CheckIgnores())

    assert store._read() == {}


def test_damaged_store_counts_as_empty(tmp_path):
    (tmp_path / "ignores.json").write_text("{nonsense", encoding="utf-8")

    assert IgnoreStore(tmp_path / "ignores.json").load(tmp_path / "route.xml") == CheckIgnores()


def test_enabled_checks():
    assert CheckIgnores({HEIGHT}).enabled_checks == {OVERLAP, OUTSIDE}
