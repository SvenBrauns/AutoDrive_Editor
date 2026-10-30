import time

import pytest
from costmap_helpers import make_costmap

from autodrive_editor.editing.edit_context import EditContext
from autodrive_editor.editing.edit_history import EditHistory
from autodrive_editor.editing.junction import CurveKind, Stem, lane_poses
from autodrive_editor.editing.operations.junction import JunctionOperation
from autodrive_editor.editing.route_finder import Vehicle
from autodrive_editor.model.autodrive_data import AutoDriveData, NodeData
from autodrive_editor.model.connections import (
    CONNECTION_STATES,
    ConnectionType,
    write_connection_state,
)


class Fixture:
    """An east-bound lane at z = 0 from x = -60 to 60 (node IDs 1–13, 10 m apart)."""

    def __init__(self, qapp, costmap=None, stem=(Stem.AUTO, 5.5)):
        self.qapp = qapp
        self.data = AutoDriveData()

        for index, x in enumerate(range(-60, 61, 10)):
            self.data.add_node(NodeData(index + 1, x, 0, 0))

            if index:
                write_connection_state(
                    self.data, index, index + 1, CONNECTION_STATES[ConnectionType.REGULAR]
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
