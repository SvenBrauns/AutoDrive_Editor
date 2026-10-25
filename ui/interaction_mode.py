from enum import Enum, auto


class InteractionMode(Enum):
    """The active map tool. Exactly one is active at a time."""

    NAVIGATE = auto()
    SELECT = auto()
    MOVE_NODES = auto()

    @property
    def display_name(self) -> str:
        display_names = {
            InteractionMode.NAVIGATE: "Navigation",
            InteractionMode.SELECT: "Auswahl",
            InteractionMode.MOVE_NODES: "Nodes verschieben"
        }

        return display_names[self]
