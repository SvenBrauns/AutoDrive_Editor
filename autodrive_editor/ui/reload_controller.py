"""Reload in game, proof of concept (hidden, Ctrl+Alt+Shift+R): writes the open network as a
route file into the companion mod's folder and asks the running game to load it.

The texts are not translated while this is a test."""

import time
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence

from autodrive_editor.file_io.autodrive_xml_writer import write_route_export
from autodrive_editor.game import editor_link
from autodrive_editor.game.savegame_info import read_savegame_info
from autodrive_editor.ui.picture_capture_controller import check_game

SHORTCUT = "Ctrl+Alt+Shift+R"
# The mod reads the request within a second; a large network takes a few seconds to load.
TIMEOUT_SEC = 30


class ReloadController(QObject):
    status_changed = Signal(str)

    def __init__(self, window, settings, project_coordinator):
        super().__init__(window)

        self.settings = settings
        self.project_coordinator = project_coordinator
        self.link = None
        self.request_id: int | None = None
        self.started_at = 0.0
        self.export_sec = 0.0

        self.action = QAction(window)
        self.action.setShortcut(QKeySequence(SHORTCUT))
        self.action.triggered.connect(self.reload)
        window.addAction(self.action)

        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self._poll)

    def reload(self):
        if self.request_id is not None:
            return

        data = self.project_coordinator.autodrive_data
        game_folder = self.settings.game_folder
        savegame_folder = self.project_coordinator.savegame_folder()

        if data is None or game_folder is None or not game_folder.is_valid:
            self.status_changed.emit("Reload in game: open a config and set the FS25 user folder.")
            return

        if savegame_folder is None:
            self.status_changed.emit("Reload in game: open a savegame first.")
            return

        savegame = read_savegame_info(savegame_folder)
        link = editor_link.link_directory(game_folder.path)
        ready, text = check_game(link, savegame)

        if not ready:
            self.status_changed.emit(f"Reload in game: {text}")
            return

        self.link, self.request_id = link, editor_link.new_request_id(datetime.now())
        self.started_at = time.monotonic()
        editor_link.clean_up(link)
        write_route_export(data, link / editor_link.network_file_name(self.request_id))
        self.export_sec = time.monotonic() - self.started_at
        editor_link.write_reload_request(
            link, self.request_id, savegame.map_id, str(savegame.number)
        )

        self.status_changed.emit(f"Reload in game: sent {len(data.nodes)} nodes…")
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
            self.status_changed.emit(f"Reload in game: no answer after {TIMEOUT_SEC} s.")
        elif result.status != "done" or result.reload is None:
            self.status_changed.emit(f"Reload in game failed: {result.message}")
        else:
            info = result.reload
            self.status_changed.emit(
                f"Reloaded in game: {info.nodes} nodes, {info.markers} markers, "
                f"{info.groups} groups · export {self.export_sec:.2f} s, "
                f"read {info.read_sec:.2f} s, upload {info.upload_sec:.2f} s, "
                f"total {seconds:.1f} s"
            )
