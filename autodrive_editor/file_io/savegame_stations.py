"""Stops of the stations in the buildings of a savegame: where vehicles unload or load.

    greenHouseGlassLarge.xml  (building definition)
        <productionPoint>
            <sellingStation node="sellingStation">
                <unloadTrigger exactFillRootNode="exactFillRootNode" fillTypes="WATER"
                    aiNode="unloadTriggerAINode"/>
        <i3dMappings><i3dMapping id="unloadTriggerAINode" node="0>5|4|2"/>

    greenHouseGlassLarge.i3d
        <TransformGroup name="unloadTriggerAINode" translation="3 0 7" rotation="0 90 0"/>

aiNode is the spot the game's AI helper drives to; its local z axis runs along the lane. Without
it the stop is at the trigger node (exactFillRootNode or triggerNode) and the lane follows the
building's z axis. Several triggers often sit at the same spot, one per fill type; they are merged
into one stop. The buildings themselves are read by savegame_buildings.
"""

import math
from dataclasses import dataclass, replace
from enum import StrEnum

from autodrive_editor.error_log import logger
from autodrive_editor.file_io.building_definitions import (
    BuildingScene,
    Transform,
    apply_transform,
    rotate,
)
from autodrive_editor.i18n import tr

Point = tuple[float, float, float]

TRIGGERS = ("unloadTrigger", "loadTrigger")

# Triggers of the same kind closer than this (in metres) are one stop.
MERGE_DISTANCE = 3.0


class StopKind(StrEnum):
    SELL = "sell"
    UNLOAD = "unload"
    LOAD = "load"
    BUY = "buy"
    PRODUCTION = "production"
    ANIMALS = "animals"
    DIESEL = "diesel"

    @property
    def label(self) -> str:
        return {
            StopKind.SELL: tr("Selling point"),
            StopKind.UNLOAD: tr("Unloading"),
            StopKind.LOAD: tr("Loading"),
            StopKind.BUY: tr("Buying station"),
            StopKind.PRODUCTION: tr("Production"),
            StopKind.ANIMALS: tr("Animals"),
            StopKind.DIESEL: tr("Diesel"),
        }[self]


# Sections that give the kind of every trigger inside them, from the outside in.
BUILDING_KINDS = {"productionPoint": StopKind.PRODUCTION, "husbandry": StopKind.ANIMALS}
STATION_KINDS = {
    "sellingStation": StopKind.SELL,
    "unloadingStation": StopKind.UNLOAD,
    "loadingStation": StopKind.LOAD,
    "buyingStation": StopKind.BUY,
}


@dataclass(frozen=True)
class LocalStop:
    """A stop relative to its building; direction is the lane's (x, y, z) direction."""

    kind: StopKind
    fill_types: tuple[str, ...]
    position: Point
    direction: Point
    from_ai_node: bool
    # True for a load trigger (the vehicle takes goods), False for an unload trigger.
    loads: bool = False


@dataclass(frozen=True)
class Stop:
    """A stop of a placed building. heading is the map angle of its lane (0° up, 90° right); the
    lane is drive-through, so the opposite direction fits as well."""

    building_file: str
    unique_id: str
    # Name of the building.
    name: str
    kind: StopKind
    fill_types: tuple[str, ...]
    position: Point
    heading: float
    # False if the building has no AI node here and heading is the building's orientation.
    from_ai_node: bool
    # Map position (x, z) of the building's origin.
    building_position: tuple[float, float] = (0.0, 0.0)
    # True for a load trigger (the vehicle takes goods), False for an unload trigger.
    loads: bool = False


def local_stops(definition, scene: BuildingScene) -> list[LocalStop]:
    """The stops of a building definition, triggers at nearly the same spot merged."""

    parents = {child: parent for parent in definition.iter() for child in parent}
    stops = []

    for trigger in definition.iter():
        if trigger.tag not in TRIGGERS:
            continue

        ai_node = trigger.get("aiNode")
        node = ai_node or trigger.get("exactFillRootNode") or trigger.get("triggerNode")

        if not node:
            continue

        try:
            transform = scene.transform(node)
        except (IndexError, ValueError) as error:
            logger.warning("Trigger node %s could not be found: %s", node, error)
            continue

        sections = []
        element = trigger

        while element in parents:
            element = parents[element]
            sections.append(element.tag)

        fill_types = tuple(
            (trigger.get("fillTypes") or trigger.get("fillTypeCategories") or "").split()
        )
        direction = rotate(transform, (0.0, 0.0, 1.0)) if ai_node else (0.0, 0.0, 1.0)
        stops.append(
            LocalStop(
                _kind(trigger.tag, sections, fill_types),
                fill_types,
                transform[1],
                direction,
                bool(ai_node),
                trigger.tag == "loadTrigger",
            )
        )

    return _merged(stops)


def placed_stop(
    stop: LocalStop, placement: Transform, building_file: str, unique_id: str, name: str
) -> Stop:
    dx, _, dz = rotate(placement, stop.direction)
    origin_x, _, origin_z = apply_transform(placement, (0.0, 0.0, 0.0))

    return Stop(
        building_file=building_file,
        unique_id=unique_id,
        name=name,
        kind=stop.kind,
        fill_types=stop.fill_types,
        position=apply_transform(placement, stop.position),
        heading=math.degrees(math.atan2(dx, -dz)) % 360,
        from_ai_node=stop.from_ai_node,
        building_position=(origin_x, origin_z),
        loads=stop.loads,
    )


def _kind(trigger: str, sections: list[str], fill_types: tuple[str, ...]) -> StopKind:
    """sections: the tags around the trigger, from the inside out."""

    for section in reversed(sections):
        if section in BUILDING_KINDS:
            return BUILDING_KINDS[section]

    if fill_types == ("DIESEL",):
        return StopKind.DIESEL

    for section in sections:
        if section in STATION_KINDS:
            return STATION_KINDS[section]

    return StopKind.UNLOAD if trigger == "unloadTrigger" else StopKind.LOAD


def _merged(stops: list[LocalStop]) -> list[LocalStop]:
    merged: list[LocalStop] = []

    for stop in stops:
        for index, other in enumerate(merged):
            close = math.dist(stop.position[::2], other.position[::2]) <= MERGE_DISTANCE

            if other.kind == stop.kind and close:
                fill_types = other.fill_types + tuple(
                    fill_type for fill_type in stop.fill_types if fill_type not in other.fill_types
                )
                merged[index] = replace(other, fill_types=fill_types)
                break
        else:
            merged.append(stop)

    return merged
