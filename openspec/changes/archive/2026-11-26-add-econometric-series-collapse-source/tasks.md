## 1. Gap Projection

- [x] 1.1 Extend `GapCollapsedTimeMap` with scalar and vectorized follower projection that handles retained segments, removed gaps, and values outside the source range.
- [x] 1.2 Implement and document the initial `next` and `previous` in-gap policies.
- [x] 1.3 Add focused tests for source timestamps, in-gap timestamps, boundary timestamps, and before/after-range timestamps.

## 2. Econometric Series

- [x] 2.1 Add `PlotEconometricSeries` using native `dcg.PlotLine` and optional `dcg.PlotScatter` rendering.
- [x] 2.2 Validate timestamp/value lengths and preserve NaN observations as line breaks by default.
- [x] 2.3 Preserve separate source and plot dates and provide atomic data and plot-date update methods.
- [x] 2.4 Add basic observation tooltips showing series label, formatted source date, and formatted value.
- [x] 2.5 Export the stable econometric series API from the package and add focused tests where GUI-independent behavior can be isolated.

## 3. Collapse Source Coordination

- [x] 3.1 Add a chart-level time-series registration model with stable IDs and per-follower projection policy.
- [x] 3.2 Add the nullable `collapse_source_id` property with validation and source-selection behavior.
- [x] 3.3 Register the candle series as `"candles"` from `set_data(...)` and use it as the default source only when no explicit source exists.
- [x] 3.4 Refactor existing collapse methods to build one map from the selected source and atomically synchronize all registered series.
- [x] 3.5 Restore real coordinates and clear collapse state when the source changes, reloads, or is removed.
- [x] 3.6 Preserve existing candle-only method calls and add regression tests for that workflow.

## 4. Toy Econometric Provider Widget

- [x] 4.1 Add demo-owned provider-neutral request/result types and an explicit data-widget registry under `examples/DearCyFi_Demo/data_widgets/`.
- [x] 4.2 Add a deterministic weekly econometric generator/adapter that returns `PlotSeries(kind="line")` with source metadata.
- [x] 4.3 Add `ToyEconometricDataWidget` controls that request data through a host callback without mutating plots.
- [x] 4.4 Adapt the demo host to create/update the econometric series, register it as a follower, and retain hourly candles as the selected collapse source.
- [x] 4.5 Add a visible source selection/status control and a reproducible hourly-candle plus weekly-econometric collapse scenario.
- [x] 4.6 Add tests for deterministic generation, normalization, and host-independent request/result behavior.

## 5. Validation and Documentation

- [x] 5.1 Run the focused gap, econometric-series, widget, and existing candle tests.
- [x] 5.2 Run the DearCyFi demo and verify line rendering, basic tooltips, source-date display, collapse synchronization, and restoration.
- [x] 5.3 Document the econometric series API, collapse-source selection, follower projection policies, and demo validation path.
