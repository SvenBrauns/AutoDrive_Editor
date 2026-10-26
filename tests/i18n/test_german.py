"""Every tr() text in the editor has a German translation with the same
placeholders, and the catalog holds no texts the editor no longer uses."""

import ast
from pathlib import Path
from string import Formatter

import autodrive_editor
from autodrive_editor.i18n.german import TEXTS

PACKAGE = Path(autodrive_editor.__file__).parent


def tr_calls():
    for path in sorted(PACKAGE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "tr":
                yield path, node


def tr_texts() -> set[str]:
    return {node.args[0].value for _, node in tr_calls()}


def placeholders(text: str) -> set[tuple[str, str]]:
    return {(name, spec) for _, name, spec, _ in Formatter().parse(text) if name is not None}


def test_tr_is_called_with_the_text_itself():
    """Only literal texts can be checked against the catalog."""

    calls = [
        f"{path.name}:{node.lineno}"
        for path, node in tr_calls()
        if not (isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str))
    ]

    assert calls == []


def test_every_text_has_a_german_translation():
    assert sorted(tr_texts() - TEXTS.keys()) == []


def test_catalog_has_no_unused_texts():
    assert sorted(TEXTS.keys() - tr_texts()) == []


def test_translations_keep_the_placeholders():
    assert [
        text for text, german in TEXTS.items() if placeholders(text) != placeholders(german)
    ] == []
