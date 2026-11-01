"""File → Open recent."""

import shutil

import pytest
from game_folder_helpers import add_routes, make_game_folder
from PySide6.QtWidgets import QFileDialog

from autodrive_editor.settings.recent_items import RecentItem, RecentKind
from autodrive_editor.ui.dialogs.open_dialog import OpenDialog


@pytest.fixture
def open_xml(window, monkeypatch):
    """Opens a file through File → Open… → Open other file…."""

    def _open(path):
        monkeypatch.setattr(window.files, "_ask_open", lambda: OpenDialog.BROWSE)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))
        window.files.open()

    return _open


def menu_texts(window):
    window.actions.fill_recent_menu()
    return [action.text() for action in window.actions.recent_menu.actions() if action.text()]


def test_opened_xml_is_listed_in_the_menu(window, write_xml, open_xml):
    open_xml(write_xml())

    assert menu_texts(window) == ["route.xml – XML file", "Clear list"]


def test_empty_list_shows_a_disabled_hint(window):
    window.actions.fill_recent_menu()
    actions = [action for action in window.actions.recent_menu.actions() if action.text()]

    assert [(action.text(), action.isEnabled()) for action in actions] == [
        ("No recent files", False),
        ("Clear list", False),
    ]


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
    assert menu_texts(window)[0] == "NF Marsch – Route"


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


def test_clear_list_empties_the_menu(window, write_xml, open_xml):
    open_xml(write_xml())

    window.files.clear_recent_items()

    assert menu_texts(window) == ["No recent files", "Clear list"]


def test_last_file_opens_at_startup(window, write_xml):
    path = write_xml()
    window.settings.set_recent_items([RecentItem(RecentKind.XML, str(path), path.name)])

    window.files.open_at_startup()

    assert window.project_coordinator.config_source.path == path


def test_nothing_opens_at_startup_when_turned_off(window, write_xml):
    path = write_xml()
    window.settings.set_recent_items([RecentItem(RecentKind.XML, str(path), path.name)])
    window.settings.set_reopen_last(False)

    window.files.open_at_startup()

    assert window.project_coordinator.autodrive_data is None


def test_missing_last_file_is_skipped_quietly_at_startup(window, monkeypatch, tmp_path):
    monkeypatch.setattr(window.files, "_inform", lambda message: pytest.fail(message))
    gone = RecentItem(RecentKind.XML, str(tmp_path / "gone.xml"), "gone.xml")
    window.settings.set_recent_items([gone])

    window.files.open_at_startup()

    assert window.project_coordinator.autodrive_data is None
