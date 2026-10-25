"""File system locations used by the editor."""

from pathlib import Path

# The autodrive_editor package folder.
PACKAGE_ROOT = Path(__file__).resolve().parent

# The repository folder that contains the package.
PROJECT_ROOT = PACKAGE_ROOT.parent

# User data stays outside the package.
LOCAL_PROJECTS_DIRECTORY = PROJECT_ROOT / "local_projects"

# Icons ship with the package.
ICON_DIRECTORY = PACKAGE_ROOT / "resources" / "icons"

MARKER_ICON_PATH = ICON_DIRECTORY / "marker.svg"

TOOL_ICON_DIRECTORY = ICON_DIRECTORY / "tools"
