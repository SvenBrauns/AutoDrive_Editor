import pytest

from autodrive_editor.file_io import building_cache
from autodrive_editor.file_io.building_cache import BuildingCache


class Reader:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return {"value": self.calls}


def test_entry_is_used_while_the_stamp_stays_the_same():
    cache, read = BuildingCache(), Reader()

    assert cache.get("key", (1, 2), read) == {"value": 1}
    assert cache.get("key", (1, 2), read) == {"value": 1}
    assert cache.get("key", (1, 3), read) == {"value": 2}
    assert read.calls == 2


def test_without_a_stamp_nothing_is_kept():
    cache, read = BuildingCache(), Reader()

    cache.get("key", None, read)
    cache.get("key", None, read)

    assert read.calls == 2


def test_failed_read_is_not_kept():
    cache = BuildingCache()

    def fail():
        raise OSError("gone")

    with pytest.raises(OSError):
        cache.get("key", (1, 2), fail)

    assert cache.get("key", (1, 2), Reader()) == {"value": 1}


def test_saved_entries_are_used_in_the_next_session(tmp_path):
    path = tmp_path / "cache/buildings.pickle"
    BuildingCache(path).get("key", (1, 2), Reader())
    first = BuildingCache(path)
    first.get("key", (1, 2), Reader())
    first.save()

    read = Reader()
    BuildingCache(path).get("key", (1, 2), read)

    assert path.is_file()
    assert read.calls == 0


def test_entries_of_another_version_or_a_broken_file_are_not_used(tmp_path, monkeypatch):
    path = tmp_path / "buildings.pickle"
    cache = BuildingCache(path)
    cache.get("key", (1, 2), Reader())
    cache.save()
    monkeypatch.setattr(building_cache, "VERSION", building_cache.VERSION + 1)
    read = Reader()

    BuildingCache(path).get("key", (1, 2), read)
    path.write_bytes(b"broken")
    BuildingCache(path).get("key", (1, 2), read)

    assert read.calls == 2
