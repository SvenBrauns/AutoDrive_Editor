"""Asks GitHub for the latest release, to tell the user about a newer version."""

import json
import urllib.request
from dataclasses import dataclass

LATEST_RELEASE_URL = "https://api.github.com/repos/SvenBrauns/AutoDrive_Editor/releases/latest"
TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    notes: str


def fetch_latest_release() -> dict:
    """The latest release as GitHub describes it. Raises OSError or
    ValueError when GitHub cannot be reached or answers nonsense."""

    request = urllib.request.Request(
        LATEST_RELEASE_URL, headers={"Accept": "application/vnd.github+json"}
    )

    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def newer_release(data: dict, current_version: str) -> Release | None:
    """The release from GitHub's answer if it is newer than the running version."""

    latest = parse_version(data.get("tag_name", ""))
    current = parse_version(current_version)

    if latest is None or current is None or latest <= current:
        return None

    return Release(
        version=data["tag_name"].removeprefix("v"),
        url=data.get("html_url", ""),
        notes=data.get("body") or "",
    )


def parse_version(text: str) -> tuple[int, ...] | None:
    """ "v1.2.0" → (1, 2, 0); None if the text is no plain version number."""

    try:
        return tuple(int(part) for part in text.removeprefix("v").split("."))
    except ValueError:
        return None
