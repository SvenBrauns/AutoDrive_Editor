from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QWidget

from autodrive_editor.file_io.autodrive_xml import ConfigFormat, ConfigSource
from autodrive_editor.game.savegame_info import SavegameInfo, savegames_with_autodrive
from autodrive_editor.i18n import tr
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.messages import inform
from autodrive_editor.ui.dialogs.savegame_link_dialog import SavegameLinkDialog


class SavegameLinkController(QObject):
    """Links a savegame to the loaded route, so the parking positions of its
    vehicles are shown. The link is remembered for the route."""

    status_changed = Signal(str)

    def __init__(
        self,
        window: QWidget,
        settings: AppSettings,
        project_coordinator: ProjectCoordinator,
    ):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.project_coordinator = project_coordinator

    def offer_link(self):
        """After a route was opened: takes its remembered link, or asks for a
        savegame unless that is turned off for the route."""

        source = self._route_source()

        if source is None or self.project_coordinator.savegame_directory is not None:
            return

        savegame = self.settings.linked_savegame(source.path)

        if savegame is not None:
            self.project_coordinator.set_savegame(savegame)
            return

        if not self.settings.asks_for_savegame(source.path):
            return

        game_folder = self.settings.game_folder

        if game_folder is None or not game_folder.is_valid:
            return

        savegames = savegames_with_autodrive(game_folder)

        if savegames:
            self._ask(source, savegames, asked_on_loading=True)

    def choose_link(self):
        """File → Link savegame…: links another savegame or removes the link."""

        source = self._route_source()

        if source is None:
            return

        game_folder = self.settings.game_folder

        if game_folder is None or not game_folder.is_valid:
            self._inform(
                tr("No valid FS25 game folder is set.\nPlease set it under File → Settings.")
            )
            return

        savegames = savegames_with_autodrive(game_folder)

        if not savegames:
            self._inform(tr("No savegame in the game folder contains AutoDrive data."))
            return

        self._ask(source, savegames, asked_on_loading=False)

    def _ask(self, source: ConfigSource, savegames: list[SavegameInfo], asked_on_loading: bool):
        dialog = SavegameLinkDialog(
            source.display_name,
            source.map_name or "",
            savegames,
            asked_on_loading,
            self.project_coordinator.savegame_directory,
            parent=self.window,
        )
        result = self._run_dialog(dialog)

        if dialog.dont_ask_again:
            self.settings.set_asks_for_savegame(source.path, False)

        if result == QDialog.DialogCode.Accepted and dialog.chosen_value is not None:
            self._link(source, dialog.chosen_value)
        elif result == SavegameLinkDialog.REMOVE:
            self._link(source, None)

    def _link(self, source: ConfigSource, savegame: SavegameInfo | None):
        directory = savegame.directory if savegame is not None else None
        self.project_coordinator.set_savegame(directory)
        self.settings.set_linked_savegame(source.path, directory)

        if savegame is None:
            self.status_changed.emit(tr("Savegame link removed"))
        else:
            self.status_changed.emit(
                tr("“{name}” linked", name=savegame.display_name)
                + self.project_coordinator.sheds_note
            )

    def _route_source(self) -> ConfigSource | None:
        source = self.project_coordinator.config_source

        if source is None or source.format != ConfigFormat.ROUTE_EXPORT:
            return None

        return source

    @staticmethod
    def _run_dialog(dialog: SavegameLinkDialog) -> int:
        return dialog.exec()

    def _inform(self, message: str):
        inform(self.window, message)
