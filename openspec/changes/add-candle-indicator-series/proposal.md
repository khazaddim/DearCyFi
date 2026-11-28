# Change: Add Candle Indicator Series

## Why

Applications need to add and edit indicators such as multiple moving averages
at runtime, with each indicator following the candle data and occupying its
own legend entry. Time projection alone does not recalculate a derived series
when a candle changes.

## What Changes

- Add a reusable indicator calculation contract, a chart-facing indicator
  series, and instance management that supports creation, editing, and removal.
- Implement a simple moving average (SMA) as the first indicator, with a
  configurable positive period and open, high, low, or close input.
- Keep each indicator synchronized with complete candle replacement,
  latest-candle revisions, and appends, including collapsed-time coordinates.
- Provide a left-side demo panel for adding SMA instances and a per-instance
  right-click legend menu that opens a parameter editor and offers removal.
- Preserve menu controls across redraws and retain each indicator's identity,
  visibility, and styling when its parameters change.
- Allow each indicator instance to use an independent line color, configurable
  through the public API and demo.
- Document and test numerical results, lifecycle, error handling, streaming,
  time collapse, legend interactions, and demo behavior.

## Scope And Non-Goals

- SMA is the only implemented indicator. EMA initialization and alpha,
  Bollinger Bands, other formulas, and multi-line rendering are future changes.
- Keep the calculation/output contract extensible for future multiple candle
  inputs and named output lines, without implementing unused formula or
  rendering frameworks.
- The demo adds indicators to its DearCyFi chart, not the original-time
  comparison plot.
- Per-indicator line-thickness controls are out of scope.
- No new broker integration, background execution framework, automatic
  scrolling or fitting, historical correction API, or DearCyGui modification.

## Impact

- New capability: `candle-indicator-series`.
- Expected areas: `src/dearcyfi/core.py`, a focused indicator module, demo
  controls and plot wiring, tests, and package/demo documentation.
- Depends on the candle mutation and projection contracts in the active
  `add-incremental-series-streaming` change, which still has verification and
  review outstanding. Coordinate shared files and complete its pending work;
  do not treat it as already archived or fully verified.
- Follow `refactor-econometric-series-drawing` as prior art for composite series
  and coordinate changes to shared rendering behavior. The proposed
  `add-econometric-series-display-shift` is separate and is not required.
- Preserve existing chart and econometric APIs; this capability is additive.

## Approval

This is a proposal only. Request review and approval before implementation.
