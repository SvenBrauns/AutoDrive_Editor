from dataclasses import dataclass

from autodrive_editor.rendering.connections.connection_data import ConnectionKind


@dataclass(frozen=True)
class Visibility:
    """What is shown on the map. Hidden nodes and connections can only be clicked or
    area-selected while hidden_selectable is on."""

    nodes: bool = True
    node_ids: bool = False
    regular_connections: bool = True
    dual_connections: bool = True
    reverse_connections: bool = True
    subprio_connections: bool = True
    markers: bool = True
    parking: bool = True
    hidden_selectable: bool = False

    def shows_connection(self, kind: ConnectionKind) -> bool:
        return getattr(self, f"{kind.value}_connections")

    @property
    def nodes_selectable(self) -> bool:
        return self.nodes or self.hidden_selectable

    def connection_selectable(self, kind: ConnectionKind) -> bool:
        return self.shows_connection(kind) or self.hidden_selectable
