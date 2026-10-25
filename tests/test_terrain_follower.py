import pytest

from editing.terrain_follower import TerrainFollower


def slope(x, z):
    """Terrain rising 0.5 m per unit in x, flat in z."""
    return 0.5 * x


def test_node_on_the_ground_follows_the_terrain():
    follower = TerrainFollower(slope)
    follower.begin({1: (0.0, 0.0, 0.0)})

    assert follower.height_at(1, (0.0, 0.0, 0.0), 10.0, 3.0) == pytest.approx(5.0)


def test_node_above_the_terrain_keeps_its_distance():
    follower = TerrainFollower(slope)
    follower.begin({1: (0.0, 8.0, 0.0)})  # 8 m above ground, e.g. a bridge

    assert follower.height_at(1, (0.0, 8.0, 0.0), 10.0, 0.0) == pytest.approx(13.0)


def test_without_terrain_the_height_stays():
    follower = TerrainFollower(None)
    follower.begin({1: (0.0, 4.0, 0.0)})

    assert follower.height_at(1, (0.0, 4.0, 0.0), 10.0, 0.0) == 4.0


def test_outside_the_map_the_height_stays():
    def only_near_origin(x, z):
        return 0.0 if abs(x) < 5 else None

    follower = TerrainFollower(only_near_origin)
    follower.begin({1: (0.0, 2.0, 0.0)})

    assert follower.height_at(1, (0.0, 2.0, 0.0), 10.0, 0.0) == 2.0


def test_start_outside_the_map_keeps_the_height():
    follower = TerrainFollower(lambda x, z: None if x < 0 else 1.0)
    follower.begin({1: (-1.0, 2.0, 0.0)})

    assert follower.height_at(1, (-1.0, 2.0, 0.0), 10.0, 0.0) == 2.0


def test_unmoved_node_keeps_exact_height():
    follower = TerrainFollower(lambda x, z: 0.1 + 0.2)  # float noise
    follower.begin({1: (3.0, 0.7, 4.0)})

    assert follower.height_at(1, (3.0, 0.7, 4.0), 3.0, 4.0) == 0.7
