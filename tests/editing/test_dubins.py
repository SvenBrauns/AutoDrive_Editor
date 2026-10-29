import math
import random

import pytest

from autodrive_editor.editing.dubins import advance, shortest_path


def test_straight_ahead_is_a_straight_line():
    path = shortest_path((0, 0, 0), (30, 0, 0), 10)

    assert path.length == pytest.approx(30)


def test_turning_back_takes_half_a_circle():
    # Same spot one diameter to the left, heading the other way.
    path = shortest_path((0, 0, 0), (0, 20, math.pi), 10)

    assert path.length == pytest.approx(math.pi * 10)


def test_every_path_ends_at_the_goal_pose():
    rng = random.Random(1)

    for _ in range(500):
        start = (rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-4, 4))
        goal = (rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-4, 4))
        x, z, heading = shortest_path(start, goal, 8).sample(0.5)[-1]

        assert (x, z) == pytest.approx(goal[:2], abs=1e-6)
        assert math.remainder(heading - goal[2], math.tau) == pytest.approx(0, abs=1e-6)


def test_advance_on_a_left_arc():
    # A quarter circle to the left with radius 10, starting towards +x.
    assert advance((0, 0, 0), 0.1, math.pi * 5) == pytest.approx((10, 10, math.pi / 2))
