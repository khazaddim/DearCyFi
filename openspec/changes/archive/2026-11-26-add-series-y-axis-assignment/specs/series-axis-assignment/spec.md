## ADDED Requirements

### Requirement: Configurable Candle Y Axis

The candle renderer SHALL accept an explicit DearCyGui Y-axis selection from `Y1`, `Y2`, or `Y3`, SHALL default to `Y1`, and SHALL retain `X1` as its time axis.

#### Scenario: Use the backward-compatible candle default
- **WHEN** a consumer creates or loads candle data without selecting a Y axis
- **THEN** the candle drawing composite and its volume series use `(X1, Y1)`

#### Scenario: Assign candles to another scale
- **WHEN** a consumer selects `Y2` or `Y3` for candle data
- **THEN** the candle drawing composite and its volume series use `X1` and the selected Y axis
- **AND** replacing candle data does not split those elements across different axes

#### Scenario: Change the candle scale during replacement
- **WHEN** a consumer reloads an existing `DearCyFi` candle series with a different valid Y axis
- **THEN** the existing candle drawing composite and volume series move together to the newly selected axis

### Requirement: Configurable Econometric Y Axis

The econometric renderer SHALL accept an explicit DearCyGui Y-axis selection from `Y1`, `Y2`, or `Y3`, SHALL default to `Y1`, and SHALL retain `X1` as its time axis.

#### Scenario: Render econometric data on an independent scale
- **WHEN** a consumer creates an econometric series on `Y3` with markers and tooltips enabled
- **THEN** its line, markers, and tooltip interaction coordinates all use `(X1, Y3)`
- **AND** complete data and collapsed-date updates retain that axis assignment

#### Scenario: Use the backward-compatible econometric default
- **WHEN** a consumer creates an econometric series without selecting a Y axis
- **THEN** all of its rendering and interaction elements use `(X1, Y1)`

### Requirement: Axis Assignment Validation

Series axis assignment SHALL reject unsupported or ambiguous configuration rather than creating a partially aligned composite.

#### Scenario: Reject a non-Y axis
- **WHEN** a consumer supplies an X axis or another unsupported value as `y_axis`
- **THEN** construction or replacement fails with a clear `ValueError`

#### Scenario: Reject a conflicting extension option
- **WHEN** renderer extension kwargs contain an `axes` value in addition to the explicit `y_axis`
- **THEN** construction fails with a clear error identifying the conflict

### Requirement: Independently Scaled Demo Series

The demo SHALL display candle prices and toy econometric observations on separate, labeled, independently fitted Y axes.

#### Scenario: Load the combined demo chart
- **WHEN** the demo loads candles and the toy weekly econometric series
- **THEN** candles render on `Y1`
- **AND** econometric observations render on enabled `Y3`
- **AND** each visible Y axis is fitted to its assigned data range

#### Scenario: Collapse and restore the combined chart
- **WHEN** the user collapses and restores time gaps in the combined demo chart
- **THEN** both series retain their assigned Y axes and readable independent scales
- **AND** only their plotted X coordinates change