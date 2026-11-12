## MODIFIED Requirements

### Requirement: Scalar Econometric Line Rendering
The package SHALL provide a reusable econometric series that renders one numeric value per timestamp using line primitives and optional observation markers inside one legend-enabled DearCyGui drawing item.

#### Scenario: Render a weekly scalar series
- **WHEN** a consumer creates an econometric series with equal-length timestamp and numeric value arrays
- **THEN** the series renders a line at those coordinates
- **AND** the consumer may enable visible markers without creating a second data model
- **AND** markers keep a constant screen-space size while zooming
- **AND** fitting the assigned axes includes every finite observation, including isolated observations when markers and tooltips are disabled

#### Scenario: Preserve missing observations
- **WHEN** the value array contains a NaN observation
- **THEN** the line rendering breaks at that observation
- **AND** the series does not silently interpolate or forward-fill the missing value

#### Scenario: Fit empty or non-finite data
- **WHEN** the series contains no finite observations
- **THEN** it does not supply invalid bounds to axis fitting

#### Scenario: Toggle the series from the legend
- **WHEN** a user hides the series using its legend entry
- **THEN** its line, markers, and observation interactions are hidden together
- **AND** any active observation tooltip is dismissed
- **AND** the hidden series does not affect axis fitting
- **AND** restoring the legend entry restores the complete series

#### Scenario: Update a hidden series
- **WHEN** a consumer updates the data or plotted dates of a hidden series
- **THEN** the series remains hidden until the user restores it from the legend

### Requirement: Econometric Data Validation and Updates
The econometric series SHALL validate its scalar data and SHALL support replacing its complete dataset without leaving rendering or interaction state partially updated.

#### Scenario: Reject mismatched arrays
- **WHEN** timestamp and value arrays have different lengths
- **THEN** construction or update fails with a clear `ValueError`

#### Scenario: Replace all observations
- **WHEN** a consumer performs a complete data update with valid timestamps, values, and optional metadata
- **THEN** the drawing primitives and tooltip interaction coordinates reflect the new dataset
- **AND** the update does not retain stale observation hit regions

### Requirement: Separate Source and Plot Timestamps
The econometric series SHALL preserve original source timestamps separately from mutable plotted X coordinates.

#### Scenario: Apply collapsed coordinates
- **WHEN** the chart supplies collapsed plot dates for an existing econometric series
- **THEN** the line, markers, and interaction layer move to the supplied plot dates
- **AND** the original source dates remain unchanged

#### Scenario: Restore original coordinates
- **WHEN** the chart requests restoration after time collapse is cleared
- **THEN** the plotted X coordinates equal the original source dates

### Requirement: Basic Observation Tooltips
The econometric series SHALL provide an optional basic tooltip for individual observations.

#### Scenario: Hover an observation after collapse
- **WHEN** the pointer hovers an econometric observation after its plotted timestamp has been collapsed
- **THEN** the tooltip displays the series label, formatted original source date, and formatted numeric value
- **AND** the tooltip does not display the synthetic collapsed coordinate as the observation date

#### Scenario: Disable tooltips
- **WHEN** tooltips are disabled for the series
- **THEN** observation hover does not create a tooltip

## ADDED Requirements

### Requirement: Explicit Primitive Renderer Styling
The econometric renderer SHALL expose explicit line color, line thickness, marker color, and marker radius options, with thickness and radius in screen-space units, and SHALL document their defaults and migration from the native `line`/`markers` objects and `line_kwargs`/`marker_kwargs`.

#### Scenario: Style the series
- **WHEN** a consumer supplies line and marker style options
- **THEN** the line and markers render with those styles

#### Scenario: Supply legacy native kwargs
- **WHEN** a consumer supplies `line_kwargs` or `marker_kwargs`
- **THEN** construction fails with a clear error identifying the unsupported option and pointing to the explicit styling options
