# Version history

## Unreleased

- Create, Connect, Draw (Line, Arc, Bézier) and Marker are one tool each; their variants are buttons in the options bar. The keys stay and pick tool and variant; the tool button shows the current variant. Switching the Draw variant keeps a half drawn path
- Generate: the four tasks (Route, Junction, Parking spots, Stations) are icon buttons in the options bar and entries of the `Generate` menu; the Generate button shows the current task
- Measure is a tool (Distance `D`, Angle `Shift+D`) with `Align view to line` in its options bar; the three measuring buttons left the toolbar. Esc with nothing to clear goes back to the tool used before
- The Tools panel is now a fixed one-column tool strip at the left with all 17 tools. Selection is the start tool; the Navigation tool is gone (left-drag on free ground pans in every tool). Selection and Generate left the top toolbar; `View → Tools` and `Show tool labels` are gone
- Top toolbar: Open and Save (new icons), a Background button with the three backgrounds, then Grid, Snap to grid, Rotation and Refresh game picture tiles. The Grid popup no longer has its own snap checkbox (it showed the wrong key `G`)
- Inspector dock (tabbed with Markers): shows the selected node; the node info left `Debug info`, which keeps only the runtime numbers and moved to `Help → Debug info`
- Options bar above the map: shows the active tool's name and its options. The options of Rotate, Line, Arc, Bézier and Generate moved there from the arrows of their buttons
- `Map → Refresh game picture tiles`: mark tiles of the game picture on the map (click, or right-drag a box) and let the game render just those again, e.g. after changing a yard; the status bar shows the estimated time
- `Map → Capture game picture…`: the companion mod `FS25_AutoDriveEditorLink` renders the whole map from above in the running game; the editor shows it as `View → Background → Game picture`. Resolution 0.25 or 0.5 m/px, progress and `Cancel` in the status bar, tiles appear as they arrive
- Planning mode (`Edit → Planning mode`, `Ctrl+P`, button at the right of the toolbar): edit with all tools, then apply the plan as one undo step or discard it. Changed nodes get a blue halo; saving and autosave wait until the plan is applied or discarded
- The Generate tool (`G`) replaces the Parking spots tool. It starts planning mode and creates what is picked in the options bar: a route, the parking spots of a shed or the lanes of stations, and shows the name and category of the building under the pointer. Grid snapping moves from `G` to `S`
- Find route (Generate tool, task `Route`): click nodes, connections or free ground as waypoints and get a drivable one-way route through them over the savegame's drivability map, with turning radius, vehicle width and safety margin from `File → Settings → Route finder`. The route is searched again while waypoints or nodes are dragged, pressing on it inserts a waypoint, and parts crossing obstacles are red. `Enter` adds it to the plan; a waypoint on a connection splits it there. It keeps to roads and yards and reuses routes already in the plan; a way back without room for its own lane makes the shared lane dual. The status bar warns when the route joins at a marker node, starts at a node nothing drives to or ends at a node that leads nowhere
- Junctions (Generate tool, task `Junction`): drag from a road towards a yard, bend the stem by its handle or drop it on a node. Builds a compact crossing box (lanes share a node where they cross, a centre node for left turns) or turn curves, with a stem of two lanes or one two-way lane and lanes straight across where a road continues opposite. Turns that do not fit are listed
- Station lanes (Generate tool, task `Stations`): click a station or right-drag a box around several; a dialog with a map preview creates a one-way subprio lane over each chosen stop with a marker (name and group per type). Lanes can be turned by dragging their end on the map or by angle. The marker sits 8 m past the stop (adjustable), so the trailer stands over the trigger
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
