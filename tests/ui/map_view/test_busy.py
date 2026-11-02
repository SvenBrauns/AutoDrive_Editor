"""The logo on gray while nothing is loaded, and the text and wait cursor while a file loads."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def test_logo_is_shown_until_a_file_is_loaded(window, write_xml, qapp):
    assert window.view.logo_visible

    window.project_coordinator.load_xml_file(write_xml())

    assert not window.view.logo_visible


def test_busy_shows_the_text_and_a_wait_cursor_during_the_block(window):
    notice = window.view._notice

    with window.view.busy("Loading “a”…"):
        assert notice.isVisible() and notice.text() == "Loading “a”…"
        assert QApplication.overrideCursor().shape() == Qt.WaitCursor

    assert not notice.isVisible()
    assert QApplication.overrideCursor() is None


def test_busy_ends_when_the_block_fails(window):
    with pytest.raises(ValueError), window.view.busy("Loading"):
        raise ValueError

    assert not window.view._notice.isVisible()
    assert QApplication.overrideCursor() is None
