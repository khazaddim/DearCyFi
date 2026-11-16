## ADDED Requirements

### Requirement: Incremental Source Timeline Extension
When the selected collapse source appends an observation, the chart SHALL extend its gap metadata and applicable time map using the cached source cadence and latest timestamp pair, without rediscovering historical gaps or recalculating the median in steady state.

#### Scenario: Extend a normal source interval
- **WHEN** the chart is collapsed and the appended source timestamp continues the regular interval within tolerance
- **THEN** the final retained segment extends without a new removed gap
- **AND** the new observation uses the existing cumulative shift without additional gap removal
- **AND** earlier source plot coordinates remain unchanged

#### Scenario: Discover a new source gap
- **WHEN** the chart is collapsed and the appended source timestamp is more than one regular interval after the previous source endpoint outside tolerance
- **THEN** a new gap record and retained segment are added
- **AND** cumulative removed time increases by the elapsed interval minus the cached regular interval
- **AND** the appended observation is plotted one cached regular interval after the previous source endpoint's plotted coordinate
- **AND** earlier gap records and source plot coordinates remain unchanged

#### Scenario: Verify incremental work
- **WHEN** appending after initial streaming state has been established
- **THEN** source gap detection and map-tail maintenance do not scan historical source timestamps or invoke full gap builders
- **AND** only newly encountered date-boundary anchors and segment lookup entries are added
- **AND** this bound excludes data-buffer copying, affected follower work, and renderer rebuilding

### Requirement: Incremental Follower Synchronization
A collapsed chart SHALL update affected follower coordinates after a source map extension using the same map and existing follower policies, without modifying follower source timestamps or values.

#### Scenario: Reproject liquidity inside and beyond a new gap
- **WHEN** a newly appended candle reveals a removed interval containing liquidity observations and additional observations beyond the new source endpoint
- **THEN** affected observations are reprojected under their registered `next` or `previous` policy
- **AND** observations beyond the new endpoint use the updated final cumulative shift
- **AND** follower coordinates at or before the previous source endpoint are reused unchanged

#### Scenario: Preserve unaffected followers on normal continuation
- **WHEN** the source extends without adding a removed gap
- **THEN** existing follower projections remain unchanged

#### Scenario: Append to a follower
- **WHEN** a non-source series appends while the chart is collapsed
- **THEN** its new timestamp is projected through the active source map
- **AND** the source map, selected source, and other series coordinates are unchanged
- **AND** this rule also applies to candles when a different series is the selected source

### Requirement: Streaming Collapse Lifecycle Consistency
Incremental source changes SHALL retain sufficient timeline state in both collapsed and uncollapsed modes to keep collapse, restore, date labels, cursor mapping, and registered tools consistent with accepted source timestamps and cadence.

#### Scenario: Stream while uncollapsed then collapse
- **WHEN** normal and gapped source observations append on an uncollapsed chart and the user subsequently collapses time
- **THEN** series were displayed at real source timestamps before collapse
- **AND** appending did not collapse any displayed interval or reproject followers or tools for gap removal
- **AND** collapse applies the same cached cadence and accepted gap history used by the streaming path

#### Scenario: Refresh tools across an appended gap
- **WHEN** source append extends the active map
- **THEN** registered tools refresh against that map using unchanged canonical source-time anchors and Y values
- **AND** axis boundary anchors and cursor expansion reflect the extended timeline

#### Scenario: Restore after streaming
- **WHEN** a chart is restored after collapsed streaming updates
- **THEN** every registered series displays its complete updated source timestamps
- **AND** tools display their preserved canonical source coordinates

#### Scenario: Update values without timeline changes
- **WHEN** only the latest observation values are modified
- **THEN** no gap detection, map reconstruction, or follower-coordinate reprojection is performed
