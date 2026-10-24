import math
from dataclasses import dataclass
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPolygonF

from autodrive.models import NodeData
from rendering.connection_data import ConnectionType


MINIMUM_CONNECTION_LENGTH = 0.000001
MINIMUM_VISIBLE_LENGTH = 0.0001
@dataclass(frozen=True)
class ConnectionGeometry:

    source_tip: QPointF
    target_tip: QPointF

    direction_x: float
    direction_z: float

    distance: float
    endpoint_offset: float


def get_connection_type(
    source_node: NodeData,
    target_node: NodeData
) -> ConnectionType:
    if is_dual_connection(
        source_node,
        target_node
    ):
        return ConnectionType.DUAL

    if is_reverse_connection(
        source_node,
        target_node
    ):
        return ConnectionType.REVERSE

    return ConnectionType.REGULAR


def is_dual_connection(
    source_node: NodeData,
    target_node: NodeData
) -> bool:
    return (
        target_node.node_id
        in source_node.outgoing
        and target_node.node_id
        in source_node.incoming
        and source_node.node_id
        in target_node.outgoing
        and source_node.node_id
        in target_node.incoming
    )


def is_reverse_connection(
    source_node: NodeData,
    target_node: NodeData
) -> bool:
    return (
        target_node.node_id
        in source_node.outgoing
        and source_node.node_id
        not in target_node.incoming
    )


def calculate_connection_endpoints(
    source_x: float,
    source_z: float,
    target_x: float,
    target_z: float,
    node_diameter: float
) -> tuple[QPointF, QPointF] | None:
    geometry = calculate_connection_geometry(
        source_x=source_x,
        source_z=source_z,
        target_x=target_x,
        target_z=target_z,
        node_diameter=node_diameter
    )

    if geometry is None:
        return None

    return (
        geometry.source_tip,
        geometry.target_tip
    )

def calculate_connection_geometry(
    source_x: float,
    source_z: float,
    target_x: float,
    target_z: float,
    node_diameter: float
) -> ConnectionGeometry | None:
    delta_x = target_x - source_x
    delta_z = target_z - source_z

    distance = math.hypot(
        delta_x,
        delta_z
    )

    if distance <= MINIMUM_CONNECTION_LENGTH:
        return None

    direction_x = delta_x / distance
    direction_z = delta_z / distance

    node_radius = node_diameter / 2

    maximum_offset = max(
        0.0,
        distance / 2 - MINIMUM_VISIBLE_LENGTH
    )

    endpoint_offset = min(
        node_radius,
        maximum_offset
    )

    source_tip = QPointF(
        source_x
        + direction_x * endpoint_offset,
        source_z
        + direction_z * endpoint_offset
    )

    target_tip = QPointF(
        target_x
        - direction_x * endpoint_offset,
        target_z
        - direction_z * endpoint_offset
    )

    return ConnectionGeometry(
        source_tip=source_tip,
        target_tip=target_tip,
        direction_x=direction_x,
        direction_z=direction_z,
        distance=distance,
        endpoint_offset=endpoint_offset
    )

def create_arrow_polygon(
    tip: QPointF,
    direction_x: float,
    direction_z: float,
    arrow_length: float,
    arrow_width: float
) -> QPolygonF:
    base_x = (
        tip.x()
        - direction_x * arrow_length
    )

    base_z = (
        tip.y()
        - direction_z * arrow_length
    )

    perpendicular_x = -direction_z
    perpendicular_z = direction_x

    half_width = arrow_width / 2

    left_point = QPointF(
        base_x
        + perpendicular_x * half_width,
        base_z
        + perpendicular_z * half_width
    )

    right_point = QPointF(
        base_x
        - perpendicular_x * half_width,
        base_z
        - perpendicular_z * half_width
    )

    return QPolygonF(
        [
            tip,
            left_point,
            right_point
        ]
    )