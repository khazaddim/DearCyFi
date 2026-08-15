## ADDED Requirements

### Requirement: Extensible Interactive Tool Foundation
DearCyFi SHALL define a minimal interactive chart-tool contract with stable per-chart identity, semantic tool kind, projection refresh, and disposal lifecycle, without requiring every tool to use rectangle geometry or corner handles.

#### Scenario: Register different concrete tool shapes
- **WHEN** a concrete chart tool implements the shared lifecycle contract
- **THEN** the chart can retain and refresh it through the generic tool collection
- **AND** the tool remains responsible for its own semantic geometry, drawing children, and interaction regions

#### Scenario: Identify a tool
- **WHEN** a tool is added to a chart
- **THEN** it has a non-empty `tool_id` unique within that chart
- **AND** a stable semantic `tool_kind` for its lifetime

#### Scenario: Reject duplicate identity
- **WHEN** registration would add a second tool with the same `tool_id` to one chart
- **THEN** registration fails clearly
- **AND** the existing tool remains registered and unchanged

### Requirement: Common Source-Space Anchors
DearCyFi SHALL provide an immutable finite source-space anchor representation containing a real source timestamp and a Y-axis value, while allowing each concrete tool to assign its own semantic anchor roles and geometry container.

#### Scenario: Define box and future pattern anchors
- **WHEN** a range box uses two normalized corner anchors and a future multi-point tool uses named pattern anchors
- **THEN** both use the same source-time and Y-value coordinate meaning
- **AND** neither is required to adopt the other's geometry shape or interaction rules

#### Scenario: Reject an invalid anchor
- **WHEN** an anchor contains a non-finite source timestamp or Y value
- **THEN** anchor construction fails with a clear validation error

### Requirement: Interactive Range Box
DearCyFi SHALL provide a reusable range-box tool with a visible rectangle, a movable body region, and four corner resize regions implemented with DearCyGui invisible interaction items.

#### Scenario: Move a box
- **WHEN** a user drags the box body by a finite plot-coordinate delta
- **THEN** both corners move by that delta
- **AND** the box width and height remain unchanged
- **AND** plot panning does not consume the owned drag

#### Scenario: Resize from a corner
- **WHEN** a user drags a corner handle
- **THEN** the corresponding X and Y anchors change from the drag-start geometry
- **AND** the opposite corner remains fixed
- **AND** visible geometry and invisible hit regions remain synchronized

#### Scenario: Interact outside a box
- **WHEN** the pointer is outside all body and handle hit regions
- **THEN** the range-box tool does not capture the pointer
- **AND** normal plot pan and zoom interaction remains available

### Requirement: Canonical Source-Time Geometry
Each range box SHALL preserve its X anchors as real source timestamps separately from its rendered plot X coordinates and SHALL preserve its Y anchors in its assigned price-axis coordinate space.

#### Scenario: Render without collapsed time
- **WHEN** the chart has no active collapsed-time map
- **THEN** each rendered box X anchor equals its source-time anchor

#### Scenario: Render with collapsed time
- **WHEN** the chart has an active collapsed-time map
- **THEN** each source-time anchor is projected through that map for rendering
- **AND** the stored source-time anchors remain unchanged

#### Scenario: Drag while time is collapsed
- **WHEN** a user moves or resizes a box on a collapsed chart
- **THEN** each changed rendered X anchor is expanded through the active map before source geometry is committed
- **AND** subsequent restore and collapse operations derive their rendered positions from that committed source geometry

#### Scenario: Reject invalid geometry
- **WHEN** a caller supplies a non-finite X or Y anchor or geometry below configured minimum dimensions
- **THEN** box creation or mutation fails with a clear validation error
- **AND** no partially initialized box remains managed by the chart

### Requirement: Chart-Managed Box Commands
The `DearCyFi` chart SHALL own one ordered collection of interactive tools and SHALL expose callback-friendly `add_box(...)` and `remove_all_boxes()` operations plus read-only generic and box-filtered collection access.

#### Scenario: Add an explicit box
- **WHEN** a caller invokes `add_box(...)` with valid source-time and price corners after candles are loaded
- **THEN** the chart creates and retains one independent range-box tool
- **AND** returns that tool to the caller

#### Scenario: Add a default box from a UI control
- **WHEN** a DearCyGui callback invokes `add_box(...)` without explicit corners on a chart with candles
- **THEN** the chart derives useful initial geometry from the visible chart range or candle extents
- **AND** adds one box without requiring provider-specific state

#### Scenario: Add without candles
- **WHEN** `add_box(...)` is invoked before a candle series is loaded
- **THEN** it fails with a clear missing-candle error
- **AND** the managed box collection remains unchanged

#### Scenario: Remove all boxes
- **WHEN** `remove_all_boxes()` is invoked with zero or more active boxes
- **THEN** every managed box and its visible and interactive children are disposed
- **AND** no range-box tools remain in either collection view
- **AND** managed tools of other kinds remain unchanged
- **AND** candle and other plotted series remain unchanged

