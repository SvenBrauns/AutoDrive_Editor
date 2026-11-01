"""Reload in game (proof of concept), with the companion mod played by the test."""

from datetime import datetime

import pytest
from game_folder_helpers import add_savegame, make_game_folder
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QWidget

from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader
from autodrive_editor.game import editor_link
from autodrive_editor.ui import reload_controller

MAP_ID = "FS25_Test.SampleModMap"


@pytest.fixture
def reload_window(window, tmp_path):
    """Savegame 1 is open; status messages are collected."""

    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    savegame = add_savegame(folder, 1, "Spielstand", "LS25 Testkarte 2.0", "LS25_Testkarte_2_0")
    window.project_coordinator.load_xml_file(savegame / "AutoDrive_config.xml")

    window.link = editor_link.link_directory(folder)
    window.link.mkdir(parents=True)
    window.messages = []
    window.reload.status_changed.connect(window.messages.append)
    return window


def game_status(window, savegame=1):
    (window.link / "status.xml").write_text(
        f'<status format="1" map="{MAP_ID}" savegame="{savegame}" '
        f'time="{datetime.now().isoformat(timespec="seconds")}"/>',
        encoding="utf-8",
    )


def mod_result(window, body='<result format="1" status="done" message=""/>'):
    name = f"result_{window.reload.request_id}"
    (window.link / f"{name}.xml").write_text(body, encoding="utf-8")
    (window.link / f"{name}.done").write_bytes(b"")


def test_shortcut_is_on_the_window(reload_window):
    action = reload_window.reload.action

    assert action.shortcut() == QKeySequence("Ctrl+Alt+Shift+R")
    # MainWindow.actions is the editor's action set, so Qt's list is asked directly.
    assert action in QWidget.actions(reload_window)


def test_refused_while_the_game_runs_another_savegame(reload_window):
    game_status(reload_window, savegame=2)

    reload_window.reload.reload()

    assert reload_window.reload.request_id is None
    assert not (reload_window.link / "request.xml").exists()
    assert reload_window.messages == [
        "Reload in game: The game runs savegame 2, the editor shows savegame 1."
    ]


def test_sends_the_open_network_and_shows_the_answer(reload_window):
    game_status(reload_window)
    controller = reload_window.reload

    controller.reload()

    request_id = controller.request_id
    request = (reload_window.link / "request.xml").read_text(encoding="utf-8")
    assert f'id="{request_id}" type="reload"' in request
    network = AutoDriveXmlReader.load(
        reload_window.link / editor_link.network_file_name(request_id)
    )
    data = reload_window.project_coordinator.autodrive_data
    assert len(network.nodes) == len(data.nodes)
    assert controller.timer.isActive()

    controller._poll()
    assert controller.request_id == request_id

    mod_result(
        reload_window,
        '<result format="1" status="done" message="">'
        '<reload nodes="3" markers="1" groups="1" readSec="0.25" uploadSec="0.5"/></result>',
    )
    controller._poll()

    assert controller.request_id is None
    assert not controller.timer.isActive()
    assert reload_window.messages[-1].startswith(
        "Reloaded in game: 3 nodes, 1 markers, 1 groups · export "
    )
    assert "read 0.25 s, upload 0.50 s" in reload_window.messages[-1]
    assert [path.name for path in reload_window.link.iterdir()] == ["status.xml"]


def test_error_of_the_game_is_shown(reload_window):
    game_status(reload_window)
    reload_window.reload.reload()

    mod_result(reload_window, '<result format="1" status="error" message="AutoDrive not found"/>')
    reload_window.reload._poll()

    assert reload_window.messages[-1] == "Reload in game failed: AutoDrive not found"


def test_gives_up_without_an_answer(reload_window, monkeypatch):
    monkeypatch.setattr(reload_controller, "TIMEOUT_SEC", 0)
    game_status(reload_window)
    reload_window.reload.reload()

    reload_window.reload._poll()

    assert reload_window.reload.request_id is None
    assert reload_window.messages[-1] == "Reload in game: no answer after 0 s."
