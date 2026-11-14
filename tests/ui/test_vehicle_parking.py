"""Edit → Vehicle parking positions, on vehicles.xml and in the game with the mod played by the
test."""

import xml.etree.ElementTree as ET
from datetime import datetime

import pytest
from game_folder_helpers import add_savegame, make_game_folder

from autodrive_editor.editing.commands.markers import AddMarkerCommand
from autodrive_editor.file_io.savegame_vehicles import read_vehicles
from autodrive_editor.game import editor_link
from autodrive_editor.ui import vehicle_parking_controller

MAP_ID = "FS25_Test.SampleModMap"
VEHICLES = (
    '<vehicles><vehicle filename="data/vehicles/vario.xml" uniqueId="tractor" farmId="1">'
    '<AutoDrive mode="1" driverName="Vario"/></vehicle>'
    '<vehicle filename="data/vehicles/gx520.xml" uniqueId="trailer" farmId="1">'
    '<attachable/><AutoDrive parkDestination="1"/></vehicle></vehicles>'
)


@pytest.fixture
def parking_window(window, tmp_path, monkeypatch):
    """Savegame 1 with two vehicles and the saved markers Hof (1) and Feld (2)."""

    folder = make_game_folder(tmp_path / "FarmingSimulator2025")
    window.settings.set_game_folder(folder)
    savegame = add_savegame(folder, 1, "Spielstand", "LS25 Testkarte 2.0", "LS25_Testkarte_2_0")
    (savegame / "vehicles.xml").write_text(VEHICLES, encoding="utf-8")
    window.project_coordinator.load_xml_file(savegame / "AutoDrive_config.xml")
    data = window.project_coordinator.autodrive_data
    window.edit_history.push(AddMarkerCommand(data, 1, "Hof", "All"))
    window.edit_history.push(AddMarkerCommand(data, 2, "Feld", "All"))
    window.files.save_xml()

    monkeypatch.setattr(vehicle_parking_controller, "game_is_running", lambda: False)
    window.boxes = []
    monkeypatch.setattr(window.vehicle_parking, "_inform", window.boxes.append)
    window.vehicles_path = savegame / "vehicles.xml"
    window.link = editor_link.link_directory(folder)
    return window


def choose(monkeypatch, window, parks):
    """The user sets the parks (unique id -> marker number) in the dialog and presses OK."""

    shown = []

    def run(dialog):
        shown.append([(row.unique_id, row.name, row.attached_to, row.park) for row in dialog.rows])
        for unique_id, number in parks.items():
            dialog.set_park(unique_id, number)
        return True

    monkeypatch.setattr(window, "_run_dialog", run)
    return shown


def test_parking_positions_are_written_into_vehicles_xml(parking_window, monkeypatch):
    shown = choose(monkeypatch, parking_window, {"tractor": 2, "trailer": None})

    parking_window.vehicle_parking.open()

    assert shown == [[("trailer", "gx520", "", 1), ("tractor", "vario · Vario", "", None)]]
    vehicles = read_vehicles(parking_window.vehicles_path)
    assert {v.unique_id: v.park for v in vehicles} == {"tractor": 2, "trailer": None}


def test_in_the_running_game_the_mod_lists_and_parks_the_vehicles(parking_window, monkeypatch):
    link = parking_window.link
    link.mkdir(parents=True)
    (link / "status.xml").write_text(
        f'<status format="1" map="{MAP_ID}" savegame="1" '
        f'time="{datetime.now().isoformat(timespec="seconds")}"/>',
        encoding="utf-8",
    )
    requests = []

    def mod_answers():
        request = ET.parse(link / "request.xml").getroot()
        requests.append(request)
        vehicles = (
            '<vehicle uniqueId="tractor" filename="data/vehicles/vario.xml" name="Fendt Vario"'
            ' driverName="" attachedTo="" park="-1"/>'
            '<vehicle uniqueId="tool" filename="data/vehicles/gx520.xml" name="Krone GX 520"'
            ' driverName="" attachedTo="tractor" park="2"/>'
        )
        body = vehicles if request.get("type") == "vehicles" else ""
        name = f"result_{request.get('id')}"
        (link / f"{name}.xml").write_text(
            f'<result format="1" status="done" message="">{body}</result>', encoding="utf-8"
        )
        (link / f"{name}.done").write_bytes(b"")

    monkeypatch.setattr(parking_window.vehicle_parking, "_wait", mod_answers)
    shown = choose(monkeypatch, parking_window, {"tractor": 1})

    parking_window.vehicle_parking.open()

    assert shown == [
        [("tractor", "Fendt Vario", "", None), ("tool", "Krone GX 520", "Fendt Vario", 2)]
    ]
    assert [r.get("type") for r in requests] == ["vehicles", "park"]
    assert [v.attrib for v in requests[1].findall("park/vehicle")] == [
        {"uniqueId": "tractor", "marker": "1"}
    ]
    assert parking_window.boxes == []
    # vehicles.xml is the game's to write.
    assert {v.park for v in read_vehicles(parking_window.vehicles_path)} == {None, 1}


def test_a_route_has_no_vehicles(window, monkeypatch):
    boxes = []
    monkeypatch.setattr(window.vehicle_parking, "_inform", boxes.append)

    window.vehicle_parking.open()

    assert boxes == ["Open a savegame to set the parking positions of its vehicles."]
