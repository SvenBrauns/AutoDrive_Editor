"""Reload in game after Save: when the game runs the saved savegame, the companion mod loads the
saved network into the running game, so the game's next save does not overwrite it."""

import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from autodrive_editor.file_io.autodrive_xml import ConfigFormat
from autodrive_editor.file_io.autodrive_xml_writer import write_route_export
from autodrive_editor.game import editor_link
from autodrive_editor.game.game_process import game_is_running
from autodrive_editor.game.savegame_info import read_savegame_info
from autodrive_editor.i18n import tr
from autodrive_editor.ui.dialogs.messages import inform
from autodrive_editor.ui.picture_capture_controller import check_game

# The mod reads the request within a second; a large network takes a few seconds to load.
TIMEOUT_SEC = 30


class ReloadController(QObject):
    status_changed = Signal(str)

    def __init__(self, window, settings, project_coordinator):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.project_coordinator = project_coordinator
        self.link = None
        self.request_id: int | None = None
        self.started_at = 0.0

        # Savegames warned about in this session: the game runs them without the mod.
        self.warned_paths: set[Path] = set()

        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._poll)

    def after_save(self):
        """After Save on a savegame: reloads it in the game if the game runs exactly this
        savegame; warns if the game runs without the mod."""

        source = self.project_coordinator.config_source
        game_folder = self.settings.game_folder

        if (
            source is None
            or source.format != ConfigFormat.SAVEGAME
            or game_folder is None
            or not game_folder.is_valid
            # A savegame config copied elsewhere is not the game's.
            or source.path.parent.parent != game_folder.path.resolve()
            or self.request_id is not None
        ):
            return

        savegame = read_savegame_info(source.path.parent)
        link = editor_link.link_directory(game_folder.path)
        status = editor_link.read_status(link)

        if status is None or not status.is_fresh(datetime.now()):
            self._warn_without_mod(source.path)
            return

        if not check_game(link, savegame)[0]:
            return

        self._send(link, savegame)

    def _warn_without_mod(self, path: Path):
        if path in self.warned_paths or not game_is_running():
            return

        self.warned_paths.add(path)
        self._inform(
            tr(
                "Saved. The game is running, but the mod FS25_AutoDriveEditorLink does not "
                "answer, so the editor cannot reload the savegame in the game. The game "
                "overwrites the file on its next save: exit the game without saving, or "
                "install the mod."
            )
        )

    def _send(self, link: Path, savegame):
        data = self.project_coordinator.autodrive_data
        self.link, self.request_id = link, editor_link.new_request_id(datetime.now())
        self.started_at = time.monotonic()
        editor_link.clean_up(link)
        write_route_export(data, link / editor_link.network_file_name(self.request_id))
        editor_link.write_reload_request(
            link, self.request_id, savegame.map_id, str(savegame.number)
        )

        self.status_changed.emit(tr("Saved · reloading in game…"))
        self.timer.start()

    def _poll(self):
        result = editor_link.read_result(self.link, self.request_id)
        seconds = time.monotonic() - self.started_at

        if result is None and seconds < TIMEOUT_SEC:
            return

        self.timer.stop()
        editor_link.clean_up(self.link)
        self.request_id = None

        if result is None:
            self._not_reloaded(
                tr("The game did not answer within {seconds} s.", seconds=TIMEOUT_SEC)
            )
        elif result.status != "done" or result.reload is None:
            self._not_reloaded(result.message)
        else:
            self.status_changed.emit(
                tr(
                    "Saved · reloaded in game ({nodes} nodes, {seconds} s)",
                    nodes=result.reload.nodes,
                    seconds=f"{seconds:.1f}",
                )
            )

    def _not_reloaded(self, reason: str):
        self.status_changed.emit(tr("Saved"))
        self._inform(
            tr(
                "Saved, but not reloaded in the game: {reason}\n\n"
                "The game overwrites the file on its next save.",
                reason=reason,
            )
        )

    def _inform(self, message: str):
        inform(self.window, message)
