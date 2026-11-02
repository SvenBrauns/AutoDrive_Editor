"""The status bar while a file loads."""

import pytest


@pytest.fixture
def statuses(window):
    texts = []
    window.files.status_changed.connect(texts.append)
    return texts


def test_loading_text_comes_before_the_loaded_text(window, write_xml, statuses):
    window.files._load_config(write_xml(), display_name="Hof")

    assert statuses[0] == "Loading “Hof”…"
    assert "“Hof” loaded" in window.status.text()


def test_failed_loading_is_shown_in_the_status_bar(window, tmp_path, statuses, monkeypatch):
    broken = tmp_path / "broken.xml"
    broken.write_text("not xml")
    monkeypatch.setattr(window.files, "_inform", lambda text: None)

    assert not window.files._load_config(broken)

    assert statuses == ["Loading “broken.xml”…", "“broken.xml” could not be loaded"]
