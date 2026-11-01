import xml.etree.ElementTree as ET
from datetime import datetime

from PIL import Image

from autodrive_editor.game import editor_link
from autodrive_editor.game.editor_link import CaptureResult, GameStatus

MAP = "FS25_Thueringen_2_0_16x.SampleModMap"
NOW = datetime(2026, 11, 1, 14, 3, 22)


def write_status(directory, time="2026-11-01T14:03:22", format="1"):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "status.xml").write_text(
        f'<status format="{format}" revision="812" modVersion="0.1.0.0" map="{MAP}" '
        f'savegame="1" time="{time}"/>',
        encoding="utf-8",
    )


def test_link_folder_is_in_mod_settings(tmp_path):
    assert editor_link.link_directory(tmp_path) == tmp_path / "modSettings/FS25_AutoDriveEditorLink"


def test_status_is_read_and_fresh_for_ten_seconds(tmp_path):
    write_status(tmp_path)
    status = editor_link.read_status(tmp_path)

    assert status == GameStatus(MAP, "1", NOW)
    assert status.is_fresh(datetime(2026, 11, 1, 14, 3, 32))
    assert not status.is_fresh(datetime(2026, 11, 1, 14, 3, 33))


def test_missing_half_written_or_other_format_status_is_none(tmp_path):
    assert editor_link.read_status(tmp_path) is None

    (tmp_path / "status.xml").write_text('<status format="1" map=', encoding="utf-8")
    assert editor_link.read_status(tmp_path) is None

    write_status(tmp_path, format="2")
    assert editor_link.read_status(tmp_path) is None


def test_request_id_counts_month_to_second():
    assert editor_link.new_request_id(NOW) == 1101140322


def test_request_lists_the_tiles_in_order(tmp_path):
    editor_link.write_request(
        tmp_path, 17, MAP, "1", 0.25, 2000, 500, [(3, 7, -2346, -406.5), (4, 7, -1846, -406.5)]
    )
    root = ET.parse(tmp_path / "request.xml").getroot()
    pictures = root.find("pictures")

    assert root.attrib == {
        "format": "1",
        "id": "17",
        "type": "pictures",
        "map": MAP,
        "savegame": "1",
    }
    assert pictures.attrib == {
        "mPerPx": "0.25",
        "res": "2000",
        "mode": "raw",
        "altitude": "150",
        "waitMs": "500",
        "firstWaitMs": "3000",
        "dayTime": "12",
        "weather": "SUN",
    }
    assert [tile.attrib for tile in pictures] == [
        {"col": "3", "row": "7", "x": "-2346", "z": "-406.5"},
        {"col": "4", "row": "7", "x": "-1846", "z": "-406.5"},
    ]
    assert not (tmp_path / "request.xml.tmp").exists()


def test_only_tiles_with_a_marker_are_finished(tmp_path):
    folder = editor_link.pictures_directory(tmp_path, 17)
    assert editor_link.finished_tiles(tmp_path, 17) == []

    folder.mkdir()
    for name in ("tile_1_0.dds", "tile_1_0.done", "tile_0_1.dds", "tile_0_1.done", "tile_0_0.dds"):
        (folder / name).write_bytes(b"")

    assert editor_link.finished_tiles(tmp_path, 17) == [
        (1, 0, folder / "tile_1_0.dds", folder / "tile_1_0.done"),
        (0, 1, folder / "tile_0_1.dds", folder / "tile_0_1.done"),
    ]


def test_result_is_read_once_its_marker_exists(tmp_path):
    (tmp_path / "result_17.xml").write_text(
        '<result format="1" id="17" status="error" message="Other map"/>', encoding="utf-8"
    )
    assert editor_link.read_result(tmp_path, 17) is None

    (tmp_path / "result_17.done").write_bytes(b"")
    assert editor_link.read_result(tmp_path, 17) == CaptureResult("error", "Other map")


def test_result_of_another_format_is_an_error(tmp_path):
    (tmp_path / "result_17.xml").write_text('<result format="2" status="done"/>', encoding="utf-8")
    (tmp_path / "result_17.done").write_bytes(b"")

    assert editor_link.read_result(tmp_path, 17).status == "error"


def test_clean_up_removes_answer_cancel_and_leftover_tiles(tmp_path):
    editor_link.write_cancel(tmp_path, 17)
    assert (tmp_path / "cancel_17").is_file()

    folder = editor_link.pictures_directory(tmp_path, 17)
    folder.mkdir()
    (folder / "tile_0_0.dds").write_bytes(b"")
    for name in ("result_17.xml", "result_17.done", "request.xml"):
        (tmp_path / name).write_bytes(b"")

    editor_link.clean_up(tmp_path, 17)

    assert [path.name for path in tmp_path.iterdir()] == ["request.xml"]


def test_tiles_of_the_mod_are_read_like_pillow_reads_them(tmp_path):
    image = Image.new("RGB", (6, 4))
    image.putdata([(x * 40, y * 60, 200) for y in range(4) for x in range(6)])
    image.save(tmp_path / "tile.dds", "DDS")
    image.save(tmp_path / "tile.png")

    for name in ("tile.dds", "tile.png"):
        assert editor_link.read_tile(tmp_path / name).convert("RGB").tobytes() == image.tobytes()
