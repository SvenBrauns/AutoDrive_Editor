from enum import Enum


class MeasurementMode(Enum):
    """Which measuring tool is active."""

    INACTIVE = "inactive"
    DISTANCE = "distance"
    ANGLE = "angle"

    @property
    def display_name(self) -> str:
        display_names = {
            MeasurementMode.INACTIVE: "Inaktiv",
            MeasurementMode.DISTANCE: "Abstand",
            MeasurementMode.ANGLE: "Winkel",
        }

        return display_names[self]

    @property
    def unit(self) -> str:
        units = {
            MeasurementMode.INACTIVE: "",
            MeasurementMode.DISTANCE: "m",
            MeasurementMode.ANGLE: "°",
        }

        return units[self]
