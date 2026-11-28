## ADDED Requirements

### Requirement: Versioned Portable Chart Snapshot

DearCyFi SHALL provide programmatic capture and restore of a detached, JSON-compatible chart state and file save and open operations for that state. The UTF-8 document SHALL identify the format and version and represent one chart with ordered, explicitly typed records for source series, indicator definitions, and drawings. A snapshot SHALL open without accessing any provider, querying a database, regenerating source data, or restoring a live subscription.

#### Scenario: Open a snapshot on a fresh chart
- **WHEN** a chart containing candles, econometric observations, an SMA, and a range box is saved and opened in a fresh DearCyFi chart without the original provider
- **THEN** the destination contains the saved data and independently usable indicator and drawing
- **AND** the built-in loaders do not need the demo or a provider connection

#### Scenario: Capture one chart revision
- **WHEN** a snapshot is captured while the chart is streaming and the source is subsequently updated
- **THEN** the detached snapshot retains the captured revision, including the forming candle as of capture
- **AND** its candles, dependent configuration, and presentation describe the same revision

### Requirement: Preserve Built-In Source Data

The snapshot SHALL embed the chart's candle timestamps and OHLC values, supplied index and volume, registered built-in econometric scalar series, and any chart-owned horizontal bar overlay. It SHALL preserve collection order, each time series' source timestamp/value alignment and gap policy, and missing observations in supported columns. Source dates SHALL be UTC Unix seconds; projected sample dates SHALL NOT substitute for source dates.

#### Scenario: Preserve an independent cadence and missing sample
- **WHEN** a registered weekly econometric series includes an observation missing between two finite values on a daily-candle chart
- **THEN** reopening restores the original weekly dates and values with a break at the missing observation
- **AND** the JSON represents the missing value as `null`, without filling, resampling, or dropping it

#### Scenario: Preserve bars without reloading them
- **WHEN** candles with volume and a chart-owned horizontal bar overlay are saved
- **THEN** reopening reproduces the saved volume samples and the actual horizontal bar lengths, price levels, and display mode

### Requirement: Restore Extensible Indicators and Drawings

DearCyFi SHALL restore supported indicators and drawings using stable instance IDs and kind-specific definitions, preserving dependencies, order, axis assignments, and supported per-instance style and options. Version 1 SHALL support SMA and range boxes. It SHALL recompute indicator outputs and reconstruct interactive drawings from canonical geometry, not deserialize GUI objects or cached results. The schema SHALL accommodate future indicator parameters and drawing geometry through explicit kind handlers without imposing SMA or rectangle fields on other kinds.

#### Scenario: Round trip independently configured indicators
- **WHEN** a snapshot contains two SMA instances with different periods, input fields, colors, or axes
- **THEN** both reopen with their original IDs and their own settings and computed values, including warm-up gaps
- **AND** each remains independently editable, removable, and synchronized with later candle changes

#### Scenario: Restore an interactive box on collapsed time
- **WHEN** a range box is saved after it has been moved or resized on a collapsed chart
- **THEN** reopening restores its source anchors, Y axis, configurable constraints, and presentation
- **AND** its handles remain interactive and toggling collapse does not change those source anchors

### Requirement: Restore Chart View and Time State

DearCyFi SHALL restore supported X1 and Y1/Y2/Y3 axis settings and initialized visible ranges, per-series axes, chart and item legend configuration, and supported chart date presentation. Reconstructed plot items SHALL start shown and enabled; the snapshot SHALL NOT store per-item hide/show state. It SHALL restore the selected collapse source, the next-collapse method preference, and the active time state; a collapsed snapshot SHALL recreate the active gap mapping, including incrementally extended gaps, from validated saved gap definitions. An unset range SHALL use normal initialization for that axis rather than overwrite initialized saved ranges.

#### Scenario: Restore a zoomed, collapsed chart after streaming
- **WHEN** the saved chart is zoomed into a collapsed view after a gapped append, with an X1 range edge inside a retained gap
- **THEN** reopening displays the same active gap layout, axis ranges and series placements within chart numeric precision
- **AND** the collapse checkmark and source label reflect the restored state
- **AND** disabling collapse returns series to their original timestamps

#### Scenario: Reopen saved series visible
- **WHEN** one saved item was disabled by clicking its legend entry and a second item was fully hidden
- **THEN** both reopen shown and enabled
- **AND** items with legend entries can still be toggled from the legend

### Requirement: Validate Snapshots Before Replacement

DearCyFi SHALL validate the versioned schema, supported kinds, data shapes and ranges, and cross-references before applying a snapshot. It SHALL reject malformed or ambiguous JSON, numeric inputs that cannot be represented as finite numbers, and documents above the 64 MiB UTF-8 limit. It SHALL NOT execute code or use provider or filesystem references from a document. Unsupported source data or record kinds SHALL be reported rather than silently dropped during capture or open.

#### Scenario: Reject invalid or unsupported content
- **WHEN** a file contains a future document version, an unknown record kind, unequal sample column lengths, invalid geometry, or a dangling collapse source
- **THEN** Open identifies the problem and leaves the current chart unchanged
- **AND** no partial result is displayed

#### Scenario: Reject a chart-owned item without a serializer
- **WHEN** a chart contains a registered series, indicator, or drawing without a supported snapshot representation
- **THEN** Save identifies the unsupported item and does not create an incomplete snapshot

### Requirement: Save and Open Without Partial Changes

An accepted Open SHALL replace the supported contents of the same chart, not merge or create a sibling, and SHALL leave unrelated host-owned UI outside the replacement. Failed Open SHALL leave the previous chart contents, view, registrations, and managed controls usable, including after a failure during publication. A successful Open SHALL prevent stale demo producers from mutating the restored chart and SHALL rebind demo controls to the replacement instances. Save SHALL publish a complete file atomically and SHALL require explicit permission to overwrite an existing destination.

#### Scenario: Replace chart contents, including with an empty snapshot
- **WHEN** an accepted snapshot omits an indicator or drawing present on the current chart, or contains no items
- **THEN** the omitted contents are removed with their owned UI and registrations
- **AND** the chart object and other charts remain in place

#### Scenario: A late open failure preserves the current chart
- **WHEN** chart construction, projection, or publication fails after a valid file has been read
- **THEN** the original chart and its controls remain coherent
- **AND** the original stream, if running, is not replaced or stopped by that failed operation

#### Scenario: A write fails while replacing a snapshot
- **WHEN** the user has authorized an overwrite but writing or publishing the new file fails
- **THEN** the old file remains intact and the operation reports the error

### Requirement: Chart Context Menu Save and Open

DearCyFi SHALL offer **Save Chart...** and **Open Chart...** in its existing right-click plot menu without removing existing controls. The actions SHALL launch a chart-owned path popup with an action, Cancel, and actionable error feedback. The popup SHALL confirm overwriting an existing file or replacing the selected chart before committing. File I/O SHALL NOT block chart rendering; repeated submissions SHALL NOT race to update the same chart or popup.

#### Scenario: Save and reopen from the right-click menu
- **WHEN** the user saves a snapshot from the chart menu, changes the chart, then opens that file and confirms replacement
- **THEN** the chart whose menu the user opened returns to the saved state
- **AND** the native menu and DearCyFi's collapse and diagnostic controls still work

#### Scenario: Cancel or correct an operation
- **WHEN** the user cancels a popup or declines overwrite or replacement
- **THEN** neither the chart nor the destination file changes
- **WHEN** a selected path cannot be read or written
- **THEN** the popup reports the error and lets the user correct the path or cancel
