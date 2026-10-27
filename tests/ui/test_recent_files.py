"""File → Open recent and the recent list on the welcome screen."""

import shutil

import pytest
from game_folder_helpers import add_routes, make_game_folder
from PySide6.QtWidgets import QFileDialog

from autodrive_editor.settings.recent_items import RecentItem, RecentKind


@pytest.fixture
def open_xml(window, monkeypatch):
    """Opens a file through File → Open XML file."""

    def _open(path):
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))
        window.files.load_xml()

    return _open


def menu_texts(window):
    window.actions.fill_recent_menu()
    return [action.text() for action in window.actions.recent_menu.actions() if action.text()]


def welcome_texts(window):
    panel = window.welcome_panel
    return [
        panel.recent_layout.itemAt(i).widget().text() for i in range(panel.recent_layout.count())
    ]


def test_opened_xml_is_listed_in_the_menu_and_on_the_welcome_screen(window, write_xml, open_xml):
    open_xml(write_xml())

    assert menu_texts(window) == ["route.xml – XML file", "Clear list"]
    assert welcome_texts(window) == ["route.xml – XML file"]
    assert window.welcome_panel.recent_list.isVisibleTo(window.welcome_panel)


def test_empty_list_shows_a_disabled_hint(window):
    window.actions.fill_recent_menu()
    actions = [action for action in window.actions.recent_menu.actions() if action.text()]

    assert [(action.text(), action.isEnabled()) for action in actions] == [
        ("No recent files", False),
        ("Clear list", False),
    ]
    assert not window.welcome_panel.recent_list.isVisibleTo(window.welcome_panel)


def test_newest_file_comes_first(window, write_xml, open_xml, tmp_path):
    first = write_xml()
    second = tmp_path / "second.xml"
    shutil.copy(first, second)

    open_xml(first)
    open_xml(second)
    open_xml(first)

    assert menu_texts(window)[:2] == ["route.xml – XML file", "second.xml – XML file"]


def test_menu_entry_opens_the_file_again(window, write_xml, open_xml, tmp_path):
    first = write_xml()
    second = tmp_path / "second.xml"
    shutil.copy(first, second)
    open_xml(first)
    open_xml(second)

    menu_texts(window)
    window.actions.recent_menu.actions()[1].trigger()  # route.xml

    assert window.project_coordinator.config_source.path == first.resolve()
    assert menu_texts(window)[0] == "route.xml – XML file"


def test_recent_route_opens_with_its_name_and_map(window, tmp_path):
    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    manager = add_routes(folder, [("NF Marsch", "I0pc.xml", "NF_Marsch_4fach_oG", 7)])

    window.files.open_recent(
        RecentItem(RecentKind.ROUTE, str(manager / "routes" / "I0pc.xml"), "NF Marsch", "Map")
    )

    source = window.project_coordinator.config_source
    assert (source.display_name, source.map_name) == ("NF Marsch", "Map")
    assert welcome_texts(window) == ["NF Marsch – Route"]


def test_missing_file_is_removed_with_a_message(window, monkeypatch, tmp_path):
    messages = []
    monkeypatch.setattr(window.files, "_inform", messages.append)
    gone = RecentItem(RecentKind.XML, str(tmp_path / "gone.xml"), "gone.xml")
    window.settings.set_recent_items([gone])

    window.files.open_recent(gone)

    assert window.settings.recent_items == []
    assert "no longer exists" in messages[0]
    assert window.project_coordinator.autodrive_data is None


def test_failed_load_is_not_listed(window, open_xml, tmp_path):
    broken = tmp_path / "broken.xml"
    broken.write_text("<nothing/>", encoding="utf-8")

    open_xml(broken)

    assert window.settings.recent_items == []


def test_clear_list_empties_menu_and_welcome_screen(window, write_xml, open_xml):
    open_xml(write_xml())

    window.files.clear_recent_items()

    assert menu_texts(window) == ["No recent files", "Clear list"]
    assert welcome_texts(window) == []
