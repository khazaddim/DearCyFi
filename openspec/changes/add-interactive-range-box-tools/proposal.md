# Change: Add Interactive Range Box Tools

## Why

The rectangle proof of concept proves that DearCyGui invisible hit regions can provide reliable move and resize interaction, but it is not yet a DearCyFi feature and its X coordinates become ambiguous when the candle timeline is collapsed. DearCyFi needs a first chart-managed technical-analysis drawing tool whose geometry remains tied to real candle time and that establishes a reusable foundation for Fibonacci retracements and candle-derived calculations.

## What Changes

- Add a small package-owned interactive chart-tool contract with stable identity, canonical source-space anchors, collapse refresh, and disposal lifecycle hooks.
- Add a reusable `RangeBoxTool` to the DearCyFi package, using visible drawing items and internal `DrawInvisibleButton` hit regions for body movement and corner resizing.
- Store box X anchors as source timestamps and derive plotted X coordinates from the chart's active time-collapse map, while storing Y anchors directly in the assigned price-axis coordinate space.
- Make `RangeBoxTool` the first concrete tool built on that contract, without attempting to implement a general plugin or pattern-recognition framework.
- Add generic chart ownership plus chart-level `add_box(...)`, `remove_all_boxes()`, and box-diagnostic conveniences and read-only access to active tools and boxes.
- Keep every managed box synchronized when time is collapsed, restored, or candle data is replaced.
- Associate boxes with the chart's candle series and expose changing and committed geometry hooks suitable for later corner labels, candle selection, and price-volume calculations.
- Add chart-managed anchor tooltips composed of simple text rows for semantic anchor identity, real date/time, and price while avoiding the parent and duplicate-hover races fixed in candle tooltips.
- Add a `Technical Analysis` control group beside the demo's existing data and collapse controls with `Add Box`, `Print Boxes`, and `Remove All Boxes` commands.
- Add focused automated tests and a manual demo validation path for interaction, lifecycle, and collapse round trips.

The initial change does not implement Fibonacci levels, head-and-shoulders recognition, persistent plot labels, persistence, undo/redo, or candle price-volume aggregation. Persistent labels require separate decisions about location, style, collision, and text scaling under zoom; hover tooltips do not.

## Impact

- Affected specs: `interactive-range-box-tools` (new capability)
- Affected code: `src/dearcyfi/core.py`, a new package-owned technical-analysis module, package exports, `examples/DearCyFi_Demo/DearCyFi_Demo.py`, and focused tests
- Dependencies: builds on the existing `GapCollapsedTimeMap` projection/expansion behavior and chart-owned candle/collapse lifecycle; adds no external dependency
