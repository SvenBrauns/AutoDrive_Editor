import pytest

from autodrive_editor.rendering.scale_bar import scale_bar_metres, scale_bar_text


@pytest.mark.parametrize(
    ("pixels_per_metre", "metres"),
    [
        (1.0, 100),
        (2.0, 50),
        (0.1, 1000),
        (0.05, 2000),
        (4.0, 20),
        (50.0, 2),
        (120.0, 1),
        (200.0, 0.5),
    ],
)
def test_the_bar_is_the_longest_round_length_that_fits(pixels_per_metre, metres):
    assert scale_bar_metres(pixels_per_metre, max_pixels=120) == pytest.approx(metres)


def test_long_bars_are_given_in_kilometres():
    assert (scale_bar_text(500), scale_bar_text(2000), scale_bar_text(0.5)) == (
        "500 m",
        "2 km",
        "0.5 m",
    )
