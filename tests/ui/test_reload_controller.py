"""Save on a savegame reloads it in the game, with the companion mod played by the test."""

from datetime import datetime

import pytest
from game_folder_helpers import add_savegame, make_game_folder

from autodrive_editor.file_io.autodrive_xml import AutoDriveXmlReader
from autodrive_editor.game import editor_link
from autodrive_editor.ui import reload_controller

MAP_ID = "FS25_Test.SampleModMap"


@pytest.fixture
def reload_window(window, tmp_path, monkeypatch):
    """Savegame 1 is open; status lines and message boxes are collected."""

    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    savegame = add_savegame(folder, 1, "Spielstand", "LS25 Testkarte 2.0", "LS25_Testkarte_2_0")
    window.project_coordinator.load_xml_file(savegame / "AutoDrive_config.xml")

    window.link = editor_link.link_directory(folder)
    window.link.mkdir(parents=True)
    window.messages = []
    window.boxes = []
    window.reload.status_changed.connect(window.messages.append)
    monkeypatch.setattr(window.reload, "_inform", window.boxes.append)
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


def test_no_hidden_shortcut_any_more(reload_window):
    assert not hasattr(reload_window.reload, "action")


def test_save_reloads_the_savegame_the_game_runs(reload_window):
    game_status(reload_window)
    controller = reload_window.reload

    assert reload_window.files.save_xml()

    request_id = controller.request_id
    request = (reload_window.link / "request.xml").read_text(encoding="utf-8")
    assert f'id="{request_id}" type="reload"' in request
    network = AutoDriveXmlReader.load(
        reload_window.link / editor_link.network_file_name(request_id)
    )
    assert len(network.nodes) == len(reload_window.project_coordinator.autodrive_data.nodes)
    assert reload_window.messages[-1] == "Saved · reloading in game…"

    mod_result(
        reload_window,
        '<result format="1" status="done" message="">'
        '<reload nodes="3" markers="1" groups="1" readSec="0.25" uploadSec="0.5"/></result>',
    )
    controller._poll()

    assert controller.request_id is None
    assert not controller.timer.isActive()
    assert reload_window.messages[-1].startswith("Saved · reloaded in game (3 nodes, ")
    assert [path.name for path in reload_window.link.iterdir()] == ["status.xml"]


def test_no_reload_while_the_game_runs_another_savegame(reload_window):
    game_status(reload_window, savegame=2)

    reload_window.files.save_xml()

    assert reload_window.reload.request_id is None
    assert not (reload_window.link / "request.xml").exists()
    assert reload_window.boxes == []


def test_error_of_the_game_is_shown_in_a_box(reload_window):
    game_status(reload_window)
    reload_window.files.save_xml()

    mod_result(reload_window, '<result format="1" status="error" message="AutoDrive not found"/>')
    reload_window.reload._poll()

    assert reload_window.messages[-1] == "Saved"
    assert reload_window.boxes[0].startswith("Saved, but not reloaded in the game: AutoDrive not")
    assert "overwrites the file on its next save" in reload_window.boxes[0]


def test_no_answer_is_shown_in_a_box(reload_window, monkeypatch):
    monkeypatch.setattr(reload_controller, "TIMEOUT_SEC", 0)
    game_status(reload_window)
    reload_window.files.save_xml()

    reload_window.reload._poll()

    assert reload_window.reload.request_id is None
    assert "did not answer within 0 s" in reload_window.boxes[0]


def test_game_without_the_mod_is_warned_about_once(reload_window, monkeypatch):
    monkeypatch.setattr(reload_controller, "game_is_running", lambda: True)

    reload_window.files.save_xml()
    reload_window.files.save_xml()

    assert len(reload_window.boxes) == 1
    assert "exit the game without saving, or install the mod" in reload_window.boxes[0]


def test_no_warning_when_the_game_is_closed(reload_window):
    reload_window.files.save_xml()

    assert reload_window.boxes == []
