"""Setup dialog on first start."""

import pytest

from autodrive_editor.settings.app_settings import AppSettings


@pytest.fixture
def setup_window(window, isolated_user_data):
    window.settings = window.files.settings = window.map_import.settings = AppSettings()
    return window


def test_first_start_shows_setup_once(setup_window, monkeypatch):
    shown = []
    monkeypatch.setattr(
        setup_window.map_import, "_show_first_start_dialog", lambda: shown.append(1)
    )

    setup_window.map_import.run_first_start()
    setup_window.map_import.run_first_start()

    assert shown == [1]
    assert not setup_window.settings.needs_setup
