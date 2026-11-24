## ADDED Requirements

### Requirement: Independent Econometric Display Shifts
The chart SHALL support separate configurable collapsed and uncollapsed horizontal display shifts for an econometric series, without changing its observation timestamps or values.

#### Scenario: Shift in either direction
- **WHEN** a positive or negative shift is configured
- **THEN** the complete visible series moves respectively forward or backward on the active plot axis
- **AND** line, markers, and tooltip hit regions move together
- **AND** observation timestamps and values remain unchanged

#### Scenario: Zero shift
- **WHEN** both shifts are zero or the feature is not configured
- **THEN** the series retains existing projection and rendering behavior

#### Scenario: Switch time modes
- **WHEN** the chart switches between collapsed and uncollapsed time
- **THEN** it applies the configured shift for that mode exactly once
- **AND** changing one setting does not overwrite the other

### Requirement: Shift Units and Initial Conversion
The feature SHALL accept shifts in collapsed source-candle intervals and approximate calendar weeks, and SHALL initialize an independently editable uncollapsed shift using the average historical compression of the candle source.

#### Scenario: Approximate weeks
- **WHEN** a user configures a shift in approximate calendar weeks
- **THEN** its collapsed-axis distance uses the source's observed historical compression
- **AND** the interface describes the result as approximate rather than an exact future calendar mapping

#### Scenario: Preserve an independent override
- **WHEN** a user changes the uncollapsed shift after initialization
- **THEN** the new value remains in effect independently of the collapsed shift
- **AND** streaming or toggling collapse does not silently replace it

#### Scenario: Insufficient conversion history
- **WHEN** the source history cannot establish the data required for a requested conversion
- **THEN** the operation reports that the conversion is unavailable
- **AND** it does not silently invent an interval or a compression ratio

### Requirement: Shift Lifecycle Coordination
Display shifts SHALL be coordinated with chart projection and incremental streaming so each series remains aligned with its active mode without double application.

#### Scenario: Stream while collapsed
- **WHEN** source candles append or reveal a gap and an econometric follower has a configured shift
- **THEN** affected base projections are updated using the source map
- **AND** the display shift is applied once to the resulting coordinates
- **AND** original follower timestamps remain unchanged

#### Scenario: Restore and recollapse
- **WHEN** the chart is restored and subsequently collapsed again
- **THEN** the series uses the respective uncollapsed and collapsed shift settings
- **AND** repeated transitions do not accumulate offsets

#### Scenario: Change or reload source
- **WHEN** a source change or reload would make a stored conversion ambiguous
- **THEN** the chart does not silently reinterpret the setting against a different cadence
- **AND** it communicates any required reconfiguration

### Requirement: Historical Compression Uncertainty Ranges
The feature SHALL display an approximate horizontal timing range for eligible shifted econometric observations beyond the last candle, using a documented estimate derived from the historical distribution of time removed by gap collapse.

#### Scenario: Future shifted observations
- **WHEN** a shifted observation lies beyond the last plotted candle and the estimate has sufficient historical support
- **THEN** its horizontal range is rendered as part of the same econometric series
- **AND** the range is identified as an approximation based on historical gap compression
- **AND** it is not presented as a confidence interval or as uncertainty in the signal's predictive accuracy

#### Scenario: Insufficient evidence
- **WHEN** historical data is insufficient for the selected uncertainty estimator
- **THEN** the range is reported as unavailable
- **AND** the chart does not present unavailable uncertainty as a zero-width estimate

#### Scenario: Hide a shifted series
- **WHEN** the econometric series is hidden using its legend
- **THEN** its horizontal ranges and interaction targets are hidden with the rest of the series

### Requirement: Honest Future Time Presentation
The chart SHALL distinguish original observation timestamps from approximate shifted positions and SHALL NOT present an unknown future calendar date as exact.

#### Scenario: Hover a shifted observation
- **WHEN** a user hovers a shifted observation
- **THEN** its tooltip identifies the original observation timestamp and value
- **AND** any displayed shifted date or timing range is identified as approximate

#### Scenario: Axis or cursor beyond the source endpoint
- **WHEN** a shifted observation extends beyond the source timeline and no exact future market mapping is available
- **THEN** axis and cursor presentation either clearly identifies dates as approximate or reports them as unavailable
- **AND** it does not present the clamped last source date as the exact date of that future position
