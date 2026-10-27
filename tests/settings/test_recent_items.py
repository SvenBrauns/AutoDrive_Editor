from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.settings.recent_items import (
    MAX_RECENT_ITEMS,
    RecentItem,
    RecentKind,
    with_recent_item,
    without_recent_item,
)


def item(name, kind=RecentKind.XML):
    return RecentItem(kind, f"C:/data/{name}.xml", name)


def test_new_item_goes_to_the_top_and_the_list_is_limited():
    items = []

    for index in range(MAX_RECENT_ITEMS + 2):
        items = with_recent_item(items, item(f"file{index}"))

    assert [old.name for old in items] == ["file6", "file5", "file4", "file3", "file2"]


def test_reopened_file_moves_to_the_top_without_a_duplicate():
    items = [item("a"), item("b"), item("c")]

    items = with_recent_item(items, RecentItem(RecentKind.XML, "C:/data/c.xml", "c"))

    assert [old.name for old in items] == ["c", "a", "b"]


def test_item_can_be_removed():
    assert without_recent_item([item("a"), item("b")], item("a")) == [item("b")]


def test_label_names_the_kind():
    assert RecentItem(RecentKind.ROUTE, "x.xml", "NF Marsch").label == "NF Marsch – Route"


def test_items_are_kept_between_sessions():
    items = [RecentItem(RecentKind.ROUTE, "C:/r.xml", "Route A", "MapX"), item("b")]

    AppSettings().set_recent_items(items)

    assert AppSettings().recent_items == items


def test_unreadable_stored_items_are_left_out():
    settings = AppSettings()
    settings._settings.setValue(
        AppSettings.RECENT_ITEMS_KEY,
        '[{"kind": "nonsense", "path": "x", "name": "x"}, '
        '{"kind": "xml", "path": "C:/data/b.xml", "name": "b"}, 7]',
    )

    assert AppSettings().recent_items == [item("b")]


def test_broken_stored_list_gives_no_items():
    AppSettings()._settings.setValue(AppSettings.RECENT_ITEMS_KEY, "{not json")

    assert AppSettings().recent_items == []
