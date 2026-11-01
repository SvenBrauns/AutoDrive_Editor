"""Map → Capture game picture: asks the companion mod for the whole map, or with the refresh
tool for the marked tiles, shows the progress in the status bar and puts the tiles into the
shown picture as they arrive."""

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMessageBox, QPushButton, QWidget

from autodrive_editor.file_io.map_mod import BASE_MAP_SIZE
from autodrive_editor.game import editor_link
from autodrive_editor.game.editor_link import CaptureResult
from autodrive_editor.game.savegame_info import SavegameInfo, read_savegame_info
from autodrive_editor.i18n import tr
from autodrive_editor.terrain.game_picture import PICTURE_FOLDER, GamePicture, PictureGrid
from autodrive_editor.terrain.picture_capture import PictureCapture, estimate, whole_map_tiles
from autodrive_editor.ui.dialogs.messages import APP_TITLE, inform
from autodrive_editor.ui.dialogs.picture_capture_dialog import PictureCaptureDialog, minutes
from autodrive_editor.ui.tools.picture_refresh_tool import PictureRefreshTool

# Conversion and level builds; more do not help, the game delivers a tile every ~0.6 s.
WORKERS = 3


@dataclass(frozen=True)
class CaptureTarget:
    link: Path
    picture_directory: Path
    map_size: float
    savegame: SavegameInfo


