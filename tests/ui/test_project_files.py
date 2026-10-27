"""Saving and loading projects from the File menu."""

import pytest
from map_mod_helpers import overview_dds
from PySide6.QtWidgets import QFileDialog

from autodrive_editor.editing.commands.delete_nodes import DeleteNodesCommand


@pytest.fixture
def dialog_answer(monkeypatch):
    """The path the file dialogs return; empty means cancelled."""
    answer = {"path": ""}
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (answer["path"], ""))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (answer["path"], ""))
    return answer


@pytest.fixture
def project_window(loaded_window, tmp_path, sloped_heightmap):
    """Route with 3 nodes, background, heightmap and map size 4x."""
    window = loaded_window
    background = tmp_path / "overview.dds"
    background.write_bytes(overview_dds())
    window.project_coordinator.load_background_file(str(background))
    window.project_coordinator.load_heightmap_file(str(sloped_heightmap))
    window.project_coordinator.set_map_scale(4, "4x")
    return window


def test_saved_project_brings_back_route_map_and_heightmap(project_window, dialog_answer, tmp_path):
    window = project_window
    coordinator = window.project_coordinator
    dialog_answer["path"] = str(tmp_path / "projects" / "hof")
    window.files.save_project()
    assert (tmp_path / "projects" / "hof.json").is_file()

    coordinator.remove_heightmap()
    coordinator.set_map_scale(1, "1x")
    window.edit_history.push(DeleteNodesCommand(coordinator.autodrive_data, {2}))

    dialog_answer["path"] = str(tmp_path / "projects" / "hof.json")
    window.files.load_project()

    assert len(coordinator.autodrive_data) == 3
    assert window.background_map.has_background()
    assert window.background_map.map_scale == 4
    assert window.actions.map_scale_actions[4].isChecked()
    assert window.heightmap.has_heightmap()
    assert "Project loaded with heightmap: hof.json" in window.status.text()


def test_broken_project_keeps_the_loaded_data(loaded_window, dialog_answer, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    dialog_answer["path"] = str(path)

    loaded_window.files.load_project()

    assert len(loaded_window.project_coordinator.autodrive_data) == 3
    assert "could not be loaded" in loaded_window.status.text()


def test_project_needs_loaded_data(window, dialog_answer, tmp_path):
    dialog_answer["path"] = str(tmp_path / "hof.json")

    window.files.save_project()

    assert not (tmp_path / "hof.json").exists()
    assert window.status.text() == "Load an AutoDrive XML first"
