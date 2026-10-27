from packaging_helpers import load_packaging_script

from autodrive_editor import __version__

version_info = load_packaging_script("version_info")


def test_text_has_version_numbers_and_strings():
    text = version_info.version_info_text("1.2.3")

    assert "filevers=(1, 2, 3, 0), prodvers=(1, 2, 3, 0)" in text
    assert "StringStruct('ProductVersion', '1.2.3')" in text
    assert "StringStruct('OriginalFilename', 'AutoDrive Editor.exe')" in text


def test_written_file_uses_the_project_version(tmp_path):
    path = tmp_path / "build" / "version_info.txt"

    version_info.write_version_info(path)

    assert f"StringStruct('FileVersion', '{__version__}')" in path.read_text(encoding="utf-8")
