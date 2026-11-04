import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.bunker_silo import SiloMode, silo_access
from autodrive_editor.file_io.savegame_sheds import IndoorArea

# 10 m wide from x = -5 to 5, driven along z from 0 (back) to 20 (front).
SILO = IndoorArea("silo.xml", "s", ((-5, 0), (5, 0), (5, 20), (-5, 20)), height=0)
SIDE_WALLS = [(-6, -2, -5, 22), (5, -2, 6, 22)]
BACK_WALL = (-6, -2, 6, 0)
FRONT_WALL = (-6, 20, 6, 22)


@pytest.mark.parametrize(
    ("walls", "access"),
    [
        ([BACK_WALL], (SiloMode.BACK_IN, "front")),
        ([FRONT_WALL], (SiloMode.BACK_IN, "back")),
        ([], (SiloMode.DRIVE_THROUGH, "front")),
    ],
)
def test_closed_end_is_found_from_the_drivability_map(walls, access):
    assert silo_access(SILO, make_costmap(60, blocked=SIDE_WALLS + walls)) == access


def test_turned_silo_is_entered_at_its_open_end():
    # The same silo turned by 90°: its back lies at x = 0, its front at x = -20.
    turned = IndoorArea("silo.xml", "s", ((0, -5), (0, 5), (-20, 5), (-20, -5)), height=0)

    front_wall = (-22, -6, -20, 6)

    assert silo_access(turned, make_costmap(60, blocked=[front_wall])) == (SiloMode.BACK_IN, "back")


def test_without_map_a_silo_is_backed_into_from_the_front():
    assert silo_access(SILO, None) == (SiloMode.BACK_IN, "front")
