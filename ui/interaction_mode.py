from enum import Enum, auto


class InteractionMode(Enum):
    """The active map tool. Exactly one is active at a time."""

    NAVIGATE = auto()
    SELECT = auto()
    MOVE_NODES = auto()
    DELETE_NODES = auto()
    CONNECT_REGULAR = auto()
    CONNECT_DUAL = auto()
    CONNECT_REVERSE = auto()

    @property
    def display_name(self) -> str:
        display_names = {
            InteractionMode.NAVIGATE: "Navigation",
            InteractionMode.SELECT: "Auswahl",
            InteractionMode.MOVE_NODES: "Nodes verschieben",
            InteractionMode.DELETE_NODES: "Nodes löschen",
            InteractionMode.CONNECT_REGULAR: "Verbinden (Regular)",
            InteractionMode.CONNECT_DUAL: "Verbinden (Dual)",
            InteractionMode.CONNECT_REVERSE: "Verbinden (Reverse)"
        }

        return display_names[self]
