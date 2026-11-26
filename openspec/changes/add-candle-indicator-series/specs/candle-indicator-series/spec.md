## ADDED Requirements

### Requirement: Reusable Candle Indicator Contract
The package SHALL provide a reusable calculation contract for indicators derived from candle data, with timestamp-aligned named output arrays, and SHALL allow indicator instances to be created, edited, and removed independently of the demo GUI.

#### Scenario: Calculate without the demo
- **WHEN** a caller constructs an SMA calculation with valid parameters and supplies candle data
- **THEN** it produces one named output aligned to the candle source timestamps without requiring demo widgets
- **AND** the contract can represent future calculations using multiple candle inputs and named outputs without requiring those indicators to be implemented now

#### Scenario: Create matching instances
- **WHEN** two indicators of the same type and parameters are created
- **THEN** each has a distinct stable instance ID and can be edited, hidden, and removed independently

### Requirement: Simple Moving Average Calculation
The system SHALL calculate an SMA over a positive integer number of existing candle observations, using a selectable open, high, low, or close input. Output SHALL be aligned with the candle timestamps and SHALL be NaN until a complete finite window exists.

#### Scenario: Compute a known window
- **GIVEN** close values `[1, 2, 3, 4]` and period 3
- **WHEN** the SMA is calculated
- **THEN** its output is `[NaN, NaN, 2, 3]`

#### Scenario: Select another candle field
- **WHEN** the SMA input is changed from close to high
- **THEN** its values are recalculated using highs and not closes

#### Scenario: Preserve gaps and non-finite windows
- **WHEN** source candles have a time gap
- **THEN** the window counts existing observations across that gap without adding or resetting samples
- **AND** any window containing a non-finite selected value yields NaN until a complete finite window is available

#### Scenario: Reject invalid parameters
- **WHEN** the period is a boolean, non-integral, or less than one, or the selected field is unsupported
- **THEN** creation or editing fails with a clear error without changing an existing indicator

### Requirement: Candle Mutation Synchronization
The chart SHALL synchronize all attached candle-derived indicators on complete candle replacement, latest-candle revision, and candle append through the supported chart-managed APIs. It SHALL calculate from canonical candle values and SHALL keep source data, indicator values, projections, and presentation coherent when an operation fails.

#### Scenario: Revise a forming candle repeatedly
- **WHEN** the latest candle is revised more than once
- **THEN** each indicator reflects the current complete candle state
- **AND** its output equals a fresh calculation from that state, without accumulating prior revisions

#### Scenario: Append a candle with a time gap
- **WHEN** a candle is appended after a normal interval or an accepted longer gap
- **THEN** every indicator gains exactly one aligned source timestamp and updated value
- **AND** the gap does not create synthetic SMA observations

#### Scenario: Replace loaded candles
- **WHEN** the chart reloads candles or changes symbol through complete data replacement
- **THEN** existing indicators recalculate against the replacement data while retaining their configurations and identities
- **AND** the chart follows the existing full-replacement time restore/reset lifecycle

#### Scenario: Reject failed preparation or publication
- **WHEN** indicator preparation or publication fails during a candle mutation
- **THEN** the operation surfaces the failure and leaves or restores the previous coherent candle, indicator, time-map, and presentation state
- **AND** it does not report success with stale derived values

### Requirement: Indicator Rendering and Shared Time
Each indicator instance SHALL render as one independently toggleable legend item, preserve real candle timestamps separately from plotted coordinates, and follow the chart's active time projection without changing candle source data.

#### Scenario: Add an indicator to a collapsed chart
- **WHEN** an SMA is added while time is collapsed
- **THEN** its plotted timestamps immediately align with their corresponding candle plot coordinates
- **AND** its source timestamps remain the original candle timestamps

#### Scenario: Use another collapse source
- **WHEN** another registered series is the collapse source
- **THEN** each indicator remains aligned with its corresponding candle's plotted coordinate through collapse, streaming, and restore

#### Scenario: Toggle a legend entry
- **WHEN** a user hides one indicator from its legend entry
- **THEN** its line and hover targets are hidden together and do not contribute to fit
- **AND** other indicators and candles remain unchanged

#### Scenario: Inspect a source-time tooltip
- **WHEN** the user hovers a visible finite indicator observation after collapse
- **THEN** the tooltip displays the original candle timestamp and indicator value rather than the synthetic plot timestamp

#### Scenario: Preserve presentation during updates
- **WHEN** a candle update or valid parameter edit redraws an indicator
- **THEN** its identity, legend visibility, styles, Y-axis assignment, popup controls, and viewport limits are preserved
- **AND** missing or warm-up values break the line rather than being interpolated

### Requirement: Independent Indicator Line Styling
Each indicator instance SHALL expose an independent validated line color and line thickness while remaining a single legend-enabled drawing item.

#### Scenario: Create with a custom line style
- **WHEN** a caller creates or adds an indicator with a valid RGBA line color and positive finite screen-pixel thickness
- **THEN** the indicator's `DrawPolyline` children use that color and thickness
- **AND** the style belongs only to that indicator instance

#### Scenario: Edit line styling
- **WHEN** a caller or the demo edits an indicator's line color or thickness
- **THEN** the line redraws with the validated style
- **AND** the instance ID, parameters, legend visibility, Y-axis, source timestamps, and plot projection remain unchanged

#### Scenario: Reject invalid line styling
- **WHEN** line thickness is not a positive finite number or line color is malformed
- **THEN** creation or editing fails with a clear error
- **AND** an existing indicator's style and chart state remain unchanged

### Requirement: Transactional Indicator Lifecycle
The system SHALL validate and prepare indicator creation and parameter edits before publishing them, and SHALL remove an indicator's chart registration, drawing item, and associated UI resources when it is removed.

#### Scenario: Edit an existing indicator
- **WHEN** a user changes SMA 20 to period 30 with valid settings
- **THEN** that instance recalculates and updates its legend label and values
- **AND** it retains its stable ID, presentation state, and active time projection

#### Scenario: Reject an invalid edit
- **WHEN** parameter validation or recalculation fails during an edit
- **THEN** the error is reported and the existing parameters, values, identity, presentation, and chart state remain unchanged

#### Scenario: Remove one instance
- **WHEN** one indicator is removed
- **THEN** its registration, legend entry, drawings, callbacks, and edit popup are cleaned up
- **AND** the candles and other indicator instances remain intact

### Requirement: Demo Indicator Controls
The demo SHALL provide a left-side control for adding SMA instances and a per-instance legend context menu that opens a parameter editor and supports removal. The editor SHALL target the specific selected instance.

#### Scenario: Add multiple SMAs
- **WHEN** the user selects SMA, enters a positive period, chooses an OHLC field, and selects Add
- **THEN** a new SMA appears on the DearCyFi chart with its own legend entry
- **AND** repeating the action creates a separate instance, even for matching parameters

#### Scenario: Open and apply an edit
- **WHEN** the user right-clicks an indicator legend entry and selects Edit
- **THEN** a popup opens with that instance's current period, input field, line color, and line thickness
- **AND** Apply updates only that instance after successful validation

#### Scenario: Cancel or reject an edit
- **WHEN** the user cancels or applies invalid parameters
- **THEN** the indicator remains unchanged
- **AND** invalid Apply keeps the popup open and shows an actionable error

#### Scenario: Stream while a menu is present
- **WHEN** synthetic candle streaming revises or appends candles
- **THEN** existing indicator menus remain usable and their displayed indicator values stay synchronized
- **AND** the original-time comparison plot does not gain indicator items
