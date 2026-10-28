from autodrive_editor.file_io.savegame_parking import (
    linked_park_markers,
    match_park_markers,
    read_marker_keys,
)
from autodrive_editor.model.autodrive_data import MarkerData

CONFIG = (
    "<AutoDrive><mapmarker>"
    "<mm2><id>5</id><name>G1</name><group>15</group></mm2>"
    "<mm1><id>4</id><name>Hof</name><group>All</group></mm1>"
    "</mapmarker></AutoDrive>"
)


def markers(*keys):
    return [MarkerData(node_id, name, group) for node_id, (name, group) in enumerate(keys, 1)]


def test_reads_name_and_group_in_number_order(tmp_path):
    path = tmp_path / "AutoDrive_config.xml"
    path.write_text(CONFIG, encoding="utf-8")

    assert read_marker_keys(path) == [("Hof", "All"), ("G1", "15")]


def test_matches_by_name_and_group_not_by_number():
    route = markers(("G1", "15"), ("Hof", "All"))

    parked = match_park_markers(route, [("Hof", "All"), ("G1", "15")], {2})

    assert parked == [route[0]]


def test_several_markers_with_the_same_name_and_group_fall_back_to_the_number():
    route = markers(("G1", "15"), ("G1", "15"), ("Hof", "All"))
    savegame = [("Hof", "All"), ("G1", "15"), ("G1", "15")]

    assert match_park_markers(route, savegame, {2}) == [route[1]]
    assert match_park_markers(route, savegame, {3}) == []


def test_numbers_without_a_savegame_marker_or_route_match_are_skipped():
    route = markers(("Hof", "All"))

    assert match_park_markers(route, [("Feld", "All")], {1, 7}) == []


def test_savegame_without_vehicles_has_no_parking(tmp_path):
    (tmp_path / "AutoDrive_config.xml").write_text(CONFIG, encoding="utf-8")

    assert linked_park_markers(markers(("Hof", "All")), tmp_path) == []


def test_broken_config_has_no_parking(tmp_path):
    (tmp_path / "AutoDrive_config.xml").write_text("<AutoDrive>", encoding="utf-8")
    (tmp_path / "vehicles.xml").write_text(
        '<vehicles><AutoDrive parkDestination="1"/></vehicles>', encoding="utf-8"
    )

    assert linked_park_markers(markers(("Hof", "All")), tmp_path) == []
