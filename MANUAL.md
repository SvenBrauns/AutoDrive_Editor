# AutoDrive FS25 Editor – Manual

**English** | [Deutsch](MANUAL.de.md) · back to the [README](README.md)

- [First start](#first-start)
- [Opening a network](#opening-a-network)
- [Controls](#controls)
- [Display](#display)
- [Parking spots in sheds](#parking-spots-in-sheds)
- [Checking the network](#checking-the-network)
- [Saving](#saving)
- [Settings](#settings)
- [Help and errors](#help-and-errors)

## First start

The editor looks for the FS25 user folder (usually `Documents\My Games\FarmingSimulator2025`) and the game's installation folder and shows both for you to check. You can change either later under `File → Settings`.

Map images are not shipped with the editor. Use `Map → Scan maps` to search the `mods` folder and the base game maps; the editor then imports the map image, heightmap and map size. This is needed only once per map. After that, the matching map loads automatically when you open a route. If the map is missing, the editor offers the scan directly.

**Ground map.** `View → Ground map` replaces the map image with a map drawn from the map's ground textures: asphalt, concrete, gravel, grass, mud, forest, rock and sand each in their own color, with the field outlines and field numbers on top. It shows the map as the game paints it, which helps where the map image is out of date. Maps imported with an older version of the editor have no ground map; import them again to get one. Importing a large map takes a little longer for this (about 15 seconds for a 16x map).

## Opening a network

`File → Open…` (`Ctrl+O`) shows the routes and savegames of the game folder on two tabs:

- **Routes** (recommended): routes from AutoDrive's RoutesManager. AutoDrive can reload them in a running game, so the game does not need to be restarted.
- **Savegames**: the `AutoDrive_config.xml` of a savegame. The savegame's heightmap is loaded with it.
- **Browse file…**: any AutoDrive XML file in either format.

The dialog opens on the tab you used last.

## Controls

- **Mouse wheel** zooms, **left drag** moves the map, **middle drag** rotates the view.
- **Right click** or **Esc** cancels the current step of a tool; **Enter** confirms it (for example for curves).
- The tools are in the tool panel; the status bar shows what the active tool expects next. Tools with options have a small arrow on their button that opens them.

| Tool | Key | What it does |
| --- | --- | --- |
| Navigation | `N` | Move and rotate the map |
| Selection | `A` | Click or right-drag to select; Shift + right-drag for freehand selection; Ctrl adds to the selection |
| Parking spots | `S` | Click a shed to create parking spots in it, see [Parking spots in sheds](#parking-spots-in-sheds) |
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

## Planning mode

The planning button at the right end of the toolbar (`Edit → Planning mode`, `Ctrl+P`) starts a plan. All tools work as usual, but the edits are collected in the plan: a blue bar above the map shows how many nodes the plan changed, and those nodes get a blue halo. Undo and Redo work inside the plan and stop at its start. `Apply plan` adds the whole plan to the history as one undo step; `Discard plan` reverts all of it. Clicking the planning button again, opening another file or closing the editor asks whether to apply or discard the plan. While a plan is open, saving is not possible and autosave pauses.

## Display

`View → Show` switches nodes, node IDs, each connection type (Regular, Dual, Reverse), markers, marker names, the parking positions of vehicles and sheds on and off. The line color shows the connection type; arrows show the direction, dual connections get one pointing to each end. Subprio nodes are drawn orange. Node IDs appear only when zoomed in; parking positions (a "P" next to the marker) are read from a savegame's `vehicles.xml`. A route needs a linked savegame for this, see [Parking spots in sheds](#parking-spots-in-sheds), which also explains the sheds. Hidden nodes and connections cannot be clicked or selected unless `Hidden items can be selected` is on. Sizes and colors are set under `View → Display options`. All switches are remembered.

## Parking spots in sheds

The editor creates AutoDrive parking spots in the sheds of a savegame.

**Link a savegame.** A route has no savegame. When a route is opened, the editor offers to link one (savegames on the route's map come first); `File → Link savegame…` changes or removes the link. The editor remembers the link for the route. With "Don't ask again for this route" the question no longer comes for that route. The linked savegame's heightmap replaces the map's, since terraforming and buildings change the ground. An opened savegame needs no link.

**Sheds.** `View → Show → Sheds` draws the indoor areas of the savegame's buildings as purple outlines: those placed in game and those that came with the map, unless they were torn down. The building files are read from the game install folder and the mods folder; buildings whose files are missing are left out and counted in the status bar. Only buildings of the Sheds group are drawn as sheds (see Building types below).

**Stations.** `View → Show → Stations` draws a yellow arrow at each stop of the savegame's stations: the spots where vehicles unload or load at selling points, productions, silos, animal barns and diesel tanks. The arrow lies along the lane over the trigger. Most buildings define the spot the game's AI helper drives to; there the arrow follows it. Where a building has none (many diesel tanks and animal barns), the arrow sits on the trigger and follows the building's orientation, so it may point the wrong way. Triggers of the same kind at nearly the same spot, one per fill type, are shown as one stop.

**Building types.** `Generate → Building types…` lists the building types of the savegame that have indoor areas, stations or a bunker silo, in four groups: Stations (unload or load triggers), Sheds (only indoor areas), Bunker silos and Other. A production with a hall is a station, not a shed; farmhouses and weighing stations are in Other, as only the player's character goes inside or vehicles only drive over them. If a type is in the wrong group, choose another one in its `Group` column; unticked types or groups are hidden. `Reset` puts every listed type back in its own group and shows it. Both apply on every map.

**Create parking spots.** Choose the Parking spots tool (`S`); pointing at a shed shows the building's name and category. Left-click a shed outline. The dialog shows a top view of the shed, turned so the open side is at the bottom, with an arrow to north, and updates while you type. The planned spots are also drawn on the map; while the dialog is open the map can be moved, zoomed and rotated, but not edited.

- **Mode**: *Back in* (vehicles reverse into the bay, the marker is at the back wall) or *Drive through* (one forward line per bay through the shed, the exit is on the opposite side).
- **Open side** / **Entry side**: the side the vehicles come in. Click a side or its compass label in the top view to change it.
- **Number of bays**: the bay width is calculated from it and shown below. Bays narrower than 3 m are shown in red and cannot be created.
- **Left wall**, **Right wall**, **Back wall** (or **Exit offset**), **All gaps**: distances in metres. Click a wall or a gap in the top view to edit just that one; a small box opens at the click spot (Enter applies, Esc cancels). Single gaps are kept when the number of bays changes.
- **Positions per bay**, **Position spacing** (drive through only): several parking positions in a row in each bay, the first at the exit offset and the others toward the entry, each with its own marker.
- **Entry line**, **Exit line**: the driving direction of the two lines outside the open side, seen from outside.
- **Marker name**, **Start number**, **Group**: "Shed" from 3 gives "Shed 3", "Shed 4", … With several positions per bay the numbers count on through the positions of each bay, starting at the exit. A new group name creates the group.

When backing in, the side view below shows the line of one bay, which all bays use. Click a segment to change its length, "+" splits a segment in half, `Delete` removes the selected node. The points where the entry and exit lines branch off can be dragged to another node. In drive-through mode the side view only shows the line.

`Create` adds all nodes as subprio nodes at the shed's height, as one undo step. Running it twice creates the spots twice. Afterwards the four open ends of the entry and exit lines are selected, so you can connect them to the road network. `Reset shed settings` brings back the default layout.

**Templates.** `Save as template…` stores the mode, side, number of bays, distances, parking positions and bay line under a name for this shed type, so it works for the same building on any map. Line directions, marker name, start number and group are not stored. `Load template…` lists the templates of the shed type, where they can also be deleted. The dialog opens with the template saved or loaded last for the shed type.

## Checking the network

`Check → Check network` lists overlapping nodes, nodes outside the map and, with a heightmap loaded, nodes whose height differs too much from the terrain, invalid connection references (to a node that does not exist, to the node itself, or an incoming entry without the other node's outgoing entry) and nodes without any connection. The distance for overlapping nodes and the allowed height difference are set at the top of the dock. Click an entry to show it on the map. `Fix selected` or `Fix all` merges overlapping nodes into one (the node with a marker, otherwise the lowest ID), moves nodes back onto the map, sets heights from the heightmap, removes invalid references and deletes nodes without connections (nodes with a marker are kept). Each kind of fix is one undo step.

Entries that are fine as they are, such as nodes on a bridge, can be hidden with `Ignore`. They move to the `Ignored` group and are not fixed by `Fix all`; `Don't ignore` brings them back. An ignored entry also shows up again when one of its nodes is moved. The checkboxes switch off a whole check. Ignored entries and switched-off checks are remembered for each route or savegame.

Saving runs the check first. If it finds problems that are not ignored, the dock shows them and the editor asks whether to save anyway.

## Saving

`File → Save` (`Ctrl+S`) writes to the same format and file you loaded from. Before the first overwrite, the editor creates a backup copy (`.bak`). For savegames, the marker targets of vehicles in `vehicles.xml` are updated as well.

`Save as` saves a route as a new route in the RoutesManager.

Unsaved changes are backed up automatically every few minutes (interval under `File → Settings`). If the editor closes unexpectedly, it offers to restore them on the next start.

`File → Open recent` and the welcome screen list the last five opened routes, savegames and XML files. At startup the editor opens the last one again, unless an autosave is restored; this can be turned off under `File → Settings`.

## Settings

The editor is available in English and German. On first start it uses German on a German Windows and English everywhere else. You can change the language under `File → Settings`; it takes effect after a restart.

The editor follows the light or dark mode of Windows. Under `File → Settings` you can choose a light or dark theme instead, and change the keyboard shortcuts of all menu entries and tools on the `Shortcuts` tab.

`Help → Check for updates` asks GitHub whether a newer version exists. To check automatically at every start, turn this on in the setup dialog on first start or under `File → Settings`. It is off by default, because it connects to github.com. An update is installed by downloading the zip from the release page and replacing the old program folder with it; settings and imported maps are kept.

## Help and errors

`Help → Version history` shows what changed in each version, `Help → About` shows the version and license. If an unexpected error occurs, the editor shows a message and keeps running. The details are written to a log file (`Help → Open log folder`, in `%APPDATA%\AutoDrive Editor\logs`); please attach it when reporting a bug.
