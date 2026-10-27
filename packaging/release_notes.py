"""Checks the release tag against the project version and writes that version's CHANGELOG section.

Usage: python packaging/release_notes.py v1.0.0 build/release_notes.md
"""

import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]


def changelog_section(changelog: str, version: str) -> str:
    lines = changelog.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(f"## {version} ")), None)
    if start is None:
        raise SystemExit(f"CHANGELOG.md has no section for {version}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1 : end]).strip() + "\n"


def write_release_notes(tag: str, path: Path):
    with open(PROJECT_ROOT / "pyproject.toml", "rb") as file:
        version = tomllib.load(file)["project"]["version"]
    if tag != f"v{version}":
        raise SystemExit(f"Tag {tag} does not match version {version} in pyproject.toml")
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(changelog_section(changelog, version), encoding="utf-8")


if __name__ == "__main__":
    write_release_notes(sys.argv[1], Path(sys.argv[2]))
