## ADDED Requirements

### Requirement: Provider-Neutral Incremental Operations
The chart SHALL expose separate synchronous check-latest-interval, append-one, and modify-latest operations for mutable registered time series, with candle convenience methods and initial support for candle and scalar econometric schemas, without requiring any provider SDK.

#### Scenario: Use candle convenience methods
- **WHEN** a caller uses `check_last_candle(timestamp)`, `append_candle(...)`, or `update_last_candle(...)`
- **THEN** the chart delegates to the corresponding generic operation on the `"candles"` registration
- **AND** the core API accepts normalized source data rather than broker event objects

#### Scenario: Preserve projection-only registrations
- **WHEN** a registered series implements projection but not mutation
- **THEN** it continues to participate in collapse and restore
- **AND** a mutation request fails explicitly without modifying it

#### Scenario: Stream a scalar series
- **WHEN** a scalar econometric series has established cadence
- **THEN** generic operations can check its last interval, append one timestamp/value observation, and replace its latest value independently of candles

### Requirement: Stable Median Cadence
Streaming mutation SHALL use a finite positive regular interval inferred once from the median adjacent spacing of at least two finite strictly increasing loaded source timestamps, in floating-point seconds, and SHALL retain that interval until complete data replacement.

#### Scenario: Keep daily cadence through streaming gaps
- **WHEN** loaded history establishes a one-day interval and new observations arrive two days apart
- **THEN** the regular interval remains one day
- **AND** append does not recalculate the historical median

#### Scenario: Reject insufficient cadence information
- **WHEN** append or latest modification is requested for empty, singleton, non-finite, or non-increasing history
- **THEN** it fails with an explicit cadence error without assuming a default interval

#### Scenario: Replace loaded data
- **WHEN** the complete dataset is replaced
- **THEN** cached streaming cadence is invalidated and subsequent streaming uses the replacement history
- **AND** the existing full-replacement restore/reset lifecycle is retained

### Requirement: Latest Interval Occupancy Lookup
`check_last_sample(series_id, timestamp)` and its candle convenience method SHALL be read-only and return `(matches, stored_latest_source_timestamp)`, matching the half-open latest interval with the shared bounded numerical boundary tolerance, rather than requiring exact start-time equality.

#### Scenario: Match an event inside a forming candle
- **GIVEN** five-minute cadence and a latest candle starting at 10:00
- **WHEN** lookup receives 10:03
- **THEN** it returns `(True, timestamp_of_10_00)`

#### Scenario: Respect the next interval boundary
- **GIVEN** five-minute cadence and a latest candle starting at 10:00
- **WHEN** lookup receives 10:05 or a timestamp within the shared tolerance of 10:05
- **THEN** it returns `(False, timestamp_of_10_00)`
- **AND** a timestamp within tolerance of 10:00 matches that existing candle

#### Scenario: Report a miss or an empty series
- **WHEN** a valid query is outside the latest interval
- **THEN** lookup returns `False` together with the stored latest source timestamp
- **AND** lookup of an existing empty series returns `(False, None)`

#### Scenario: Reject invalid lookup input
- **WHEN** lookup receives a non-finite timestamp, an unknown series ID, or non-empty history with no inferable cadence
- **THEN** it raises a clear error without mutating chart state

### Requirement: Shared Numerical Timestamp Tolerance
Lookup and append validation SHALL share a tolerance in seconds equal to `max(min(0.001, h * 1e-6), 8 * max(ulp(s), ulp(t), ulp(s + h)))`, where `h` is the cached interval, `s` the last source timestamp, and `t` the query or proposed append timestamp; comparisons SHALL fail explicitly if tolerance is at least half the interval.

#### Scenario: Handle realistic timestamp representation
- **WHEN** epoch-sized timestamps differ at a candle boundary only by representational error within tolerance
- **THEN** lookup and append classify the boundary consistently
- **AND** neither uses an epoch-relative tolerance that admits materially sub-interval arrivals

#### Scenario: Reject indistinguishable intervals
- **WHEN** timestamp precision makes the computed tolerance at least half the interval
- **THEN** the operation fails with a precision error instead of ambiguously matching adjacent intervals

### Requirement: Append One Observation
Append SHALL add exactly one validated observation with its real timestamp, without implicitly updating or inserting historical observations. Using the shared tolerance, append SHALL reject spacing below the cached median interval in either chart state, append without additional gap removal at equal spacing, and remove excess spacing above the median only for a selected-source append on a collapsed chart. An uncollapsed chart SHALL display every accepted append at its real source timestamp.

#### Scenario: Reject a four-hour arrival on daily data
- **GIVEN** one-day median spacing
- **WHEN** a caller attempts to append a distinct observation four hours after the last start
- **THEN** append raises a validation error
- **AND** no series, map, or presentation state changes

#### Scenario: Accept normal spacing
- **WHEN** a proposed timestamp is one regular interval after the latest start within tolerance
- **THEN** one observation is appended with its accepted real source timestamp
- **AND** its actual elapsed spacing is retained without recording a material gap
- **AND** a collapsed chart applies only the existing cumulative shift, with no additional time removed

