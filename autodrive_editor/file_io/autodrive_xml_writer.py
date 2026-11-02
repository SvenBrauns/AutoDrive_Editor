"""Writes AutoDrive networks back into the file they were loaded from.

The existing file is edited, so everything the editor does not know
(e.g. the settings in a savegame config) stays as it was. Only the
waypoints and markers are replaced.

A savegame without AutoDrive data gets a new config with only version, map name, waypoints and
markers; AutoDrive adds its settings on its next save.

Node ids are written without gaps from 1, in the order of the editor's
ids; connections and markers are renumbered to match.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

from autodrive_editor.file_io.autodrive_xml import ConfigFormat, ConfigSource
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData

XML_DECLARATION = '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n'

# The AutoDrive version written into a new savegame config (the FS25 release of 2025/26).
NEW_CONFIG_VERSION = "3.0.1.4"

# Same precision as the files AutoDrive writes.
DECIMALS = {ConfigFormat.ROUTE_EXPORT: 2, ConfigFormat.SAVEGAME: 3}


def save_config(data: AutoDriveData, source: ConfigSource):
    """Writes the data into source.path in the format it was loaded from. A savegame config
    that does not exist yet is created."""

    is_new = not source.path.is_file()
    root = (
        _new_savegame_config(source.map_name or "") if is_new else ET.parse(source.path).getroot()
    )
    nodes = data.get_sorted_nodes()
    new_ids = {node.node_id: new_id for new_id, node in enumerate(nodes, start=1)}

    if source.format == ConfigFormat.ROUTE_EXPORT:
        _write_route_waypoints(root, nodes, new_ids)
        _write_route_markers(root, data, new_ids)
    else:
        _write_savegame_waypoints(root, nodes, new_ids)
        _write_savegame_markers(root, data, new_ids)

    if is_new:
        ET.indent(root, space="    ")

    write_xml(source.path, root)


def _new_savegame_config(map_name: str) -> ET.Element:
    root = ET.Element("AutoDrive")
    ET.SubElement(root, "version").text = NEW_CONFIG_VERSION
    ET.SubElement(root, "MapName").text = map_name
    ET.SubElement(root, "waypoints")

    return root


def write_route_export(data: AutoDriveData, path: Path):
    """Writes the data as a new route file (root <routeExport>), for any loaded format. With
    the savegame's precision, so a game that loads it holds the positions of the savegame."""

    root = ET.Element("routeExport")
    nodes = data.get_sorted_nodes()
    new_ids = {node.node_id: new_id for new_id, node in enumerate(nodes, start=1)}
    _write_route_waypoints(root, nodes, new_ids, DECIMALS[ConfigFormat.SAVEGAME])
    _write_route_markers(root, data, new_ids)
    ET.indent(root, space="    ")

    write_xml(Path(path), root)


def write_xml(path: Path, root: ET.Element):
    """Writes like the game does: UTF-8 with BOM and CRLF line ends. A
    temporary file is replaced at the end, so a failed write keeps the old
    file."""

    text = XML_DECLARATION + ET.tostring(root, encoding="unicode") + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8-sig", newline="\r\n")
    os.replace(temporary, path)


def _write_route_waypoints(
    root,
    nodes: list[NodeData],
    new_ids: dict[int, int],
    decimals=DECIMALS[ConfigFormat.ROUTE_EXPORT],
):
    waypoints = root.find("waypoints")

    if waypoints is None:
        waypoints = ET.SubElement(root, "waypoints")

    waypoints.set("c", str(len(nodes)))
    _write_lists(waypoints, nodes, new_ids, ";", "in", decimals)


def _write_savegame_waypoints(root, nodes: list[NodeData], new_ids: dict[int, int]):
    waypoints = root.find("waypoints")
    _set_child(waypoints, "id", ",".join(str(new_ids[node.node_id]) for node in nodes))
    _write_lists(waypoints, nodes, new_ids, ",", "incoming", DECIMALS[ConfigFormat.SAVEGAME])


def _write_lists(waypoints, nodes, new_ids, separator: str, incoming_tag: str, decimals: int):
    for axis in ("x", "y", "z"):
        values = (f"{getattr(node, axis):.{decimals}f}" for node in nodes)
        _set_child(waypoints, axis, separator.join(values))

    _set_child(waypoints, "out", _connections(nodes, new_ids, "outgoing"))
    _set_child(waypoints, incoming_tag, _connections(nodes, new_ids, "incoming"))
    _set_child(waypoints, "flags", separator.join(str(node.flag) for node in nodes))


def _connections(nodes: list[NodeData], new_ids: dict[int, int], attribute: str) -> str:
    """Nodes separated by ';', several targets of one node by ',', -1 for
    none. Connections to nodes that do not exist are left out."""

    parts = []

    for node in nodes:
        targets = sorted(
            new_ids[target] for target in getattr(node, attribute) if target in new_ids
        )
        parts.append(",".join(map(str, targets)) or "-1")

    return ";".join(parts)


def _write_route_markers(root, data: AutoDriveData, new_ids: dict[int, int]):
    markers = _emptied_child(root, "markers")

    for marker in data.markers.values():
        ET.SubElement(markers, "m", i=str(new_ids[marker.node_id]), n=marker.name, g=marker.group)

    groups = _emptied_child(root, "groups")
    next_id = max((group.group_id or 0 for group in data.marker_groups), default=0) + 1

    for name in data.marker_group_names():
        group = data.find_marker_group(name)

        if group is not None and group.group_id is not None:
            group_id = group.group_id
        else:
            group_id, next_id = next_id, next_id + 1

        ET.SubElement(groups, "g", n=name, i=str(group_id))

    ET.indent(markers, space="    ", level=1)
    ET.indent(groups, space="    ", level=1)


def _write_savegame_markers(root, data: AutoDriveData, new_ids: dict[int, int]):
    mapmarker = _emptied_child(root, "mapmarker")

    for number, marker in enumerate(data.markers.values(), start=1):
        element = ET.SubElement(mapmarker, f"mm{number}")
        ET.SubElement(element, "id").text = f"{new_ids[marker.node_id]:.6f}"
        ET.SubElement(element, "name").text = marker.name
        ET.SubElement(element, "group").text = marker.group

    ET.indent(mapmarker, space="    ", level=1)


def _set_child(parent, tag: str, text: str):
    child = parent.find(tag)

    if child is None:
        child = ET.SubElement(parent, tag)

    child.text = text


def _emptied_child(parent, tag: str) -> ET.Element:
    """The child element without its children; created if missing. Its
    tail (the line break after it) is kept."""

    child = parent.find(tag)

    if child is None:
        child = ET.SubElement(parent, tag)

    for grandchild in list(child):
        child.remove(grandchild)

    return child
