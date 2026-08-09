---
name: data-source-widgets
description: "Use when: designing, implementing, reviewing, or testing DearCyFi demo widgets that browse or load market data from Parquet, DuckDB, databases, brokers, Tastytrade/Tastyworks, APIs, or other repositories; adapting ToyDataBrowser into a provider plugin; or normalizing OHLCV, options, and liquidity series for plotting."
argument-hint: "DearCyFi data provider or loader widget task"
---

# DearCyFi Data Source Widgets

## When To Use

Use this skill for data-loading controls embedded in the DearCyFi demo, including:

- Turning `examples/DearCyFi_Demo/toy_data_browser.py` into a reusable widget pattern.
- Adding Parquet, DuckDB, SQL, broker, Tastytrade/Tastyworks, or API-backed loaders.
- Browsing symbols, option contracts, datasets, tables, or stored series.
- Converting provider-specific records into data DearCyFi can plot.
- Reviewing widget lifecycle, asynchronous loading, credentials, validation, or tests.

This skill governs the repository development pattern. It does not dynamically load code at runtime and does not replace provider SDKs or database adapters.

## Ownership Boundary

Keep experimental provider widgets under the demo until their API is proven:

```text
examples/DearCyFi_Demo/
|-- data_widgets/
|   |-- __init__.py
|   |-- base.py
|   |-- registry.py
|   |-- toy.py
|   |-- parquet_options.py
|   |-- howell_liquidity.py
|   `-- tastytrade.py
`-- DearCyFi_Demo.py
```

Do not add broker SDKs, database credentials, or research-repository imports to `src/dearcyfi/`. The core package owns plotting behavior; the demo owns test-bed integrations. Promote only a stable, provider-neutral contract into `src/dearcyfi/` when more than one non-demo consumer needs it.

Do not import Python modules directly from another repository by modifying `sys.path`. Treat the other repository's files and databases as external data sources. If reusable source logic is needed across repositories, package it separately or implement a small adapter behind the contract below.

## Architecture

Separate each integration into three responsibilities:

```text
DearCyFiDemo host
|-- owns active widget and plot lifecycle
|-- receives load requests and status updates
`-- applies normalized results to plots

Provider widget
|-- owns DearCyGui controls and selection state
|-- builds a provider-neutral request
`-- never contains plot mutation logic

Source adapter
|-- owns files, SQL, SDK calls, and provider schemas
|-- validates and normalizes source data
`-- returns a provider-neutral result
```

Keep discovery separate from loading. A widget may first list files, tables, symbols, or contracts, then load only the selected series. Do not load a complete options chain merely because the panel was constructed.

## Minimal Widget Contract

Start with a structural contract rather than a deep base-class hierarchy. A widget should expose:

```python
class DataSourceWidget(dcg.ChildWindow):
    provider_id: str
    display_name: str

    def build_request(self) -> "DataRequest": ...
    def load(self, request: "DataRequest") -> "DataLoadResult": ...
    def dispose(self) -> None: ...
```

Constructor inputs should follow the current `ToyDataBrowser` pattern:

```python
def __init__(
    self,
    context,
    *,
    on_load_requested=None,
    on_status=None,
    **kwargs,
): ...
```

- `on_load_requested(widget, request)` asks the host to load; it does not mutate the plot.
- `on_status(text)` reports connection, discovery, loading, empty-data, and error states.
- `dispose()` releases subscriptions, clients, and tasks when applicable; it may be a no-op.
- Widget callbacks must tolerate DearCyGui's sender/app-data/user-data callback convention.

The host should keep one `active_data_widget` and route successful results through one plotting method. Avoid provider-specific `if provider == ...` branches in plotting code.

## Request And Result Shapes

A request identifies what to load without carrying provider clients or secrets:

```python
@dataclass(frozen=True)
class DataRequest:
    provider_id: str
    dataset_id: str
    start: datetime | None = None
    end: datetime | None = None
    interval: str | None = None
    filters: Mapping[str, object] = field(default_factory=dict)
```

A result must describe its plot semantics instead of pretending all data is candlestick data:

```python
@dataclass
class PlotSeries:
    name: str
    kind: Literal["candles", "line", "bars"]
    timestamps: Sequence
    values: Mapping[str, Sequence]
    metadata: Mapping[str, object] = field(default_factory=dict)

@dataclass
class DataLoadResult:
    provider_id: str
    dataset_id: str
    display_name: str
    series: Sequence[PlotSeries]
    metadata: Mapping[str, object] = field(default_factory=dict)
