# AutoDrive FS25 Editor – Manual

**English** | [Deutsch](MANUAL.de.md) · back to the [README](README.md)

- [First start](#first-start)
- [Opening](#opening)
- [The window](#the-window)
- [Tools](#tools)
- [Display](#display)
- [Game picture](#game-picture)
- [Buildings of the savegame](#buildings-of-the-savegame)
- [Planning and generating](#planning-and-generating)
- [Checking the network](#checking-the-network)
- [Saving](#saving)
- [Settings](#settings)
- [Help and errors](#help-and-errors)

## First start

The editor looks for the FS25 user folder (usually `Documents\My Games\FarmingSimulator2025`) and the game's installation folder and shows both for you to check. You can change either later under `File → Settings`.

Map images are not shipped with the editor. They are imported from your `mods` folder or the base game the first time you open a file of that map (see [Opening](#opening)).

## Opening

**Open screen.** While nothing is open, the Open screen lies on the map. `File → Open…` (`Ctrl+O`) and the Open button of the toolbar show the same screen as a dialog. It lists:

- **Savegames**, newest first, with number, name, map and the time they were saved. A savegame without AutoDrive data is listed too ("no AutoDrive network"); it opens with an empty network, and Save creates its `AutoDrive_config.xml`.
- **Routes (RoutesManager)**: all routes of AutoDrive's RoutesManager, with map, revision and date.
- **Open other file…**: any AutoDrive XML file in either format.

Double-click an entry or press `Open`. Without a game folder or savegames the screen says "No savegames found" and links to the settings. `File → Open recent` lists the last five opened files. At startup the editor opens the last one again, unless an autosave is restored; this can be turned off under `File → Settings`.

**Savegame or route.** Open the **savegame** to edit the network you drive with: AutoDrive copies an imported route into the savegame, so the savegame holds its own full network. A savegame brings everything with it: the map, the savegame's heightmap (with its terraforming), the parking positions of its vehicles, its sheds and stations, the drivability map and the game picture. Open a **route** to edit a route that is not active in any savegame, or one to share. A route opens alone: its network on the map named in the RoutesManager, without vehicles, sheds, stations or drivability map.

**Maps.** A map that is not imported yet is imported when the file opens, without asking, with a progress bar: a savegame names its map mod, for a route the mods are searched for its map name. Only a map that is not found asks: `Choose mod zip…` or `Continue without map`. Without a map the map size fits the network (2, 4, 8 or 16 km). A file that belongs to no imported map, e.g. a route file outside the RoutesManager, opens without a map; choose one under `File → Settings → Maps → Use this map for the open file` (see [Settings](#settings)). If the map's mod was updated since the map was imported, the editor offers to import it again: `Import`, `Not now` (asked again at the next start) or `Not for this version` (asked again after the next update of the mod).

## The window

- **Menus** at the top: `File`, `Edit`, `View`, `Generate`, `Check`, `Help`.
- **Toolbar** below them: Open, Save · Undo, Redo · Copy, Cut, Paste · Background (map image, ground map or game picture) · Grid (show, spacing, rotation) · Snap to grid · Rotation of the view (angle, step) · Refresh game picture tiles · Planning mode.
- **Tool strip** at the left: all tools in one column, see [Tools](#tools).
- **Options bar** above the map: the name of the active tool, its variant buttons and its options. Tools without options show only their name.
- **Docks** at the right: `Inspector` (the selected node: type, coordinates, marker, height from the file and from the heightmap; "Nothing selected" otherwise) and `Markers` (all marker groups; a click centers a marker, a double-click edits it) share one place as tabs. The `Network check` dock opens with `Check → Check network`. `View` switches the docks on and off; `Help → Debug info` shows runtime numbers.
- **Status bar** at the bottom: what the active tool expects next, and the results of saving and checking. At the right, the map position under the pointer (X and Z in metres).

**Find.** `Edit → Find marker or node…` (`Ctrl+F`) opens the `Markers` dock and puts the cursor in its search field. Typing filters the markers by name; a group whose name matches keeps all its markers. A node number offers that node (`Node 123`) at the top. `Enter` or a click centers and selects the first result, `Esc` clears the field.

**Remembered.** The window keeps its size, position and docks between starts. Each file in `File → Open recent` opens where its view was left (position, zoom, rotation); a file opened for the first time shows the whole network. `View → Show whole map` (`Home`) fits the network into the window and resets the rotation. `View → Zoom to selection` (`F`) fits the selected nodes into the window and keeps the rotation; it zooms in no further than a click on a marker does. While a file loads, the map shows "Loading …" and the pointer waits.

Mouse: the **wheel** zooms (keys: `+` and `-` zoom around the middle of the map), **left drag** on free ground moves the map in every tool, **middle drag** rotates the view. **Right click** or **Esc** cancels the current step of a tool; **Enter** confirms it (for example for curves).

## Tools

The tool strip holds 17 tools in groups. Create, Connect, Draw, Marker, Measure and Generate have **variants**: buttons at the left of the options bar. A variant's key picks the tool and that variant at once; clicking the tool in the strip picks it with the variant used last. The strip button shows the current variant. Selection is the start tool.

| Tool | Key | What it does |
| --- | --- | --- |
| Selection | `A` | Click or right-drag to select; Shift + right-drag for freehand selection; Ctrl adds to the selection |
| Move | `V` | Drag a node or the selection; Shift moves along one grid axis only |
| Generate | `G` | Starts planning mode and generates a route, a junction, the parking spots of a shed or the lanes of stations (see [Planning and generating](#planning-and-generating)) |
| Create (Regular / Subprio) | `E` / `Shift+E` | Create a node on free ground |
| Connect (Regular / Dual / Reverse) | `1` / `2` / `3` | Click nodes one after another to connect them |
| Delete | `L` | Delete a node or the selection |
| Toggle type | `T` | Switch between Regular and Subprio |
| Reverse direction | `U` | Click a connection to reverse it; inside a selection, all connections of the selection are reversed |
| Rotate | `R` | Rotate the selection using the ring; Shift snaps in steps (default 15°, `Snap step` in the options bar) |
| Enter position | `P` | Enter a node's X/Y/Z as numbers |
| Align horizontally / vertically | `H` / `J` | Put the selection on the line through a reference node |
| Height like reference / Height from heightmap | `Y` / `Shift+Y` | Set the heights of the selection |
| Draw (Line / Arc / Bézier) | `I` / `K` / `B` | Line: straight section with even node spacing. Arc and Bézier: click start and end, drag the handles, press Enter; the Bézier curve has one or two control points. Spacing, connection type, node type and control points are in the options bar. Switching the variant while drawing keeps start and end |
| Marker (Add / Edit / Move / Delete) | `M` / `Shift+M` / `Ctrl+M` / `Ctrl+Shift+M` | Add or edit a marker (name and group), move it to another node or delete it |
| Measure (Distance / Angle) | `D` / `Shift+D` | Click point A and point B (node or free ground), drag a point to move it. `Align view to line` in the options bar rotates the view along the line. Esc with nothing to clear goes back to the tool used before |

Also in the `Edit` menu and the toolbar: Undo and Redo (`Ctrl+Z` / `Ctrl+Y`), Copy, Cut and Paste (`Ctrl+C/X/V`; `Ctrl+Shift+V` pastes at the original position; pasted nodes get the terrain height at the new place, unless `Keep heights when pasting` is on, e.g. for a bridge or ramp), Delete selection (`Del`) and Snap to grid (`S`). All keys can be changed under `File → Settings → Shortcuts`.

## Display

`View → Show` switches nodes, node IDs, each connection type (Regular, Dual, Reverse), markers, marker names, the parking positions of vehicles, sheds, stations, the drivability map (see [Find route](#find-route)) and the scale bar in the bottom-left corner on and off. The line color shows the connection type; arrows show the direction, dual connections get one pointing to each end. Subprio nodes are drawn orange. In every tool, the nodes connected to the node under the pointer are drawn purple. Node IDs appear only when zoomed in; parking positions (a "P" next to the marker) are read from the savegame's `vehicles.xml`, so they show only with a savegame open, see [Buildings of the savegame](#buildings-of-the-savegame), which also explains sheds and stations. Hidden nodes and connections cannot be clicked or selected unless `Hidden items can be selected` is on. Sizes and colors are set under `View → Display options…`. All switches are remembered.

**Background.** `View → Background` (also the Background button of the toolbar) chooses what lies under the network: the map image (`Overview`), the `Ground map` or the `Game picture`. The ground map is drawn from the map's ground textures: asphalt, concrete, gravel, grass, mud, forest, rock and sand each in their own color, with the field outlines and field numbers on top. It shows the map as the game paints it, which helps where the map image is out of date. Maps imported with an older version of the editor have no ground map; import them again under `File → Settings → Maps` to get one. Importing a large map takes a little longer for this (about 15 seconds for a 16x map).

## Game picture

The game picture is the map as the game draws it from above, sharper and more current than the map image: roads, yards, buildings and fields as they are in your savegame. The companion mod `FS25_AutoDriveEditorLink` renders it in the running game; the editor stores it per map and savegame and shows it as a background.

**Capture.** Start the game with the mod active, load the savegame and open the same savegame in the editor. Then choose `View → Background → Capture game picture…`. The dialog says at the top whether the game is connected; `Start` works only then. Choose the resolution, 0.25 m/px (sharper) or 0.5 m/px (faster, smaller), each with the number of tiles, the time and the disk space it needs. Capturing at the other resolution replaces the current picture. `Wait per tile` is the time the game gets to load a place before it renders it; raise it if tiles come out with holes.

While capturing, the game is set to 12:00 and sun, and it freezes briefly for each tile. Do not move the camera or open menus in the game. Afterwards, also after `Cancel` or an error, the game gets its weather back and its clock goes on from the old time plus the capture's duration. The editor stays usable: the status bar shows `Game picture 37/289 · 4 min left` with a `Cancel` button, and the tiles appear on the map as they arrive. Cancelled or finished, the tiles captured so far are kept. Opening another file or closing the editor during a capture asks whether to cancel it.

**Show.** `View → Background → Game picture` shows the picture; it is chosen automatically after a capture. Where nothing was captured, the map image shows through. The picture of a savegame is kept when the savegame is deleted.

**Refresh tiles.** After changing something on the map, `Refresh game picture tiles` (toolbar or `View → Background`) captures just the affected tiles again. It needs a captured picture and the game connected as for a capture. The tool shows the tile grid: click a tile or right-drag a box to mark tiles, `Ctrl` + right-drag unmarks, left-drag pans. The status bar shows the number of marked tiles and the time needed; `Enter` starts the capture, `Esc` clears the marks and then ends the tool. The new tiles replace the old ones as they arrive.

## Buildings of the savegame

With a savegame open, the editor reads its buildings: the sheds to park in and the stations where vehicles load and unload. The Generate tool builds on them. A route opened alone has none.

**Sheds.** `View → Show → Sheds` draws the indoor areas of the savegame's buildings as purple outlines: those placed in game and those that came with the map, unless they were torn down. The building files are read from the game install folder and the mods folder; buildings whose files are missing are left out and counted in the status bar. What was read is kept in `%APPDATA%\AutoDrive Editor\cache` and read again only when the files change, so a savegame opens faster the second time. Only buildings of the Sheds group are drawn as sheds (see Building types below).

**Bunker silos.** `View → Show → Bunker silos` draws the floor of each bunker silo between its walls as a teal outline, for the building types of the Bunker silos group.

**Stations.** `View → Show → Stations` draws a yellow arrow at each stop of the savegame's stations: the spots where vehicles unload or load at selling points, productions, silos, animal barns and diesel tanks. The arrow lies along the lane over the trigger. Most buildings define the spot the game's AI helper drives to; there the arrow sits on it. Where a building has none (many diesel tanks and animal barns), the arrow sits on the trigger. With the savegame's drivability map, the arrow takes the direction with the most free room through the stop (where the building defines the AI spot: along it or across it), and all stops of a building circle it counterclockwise, so one route can pass them all; a lane pointing at the building heads to the side with more room. It can still be wrong; the lane can be turned when it is created. Triggers of the same kind at nearly the same spot, one per fill type, are shown as one stop.

**Building types.** `Generate → Building types…` lists the building types of the savegame that have indoor areas, stations or a bunker silo, in four groups: Stations (unload or load triggers), Sheds (only indoor areas), Bunker silos and Other. A production with a hall is a station, not a shed; farmhouses and weighing stations are in Other, as only the player's character goes inside or vehicles only drive over them. If a type is in the wrong group, choose another one in its `Group` column; unticked types or groups are hidden. `Reset` puts every listed type back in its own group and shows it. Both apply on every map.

## Planning and generating

The planning button at the right end of the toolbar (`Edit → Planning mode`, `Ctrl+P`) starts a plan. All tools work as usual, but the edits are collected in the plan: a blue bar above the map shows how many nodes the plan changed, and those nodes get a blue halo. Undo and Redo work inside the plan and stop at its start. `Apply plan` adds the whole plan to the history as one undo step; `Discard plan` reverts all of it. Clicking the planning button again, opening another file or closing the editor asks whether to apply or discard the plan. While a plan is open, saving is not possible; starting a plan backs up the edits made before it, and autosave then pauses until the plan is applied or discarded.

The Generate tool (`G`) starts planning mode and creates what is picked with the task buttons in the options bar: a route, a junction, the parking spots of a shed, the lanes of stations or of bunker silos. The `Generate` menu has the same five tasks.

### Find route

Choose the task `Route` of the Generate tool, then click nodes, connections or free ground one after another as waypoints. The editor searches a drivable one-way route through them in that order and shows it; parts that cross buildings, fences, trees or water are red. The route drives only forward and is built like a hand-drawn course: straight pieces with arcs of the curve radius through the corners. Its nodes are spaced the way AutoDrive records a drive, on straights up to the spacing set under `File → Settings → Generators` (default 12 m), closer the tighter it turns. It keeps half the vehicle width plus a safety margin away from obstacles; curve radius, vehicle width and margin are set there too. It prefers roads and yards and follows a road around a meadow or orchard rather than crossing it, but crosses grass where that is much shorter; it avoids fields and leaves the first and enters the last node in the direction of their connections. At the waypoints in between it takes the direction that suits the next part. Near the waypoints, blocked ground may be crossed, since nodes can sit under a roof or in a hall. Drag free waypoints or any node to change the route; it is searched again after each change. Pressing on the route inserts a waypoint there, which can be dragged right away.

The waypoint under the pointer is highlighted; `Delete` or a right-click removes it. `Remove last (Backspace)` and `Clear (Esc)` in the options bar remove the last or all waypoints. `Ctrl+Z` first takes back waypoint changes (add, move, remove) of the route being built, then the plan's edits. Where the route is red, move nodes or add a waypoint on the way round. `Enter` adds a route without red parts to the plan as one undo step; free waypoints become nodes, and a waypoint on a connection splits it with a new node (same type and direction). Then the tool starts empty, and the next click picks a new start. If the route found joins at a poor node, the status bar says why, e.g. a marker node (other routes would lead through the marker), a first node that nothing drives to or a last node that leads nowhere; the route can still be added.

Where no drivable way exists, the editor shows the part that can be driven and a red dashed line to the waypoint it could not reach; the status bar names that waypoint, and `Enter` adds nothing until waypoints there are moved or added. Two waypoints too close for the curve radius are marked the same way before any search. If a search fails with an error, the status bar says so; the details are in the log file.

Routes already in the plan are reused: a route in the same direction joins them. The way back (select the nodes the other way round) gets its own lane where there is room; where there is not, it shares the lane, which becomes dual there. If there is no room to turn at all, the editor reports that no drivable route was found.

**Several starts and ends.** `Shift`+click a node to add another start, `Ctrl`+click a node to add another end; with several starts or ends, all starts and ends are existing nodes. The editor then searches a route from every start to every end and builds them as a tree: each route reuses the routes before it where it runs along them, so routes from the same start run together and branch off later, and routes to the same end join. A click adds a waypoint all routes share; they pass it in the same direction, run as one up to it and split there. Pressing on a route inserts a waypoint into that route only, or into all routes that run together there, also when pressed up to 5 m past where they split. A new start or end gets the waypoints all routes share. `Delete` or a right-click on a start or end removes it with its routes; `Remove last (Backspace)` removes the waypoint added last. When a route changes, only that one is searched again, and routes running close beside it, so they can join it. While a search runs, all routes are drawn faded. `Enter` needs all routes clear (the status bar names those that are not) and adds them as one undo step.

The route finder uses the game's drivability map, which Farming Simulator writes into the savegame (`vehicleNavigationCostmap.dat`) on every save, so it needs a savegame open. Save the game again after placing buildings, so the map knows them. `View → Show → Drivability map` draws it: blocked ground red (blue in forests), rough ground orange, grass yellow, fields green; roads and yards are clear.

### Junctions

Choose the task `Junction` of the Generate tool to connect a yard road to a road. Press on the road and drag towards the yard: the junction moves along the road with the mouse, and the stem leaves the road at a right angle as far as the mouse reaches. After releasing, a handle sits at the stem's tip; drag it to bend the stem, or drop it on a node to join the stem there. `Enter` or a click away from the handle adds the junction to the plan, `Esc` cancels. Undo while drawing first straightens a bent stem, then goes back to placing the junction, then cancels.

The options in the options bar set how the junction is built, and are kept for next time:

- **Style**: *Box* (default) builds a compact crossing box where a road of two one-way lanes meets a stem of two lanes: the lanes share a node where they cross, a centre node takes the left turns and U-turns, and short curves take the right turns. The pieces from the crossings out to the box edge are two-way, so AutoDrive drivers see each other inside the box. *Curves* builds a one-way turn curve for each direction instead. If road or stem do not have two one-way lanes, curves are built and the status bar says so.
- **Stem**: *Auto* (default) uses two lanes at a road of two one-way lanes and one two-way lane at a two-way road, or at a two-way road at the stem's tip. *Two-way* or *Two lanes* choose it directly. *One way in* and *One way out* build a one-way stem with only the curves into or out of the yard, e.g. for a yard with a separate exit; a box needs both ways, so these build curves. **Lane gap** is the distance between the two lanes (default 5.5 m).

Curves leave and join the road with a slight kink (20°) and then bend in an arc of the curve radius (`File → Settings → Generators`), like the forks of hand-made courses. Where a road continues on the other side, lanes straight across are added too. Curves or lanes that do not fit on the drivability map are searched with the route finder; those still blocked are left out, drawn as red dashed lines and listed in the status bar (e.g. "No left turn in from the north"), as are pieces of a box on blocked ground. The rest of the junction can still be added.

### Parking spots in sheds

The editor creates AutoDrive parking spots in the sheds of a savegame. Choose the task `Parking spots` of the Generate tool; pointing at a shed shows the building's name and category. Left-click a shed outline, or pick several sheds of one type: `Shift`+click them and press `Enter` (or click one of them), or right-drag a box around them; `Esc` drops the pick. The dialog shows a top view of the shed, turned so the open side is at the bottom, with an arrow to north, and updates while you type. The planned spots are also drawn on the map; while the dialog is open the map can be moved, zoomed and rotated, but not edited.

- **Mode**: *Back in* (vehicles reverse into the bay, the marker is at the back wall) or *Drive through* (one forward line per bay through the shed, the exit is on the opposite side).
- **Open side** / **Entry side**: the side the vehicles come in. Click a side or its compass label in the top view to change it.
- **Number of bays**: the bay width is calculated from it and shown below. Bays narrower than 3 m are shown in red and cannot be created.
- **Left wall**, **Right wall**, **Back wall** (or **Exit offset**), **All gaps**: distances in metres. Click a wall or a gap in the top view to edit just that one; a small box opens at the click spot (Enter applies, Esc cancels). Single gaps are kept when the number of bays changes.
- **Positions per bay**, **Position spacing** (drive through only): several parking positions in a row in each bay, the first at the exit offset and the others toward the entry, each with its own marker.
- **Entry line**, **Exit line**: the driving direction of the two lines outside the open side, seen from outside.
- **Marker name**, **Start number**, **Group**: "Shed" from 3 gives "Shed 3", "Shed 4", … With several positions per bay the numbers count on through the positions of each bay, starting at the exit. A new group name creates the group.

When backing in, the side view below shows the line of one bay, which all bays use. Click a segment to change its length, "+" splits a segment in half, `Delete` removes the selected node. The points where the entry and exit lines branch off can be dragged to another node. In drive-through mode the side view only shows the line.

`Create` adds all nodes as subprio nodes at the shed's height, as one undo step. Running it twice creates the spots twice. Afterwards the four open ends of the entry and exit lines still need to be connected to the road network. `Reset shed settings` brings back the default layout.

**Several sheds.** The same settings apply to all picked sheds; `Shed:` chooses which one the top and side views show, and the map shows the spots of all. Neighbouring sheds facing the same way (within 10°, open sides in line within 3 m, at most 5 m apart) form a row and share one entry and one exit line. The marker numbers run on from shed to shed, row by row and from left to right seen from the open side: two sheds with four bays give "Shed 1" … "Shed 8". Sheds of different types cannot be picked together, as templates are kept per shed type.

**Templates.** `Save as template…` stores the mode, side, number of bays, distances, parking positions and bay line under a name for this shed type, so it works for the same building on any map. Line directions, marker name, start number and group are not stored. `Load template…` lists the templates of the shed type, where they can also be deleted. The dialog opens with the template saved or loaded last for the shed type.

### Bunker silos

Choose the task `Bunker silos` of the Generate tool; pointing at a silo shows its building's name. Left-click a silo outline to create the lanes of that silo. To create several at once, `Shift`+click silos one after another (the picked ones are filled darker; `Shift`+click again removes one), then press `Enter` or click one of them; `Esc` drops the pick. Right-dragging a box (`Shift`: a lasso) picks all silos inside it and opens the dialog right away.

The dialog is the one of [Parking spots in sheds](#parking-spots-in-sheds) with the lanes of a silo as bays, and the same settings apply to all picked silos. It starts from the silo's own layout:

- **Mode** and **Open side** come from the drivability map: a silo closed at one end is *Back in* from the other end, a silo open at both ends is *Drive through*. Without a drivability map it is Back in from the front. Both can be changed.
- **Number of lanes**: one lane per about 5.5 m of inner width, in the centres of equal strips.
- **Back in**: the marker is 3 m before the back wall; vehicles turn in facing away, drive to the turn about 31 m outside, back down to the marker and leave forwards. The entry line is about 5.5 m and the exit line about 22 m outside the silo. **Drive through**: lanes from about 20 m before the silo to a marker **past the silo** (default 15 m), without an exit line.
- **Marker name** and **Group** are patterns with `{building}` (the building's name), `{letter}` (the silo's letter: A, B, … along the open side) and `{n}` (the lane's number from `Start number`, from one wall to the other). Defaults: `KS-{letter}-{n}` in `{building}-KS-{letter}` for back in, `DS-{letter}-{n}` in `{building}-DS-{letter}` for drive through. The text below the settings lists the markers of each group and marks new groups. Names repeated within a group, or already in the network in that group, cannot be created.
- **Silo** (with several silos): which silo the top view and side view show. The map shows the lanes of all of them.

Neighbouring silos facing the same way (within 10°, open sides in line within 3 m, at most 5 m apart) form a row and share one entry and one exit line. `Create` adds all lanes as subprio nodes at the silo's height into the plan, as one undo step; the ends of the entry and exit lines still need to be connected to the network. Templates are kept per silo type, as for sheds. The default patterns are set on `File → Settings → Generators`.

### Station lanes

Choose the task `Stations` of the Generate tool. Left-click a stop arrow or the space between the arrows of a building to pick all its stops, together with the stops of buildings standing within 15 m (e.g. two gas stations side by side), or right-drag a box (`Shift`: a lasso) to pick all stops inside it; pointing at a station shows its name, or the names of the buildings a click would pick. The dialog opens beside the picked stops, so they stay visible. It lists the stops with a check box, type, fill types, marker name and group (e.g. "Grain store (Selling point)" in "Selling points"), the lane angle and a note (no AI spot in the building, an existing node where the lane goes). The marker sits a set distance past the stop (default 8 m), since the tractor stops at the marker and the trailer then stands over the trigger.

The lanes are drawn on the map. Drag the marker of a lane to turn it around its stop (`Shift`: 15° steps), or type the angle. Drag the first or last node of a lane to bend that end in an arc from the stop, e.g. where there is no room for a straight lane; turning the lane straightens it again. Drop an end on a node of the network to join the lane there; the end must fit the node's driving direction. `Create` adds a one-way lane of subprio nodes per chosen stop with the marker on the node at the stop, into the plan as one undo step. Lane ends not dropped on a node are still open and need to be connected to the network, e.g. with Find route.

**Yard road.** For a yard with several stops, e.g. a production, `Draw yard road` draws a road past them. Click its corners on the map; a corner on a node joins the road there, right-click removes the last corner. `Enter` finishes a road that runs one way from the first corner to the last. A click on an earlier corner closes a loop instead: the corners up to that one become a two-way road in and out, the rest a one-way ring in the order clicked. Corners are rounded with the curve radius, and the corners can be dragged afterwards. The `Shape` column then says how each stop is attached to the road:

- **Branch**: a one-way subprio lane over the stop that leaves the road some metres before it and rejoins it after, in the road's direction.
- **Chain**: stops close together along the road (less than 15 m) share one branch.
- **Back-in bay**: as in sheds, a line from the marker away from the road and a stub beside the road to drive past it and back in. The default for animal barns.
- **Lane**: the stop keeps its own lane with open ends. The default for stops more than 30 m from the road.

The note says when a shape does not fit, e.g. no room to leave the road before a stop. `Create` adds the road, its branches and bays and the remaining lanes as one undo step. `Remove yard road` goes back to a lane per stop.

`Generator settings…` in the dialog opens the page `File → Settings → Generators`, which holds for station lanes the lane length before the stop and after the marker (default 10 m each), the marker distance, the node spacing, and the marker name and group per stop type. A name is a pattern with the placeholders `{building}` (the building's name), `{type}` (the stop type), `{fill}` (the stop's first fill type), `{action}` (`unload` or `load`) and `{n}` (a number counted per group, `{n:03}` with three digits, starting at `Numbers start at`), e.g. `VK-{n:02}`. The group is a pattern too, without `{n}`. Productions are named as course authors do, e.g. `Diesel-unload` in `prod.Distillery` (`{fill}-{action}` in `prod.{building}`). A name already in the network in the same group is not used twice.

## Checking the network

`Check → Check network` lists overlapping nodes, nodes outside the map and, with a heightmap loaded, nodes whose height differs too much from the terrain, invalid connection references (to a node that does not exist, to the node itself, or an incoming entry without the other node's outgoing entry) and nodes without any connection. The distance for overlapping nodes and the allowed height difference are set at the top of the dock. Click an entry to show it on the map. `Fix selected` or `Fix all` merges overlapping nodes into one (the node with a marker, otherwise the lowest ID), moves nodes back onto the map, sets heights from the heightmap, removes invalid references and deletes nodes without connections (nodes with a marker are kept). Each kind of fix is one undo step.

Entries that are fine as they are, such as nodes on a bridge, can be hidden with `Ignore`. They move to the `Ignored` group and are not fixed by `Fix all`; `Don't ignore` brings them back. An ignored entry also shows up again when one of its nodes is moved. The checkboxes switch off a whole check. Ignored entries and switched-off checks are remembered for each route or savegame.

Saving runs the check first. If it finds problems that are not ignored, the dock shows them and the editor asks whether to save anyway.

## Saving

`File → Save` (`Ctrl+S`) writes to the file you opened. Before the first overwrite, the editor creates a backup copy (`.bak`).

**Changed by the game.** If the network in the file was changed since the editor opened or last saved it, usually because the game saved it, Save warns first: `Save anyway` overwrites the game's changes, `Reload (my changes are lost)` loads the file again, `Cancel` does nothing. A game save that leaves the network as it was does not warn. `File → Reload` (`F5`) loads the open file again from disk at any time and keeps the view; with unsaved changes it asks first.

**Savegame.** Save writes the savegame's `AutoDrive_config.xml` and updates the marker targets of its vehicles in `vehicles.xml`. If vehicles have a deleted marker as their target, Save lists them first and asks `Save` or `Cancel`: saving sets their target to marker 1 and removes a parking target. If the game is running this savegame with the companion mod `FS25_AutoDriveEditorLink`, the editor then reloads the network in the game: the status bar shows `Saved · reloaded in game`, and AutoDrive drives on the new network right away. Network edits made in the game since the file was opened are replaced by the reload. If the game reports an error or does not answer within 30 seconds, a message says that the file is saved but not reloaded, and that the game will overwrite it on its next save. If the game runs without the mod, a warning says the same once per savegame and session: exit the game without saving, or install the mod. With the game closed, the new network is simply there the next time the savegame is loaded.

**Route.** Save on an open route writes only the route file. To use it in a running game, press `Import` in AutoDrive's RoutesManager and save in the game.

**Save as route…** (`Ctrl+Shift+S`) keeps a version of the network as a route in the RoutesManager. It suggests the name of the route last saved or loaded, else the map name; an existing name asks before replacing the route, whose revision then goes up. A savegame stays open afterwards; a route or XML file goes on as the saved route.

**Load route into savegame…** (savegame open) replaces the network with a route of the savegame's map from the RoutesManager (name, revision and date, newest first), as one undo step. If no route holds the current network yet, it first offers to save it as a route. Vehicles keep their targets at markers with the same name and group. Save then writes the route into the savegame and reloads it in the game.

Unsaved changes are backed up automatically every few minutes (interval under `File → Settings`). If the editor closes unexpectedly, it offers to restore them on the next start.

## Settings

`File → Settings…` has four tabs:

- **General**: language (English or German; on first start German on a German Windows, English elsewhere; takes effect after a restart), theme (like Windows, light or dark), the autosave interval, opening the last file at startup, checking for updates at startup, and the game folders.
- **Maps**: the imported maps with mod, size, heightmap and game picture. `Re-import` reads the selected maps from their mods again (select several with `Ctrl` or `Shift`+click; the import runs in the background, `Cancel` stops after the map being imported), `Remove` deletes the imported map and its game picture (the question shows the size), `Import from mod zip…` imports a map from a zip anywhere on disk. `Use this map for the open file` puts the chosen map under the open file; this is remembered for the file.
- **Generators**: curve radius (default 6 m) and node spacing on straights (default 12 m) for Find route, Junction and the station lanes; vehicle width and safety margin (see [Find route](#find-route)); the lane lengths of station lanes and the marker name and group per stop type (see [Station lanes](#station-lanes)); the marker name and group patterns of bunker silo lanes for back in and drive through (see [Bunker silos](#bunker-silos)).
- **Shortcuts**: the keys of all menu entries and tools, one entry per tool variant.

`Help → Check for updates` asks GitHub whether a newer version exists. Checking at every start is off by default, because it connects to github.com. An update is installed by downloading the zip from the release page and replacing the old program folder with it; settings and imported maps are kept.

## Help and errors

`Help → Version history` shows what changed in each version, `Help → About` shows the version and license. If an unexpected error occurs, the editor shows a message and keeps running. The details are written to a log file (`Help → Open log folder`, in `%APPDATA%\AutoDrive Editor\logs`); please attach it when reporting a bug. `Help → Debug log` adds detailed entries to the log, e.g. for each route search (start, goal, headings, why no route was found); turn it on, repeat what went wrong, and attach the log. `Help → Debug info` shows runtime numbers such as the node count and the cached map tiles.
