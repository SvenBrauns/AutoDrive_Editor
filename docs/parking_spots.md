# Parking spots in sheds – design

Agreed design for creating AutoDrive parking spots in sheds. Temporary: when the feature is done, this file becomes a section of the manual and is deleted.

Steps (each its own branch, in this order): 0 connection display, 1 savegame link, 2 sheds layer, 3 parking spot dialog. Step 3 is split: 3a dialog with all fields, static top view and generator; 3b clickable previews (top view and side view); 3c templates.

## Step 0 – Connection display

- Dual connections get arrows in both directions, placed so they don't overlap.
- The line color always shows the connection type (regular, dual, reverse). Subprio is shown on the nodes only. Today a connection into a subprio node is drawn orange whatever its type (`ConnectionData.kind`), so subprio reverse and dual connections can't be told apart.

## Step 1 – Link a savegame to a route

- Parking positions come from the savegame's `vehicles.xml`. A route from the route manager has no savegame, so it shows none.
- When a route is loaded without a link, the editor asks whether to link a savegame. Savegames on the same map come first: the route's `map` in `routes.xml` (e.g. `LS25_Thüringen_2_0_16x`) is the savegame's `mapTitle` in `careerSavegame.xml` with spaces replaced by underscores.
- The link is stored in the project file (new field `savegame`, relative path like the other paths). If the route has no project, the editor offers to create one. If that is declined, the link is kept for this session only.
- The question has a "Don't ask again for this route" checkbox, stored in the editor settings per route file. Without it the question comes every time.
- Vehicles store their parking destination as a marker number in the savegame's network. Match it to the loaded route by marker name and group, using the savegame's `AutoDrive_config.xml`. If several markers share name and group (the example route has six "G1" in group 15), fall back to the number.
- The node info in the debug panel also shows the marker number.

## Step 2 – Sheds layer

- Placed buildings: `placeables.xml` in the savegame (`filename`, `position`, `rotation`, `uniqueId`). Map-preplaced buildings (`isPreplaced="true"`) have no position there and are left out.
- Only buildings with `<indoorAreas>` in their definition XML count as sheds. The indoor rectangle comes from the i3d (plain XML): `indoorAreaStart`, `indoorAreaWidth`, `indoorAreaHeight` translations, e.g. `easyShed01` = 30 × 15 m.
- Building files: `data/...` → game folder, `$moddir$<mod>/...` → mods folder (folder or .zip, via the existing mod archive code).
- Shown as outlines in their own layer that can be turned on and off. Check visually against the map image; rotation is the most likely error.

## Step 3 – Parking spot dialog

Opened with the "Parking spots" tool (toolbar, next to Selection; shortcut S): left-click a shed outline. Right-click stays area selection.

### Fields

- Mode: back in, or drive through.
- Open side (back in) or entry side (drive through, the exit is the opposite side; front ↔ back or left ↔ right, never neighboring sides). Sides are relative to the building (front = the indoor area's height end, the building's +Z) and show their compass direction. Without a template a long side is open: the front if it is long, otherwise the left.
- Number of bays. The bay width is calculated: (shed length − wall offsets − gaps) ÷ bays. It is shown read-only; if it is below 3 m, it turns red and Create is disabled. Default number of bays: shed length ÷ 6.6 m (G1's bay width).
- Offsets in metres (one decimal): left wall, right wall, back wall (back in) or exit offset (drive through), and the gap between bays. "All gaps" sets every gap; single gaps are edited by clicking them in the preview.
  Defaults: walls 0.5 m, back wall or exit offset 2.0 m, gaps 0 m.
- Direction of the entry line and the exit line, each chosen by the user: left to right or right to left, seen from outside the open side (as in the preview).
- Markers: base name, start number (e.g. "Shed" from 3 → "Shed 3", "Shed 4", …), group (existing or new).
- Buttons: Reset shed settings, Create, Cancel.

### Previews

- Top view of the shed, rotated so the open side is at the bottom, with an arrow to map north; updates live. Walls and gaps can be clicked to edit their offset; sides can be clicked to make them the open side.
- Side view of one bay line: click a segment to edit its length, "+" inserts a node, Delete removes the selected node; the entry and exit branch points can be moved to other nodes. All bays use this layout.

### Generated network (back in)

Per bay, copied from marker G1 in group "15.P&R Hörmannhof" of the example route (`xml/g8Cq02ZGwaIPuGPr.xml`, marker node 108774). Distances are from the marker; all nodes are subprio.

- Marker: the last node before the back wall (at the back wall offset).
- Default bay line, fitted to the shed depth: dual line from the marker 0.5 m, then 1.5 m steps up to 1 m before the entry branch. Outside the open side G1's spacing: nodes at 2.3, 3.3, 4.8, 6.3, 7.8, 11.2, 14.8 and 19.7 m.
- Entry line 1 m outside the open side. Its branch starts 1.2 m before the bay (against the travel direction) and joins the dual line 2.3 m outside, pointing away from the shed (so the vehicle can't turn straight into the bay).
- Exit branch from the second-to-last node of the dual line (14.8 m outside) to the exit line, 1.6 m further out and 1.7 m along the line.
- Turn: from the dual line's end two forward connections (+3.2 m, +1.2 m); the last node has a reverse connection back to the dual line's end. The vehicle reverses straight to the marker.
- Shared by all bays: the entry line and the exit line, straight and parallel to the open side, one node per bay plus an end 5 m beyond the outer bays. Their four open ends are selected after creation so the user can connect them to the road network.

### Generated network (drive through)

- One straight forward line per bay from the entry line, through the shed, to the marker just before the exit side (exit offset), then on to the exit line. No dual and no reverse connections.
- The lines run 10 m outside the entry and exit side; bay line nodes about every 1.5 m, evenly spread.

### Other rules

- All new nodes are subprio, also on the entry and exit lines.
- New nodes take the shed's height from `placeables.xml` (placing a shed levels the ground).
- Everything is one `EditCommand`, one undo step. No check for existing spots: running it twice creates them twice, undo removes them.
- Each bay holds a list of stopping points (one for now), so rows of parking positions in drive-through sheds can be added later.

### Templates

- Saved in the editor settings per shed type (building file, e.g. `data/placeables/easySheds/easyShed01/easyShed01.xml`), so they work on any map. Several named templates per shed type are possible.
- Saved: mode, open/entry side, number of bays, all offsets, bay line layout.
- Not saved (depend on the location): line directions, marker name, start number, group.
- A shed type without a template starts with the G1 bay line layout.

## Later (roadmap)

- Several parking positions in a row in drive-through sheds.
- Showing the result on the map while the dialog is open.
