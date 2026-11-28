## MODIFIED Requirements

### Requirement: Real-Time Cursor Label
The `DearCyFi` plot SHALL provide a configurable X-axis cursor tag that follows the mouse's plotted X coordinate and displays the corresponding real timestamp.

#### Scenario: Move over an uncollapsed chart
- **WHEN** the cursor tag is enabled and the mouse moves over a chart whose time is not collapsed
- **THEN** the tag coordinate equals the current plotted X coordinate
- **AND** the tag text formats that coordinate as a real timestamp

#### Scenario: Move over a collapsed chart
- **WHEN** the cursor tag is enabled and the mouse moves over a chart with an active collapsed-time map
- **THEN** the tag coordinate remains at the current plotted X coordinate
- **AND** the displayed timestamp uses the same conversion as the custom X-axis labels

#### Scenario: Move outside the collapsed source range
- **WHEN** the mouse's plotted X coordinate is before or after the collapsed source range
- **THEN** the tag timestamp advances with the axis rather than clamping to the nearest source endpoint
- **AND** built-in formatting uses the configured date/time format without adding an exterior marker
- **AND** a custom formatter receives the resolved timestamp and returns the complete tag string

#### Scenario: Restore real time
- **WHEN** a collapsed chart is restored without recreating the cursor tag
- **THEN** subsequent cursor text is formatted directly from the plotted X coordinate
- **AND** no stale collapse map is used
