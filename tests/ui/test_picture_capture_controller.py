"""Map → Capture game picture, with the companion mod played by the test."""

import json
import time
from datetime import datetime

import pytest
from game_folder_helpers import add_savegame, make_game_folder
from map_mod_helpers import make_single_map_mod
from PIL import Image
from PySide6.QtWidgets import QMessageBox

from autodrive_editor.file_io.map_mod import read_map_mod
from autodrive_editor.game import editor_link
from autodrive_editor.terrain import game_picture
from autodrive_editor.terrain.background_map import Background
from autodrive_editor.terrain.map_cache import MapCache
from autodrive_editor.ui import picture_capture_controller
from autodrive_editor.ui.tools.interaction_mode import InteractionMode

MAP_ID = "FS25_Test.SampleModMap"


@pytest.fixture
def capture_window(window, tmp_path, isolated_user_data, monkeypatch):
    """Savegame 1 of an imported map is open. The map is shrunk to 20 m and tiles to 20 px,
    so at 0.5 m/px the picture has 2 × 2 tiles."""

    monkeypatch.setattr(picture_capture_controller, "BASE_MAP_SIZE", 10)
    monkeypatch.setattr(game_picture, "TILE_PX", 20)

    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    cache = MapCache()
    window.map_cache = window.map_import.map_cache = window.project_coordinator.map_cache = cache
    mod_path = make_single_map_mod(tmp_path / "mods")
    window.cached = cache.import_map(mod_path, read_map_mod(mod_path).maps[0])
    savegame = add_savegame(folder, 1, "Spielstand", "LS25 Testkarte 2.0", "LS25_Testkarte_2_0")
    window.project_coordinator.load_xml_file(savegame / "AutoDrive_config.xml")

    window.link = editor_link.link_directory(folder)
    window.link.mkdir(parents=True)
    window.messages = []
    controller = window.picture_capture
    monkeypatch.setattr(controller, "_inform", window.messages.append)
    window.dialogs = []
    window.start = False

    def run(dialog):
        window.dialogs.append(dialog)
        dialog.resolution_buttons[0.5].setChecked(True)
        return window.start and dialog.start_button.isEnabled()

    controller._run_dialog = run
    return window


def game_status(window, map_id=MAP_ID, savegame=1, time=None):
    time = time or datetime.now()
    (window.link / "status.xml").write_text(
        f'<status format="1" map="{map_id}" savegame="{savegame}" '
        f'time="{time.isoformat(timespec="seconds")}"/>',
        encoding="utf-8",
    )


def dialog_status(window):
    window.picture_capture.open_dialog()
    dialog = window.dialogs[-1]
    return dialog.start_button.isEnabled(), dialog.status_label.text()


def start(window):
    game_status(window)
    window.start = True
    window.picture_capture.open_dialog()
    return window.picture_capture.capture


def mod_tiles(capture, tiles):
    folder = editor_link.pictures_directory(capture.link, capture.request_id)
    folder.mkdir(exist_ok=True)

    for col, row in tiles:
        Image.new("RGB", (20, 20), (255, 0, 0)).save(folder / f"tile_{col}_{row}.dds", "DDS")
        (folder / f"tile_{col}_{row}.done").write_bytes(b"")


def mod_result(capture, status="done", message=""):
    name = f"result_{capture.request_id}"
    (capture.link / f"{name}.xml").write_text(
        f'<result format="1" status="{status}" message="{message}"/>', encoding="utf-8"
    )
    (capture.link / f"{name}.done").write_bytes(b"")


def poll_until_finished(window):
    deadline = time.monotonic() + 10

    while window.picture_capture.running and time.monotonic() < deadline:
        window.picture_capture._poll()
        time.sleep(0.02)


def test_start_needs_the_game_with_the_same_map_and_savegame(capture_window):
    assert dialog_status(capture_window) == (
        False,
        "The game is not running, or the mod FS25_AutoDriveEditorLink is not active.",
    )

    game_status(capture_window, time=datetime(2026, 1, 1))
    assert not dialog_status(capture_window)[0]

    game_status(capture_window, map_id="FS25_Other.Map")
    assert dialog_status(capture_window) == (False, "The game runs another map: FS25_Other.Map.")

    game_status(capture_window, savegame=2)
    assert not dialog_status(capture_window)[0]

    game_status(capture_window)
    assert dialog_status(capture_window) == (True, "Connected: LS25 Testkarte 2.0, savegame 1")


def test_nothing_to_capture_without_an_open_config(capture_window):
    capture_window.project_coordinator.savegame_directory = None
    capture_window.project_coordinator.config_source = None
    game_status(capture_window)

    assert dialog_status(capture_window) == (False, "Open a config of an imported map first.")


