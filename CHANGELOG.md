# Version history

## Unreleased

- Road editing: Create (`E`/`Shift+E`) inserts a node into a clicked connection, keeping type and direction. Delete got the variant Reconnect (`Shift+L`, or `Edit → Delete selection and reconnect`, `Shift+Del`): nodes in the middle of a road are deleted and its ends joined the same way. Connect (`1`/`2`/`3`) draws a road: a click on free ground or a connection adds a node connected from the previous one. `Draw → Parallel` (`Shift+I`) adds a lane beside the selected roads at the distance of the pointer, in the same or the opposite direction
- Find a marker or node: `Edit → Find marker or node…` (`Ctrl+F`) opens the search field of the Markers dock, which filters markers by name or group; a node number offers that node. `Enter` shows the first result
- The status bar shows the map position under the pointer, and a scale bar sits in the bottom-left corner of the map (`View → Show → Scale bar`)
- `+` and `-` zoom; `View → Zoom to selection` (`F`) fits the selected nodes into the window
- Station yards: `Draw yard road` in the Stations dialog draws a road past the picked stops from clicked corners, one way from first to last corner, or a loop with a two-way road in and out. Each stop is attached as a branch, a chain of close stops sharing one branch, a back-in bay (animal barns) or its own lane (stops far from the road), chosen in the new `Shape` column. `Create` adds it all as one undo step
- Station marker names and groups can use `{fill}` (first fill type) and `{action}` (unload or load); groups are patterns too. Productions are named like `Diesel-unload` in `prod.Distillery` by default
- Curves of Find route, junctions and station lanes get a node every 15° (about 1.6 m on a 6 m arc), as course authors space them

