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
