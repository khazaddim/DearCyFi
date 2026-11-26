## ADDED Requirements

### Requirement: Provider-Neutral Demo Data Contract
The demo SHALL define provider-neutral request and result types that describe data-source identity and plot semantics without giving provider widgets direct access to plot mutation.

#### Scenario: Return a line-series result
- **WHEN** a demo adapter loads toy econometric data
- **THEN** it returns a normalized result containing a line series with timestamps, one value array, label, and source metadata
- **AND** it does not synthesize OHLC fields for the scalar data

### Requirement: Explicit Demo Provider Registry
The demo SHALL use an explicit registry for available data-source widgets rather than dynamic module discovery.

#### Scenario: Resolve the toy econometric provider
- **WHEN** the host requests the registered toy econometric provider ID
- **THEN** the registry returns the corresponding widget or factory
- **AND** an unknown provider ID produces a clear error

### Requirement: Toy Econometric Provider Widget
The demo SHALL provide a toy provider widget that requests deterministic fake econometric data through a host callback and does not mutate chart series directly.

#### Scenario: Load deterministic weekly data
- **WHEN** a user selects a toy econometric dataset and requests a load with the same configuration and seed
- **THEN** the adapter returns identical sorted weekly timestamps and values
- **AND** every value array has the same length as its timestamps

#### Scenario: Widget requests a load
- **WHEN** the user activates the toy widget's load command
- **THEN** the widget builds a provider-neutral request and invokes the host callback
- **AND** the host is responsible for adapting the successful result to a plot series

### Requirement: Demo Collapse Integration
The demo host SHALL provide a reproducible scenario in which hourly candles are the selected collapse source and a weekly toy econometric series is a registered follower.

#### Scenario: Collapse the combined chart
- **WHEN** the demo has loaded hourly candle data with gaps and weekly toy econometric data and the user invokes collapse
- **THEN** the chart reports or displays `"candles"` as the selected collapse source
- **AND** the candle and econometric series synchronize through the candle-derived map
- **AND** the econometric series retains original dates for tooltips

#### Scenario: Reload the econometric follower
- **WHEN** the weekly toy dataset is replaced while the chart is not collapsed
- **THEN** the follower registration updates without changing `collapse_source_id`
- **AND** the candle-derived gap configuration remains authoritative
