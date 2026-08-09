## Context

`DearCyFi` currently stores one candle dataset in chart-level arrays, resets one `GapCollapseManager` from those dates, and updates only `PlotCandleStick` when collapse is requested. `PlotCandleStick` preserves `source_dates` for labels and tooltips, but arbitrary DearCyGui line or scatter series are not registered with the chart or synchronized with the gap map.

Issue #9 calls for a line-oriented series suitable for sources such as FRED and later for irregular event or active-position data. This change addresses the low-frequency scalar econometric case first. A typical validation chart contains hourly candles with overnight and weekend gaps plus a weekly econometric series. The hourly candles define the chart timeline; the weekly series follows it and must not influence gap detection.

## Goals / Non-Goals

### Goals

- Plot one scalar econometric value per timestamp using native DearCyGui plot elements.
- Show a basic tooltip containing the series label, original observation date, and formatted value.
- Keep real/source timestamps distinct from transformed plot coordinates.
- Let the chart explicitly select one registered series as the source used to detect and collapse gaps.
- Synchronize follower series through the selected source's map without allowing followers to alter it.
- Provide deterministic demo data and a provider-style widget for manual and automated validation.
- Preserve the current candle-only public workflow.

### Non-Goals

- High-frequency active-position or event-stream optimization.
- Streaming subscriptions, polling, or broker/API authentication.
- Rich FRED metadata, revision/vintage inspection, or configurable tooltip layouts.
- Resampling, interpolation, forward-fill, or frequency conversion.
- Multiple independent collapse maps on different X axes.
- Time-based bar, area, band, or multi-value econometric renderers.
- Automatic collapse-source selection based on sampling frequency.

## Decisions

### Decision: Compose Native Plot Elements

Add a project-owned `PlotEconometricSeries` controller/composite that owns:

- immutable-in-meaning `source_dates` used for tooltips and restoration;
- mutable `plot_dates` used as DearCyGui X coordinates;
- one numeric value array;
- a native `dcg.PlotLine`;
- an optional native `dcg.PlotScatter` for visible observations; and
- an interaction layer for basic per-observation tooltips.

The class will use `PlotCandleStick` as an API and interaction reference, but it will not subclass the candle class or manually draw every line segment. Initial tooltip hit regions may use fixed-pixel-size `DrawInvisibleButton` items because the intended FRED-style weekly/monthly datasets are small. The implementation must keep the rendering and interaction layers synchronized when plot dates change.

`PlotLine.skip_nan` will remain false by default so missing values break the line instead of implying interpolation.

### Decision: Define a Small Synchronization Contract

Each chart-managed time series must expose the equivalent of:

```python
class CollapsibleSeries(Protocol):
    @property
    def source_dates(self) -> np.ndarray: ...

    def set_plot_dates(self, dates: np.ndarray) -> None: ...

    def restore_source_dates(self) -> None: ...
```

The concrete classes may expose additional update APIs. Collapse coordination depends only on original timestamps and the ability to update rendered X coordinates.

### Decision: Make Collapse Ownership Explicit at Chart Level

`DearCyFi` will own a registry keyed by stable string IDs and a nullable `collapse_source_id`:

```python
self._time_series: dict[str, TimeSeriesRegistration] = {}
self._collapse_source_id: str | None = None
```

A registration stores the series object and its follower gap-projection policy. Public chart operations will support registering, unregistering, listing, and selecting the collapse source. Setting `collapse_source_id` to an unknown ID must fail clearly.

`set_data(...)` will register the candle series under the stable ID `"candles"`. It will select `"candles"` only when no collapse source is currently selected, preserving existing candle-only behavior without overriding an explicit user selection.

No series is selected automatically by comparing frequencies. Sampling frequency is not a reliable measure of whether a series represents the chart's tradable timeline.

### Decision: Separate Map Construction from Follower Projection

Collapsing proceeds atomically:

