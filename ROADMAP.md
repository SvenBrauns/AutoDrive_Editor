# Roadmap

Planned features of the AutoDrive FS25 Editor, in the order they should be implemented. The roadmap lists only work that is not done yet: finished items are removed, not checked off. What was done is in the [CHANGELOG](CHANGELOG.md).

The editor supports only Farming Simulator 25.

## 1. Planning mode and generators

- [ ] stations generator: connect the station lanes to the roads (junctions to and from both road directions), yard roads past the stops (through or ring), back-in bays where no lane fits, regular and subprio rules for yards, gate warnings
- [ ] shed generator: connect the parking layout to the network
- [ ] bunker silos generator (designed separately)
- [ ] Find route: a clearer way to delete waypoints (right-click and `Backspace` exist but were not found); after `Enter` the tool should not stay attached to the last node; undo inside the tool should be finer (undoing the last waypoint undid the route already added with `Enter`)
- [ ] afterwards: optimize Find route. Searches block the map while dragging (thread holds the GIL; try a separate process); setup grows with each waypoint (one cost map per leg, ~2 s for 15 waypoints); cancelling takes up to 2 s; waypoints closer than the turning radius get the search stuck, and the direct curves of the fallback then loop.

## 2. Tool options

- [ ] options of the selected tool (e.g. node spacing of the line tools) appear by themselves while the tool is selected and disappear when another tool is chosen, instead of behind the arrow of the tool button
