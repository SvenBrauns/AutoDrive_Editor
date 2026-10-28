import json

import pytest

from autodrive_editor.file_io.project_file import ProjectFileStore


@pytest.fixture
def files(tmp_path):
    """Route, background and heightmap in a "data" folder next to the projects."""
    data = tmp_path / "data"
    data.mkdir()
    for name in ("route.xml", "overview.dds", "dem.png"):
        (data / name).write_text("x", encoding="utf-8")
    return data


@pytest.fixture
def store(tmp_path):
    return ProjectFileStore(tmp_path / "projects")


def save(store, tmp_path, files, **changes):
    arguments = {
        "config_path": tmp_path / "projects" / "hof.json",
        "xml_path": files / "route.xml",
        "background_path": files / "overview.dds",
        "map_scale": 4,
        "heightmap_path": files / "dem.png",
    } | changes
    return store.save_project(**arguments)


def test_save_and_load_keep_all_settings(store, tmp_path, files):
    path = save(store, tmp_path, files)

    project = store.load_project(path)

    assert project["autodrive_xml"] == str((files / "route.xml").resolve())
    assert project["background_dds"] == str((files / "overview.dds").resolve())
    assert project["heightmap"] == str((files / "dem.png").resolve())
    assert project["map_scale"] == 4


def test_paths_are_stored_relative_so_the_project_can_be_moved(store, tmp_path, files):
    path = save(store, tmp_path, files)
    assert json.loads(path.read_text(encoding="utf-8"))["autodrive_xml"] == "../data/route.xml"

    moved = tmp_path.rename(tmp_path.with_name(tmp_path.name + "_moved"))
    project = ProjectFileStore(moved / "projects").load_project(moved / "projects" / "hof.json")

    assert project["autodrive_xml"] == str((moved / "data" / "route.xml").resolve())


def test_background_and_heightmap_are_optional(store, tmp_path, files):
    path = save(store, tmp_path, files, background_path=None, heightmap_path=None)

    project = store.load_project(path)

    assert project["background_dds"] is None
    assert project["heightmap"] is None


def test_json_extension_is_added(store, tmp_path, files):
    path = save(store, tmp_path, files, config_path=tmp_path / "projects" / "hof")

    assert path.name == "hof.json"


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"map_scale": 3}, ValueError),
        ({"xml_path": None}, ValueError),
        ({"heightmap_path": "missing.png"}, FileNotFoundError),
    ],
)
def test_save_refuses_invalid_settings(store, tmp_path, files, changes, error):
    with pytest.raises(error):
        save(store, tmp_path, files, **changes)


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        "[]",
        '{"format_version": 2, "autodrive_xml": "../data/route.xml", "map_scale": 1}',
        '{"format_version": 1, "map_scale": 1}',
        '{"format_version": 1, "autodrive_xml": "../data/route.xml", "map_scale": 3}',
        '{"format_version": 1, "autodrive_xml": "C:/data/route.xml", "map_scale": 1}',
    ],
    ids=["broken", "no object", "version", "no xml", "map size", "absolute path"],
)
def test_load_refuses_invalid_project_files(store, tmp_path, files, content):
    path = tmp_path / "projects" / "bad.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        store.load_project(path)


def test_load_reports_a_missing_referenced_file(store, tmp_path, files):
    path = save(store, tmp_path, files)
    (files / "dem.png").unlink()

    with pytest.raises(FileNotFoundError):
        store.load_project(path)


def test_linked_savegame_is_stored_relative(store, tmp_path, files):
    savegame = tmp_path / "savegame3"
    savegame.mkdir()

    path = save(store, tmp_path, files, savegame_path=savegame)

    assert json.loads(path.read_text(encoding="utf-8"))["savegame"] == "../savegame3"
    assert store.load_project(path)["savegame"] == str(savegame.resolve())


def test_project_without_savegame_has_no_link(store, tmp_path, files):
    path = save(store, tmp_path, files)

    assert "savegame" not in json.loads(path.read_text(encoding="utf-8"))
    assert store.load_project(path)["savegame"] is None


def test_missing_savegame_folder_only_drops_the_link(store, tmp_path, files):
    savegame = tmp_path / "savegame3"
    savegame.mkdir()
    path = save(store, tmp_path, files, savegame_path=savegame)
    savegame.rmdir()

    assert store.load_project(path)["savegame"] is None
    assert store.stored_savegame(path) is None


def test_set_savegame_keeps_the_other_settings(store, tmp_path, files):
    savegame = tmp_path / "savegame3"
    savegame.mkdir()
    path = save(store, tmp_path, files)

    store.set_savegame(path, savegame)

    assert store.stored_savegame(path) == savegame.resolve()
    assert store.load_project(path)["map_scale"] == 4

    store.set_savegame(path, None)

    assert "savegame" not in json.loads(path.read_text(encoding="utf-8"))


def test_finds_the_project_of_an_xml(store, tmp_path, files):
    (tmp_path / "projects" / "broken.json").write_text("{", encoding="utf-8")
    other = files / "other.xml"
    other.write_text("x", encoding="utf-8")
    path = save(store, tmp_path, files)

    assert store.find_project_for(files / "route.xml") == path
    assert store.find_project_for(other) is None
    assert store.project_uses(path, files / "route.xml")
    assert not store.project_uses(tmp_path / "projects" / "broken.json", files / "route.xml")
