from autodrive_editor.file_io.savegame_vehicles import renumber_vehicle_markers

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


def test_unchanged_numbers_leave_the_file_alone(tmp_path):
    path = write_vehicles(tmp_path)

    assert renumber_vehicle_markers(path, {1: 1, 2: 2, 3: 3}) == []
    assert path.read_bytes() == VEHICLES.encode("utf-8")
