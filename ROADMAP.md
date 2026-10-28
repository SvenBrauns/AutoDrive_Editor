# Roadmap

Planned features of the AutoDrive FS25 Editor, in the order they should be implemented. The roadmap lists only work that is not done yet: finished items are removed, not checked off. What was done is in the [CHANGELOG](CHANGELOG.md).

The editor supports only Farming Simulator 25.

## 1. Parking spots in sheds

Design: [docs/parking_spots.md](docs/parking_spots.md). Each step is its own branch.

- [ ] read sheds with an indoor area from the savegame and show them as a layer
- [ ] parking spot dialog and generator (back in and drive through, templates per shed type)
- [ ] afterwards: turn docs/parking_spots.md into a manual section and delete it

## 2. Heightmap

- [ ] use the linked savegame's `terrain.heightmap.png` instead of the map's `dem.png`, since terraforming and placing buildings change the ground
- [ ] interpolate heightmap values between pixels instead of taking the nearest pixel

## 3. Further features

Features the old editor does not have.

- [ ] check for invalid connection references
- [ ] check for nodes without connections
- [ ] run the network check before saving (problems are shown, saving is still possible)
- [ ] reopen the last opened item at startup
- [ ] measuring points bound to nodes follow moved nodes
- [ ] drive-through sheds: several parking positions in a row per bay
- [ ] parking spots: show the result on the map while the dialog is open
