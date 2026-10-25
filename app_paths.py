from pathlib import Path


APP_ROOT = Path(
    __file__
).resolve().parent

LOCAL_PROJECTS_DIRECTORY = (
    APP_ROOT / "local_projects"
)

ICON_DIRECTORY = (
    APP_ROOT / "icons"
)

MARKER_ICON_PATH = (
    ICON_DIRECTORY / "marker.svg"
)

TOOL_ICON_DIRECTORY = (
    ICON_DIRECTORY / "tools"
)