# Roadmap

Planned features of the AutoDrive FS25 Editor, in the order they should be implemented. Finished items are checked off.

The editor supports only Farming Simulator 25.

## 1. Comparison with the old editor — high priority

The goal is that the editor can do everything the previous AutoDrive Course Editor for FS25 can do. The result of this comparison decides which features still need to be added to this roadmap.

- [ ] compare the feature list of the old editor and add the missing features here

## 2. Network check — high priority

Menu `Prüfen` (Check) with a result list that jumps to each location. The same check runs before saving: problems found are shown, but saving is still possible.

- [ ] invalid connection references
- [ ] nodes without connections
- [ ] merge nodes lying on top of each other
- [ ] nodes outside the map
- [ ] recalculate all heights from the heightmap
- [ ] check before saving

## 3. Project and application — medium priority

- [ ] recently opened routes, savegames and files (File menu and welcome screen)
- [ ] reopen the last opened item at startup
- [ ] clear error dialogs

## 4. English interface — medium priority

AutoDrive is used internationally. For the release, the editor should also be usable in English.

- [x] interface in English and German, language setting (default: Windows language)
- [x] README in English and German, English developer documentation

## 5. Display — low priority

New display options are saved permanently.

- [ ] show and hide nodes and individual connection types
- [ ] show node IDs
- [x] minimum and maximum node size on screen

## 6. Release — once feature parity with the old editor is reached

- [x] license chosen
- [x] licenses of the used libraries checked (PySide6/LGPL, Pillow)
- [x] provided as a Windows program (.exe)
- [ ] all items from phase 1 implemented

## Technical items on the side

These are done when a phase touches the affected code anyway.

- [x] short stutter when zooming in past zoom 1.0 for the first time
- [ ] interpolate heightmap values between pixels instead of taking the nearest pixel
- [ ] measuring points bound to nodes follow moved nodes
- [x] split `scene_renderer.py`
