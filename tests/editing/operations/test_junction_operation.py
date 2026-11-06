import logging
import math
import time

import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.junctions.junction import CurveKind, JunctionPlan, Stem, lane_poses
from autodrive_editor.editing.junctions.junction_box import BoxPlan, Style
from autodrive_editor.editing.operations.junction import JunctionOperation
from autodrive_editor.editing.routes.route_finder import Vehicle
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    write_connection_state,
)


class Fixture:
    """An east-bound lane at z = 0 from x = -60 to 60 (node IDs 1–13, 10 m apart); with
    `two_lanes` also a west-bound lane at z = -4 (IDs 101–113)."""

    def __init__(
        self,
        qapp,
        costmap=None,
        stem=(Stem.AUTO, 5.5),
        style=Style.CURVES,
        two_lanes=False,
        radius=6.0,
    ):
        self.qapp = qapp
        self.data = AutoDriveData()

        for index, x in enumerate(range(-60, 61, 10)):
            self.data.add_node(NodeData(index + 1, x, 0, 0))

            if index:
                write_connection_state(
                    self.data, index, index + 1, CONNECTION_STATES[ConnectionType.REGULAR]
                )

        if two_lanes:
            for index, x in enumerate(range(60, -61, -10)):
                self.data.add_node(NodeData(index + 101, x, 0, -4))

                if index:
                    write_connection_state(
                        self.data,
                        index + 100,
                        index + 101,
                        CONNECTION_STATES[ConnectionType.REGULAR],
                    )

        self.history = EditHistory()
        self.messages = []
        context = EditContext(edit_history=self.history, autodrive_data_provider=lambda: self.data)
        self.operation = JunctionOperation(
            context,
            costmap_provider=lambda: costmap,
            vehicle_provider=lambda: Vehicle(8, 3, 0.5),
            spacing_provider=lambda: 5.0,
            height_for_new_node=lambda data, x, z: 0.0,
            stem_provider=lambda: stem,
            style_provider=lambda: style,
            curve_radius_provider=lambda: radius,
        )
        self.operation.status_changed.connect(self.messages.append)

    def drag(self, x, z):
        """Presses on the connection between nodes 7 (x = 0) and 8 and drags to (x, z)."""

        assert self.operation.start(7, 8, 2.0, 0.5)
        self.operation.drag_to(x, z)

    def wait(self):
        deadline = time.monotonic() + 60

        while self.operation.is_searching and time.monotonic() < deadline:
            self.qapp.processEvents()
            time.sleep(0.01)


def test_dragging_previews_curves_meeting_a_radius_from_the_road_and_the_stem(qapp):
    fixture = Fixture(qapp)

    fixture.drag(2.0, 20.0)

    preview = fixture.operation.preview
    assert len(preview.plan.curves) == 2
    assert preview.junction[:2] == pytest.approx((2.0, 6.0))
    assert preview.stem_length == pytest.approx(14.0)


def test_curves_use_the_curve_radius_setting(qapp):
    fixture = Fixture(qapp, radius=9.0)

    fixture.drag(2.0, 20.0)

    assert fixture.operation.preview.junction[:2] == pytest.approx((2.0, 9.0))


def test_release_adds_the_junction_to_the_plan_in_one_step(qapp):
    fixture = Fixture(qapp)
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)

    assert fixture.operation.finish()

    assert fixture.operation.preview is None
    assert len(fixture.data.nodes) > 13
    assert fixture.data.validate_connections() == []
    assert fixture.messages[-1] == "Junction added"
    fixture.history.undo()
    assert len(fixture.data.nodes) == 13


def test_outside_planning_mode_nothing_is_added(qapp):
    fixture = Fixture(qapp)
    fixture.drag(2.0, 20.0)

    assert not fixture.operation.finish()

    assert len(fixture.data.nodes) == 13
    assert fixture.messages == ["Junctions are added in planning mode"]


def test_curves_that_do_not_fit_are_searched_then_added(qapp):
    # A wall south of the road with a gap at x = 10–30: the curves cannot turn in directly
    # at x = 2, but the route finder finds a way through the gap.
    costmap = make_costmap(blocked=[(-90, 3, 10, 8), (30, 3, 90, 8)])
    fixture = Fixture(qapp, costmap)
    fixture.history.start_plan()
    fixture.drag(2.0, 30.0)
    assert fixture.operation.preview.plan.missing

    assert fixture.operation.finish()
    assert fixture.operation.is_searching
    fixture.wait()

    assert len(fixture.data.nodes) > 13
    assert fixture.messages[-1].startswith("Junction added")


