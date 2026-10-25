"""A fake FS25 install folder with base game maps."""

from map_mod_helpers import heightmap_png, overview_dds

from autodrive_editor.game.game_installation import GAME_EXECUTABLE


def base_map_files(folder="mapUS", width=2048):
    """Files of one base map below data/, with "$data/" paths like the game."""

    root = f"maps/{folder}"
    return {
        f"{root}/{folder}.xml": (
            f'<map width="{width}" height="{width}" '
            f'imageFilename="$data/{root}/textures/ui/overview.png">'
            f"<filename>$data/{root}/{folder}.i3d</filename></map>"
        ),
        f"{root}/{folder}.i3d": (
            f'<i3D><Files><File fileId="1" filename="$data/{root}/data/dem.png"/></Files></i3D>'
        ),
        f"{root}/textures/ui/overview.dds": overview_dds(),
        f"{root}/data/dem.png": heightmap_png(),
    }


def make_installation(path, folders=("mapUS", "mapEU", "mapAS")):
    path.mkdir(parents=True, exist_ok=True)
    (path / GAME_EXECUTABLE).write_bytes(b"")

    for folder in folders:
        for name, content in base_map_files(folder).items():
            target = path / "data" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)

    return path
