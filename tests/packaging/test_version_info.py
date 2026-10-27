import importlib.util

from autodrive_editor import __version__
from autodrive_editor.paths import PROJECT_ROOT

# Loaded from its path: "packaging" is also the name of an installed library.
_spec = importlib.util.spec_from_file_location(
    "version_info", PROJECT_ROOT / "packaging" / "version_info.py"
)
version_info = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(version_info)


def test_text_has_version_numbers_and_strings():
    text = version_info.version_info_text("1.2.3")

    assert "filevers=(1, 2, 3, 0), prodvers=(1, 2, 3, 0)" in text
    assert "StringStruct('ProductVersion', '1.2.3')" in text
    assert "StringStruct('OriginalFilename', 'AutoDrive Editor.exe')" in text


def test_written_file_uses_the_project_version(tmp_path):
    path = tmp_path / "build" / "version_info.txt"

    version_info.write_version_info(path)

    assert f"StringStruct('FileVersion', '{__version__}')" in path.read_text(encoding="utf-8")
