from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class MarkerDialog(QDialog):
    """Asks for a marker's name and group. The group list can be typed
    into; a new name creates that group."""

    EMPTY_NAME_TEXT = "Bitte einen Namen eingeben."
    TAKEN_NAME_TEXT = "Ein anderer Marker heißt bereits so."
    EMPTY_GROUP_TEXT = "Bitte eine Gruppe wählen oder eingeben."
    NEW_GROUP_TEXT = "Die Gruppe „{}“ wird neu angelegt."

    def __init__(
        self,
        title: str,
        name: str,
        group: str,
        groups: list[str],
        taken_names: set[str],
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setMinimumWidth(360)

        self.groups = list(groups)
        self.taken_names = set(taken_names)

        self.name_input = QLineEdit(name, self)

        self.group_input = QComboBox(self)
        self.group_input.setEditable(True)
        self.group_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.group_input.addItems(sorted(self.groups, key=str.casefold))
        self.group_input.setCurrentText(group)

        self.hint_label = QLabel(self)
        self.hint_label.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        form = QFormLayout()
        form.addRow("Name:", self.name_input)
        form.addRow("Gruppe:", self.group_input)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.buttons)

        self.name_input.textChanged.connect(self._validate)
        self.group_input.currentTextChanged.connect(self._validate)

        self.name_input.selectAll()
        self.name_input.setFocus()
        self._validate()

    @property
    def values(self) -> tuple[str, str]:
        return self.name_input.text().strip(), self.group_input.currentText().strip()

    @property
    def is_valid(self) -> bool:
        return self.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()

    def _validate(self):
        name, group = self.values

        problem = None
        if not name:
            problem = self.EMPTY_NAME_TEXT
        elif name in self.taken_names:
            problem = self.TAKEN_NAME_TEXT
        elif not group:
            problem = self.EMPTY_GROUP_TEXT

        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(problem is None)

        if problem is None and group not in self.groups:
            self.hint_label.setText(self.NEW_GROUP_TEXT.format(group))
        else:
            self.hint_label.setText(problem or "")
