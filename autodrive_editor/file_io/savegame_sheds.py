"""Indoor areas of the buildings placed in a savegame, used as sheds.

    easyShed01.xml  (building definition)
        <indoorAreas><indoorArea startNode="indoorAreaStart01" widthNode="…" heightNode="…"/>
        <i3dMappings><i3dMapping id="indoorAreaStart01" node="0>2|0"/>

    easyShed01.i3d
        <TransformGroup name="indoorAreaStart01" translation="-15 0 -7.5">
            <TransformGroup name="indoorAreaWidth01" translation="30 0 0"/>
            <TransformGroup name="indoorAreaHeight01" translation="0 0 15"/>

The buildings themselves are read by savegame_buildings.
"""

from dataclasses import dataclass

from autodrive_editor.file_io.building_definitions import (
    BuildingScene,
    Transform,
    apply_transform,
    category_label,
)

Point = tuple[float, float, float]


@dataclass(frozen=True)
class IndoorArea:
    """One indoor area of a placed building. corners are (x, z) on the map: the start, the end of
    its width, the opposite corner and the end of its height."""

    building_file: str
    unique_id: str
    corners: tuple[tuple[float, float], ...]
    # Ground height of the building.
    height: float
    name: str = ""
    # Shop category of the building, e.g. "sheds" or "productionPoints".
    category: str = ""

    @property
    def category_label(self) -> str:
        return category_label(self.category)


def local_areas(definition, scene: BuildingScene) -> list[tuple[Point, Point, Point]]:
    """The indoor areas of a building definition as (start, width, height) points relative to
    the building."""

    return [
        tuple(
            scene.transform(area.get(key, ""))[1]
            for key in ("startNode", "widthNode", "heightNode")
        )
        for area in definition.findall("indoorAreas/indoorArea")
    ]


def placed_area(
    points: tuple[Point, Point, Point],
    placement: Transform,
    building_file: str,
    unique_id: str,
    name: str,
    category: str,
) -> IndoorArea:
    start, width, height = (apply_transform(placement, point) for point in points)
    opposite = tuple(w + h - s for s, w, h in zip(start, width, height, strict=True))

    return IndoorArea(
        building_file=building_file,
        unique_id=unique_id,
        corners=tuple((p[0], p[2]) for p in (start, width, opposite, height)),
        height=placement[1][1],
        name=name,
        category=category,
    )
