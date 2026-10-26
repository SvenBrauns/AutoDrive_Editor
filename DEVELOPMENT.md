# Development

Notes for working on the code of the AutoDrive FS25 Editor. The user guide is the [README](README.md); planned features are in the [roadmap](ROADMAP.md).

## Running from source

```text
pip install -r requirements.txt
python main.py
```

or `python -m autodrive_editor`.

## Tests and checks

```text
pip install -r requirements-dev.txt
python -m pytest
ruff check .
ruff format .
```

GitHub Actions checks every push and pull request with `ruff` and `pytest`. A tag such as `v0.1.0` builds the Windows version with PyInstaller and publishes it as a release:

```text
git tag v0.1.0
git push origin v0.1.0
```

## Structure

```text
autodrive_editor/
  model/        data model: nodes, markers, connection types
  file_io/      file formats: AutoDrive XML, project files, heightmap, DDS
  terrain/      background map, heightmap, terrain height for moved nodes
  editing/
    commands/   undoable changes to the data model
    operations/ editing workflows of the tools (move, connect, …)
    edit_history.py  shared undo/redo history
  selection/    node selection
  measurement/  distance and angle measurement
  project/      loading XML, map, heightmap and projects
  rendering/    map drawing
    spatial/    spatial indexes for nodes and connections
    visible/    graphics items only for the visible area
    connections/ connection data, geometry and detail drawing
    items/      individual graphics items
  ui/
    main_window.py  main window, assembles all parts
    actions/    tool catalog, menus, toolbars
    map_view/   map view with zoom, rotation and area selection
    tools/      mouse handling per tool
    panels/     tool panel, debug dock, display options
    controls/   grid and rotation settings
  resources/    icons
tests/          same folder structure as autodrive_editor/
packaging/      app icon and license texts for the Windows version
.github/        CI and release build
```

## Core rules in the code

- Every change to the data model is an `EditCommand` and goes through `EditHistory.push()`, so it can be undone.
- After each change, the command reports a `DataChange`; the `SceneRenderer` then updates only the affected nodes.
- Only nodes, markers and selection rings in the visible area exist as graphics items, so networks with over 100,000 nodes stay responsive.
- Each tool is a `MapTool` subclass under `ui/tools/` and is described in `ui/actions/tool_catalog.py` with its icon and shortcut.

## Principles

- Direct compatibility: `overview.dds` and `dem.png` are used without manual conversion.
- Source data is never overwritten automatically; writing happens only through an explicit save (with a `.bak` backup first).
- The meaning of nodes, flags, markers, coordinates and heightmap values is verified against real AutoDrive data.
- Use our own icons; before a release, check licenses, map images and third-party content.

## Background knowledge

- **Connections** between A and B are stored on both nodes (see `model/connections.py`):

  ```text
              A.outgoing∋B  A.incoming∋B  B.outgoing∋A  B.incoming∋A
  Regular          yes           -             -             yes
  Dual             yes           yes           yes           yes
  Reverse          yes           -             -             -
  ```

- **Flags**: `0` = Regular, `1` = Subprio. The XML IDs are 1-based.
- **Maps**: for FS22/FS25, `overview.dds` has a middle quarter that must be cropped (4096² → 2048²). The map size (`map_scale` 1/2/4/8 for original/4x/16x/64x) comes from the map configuration, never from the network bounds. For a 16x map: 8192 × 8192 m, world coordinates −4096 to +4096.
- **Heightmap** (`dem.png`, 16-bit grayscale): `height = raw_value / 65535.0 * 255.0`. Compared with the Y values of a test network with 113,058 nodes, the median difference is 0.02 m; larger differences occur only on bridges, ramps and building platforms.
- **Angles**: map angle 0° = up, 90° = right; independent of view and grid rotation.
- **Zoom**: below technical zoom 1.0, only three bundled connection paths are drawn; from 1.0 on, nodes, markers, selection rings and connections with arrows are drawn. Visible-area changes are reported with a 50 ms delay.

## File formats when saving

Saving always uses the format the data was loaded from.

**RoutesManager**: `routes.xml` (root `autoDriveRoutesManager`) lists the routes with `name`, `fileName`, `map`, `revision`, `date` and `serverId`. The route files are in `routes/` (root `routeExport`). `<waypoints c="count">` with `x`, `y`, `z`, `out`, `in`, `flags`: values separated by `;`, several connections of one node separated by `,`, `-1` for no connection. Markers as `<markers><m i n g/>`, groups as `<groups><g i n/>`. When saving, the entry in `routes.xml` gets `revision` + 1 and the current date.

**Savegame config** (`AutoDrive_config.xml`, root `AutoDrive`, `version` 3 = FS25): `<waypoints>` with `id`, `x`, `y`, `z`, `out`, `incoming`, `flags`: values separated by `,`, connections of each node separated by `;`. Markers as `<mapmarker><mm1><id/><name/><group/></mm1>…`; their order is also their marker number. The existing file is edited, so all other settings are kept. Vehicles in `vehicles.xml` refer to targets by marker number (`firstMarker`, `secondMarker`, `parkDestination`); if the order changes, these references are updated.

**For all formats**: coordinates with three decimals (savegame) or two (route). Node IDs are the positions in the lists; gaps left by deleted nodes are closed on save, and all references and markers are rewritten. Flags are written back unchanged (including `2` and `4`), unless the type of a node was changed.

## Performance (test network with 113,058 nodes and 116,260 connections)

Proven: native `QGraphicsEllipseItem` nodes, graphics items only for the visible area plus a buffer (256 m tiles, 128 m buffer), three bundled global connection paths, spatial indexes, selection stored only as node IDs, separate preview and final selection.

Not suitable: custom `paint()` per node, permanent NodeItems for all nodes, one graphics item per connection, large stored arrow paths, permanent selection rings for all selected nodes.
