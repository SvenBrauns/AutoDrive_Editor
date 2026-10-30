# Roadmap

Planned features of the AutoDrive FS25 Editor, in the order they should be implemented. The roadmap lists only work that is not done yet: finished items are removed, not checked off. What was done is in the [CHANGELOG](CHANGELOG.md).

The editor supports only Farming Simulator 25.

## 1. Planning mode and generators

Design: [docs/generators.md](docs/generators.md). Each step is its own branch.

- [ ] stations generator, entry and exit routes (5b): connect the lanes over the triggers to the network; with the rest of the join rules (fixed nodes, "part of another layout" for join points, reuse of separate pieces, replacement of pass-through stretches, regular and subprio for yards)
- [ ] shed generator: connect the parking layout to the network
- [ ] bunker silos generator (designed separately)
- [ ] afterwards: turn docs/generators.md into manual sections and delete it
- [ ] Find route: a clearer way to delete waypoints (right-click and `Backspace` exist but were not found); after `Enter` the tool should not stay attached to the last node; undo inside the tool should be finer (undoing the last waypoint undid the route already added with `Enter`)
- [ ] afterwards: optimize Find route. Searches block the map while dragging (thread holds the GIL; try a separate process); setup grows with each waypoint (one cost map per leg, ~2 s for 15 waypoints); cancelling takes up to 2 s; waypoints closer than the turning radius get the search stuck, and the direct curves of the fallback then loop. Also: measure the turning radii used in the biggest Thüringen route (`modSettings/FS25_AutoDrive/routesManager/routes/FdwBaSDQopZtIWyv.xml`, "Thueringen_2.0") to pick the default radius, and make routes straight where possible instead of wavy (e.g. a higher turn cost or smoothing the found path)

## 2. Tool options

- [ ] options of the selected tool (e.g. node spacing of the line tools) appear by themselves while the tool is selected and disappear when another tool is chosen, instead of behind the arrow of the tool button
