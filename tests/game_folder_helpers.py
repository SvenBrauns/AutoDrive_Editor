"""A fake FS25 user folder for tests."""

ROUTE_XML = (
    '<routeExport><waypoints c="3">'
    "<x>0;10;20</x><y>0;0;0</y><z>0;0;0</z>"
    "<out>2;3;-1</out><in>-1;1;2</in><flags>0;1;0</flags>"
    "</waypoints>"
    '<markers><m i="1" n="Hof" g="All"/></markers>'
    '<groups><g i="1" n="All"/></groups>'
    "</routeExport>"
)

SAVEGAME_XML = (
    "<AutoDrive><version>3.0.1.4</version><MapName>{map_name}</MapName>"
    "<waypoints><id>1,2</id><x>0,10</x><y>0,0</y><z>0,0</z>"
    "<out>2;-1</out><incoming>-1;1</incoming><flags>0,0</flags></waypoints>"
    "<mapmarker/></AutoDrive>"
)


def make_game_folder(path):
    path.mkdir(parents=True, exist_ok=True)
    (path / "game.xml").write_text("<game/>", encoding="utf-8")
    for number in (1, 2, 10):
        (path / f"savegame{number}").mkdir(exist_ok=True)
    (path / "savegameBackup").mkdir(exist_ok=True)
    return path


def add_routes(game_folder, routes):
    """routes: list of (name, file_name, map_name, revision). Writes routes.xml
    and a small route file for each entry."""

    manager = game_folder / "modSettings" / "FS25_AutoDrive" / "routesManager"
    (manager / "routes").mkdir(parents=True, exist_ok=True)

    entries = "".join(
        f'<route name="{name}" fileName="{file_name}" map="{map_name}" '
        f'revision="{revision}" date="2026/10/23 19:13:30"><serverId/></route>'
        for name, file_name, map_name, revision in routes
    )
    (manager / "routes.xml").write_text(
        f"<autoDriveRoutesManager>{entries}</autoDriveRoutesManager>", encoding="utf-8"
    )

    for _, file_name, _, _ in routes:
        (manager / "routes" / file_name).write_text(ROUTE_XML, encoding="utf-8")

    return manager


def add_savegame(game_folder, number, name, map_title, map_name, with_autodrive=True):
    directory = game_folder / f"savegame{number}"
    directory.mkdir(parents=True, exist_ok=True)

    (directory / "careerSavegame.xml").write_text(
        "<careerSavegame><settings>"
        f"<savegameName>{name}</savegameName><mapTitle>{map_title}</mapTitle>"
        "<mapId>FS25_Test.SampleModMap</mapId><saveDateFormatted>23.10.2026</saveDateFormatted>"
        "</settings></careerSavegame>",
        encoding="utf-8",
    )

    if with_autodrive:
        (directory / "AutoDrive_config.xml").write_text(
            SAVEGAME_XML.format(map_name=map_name), encoding="utf-8"
        )

    return directory