def test_whole_capture_shows_progress_and_the_tiles(capture_window):
    capture = start(capture_window)

    assert (capture_window.link / "request.xml").is_file()
    assert capture_window.background_map.showing_picture()
    assert capture_window.actions.background_actions[Background.PICTURE].isChecked()
    assert capture_window.picture_capture.progress.isVisible()
    assert capture_window.picture_capture.progress_label.text().startswith("Game picture 0/4")
    assert not capture_window.actions.capture_picture_action.isEnabled()
    assert capture_window.settings.picture_wait_ms == 500

    mod_tiles(capture, [(0, 0), (1, 0), (0, 1), (1, 1)])
    mod_result(capture)
    poll_until_finished(capture_window)

    meta = json.loads((capture.picture.directory / "meta.json").read_text(encoding="utf-8"))
    assert len(meta["tiles"]) == 4
    assert capture.picture.tile_path(1, 0, 0).is_file()
    assert capture_window.status.text() == "Game picture captured: 4 tiles"
    assert not capture_window.picture_capture.progress.isVisible()
    assert capture_window.actions.capture_picture_action.isEnabled()


def test_cancel_asks_the_mod_to_stop(capture_window):
    capture = start(capture_window)

    capture_window.picture_capture.cancel_button.click()

    assert (capture_window.link / f"cancel_{capture.request_id}").is_file()
    assert capture_window.picture_capture.progress_label.text() == "Game picture: cancelling…"

    mod_tiles(capture, [(0, 0)])
    mod_result(capture, "cancelled")
    poll_until_finished(capture_window)

    assert capture_window.status.text() == "Game picture cancelled: 1 of 4 tiles"


def test_an_error_of_the_mod_is_shown(capture_window):
    capture = start(capture_window)

    mod_result(capture, "error", "Other map")
    poll_until_finished(capture_window)

    assert capture_window.messages == ["The game picture could not be captured: Other map"]


def test_closing_during_a_capture_asks_and_cancels(capture_window, monkeypatch):
    capture = start(capture_window)
    answers = [QMessageBox.No, QMessageBox.Yes]
    monkeypatch.setattr(QMessageBox, "question", lambda *args: answers.pop(0))

    assert not capture_window.picture_capture.confirm_stop()
    assert capture_window.picture_capture.running

    assert capture_window.picture_capture.confirm_stop()
    assert not capture_window.picture_capture.running
    assert (capture_window.link / f"cancel_{capture.request_id}").is_file()


def captured_picture(window):
    capture = start(window)
    mod_tiles(capture, [(0, 0), (1, 0), (0, 1), (1, 1)])
    mod_result(capture)
    poll_until_finished(window)
    return capture.picture


def test_refresh_needs_a_captured_picture(capture_window):
    assert not capture_window.actions.refresh_picture_action.isEnabled()

    capture_window.picture_capture.set_refresh_active(True)

    assert capture_window.messages == ["Capture the whole map first (Map → Capture game picture…)."]
    assert capture_window.picture_capture.refresh_tool is None
    assert not capture_window.actions.refresh_picture_action.isChecked()


def test_refresh_captures_the_marked_tiles(capture_window):
    picture = captured_picture(capture_window)
    action = capture_window.actions.refresh_picture_action
    assert action.isEnabled()

    action.setChecked(True)
    tool = capture_window.picture_capture.refresh_tool
    assert capture_window.view.active_tool is tool
    assert tool.picture is capture_window.background_map.picture is picture

    tool._set_marked({(1, 0)})
    tool.confirm()

    capture = capture_window.picture_capture.capture
    assert capture.tiles == [(1, 0)]
    assert capture.picture is picture
    assert capture_window.picture_capture.refresh_tool is None
    assert not action.isChecked() and not action.isEnabled()

    mod_tiles(capture, [(1, 0)])
    mod_result(capture)
    poll_until_finished(capture_window)

    assert capture_window.status.text() == "Game picture refreshed: 1 tiles"
    assert action.isEnabled()


def test_refresh_waits_for_the_game(capture_window):
    captured_picture(capture_window)
    capture_window.actions.refresh_picture_action.setChecked(True)
    tool = capture_window.picture_capture.refresh_tool
    game_status(capture_window, time=datetime(2026, 1, 1))

    tool._set_marked({(1, 0)})
    tool.confirm()

    assert capture_window.messages == [
        "The game is not running, or the mod FS25_AutoDriveEditorLink is not active."
    ]
    assert not capture_window.picture_capture.running
    assert capture_window.picture_capture.refresh_tool is tool and tool.marked == {(1, 0)}


def test_refresh_and_measuring_end_each_other(capture_window):
    captured_picture(capture_window)
    actions = capture_window.actions

    capture_window.set_interaction_mode(InteractionMode.MEASURE_DISTANCE)
    actions.refresh_picture_action.setChecked(True)
    assert capture_window.view.interaction_mode != InteractionMode.MEASURE_DISTANCE

    capture_window.set_interaction_mode(InteractionMode.MEASURE_DISTANCE)
    assert not actions.refresh_picture_action.isChecked()
    assert capture_window.picture_capture.refresh_tool is None
