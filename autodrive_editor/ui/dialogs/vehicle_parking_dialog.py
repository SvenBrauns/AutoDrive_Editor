"""Lists the vehicles and implements of a savegame with their picture and parking marker; each
marker is chosen in a dropdown that can be searched by typing."""

from dataclasses import dataclass

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from autodrive_editor.i18n import tr

PICTURE_SIZE = 64


@dataclass(frozen=True)
class VehicleRow:
    unique_id: str
    name: str
    attached_to: str
    park: int | None
    picture: Image.Image | None


class VehicleParkingDialog(QDialog):
    def __init__(self, rows: list[VehicleRow], markers: list[tuple[int, str]], parent=None):
        """markers: number and label of each marker, in the order they are offered."""

        super().__init__(parent)

        self.setWindowTitle(tr("Vehicle parking positions"))
        self.resize(760, 560)
        self.rows = rows

        self.table = QTableWidget(len(rows), 4)
        self.table.setHorizontalHeaderLabels(
            ["", tr("Vehicle"), tr("Attached to"), tr("Parking marker")]
        )
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(PICTURE_SIZE + 4)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, PICTURE_SIZE + 8)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.combos: list[QComboBox] = []

        for index, row in enumerate(rows):
            self.table.setCellWidget(index, 0, _picture_label(row.picture))
            self.table.setItem(index, 1, QTableWidgetItem(row.name))
            self.table.setItem(index, 2, QTableWidgetItem(row.attached_to))
            combo = _marker_combo(markers, row.park)
            self.table.setCellWidget(index, 3, combo)
            self.combos.append(combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        note = QLabel(tr("Type into a marker field to search the markers."))
        note.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def set_park(self, unique_id: str, number: int | None):
        """Chooses the marker of a vehicle, as the user does."""

        index = next(i for i, row in enumerate(self.rows) if row.unique_id == unique_id)
        combo = self.combos[index]
        combo.setCurrentIndex(combo.findData(number))

    def changes(self) -> dict[str, int | None]:
        """Unique id -> new marker number (None: no parking position) of the changed vehicles."""

        changes = {}

        for row, combo in zip(self.rows, self.combos, strict=True):
            number = combo.currentData()

            if number != row.park:
                changes[row.unique_id] = number

        return changes


def _picture_label(picture: Image.Image | None) -> QLabel:
    label = QLabel()
    label.setAlignment(Qt.AlignCenter)

    if picture is not None:
        thumbnail = picture.copy()
        thumbnail.thumbnail((PICTURE_SIZE, PICTURE_SIZE))
        image = QImage(
            thumbnail.tobytes("raw", "RGBA"),
            thumbnail.width,
            thumbnail.height,
            QImage.Format_RGBA8888,
        ).copy()
        label.setPixmap(QPixmap.fromImage(image))

    return label


def _marker_combo(markers: list[tuple[int, str]], park: int | None) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)
    combo.addItem(tr("(none)"), None)

    for number, label in markers:
        combo.addItem(label, number)

    if park is not None and combo.findData(park) < 0:
        # A number beyond the markers, e.g. a marker deleted in the game: shown, kept if untouched.
        combo.addItem(tr("Marker {number} (not in the network)", number=park), park)

    combo.setCurrentIndex(max(combo.findData(park), 0))

    completer = QCompleter(combo.model(), combo)
    completer.setFilterMode(Qt.MatchContains)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)

    def keep_valid_text():
        index = combo.findText(combo.currentText())

        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setEditText(combo.itemText(combo.currentIndex()))

    combo.lineEdit().editingFinished.connect(keep_valid_text)

    return combo
