from autodrive_editor import __version__
from autodrive_editor.ui.dialogs.update_dialog import create_update_box
from autodrive_editor.updates import Release


def test_box_names_both_versions_and_shows_notes(window):
    box = create_update_box(window, Release("9.0.0", "https://example.org", "- New things"))

    assert "9.0.0" in box.text()
    assert __version__ in box.text()
    assert box.detailedText() == "- New things"
    assert box.defaultButton() is box.download_button
