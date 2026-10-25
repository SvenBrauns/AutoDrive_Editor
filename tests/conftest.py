import os
import sys
import traceback

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
    """Write an AutoDrive XML file and return its path."""

    def _write(
        x="0;10;20",
        y="0;0;0",
        z="0;0;0",
        out="2;3;",
        incoming=";1;2",
        flags="0;0;0",
        markers="",
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
                "<AutoDrive>"
                "<waypoints>"
                f"<x>{x}</x><y>{y}</y><z>{z}</z>"
                f"{optional}"
                "</waypoints>"
                f"<markers>{markers}</markers>"
                "</AutoDrive>"
            )

        path = tmp_path / "AutoDrive_config.xml"
        path.write_text(raw, encoding="utf-8")
        return path

    return _write


@pytest.fixture
def window(qapp):
    from autodrive_editor.ui.main_window import MainWindow

    main_window = MainWindow()
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
    on the line z=0 are drawn as clickable items."""

    window = loaded_window
    window.view.set_zoom_level(4.0)
    window.view.centerOn(10, 0)
    qapp.processEvents()

    window.scene_renderer.update_visible_scene_rect(window.view.get_visible_scene_rect())
    assert set(window.scene_renderer.visible_node_manager.visible_node_items) == {1, 2, 3}

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
