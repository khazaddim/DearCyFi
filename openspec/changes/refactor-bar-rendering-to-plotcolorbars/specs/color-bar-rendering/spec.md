## ADDED Requirements

### Requirement: Horizontal Liquidity Bars Use Native PlotColorBars Anchoring
The DearCyFi plot SHALL render horizontal liquidity overlays with `dcg.PlotColorBars` anchored to the visible right edge, so bar positioning follows pan/zoom without callback-driven rectangle recomputation.

#### Scenario: Initial horizontal overlay creation
- **WHEN** `DearCyFi.load_horizontal_bars(...)` is called on a plot with or without prior candle data
- **THEN** DearCyFi creates a horizontal `dcg.PlotColorBars` series using `anchor="axis_max"`
- **AND** the series is configured as non-fit-affecting overlay data

#### Scenario: Panning and zooming the X axis
- **WHEN** the user pans or zooms after horizontal bars are loaded
- **THEN** bar start and end positions track the visible right edge based on current axis limits
- **AND** no explicit bar-geometry update callback is required for repositioning

### Requirement: Candle Volume Uses PlotColorBars With Directional Colors
`PlotCandleStick` SHALL render its internal volume bars with `dcg.PlotColorBars` rather than `dcg.PlotDigital`, with default colors derived from candle direction.

#### Scenario: Up/down default coloring
- **WHEN** candle and volume data are rendered with default configuration
- **THEN** each volume bar uses the bull color when close >= open
- **AND** each volume bar uses the bear color when close < open

#### Scenario: Explicit volume color override
- **WHEN** caller-provided `volume_kwargs` supplies a valid `colors` payload
- **THEN** the provided color configuration is used
- **AND** DearCyFi still enforces count-valid color assignment behavior

### Requirement: Axis Assignment Remains Composite-Consistent
Bar series introduced by this change SHALL remain bound to the same axis pair as their owning composite or API selection.

#### Scenario: Candle axis reassignment after creation
- **WHEN** `DearCyFi.set_data(..., candle_y_axis=...)` changes candle axis assignment on an existing plot
- **THEN** the candle volume PlotColorBars series moves with the candle composite to the new axis pair
- **AND** subsequent updates continue rendering on that axis

#### Scenario: Secondary-axis horizontal overlays
- **WHEN** horizontal overlays are configured on a plot using the standard X1 time axis
- **THEN** their axis binding remains explicit and stable across updates

### Requirement: Count-Changing Updates Avoid Transient Validation Errors
DearCyFi SHALL apply update ordering compatible with `PlotColorBars` validation rules when X/Y/color array lengths change.

#### Scenario: Overlay lane count change
- **WHEN** bar count changes between updates (for example from user control input)
- **THEN** DearCyFi updates arrays in an order that avoids temporary length mismatches
- **AND** update calls complete without intermediate validation exceptions

### Requirement: DearCyFi Documents Custom DearCyGui Dependency For Color Bars
DearCyFi SHALL document that this branch requires a DearCyGui build exposing `dcg.PlotColorBars` for bar rendering features covered by this spec.

#### Scenario: Missing PlotColorBars in runtime
- **WHEN** DearCyFi runs with a DearCyGui build that lacks `PlotColorBars`
- **THEN** DearCyFi raises a clear runtime error indicating unsupported dependency level
- **AND** documentation points to the required custom DearCyGui branch