def test_a_failing_search_ends_with_an_error_message(qapp, monkeypatch):
    def broken(*args):
        raise RuntimeError("broken")

    monkeypatch.setattr("autodrive_editor.editing.routes.route_finder.RouteFinder.find", broken)
    costmap = make_costmap(blocked=[(-90, 3, 10, 8), (30, 3, 90, 8)])
    fixture = Fixture(qapp, costmap)
    fixture.history.start_plan()
    fixture.drag(2.0, 30.0)

    assert fixture.operation.finish()
    fixture.wait()

    assert not fixture.operation.is_searching
    assert len(fixture.data.nodes) == 13
    assert fixture.messages[-1] == "The junction search failed. Details are in the log file"


def test_pieces_left_out_stay_shown_as_gaps_until_esc(qapp, monkeypatch):
    # A wall west of the junction; the search finds no way round it.
    monkeypatch.setattr(
        "autodrive_editor.editing.routes.route_finder.RouteFinder.find", lambda *args: None
    )
    fixture = Fixture(qapp, make_costmap(blocked=[(-100, 3, 1, 8)]))
    fixture.history.start_plan()
    fixture.drag(2.0, 30.0)
    assert fixture.operation.gaps == fixture.operation.preview.plan.gaps != []

    assert fixture.operation.finish()
    fixture.wait()

    assert "missing: No right turn in from the west" in fixture.messages[-1]
    assert fixture.operation.preview is None
    assert len(fixture.operation.gaps) == 1

    assert fixture.operation.cancel()
    assert fixture.operation.gaps == []


def test_cancel_clears_the_preview(qapp):
    fixture = Fixture(qapp)
    fixture.drag(2.0, 20.0)

    assert fixture.operation.cancel()

    assert fixture.operation.preview is None
    assert not fixture.operation.finish()


def test_a_two_lane_stem_has_its_lanes_the_gap_apart(qapp):
    fixture = Fixture(qapp, stem=(Stem.TWO_LANES, 6.0))
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)

    preview = fixture.operation.preview
    assert preview.gap == 6.0
    in_pose, _ = lane_poses(preview.junction, 6.0)
    curve_in = next(curve for curve in preview.plan.curves if curve.kind == CurveKind.IN)
    assert curve_in.points[-1] == pytest.approx(in_pose[:2])

    assert fixture.operation.finish()
    assert fixture.data.validate_connections() == []


def test_auto_stem_is_two_way_on_a_single_lane(qapp):
    fixture = Fixture(qapp, stem=(Stem.AUTO, 6.0))
    fixture.drag(2.0, 20.0)

    assert fixture.operation.preview.gap == 0.0


def add_west_bound_lane(data):
    """A west-bound lane at z = -4 (IDs 101–113) beside the fixture's road."""

    for index, x in enumerate(range(60, -61, -10)):
        data.add_node(NodeData(101 + index, x, 0, -4))

        if index:
            write_connection_state(
                data, 100 + index, 101 + index, CONNECTION_STATES[ConnectionType.REGULAR]
            )


def test_moving_along_the_road_moves_the_junction_and_keeps_the_stem_square(qapp):
    fixture = Fixture(qapp)

    fixture.drag(12.0, 20.0)

    preview = fixture.operation.preview
    assert preview.junction == pytest.approx((12.0, 6.0, math.pi / 2))
    assert preview.stem[-1][:2] == pytest.approx((12.0, 20.0))


def test_release_shows_the_tip_and_bending_moves_it(qapp):
    fixture = Fixture(qapp)
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)

    assert fixture.operation.release()
    assert fixture.operation.is_bending
    assert len(fixture.data.nodes) == 13

    fixture.operation.bend_to(12.0, 30.0)

    stem = fixture.operation.preview.stem
    assert stem[0] == pytest.approx(fixture.operation.preview.junction)
    assert stem[-1][:2] == pytest.approx((12.0, 30.0))
    assert fixture.operation.finish()
    assert not fixture.operation.is_bending
    assert any(
        (node.x, node.z) == pytest.approx((12.0, 30.0)) for node in fixture.data.nodes.values()
    )


