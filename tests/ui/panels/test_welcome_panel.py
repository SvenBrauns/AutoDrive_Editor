from PySide6.QtWidgets import QPushButton

from autodrive_editor.model.autodrive_data import AutoDriveData


def test_welcome_panel_offers_the_open_actions(window):
    labels = [button.text() for button in window.welcome_panel.findChildren(QPushButton)]

    assert labels == [
        window.actions.open_route_action.text(),
        window.actions.open_savegame_action.text(),
        window.actions.load_xml_action.text(),
    ]


def test_welcome_panel_hides_once_data_is_loaded(window):
    window.show()
    assert window.welcome_panel.isVisible()

    window._handle_autodrive_data_loaded(AutoDriveData())

    assert not window.welcome_panel.isVisible()
