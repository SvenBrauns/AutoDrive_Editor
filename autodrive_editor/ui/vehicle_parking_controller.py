"""Edit → Vehicle parking positions: shows the vehicles and implements of the loaded savegame and
sets their parking markers. While the game runs the savegame with the companion mod, the vehicles
come from the game and the changes go straight into it; otherwise from and into vehicles.xml."""

import time
from datetime import datetime
from pathlib import Path, PurePosixPath

from PySide6.QtCore import QEventLoop, QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from autodrive_editor.file_io.autodrive_xml import ConfigFormat
from autodrive_editor.file_io.savegame_vehicles import (
    SavegameVehicle,
    read_vehicles,
)
from autodrive_editor.game import editor_link
from autodrive_editor.game.game_process import game_is_running
from autodrive_editor.game.savegame_info import read_savegame_info
from autodrive_editor.game.vehicle_store import store_info
from autodrive_editor.i18n import tr
from autodrive_editor.ui.dialogs.messages import APP_TITLE, inform
from autodrive_editor.ui.dialogs.vehicle_parking_dialog import VehicleParkingDialog, VehicleRow
from autodrive_editor.ui.picture_capture_controller import check_game

# The mod answers within a second or two; a reload just started can take a few more.
TIMEOUT_SEC = 30


