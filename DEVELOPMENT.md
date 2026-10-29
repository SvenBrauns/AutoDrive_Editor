# Development

Notes for working on the code of the AutoDrive FS25 Editor. The user guide is the [manual](MANUAL.md) (German: [MANUAL.de.md](MANUAL.de.md)), the overview the [README](README.md); screenshots for it are in `docs/images`; planned features are in the [roadmap](ROADMAP.md).

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

GitHub Actions checks every push and pull request with `ruff` and `pytest`. A tag such as `v0.1.0` builds the Windows version with PyInstaller and publishes it as a release. Before tagging, raise the version in `autodrive_editor/__init__.py` and `pyproject.toml` (a test checks that they match) and turn the `Unreleased` section of `CHANGELOG.md` into the new version; the app shows that file under `Help → Version history`. The release stops if the tag does not match the version, and its notes are the version's section of `CHANGELOG.md`.

```text
git tag v0.1.0
git push origin v0.1.0
```

## Structure

```text
autodrive_editor/
  model/        data model: nodes, markers, connection types
  file_io/      file formats: AutoDrive XML, heightmap, DDS
  terrain/      background map, heightmap, terrain height for moved nodes
  editing/
    commands/   undoable changes to the data model
    operations/ editing workflows of the tools (move, connect, …)
    edit_context.py  EditContext and the EditOperation base class
    edit_history.py  shared undo/redo history
  selection/    node selection
  measurement/  distance and angle measurement
  network_check/ checks that find problems in the network
  project/      loading XML, map and heightmap
  rendering/    map drawing
    spatial/    spatial indexes for nodes and connections
    layers/     the network layers (connections, nodes, markers, selection), their tile cache and the sheds
    connections/ connection data
    items/      other graphics items (grid, measurement)
  ui/
    main_window.py  main window, assembles all parts
    file_controller.py  File menu: open, save, autosave
    map_import_controller.py  map import, first start, missing maps
    actions/    tool catalog, menus, toolbars
    map_view/   map view with zoom, rotation and area selection
    tools/      mouse handling per tool
    panels/     tool panel, debug dock, display options
    controls/   grid and rotation settings
  settings/     settings kept between sessions, recently opened files
  i18n/         translation of the interface texts (tr(), German catalog)
  resources/    icons
  error_log.py  log file (%APPDATA%\AutoDrive Editor\logs) and the handler for unexpected errors
tests/          same folder structure as autodrive_editor/
packaging/      app icon, license texts and exe version info (version_info.py) for the Windows version
.github/        CI and release build
```

## Core rules in the code

- Every change to the data model is an `EditCommand` and goes through `EditHistory.push()`, so it can be undone.
- After each change, the command reports a `DataChange`; the `SceneRenderer` then updates only the affected nodes.
- Nodes, node IDs, connections, markers and the selection are not graphics items. Five layer items paint them straight from the spatial indexes, using drawing data cached per 256 m tile; after an edit only the changed tiles are rebuilt. This keeps networks with over 100,000 nodes responsive. Clicks find nodes through `SceneRenderer.get_node_at()`.
- Each editing workflow is an `EditOperation` under `editing/operations/`; it gets the shared parts (history, data, selection, view, terrain height, snapping) through one `EditContext`.
- Each tool is a `MapTool` subclass under `ui/tools/` and is described in `ui/actions/tool_catalog.py` with its icon and shortcut.
- Actions whose shortcut can be changed are registered in `MainWindowActions._create_shortcut_registry()` under a fixed name; settings.ini stores only the shortcuts that differ from the defaults, by that name. A new menu entry or tool should be registered there too.

## Translations

The interface is English and German. Texts in the code are English and wrapped in `tr()` from `autodrive_editor.i18n`; values are passed as keywords and filled into `{placeholders}` after translating:

```python
tr("Marker “{name}” added", name=name)
```

- Every new `tr()` text needs a German entry in `i18n/german.py`. `tests/i18n/test_german.py` fails for missing or unused entries and for placeholders that differ.
- Pass the text itself to `tr()`, never a variable or f-string, so the test can find it.
- Internal errors that only signal a programming mistake (e.g. `TypeError` checks) stay English and are not translated.
- The language is set at startup, before the UI modules are imported (see `app.py`), because some of them translate texts at import time. Changing the language in the settings takes effect after a restart.
- Qt's own texts (e.g. message box buttons) come from Qt's `qtbase_de.qm`.

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
- **Zoom**: there are no zoom thresholds. Every size in `DisplayStyle` is in metres and grows with the zoom, but stays between a minimum and maximum size on screen. Nodes fade in while they grow from 1.5 to 4 px, and only drawn nodes can be clicked (selected nodes always). Arrows sit in the middle of one-way connections once the connection is long enough on screen; dual connections get one a third from each end, pointing to that end. Marker icons are drawn at every zoom level; their names fade in just below `marker_name_min_zoom` (1.0), and names that would overlap an earlier one are left out. Node IDs are shown from `node_id_min_zoom` (4.0), left out where they would overlap the label of a lower ID.
- **Visibility** (`rendering/visibility.py`, `View → Show`): the layers skip hidden nodes and connection types, and `SceneRenderer.get_node_at()`, `get_connection_at()` and area selection ignore them unless `hidden_selectable` is on. Connections are drawn by their `ConnectionType` only; subprio is shown on the nodes.

## File formats when saving

Saving always uses the format the data was loaded from.

**RoutesManager**: `routes.xml` (root `autoDriveRoutesManager`) lists the routes with `name`, `fileName`, `map`, `revision`, `date` and `serverId`. The route files are in `routes/` (root `routeExport`). `<waypoints c="count">` with `x`, `y`, `z`, `out`, `in`, `flags`: values separated by `;`, several connections of one node separated by `,`, `-1` for no connection. Markers as `<markers><m i n g/>`, groups as `<groups><g i n/>`. When saving, the entry in `routes.xml` gets `revision` + 1 and the current date.

**Savegame config** (`AutoDrive_config.xml`, root `AutoDrive`, `version` 3 = FS25): `<waypoints>` with `id`, `x`, `y`, `z`, `out`, `incoming`, `flags`: values separated by `,`, connections of each node separated by `;`. Markers as `<mapmarker><mm1><id/><name/><group/></mm1>…`; their order is also their marker number. The existing file is edited, so all other settings are kept. Vehicles in `vehicles.xml` refer to targets by marker number (`firstMarker`, `secondMarker`, `parkDestination`); if the order changes, these references are updated.

**For all formats**: coordinates with three decimals (savegame) or two (route). Node IDs are the positions in the lists; gaps left by deleted nodes are closed on save, and all references and markers are rewritten. Flags are written back unchanged (including `2` and `4`), unless the type of a node was changed.

## Performance (test network with 113,058 nodes and 116,260 connections)

Proven: one layer item per kind of object that paints from the spatial indexes; per 256 m tile one `QPainterPath` per connection type and one `QPolygonF` of node positions, drawn with one Qt call each (`drawPath`, `drawPoints` with a round pen for dots); cosmetic pens with the width set per paint; arrows computed per paint from the connections sorted by length, so the loop stops at the first one too short; selection stored only as node IDs. A full repaint of the whole map takes about 30 ms, zoomed in about 20 ms.

Not suitable: a graphics item per node or connection (creating and deleting them while panning stutters), one path for the whole network (every edit rebuilds it), `Qt.RoundCap` on connection pens (wide lines become 20–50 times slower; flat caps look the same since nodes cover the joints).
