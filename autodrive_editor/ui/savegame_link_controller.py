from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget

from autodrive_editor.file_io.autodrive_xml import ConfigFormat, ConfigSource
from autodrive_editor.file_io.project_file import ProjectFileStore
from autodrive_editor.game.savegame_info import SavegameInfo, savegames_with_autodrive
from autodrive_editor.i18n import tr
from autodrive_editor.project.project_coordinator import ProjectCoordinator
from autodrive_editor.settings.app_settings import AppSettings
from autodrive_editor.ui.dialogs.messages import APP_TITLE, inform
from autodrive_editor.ui.dialogs.savegame_link_dialog import SavegameLinkDialog


class SavegameLinkController(QObject):
    """Links a savegame to the loaded route, so the parking positions of its
    vehicles are shown. The link is kept in the route's project file; without
    a project it lasts for this session."""

    status_changed = Signal(str)

    def __init__(
        self,
        window: QWidget,
        settings: AppSettings,
        project_coordinator: ProjectCoordinator,
        project_files: ProjectFileStore,
    ):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.project_coordinator = project_coordinator
        self.project_files = project_files

    def offer_link(self):
        """After a route was opened: takes the link from its project, or asks
        for a savegame unless that is turned off for the route."""

        source = self._route_source()

        if source is None or self.project_coordinator.savegame_directory is not None:
            return

        project_path = self._project_path(source.path)

        if project_path is not None:
            savegame = self.project_files.stored_savegame(project_path)

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

        project_path = self._project_path(source.path)

        if project_path is None and savegame is not None:
            project_path = self._create_project(source)

        if project_path is not None:
            self.project_files.set_savegame(project_path, directory)

        if savegame is None:
            self.status_changed.emit(tr("Savegame link removed"))
        elif project_path is None:
            self.status_changed.emit(
                tr("“{name}” linked for this session", name=savegame.display_name)
                + self.project_coordinator.sheds_note
            )
        else:
            self.status_changed.emit(
                tr("“{name}” linked", name=savegame.display_name)
                + self.project_coordinator.sheds_note
            )

    def _create_project(self, source: ConfigSource) -> Path | None:
        """Offers to save a project for the route, so the link is kept."""

        config_path = self._ask_project_path(source)

        if config_path is None:
            return None

        try:
            return self.project_coordinator.save_project_file(config_path)
        except Exception as ex:
            self._inform(tr("The project could not be saved: {error}", error=ex))
            return None

    def _ask_project_path(self, source: ConfigSource) -> Path | None:
        answer = QMessageBox.question(
            self.window,
            APP_TITLE,
            tr(
                "The route has no project, so the link is only kept for this session. "
                "Create a project to keep it?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        if answer != QMessageBox.Yes:
            return None

        default_path = self.project_files.projects_directory / f"{source.display_name}.json"
        config_path, _ = QFileDialog.getSaveFileName(
            self.window, tr("Save project"), str(default_path), tr("JSON project (*.json)")
        )

        return Path(config_path) if config_path else None

    def _project_path(self, xml_path: Path) -> Path | None:
        """The open project if it belongs to the route, else a project in the
        projects folder that does."""

        current = self.project_coordinator.current_config_path

        if current and self.project_files.project_uses(current, xml_path):
            return Path(current)

        return self.project_files.find_project_for(xml_path)

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
