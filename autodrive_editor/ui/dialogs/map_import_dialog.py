from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from autodrive_editor.file_io.map_mod import MapEntry, MapMod
from autodrive_editor.terrain.map_cache import MapCache

MAP_SCALE_LABELS = {1: "Originalgröße", 2: "4x", 4: "16x", 8: "64x"}


class MapImportDialog(QDialog):
    """Lists the maps found in the mods folder; the user checks the ones to
    import. Maps already imported and maps that cannot be imported are
    marked."""

    def __init__(self, map_mods: list[MapMod], map_cache: MapCache, skipped=(), parent=None):
        super().__init__(parent)

        self.setWindowTitle("Karten scannen")
        self.resize(820, 440)

        hint_text = (
            "Kartenmods im Mods-Ordner. Ausgewählte Karten werden importiert: Kartenbild "
            "und Heightmap werden im Datenordner des Editors abgelegt und danach beim "
            "Öffnen einer Route oder eines Savegames automatisch geladen."
        )

        if skipped:
            hint_text += (
                f"\nNicht lesbar und übersprungen: {', '.join(name for name, _ in skipped)}"
            )

        hint = QLabel(hint_text, self)
        hint.setWordWrap(True)

        self.table = QTreeWidget(self)
        self.table.setHeaderLabels(["Karte", "Mod", "Größe", "Status"])
        self.table.setRootIsDecorated(False)

        for map_mod in map_mods:
            for entry in map_mod.maps:
                self._add_row(map_mod, entry, map_cache)

        for column in range(4):
            self.table.resizeColumnToContents(column)

        select_all = QPushButton("Alle neuen auswählen", self)
        select_all.clicked.connect(self.select_new_maps)

        self.buttons = QDialogButtonBox(self)
        self.import_button = self.buttons.addButton(
            "Importieren", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.table.itemChanged.connect(lambda item, column: self._update_import_button())

        bottom = QHBoxLayout()
        bottom.addWidget(select_all)
        bottom.addStretch(1)
        bottom.addWidget(self.buttons)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.table, 1)
        layout.addLayout(bottom)

        self._update_import_button()

    def _add_row(self, map_mod: MapMod, entry: MapEntry, map_cache: MapCache):
        imported = map_cache.find_import(map_mod.name, entry) is not None

        if entry.problems:
            status = ", ".join(entry.problems)
        elif imported:
            status = "bereits importiert"
        else:
            status = "neu"

        item = QTreeWidgetItem(
            [entry.title, map_mod.name, MAP_SCALE_LABELS.get(entry.map_scale, "?"), status]
        )
        item.setData(0, Qt.ItemDataRole.UserRole, (map_mod, entry, imported))

        if entry.problems:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        else:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)

        self.table.addTopLevelItem(item)

    def _items(self):
        return [self.table.topLevelItem(row) for row in range(self.table.topLevelItemCount())]

    def select_new_maps(self):
        for item in self._items():
            _, entry, imported = item.data(0, Qt.ItemDataRole.UserRole)

            if not entry.problems:
                item.setCheckState(
                    0, Qt.CheckState.Unchecked if imported else Qt.CheckState.Checked
                )

    @property
    def chosen_maps(self) -> list[tuple[MapMod, MapEntry]]:
        return [
            item.data(0, Qt.ItemDataRole.UserRole)[:2]
            for item in self._items()
            if item.flags() & Qt.ItemFlag.ItemIsUserCheckable
            and item.checkState(0) == Qt.CheckState.Checked
        ]

    def _update_import_button(self):
        self.import_button.setEnabled(bool(self.chosen_maps))
