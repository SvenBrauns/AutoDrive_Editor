import pytest
from packaging_helpers import load_packaging_script

from autodrive_editor import __version__

release_notes = load_packaging_script("release_notes")

CHANGELOG = """# Version history

## Unreleased

- coming

## 1.1.0 – 2026-11-01

- new tool
- fix

## 1.0.0 – 2026-10-27

- first
"""


def test_section_is_the_text_up_to_the_next_version():
    assert release_notes.changelog_section(CHANGELOG, "1.1.0") == "- new tool\n- fix\n"


def test_last_section_goes_to_the_end():
    assert release_notes.changelog_section(CHANGELOG, "1.0.0") == "- first\n"


def test_missing_section_stops_the_release():
    with pytest.raises(SystemExit, match="no section for 2.0.0"):
        release_notes.changelog_section(CHANGELOG, "2.0.0")


def test_tag_must_match_the_project_version(tmp_path):
    with pytest.raises(SystemExit, match="does not match"):
        release_notes.write_release_notes("v0.0.1", tmp_path / "notes.md")


def test_notes_of_the_current_version_are_written(tmp_path):
    path = tmp_path / "build" / "notes.md"

    release_notes.write_release_notes(f"v{__version__}", path)

    text = path.read_text(encoding="utf-8")
    assert text.strip()
    assert "## " not in text