```

Series value rules:

- `candles`: require `open`, `high`, `low`, and `close`; `volume` is optional.
- `line`: require `value`.
- `bars`: require `value`; bar direction and baseline belong in metadata when needed.
- Multiple series may have different frequencies. Do not silently forward-fill or resample in the generic contract.
- Keep source-specific identity and provenance in metadata, not in positional tuples.

The host adapts candle series to `DearCyFi.set_data(...)`. Line and bar series should use their appropriate DearCyGui/DearCyFi plotting primitives. Do not synthesize fake OHLC values from a liquidity line merely to pass through the candle API.

## Current DearCyFi Limitation

DearCyFi currently has gap-aware candle plotting, but it does not yet have a provider-neutral econometric series type that collapses or fills time gaps for non-candle data. Treat `line` and `bars` in `PlotSeries` as the intended adapter boundary, not proof that this plotting capability already exists.

Until that series type is designed and implemented:

- Preserve original timestamps, missing observations, frequency, and provenance in loader results.
- Do not pre-collapse timestamps inside provider adapters.
- Do not convert a scalar econometric observation into artificial OHLC candles.
- Do not silently forward-fill weekly/monthly data merely to satisfy the current candle path.
- Either plot non-candle data with ordinary DearCyGui series without DearCyFi gap collapsing, or report that the selected result needs the future econometric series capability.
- Keep gap-policy metadata explicit so a later series can distinguish market closures, unavailable observations, publication cadence, and intentionally shifted future dates.

The future econometric series should be designed as a separate DearCyFi capability. Before implementing it, inspect the existing candle gap/index/locator ownership and create an OpenSpec proposal covering scalar and multi-line data, gap policy, interpolation/fill semantics, mixed frequencies, overlays, and axis/date-label behavior. Do not implement that capability as an incidental part of adding a provider widget.

## Normalization Rules

Every adapter must validate before returning:

1. Parse timestamps explicitly and state the timezone policy.
2. Sort timestamps in ascending order.
3. Detect duplicate keys before choosing a deduplication rule.
4. Convert plotted values to numeric and report invalid rows.
5. Reject an empty result after filters with an actionable status message.
6. Ensure every value array has the same length as its timestamp array.
7. Preserve source path, table/view, query parameters, symbol/contract identity, and provenance in metadata where applicable.

Do not hide source corrections in the generic adapter. Provider-specific deduplication, aggregation, resampling, and lead/lag transforms must be explicit and tested.

## Parquet Options Pattern

The inspected `Macro_Ideas` options workflow contains two example stores:

- `data/btc_met_day_aggregates.parquet`: options daily aggregates.
- `data/spy_qqq.parquet`: options minute aggregates.

Its helper reads Parquet through DuckDB and supports these source aliases:

- Symbol: `underlying_symbol`, `underlying`, `symbol`, `ticker`, or `underlying_ticker`.
- Daily time priority: `trade_date`, `window_start`, then `trade_timestamp`.
- Minute time priority: `window_start`, `trade_timestamp`, `timestamp`, `datetime`, `time`, then `trade_date`.
- Required contract fields: `expiration_date` and `strike`.
- Common optional identity: `option_type` and `option_symbol`.
- Common bar fields: `open`, `high`, `low`, `close`, `volume`, and `transactions`.

Contract identity is normally:

```text
underlying + expiration_date + strike + option_type
```

Include `option_symbol` when present. A trading date alone is not unique because many contracts trade on the same date.

For daily contract series, aggregate duplicate intraday rows explicitly:

- `open`: first
- `high`: maximum
- `low`: minimum
- `close`: last
- `volume`: sum
- `transactions`: sum

For minute series, group by the normalized analysis timestamp and use the same OHLCV aggregation rules. Sort before applying `first` and `last`.

Use DuckDB for schema discovery and filtered projection. Once columns are known, push symbol, expiry, strike, type, and date predicates into SQL and avoid `SELECT *` over large option stores. Quote paths through parameters and validate selected files; do not concatenate user-entered paths or identifiers into SQL.

The options widget should follow a staged workflow:

```text
choose Parquet file
-> inspect schema
-> choose underlying
-> choose call/put when available
-> choose expiration
-> choose strike/contract
-> choose date range and interval
-> load one normalized contract series
```

## Howell Liquidity DuckDB Pattern

The inspected `Macro_Ideas` Howell store uses:

- Database: `data/howell_liquidity.duckdb`
- Audit table: `howell_flash_raw`
- Consumer view: `howell_flash_latest`

Read the database in read-only mode. Consumer widgets should use `howell_flash_latest`, which keeps one row per parsed weekly date. Do not use the overlapping raw import table as the default chart source.

Expected strategy columns are:

- `date`
- `Global Liquidity Flash`
- `Global Liquidity Full` when present
- `Shadow Monetary Base`
- `Collateral Multiplier`
- `source_image`
- `source_publication_date`

Validate that the result is non-empty, dates parse, required columns exist, and latest-view dates are unique. Preserve provenance columns in result metadata or an associated inspection view.

Treat `Global Liquidity Flash` as a weekly line series by default. Any rate of change, z-score, forward shift, or daily forward-fill is a named transform, not part of basic loading. For information-available-as-of alignment, use backward as-of semantics. Use nearest-date matching only for an explicitly shifted research design.

## Broker And API Pattern

For Tastytrade/Tastyworks or another provider:

- Verify the current SDK name, authentication flow, response schema, rate limits, and streaming model before coding.
- Put SDK imports inside the provider adapter when the dependency is optional, and return a clear missing-dependency message.
- Read credentials from environment variables, an OS credential store, or an ignored external config. Never commit tokens, session files, account identifiers, or secrets.
- Keep account/trading operations outside a market-data widget unless the task explicitly introduces an order-entry capability with separate review.
- Add cancellation, timeout, retry, and rate-limit behavior appropriate to the verified provider API.
- Marshal completed results back through the app's established DearCyGui/async queue boundary before mutating UI state.

Do not let network or large file operations block a DearCyGui callback or render loop. Wake the viewport after status or data changes.

## Registry Pattern

Use an explicit registry first:

```python
DATA_WIDGETS = {
    ToyDataWidget.provider_id: ToyDataWidget,
    ParquetOptionsWidget.provider_id: ParquetOptionsWidget,
}
```

An explicit registry is inspectable, testable, and sufficient for a repository test bed. Do not add entry-point discovery, arbitrary dynamic imports, or plugin package loading until external packages genuinely need to register widgets.

Provider-specific dependencies must not prevent the demo from starting. Register optional widgets conditionally or let them display an unavailable state with installation guidance.

## Migrating ToyDataBrowser

Use `examples/DearCyFi_Demo/toy_data_browser.py` as the first compatibility implementation:

1. Move it under `data_widgets/toy.py` without changing selection behavior.
2. Rename provider-facing concepts from `toy_data_browser` to `active_data_widget` in the host.
3. Convert the selected profile into `DataRequest.filters` or a toy adapter input.
4. Return generated candles as `DataLoadResult` instead of calling the plot from the widget.
5. Keep the existing callback as a temporary adapter only while migrating call sites.
6. Verify initial load and symbol selection still update both demo charts.

## Implementation Procedure

When adding a provider widget:

1. Inspect the authoritative helper, schema, SDK docs, and one realistic data sample.
2. Write down dataset identity, timestamp semantics, uniqueness key, required columns, optional columns, and expected frequency.
3. Implement source discovery without loading the full dataset where practical.
4. Implement adapter validation and normalization independently of DearCyGui.
5. Build the widget controls around the adapter's discovery outputs.
6. Register the widget explicitly.
7. Connect load requests to the host's async/status/plot path.
8. Test adapter failures as well as the successful plotting path.

## Test Checklist

Adapter tests should cover:

- Missing file, database, table/view, dependency, or credential.
- Missing required columns and supported alias selection.
- Invalid and timezone-aware timestamps.
- Empty filters and empty source data.
- Duplicate contract/time keys and the documented aggregation rule.
- Stable ordering and equal-length result arrays.
- Read-only DuckDB consumption where applicable.
- One candle result and one non-candle line result.

Widget or integration checks should cover:

- Demo startup when optional provider dependencies are absent.
- Switching providers disposes the previous widget without stale callbacks.
- Discovery controls update dependent choices in order.
- Loading reports progress/errors through the status sink.
- A selected options contract plots OHLCV with its full identity.
- A weekly liquidity selection remains a line result and preserves provenance, even when the host must report that gap-aware econometric plotting is not yet supported.
- Existing toy symbol selection and initial demo load still work.

## Common Pitfalls

- Do not make every dataset look like candles; liquidity and derived indicators are line series.
- Do not claim non-candle series have DearCyFi gap collapsing until the econometric series capability exists.
- Do not put SQL, SDK calls, and plot mutation in one DearCyGui callback.
- Do not use a date alone as an options-row uniqueness key.
- Do not import the sibling research repository as an undeclared runtime dependency.
- Do not query `howell_flash_raw` by default when a deduplicated latest view exists.
- Do not discard source provenance before validation and diagnostics.
- Do not auto-load large datasets during widget construction.
- Do not add dynamic plugin discovery before an external registration use case exists.
- Do not hardcode credentials or expose secrets in status text, logs, or exceptions.