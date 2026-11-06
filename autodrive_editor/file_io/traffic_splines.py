"""The lanes of the map's AI traffic, from the map scene and its shapes file.

    map.i3d
        <Shapes externalShapesFile="map.i3d.shapes">
        <Scene> … <TransformGroup name="trafficSystem" nodeId="17">
                      <TransformGroup rotation="0 -35 0" …><Shape shapeId="812" nodeId="18"/>
        <UserAttribute nodeId="17">
            <Attribute name="onCreate" type="scriptCallback" value="TrafficSystem.onCreate"/>
        <UserAttribute nodeId="18">
            <Attribute name="speedLimit" type="float" value="50"/>

Every Shape below the traffic system node is a spline (see i3d_shapes) and one one-way lane;
lanes join end to start. Splines with isTeleport="true" place the cars and are left out. Maps
without a traffic system have no lanes.
"""

import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from autodrive_editor.file_io.building_cache import BuildingCache
from autodrive_editor.file_io.building_definitions import (
    IDENTITY,
    apply_transform,
    combine,
    local_transform,
    map_scene,
)
from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.i3d_shapes import read_splines

TRAFFIC_SYSTEM = "TrafficSystem.onCreate"


@dataclass(frozen=True)
class TrafficLane:
    # World positions in driving order.
    points: tuple[tuple[float, float, float], ...]
    speed_limit: float | None


def shapes_file_name(scene) -> str | None:
    """The shapes file named in the scene, relative to the scene's folder."""

    shapes = scene.find("Shapes")

    return None if shapes is None else shapes.get("externalShapesFile")


def read_traffic_lanes(scene, open_shapes: Callable[[], BinaryIO]) -> list[TrafficLane]:
    """The traffic lanes of a parsed map scene; open_shapes opens its shapes file, which is
    only read when the map has a traffic system."""

    attributes = {
        node.get("nodeId"): {attribute.get("name"): attribute.get("value") for attribute in node}
        for node in scene.iter("UserAttribute")
    }
    system_ids = [
        node_id
        for node_id, values in attributes.items()
        if values.get("onCreate") == TRAFFIC_SYSTEM
    ]
    tree = scene.find("Scene")
    system = next((node for node in tree.iter() if node.get("nodeId") in system_ids), None)

    if system is None:
        return []

    parents = {child: parent for parent in tree.iter() for child in parent}
    with open_shapes() as stream:
        splines = read_splines(stream)

    path = [system]

    while parents.get(path[-1]) not in (None, tree):
        path.append(parents[path[-1]])

    transform = IDENTITY

    for node in reversed(path):
        transform = combine(transform, local_transform(node))

    lanes = []

    def walk(node, transform):
        for child in node:
            child_transform = combine(transform, local_transform(child))
            values = attributes.get(child.get("nodeId"), {})
            points = splines.get(int(child.get("shapeId", -1)))

            if child.tag == "Shape" and points and values.get("isTeleport") != "true":
                speed = values.get("speedLimit")
                lanes.append(
                    TrafficLane(
                        tuple(apply_transform(child_transform, point) for point in points),
                        None if speed is None else float(speed),
                    )
                )

            walk(child, child_transform)

    walk(system, transform)

    return lanes


def map_traffic_lanes(
    savegame_directory: Path, files: GameFiles, cache: BuildingCache | None = None
) -> list[TrafficLane]:
    """The traffic lanes of a savegame's map, kept in the cache while the map scene stays the
    same (the shapes file is saved with it). Raises the errors of
    building_definitions.READ_ERRORS and i3d_shapes.ShapesError."""

    mod, scene_path = map_scene(savegame_directory, files)

    def read():
        scene = ET.fromstring(files.read(mod, scene_path))
        folder = PurePosixPath(scene_path).parent
        shapes_path = str(folder / (shapes_file_name(scene) or Path(scene_path).name + ".shapes"))

        return read_traffic_lanes(scene, lambda: files.open(mod, shapes_path))

    return (cache or BuildingCache()).get(
        ("traffic lanes", mod, scene_path), files.stamp(mod, scene_path), read
    )
