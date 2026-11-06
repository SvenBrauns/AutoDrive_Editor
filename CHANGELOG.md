# Version history

## 2.0.0

Generators build routes, junctions, roads, station lanes, parking spots and bunker silo lanes from the map's data, in a planning mode that applies them as one undo step. With the companion mod `FS25_AutoDriveEditorLink` the editor takes a picture of the map in the running game and reloads saved networks there.

**Generators and planning**

- Planning mode (`Edit → Planning mode`, `Ctrl+P`, button at the right of the toolbar): edit with all tools, then apply the plan as one undo step or discard it. Changed nodes get a blue halo; saving and autosave wait for the plan, and the edits made before it are backed up
- Generate tool (`G`, replaces the Parking spots tool; grid snapping moved to `S`): its tasks Route, Junction, Parking spots, Stations, Bunker silos and Roads are buttons in the options bar and entries of the `Generate` menu. It starts planning mode and shows the name and category of the building under the pointer
- Find route: click nodes, connections or free ground as waypoints and get a drivable one-way route over the savegame's drivability map, built like hand-drawn courses (straights, arcs through the corners, nodes spaced as AutoDrive records them). It prefers roads and yards, reuses routes in the plan, and is searched again while waypoints are dragged; parts crossing obstacles are red, unreachable waypoints get a red dashed gap. Several starts (`Shift`+click) and ends (`Ctrl`+click) build a tree of routes sharing nodes. The status bar warns about doubtful joins (at a marker, from a node nothing drives to, into a dead end)
- Junctions: drag from a road towards a yard to build a crossing box or turn curves, with a stem of two lanes, one two-way lane or one one-way lane. Turns that do not fit are drawn red dashed and listed
- Roads: AutoDrive roads along the map's traffic lanes, for the whole map, a box or a clicked road; existing roads are skipped and joined, or replaced; two one-way lanes or one two-way lane; junction boxes where three or four roads meet. Places to look at are listed in the `Road network` group of the Check dock
- Station lanes: `View → Show → Stations` draws an arrow at each stop of selling points, productions, silos, animal barns and diesel tanks. Click a station or right-drag a box; a dialog creates a one-way subprio lane with a marker over each chosen stop, adjustable on the map. `Draw yard road` lays a road past the stops, attaching each as a branch, a shared branch, a back-in bay or its own lane
- Parking spots in one or several sheds of a type, drive-through bays with several positions in a row, shown on the map while the dialog is open
- Bunker silos (`View → Show → Bunker silos`): back-in or drive-through lanes for one or several silos, one lane per ~5.5 m of width, with the open side taken from the drivability map
- Marker names and groups are patterns (`{building}`, `{type}`, `{n}`, `{fill}`, `{action}`, `{letter}`), set per stop type under `File → Settings → Generators`, together with curve radius, node spacing, vehicle width, safety margin and lane lengths. Curves get a node every 15°
- `Generate → Building types…`: move the savegame's building types between Stations, Sheds, Bunker silos and Other, or hide them

**Editing**

- The tools sit in a one-column strip at the left; Create, Connect, Draw (Line, Arc, Bézier), Marker and Measure are one tool each with their variants in the options bar above the map, which shows the active tool's options. Left-drag on free ground pans in every tool, so the Navigation tool is gone
- Road editing: Create inserts a node into a clicked connection, Connect draws a road from click to click, `Draw → Parallel` (`Shift+I`) adds a lane beside the selected roads, and Delete and reconnect (`Shift+Del`) joins the ends of the deleted nodes
- `Edit → Select all` (`Ctrl+A`); a double-click or `Edit → Select road piece` selects a road up to the next junctions
- `Edit → Find marker or node…` (`Ctrl+F`) filters the Markers dock by name or group, or offers a node by number
- `Edit → Keep heights when pasting`, e.g. for bridges and ramps
- The Inspector dock shows the selected node; the nodes connected to the node under the pointer are drawn purple
- `+`/`-` zoom, `View → Zoom to selection` (`F`), `View → Show whole map` (`Home`); a scale bar and the map position under the pointer in the status bar
- Measuring points on a node move with it

**Files and maps**

