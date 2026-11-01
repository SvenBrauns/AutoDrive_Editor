import math
from collections.abc import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

from autodrive_editor.i18n import tr
from autodrive_editor.terrain.game_picture import PictureGrid
from autodrive_editor.terrain.picture_capture import estimate, whole_map_tiles

RESOLUTIONS = (0.25, 0.5)


def minutes(seconds: float) -> int:
    return max(1, math.ceil(seconds / 60))


class PictureCaptureDialog(QDialog):
    """Asks for the resolution and wait time of a game picture capture. The status line is
    checked every second; Start works only while the game is ready."""

    def __init__(
        self,
        check: Callable[[], tuple[bool, str]],
        map_size: float,
        current_m_per_px: float | None,
        wait_ms: int,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(tr("Capture game picture"))
        self.check = check
        self.map_size = map_size
        self.current_m_per_px = current_m_per_px

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)

        self.wait_input = QSpinBox(self)
        self.wait_input.setRange(100, 3000)
        self.wait_input.setSingleStep(50)
        self.wait_input.setSuffix(" ms")
        self.wait_input.setValue(wait_ms)
        self.wait_input.setToolTip(
            tr(
                "Time the game gets to load a place before it renders it. "
                "Raise it if tiles have holes."
            )
        )

        resolution_box = QGroupBox(tr("Resolution"), self)
        resolution_layout = QVBoxLayout(resolution_box)
        self.resolution_buttons = {}

        for m_per_px in RESOLUTIONS:
            button = QRadioButton(resolution_box)
            button.toggled.connect(self._update_texts)
            resolution_layout.addWidget(button)
            self.resolution_buttons[m_per_px] = button

        self.replace_label = QLabel(resolution_box)
        self.replace_label.setWordWrap(True)
        resolution_layout.addWidget(self.replace_label)
        self.resolution_buttons[current_m_per_px or RESOLUTIONS[0]].setChecked(True)
        self.wait_input.valueChanged.connect(self._update_texts)

        note = QLabel(
            tr(
                "The game is set to 12:00 and sun; afterwards the old weather and time come back. "
                "The game freezes briefly for each tile. The editor stays usable, the tiles "
                "appear as they arrive."
            ),
            self,
        )
        note.setWordWrap(True)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.start_button = self.buttons.addButton(
            tr("Start"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow(tr("Wait per tile:"), self.wait_input)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(resolution_box)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(self.buttons)
        self.setMinimumWidth(420)

        self._update_texts()
        self.update_status()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)

    @property
    def m_per_px(self) -> float:
        return next(
            value for value, button in self.resolution_buttons.items() if button.isChecked()
        )

    @property
    def wait_ms(self) -> int:
        return self.wait_input.value()

    def update_status(self):
        ready, text = self.check()
        self.status_label.setText(text)
        self.start_button.setEnabled(ready)

    def _update_texts(self):
        for m_per_px, button in self.resolution_buttons.items():
            count = len(whole_map_tiles(PictureGrid(self.map_size, m_per_px)))
            seconds, megabytes = estimate(count, self.wait_ms)
            button.setText(
                tr(
                    "{resolution} m/px · {count} tiles · about {minutes} min, {size} MB",
                    resolution=f"{m_per_px:g}",
                    count=count,
                    minutes=minutes(seconds),
                    size=round(megabytes),
                )
            )

        replaces = self.current_m_per_px not in (None, self.m_per_px)
        self.replace_label.setVisible(replaces)
        self.replace_label.setText(
            tr(
                "Replaces the current picture ({resolution} m/px).",
                resolution=f"{self.current_m_per_px or 0:g}",
            )
        )
