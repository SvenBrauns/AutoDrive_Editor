from autodrive_editor.file_io.savegame_vehicles import (
    SavegameVehicle,
    read_park_destinations,
    read_vehicles,
    renumber_vehicle_markers,
    set_park_destinations,
    vehicles_losing_markers,
)

VEHICLES = (
    '﻿<?xml version="1.0" encoding="utf-8" standalone="no"?>\r\n<vehicles>\r\n'
    '    <vehicle filename="data/vehicles/fendt/vario1050.xml" uniqueId="v1">\r\n'
    '        <AutoDrive mode="1" firstMarker="2" secondMarker="3" driverName="1050 Vario"'
    ' active="false"/>\r\n'
    "    </vehicle>\r\n"
    '    <vehicle filename="$moddir$Map/vehicles/wagonGrainEU.xml" uniqueId="v2">\r\n'
    '        <AutoDrive parkDestination="3"/>\r\n'
    "    </vehicle>\r\n"
    "</vehicles>\r\n"
)


def write_vehicles(tmp_path):
    path = tmp_path / "vehicles.xml"
    path.write_bytes(VEHICLES.encode("utf-8"))
    return path


def test_marker_numbers_follow_the_new_order(tmp_path):
    path = write_vehicles(tmp_path)

    affected = renumber_vehicle_markers(path, {1: 1, 2: 5, 3: 2})

    assert affected == []
    expected = (
        VEHICLES.replace('firstMarker="2"', 'firstMarker="5"')
        .replace('secondMarker="3"', 'secondMarker="2"')
        .replace('parkDestination="3"', 'parkDestination="2"')
    )
    assert path.read_bytes() == expected.encode("utf-8")


def test_deleted_marker_resets_targets_and_removes_park_destination(tmp_path):
    path = write_vehicles(tmp_path)

    affected = renumber_vehicle_markers(path, {1: 1, 2: 2, 3: None})

    assert affected == ["1050 Vario", "wagonGrainEU"]
    text = path.read_text(encoding="utf-8-sig")
    assert 'firstMarker="2" secondMarker="1" driverName="1050 Vario"' in text
    assert "<AutoDrive/>" in text


def test_vehicles_losing_markers_are_named_without_changing_the_file(tmp_path):
    path = write_vehicles(tmp_path)

    assert vehicles_losing_markers(path, {1: 1, 2: 2, 3: None}) == ["1050 Vario", "wagonGrainEU"]
    assert path.read_bytes() == VEHICLES.encode("utf-8")


def test_unchanged_numbers_leave_the_file_alone(tmp_path):
    path = write_vehicles(tmp_path)

    assert renumber_vehicle_markers(path, {1: 1, 2: 2, 3: 3}) == []
    assert path.read_bytes() == VEHICLES.encode("utf-8")


def test_park_destinations_are_read_from_the_vehicles(tmp_path):
    assert read_park_destinations(write_vehicles(tmp_path)) == {3}


def test_vehicles_without_park_destination_give_none(tmp_path):
    path = tmp_path / "vehicles.xml"
    path.write_text('<vehicles><vehicle><AutoDrive firstMarker="1"/></vehicle></vehicles>')

    assert read_park_destinations(path) == set()


FARM = (
    '<?xml version="1.0" encoding="utf-8" standalone="no"?>\r\n<vehicles>\r\n'
    '    <vehicle filename="data/vehicles/vario1000.xml" uniqueId="tractor" farmId="1">\r\n'
    "        <attacherJoints>\r\n"
    '            <attachedImplement jointIndex="1" attachedVehicleUniqueId="weight"/>\r\n'
    "        </attacherJoints>\r\n"
    '        <AutoDrive mode="1" firstMarker="2" driverName="Vario"/>\r\n'
    "    </vehicle>\r\n"
    '    <vehicle filename="data/vehicles/weight3300.xml" uniqueId="weight" farmId="1">\r\n'
    "        <attachable/>\r\n"
    '        <AutoDrive parkDestination="7"/>\r\n'
    "    </vehicle>\r\n"
    '    <vehicle filename="data/vehicles/gx520.xml" uniqueId="trailer" farmId="1">\r\n'
    "        <attachable/>\r\n"
    "    </vehicle>\r\n"
    '    <vehicle filename="data/vehicles/wagon.xml" uniqueId="wagon" farmId="0">\r\n'
    "        <attachable/>\r\n"
    "    </vehicle>\r\n"
    '    <vehicle filename="data/objects/pallet.xml" uniqueId="pallet" farmId="1">\r\n'
    "    </vehicle>\r\n"
    "</vehicles>\r\n"
)


def write_farm(tmp_path):
    path = tmp_path / "vehicles.xml"
    path.write_bytes(FARM.encode("utf-8"))
    return path


def test_farm_vehicles_and_implements_are_read_with_their_parking_position(tmp_path):
    assert read_vehicles(write_farm(tmp_path)) == [
        SavegameVehicle("tractor", "data/vehicles/vario1000.xml", "Vario", "", None),
        SavegameVehicle("weight", "data/vehicles/weight3300.xml", "", "tractor", 7),
        SavegameVehicle("trailer", "data/vehicles/gx520.xml", "", "", None),
    ]


def test_park_destinations_are_set_changed_and_removed(tmp_path):
    path = write_farm(tmp_path)

    set_park_destinations(path, {"tractor": 3, "weight": None, "trailer": 12})

    expected = (
        FARM.replace('<AutoDrive mode="1"', '<AutoDrive parkDestination="3" mode="1"')
        .replace('<AutoDrive parkDestination="7"/>', "<AutoDrive/>")
        .replace(
            '<attachable/>\r\n    </vehicle>\r\n    <vehicle filename="data/vehicles/wagon',
            '<attachable/>\r\n        <AutoDrive parkDestination="12"/>\r\n'
            '    </vehicle>\r\n    <vehicle filename="data/vehicles/wagon',
        )
    )
    assert path.read_bytes() == expected.encode("utf-8-sig")
    assert [v.park for v in read_vehicles(path)] == [3, None, 12]
