## ADDED Requirements

### Requirement: Real-Time Cursor Label
The `DearCyFi` plot SHALL provide a configurable X-axis cursor tag that follows the mouse's plotted X coordinate and displays the corresponding real timestamp.

#### Scenario: Move over an uncollapsed chart
- **WHEN** the cursor tag is enabled and the mouse moves over a chart whose time is not collapsed
- **THEN** the tag coordinate equals the current plotted X coordinate
- **AND** the tag text formats that coordinate as a real timestamp

#### Scenario: Move over a collapsed chart
- **WHEN** the cursor tag is enabled and the mouse moves over a chart with an active collapsed-time map
- **THEN** the tag coordinate remains at the current plotted X coordinate
- **AND** the displayed timestamp is obtained by expanding that coordinate through the active time map

#### Scenario: Restore real time
- **WHEN** a collapsed chart is restored without recreating the cursor tag
- **THEN** subsequent cursor text is formatted directly from the plotted X coordinate
- **AND** no stale collapse map is used

### Requirement: Cursor Timestamp Formatting
The cursor tag SHALL support a configurable `DateTimeSpec` or a custom callable that receives the expanded real Unix timestamp and returns the complete tag string.

#### Scenario: Use a configured format spec
- **WHEN** the cursor tag is configured with a supported `DateTimeSpec`
- **THEN** its date and time components follow that spec
- **AND** applications can select different date-only, time-only, or combined date-and-time strings

#### Scenario: Apply chart time options
- **WHEN** a built-in `DateTimeSpec` is active and the plot is configured for local or UTC time, 12-hour or 24-hour time, or ISO-8601 date formatting
- **THEN** cursor timestamps use the same configured options as DearCyFi's time-axis labels

#### Scenario: Use a custom formatter
- **WHEN** the cursor tag is configured with a callable formatter
- **THEN** the callable receives the expanded real Unix timestamp
- **AND** its returned string becomes the complete cursor tag text

#### Scenario: Reject invalid formatter output
- **WHEN** a configured custom formatter returns a non-string value
- **THEN** the cursor update fails with a clear formatting error
- **AND** the invalid value is not assigned to the axis tag

#### Scenario: Cross a retained collapse bridge
- **WHEN** the mouse moves through the synthetic interval retained between two collapsed source chunks
- **THEN** timestamp conversion uses the existing `GapCollapsedTimeMap.expand()` boundary behavior
- **AND** cursor labels remain consistent with collapsed-axis tick conversion

### Requirement: Candle-Aware Tag Color
The cursor tag SHALL indicate candle direction using configurable bullish, bearish, and no-candle background colors that default to green, red, and blue respectively. Each candle's semantic color band SHALL extend by half the median positive spacing between currently rendered candle centers on each side of its center.

#### Scenario: Cursor is over a bullish candle
- **WHEN** the cursor's plotted X coordinate falls within the horizontal semantic color band of a candle whose close is greater than or equal to its open
- **THEN** the cursor tag uses the configured bullish background color

#### Scenario: Cursor is over a bearish candle
- **WHEN** the cursor's plotted X coordinate falls within the horizontal semantic color band of a candle whose close is less than its open
- **THEN** the cursor tag uses the configured bearish background color

#### Scenario: Cursor is not over a candle
- **WHEN** no candle's semantic color band contains the cursor's plotted X coordinate
- **THEN** the cursor tag uses the configured no-candle background color
- **AND** that color is blue by default

#### Scenario: Chart has no candle series
- **WHEN** the cursor tag is active on a chart with no loaded candle series
- **THEN** the cursor tag uses the configured no-candle background color

#### Scenario: Resolve overlapping candle bounds
- **WHEN** more than one candle's semantic color band contains the cursor's plotted X coordinate
- **THEN** the candle with the nearest plotted center determines the tag color

#### Scenario: Preserve lookup after time collapse
- **WHEN** candle coordinates have been collapsed
- **THEN** candle hit lookup uses the currently rendered candle coordinates
- **AND** direction still uses the corresponding candle's original open and close values

### Requirement: Cursor Tag Visibility
The cursor tag SHALL be visible only while it can represent a valid mouse position over the plot.

#### Scenario: Enter and leave the plot
- **WHEN** the mouse enters the plot and reports a finite X coordinate
- **THEN** the cursor tag becomes visible and follows mouse movement
- **WHEN** the mouse leaves the plot
- **THEN** the cursor tag is hidden

#### Scenario: Receive an invalid coordinate
- **WHEN** the mouse callback receives a non-finite X coordinate
- **THEN** the cursor tag is hidden
- **AND** its text is not updated with an invalid timestamp

### Requirement: Built-In Readout Coordination
The `DearCyFi` plot SHALL suppress DearCyGui's built-in mouse-position text while the replacement cursor tag is enabled and SHALL leave caller-controlled mouse-position configuration unchanged when the feature is disabled.

#### Scenario: Enable replacement cursor tag
- **WHEN** a chart enables the collapsed-time cursor tag
- **THEN** DearCyGui's built-in corner mouse-position text is hidden
- **AND** only the corrected X-axis timestamp tag is presented by this feature

#### Scenario: Disable replacement cursor tag
- **WHEN** a chart disables the collapsed-time cursor tag
- **THEN** DearCyFi does not create or update the replacement tag
- **AND** DearCyFi does not override the caller's built-in mouse-position setting

### Requirement: Host Styling Access
The `DearCyFi` plot SHALL expose its managed cursor tag and semantic bullish, bearish, and no-candle colors so host applications can customize presentation without replacing time conversion or candle lookup behavior.

#### Scenario: Customize semantic tag colors
- **WHEN** a host changes one or more exposed semantic tag colors
- **THEN** subsequent cursor updates use the host-selected colors for their corresponding candle states
- **AND** continue updating tag coordinate, text, color, and interaction-driven visibility