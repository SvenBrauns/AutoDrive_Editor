from pathlib import Path


APP_ROOT = Path(
    __file__
).resolve().parent

CONFIG_DIRECTORY = (
    APP_ROOT / "config"
)

ICON_DIRECTORY = (
    APP_ROOT / "icons"
)

MARKER_ICON_PATH = (
    ICON_DIRECTORY / "marker.svg"
)