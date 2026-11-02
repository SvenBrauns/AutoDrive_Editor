"""Each file opens where its view was left; View → Show whole map."""

import shutil

import pytest
from PySide6.QtWidgets import QFileDialog

from autodrive_editor.settings.view_state import ViewState
from autodrive_editor.ui.dialogs.open_dialog import OpenDialog


@pytest.fixture
def open_xml(window, monkeypatch):
    def _open(path):
        monkeypatch.setattr(window.files, "_ask_open", lambda: OpenDialog.BROWSE)
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))
        window.files.open()

    return _open


@pytest.fixture
def two_files(write_xml, tmp_path):
    first = write_xml(x="0;100;200", z="0;0;0", out="2;3;", incoming=";1;2")
    second = tmp_path / "second.xml"
    shutil.copy(first, second)
    return first, second


def test_a_file_opens_where_its_view_was_left(window, two_files, open_xml):
    first, second = two_files
    open_xml(first)
    window.view.show_view_state(ViewState(150.0, 0.0, 4.0, 20.0))

    open_xml(second)
    assert window.view.zoom_level != pytest.approx(4.0)

    open_xml(first)
    view = window.view.view_state()
    assert (view.zoom, view.rotation) == (pytest.approx(4.0), pytest.approx(20.0))
    assert view.x == pytest.approx(150.0, abs=1)


def test_the_view_is_kept_when_the_editor_closes(window, two_files, open_xml):
    first, _ = two_files
    open_xml(first)
    window.view.show_view_state(ViewState(150.0, 0.0, 4.0, 20.0))

    window.close()

    assert window.settings.file_view(first).zoom == pytest.approx(4.0)


def test_show_whole_map_fits_the_network_and_resets_the_rotation(window, two_files, open_xml):
    first, _ = two_files
    assert not window.actions.show_whole_map_action.isEnabled()
    open_xml(first)
    fitted = window.view.zoom_level
    window.view.show_view_state(ViewState(150.0, 0.0, 4.0, 20.0))

    window.actions.show_whole_map_action.trigger()

    assert window.view.rotation_angle == pytest.approx(0.0)
    assert window.view.zoom_level == pytest.approx(fitted)
