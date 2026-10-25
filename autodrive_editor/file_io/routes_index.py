"""Reads AutoDrive's RoutesManager index, routes.xml.

    <autoDriveRoutesManager>
        <route name="Thueringen" fileName="g8Cq02ZGwaIPuGPr.xml"
               map="LS25_Thüringen_2_0_16x" revision="1" date="2026/10/23 19:13:30">
            <serverId/>
        </route>
    </autoDriveRoutesManager>

The route files themselves live in the routes folder next to routes.xml.
AutoDrive also writes autosaves there (<file>_autosave_<n>.xml), which
are not listed in routes.xml.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROUTES_INDEX_ROOT = "autoDriveRoutesManager"

_AUTOSAVE_SUFFIX = re.compile(r"_autosave_\d+$")


@dataclass(frozen=True)
class RouteEntry:
    """One route listed in routes.xml."""

    name: str
    file_name: str
    map_name: str
    revision: int
    date: str
    path: Path


def read_routes_index(routes_xml_path: Path) -> list[RouteEntry]:
    """All routes in routes.xml, in file order."""

    routes_xml_path = Path(routes_xml_path)

    try:
        root = ET.parse(routes_xml_path).getroot()
    except ET.ParseError as ex:
        raise ValueError(f"routes.xml ist ungültig: {ex}") from ex

    if root.tag != ROUTES_INDEX_ROOT:
        raise ValueError(f"routes.xml hat ein unbekanntes Format (<{root.tag}>).")

    routes_directory = routes_xml_path.parent / "routes"
    entries = []

    for route in root.iter("route"):
        file_name = route.get("fileName", "")
        revision = route.get("revision", "0")

        entries.append(
            RouteEntry(
                name=route.get("name", ""),
                file_name=file_name,
                map_name=route.get("map", ""),
                revision=int(revision) if revision.isdigit() else 0,
                date=route.get("date", ""),
                path=routes_directory / file_name,
            )
        )

    return entries


def find_route_entry(route_file: Path) -> RouteEntry | None:
    """The routes.xml entry of a route file opened by hand. routes.xml is
    expected one folder above the routes folder. Autosaves map to the
    route they belong to."""

    route_file = Path(route_file)
    routes_xml_path = route_file.parent.parent / "routes.xml"

    if not routes_xml_path.is_file():
        return None

    base_name = _AUTOSAVE_SUFFIX.sub("", route_file.stem) + route_file.suffix

    try:
        entries = read_routes_index(routes_xml_path)
    except ValueError:
        return None

    return next((entry for entry in entries if entry.file_name == base_name), None)
