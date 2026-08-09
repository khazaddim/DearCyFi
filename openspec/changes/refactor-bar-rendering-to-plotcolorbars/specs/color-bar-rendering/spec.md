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
`PlotCandleStick` SHALL render its internal volume bars with `dcg.PlotColorBars` rather than `dcg.PlotDigital`, with default colors derived from candle direction and normalized geometry that preserves the prior bottom-anchored, Y-zoom-independent visual behavior.

#### Scenario: Up/down default coloring
- **WHEN** candle and volume data are rendered with default configuration
- **THEN** each volume bar uses the bull color when close >= open
- **AND** each volume bar uses the bear color when close < open

#### Scenario: Explicit volume color override
- **WHEN** caller-provided `volume_kwargs` supplies a valid `colors` payload
- **THEN** the provided color configuration is used
- **AND** DearCyFi still enforces count-valid color assignment behavior

### Requirement: Candle Volume Uses Normalized Screen-Relative Geometry
The default candle-volume `PlotColorBars` SHALL use `anchor="axis_min"`, `value_space="normalized"`, and `ignore_fit=True`, with non-negative volume magnitudes normalized before assignment so volume remains bottom-anchored and screen-relative as Y-axis limits change.

#### Scenario: Y-axis zoom changes price limits
- **WHEN** the selected Y-axis is panned or zoomed without changing candle-volume data
- **THEN** volume bars remain anchored to the visible bottom of that Y-axis
- **AND** their relative screen heights remain stable rather than scaling as raw price-axis values
- **AND** volume bars do not influence automatic axis fitting

#### Scenario: Positive volume values are normalized
- **WHEN** a candle update contains one or more positive volume values
- **THEN** DearCyFi normalizes their non-negative magnitudes to a stable input range
- **AND** the largest volume maps to the configured `normalized_max_fraction` of visible plot height
- **AND** smaller volumes retain proportional heights

#### Scenario: Volume values contain no positive magnitude
- **WHEN** volume data is empty, zero, or all zero
- **THEN** normalization completes without division errors or non-finite values
- **AND** no positive-height volume bar is produced for a zero value

### Requirement: Existing Diagnostics Remain Unchanged
The PlotColorBars migration SHALL NOT change label-extent, overlap, date-context, or gap-collapse diagnostic rendering and behavior.

#### Scenario: Diagnostics remain available after bar migration
- **WHEN** the PlotColorBars-backed volume and horizontal bar paths are active
- **THEN** label-extent, overlap, and date-context diagnostics continue using their existing `dcg.PlotDigital` series
- **AND** gap-collapse diagnostics and testing behavior remain unchanged

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

### Requirement: Legacy Bar Utility Is Deprecated
DearCyFi SHALL retain `DCG_Bar_Utils.py` temporarily for compatibility while removing it from default production and demo rendering paths.

#### Scenario: Existing downstream import
- **WHEN** downstream code imports the legacy bar utility during the deprecation period
- **THEN** the module remains available
- **AND** it communicates that new code must use `dcg.PlotColorBars`

### Requirement: First-Stage Horizontal Bar Sizing Is Approximate
The first-stage integration SHALL provide stable default price-sampled horizontal bars without requiring exact horizontal-bar visual sizing at every zoom level. This approximation SHALL NOT waive the normalized, Y-zoom-independent candle-volume behavior required by this specification.

#### Scenario: Zoom changes approximate horizontal bar sizing
- **WHEN** the user changes plot zoom and the apparent bar size is not yet exact
- **THEN** the horizontal bars remain visible and usable through `PlotColorBars`
- **AND** precise horizontal sizing is deferred to a follow-up design for volume-weighted price sampling
