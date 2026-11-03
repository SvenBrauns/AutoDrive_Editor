"""Benchmark of the route finder against hand-made route pieces.

The pieces are one-way stretches of 60-150 m from the hand-made Thüringen 2.0 16x course by
Bonzai1900, each with its part of the savegame's drivability map (coordinates shifted so the crop
is centred on the origin, 120 m around the piece; the map outside the crop counts as blocked).
Every piece is searched again with the same start, goal and headings,
and the result is compared with the hand-made line.

Skipped by default; run with `python -m pytest -m benchmark -s` to see the report. The test fails
when the results are worse than the BASELINE recorded below; record new numbers when a change
makes them better.
"""

import base64
import json
import math
import statistics
import time
import zlib
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import pytest

from autodrive_editor.editing.route_finder import CURVE_RADIUS, RouteFinder, RouteRequest, Vehicle
from autodrive_editor.file_io.navigation_costmap import NavigationCostmap

FIXTURE = Path(__file__).parent / "data" / "route_benchmark.json"
TIME_LIMIT = 20.0
# Extra turning of a route beyond the hand-made piece that counts as a loop.
LOOP_TURNING = math.radians(180)
# The editor's default vehicle.
VEHICLE = Vehicle()


@dataclass(frozen=True)
class Piece:
    node: int
    kind: str
    points: list[tuple[float, float]]
    costmap: NavigationCostmap


@dataclass(frozen=True)
class Result:
    piece: Piece
    seconds: float
    complete: bool = False
    clear: bool = False
    mean_deviation: float = math.nan
    max_deviation: float = math.nan
    extra_turning: float = math.nan

    @property
    def is_loop(self) -> bool:
        return self.extra_turning > LOOP_TURNING


def load_pieces(path: Path = FIXTURE) -> list[Piece]:
    content = json.loads(path.read_text(encoding="utf-8"))

    return [
        Piece(
            piece["node"],
            piece["kind"],
            [tuple(point) for point in piece["points"]],
            NavigationCostmap(
                piece["width"], piece["height"], zlib.decompress(base64.b64decode(piece["cells"]))
            ),
        )
        for piece in content["pieces"]
    ]


def heading(a, b) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def total_turning(points) -> float:
    """Sum of the heading changes along the points, in radians."""

    headings = [heading(a, b) for a, b in pairwise(points) if math.dist(a, b) > 1e-6]

    return sum(abs((h2 - h1 + math.pi) % math.tau - math.pi) for h1, h2 in pairwise(headings))


def distance_to_polyline(point, line) -> float:
    best = math.inf

    for a, b in pairwise(line):
        dx, dz = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dz * dz
        t = 0.0 if length2 == 0 else ((point[0] - a[0]) * dx + (point[1] - a[1]) * dz) / length2
        t = max(0.0, min(1.0, t))
        best = min(best, math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dz))

    return best


