import pytest
from costmap_helpers import costmap_file_bytes, make_costmap

from autodrive_editor.file_io.navigation_costmap import (
    CostmapError,
    NavigationCostmap,
    costmap_path,
    read_costmap,
)


def test_reads_the_cells_after_the_unknown_block(tmp_path):
    costmap = make_costmap(4, blocked=[(0, -2, 1, -1)])
    path = costmap_path(tmp_path)
    path.write_bytes(costmap_file_bytes(costmap))

    assert read_costmap(path) == costmap


@pytest.mark.parametrize("data", [b"XXXX" + bytes(20), b"VNCM" + bytes(8) + b"not zlib"])
def test_other_files_are_rejected(tmp_path, data):
    path = tmp_path / "map.dat"
    path.write_bytes(data)

    with pytest.raises(CostmapError):
        read_costmap(path)


def test_world_position_to_cell():
    # 4 × 4 map from -2 to 2; row 0 is z = -2.
    costmap = NavigationCostmap(4, 4, bytes(range(16)))

    assert costmap.cell_of(-2, -2) == (0, 0)
    assert costmap.value_at(1.5, -0.5) == 7
    assert costmap.value_at(5, 0) == 255


def test_row_outside_the_map_is_blocked():
    costmap = NavigationCostmap(4, 4, bytes(range(16)))

    assert costmap.row(1, -1, 2) == b"\xff\x04\x05"
    assert costmap.row(3, 3, 5) == b"\x0f\xff"
    assert costmap.row(9, 0, 2) == b"\xff\xff"
