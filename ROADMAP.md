# Roadmap

Planned features of the AutoDrive FS25 Editor, in the order they should be implemented. The roadmap lists only work that is not done yet: finished items are removed, not checked off. What was done is in the [CHANGELOG](CHANGELOG.md).

The editor supports only Farming Simulator 25.

## 1. Planning mode and generators

Design: [docs/generators.md](docs/generators.md). Each step is its own branch.

- [ ] drivability map from the savegame's `vehicleNavigationCostmap.dat`, route finder with turning radius, `Find route` in planning mode
- [ ] join rules: fixed nodes, join points, reuse of separate pieces, replacement of pass-through stretches, regular and subprio for yards
- [ ] stations generator: pick buildings on the map, lanes over the triggers, markers, entry and exit routes
- [ ] shed generator: connect the parking layout to the network, move it to the `Generate` menu
- [ ] bunker silos generator (designed separately)
- [ ] afterwards: turn docs/generators.md into manual sections and delete it
