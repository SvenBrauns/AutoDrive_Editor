import pytest
from base_game_helpers import make_installation
from game_folder_helpers import make_game_folder

from autodrive_editor.editing.path_shapes import PathOptions
from autodrive_editor.game.game_folder import GameFolder
from autodrive_editor.game.game_installation import GameInstallation
from autodrive_editor.model.autodrive_data import SUBPRIO_FLAG
from autodrive_editor.model.connections import ConnectionType
from autodrive_editor.rendering.visibility import Visibility
from autodrive_editor.settings import app_settings
from autodrive_editor.settings.app_settings import AppSettings

pytestmark = pytest.mark.usefixtures("isolated_user_data")


def test_settings_live_in_the_user_data_folder(isolated_user_data):
    settings = AppSettings()

    assert settings.settings_path == isolated_user_data / "settings.ini"


def test_game_folder_is_kept_between_sessions(tmp_path):
    AppSettings().set_game_folder(tmp_path / "fs25")

    assert AppSettings().game_folder.path == tmp_path / "fs25"


def test_game_folder_can_be_cleared(tmp_path):
    settings = AppSettings()
    settings.set_game_folder(tmp_path)

    settings.set_game_folder(None)

    assert AppSettings().game_folder is None


def test_first_start_stores_detected_game_folder(tmp_path, monkeypatch):
    fake = make_game_folder(tmp_path / "FarmingSimulator2025")
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: fake))

    folder = AppSettings().ensure_game_folder()

    assert folder.path == fake
    assert AppSettings().game_folder.path == fake


def test_configured_game_folder_is_not_replaced_by_detection(tmp_path, monkeypatch):
    fake = make_game_folder(tmp_path / "FarmingSimulator2025")
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: fake))
    settings = AppSettings()
    settings.set_game_folder(tmp_path / "my_own_choice")

    assert settings.ensure_game_folder().path == tmp_path / "my_own_choice"


def test_without_game_folder_nothing_is_stored(tmp_path, monkeypatch):
    monkeypatch.setattr(GameFolder, "default_path", staticmethod(lambda: tmp_path / "none"))

    assert AppSettings().ensure_game_folder() is None


def test_install_folder_is_detected_and_kept(tmp_path, isolated_user_data, monkeypatch):
    install = make_installation(tmp_path / "FS25")
    monkeypatch.setattr(
        GameInstallation, "detect", classmethod(lambda cls: GameInstallation(install))
    )

    assert AppSettings().ensure_install_folder().path == install
    assert AppSettings().install_folder.path == install


def test_install_folder_can_be_cleared(tmp_path, isolated_user_data):
    settings = AppSettings()
    settings.set_install_folder(tmp_path)
    settings.set_install_folder(None)

    assert AppSettings().install_folder is None


def test_setup_is_needed_until_marked_done(tmp_path, isolated_user_data):
    settings = AppSettings()
    assert settings.needs_setup

    settings.mark_setup_done()

    assert not AppSettings().needs_setup


def test_setup_is_needed_again_when_a_folder_is_gone(tmp_path, isolated_user_data):
    settings = AppSettings()
    settings.set_game_folder(make_game_folder(tmp_path / "fs25"))
    settings.set_install_folder(make_installation(tmp_path / "install"))
    settings.mark_setup_done()
    assert not settings.needs_setup

    settings.set_install_folder(tmp_path / "moved")

    assert settings.needs_setup


def test_empty_folders_do_not_ask_again(isolated_user_data):
    settings = AppSettings()
    settings.mark_setup_done()

    assert not settings.needs_setup


def test_path_options_are_kept_between_sessions():
    options = PathOptions(7.5, ConnectionType.DUAL, SUBPRIO_FLAG, control_points=1)

    AppSettings().set_path_options(options)

    assert AppSettings().path_options == options


def test_path_options_default_without_stored_values():
    assert AppSettings().path_options == PathOptions()


def test_invalid_stored_path_options_fall_back_to_defaults():
    settings = AppSettings()
    settings.set_path_options(PathOptions(7.5, ConnectionType.DUAL, SUBPRIO_FLAG))
    settings._settings.setValue(AppSettings.PATH_CONNECTION_KEY, "nonsense")

    assert AppSettings().path_options == PathOptions()


def test_invalid_stored_control_points_fall_back_to_defaults():
    AppSettings()._settings.setValue(AppSettings.PATH_CONTROL_POINTS_KEY, 3)

    assert AppSettings().path_options == PathOptions()