def test_undo_in_step_two_resets_the_bend_then_goes_back_to_step_one_then_cancels(qapp):
    operation = Fixture(qapp).operation
    operation.start(7, 8, 2.0, 0.5)
    operation.drag_to(2.0, 20.0)
    operation.release()
    released = operation.preview
    operation.bend_to(12.0, 30.0)

    assert operation.undo()

    assert operation.preview == released
    assert operation.is_bending
    assert operation.undo()
    assert not operation.is_bending
    assert operation.is_following
    operation.drag_to(-8.0, 20.0)
    assert operation.preview.junction[0] == pytest.approx(-8.0)
    assert operation.release()
    assert operation.is_bending and not operation.is_following
    assert operation.undo()
    assert operation.undo()
    assert operation.preview is None and not operation.is_following
    assert not operation.undo()


def test_dropping_the_tip_on_a_node_joins_it(qapp):
    fixture = Fixture(qapp)
    fixture.data.add_node(NodeData(500, 10.0, 0, 30.0))
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)
    fixture.operation.release()

    fixture.operation.bend_to(11.0, 29.0, 500)

    assert fixture.operation.preview.stem[-1][:2] == pytest.approx((10.0, 30.0))
    assert fixture.operation.finish()
    assert fixture.data.nodes[500].incoming and fixture.data.nodes[500].outgoing


def test_auto_stem_is_two_way_when_the_tip_joins_a_two_way_road(qapp):
    fixture = Fixture(qapp)
    add_west_bound_lane(fixture.data)
    fixture.data.add_node(NodeData(500, 10.0, 0, 30.0))
    fixture.data.add_node(NodeData(501, 20.0, 0, 30.0))
    fixture.data.add_node(NodeData(502, 10.0, 0, 40.0))
    write_connection_state(fixture.data, 500, 501, CONNECTION_STATES[ConnectionType.DUAL])
    write_connection_state(fixture.data, 502, 501, CONNECTION_STATES[ConnectionType.REGULAR])
    fixture.drag(2.0, 20.0)
    assert fixture.operation.preview.gap == 5.5
    fixture.operation.release()

    fixture.operation.bend_to(10.0, 30.0, 500)
    assert fixture.operation.preview.gap == 0.0

    fixture.operation.bend_to(10.0, 40.0, 502)
    assert fixture.operation.preview.gap == 5.5

    fixture.operation.bend_to(10.0, 30.0, 500)
    fixture.operation.bend_to(15.0, 35.0)
    assert fixture.operation.preview.gap == 5.5


def test_adding_a_junction_writes_debug_log_lines(qapp, caplog):
    caplog.set_level(logging.DEBUG, logger="autodrive_editor.editing.operations.junction")
    fixture = Fixture(qapp)
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)

    fixture.operation.finish()

    assert "Junction at (2.0, 6.0)" in caplog.text
    assert "curve in from lane" in caplog.text


def test_the_box_style_builds_a_box_on_a_road_of_two_one_way_lanes(qapp):
    fixture = Fixture(qapp, style=Style.BOX, two_lanes=True)
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)

    preview = fixture.operation.preview
    assert isinstance(preview.plan, BoxPlan)
    assert preview.junction[:2] == pytest.approx((2.0, 7.0))
    assert preview.gap == 5.5
    assert fixture.operation.release()
    assert fixture.operation.finish()

    assert fixture.data.validate_connections() == []
    assert fixture.messages[-1] == "Junction added"
    centre = [n for n in fixture.data.nodes.values() if math.dist((n.x, n.z), (2, -2)) < 1e-6]
    assert len(centre) == 1 and len(centre[0].outgoing) == 4


def test_the_box_style_falls_back_to_curves_and_says_so(qapp):
    fixture = Fixture(qapp, style=Style.BOX)
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)

    assert isinstance(fixture.operation.preview.plan, JunctionPlan)
    assert fixture.operation.finish()

    assert fixture.messages[-1] == (
        "Junction added; built with curves: a box needs two one-way lanes on the road and the stem"
    )


def test_a_one_way_in_stem_adds_only_the_curve_in_and_a_one_way_stem(qapp):
    fixture = Fixture(qapp, stem=(Stem.IN_ONLY, 5.5), two_lanes=True, style=Style.BOX)
    fixture.history.start_plan()
    fixture.drag(2.0, 20.0)

    assert [curve.kind.value for curve in fixture.operation.preview.plan.curves] == ["in", "in"]
    assert fixture.operation.finish()

    new = [node for node in fixture.data.nodes.values() if node.node_id > 113]
    tip = max(new, key=lambda node: node.z)
    assert not tip.outgoing and tip.incoming
