import os
import sys
import traceback
from pathlib import Path

# Must be set before PySide6 creates an application, so no window opens.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True, scope="session")
def test_user_data(tmp_path_factory):
    r"""Settings and imported maps go to a temporary folder during the whole
    test run, never to the real %APPDATA%\AutoDrive Editor."""
    data_directory = tmp_path_factory.mktemp("user_data")
    previous = os.environ.get("AUTODRIVE_EDITOR_DATA_DIR")
    os.environ["AUTODRIVE_EDITOR_DATA_DIR"] = str(data_directory)

    yield data_directory

    if previous is None:
        os.environ.pop("AUTODRIVE_EDITOR_DATA_DIR", None)
    else:
        os.environ["AUTODRIVE_EDITOR_DATA_DIR"] = previous


@pytest.fixture(autouse=True)
def no_installed_game(monkeypatch):
    """Tests never find the real FS25 install folder and its base maps."""
    from autodrive_editor.game import game_installation

    monkeypatch.setattr(game_installation, "STEAM_LIBRARY_FILE", Path("missing.vdf"))
    monkeypatch.setattr(game_installation, "STANDALONE_PATHS", ())


@pytest.fixture(autouse=True)
def no_recent_items():
    """Every test starts with an empty list of recently opened files."""
    from autodrive_editor.settings.app_settings import AppSettings

    settings = AppSettings()

    if settings.recent_items:
        settings.set_recent_items([])


@pytest.fixture
def isolated_user_data(tmp_path, monkeypatch):
    """A fresh, empty user data folder for tests that need clean settings."""
    data_directory = tmp_path / "user_data"
    monkeypatch.setenv("AUTODRIVE_EDITOR_DATA_DIR", str(data_directory))
    return data_directory


@pytest.fixture(autouse=True)
def fail_on_slot_exceptions():
    """Qt only prints exceptions raised inside slots. Fail the test instead."""
    caught = []
    previous_hook = sys.excepthook
    sys.excepthook = lambda *exc_info: caught.append(exc_info)

    yield

    sys.excepthook = previous_hook

    if caught:
        details = "".join("".join(traceback.format_exception(*exc_info)) for exc_info in caught)
        pytest.fail(f"Unhandled exception in a Qt slot:\n{details}", pytrace=False)


@pytest.fixture
def write_xml(tmp_path):
    """Write a RoutesManager route file (<routeExport>) and return its path."""

    def _write(
        x="0;10;20",
        y="0;0;0",
        z="0;0;0",
        out="2;3;",
        incoming=";1;2",
        flags="0;0;0",
        markers="",
        groups="",
        raw=None,
    ):
        if raw is None:
            optional = ""

            if out is not None:
                optional += f"<out>{out}</out>"

            if incoming is not None:
                optional += f"<in>{incoming}</in>"

            if flags is not None:
                optional += f"<flags>{flags}</flags>"

            raw = (
                "<routeExport>"
                "<waypoints>"
                f"<x>{x}</x><y>{y}</y><z>{z}</z>"
                f"{optional}"
                "</waypoints>"
                f"<markers>{markers}</markers>"
                f"<groups>{groups}</groups>"
                "</routeExport>"
            )

        path = tmp_path / "route.xml"
        path.write_text(raw, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def window(qapp, tmp_path):
    from PySide6.QtWidgets import QMessageBox

    from autodrive_editor.project.autosave import AutosaveStore
    from autodrive_editor.ui.main_window import MainWindow

    main_window = MainWindow()
    main_window.files.autosave_store = AutosaveStore(tmp_path / "autosave")
    # Tests that need the missing-map question replace this again.
    main_window.map_import._ask_missing_map = lambda map_name: None
    # Tests that link a savegame replace this again.
    main_window.savegame_link._run_dialog = lambda dialog: 0
    # Closing at the end of a test drops unsaved edits without asking.
    main_window.files._ask_save_changes = lambda: QMessageBox.Discard
    main_window.show()
    qapp.processEvents()

    yield main_window

    main_window.close()
    main_window.deleteLater()
    qapp.processEvents()


@pytest.fixture
def loaded_window(window, write_xml, qapp):
    path = write_xml(x="0;10;20", z="0;0;0", out="2;3;", incoming=";1;2")
    window.project_coordinator.load_xml_file(path)
    qapp.processEvents()
    return window


@pytest.fixture
def zoomed_window(loaded_window, qapp):
    """Loaded window zoomed in so nodes 1 (x=0), 2 (x=10) and 3 (x=20)
    on the line z=0 are drawn and can be clicked."""

    window = loaded_window
    window.view.set_zoom_level(4.0)
    window.view.centerOn(10, 0)
    qapp.processEvents()

    for node_id, x in ((1, 0), (2, 10), (3, 20)):
        assert window.scene_renderer.get_node_at(x, 0, window.view.zoom_level).node_id == node_id

    return window


@pytest.fixture
def sloped_heightmap(tmp_path):
    """16-bit heightmap that rises from west to east, so the terrain
    height depends on x only."""
    from PIL import Image

    size = 257
    image = Image.new("I;16", (size, size))
    image.putdata([column * 200 for row in range(size) for column in range(size)])
    path = tmp_path / "dem.png"
    image.save(path)
    return path


@pytest.fixture
def german():
    """The editor's texts in German for one test."""
    from autodrive_editor import i18n

    i18n.set_language(i18n.GERMAN)
    yield
    i18n.set_language(i18n.ENGLISH)