- One Open screen (`Ctrl+O`) lists the savegames and RoutesManager routes; it replaces the Open dialog and the welcome page. Savegames are named by folder first, and savegames without AutoDrive data open with an empty network
- A route opens alone, on the map named in `routes.xml`; linking a savegame to a route is gone
- Maps are imported automatically in the background when a file opens, and offered again when the map's mod was updated. `File → Settings → Maps` lists the imported maps to re-import, remove or import from a mod zip; the Map menu is gone
- `View → Ground map` (drawn from the ground textures, with field numbers) and `View → Show → Drivability map`; `View → Show → Sheds` includes the map's own buildings. Terrain heights are interpolated between heightmap pixels
- Saving runs the network check first, names vehicles whose target marker was deleted, and warns when the file was changed on disk (usually by the game). `File → Reload` (`F5`) loads it again
- `File → Save as route…` (`Ctrl+Shift+S`) keeps a version of the network in the RoutesManager; `File → Load route into savegame…` puts such a route back
- The window keeps its size and docks, each recent file opens at its last view, and the last file opens again at startup. Savegames open faster thanks to a building cache
- The network check also finds invalid connection references and unconnected nodes

**Companion mod**

- `View → Background → Capture game picture…`: the companion mod `FS25_AutoDriveEditorLink` renders the whole map from above in the running game, shown as `View → Background → Game picture`; `Refresh game picture tiles` renders marked tiles again. The game's weather and time are restored afterwards
- Save on a savegame the game is running reloads it in the game

**Help**

- `Help → Manual` (`F1`) in English or German, `Help → Debug log` and `Help → Debug info`

## 1.2.0 – 2026-10-29

- Dual connections get an arrow pointing to each end
- Connections are always colored by their type, also into subprio nodes; the separate subprio connection color and `View → Show → Subprio connections` are gone
- The colors of regular and subprio nodes can be set under `View → Display options`
- Routes can be linked to a savegame (`File → Link savegame…`, also offered when a route is opened) to show where its vehicles park; the editor remembers the link for the route
- A route linked to a savegame uses the savegame's heightmap, which includes terrain changes made in game
- The debug info shows the number of a selected marker
- `View → Show → Sheds`: outlines of the indoor areas of the buildings placed in the loaded or linked savegame
- Parking spots tool (`S`, next to Selection): click a shed to create its parking spots, backed in or driven through, with markers and shared entry and exit lines, in one undo step
- Parking spot layouts can be saved as named templates per shed type; the last used one is applied when the dialog opens
- `File → Open…` (`Ctrl+O`) replaces Open route, Open savegame and Open XML file: routes and savegames on two tabs, any XML file with `Browse file…`
- Project files are gone: the matching map loads automatically, and savegame links are remembered per route. `Load project` and `Save project` are removed

## 1.1.0 – 2026-10-27

- `Help → Check for updates`: asks GitHub whether a newer version exists and links to its release page; optional check at startup (off by default, set in the first-start dialog or under `File → Settings`)

## 1.0.0 – 2026-10-27

The editor can now do everything the AutoDrive Course Editor 1.1.1 can do for Farming Simulator 25, except its experimental tools.

- Network check (`Check → Check network`): find and fix overlapping nodes, nodes outside the map and heights that differ from the heightmap; entries can be ignored
- `View → Show`: show and hide nodes, node IDs, each connection type, markers, marker names and the parking positions of vehicles
- Minimum and maximum size of nodes on screen
- Faster drawing of large networks at every zoom level
- The top toolbar shows larger icons and has copy, cut and paste
- Move tool: Shift moves along one grid axis only
- Rotate tool: the snap step for Shift can be set (default 15°)
- Bézier curve with one or two control points
- The options of the Rotate, Line, Bézier and Arc tools open from the arrow on their button
- Recently opened files in `File → Open recent` and on the welcome screen
- Log file and an error dialog for unexpected errors
- `Help` menu with this version history
- Keyboard shortcuts can be changed under `File → Settings → Shortcuts`
- Light and dark theme, or following Windows (`File → Settings`)
- New README with screenshots and a comparison with the AutoDrive Course Editor; the detailed guide moved to `MANUAL.md`
- The exe shows its version under `Properties → Details`

## 0.2.0 – 2026-10-26

- Line, Bézier curve and arc tools with even node spacing
- Interface in English and German, language setting (default: Windows language)
- README in English and German

## 0.1.0 – 2026-10-26

First release as a Windows program.

- Open routes from the RoutesManager, savegames and AutoDrive XML files of Farming Simulator 25
- Map images and heightmaps imported from map mods and the base game maps; the matching map is loaded with each route or savegame
- Select, move, rotate, create, delete and connect nodes; switch between Regular and Subprio
- Reverse connection directions, enter node positions as numbers, align nodes and set heights
- Markers: add, edit, move and delete, with a dock for all marker groups
- Copy, cut and paste of nodes
- Grid with snapping, distance and angle measurement
- Undo and redo for every change
- Save into the loaded format with a backup copy, Save as, autosave of unsaved changes
- Setup dialog on first start