#### Scenario: Add multiple boxes
- **WHEN** `add_box(...)` is invoked more than once
- **THEN** each returned box has independent geometry and interaction state
- **AND** all created boxes are present in chart collection order

### Requirement: Collapse Lifecycle Synchronization
The chart SHALL invoke the generic projection-refresh lifecycle for all managed interactive tools whenever candle time is collapsed, restored, or replaced, without using annotation anchors to construct the collapse map.

#### Scenario: Collapse with existing boxes
- **WHEN** candle time is collapsed after boxes have been added
- **THEN** candle timestamps remain the selected source for map construction
- **AND** every box reprojects its source-time anchors through the resulting map

#### Scenario: Restore with existing boxes
- **WHEN** a collapsed chart is restored
- **THEN** every box renders at its preserved source-time anchors
- **AND** box Y bounds remain unchanged

#### Scenario: Replace candle data
- **WHEN** candle data is replaced while boxes exist
- **THEN** each box remains associated with the chart's current candle series
- **AND** preserves its canonical source geometry
- **AND** refreshes against the chart's resulting collapsed or uncollapsed state

### Requirement: Box Coordinate Diagnostics
The chart SHALL provide immutable range-box diagnostic snapshots and a callback-friendly print command that reports each box's stable identity, canonical source-time/price geometry, and current rendered plot geometry.

#### Scenario: Print boxes without collapsed time
- **WHEN** one or more boxes exist on an uncollapsed chart and the print command is invoked
- **THEN** output contains each box's stable ID and tool kind
- **AND** contains its source and rendered corner coordinates
- **AND** rendered X coordinates equal source X timestamps

#### Scenario: Print boxes with collapsed time
- **WHEN** one or more boxes exist on a collapsed chart and the print command is invoked
- **THEN** output preserves each box's real source-time coordinates
- **AND** separately reports its projected plot coordinates
- **AND** does not label projected X coordinates as real timestamps

#### Scenario: Print an empty collection
- **WHEN** no range boxes exist and the print command is invoked
- **THEN** it returns and reports an explicit `No range boxes.` message

#### Scenario: Consume diagnostics programmatically
- **WHEN** application or test code requests box snapshots
- **THEN** it receives immutable snapshots in chart collection order
- **AND** formatting or printing does not mutate any tool geometry

### Requirement: Geometry Hooks for Future Analysis
Each range box SHALL expose immutable source-space geometry and SHALL support distinct high-level changing and committed geometry callbacks without exposing internal invisible-button plumbing.

#### Scenario: Receive a live geometry update
- **WHEN** a box is moving or resizing interactively
- **THEN** the configured changing callback receives the box and an immutable source-time/price geometry snapshot
- **AND** application code can update inexpensive live readouts

#### Scenario: Receive a committed geometry update
- **WHEN** an interactive drag is released or valid geometry is assigned programmatically
- **THEN** the configured committed callback receives the box and an immutable source-time/price geometry snapshot exactly once for that commit
- **AND** application code can inspect the chart's associated candle series using those bounds

#### Scenario: Resolve current candles after replacement
- **WHEN** candle data has been replaced since a box was created
- **THEN** analysis hooks resolve the chart's current candle series
- **AND** do not retain a stale candle object

#### Scenario: Add future analysis without changing coordinate meaning
- **WHEN** a later feature adds corner labels, candle selection, Fibonacci levels, or price-volume calculations
- **THEN** it can use the preserved source timestamps and price bounds
- **AND** does not need to interpret collapsed plot coordinates as real timestamps

### Requirement: Demo Technical-Analysis Controls
The DearCyFi demo SHALL provide `Add Box`, `Print Boxes`, and `Remove All Boxes` commands in a dedicated technical-analysis control group near the existing data and collapse controls.

#### Scenario: Add boxes from the demo
- **WHEN** the user activates `Add Box` after candle data is loaded
- **THEN** the demo delegates to the chart's `add_box(...)` operation
- **AND** a new independently interactive box appears on the candle plot

#### Scenario: Clear boxes from the demo
- **WHEN** the user activates `Remove All Boxes`
- **THEN** the demo delegates to the chart's `remove_all_boxes()` operation
- **AND** all boxes disappear without reloading or changing plotted data

#### Scenario: Print boxes from the demo
- **WHEN** the user activates `Print Boxes`
- **THEN** the demo delegates to the chart's box diagnostic command
- **AND** reports the resulting identities and coordinates through the existing status path
- **AND** emits the same diagnostic text to the console

#### Scenario: Keep tool controls separate from providers
- **WHEN** the demo constructs its technical-analysis controls
- **THEN** those controls are not registered as a data-source widget
- **AND** they do not participate in provider discovery, loading, or disposal contracts