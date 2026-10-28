# Version history

## Unreleased

- Dual connections get an arrow pointing to each end
- Connections are always colored by their type, also into subprio nodes; the separate subprio connection color and `View → Show → Subprio connections` are gone
- The colors of regular and subprio nodes can be set under `View → Display options`
- Routes can be linked to a savegame (`File → Link savegame…`, also offered when a route is opened) to show where its vehicles park; the link is kept in the route's project
- The debug info shows the number of a selected marker
- `View → Show → Sheds`: outlines of the indoor areas of the buildings placed in the loaded or linked savegame

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
