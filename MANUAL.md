# AutoDrive FS25 Editor – Manual

**English** | [Deutsch](MANUAL.de.md) · back to the [README](README.md)

- [First start](#first-start)
- [Opening a network](#opening-a-network)
- [Controls](#controls)
- [Display](#display)
- [Checking the network](#checking-the-network)
- [Saving](#saving)
- [Settings](#settings)
- [Help and errors](#help-and-errors)

## First start

The editor looks for the FS25 user folder (usually `Documents\My Games\FarmingSimulator2025`) and the game's installation folder and shows both for you to check. You can change either later under `File → Settings`.

Map images are not shipped with the editor. Use `Map → Scan maps` to search the `mods` folder and the base game maps; the editor then imports the map image, heightmap and map size. This is needed only once per map. After that, the matching map loads automatically when you open a route. If the map is missing, the editor offers the scan directly.

## Opening a network

- **Open route** (recommended): routes from AutoDrive's RoutesManager. AutoDrive can reload them in a running game, so the game does not need to be restarted.
- **Open savegame**: the `AutoDrive_config.xml` of a savegame. The savegame's heightmap is loaded with it.
- **Open XML file**: a single file in either format.

## Controls

- **Mouse wheel** zooms, **left drag** moves the map, **middle drag** rotates the view.
- **Right click** or **Esc** cancels the current step of a tool; **Enter** confirms it (for example for curves).
- The tools are in the tool panel; the status bar shows what the active tool expects next. Tools with options have a small arrow on their button that opens them.

| Tool | Key | What it does |
| --- | --- | --- |
| Navigation | `N` | Move and rotate the map |
| Selection | `A` | Click or right-drag to select; Shift + right-drag for freehand selection; Ctrl adds to the selection |
| Move | `V` | Drag a node or the selection; Shift moves along one grid axis only |
| Rotate | `R` | Rotate the selection using the ring; Shift snaps in steps (default 15°, set with the arrow) |
| Create (Regular / Subprio) | `E` / `Shift+E` | Create a node on free ground |
| Toggle type | `T` | Switch between Regular and Subprio |
| Delete | `L` | Delete a node or the selection |
| Connect (Regular / Dual / Reverse) | `1` / `2` / `3` | Click nodes one after another to connect them |
| Reverse direction | `U` | Click a connection to reverse it; inside a selection, all connections of the selection are reversed |
| Enter position | `P` | Enter a node's X/Y/Z as numbers |
| Align horizontally / vertically | `H` / `J` | Put the selection on the line through a reference node |
| Height like reference / Height from heightmap | `Y` / `Shift+Y` | Set the heights of the selection |
| Line | `I` | Straight route section with even node spacing (spacing, connection type and node type under the arrow) |
| Bézier curve / Arc | `B` / `K` | Click start and end, drag the handles, press Enter; the Bézier curve has one or two control points |
| Add marker / Edit marker | `M` / `Shift+M` | Add or edit a marker; enter its name and group |
| Move marker / Delete marker | `Ctrl+M` / `Ctrl+Shift+M` | Move a marker to another node or delete it |

Also available: Undo and Redo (`Ctrl+Z` / `Ctrl+Y`), Copy, Cut and Paste (`Ctrl+C/X/V`; `Ctrl+Shift+V` pastes at the original position), the grid with snapping (`G`), distance and angle measurement, and the `Markers` dock with all marker groups.

## Display

`View → Show` switches nodes, node IDs, each connection type (Regular, Dual, Reverse, Subprio), markers, marker names and the parking positions of vehicles on and off. Subprio connections are the ones leading into a Subprio node. Node IDs appear only when zoomed in; parking positions (a "P" next to the marker) are read from a savegame's `vehicles.xml`. Hidden nodes and connections cannot be clicked or selected unless `Hidden items can be selected` is on. Sizes and colors are set under `View → Display options`. All switches are remembered.

## Checking the network

`Check → Check network` lists overlapping nodes, nodes outside the map and, with a heightmap loaded, nodes whose height differs too much from the terrain. The distance for overlapping nodes and the allowed height difference are set at the top of the dock. Click an entry to show it on the map. `Fix selected` or `Fix all` merges overlapping nodes into one (the node with a marker, otherwise the lowest ID), moves nodes back onto the map and sets heights from the heightmap. Each kind of fix is one undo step.

Entries that are fine as they are, such as nodes on a bridge, can be hidden with `Ignore`. They move to the `Ignored` group and are not fixed by `Fix all`; `Don't ignore` brings them back. An ignored entry also shows up again when one of its nodes is moved. The checkboxes switch off a whole check. Ignored entries and switched-off checks are remembered for each route or savegame.

## Saving

`File → Save` (`Ctrl+S`) writes to the same format and file you loaded from. Before the first overwrite, the editor creates a backup copy (`.bak`). For savegames, the marker targets of vehicles in `vehicles.xml` are updated as well.

`Save as` saves a route as a new route in the RoutesManager.

Unsaved changes are backed up automatically every few minutes (interval under `File → Settings`). If the editor closes unexpectedly, it offers to restore them on the next start.

`File → Open recent` and the welcome screen list the last five opened routes, savegames, XML files and projects.

## Settings

The editor is available in English and German. On first start it uses German on a German Windows and English everywhere else. You can change the language under `File → Settings`; it takes effect after a restart.

The editor follows the light or dark mode of Windows. Under `File → Settings` you can choose a light or dark theme instead, and change the keyboard shortcuts of all menu entries and tools on the `Shortcuts` tab.

## Help and errors

`Help → Version history` shows what changed in each version, `Help → About` shows the version and license. If an unexpected error occurs, the editor shows a message and keeps running. The details are written to a log file (`Help → Open log folder`, in `%APPDATA%\AutoDrive Editor\logs`); please attach it when reporting a bug.
