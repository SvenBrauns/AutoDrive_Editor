import pytest

from autodrive_editor.file_io.game_files import GameFiles
from autodrive_editor.file_io.savegame_buildings import read_savegame_buildings
from autodrive_editor.file_io.savegame_stations import StopKind

STATION_XML = """<placeable>
    <storeData><name>Mill</name></storeData>
    <base><filename>$data/placeables/mill/mill.i3d</filename></base>
    {sections}
    <i3dMappings>
        <i3dMapping id="aiNode" node="0>0"/>
        <i3dMapping id="exactFillRootNode" node="0>1"/>
        <i3dMapping id="fillRoot2" node="0>2"/>
        <i3dMapping id="farAway" node="0>3"/>
    </i3dMappings>
</placeable>"""

# The AI node is turned by 90°: its z axis points along +x.
STATION_I3D = """<i3D><Scene><TransformGroup name="mill" translation="500 0 500">
    <TransformGroup name="aiNode" translation="3 0 7" rotation="0 90 0"/>
    <TransformGroup name="exactFillRootNode" translation="-4 1 2"/>
    <TransformGroup name="fillRoot2" translation="-3 1 2"/>
    <TransformGroup name="farAway" translation="20 1 2"/>
</TransformGroup></Scene></i3D>"""

PLACEABLE = (
    '<placeable filename="data/placeables/mill/mill.xml" uniqueId="u" position="100 80 200" '
    'rotation="0 {turn} 0"/>'
)


def stops(tmp_path, sections, turn=0):
    folder = tmp_path / "game/data/placeables/mill"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "mill.xml").write_text(STATION_XML.format(sections=sections), encoding="utf-8")
    (folder / "mill.i3d").write_text(STATION_I3D, encoding="utf-8")
    (tmp_path / "savegame1").mkdir(exist_ok=True)
    (tmp_path / "savegame1/placeables.xml").write_text(
        f"<placeables>{PLACEABLE.format(turn=turn)}</placeables>", encoding="utf-8"
    )
    with GameFiles(tmp_path / "game", None) as files:
        return read_savegame_buildings(tmp_path / "savegame1", files).stops


def test_stop_at_the_ai_node_heads_along_its_z_axis(tmp_path):
    sections = """<sellingStation><unloadTrigger exactFillRootNode="exactFillRootNode"
        fillTypes="WHEAT BARLEY" aiNode="aiNode"/></sellingStation>"""

    (stop,) = stops(tmp_path, sections)

    assert stop.position == pytest.approx((103, 80, 207))
    # +x is right on the map.
    assert stop.heading == pytest.approx(90)
    assert stop.building_position == pytest.approx((100, 200))
    assert stop.from_ai_node
    assert (stop.kind, stop.fill_types) == (StopKind.SELL, ("WHEAT", "BARLEY"))
    assert (stop.name, stop.unique_id) == ("Mill", "u")
    assert stop.building_file == "data/placeables/mill/mill.xml"


def test_stop_without_ai_node_is_at_the_trigger_and_heads_like_the_building(tmp_path):
    sections = """<unloadingStation>
        <unloadTrigger exactFillRootNode="exactFillRootNode" fillTypeCategories="BULK"/>
    </unloadingStation>"""

    (stop,) = stops(tmp_path, sections, turn=90)

    # Turned by 90° around y: x → -z, z → x.
    assert stop.position == pytest.approx((102, 81, 204))
    assert stop.heading == pytest.approx(90)
    assert not stop.from_ai_node
    assert (stop.kind, stop.fill_types) == (StopKind.UNLOAD, ("BULK",))


def test_triggers_of_one_kind_at_nearly_the_same_spot_are_one_stop(tmp_path):
    sections = """<loadingStation>
        <loadTrigger triggerNode="exactFillRootNode" fillTypes="WHEAT"/>
        <loadTrigger triggerNode="fillRoot2" fillTypes="WHEAT OAT"/>
        <loadTrigger triggerNode="farAway" fillTypes="OAT"/>
    </loadingStation>
    <unloadingStation><unloadTrigger exactFillRootNode="fillRoot2" fillTypes="OAT"/>
    </unloadingStation>"""

    found = stops(tmp_path, sections)

    assert [(stop.kind, stop.fill_types) for stop in found] == [
        (StopKind.LOAD, ("WHEAT", "OAT")),
        (StopKind.LOAD, ("OAT",)),
        (StopKind.UNLOAD, ("OAT",)),
    ]


@pytest.mark.parametrize(
    ("sections", "kind"),
    [
        (
            "<productionPoint><sellingStation><unloadTrigger exactFillRootNode="
            '"exactFillRootNode"/></sellingStation></productionPoint>',
            StopKind.PRODUCTION,
        ),
        (
            '<husbandry><food><unloadTrigger exactFillRootNode="exactFillRootNode"/></food>'
            "</husbandry>",
            StopKind.ANIMALS,
        ),
        (
            '<silo><loadingStation><loadTrigger triggerNode="exactFillRootNode" '
            'fillTypes="DIESEL"/></loadingStation></silo>',
            StopKind.DIESEL,
        ),
        (
            '<buyingStation><loadTrigger triggerNode="exactFillRootNode"/></buyingStation>',
            StopKind.BUY,
        ),
        ('<loadTrigger triggerNode="exactFillRootNode"/>', StopKind.LOAD),
    ],
)
def test_kind_comes_from_the_sections_around_the_trigger(tmp_path, sections, kind):
    assert [stop.kind for stop in stops(tmp_path, sections)] == [kind]


def test_a_production_stop_knows_whether_it_loads_or_unloads(tmp_path):
    sections = (
        '<productionPoint><unloadTrigger exactFillRootNode="exactFillRootNode"/>'
        '<loadTrigger triggerNode="farAway"/></productionPoint>'
    )

    assert [stop.loads for stop in stops(tmp_path, sections)] == [False, True]


def test_triggers_whose_node_is_missing_are_left_out(tmp_path):
    sections = """<sellingStation>
        <unloadTrigger exactFillRootNode="noSuchNode"/>
        <unloadTrigger/>
        <unloadTrigger exactFillRootNode="exactFillRootNode"/>
    </sellingStation>"""

    assert len(stops(tmp_path, sections)) == 1


def test_kind_label_is_translated(german):
    assert StopKind.SELL.label == "Verkaufsstelle"