1. Restore or read original timestamps from all registrations.
2. Build one `GapCollapsedTimeMap` from the selected source's `source_dates`.
3. Project the source timestamps through that map.
4. Project every follower's `source_dates` through the same map.
5. Update each series' plotted dates only after all projections succeed.
6. Keep original timestamps unchanged for restoration and tooltip formatting.

Follower timestamps must never be appended to the source dates or used to recalculate the source median interval.

### Decision: Add Explicit In-Gap Projection

The existing `GapCollapsedTimeMap.collapse()` is well-defined only inside retained real-time segments and currently clamps unmatched timestamps incorrectly. Add scalar and vectorized projection APIs that distinguish:

- timestamps within a retained segment;
- timestamps inside a removed gap;
- timestamps before the primary range; and
- timestamps after the primary range.

The initial follower policies are:

- `next`: map an in-gap timestamp to the first primary timestamp after the gap;
- `previous`: map an in-gap timestamp to the last primary timestamp before the gap.

Before-range timestamps retain their real offset from the first source timestamp. After-range timestamps receive the final cumulative collapse shift, avoiding destructive clamping. The selected policy is stored per follower registration. Additional policies such as compressed interpolation, hiding, or rejection can be proposed later.

The toy weekly series will normally sample real candle timestamps so its expected mapping is unambiguous. Unit tests will additionally cover timestamps inside a removed gap for both initial policies.

### Decision: Keep Provider Logic in the Demo

Following `.github/skills/data-source-widgets/SKILL.md`, add a demo-owned `data_widgets` package with:

- provider-neutral `DataRequest`, `PlotSeries`, and `DataLoadResult` types;
- a small explicit provider registry;
- a `ToyEconometricDataWidget` that owns controls and selection state; and
- a deterministic toy adapter/generator that returns a weekly `PlotSeries(kind="line")`.

The widget asks the demo host to load data through a callback. It does not import or mutate `DearCyFi` plotting internals. The host adapts the normalized line result into `PlotEconometricSeries`, registers it as a follower, and leaves the hourly candle registration selected as `collapse_source_id`.

The existing candle `ToyDataBrowser` does not need to migrate as part of this change.

### Decision: Validate Through Unit and Demo Paths

Automated tests will use deterministic timestamps and values to verify:

- line-series validation and atomic updates;
- preservation of original dates after plot-date updates;
- gap-map construction from only the selected source;
- synchronized source and follower coordinates;
- `next` and `previous` behavior within removed gaps;
- source changes, removal, and restoration; and
- deterministic normalized toy results.

The demo will provide a reproducible hourly-candle plus weekly-line scenario and expose the selected collapse source in its controls or status text.

## Risks / Trade-offs

- Per-observation invisible buttons can become expensive for dense series. This first implementation targets low-frequency data; a nearest-point plot-level hover strategy remains a follow-up for event streams.
- Snapping an observation inside a removed gap can cause multiple observations to share one X coordinate. The selected policy remains explicit, while source timestamps in tooltips preserve their identity.
- Introducing a registry adds lifecycle work when data is replaced or removed. Atomic projection and restoration tests reduce the risk of partially transformed charts.
- The existing mutable `DearCyFi.dates` field conflates source and plotted dates. The implementation should route new coordination through registrations and avoid expanding that legacy state beyond compatibility needs.

## Migration Plan

1. Add projection behavior and tests without changing current candle callers.
2. Add the econometric series and its focused tests.
3. Add chart registration and select `"candles"` by default for existing `set_data(...)` usage.
4. Route collapse operations through the registry while retaining existing method names.
5. Add the demo provider contract, toy widget, and host adaptation.
6. Run unit tests and the manual demo scenario before documenting the new API.

Rollback can retain the new standalone econometric renderer while restoring candle-only collapse calls if registry integration causes regressions.

## Open Questions

- Should the public registration API accept any structural object satisfying the synchronization contract, or only DearCyFi-provided series classes in the first release?
- Should source removal automatically clear collapse state, or require an explicit restore operation before removal? The proposed default is to restore all registered series and clear the map.
