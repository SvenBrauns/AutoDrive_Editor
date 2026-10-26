import pytest
from PySide6.QtCore import QLocale

from autodrive_editor import i18n
from autodrive_editor.i18n import tr


def test_texts_are_english_by_default():
    assert tr("Save") == "Save"


def test_german_texts_come_from_the_catalog(german):
    assert tr("Save") == "Speichern"


def test_values_are_filled_in_after_translating(german):
    assert tr("Marker “{name}” added", name="Hof") == "Marker „Hof“ hinzugefügt"


def test_values_keep_their_format():
    assert tr("Rotation: {angle:.1f}°", angle=12.345) == "Rotation: 12.3°"


def test_a_value_may_be_called_text():
    assert tr("{text}: 1 node", text="Align horizontally") == "Align horizontally: 1 node"


def test_unknown_texts_stay_as_they_are(german):
    assert tr("Not in the catalog") == "Not in the catalog"


@pytest.mark.parametrize(
    ("windows_language", "expected"),
    [
        (QLocale.Language.German, i18n.GERMAN),
        (QLocale.Language.English, i18n.ENGLISH),
        (QLocale.Language.French, i18n.ENGLISH),
    ],
)
def test_system_language_is_german_only_on_a_german_windows(
    monkeypatch, windows_language, expected
):
    monkeypatch.setattr(QLocale, "system", staticmethod(lambda: QLocale(windows_language)))

    assert i18n.system_language() == expected
