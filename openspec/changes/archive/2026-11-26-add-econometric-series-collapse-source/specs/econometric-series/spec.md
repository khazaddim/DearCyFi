## ADDED Requirements

### Requirement: Scalar Econometric Line Rendering
The package SHALL provide a reusable econometric series that renders one numeric value per timestamp with a native DearCyGui line element and optional native observation markers.

#### Scenario: Render a weekly scalar series
- **WHEN** a consumer creates an econometric series with equal-length timestamp and numeric value arrays
- **THEN** the series renders a line at those coordinates
- **AND** the consumer may enable visible markers without creating a second data model

#### Scenario: Preserve missing observations
- **WHEN** the value array contains a NaN observation
- **THEN** the default line rendering breaks at that observation
- **AND** the series does not silently interpolate or forward-fill the missing value

### Requirement: Econometric Data Validation and Updates
The econometric series SHALL validate its scalar data and SHALL support replacing its complete dataset without leaving rendering or interaction state partially updated.

#### Scenario: Reject mismatched arrays
- **WHEN** timestamp and value arrays have different lengths
- **THEN** construction or update fails with a clear `ValueError`

#### Scenario: Replace all observations
- **WHEN** a consumer performs a complete data update with valid timestamps, values, and optional metadata
- **THEN** the native rendering elements and tooltip interaction coordinates reflect the new dataset
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