class VehicleParkingController(QObject):
    status_changed = Signal(str)

    def __init__(self, window, settings, project_coordinator, edit_history, files, reload, capture):
        super().__init__(window)

        self.window = window
        self.settings = settings
        self.project_coordinator = project_coordinator
        self.edit_history = edit_history
        self.files = files
        self.reload = reload
        self.capture = capture
        self.last_request_id = 0

    def open(self):
        coordinator = self.project_coordinator
        source = coordinator.config_source

        if source is None or source.format != ConfigFormat.SAVEGAME:
            self._inform(tr("Open a savegame to set the parking positions of its vehicles."))
            return

        if not self.edit_history.is_clean and not self._save_first():
            return

        link, savegame = self._game_link(source.path)

        if link is not None:
            self._edit_in_game(link, savegame)
        else:
            self._edit_file(source.path.parent / "vehicles.xml")

    def _save_first(self) -> bool:
        answer = QMessageBox.question(
            self.window,
            APP_TITLE,
            tr(
                "Parking positions are marker numbers of the saved network. Save the network first?"
            ),
            QMessageBox.Save | QMessageBox.Cancel,
            QMessageBox.Save,
        )

        return answer == QMessageBox.Save and self.files.save_xml()

    def _game_link(self, config_path: Path):
        """The exchange folder and savegame if the game runs this savegame with the mod."""

        game_folder = self.settings.game_folder

        if (
            game_folder is None
            or not game_folder.is_valid
            or config_path.parent.parent != game_folder.path.resolve()
        ):
            return None, None

        savegame = read_savegame_info(config_path.parent)
        link = editor_link.link_directory(game_folder.path)

        return (link, savegame) if check_game(link, savegame)[0] else (None, None)

    def _edit_in_game(self, link: Path, savegame):
        if self.capture.running:
            self._inform(tr("A game picture capture is running. Try again when it is done."))
            return

        result = self._ask_game(
            link,
            lambda request_id: editor_link.write_vehicles_request(
                link, request_id, savegame.map_id, str(savegame.number)
            ),
        )

        if result is None:
            return

        changes = self._run_dialog(list(result.vehicles))

        if not changes:
            return

        result = self._ask_game(
            link,
            lambda request_id: editor_link.write_park_request(
                link, request_id, savegame.map_id, str(savegame.number), changes
            ),
        )

        if result is not None:
            parks = {changes.get(v.unique_id, v.park) for v in self._vehicles}
            self.project_coordinator.show_game_parking({number for number in parks if number})
            self.status_changed.emit(
                tr("Parking positions set in the game ({count})", count=len(changes))
            )

    def _edit_file(self, vehicles_path: Path):
        if not vehicles_path.is_file():
            self._inform(tr("The savegame has no vehicles.xml."))
            return

        if game_is_running():
            self._inform(
                tr(
                    "The game is running, but not this savegame with the mod "
                    "FS25_AutoDriveEditorLink. If it runs this savegame, it overwrites the "
                    "parking positions on its next save."
                )
            )

        changes = self._run_dialog(read_vehicles(vehicles_path))

        if not changes:
            return

        self.project_coordinator.set_park_destinations(changes)
        self.status_changed.emit(
            tr("Parking positions saved in vehicles.xml ({count})", count=len(changes))
        )

    def _run_dialog(self, vehicles: list[SavegameVehicle]) -> dict[str, int | None]:
        self._vehicles = vehicles

        if not vehicles:
            self._inform(tr("The savegame has no vehicles AutoDrive can park."))
            return {}

        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            rows = self._rows(vehicles)
        finally:
            QApplication.restoreOverrideCursor()

        data = self.project_coordinator.autodrive_data
        markers = sorted(
            (
                (number, f"{marker.name} ({marker.group})")
                for number, marker in enumerate(data.markers.values(), start=1)
            ),
            key=lambda item: item[1].lower(),
        )
        dialog = VehicleParkingDialog(rows, markers, parent=self.window)

        return dialog.changes() if self.window._run_dialog(dialog) else {}

    def _rows(self, vehicles: list[SavegameVehicle]) -> list[VehicleRow]:
        """Each vehicle followed by the implements attached to it."""

        install = self.settings.install_folder
        game_folder = self.settings.game_folder
        install_path = install.path if install is not None else None
        mods_path = game_folder.mods_directory if game_folder is not None else None
        infos = {v.unique_id: store_info(v.filename, install_path, mods_path) for v in vehicles}
        names = {}

        for vehicle in vehicles:
            name = vehicle.name or infos[vehicle.unique_id].name
            name = name or PurePosixPath(vehicle.filename).stem

            if vehicle.driver_name and vehicle.driver_name != name:
                name = f"{name} · {vehicle.driver_name}"

            names[vehicle.unique_id] = name

        children: dict[str, list[SavegameVehicle]] = {}

        for vehicle in vehicles:
            children.setdefault(vehicle.attached_to, []).append(vehicle)

        rows = []

        def add(parent_id: str):
            for vehicle in sorted(children.get(parent_id, []), key=lambda v: names[v.unique_id]):
                rows.append(
                    VehicleRow(
                        vehicle.unique_id,
                        names[vehicle.unique_id],
                        names.get(vehicle.attached_to, ""),
                        vehicle.park,
                        infos[vehicle.unique_id].image,
                    )
                )
                add(vehicle.unique_id)

        known = {v.unique_id for v in vehicles}
        add("")

        # Implements of a vehicle not in the list (e.g. a train) are shown on their own.
        for parent_id in children:
            if parent_id and parent_id not in known:
                add(parent_id)

        return rows

    def _ask_game(self, link: Path, write_request) -> editor_link.CaptureResult | None:
        """Writes a request and waits for the mod's answer; tells the user if there is none."""

        deadline = time.monotonic() + TIMEOUT_SEC
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            # A reload after Save uses the same folder.
            while self.reload.request_id is not None and time.monotonic() < deadline:
                self._wait()

            request_id = max(editor_link.new_request_id(datetime.now()), self.last_request_id + 1)
            self.last_request_id = request_id
            editor_link.clean_up(link)
            write_request(request_id)

            while (result := editor_link.read_result(link, request_id)) is None:
                if time.monotonic() >= deadline:
                    break

                self._wait()

            editor_link.clean_up(link)
        finally:
            QApplication.restoreOverrideCursor()

        if result is None:
            self._inform(tr("The game did not answer within {seconds} s.", seconds=TIMEOUT_SEC))
        elif result.status != "done":
            self._inform(tr("The game reported: {message}", message=result.message))
            return None

        return result

    @staticmethod
    def _wait():
        QApplication.processEvents(QEventLoop.AllEvents, 50)
        time.sleep(0.05)

    def _inform(self, message: str):
        inform(self.window, message)
