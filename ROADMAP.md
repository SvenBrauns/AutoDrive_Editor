# Roadmap

Planned features of the AutoDrive FS25 Editor, in the order they should be implemented. Finished items are checked off.

The editor supports only Farming Simulator 25.

## Goal: feature parity with the old editor

The phases 1–5 contain everything the previous AutoDrive Course Editor (v1.1.1) can do and this editor cannot yet. When they are done, the editor is released (phase 6). Everything else waits until after the release.

Not taken over on purpose:

- FS19/FS22 support and the DDS import for those games (the editor supports only FS25)
- importing map images from a .zip and downloading them from the map image repository (replaced by `Map → Scan maps`)
- "save as default map image/heightmap" (replaced by the map cache)
- the experimental tools (road connection, scale, templates); they are unfinished in the old editor
- the debug and logging menus (replaced by the debug dock and the log file)

## 1. Network check — high priority

Menu `Check` with a result list that jumps to each location.

- [x] find nodes lying on top of each other
- [x] merge nodes lying on top of each other
- [x] move nodes outside the map back onto the map
- [x] recalculate invalid heights from the heightmap

## 2. Display — high priority

New display options are saved permanently.

- [x] minimum and maximum node size on screen
- [x] show and hide nodes and each connection type (regular, dual, reverse, subprio)
- [x] option whether hidden nodes and connections can be selected
- [x] show node IDs
- [x] show and hide marker icons
- [x] show parking positions of vehicles (savegames)

## 3. Editing — medium priority

- [x] move along one axis only (X or Z)
- [x] adjustable step for rotation snapping (today fixed 15°)
- [x] quadratic Bézier curve (one control point)

## 4. Project and application — medium priority

- [x] recently opened routes, savegames and files (File menu and welcome screen)
- [x] log file and clear error dialogs for unexpected errors
- [x] `Help` menu: about the editor, version history

## 5. Settings — low priority

- [x] change keyboard shortcuts
- [x] dark theme

## 6. Release — once phases 1–5 are done

- [x] license chosen
- [x] licenses of the used libraries checked (PySide6/LGPL, Pillow)
- [x] provided as a Windows program (.exe)
- [x] all items from phases 1–5 implemented

## 7. After the release

Features the old editor does not have.

- [ ] check for invalid connection references
- [ ] check for nodes without connections
- [ ] run the network check before saving (problems are shown, saving is still possible)
- [ ] reopen the last opened item at startup
- [ ] interpolate heightmap values between pixels instead of taking the nearest pixel
- [ ] measuring points bound to nodes follow moved nodes

## Done

- [x] interface in English and German, language setting (default: Windows language)
- [x] README in English and German, English developer documentation
- [x] short stutter when zooming in past zoom 1.0 for the first time
- [x] split `scene_renderer.py`
