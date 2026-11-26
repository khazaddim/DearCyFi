## ADDED Requirements

### Requirement: Registered Time Series
The `DearCyFi` chart SHALL track collapsible time series by stable string identifiers and SHALL retain each registration's original timestamps and follower projection policy.

#### Scenario: Register source and follower series
- **WHEN** candles and an econometric line are registered under distinct IDs
- **THEN** the chart can list and address both registrations independently
- **AND** registering the econometric line does not modify candle timestamps or reset the gap manager

#### Scenario: Reject a duplicate identifier
- **WHEN** a consumer registers a second series with an existing ID without explicitly replacing it
- **THEN** registration fails with a clear error

### Requirement: Explicit Collapse Source Selection
The chart SHALL expose a nullable `collapse_source_id` that identifies the only registered series used to detect gaps and build the active time map.

#### Scenario: Select hourly candles as source
- **WHEN** hourly candles and weekly econometric data are registered and `collapse_source_id` identifies the candles
- **THEN** gap detection and base-step calculation use only the hourly candle source dates
- **AND** weekly dates do not alter detected gaps or the base step

#### Scenario: Select an unknown source
- **WHEN** a consumer assigns an ID that is not registered
- **THEN** the chart rejects the assignment with a clear error

#### Scenario: Collapse without a source
- **WHEN** collapse is requested while `collapse_source_id` is `None`
- **THEN** no series coordinates are changed
- **AND** the chart reports that a collapse source must be selected

### Requirement: Backward-Compatible Candle Source
The existing candle loading workflow SHALL remain usable without requiring callers to register the candle series manually.

#### Scenario: Load candles into an unconfigured chart
- **WHEN** `set_data(...)` creates or updates candles and no collapse source is selected
- **THEN** the chart registers the candle series under the stable ID `"candles"`
- **AND** sets `collapse_source_id` to `"candles"`

#### Scenario: Preserve an explicit source selection
- **WHEN** a valid non-candle source has already been selected and `set_data(...)` updates candles
- **THEN** the candle registration is updated
- **AND** the explicit `collapse_source_id` is not silently replaced

### Requirement: Source-Driven Follower Synchronization
The chart SHALL build one time map from the selected source and SHALL apply that same map to every registered follower without changing any series' original source timestamps.

#### Scenario: Collapse hourly candles with a weekly follower
- **WHEN** hourly candles are selected as the source and collapse removes overnight or weekend intervals
- **THEN** candle plot dates are collapsed from the candle source dates
- **AND** weekly econometric plot dates are projected through the same map
- **AND** the weekly series does not contribute timestamps to map construction

#### Scenario: Projection fails before mutation
- **WHEN** any registered series cannot be projected under its configured policy
- **THEN** the collapse operation fails without leaving some series collapsed and others on real time

### Requirement: Follower Projection Across Primary Gaps
The time map SHALL project arbitrary follower timestamps inside and outside the selected source range without using the current destructive clamp behavior.

#### Scenario: Project inside a removed gap using next
- **WHEN** a follower timestamp falls inside a removed primary gap and its policy is `next`
- **THEN** it maps to the collapsed coordinate of the first primary timestamp after the gap

#### Scenario: Project inside a removed gap using previous
- **WHEN** a follower timestamp falls inside a removed primary gap and its policy is `previous`
- **THEN** it maps to the collapsed coordinate of the last primary timestamp before the gap

#### Scenario: Project outside the primary range
- **WHEN** a follower timestamp is before the first or after the last primary timestamp
- **THEN** its relative time is preserved using the first or final cumulative collapse shift
- **AND** it is not clamped to an unrelated endpoint

### Requirement: Collapse Lifecycle Restoration
The chart SHALL restore all registered series to their original coordinates when the active source or map becomes invalid.

#### Scenario: Remove the active source
- **WHEN** the registered series identified by `collapse_source_id` is removed
- **THEN** all remaining series restore their original source dates
- **AND** the active map is cleared
- **AND** `collapse_source_id` becomes `None`

#### Scenario: Replace source data after collapse
- **WHEN** the active source receives a complete new dataset after a collapse
- **THEN** the old map is invalidated
- **AND** registered series are restored before a new collapse map can be built
