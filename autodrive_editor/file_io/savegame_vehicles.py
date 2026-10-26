"""Keeps the marker numbers in a savegame's vehicles.xml in step with the
AutoDrive config.

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
from pathlib import Path, PurePosixPath

# Vehicle start tags and their AutoDrive elements, in file order.
_TAG = re.compile(r"<(vehicle|AutoDrive)\b[^>]*>")
_MARKER_ATTRIBUTE = re.compile(r'\s(firstMarker|secondMarker|parkDestination)="(-?\d+)"')


def renumber_vehicle_markers(vehicles_path: Path, new_numbers: dict[int, int | None]) -> list[str]:
    """Rewrites the marker numbers by new_numbers (old number -> new number,
    None for a deleted marker). Targets of deleted markers go to marker 1,
    park destinations of deleted markers are removed. Returns the names of
    those vehicles."""

    with open(vehicles_path, encoding="utf-8-sig", newline="") as file:
        text = file.read()

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

    new_text = _TAG.sub(replace_tag, text)

    if new_text != text:
        temporary = vehicles_path.with_name(vehicles_path.name + ".tmp")

        with open(temporary, "w", encoding="utf-8-sig", newline="") as file:
            file.write(new_text)

        os.replace(temporary, vehicles_path)

    return affected


def _attribute(tag: str, name: str) -> str:
    match = re.search(rf'\s{name}="([^"]*)"', tag)
    return match.group(1) if match else ""
