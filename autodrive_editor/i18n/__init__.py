"""Translation of the user interface texts.

The texts in the code are English and are wrapped in tr(). For German,
tr() looks them up in german.TEXTS. Values are passed as keywords and
filled into the {placeholders} after the lookup:

    tr("Marker “{name}” added", name=name)

The language is set once at startup, before the UI modules are imported,
because some of them translate texts when they are imported.
"""

from PySide6.QtCore import QLocale

from autodrive_editor.i18n.german import TEXTS as GERMAN_TEXTS

ENGLISH = "en"
GERMAN = "de"

# Language code -> name shown in the settings, always in its own language.
LANGUAGES = {ENGLISH: "English", GERMAN: "Deutsch"}

_language = ENGLISH
_texts: dict[str, str] = {}


def set_language(language: str):
    global _language, _texts

    _language = GERMAN if language == GERMAN else ENGLISH
    _texts = GERMAN_TEXTS if _language == GERMAN else {}


def current_language() -> str:
    return _language


def tr(text: str, /, **values) -> str:
    text = _texts.get(text, text)

    return text.format(**values) if values else text


def system_language() -> str:
    """German on a German Windows, English everywhere else."""

    return GERMAN if QLocale.system().language() == QLocale.Language.German else ENGLISH
