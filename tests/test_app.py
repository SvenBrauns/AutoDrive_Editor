import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTranslator

from autodrive_editor import i18n
from autodrive_editor.app import install_language
from autodrive_editor.i18n import tr

PROJECT_DIRECTORY = Path(__file__).parents[1]


def test_ui_modules_are_not_imported_before_the_language_is_set():
    """Some UI modules translate texts when they are imported."""

    code = (
        "import sys, autodrive_editor.app; "
        "print(any(name.startswith('autodrive_editor.ui') for name in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_DIRECTORY,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "False"


def test_german_translates_editor_and_qt_texts(qapp):
    install_language(qapp, i18n.GERMAN)

    try:
        assert tr("Save") == "Speichern"
        assert QCoreApplication.translate("QPlatformTheme", "Cancel") == "Abbrechen"

    finally:
        i18n.set_language(i18n.ENGLISH)

        for translator in qapp.findChildren(QTranslator):
            qapp.removeTranslator(translator)
            translator.deleteLater()
