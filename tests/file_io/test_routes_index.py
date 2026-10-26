import re
from datetime import datetime

import pytest
from game_folder_helpers import add_routes

from autodrive_editor.file_io.routes_index import add_route, find_route_entry, read_routes_index

ROUTES = [
    ("Thueringen", "g8Cq.xml", "LS25_Thüringen_2_0_16x", 1),
    ("NF Marsch", "I0pc.xml", "NF_Marsch_4fach_oG", 7),
]


def test_reads_all_routes_in_order(tmp_path):
    manager = add_routes(tmp_path, ROUTES)

    entries = read_routes_index(manager / "routes.xml")

    assert [(e.name, e.file_name, e.map_name, e.revision) for e in entries] == ROUTES
    assert entries[0].path == manager / "routes" / "g8Cq.xml"
    assert entries[0].date == "2026/10/23 19:13:30"


def test_rejects_other_files(tmp_path):
    path = tmp_path / "routes.xml"
    path.write_text("<something/>", encoding="utf-8")

    with pytest.raises(ValueError, match="unbekanntes Format"):
        read_routes_index(path)


def test_finds_entry_of_a_route_file(tmp_path):
    manager = add_routes(tmp_path, ROUTES)

    entry = find_route_entry(manager / "routes" / "I0pc.xml")

    assert entry.name == "NF Marsch"
    assert entry.map_name == "NF_Marsch_4fach_oG"


def test_autosaves_belong_to_their_route(tmp_path):
    manager = add_routes(tmp_path, ROUTES)

    entry = find_route_entry(manager / "routes" / "g8Cq_autosave_3.xml")

    assert entry.name == "Thueringen"


def test_route_file_outside_routes_manager_has_no_entry(tmp_path):
    loose = tmp_path / "somewhere" / "route.xml"
    loose.parent.mkdir()
    loose.write_text("<routeExport/>", encoding="utf-8")

    assert find_route_entry(loose) is None


def test_new_route_is_added_with_revision_one(tmp_path):
    manager = add_routes(tmp_path, ROUTES)

    path = add_route(manager / "routes.xml", "Neu", "LS25_X", datetime(2026, 10, 26, 8, 0, 0))

    entries = read_routes_index(manager / "routes.xml")
    assert [e.name for e in entries] == ["Thueringen", "NF Marsch", "Neu"]
    new = entries[-1]
    assert (new.map_name, new.revision, new.date) == ("LS25_X", 1, "2026/10/26 08:00:00")
    assert new.path == path
    assert re.fullmatch(r"[A-Za-z0-9]{16}\.xml", path.name)
    assert not path.exists()
