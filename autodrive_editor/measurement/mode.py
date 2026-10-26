from enum import Enum

from autodrive_editor.i18n import tr


class MeasurementMode(Enum):
    """Which measuring tool is active."""

    INACTIVE = "inactive"
    DISTANCE = "distance"
    ANGLE = "angle"

    @property
    def display_name(self) -> str:
        display_names = {
            MeasurementMode.INACTIVE: tr("Inactive"),
            MeasurementMode.DISTANCE: tr("Distance"),
            MeasurementMode.ANGLE: tr("Angle"),
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
