# Roadmap

Planned features of the AutoDrive FS25 Editor, in the order they should be implemented. The roadmap lists only work that is not done yet: finished items are removed, not checked off. What was done is in the [CHANGELOG](CHANGELOG.md).

The editor supports only Farming Simulator 25.

## 1. Planning mode and generators

Design: [docs/generators.md](docs/generators.md). Each step is its own branch.

- [ ] join rules: fixed nodes, join points, reuse of separate pieces, replacement of pass-through stretches, regular and subprio for yards
- [ ] stations generator: pick buildings on the map, lanes over the triggers, markers, entry and exit routes
- [ ] shed generator: connect the parking layout to the network
- [ ] bunker silos generator (designed separately)
- [ ] afterwards: turn docs/generators.md into manual sections and delete it
- [ ] afterwards: optimize Find route. Searches block the map while dragging (thread holds the GIL; try a separate process); setup grows with each waypoint (one cost map per leg, ~2 s for 15 waypoints); cancelling takes up to 2 s; waypoints closer than the turning radius get the search stuck, and the direct curves of the fallback then loop

## 2. Tool options

- [ ] options of the selected tool (e.g. node spacing of the line tools) appear by themselves while the tool is selected and disappear when another tool is chosen, instead of behind the arrow of the tool button
