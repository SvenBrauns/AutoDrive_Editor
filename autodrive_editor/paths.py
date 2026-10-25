"""File system locations used by the editor."""

import os
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

# Environment variable to use another user data folder, e.g. in tests.
USER_DATA_DIRECTORY_VARIABLE = "AUTODRIVE_EDITOR_DATA_DIR"


def user_data_directory() -> Path:
    r"""Folder for settings and imported maps: %APPDATA%\AutoDrive Editor
    on Windows, ~/.autodrive_editor elsewhere."""

    override = os.environ.get(USER_DATA_DIRECTORY_VARIABLE)

    if override:
        return Path(override)

    app_data = os.environ.get("APPDATA")

    if app_data:
        return Path(app_data) / "AutoDrive Editor"

    return Path.home() / ".autodrive_editor"
