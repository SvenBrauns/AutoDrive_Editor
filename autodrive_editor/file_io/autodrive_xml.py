"""Reads AutoDrive networks from the two FS25 file formats.

Route export (RoutesManager, root <routeExport>):

    <waypoints c="3">
        <x>1.0;2.0;3.0</x> <y>…</y> <z>…</z>
        <out>2;3;-1</out> <in>-1;1;2</in> <flags>0;1;0</flags>
    </waypoints>
    <markers><m i="1" n="Hof" g="All"/></markers>
    <groups><g i="1" n="All"/></groups>

Savegame config (savegameN/AutoDrive_config.xml, root <AutoDrive>):

    <version>3.0.1.4</version> <MapName>…</MapName>
    <waypoints>
        <id>1,2,3</id> <x>1.0,2.0,3.0</x> <y>…</y> <z>…</z>
        <out>2;3;-1</out> <incoming>-1;1;2</incoming> <flags>0,1,0</flags>
    </waypoints>
    <mapmarker><mm1><id>1.000000</id><name>Hof</name><group>All</group></mm1></mapmarker>

In both formats a node's id is its 1-based position in the lists, -1
means "no connection" and several connections of a node are separated
by commas.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from autodrive_editor.model.autodrive_data import (
    REGULAR_FLAG,
    AutoDriveData,
    MarkerData,
    MarkerGroup,
    NodeData,
)

# Savegame configs of FS25 have AutoDrive version 3.x.
FS25_CONFIG_MAJOR_VERSION = 3


class ConfigFormat(Enum):
    ROUTE_EXPORT = "route_export"
    SAVEGAME = "savegame"


@dataclass(frozen=True)
class ConfigSource:
    """Where loaded data came from. Needed to find the matching map and,
    later, to save back into the same format."""

    format: ConfigFormat
    path: Path
    map_name: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class LoadedConfig:
    data: AutoDriveData
    source: ConfigSource


@dataclass(frozen=True)
class _FormatLayout:
    """How a format names its lists and separates its values."""

    value_separator: str
    incoming_element: str


_LAYOUTS = {
    ConfigFormat.ROUTE_EXPORT: _FormatLayout(value_separator=";", incoming_element="in"),
    ConfigFormat.SAVEGAME: _FormatLayout(value_separator=",", incoming_element="incoming"),
}

_ROOT_FORMATS = {"routeExport": ConfigFormat.ROUTE_EXPORT, "AutoDrive": ConfigFormat.SAVEGAME}


class AutoDriveXmlReader:
    """Reads a route export or an FS25 savegame config into AutoDriveData.
    The format is detected from the root element."""

    @classmethod
    def load(cls, file_path) -> AutoDriveData:
        return cls.read(file_path).data

    @classmethod
    def read(cls, file_path) -> LoadedConfig:
        xml_path = Path(file_path).resolve()

        if not xml_path.is_file():
            raise FileNotFoundError(f"Die AutoDrive-XML wurde nicht gefunden: {xml_path}")

        try:
            root = ET.parse(xml_path).getroot()
        except ET.ParseError as ex:
            raise ValueError(f"Die XML-Datei ist ungültig: {ex}") from ex

        config_format = _ROOT_FORMATS.get(root.tag)

        if config_format is None:
            raise ValueError(
                f"Unbekanntes Format: Wurzelelement <{root.tag}>. Erwartet wird eine "
                "RoutesManager-Route (<routeExport>) oder eine Savegame-Config (<AutoDrive>)."
            )

        version = None

        if config_format == ConfigFormat.SAVEGAME:
            version = cls._check_fs25_version(root)

        waypoints = root.find("waypoints")

        if waypoints is None:
            raise ValueError("Die XML enthält keinen Waypoint-Bereich.")

        data = cls._read_nodes(waypoints, _LAYOUTS[config_format])

        if config_format == ConfigFormat.ROUTE_EXPORT:
            cls._read_route_markers(root, data)
        else:
            cls._read_savegame_markers(root, data)

        map_name = (root.findtext("MapName") or "").strip() or None

        return LoadedConfig(
            data=data,
            source=ConfigSource(
                format=config_format, path=xml_path, map_name=map_name, version=version
            ),
        )

    @staticmethod
    def _check_fs25_version(root) -> str:
        version = (root.findtext("version") or "").strip()
        major = version.split(".")[0]

        if not major.isdigit():
            raise ValueError("Die Savegame-Config enthält keine gültige AutoDrive-Version.")

        if int(major) != FS25_CONFIG_MAJOR_VERSION:
            raise ValueError(
                f"Nur Configs aus dem LS25 werden unterstützt (AutoDrive-Version 3.x). "
                f"Diese Config hat Version {version}."
            )

        return version

    @classmethod
    def _read_nodes(cls, waypoints, layout: _FormatLayout) -> AutoDriveData:
        separator = layout.value_separator

        x_values = cls._read_floats(waypoints, "x", separator)
        y_values = cls._read_floats(waypoints, "y", separator)
        z_values = cls._read_floats(waypoints, "z", separator)

        lengths = {"x": len(x_values), "y": len(y_values), "z": len(z_values)}

        if len(set(lengths.values())) != 1:
            raise ValueError(
                f"Die Anzahl der X-, Y- und Z-Koordinaten stimmt nicht überein: {lengths}"
            )

        node_count = len(x_values)

        flags = cls._read_flags(waypoints, separator, node_count)
        outgoing = cls._read_connections(waypoints, "out", node_count)
        incoming = cls._read_connections(waypoints, layout.incoming_element, node_count)

        data = AutoDriveData()

        for index in range(node_count):
            data.add_node(
                NodeData(
                    node_id=index + 1,
                    x=x_values[index],
                    y=y_values[index],
                    z=z_values[index],
                    flag=flags[index],
                    outgoing=outgoing[index],
                    incoming=incoming[index],
                )
            )

        return data

    @staticmethod
    def _split(waypoints, element_name: str, separator: str) -> list[str] | None:
        text = waypoints.findtext(element_name)

        if text is None or not text.strip():
            return None

        return [part.strip() for part in text.strip().split(separator)]

    @classmethod
    def _read_floats(cls, waypoints, element_name: str, separator: str) -> list[float]:
        parts = cls._split(waypoints, element_name, separator)

        if parts is None:
            raise ValueError(f"Die XML enthält keine {element_name}-Koordinaten.")

        values = []

        for part in parts:
            try:
                values.append(float(part))
            except ValueError as ex:
                raise ValueError(f"Ungültiger Wert im Element '{element_name}': {part}") from ex

        return values

    @classmethod
    def _read_flags(cls, waypoints, separator: str, node_count: int) -> list[int]:
        """Flags by position. Missing or empty entries are regular nodes, so
        later flags keep their position."""

        parts = cls._split(waypoints, "flags", separator) or []
        flags = []

        for part in parts[:node_count]:
            if not part:
                flags.append(REGULAR_FLAG)
                continue

            try:
                flags.append(int(float(part)))
            except ValueError as ex:
                raise ValueError(f"Ungültiger Node-Flag: {part}") from ex

        flags.extend([REGULAR_FLAG] * (node_count - len(flags)))

        return flags

    @classmethod
    def _read_connections(cls, waypoints, element_name: str, node_count: int) -> list[set[int]]:
        """Connections per node: nodes separated by ';', several targets of
        one node by ','. Values <= 0 (like -1) mean no connection."""

        parts = cls._split(waypoints, element_name, ";") or []
        connections = []

        for part in parts[:node_count]:
            targets = set()

            for raw_id in part.split(","):
                raw_id = raw_id.strip()

                if not raw_id:
                    continue

                try:
                    node_id = int(raw_id)
                except ValueError as ex:
                    raise ValueError(f"Ungültige Verbindungs-ID: {raw_id}") from ex

                if node_id > 0:
                    targets.add(node_id)

            connections.append(targets)

        connections.extend(set() for _ in range(node_count - len(connections)))

        return connections

    @staticmethod
    def _add_marker(data: AutoDriveData, raw_node_id, name: str, group: str):
        try:
            node_id = int(float(raw_node_id))
        except (TypeError, ValueError):
            return

        if node_id in data.nodes:
            data.add_marker(MarkerData(node_id=node_id, name=name, group=group))

    @classmethod
    def _read_route_markers(cls, root, data: AutoDriveData):
        for marker in root.findall("markers/*"):
            cls._add_marker(data, marker.get("i"), marker.get("n", ""), marker.get("g", ""))

        for group in root.findall("groups/*"):
            raw_id = group.get("i", "")
            data.marker_groups.append(
                MarkerGroup(
                    name=group.get("n", ""),
                    group_id=int(raw_id) if raw_id.strip().isdigit() else None,
                )
            )

    @classmethod
    def _read_savegame_markers(cls, root, data: AutoDriveData):
        """Markers are mm1, mm2, … in that order. The groups are not listed
        separately; they are collected from the markers' group names."""

        def marker_number(element):
            suffix = element.tag.removeprefix("mm")
            return int(suffix) if suffix.isdigit() else 0

        group_names = []

        for marker in sorted(root.findall("mapmarker/*"), key=marker_number):
            name = (marker.findtext("name") or "").strip()
            group = (marker.findtext("group") or "").strip()

            cls._add_marker(data, marker.findtext("id"), name, group)

            if group and group not in group_names:
                group_names.append(group)

        data.marker_groups.extend(MarkerGroup(name=name) for name in group_names)
