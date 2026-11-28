## ADDED Requirements

### Requirement: Collapsed Axis Labels Outside the Source Range
With an active collapse map, the chart SHALL resolve exterior custom X-axis labels by adding the first or final source segment's time shift to the plotted coordinate. Regular tick labels and supplemental date-context labels SHALL use the same conversion and the configured date/time formatting. Labels not coincident with an unshifted registered follower observation SHALL identify the exterior date as extrapolated rather than as an observed or calendar-confirmed date. The chart SHALL preserve existing label conversion inside the source range, including retained bridges, and in original-time mode.

#### Scenario: Pan past both ends of a collapsed chart
- **WHEN** visible custom ticks extend before the first or after the last collapsed source coordinate
- **THEN** the underlying timestamp advances one elapsed second per plotted second on each exterior side, rather than repeating the source endpoint
- **AND** regular and supplemental labels outside the range without a matching observation are visibly marked as extrapolated
- **AND** labels at the source endpoints and in retained bridges continue to use existing conversion without an exterior marker

#### Scenario: Label a follower observation beyond the loaded candles
- **WHEN** candles are the selected collapse source, a registered econometric follower carries observations before and after the candles, and a selected axis tick coincides with either observation's projected coordinate
- **THEN** the timestamp used to format that tick equals the observation's original timestamp to floating-point precision and is not marked as extrapolated
- **AND** neighboring ticks without coincident observations use their own converted timestamps rather than snapping to a follower point
- **AND** follower timestamps do not alter the collapse map or force additional ticks
- **AND** observation tooltips continue to display original source timestamps even when no axis tick coincides

#### Scenario: Refresh labels when the active map changes
- **WHEN** the chart refreshes after a source append or change in source selection
- **THEN** label conversion and observation matching use the current map and follower projections, not the previous source boundaries
- **WHEN** the chart restores original time
- **THEN** ticks are formatted directly from real coordinates without exterior extrapolation markers
