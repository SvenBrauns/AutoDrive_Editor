"""Parking positions of a savegame shown on a route.

Vehicles in vehicles.xml park at a marker number of the savegame's own
network (AutoDrive_config.xml). A route has its own marker order, so the
markers are matched by name and group:

    vehicles.xml          <AutoDrive parkDestination="931"/>
    AutoDrive_config.xml  <mm931><id>…</id><name>G1</name><group>15</group></mm931>
    route                 marker "G1" in group "15"
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from autodrive_editor.file_io.savegame_vehicles import read_park_destinations
from autodrive_editor.game.savegame_info import AUTODRIVE_CONFIG_NAME
from autodrive_editor.model.autodrive_data import MarkerData


def read_marker_keys(config_path: Path) -> list[tuple[str, str]]:
    """(name, group) of the savegame's markers, in number order."""

    def marker_number(element):
        suffix = element.tag.removeprefix("mm")
        return int(suffix) if suffix.isdigit() else 0

    markers = ET.parse(config_path).getroot().findall("mapmarker/*")

    return [
        ((marker.findtext("name") or "").strip(), (marker.findtext("group") or "").strip())
        for marker in sorted(markers, key=marker_number)
    ]


def match_park_markers(
    route_markers: list[MarkerData], savegame_keys: list[tuple[str, str]], park_numbers: set[int]
) -> list[MarkerData]:
    """The route markers the parked vehicles stand at. route_markers are in
    file order. If several route markers share name and group, the one with
    the same number is taken, if it is one of them."""

    matches = []

    for number in sorted(park_numbers):
        if not 1 <= number <= len(savegame_keys):
            continue

        key = savegame_keys[number - 1]
        candidates = [marker for marker in route_markers if (marker.name, marker.group) == key]

        if len(candidates) == 1:
            matches.append(candidates[0])
        elif number <= len(route_markers) and route_markers[number - 1] in candidates:
            matches.append(route_markers[number - 1])

    return matches


def linked_park_markers(route_markers: list[MarkerData], savegame_directory: Path):
    """The route markers vehicles of the linked savegame park at. A savegame
    without vehicles or AutoDrive data, or with a broken file, has none."""

    config_path = savegame_directory / AUTODRIVE_CONFIG_NAME
    vehicles_path = savegame_directory / "vehicles.xml"

    if not config_path.is_file() or not vehicles_path.is_file():
        return []

    try:
        keys = read_marker_keys(config_path)
    except ET.ParseError:
        return []

    return match_park_markers(route_markers, keys, read_park_destinations(vehicles_path))
