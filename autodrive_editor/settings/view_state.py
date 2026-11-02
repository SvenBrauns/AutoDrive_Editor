"""Where the map view looks: kept per file, so a file opens where it was left."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ViewState:
    """Scene point in the middle of the view, zoom factor and rotation in degrees."""

    x: float
    z: float
    zoom: float
    rotation: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict) -> "ViewState":
        return cls(*(float(values[name]) for name in ("x", "z", "zoom", "rotation")))