class PictureCaptureController(QObject):
    status_changed = Signal(str)
    # A new picture is shown; the window switches the background to it.
    picture_shown = Signal()
    running_changed = Signal(bool)
    refresh_active_changed = Signal(bool)

    def __init__(self, window, settings, project_coordinator, background_map):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.project_coordinator = project_coordinator
        self.background_map = background_map
        self.capture: PictureCapture | None = None
        self.executor: ThreadPoolExecutor | None = None
        self.started_at = 0.0
        self.wait_ms = 0
        self.refreshing = False
        self.refresh_tool: PictureRefreshTool | None = None
        self.refresh_target: CaptureTarget | None = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._poll)

        self.progress = QWidget(window)
        self.progress_label = QLabel(self.progress)
        self.cancel_button = QPushButton(tr("Cancel"), self.progress)
        self.cancel_button.clicked.connect(self.cancel)
        layout = QHBoxLayout(self.progress)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.cancel_button)
        self.progress.hide()
        window.statusBar().addPermanentWidget(self.progress)

    @property
    def running(self) -> bool:
        return self.capture is not None

    def open_dialog(self):
        if self.running:
            return

        target, problem = self._target()
        current = GamePicture.open(target.picture_directory) if target else None
        dialog = PictureCaptureDialog(
            lambda: self._check(target, problem),
            target.map_size if target else BASE_MAP_SIZE,
            current.grid.m_per_px if current else None,
            self.settings.picture_wait_ms,
            self.window,
        )

        if not self._run_dialog(dialog):
            return

        self.settings.set_picture_wait_ms(dialog.wait_ms)
        grid = PictureGrid(target.map_size, dialog.m_per_px)
        picture = GamePicture.open_or_create(target.picture_directory, grid)
        self.background_map.set_picture(picture)
        self.picture_shown.emit()
        self._start(target, picture, whole_map_tiles(grid), dialog.wait_ms)

    def set_refresh_active(self, active: bool):
        """Turns the refresh tool on or off. On, it shows the grid of the linked savegame's
        picture; it stays off if there is none or a capture runs."""

        if active == (self.refresh_tool is not None):
            return

        if not active:
            self.refresh_tool = self.refresh_target = None
            self.window.view.set_overlay_tool(None)
            self.refresh_active_changed.emit(False)
            return

        target, problem = self._target()
        picture = self._shown_picture(target) if target else None

        if self.running or picture is None:
            if not self.running:
                self._inform(
                    problem or tr("Capture the whole map first (Map → Capture game picture…).")
                )

            self.refresh_active_changed.emit(False)
            return

        self.picture_shown.emit()
        self.refresh_target = target
        self.refresh_tool = PictureRefreshTool(
            self.window.view,
            picture,
            self.settings.picture_wait_ms,
            self._refresh,
            lambda: self.set_refresh_active(False),
            self.status_changed.emit,
        )
        self.window.view.set_overlay_tool(self.refresh_tool)
        self.refresh_active_changed.emit(True)

    def cancel(self):
        if not self.running:
            return

        self.capture.cancel()
        self.cancel_button.setEnabled(False)
        self.progress_label.setText(tr("Game picture: cancelling…"))

    def confirm_stop(self) -> bool:
        """Before the editor closes or loads another file: asks whether to cancel a running
        capture. Returns whether to go on."""

        self.set_refresh_active(False)

        if not self.running:
            return True

        answer = QMessageBox.question(
            self.window,
            APP_TITLE,
            tr("A game picture capture is running. Cancel it?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return False

        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            self.capture.stop()
        finally:
            QApplication.restoreOverrideCursor()

        self._finish()
        return True

    def _target(self) -> tuple[CaptureTarget | None, str]:
        """Where the picture goes, or why there is no such place."""

        game_folder = self.settings.game_folder

        if game_folder is None or not game_folder.is_valid:
            return None, tr("Set the FS25 user folder in the settings first.")

        cached = self.project_coordinator.loaded_map()

        if cached is None:
            return None, tr("Open a config of an imported map first.")

        savegame_folder = self.project_coordinator.savegame_folder()

        if savegame_folder is None:
            return None, tr("Link a savegame to the route first (File → Link savegame…).")

        savegame = read_savegame_info(savegame_folder)
        directory = cached.directory / PICTURE_FOLDER / str(savegame.number)
        link = editor_link.link_directory(game_folder.path)

        return CaptureTarget(link, directory, cached.map_scale * BASE_MAP_SIZE, savegame), ""

    @staticmethod
    def _check(target: CaptureTarget | None, problem: str) -> tuple[bool, str]:
        """Whether the game runs the target's map and savegame, and a line saying so."""

        if target is None:
            return False, problem

        status = editor_link.read_status(target.link)
        savegame = target.savegame

        if status is None or not status.is_fresh(datetime.now()):
            return False, tr(
                "The game is not running, or the mod FS25_AutoDriveEditorLink is not active."
            )

        if status.map_id != savegame.map_id:
            return False, tr("The game runs another map: {map}.", map=status.map_id)

        if status.savegame != str(savegame.number):
            return False, tr(
                "The game runs savegame {game}, the editor shows savegame {editor}.",
                game=status.savegame,
                editor=savegame.number,
            )

        return True, tr(
            "Connected: {map}, savegame {number}", map=savegame.map_title, number=savegame.number
        )

    def _shown_picture(self, target: CaptureTarget) -> GamePicture | None:
        """The target's picture, put into the background unless it is shown already."""

        shown = self.background_map.picture

        if shown is not None and shown.directory == target.picture_directory:
            return shown

        picture = GamePicture.open(target.picture_directory)

        if picture is not None:
            self.background_map.set_picture(picture)

        return picture

    def _refresh(self, tiles: list[tuple[int, int]]):
        ready, text = self._check(self.refresh_target, "")

        if not ready:
            self._inform(text)
            return

        target, picture = self.refresh_target, self.refresh_tool.picture
        self.set_refresh_active(False)
        self._start(target, picture, tiles, self.settings.picture_wait_ms, refreshing=True)

    def _start(
        self,
        target: CaptureTarget,
        picture: GamePicture,
        tiles: list[tuple[int, int]],
        wait_ms: int,
        refreshing: bool = False,
    ):
        self.refreshing = refreshing
        self.executor = ThreadPoolExecutor(max_workers=WORKERS)
        self.capture = PictureCapture.start(
            target.link,
            picture,
            tiles,
            self.executor,
            target.savegame.map_id,
            str(target.savegame.number),
            wait_ms,
        )
        self.started_at = time.monotonic()
        self.wait_ms = wait_ms

        self.cancel_button.setEnabled(True)
        self._update_progress()
        self.progress.show()
        self.timer.start()
        self.running_changed.emit(True)

    def _poll(self):
        try:
            self._show_written(self.capture.poll())
        except Exception as ex:
            self.capture.cancel()
            self.capture.result = CaptureResult("error", str(ex))
            self._finish()
            return

        if self.capture.finished:
            self._finish()
        else:
            self._update_progress()

    def _show_written(self, written):
        if written:
            self.background_map.picture_tiles_changed(written)

    def _update_progress(self):
        if not self.cancel_button.isEnabled():
            return

        done, total = self.capture.converted, len(self.capture.tiles)

        if done:
            left = (time.monotonic() - self.started_at) / done * (total - done)
        else:
            left = estimate(total, self.wait_ms)[0]

        self.progress_label.setText(
            tr(
                "Game picture {done}/{total} · {minutes} min left",
                done=done,
                total=total,
                minutes=minutes(left),
            )
        )

    def _finish(self):
        capture, self.capture = self.capture, None
        self.timer.stop()
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.executor = None
        self.progress.hide()
        self.running_changed.emit(False)

        result, done, total = capture.result, capture.converted, len(capture.tiles)

        if result.status == "done" and self.refreshing:
            self.status_changed.emit(tr("Game picture refreshed: {count} tiles", count=done))
        elif result.status == "done":
            self.status_changed.emit(tr("Game picture captured: {count} tiles", count=done))
        elif result.status == "cancelled":
            self.status_changed.emit(
                tr("Game picture cancelled: {done} of {total} tiles", done=done, total=total)
            )
        else:
            message = tr("The game picture could not be captured: {error}", error=result.message)
            self.status_changed.emit(message)
            self._inform(message)

    def _run_dialog(self, dialog: PictureCaptureDialog) -> bool:
        return bool(dialog.exec())

    def _inform(self, message: str):
        inform(self.window, message)
