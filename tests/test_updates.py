from autodrive_editor.updates import Release, newer_release, parse_version

RELEASE = {"tag_name": "v1.2.0", "html_url": "https://example.org/v1.2.0", "body": "Notes"}


def test_parse_version():
    assert parse_version("v1.2.0") == (1, 2, 0)
    assert parse_version("1.10") == (1, 10)
    assert parse_version("v1.2.0-beta") is None
    assert parse_version("") is None


def test_newer_release_is_returned():
    assert newer_release(RELEASE, "1.0.0") == Release(
        "1.2.0", "https://example.org/v1.2.0", "Notes"
    )


def test_same_or_older_release_is_ignored():
    assert newer_release(RELEASE, "1.2.0") is None
    assert newer_release(RELEASE, "1.10.0") is None


def test_unusable_answer_is_ignored():
    assert newer_release({}, "1.0.0") is None
    assert newer_release({"tag_name": "nightly"}, "1.0.0") is None


def test_missing_notes_become_empty():
    data = {"tag_name": "v2.0.0", "html_url": "u", "body": None}

    assert newer_release(data, "1.0.0").notes == ""