def measure(piece: Piece, vehicle: Vehicle = VEHICLE) -> Result:
    """Searches the piece again and compares the route with the hand-made line."""

    points = piece.points
    request = RouteRequest(
        (points[0], points[-1]),
        (heading(points[0], points[1]),),
        (heading(points[-2], points[-1]),),
        turning_radius=CURVE_RADIUS,
    )
    started = time.perf_counter()
    deadline = started + TIME_LIMIT
    route = RouteFinder(piece.costmap, vehicle).find(
        request, lambda: time.perf_counter() > deadline
    )
    seconds = time.perf_counter() - started

    if route is None or not route.is_complete:
        return Result(piece, seconds)

    found = route.points
    deviations = [distance_to_polyline(p, points) for p in found[:: max(1, len(found) // 150)]]
    back = [distance_to_polyline(p, found) for p in points]

    return Result(
        piece,
        seconds,
        complete=True,
        clear=route.is_clear,
        mean_deviation=statistics.mean(deviations),
        max_deviation=max(max(deviations), max(back)),
        extra_turning=total_turning(found[::4]) - total_turning(points),
    )


def summary(results: list[Result]) -> dict[str, float]:
    complete = [r for r in results if r.complete]
    numbers = {
        "incomplete": len(results) - len(complete),
        "blocked": sum(not r.clear for r in complete),
        "loops": sum(r.is_loop for r in complete),
        "time median": statistics.median(r.seconds for r in results),
        "time max": max(r.seconds for r in results),
    }

    for kind in ("curve", "straight"):
        of_kind = [r for r in complete if r.piece.kind == kind]
        numbers[f"{kind} mean deviation"] = statistics.median(r.mean_deviation for r in of_kind)
        numbers[f"{kind} max deviation"] = statistics.median(r.max_deviation for r in of_kind)

    return numbers


def report(results: list[Result], numbers: dict[str, float]) -> str:
    lines = [
        f"{r.piece.kind:8} node {r.piece.node:6} {r.seconds:5.2f} s "
        + (
            f"dev mean {r.mean_deviation:4.1f} max {r.max_deviation:4.1f} m "
            f"extra turn {math.degrees(r.extra_turning):4.0f}°"
            + (" BLOCKED" if not r.clear else "")
            + (" LOOP" if r.is_loop else "")
            if r.complete
            else "no route"
        )
        for r in results
    ]

    return "\n".join(lines + [f"{key}: {value:.2f}" for key, value in numbers.items()])


# Results of 2026-11-03 (legs built from straight pieces and arcs of the 6 m curve radius, the
# search only where that fails, grass 3 times the cost of roads); deviations are medians in
# metres, times in seconds.
BASELINE = {
    "incomplete": 0,
    "blocked": 0,
    "loops": 0,
    "time median": 0.02,
    "time max": 5.4,
    "curve mean deviation": 1.73,
    "curve max deviation": 3.99,
    "straight mean deviation": 0.28,
    "straight max deviation": 0.49,
}
# Allowed scatter of the times between runs and machines.
TIME_FACTOR = 2.0


@pytest.mark.benchmark
def test_route_finder_is_not_worse_than_the_baseline():
    results = [measure(piece) for piece in load_pieces()]
    numbers = summary(results)
    print("\n" + report(results, numbers))

    for key, value in BASELINE.items():
        limit = value * TIME_FACTOR if key.startswith("time") else value + 0.05
        assert numbers[key] <= limit, f"{key}: {numbers[key]:.2f}, baseline {value:.2f}"


def test_the_fixture_holds_pieces_on_their_map():
    pieces = load_pieces()

    assert len(pieces) >= 40
    assert {piece.kind for piece in pieces} == {"curve", "straight"}

    for piece in pieces:
        assert len(piece.costmap.cells) == piece.costmap.width * piece.costmap.height
        for x, z in piece.points:
            column, row = piece.costmap.cell_of(x, z)
            assert 0 <= column < piece.costmap.width and 0 <= row < piece.costmap.height


def test_total_turning_sums_heading_changes():
    assert total_turning([(0, 0), (10, 0), (10, 10), (0, 10)]) == pytest.approx(math.pi)
    assert total_turning([(0, 0), (10, 0), (20, 0)]) == 0


def test_distance_to_polyline_measures_to_the_nearest_segment():
    line = [(0, 0), (10, 0), (10, 10)]

    assert distance_to_polyline((5, 3), line) == pytest.approx(3)
    assert distance_to_polyline((13, 5), line) == pytest.approx(3)
    assert distance_to_polyline((-4, 3), line) == pytest.approx(5)


def test_summary_counts_failures_and_takes_medians():
    costmap = NavigationCostmap(2, 2, bytes(4))
    curve = Piece(1, "curve", [(0, 0), (1, 1)], costmap)
    straight = Piece(2, "straight", [(0, 0), (1, 0)], costmap)
    results = [
        Result(curve, 1.0, True, True, 2.0, 4.0, 0.0),
        Result(curve, 3.0, True, False, 4.0, 6.0, math.tau),
        Result(straight, 2.0, True, True, 0.5, 1.0, 0.0),
        Result(straight, 5.0),
    ]

    numbers = summary(results)

    assert numbers["incomplete"] == 1
    assert numbers["blocked"] == 1
    assert numbers["loops"] == 1
    assert numbers["time median"] == 2.5
    assert numbers["curve mean deviation"] == 3.0
    assert numbers["straight max deviation"] == 1.0
