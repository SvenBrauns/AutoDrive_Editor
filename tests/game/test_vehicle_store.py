import io
import zipfile

from PIL import Image

from autodrive_editor.game.vehicle_store import store_info

VEHICLE_XML = (
    "<vehicle><storeData><name><en>Wagon</en><de>Wagen</de></name>"
    "<image>store_wagon.png</image></storeData></vehicle>"
)


def dds_bytes() -> bytes:
    data = io.BytesIO()
    Image.new("RGBA", (4, 4), "red").save(data, "DDS")
    return data.getvalue()


def test_name_and_picture_come_from_a_zipped_mod(tmp_path):
    with zipfile.ZipFile(tmp_path / "FS25_Wagon.zip", "w") as archive:
        archive.writestr("xml/wagon.xml", VEHICLE_XML)
        archive.writestr("xml/store_wagon.dds", dds_bytes())

    info = store_info("$moddir$FS25_Wagon/xml/wagon.xml", None, tmp_path)

    assert info.name == "Wagon"
    assert info.image.size == (4, 4)


def test_base_game_vehicle_with_data_picture_path(tmp_path):
    folder = tmp_path / "data" / "vehicles" / "fendt"
    folder.mkdir(parents=True)
    (folder / "vario.xml").write_text(
        "<vehicle><storeData><name>1000 Vario</name>"
        "<image>$data/vehicles/fendt/store_vario.png</image></storeData></vehicle>"
    )
    (folder / "store_vario.dds").write_bytes(dds_bytes())

    info = store_info("data/vehicles/fendt/vario.xml", tmp_path, None)

    assert info.name == "1000 Vario"
    assert info.image is not None


def test_missing_files_give_no_name_and_no_picture(tmp_path):
    info = store_info("$moddir$FS25_Gone/x.xml", tmp_path, tmp_path)

    assert info.name == "" and info.image is None
