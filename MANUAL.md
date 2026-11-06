# AutoDrive FS25 Editor – Manual

**English** | [Deutsch](MANUAL.de.md) · back to the [README](README.md)

New here? Start with the [Quick start](#quick-start). The other parts can be read in any order.

1. [Quick start](#quick-start)
2. [Basics](#basics)
3. [Editing the network](#editing-the-network)
4. [Planning and generators](#planning-and-generators)
5. [The map underneath](#the-map-underneath)
6. [Companion mod](#companion-mod)
7. [Checking and saving](#checking-and-saving)
8. [Reference](#reference)

## Quick start

This walks you through a first small edit: open a savegame, draw a road, add a marker and save.

1. **Start the editor.** On the first start it shows the FS25 user folder it found (usually `Documents\My Games\FarmingSimulator2025`) and the game's installation folder. Check both and confirm.
2. **Open a savegame.** The Open screen lists your savegames, newest first. Double-click one. The first time, its map is imported from your `mods` folder or the base game; a progress bar shows how far it is.
3. **Find a place.** Turn the mouse wheel to zoom and drag the map with the left mouse button. `Home` shows the whole map.
4. **Draw a road.** Press `1` (Connect). Click on free ground, then click again a bit further on, and again: each click creates a node and connects it from the one before. Click an existing node to join your road to it. Press `Esc` to end the road.
5. **Add a marker.** Press `M` (Marker) and click the last node of your road. Enter a name, e.g. "My yard", and a group, then confirm.
6. **Undo a mistake** with `Ctrl+Z`. Every change can be undone.
7. **Save** with `Ctrl+S`. If the game is running this savegame with the [Companion mod](#companion-mod), AutoDrive drives on the new road right away. Otherwise it is there the next time you load the savegame.

> **Tip:** Building junctions, station lanes or whole routes by hand takes long. The [generators](#planning-and-generators) do most of it for you.

## Basics

### Words used in this manual

- **Node**: a point of the AutoDrive network. Vehicles drive from node to node.
- **Connection**: the line between two nodes. Its color shows its type:
  - **Regular**: one way, in the direction of the arrow.
  - **Dual**: both ways.
  - **Reverse**: one way, driven backwards.
- **Regular and subprio nodes**: AutoDrive prefers regular nodes. Subprio nodes (drawn orange) are used only where a route must, e.g. lanes into parking spots or stations, so other routes don't lead through them.
- **Marker**: a named node that vehicles can drive to, e.g. a field, a shed or a selling point. Markers are sorted into **groups**, which AutoDrive shows as folders.
- **Savegame**: a game you play. It holds its own copy of the network, together with the map, vehicles and buildings.
- **Route**: a network saved in AutoDrive's **RoutesManager**, to keep versions or share them. A route can be imported into a savegame.
- **Plan**: a group of changes you can still throw away, see [Planning mode](#planning-mode).

### The window

- **Menus** at the top: `File`, `Edit`, `View`, `Generate`, `Check`, `Help`.
- **Toolbar** below them: Open, Save · Undo, Redo · Copy, Cut, Paste · Background · Grid (show, spacing, rotation) · Snap to grid · Rotation of the view (angle, step) · Refresh game picture tiles · Planning mode.
- **Tool strip** at the left: all tools in one column, see [All tools and keys](#all-tools-and-keys).
- **Options bar** above the map: the name of the active tool, its variant buttons and its options.
- **Docks** at the right: `Inspector` (the selected node: type, coordinates, marker, height from the file and from the heightmap) and `Markers` (all markers by group) share one place as tabs. The `Network check` dock opens with `Check → Check network`. `View` switches the docks on and off.
- **Status bar** at the bottom: what the active tool expects next, results of saving and checking, and at the right the map position under the pointer (X and Z in metres).

### Moving around the map

| Action | How |
| --- | --- |
| Zoom | Mouse wheel; `+` and `-` zoom around the middle |
| Move the map | Left-drag on free ground (in every tool) |
| Rotate the view | Middle-drag |
| Show the whole map | `Home` (`View → Show whole map`), also resets the rotation |
| Zoom to the selection | `F` (`View → Zoom to selection`), keeps the rotation |
| Cancel a tool's current step | Right-click or `Esc` |
| Confirm a tool's step | `Enter`, e.g. for curves |

The window keeps its size, position and docks. Each recent file opens where you left its view; a file opened for the first time shows the whole network.

### Finding a marker or node

Press `Ctrl+F` (`Edit → Find marker or node…`). The `Markers` dock opens with the cursor in its search field.

- Type part of a name: the markers are filtered. A group whose name matches keeps all its markers.
- Type a node number: that node is offered at the top (`Node 123`).
- `Enter` or a click centers and selects the first result; `Esc` clears the field.

In the `Markers` dock, a click on a marker centers it and a double-click edits it.

### Opening files

`File → Open…` (`Ctrl+O`) shows the Open screen, which also lies on the map while nothing is open. It lists:

- **Savegames**, newest first, with number, name, map and save time. A savegame without AutoDrive data is listed too ("no AutoDrive network"); it opens with an empty network, and Save creates its `AutoDrive_config.xml`.
- **Routes (RoutesManager)**, with map, revision and date.
- **Open other file…**: any AutoDrive XML file in either format.

`File → Open recent` lists the last five files. At startup the editor opens the last one again (can be turned off under `File → Settings`), unless it restores an autosave.

**Savegame or route?**

- Open the **savegame** to edit the network you drive with. It brings everything with it: the map, the heightmap with its terraforming, the parking positions of its vehicles, its sheds and stations, the drivability map and the game picture.
- Open a **route** to edit a network that isn't active in any savegame, or one to share. A route opens alone: its network on its map, without vehicles, buildings or drivability map.

**Maps.** A map is imported automatically the first time a file of it opens. A savegame names its map mod; for a route, the mods are searched for its map name.

- If the map is not found, choose `Choose mod zip…` or `Continue without map`. Without a map, the map size fits the network (2, 4, 8 or 16 km).
- A file that belongs to no map (e.g. a route file outside the RoutesManager) opens without one. Choose a map under `File → Settings → Maps → Use this map for the open file`.
- If the map's mod was updated, the editor offers to import it again: `Import`, `Not now` (asked again at the next start) or `Not for this version` (asked again after the next update).

## Editing the network

Each tool has a key; all keys are listed in [All tools and keys](#all-tools-and-keys). Some tools have **variants**, shown as buttons at the left of the options bar. A variant's key picks the tool and that variant at once.

> **Tip:** While any tool is active, the nodes connected to the node under the pointer are drawn purple.

### Selecting

Press `A` (Selection).

- Click a node, or right-drag a box. `Shift` + right-drag draws a freehand lasso. `Ctrl` adds to the selection.
- Double-click a node or connection to select its whole **road piece**: up to the next junctions or road ends, or to where the connection or node type changes.
- `Ctrl+A` selects everything; `Edit → Select road piece` grows the selection to whole road pieces.

Hidden nodes and connections can't be selected unless `Hidden items can be selected` is on (see [Display options](#display-options)).

### Creating and connecting nodes

- **Create** (`E` regular, `Shift+E` subprio): click free ground to create a node. Click a connection to insert a node into it; it lies on the line, between the heights of the ends, and keeps the connection's type and direction.
- **Connect** (`1` regular, `2` dual, `3` reverse): click nodes one after another to connect them. A click on free ground creates a node, a click on a connection inserts one, and either is connected from the previous node. So you can draw a whole road with this one tool. The node type is in the options bar. `Esc` or right-click ends the chain.
- **Toggle type** (`T`): click a node to switch between regular and subprio.
- **Reverse direction** (`U`): click a connection to turn it around. Inside a selection, all its connections are turned.

### Drawing lines and curves

Press `I` (Line), `K` (Arc) or `B` (Bézier).

1. Click the start and the end.
2. For Arc and Bézier, drag the handles to shape the curve. A Bézier curve has one or two control points.
3. Press `Enter`.

The nodes are spaced evenly. Spacing, connection type, node type and number of control points are in the options bar. Switching the variant while drawing keeps start and end.

### Parallel lanes

`Shift+I` (Draw → Parallel) adds a lane beside each selected road, e.g. the second lane of a pair of one-way roads.

1. Select the roads, before or in the tool: right-drag a box, `Shift` + right-drag a lasso, `Ctrl`+click toggles a node, right-click clears.
2. Point beside a road. The dashed preview follows the pointer, which sets the side and the distance (steps of 0.5 m, shown in `Lane distance`).
3. Click to create the lanes there, or press `Enter` (`Apply`) to use the distance in the box.

- Every road gets its lane on the same side of its own driving direction, so several one-way roads are done at once.
- The lane is connected like its road (regular, dual or reverse). `Direction` sets the same or the opposite way. `Spacing` and `Node type` set the nodes; they get the terrain height, or the height of the road beside them.
- The ends stay open and the new nodes aren't selected. One undo removes all lanes.
- Refused, with a message: a junction in the selection, a closed ring, a road whose connections differ in type or direction, or a curve tighter than the distance on the inner side.

### Moving, rotating and aligning

- **Move** (`V`): drag a node or the selection. `Shift` moves along one grid axis only. `S` switches snap to grid.
- **Rotate** (`R`): rotate the selection with the ring. `Shift` snaps in steps (`Snap step`, default 15°).
- **Enter position** (`P`): type a node's X/Y/Z.
- **Align horizontally / vertically** (`H` / `J`): put the selection on the line through a reference node.

### Heights

- **Height like reference** (`Y`): give the selection the height of a reference node.
- **Height from heightmap** (`Shift+Y`): set the selection onto the terrain.

### Deleting

- **Delete node** (`L`, or `Del` for the selection): deletes nodes and their connections.
- **Delete and reconnect** (`Shift+L`, or `Shift+Del` for the selection): deletes nodes in the middle of a road and joins its two ends the same way: A→N→B becomes A→B, dual stays dual. Refused for junctions, road ends and connections of different types.

### Markers

Press `M` and click a node to add a marker, with a name and a group. A new group name creates the group. The other variants:

- **Edit** (`Shift+M`): change name and group.
- **Move** (`Ctrl+M`): move the marker to another node.
- **Delete** (`Ctrl+Shift+M`).

### Measuring

Press `D` (Distance) or `Shift+D` (Angle), then click point A and point B (a node or free ground). Drag a point to move it. `Align view to line` rotates the view along the line. `Esc` with nothing to clear returns to the tool used before.

### Copy and paste

`Ctrl+C`, `Ctrl+X`, `Ctrl+V` copy, cut and paste the selection. `Ctrl+Shift+V` pastes at the original position. Pasted nodes get the terrain height at their new place, unless `Keep heights when pasting` is on, e.g. for a bridge or ramp.

### Undo

`Ctrl+Z` undoes and `Ctrl+Y` redoes every change. To try something larger first, use [Planning mode](#planning-mode).

## Planning and generators

### Planning mode

A plan collects changes so you can look at them before keeping them.

1. Click the planning button at the right end of the toolbar (`Ctrl+P`, `Edit → Planning mode`). A blue bar appears above the map.
2. Edit with any tool. The bar counts the changed nodes, which get a blue halo. Undo and Redo work inside the plan.
3. Click `Apply plan` to keep everything as one undo step, or `Discard plan` to throw it away.

Clicking the planning button again, opening another file or closing the editor asks whether to apply or discard. While a plan is open you can't save; the edits made before the plan are backed up, and autosave pauses until the plan ends.

### The Generate tool

Press `G` and choose a task in the options bar (or in the `Generate` menu). The tool starts planning mode by itself.

| Task | Builds | Needs |
| --- | --- | --- |
| [Route](#route) | a drivable route through waypoints you click | a savegame |
| [Junction](#junction) | a crossing box or turn curves from a road into a yard | |
| [Stations](#stations) | lanes with markers over the stops of selling points, productions, silos, barns | a savegame |
| [Roads](#roads) | AutoDrive roads along the map's traffic lanes | a savegame |
| [Parking spots](#parking-spots) | parking spots with markers in sheds | a savegame |
| [Bunker silos](#bunker-silos) | lanes with markers in bunker silos | a savegame |

Curve radius, node spacing, vehicle width and the marker patterns are set under `File → Settings → Generators`.

> **Tip:** Generated lanes usually end open. Connect them to the network afterwards, e.g. with the Route task.

### Route

Finds a drivable one-way route through waypoints, around buildings, fences, trees and water.

1. Choose the task **Route**.
2. Click nodes, connections or free ground one after another as waypoints. The route is searched and shown; parts that cross obstacles are red.
3. Change it: drag a waypoint or any node, or press on the route to insert a waypoint there and drag it. The route is searched again after each change.
4. Press `Enter` to add it to the plan. Free waypoints become nodes; a waypoint on a connection splits it with a new node.

Afterwards the tool starts empty, and the next click picks a new start.

**Editing waypoints.** The waypoint under the pointer is highlighted. `Delete` or right-click removes it, `Backspace` removes the last one, `Esc` all of them. `Ctrl+Z` first takes back waypoint changes, then the plan's edits.

**How the route is built.** It drives only forward, like a hand-drawn course: straight pieces joined by arcs of the curve radius. Nodes are spaced as AutoDrive records a drive, up to the node spacing on straights (default 12 m) and closer in tight turns. It keeps half the vehicle width plus a safety margin from obstacles. It prefers roads and yards, goes around a meadow or orchard rather than across it, but crosses grass where that is much shorter, and avoids fields. It leaves the first and enters the last node in the direction of their connections. Near the waypoints it may cross blocked ground, since nodes can sit under a roof or in a hall.

**Joining other routes.** Routes already in the plan are reused: a route in the same direction joins them. The way back gets its own lane where there is room and shares the lane (as dual) where there is not.

**Several starts and ends.** `Shift`+click a node to add another start, `Ctrl`+click to add another end. The editor then finds a route from every start to every end and builds them as a tree: routes from the same start run together and branch off later, and routes to the same end join.

- A click adds a waypoint all routes share; they run as one up to it.
- Pressing on a route inserts a waypoint into that route only, or into all routes that run together there (also up to 5 m past where they split).
- `Delete` or right-click on a start or end removes it with its routes.
- While a search runs, all routes are drawn faded. `Enter` needs all routes clear; the status bar names those that are not.

**If no route is found.** The editor shows the part that can be driven and a red dashed line to the waypoint it could not reach; the status bar names it. Move or add waypoints there. Two waypoints too close for the curve radius are marked the same way. If the route joins at a poor node (a marker node, a first node nothing drives to, a last node that leads nowhere), the status bar says so, but you can still add it.

**The drivability map.** The route finder uses the map that Farming Simulator writes into the savegame on every save (`vehicleNavigationCostmap.dat`). After placing buildings, save the game again so the map knows them. `View → Show → Drivability map` shows it: blocked ground red (blue in forests), rough ground orange, grass yellow, fields green; roads and yards are clear.

### Junction

Connects a yard road to a road, with a crossing box or turn curves.

1. Choose the task **Junction**.
2. Press on the road and drag towards the yard. The junction slides along the road, and the stem grows out at a right angle.
3. Release. Drag the handle at the stem's tip to bend the stem, or drop it on a node to join there.
4. Press `Enter` (or click away from the handle) to add the junction to the plan. `Esc` cancels.

`Ctrl+Z` while drawing first straightens a bent stem, then goes back to placing, then cancels.

| Option | Choices |
| --- | --- |
| Style | **Box** (default): a compact crossing box where a road of two one-way lanes meets a stem of two lanes. The lanes share a node where they cross, a centre node takes left turns and U-turns, short curves take right turns. The pieces inside the box are two-way, so AutoDrive drivers see each other there. **Curves**: one one-way turn curve per direction. |
| Stem | **Auto** (default): two lanes at a road of two one-way lanes, one two-way lane at a two-way road. **Two-way** or **Two lanes** choose directly. **One way in** / **One way out**: only the curves into or out of the yard, e.g. for a yard with a separate exit. |
| Lane gap | Distance between two lanes (default 5.5 m) |

The options are kept for next time. If road or stem don't have two one-way lanes, curves are built instead of a box, and the status bar says so.

Curves leave and join the road with a slight kink (20°), then bend in an arc of the curve radius, like the forks of hand-made courses. Where a road continues on the other side, lanes straight across are added too.

**If something doesn't fit:** curves that don't fit on the drivability map are searched with the route finder. Those still blocked are drawn as red dashed lines and listed in the status bar, e.g. "No left turn in from the north". You can still add the rest.

### Stations

Builds a one-way lane with a marker over each stop of selling points, productions, silos, animal barns and diesel tanks.

1. Choose the task **Stations**. Pointing at a station shows its name.
2. Click a stop arrow, or the space between the arrows of a building, to pick all its stops. Buildings within 15 m are picked too (e.g. two gas stations side by side). Or right-drag a box (`Shift`: lasso) around the stops.
3. A dialog opens beside the stops. It lists each stop with a check box, type, fill types, marker name and group, lane angle and a note (e.g. no AI spot in the building, or an existing node where the lane goes).
4. Adjust the lanes on the map if needed (see below).
5. Click `Create`. The lanes go into the plan as one undo step.

The marker sits a set distance past the stop (default 8 m): the tractor stops at the marker, so the trailer stands over the trigger.

**Adjusting lanes.**

- Drag a lane's marker to turn the lane around its stop (`Shift`: 15° steps), or type the angle.
- Drag the first or last node to bend that end in an arc, e.g. where there is no room for a straight lane. Turning the lane straightens it again.
- Drop an end on a node of the network to join the lane there; it must fit the node's driving direction. Ends not joined stay open.

**Yard road.** For a yard with several stops, e.g. a production, click `Draw yard road` and draw a road past them:

1. Click its corners on the map. A corner on a node joins the road there; right-click removes the last corner.
2. Press `Enter` for a one-way road from the first corner to the last. Or click an earlier corner to close a loop: the corners up to it become a two-way road in and out, the rest a one-way ring.
3. Corners are rounded with the curve radius and can be dragged afterwards.

The `Shape` column then says how each stop is attached to the road:

| Shape | Meaning |
| --- | --- |
| Branch | a one-way lane over the stop that leaves the road before it and rejoins after |
| Chain | stops closer than 15 m along the road share one branch |
| Back-in bay | a line from the marker away from the road, and a stub to drive past and back in. Default for animal barns |
| Lane | the stop keeps its own lane with open ends. Default for stops more than 30 m from the road |

The note says when a shape doesn't fit. `Create` adds road, branches, bays and lanes as one undo step. `Remove yard road` goes back to one lane per stop.

**Names.** `Generator settings…` opens `File → Settings → Generators`. There you set the lane length before the stop and after the marker (default 10 m each), the marker distance, the node spacing, and the marker name and group per stop type. Names are patterns:

| Placeholder | Becomes |
| --- | --- |
| `{building}` | the building's name |
| `{type}` | the stop type |
| `{fill}` | the stop's first fill type |
| `{action}` | `unload` or `load` |
| `{n}` | a number counted per group, from `Numbers start at`; `{n:03}` with three digits |

For example `VK-{n:02}`, or for productions `{fill}-{action}` in `prod.{building}`, which gives `Diesel-unload` in `prod.Distillery`. Groups are patterns too, without `{n}`. A name already in the same group isn't used twice.

### Roads

Builds AutoDrive roads along the map's own traffic lanes, the lanes the game's traffic drives on.

1. Choose the task **Roads**. The first time, the traffic lanes are read from the map (with a progress window and `Cancel`); they are drawn as thin lines.
2. Choose the **Mode**:
   - **Whole map**: press `Create` or `Enter`.
   - **Box**: right-drag a box. The roads in it are built, cut off at the box edge, with the junctions whose middle lies inside.
   - **Click road**: click a road to build it from junction to junction (the junctions themselves are not built).
3. Check the result in the `Road network` group of the Network check dock (see below).

| Option | Choices |
| --- | --- |
| Existing | **Skip and connect** (default): existing roads stay; new roads are built only where none run and join the existing lanes. Junctions with existing nodes are kept. **Replace**: existing regular nodes along the new roads are removed, including inside junction boxes; side branches join the new lanes and markers move to the nearest new node. Subprio lanes are never removed. |
| Lanes | **Two one-way** (at the Junction task's lane gap), **Two-way**, or **Auto** (default): what most of the network uses, two one-way lanes in an empty network |

Where three or four two-way roads meet, a junction box is built as by the Junction task (in the two-way style, the roads meet at one shared node). Other junctions, such as roundabouts, slip roads and forks, use the map's own lanes. The result goes into the plan as one undo step.

**Checking the result.** The editor checks that every turn the traffic allows through a junction can be driven, that the new lanes lead on and are reached, and that they avoid blocked ground. Places to look at are listed, e.g. "No junction box", "Existing junction kept", "2 of 6 turns missing", "Dead end" or "Road end not joined to the network"; a click shows the place. Places at the edge of a box or clicked road are not listed, as the roads end there on purpose.

Maps without traffic lanes can't use this task. On maps whose traffic lanes are only a few loops without junctions, the status bar asks you to check the roads where they cross.

### Parking spots

Creates AutoDrive parking spots in the sheds of a savegame.

1. Choose the task **Parking spots**. Pointing at a shed shows its name and category.
2. Click a shed outline. For several sheds of one type, `Shift`+click them and press `Enter`, or right-drag a box around them. `Esc` drops the pick.
3. Set up the spots in the dialog. Its top view shows the shed with the open side at the bottom and an arrow to north; the planned spots are also drawn on the map. You can move and zoom the map meanwhile, but not edit it.
4. Click `Create`. All nodes are added as subprio nodes at the shed's height, as one undo step.
5. Connect the four open ends of the entry and exit lines to the network.

| Setting | Meaning |
| --- | --- |
| Mode | **Back in**: vehicles reverse into the bay; the marker is at the back wall. **Drive through**: one forward line per bay; the exit is on the opposite side. |
| Open side / Entry side | where vehicles come in. Click a side or its compass label in the top view to change it. |
| Number of bays | the bay width is calculated from it. Bays narrower than 3 m are red and can't be created. |
| Left wall, Right wall, Back wall (or Exit offset), All gaps | distances in metres. Click a wall or gap in the top view to edit just that one (`Enter` applies, `Esc` cancels). Single gaps are kept when the number of bays changes. |
| Positions per bay, Position spacing | drive through only: several parking positions in a row, each with its own marker, the first at the exit offset |
| Entry line, Exit line | the driving direction of the two lines outside, seen from outside |
| Marker name, Start number, Group | "Shed" from 3 gives "Shed 3", "Shed 4", … With several positions per bay, the numbers count through each bay from the exit. |

**Side view** (back in): shows the line of one bay, used by all bays. Click a segment to change its length, "+" splits it, `Delete` removes the selected node. The points where entry and exit lines branch off can be dragged to another node. In drive-through mode the side view only shows the line.

**Several sheds.** The settings apply to all picked sheds; `Shed:` chooses which one the views show. Neighbouring sheds facing the same way (within 10°, open sides in line within 3 m, at most 5 m apart) form a row and share one entry and one exit line. Marker numbers run on row by row, left to right seen from the open side: two sheds with four bays give "Shed 1" … "Shed 8". Sheds of different types can't be picked together.

**Templates.** `Save as template…` stores mode, side, bays, distances, positions and bay line under a name for this shed type, so it works for the same building on any map. Line directions, marker name, start number and group are not stored. `Load template…` lists the templates, where they can also be deleted. The dialog opens with the template used last. `Reset shed settings` brings back the default layout.

> **Note:** Running Create twice creates the spots twice.

### Bunker silos

Creates the lanes of bunker silos, with markers.

1. Choose the task **Bunker silos**. Pointing at a silo shows its building's name.
2. Click a silo outline. For several, `Shift`+click them one after another (picked ones turn darker; `Shift`+click again removes one) and press `Enter`, or right-drag a box (`Shift`: lasso), which opens the dialog right away. `Esc` drops the pick.
3. Adjust the settings. The dialog is the one of [Parking spots](#parking-spots), with the silo's lanes as bays.
4. Click `Create`. The lanes are added as subprio nodes at the silo's height, as one undo step.
5. Connect the ends of the entry and exit lines to the network.

The dialog starts from the silo's own layout:

- **Mode and open side** come from the drivability map: a silo closed at one end is *Back in* from the other end, a silo open at both ends is *Drive through*. Without a drivability map: back in from the front.
- **Number of lanes**: one lane per about 5.5 m of inner width.
- **Back in**: the marker is 3 m before the back wall. Vehicles turn about 31 m outside, back down to the marker and leave forwards. The entry line is about 5.5 m and the exit line about 22 m outside.
- **Drive through**: lanes from about 20 m before the silo to a marker past it (default 15 m), without an exit line.
- **Marker name and group** are patterns with `{building}`, `{letter}` (the silo's letter A, B, … along the open side) and `{n}` (the lane's number from one wall to the other). Defaults: `KS-{letter}-{n}` in `{building}-KS-{letter}` for back in, `DS-{letter}-{n}` in `{building}-DS-{letter}` for drive through (changed under `File → Settings → Generators`). The text below the settings lists the markers per group. Names that repeat can't be created.
- **Silo** (with several silos): which silo the views show.

Rows of neighbouring silos share one entry and one exit line, as for sheds. Templates are kept per silo type.

## The map underneath

### Background

`View → Background` (or the Background button of the toolbar) chooses what lies under the network:

- **Overview**: the map image of the map mod.
- **Ground map**: drawn from the map's ground textures. Asphalt, concrete, gravel, grass, mud, forest, rock and sand each get a color, with field outlines and numbers. It shows the map as the game paints it, which helps where the map image is out of date. Maps imported with an older version of the editor have no ground map; import them again under `File → Settings → Maps` (about 15 seconds for a 16x map).
- **Game picture**: see below.

### Game picture

The game picture is the map as the game draws it from above: sharper and more current than the map image, with your yards, roads and buildings as they are in your savegame. It needs the [Companion mod](#companion-mod). The editor stores it per map and savegame.

**Capture**

1. Start the game with the mod active and load the savegame. Open the same savegame in the editor.
2. Choose `View → Background → Capture game picture…`. The dialog says at the top whether the game is connected; `Start` works only then.
3. Choose the resolution: 0.25 m/px (sharper) or 0.5 m/px (faster, smaller). Each shows the number of tiles, the time and the disk space.
4. Click `Start`.

While capturing, don't move the camera or open menus in the game. The game is set to 12:00 and sun and freezes briefly for each tile. Afterwards (also after `Cancel` or an error) it gets its weather back, and its clock goes on from the old time plus the capture's duration.

The editor stays usable meanwhile. The status bar shows the progress (`Game picture 37/289 · 4 min left`) with a `Cancel` button, and the tiles appear on the map as they arrive. Tiles captured so far are kept. Opening another file or closing the editor asks whether to cancel the capture.

> **Tip:** If tiles come out with holes, raise `Wait per tile`, the time the game gets to load a place before rendering it.

Capturing at the other resolution replaces the current picture. Where nothing was captured, the map image shows through. The picture is kept when the savegame is deleted.

**Refresh tiles after a change on the map**

1. Click `Refresh game picture tiles` (toolbar or `View → Background`). The tile grid is shown. The game must be connected as for a capture.
2. Click tiles or right-drag a box to mark them; `Ctrl` + right-drag unmarks. The status bar shows the number of tiles and the time.
3. Press `Enter`. The new tiles replace the old ones as they arrive. `Esc` clears the marks, then ends the tool.

### Buildings of the savegame

With a savegame open, the editor reads its buildings. The generators build on them. A route opened alone has none.

- **Sheds** (`View → Show → Sheds`): the indoor areas of the buildings as purple outlines, both those placed in the game and those of the map, unless torn down.
- **Bunker silos** (`View → Show → Bunker silos`): the floor between the walls as a teal outline.
- **Stations** (`View → Show → Stations`): a yellow arrow at each stop where vehicles unload or load: selling points, productions, silos, animal barns and diesel tanks.

The building files are read from the game and the mods folder; buildings whose files are missing are left out and counted in the status bar. What was read is kept in `%APPDATA%\AutoDrive Editor\cache`, so a savegame opens faster the second time.

**Where the stop arrows point.** Most buildings define the spot the game's AI helper drives to; the arrow sits on it. Where a building has none (many diesel tanks and animal barns), the arrow sits on the trigger. With a drivability map, the arrow takes the direction with the most free room, and all stops of a building circle it counterclockwise, so one route can pass them all. It can still be wrong; you can turn the lane when you create it. Triggers of one kind at nearly the same spot (one per fill type) are shown as one stop.

**Building types.** `Generate → Building types…` lists the savegame's building types in four groups: Stations, Sheds, Bunker silos and Other. A production with a hall is a station, not a shed; farmhouses and weighing stations are in Other. If a type is in the wrong group, choose another in its `Group` column. Unticked types or groups are hidden. `Reset` puts every type back and shows it. Both apply on every map.

### Display options

`View → Show` switches each of these on and off: nodes, node IDs (only when zoomed in), each connection type, markers, marker names, vehicle parking positions (a "P" next to the marker, from the savegame's `vehicles.xml`), sheds, bunker silos, stations, the drivability map and the scale bar. Arrows show the driving direction; dual connections get one at each end.

`View → Display options…` sets sizes and colors, and `Hidden items can be selected`. All switches are remembered.

## Companion mod

The editor works without any mod. The small companion mod **FS25_AutoDriveEditorLink** connects it to the running game and adds two things:

- **Game picture**: the game renders the map from above, and the editor shows it as its background. See [Game picture](#game-picture).
- **Reload on save**: when you save the savegame that is running in the game, AutoDrive drives on the new network right away. Without the mod, the game keeps its old network and overwrites your changes the next time it saves.

### Install

1. Download `FS25_AutoDriveEditorLink.zip` from the [latest release](https://github.com/SvenBrauns/FS25_AutoDriveEditorLink/releases/latest).
2. Put the zip into your `mods` folder (usually `Documents\My Games\FarmingSimulator2025\mods`). Don't unpack or rename it.
3. Start the game, select your savegame and activate the mod in the mod list, then load the savegame.

To update the mod, replace the zip with the new one.

### Check the connection

Load the savegame in the game and open the same savegame in the editor. Choose `View → Background → Capture game picture…`: the top of the dialog says whether the game is connected.

If it says the game is not connected:

- Is the mod active in this savegame?
- Is the same savegame loaded in the game and open in the editor?
- Is the game folder under `File → Settings → General` the one the game uses?

> **Note:** The editor and the mod talk through files in the folder `modSettings\FS25_AutoDriveEditorLink` of your FS25 user folder. Nothing is sent over the internet.

## Checking and saving

### Network check

`Check → Check network` opens the `Network check` dock and lists:

- overlapping nodes,
- nodes outside the map,
- nodes whose height differs too much from the terrain (with a heightmap),
- invalid connections: to a node that doesn't exist, to the node itself, or an incoming entry without the other node's outgoing entry,
- nodes without any connection.

The distance for overlapping nodes and the allowed height difference are set at the top of the dock. Click an entry to show it on the map.

**Fixing.** `Fix selected` or `Fix all` merges overlapping nodes (keeping the node with a marker, otherwise the lowest ID), moves nodes back onto the map, sets heights from the heightmap, removes invalid references and deletes nodes without connections (nodes with a marker are kept). Each kind of fix is one undo step.

**Ignoring.** Entries that are fine as they are, e.g. nodes on a bridge, can be hidden with `Ignore`. They move to the `Ignored` group and aren't fixed by `Fix all`; `Don't ignore` brings them back. An ignored entry shows up again when one of its nodes moves. The checkboxes switch off a whole check. Both are remembered per route or savegame.

Saving runs the check first. If it finds problems that aren't ignored, the dock shows them and the editor asks whether to save anyway.

### Saving

`File → Save` (`Ctrl+S`) writes to the file you opened. Before the first overwrite, a backup copy (`.bak`) is made.

**Saving a savegame** writes its `AutoDrive_config.xml` and updates the marker targets of its vehicles in `vehicles.xml`. If vehicles have a deleted marker as target, the editor lists them and asks first; saving sets their target to marker 1 and removes a parking target. Then:

- **Game running this savegame with the companion mod:** the network is reloaded in the game, and the status bar shows `Saved · reloaded in game`. Network edits made in the game since the file was opened are replaced. If the game reports an error or doesn't answer within 30 seconds, a message says the file is saved but not reloaded.
- **Game running without the mod:** a warning says the game will overwrite the file on its next save. Exit the game without saving, or install the [Companion mod](#companion-mod).
- **Game closed:** the new network is there the next time the savegame is loaded.

**Saving a route** writes only the route file. To use it in a running game, press `Import` in AutoDrive's RoutesManager and save in the game.

**When the game changed the file.** If the network in the file changed since the editor opened or last saved it, usually because the game saved, Save warns first: `Save anyway` overwrites the game's changes, `Reload (my changes are lost)` loads the file again, `Cancel` does nothing. `File → Reload` (`F5`) loads the open file again at any time and keeps the view; with unsaved changes it asks first.

### Routes in the RoutesManager

- **Save as route…** (`Ctrl+Shift+S`) keeps a version of the network as a route. It suggests the name of the route saved or loaded last, else the map name. An existing name asks before replacing; the revision then goes up. A savegame stays open afterwards; a route or XML file goes on as the saved route.
- **Load route into savegame…** (with a savegame open) replaces the network with a route of the same map, as one undo step. If the current network isn't saved as a route yet, it offers to do that first. Vehicles keep their targets at markers with the same name and group. Save then writes the route into the savegame and reloads it in the game.

### Autosave

Unsaved changes are backed up every few minutes (interval under `File → Settings`). If the editor closes unexpectedly, it offers to restore them at the next start.

## Reference

### All tools and keys

All keys can be changed under `File → Settings → Shortcuts`. Clicking a tool in the strip picks it with the variant used last.

| Tool | Key | What it does |
| --- | --- | --- |
| Selection | `A` | Select nodes, see [Selecting](#selecting) |
| Move | `V` | Drag nodes; `Shift` along one grid axis |
| Generate | `G` | Generators, see [The Generate tool](#the-generate-tool) |
| Create (Regular / Subprio) | `E` / `Shift+E` | Create a node, or insert one into a connection |
| Connect (Regular / Dual / Reverse) | `1` / `2` / `3` | Connect nodes one after another; draws a road |
| Delete (Node / Reconnect) | `L` / `Shift+L` | Delete nodes, or delete and join the ends |
| Toggle type | `T` | Regular ↔ subprio |
| Reverse direction | `U` | Turn a connection around |
| Rotate | `R` | Rotate the selection |
| Enter position | `P` | Type a node's coordinates |
| Align horizontally / vertically | `H` / `J` | Put the selection on a line |
| Height like reference / from heightmap | `Y` / `Shift+Y` | Set heights of the selection |
| Draw (Line / Arc / Bézier / Parallel) | `I` / `K` / `B` / `Shift+I` | Lines, curves and parallel lanes |
| Marker (Add / Edit / Move / Delete) | `M` / `Shift+M` / `Ctrl+M` / `Ctrl+Shift+M` | Markers |
| Measure (Distance / Angle) | `D` / `Shift+D` | Measure between two points |

| Command | Key |
| --- | --- |
| Open / Save / Save as route | `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S` |
| Reload file | `F5` |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Y` |
| Copy / Cut / Paste / Paste in place | `Ctrl+C` / `Ctrl+X` / `Ctrl+V` / `Ctrl+Shift+V` |
| Select all | `Ctrl+A` |
| Delete selection / and reconnect | `Del` / `Shift+Del` |
| Snap to grid | `S` |
| Find marker or node | `Ctrl+F` |
| Planning mode | `Ctrl+P` |
| Show whole map / Zoom to selection | `Home` / `F` |
| Manual | `F1` |

### Settings

`File → Settings…` has four tabs:

- **General**: language (English or German, after a restart; on first start German on a German Windows), theme (like Windows, light or dark), autosave interval, opening the last file at startup, checking for updates at startup, and the game folders.
- **Maps**: the imported maps with mod, size, heightmap and game picture.
  - `Re-import` reads the selected maps again (several with `Ctrl` or `Shift`+click; runs in the background, `Cancel` stops after the current map).
  - `Remove` deletes the imported map and its game picture.
  - `Import from mod zip…` imports a map from a zip anywhere on disk.
  - `Use this map for the open file` puts the chosen map under the open file; remembered for the file.
- **Generators**: curve radius (default 6 m) and node spacing on straights (default 12 m) for Route, Junction and Stations; vehicle width and safety margin for Route; lane lengths and marker patterns of [Stations](#stations); marker patterns of [Bunker silos](#bunker-silos).
- **Shortcuts**: the keys of all menu entries and tools, one entry per tool variant.

### Updates

`Help → Check for updates` asks GitHub whether a newer version exists. Checking at every start is off by default, because it connects to github.com. To update, download the zip from the release page and replace the old program folder with it; settings and imported maps are kept.

### Help and errors

- `Help → Manual` (`F1`) opens this manual in the editor's language; `Help → Version history` shows what changed; `Help → About` shows version and license.
- If an unexpected error occurs, the editor shows a message and keeps running. The details are in a log file: `Help → Open log folder` (`%APPDATA%\AutoDrive Editor\logs`). Please attach it when reporting a bug.
- `Help → Debug log` adds detailed entries, e.g. for each route search (start, goal, headings, why no route was found). Turn it on, repeat what went wrong, and attach the log.
- `Help → Debug info` shows runtime numbers such as the node count and cached map tiles.
