import pytest

from autodrive_editor import updates
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui import update_controller
from autodrive_editor.ui.update_controller import UpdateController

NEWER = {"tag_name": "v99.0.0", "html_url": "https://example.org", "body": ""}


@pytest.fixture
def controller(window, isolated_user_data, monkeypatch):
    controller = UpdateController(window, AppSettings())
    controller.shown = []
    monkeypatch.setattr(update_controller, "show_update", lambda _, r: controller.shown.append(r))
    monkeypatch.setattr(update_controller, "inform", lambda _, m: controller.shown.append(m))
    # Run the check right away instead of in a thread.
    monkeypatch.setattr(controller, "_start", controller._check)
    return controller


def answer(monkeypatch, data=None, error=None):
    def fetch():
        if error:
            raise error
        return data

    monkeypatch.setattr(updates, "fetch_latest_release", fetch)


def test_startup_check_does_nothing_when_turned_off(controller, monkeypatch):
    answer(monkeypatch, NEWER)

    controller.check_at_startup()

    assert controller.shown == []


def test_startup_check_shows_newer_version(controller, monkeypatch):
    answer(monkeypatch, NEWER)
    controller.settings.set_check_updates(True)

    controller.check_at_startup()

    assert [r.version for r in controller.shown] == ["99.0.0"]


def test_startup_check_stays_quiet_without_update_or_connection(controller, monkeypatch):
    controller.settings.set_check_updates(True)

    answer(monkeypatch, {"tag_name": "v0.0.1"})
    controller.check_at_startup()
    answer(monkeypatch, error=OSError("offline"))
    controller.check_at_startup()

    assert controller.shown == []


def test_menu_check_reports_latest_version_and_errors(controller, monkeypatch):
    answer(monkeypatch, {"tag_name": "v0.0.1"})
    controller.check_now()
    answer(monkeypatch, error=OSError("offline"))
    controller.check_now()

    assert "latest version" in controller.shown[0]
    assert "offline" in controller.shown[1]