#### Scenario: Accept an irregular longer gap
- **GIVEN** one-day median spacing
- **WHEN** a candle arrives two days or two and a half days after the latest start
- **THEN** append accepts it and records the actual interval as a gap
- **AND** if the candles are the selected source and the chart is collapsed, the new candle is plotted one day after the preceding candle's plotted start
- **AND** only the actual elapsed interval minus one day is removed

#### Scenario: Append without collapse
- **GIVEN** an uncollapsed chart with one-day median spacing
- **WHEN** a candle arrives one day, two days, or two and a half days after the latest start
- **THEN** it is appended at its real source timestamp without removing any displayed time
- **AND** no followers or tools are reprojected due to gap removal
- **AND** an arrival only four hours after the latest start is still rejected

#### Scenario: Reject duplicate and earlier observations
- **WHEN** append receives the latest start timestamp or any earlier timestamp
- **THEN** it fails explicitly without modifying the existing observation

### Requirement: Modify Only Latest Values
Latest modification SHALL replace only supplied latest values, preserve all timestamps and observation counts, reject empty updates, and validate the resulting complete observation before mutation.

#### Scenario: Revise a forming candle
- **WHEN** a caller supplies any valid subset of open, high, low, close, and volume
- **THEN** only those latest candle fields are replaced
- **AND** omitted fields and earlier candles remain unchanged
- **AND** supplied volume replaces rather than increments stored volume
- **AND** the time map and cached cadence are unchanged

#### Scenario: Reject an invalid resulting candle
- **WHEN** the proposed complete candle contains non-finite OHLC, negative or non-finite volume, or inconsistent OHLC bounds
- **THEN** modification fails without partial field changes

### Requirement: Coherent Streaming Publication
Streaming operations SHALL validate and prepare proposed data and projection changes before publication, surface failures explicitly, and preserve a coherent prior chart state if preparation or application fails.

#### Scenario: Prepare or apply a failing follower update
- **WHEN** source append encounters a follower projection or application failure
- **THEN** the operation raises an error and retains or restores the previous coherent source, follower, map, and tool state
- **AND** it does not silently uncollapse the chart

#### Scenario: Preserve chart presentation
- **WHEN** a streaming mutation succeeds
- **THEN** chart and series arrays, indexes, annotations, volume, and tooltip source data remain consistent
- **AND** series identity, styles, legend visibility, assigned axes, viewport limits, and collapse selection/state are preserved
- **AND** the viewport is notified to render the change without automatic fitting or scrolling

### Requirement: Serialized Provider Consumption
Documentation SHALL show a provider-neutral check/update-or-append consumer on a serialized host chart-update boundary, with no suspension between check and mutation, and SHALL explain that a lookup miss does not guarantee append validity.

#### Scenario: Consume async candle events
- **WHEN** an external async adapter delivers a normalized candle event after initial bulk loading
- **THEN** the host can dispatch one synchronous callback that checks interval occupancy and either updates the latest candle or attempts append
- **AND** provider network work remains outside chart mutation
- **AND** validation errors are explicitly reported rather than silently dropping events
- **AND** initial collection timeouts, broker SDK setup, and tick aggregation remain outside the core streaming contract

### Requirement: Synthetic Streaming Demo
The demo SHALL provide controls for starting and stopping a deterministic synthetic candle stream over already loaded candle data, with a configurable update period and an option to introduce a gap in the next appended candle. The demo host SHALL own the stream lifecycle and serialize chart mutations, without adding a provider SDK or a background-task framework to the core.

#### Scenario: Visually inspect revisions and new candles
- **GIVEN** synthetic candle history with an established cadence is loaded
- **WHEN** the user starts streaming
- **THEN** the stream repeatedly emits valid OHLCV revisions of the latest candle and appends subsequent candles using real interval-start timestamps
- **AND** the DearCyFi chart uses its public streaming operations while the original-time comparison plot reflects the same observations at real timestamps
- **AND** updates do not automatically fit or scroll either plot

#### Scenario: Inspect a streamed gap
- **WHEN** the user requests a gap for the next new candle while streaming
- **THEN** the next appended timestamp is more than one established candle interval after the latest timestamp
- **AND** the user can inspect the resulting candle and existing follower behavior in collapsed and uncollapsed modes

#### Scenario: Stop, reload, or shut down
- **WHEN** the user stops streaming, reloads candle data, selects a different toy symbol, or closes the demo
- **THEN** the previous producer stops before it can apply further events to the replacement data or closed demo
- **AND** starting again uses the current loaded series without creating multiple concurrent producers
- **AND** the demo reports running, stopped, and failure status

#### Scenario: Reject an unavailable or failed stream
- **WHEN** streaming is started without enough loaded history to establish cadence, or a generated update fails
- **THEN** the demo reports an actionable error and does not continue silently applying events
