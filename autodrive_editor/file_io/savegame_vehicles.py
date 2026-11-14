"""Keeps the marker numbers in a savegame's vehicles.xml in step with the
AutoDrive config, and reads and sets the vehicles' parking positions.

Vehicles refer to markers by their number (position in the config):

    <vehicle filename="…/vario1050.xml" uniqueId="…">
        <AutoDrive firstMarker="122" secondMarker="922" driverName="1050 Vario" …/>
        …
    <AutoDrive parkDestination="931"/>

The file is edited as text, so everything else stays exactly as the game
wrote it.
"""

import html
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# Vehicle start tags and their AutoDrive elements, in file order.
_TAG = re.compile(r"<(vehicle|AutoDrive)\b[^>]*>")
_MARKER_ATTRIBUTE = re.compile(r'\s(firstMarker|secondMarker|parkDestination)="(-?\d+)"')
_PARK_DESTINATION = re.compile(r'<AutoDrive\b[^>]*\sparkDestination="(\d+)"')
_VEHICLE_BLOCK = re.compile(r"(<vehicle\b[^>]*>)(.*?)(</vehicle>)", re.DOTALL)
_AUTODRIVE_TAG = re.compile(r"<AutoDrive\b[^>]*>")
_PARK_ATTRIBUTE = re.compile(r'\sparkDestination="-?\d+"')


@dataclass(frozen=True)
class SavegameVehicle:
    """A vehicle or implement that can have a parking position."""

    unique_id: str
    filename: str
    driver_name: str
    # Unique id of the vehicle it is attached to, "" if none.
    attached_to: str
    park: int | None
    # Brand and name, given by the game; empty when read from the file.
    name: str = ""


def read_vehicles(vehicles_path: Path) -> list[SavegameVehicle]:
    """The vehicles and implements of the farms that AutoDrive can park: those with AutoDrive
    data and attachable ones. Trains (no farm) and pallets (not attachable) are left out."""

    root = ET.parse(vehicles_path).getroot()
    parents = {
        implement.get("attachedVehicleUniqueId"): vehicle.get("uniqueId", "")
        for vehicle in root.iter("vehicle")
        for implement in vehicle.iter("attachedImplement")
    }
    vehicles = []

    for vehicle in root.iter("vehicle"):
        autodrive = vehicle.find("AutoDrive")

        if vehicle.get("farmId", "0") == "0" or (
            autodrive is None and vehicle.find("attachable") is None
        ):
            continue

        attributes = autodrive.attrib if autodrive is not None else {}
        park = int(attributes.get("parkDestination", "-1"))
        unique_id = vehicle.get("uniqueId", "")
        vehicles.append(
            SavegameVehicle(
                unique_id,
                vehicle.get("filename", ""),
                attributes.get("driverName", ""),
                parents.get(unique_id, ""),
                park if park > 0 else None,
            )
        )

    return vehicles


def set_park_destinations(vehicles_path: Path, parks: dict[str, int | None]):
    """Sets the parking marker of the vehicles by unique id (None: no parking position)."""

    with open(vehicles_path, encoding="utf-8-sig", newline="") as file:
        text = file.read()

    newline = "\r\n" if "\r\n" in text else "\n"

    def replace_block(match):
        start, body, end = match.groups()
        unique_id = _attribute(start, "uniqueId")

        if unique_id not in parks:
            return match.group(0)

        park = parks[unique_id]
        attribute = f' parkDestination="{park}"' if park else ""
        tag = _AUTODRIVE_TAG.search(body)

        if tag is not None:
            cleared = _PARK_ATTRIBUTE.sub("", tag.group(0))
            new_tag = cleared.replace("<AutoDrive", "<AutoDrive" + attribute, 1)
            body = body[: tag.start()] + new_tag + body[tag.end() :]
        elif park:
            closing_indent = body[body.rfind("\n") + 1 :]
            body += f"    <AutoDrive{attribute}/>{newline}{closing_indent}"

        return start + body + end

    _write(vehicles_path, _VEHICLE_BLOCK.sub(replace_block, text))


def read_park_destinations(vehicles_path: Path) -> set[int]:
    """The marker numbers vehicles use as parking destination."""

    with open(vehicles_path, encoding="utf-8-sig") as file:
        return {int(number) for number in _PARK_DESTINATION.findall(file.read())}


def vehicles_losing_markers(vehicles_path: Path, new_numbers: dict[int, int | None]) -> list[str]:
    """The names of the vehicles renumber_vehicle_markers would reset, without changing the
    file."""

    with open(vehicles_path, encoding="utf-8-sig", newline="") as file:
        return _renumber(file.read(), new_numbers)[1]


def renumber_vehicle_markers(vehicles_path: Path, new_numbers: dict[int, int | None]) -> list[str]:
    """Rewrites the marker numbers by new_numbers (old number -> new number,
    None for a deleted marker). Targets of deleted markers go to marker 1,
    park destinations of deleted markers are removed. Returns the names of
    those vehicles."""

    with open(vehicles_path, encoding="utf-8-sig", newline="") as file:
        text = file.read()

    new_text, affected = _renumber(text, new_numbers)

    if new_text != text:
        _write(vehicles_path, new_text)

    return affected


def _write(vehicles_path: Path, text: str):
    temporary = vehicles_path.with_name(vehicles_path.name + ".tmp")

    with open(temporary, "w", encoding="utf-8-sig", newline="") as file:
        file.write(text)

    os.replace(temporary, vehicles_path)


def _renumber(text: str, new_numbers: dict[int, int | None]) -> tuple[str, list[str]]:
    affected = []
    vehicle_name = ""

    def replace_tag(match):
        nonlocal vehicle_name
        tag = match.group(0)

        if match.group(1) == "vehicle":
            vehicle_name = PurePosixPath(_attribute(tag, "filename")).stem
            return tag

        reset = False

        def replace_number(attribute):
            nonlocal reset
            name, number = attribute.group(1), int(attribute.group(2))

            if number not in new_numbers:
                return attribute.group(0)

            if new_numbers[number] is None:
                reset = True
                return "" if name == "parkDestination" else f' {name}="1"'

            return f' {name}="{new_numbers[number]}"'

        tag = _MARKER_ATTRIBUTE.sub(replace_number, tag)

        if reset:
            affected.append(html.unescape(_attribute(tag, "driverName")) or vehicle_name)

        return tag

    return _TAG.sub(replace_tag, text), affected


def _attribute(tag: str, name: str) -> str:
    match = re.search(rf'\s{name}="([^"]*)"', tag)
    return match.group(1) if match else ""
