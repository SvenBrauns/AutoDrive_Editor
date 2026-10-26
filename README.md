# AutoDrive FS25 Editor

Editor for AutoDrive route networks in Farming Simulator 25. It shows the network on the map image with terrain heights and provides tools to edit nodes, connections, markers and whole route sections. All changes can be undone.

The editor supports only FS25.

The interface is currently German. Menu and tool names below are the German labels as they appear in the app; the English descriptions explain what they do.

## Download

The Windows version is available as a zip under [Releases](https://github.com/SvenBrauns/AutoDrive_Editor/releases). Unzip it and start `AutoDrive Editor.exe`. No Python installation is needed.

## First start

The editor looks for the FS25 user folder (usually `Dokumente\My Games\FarmingSimulator2025`) and the game's installation folder and shows both for you to check. You can change either later under `Datei → Einstellungen` (File → Settings).

Map images are not shipped with the editor. Use `Karte → Karten scannen` (Map → Scan maps) to search the `mods` folder and the base game maps; the editor then imports the map image, heightmap and map size. This is needed only once per map. After that, the matching map loads automatically when you open a route. If the map is missing, the editor offers the scan directly.

## Opening a network

- **Route öffnen** (Open route), recommended: routes from AutoDrive's RoutesManager. AutoDrive can reload them in a running game, so the game does not need to be restarted.
- **Savegame öffnen** (Open savegame): the `AutoDrive_config.xml` of a savegame. The savegame's heightmap is loaded with it.
- **XML-Datei öffnen** (Open XML file): a single file in either format.

## Controls

- **Mouse wheel** zooms, **left drag** moves the map, **middle drag** rotates the view.
- **Right click** or **Esc** cancels the current step of a tool; **Enter** confirms it (for example for curves).
- The tools are in the tool panel; the status bar shows what the active tool expects next.

| Tool (as shown in the app) | Key | What it does |
| --- | --- | --- |
| Navigation | `N` | Move and rotate the map |
| Auswahl (Selection) | `A` | Click or right-drag to select; Shift + right-drag for freehand selection; Ctrl adds to the selection |
| Verschieben (Move) | `V` | Drag a node or the selection |
| Rotieren (Rotate) | `R` | Rotate the selection using the ring (Shift: 15° steps) |
| Erstellen Regular / Subprio (Create) | `E` / `Shift+E` | Create a node on free ground |
| Typ wechseln (Toggle type) | `T` | Switch between Regular and Subprio |
| Löschen (Delete) | `L` | Delete a node or the selection |
| Verbinden Regular / Dual / Reverse (Connect) | `1` / `2` / `3` | Click nodes one after another to connect them |
| Richtung umkehren (Reverse direction) | `U` | Click a connection to reverse it; inside a selection, all connections of the selection are reversed |
| Position eingeben (Enter position) | `P` | Enter a node's X/Y/Z as numbers |
| Horizontal / vertikal ausrichten (Align) | `H` / `J` | Put the selection on the line through a reference node |
| Höhe wie Referenz / aus Heightmap (Height) | `Y` / `Shift+Y` | Set the heights of the selection |
| Linie (Line) | `I` | Straight route section with even node spacing |
| Bézierkurve / Kreisbogen (Curve / Arc) | `B` / `K` | Click start and end, drag the handles, press Enter |
| Marker hinzufügen / bearbeiten (Marker) | `M` / `Shift+M` | Add or edit a marker; enter its name and group |
| Marker verschieben / löschen (Marker) | `Ctrl+M` / `Ctrl+Shift+M` | Move a marker to another node or delete it |

Also available: Undo and Redo (`Ctrl+Z` / `Ctrl+Y`), Copy, Cut and Paste (`Ctrl+C/X/V`; `Ctrl+Shift+V` pastes at the original position), the grid with snapping (`G`), distance and angle measurement, and the `Marker` dock with all marker groups.

## Saving

`Datei → Speichern` (File → Save, `Ctrl+S`) writes to the same format and file you loaded from. Before the first overwrite, the editor creates a backup copy (`.bak`). For savegames, the marker targets of vehicles in `vehicles.xml` are updated as well.

`Speichern unter` (Save as) saves a route as a new route in the RoutesManager.

Unsaved changes are backed up automatically every few minutes (interval under `Datei → Einstellungen`). If the editor closes unexpectedly, it offers to restore them on the next start.

## License

GNU General Public License v3.0 or later, see [LICENSE](LICENSE). The Windows version contains PySide6/Qt (LGPLv3) and Pillow, see [THIRD_PARTY_NOTICES.md](packaging/THIRD_PARTY_NOTICES.md).

The editor contains no files from Farming Simulator or from map mods. Map images and heightmaps are read from your own installation. This project has no connection to GIANTS Software.

For development, see [DEVELOPMENT.md](DEVELOPMENT.md).