def test_rotate_snap_angle_defaults_to_15_and_is_kept():
    assert AppSettings().rotate_snap_angle == 15.0

    AppSettings().set_rotate_snap_angle(7.5)

    assert AppSettings().rotate_snap_angle == 7.5


def test_check_tolerances_default_and_are_kept_between_sessions():
    assert AppSettings().check_tolerances == (0.1, 5.0)

    AppSettings().set_check_tolerances(0.25, 3)

    assert AppSettings().check_tolerances == (0.25, 3.0)


def test_language_follows_windows_until_one_is_chosen(monkeypatch):
    monkeypatch.setattr(app_settings, "system_language", lambda: "de")
    assert AppSettings().language == "de"

    AppSettings().set_language("en")

    assert AppSettings().language == "en"


def test_unknown_stored_language_falls_back_to_windows(monkeypatch):
    monkeypatch.setattr(app_settings, "system_language", lambda: "de")
    AppSettings().set_language("fr")

    assert AppSettings().language == "de"


def test_visibility_defaults_and_is_kept_between_sessions():
    assert AppSettings().visibility == Visibility()

    shown = Visibility(
        nodes=False, node_ids=True, reverse_connections=False, hidden_selectable=True
    )
    AppSettings().set_visibility(shown)

    assert AppSettings().visibility == shown


def test_each_visibility_switch_is_stored_on_its_own():
    settings = AppSettings()
    settings.set_visibility(Visibility(parking=False))

    assert settings._settings.value("view/show_parking", type=bool) is False
    assert settings._settings.value("view/show_nodes", type=bool) is True


def test_theme_follows_windows_until_chosen():
    assert AppSettings().theme == "system"

    AppSettings().set_theme("dark")

    assert AppSettings().theme == "dark"


def test_unknown_theme_falls_back_to_windows():
    AppSettings().set_theme("purple")

    assert AppSettings().theme == "system"


def test_changed_shortcuts_are_kept_between_sessions():
    AppSettings().set_shortcuts({"save_xml": ["Ctrl+Alt+S"], "exit": []})

    assert AppSettings().shortcuts == {"save_xml": ["Ctrl+Alt+S"], "exit": []}


def test_unreadable_shortcuts_are_left_out():
    settings = AppSettings()
    settings._settings.setValue(AppSettings.SHORTCUTS_KEY, "not json")
    assert settings.shortcuts == {}

    settings.set_shortcuts({"save_xml": "Ctrl+S", "exit": [1], "copy": ["Ctrl+C"]})
    assert settings.shortcuts == {"copy": ["Ctrl+C"]}


def test_update_check_is_off_until_turned_on():
    assert not AppSettings().check_updates

    AppSettings().set_check_updates(True)

    assert AppSettings().check_updates


def test_savegame_question_can_be_turned_off_per_route(tmp_path):
    settings = AppSettings()
    settings.set_asks_for_savegame(tmp_path / "a.xml", False)

    reloaded = AppSettings()
    assert not reloaded.asks_for_savegame(tmp_path / "a.xml")
    assert reloaded.asks_for_savegame(tmp_path / "b.xml")

    reloaded.set_asks_for_savegame(tmp_path / "a.xml", True)
    assert AppSettings().asks_for_savegame(tmp_path / "a.xml")


def test_parking_templates_are_kept_per_shed_type():
    AppSettings().save_parking_template("a.xml", "Big", {"bays": 2})
    AppSettings().save_parking_template("a.xml", "Small", {"bays": 5})
    AppSettings().save_parking_template("b.xml", "Other", {"bays": 1})

    settings = AppSettings()

    assert settings.parking_templates("a.xml") == {"Big": {"bays": 2}, "Small": {"bays": 5}}
    assert settings.last_parking_template("a.xml") == "Small"
    assert settings.parking_templates("c.xml") == {}
    assert settings.last_parking_template("c.xml") is None


def test_last_parking_template_follows_loading_and_deleting():
    settings = AppSettings()
    settings.save_parking_template("a.xml", "Big", {})
    settings.save_parking_template("a.xml", "Small", {})

    settings.set_last_parking_template("a.xml", "Big")
    assert settings.last_parking_template("a.xml") == "Big"

    settings.delete_parking_template("a.xml", "Big")
    assert settings.parking_templates("a.xml") == {"Small": {}}
    assert settings.last_parking_template("a.xml") is None