- Parking spots: `Create` no longer selects the line ends, as for station lanes
- Parking spots in several sheds of one type at once: `Shift`+click them and press `Enter`, or right-drag a box. One layout for all, `Shed:` picks the shed the views show, neighbouring sheds share one entry and one exit line, and the marker numbers run on from shed to shed
- Bunker silos (Generate tool, task `Bunker silos`): `View → Show → Bunker silos` draws the silos' floors. Click a silo, or `Shift`+click several and press `Enter`, or right-drag a box; the parking spots dialog then lays out the lanes: back in or drive through and the open side from the drivability map, one lane per ~5.5 m of width, the silo's distances, marker name and group as patterns with the new placeholder `{letter}` (defaults `KS-{letter}-{n}` in `{building}-KS-{letter}`, `DS-…` for drive through, set on `File → Settings → Generators`). Neighbouring silos facing the same way share one entry and one exit line
- The nodes connected to the node under the pointer are drawn purple, in every tool, as in AutoDrive
- `File → Settings → Generators`: curve radius and node spacing on straights (default 12 m) for Find route, Junction and station lanes, vehicle width and safety margin, the lane lengths of station lanes, and a marker name pattern (`{building}`, `{type}`, `{n}`) and group per stop type. The Stations dialog opens it with `Generator settings…`
- Save names the vehicles whose target marker was deleted (they would go to marker 1, a parking target is removed) and asks `Save` or `Cancel` before writing, instead of telling afterwards
- `Edit → Keep heights when pasting` (off by default, remembered): pasted nodes keep their copied heights, e.g. on a bridge or ramp; off, they get the terrain height at the new place
- Starting a plan backs up the edits made before it, so a crash in a long plan loses at most the plan; the plan's own edits are not backed up
- Closing the editor while a route or junction is being searched no longer can crash it
- Savegames open faster: the buildings read from the map and from the game's and mods' building files are kept in `%APPDATA%\AutoDrive Editor\cache` and read again only when those files change
- When a file opens and its map's mod was updated since the map was imported, the editor offers to import it again: `Import`, `Not now` (asked again at the next start) or `Not for this version` (asked again after the next update). Maps imported with an older version are noticed from their next update on
- Maps are imported in the background: the window keeps painting, and `Cancel` stops after the map being imported. `File → Settings → Maps` can re-import several selected maps at once (`Ctrl`/`Shift`+click), and the selected rows are clearly marked
- Savegames are named by folder first, e.g. "savegame1 – Mein Spielstand", in the window title, status bar, `Open recent`, loading text and dialogs, so savegames with the game's default name can be told apart. The Open screen list keeps the plain name next to its number
- While a file loads, the map shows "Loading …" and the pointer waits; at startup the window appears first, gray with the app logo instead of white. The window keeps its size, position and docks between starts, and each recent file opens where its view (position, zoom, rotation) was left. `View → Show whole map` (`Home`) replaces the unused `Reset view`
- Save warns when the network in the file was changed since it was opened or saved, usually by the game: `Save anyway`, `Reload (my changes are lost)` or `Cancel`. A game save with the same network does not warn. `File → Reload` (`F5`) loads the open file again from disk and keeps the view; with unsaved changes it asks first
- Find route with several starts and ends: `Shift`+click a node adds a start, `Ctrl`+click an end, and a route from every start to every end is built as a tree, sharing nodes where routes run together. A click adds a waypoint all routes share and pass in the same direction; pressing on a route, or up to 5 m past where routes split, inserts into the routes there. `Delete` on a start or end removes it with its routes; only changed routes are searched again. `Enter` adds all routes as one undo step
- Find route: the waypoint under the pointer is highlighted and `Delete` removes it (the selection stays); the options bar has `Remove last (Backspace)` and `Clear (Esc)`. `Ctrl+Z` first takes back waypoint changes (add, move, remove) of the route being built, then the plan's edits. After `Enter` the tool starts empty
- Capture game picture: afterwards the game gets its weather back and its time continues from the old time (old time plus the capture's duration), also after Cancel or an error. Needs the updated companion mod
- `File → Load route into savegame…` (savegame open): replaces the network with a RoutesManager route of the savegame's map (Name, Revision, Date, newest first), as one undo step; Save then writes it and reloads it in the game. If no route holds the current network, it first offers to save it as a route. Vehicles keep their targets at markers with the same name and group
- Save on a savegame the game is running reloads it in the game through the companion mod (status `Saved · reloaded in game`); if the game reports an error or does not answer within 30 s a message says the game will overwrite the file on its next save. If the game runs without the mod, a warning says so (once per savegame and session). `File → Save as…` became `Save as route…` (`Ctrl+Shift+S`): it keeps a version of the network in the RoutesManager, suggests the last route's name, and asks before replacing a route of the same name (its revision goes up); a savegame stays open. The hidden test shortcut `Ctrl+Alt+Shift+R` is gone
- `File → Settings → Maps`: the imported maps with size, heightmap and game picture; `Re-import`, `Remove` (with its game picture, the question shows the size), `Import from mod zip…` and `Use this map for the open file` (remembered for that file). The Map menu is gone: `Capture game picture…` and `Refresh game picture tiles` are in `View → Background`; Scan maps, Choose DDS, Choose heightmap, Remove heightmap and Map size are dropped (the size always comes from the map). The first start asks only for the folders
- A map that is not imported yet is imported without asking when a file is opened, with a progress bar: a savegame names its mod (`mapId`), for a route the mods are searched for its map name. Only a map that is not found asks: `Choose mod zip…` or `Continue without map`; the Missing map question is gone. Without a map the map size fits the network (2, 4, 8 or 16 km)
- A route opens alone: its network on the map named in `routes.xml`, without vehicles, sheds or stations. The question to link a savegame on loading and `File → Link savegame…` are gone; Save on a route writes only the route
- One Open screen: the savegames (newest first) and below them the RoutesManager routes, plus `Open other file…`. It lies on the map while nothing is open and comes as a dialog with `File → Open…` (`Ctrl+O`). It replaces the Open dialog with its tabs and the welcome page with its recent list (`Open recent` stays in the File menu). Savegames without AutoDrive data are listed too; they open with an empty network, and Save creates their `AutoDrive_config.xml`
- Create, Connect, Draw (Line, Arc, Bézier) and Marker are one tool each; their variants are buttons in the options bar. The keys stay and pick tool and variant; the tool button shows the current variant. Switching the Draw variant keeps a half drawn path
- Generate: the four tasks (Route, Junction, Parking spots, Stations) are icon buttons in the options bar and entries of the `Generate` menu; the Generate button shows the current task
- Measure is a tool (Distance `D`, Angle `Shift+D`) with `Align view to line` in its options bar; the three measuring buttons left the toolbar. Esc with nothing to clear goes back to the tool used before
- The Tools panel is now a fixed one-column tool strip at the left with all 17 tools. Selection is the start tool; the Navigation tool is gone (left-drag on free ground pans in every tool). Selection and Generate left the top toolbar; `View → Tools` and `Show tool labels` are gone
- Top toolbar: Open and Save (new icons), a Background button with the three backgrounds, then Grid, Snap to grid, Rotation and Refresh game picture tiles. The Grid popup no longer has its own snap checkbox (it showed the wrong key `G`)
- Inspector dock (tabbed with Markers): shows the selected node; the node info left `Debug info`, which keeps only the runtime numbers and moved to `Help → Debug info`
- Options bar above the map: shows the active tool's name and its options. The options of Rotate, Line, Arc, Bézier and Generate moved there from the arrows of their buttons
- `View → Background → Refresh game picture tiles`: mark tiles of the game picture on the map (click, or right-drag a box) and let the game render just those again, e.g. after changing a yard; the status bar shows the estimated time
- `View → Background → Capture game picture…`: the companion mod `FS25_AutoDriveEditorLink` renders the whole map from above in the running game; the editor shows it as `View → Background → Game picture`. Resolution 0.25 or 0.5 m/px, progress and `Cancel` in the status bar, tiles appear as they arrive
- Planning mode (`Edit → Planning mode`, `Ctrl+P`, button at the right of the toolbar): edit with all tools, then apply the plan as one undo step or discard it. Changed nodes get a blue halo; saving and autosave wait until the plan is applied or discarded
- The Generate tool (`G`) replaces the Parking spots tool. It starts planning mode and creates what is picked in the options bar: a route, the parking spots of a shed or the lanes of stations, and shows the name and category of the building under the pointer. Grid snapping moves from `G` to `S`
- Find route (Generate tool, task `Route`): click nodes, connections or free ground as waypoints and get a drivable one-way route through them over the savegame's drivability map, with curve radius, vehicle width and safety margin from `File → Settings → Generators`. Routes are built like hand-drawn courses, straight pieces with arcs through the corners, and their nodes are spaced like AutoDrive records a drive (closer in curves). The route is searched again while waypoints or nodes are dragged, pressing on it inserts a waypoint, and parts crossing obstacles are red. `Enter` adds it to the plan; a waypoint on a connection splits it there. It prefers roads and yards, follows a road around a meadow rather than crossing it, but crosses grass where that is much shorter, and reuses routes already in the plan (but keeps its own nodes along a lane right at its start or goal); a way back without room for its own lane makes the shared lane dual. The status bar warns when the route joins at a marker node, starts at a node nothing drives to or ends at a node that leads nowhere. Where no drivable way exists, the drivable part is shown with a red dashed gap to the waypoint not reached (also for waypoints too close for the curve radius) and `Enter` adds nothing; a search that fails shows an error instead of leaving the tool stuck
- Junctions (Generate tool, task `Junction`): drag from a road towards a yard, bend the stem by its handle or drop it on a node. Builds a compact crossing box (lanes share a node where they cross, a centre node for left turns) or turn curves, with a stem of two lanes, one two-way lane or one one-way lane (`One way in`, `One way out`, only the curves of that direction) and lanes straight across where a road continues opposite. Curves leave and join the road with a 20° kink like hand-made forks and bend with the curve radius of `File → Settings → Generators` (default 6 m). Turns that do not fit are listed and drawn red dashed; the rest can still be added
- Station lanes (Generate tool, task `Stations`): click a station (buildings standing within 15 m of it come along) or right-drag a box around several; a dialog beside the picked stops creates a one-way subprio lane over each chosen stop with a marker (name and group per stop type). On the map, dragging a lane's marker turns it, dragging its first or last node bends that end in an arc where there is no room for a straight lane, and dropping an end on a node joins the lane there. The marker sits 8 m past the stop (adjustable), so the trailer stands over the trigger
- Parking spots: drive-through bays can have several parking positions in a row (`Positions per bay`, `Position spacing`), each with its own marker. While the dialog is open, the planned spots are drawn on the map, and the map can be moved, zoomed and rotated
- `Generate → Building types…` (replaces `View → Sheds…`): the building types of the savegame in the groups Stations, Sheds, Bunker silos and Other; a type can be moved to another group or hidden, on every map; `Reset` undoes both. Productions, farmhouses and weighing stations are no longer drawn as sheds
- `View → Show → Stations`: an arrow at each stop of the savegame's selling points, productions, silos, animal barns and diesel tanks, along the lane over the trigger. The arrows take their direction from the drivability map, and the stops of a building circle it counterclockwise
- `View → Show → Sheds` also shows the buildings that came with the map
- `View → Show → Drivability map`: the game's drivability map of the savegame (blocked ground, grass, fields, roads)
- `View → Ground map`: a map drawn from the map's ground textures (asphalt, concrete, gravel, grass, …) with field outlines and numbers, instead of the map image. Maps need to be imported again for it
- Terrain heights are interpolated between the heightmap pixels instead of taken from the nearest pixel, so nodes follow slopes smoothly
- The network check also finds invalid connection references (to unknown nodes, to the node itself, or incoming without the matching outgoing entry) and nodes without connections. `Fix` removes the invalid entries and deletes the unconnected nodes, except those with a marker
- Saving runs the network check first; if it finds problems, they are shown and the editor asks whether to save anyway
- The last opened file opens again at startup; can be turned off under `File → Settings`
- Measuring points on a node move with the node (e.g. on undo); if the node is deleted, the point stays as a free point
- `Help → Debug log`: detailed log entries for finding problems, e.g. for each route search

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
