import os
import zipfile

from autodrive_editor.file_io.mod_archive import ModArchive


def test_stamp_of_a_zipped_mod_is_that_of_the_zip(tmp_path):
    path = tmp_path / "FS25_Mod.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("a.xml", "a")

    with ModArchive(path) as archive:
        stamp = archive.stamp(["a.xml", "missing.xml"])

    info = path.stat()
    assert stamp == (info.st_size, info.st_mtime_ns)


def test_stamp_of_an_unpacked_mod_changes_with_its_files(tmp_path):
    (tmp_path / "a.xml").write_text("a", encoding="utf-8")
    (tmp_path / "b.xml").write_text("b", encoding="utf-8")
    archive = ModArchive(tmp_path)
    before = archive.stamp(["A.xml", "b.xml"])
    os.utime(tmp_path / "b.xml", ns=(0, 10**18))

    assert len(before) == 4
    assert archive.stamp(["a.xml", "b.xml"]) != before
    assert archive.stamp(["a.xml", "missing.xml"]) is None
